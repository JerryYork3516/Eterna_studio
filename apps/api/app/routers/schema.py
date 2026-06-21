"""GET /schema/workflow — Contract §7.2.

Returns the Workflow JSON Schema (exported from Pydantic) so the frontend can
generate TS types.
"""

from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter

from ..models.workflow import Workflow

router = APIRouter(prefix="/schema", tags=["schema"])


@router.get("/workflow")
def workflow_schema() -> Dict[str, Any]:
    return Workflow.model_json_schema()
