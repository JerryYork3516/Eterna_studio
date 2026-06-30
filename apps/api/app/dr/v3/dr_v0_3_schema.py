"""DR v0.3 envelope schema — Stage 6.11 contract-only declaration.

This module defines a strictly declarative .digital_resident v0.3 envelope.
It does not execute runtime logic, does not call providers, and does not embed
secrets or credentials. The schema is intentionally additive and mock-only.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from ...models.v0_4 import SCHEMA_VERSION_V0_4, PROTOCOL_VERSION_V0_4

DR_FILE_TYPE = "digital_resident"
DR_VERSION_V0_3 = "0.3"
DR_SCHEMA_VERSION_V0_3 = "0.3.0"


class V03BaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class DRManifestV03(V03BaseModel):
    resident_id: str
    resident_name: str
    dr_schema_version: Literal["0.3.0"] = DR_SCHEMA_VERSION_V0_3
    revision: str = "1"
    source_protocol_version: Literal["0.4.0"] = PROTOCOL_VERSION_V0_4
    compatible_runtime: str = "resident_v1_mock"
    required_capabilities: List[str] = Field(default_factory=list)
    checksum: str = "mock-checksum"


class ResidentIdentityV03(V03BaseModel):
    resident_id: str
    name: str
    resident_type: str = "digital_resident"
    primary_language: str = "zh"
    symbolic_origin: str = "Eterna Studio"
    city_symbol: str = "Aftelle"
    personality_summary: str = "mock persona summary"
    domain_focus: List[str] = Field(default_factory=list)


class ResidentBlueprintV03(V03BaseModel):
    resident_id: str
    resident_name: str
    description: Optional[str] = None
    source_workflow_name: Optional[str] = None
    ui_language: Optional[Literal["zh", "en"]] = None
    tags: List[str] = Field(default_factory=list)


class RuntimeRequirementsV03(V03BaseModel):
    required_slot_types: List[str] = Field(default_factory=list)
    required_engines: List[str] = Field(default_factory=list)
    required_provider_types: List[str] = Field(default_factory=list)
    runtime_api_version: str = SCHEMA_VERSION_V0_4
    execution_mode: str = "mock"
    fallback_mode: str = "mock_fallback"


class MemoryPolicyV03(V03BaseModel):
    schema_version: str = DR_SCHEMA_VERSION_V0_3
    resident_id: str
    namespace: str = "default"
    memory_types: List[str] = Field(default_factory=list)
    interaction_log: Dict[str, Any] = Field(default_factory=dict)
    preference_memory: Dict[str, Any] = Field(default_factory=dict)
    retention_policy: str = "persistent"
    read_write_policy: str = "local_runtime"


class MemoryConfigV03(V03BaseModel):
    schema_version: str = DR_SCHEMA_VERSION_V0_3
    resident_id: str
    namespace: str = "default"
    storage_backend: str = "sqlite"
    memory_types: List[str] = Field(default_factory=list)
    interaction_log: Dict[str, Any] = Field(default_factory=dict)
    preference_memory: Dict[str, Any] = Field(default_factory=dict)
    mock_only: bool = True


class LatticeConfigV03(V03BaseModel):
    schema_version: str = DR_SCHEMA_VERSION_V0_3
    resident_id: str
    emotion: str = "neutral"
    energy: float = 0.5
    attention: str = "self"
    motion: str = "idle_breathing"
    voice_state: str = "idle"
    particle_density: float = 0.5
    color_palette: List[str] = Field(default_factory=list)
    focus_target: str = "none"
    state_transition_policy: str = "mock_transition"


class VoiceConfigV03(V03BaseModel):
    schema_version: str = DR_SCHEMA_VERSION_V0_3
    tts_profile: Dict[str, Any] = Field(default_factory=dict)
    voice_profile: Dict[str, Any] = Field(default_factory=dict)
    voice_state_schema: Dict[str, Any] = Field(default_factory=dict)
    voice_lattice_sync_policy: Dict[str, Any] = Field(default_factory=dict)
    speech_event_schema: Dict[str, Any] = Field(default_factory=dict)
    subtitle_policy: Dict[str, Any] = Field(default_factory=dict)


class ScreenCapabilityDeclarationV03(V03BaseModel):
    schema_version: str = DR_SCHEMA_VERSION_V0_3
    screen_context_schema: Dict[str, Any] = Field(default_factory=dict)
    ui_element_schema: Dict[str, Any] = Field(default_factory=dict)
    ui_anchor_schema: Dict[str, Any] = Field(default_factory=dict)
    guidance_action_schema: Dict[str, Any] = Field(default_factory=dict)
    screen_trace_schema: Dict[str, Any] = Field(default_factory=dict)
    screen_permission_policy: Dict[str, Any] = Field(default_factory=dict)
    mock_only: bool = True
    no_execution: bool = True
    no_real_screen_read: bool = True
    no_auto_click: bool = True
    no_accessibility_automation: bool = True
    no_cross_app_control: bool = True


class SafetyPolicyV03(V03BaseModel):
    no_secret_in_dr: bool = True
    no_direct_provider_binding: bool = True
    mock_screen_only: bool = True
    user_data_not_embedded: bool = True
    not_executable: bool = True
    notes: List[str] = Field(default_factory=list)


class RuntimePlanStepV03(V03BaseModel):
    step: str
    from_: str = Field(alias="from")
    to: str
    optional: bool = False


class RuntimePlanV03(V03BaseModel):
    schema_version: str = DR_SCHEMA_VERSION_V0_3
    mode: str = "declarative"
    steps: List[RuntimePlanStepV03] = Field(default_factory=list)
    forbidden: List[str] = Field(default_factory=list)


class FallbackRouteV03(V03BaseModel):
    capability: str
    route: str
    mode: str = "mock"
    notes: str = ""


class CompileInfoV03(V03BaseModel):
    compiler: str
    compiler_version: str
    compiled_at: str
    source: str
    layer_count: int
    module_count: int
    slot_count: int
    schema_version: str
    protocol_version: str


class AuditFindingV03(V03BaseModel):
    status: Literal["PASS", "WARNING", "FAIL"]
    code: str
    message: str
    path: str


class AuditReportV03(V03BaseModel):
    schema_version: str = DR_SCHEMA_VERSION_V0_3
    valid: bool
    findings: List[AuditFindingV03] = Field(default_factory=list)
    checked_at: str
    summary: Dict[str, int] = Field(default_factory=dict)


class DRPayloadV03(V03BaseModel):
    resident_identity: ResidentIdentityV03
    resident_blueprint: ResidentBlueprintV03
    layers_snapshot: List[Dict[str, Any]] = Field(default_factory=list, alias="13_layers_snapshot")
    modules: List[Dict[str, Any]] = Field(default_factory=list)
    nodes: List[Dict[str, Any]] = Field(default_factory=list)
    slots: List[Dict[str, Any]] = Field(default_factory=list)
    edges: List[Dict[str, Any]] = Field(default_factory=list)
    runtime_requirements: RuntimeRequirementsV03
    provider_requirements: Dict[str, Any] = Field(default_factory=dict)
    memory_policy: MemoryPolicyV03
    memory_config: MemoryConfigV03
    lattice_config: LatticeConfigV03
    voice_config: VoiceConfigV03
    screen_capability_declaration: ScreenCapabilityDeclarationV03
    safety_policy: SafetyPolicyV03
    audit_policy: Dict[str, Any] = Field(default_factory=dict)
    runtime_plan: RuntimePlanV03
    fallback_routes: List[FallbackRouteV03] = Field(default_factory=list)
    graph_snapshot: Dict[str, Any] = Field(default_factory=dict)
    node_snapshot: List[Dict[str, Any]] = Field(default_factory=list)
    raw_layers: List[Dict[str, Any]] = Field(default_factory=list)


class DRDocumentV03(V03BaseModel):
    file_type: Literal["digital_resident"] = DR_FILE_TYPE
    dr_version: Literal["0.3"] = DR_VERSION_V0_3
    dr_schema_version: Literal["0.3.0"] = DR_SCHEMA_VERSION_V0_3
    protocol_version: Literal["0.4.0"] = PROTOCOL_VERSION_V0_4
    revision: str = "1"
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    not_executable: bool = True
    manifest: DRManifestV03
    payload: DRPayloadV03
    compile_info: CompileInfoV03
    audit_report: AuditReportV03
    # Backward-compatible legacy aliases for consumers that still inspect the
    # prior compile envelope. These remain declarative only.
    legacy_compiled_dr: Optional[Dict[str, Any]] = None
    legacy_dr_payload: Optional[Dict[str, Any]] = None

"""Convenience builders for deterministic defaults."""


def build_runtime_plan_steps() -> List[RuntimePlanStepV03]:
    return [
        RuntimePlanStepV03(step="user_input", **{"from": "user_input"}, to="memory.read"),
        RuntimePlanStepV03(step="memory.read", **{"from": "memory.read"}, to="llm.reasoning"),
        RuntimePlanStepV03(step="llm.reasoning", **{"from": "llm.reasoning"}, to="memory.write"),
        RuntimePlanStepV03(step="memory.write", **{"from": "memory.write"}, to="lattice.update"),
        RuntimePlanStepV03(step="lattice.update", **{"from": "lattice.update"}, to="voice.speak", optional=True),
        RuntimePlanStepV03(step="voice.speak", **{"from": "voice.speak"}, to="output", optional=True),
    ]
