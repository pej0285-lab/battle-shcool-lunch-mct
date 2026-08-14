from __future__ import annotations

import json
from collections.abc import AsyncIterator, Awaitable, Callable

from pydantic import BaseModel


class AgUiRunEvent(BaseModel):
    type: str
    message: str | None = None
    data: object | None = None


async def agui_sse_stream(run_analysis: Callable[[], Awaitable[object]]) -> AsyncIterator[str]:
    yield _encode(AgUiRunEvent(type="RUN_STARTED", message="분석 워크플로우를 시작합니다."))
    yield _encode(AgUiRunEvent(type="TEXT_MESSAGE_CONTENT", message="데이터 게이트를 통과하면 3개 전문 평가 에이전트를 병렬 실행합니다."))
    try:
        result = await run_analysis()
    except Exception as exc:
        yield _encode(AgUiRunEvent(type="RUN_ERROR", message=str(exc)))
        return
    yield _encode(AgUiRunEvent(type="TEXT_MESSAGE_CONTENT", message="최종 평가자 품질 게이트를 완료했습니다."))
    yield _encode(AgUiRunEvent(type="RUN_FINISHED", data=_dump_model(result)))


def _encode(event: AgUiRunEvent) -> str:
    return f"data: {event.model_dump_json(exclude_none=True)}\n\n"


def _dump_model(value: object) -> object:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    try:
        return json.loads(json.dumps(value))
    except TypeError:
        return str(value)
