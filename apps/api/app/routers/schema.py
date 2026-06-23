"""GET /schema/workflow — Contract §7.2.

Returns the Workflow JSON Schema (exported from Pydantic) so the frontend can
generate TS types.
"""

from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter

from ..models.v0_3 import ResidentInstanceV03, WorkflowV03
from ..registry.node_registry import NODE_REGISTRY

router = APIRouter(prefix="/schema", tags=["schema"])


@router.get("/workflow")
def workflow_schema() -> Dict[str, Any]:
    return WorkflowV03.model_json_schema()


@router.get("/workflow-v0.3")
def workflow_schema_v0_3() -> Dict[str, Any]:
    return WorkflowV03.model_json_schema()


@router.get("/resident-instance-v0.3")
def resident_instance_schema_v0_3() -> Dict[str, Any]:
    return ResidentInstanceV03.model_json_schema()


@router.get("/node-registry-v0.3")
def node_registry_v0_3() -> Dict[str, Any]:
    return {key: value.model_dump(mode="json") for key, value in NODE_REGISTRY.items()}
