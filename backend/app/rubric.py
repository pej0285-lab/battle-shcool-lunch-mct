from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RubricCriterion:
    key: str
    title: str
    weight: float
    agent_name: str
    description: str


RUBRIC_CRITERIA: tuple[RubricCriterion, ...] = (
    RubricCriterion(
        key="nutrition_balance",
        title="영양 균형",
        weight=45.0,
        agent_name="영양 균형 평가 에이전트",
        description="열량, NEIS 영양정보, 주식·국/찌개·주찬·부찬·채소·과일/유제품 등 확인 가능한 식품군 구성을 평가합니다.",
    ),
    RubricCriterion(
        key="healthiness",
        title="건강성",
        weight=30.0,
        agent_name="건강성 평가 에이전트",
        description="NEIS 영양 수치와 메뉴명에서 직접 확인되는 튀김·가공육·당류 높은 후식 신호만 제한적으로 평가합니다.",
    ),
    RubricCriterion(
        key="ingredient_menu_quality",
        title="식재료 및 메뉴 품질",
        weight=25.0,
        agent_name="식재료 및 메뉴 품질 평가 에이전트",
        description="메뉴와 원산지 정보로 확인 가능한 식재료 다양성, 메뉴 조화, 중복 여부, 한 끼 구성 완성도를 평가합니다.",
    ),
)


QUALITY_GATE_ROLE = "최종 평가자 품질 게이트"
PATTERN_DESCRIPTION = "Sequential data gate -> Concurrent expert fan-out -> deterministic score aggregation -> Sequential quality gate"


def validate_rubric_weights() -> None:
    total = sum(criterion.weight for criterion in RUBRIC_CRITERIA)
    if round(total, 1) != 100.0:
        raise ValueError(f"루브릭 가중치 합계는 100%여야 합니다. 현재 합계: {total}%")
