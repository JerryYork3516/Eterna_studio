"""DR router — Stage 6.2 DR Compiler v0.1 endpoints.

POST /dr/compile  : Canvas (workflow + nodes + edges) -> downloadable
                    .digital_resident file (NOT a bare JSON response).
POST /dr/load     : mock-load a DR document the way the Stage 6.1 runtime would
                    read it (read-only, no execution).

The compile logic lives entirely in the service layer (dr_compiler). This router
only forwards canvas data and serializes the result as a file attachment. It
never executes anything and never touches the Runtime Kernel.
"""

from __future__ import annotations

import json
from typing import Any, Dict, Optional

from fastapi import APIRouter
from fastapi.responses import Response
from pydantic import BaseModel

from ..services.dr_compiler import compile_dr, dr_filename, mock_load_dr

router = APIRouter(prefix="/dr", tags=["dr"])

# Custom media type so the response is a downloadable file, never a bare JSON body.
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
def dr_compile(req: DRCompileRequest) -> Response:
    """Compile the canvas into a downloadable .digital_resident file."""
    dr = compile_dr(_build_canvas(req), resident_name=req.resident_name)
    filename = dr_filename(dr)
    body = json.dumps(dr, ensure_ascii=False, indent=2)
    return Response(
        content=body,
        media_type=DR_MEDIA_TYPE,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-DR-Filename": filename,
            "X-DR-Audit-Valid": str(dr["audit"]["valid"]).lower(),
            "X-DR-Version": dr["dr_version"],
        },
    )


@router.post("/load")
def dr_load(req: DRLoadRequest) -> Dict[str, Any]:
    """Mock-load a DR document (read-only; proves runtime can consume it)."""
    return mock_load_dr(req.dr)
