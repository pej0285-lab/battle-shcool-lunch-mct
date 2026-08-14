# 급식 배틀 백엔드/에이전트 앱

FastAPI 기반 백엔드와 Microsoft Agent Framework 기반 멀티에이전트 분석 앱입니다.

## 선택한 에이전트 연동 방식

- **SDK**: Foundry 배포 없이 실행 가능한 GitHub Copilot SDK 친화 구조를 선택했습니다. `agent-framework`와 `agent-framework-ag-ui`를 의존성으로 포함하고, 실제 점수 산정은 테스트 가능한 전문 평가 실행기로 분리했습니다.
- **프로토콜**: 프론트엔드와 분석 앱은 `/api/analysis/ag-ui`의 AG-UI 호환 SSE 이벤트로 진행 상태와 결과를 주고받습니다. `/api/agent-framework`에서 사용한 Agent Framework AG-UI/DevUI 통합 패키지와 역할 구성을 확인할 수 있습니다.
- **MCP**: `mcp` 1.x SDK의 FastMCP로 `/mcp` 서버를 마운트하고, `search_schools`, `get_lunch` 도구를 제공합니다.
- **DevUI**: `agent_framework.devui.DevServer` 패키지 통합을 노출합니다. 워크플로우 구조는 `/api/rubric`, `/api/agent-framework`, AG-UI 이벤트에서 확인할 수 있습니다.

## 멀티에이전트 패턴

`Sequential data gate -> Concurrent expert fan-out -> deterministic score aggregation -> Sequential quality gate`

1. 데이터 게이트: 두 학교의 선택 날짜 중식 데이터가 모두 있는지 확인하고 없으면 분석을 중단합니다.
2. 병렬 전문 평가: 영양 균형, 건강성, 식재료 및 메뉴 품질 에이전트가 독립적으로 평가합니다.
3. 결정론적 집계: `(평점 / 5) × 가중치`로 100점 기준 총점을 계산합니다.
4. 최종 품질 게이트: 별도 점수는 부여하지 않는 4번째 역할로 루브릭 적용, 근거, 모순, 총점 불변 조건을 검증합니다.

## 실행

```powershell
python -m pip install -e ".[dev]"
uvicorn app.main:app --reload
```
