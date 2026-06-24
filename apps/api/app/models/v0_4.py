"""Protocol Contract v0.4.0 DTOs — Stage 5 protocol convergence (part 1).

Scope is protocol-only: schema tightening + Module / Slot protocol introduction.
No real AI, TTS, AR, runtime, or provider call is made here. The existing v0.3
runtime (compile / audit / preview) is untouched; v0.4 is additive and reached
only through migration + the new /…-v0.4 endpoints.

The 13-layer trunk (layer_id / layer_name / layer_order) is frozen in
CANONICAL_LAYERS and must never be reordered or renamed by this layer.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from .v0_3 import NodeInputField, NodeStatus, OutputSchemaField

SCHEMA_VERSION_V0_4 = "0.4.0"
PROTOCOL_VERSION_V0_4 = "0.4.0"


class V04BaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


# --- Frozen 13-layer trunk -------------------------------------------------
# (layer_id, layer_name, layer_order). Ids/names/order match the existing
# persona-builder trunk and MUST stay identical across versions.
CANONICAL_LAYERS: List[tuple[str, str, int]] = [
    ("layer_1", "Source Input", 1),
    ("layer_2", "Identity Core", 2),
    ("layer_3", "Legal Permission", 3),
    ("layer_4", "Safety Boundary", 4),
    ("layer_5", "World Context", 5),
    ("layer_6", "Personality", 6),
    ("layer_7", "Memory", 7),
    ("layer_8", "Knowledge", 8),
    ("layer_9", "Relationship", 9),
    ("layer_10", "Behavior", 10),
    ("layer_11", "Capability Tools", 11),
    ("layer_12", "Multimodal", 12),
    ("layer_13", "Audit Export Deploy", 13),
]

CANONICAL_LAYER_IDS = frozenset(layer_id for layer_id, _name, _order in CANONICAL_LAYERS)


# --- Shared enums ----------------------------------------------------------
class RiskLevel(str, Enum):
    none = "none"
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class ProtocolStatus(str, Enum):
    """Status allowed for Module and Slot (capability lifecycle)."""

    core = "CORE"
    ready = "READY"
    mock = "MOCK"
    planned = "PLANNED"
    later = "LATER"
    disabled = "DISABLED"


class SlotType(str, Enum):
    llm = "llm"
    tts = "tts"
    memory = "memory"
    avatar = "avatar"
    ar = "ar"
    tool = "tool"


class ExecutionMode(str, Enum):
    mock = "mock"
    sync = "sync"
    async_ = "async"


class OnError(str, Enum):
    mock = "mock"
    next_provider = "next_provider"
    fail = "fail"


# --- Layer reference (trunk) ----------------------------------------------
class LayerRefV04(V04BaseModel):
    layer_id: str
    layer_name: str
    layer_order: int
    module_ids: List[str] = Field(default_factory=list)
    node_ids: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


# --- Node Protocol ---------------------------------------------------------
class NodeV04(V04BaseModel):
    """Locked Node Protocol.

    A Node orchestrates execution. It never binds a real provider directly;
    it calls a Slot via slot_binding, and the Slot binds an engine/provider.
    """

    node_id: str
    node_type: str
    input_schema: List[NodeInputField] = Field(default_factory=list)
    output_schema: List[OutputSchemaField] = Field(default_factory=list)
    execution_status: NodeStatus = NodeStatus.mock
    slot_binding: Optional[str] = None  # which Slot this node invokes
    layer_id: Optional[str] = None
    module_id: Optional[str] = None
    # Data fidelity (not part of the locked protocol surface, kept for export):
    inputs: Dict[str, Any] = Field(default_factory=dict)
    outputs: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class EdgeV04(V04BaseModel):
    id: str
    source_node_id: str
    source_output: str = "output"
    target_node_id: str
    target_input: str = "input"
    metadata: Dict[str, Any] = Field(default_factory=dict)


# --- Module Protocol -------------------------------------------------------
class ModuleV04(V04BaseModel):
    """Capability container. A Module is NOT an execution node.

    Modules never participate in workflow execution and never write into a
    resident_instance. Every future capability (Agent / Wallet / Phone / Social
    / AR / Emergency Contact) must register here, bound to an existing layer_id.
    """

    protocol_version: Literal["0.4.0"] = PROTOCOL_VERSION_V0_4
    module_id: str
    module_type: str
    module_name: str
    module_version: str = "0.1.0"
    layer_id: str  # must be one of CANONICAL_LAYER_IDS
    inputs: Dict[str, Any] = Field(default_factory=dict)
    outputs: Dict[str, Any] = Field(default_factory=dict)
    config: Dict[str, Any] = Field(default_factory=dict)
    permissions: List[str] = Field(default_factory=list)
    risk_level: RiskLevel = RiskLevel.none
    status: ProtocolStatus = ProtocolStatus.mock
    slot_type: Optional[SlotType] = None
    # Reserved fields (declared only this stage; no complex logic yet):
    audit_required: bool = False
    human_confirm_required: bool = False
    runtime_enabled: bool = False
    is_placeholder: bool = True
    category: str = ""
    tags: List[str] = Field(default_factory=list)
    color_status: str = "gray"


# --- Slot Protocol ---------------------------------------------------------
class FallbackPolicy(V04BaseModel):
    on_error: OnError = OnError.mock
    retry: int = 0
    fallback_provider: Optional[str] = None


class SlotV04(V04BaseModel):
    """Capability interface. A Slot is not a workflow and never calls a real API.

    Module declares a slot_type; Node calls a Slot via slot_binding; Slot binds
    an engine/provider via engine_binding.
    """

    protocol_version: Literal["0.4.0"] = PROTOCOL_VERSION_V0_4
    slot_id: str
    slot_type: SlotType
    input_schema: List[NodeInputField] = Field(default_factory=list)
    output_schema: List[OutputSchemaField] = Field(default_factory=list)
    provider: Optional[str] = None
    execution_mode: ExecutionMode = ExecutionMode.mock
    fallback_policy: FallbackPolicy = Field(default_factory=FallbackPolicy)
    status: ProtocolStatus = ProtocolStatus.mock
    engine_binding: Optional[str] = None  # which Engine / Provider this Slot binds
    enabled: bool = False


# --- Workflow / Persona v0.4 core envelope ---------------------------------
class WorkflowV04(V04BaseModel):
    schema_version: Literal["0.4.0"] = SCHEMA_VERSION_V0_4
    protocol_version: Literal["0.4.0"] = PROTOCOL_VERSION_V0_4
    id: str
    type: str = "workflow"
    name: str = "Untitled Workflow"
    # 13-layer trunk preserved (NOT new functionality):
    layers: List[LayerRefV04] = Field(default_factory=list)
    nodes: List[NodeV04] = Field(default_factory=list)
    edges: List[EdgeV04] = Field(default_factory=list)
    # New v0.4 capability surface:
    modules: List[ModuleV04] = Field(default_factory=list)
    inputs: Dict[str, Any] = Field(default_factory=dict)
    outputs: Dict[str, Any] = Field(default_factory=dict)
    permissions: List[str] = Field(default_factory=list)
    risk_level: RiskLevel = RiskLevel.none
    audit_log: List[Dict[str, Any]] = Field(default_factory=list)
    extensions: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class PersonaIdentityV04(V04BaseModel):
    name: str = ""
    role: str = "digital_resident"
    description: Optional[str] = None
    disclosure: str = "AI-generated digital resident; synthetic persona."


class PersonaV04(V04BaseModel):
    schema_version: Literal["0.4.0"] = SCHEMA_VERSION_V0_4
    protocol_version: Literal["0.4.0"] = PROTOCOL_VERSION_V0_4
    id: str
    type: str = "persona"
    identity: PersonaIdentityV04 = Field(default_factory=PersonaIdentityV04)
    # New v0.4 capability surface:
    modules: List[ModuleV04] = Field(default_factory=list)
    inputs: Dict[str, Any] = Field(default_factory=dict)
    outputs: Dict[str, Any] = Field(default_factory=dict)
    permissions: List[str] = Field(default_factory=list)
    risk_level: RiskLevel = RiskLevel.none
    audit_log: List[Dict[str, Any]] = Field(default_factory=list)
    extensions: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)


# --- Catalog + validation responses ---------------------------------------
class ModuleCatalogResponseV04(V04BaseModel):
    protocol_version: Literal["0.4.0"] = PROTOCOL_VERSION_V0_4
    layers: List[LayerRefV04] = Field(default_factory=list)
    modules: List[ModuleV04] = Field(default_factory=list)


class SlotCatalogResponseV04(V04BaseModel):
    protocol_version: Literal["0.4.0"] = PROTOCOL_VERSION_V0_4
    slots: List[SlotV04] = Field(default_factory=list)


class ProtocolValidationFinding(V04BaseModel):
    status: Literal["PASS", "WARNING", "FAIL"]
    code: str
    message: str
    path: str


class WorkflowValidationResponseV04(V04BaseModel):
    schema_version: Literal["0.4.0"] = SCHEMA_VERSION_V0_4
    protocol_version: Literal["0.4.0"] = PROTOCOL_VERSION_V0_4
    valid: bool
    findings: List[ProtocolValidationFinding] = Field(default_factory=list)


class MigrationResponseV04(V04BaseModel):
    schema_version: Literal["0.4.0"] = SCHEMA_VERSION_V0_4
    protocol_version: Literal["0.4.0"] = PROTOCOL_VERSION_V0_4
    migrated_from: str
    workflow: WorkflowV04
