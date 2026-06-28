"""Runtime router — Stage 6 Resident v1 step endpoint.

The UI dispatches here to run the minimal mock resident loop. The request only
ever flows: router -> execution_engine (single runtime entry) -> resident_runtime
-> provider_adapters (mock providers). The UI never calls a provider directly.

This is additive; /protocol/execute and the v0.3 endpoints are unchanged.

Stage 6.1 observability: the /runtime/resident/step response carries everything
a frontend Debug Panel needs to replay one step — ``execution_trace`` (alias
``trace``): the ordered structured trace, one entry per loop phase; plus
``memory_snapshot``, ``status`` (running -> completed), ``turn_count``,
``output_text``, ``run_id`` and ``run_history``. The trace logic lives entirely
in the service layer; this router only forwards the envelope.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Request
from pydantic import BaseModel

from ..services.execution_engine import execute_load_digital_resident_from_bytes, execute_resident_step

router = APIRouter(prefix="/runtime", tags=["runtime"])


class RuntimeResidentStepRequest(BaseModel):
    workflow: Any = None
    input_text: str = ""
    resident_id: Optional[str] = None


@router.post("/resident/step")
def resident_step(req: RuntimeResidentStepRequest) -> Dict[str, Any]:
    return execute_resident_step(req.workflow, req.input_text, req.resident_id or "resident_v1")


@router.post("/resident/load-dr")
async def resident_load_dr(request: Request) -> Dict[str, Any]:
    """Load a .digital_resident JSON document and run one mock resident step."""
    raw = await request.body()
    return execute_load_digital_resident_from_bytes(raw)
