from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class School(BaseModel):
    office_code: str
    office_name: str
    school_code: str
    school_name: str
    region: str | None = None
    kind: str | None = None


class Meal(BaseModel):
    school: School
    date: date
    meal_name: str = "중식"
    menu: list[str]
    calories: str | None = None
    nutrition: str | None = None
    origin: str | None = None
    meal_count: str | None = None


class MealComparisonInput(BaseModel):
    schools: list[School] = Field(min_length=2, max_length=2)
    meal_date: date
    prompt: str = Field(min_length=1)


class CriterionScore(BaseModel):
    key: Literal["nutrition_balance", "healthiness", "ingredient_menu_quality"]
    title: str
    weight: float
    rating: int = Field(ge=1, le=5)
    weighted_score: float
    evidence: list[str]
    rationale: str


class SchoolEvaluation(BaseModel):
    school: School
    criteria: list[CriterionScore]
    total_score: float
    summary: str


class QualityGate(BaseModel):
    passed: bool
    findings: list[str]
    non_scored_role: str = "최종 평가자 품질 게이트"


class AnalysisResult(BaseModel):
    pattern: str
    schools: list[SchoolEvaluation]
    winner: str | None
    is_tie: bool
    overall_commentary: str
    improvements: dict[str, list[str]]
    quality_gate: QualityGate


class AnalysisRequest(BaseModel):
    schools: list[School] = Field(min_length=2, max_length=2)
    meal_date: date
    prompt: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_distinct_schools(self) -> "AnalysisRequest":
        codes = {school.school_code for school in self.schools}
        if len(codes) != 2:
            raise ValueError("서로 다른 학교 2개를 선택해야 합니다.")
        return self


class PromptRequest(BaseModel):
    schools: list[School] = Field(min_length=2, max_length=2)
    meal_date: date


class AgUiEvent(BaseModel):
    type: str
    message: str | None = None
    data: AnalysisResult | dict | None = None
