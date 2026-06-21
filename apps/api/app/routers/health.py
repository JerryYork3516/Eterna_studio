"""GET /health — Contract §7.1."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from ..schema_version import SCHEMA_VERSION

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    status: str = "ok"
    schema_version: str = SCHEMA_VERSION


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", schema_version=SCHEMA_VERSION)
