"""GET /health — Contract §7.1."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from ..models.v0_4 import PROTOCOL_VERSION_V0_4
from ..schema_version import SCHEMA_VERSION

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    status: str = "ok"
    # schema_version stays at the v0.3 runtime value for frontend compatibility;
    # protocol_version advertises the additive v0.4 protocol layer.
    schema_version: str = SCHEMA_VERSION
    protocol_version: str = PROTOCOL_VERSION_V0_4


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        schema_version=SCHEMA_VERSION,
        protocol_version=PROTOCOL_VERSION_V0_4,
    )
