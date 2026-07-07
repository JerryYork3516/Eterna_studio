"""Studio Assistant API router.

The /studio-assistant routes are intentionally isolated from /runtime routes.
They are Canvas configuration helpers only and never execute residents.
"""

from __future__ import annotations

from fastapi import APIRouter

from ..services.studio_assistant_service import (
    AssistantMode,
    StudioAssistantRequest,
    StudioAssistantResponse,
    run_studio_assistant,
)

router = APIRouter(prefix="/studio-assistant", tags=["studio-assistant"])


def _with_mode(request: StudioAssistantRequest, mode: AssistantMode) -> StudioAssistantRequest:
    data = request.model_dump()
    data["mode"] = mode
    return StudioAssistantRequest(**data)


@router.post("/explain", response_model=StudioAssistantResponse)
def explain(request: StudioAssistantRequest) -> StudioAssistantResponse:
    return run_studio_assistant(_with_mode(request, "explain"))


@router.post("/recommend", response_model=StudioAssistantResponse)
def recommend(request: StudioAssistantRequest) -> StudioAssistantResponse:
    return run_studio_assistant(_with_mode(request, "recommend"))


@router.post("/audit", response_model=StudioAssistantResponse)
def audit(request: StudioAssistantRequest) -> StudioAssistantResponse:
    return run_studio_assistant(_with_mode(request, "audit"))


@router.post("/check-conflicts", response_model=StudioAssistantResponse)
def check_conflicts(request: StudioAssistantRequest) -> StudioAssistantResponse:
    return run_studio_assistant(_with_mode(request, "check_conflicts"))
