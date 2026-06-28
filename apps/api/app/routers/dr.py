"""DR router — Stage 6.3.3 split: Compile (validate, no download) vs Export.

POST /dr/compile : Canvas -> compile + validate_dr_v0_2 -> JSON result (NO file
                   download). Carries valid / errors / warnings / module_audit /
                   layer_audit / compile_audit / orchestration_compatibility /
                   pseudo_dag / dr_version / compiled_dr / dr_payload / metadata.
POST /dr/export  : Download the already-validated compiled DR as a
                   .digital_resident file. Rejected (422) when not valid.
POST /dr/load    : mock-load a DR document (read-only, no execution).

The compile/validate logic lives entirely in the service layer (dr_compiler +
the DR v0.2 Validation Gate). This router only forwards canvas data and shapes
the response. It never executes anything and never touches the Runtime Kernel.
"""

from __future__ import annotations

import json
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

from ..services.dr_compiler import compile_dr_result, mock_load_dr

router = APIRouter(prefix="/dr", tags=["dr"])

# Custom media type so the export response is a downloadable file, never JSON.
DR_MEDIA_TYPE = "application/x-digital-resident"


class DRCompileRequest(BaseModel):
    # Canvas data. `workflow` may already carry nodes/edges/modules; the explicit
    # nodes/edges/modules/slots fields override when provided.
    workflow: Any = None
    nodes: Optional[list] = None
    edges: Optional[list] = None
    modules: Optional[list] = None
    slots: Optional[list] = None
    resident_name: Optional[str] = None


class DRLoadRequest(BaseModel):
    dr: Dict[str, Any]


def _build_canvas(req: DRCompileRequest) -> Dict[str, Any]:
    canvas: Dict[str, Any] = {"workflow": req.workflow}
    if req.nodes is not None:
        canvas["nodes"] = req.nodes
    if req.edges is not None:
        canvas["edges"] = req.edges
    if req.modules is not None:
        canvas["modules"] = req.modules
    if req.slots is not None:
        canvas["slots"] = req.slots
    return canvas


@router.post("/compile")
def dr_compile(req: DRCompileRequest) -> Dict[str, Any]:
    """Compile + validate the canvas and return JSON. Does NOT download a file."""
    return compile_dr_result(_build_canvas(req), resident_name=req.resident_name)


@router.post("/export")
def dr_export(req: DRCompileRequest) -> Response:
    """Download the validated compiled DR. Rejected (422) when the DR is invalid."""
    result = compile_dr_result(_build_canvas(req), resident_name=req.resident_name)
    if not result["valid"] or result.get("compiled_dr") is None:
        raise HTTPException(
            status_code=422,
            detail={"error": "DR did not pass validation; export is not allowed", "errors": result["errors"]},
        )
    dr = result["compiled_dr"]
    filename = result["filename"]
    body = json.dumps(dr, ensure_ascii=False, indent=2)
    return Response(
        content=body,
        media_type=DR_MEDIA_TYPE,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-DR-Filename": filename,
            "X-DR-Audit-Valid": "true",
            "X-DR-Version": str(dr.get("dr_version", "0.1")),
        },
    )


@router.post("/load")
def dr_load(req: DRLoadRequest) -> Dict[str, Any]:
    """Mock-load a DR document (read-only; proves runtime can consume it)."""
    return mock_load_dr(req.dr)
