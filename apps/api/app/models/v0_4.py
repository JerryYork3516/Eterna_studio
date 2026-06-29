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
    ("layer_1", "Identity Core", 1),
    ("layer_2", "Personality", 2),
    ("layer_3", "Safety Boundary", 3),
    ("layer_4", "Legal Permission", 4),
    ("layer_5", "Memory", 5),
    ("layer_6", "Knowledge", 6),
    ("layer_7", "World / Context", 7),
    ("layer_8", "Behavior", 8),
    ("layer_9", "Capability / Tools", 9),
    ("layer_10", "Multimodal", 10),
    ("layer_11", "Relationship", 11),
    ("layer_12", "Meta / Self-Reflection", 12),
    ("layer_13", "Export / Deployment", 13),
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
    """Legacy status preserved for v0.4 compatibility."""

    core = "CORE"
    ready = "READY"
    mock = "MOCK"
    planned = "PLANNED"
    later = "LATER"
    disabled = "DISABLED"
    unplanned = "UNPLANNED"
    error = "ERROR"


class ContractStatus(str, Enum):
    unplanned = "UNPLANNED"
    mock = "MOCK"
    ready = "READY"
    error = "ERROR"


class NodeRole(str, Enum):
    input = "input"
    config = "config"
    slot = "slot"
    output = "output"
    debug = "debug"


class SlotRole(str, Enum):
    input = "input"
    config = "config"
    slot = "slot"
    output = "output"
    debug = "debug"


class SlotType(str, Enum):
    llm = "llm"
    tts = "tts"
    memory = "memory"
    avatar = "avatar"
    speech = "speech"
    screen = "screen"
    ar = "ar"
    tool = "tool"
    lattice = "lattice"


class ExecutionMode(str, Enum):
    mock = "mock"
    sync = "sync"
    async_ = "async"


class OnError(str, Enum):
    mock = "mock"
    next_provider = "next_provider"
    fail = "fail"


class LatticeEmotion(str, Enum):
    calm = "calm"
    focused = "focused"
    thinking = "thinking"
    speaking = "speaking"
    neutral = "neutral"


class LatticeMotion(str, Enum):
    idle_breathing = "idle_breathing"
    thinking_pulse = "thinking_pulse"
    speaking_motion = "speaking_motion"
    focused_stillness = "focused_stillness"
    idle = "idle"
    thinking = "thinking"


class LatticeVoiceState(str, Enum):
    idle = "idle"
    speaking = "speaking"
    listening = "listening"
    muted = "muted"


class LatticeParticleStyle(str, Enum):
    sparse = "sparse"
    medium = "medium"
    dense = "dense"


class LatticeConfigV04(V04BaseModel):
    resident_id: str
    grid_size: Dict[str, int] = Field(default_factory=lambda: {"x": 8, "y": 8, "z": 4})
    multi_resident_enabled: bool = False
    focus_mode: str = "single"
    color_palette: List[str] = Field(default_factory=list)
    reserved: Dict[str, Any] = Field(default_factory=dict)


class LatticeStateV04(V04BaseModel):
    resident_id: str
    emotion: LatticeEmotion = LatticeEmotion.neutral
    energy: float = 0.5
    attention: str = "self"
    motion: LatticeMotion = LatticeMotion.idle_breathing
    voice_state: LatticeVoiceState = LatticeVoiceState.idle
    particle_density: float = 0.5
    color_palette: List[str] = Field(default_factory=list)
    focus_target: str = "none"
    stage: str = "calm"
    reserved: Dict[str, Any] = Field(default_factory=dict)


class MultiResidentLatticeStateV04(V04BaseModel):
    resident_ids: List[str] = Field(default_factory=list)
    states: List[LatticeStateV04] = Field(default_factory=list)
    reserved: Dict[str, Any] = Field(default_factory=dict)


# --- Layer reference (trunk) ----------------------------------------------
class LayerRefV04(V04BaseModel):
    layer_id: str
    layer_name: str
    layer_order: int
    module_ids: List[str] = Field(default_factory=list)
    node_ids: List[str] = Field(default_factory=list)
    layer_context: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)


# --- Node Protocol ---------------------------------------------------------
class NodeV04(V04BaseModel):
    """Locked Node Protocol.

    A Node orchestrates execution. It never binds a real provider directly;
    it calls a Slot via slot_binding, and the Slot binds an engine/provider.
    """

    node_id: str
    node_type: str
    node_role: Optional[NodeRole] = None
    params: Dict[str, Any] = Field(default_factory=dict)
    input_schema: List[NodeInputField] = Field(default_factory=list)
    output_schema: List[OutputSchemaField] = Field(default_factory=list)
    execution_status: NodeStatus = NodeStatus.mock
    slot_binding: Optional[str] = None  # which Slot this node invokes
    context_requirements: List[str] = Field(default_factory=list)
    runtime_mapping: Dict[str, Any] = Field(default_factory=dict)
    dr_mapping: Dict[str, Any] = Field(default_factory=dict)
    ui_color: str = ""
    collapsed_sections: List[str] = Field(default_factory=list)
    i18n_keys: Dict[str, str] = Field(default_factory=dict)
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
    module_graph: Dict[str, Any] = Field(default_factory=dict)
    input_schema: List[NodeInputField] = Field(default_factory=list)
    output_schema: List[OutputSchemaField] = Field(default_factory=list)
    slot_bindings: List[Dict[str, Any]] = Field(default_factory=list)
    context_bindings: List[Dict[str, Any]] = Field(default_factory=list)
    runtime_mapping: Dict[str, Any] = Field(default_factory=dict)
    dr_mapping: Dict[str, Any] = Field(default_factory=dict)
    ui_config: Dict[str, Any] = Field(default_factory=dict)
    i18n_keys: Dict[str, str] = Field(default_factory=dict)
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


class LatticeModuleConfigV04(V04BaseModel):
    lattice_config: LatticeConfigV04 = Field(default_factory=lambda: LatticeConfigV04(resident_id="resident_v1"))
    lattice_state_schema: LatticeStateV04 = Field(default_factory=lambda: LatticeStateV04(resident_id="resident_v1"))
    multi_resident_lattice_state: MultiResidentLatticeStateV04 = Field(default_factory=MultiResidentLatticeStateV04)


# --- Slot Protocol ---------------------------------------------------------
class FallbackPolicy(V04BaseModel):
    on_error: OnError = OnError.mock
    retry: int = 0
    fallback_provider: Optional[str] = None


class PermissionPolicy(V04BaseModel):
    allowed: bool = True
    human_confirm_required: bool = False
    scopes: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TraceSchema(V04BaseModel):
    fields: List[Dict[str, Any]] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SlotV04(V04BaseModel):
    """Capability interface. A Slot is not a workflow and never calls a real API.

    Module declares a slot_type; Node calls a Slot via slot_binding; Slot binds
    an engine/provider via engine_binding.
    """

    protocol_version: Literal["0.4.0"] = PROTOCOL_VERSION_V0_4
    slot_id: str
    slot_type: SlotType
    slot_role: Optional[SlotRole] = None
    input_schema: List[NodeInputField] = Field(default_factory=list)
    output_schema: List[OutputSchemaField] = Field(default_factory=list)
    provider: Optional[str] = None
    provider_requirement: Dict[str, Any] = Field(default_factory=dict)
    runtime_capability: Dict[str, Any] = Field(default_factory=dict)
    execution_mode: ExecutionMode = ExecutionMode.mock
    fallback_policy: FallbackPolicy = Field(default_factory=FallbackPolicy)
    permission_policy: PermissionPolicy = Field(default_factory=PermissionPolicy)
    trace_schema: TraceSchema = Field(default_factory=TraceSchema)
    status: ContractStatus = ContractStatus.mock
    engine_binding: Optional[str] = None  # which Engine / Provider this Slot binds
    mock_supported: bool = True
    i18n_keys: Dict[str, str] = Field(default_factory=dict)
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
    layer_contexts: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
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


# --- Lattice State (reserved, declarative only) ----------------------------
class LatticeConfigV04(V04BaseModel):
    resident_id: str
    point_grid: Dict[str, Any] = Field(default_factory=dict)
    emotion_model: Dict[str, Any] = Field(default_factory=dict)
    energy_model: Dict[str, Any] = Field(default_factory=dict)
    motion_model: Dict[str, Any] = Field(default_factory=dict)
    attention_model: Dict[str, Any] = Field(default_factory=dict)
    voice_model: Dict[str, Any] = Field(default_factory=dict)
    particle_model: Dict[str, Any] = Field(default_factory=dict)
    multi_resident: Dict[str, Any] = Field(default_factory=dict)


class LatticeModuleConfigV04(V04BaseModel):
    lattice_config: LatticeConfigV04 = Field(default_factory=lambda: LatticeConfigV04(resident_id="resident_v1"))
    lattice_state_schema: LatticeStateSchemaV04 = Field(default_factory=lambda: LatticeStateSchemaV04(resident_id="resident_v1"))
    multi_resident_lattice_state: MultiResidentLatticeStateV04 = Field(default_factory=MultiResidentLatticeStateV04)


class LatticeStateSchemaV04(V04BaseModel):
    resident_id: str
    emotion: str = "calm"
    energy: float = 0.5
    attention: str = "self"
    motion: str = "idle_breathing"
    voice_state: str = "idle"
    particle_density: float = 0.4
    color_palette: List[str] = Field(default_factory=list)
    focus_target: str = "self"


class MultiResidentLatticeStateV04(V04BaseModel):
    resident_ids: List[str] = Field(default_factory=list)
    lattice_states: List[LatticeStateSchemaV04] = Field(default_factory=list)
    coordination_mode: str = "reserved"
    metadata: Dict[str, Any] = Field(default_factory=dict)


# --- Engine Registry -------------------------------------------------------
class EngineType(str, Enum):
    llm = "llm"
    memory = "memory"
    tool = "tool"
    tts = "tts"
    avatar = "avatar"
    speech = "speech"
    screen = "screen"


class EngineV04(V04BaseModel):
    """Real capability adapter layer (Stage 5: mock provider only).

    Binding chain: Node.slot_binding -> Slot.engine_binding -> Engine -> Provider.
    No real AI/provider, no API key read this stage.
    """

    protocol_version: Literal["0.4.0"] = PROTOCOL_VERSION_V0_4
    engine_id: str
    engine_type: EngineType = EngineType.llm
    engine_name: str
    supported_slot_types: List[SlotType] = Field(default_factory=list)
    providers: List[str] = Field(default_factory=lambda: ["provider_llm_mock"])
    status: ProtocolStatus = ProtocolStatus.mock


# --- Permission + risk decision -------------------------------------------
class PermissionResult(str, Enum):
    allowed = "allowed"
    denied = "denied"
    requires_human_confirm = "requires_human_confirm"


class Decision(str, Enum):
    allowed = "allowed"
    blocked = "blocked"


class PermissionDecisionV04(V04BaseModel):
    risk_level: RiskLevel
    permission_result: PermissionResult
    blocked_or_allowed: Decision
    audit_required: bool
    decision_reason: str


# --- Audit log -------------------------------------------------------------
class AuditLogEntryV04(V04BaseModel):
    """Factual record of a gated action. Not used by any UI display logic."""

    action_id: str
    module_id: Optional[str] = None
    actor: str = "system"
    input: Dict[str, Any] = Field(default_factory=dict)
    output: Dict[str, Any] = Field(default_factory=dict)
    decision_reason: str = ""
    risk_level: RiskLevel = RiskLevel.none
    permission_result: PermissionResult = PermissionResult.allowed
    blocked_or_allowed: Decision = Decision.allowed
    timestamp: str
    human_confirmed_by: Optional[str] = None


# --- Catalog + validation responses ---------------------------------------
class EngineRegistryResponseV04(V04BaseModel):
    schema_version: Literal["0.4.0"] = SCHEMA_VERSION_V0_4
    protocol_version: Literal["0.4.0"] = PROTOCOL_VERSION_V0_4
    engines: List[EngineV04] = Field(default_factory=list)


class ModuleCatalogResponseV04(V04BaseModel):
    schema_version: Literal["0.4.0"] = SCHEMA_VERSION_V0_4
    protocol_version: Literal["0.4.0"] = PROTOCOL_VERSION_V0_4
    layers: List[LayerRefV04] = Field(default_factory=list)
    modules: List[ModuleV04] = Field(default_factory=list)


class SlotCatalogResponseV04(V04BaseModel):
    schema_version: Literal["0.4.0"] = SCHEMA_VERSION_V0_4
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


# --- Execution control plane (v0.4 orchestration over v0.3 runtime) --------
# The control plane never executes anything itself. It resolves the
# Node -> Slot -> Engine chain, computes permission/risk decisions, translates
# the v0.4 workflow to a v0.3 workflow, and forwards to the v0.3 runtime through
# the single Execution Adapter. v0.3 remains the only execution core.
class V4ResolvedBinding(V04BaseModel):
    node_id: str
    node_type: str
    slot_id: Optional[str] = None
    slot_type: Optional[SlotType] = None
    engine_id: Optional[str] = None
    engine_provider: Optional[str] = None
    execution_mode: Optional[ExecutionMode] = None
    module_id: Optional[str] = None
    layer_context: Dict[str, Any] = Field(default_factory=dict)
    resolved: bool = False
    note: str = ""


class V4ExecutionPlan(V04BaseModel):
    schema_version: Literal["0.4.0"] = SCHEMA_VERSION_V0_4
    protocol_version: Literal["0.4.0"] = PROTOCOL_VERSION_V0_4
    workflow_id: str
    action: str
    target_runtime: Literal["v0.3"] = "v0.3"
    resolved_bindings: List[V4ResolvedBinding] = Field(default_factory=list)
    permission_decisions: List[PermissionDecisionV04] = Field(default_factory=list)
    audit_log: List[AuditLogEntryV04] = Field(default_factory=list)
    blocked: bool = False
    v0_3_workflow: Dict[str, Any] = Field(default_factory=dict)
    layer_contexts: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    notes: List[str] = Field(default_factory=list)


class V4ExecutionRequest(V04BaseModel):
    workflow: Any = None
    action: Literal["validate", "audit", "mock_run", "compile"] = "mock_run"


class V4ExecutionResponse(V04BaseModel):
    schema_version: Literal["0.4.0"] = SCHEMA_VERSION_V0_4
    protocol_version: Literal["0.4.0"] = PROTOCOL_VERSION_V0_4
    runtime: Literal["v0.3"] = "v0.3"
    executed: bool
    plan: V4ExecutionPlan
    result: Dict[str, Any] = Field(default_factory=dict)
