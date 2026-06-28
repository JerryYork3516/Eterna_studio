"""DR v0.2 Gate schema — the schedulable persona model (Behavior Policy Spec).

==============================  IMPORTANT  ==============================
**DR = Policy Layer, NOT Runtime Layer.** Every field below is *declarative
configuration only*. Parsing this object must never execute, schedule, or
orchestrate anything. `scheduling_policy` is data an Orchestrator may parse to
plan; it is not a scheduler. No field implements behavior.
========================================================================

This Gate schema is intentionally independent from the legacy
`app/schemas/digital_resident_v0_2.py` (whose `scheduling_policy` differs). The
Gate is strict (`extra="forbid"`) so the schema validator can flag unknown
fields. Eleven declarative sections:

  identity / intent_model / scheduling_policy / execution_policy / capabilities
  / memory_policy / risk_policy / stability_constraints / capability_profile
  / security_manifest / skill_policy
"""

from __future__ import annotations

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

DR_VERSION_V0_2 = "0.2"
DR_FILE_TYPE = "digital_resident"
DR_LAYER_ROLE = "policy"


class _GateBaseModel(BaseModel):
    # Strict: unknown fields are rejected so the schema validator can flag them.
    model_config = ConfigDict(extra="forbid")


# --- Enums (declarative labels only) ---------------------------------------
class Proactivity(str, Enum):
    passive = "passive"
    reactive = "reactive"
    proactive = "proactive"


class SchedulingMode(str, Enum):
    serial = "serial"
    semi_parallel = "semi_parallel"
    adaptive = "adaptive"


class PriorityModel(str, Enum):
    fifo = "fifo"
    weighted = "weighted"
    intent_driven = "intent_driven"


class InterruptPolicy(str, Enum):
    none = "none"
    cooperative = "cooperative"
    immediate = "immediate"


class PreemptionPolicy(str, Enum):
    disabled = "disabled"
    priority_based = "priority_based"
    deadline_based = "deadline_based"


class ExecutionModeDecl(str, Enum):
    mock = "mock"


class FallbackMode(str, Enum):
    mock_fallback = "mock_fallback"
    halt = "halt"
    skip = "skip"
    none = "none"


class RiskLevelDecl(str, Enum):
    none = "none"
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class ResidentClass(str, Enum):
    industry_expertise = "industry_expertise"
    human_empathy = "human_empathy"
    # Reserved only; NOT enabled this stage (rejected by the validator).
    civilization_synthesis = "civilization_synthesis"


class SkillSource(str, Enum):
    official = "official"
    verified = "verified"


class UnsignedSkillPolicy(str, Enum):
    deny = "deny"
    allow = "allow"
    warn = "warn"


# --- 1. identity -----------------------------------------------------------
class Identity(_GateBaseModel):
    resident_id: str
    name: str = ""
    role: str = "digital_resident"
    description: Optional[str] = None
    disclosure: str = "AI-generated digital resident; synthetic persona."
    tags: List[str] = Field(default_factory=list)


# --- 2. intent_model -------------------------------------------------------
class IntentStep(_GateBaseModel):
    """One declared intent step. The ordered source for the pseudo-DAG.

    `requires_slot_type` / `requires_tool` are *resolution hints* only — a
    validator checks whether a binding exists; nothing is ever invoked.
    """

    step_id: str
    description: str = ""
    requires_slot_type: Optional[str] = None
    requires_tool: Optional[str] = None
    depends_on: List[str] = Field(default_factory=list)
    parallelizable: bool = False


class IntentModel(_GateBaseModel):
    primary_intent: str = ""
    goals: List[str] = Field(default_factory=list)
    intents: List[IntentStep] = Field(default_factory=list)
    conversation_style: Optional[str] = None
    tone: Optional[str] = None
    proactivity: Proactivity = Proactivity.reactive
    domains: List[str] = Field(default_factory=list)


# --- 3. scheduling_policy --------------------------------------------------
class SchedulingPolicy(_GateBaseModel):
    """Read ONLY by Orchestration to plan. Pure data; triggers nothing."""

    mode: SchedulingMode
    priority_model: PriorityModel
    interrupt_policy: InterruptPolicy = InterruptPolicy.none
    preemption: PreemptionPolicy = PreemptionPolicy.disabled
    max_parallel_hint: int = 1
    notes: Optional[str] = None


# --- 4. execution_policy ---------------------------------------------------
class ExecutionPolicy(_GateBaseModel):
    """How an orchestrator SHOULD treat the resident. Declaration, not execution."""

    execution_mode: ExecutionModeDecl = ExecutionModeDecl.mock
    runtime_version: str = "resident_v1_mock"
    min_kernel: str = "6.1"
    required_slot_types: List[str] = Field(default_factory=list)
    allow_tool_use: bool = False
    fallback_mode: FallbackMode = FallbackMode.mock_fallback
    determinism: str = "deterministic_mock"
    execution_constraints: List[str] = Field(default_factory=list)


# --- 5. capabilities -------------------------------------------------------
class SlotRef(_GateBaseModel):
    slot_id: str
    slot_type: str
    engine_binding: Optional[str] = None


class ToolRef(_GateBaseModel):
    tool_id: str
    slot_type: str = "tool"
    module_id: Optional[str] = None
    fallback_mode: FallbackMode = FallbackMode.mock_fallback


class Capabilities(_GateBaseModel):
    slots: List[SlotRef] = Field(default_factory=list)
    tools: List[ToolRef] = Field(default_factory=list)
    tool_preferences: List[str] = Field(default_factory=list)


# --- 6. memory_policy ------------------------------------------------------
class MemoryPolicy(_GateBaseModel):
    provider: str = "mock"
    store: str = "in_process"
    isolation: str = "per_resident"
    persistence: bool = False
    retention: Optional[str] = None
    scope: Optional[str] = None


# --- 7. risk_policy --------------------------------------------------------
class RiskPolicy(_GateBaseModel):
    disclosure_required: bool = True
    audit_required: bool = False
    human_confirm_required: bool = False
    risk_level: RiskLevelDecl = RiskLevelDecl.none
    blocked_modules: List[str] = Field(default_factory=list)
    forbidden_tool_paths: List[str] = Field(default_factory=list)
    system_locked: bool = False
    system_locked_fields: List[str] = Field(
        default_factory=lambda: ["risk_level", "disclosure_required"]
    )


# --- 8. stability_constraints ----------------------------------------------
class StabilityConstraints(_GateBaseModel):
    max_context_items: Optional[int] = None
    max_output_length: Optional[int] = None
    immutable_layers: List[str] = Field(default_factory=lambda: ["layer_1", "layer_3"])
    forbidden_transitions: List[str] = Field(default_factory=list)
    invariants: List[str] = Field(default_factory=list)


# --- 9. capability_profile (declarative; first two resident classes only) ---
class CapabilityProfile(_GateBaseModel):
    """Declared resident class blend. Pure data — no behavior, no execution.

    Only the first two classes are enabled this stage; civilization_synthesis is
    reserved (the validator rejects it).
    """

    resident_class: ResidentClass
    primary_type: str
    secondary_type: str
    primary_weight: float
    secondary_weight: float


# --- 10. security_manifest (declaration only; no real crypto) ---------------
class SecurityManifest(_GateBaseModel):
    """Signature / license / encryption declarations. NO real security system is
    implemented (no AES / license server / keychain / secure enclave)."""

    signature_required: bool = True
    license_required: bool = False
    watermark_required: bool = True
    encryption_required: bool = False
    secure_loader_required: bool = True


# --- 11. skill_policy (MCP / Skill ecosystem declaration; no real MCP) -------
class SkillPolicy(_GateBaseModel):
    """MCP / Skill declarations. NO real MCP connection, NO Skill sandbox is
    implemented. required_skills / skill_permissions are declarations only and
    never produce an execution step."""

    # Free-string list so the skill_policy validator can emit a dedicated
    # DR_SKILL_SOURCE_INVALID for values outside {official, verified}.
    allowed_skill_sources: List[str] = Field(default_factory=list)
    unsigned_skill_policy: UnsignedSkillPolicy = UnsignedSkillPolicy.deny
    sandbox_required: bool = True
    required_skills: List[str] = Field(default_factory=list)
    skill_permissions: List[str] = Field(default_factory=list)


# --- Root DR v0.2 Gate document --------------------------------------------
class DigitalResidentV02Gate(_GateBaseModel):
    """Root DR v0.2 document for the Validation Gate.

    POLICY LAYER, NOT RUNTIME LAYER. Validating this object never executes
    anything. `dr_layer="policy"` and `not_executable=True` make that explicit.
    """

    file_type: str = DR_FILE_TYPE
    dr_version: str = DR_VERSION_V0_2
    schema_version: str = "0.4.0"
    protocol_version: str = "0.4.0"
    dr_layer: str = DR_LAYER_ROLE
    not_executable: bool = True

    identity: Identity
    intent_model: IntentModel
    scheduling_policy: SchedulingPolicy
    execution_policy: ExecutionPolicy
    capabilities: Capabilities
    memory_policy: MemoryPolicy
    risk_policy: RiskPolicy
    stability_constraints: StabilityConstraints
    capability_profile: CapabilityProfile
    security_manifest: SecurityManifest
    skill_policy: SkillPolicy
