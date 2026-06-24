"""GET /schema/workflow — Contract §7.2.

Returns the Workflow JSON Schema (exported from Pydantic) so the frontend can
generate TS types.
"""

from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter

from ..models.v0_3 import ResidentInstanceV03, WorkflowV03
from ..models.v0_4 import (
    EngineRegistryResponseV04,
    ModuleCatalogResponseV04,
    PROTOCOL_VERSION_V0_4,
    SCHEMA_VERSION_V0_4,
    SlotCatalogResponseV04,
)
from ..models.v0_4 import LayerRefV04
from ..registry.engine_registry import get_engine_registry
from ..registry.module_catalog import get_module_catalog
from ..registry.node_registry import NODE_REGISTRY
from ..registry.slot_catalog import get_slot_catalog
from ..models.v0_4 import CANONICAL_LAYERS

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


# --- Protocol v0.4 read-only endpoints (additive; no existing API removed) ---
@router.get("/protocol-version")
def protocol_version() -> Dict[str, Any]:
    return {"schema_version": SCHEMA_VERSION_V0_4, "protocol_version": PROTOCOL_VERSION_V0_4}


@router.get("/node-registry-v0.4")
def node_registry_v0_4() -> Dict[str, Any]:
    # Node type definitions are version-agnostic content (input/output schema,
    # status, mock_executor, audit_rules). v0.4 reuses the same registry; the
    # response shape is identical to /schema/node-registry-v0.3 (a map keyed by
    # node type) so the frontend single source can switch URL with no reshape.
    return {key: value.model_dump(mode="json") for key, value in NODE_REGISTRY.items()}


@router.get("/module-catalog-v0.4", response_model=ModuleCatalogResponseV04)
def module_catalog_v0_4() -> ModuleCatalogResponseV04:
    layers = [LayerRefV04(layer_id=lid, layer_name=name, layer_order=order) for lid, name, order in CANONICAL_LAYERS]
    return ModuleCatalogResponseV04(layers=layers, modules=get_module_catalog())


@router.get("/slot-catalog-v0.4", response_model=SlotCatalogResponseV04)
def slot_catalog_v0_4() -> SlotCatalogResponseV04:
    return SlotCatalogResponseV04(slots=get_slot_catalog())


@router.get("/engine-registry-v0.4", response_model=EngineRegistryResponseV04)
def engine_registry_v0_4() -> EngineRegistryResponseV04:
    return EngineRegistryResponseV04(engines=get_engine_registry())
