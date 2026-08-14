from __future__ import annotations

import random
from datetime import date

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from .agui import agui_sse_stream
from .analysis import AgentWorkflowInputError, LunchBattleWorkflow, build_default_prompt
from .maf_integration import agent_framework_capabilities
from .models import AnalysisRequest, PromptRequest
from .mcp_server import mcp
from .neis_client import NeisClient, NeisClientError, NoMealDataError
from .rubric import PATTERN_DESCRIPTION, QUALITY_GATE_ROLE, RUBRIC_CRITERIA
from .sample_data import SAMPLE_SCHOOLS

app = FastAPI(title="급식 배틀 API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/mcp", mcp.streamable_http_app())


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/schools/random")
async def random_schools(count: int = Query(default=10, ge=2, le=10)) -> list[dict]:
    schools = list(SAMPLE_SCHOOLS)
    random.Random(date.today().isoformat()).shuffle(schools)
    return [school.model_dump() for school in schools[:count]]


@app.get("/api/schools/search")
async def search_schools(q: str = Query(min_length=1), limit: int = Query(default=10, ge=1, le=20)) -> list[dict]:
    schools = await NeisClient().search_schools(q, limit)
    return [school.model_dump() for school in schools]


@app.get("/api/rubric")
async def rubric() -> dict:
    return {
        "pattern": PATTERN_DESCRIPTION,
        "scoredCriteria": [criterion.__dict__ for criterion in RUBRIC_CRITERIA],
        "qualityGate": QUALITY_GATE_ROLE,
        "scoreScale": "각 가중 평가영역은 1~5점으로 평가한 뒤 (평점 / 5) × 가중치로 100점 기준 총점에 합산합니다.",
    }


@app.get("/api/agent-framework")
async def agent_framework() -> dict:
    return agent_framework_capabilities()


@app.post("/api/analysis/default-prompt")
async def default_prompt(request: PromptRequest) -> dict[str, str]:
    return {"prompt": build_default_prompt((school.school_name for school in request.schools), request.meal_date)}


@app.post("/api/analysis")
async def analyze(request: AnalysisRequest) -> dict:
    try:
        result = await LunchBattleWorkflow().run(request.schools, request.meal_date, request.prompt)
    except NoMealDataError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (AgentWorkflowInputError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except NeisClientError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return result.model_dump(mode="json")


@app.post("/api/analysis/ag-ui")
async def analyze_ag_ui(request: AnalysisRequest) -> StreamingResponse:
    async def run() -> object:
        return await LunchBattleWorkflow().run(request.schools, request.meal_date, request.prompt)

    return StreamingResponse(agui_sse_stream(run), media_type="text/event-stream")
