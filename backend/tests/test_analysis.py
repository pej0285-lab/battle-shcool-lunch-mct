from __future__ import annotations

from datetime import date

import pytest

from app.analysis import LunchBattleWorkflow, build_default_prompt
from app.models import Meal
from app.neis_client import NeisClient
from app.sample_data import SAMPLE_SCHOOLS


class FakeNeisClient:
    async def get_lunch(self, school, meal_date):
        if school.school_code == SAMPLE_SCHOOLS[0].school_code:
            return Meal(
                school=school,
                date=meal_date,
                menu=["현미밥", "미역국", "닭갈비", "시금치나물", "배추김치", "요구르트"],
                calories="720 Kcal",
                nutrition="탄수화물 90g / 단백질 35g / 지방 20g / 나트륨 900mg",
                origin="닭고기: 국내산",
                meal_count="500",
            )
        return Meal(
            school=school,
            date=meal_date,
            menu=["쌀밥", "햄버거스테이크", "감자튀김", "케이크"],
            calories="1120 Kcal",
            nutrition="탄수화물 130g / 단백질 22g / 지방 45g / 나트륨 1450mg",
            origin="돼지고기: 국내산",
            meal_count="480",
        )


@pytest.mark.asyncio
async def test_workflow_runs_concurrent_experts_and_aggregates_scores() -> None:
    schools = [SAMPLE_SCHOOLS[0], SAMPLE_SCHOOLS[1]]
    result = await LunchBattleWorkflow(FakeNeisClient()).run(schools, date(2026, 8, 14), "비교해줘")

    assert result.pattern.startswith("Sequential data gate -> Concurrent expert fan-out")
    assert len(result.schools) == 2
    assert result.winner == SAMPLE_SCHOOLS[0].school_name
    assert result.quality_gate.passed is True
    assert [criterion.weight for criterion in result.schools[0].criteria] == [45.0, 30.0, 25.0]
    assert result.schools[0].total_score == round(sum(criterion.weighted_score for criterion in result.schools[0].criteria), 1)


@pytest.mark.asyncio
async def test_neis_client_uses_demo_meal_when_key_is_missing_or_placeholder() -> None:
    client = NeisClient(api_key="sample")
    meal = await client.get_lunch(SAMPLE_SCHOOLS[0], date(2026, 8, 14))

    assert client.api_key is None
    assert meal.school.school_name == SAMPLE_SCHOOLS[0].school_name
    assert meal.menu
    assert meal.calories is not None


def test_default_prompt_includes_rubric_constraints() -> None:
    prompt = build_default_prompt(["A고", "B고"], date(2026, 8, 14))

    assert "EVALUATION_RUBRIC.md" in prompt
    assert "확인 가능한 NEIS 데이터" in prompt
