from __future__ import annotations

from agent_framework.ag_ui import AGUIHttpService, AgentFrameworkWorkflow, add_agent_framework_fastapi_endpoint
from agent_framework.devui import DevServer

from .rubric import PATTERN_DESCRIPTION, QUALITY_GATE_ROLE, RUBRIC_CRITERIA


def agent_framework_capabilities() -> dict:
    return {
        "packages": {
            "agentFrameworkAgUi": AGUIHttpService.__name__,
            "agentFrameworkWorkflowAdapter": AgentFrameworkWorkflow.__name__,
            "fastApiEndpointHelper": add_agent_framework_fastapi_endpoint.__name__,
            "devUi": DevServer.__name__,
        },
        "orchestrationPattern": PATTERN_DESCRIPTION,
        "roles": [criterion.agent_name for criterion in RUBRIC_CRITERIA] + [QUALITY_GATE_ROLE],
        "scoredCriteria": [
            {"key": criterion.key, "title": criterion.title, "weight": criterion.weight}
            for criterion in RUBRIC_CRITERIA
        ],
    }
