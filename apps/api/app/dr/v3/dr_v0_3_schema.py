"""DR v0.3 envelope schema — Stage 6.11 contract-only declaration.

This module defines a strictly declarative .digital_resident v0.3 envelope.
It does not execute runtime logic, does not call providers, and does not embed
secrets or credentials. The schema is intentionally additive and mock-only.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from ...models.v0_4 import SCHEMA_VERSION_V0_4, PROTOCOL_VERSION_V0_4
from ...services.abstract_bust_blueprint import AbstractBustBlueprint

DR_FILE_TYPE = "digital_resident"
DR_VERSION_V0_3 = "0.3"
DR_SCHEMA_VERSION_V0_3 = "0.3.0"
STAGE7_4_REQUIRED_CAPABILITIES_V0_3 = ("llm", "memory", "lattice")


class V03BaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class DRManifestV03(V03BaseModel):
    resident_id: str
    resident_name: str
    dr_schema_version: Literal["0.3.0"]
    revision: str = "1"
    source_protocol_version: Literal["0.4.0"]
    compatible_runtime: Literal["resident_v1_mock"]
    required_capabilities: List[str]
    checksum: str = "mock-checksum"

    @field_validator("required_capabilities")
    @classmethod
    def _required_capabilities_are_frozen(
        cls, value: List[str]
    ) -> List[str]:
        if value != list(STAGE7_4_REQUIRED_CAPABILITIES_V0_3):
            raise ValueError(
                "required_capabilities must remain "
                "['llm', 'memory', 'lattice']"
            )
        return value


class ResidentIdentityV03(V03BaseModel):
    resident_id: str
    name: str
    resident_type: str = "digital_resident"
    primary_language: str = "zh"
    symbolic_origin: str = "Eterna Studio"
    city_symbol: str = "Aftelle"
    personality_summary: str = "mock persona summary"
    domain_focus: List[str] = Field(default_factory=list)


class BehaviorFieldReferenceV03(V03BaseModel):
    reference_id: str = ""
    reference_type: str
    layer_id: str
    module_id: str
    field_id: str
    path: str
    usage: str = ""
    usage_key: str = ""


class BehaviorModulePolicyV03(V03BaseModel):
    module_id: str
    source_module_id: str
    module_type: str
    policy_key: str
    preset_id: str
    selected_options: List[str] = Field(default_factory=list)
    custom_text: str = ""
    field_references: List[BehaviorFieldReferenceV03] = Field(
        default_factory=list
    )
    validation_rules: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    source_nodes: List[str] = Field(default_factory=list)


class BehaviorPolicyModulesV03(V03BaseModel):
    language_behavior: Optional[BehaviorModulePolicyV03] = None
    interaction_behavior: Optional[BehaviorModulePolicyV03] = None
    task_behavior: Optional[BehaviorModulePolicyV03] = None
    social_behavior: Optional[BehaviorModulePolicyV03] = None
    decision_behavior: Optional[BehaviorModulePolicyV03] = None
    detail_behavior: Optional[BehaviorModulePolicyV03] = None


class BehaviorPolicyV03(V03BaseModel):
    schema_version: str = "0.1"
    source_layer: Literal["layer_8"] = "layer_8"
    modules: BehaviorPolicyModulesV03


class ResidentBlueprintV03(V03BaseModel):
    resident_id: str
    resident_name: str
    description: Optional[str] = None
    source_workflow_name: Optional[str] = None
    ui_language: Optional[Literal["zh-CN", "en", "zh", "en-US"]] = None
    tags: List[str] = Field(default_factory=list)
    behavior_policy: Optional[BehaviorPolicyV03] = None


class RuntimeRequirementsV03(V03BaseModel):
    required_slot_types: List[str] = Field(default_factory=list)
    required_engines: List[str] = Field(default_factory=list)
    required_provider_types: List[str] = Field(default_factory=list)
    runtime_api_version: Literal["0.4.0"] = SCHEMA_VERSION_V0_4
    execution_mode: Literal["mock"] = "mock"
    fallback_mode: Literal["mock_fallback"] = "mock_fallback"


class MemoryPolicyV03(V03BaseModel):
    schema_version: str = DR_SCHEMA_VERSION_V0_3
    resident_id: str
    namespace: str = "default"
    memory_types: List[str] = Field(default_factory=list)
    interaction_log: Dict[str, Any] = Field(default_factory=dict)
    preference_memory: Dict[str, Any] = Field(default_factory=dict)
    retention_policy: str = "persistent"
    read_write_policy: str = "local_runtime"
    memory_policy_extensions: Optional[Dict[str, Any]] = None


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
    status_classification: Dict[str, Any] = Field(default_factory=dict)


class VoiceConfigV03(V03BaseModel):
    schema_version: str = DR_SCHEMA_VERSION_V0_3
    tts_profile: Dict[str, Any] = Field(default_factory=dict)
    voice_profile: Dict[str, Any] = Field(default_factory=dict)
    voice_state_schema: Dict[str, Any] = Field(default_factory=dict)
    voice_lattice_sync_policy: Dict[str, Any] = Field(default_factory=dict)
    speech_event_schema: Dict[str, Any] = Field(default_factory=dict)
    subtitle_policy: Dict[str, Any] = Field(default_factory=dict)
    status_classification: Dict[str, Any] = Field(default_factory=dict)


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
    not_executable: Literal[True] = True
    notes: List[str] = Field(default_factory=list)
    content_safety_policy: Optional[Dict[str, Any]] = None
    behavior_safety_policy: Optional[Dict[str, Any]] = None
    data_safety_policy: Optional[Dict[str, Any]] = None
    interaction_safety_policy: Optional[Dict[str, Any]] = None
    risk_policy: Optional[Dict[str, Any]] = None
    hard_block_policy: Optional[Dict[str, Any]] = None
    human_review_policy: Optional[Dict[str, Any]] = None
    audit_log_policy: Optional[Dict[str, Any]] = None
    safe_redirect_policy: Optional[Dict[str, Any]] = None


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
    schema_version: Literal["0.3.0"]
    protocol_version: Literal["0.4.0"]


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
    serialization_metrics: Dict[str, Any] = Field(default_factory=dict)
    compatibility_metrics: Dict[str, int] = Field(default_factory=dict)


class VisualExpressionIntensityRangeV03(V03BaseModel):
    minimum: float = Field(ge=0.0, le=1.0)
    maximum: float = Field(ge=0.0, le=1.0)


class VisualExpressionParameterRangeV03(V03BaseModel):
    minimum: float
    maximum: float


class VisualExpressionParameterRangesV03(V03BaseModel):
    expression_intensity: VisualExpressionParameterRangeV03
    brightness_multiplier: VisualExpressionParameterRangeV03
    saturation_multiplier: VisualExpressionParameterRangeV03
    temperature_shift: VisualExpressionParameterRangeV03
    energy_multiplier: VisualExpressionParameterRangeV03
    motion_speed_multiplier: VisualExpressionParameterRangeV03
    diffusion_multiplier: VisualExpressionParameterRangeV03


class VisualExpressionStateSelectionPolicyV03(V03BaseModel):
    selection_source: Literal["runtime_core"] = "runtime_core"
    state_field: Literal["expression_state"] = "expression_state"
    intensity_field: Literal["expression_intensity"] = "expression_intensity"
    selection_rules: Optional[List[str]] = None
    allowed_states: List[
        Literal["neutral", "calm", "caring", "subdued", "joyful"]
    ] = Field(default_factory=list)
    default_state: Literal["neutral"] = "neutral"
    missing_state_fallback: Literal["neutral"] = "neutral"
    invalid_state_fallback: Literal["neutral"] = "neutral"
    single_state_per_turn: bool = True
    resident_expression_only: bool = True
    user_emotion_diagnosis: bool = False
    renderer_parameters_allowed: bool = False
    lifecycle_state_separated: bool = True


class VisualExpressionBaseColorPolicyV03(V03BaseModel):
    priority: List[str] = Field(default_factory=list)
    resident_default_base_color: Optional[str] = None
    particle_core_fallback: Literal["default_gray_white"] = "default_gray_white"


class ParticleCoreRelativeMappingV03(V03BaseModel):
    brightness_multiplier: float = Field(ge=0.7, le=1.25)
    saturation_multiplier: float = Field(ge=0.65, le=1.2)
    temperature_shift: float = Field(ge=-0.15, le=0.15)
    energy_multiplier: float = Field(ge=0.7, le=1.25)
    motion_speed_multiplier: float = Field(ge=0.75, le=1.2)
    diffusion_multiplier: float = Field(ge=0.75, le=1.25)


class VisualExpressionTransitionPolicyV03(V03BaseModel):
    transition_duration: float = Field(ge=0.0, le=10.0)
    minimum_hold_duration: float = Field(ge=0.0, le=10.0)
    transition_style: Literal["smooth"] = "smooth"
    repeat_same_state_restarts_transition: bool = False
    continue_from_current_visual_value: bool = True
    uses_accumulated_idle_time_as_progress: Optional[bool] = None
    minimum_hold_prevents_flicker: Optional[bool] = None
    transition_executor: Optional[Literal["aftelle"]] = None


class VisualExpressionLifecyclePriorityV03(V03BaseModel):
    override_states: List[str] = Field(default_factory=list)
    composable_states: List[str] = Field(default_factory=list)


class VisualExpressionFallbackPolicyV03(V03BaseModel):
    invalid_state: Literal["neutral"] = "neutral"
    missing_state: Literal["neutral"] = "neutral"
    clamp_intensity: bool = True
    clamp_mapping_values: bool = True


class AbstractBustMappingV03(V03BaseModel):
    status: Literal["reserved"] = "reserved"


class VisualExpressionMappingV03(V03BaseModel):
    protocol_version: Literal["1.0"] = "1.0"
    content_revision: Literal[
        "stage7_4_11_visual_expression_projection_v1",
        "stage7_4_11_aftelle_projection_completion_v1",
        "stage7_4_11_selection_transition_projection_completion_v1",
    ] = "stage7_4_11_selection_transition_projection_completion_v1"
    allowed_states: List[
        Literal["neutral", "calm", "caring", "subdued", "joyful"]
    ] = Field(default_factory=list)
    default_state: Literal["neutral"] = "neutral"
    intensity_range: VisualExpressionIntensityRangeV03
    parameter_ranges: Optional[VisualExpressionParameterRangesV03] = None
    state_selection_policy: Optional[
        VisualExpressionStateSelectionPolicyV03
    ] = None
    base_color_policy: VisualExpressionBaseColorPolicyV03
    particle_core_mapping: Dict[
        Literal["neutral", "calm", "caring", "subdued", "joyful"],
        ParticleCoreRelativeMappingV03,
    ] = Field(default_factory=dict)
    transition_policy: VisualExpressionTransitionPolicyV03
    lifecycle_priority: VisualExpressionLifecyclePriorityV03
    fallback_policy: VisualExpressionFallbackPolicyV03
    abstract_bust_mapping: AbstractBustMappingV03


class DRLayerSnapshotV03(V03BaseModel):
    layer_id: str
    layer_name: str
    layer_order: int
    module_ids: List[str] = Field(default_factory=list)
    present: bool
    content_state: Optional[str] = None
    empty_by_design: Optional[bool] = None
    runtime_enabled: Optional[bool] = None
    declares_capability: Optional[bool] = None
    status_description_key: Optional[str] = None
    content_revision: Optional[str] = None


class DRModuleNodeV03(V03BaseModel):
    node_id: str
    node_type: str
    type: Optional[str] = None
    module_id: str
    layer_id: str
    params: Dict[str, Any] = Field(default_factory=dict)
    i18n_keys: Dict[str, Any] = Field(default_factory=dict)
    outputs: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    position: Optional[Dict[str, Any]] = None


class DRModuleEdgeV03(V03BaseModel):
    edge_id: str
    source: str
    source_port: str
    target: str
    target_port: str


class DRModuleGraphV03(V03BaseModel):
    nodes: List[DRModuleNodeV03] = Field(default_factory=list)
    edges: List[DRModuleEdgeV03] = Field(default_factory=list)
    compile_time_only: Optional[bool] = None
    output_key: Optional[str] = None
    shell_version: Optional[str] = None
    content_revision: Optional[str] = None
    fact_source_bindings: Optional[Dict[str, Any]] = None
    source_output_identity_cleanup_revision: Optional[str] = None
    source_priority_revision: Optional[str] = None
    validation_compatibility_revision: Optional[str] = None
    node_roles: Optional[List[Any]] = None
    mock_only: Optional[bool] = None
    no_real_screen: Optional[bool] = None
    no_auto_click: Optional[bool] = None
    no_cross_app_control: Optional[bool] = None
    no_accessibility_automation: Optional[bool] = None
    no_agent_loop: Optional[bool] = None
    no_runtime_kernel_change: Optional[bool] = None
    no_cloud_bridge: Optional[bool] = None
    runtime_chain: Optional[List[str]] = None


class DRModuleV03(V03BaseModel):
    module_id: str
    module_name: str
    module_type: str
    module_version: str
    layer_id: str
    module_graph: DRModuleGraphV03
    category: str = ""
    status: str = "MOCK"
    protocol_version: str = PROTOCOL_VERSION_V0_4
    color_status: str = ""
    config: Dict[str, Any] = Field(default_factory=dict)
    context_bindings: List[Any] = Field(default_factory=list)
    dr_mapping: Dict[str, Any] = Field(default_factory=dict)
    dr_write_keys: List[Any] = Field(default_factory=list)
    input_schema: List[Any] = Field(default_factory=list)
    inputs: Dict[str, Any] = Field(default_factory=dict)
    output_schema: List[Any] = Field(default_factory=list)
    outputs: Dict[str, Any] = Field(default_factory=dict)
    permissions: List[Any] = Field(default_factory=list)
    risk_level: str = "none"
    audit_required: bool = False
    human_confirm_required: bool = False
    i18n_keys: Dict[str, Any] = Field(default_factory=dict)
    is_placeholder: bool = False
    mock_only: bool = True
    no_execution: bool = True
    runtime_enabled: bool = False
    runtime_mapping: Dict[str, Any] = Field(default_factory=dict)
    screen_config: Dict[str, Any] = Field(default_factory=dict)
    slot_bindings: List[Any] = Field(default_factory=list)
    slot_declarations: List[Any] = Field(default_factory=list)
    slot_type: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    ui_config: Dict[str, Any] = Field(default_factory=dict)
    status_classification: Optional[Dict[str, Any]] = None


class DRCanvasNodeV03(V03BaseModel):
    node_id: str
    type: Optional[str] = None
    category: Optional[str] = None
    title_key: Optional[str] = None
    title_fallback: Optional[str] = None
    position: Dict[str, Any] = Field(default_factory=dict)
    lock_level: Optional[str] = None
    locale: Optional[str] = None
    data: Dict[str, Any] = Field(default_factory=dict)
    ports: Dict[str, Any] = Field(default_factory=dict)
    validation: Optional[Dict[str, Any]] = None


class DRSlotV03(V03BaseModel):
    protocol_version: str = PROTOCOL_VERSION_V0_4
    slot_id: str
    slot_type: str
    slot_role: Optional[str] = None
    input_schema: List[Any] = Field(default_factory=list)
    output_schema: List[Any] = Field(default_factory=list)
    provider: Optional[Any] = None
    provider_requirement: Dict[str, Any] = Field(default_factory=dict)
    runtime_capability: Dict[str, Any] = Field(default_factory=dict)
    execution_mode: str = "mock"
    fallback_policy: Dict[str, Any] = Field(default_factory=dict)
    permission_policy: Dict[str, Any] = Field(default_factory=dict)
    trace_schema: Dict[str, Any] = Field(default_factory=dict)
    status: str = "MOCK"
    engine_binding: str
    mock_supported: bool = True
    i18n_keys: Dict[str, Any] = Field(default_factory=dict)
    enabled: bool = False


class ProviderRequirementV03(V03BaseModel):
    required: bool
    mode: Optional[str] = None
    capabilities: List[str] = Field(default_factory=list)
    provider_type: Optional[str] = None
    fallback_provider_type: Optional[str] = None


class CompatibilitySurfaceStatusV03(V03BaseModel):
    surface_id: str
    states: List[str] = Field(default_factory=list)
    role: str
    authoritative: bool
    derived_from: str
    may_override_authority: bool
    forbidden_keys: List[str] = Field(default_factory=list)
    content_revision: str


class GraphSnapshotV03(V03BaseModel):
    nodes: List[DRCanvasNodeV03] = Field(default_factory=list)
    edges: List[DRModuleEdgeV03] = Field(default_factory=list)
    layers: List[DRLayerSnapshotV03] = Field(default_factory=list)
    slots: List[DRSlotV03] = Field(default_factory=list)
    compatibility_status: Optional[CompatibilitySurfaceStatusV03] = None
    layer_outputs: Dict[str, Any] = Field(default_factory=dict)
    layer_outputs_status: Optional[CompatibilitySurfaceStatusV03] = None


class AuditPolicyV03(V03BaseModel):
    mode: str = "declarative"
    source: str = "compile_audit"
    requires_review: bool = False
    content_revision: Optional[str] = None
    capability_status_governance: Optional[Dict[str, Any]] = None
    runtime_dialogue_projection_expected: Optional[bool] = None
    schema_traceability_gate_revision: Optional[
        Literal["stage7_4_12_final_schema_traceability_gate_fix_v1"]
    ] = None
    identity_literal_export_gate_revision: Optional[
        Literal["stage7_4_12_identity_literal_export_gate_fix_v1"]
    ] = None


class BehaviorProjectionV03(V03BaseModel):
    first_interaction: Dict[str, Any]


class ExpressionProjectionV03(V03BaseModel):
    first_greeting: Optional[Dict[str, Any]] = None
    first_presence: Optional[Dict[str, Any]] = None


class RelationshipProjectionV03(V03BaseModel):
    initial_relationship: Dict[str, Any]


class NarrativeMemoryPolicyReferenceV03(V03BaseModel):
    source_layer_id: Literal["layer_3", "layer_8", "layer_11"]
    source_module_id: str
    source_node_id: str
    source_path: str
    usage: str


class NarrativeMemoryCandidateEvidenceRulesV03(V03BaseModel):
    requirements: List[str]
    excluded_inputs: List[str]
    candidate_fields: List[str]
    explicit_user_statement_required: Literal[True]
    source_turn_traceability_required: Literal[True]


class NarrativeMemoryConsentPolicyV03(V03BaseModel):
    explicit_remember_request_raises_candidate_priority: Literal[True]
    explicit_remember_request_bypasses_safety: Literal[False]
    sensitive_or_ambiguous_requires_explicit_user_consent: Literal[True]
    user_rejection_state: Literal["rejected"]
    rejected_candidate_auto_reproposal: Literal[False]
    user_forget_request_target_state: Literal["deleted"]


class NarrativeMemorySensitiveEventAliasV03(V03BaseModel):
    status: Literal["compatibility_alias"]
    interpretation: Literal[
        (
            "sensitive_or_ambiguous_requires_explicit_"
            "user_consent_and_safety_validation"
        )
    ]
    not_a_blanket_allow: Literal[True]
    not_a_blanket_deny: Literal[True]


class NarrativeMemorySensitivityPolicyV03(V03BaseModel):
    sensitive_or_ambiguous_requires_explicit_user_consent: Literal[True]
    permanently_forbidden_categories: List[str]
    safety_boundary_enforced: Literal[True]
    legacy_sensitive_event_alias: (
        NarrativeMemorySensitiveEventAliasV03
    )


class NarrativeMemoryDeduplicationPolicyV03(V03BaseModel):
    same_event_action: Literal["deduplicate_or_merge"]
    duplicate_events_are_merged: Literal[True]


class NarrativeMemoryConflictResolutionPolicyV03(V03BaseModel):
    latest_explicit_user_statement: Literal[
        "supersede_older_information"
    ]
    user_latest_explicit_statement_has_priority: Literal[True]


class NarrativeMemorySupersessionPolicyV03(V03BaseModel):
    older_conflicting_memory_state: Literal["superseded"]
    superseded_memory_is_current_fact: Literal[False]
    superseded_memory_retrievable: Literal[False]


class NarrativeMemoryDeletionPolicyV03(V03BaseModel):
    single_item_delete: Literal[True]
    clear_all: Literal[True]
    deleted_is_retrievable: Literal[False]
    restore_from_model_inference: Literal[False]
    restore_from_historical_transcript: Literal[False]
    deleted_memory_retrievable: Literal[False]
    deleted_memory_enters_model_context: Literal[False]


class NarrativeMemoryRetrievalPolicyV03(V03BaseModel):
    allowed_lifecycle_states: List[str]
    excluded_lifecycle_states: List[str]
    rules: List[str]
    deleted_memory_retrievable: Literal[False]
    rejected_memory_retrievable: Literal[False]
    deleted_or_rejected_enters_model_context: Literal[False]


class NarrativeMemoryExpressionPolicyV03(V03BaseModel):
    rules: List[str]
    relationship_stage_transition_allowed: Literal[False]
    never_claim_permanent_memory: Literal[True]


class NarrativeMemoryModelAuthorityV03(V03BaseModel):
    model_can_propose_candidate_only: Literal[True]
    model_can_write_memory: Literal[False]
    model_can_update_memory: Literal[False]
    model_can_delete_memory: Literal[False]


class NarrativeMemoryRuntimeAuthorityV03(V03BaseModel):
    runtime_is_final_decision_owner: Literal[True]


class NarrativeMemoryProjectionV03(V03BaseModel):
    schema_version: Literal["0.1"]
    content_revision: Literal[
        "stage7_4_14_narrative_memory_projection_v0_1"
    ]
    derived: Literal[True]
    read_only: Literal[True]
    source_paths: List[str]
    enabled: Literal[True]
    allowed_memory_types: List[str]
    memory_lifecycle_states: List[str]
    candidate_evidence_rules: NarrativeMemoryCandidateEvidenceRulesV03
    forbidden_content_rules: List[str]
    consent_policy: NarrativeMemoryConsentPolicyV03
    sensitivity_policy: NarrativeMemorySensitivityPolicyV03
    deduplication_policy: NarrativeMemoryDeduplicationPolicyV03
    conflict_resolution_policy: NarrativeMemoryConflictResolutionPolicyV03
    supersession_policy: NarrativeMemorySupersessionPolicyV03
    deletion_policy: NarrativeMemoryDeletionPolicyV03
    retrieval_policy: NarrativeMemoryRetrievalPolicyV03
    expression_policy: NarrativeMemoryExpressionPolicyV03
    model_authority: NarrativeMemoryModelAuthorityV03
    runtime_authority: NarrativeMemoryRuntimeAuthorityV03
    relationship_boundary_refs: List[
        NarrativeMemoryPolicyReferenceV03
    ]
    safety_boundary_refs: List[NarrativeMemoryPolicyReferenceV03]
    dialogue_boundary_refs: List[NarrativeMemoryPolicyReferenceV03]
    deleted_memory_retrievable: Literal[False]
    rejected_candidate_reproposal_allowed: Literal[False]
    relationship_stage_transition_allowed: Literal[False]
    full_dialogue_storage_allowed: Literal[False]
    single_item_delete_supported: Literal[True]
    clear_all_supported: Literal[True]
    contains_user_memory_records: Literal[False]

    @model_validator(mode="after")
    def _narrative_memory_projection_is_static_and_safe(
        self,
    ) -> "NarrativeMemoryProjectionV03":
        if self.allowed_memory_types != [
            "shared_experience",
            "confirmed_plan",
            "important_progress",
            "confirmed_emotional_event",
            "mutual_commitment",
            "user_marked_important",
        ]:
            raise ValueError(
                "allowed_memory_types must contain exactly the six "
                "Stage 7.4.14 narrative-memory types in stable order"
            )
        if self.memory_lifecycle_states != [
            "candidate",
            "active",
            "superseded",
            "deleted",
            "rejected",
        ]:
            raise ValueError(
                "memory_lifecycle_states must contain exactly candidate, "
                "active, superseded, deleted, and rejected"
            )
        if self.candidate_evidence_rules.candidate_fields != [
            "memory_type",
            "candidate_summary",
            "source_turn_reference",
            "importance_reason",
            "sensitivity_level",
            "requires_user_consent",
        ]:
            raise ValueError(
                "narrative-memory candidates must use the closed six-field "
                "contract"
            )
        if self.retrieval_policy.allowed_lifecycle_states != ["active"]:
            raise ValueError(
                "only active narrative memory may be retrieved"
            )
        if self.retrieval_policy.excluded_lifecycle_states != [
            "candidate",
            "superseded",
            "deleted",
            "rejected",
        ]:
            raise ValueError(
                "candidate, superseded, deleted, and rejected memory must "
                "remain outside retrieval context"
            )
        if {
            reference.source_layer_id
            for reference in self.safety_boundary_refs
        } != {"layer_3"}:
            raise ValueError(
                "safety_boundary_refs must reference Layer 3 only"
            )
        if {
            reference.source_layer_id
            for reference in self.dialogue_boundary_refs
        } != {"layer_8"}:
            raise ValueError(
                "dialogue_boundary_refs must reference Layer 8 only"
            )
        if {
            reference.source_layer_id
            for reference in self.relationship_boundary_refs
        } != {"layer_11"}:
            raise ValueError(
                "relationship_boundary_refs must reference Layer 11 only"
            )
        required_forbidden = {
            "password",
            "verification_code",
            "api_key",
            "payment_credential",
            "precise_identity_credential",
            "authentication_information",
            "inferred_health_relationship_or_emotion_conclusion",
            "full_dialogue_transcript",
            "provider_request",
            "internal_reasoning",
            "provider_trace",
            "user_requested_not_to_save",
            "generated_from_count_duration_or_relationship_stage_only",
        }
        if not required_forbidden.issubset(
            set(self.forbidden_content_rules)
        ):
            raise ValueError(
                "forbidden_content_rules must cover credentials, inferred "
                "conclusions, full dialogue, internal traces, user refusal, "
                "and count/duration/relationship-stage generation"
            )
        return self


class RelationshipPolicyReferenceV03(V03BaseModel):
    reference_id: str
    source_layer_id: Literal["layer_3", "layer_5", "layer_12"]
    source_module_id: str
    source_node_id: str
    source_path: str


class RelationshipTransitionEvidenceRulesV03(V03BaseModel):
    allowed_evidence_types: List[str]
    progression_requirements: List[str]
    candidate_fields: List[str]
    requires_explicit_user_expression: Literal[True]


class RelationshipForbiddenTransitionRulesV03(V03BaseModel):
    forbidden_evidence: List[str]
    automatic_transition: Literal[False]
    vulnerability_cannot_trigger: Literal[True]
    model_or_resident_inference_cannot_trigger: Literal[True]


class RelationshipResetRollbackPolicyV03(V03BaseModel):
    available_user_actions: List[str]
    user_control_has_highest_priority: Literal[True]
    resident_must_not_block_or_dissuade: Literal[True]
    reset_target: Literal["initial_acquaintance"]
    reset_deletes_memory: Literal[False]
    memory_deletion_authority: Literal["layer_5"]
    forbidden_responses: List[str]


class RelationshipUserConsentPolicyV03(V03BaseModel):
    requires_explicit_user_consent: Literal[True]
    user_control_priority: Literal["highest"]
    confirmation_required_when_requested: Literal[True]
    single_utterance_unlocks_reserved_stage: Literal[False]
    consent_cannot_bypass_feature_gate: Literal[True]
    user_can_disable_progression: Literal[True]


class RomanticRelationshipFeatureGateV03(V03BaseModel):
    stage_id: Literal["romantic_relationship_reserved"]
    status: Literal["reserved"]
    runtime_enabled: Literal[False]
    automatic_transition: Literal[False]
    requires_explicit_user_consent: Literal[True]
    requires_runtime_feature_gate: Literal[True]
    current_version_unlock_allowed: Literal[False]
    single_utterance_unlock_allowed: Literal[False]
    activation_requirements: List[str]
    forbidden_trigger_evidence: List[str]
    excluded_from: List[str]

    @model_validator(mode="after")
    def _reserved_gate_remains_closed(
        self,
    ) -> "RomanticRelationshipFeatureGateV03":
        if self.activation_requirements != [
            "future_version_runtime_feature_gate_enabled",
            "explicit_user_consent_confirmed",
        ]:
            raise ValueError(
                "romantic reserved stage requires both the future runtime "
                "feature gate and explicit user consent"
            )
        if self.forbidden_trigger_evidence != [
            "user_loneliness",
            "user_low_mood",
            "user_vulnerability",
            "dependency_testing",
            "chat_count",
            "usage_duration",
            "payment_status",
            "model_or_resident_inference",
        ]:
            raise ValueError(
                "romantic reserved stage forbidden triggers must remain "
                "complete and stable"
            )
        if self.excluded_from != [
            "enabled_stages",
            "model_context",
            "few_shot",
            "automatic_transition_path",
        ]:
            raise ValueError(
                "romantic reserved stage must stay outside enabled stages, "
                "model context, Few-shot, and automatic transition"
            )
        return self


class RelationshipProgressionProjectionV03(V03BaseModel):
    schema_version: Literal["0.1"]
    content_revision: Literal[
        "stage7_4_13_relationship_progression_projection_v0_1"
    ]
    derived: Literal[True]
    read_only: Literal[True]
    source_paths: List[str]
    default_stage: Literal["initial_acquaintance"]
    enabled_stages: List[str]
    reserved_stages: List[str]
    stage_definitions: Dict[str, Dict[str, str]]
    transition_evidence_rules: RelationshipTransitionEvidenceRulesV03
    forbidden_transition_rules: RelationshipForbiddenTransitionRulesV03
    reset_and_rollback_policy: RelationshipResetRollbackPolicyV03
    user_consent_policy: RelationshipUserConsentPolicyV03
    safety_boundary_refs: List[RelationshipPolicyReferenceV03]
    memory_policy_refs: List[RelationshipPolicyReferenceV03]
    romantic_feature_gate: RomanticRelationshipFeatureGateV03
    stage_decision_owner: Literal["runtime"]
    model_can_propose_evidence_only: Literal[True]
    model_can_change_stage: Literal[False]
    user_control_priority: Literal["highest"]

    @model_validator(mode="after")
    def _relationship_projection_is_static_and_safe(
        self,
    ) -> "RelationshipProgressionProjectionV03":
        enabled_stages = [
            "initial_acquaintance",
            "growing_familiarity",
            "stable_companionship",
            "trusted_relationship",
        ]
        if self.enabled_stages != enabled_stages:
            raise ValueError(
                "enabled_stages must contain exactly the four current "
                "relationship stages in stable order"
            )
        if self.reserved_stages != [
            "romantic_relationship_reserved"
        ]:
            raise ValueError(
                "reserved_stages must contain only "
                "romantic_relationship_reserved"
            )
        if list(self.stage_definitions) != enabled_stages:
            raise ValueError(
                "stage_definitions must contain exactly the four enabled "
                "stages in stable order"
            )
        if (
            "romantic_relationship_reserved"
            in self.stage_definitions
        ):
            raise ValueError(
                "romantic reserved stage must not enter stage_definitions"
            )
        if (
            self.transition_evidence_rules.candidate_fields
            != [
                "evidence_type",
                "evidence_detected",
                "evidence_source",
                "requires_user_confirmation",
            ]
        ):
            raise ValueError(
                "model evidence candidates must use the closed four-field "
                "contract"
            )
        if self.forbidden_transition_rules.forbidden_evidence != [
            "chat_count",
            "usage_duration",
            "payment_status",
            "user_loneliness_depression_vulnerability_or_dependency_testing",
            "resident_or_model_self_judgement",
            "few_shot_resident_reply_or_model_inference",
            "unconfirmed_memory",
        ]:
            raise ValueError(
                "forbidden transition evidence must remain complete"
            )
        if (
            self.reset_and_rollback_policy.available_user_actions
            != [
                "reject_upgrade",
                "revoke_relationship_confirmation",
                "downgrade_to_lower_stage",
                "reset_to_initial_acquaintance",
                "disable_relationship_progression",
            ]
        ):
            raise ValueError(
                "user reject, revoke, downgrade, reset, and disable controls "
                "must all remain available"
            )
        if {
            reference.source_layer_id
            for reference in self.safety_boundary_refs
        } != {"layer_3", "layer_12"}:
            raise ValueError(
                "safety_boundary_refs must reference Layer 3 and Layer 12"
            )
        if {
            reference.source_layer_id
            for reference in self.memory_policy_refs
        } != {"layer_5"}:
            raise ValueError(
                "memory_policy_refs must reference Layer 5 only"
            )
        return self


class RuntimeDialogueProjectionV03(V03BaseModel):
    schema_version: str
    projection_type: str
    derived: bool
    read_only: bool
    primary_source_path: str
    supporting_source_paths: List[str] = Field(default_factory=list)
    locale: str
    usage: str
    system_instruction: str
    scenarios: List[Any] = Field(default_factory=list)
    language_policy: Dict[str, Any] = Field(default_factory=dict)
    response_style: Dict[str, Any] = Field(default_factory=dict)
    response_order: Dict[str, Any] = Field(default_factory=dict)
    follow_up_policy: Dict[str, Any] = Field(default_factory=dict)
    advice_policy: Dict[str, Any] = Field(default_factory=dict)
    silence_policy: Dict[str, Any] = Field(default_factory=dict)
    relationship_policy: Dict[str, Any] = Field(default_factory=dict)
    memory_usage_policy: Dict[str, Any] = Field(default_factory=dict)
    self_disclosure_policy: Dict[str, Any] = Field(default_factory=dict)
    ending_policy: Dict[str, Any] = Field(default_factory=dict)
    source_rule_coverage: Dict[str, Any] = Field(default_factory=dict)
    few_shot_examples: List[Any] = Field(default_factory=list)
    few_shot_selection: Dict[str, Any] = Field(default_factory=dict)
    prohibited_patterns: List[Any] = Field(default_factory=list)
    context_usage_policy: Dict[str, Any] = Field(default_factory=dict)
    fallback_behavior: Dict[str, Any] = Field(default_factory=dict)
    emotional_dialogue: Dict[str, Any] = Field(default_factory=dict)
    not_fixed_response: bool
    not_keyword_matching: bool


class ResidentCompatibilityProjectionV03(V03BaseModel):
    resident_id: str
    name: str
    role: str
    description: str
    disclosure: str
    dr_version: Literal["0.1", "0.3"] = DR_VERSION_V0_3
    template_type: str


class LatticeStateSchemaV03(V03BaseModel):
    resident_id: str
    emotion: str
    energy: float
    attention: str
    motion: str
    voice_state: str
    particle_density: float
    color_palette: List[str] = Field(default_factory=list)
    focus_target: str


class MultiResidentLatticeStateV03(V03BaseModel):
    resident_ids: List[str] = Field(default_factory=list)
    states: List[Dict[str, Any]] = Field(default_factory=list)


class LegacyVisualStateV03(V03BaseModel):
    state: Optional[str] = None
    color: Optional[str] = None


class LegacyBlueprintV03(V03BaseModel):
    resident: ResidentCompatibilityProjectionV03
    layers: List[DRLayerSnapshotV03] = Field(default_factory=list)
    slots: List[DRSlotV03] = Field(default_factory=list)
    layer_contexts: Dict[str, Any] = Field(default_factory=dict)
    runtime_requirements: Dict[str, Any] = Field(default_factory=dict)
    memory_config: Dict[str, Any] = Field(default_factory=dict)
    memory_namespace: str = "default"
    memory_policy: Dict[str, Any] = Field(default_factory=dict)
    memory_storage_requirement: Dict[str, Any] = Field(default_factory=dict)
    voice_config: Dict[str, Any] = Field(default_factory=dict)
    tts_provider_config: Dict[str, Any] = Field(default_factory=dict)
    voice_profile_config: Dict[str, Any] = Field(default_factory=dict)
    voice_lattice_sync_policy: Dict[str, Any] = Field(default_factory=dict)
    speech_event_schema: Dict[str, Any] = Field(default_factory=dict)
    lattice_config: Dict[str, Any] = Field(default_factory=dict)
    lattice_state_schema: Dict[str, Any] = Field(default_factory=dict)
    multi_resident_lattice_state: Dict[str, Any] = Field(
        default_factory=dict
    )
    resident_instance: Dict[str, Any] = Field(default_factory=dict)
    safety_policy: Dict[str, Any] = Field(default_factory=dict)
    compatibility_status: Optional[CompatibilitySurfaceStatusV03] = None


class DRPayloadV03(V03BaseModel):
    resident_identity: ResidentIdentityV03
    resident_blueprint: ResidentBlueprintV03
    layers_snapshot: List[DRLayerSnapshotV03] = Field(
        alias="13_layers_snapshot"
    )
    modules: List[DRModuleV03]
    nodes: List[DRCanvasNodeV03] = Field(default_factory=list)
    slots: List[DRSlotV03]
    edges: List[DRModuleEdgeV03] = Field(default_factory=list)
    runtime_requirements: RuntimeRequirementsV03
    provider_requirements: Dict[str, ProviderRequirementV03] = Field(
        default_factory=dict
    )
    memory_policy: MemoryPolicyV03
    memory_config: MemoryConfigV03
    lattice_config: LatticeConfigV03
    voice_config: VoiceConfigV03
    screen_capability_declaration: ScreenCapabilityDeclarationV03
    safety_policy: SafetyPolicyV03
    audit_policy: AuditPolicyV03
    runtime_plan: RuntimePlanV03
    fallback_routes: List[FallbackRouteV03] = Field(default_factory=list)
    graph_snapshot: GraphSnapshotV03
    node_snapshot: List[DRCanvasNodeV03] = Field(default_factory=list)
    raw_layers: List[DRLayerSnapshotV03] = Field(default_factory=list)
    behavior: Optional[BehaviorProjectionV03] = None
    behavior_policy: Optional[BehaviorPolicyV03] = None
    expression: Optional[ExpressionProjectionV03] = None
    relationship: Optional[RelationshipProjectionV03] = None
    runtime_dialogue_projection: Optional[RuntimeDialogueProjectionV03] = None
    relationship_progression_projection: Optional[
        RelationshipProgressionProjectionV03
    ] = None
    narrative_memory_projection: Optional[
        NarrativeMemoryProjectionV03
    ] = None
    abstract_bust_blueprint: Optional[AbstractBustBlueprint] = None

    @model_validator(mode="after")
    def _abstract_bust_projection_is_read_only(self) -> "DRPayloadV03":
        if self.abstract_bust_blueprint is None:
            return self

        particle_modules = [
            module
            for module in self.modules
            if module.module_id == "particle_avatar"
        ]
        if len(particle_modules) != 1:
            raise ValueError(
                "abstract_bust_blueprint requires exactly one "
                "payload.modules particle_avatar authority"
            )
        module_blueprint = particle_modules[0].config.get(
            "abstract_bust_blueprint"
        )
        if (
            module_blueprint
            != self.abstract_bust_blueprint.model_dump(mode="json")
        ):
            raise ValueError(
                "abstract_bust_blueprint is a read-only projection and must "
                "equal payload.modules particle_avatar config"
            )
        return self


class DRDocumentV03(V03BaseModel):
    file_type: Literal["digital_resident"]
    dr_version: Literal["0.3"]
    dr_schema_version: Literal["0.3.0"]
    protocol_version: Literal["0.4.0"]
    schema_version: Literal["0.4.0"]
    revision: str = "1"
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    not_executable: Literal[True]
    manifest: DRManifestV03
    payload: DRPayloadV03
    visual_expression_mapping: Optional[VisualExpressionMappingV03] = None
    compile_info: CompileInfoV03
    audit_report: Optional[AuditReportV03] = None
    audit: Optional[AuditReportV03] = None
    # Frozen v0.3 compatibility projections. They are read-only aliases and
    # never replace the authoritative values under payload.
    resident: Optional[ResidentCompatibilityProjectionV03] = None
    layers: Optional[List[DRLayerSnapshotV03]] = None
    modules: Optional[List[DRModuleV03]] = None
    slots: Optional[List[DRSlotV03]] = None
    runtime_requirements: Optional[RuntimeRequirementsV03] = None
    memory_config: Optional[MemoryConfigV03] = None
    memory_namespace: Optional[str] = None
    memory_policy: Optional[MemoryPolicyV03] = None
    lattice_config: Optional[LatticeConfigV03] = None
    lattice_state_schema: Optional[LatticeStateSchemaV03] = None
    multi_resident_lattice_state: Optional[
        MultiResidentLatticeStateV03
    ] = None
    voice_config: Optional[VoiceConfigV03] = None
    voice_state: Optional[str] = None
    visual_state: Optional[LegacyVisualStateV03] = None
    safety_policy: Optional[SafetyPolicyV03] = None
    screen_capability_declaration: Optional[
        ScreenCapabilityDeclarationV03
    ] = None
    legacy_blueprint: Optional[LegacyBlueprintV03] = None
    # Backward-compatible legacy aliases for consumers that still inspect the
    # prior compile envelope. These remain declarative only.
    legacy_compiled_dr: Optional[Dict[str, Any]] = None
    legacy_dr_payload: Optional[Dict[str, Any]] = None

    @model_validator(mode="after")
    def _compatibility_projections_are_read_only(self) -> "DRDocumentV03":
        if self.audit_report is None and self.audit is None:
            raise ValueError("audit_report or audit is required")

        resident_ids = {
            self.manifest.resident_id,
            self.payload.resident_identity.resident_id,
            self.payload.resident_blueprint.resident_id,
        }
        resident_names = {
            self.manifest.resident_name,
            self.payload.resident_identity.name,
            self.payload.resident_blueprint.resident_name,
        }
        if self.resident is not None:
            resident_ids.add(self.resident.resident_id)
            resident_names.add(self.resident.name)
        if self.legacy_blueprint is not None:
            resident_ids.add(
                self.legacy_blueprint.resident.resident_id
            )
            resident_names.add(self.legacy_blueprint.resident.name)
        if len(resident_ids) != 1 or len(resident_names) != 1:
            raise ValueError(
                "resident compatibility projections must match the "
                "authoritative payload identity and manifest"
            )

        projection_pairs = (
            ("layers", self.layers, self.payload.layers_snapshot),
            ("modules", self.modules, self.payload.modules),
            ("slots", self.slots, self.payload.slots),
            (
                "runtime_requirements",
                self.runtime_requirements,
                self.payload.runtime_requirements,
            ),
            ("memory_config", self.memory_config, self.payload.memory_config),
            ("memory_policy", self.memory_policy, self.payload.memory_policy),
            ("lattice_config", self.lattice_config, self.payload.lattice_config),
            ("voice_config", self.voice_config, self.payload.voice_config),
            ("safety_policy", self.safety_policy, self.payload.safety_policy),
            (
                "screen_capability_declaration",
                self.screen_capability_declaration,
                self.payload.screen_capability_declaration,
            ),
        )
        for path, root_value, payload_value in projection_pairs:
            if root_value is not None and root_value != payload_value:
                raise ValueError(
                    f"{path} is a read-only compatibility projection and "
                    f"must equal payload.{path}"
                )
        if (
            self.memory_namespace is not None
            and self.memory_namespace != self.payload.memory_policy.namespace
        ):
            raise ValueError(
                "memory_namespace must equal payload.memory_policy.namespace"
            )
        if (
            self.audit_report is not None
            and self.audit is not None
            and self.audit_report != self.audit
        ):
            raise ValueError(
                "audit is a read-only compatibility projection and must "
                "equal audit_report"
            )
        return self

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
