"""Workflow operations — Contract §7.5, §7.6, §7.7."""

from __future__ import annotations

from typing import List, Literal

from fastapi import APIRouter
from pydantic import BaseModel

from ..models.export import ExportPreview
from ..models.review import ValidationReview
from ..models.run import RunResult
from ..models.workflow import Workflow
from ..services import exporter, mock_runner, validator

router = APIRouter(prefix="/workflow", tags=["workflow"])


# --- §7.5 validate ---
class ValidateRequest(BaseModel):
    workflow: Workflow


class ValidateResponse(BaseModel):
    package: ValidationReview
    layers: List[ValidationReview]
    nodes: List[ValidationReview]


@router.post("/validate", response_model=ValidateResponse)
def validate(req: ValidateRequest) -> ValidateResponse:
    package, layers, nodes = validator.validate(req.workflow)
    return ValidateResponse(package=package, layers=layers, nodes=nodes)


# --- §7.6 mock-run ---
class MockRunRequest(BaseModel):
    workflow: Workflow


class MockRunResponse(BaseModel):
    run: RunResult


@router.post("/mock-run", response_model=MockRunResponse)
def mock_run(req: MockRunRequest) -> MockRunResponse:
    return MockRunResponse(run=mock_runner.mock_run(req.workflow))


# --- §7.7 export-preview ---
class ExportPreviewRequest(BaseModel):
    workflow: Workflow
    export_kind: Literal["workflow_json", "persona"]


class ExportPreviewResponse(BaseModel):
    preview: ExportPreview


@router.post("/export-preview", response_model=ExportPreviewResponse)
def export_preview(req: ExportPreviewRequest) -> ExportPreviewResponse:
    preview = exporter.export_preview(req.workflow, req.export_kind)
    return ExportPreviewResponse(preview=preview)
