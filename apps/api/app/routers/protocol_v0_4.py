"""Protocol v0.4 router — additive endpoints for Stage 5 (part 1).

Exposes the frozen 13-layer trunk, Module catalog, Slot catalog, the v0.4
schemas, plus v0.3 → v0.4 migration and v0.4 node/module validation. None of
these touch the existing v0.3 compile / audit / preview path.
"""

from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter
from pydantic import BaseModel

from ..models.v0_4 import (
    CANONICAL_LAYERS,
    LayerRefV04,
    ModuleCatalogResponseV04,
    ModuleV04,
    PersonaV04,
    SlotCatalogResponseV04,
    SlotV04,
    WorkflowV04,
    WorkflowValidationResponseV04,
)
from ..registry.module_catalog import get_module_catalog, validate_module_catalog
from ..registry.slot_catalog import get_slot_catalog, validate_slot_catalog
from ..services.migration_v0_4 import migrate_response, validate_workflow_v0_4

router = APIRouter(prefix="/protocol", tags=["protocol-v0.4"])


def _canonical_layer_refs() -> List[LayerRefV04]:
    return [LayerRefV04(layer_id=lid, layer_name=name, layer_order=order) for lid, name, order in CANONICAL_LAYERS]


@router.get("/layers", response_model=List[LayerRefV04])
def layers() -> List[LayerRefV04]:
    return _canonical_layer_refs()


@router.get("/modules/catalog", response_model=ModuleCatalogResponseV04)
def module_catalog() -> ModuleCatalogResponseV04:
    return ModuleCatalogResponseV04(layers=_canonical_layer_refs(), modules=get_module_catalog())


@router.get("/slots/catalog", response_model=SlotCatalogResponseV04)
def slot_catalog() -> SlotCatalogResponseV04:
    return SlotCatalogResponseV04(slots=get_slot_catalog())


class CatalogHealthResponse(BaseModel):
    module_errors: List[str]
    slot_errors: List[str]
    ok: bool


@router.get("/catalog/health", response_model=CatalogHealthResponse)
def catalog_health() -> CatalogHealthResponse:
    module_errors = validate_module_catalog(get_module_catalog())
    slot_errors = validate_slot_catalog(get_slot_catalog())
    return CatalogHealthResponse(module_errors=module_errors, slot_errors=slot_errors, ok=not (module_errors or slot_errors))


class WorkflowPayload(BaseModel):
    workflow: Any


@router.post("/workflow/migrate")
def migrate(req: WorkflowPayload) -> Dict[str, Any]:
    return migrate_response(req.workflow).model_dump(mode="json")


@router.post("/workflow/validate-v0.4", response_model=WorkflowValidationResponseV04)
def validate_v0_4(req: WorkflowPayload) -> WorkflowValidationResponseV04:
    return validate_workflow_v0_4(req.workflow)


@router.get("/schema/workflow-v0.4")
def workflow_schema_v0_4() -> Dict[str, Any]:
    return WorkflowV04.model_json_schema()


@router.get("/schema/persona-v0.4")
def persona_schema_v0_4() -> Dict[str, Any]:
    return PersonaV04.model_json_schema()


@router.get("/schema/module-v0.4")
def module_schema_v0_4() -> Dict[str, Any]:
    return ModuleV04.model_json_schema()


@router.get("/schema/slot-v0.4")
def slot_schema_v0_4() -> Dict[str, Any]:
    return SlotV04.model_json_schema()
