"""Resident API contracts for Schema Contract v0.3.

Endpoints return contract DTOs only. They do not call LLM, TTS, AR runtime, or
workflow execution services.
"""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from ..models.v0_3 import (
    AuditReportV03,
    OutputDtoV03,
    ResidentCompileRequestV03,
    ResidentCompileResponseV03,
    ResidentInstanceV03,
    ResidentPreviewRequestV03,
    ResidentPreviewResponseV03,
)
from ..services.audit_v0_3 import audit_resident
from ..services.workflow_v0_3 import compile_resident_from_workflow, normalize_workflow_v0_3

router = APIRouter(prefix="/resident", tags=["resident-v0.3"])


class ResidentAuditRequest(BaseModel):
    resident_instance: ResidentInstanceV03


class ResidentAuditResponse(BaseModel):
    audit: AuditReportV03


@router.post("/compile", response_model=ResidentCompileResponseV03)
def compile_resident(req: ResidentCompileRequestV03) -> ResidentCompileResponseV03:
    if req.workflow is not None:
        workflow = normalize_workflow_v0_3(req.workflow)
        resident = compile_resident_from_workflow(workflow)
    else:
        resident = req.resident_instance or ResidentInstanceV03()
    return ResidentCompileResponseV03(resident_instance=resident, audit=audit_resident(resident))


@router.post("/audit", response_model=ResidentAuditResponse)
def audit(req: ResidentAuditRequest) -> ResidentAuditResponse:
    return ResidentAuditResponse(audit=audit_resident(req.resident_instance))


@router.post("/preview", response_model=ResidentPreviewResponseV03)
def preview(req: ResidentPreviewRequestV03) -> ResidentPreviewResponseV03:
    resident = req.resident_instance
    preview = OutputDtoV03(
        kind="resident_preview",
        data={
            "identity": resident.identity.model_dump(mode="json"),
            "personality": resident.personality.model_dump(mode="json"),
            "dialogue": resident.dialogue.model_dump(mode="json"),
            "voice_profile": resident.voice_profile.model_dump(mode="json"),
            "avatar": resident.avatar.model_dump(mode="json"),
        },
        metadata=resident.metadata.model_dump(mode="json"),
    )
    return ResidentPreviewResponseV03(preview=preview, audit=audit_resident(resident))
