"""Workflow API router — v0.3 is the single runtime path."""

from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter
from pydantic import BaseModel

from ..models.export import ExportPreview
from ..models.run import RunResult
from ..models.v0_3 import AuditReportV03, WorkflowValidationResponseV03
from ..services.audit_v0_3 import audit_workflow
from ..services.workflow_v0_3 import export_preview_v0_3, mock_run_v0_3, normalize_workflow_v0_3

router = APIRouter(prefix="/workflow", tags=["workflow-v0.3"])


class WorkflowPayloadRequest(BaseModel):
    workflow: Any


class AuditResponse(BaseModel):
    audit: AuditReportV03


@router.post("/validate", response_model=WorkflowValidationResponseV03)
def validate(req: WorkflowPayloadRequest) -> WorkflowValidationResponseV03:
    workflow = normalize_workflow_v0_3(req.workflow)
    audit = audit_workflow(workflow)
    return WorkflowValidationResponseV03(valid=audit.status != "FAIL", audit=audit)


@router.post("/audit", response_model=AuditResponse)
def audit(req: WorkflowPayloadRequest) -> AuditResponse:
    workflow = normalize_workflow_v0_3(req.workflow)
    return AuditResponse(audit=audit_workflow(workflow))


class MockRunResponse(BaseModel):
    run: RunResult


@router.post("/mock-run", response_model=MockRunResponse)
def mock_run(req: WorkflowPayloadRequest) -> MockRunResponse:
    workflow = normalize_workflow_v0_3(req.workflow)
    return MockRunResponse(run=mock_run_v0_3(workflow))


class ExportPreviewRequest(BaseModel):
    workflow: Any
    export_kind: Literal["workflow_json", "persona", "resident"]


class ExportPreviewResponse(BaseModel):
    preview: ExportPreview


@router.post("/export-preview", response_model=ExportPreviewResponse)
def export_preview(req: ExportPreviewRequest) -> ExportPreviewResponse:
    workflow = normalize_workflow_v0_3(req.workflow)
    return ExportPreviewResponse(preview=export_preview_v0_3(workflow, req.export_kind))
