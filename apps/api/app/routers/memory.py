"""Memory router — Stage 6.7 Memory Module v1.

Read-only viewer + clear for a resident's local memory. The UI dispatches here;
the backend resolves Engine -> Provider Registry -> memory provider (the same
path the runtime loop uses). The UI never touches the store directly.

This is additive and does not change the runtime loop or the 6.6 LLM path.
"""

from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Query
from pydantic import BaseModel

from ..services.memory_store import DEFAULT_MEMORY_TYPE, DEFAULT_NAMESPACE
from ..services.provider_adapters import route_provider_for_engine

router = APIRouter(prefix="/runtime/memory", tags=["runtime-memory"])


class MemoryClearRequest(BaseModel):
    resident_id: str
    namespace: str = DEFAULT_NAMESPACE
    memory_type: str = DEFAULT_MEMORY_TYPE


@router.get("/view")
def memory_view(
    resident_id: str = Query("resident_v1"),
    namespace: str = Query(DEFAULT_NAMESPACE),
    memory_type: str = Query(DEFAULT_MEMORY_TYPE),
    limit: int = Query(20, ge=0),
) -> Dict[str, Any]:
    """memory.view — list a resident's memory records (with metadata)."""
    payload: Dict[str, Any] = {
        "op": "view",
        "resident_id": resident_id,
        "namespace": namespace,
        "memory_type": memory_type,
        "limit": limit,
    }
    return route_provider_for_engine("memory_mock", payload)


@router.post("/clear")
def memory_clear(req: MemoryClearRequest) -> Dict[str, Any]:
    """memory.clear — delete a resident's memory (optionally scoped to ns/type)."""
    payload: Dict[str, Any] = {
        "op": "clear",
        "resident_id": req.resident_id,
        "namespace": req.namespace,
        "memory_type": req.memory_type,
    }
    return route_provider_for_engine("memory_mock", payload)
