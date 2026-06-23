"""Legacy workflow shape kept for adapter compatibility.

Runtime source of truth is WorkflowV03 in app.models.v0_3. Do not mount this
model as a main API schema; normalize legacy payloads through services.workflow_v0_3.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

from ..schema_version import SCHEMA_VERSION
from ..util import gen_id, now
from .enums import LockLevel, NodeCategory, NodeType
from .review import ValidationReview


class Port(BaseModel):
    port_id: str
    name: str
    direction: Literal["in", "out"]


class Ports(BaseModel):
    inputs: List[Port] = Field(default_factory=list)
    outputs: List[Port] = Field(default_factory=list)


class Position(BaseModel):
    x: float = 0.0
    y: float = 0.0


class Viewport(BaseModel):
    x: float = 0.0
    y: float = 0.0
    zoom: float = 1.0


class WorkflowMetadata(BaseModel):
    description: Optional[str] = None
    author: Optional[str] = None
    tags: Optional[List[str]] = None
    ui_language: Optional[str] = None  # "zh" | "en" — UI language only


class WorkflowNode(BaseModel):  # M6
    node_id: str
    type: NodeType
    category: NodeCategory
    title_key: str  # i18n key, e.g. "layer.identity_core"
    title_fallback: str  # debug / missing-translation fallback
    position: Position = Field(default_factory=Position)
    lock_level: LockLevel  # M5: single authority. Container may be `mixed`.
    locale: Optional[str] = None  # reserved; MVP disabled (always null)
    data: Dict[str, Any] = Field(default_factory=dict)  # shape varies by type (§2.5)
    ports: Ports = Field(default_factory=Ports)
    validation: Optional[ValidationReview] = None


class WorkflowEdge(BaseModel):
    edge_id: str
    source: str
    source_port: str
    target: str
    target_port: str


class Workflow(BaseModel):
    schema_version: str = SCHEMA_VERSION
    workflow_id: str = Field(default_factory=lambda: gen_id("wf"))
    name: str
    version: str = "1.0.0"
    template_type: str = "blank"
    content_locale: Optional[str] = None
    nodes: List[WorkflowNode] = Field(default_factory=list)
    edges: List[WorkflowEdge] = Field(default_factory=list)
    viewport: Optional[Viewport] = None
    metadata: WorkflowMetadata = Field(default_factory=WorkflowMetadata)
    created_at: datetime = Field(default_factory=now)
    updated_at: datetime = Field(default_factory=now)
