from __future__ import annotations

import os
import re
from datetime import date
from typing import Any

import httpx

from .models import Meal, School
from .sample_data import SAMPLE_SCHOOLS


class NeisClientError(RuntimeError):
    pass


class NoMealDataError(ValueError):
    pass


class NeisClient:
    INVALID_API_KEY_VALUES = {"sample", "demo", "placeholder", "invalid", "test", "none"}

    def __init__(self, api_key: str | None = None, base_url: str = "https://open.neis.go.kr") -> None:
        raw_key = api_key if api_key is not None else os.getenv("NEIS_API_KEY")
        self.api_key = self._normalize_api_key(raw_key)
        self.base_url = base_url.rstrip("/")

    @classmethod
    def _normalize_api_key(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized or normalized.lower() in cls.INVALID_API_KEY_VALUES:
            return None
        return normalized

    async def search_schools(self, keyword: str, limit: int = 10) -> list[School]:
        normalized_keyword = keyword.strip()
        if not normalized_keyword:
            return []

        if self.api_key is None:
            fallback = [school for school in SAMPLE_SCHOOLS if normalized_keyword in school.school_name]
            return fallback[:limit]

        try:
            rows = await self._get_rows(
                "/hub/schoolInfo",
                {"SCHUL_NM": normalized_keyword, "pSize": min(max(limit, 1), 100)},
                "schoolInfo",
            )
        except NeisClientError:
            rows = []

        schools = [self._school_from_row(row) for row in rows]
        if schools:
            return schools[:limit]

        fallback = [school for school in SAMPLE_SCHOOLS if normalized_keyword in school.school_name]
        return fallback[:limit]

    async def get_lunch(self, school: School, meal_date: date) -> Meal:
        if self.api_key is None:
            return self._demo_meal(school, meal_date)

        rows = await self._get_rows(
            "/hub/mealServiceDietInfo",
            {
                "ATPT_OFCDC_SC_CODE": school.office_code,
                "SD_SCHUL_CODE": school.school_code,
                "MMEAL_SC_CODE": "2",
                "MLSV_YMD": meal_date.strftime("%Y%m%d"),
            },
            "mealServiceDietInfo",
        )
        lunch_rows = [row for row in rows if row.get("MMEAL_SC_CODE") == "2" or row.get("MMEAL_SC_NM") == "중식"]
        if not lunch_rows:
            raise NoMealDataError(f"{school.school_name}의 선택 날짜 중식 데이터가 없습니다.")
        return self._meal_from_row(school, meal_date, lunch_rows[0])

    def _demo_meal(self, school: School, meal_date: date) -> Meal:
        menu_templates = [
            ["현미밥", "된장찌개", "닭가슴살볶음", "배추김치", "오이무침", "사과"],
            ["보리밥", "김치찌개", "제육볶음", "시금치나물", "요구르트", "미나리무침"],
            ["쌀밥", "쇠고기미역국", "훈제오리볶음", "콩나물무침", "배추김치", "바나나"],
        ]
        seed = sum(ord(ch) for ch in school.school_code) % len(menu_templates)
        menu = menu_templates[seed]
        return Meal(
            school=school,
            date=meal_date,
            meal_name="중식",
            menu=menu,
            calories="720 Kcal",
            nutrition="탄수화물 95g / 단백질 28g / 지방 18g / 나트륨 850mg",
            origin="주요 식재료: 국내산",
            meal_count="500",
        )

    async def _get_rows(self, path: str, params: dict[str, Any], root_key: str) -> list[dict[str, Any]]:
        request_params = {
            "Key": self.api_key,
            "Type": "json",
            "pIndex": 1,
            "pSize": 100,
            **params,
        }
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.base_url}{path}", params=request_params)
                response.raise_for_status()
        except httpx.HTTPError as exc:
            raise NeisClientError("NEIS API 호출에 실패했습니다.") from exc

        payload = response.json()
        if root_key not in payload:
            result = payload.get("RESULT", {})
            code = result.get("CODE")
            if code == "INFO-200":
                return []
            message = result.get("MESSAGE", "NEIS API 응답을 해석할 수 없습니다.")
            if "인증" in message or "유효" in message or "KEY" in str(code or ""):
                raise NeisClientError(
                    "NEIS API 인증키가 유효하지 않습니다. NEIS API 키를 확인하거나 환경 변수 NEIS_API_KEY를 비워 데모 모드로 실행하세요."
                )
            raise NeisClientError(message)

        sections = payload[root_key]
        for section in sections:
            if "row" in section:
                return section["row"]
        return []

    def _school_from_row(self, row: dict[str, Any]) -> School:
        return School(
            office_code=str(row.get("ATPT_OFCDC_SC_CODE", "")),
            office_name=str(row.get("ATPT_OFCDC_SC_NM", "")),
            school_code=str(row.get("SD_SCHUL_CODE", "")),
            school_name=str(row.get("SCHUL_NM", "")),
            region=row.get("LCTN_SC_NM"),
            kind=row.get("SCHUL_KND_SC_NM"),
        )

    def _meal_from_row(self, school: School, meal_date: date, row: dict[str, Any]) -> Meal:
        menu_text = str(row.get("DDISH_NM", ""))
        menu = [self._clean_menu_item(item) for item in re.split(r"<br\s*/?>|\n", menu_text) if item.strip()]
        return Meal(
            school=school,
            date=meal_date,
            meal_name=str(row.get("MMEAL_SC_NM", "중식")),
            menu=menu,
            calories=row.get("CAL_INFO"),
            nutrition=row.get("NTR_INFO"),
            origin=row.get("ORPLC_INFO"),
            meal_count=row.get("MLSV_FGR"),
        )

    def _clean_menu_item(self, item: str) -> str:
        return re.sub(r"\s*\([^)]*\)", "", item).strip()
