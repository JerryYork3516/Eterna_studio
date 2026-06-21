"""Mock Run results — Contract §4."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Literal

from pydantic import BaseModel, Field

from ..schema_version import SCHEMA_VERSION
from ..util import now
from .enums import RunStatus


class RunLog(BaseModel):
    ts: datetime = Field(default_factory=now)
    level: Literal["info", "warn", "error"] = "info"
    message: str


class Artifact(BaseModel):
    artifact_id: str
    node_id: str
    kind: str
    name: str
    preview: Dict[str, Any] = Field(default_factory=dict)


class NodeRunResult(BaseModel):
    node_id: str
    status: RunStatus  # success | warning | skipped | error
    output: Dict[str, Any] = Field(default_factory=dict)
    logs: List[RunLog] = Field(default_factory=list)
    duration_ms: int = 0


class RunResult(BaseModel):
    schema_version: str = SCHEMA_VERSION
    workflow_id: str
    status: RunStatus
    order: List[str] = Field(default_factory=list)  # topological order
    node_results: List[NodeRunResult] = Field(default_factory=list)
    artifacts: List[Artifact] = Field(default_factory=list)
    started_at: datetime = Field(default_factory=now)
    finished_at: datetime = Field(default_factory=now)
