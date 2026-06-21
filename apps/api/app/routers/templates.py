"""Templates — Contract §7.3, §7.4."""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter
from pydantic import BaseModel

from ..models.template import TemplateDefinition
from ..models.workflow import Workflow
from ..services import persona_builder

router = APIRouter(prefix="/templates", tags=["templates"])

# Built-in templates (§7.3). Only persona_builder is materialized in MVP.
_TEMPLATES = [
    TemplateDefinition(
        template_type="blank",
        name="Blank",
        description="Empty canvas.",
        builder="blank",
    ),
    TemplateDefinition(
        template_type="persona_builder",
        name="Persona Builder",
        description="13-layer persona trunk (Contract §8).",
        builder="persona_builder",
    ),
    TemplateDefinition(
        template_type="agent",
        name="Agent",
        description="Agent-centric workflow.",
        builder="agent",
    ),
    TemplateDefinition(
        template_type="knowledge_pipeline",
        name="Knowledge Pipeline",
        description="Knowledge ingestion / processing pipeline.",
        builder="knowledge_pipeline",
    ),
    TemplateDefinition(
        template_type="review_pipeline",
        name="Review Pipeline",
        description="Review-centric pipeline.",
        builder="review_pipeline",
    ),
]


class TemplatesListResponse(BaseModel):
    templates: List[TemplateDefinition]


class PersonaBuilderRequest(BaseModel):
    name: Optional[str] = None
    ui_language: Optional[str] = None  # "zh" | "en"


class PersonaBuilderResponse(BaseModel):
    workflow: Workflow


@router.get("/list", response_model=TemplatesListResponse)
def list_templates() -> TemplatesListResponse:
    return TemplatesListResponse(templates=_TEMPLATES)


@router.post("/persona-builder", response_model=PersonaBuilderResponse)
def create_persona_builder(req: PersonaBuilderRequest) -> PersonaBuilderResponse:
    workflow = persona_builder.build(
        name=req.name,
        ui_language=req.ui_language or "zh",
    )
    return PersonaBuilderResponse(workflow=workflow)
