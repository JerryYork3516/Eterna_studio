"""Digital Resident (DR) v0.2 schema — the Behavior Policy Spec.

================================  IMPORTANT  ================================
DR = POLICY LAYER, *NOT* RUNTIME LAYER.

A Digital Resident document is a *declarative* description of a schedulable
persona. Every field below is configuration data only. There is NO scheduler,
NO orchestration, NO execution, NO DAG / concurrency / retry logic in this file
or anywhere a DR is parsed. A DR is the standardized *input* that a future
Orchestration v0.1 will READ — reading a DR must never trigger behavior.

  * DR declares intent / scheduling preference / capability — it does not act.
  * `scheduling_policy` is data for an Orchestrator to parse. It is never a
    scheduler and never starts a job.
  * `execution_policy` declares how an orchestrator *should treat* the resident
    (mode, hints, preferences). It contains no execution code.
  * The Stage 6 Runtime Kernel (execution_engine / trace / memory / state) is
    unchanged and unaware of this module.
============================================================================

v0.2 is a strict superset of v0.1: the v0.1 blueprint fields (resident / layers
/ modules / slots / runtime_requirements / memory_config / safety_policy /
audit / compile_info) are preserved as optional compatibility fields so old
.digital_resident data upgrades smoothly without conflict or loss.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

DR_VERSION_V0_2 = "0.2"
DR_FILE_TYPE = "digital_resident"
# Explicit, machine-readable marker: this document lives in the policy layer.
DR_LAYER_ROLE = "policy"


class _DRBaseModel(BaseModel):
    # extra="allow": preserve unknown / legacy v0.1 fields so upgrades never lose
    # data. Declarative containers only — no methods that act.
    model_config = ConfigDict(extra="allow")


# --- Declarative option enums (data labels only) ---------------------------
class Proactivity(str, Enum):
    """Declared disposition only — NOT a runtime behavior switch."""

    passive = "passive"
    reactive = "reactive"
    proactive = "proactive"


class Priority(str, Enum):
    low = "low"
    normal = "normal"
    high = "high"


class TriggerMode(str, Enum):
    """Declared trigger surfaces an Orchestrator MAY parse. Declaration only."""

    on_message = "on_message"
    on_event = "on_event"
    on_schedule = "on_schedule"


class CadenceType(str, Enum):
    """Schedule descriptor type. Pure data — describes, never schedules."""

    none = "none"
    interval = "interval"
    cron = "cron"


class ExecutionModeDecl(str, Enum):
    """Declared execution mode the orchestrator should assume. Mock-only stage."""

    mock = "mock"


class OnErrorPreference(str, Enum):
    """Declared error disposition preference. NOT a retry/recovery mechanism."""

    mock_fallback = "mock_fallback"
    halt = "halt"
    skip = "skip"


class RiskLevelDecl(str, Enum):
    none = "none"
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


# --- 1. identity -----------------------------------------------------------
class Identity(_DRBaseModel):
    """Who the resident is. Declarative identity card."""

    resident_id: str
    name: str = ""
    role: str = "digital_resident"
    description: Optional[str] = None
    disclosure: str = "AI-generated digital resident; synthetic persona."
    persona_summary: Optional[str] = None
    tags: List[str] = Field(default_factory=list)


# --- 2. intent_model -------------------------------------------------------
class IntentModel(_DRBaseModel):
    """What the resident is *for*. Declared goals / style — no behavior."""

    primary_intent: str = ""
    goals: List[str] = Field(default_factory=list)
    conversation_style: Optional[str] = None
    tone: Optional[str] = None
    proactivity: Proactivity = Proactivity.reactive
    domains: List[str] = Field(default_factory=list)


# --- 3. scheduling_policy --------------------------------------------------
class Cadence(_DRBaseModel):
    """Schedule *descriptor*. Data only — it describes a cadence, never runs it."""

    type: CadenceType = CadenceType.none
    value: Optional[str] = None  # e.g. "30m" for interval, a cron string for cron


class SchedulingPolicy(_DRBaseModel):
    """Read ONLY by Orchestration to plan. Pure data; triggers nothing.

    Nothing here starts a job, spawns a task, or runs on a timer. These are
    declared preferences an external Orchestrator MAY interpret later.
    """

    schedulable: bool = False
    trigger_modes: List[TriggerMode] = Field(default_factory=lambda: [TriggerMode.on_message])
    priority: Priority = Priority.normal
    concurrency_hint: int = 1  # a hint for the orchestrator; not a concurrency mechanism
    cadence: Cadence = Field(default_factory=Cadence)
    max_turns_per_session: Optional[int] = None
    cooldown_seconds: Optional[int] = None
    notes: Optional[str] = None


# --- 4. execution_policy ---------------------------------------------------
class ExecutionPolicy(_DRBaseModel):
    """How an orchestrator SHOULD treat the resident. Declaration, not execution.

    No retry counts, no DAG, no concurrency. `on_error_preference` is a declared
    disposition string, not a recovery mechanism. The Runtime Kernel ignores it.
    """

    execution_mode: ExecutionModeDecl = ExecutionModeDecl.mock
    runtime_version: str = "resident_v1_mock"
    min_kernel: str = "6.1"
    required_slot_types: List[str] = Field(default_factory=list)
    engines: List[Dict[str, Any]] = Field(default_factory=list)
    allow_tool_use: bool = False  # declared permission, not a capability switch
    determinism: str = "deterministic_mock"
    timeout_hint_seconds: Optional[int] = None  # hint only
    on_error_preference: OnErrorPreference = OnErrorPreference.mock_fallback


# --- 5. capabilities -------------------------------------------------------
class CapabilityRef(_DRBaseModel):
    """A declared capability descriptor (mirrors a Module/Slot). Descriptor only."""

    id: str
    type: str = ""
    name: Optional[str] = None
    slot_type: Optional[str] = None
    layer_id: Optional[str] = None
    status: Optional[str] = None


class Capabilities(_DRBaseModel):
    """What the resident is declared able to use. Declarations, never invoked."""

    modules: List[Dict[str, Any]] = Field(default_factory=list)
    slots: List[Dict[str, Any]] = Field(default_factory=list)
    declared_capabilities: List[CapabilityRef] = Field(default_factory=list)


# --- 6. memory_policy ------------------------------------------------------
class MemoryPolicy(_DRBaseModel):
    """Declared memory configuration. No memory engine, no I/O."""

    provider: str = "mock"
    store: str = "in_process"
    isolation: str = "per_resident"
    persistence: bool = False
    retention: Optional[str] = None  # declared retention descriptor, e.g. "session"
    scope: Optional[str] = None


# --- 7. risk_policy --------------------------------------------------------
class RiskPolicy(_DRBaseModel):
    """Declared safety / governance posture. Declarations only."""

    disclosure_required: bool = True
    audit_required: bool = False
    human_confirm_required: bool = False
    risk_level: RiskLevelDecl = RiskLevelDecl.none
    blocked_modules: List[str] = Field(default_factory=list)
    safety_boundaries: List[str] = Field(default_factory=list)


# --- 8. stability_constraints ----------------------------------------------
class StabilityConstraints(_DRBaseModel):
    """Invariants an orchestrator MUST respect. Declared limits — not enforced here."""

    max_context_items: Optional[int] = None
    max_output_length: Optional[int] = None
    immutable_layers: List[str] = Field(default_factory=lambda: ["layer_1", "layer_3"])
    forbidden_transitions: List[str] = Field(default_factory=list)
    invariants: List[str] = Field(default_factory=list)


# --- DR v0.2 root document -------------------------------------------------
class DigitalResidentV02(_DRBaseModel):
    """Root DR v0.2 document — the Behavior Policy Spec.

    POLICY LAYER, NOT RUNTIME LAYER. Parsing this object must never execute
    anything. `dr_layer="policy"` and `not_executable=True` make that explicit
    and machine-checkable.
    """

    # --- DR metadata (frozen markers) ---
    file_type: str = DR_FILE_TYPE
    dr_version: str = DR_VERSION_V0_2
    schema_version: str = "0.4.0"
    protocol_version: str = "0.4.0"
    dr_layer: str = DR_LAYER_ROLE  # always "policy"
    not_executable: bool = True  # DR never runs; it is read by Orchestration

    # --- 8 required v0.2 policy sections ---
    identity: Identity
    intent_model: IntentModel = Field(default_factory=IntentModel)
    scheduling_policy: SchedulingPolicy = Field(default_factory=SchedulingPolicy)
    execution_policy: ExecutionPolicy = Field(default_factory=ExecutionPolicy)
    capabilities: Capabilities = Field(default_factory=Capabilities)
    memory_policy: MemoryPolicy = Field(default_factory=MemoryPolicy)
    risk_policy: RiskPolicy = Field(default_factory=RiskPolicy)
    stability_constraints: StabilityConstraints = Field(default_factory=StabilityConstraints)

    # --- v0.1 backward-compatibility fields (optional; preserved on upgrade) ---
    # Old .digital_resident blueprints carry these; v0.2 keeps them so no data is
    # lost and old readers still find what they expect. Declarative data only.
    resident: Optional[Dict[str, Any]] = None
    layers: Optional[List[Dict[str, Any]]] = None
    modules: Optional[List[Dict[str, Any]]] = None
    slots: Optional[List[Dict[str, Any]]] = None
    runtime_requirements: Optional[Dict[str, Any]] = None
    memory_config: Optional[Dict[str, Any]] = None
    safety_policy: Optional[Dict[str, Any]] = None
    audit: Optional[Dict[str, Any]] = None
    compile_info: Optional[Dict[str, Any]] = None


# ---------------------------------------------------------------------------
# v0.1 -> v0.2 upgrade: a PURE, declarative field mapping. This transforms data
# shapes only. It runs no behavior, schedules nothing, executes nothing.
# ---------------------------------------------------------------------------
def upgrade_v0_1_to_v0_2(dr_v01: Dict[str, Any]) -> Dict[str, Any]:
    """Map a v0.1 DR dict onto the v0.2 policy structure (data transform only).

    Backward compatible: the original v0.1 blueprint fields are kept verbatim
    under their compatibility keys, and the new v0.2 policy sections are derived
    from them. No field is renamed-away or dropped, so old data is never broken.
    """
    dr_v01 = dr_v01 or {}
    resident = dict(dr_v01.get("resident") or {})
    runtime_req = dict(dr_v01.get("runtime_requirements") or {})
    memory_config = dict(dr_v01.get("memory_config") or {})
    safety_policy = dict(dr_v01.get("safety_policy") or {})
    modules = list(dr_v01.get("modules") or [])
    slots = list(dr_v01.get("slots") or [])

    identity = {
        "resident_id": resident.get("resident_id") or "digital_resident",
        "name": resident.get("name", ""),
        "role": resident.get("role", "digital_resident"),
        "description": resident.get("description"),
        "disclosure": resident.get("disclosure", "AI-generated digital resident; synthetic persona."),
        "persona_summary": resident.get("persona_summary"),
        "tags": resident.get("tags", []),
    }

    intent_model = {
        "primary_intent": resident.get("primary_intent", ""),
        "goals": resident.get("goals", []),
        "proactivity": Proactivity.reactive.value,
        "domains": [],
    }

    # scheduling_policy: defaults only — v0.1 declared no scheduling surface.
    scheduling_policy = {
        "schedulable": False,
        "trigger_modes": [TriggerMode.on_message.value],
        "priority": Priority.normal.value,
        "concurrency_hint": 1,
        "cadence": {"type": CadenceType.none.value, "value": None},
    }

    execution_policy = {
        "execution_mode": ExecutionModeDecl.mock.value,
        "runtime_version": runtime_req.get("runtime_version", "resident_v1_mock"),
        "min_kernel": runtime_req.get("min_kernel", "6.1"),
        "required_slot_types": runtime_req.get("required_slot_types", []),
        "engines": runtime_req.get("engines", []),
        "allow_tool_use": False,
        "determinism": "deterministic_mock",
        "on_error_preference": OnErrorPreference.mock_fallback.value,
    }

    capabilities = {
        "modules": modules,
        "slots": slots,
        "declared_capabilities": [],
    }

    memory_policy = {
        "provider": memory_config.get("provider", "mock"),
        "store": memory_config.get("store", "in_process"),
        "isolation": memory_config.get("isolation", "per_resident"),
        "persistence": memory_config.get("persistence", False),
    }

    risk_policy = {
        "disclosure_required": safety_policy.get("disclosure_required", True),
        "audit_required": safety_policy.get("audit_required", False),
        "human_confirm_required": safety_policy.get("human_confirm_required", False),
        "risk_level": safety_policy.get("risk_level", RiskLevelDecl.none.value),
        "blocked_modules": safety_policy.get("blocked_modules", []),
        "safety_boundaries": [],
    }

    stability_constraints = {
        "immutable_layers": ["layer_1", "layer_3"],
        "forbidden_transitions": [],
        "invariants": [],
    }

    upgraded: Dict[str, Any] = {
        "file_type": dr_v01.get("file_type", DR_FILE_TYPE),
        "dr_version": DR_VERSION_V0_2,
        "schema_version": dr_v01.get("schema_version", "0.4.0"),
        "protocol_version": dr_v01.get("protocol_version", "0.4.0"),
        "dr_layer": DR_LAYER_ROLE,
        "not_executable": True,
        "identity": identity,
        "intent_model": intent_model,
        "scheduling_policy": scheduling_policy,
        "execution_policy": execution_policy,
        "capabilities": capabilities,
        "memory_policy": memory_policy,
        "risk_policy": risk_policy,
        "stability_constraints": stability_constraints,
        # --- preserved v0.1 compatibility fields (verbatim) ---
        "resident": dr_v01.get("resident"),
        "layers": dr_v01.get("layers"),
        "modules": dr_v01.get("modules"),
        "slots": dr_v01.get("slots"),
        "runtime_requirements": dr_v01.get("runtime_requirements"),
        "memory_config": dr_v01.get("memory_config"),
        "safety_policy": dr_v01.get("safety_policy"),
        "audit": dr_v01.get("audit"),
        "compile_info": dr_v01.get("compile_info"),
    }
    return upgraded
