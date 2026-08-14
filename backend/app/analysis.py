from __future__ import annotations

import asyncio
import re
from datetime import date
from typing import Iterable

from .models import AnalysisResult, CriterionScore, Meal, QualityGate, SchoolEvaluation
from .neis_client import NeisClient, NoMealDataError
from .rubric import PATTERN_DESCRIPTION, RUBRIC_CRITERIA, RubricCriterion, validate_rubric_weights


class AgentWorkflowInputError(ValueError):
    pass


MAIN_FOOD_SIGNALS = ("밥", "비빔", "덮밥", "볶음밥", "국수", "면", "스파게티", "빵")
SOUP_SIGNALS = ("국", "탕", "찌개", "스프")
PROTEIN_SIGNALS = ("고기", "돼지", "소고기", "닭", "치킨", "계란", "달걀", "두부", "생선", "오징어", "새우", "장어", "함박")
VEGETABLE_SIGNALS = ("나물", "샐러드", "김치", "깍두기", "오이", "상추", "채소", "무침", "브로콜리", "시금치")
FRUIT_DAIRY_SIGNALS = ("과일", "사과", "배", "귤", "바나나", "요거트", "요구르트", "우유", "치즈")
BURDEN_SIGNALS = ("튀김", "프라이", "치킨", "돈까스", "소시지", "햄", "핫도그", "케이크", "초코", "쿠키", "도넛", "아이스")


class LunchBattleWorkflow:
    def __init__(self, neis_client: NeisClient | None = None) -> None:
        validate_rubric_weights()
        self.neis_client = neis_client or NeisClient()

    async def run(self, schools: list, meal_date: date, prompt: str) -> AnalysisResult:
        if len({school.school_code for school in schools}) != 2:
            raise AgentWorkflowInputError("서로 다른 학교 2개를 선택해야 합니다.")

        meals = await asyncio.gather(*(self.neis_client.get_lunch(school, meal_date) for school in schools))
        if len(meals) != 2:
            raise NoMealDataError("두 학교의 중식 데이터가 모두 필요합니다.")

        expert_results = await asyncio.gather(
            *(self._evaluate_criterion(criterion, meals) for criterion in RUBRIC_CRITERIA)
        )
        evaluations = self._aggregate(meals, expert_results)
        quality_gate = self._quality_gate(evaluations)
        winner, is_tie = self._decide_winner(evaluations)
        return AnalysisResult(
            pattern=PATTERN_DESCRIPTION,
            schools=evaluations,
            winner=winner,
            is_tie=is_tie,
            overall_commentary=self._overall_commentary(evaluations, winner, is_tie),
            improvements={evaluation.school.school_name: self._improvements(evaluation) for evaluation in evaluations},
            quality_gate=quality_gate,
        )

    async def _evaluate_criterion(self, criterion: RubricCriterion, meals: list[Meal]) -> dict[str, CriterionScore]:
        await asyncio.sleep(0)
        return {meal.school.school_code: self._score_meal(criterion, meal) for meal in meals}

    def _score_meal(self, criterion: RubricCriterion, meal: Meal) -> CriterionScore:
        if criterion.key == "nutrition_balance":
            rating, evidence, rationale = self._score_nutrition_balance(meal)
        elif criterion.key == "healthiness":
            rating, evidence, rationale = self._score_healthiness(meal)
        else:
            rating, evidence, rationale = self._score_ingredient_quality(meal)

        return CriterionScore(
            key=criterion.key,  # type: ignore[arg-type]
            title=criterion.title,
            weight=criterion.weight,
            rating=rating,
            weighted_score=round((rating / 5) * criterion.weight, 1),
            evidence=evidence,
            rationale=rationale,
        )

    def _score_nutrition_balance(self, meal: Meal) -> tuple[int, list[str], str]:
        menu_text = " ".join(meal.menu)
        groups = {
            "주식": any(signal in menu_text for signal in MAIN_FOOD_SIGNALS),
            "국/찌개": any(signal in menu_text for signal in SOUP_SIGNALS),
            "단백질": any(signal in menu_text for signal in PROTEIN_SIGNALS),
            "채소": any(signal in menu_text for signal in VEGETABLE_SIGNALS),
            "과일/유제품": any(signal in menu_text for signal in FRUIT_DAIRY_SIGNALS),
        }
        group_count = sum(groups.values())
        calories = _extract_first_number(meal.calories)
        rating = 2 + min(group_count, 3)
        if group_count >= 4:
            rating = 4
        if group_count == 5 and (calories is None or 500 <= calories <= 1000):
            rating = 5
        if calories is not None and (calories < 450 or calories > 1100):
            rating = max(1, rating - 1)

        evidence = [f"확인 식품군: {', '.join(name for name, present in groups.items() if present) or '제한적'}"]
        if meal.calories:
            evidence.append(f"열량: {meal.calories}")
        if meal.nutrition:
            evidence.append(f"NEIS 영양정보 제공: {meal.nutrition}")
        return rating, evidence, "확인 가능한 식품군 구성과 열량 범위를 함께 반영했습니다."

    def _score_healthiness(self, meal: Meal) -> tuple[int, list[str], str]:
        menu_text = " ".join(meal.menu)
        burden_count = sum(1 for signal in BURDEN_SIGNALS if signal in menu_text)
        sodium = _extract_named_number(meal.nutrition, "나트륨")
        rating = 5
        if burden_count:
            rating -= min(burden_count, 3)
        if sodium is not None and sodium > 1300:
            rating -= 1
        rating = max(1, min(5, rating))
        if not meal.nutrition and burden_count == 0:
            rating = min(rating, 4)

        evidence = []
        if meal.nutrition:
            evidence.append(f"NEIS 영양정보: {meal.nutrition}")
        if burden_count:
            evidence.append(f"메뉴명에서 직접 확인되는 부담 신호 {burden_count}개: {', '.join(signal for signal in BURDEN_SIGNALS if signal in menu_text)}")
        if not evidence:
            evidence.append("제공 데이터에서 뚜렷한 건강 부담 신호가 제한적으로 확인됩니다.")
        return rating, evidence, "나트륨 등 제공 수치와 메뉴명에 직접 드러난 부담 신호만 사용했습니다."

    def _score_ingredient_quality(self, meal: Meal) -> tuple[int, list[str], str]:
        normalized_items = {_normalize_menu_name(item) for item in meal.menu}
        variety = len(normalized_items)
        has_origin = bool(meal.origin and meal.origin.strip())
        duplicate_penalty = len(meal.menu) - variety
        rating = 2
        if variety >= 4:
            rating = 3
        if variety >= 5 and has_origin:
            rating = 4
        if variety >= 6 and has_origin and duplicate_penalty == 0:
            rating = 5
        if duplicate_penalty >= 2:
            rating = max(1, rating - 1)

        evidence = [f"메뉴 항목 수: {len(meal.menu)}개, 중복 제외: {variety}개"]
        if meal.origin:
            evidence.append("원산지 정보 제공")
        return rating, evidence, "메뉴 다양성, 중복 여부, 원산지 정보 제공 여부를 확인 가능한 범위에서 평가했습니다."

    def _aggregate(self, meals: list[Meal], expert_results: tuple[dict[str, CriterionScore], ...]) -> list[SchoolEvaluation]:
        evaluations: list[SchoolEvaluation] = []
        for meal in meals:
            criteria = [result[meal.school.school_code] for result in expert_results]
            total = round(sum(score.weighted_score for score in criteria), 1)
            evaluations.append(
                SchoolEvaluation(
                    school=meal.school,
                    criteria=criteria,
                    total_score=total,
                    summary=f"{meal.school.school_name}은(는) {total:.1f}점으로 평가되었습니다.",
                )
            )
        return evaluations

    def _quality_gate(self, evaluations: list[SchoolEvaluation]) -> QualityGate:
        findings: list[str] = []
        for evaluation in evaluations:
            keys = {criterion.key for criterion in evaluation.criteria}
            if keys != {criterion.key for criterion in RUBRIC_CRITERIA}:
                findings.append(f"{evaluation.school.school_name}: 루브릭 평가영역이 누락되었습니다.")
            computed = round(sum(criterion.weighted_score for criterion in evaluation.criteria), 1)
            if computed != evaluation.total_score:
                findings.append(f"{evaluation.school.school_name}: 총점 계산이 일치하지 않습니다.")
            for criterion in evaluation.criteria:
                if not criterion.evidence:
                    findings.append(f"{evaluation.school.school_name} {criterion.title}: 근거가 없습니다.")
        if not findings:
            findings.append("루브릭 기준, 근거, 환산 점수, 총점 불변 조건을 통과했습니다.")
        return QualityGate(passed=len(findings) == 1 and findings[0].startswith("루브릭"), findings=findings)

    def _decide_winner(self, evaluations: list[SchoolEvaluation]) -> tuple[str | None, bool]:
        first, second = evaluations
        if first.total_score == second.total_score:
            return None, True
        return (first.school.school_name if first.total_score > second.total_score else second.school.school_name), False

    def _overall_commentary(self, evaluations: list[SchoolEvaluation], winner: str | None, is_tie: bool) -> str:
        if is_tie:
            return "두 학교의 총점이 같아 동점입니다. 영역별 강점과 개선점이 다르므로 세부 평가를 함께 확인해야 합니다."
        scores = ", ".join(f"{evaluation.school.school_name} {evaluation.total_score:.1f}점" for evaluation in evaluations)
        return f"총점 기준 승자는 {winner}입니다. {scores}으로 집계되었습니다."

    def _improvements(self, evaluation: SchoolEvaluation) -> list[str]:
        weakest = sorted(evaluation.criteria, key=lambda criterion: criterion.rating)[0]
        return [
            f"{weakest.title} 영역의 보완이 우선입니다.",
            "NEIS에 제공된 메뉴·영양·원산지 데이터로 확인 가능한 항목을 중심으로 개선안을 검토하세요.",
        ]


def build_default_prompt(school_names: Iterable[str], meal_date: date) -> str:
    names = " vs ".join(school_names)
    return (
        f"{meal_date.isoformat()} 중식을 기준으로 {names} 급식을 비교해 주세요. "
        "EVALUATION_RUBRIC.md의 영양 균형, 건강성, 식재료 및 메뉴 품질 기준을 적용하고 "
        "확인 가능한 NEIS 데이터에 근거한 주장만 작성해 주세요."
    )


def _extract_first_number(value: str | None) -> float | None:
    if not value:
        return None
    match = re.search(r"(\d+(?:\.\d+)?)", value.replace(",", ""))
    return float(match.group(1)) if match else None


def _extract_named_number(value: str | None, name: str) -> float | None:
    if not value or name not in value:
        return None
    tail = value.split(name, 1)[1]
    return _extract_first_number(tail)


def _normalize_menu_name(value: str) -> str:
    return re.sub(r"\s+", "", value)
