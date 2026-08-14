from __future__ import annotations

from datetime import date

from mcp.server.fastmcp import FastMCP

from .models import School
from .neis_client import NeisClient

mcp = FastMCP(
    "battle-school-lunch-mcp",
    instructions="NEIS 공개 API 기반 학교 검색과 선택 날짜 중식 조회 도구를 제공합니다.",
)


@mcp.tool()
async def search_schools(keyword: str, limit: int = 10) -> list[dict]:
    """학교명 일부로 학교 후보를 검색합니다."""
    schools = await NeisClient().search_schools(keyword, limit)
    return [school.model_dump(mode="json") for school in schools]


@mcp.tool()
async def get_lunch(
    office_code: str,
    office_name: str,
    school_code: str,
    school_name: str,
    meal_date: str,
    region: str | None = None,
    kind: str | None = None,
) -> dict:
    """선택한 학교와 날짜의 중식 정보를 조회합니다."""
    school = School(
        office_code=office_code,
        office_name=office_name,
        school_code=school_code,
        school_name=school_name,
        region=region,
        kind=kind,
    )
    meal = await NeisClient().get_lunch(school, date.fromisoformat(meal_date))
    return meal.model_dump(mode="json")
