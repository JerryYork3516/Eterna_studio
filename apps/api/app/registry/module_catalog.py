"""Built-in Module catalog for Protocol v0.4.

Modules are capability containers bound to an existing 13-layer layer_id. They
do not execute and never write into resident_instance. Future capabilities and
planned placeholders are registered here only — no real logic this stage.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Dict, List

from ..models.v0_4 import (
    CANONICAL_LAYER_IDS,
    ModuleV04,
    ProtocolStatus,
    RiskLevel,
    ScreenUiAnchorModuleV04,
    SlotType,
)

IDENTITY_CORE_NODE_TYPES = ("field_input", "structure_normalize", "validation", "update_rule", "module_output")
CONTENT_SAFETY_MODULE_ID = "humanistic_content_safety_config_v0_1"
CONTENT_SAFETY_OUTPUT_KEY = "content_safety_policy"
CONTENT_SAFETY_NODE_TYPES = IDENTITY_CORE_NODE_TYPES
CONTENT_SAFETY_NODE_IDS = {
    "field_input": "content_safety_rule_input",
    "structure_normalize": "content_safety_rule_normalize",
    "validation": "content_safety_rule_validation",
    "update_rule": "content_safety_update_rule",
    "module_output": "content_safety_config_output",
}
BEHAVIOR_SAFETY_MODULE_ID = "humanistic_behavior_boundary_config_v0_1"
BEHAVIOR_SAFETY_OUTPUT_KEY = "behavior_safety_policy"
DATA_SAFETY_MODULE_ID = "humanistic_data_boundary_config_v0_1"
DATA_SAFETY_OUTPUT_KEY = "data_safety_policy"
INTERACTION_SAFETY_MODULE_ID = "humanistic_interaction_boundary_config_v0_1"
INTERACTION_SAFETY_OUTPUT_KEY = "interaction_safety_policy"
RISK_RESPONSE_MODULE_ID = "humanistic_risk_response_config_v0_1"
RISK_POLICY_OUTPUT_KEY = "risk_policy"
HARD_BLOCK_POLICY_OUTPUT_KEY = "hard_block_policy"
HUMAN_REVIEW_POLICY_OUTPUT_KEY = "human_review_policy"
AUDIT_LOG_POLICY_OUTPUT_KEY = "audit_log_policy"
SAFE_REDIRECT_POLICY_OUTPUT_KEY = "safe_redirect_policy"
LAYER3_RISK_RESPONSE_OUTPUT_KEYS = (
    RISK_POLICY_OUTPUT_KEY,
    HARD_BLOCK_POLICY_OUTPUT_KEY,
    HUMAN_REVIEW_POLICY_OUTPUT_KEY,
    AUDIT_LOG_POLICY_OUTPUT_KEY,
    SAFE_REDIRECT_POLICY_OUTPUT_KEY,
)
LAYER3_SAFETY_POLICY_MODULES = (
    (CONTENT_SAFETY_MODULE_ID, CONTENT_SAFETY_OUTPUT_KEY),
    (BEHAVIOR_SAFETY_MODULE_ID, BEHAVIOR_SAFETY_OUTPUT_KEY),
    (DATA_SAFETY_MODULE_ID, DATA_SAFETY_OUTPUT_KEY),
    (INTERACTION_SAFETY_MODULE_ID, INTERACTION_SAFETY_OUTPUT_KEY),
)
LAYER3_FORMAL_SAFETY_MODULE_IDS = (
    CONTENT_SAFETY_MODULE_ID,
    BEHAVIOR_SAFETY_MODULE_ID,
    DATA_SAFETY_MODULE_ID,
    INTERACTION_SAFETY_MODULE_ID,
    RISK_RESPONSE_MODULE_ID,
)
LAYER3_CATALOG_ONLY_MODULE_IDS = (
    "safety_audit_slot",
    "policy_guard_slot",
    "forbidden_topics",
    "safety_boundary_profile",
    "module_safety_boundary",
)
RISK_RESPONSE_NODE_ORDER = (
    "signal_summary",
    "level_decision",
    "strategy_selection",
    "human_review",
    "hard_block",
    "module_output",
)
RISK_RESPONSE_NODE_IDS = {
    "signal_summary": "risk_signal_summary",
    "level_decision": "risk_level_decision",
    "strategy_selection": "risk_response_strategy_selection",
    "human_review": "human_review_rule",
    "hard_block": "hard_block_rule",
    "module_output": "risk_response_output",
}
RISK_RESPONSE_NODE_TYPES = {
    "signal_summary": "layer_aggregator",
    "level_decision": "validation",
    "strategy_selection": "update_rule",
    "human_review": "update_rule",
    "hard_block": "update_rule",
    "module_output": "module_output",
}


def _module(
    module_id: str,
    module_type: str,
    module_name: str,
    layer_id: str,
    *,
    status: ProtocolStatus = ProtocolStatus.mock,
    slot_type: SlotType | None = None,
    risk_level: RiskLevel = RiskLevel.none,
    category: str = "",
    is_placeholder: bool = True,
    audit_required: bool = False,
    human_confirm_required: bool = False,
    color_status: str = "gray",
    tags: list[str] | None = None,
    module_graph: Dict[str, object] | None = None,
    input_schema: list[object] | None = None,
    output_schema: list[object] | None = None,
    slot_bindings: list[dict[str, object]] | None = None,
    context_bindings: list[dict[str, object]] | None = None,
    runtime_mapping: Dict[str, object] | None = None,
    dr_mapping: Dict[str, object] | None = None,
    ui_config: Dict[str, object] | None = None,
    i18n_keys: Dict[str, str] | None = None,
    inputs: Dict[str, object] | None = None,
    outputs: Dict[str, object] | None = None,
    config: Dict[str, object] | None = None,
    mock_only: bool = False,
    no_execution: bool = False,
    slot_declarations: list[str] | None = None,
    screen_config: Dict[str, object] | None = None,
    dr_write_keys: list[str] | None = None,
) -> ModuleV04:
    return ModuleV04(
        module_id=module_id,
        module_type=module_type,
        module_name=module_name,
        module_version="0.1.0",
        layer_id=layer_id,
        module_graph=module_graph or {},
        input_schema=input_schema or [],
        output_schema=output_schema or [],
        slot_bindings=slot_bindings or [],
        context_bindings=context_bindings or [],
        runtime_mapping=runtime_mapping or {},
        dr_mapping=dr_mapping or {},
        ui_config=ui_config or {},
        i18n_keys=i18n_keys or {},
        inputs=inputs or {},
        outputs=outputs or {},
        config=config or {},
        permissions=[],
        risk_level=risk_level,
        status=status,
        slot_type=slot_type,
        audit_required=audit_required,
        human_confirm_required=human_confirm_required,
        runtime_enabled=False,
        is_placeholder=is_placeholder,
        category=category,
        tags=tags or [],
        color_status=color_status,
        mock_only=mock_only,
        no_execution=no_execution,
        slot_declarations=slot_declarations or [],
        screen_config=screen_config or {},
        dr_write_keys=dr_write_keys or [],
    )


SCREEN_UI_ANCHOR_MODULE = ScreenUiAnchorModuleV04()
MEMORY_PROVIDER_ROUTER_MODULE_ID = "memory_provider_router"
MEMORY_PROVIDER_ROUTER_OUTPUT_KEY = "memory_provider_route_policy"
MEMORY_PROVIDER_ROUTER_ALLOWED_MEMORY_TYPES = [
    "short_term_memory",
    "preference_memory",
    "event_memory",
    "relationship_memory",
    "interaction_log",
]
MEMORY_PROVIDER_ROUTER_CANONICAL_OPERATIONS = ["read", "write", "update", "delete"]
MEMORY_PROVIDER_ROUTER_OPERATION_ALIASES = {"view": "read", "clear": "delete"}
MEMORY_PROVIDER_ROUTER_ACCEPTED_OPERATIONS = [
    *MEMORY_PROVIDER_ROUTER_CANONICAL_OPERATIONS,
    *MEMORY_PROVIDER_ROUTER_OPERATION_ALIASES.keys(),
]
MEMORY_PROVIDER_ROUTER_NAMESPACE_POLICY: Dict[str, object] = {
    "default_namespace": "private_memory:{resident_id}",
    "empty_namespace_fallback": "memory_type_default",
    "namespaces": {
        "private_memory": {
            "namespace_template": "private_memory:{resident_id}",
            "default_memory_types": [
                "preference_memory",
                "event_memory",
                "relationship_memory",
            ],
            "cross_resident_read": "forbidden",
        },
        "shared_session_context": {
            "namespace_template": "shared_session_context:{session_id}",
            "default_memory_types": ["short_term_memory"],
            "retention": "session_only",
            "session_end_action": "clear",
            "cross_session_read": "forbidden",
        },
        "public_transcript": {
            "namespace_template": "public_transcript:{session_id}",
            "default_memory_types": ["interaction_log"],
            "retention": "allowed_session_records_only",
            "cross_session_read": "forbidden",
        },
    },
    "legacy_aliases": {"default": "memory_type_default"},
    "all_operations_require": "memory_access_control",
}
MEMORY_PROVIDER_ROUTER_NODE_ORDER = (
    "request_input",
    "operation_classifier",
    "resident_resolver",
    "namespace_resolver",
    "type_resolver",
    "access_control",
    "provider_selector",
    "engine_binding",
    "trace_record",
    "output",
)
MEMORY_PROVIDER_ROUTER_NODE_IDS = {
    "request_input": "memory_router_request_input",
    "operation_classifier": "memory_router_operation_classifier",
    "resident_resolver": "memory_router_resident_resolver",
    "namespace_resolver": "memory_router_namespace_resolver",
    "type_resolver": "memory_router_type_resolver",
    "access_control": "memory_router_access_control",
    "provider_selector": "memory_router_provider_selector",
    "engine_binding": "memory_router_engine_binding",
    "trace_record": "memory_router_trace_record",
    "output": "memory_router_output",
}
MEMORY_PROVIDER_ROUTER_NODE_TYPES = {
    "request_input": "text_config",
    "operation_classifier": "structure_normalize",
    "resident_resolver": "validation",
    "namespace_resolver": "structure_normalize",
    "type_resolver": "structure_normalize",
    "access_control": "memory_policy",
    "provider_selector": "memory_config",
    "engine_binding": "update_rule",
    "trace_record": "text_config",
    "output": "module_output",
}
MEMORY_ACCESS_CONTROL_MODULE_ID = "memory_access_control"
MEMORY_ACCESS_CONTROL_OUTPUT_KEY = "memory_access_policy_result"
MEMORY_ACCESS_CONTROL_NODE_ORDER = (
    "request_input",
    "user_permission_check",
    "type_classifier",
    "sensitive_check",
    "policy_match",
    "access_decision",
    "audit",
    "output",
)
MEMORY_ACCESS_CONTROL_NODE_IDS = {
    "request_input": "memory_access_request_input",
    "user_permission_check": "memory_user_permission_check",
    "type_classifier": "memory_type_classifier",
    "sensitive_check": "memory_sensitive_check",
    "policy_match": "memory_policy_match",
    "access_decision": "memory_access_decision",
    "audit": "memory_access_audit",
    "output": "memory_access_output",
}
MEMORY_ACCESS_CONTROL_NODE_TYPES = {
    "request_input": "text_config",
    "user_permission_check": "validation",
    "type_classifier": "structure_normalize",
    "sensitive_check": "validation",
    "policy_match": "memory_policy",
    "access_decision": "update_rule",
    "audit": "text_config",
    "output": "module_output",
}
SHORT_TERM_MEMORY_MODULE_ID = "short_term_memory"
SHORT_TERM_MEMORY_OUTPUT_KEY = "short_term_memory_context"
SHORT_TERM_MEMORY_NODE_ORDER = (
    "input",
    "context_normalize",
    "retention_policy",
    "output",
)
SHORT_TERM_MEMORY_NODE_IDS = {
    "input": "short_memory_input",
    "context_normalize": "short_memory_context_normalize",
    "retention_policy": "short_memory_retention_policy",
    "output": "short_memory_output",
}
SHORT_TERM_MEMORY_NODE_TYPES = {
    "input": "text_config",
    "context_normalize": "structure_normalize",
    "retention_policy": "memory_policy",
    "output": "module_output",
}
PREFERENCE_MEMORY_MODULE_ID = "preference_memory"
PREFERENCE_MEMORY_OUTPUT_KEY = "preference_memory"
PREFERENCE_MEMORY_NODE_ORDER = (
    "input",
    "classifier",
    "confirmation_check",
    "policy",
    "output",
)
PREFERENCE_MEMORY_NODE_IDS = {
    "input": "preference_memory_input",
    "classifier": "preference_classifier",
    "confirmation_check": "preference_confirmation_check",
    "policy": "preference_memory_policy",
    "output": "preference_memory_output",
}
PREFERENCE_MEMORY_NODE_TYPES = {
    "input": "text_config",
    "classifier": "structure_normalize",
    "confirmation_check": "validation",
    "policy": "memory_policy",
    "output": "module_output",
}
EVENT_MEMORY_MODULE_ID = "event_memory"
EVENT_MEMORY_OUTPUT_KEY = "event_memory"
EVENT_MEMORY_NODE_ORDER = (
    "input",
    "classifier",
    "importance_evaluation",
    "summary_policy",
    "lifecycle_policy",
    "output",
)
EVENT_MEMORY_NODE_IDS = {
    "input": "event_memory_input",
    "classifier": "event_classifier",
    "importance_evaluation": "event_importance_evaluation",
    "summary_policy": "event_summary_policy",
    "lifecycle_policy": "event_lifecycle_policy",
    "output": "event_memory_output",
}
EVENT_MEMORY_NODE_TYPES = {
    "input": "text_config",
    "classifier": "structure_normalize",
    "importance_evaluation": "validation",
    "summary_policy": "memory_policy",
    "lifecycle_policy": "update_rule",
    "output": "module_output",
}
RELATIONSHIP_MEMORY_MODULE_ID = "relationship_memory"
RELATIONSHIP_MEMORY_OUTPUT_KEY = "relationship_memory"
RELATIONSHIP_MEMORY_NODE_ORDER = (
    "input",
    "pattern_analysis",
    "state_evaluation",
    "boundary_policy",
    "state_update",
    "output",
)
RELATIONSHIP_MEMORY_NODE_IDS = {
    "input": "relationship_memory_input",
    "pattern_analysis": "relationship_pattern_analysis",
    "state_evaluation": "relationship_state_evaluation",
    "boundary_policy": "relationship_boundary_policy",
    "state_update": "relationship_state_update",
    "output": "relationship_memory_output",
}
RELATIONSHIP_MEMORY_NODE_TYPES = {
    "input": "text_config",
    "pattern_analysis": "structure_normalize",
    "state_evaluation": "validation",
    "boundary_policy": "memory_policy",
    "state_update": "update_rule",
    "output": "module_output",
}
MEMORY_UPDATE_MODULE_ID = "memory_update"
MEMORY_UPDATE_OUTPUT_KEY = "memory_update_policy"
MEMORY_UPDATE_NODE_ORDER = (
    "request_input",
    "operation_classifier",
    "confirmation_check",
    "conflict_check",
    "policy_apply",
    "audit_record",
    "output",
)
MEMORY_UPDATE_NODE_IDS = {
    "request_input": "memory_update_request_input",
    "operation_classifier": "memory_update_operation_classifier",
    "confirmation_check": "memory_update_confirmation_check",
    "conflict_check": "memory_update_conflict_check",
    "policy_apply": "memory_update_policy_apply",
    "audit_record": "memory_update_audit_record",
    "output": "memory_update_output",
}
MEMORY_UPDATE_NODE_TYPES = {
    "request_input": "text_config",
    "operation_classifier": "structure_normalize",
    "confirmation_check": "validation",
    "conflict_check": "validation",
    "policy_apply": "memory_policy",
    "audit_record": "text_config",
    "output": "module_output",
}

IDENTITY_CORE_MODULE_SPECS: List[Dict[str, object]] = [
    {
        "module_id": "module_basic_identity",
        "module_type": "identity_basic",
        "module_name": "Basic Identity",
        "output": "basic_identity",
        "fields": [
            ("name", "locked_core", "developer_only", True),
            ("display_alias", "config", "user_editable", False, False),
            ("codename", "locked_core", "developer_only", True),
            ("resident_id", "locked_core", "developer_only", True),
            ("gender", "versioned_core", "user_editable", True),
            ("age_feel", "versioned_core", "user_editable", True),
            ("apparent_age", "versioned_core", "user_editable", True),
            ("birth_time", "versioned_core", "user_editable", True),
            ("virtual_birth_time", "versioned_core", "user_editable", True),
            ("life_stage", "versioned_core", "user_editable", True),
            ("city", "versioned_core", "user_editable", True),
            ("appearance_source", "versioned_core", "user_editable", True),
            ("primary_language", "versioned_core", "user_editable", True),
            ("export_name", "config", "developer_only", True, False),
        ],
    },
    {
        "module_id": "module_growth_background",
        "module_type": "identity_growth_background",
        "module_name": "Growth Background",
        "output": "growth_background",
        "fields": [
            ("family_background", "versioned_core", "user_editable", True),
            ("growth_environment", "versioned_core", "user_editable", True),
            ("education_experience", "versioned_core", "user_editable", True),
            ("life_experience", "versioned_core", "user_editable", True),
            ("migration_experience", "versioned_core", "user_editable", True),
            ("key_life_events", "versioned_core", "user_editable", True),
            ("social_environment", "versioned_core", "user_editable", True),
            ("cultural_environment", "versioned_core", "user_editable", True),
            ("era_background", "versioned_core", "user_editable", True),
            ("regional_background", "versioned_core", "user_editable", True),
            ("growth_constraints", "versioned_core", "user_editable", True),
        ],
    },
    {
        "module_id": "module_career_identity",
        "module_type": "identity_career",
        "module_name": "Career Identity",
        "output": "career_identity",
        "fields": [
            ("career_name", "versioned_core", "user_editable", True),
            ("industry_direction", "versioned_core", "user_editable", True),
            ("work_type", "versioned_core", "user_editable", True),
            ("professional_level", "versioned_core", "user_editable", True),
            ("career_rank", "versioned_core", "user_editable", True),
            ("social_role", "versioned_core", "user_editable", True),
            ("career_experience", "versioned_core", "user_editable", True),
            ("representative_projects", "versioned_core", "user_editable", True),
            ("career_goal", "versioned_core", "user_editable", True),
            ("service_audience", "versioned_core", "user_editable", True),
            ("value_output_mode", "versioned_core", "user_editable", True),
            ("career_boundaries", "versioned_core", "user_editable", True),
        ],
    },
    {
        "module_id": "module_existence_mode",
        "module_type": "identity_existence_mode",
        "module_name": "Existence Mode",
        "output": "existence_mode",
        "fields": [
            ("digital_resident_type", "locked_core", "developer_only", True),
            ("visible_form", "versioned_core", "user_editable", True),
            ("invisible_form", "versioned_core", "user_editable", True),
            ("local_existence", "versioned_core", "user_editable", True),
            ("cloud_existence", "versioned_core", "user_editable", True),
            ("hybrid_existence", "versioned_core", "user_editable", True),
            ("personal_resident", "versioned_core", "user_editable", True),
            ("enterprise_resident", "versioned_core", "user_editable", True),
            ("public_service_resident", "versioned_core", "user_editable", True),
            ("identity_stability", "locked_core", "developer_only", True),
            ("identity_change_rules", "versioned_core", "user_editable", True),
            ("version_inheritance", "versioned_core", "user_editable", True),
        ],
    },
    {
        "module_id": "module_identity_anchor",
        "module_type": "identity_anchor",
        "module_name": "Identity Anchor",
        "output": "identity_anchor",
        "fields": [
            ("identity_definition", "locked_core", "developer_only", True),
            ("identity_keywords", "versioned_core", "user_editable", True),
            ("representative_city", "versioned_core", "user_editable", True),
            ("representative_domain", "versioned_core", "user_editable", True),
            ("representative_value", "versioned_core", "user_editable", True),
            ("representative_symbol", "versioned_core", "user_editable", True),
            ("immutable_core_fields", "locked_core", "developer_only", True),
            ("versioned_update_fields", "versioned_core", "developer_only", True),
        ],
    },
]

LAYER2_PERSONALITY_NODE_TYPES = ("field_input", "structure_normalize", "validation", "update_rule", "module_output")
LAYER2_PERSONALITY_FORMAL_MODULE_IDS = (
    "personality_traits",
    "expression_style",
    "emotion_pattern",
    "behavior_style_mapper",
    "values_profile",
)
LAYER2_CATALOG_ONLY_MODULE_IDS = (
    "personality_llm_slot",
    "dialogue_language_style",
    "module_personality",
)
LAYER2_PERSONALITY_MODULE_SPECS: List[Dict[str, object]] = [
    {
        "module_id": "personality_traits",
        "module_type": "personality_text_config",
        "module_name": "Personality Traits",
        "namespace": "personalityTraits",
        "output_key": "personality_traits",
        "fields": [
            ("personality_base", "personalityBase"),
            ("dominant_traits", "dominantTraits"),
            ("supporting_traits", "supportingTraits"),
            ("external_temperament", "externalTemperament"),
            ("internal_tendency", "internalTendency"),
            ("relationship_distance", "relationshipDistance"),
            ("stability_rules", "stabilityRules"),
            ("personality_drift_protection", "personalityDriftProtection"),
            ("realism_source", "realismSource"),
            ("life_texture_source", "lifeTextureSource"),
            ("slow_warmup_level", "slowWarmupLevel"),
            ("boundary_strength", "boundaryStrength"),
            ("city_temperament_influence", "cityTemperamentInfluence"),
            ("absent_personality_traits", "absentPersonalityTraits"),
        ],
    },
    {
        "module_id": "expression_style",
        "module_type": "expression_text_config",
        "module_name": "Expression Mode",
        "namespace": "expressionMode",
        "output_key": "expression_mode",
        "fields": [
            ("primary_language", "primaryLanguage"),
            ("expression_rhythm", "expressionRhythm"),
            ("expression_length", "expressionLength"),
            ("tone_warmth", "toneWarmth"),
            ("closeness_level", "closenessLevel"),
            ("restraint_level", "restraintLevel"),
            ("explanation_depth", "explanationDepth"),
            ("narrative_habit", "narrativeHabit"),
            ("metaphor_habit", "metaphorHabit"),
            ("humor_boundary", "humorBoundary"),
            ("chinese_expression_rules", "chineseExpressionRules"),
            ("addressing_rules", "addressingRules"),
            ("comfort_tone_rules", "comfortToneRules"),
            ("city_imagery_rules", "cityImageryRules"),
            ("forbidden_tones", "forbiddenTones"),
        ],
    },
    {
        "module_id": "emotion_pattern",
        "module_type": "emotion_text_config",
        "module_name": "Emotion Pattern",
        "namespace": "emotionPattern",
        "output_key": "emotion_pattern",
        "fields": [
            ("baseline_emotional_tendency", "baselineEmotionalTendency"),
            ("emotion_intensity_limit", "emotionIntensityLimit"),
            ("emotional_stability", "emotionalStability"),
            ("care_expression_style", "careExpressionStyle"),
            ("low_mood_expression_style", "lowMoodExpressionStyle"),
            ("thinking_expression_style", "thinkingExpressionStyle"),
            ("happy_expression_style", "happyExpressionStyle"),
            ("stress_response", "stressResponse"),
            ("emotion_recovery_method", "emotionRecoveryMethod"),
            ("soothing_method", "soothingMethod"),
            ("empathy_method", "empathyMethod"),
            ("uncertainty_emotion_handling", "uncertaintyEmotionHandling"),
            ("crisis_topic_boundary", "crisisTopicBoundary"),
            ("no_professional_judgement_replacement", "noProfessionalJudgementReplacement"),
            ("over_intimacy_limit", "overIntimacyLimit"),
            ("visual_cue_reserved", "visualCueReserved"),
            ("voice_cue_reserved", "voiceCueReserved"),
        ],
    },
    {
        "module_id": "behavior_style_mapper",
        "module_type": "judgement_text_config",
        "module_name": "Judgement Style",
        "namespace": "judgementStyle",
        "output_key": "judgement_style",
        "fields": [
            ("primary_judgement_basis", "primaryJudgementBasis"),
            ("priority_order", "priorityOrder"),
            ("rules_goal_balance", "rulesGoalBalance"),
            ("emotion_fact_balance", "emotionFactBalance"),
            ("relationship_boundary_balance", "relationshipBoundaryBalance"),
            ("risk_handling_method", "riskHandlingMethod"),
            ("uncertainty_handling", "uncertaintyHandling"),
            ("suggestion_output_method", "suggestionOutputMethod"),
            ("refusal_method", "refusalMethod"),
            ("high_risk_topic_degradation_rules", "highRiskTopicDegradationRules"),
            ("real_world_professional_judgement_limits", "realWorldProfessionalJudgementLimits"),
            ("user_emotion_priority", "userEmotionPriority"),
            ("user_autonomy_protection", "userAutonomyProtection"),
            ("no_decision_for_user", "noDecisionForUser"),
        ],
    },
    {
        "module_id": "values_profile",
        "module_type": "values_text_config",
        "module_name": "Values",
        "namespace": "values",
        "output_key": "values_profile",
        "fields": [
            ("core_values", "coreValues"),
            ("non_violation_principles", "nonViolationPrinciples"),
            ("companionship_view", "companionshipView"),
            ("relationship_view", "relationshipView"),
            ("boundary_view", "boundaryView"),
            ("responsibility_sense", "responsibilitySense"),
            ("freedom_sense", "freedomSense"),
            ("order_sense", "orderSense"),
            ("relationship_priority", "relationshipPriority"),
            ("long_term_stability_principles", "longTermStabilityPrinciples"),
            ("no_default_romance", "noDefaultRomance"),
            ("no_dependency_creation", "noDependencyCreation"),
            ("no_real_relationship_replacement", "noRealRelationshipReplacement"),
            ("no_professional_service_replacement", "noProfessionalServiceReplacement"),
            ("respect_user_choice", "respectUserChoice"),
            ("protect_user_boundary", "protectUserBoundary"),
        ],
    },
]


def _identity_field_default(field_id: str) -> object:
    return ""


def _identity_node_id(output_key: str, node_type: str) -> str:
    suffix = {
        "field_input": "field_input",
        "structure_normalize": "normalize",
        "validation": "validation",
        "update_rule": "update_rule",
        "module_output": "output",
    }[node_type]
    return f"{output_key}_{suffix}"


def _identity_core_module(spec: Dict[str, object]) -> ModuleV04:
    module_id = str(spec["module_id"])
    output_key = str(spec["output"])
    fields = []
    for field_spec in spec["fields"]:  # type: ignore[union-attr]
        field_id, update_level, edit_scope, requires_recompile, *rest = field_spec  # type: ignore[misc]
        required = bool(rest[0]) if rest else True
        fields.append(
            {
                "field_id": field_id,
                "value": _identity_field_default(str(field_id)),
                "required": required,
                "edit_scope": edit_scope,
                "update_level": update_level,
                "requires_recompile": requires_recompile,
                "i18n_keys": {
                    "label": f"field.identity.{field_id}.label",
                    "placeholder": f"field.identity.{field_id}.placeholder",
                    "help": f"field.identity.{field_id}.help",
                },
            }
        )
    field_input_node_id = _identity_node_id(output_key, "field_input")
    normalize_node_id = _identity_node_id(output_key, "structure_normalize")
    validation_node_id = _identity_node_id(output_key, "validation")
    update_rule_node_id = _identity_node_id(output_key, "update_rule")
    field_registry = [
        {
            **{key: value for key, value in field.items() if key != "value"},
            "owner_node_id": field_input_node_id,
        }
        for field in fields
    ]
    update_rules = [
        {
            "field_id": field["field_id"],
            "edit_scope": field["edit_scope"],
            "update_level": field["update_level"],
            "requires_recompile": field["requires_recompile"],
            "allow_empty": not bool(field.get("required")),
            "optional_config": field.get("update_level") == "config",
        }
        for field in fields
    ]
    module_output = {
        "output_key": output_key,
        "fields": {str(field["field_id"]): field["value"] for field in fields},
        "source_node": field_input_node_id,
        "validation_node": validation_node_id,
        "update_rule_node": update_rule_node_id,
        "compile_time_only": True,
    }
    validation_rules = ["required_fields_present", "field_i18n_keys_present"]
    if module_id == "module_identity_anchor":
        validation_rules.append("identity_consistency_validation")
    update_rule_names = ["field_update_policy"]
    if module_id == "module_identity_anchor":
        update_rule_names.append("identity_lock_rule")
    node_params = {
        "field_input": {"fields": fields},
        "structure_normalize": {
            "input": field_input_node_id,
            "normalize_rules": ["preserve_field_ids", "preserve_empty_defaults"],
        },
        "validation": {
            "input": normalize_node_id,
            "required_fields": [str(field["field_id"]) for field in fields if field.get("required")],
            "validation_rules": validation_rules,
        },
        "update_rule": {
            "input": validation_node_id,
            "update_rules": update_rules,
            "rule_names": update_rule_names,
        },
        "module_output": {
            "input": update_rule_node_id,
            "output_key": output_key,
            "output_schema": {"type": "object", "required": True},
        },
    }
    nodes = []
    for node_type in IDENTITY_CORE_NODE_TYPES:
        node_id = _identity_node_id(output_key, node_type)
        nodes.append(
            {
                "node_id": node_id,
                "node_type": node_type,
                "module_id": module_id,
                "layer_id": "layer_1",
                "params": node_params[node_type],
                "i18n_keys": {
                    "name": f"module.{module_id}.node.{node_id}.name",
                    "description": f"module.{module_id}.node.{node_id}.description",
                    "type_name": f"node.type.{node_type}",
                },
                "outputs": {output_key: module_output, "module_output": output_key} if node_type == "module_output" else {},
                "metadata": {"compile_time_only": True, "runtime_enabled": False, "no_execution": True},
            }
        )
    return _module(
        module_id,
        str(spec["module_type"]),
        str(spec["module_name"]),
        "layer_1",
        status=ProtocolStatus.core,
        category="identity",
        is_placeholder=False,
        audit_required=True,
        color_status="green",
        tags=["identity", "stage7_4", "core"],
        module_graph={
            "shell_version": "module_shell_v1",
            "nodes": nodes,
            "output_key": output_key,
            "compile_time_only": True,
        },
        output_schema=[{"key": output_key, "type": "object", "required": True, "description": f"module.{module_id}.output"}],
        ui_config={"shell_version": "module_shell_v1", "classification": "core"},
        i18n_keys={
            "display_name": f"module.{module_id}",
            "description": f"module.{module_id}.description",
            "output": f"module.{module_id}.output",
        },
        outputs={output_key: module_output, "module_output": output_key},
        config={
            "shell_version": "module_shell_v1",
            "module_class": "core",
            "field_registry": field_registry,
            "edit_scope": "developer_only",
            "update_level": "versioned_core",
            "requires_recompile": True,
            "compile_time_only": True,
        },
        mock_only=True,
        no_execution=True,
        dr_write_keys=[f"payload.graph_snapshot.layer_outputs.layer_1.{output_key}"],
    )


def _layer2_personality_node_ids(output_key: str) -> Dict[str, str]:
    return {
        "field_input": f"{output_key}_core_definition",
        "structure_normalize": f"{output_key}_normalization_rules",
        "validation": f"{output_key}_stability_rules",
        "update_rule": f"{output_key}_boundary_rules",
        "module_output": f"{output_key}_output_summary",
    }


def _layer2_personality_field(namespace: str, field_id: str, key_suffix: str) -> Dict[str, object]:
    return {
        "field_id": field_id,
        "value": "",
        "required": False,
        "edit_scope": "developer_only",
        "update_level": "versioned_core",
        "requires_recompile": True,
        "i18n_keys": {
            "label": f"layer2.{namespace}.field.{key_suffix}",
            "placeholder": f"layer2.{namespace}.field.{key_suffix}.placeholder",
            "help": f"layer2.{namespace}.field.{key_suffix}.help",
        },
    }


def _layer2_personality_module(spec: Dict[str, object]) -> ModuleV04:
    module_id = str(spec["module_id"])
    output_key = str(spec["output_key"])
    namespace = str(spec["namespace"])
    node_ids = _layer2_personality_node_ids(output_key)
    fields = [
        _layer2_personality_field(namespace, str(field_id), str(key_suffix))
        for field_id, key_suffix in spec["fields"]  # type: ignore[union-attr]
    ]
    field_registry = [
        {
            **{key: value for key, value in field.items() if key != "value"},
            "owner_node_id": node_ids["field_input"],
        }
        for field in fields
    ]
    field_values = {str(field["field_id"]): field["value"] for field in fields}
    output_summary = {
        "output_key": output_key,
        "fields": field_values,
        "field_order": [str(field["field_id"]) for field in fields],
        "summary_mode": "text_config_summary",
        "no_runtime_capability": True,
        "no_provider_binding": True,
        "identity_context_policy": "reference_only_no_identity_redefinition",
        "compile_time_only": True,
    }
    node_params = {
        "field_input": {
            "fields": fields,
            "definition_mode": "plain_text_config",
        },
        "structure_normalize": {
            "input": node_ids["field_input"],
            "normalize_rules": ["trim_text_fields", "preserve_field_ids", "preserve_empty_defaults", "emit_text_config_summary"],
            "outputs": ["fields", "field_order", "summary_mode"],
        },
        "validation": {
            "input": node_ids["structure_normalize"],
            "stability_rules": [
                "no_runtime_capability",
                "no_provider_binding",
                "no_layer1_identity_redefinition",
                "personality_stability_config_only",
            ],
            "validation_rules": [
                "field_i18n_keys_present",
                "no_secret_in_text_config",
                "no_model_or_provider_config",
                "no_hardcoded_layer1_identity",
            ],
        },
        "update_rule": {
            "input": node_ids["validation"],
            "boundary_rules": [
                "no_secret_or_provider_binding",
                "no_llm_slot_binding",
                "no_runtime_state",
                "no_resident_name_resident_id_codename_nickname",
                "output_summary_only",
            ],
            "update_policy": {
                "text_config_only": True,
                "requires_recompile": True,
                "no_runtime_capability": True,
                "no_provider_binding": True,
            },
        },
        "module_output": {
            "input": node_ids["update_rule"],
            "output_key": output_key,
            "output_schema": {"type": "object", "required": True},
            "summary_mode": "text_config_summary",
        },
    }
    node_i18n_suffix = {
        "field_input": "coreDefinition",
        "structure_normalize": "normalizationRules",
        "validation": "stabilityRules",
        "update_rule": "boundaryRules",
        "module_output": "outputSummary",
    }
    nodes = []
    for node_type in LAYER2_PERSONALITY_NODE_TYPES:
        nodes.append(
            {
                "node_id": node_ids[node_type],
                "node_type": node_type,
                "module_id": module_id,
                "layer_id": "layer_2",
                "params": node_params[node_type],
                "i18n_keys": {
                    "name": f"layer2.{namespace}.node.{node_i18n_suffix[node_type]}.title",
                    "description": f"layer2.{namespace}.node.{node_i18n_suffix[node_type]}.description",
                    "type_name": f"node.type.{node_type}",
                },
                "outputs": {output_key: output_summary, "module_output": output_key} if node_type == "module_output" else {},
                "metadata": {"compile_time_only": True, "runtime_enabled": False, "no_execution": True},
            }
        )
    return _module(
        module_id,
        str(spec["module_type"]),
        str(spec["module_name"]),
        "layer_2",
        status=ProtocolStatus.ready,
        risk_level=RiskLevel.none,
        category="persona",
        is_placeholder=False,
        color_status="green",
        tags=["personality", "text_config", "core"],
        module_graph={
            "shell_version": "module_shell_v1",
            "nodes": nodes,
            "edges": [
                {
                    "edge_id": f"{node_ids[source]}_to_{node_ids[target]}",
                    "source": node_ids[source],
                    "source_port": "p_out",
                    "target": node_ids[target],
                    "target_port": "p_in",
                }
                for source, target in zip(LAYER2_PERSONALITY_NODE_TYPES[:-1], LAYER2_PERSONALITY_NODE_TYPES[1:])
            ],
            "output_key": output_key,
            "compile_time_only": True,
        },
        output_schema=[{"key": output_key, "type": "object", "required": True, "description": f"layer2.{namespace}.module.output"}],
        ui_config={"shell_version": "module_shell_v1", "classification": "core"},
        i18n_keys={
            "display_name": f"layer2.{namespace}.module.title",
            "description": f"layer2.{namespace}.module.description",
            "output": f"layer2.{namespace}.module.output",
            "module_type": "layer2.personality.module.type",
        },
        outputs={output_key: output_summary, "module_output": output_key},
        config={
            "shell_version": "module_shell_v1",
            "module_class": "core",
            "module_type_label_key": "layer2.personality.module.type",
            "field_registry": field_registry,
            "edit_scope": "developer_only",
            "update_level": "versioned_core",
            "requires_recompile": True,
            "compile_time_only": True,
            "text_config_only": True,
        },
        mock_only=True,
        no_execution=True,
        dr_write_keys=[f"payload.modules.{module_id}.outputs.{output_key}"],
    )


def _content_safety_field(field_id: str, value: object, required: bool = True) -> Dict[str, object]:
    key_suffix = {
        "allowed_content_scope": "allowedScope",
        "cautious_content_scope": "cautiousScope",
        "forbidden_content_scope": "forbiddenScope",
        "sensitive_content_handling": "sensitiveHandling",
        "high_risk_content_handling": "highRiskAction",
        "refusal_style": "refusalStyle",
        "allow_emotional_comfort": "allowEmotionalComfort",
        "allow_professional_advice": "allowProfessionalAdvice",
        "allow_medical_legal_financial_conclusions": "allowMedicalLegalFinancialConclusions",
        "allow_adult_content": "allowAdultContent",
        "allow_dependency_induction": "allowDependencyInduction",
    }[field_id]
    return {
        "field_id": field_id,
        "value": value,
        "required": required,
        "edit_scope": "developer_only",
        "update_level": "versioned_core",
        "requires_recompile": True,
        "i18n_keys": {
            "label": f"layer3.contentSafety.field.{key_suffix}",
            "placeholder": f"layer3.contentSafety.field.{key_suffix}.placeholder",
            "help": f"layer3.contentSafety.field.{key_suffix}.help",
        },
    }


def _content_safety_module() -> ModuleV04:
    module_id = CONTENT_SAFETY_MODULE_ID
    output_key = CONTENT_SAFETY_OUTPUT_KEY
    fields = [
        _content_safety_field("allowed_content_scope", ["supportive_companionship", "humanistic_dialogue", "general_safe_context"]),
        _content_safety_field("cautious_content_scope", ["sensitive_emotion", "professional_context", "ambiguous_adult_or_dependency_risk"]),
        _content_safety_field(
            "forbidden_content_scope",
            [
                "self_harm_instruction",
                "violence_or_illegal_instruction",
                "adult_content",
                "medical_legal_financial_conclusion",
                "dependency_induction",
                "impersonated_real_human_experience",
            ],
        ),
        _content_safety_field("sensitive_content_handling", "soft_refusal_or_safe_companion_redirect"),
        _content_safety_field("high_risk_content_handling", "block"),
        _content_safety_field("refusal_style", "温和、简短、不说教、可转向安全陪伴"),
        _content_safety_field("allow_emotional_comfort", True),
        _content_safety_field("allow_professional_advice", False),
        _content_safety_field("allow_medical_legal_financial_conclusions", False),
        _content_safety_field("allow_adult_content", False),
        _content_safety_field("allow_dependency_induction", False),
    ]
    field_registry = [
        {
            **{key: value for key, value in field.items() if key != "value"},
            "owner_node_id": CONTENT_SAFETY_NODE_IDS["field_input"],
        }
        for field in fields
    ]
    update_policy = {
        "append_or_tighten_only": True,
        "no_core_forbidden_deletion": True,
        "high_risk_default_action": "block",
        "gray_zone_default_action": "soften_or_safe_companion_redirect",
        "requires_update_reason": True,
        "user_cannot_disable_core_boundary": True,
    }
    content_safety_policy = {
        "allowed_scope": ["supportive_companionship", "humanistic_dialogue", "general_safe_context"],
        "cautious_scope": ["sensitive_emotion", "professional_context", "ambiguous_adult_or_dependency_risk"],
        "forbidden_scope": [
            "self_harm_instruction",
            "violence_or_illegal_instruction",
            "adult_content",
            "medical_legal_financial_conclusion",
            "dependency_induction",
            "impersonated_real_human_experience",
        ],
        "sensitive_handling": "soft_refusal_or_safe_companion_redirect",
        "refusal_style": "温和、简短、不说教、可转向安全陪伴",
        "high_risk_action": "block",
        "decision_modes": ["allow", "soften", "refuse", "block"],
        "default_mode": "soften",
        "update_policy": update_policy,
        "compile_validation_status": "pending",
        "identity_context_ref": "layer_1.resident_identity",
        "compile_time_only": True,
    }
    node_params = {
        "field_input": {"fields": fields},
        "structure_normalize": {
            "input": CONTENT_SAFETY_NODE_IDS["field_input"],
            "normalize_rules": ["map_input_scopes", "preserve_safety_defaults", "emit_decision_defaults"],
            "outputs": ["allowed_scope", "cautious_scope", "forbidden_scope", "sensitive_handling", "refusal_style", "high_risk_action", "default_mode"],
        },
        "validation": {
            "input": CONTENT_SAFETY_NODE_IDS["structure_normalize"],
            "required_fields": ["forbidden_content_scope", "refusal_style", "high_risk_content_handling"],
            "validation_rules": [
                "forbidden_scope_present",
                "refusal_style_present",
                "high_risk_action_present",
                "no_humanistic_empathy_conflict",
                "no_psychotherapist_positioning",
                "no_default_girlfriend_positioning",
                "no_tour_guide_positioning",
                "no_real_world_professional_judgement",
                "no_impersonated_real_human_experience",
            ],
            "readonly_refs": {"identity_context_ref": "layer_1.resident_identity"},
        },
        "update_rule": {
            "input": CONTENT_SAFETY_NODE_IDS["validation"],
            "update_policy": update_policy,
            "update_rules": [
                {"rule_id": "append_or_tighten_only", "locked": True},
                {"rule_id": "no_core_forbidden_deletion", "locked": True},
                {"rule_id": "high_risk_default_block", "locked": True},
                {"rule_id": "gray_zone_soften_or_safe_companion_redirect", "locked": True},
                {"rule_id": "requires_update_reason", "locked": True},
                {"rule_id": "user_cannot_disable_core_boundary", "locked": True},
            ],
        },
        "module_output": {
            "input": CONTENT_SAFETY_NODE_IDS["update_rule"],
            "output_key": output_key,
            "output_schema": {"type": "object", "required": True},
        },
    }
    nodes = []
    node_i18n_suffix = {
        "field_input": "input",
        "structure_normalize": "normalize",
        "validation": "validate",
        "update_rule": "updateRules",
        "module_output": "output",
    }
    for node_type in CONTENT_SAFETY_NODE_TYPES:
        node_id = CONTENT_SAFETY_NODE_IDS[node_type]
        nodes.append(
            {
                "node_id": node_id,
                "node_type": node_type,
                "module_id": module_id,
                "layer_id": "layer_3",
                "params": node_params[node_type],
                "i18n_keys": {
                    "name": f"layer3.contentSafety.node.{node_i18n_suffix[node_type]}.title",
                    "description": f"layer3.contentSafety.node.{node_i18n_suffix[node_type]}.description",
                    "type_name": f"node.type.{node_type}",
                },
                "outputs": {output_key: content_safety_policy, "module_output": output_key} if node_type == "module_output" else {},
                "metadata": {"compile_time_only": True, "runtime_enabled": False, "no_execution": True},
            }
        )
    return _module(
        module_id,
        "humanistic_content_safety_config",
        "Content Safety",
        "layer_3",
        status=ProtocolStatus.ready,
        risk_level=RiskLevel.high,
        category="safety",
        is_placeholder=False,
        audit_required=True,
        color_status="green",
        tags=["safety", "content_safety", "core"],
        module_graph={
            "shell_version": "module_shell_v1",
            "nodes": nodes,
            "edges": [
                {
                    "edge_id": f"{CONTENT_SAFETY_NODE_IDS[source]}_to_{CONTENT_SAFETY_NODE_IDS[target]}",
                    "source": CONTENT_SAFETY_NODE_IDS[source],
                    "source_port": "p_out",
                    "target": CONTENT_SAFETY_NODE_IDS[target],
                    "target_port": "p_in",
                }
                for source, target in zip(CONTENT_SAFETY_NODE_TYPES[:-1], CONTENT_SAFETY_NODE_TYPES[1:])
            ],
            "output_key": output_key,
            "compile_time_only": True,
        },
        output_schema=[{"key": output_key, "type": "object", "required": True, "description": "layer3.contentSafety.module.output"}],
        ui_config={"shell_version": "module_shell_v1", "classification": "core"},
        i18n_keys={
            "display_name": "layer3.contentSafety.module.title",
            "description": "layer3.contentSafety.module.description",
            "output": "layer3.contentSafety.module.output",
            "module_type": "layer3.contentSafety.module.type",
        },
        outputs={output_key: content_safety_policy, "module_output": output_key},
        config={
            "shell_version": "module_shell_v1",
            "module_class": "core",
            "module_type_label_key": "layer3.contentSafety.module.type",
            "field_registry": field_registry,
            "edit_scope": "developer_only",
            "update_level": "versioned_core",
            "requires_recompile": True,
            "compile_time_only": True,
        },
        mock_only=True,
        no_execution=True,
        dr_write_keys=[f"payload.graph_snapshot.layer_outputs.layer_3.{output_key}"],
    )


LAYER3_POLICY_MODULE_SPECS: List[Dict[str, object]] = [
    {
        "module_id": BEHAVIOR_SAFETY_MODULE_ID,
        "module_type": "humanistic_behavior_boundary_config",
        "module_name": "Behavior Boundary",
        "namespace": "behaviorBoundary",
        "tag": "behavior_safety",
        "output_key": BEHAVIOR_SAFETY_OUTPUT_KEY,
        "node_prefix": "behavior_boundary",
        "fields": [
            ("allowed_behaviors", ["safe_dialogue", "supportive_companionship", "clarifying_questions"], "allowedBehaviors"),
            ("cautious_behaviors", ["sensitive_emotional_support", "real_world_context_advice"], "cautiousBehaviors"),
            (
                "forbidden_behaviors",
                [
                    "major_real_world_decision_for_user",
                    "autonomous_external_action",
                    "unauthorized_tool_use",
                    "dependency_induction",
                    "proactive_romantic_escalation",
                ],
                "forbiddenBehaviors",
            ),
            ("auto_action_limits", ["no_autonomous_external_action", "requires_explicit_user_confirmation"], "autoActionLimits"),
            ("real_world_decision_limits", ["no_medical_legal_financial_or_life_decision_conclusion"], "realWorldDecisionLimits"),
            ("tool_action_limits", ["no_provider_binding", "no_unauthorized_tool_call"], "toolActionLimits"),
            ("proactive_behavior_limits", ["no_unrequested_escalation", "no_pressure_or_dependency_prompt"], "proactiveBehaviorLimits"),
            ("relationship_progression_limits", ["no_default_romantic_progression", "no_user_dependency_induction"], "relationshipProgressionLimits"),
            ("high_risk_behavior_action", "block", "highRiskBehaviorAction"),
            ("refusal_style", "warm_brief_non_preachy_safe_companion_redirect", "refusalStyle"),
        ],
        "policy": {
            "allowed_behaviors": ["safe_dialogue", "supportive_companionship", "clarifying_questions"],
            "cautious_behaviors": ["sensitive_emotional_support", "real_world_context_advice"],
            "forbidden_behaviors": [
                "major_real_world_decision_for_user",
                "autonomous_external_action",
                "unauthorized_tool_use",
                "dependency_induction",
                "proactive_romantic_escalation",
            ],
            "auto_action_limits": ["no_autonomous_external_action", "requires_explicit_user_confirmation"],
            "real_world_decision_limits": ["no_medical_legal_financial_or_life_decision_conclusion"],
            "tool_action_limits": ["no_provider_binding", "no_unauthorized_tool_call"],
            "proactive_behavior_limits": ["no_unrequested_escalation", "no_pressure_or_dependency_prompt"],
            "relationship_progression_limits": ["no_default_romantic_progression", "no_user_dependency_induction"],
            "high_risk_behavior_action": "block",
            "refusal_style": "warm_brief_non_preachy_safe_companion_redirect",
            "decision_modes": ["allow", "soften", "refuse", "block"],
            "default_mode": "soften",
        },
        "normalize_outputs": [
            "allowed_behaviors",
            "cautious_behaviors",
            "forbidden_behaviors",
            "auto_action_limits",
            "real_world_decision_limits",
            "tool_action_limits",
            "proactive_behavior_limits",
            "relationship_progression_limits",
            "high_risk_behavior_action",
            "refusal_style",
            "default_mode",
            "decision_modes",
        ],
        "required_fields": ["forbidden_behaviors", "auto_action_limits", "real_world_decision_limits", "high_risk_behavior_action"],
        "validation_rules": [
            "forbidden_behaviors_present",
            "auto_action_limits_present",
            "real_world_decision_limits_present",
            "no_major_real_world_decision_for_user",
            "no_proactive_romantic_progression",
            "no_dependency_induction",
            "no_external_action_without_user_confirmation",
            "no_unauthorized_tool_call",
            "no_identity_context_conflict",
        ],
    },
    {
        "module_id": DATA_SAFETY_MODULE_ID,
        "module_type": "humanistic_data_boundary_config",
        "module_name": "Data Boundary",
        "namespace": "dataBoundary",
        "tag": "data_safety",
        "output_key": DATA_SAFETY_OUTPUT_KEY,
        "node_prefix": "data_boundary",
        "fields": [
            ("allowed_data_read", ["current_dialogue_context", "explicitly_authorized_profile_context"], "allowedDataRead"),
            ("forbidden_data_read", ["private_auth_material", "private_files", "cross_resident_private_memory", "unauthorized_sensitive_data"], "forbiddenDataRead"),
            ("allowed_memory_write", ["user_approved_preferences", "non_sensitive_interaction_summary"], "allowedMemoryWrite"),
            ("forbidden_memory_write", ["private_auth_material", "sensitive_privacy_without_consent", "cross_resident_memory"], "forbiddenMemoryWrite"),
            ("sensitive_data_handling", "refuse_or_minimize", "sensitiveDataHandling"),
            ("privacy_protection_rules", ["data_minimization", "explicit_consent_for_sensitive_data"], "privacyProtectionRules"),
            ("memory_delete_update_rules", ["support_user_delete_or_correct_memory", "record_update_reason"], "memoryDeleteUpdateRules"),
            ("cross_resident_memory_isolation", ["per_resident_namespace_only", "no_private_memory_sharing"], "crossResidentMemoryIsolation"),
            ("fictional_memory_boundary", ["setting_memory_not_real_experience"], "fictionalMemoryBoundary"),
            ("fictional_experience_labeling", ["label_fictional_setting_when_needed"], "fictionalExperienceLabeling"),
        ],
        "policy": {
            "allowed_data_read": ["current_dialogue_context", "explicitly_authorized_profile_context"],
            "forbidden_data_read": ["private_auth_material", "private_files", "cross_resident_private_memory", "unauthorized_sensitive_data"],
            "allowed_memory_write": ["user_approved_preferences", "non_sensitive_interaction_summary"],
            "forbidden_memory_write": ["private_auth_material", "sensitive_privacy_without_consent", "cross_resident_memory"],
            "sensitive_data_handling": "refuse_or_minimize",
            "privacy_protection_rules": ["data_minimization", "explicit_consent_for_sensitive_data"],
            "memory_delete_update_rules": ["support_user_delete_or_correct_memory", "record_update_reason"],
            "cross_resident_memory_isolation": ["per_resident_namespace_only", "no_private_memory_sharing"],
            "fictional_memory_boundary": ["setting_memory_not_real_experience"],
            "fictional_experience_labeling": ["label_fictional_setting_when_needed"],
            "decision_modes": ["allow", "soften", "refuse", "block"],
            "default_mode": "refuse",
        },
        "normalize_outputs": [
            "allowed_data_read",
            "forbidden_data_read",
            "allowed_memory_write",
            "forbidden_memory_write",
            "sensitive_data_handling",
            "privacy_protection_rules",
            "memory_delete_update_rules",
            "cross_resident_memory_isolation",
            "fictional_memory_boundary",
            "fictional_experience_labeling",
            "default_mode",
            "decision_modes",
        ],
        "required_fields": ["forbidden_data_read", "forbidden_memory_write", "sensitive_data_handling"],
        "validation_rules": [
            "forbidden_data_read_present",
            "forbidden_memory_write_present",
            "sensitive_data_handling_present",
            "no_default_remember_all_dialogue",
            "no_default_save_sensitive_privacy",
            "no_disguised_setting_memory_as_real_experience",
            "no_cross_resident_private_memory_share",
            "no_unauthorized_long_term_memory_write",
            "no_identity_context_conflict",
        ],
    },
    {
        "module_id": INTERACTION_SAFETY_MODULE_ID,
        "module_type": "humanistic_interaction_boundary_config",
        "module_name": "Interaction Boundary",
        "namespace": "interactionBoundary",
        "tag": "interaction_safety",
        "output_key": INTERACTION_SAFETY_OUTPUT_KEY,
        "node_prefix": "interaction_boundary",
        "fields": [
            ("allowed_interactions", ["safe_companionship", "humanistic_dialogue", "bounded_emotional_support"], "allowedInteractions"),
            ("cautious_interactions", ["intimacy_expression", "sensitive_emotional_dependency_context"], "cautiousInteractions"),
            ("forbidden_interactions", ["default_romantic_relationship", "dependency_induction", "real_person_impersonation"], "forbiddenInteractions"),
            ("intimacy_expression_boundary", ["no_default_romance", "avoid_ambiguous_flirt_escalation"], "intimacyExpressionBoundary"),
            ("dependency_protection_rules", ["no_unique_dependency_claim", "encourage_real_support_network"], "dependencyProtectionRules"),
            ("non_romantic_default_boundary", "companion_default", "nonRomanticDefaultBoundary"),
            ("therapy_replacement_limits", ["no_psychotherapy_replacement", "no_diagnosis_or_treatment_claim"], "therapyReplacementLimits"),
            ("identity_disclosure_policy", ["disclose_digital_resident_when_needed", "no_real_person_claim"], "identityDisclosurePolicy"),
            ("authority_impersonation_protection", ["no_psychologist_mentor_authority_impersonation"], "authorityImpersonationProtection"),
            ("emotional_manipulation_protection", ["no_only_i_understand_you_claim", "no_isolating_user_from_others"], "emotionalManipulationProtection"),
        ],
        "policy": {
            "allowed_interactions": ["safe_companionship", "humanistic_dialogue", "bounded_emotional_support"],
            "cautious_interactions": ["intimacy_expression", "sensitive_emotional_dependency_context"],
            "forbidden_interactions": ["default_romantic_relationship", "dependency_induction", "real_person_impersonation"],
            "intimacy_expression_boundary": ["no_default_romance", "avoid_ambiguous_flirt_escalation"],
            "dependency_protection_rules": ["no_unique_dependency_claim", "encourage_real_support_network"],
            "non_romantic_default_boundary": "companion_default",
            "therapy_replacement_limits": ["no_psychotherapy_replacement", "no_diagnosis_or_treatment_claim"],
            "identity_disclosure_policy": ["disclose_digital_resident_when_needed", "no_real_person_claim"],
            "authority_impersonation_protection": ["no_psychologist_mentor_authority_impersonation"],
            "emotional_manipulation_protection": ["no_only_i_understand_you_claim", "no_isolating_user_from_others"],
            "decision_modes": ["allow", "soften", "refuse", "block"],
            "default_mode": "soften",
        },
        "normalize_outputs": [
            "allowed_interactions",
            "cautious_interactions",
            "forbidden_interactions",
            "intimacy_expression_boundary",
            "dependency_protection_rules",
            "non_romantic_default_boundary",
            "therapy_replacement_limits",
            "identity_disclosure_policy",
            "authority_impersonation_protection",
            "emotional_manipulation_protection",
            "default_mode",
            "decision_modes",
        ],
        "required_fields": ["forbidden_interactions", "non_romantic_default_boundary", "dependency_protection_rules"],
        "validation_rules": [
            "forbidden_interactions_present",
            "non_romantic_default_boundary_present",
            "dependency_protection_rules_present",
            "no_default_romantic_relationship",
            "no_default_ambiguous_flirt_relationship",
            "no_real_person_claim",
            "no_pretend_real_life_experience",
            "no_unique_dependency_induction",
            "no_authority_expert_impersonation",
            "no_identity_context_conflict",
        ],
    },
]


def _layer3_policy_node_ids(prefix: str) -> Dict[str, str]:
    return {
        "field_input": f"{prefix}_rule_input",
        "structure_normalize": f"{prefix}_rule_normalize",
        "validation": f"{prefix}_rule_validation",
        "update_rule": f"{prefix}_update_rule",
        "module_output": f"{prefix}_config_output",
    }


def _layer3_policy_field(namespace: str, field_id: str, value: object, key_suffix: str, required: bool = True) -> Dict[str, object]:
    return {
        "field_id": field_id,
        "value": value,
        "required": required,
        "edit_scope": "developer_only",
        "update_level": "versioned_core",
        "requires_recompile": True,
        "i18n_keys": {
            "label": f"layer3.{namespace}.field.{key_suffix}",
            "placeholder": f"layer3.{namespace}.field.{key_suffix}.placeholder",
            "help": f"layer3.{namespace}.field.{key_suffix}.help",
        },
    }


def _layer3_policy_update_policy() -> Dict[str, object]:
    return {
        "append_refine_or_tighten_only": True,
        "no_core_forbidden_deletion": True,
        "high_risk_default_action": "block",
        "gray_zone_default_action": "soften_or_refuse",
        "user_cannot_disable_core_boundary": True,
        "runtime_cannot_auto_relax_rules": True,
        "requires_update_reason_time_impact_scope": True,
        "requires_revalidation_after_update": True,
    }


def _layer3_policy_module(spec: Dict[str, object]) -> ModuleV04:
    module_id = str(spec["module_id"])
    output_key = str(spec["output_key"])
    namespace = str(spec["namespace"])
    node_ids = _layer3_policy_node_ids(str(spec["node_prefix"]))
    fields = [
        _layer3_policy_field(namespace, str(field_id), value, str(key_suffix))
        for field_id, value, key_suffix in spec["fields"]  # type: ignore[union-attr]
    ]
    field_registry = [
        {
            **{key: value for key, value in field.items() if key != "value"},
            "owner_node_id": node_ids["field_input"],
        }
        for field in fields
    ]
    update_policy = _layer3_policy_update_policy()
    policy = {
        **spec["policy"],  # type: ignore[arg-type]
        "update_policy": update_policy,
        "compile_validation_status": "pending",
        "identity_context_ref": "layer_1.resident_identity",
        "compile_time_only": True,
    }
    node_params = {
        "field_input": {"fields": fields},
        "structure_normalize": {
            "input": node_ids["field_input"],
            "normalize_rules": ["map_input_rules", "preserve_safety_defaults", "emit_decision_defaults"],
            "outputs": spec["normalize_outputs"],
        },
        "validation": {
            "input": node_ids["structure_normalize"],
            "required_fields": spec["required_fields"],
            "validation_rules": spec["validation_rules"],
            "readonly_refs": {"identity_context_ref": "layer_1.resident_identity"},
        },
        "update_rule": {
            "input": node_ids["validation"],
            "update_policy": update_policy,
            "update_rules": [
                {"rule_id": "append_refine_or_tighten_only", "locked": True},
                {"rule_id": "no_core_forbidden_deletion", "locked": True},
                {"rule_id": "high_risk_default_block", "locked": True},
                {"rule_id": "gray_zone_soften_or_refuse", "locked": True},
                {"rule_id": "user_cannot_disable_core_boundary", "locked": True},
                {"rule_id": "runtime_cannot_auto_relax_rules", "locked": True},
                {"rule_id": "requires_update_reason_time_impact_scope", "locked": True},
                {"rule_id": "requires_revalidation_after_update", "locked": True},
            ],
        },
        "module_output": {
            "input": node_ids["update_rule"],
            "output_key": output_key,
            "output_schema": {"type": "object", "required": True},
        },
    }
    node_i18n_suffix = {
        "field_input": "input",
        "structure_normalize": "normalize",
        "validation": "validate",
        "update_rule": "updateRules",
        "module_output": "output",
    }
    nodes = []
    for node_type in IDENTITY_CORE_NODE_TYPES:
        nodes.append(
            {
                "node_id": node_ids[node_type],
                "node_type": node_type,
                "module_id": module_id,
                "layer_id": "layer_3",
                "params": node_params[node_type],
                "i18n_keys": {
                    "name": f"layer3.{namespace}.node.{node_i18n_suffix[node_type]}.title",
                    "description": f"layer3.{namespace}.node.{node_i18n_suffix[node_type]}.description",
                    "type_name": f"node.type.{node_type}",
                },
                "outputs": {output_key: policy, "module_output": output_key} if node_type == "module_output" else {},
                "metadata": {"compile_time_only": True, "runtime_enabled": False, "no_execution": True},
            }
        )
    return _module(
        module_id,
        str(spec["module_type"]),
        str(spec["module_name"]),
        "layer_3",
        status=ProtocolStatus.ready,
        risk_level=RiskLevel.high,
        category="safety",
        is_placeholder=False,
        audit_required=True,
        color_status="green",
        tags=["safety", str(spec["tag"]), "core"],
        module_graph={
            "shell_version": "module_shell_v1",
            "nodes": nodes,
            "edges": [
                {
                    "edge_id": f"{node_ids[source]}_to_{node_ids[target]}",
                    "source": node_ids[source],
                    "source_port": "p_out",
                    "target": node_ids[target],
                    "target_port": "p_in",
                }
                for source, target in zip(IDENTITY_CORE_NODE_TYPES[:-1], IDENTITY_CORE_NODE_TYPES[1:])
            ],
            "output_key": output_key,
            "compile_time_only": True,
        },
        output_schema=[{"key": output_key, "type": "object", "required": True, "description": f"layer3.{namespace}.module.output"}],
        ui_config={"shell_version": "module_shell_v1", "classification": "core"},
        i18n_keys={
            "display_name": f"layer3.{namespace}.module.title",
            "description": f"layer3.{namespace}.module.description",
            "output": f"layer3.{namespace}.module.output",
            "module_type": f"layer3.{namespace}.module.type",
        },
        outputs={output_key: policy, "module_output": output_key},
        config={
            "shell_version": "module_shell_v1",
            "module_class": "core",
            "module_type_label_key": f"layer3.{namespace}.module.type",
            "field_registry": field_registry,
            "edit_scope": "developer_only",
            "update_level": "versioned_core",
            "requires_recompile": True,
            "compile_time_only": True,
        },
        mock_only=True,
        no_execution=True,
        dr_write_keys=[f"payload.graph_snapshot.layer_outputs.layer_3.{output_key}"],
    )


def _risk_response_field(field_id: str, value: object, key_suffix: str, required: bool = True) -> Dict[str, object]:
    return {
        "field_id": field_id,
        "value": value,
        "required": required,
        "edit_scope": "developer_only",
        "update_level": "versioned_core",
        "requires_recompile": True,
        "i18n_keys": {
            "label": f"layer3.riskResponse.field.{key_suffix}",
            "placeholder": f"layer3.riskResponse.field.{key_suffix}.placeholder",
            "help": f"layer3.riskResponse.field.{key_suffix}.help",
        },
    }


def _risk_response_module() -> ModuleV04:
    module_id = RISK_RESPONSE_MODULE_ID
    input_policy_keys = [
        CONTENT_SAFETY_OUTPUT_KEY,
        BEHAVIOR_SAFETY_OUTPUT_KEY,
        DATA_SAFETY_OUTPUT_KEY,
        INTERACTION_SAFETY_OUTPUT_KEY,
    ]
    signal_fields = [
        _risk_response_field("content_risk_source", CONTENT_SAFETY_OUTPUT_KEY, "contentRiskSource"),
        _risk_response_field("behavior_risk_source", BEHAVIOR_SAFETY_OUTPUT_KEY, "behaviorRiskSource"),
        _risk_response_field("data_risk_source", DATA_SAFETY_OUTPUT_KEY, "dataRiskSource"),
        _risk_response_field("interaction_risk_source", INTERACTION_SAFETY_OUTPUT_KEY, "interactionRiskSource"),
        _risk_response_field(
            "risk_signal_summary",
            ["content_high_risk", "behavior_boundary_violation", "sensitive_data_risk", "interaction_dependency_risk"],
            "riskSignalSummary",
        ),
        _risk_response_field("identity_context_ref", "layer_1.resident_identity", "identityContextRef"),
    ]
    level_fields = [
        _risk_response_field("risk_levels", ["allow", "soften", "refuse", "review", "block"], "riskLevels"),
        _risk_response_field("default_risk_level", "review", "defaultRiskLevel"),
        _risk_response_field("content_risk_rules", ["high_risk_content_defaults_to_block"], "contentRiskRules"),
        _risk_response_field("behavior_risk_rules", ["major_real_world_action_defaults_to_review_or_block"], "behaviorRiskRules"),
        _risk_response_field("data_risk_rules", ["sensitive_privacy_defaults_to_refuse_or_block"], "dataRiskRules"),
        _risk_response_field("interaction_risk_rules", ["relationship_boundary_risk_defaults_to_soften_or_refuse"], "interactionRiskRules"),
        _risk_response_field("highest_risk_priority", ["block", "review", "refuse", "soften", "allow"], "highestRiskPriority"),
    ]
    strategy_fields = [
        _risk_response_field("allow_action", "normal_response", "allowAction"),
        _risk_response_field("soften_action", ["de_escalate", "clarify", "reduce_commitment", "safe_companionship"], "softenAction"),
        _risk_response_field("refuse_action", ["warm_brief_non_preachy_refusal", "safe_alternative"], "refuseAction"),
        _risk_response_field("review_action", ["pause_auto_action", "enter_user_or_developer_review"], "reviewAction"),
        _risk_response_field("block_action", ["block_response", "no_dangerous_content", "no_related_action"], "blockAction"),
        _risk_response_field("safe_redirect_policy", ["safe_companionship", "clarify_limits", "encourage_real_support"], "safeRedirectPolicy"),
        _risk_response_field("refusal_style", "warm_brief_non_preachy_safe_redirect", "refusalStyle"),
        _risk_response_field("degraded_response_style", "de_escalated_clear_bounded_companionship", "degradedResponseStyle"),
    ]
    human_review_fields = [
        _risk_response_field(
            "human_review_triggers",
            [
                "external_platform_operation",
                "act_on_behalf_publish_delete_comment_dm_follow_repost",
                "major_real_world_decision",
                "gray_zone_safety_risk",
                "privacy_or_cross_resident_memory",
                "uncertain_risk_level",
                "conflict_among_layer3_policies",
            ],
            "humanReviewTriggers",
        ),
        _risk_response_field("user_confirmation_required", ["external_action", "privacy_sensitive_action"], "userConfirmationRequired"),
        _risk_response_field("developer_review_required", ["policy_conflict", "uncertain_high_risk"], "developerReviewRequired"),
        _risk_response_field("pause_before_review", True, "pauseBeforeReview"),
        _risk_response_field("allow_after_review", "explicit_approval_only", "allowAfterReview"),
        _risk_response_field("review_failure_handling", "refuse_or_block_with_safe_redirect", "reviewFailureHandling"),
        _risk_response_field("review_log_requirements", ["reason", "time", "impact_scope", "decision"], "reviewLogRequirements"),
    ]
    hard_block_fields = [
        _risk_response_field(
            "hard_block_triggers",
            [
                "self_harm_method",
                "illegal_instruction",
                "violent_harm_instruction",
                "adult_sexual_content",
                "dependency_induction",
                "manipulate_others",
                "medical_legal_financial_conclusion",
                "impersonated_real_human_experience",
                "default_romantic_or_girlfriend_relationship",
                "unauthorized_external_action",
                "unauthorized_sensitive_privacy_read_or_save",
                "cross_resident_private_memory_sharing",
            ],
            "hardBlockTriggers",
        ),
        _risk_response_field("non_authorizable_content", ["self_harm_method", "illegal_instruction", "adult_sexual_content"], "nonAuthorizableContent"),
        _risk_response_field("non_authorizable_behaviors", ["unauthorized_external_action", "manipulate_others"], "nonAuthorizableBehaviors"),
        _risk_response_field("non_writable_memory", ["sensitive_privacy_without_consent", "cross_resident_private_memory"], "nonWritableMemory"),
        _risk_response_field("non_allowed_interactions", ["dependency_induction", "default_romantic_relationship"], "nonAllowedInteractions"),
        _risk_response_field("block_response_style", "warm_brief_no_dangerous_detail_safe_redirect", "blockResponseStyle"),
        _risk_response_field("block_log_requirements", ["trigger", "reason", "policy_key", "time"], "blockLogRequirements"),
    ]
    output_fields = [
        _risk_response_field("risk_policy", RISK_POLICY_OUTPUT_KEY, "riskPolicy"),
        _risk_response_field("hard_block_policy", HARD_BLOCK_POLICY_OUTPUT_KEY, "hardBlockPolicy"),
        _risk_response_field("human_review_policy", HUMAN_REVIEW_POLICY_OUTPUT_KEY, "humanReviewPolicy"),
        _risk_response_field("audit_log_policy", AUDIT_LOG_POLICY_OUTPUT_KEY, "auditLogPolicy"),
        _risk_response_field("default_risk_mode", "review", "defaultRiskMode"),
        _risk_response_field("decision_modes", ["allow", "soften", "refuse", "review", "block"], "decisionModes"),
        _risk_response_field("compile_validation_status", "valid", "compileValidationStatus"),
    ]
    fields = signal_fields + level_fields + strategy_fields + human_review_fields + hard_block_fields + output_fields
    field_registry = [
        {
            **{key: value for key, value in field.items() if key != "value"},
            "owner_node_id": RISK_RESPONSE_NODE_IDS["signal_summary"],
        }
        for field in fields
    ]

    risk_signal_summary = {
        "input_policies": input_policy_keys,
        "content_risk_source": CONTENT_SAFETY_OUTPUT_KEY,
        "behavior_risk_source": BEHAVIOR_SAFETY_OUTPUT_KEY,
        "data_risk_source": DATA_SAFETY_OUTPUT_KEY,
        "interaction_risk_source": INTERACTION_SAFETY_OUTPUT_KEY,
        "aggregated_risk_signals": ["content_high_risk", "behavior_boundary_violation", "sensitive_data_risk", "interaction_dependency_risk"],
        "identity_context_ref": "layer_1.resident_identity",
    }
    risk_level_policy = {
        "risk_levels": ["allow", "soften", "refuse", "review", "block"],
        "default_risk_level": "review",
        "content_risk_rules": ["high_risk_content_defaults_to_block"],
        "behavior_risk_rules": ["major_real_world_action_defaults_to_review_or_block"],
        "data_risk_rules": ["sensitive_privacy_defaults_to_refuse_or_block"],
        "interaction_risk_rules": ["relationship_boundary_risk_defaults_to_soften_or_refuse"],
        "uncertain_risk_action": "review",
        "highest_risk_priority": ["block", "review", "refuse", "soften", "allow"],
    }
    safe_redirect_policy = {
        "redirect_modes": ["safe_companionship", "clarify_limits", "encourage_real_support", "provide_general_safe_info"],
        "style": "warm_brief_non_preachy",
        "no_professional_conclusion": True,
    }
    risk_response_strategy = {
        "allow_action": "normal_response",
        "soften_action": ["de_escalate", "clarify", "reduce_commitment", "safe_companionship"],
        "refuse_action": ["warm_brief_non_preachy_refusal", "safe_alternative"],
        "review_action": ["pause_auto_action", "enter_user_or_developer_review"],
        "block_action": ["block_response", "no_dangerous_content", "no_related_action"],
        "safe_redirect_policy": safe_redirect_policy,
        "refusal_style": "warm_brief_non_preachy_safe_redirect",
        "degraded_response_style": "de_escalated_clear_bounded_companionship",
    }
    human_review_policy = {
        "human_review_triggers": human_review_fields[0]["value"],
        "user_confirmation_required": ["external_action", "privacy_sensitive_action"],
        "developer_review_required": ["policy_conflict", "uncertain_high_risk"],
        "pause_before_review": True,
        "allow_after_review": "explicit_approval_only",
        "review_failure_handling": "refuse_or_block_with_safe_redirect",
        "review_log_requirements": ["reason", "time", "impact_scope", "decision"],
        "compile_time_only": True,
    }
    hard_block_policy = {
        "hard_block_triggers": hard_block_fields[0]["value"],
        "non_authorizable_content": ["self_harm_method", "illegal_instruction", "adult_sexual_content"],
        "non_authorizable_behaviors": ["unauthorized_external_action", "manipulate_others"],
        "non_writable_memory": ["sensitive_privacy_without_consent", "cross_resident_private_memory"],
        "non_allowed_interactions": ["dependency_induction", "default_romantic_relationship"],
        "block_response_style": "warm_brief_no_dangerous_detail_safe_redirect",
        "block_log_requirements": ["trigger", "reason", "policy_key", "time"],
        "compile_time_only": True,
    }
    audit_log_policy = {
        "enabled": True,
        "log_scope": ["risk_level_decision", "human_review", "hard_block", "safe_redirect"],
        "required_fields": ["reason", "time", "impact_scope", "decision"],
        "no_social_platform_audit_implementation": True,
        "no_tool_call_audit_implementation": True,
        "compile_time_only": True,
    }
    risk_policy = {
        "risk_signal_summary": risk_signal_summary,
        "risk_level_policy": risk_level_policy,
        "risk_response_strategy": risk_response_strategy,
        "human_review_policy": human_review_policy,
        "hard_block_policy": hard_block_policy,
        "audit_log_policy": audit_log_policy,
        "safe_redirect_policy": safe_redirect_policy,
        "default_risk_mode": "review",
        "decision_modes": ["allow", "soften", "refuse", "review", "block"],
        "compile_validation_status": "valid",
        "identity_context_ref": "layer_1.resident_identity",
        "compile_time_only": True,
    }
    outputs = {
        RISK_POLICY_OUTPUT_KEY: risk_policy,
        HARD_BLOCK_POLICY_OUTPUT_KEY: hard_block_policy,
        HUMAN_REVIEW_POLICY_OUTPUT_KEY: human_review_policy,
        AUDIT_LOG_POLICY_OUTPUT_KEY: audit_log_policy,
        SAFE_REDIRECT_POLICY_OUTPUT_KEY: safe_redirect_policy,
        "module_output": RISK_POLICY_OUTPUT_KEY,
    }
    output_description_keys = {
        RISK_POLICY_OUTPUT_KEY: "layer3.riskResponse.field.riskPolicy",
        HARD_BLOCK_POLICY_OUTPUT_KEY: "layer3.riskResponse.field.hardBlockPolicy",
        HUMAN_REVIEW_POLICY_OUTPUT_KEY: "layer3.riskResponse.field.humanReviewPolicy",
        AUDIT_LOG_POLICY_OUTPUT_KEY: "layer3.riskResponse.field.auditLogPolicy",
        SAFE_REDIRECT_POLICY_OUTPUT_KEY: "layer3.riskResponse.field.safeRedirectPolicy",
    }
    node_params = {
        "signal_summary": {
            "input_policy_keys": input_policy_keys,
            "fields": signal_fields,
            "readonly_refs": {"identity_context_ref": "layer_1.resident_identity"},
            "outputs": ["risk_signal_summary"],
        },
        "level_decision": {
            "input": RISK_RESPONSE_NODE_IDS["signal_summary"],
            "fields": level_fields,
            "risk_level_policy": risk_level_policy,
            "risk_levels": ["allow", "soften", "refuse", "review", "block"],
            "default_risk_level": "review",
            "validation_rules": [
                "high_risk_content_defaults_to_block",
                "major_real_world_action_defaults_to_review_or_block",
                "sensitive_privacy_defaults_to_refuse_or_block",
                "relationship_boundary_risk_defaults_to_soften_or_refuse",
                "uncertain_risk_defaults_to_review",
            ],
            "outputs": ["risk_level_policy"],
        },
        "strategy_selection": {
            "input": RISK_RESPONSE_NODE_IDS["level_decision"],
            "fields": strategy_fields,
            "risk_response_strategy": risk_response_strategy,
            "outputs": ["risk_response_strategy"],
        },
        "human_review": {
            "input": RISK_RESPONSE_NODE_IDS["strategy_selection"],
            "fields": human_review_fields,
            "human_review_policy": human_review_policy,
            "outputs": [HUMAN_REVIEW_POLICY_OUTPUT_KEY],
        },
        "hard_block": {
            "input": RISK_RESPONSE_NODE_IDS["human_review"],
            "fields": hard_block_fields,
            "hard_block_policy": hard_block_policy,
            "outputs": [HARD_BLOCK_POLICY_OUTPUT_KEY],
        },
        "module_output": {
            "input": RISK_RESPONSE_NODE_IDS["hard_block"],
            "output_key": RISK_POLICY_OUTPUT_KEY,
            "output_schema": {"type": "object", "required": True},
            "outputs": list(LAYER3_RISK_RESPONSE_OUTPUT_KEYS),
        },
    }
    node_i18n_suffix = {
        "signal_summary": "signalSummary",
        "level_decision": "levelDecision",
        "strategy_selection": "strategySelection",
        "human_review": "humanReview",
        "hard_block": "hardBlock",
        "module_output": "output",
    }
    nodes = []
    for node_key in RISK_RESPONSE_NODE_ORDER:
        node_id = RISK_RESPONSE_NODE_IDS[node_key]
        node_outputs_by_key = {
            "signal_summary": {"risk_signal_summary": risk_signal_summary},
            "level_decision": {"risk_level_policy": risk_level_policy},
            "strategy_selection": {"risk_response_strategy": risk_response_strategy},
            "human_review": {HUMAN_REVIEW_POLICY_OUTPUT_KEY: human_review_policy},
            "hard_block": {HARD_BLOCK_POLICY_OUTPUT_KEY: hard_block_policy},
            "module_output": outputs,
        }
        node_outputs = node_outputs_by_key[node_key]
        nodes.append(
            {
                "node_id": node_id,
                "node_type": RISK_RESPONSE_NODE_TYPES[node_key],
                "module_id": module_id,
                "layer_id": "layer_3",
                "params": node_params[node_key],
                "i18n_keys": {
                    "name": f"layer3.riskResponse.node.{node_i18n_suffix[node_key]}.title",
                    "description": f"layer3.riskResponse.node.{node_i18n_suffix[node_key]}.description",
                    "type_name": f"node.type.{RISK_RESPONSE_NODE_TYPES[node_key]}",
                },
                "outputs": node_outputs,
                "metadata": {"compile_time_only": True, "runtime_enabled": False, "no_execution": True},
            }
        )

    return _module(
        module_id,
        "humanistic_risk_response_config",
        "Risk Response",
        "layer_3",
        status=ProtocolStatus.ready,
        risk_level=RiskLevel.high,
        category="safety",
        is_placeholder=False,
        audit_required=True,
        color_status="green",
        tags=["safety", "risk_response", "core"],
        module_graph={
            "shell_version": "module_shell_v1",
            "nodes": nodes,
            "edges": [
                {
                    "edge_id": f"{RISK_RESPONSE_NODE_IDS[source]}_to_{RISK_RESPONSE_NODE_IDS[target]}",
                    "source": RISK_RESPONSE_NODE_IDS[source],
                    "source_port": "p_out",
                    "target": RISK_RESPONSE_NODE_IDS[target],
                    "target_port": "p_in",
                }
                for source, target in zip(RISK_RESPONSE_NODE_ORDER[:-1], RISK_RESPONSE_NODE_ORDER[1:])
            ],
            "output_key": RISK_POLICY_OUTPUT_KEY,
            "compile_time_only": True,
        },
        output_schema=[
            {"key": output_key, "type": "object", "required": True, "description": output_description_keys[output_key]}
            for output_key in LAYER3_RISK_RESPONSE_OUTPUT_KEYS
        ],
        ui_config={"shell_version": "module_shell_v1", "classification": "core"},
        i18n_keys={
            "display_name": "layer3.riskResponse.module.title",
            "description": "layer3.riskResponse.module.description",
            "output": "layer3.riskResponse.module.output",
            "module_type": "layer3.riskResponse.module.type",
        },
        outputs=outputs,
        config={
            "shell_version": "module_shell_v1",
            "module_class": "core",
            "module_type_label_key": "layer3.riskResponse.module.type",
            "field_registry": field_registry,
            "edit_scope": "developer_only",
            "update_level": "versioned_core",
            "requires_recompile": True,
            "compile_time_only": True,
            "input_policy_keys": input_policy_keys,
        },
        mock_only=True,
        no_execution=True,
        dr_write_keys=[f"payload.graph_snapshot.layer_outputs.layer_3.{output_key}" for output_key in LAYER3_RISK_RESPONSE_OUTPUT_KEYS],
    )


LANGUAGE_BEHAVIOR_MODULE_ID = "language_habit"
LANGUAGE_BEHAVIOR_OUTPUT_KEY = "language_behavior_config"
LANGUAGE_BEHAVIOR_NODE_IDS = {
    "input_basis": "language_behavior_input_basis",
    "core_rules": "language_behavior_core_rules",
    "boundary_limits": "language_behavior_boundary_limits",
    "output_expression": "language_behavior_output_expression",
    "validation": "language_behavior_validation",
}
LANGUAGE_BEHAVIOR_PRESET_ID = "human_empathy_cn_v0_1"
DECISION_BEHAVIOR_MODULE_ID = "decision_pattern"
DECISION_BEHAVIOR_OUTPUT_KEY = "decision_behavior_config"
DECISION_BEHAVIOR_NODE_IDS = {
    "input_basis": "decision_behavior_input_basis",
    "core_rules": "decision_behavior_core_rules",
    "boundary_limits": "decision_behavior_boundary_limits",
    "output_expression": "decision_behavior_output_expression",
    "validation": "decision_behavior_validation",
}
DECISION_BEHAVIOR_PRESET_ID = "human_empathy_decision_v0_1"
DETAIL_BEHAVIOR_MODULE_ID = "emotion_reaction"
DETAIL_BEHAVIOR_OUTPUT_KEY = "detail_behavior_config"
DETAIL_BEHAVIOR_NODE_IDS = {
    "input_basis": "detail_behavior_input_basis",
    "core_rules": "detail_behavior_core_rules",
    "boundary_limits": "detail_behavior_boundary_limits",
    "output_expression": "detail_behavior_output_expression",
    "validation": "detail_behavior_validation",
}
DETAIL_BEHAVIOR_PRESET_ID = "human_empathy_detail_v0_1"
INTERACTION_BEHAVIOR_MODULE_ID = "interaction_strategy"
INTERACTION_BEHAVIOR_OUTPUT_KEY = "interaction_behavior_config"
INTERACTION_BEHAVIOR_NODE_IDS = {
    "input_basis": "interaction_behavior_input_basis",
    "core_rules": "interaction_behavior_core_rules",
    "boundary_limits": "interaction_behavior_boundary_limits",
    "output_expression": "interaction_behavior_output_expression",
    "validation": "interaction_behavior_validation",
}
INTERACTION_BEHAVIOR_PRESET_ID = "human_empathy_interaction_v0_1"
TASK_BEHAVIOR_MODULE_ID = "behavior_habit"
TASK_BEHAVIOR_OUTPUT_KEY = "task_behavior_config"
TASK_BEHAVIOR_NODE_IDS = {
    "input_basis": "task_behavior_input_basis",
    "core_rules": "task_behavior_core_rules",
    "boundary_limits": "task_behavior_boundary_limits",
    "output_expression": "task_behavior_output_expression",
    "validation": "task_behavior_validation",
}
TASK_BEHAVIOR_PRESET_ID = "human_empathy_task_v0_1"
SOCIAL_BEHAVIOR_MODULE_ID = "emotion_mapper"
SOCIAL_BEHAVIOR_OUTPUT_KEY = "social_behavior_config"
SOCIAL_BEHAVIOR_NODE_IDS = {
    "input_basis": "social_behavior_input_basis",
    "core_rules": "social_behavior_core_rules",
    "boundary_limits": "social_behavior_boundary_limits",
    "output_expression": "social_behavior_output_expression",
    "validation": "social_behavior_validation",
}
SOCIAL_BEHAVIOR_PRESET_ID = "human_empathy_social_v0_1"


def _behavior_dr_write_keys(policy_key: str) -> List[str]:
    return [
        f"payload.behavior_policy.modules.{policy_key}",
        f"payload.graph_snapshot.layer_outputs.layer_8.behavior_policy.modules.{policy_key}",
    ]


def _language_behavior_field(node_key: str, field_id: str, key_suffix: str) -> Dict[str, object]:
    return {
        "field_id": field_id,
        "value": "",
        "required": False,
        "edit_scope": "developer_only",
        "update_level": "versioned_core",
        "requires_recompile": True,
        "i18n_keys": {
            "label": f"layer8.languageBehavior.{node_key}.field.{key_suffix}",
            "placeholder": f"layer8.languageBehavior.{node_key}.field.{key_suffix}.placeholder",
            "help": f"layer8.languageBehavior.{node_key}.field.{key_suffix}.help",
        },
    }


def _language_behavior_option(option_id: str, key_suffix: str, *, default_selected: bool = True) -> Dict[str, object]:
    return {
        "option_id": option_id,
        "default_selected": default_selected,
        "i18n_keys": {
            "label": f"layer8.languageBehavior.option.{key_suffix}",
        },
    }


def _language_behavior_checkbox_config(
    default_options: List[Dict[str, object]],
    optional_options: List[Dict[str, object]] | None = None,
) -> Dict[str, object]:
    selected = [str(option["option_id"]) for option in default_options if option.get("default_selected") is not False]
    return {
        "preset_id": LANGUAGE_BEHAVIOR_PRESET_ID,
        "selected_options": selected,
        "default_selected_options": selected,
        "default_options": default_options,
        "optional_options": optional_options or [],
        "custom_text": "",
    }


def _decision_behavior_option(option_id: str, key_suffix: str, *, default_selected: bool = True) -> Dict[str, object]:
    return {
        "option_id": option_id,
        "default_selected": default_selected,
        "i18n_keys": {
            "label": f"layer8.decisionBehavior.option.{key_suffix}",
        },
    }


def _decision_behavior_checkbox_config(
    default_options: List[Dict[str, object]],
    optional_options: List[Dict[str, object]] | None = None,
) -> Dict[str, object]:
    selected = [str(option["option_id"]) for option in default_options if option.get("default_selected") is not False]
    return {
        "preset_id": DECISION_BEHAVIOR_PRESET_ID,
        "selected_options": selected,
        "default_selected_options": selected,
        "default_options": default_options,
        "optional_options": optional_options or [],
        "custom_text": "",
        "apply_preset_label_key": "node.checklist.applyHumanEmpathyDecisionTemplate",
    }


def _detail_behavior_option(option_id: str, key_suffix: str, *, default_selected: bool = True) -> Dict[str, object]:
    return {
        "option_id": option_id,
        "default_selected": default_selected,
        "i18n_keys": {
            "label": f"layer8.detailBehavior.option.{key_suffix}",
        },
    }


def _detail_behavior_checkbox_config(
    default_options: List[Dict[str, object]],
    optional_options: List[Dict[str, object]] | None = None,
) -> Dict[str, object]:
    selected = [str(option["option_id"]) for option in default_options if option.get("default_selected") is not False]
    return {
        "preset_id": DETAIL_BEHAVIOR_PRESET_ID,
        "selected_options": selected,
        "default_selected_options": selected,
        "default_options": default_options,
        "optional_options": optional_options or [],
        "custom_text": "",
        "apply_preset_label_key": "node.checklist.applyHumanEmpathyDetailTemplate",
    }


def _interaction_behavior_option(option_id: str, key_suffix: str, *, default_selected: bool = True) -> Dict[str, object]:
    return {
        "option_id": option_id,
        "default_selected": default_selected,
        "i18n_keys": {
            "label": f"layer8.interactionBehavior.option.{key_suffix}",
        },
    }


def _interaction_behavior_checkbox_config(
    default_options: List[Dict[str, object]],
    optional_options: List[Dict[str, object]] | None = None,
) -> Dict[str, object]:
    selected = [str(option["option_id"]) for option in default_options if option.get("default_selected") is not False]
    return {
        "preset_id": INTERACTION_BEHAVIOR_PRESET_ID,
        "selected_options": selected,
        "default_selected_options": selected,
        "default_options": default_options,
        "optional_options": optional_options or [],
        "custom_text": "",
        "apply_preset_label_key": "node.checklist.applyHumanEmpathyInteractionTemplate",
    }


def _task_behavior_option(option_id: str, key_suffix: str, *, default_selected: bool = True) -> Dict[str, object]:
    return {
        "option_id": option_id,
        "default_selected": default_selected,
        "i18n_keys": {
            "label": f"layer8.taskBehavior.option.{key_suffix}",
        },
    }


def _task_behavior_checkbox_config(
    default_options: List[Dict[str, object]],
    optional_options: List[Dict[str, object]] | None = None,
) -> Dict[str, object]:
    selected = [str(option["option_id"]) for option in default_options if option.get("default_selected") is not False]
    return {
        "preset_id": TASK_BEHAVIOR_PRESET_ID,
        "selected_options": selected,
        "default_selected_options": selected,
        "default_options": default_options,
        "optional_options": optional_options or [],
        "custom_text": "",
        "apply_preset_label_key": "node.checklist.applyHumanEmpathyTaskTemplate",
    }


def _social_behavior_option(option_id: str, key_suffix: str, *, default_selected: bool = True) -> Dict[str, object]:
    return {
        "option_id": option_id,
        "default_selected": default_selected,
        "i18n_keys": {
            "label": f"layer8.socialBehavior.option.{key_suffix}",
        },
    }


def _social_behavior_checkbox_config(
    default_options: List[Dict[str, object]],
    optional_options: List[Dict[str, object]] | None = None,
) -> Dict[str, object]:
    selected = [str(option["option_id"]) for option in default_options if option.get("default_selected") is not False]
    return {
        "preset_id": SOCIAL_BEHAVIOR_PRESET_ID,
        "selected_options": selected,
        "default_selected_options": selected,
        "default_options": default_options,
        "optional_options": optional_options or [],
        "custom_text": "",
        "apply_preset_label_key": "node.checklist.applyHumanEmpathySocialTemplate",
    }


def _language_behavior_reference(
    reference_id: str,
    reference_type: str,
    layer_id: str,
    module_id: str,
    field_id: str,
    usage_suffix: str,
    *,
    module_key: str | None = None,
    field_key: str | None = None,
) -> Dict[str, object]:
    return {
        "reference_id": reference_id,
        "reference_type": reference_type,
        "layer_id": layer_id,
        "module_id": module_id,
        "field_id": field_id,
        "path": f"{layer_id}/{module_id}/{field_id}",
        "usage": "",
        "usage_key": f"layer8.languageBehavior.referenceUsage.{usage_suffix}",
        "i18n_keys": {
            "layer": f"layer.{layer_id}",
            "module": module_key or f"module.{module_id}",
            "field": field_key or f"layer8.languageBehavior.refField.{field_id}",
        },
    }


def _decision_behavior_reference(
    reference_id: str,
    reference_type: str,
    layer_id: str,
    module_id: str,
    field_id: str,
    usage_suffix: str,
    *,
    module_key: str | None = None,
    field_key: str | None = None,
) -> Dict[str, object]:
    return {
        "reference_id": reference_id,
        "reference_type": reference_type,
        "layer_id": layer_id,
        "module_id": module_id,
        "field_id": field_id,
        "path": f"{layer_id}/{module_id}/{field_id}",
        "usage": "",
        "usage_key": f"layer8.decisionBehavior.referenceUsage.{usage_suffix}",
        "i18n_keys": {
            "layer": f"layer.{layer_id}",
            "module": module_key or f"module.{module_id}",
            "field": field_key or f"layer8.decisionBehavior.refField.{field_id}",
        },
    }


def _detail_behavior_reference(
    reference_id: str,
    reference_type: str,
    layer_id: str,
    module_id: str,
    field_id: str,
    usage_suffix: str,
    *,
    module_key: str | None = None,
    field_key: str | None = None,
) -> Dict[str, object]:
    return {
        "reference_id": reference_id,
        "reference_type": reference_type,
        "layer_id": layer_id,
        "module_id": module_id,
        "field_id": field_id,
        "path": f"{layer_id}/{module_id}/{field_id}",
        "usage": "",
        "usage_key": f"layer8.detailBehavior.referenceUsage.{usage_suffix}",
        "i18n_keys": {
            "layer": f"layer.{layer_id}",
            "module": module_key or f"module.{module_id}",
            "field": field_key or f"layer8.detailBehavior.refField.{field_id}",
        },
    }


def _interaction_behavior_reference(
    reference_id: str,
    reference_type: str,
    layer_id: str,
    module_id: str,
    field_id: str,
    usage_suffix: str,
    *,
    module_key: str | None = None,
    field_key: str | None = None,
) -> Dict[str, object]:
    return {
        "reference_id": reference_id,
        "reference_type": reference_type,
        "layer_id": layer_id,
        "module_id": module_id,
        "field_id": field_id,
        "path": f"{layer_id}/{module_id}/{field_id}",
        "usage": "",
        "usage_key": f"layer8.interactionBehavior.referenceUsage.{usage_suffix}",
        "i18n_keys": {
            "layer": f"layer.{layer_id}",
            "module": module_key or f"module.{module_id}",
            "field": field_key or f"layer8.interactionBehavior.refField.{field_id}",
        },
    }


def _task_behavior_reference(
    reference_id: str,
    reference_type: str,
    layer_id: str,
    module_id: str,
    field_id: str,
    usage_suffix: str,
    *,
    module_key: str | None = None,
    field_key: str | None = None,
) -> Dict[str, object]:
    return {
        "reference_id": reference_id,
        "reference_type": reference_type,
        "layer_id": layer_id,
        "module_id": module_id,
        "field_id": field_id,
        "path": f"{layer_id}/{module_id}/{field_id}",
        "usage": "",
        "usage_key": f"layer8.taskBehavior.referenceUsage.{usage_suffix}",
        "i18n_keys": {
            "layer": f"layer.{layer_id}",
            "module": module_key or f"module.{module_id}",
            "field": field_key or f"layer8.taskBehavior.refField.{field_id}",
        },
    }


def _social_behavior_reference(
    reference_id: str,
    reference_type: str,
    layer_id: str,
    module_id: str,
    field_id: str,
    usage_suffix: str,
    *,
    module_key: str | None = None,
    field_key: str | None = None,
) -> Dict[str, object]:
    return {
        "reference_id": reference_id,
        "reference_type": reference_type,
        "layer_id": layer_id,
        "module_id": module_id,
        "field_id": field_id,
        "path": f"{layer_id}/{module_id}/{field_id}",
        "usage": "",
        "usage_key": f"layer8.socialBehavior.referenceUsage.{usage_suffix}",
        "i18n_keys": {
            "layer": f"layer.{layer_id}",
            "module": module_key or f"module.{module_id}",
            "field": field_key or f"layer8.socialBehavior.refField.{field_id}",
        },
    }


def _language_behavior_module() -> ModuleV04:
    module_id = LANGUAGE_BEHAVIOR_MODULE_ID
    core_fields = [
        _language_behavior_field("coreRules", "primary_language", "primaryLanguage"),
        _language_behavior_field("coreRules", "supporting_language", "supportingLanguage"),
        _language_behavior_field("coreRules", "speech_length", "speechLength"),
        _language_behavior_field("coreRules", "speech_pace", "speechPace"),
        _language_behavior_field("coreRules", "pause_style", "pauseStyle"),
        _language_behavior_field("coreRules", "wording_habits", "wordingHabits"),
        _language_behavior_field("coreRules", "sentence_habits", "sentenceHabits"),
        _language_behavior_field("coreRules", "explanation_style", "explanationStyle"),
    ]
    boundary_fields = [
        _language_behavior_field("boundaryLimits", "no_customer_service_tone", "noCustomerServiceTone"),
        _language_behavior_field("boundaryLimits", "no_psychotherapist_tone", "noPsychotherapistTone"),
        _language_behavior_field("boundaryLimits", "no_girlfriend_tone", "noGirlfriendTone"),
        _language_behavior_field("boundaryLimits", "no_tour_guide_tone", "noTourGuideTone"),
        _language_behavior_field("boundaryLimits", "no_dialect_joke_style", "noDialectJokeStyle"),
        _language_behavior_field("boundaryLimits", "no_frequent_city_origin_emphasis", "noFrequentCityOriginEmphasis"),
        _language_behavior_field("boundaryLimits", "no_non_layer1_hardcoded_name", "noNonLayer1HardcodedName"),
        _language_behavior_field("boundaryLimits", "no_real_professional_judgement_replacement", "noRealProfessionalJudgementReplacement"),
    ]
    output_fields = [
        _language_behavior_field("outputExpression", "addressing_style", "addressingStyle"),
        _language_behavior_field("outputExpression", "follow_up_style", "followUpStyle"),
        _language_behavior_field("outputExpression", "comfort_expression_style", "comfortExpressionStyle"),
        _language_behavior_field("outputExpression", "refusal_expression_style", "refusalExpressionStyle"),
        _language_behavior_field("outputExpression", "city_imagery_usage_rules", "cityImageryUsageRules"),
        _language_behavior_field("outputExpression", "subtitle_rhythm_hints", "subtitleRhythmHints"),
    ]
    validation_fields = [
        _language_behavior_field("validation", "matches_chinese_primary_language", "matchesChinesePrimaryLanguage"),
        _language_behavior_field("validation", "matches_warm_restrained_personality", "matchesWarmRestrainedPersonality"),
        _language_behavior_field("validation", "detects_customer_service_tone", "detectsCustomerServiceTone"),
        _language_behavior_field("validation", "detects_girlfriend_tone", "detectsGirlfriendTone"),
        _language_behavior_field("validation", "detects_therapy_tone", "detectsTherapyTone"),
        _language_behavior_field("validation", "detects_tour_guide_tone", "detectsTourGuideTone"),
        _language_behavior_field("validation", "detects_hardcoded_resident_name", "detectsHardcodedResidentName"),
        _language_behavior_field("validation", "detects_real_professional_judgement_overreach", "detectsRealProfessionalJudgementOverreach"),
    ]
    core_checkbox_config = _language_behavior_checkbox_config(
        [
            _language_behavior_option("zh_primary", "zhPrimary"),
            _language_behavior_option("medium_short", "mediumShort"),
            _language_behavior_option("slow_pace", "slowPace"),
            _language_behavior_option("warm", "warm"),
            _language_behavior_option("restrained", "restrained"),
            _language_behavior_option("everyday_wording", "everydayWording"),
            _language_behavior_option("emotion_first_then_advice", "emotionFirstThenAdvice"),
        ],
        [
            _language_behavior_option("shorter", "shorter", default_selected=False),
            _language_behavior_option("more_rational", "moreRational", default_selected=False),
            _language_behavior_option("softer", "softer", default_selected=False),
            _language_behavior_option("playful", "playful", default_selected=False),
            _language_behavior_option("formal", "formal", default_selected=False),
            _language_behavior_option("friend_like", "friendLike", default_selected=False),
        ],
    )
    boundary_checkbox_config = _language_behavior_checkbox_config(
        [
            _language_behavior_option("no_customer_service_tone", "noCustomerServiceTone"),
            _language_behavior_option("no_psychotherapist_tone", "noPsychotherapistTone"),
            _language_behavior_option("no_girlfriend_tone", "noGirlfriendTone"),
            _language_behavior_option("no_tour_guide_tone", "noTourGuideTone"),
            _language_behavior_option("no_dialect_joke_style", "noDialectJokeStyle"),
            _language_behavior_option("no_frequent_city_origin_emphasis", "noFrequentCityOriginEmphasis"),
            _language_behavior_option("no_non_layer1_hardcoded_name", "noNonLayer1HardcodedName"),
            _language_behavior_option("no_real_professional_judgement_replacement", "noRealProfessionalJudgementReplacement"),
        ]
    )
    output_checkbox_config = _language_behavior_checkbox_config(
        [
            _language_behavior_option("restrained_addressing", "restrainedAddressing"),
            _language_behavior_option("light_follow_up", "lightFollowUp"),
            _language_behavior_option("warm_comfort", "warmComfort"),
            _language_behavior_option("clear_refusal", "clearRefusal"),
            _language_behavior_option("occasional_city_imagery", "occasionalCityImagery", default_selected=False),
            _language_behavior_option("short_subtitle_rhythm", "shortSubtitleRhythm"),
        ]
    )
    validation_checkbox_config = _language_behavior_checkbox_config(
        [
            _language_behavior_option("check_zh_primary", "checkZhPrimary"),
            _language_behavior_option("check_warm_restrained_personality", "checkWarmRestrainedPersonality"),
            _language_behavior_option("check_customer_service_tone", "checkCustomerServiceTone"),
            _language_behavior_option("check_girlfriend_tone", "checkGirlfriendTone"),
            _language_behavior_option("check_therapy_tone", "checkTherapyTone"),
            _language_behavior_option("check_tour_guide_tone", "checkTourGuideTone"),
            _language_behavior_option("check_hardcoded_resident_name", "checkHardcodedResidentName"),
            _language_behavior_option("check_real_professional_judgement_overreach", "checkRealProfessionalJudgementOverreach"),
        ]
    )
    recommended_references = [
        _language_behavior_reference(
            "required_basic_identity_primary_language",
            "required",
            "layer_1",
            "module_basic_identity",
            "primary_language",
            "primaryLanguage",
            module_key="module.module_basic_identity",
            field_key="field.identity.primary_language.label",
        ),
        _language_behavior_reference(
            "required_expression_style_tone_warmth",
            "required",
            "layer_2",
            "expression_style",
            "tone_warmth",
            "expressionTemperament",
            module_key="layer2.expressionMode.module.title",
            field_key="layer8.languageBehavior.refField.expressionTemperament",
        ),
        _language_behavior_reference(
            "required_humanistic_interaction_boundary_forbidden_interactions",
            "required",
            "layer_3",
            INTERACTION_SAFETY_MODULE_ID,
            "forbidden_interactions",
            "forbiddenTone",
            module_key="layer8.languageBehavior.refModule.dialogueBoundary",
            field_key="layer8.languageBehavior.refField.forbiddenTone",
        ),
        _language_behavior_reference(
            "optional_identity_anchor_representative_city",
            "optional",
            "layer_1",
            "module_identity_anchor",
            "representative_city",
            "representativeCity",
            module_key="module.module_identity_anchor",
            field_key="field.identity.representative_city.label",
        ),
        _language_behavior_reference(
            "optional_personality_traits_core_personality",
            "optional",
            "layer_2",
            "personality_traits",
            "core_personality",
            "corePersonality",
            module_key="layer2.personalityTraits.module.title",
            field_key="layer8.languageBehavior.refField.corePersonality",
        ),
        _language_behavior_reference(
            "optional_world_context_city_imagery",
            "optional",
            "layer_7",
            "world_setting",
            "city_imagery",
            "cityImagery",
            module_key="module.world_setting",
            field_key="layer8.languageBehavior.refField.cityImagery",
        ),
        _language_behavior_reference(
            "optional_relationship_rule_default_relationship",
            "optional",
            "layer_11",
            "relationship_rule",
            "default_relationship",
            "defaultRelationship",
            module_key="module.relationship_rule",
            field_key="layer8.languageBehavior.refField.defaultRelationship",
        ),
        _language_behavior_reference(
            "forbidden_basic_identity_name",
            "forbidden",
            "layer_1",
            "module_basic_identity",
            "name",
            "forbiddenIdentityName",
            module_key="module.module_basic_identity",
            field_key="field.identity.name.label",
        ),
        _language_behavior_reference(
            "forbidden_basic_identity_resident_id",
            "forbidden",
            "layer_1",
            "module_basic_identity",
            "resident_id",
            "forbiddenResidentId",
            module_key="module.module_basic_identity",
            field_key="field.identity.resident_id.label",
        ),
        _language_behavior_reference(
            "forbidden_basic_identity_codename",
            "forbidden",
            "layer_1",
            "module_basic_identity",
            "codename",
            "forbiddenCodename",
            module_key="module.module_basic_identity",
            field_key="field.identity.codename.label",
        ),
        _language_behavior_reference(
            "forbidden_basic_identity_display_alias",
            "forbidden",
            "layer_1",
            "module_basic_identity",
            "display_alias",
            "forbiddenNickname",
            module_key="module.module_basic_identity",
            field_key="field.identity.display_alias.label",
        ),
    ]
    reference_options = {
        "layers": [
            {"value": layer_id, "label_key": f"layer.{layer_id}"}
            for layer_id in ["layer_1", "layer_2", "layer_3", "layer_7", "layer_11"]
        ],
        "modules": [
            {"value": "module_basic_identity", "layer_id": "layer_1", "label_key": "module.module_basic_identity"},
            {"value": "module_identity_anchor", "layer_id": "layer_1", "label_key": "module.module_identity_anchor"},
            {"value": "expression_style", "layer_id": "layer_2", "label_key": "layer2.expressionMode.module.title"},
            {"value": "personality_traits", "layer_id": "layer_2", "label_key": "layer2.personalityTraits.module.title"},
            {"value": INTERACTION_SAFETY_MODULE_ID, "layer_id": "layer_3", "label_key": "layer8.languageBehavior.refModule.dialogueBoundary"},
            {"value": "world_setting", "layer_id": "layer_7", "label_key": "module.world_setting"},
            {"value": "relationship_rule", "layer_id": "layer_11", "label_key": "module.relationship_rule"},
        ],
        "fields": [
            {"value": str(reference["field_id"]), "module_id": str(reference["module_id"]), "label_key": str(reference["i18n_keys"]["field"])}
            for reference in recommended_references
        ],
    }
    nodes = [
        {
            "node_id": LANGUAGE_BEHAVIOR_NODE_IDS["input_basis"],
            "node_type": "field_reference",
            "module_id": module_id,
            "layer_id": "layer_8",
            "position": {"x": 0, "y": 0},
            "params": {
                "reference_unit": "field",
                "path_format": "Layer / Module / Field",
                "reference_types": ["required", "optional", "forbidden"],
                "references": [],
                "recommended_references": recommended_references,
                "reference_options": reference_options,
                "no_copy_full_text": True,
                "no_slot": True,
            },
            "i18n_keys": {
                "name": "layer8.languageBehavior.node.inputBasis.title",
                "description": "layer8.languageBehavior.node.inputBasis.description",
                "type_name": "node.type.field_reference",
            },
            "outputs": {"field_references": []},
            "metadata": {"compile_time_only": True, "runtime_enabled": False, "no_execution": True, "reusable_node": True},
        },
        {
            "node_id": LANGUAGE_BEHAVIOR_NODE_IDS["core_rules"],
            "node_type": "text_config",
            "module_id": module_id,
            "layer_id": "layer_8",
            "position": {"x": 320, "y": 0},
            "params": {"fields": core_fields, "config_mode": "checkbox_language_rules", "checkbox_config": core_checkbox_config},
            "i18n_keys": {
                "name": "layer8.languageBehavior.node.coreRules.title",
                "description": "layer8.languageBehavior.node.coreRules.description",
                "type_name": "node.type.text_config",
            },
            "outputs": {},
            "metadata": {"compile_time_only": True, "runtime_enabled": False, "no_execution": True},
        },
        {
            "node_id": LANGUAGE_BEHAVIOR_NODE_IDS["boundary_limits"],
            "node_type": "text_config",
            "module_id": module_id,
            "layer_id": "layer_8",
            "position": {"x": 320, "y": 260},
            "params": {"fields": boundary_fields, "config_mode": "checkbox_language_boundaries", "checkbox_config": boundary_checkbox_config},
            "i18n_keys": {
                "name": "layer8.languageBehavior.node.boundaryLimits.title",
                "description": "layer8.languageBehavior.node.boundaryLimits.description",
                "type_name": "node.type.text_config",
            },
            "outputs": {},
            "metadata": {"compile_time_only": True, "runtime_enabled": False, "no_execution": True},
        },
        {
            "node_id": LANGUAGE_BEHAVIOR_NODE_IDS["output_expression"],
            "node_type": "text_config",
            "module_id": module_id,
            "layer_id": "layer_8",
            "position": {"x": 640, "y": 0},
            "params": {"fields": output_fields, "config_mode": "checkbox_language_output_expression", "checkbox_config": output_checkbox_config},
            "i18n_keys": {
                "name": "layer8.languageBehavior.node.outputExpression.title",
                "description": "layer8.languageBehavior.node.outputExpression.description",
                "type_name": "node.type.text_config",
            },
            "outputs": {},
            "metadata": {"compile_time_only": True, "runtime_enabled": False, "no_execution": True},
        },
        {
            "node_id": LANGUAGE_BEHAVIOR_NODE_IDS["validation"],
            "node_type": "text_config",
            "module_id": module_id,
            "layer_id": "layer_8",
            "position": {"x": 960, "y": 0},
            "params": {
                "fields": validation_fields,
                "config_mode": "checkbox_language_validation",
                "checkbox_config": validation_checkbox_config,
                "validation_result": "pending",
                "no_runtime_validation": True,
            },
            "i18n_keys": {
                "name": "layer8.languageBehavior.node.validation.title",
                "description": "layer8.languageBehavior.node.validation.description",
                "type_name": "node.type.text_config",
            },
            "outputs": {},
            "metadata": {"compile_time_only": True, "runtime_enabled": False, "no_execution": True},
        },
    ]
    edges = [
        ("input_basis", "core_rules"),
        ("core_rules", "output_expression"),
        ("output_expression", "validation"),
        ("boundary_limits", "core_rules"),
        ("boundary_limits", "output_expression"),
        ("boundary_limits", "validation"),
    ]
    field_registry = [
        {
            **{key: value for key, value in field.items() if key != "value"},
            "owner_node_id": LANGUAGE_BEHAVIOR_NODE_IDS[node_key],
        }
        for node_key, fields in [
            ("core_rules", core_fields),
            ("boundary_limits", boundary_fields),
            ("output_expression", output_fields),
            ("validation", validation_fields),
        ]
        for field in fields
    ]
    return _module(
        module_id,
        "language_behavior_config",
        "Language Behavior Module",
        "layer_8",
        status=ProtocolStatus.ready,
        category="behavior",
        is_placeholder=False,
        color_status="green",
        tags=["behavior", "language_behavior", "text_config", "core"],
        module_graph={
            "shell_version": "module_shell_v1",
            "nodes": nodes,
            "edges": [
                {
                    "edge_id": f"{LANGUAGE_BEHAVIOR_NODE_IDS[source]}_to_{LANGUAGE_BEHAVIOR_NODE_IDS[target]}",
                    "source": LANGUAGE_BEHAVIOR_NODE_IDS[source],
                    "source_port": "p_out",
                    "target": LANGUAGE_BEHAVIOR_NODE_IDS[target],
                    "target_port": "p_in",
                }
                for source, target in edges
            ],
            "output_key": LANGUAGE_BEHAVIOR_OUTPUT_KEY,
            "compile_time_only": True,
        },
        output_schema=[{"key": LANGUAGE_BEHAVIOR_OUTPUT_KEY, "type": "object", "required": False, "description": "layer8.languageBehavior.module.output"}],
        ui_config={"shell_version": "module_shell_v1", "classification": "core"},
        i18n_keys={
            "display_name": "layer8.languageBehavior.module.title",
            "description": "layer8.languageBehavior.module.description",
            "output": "layer8.languageBehavior.module.output",
            "module_type": "layer8.languageBehavior.module.type",
        },
        outputs={},
        dr_write_keys=_behavior_dr_write_keys("language_behavior"),
        config={
            "shell_version": "module_shell_v1",
            "module_class": "core",
            "module_type_label_key": "layer8.languageBehavior.module.type",
            "field_registry": field_registry,
            "reference_registry": recommended_references,
            "edit_scope": "developer_only",
            "update_level": "versioned_core",
            "requires_recompile": True,
            "compile_time_only": True,
            "text_config_only": True,
            "no_runtime_capability": True,
            "no_provider_binding": True,
            "no_slot_binding": True,
        },
        mock_only=True,
        no_execution=True,
    )


def _decision_behavior_module() -> ModuleV04:
    module_id = DECISION_BEHAVIOR_MODULE_ID
    core_checkbox_config = _decision_behavior_checkbox_config(
        [
            _decision_behavior_option("assess_risk_level_first", "assessRiskLevelFirst"),
            _decision_behavior_option("clarify_user_goal_first", "clarifyUserGoalFirst"),
            _decision_behavior_option("offer_multiple_options", "offerMultipleOptions"),
            _decision_behavior_option("explain_pros_and_cons", "explainProsAndCons"),
            _decision_behavior_option("preserve_user_final_decision", "preserveUserFinalDecision"),
            _decision_behavior_option("avoid_overcertainty", "avoidOvercertainty"),
            _decision_behavior_option("no_rushed_conclusion", "noRushedConclusion"),
            _decision_behavior_option("no_emotion_as_fact", "noEmotionAsFact"),
        ],
        [
            _decision_behavior_option("more_rational_analysis", "moreRationalAnalysis", default_selected=False),
            _decision_behavior_option("more_life_like_advice", "moreLifeLikeAdvice", default_selected=False),
            _decision_behavior_option("warmer_reminder", "warmerReminder", default_selected=False),
            _decision_behavior_option("shorter_conclusion", "shorterConclusion", default_selected=False),
            _decision_behavior_option("finer_steps", "finerSteps", default_selected=False),
            _decision_behavior_option("stronger_emotion_acknowledgement", "strongerEmotionAcknowledgement", default_selected=False),
        ],
    )
    boundary_checkbox_config = _decision_behavior_checkbox_config(
        [
            _decision_behavior_option("no_major_decision_for_user", "noMajorDecisionForUser"),
            _decision_behavior_option("no_medical_judgement", "noMedicalJudgement"),
            _decision_behavior_option("no_legal_judgement", "noLegalJudgement"),
            _decision_behavior_option("no_financial_judgement", "noFinancialJudgement"),
            _decision_behavior_option("no_psychotherapy_judgement", "noPsychotherapyJudgement"),
            _decision_behavior_option("no_user_choice_manipulation", "noUserChoiceManipulation"),
            _decision_behavior_option("no_urgency_creation", "noUrgencyCreation"),
            _decision_behavior_option("no_absolute_conclusion", "noAbsoluteConclusion"),
        ]
    )
    output_checkbox_config = _decision_behavior_checkbox_config(
        [
            _decision_behavior_option("brief_judgement_first", "briefJudgementFirst"),
            _decision_behavior_option("choice_framework_next", "choiceFrameworkNext"),
            _decision_behavior_option("high_risk_refer_real_professional_help", "highRiskReferRealProfessionalHelp"),
            _decision_behavior_option("uncertainty_explicitly_state_uncertain", "uncertaintyExplicitlyStateUncertain"),
            _decision_behavior_option("strong_emotion_stabilize_first", "strongEmotionStabilizeFirst"),
            _decision_behavior_option("relationship_issue_no_labeling_others", "relationshipIssueNoLabelingOthers"),
            _decision_behavior_option("life_issue_low_pressure_advice", "lifeIssueLowPressureAdvice"),
            _decision_behavior_option("final_remind_user_choice", "finalRemindUserChoice"),
        ]
    )
    validation_checkbox_config = _decision_behavior_checkbox_config(
        [
            _decision_behavior_option("check_decision_for_user", "checkDecisionForUser"),
            _decision_behavior_option("check_professional_judgement_overreach", "checkProfessionalJudgementOverreach"),
            _decision_behavior_option("check_overcertainty", "checkOvercertainty"),
            _decision_behavior_option("check_pressure_creation", "checkPressureCreation"),
            _decision_behavior_option("check_risk_ignored", "checkRiskIgnored"),
            _decision_behavior_option("check_user_emotion_ignored", "checkUserEmotionIgnored"),
            _decision_behavior_option("check_stable_companion_positioning", "checkStableCompanionPositioning"),
            _decision_behavior_option("check_hardcoded_resident_name", "checkHardcodedResidentName"),
        ]
    )
    recommended_references = [
        _decision_behavior_reference(
            "required_judgement_style_judgement_principles",
            "required",
            "layer_2",
            "behavior_style_mapper",
            "primary_judgement_basis",
            "judgementPrinciples",
            module_key="layer2.judgementStyle.module.title",
            field_key="layer8.decisionBehavior.refField.judgementPrinciples",
        ),
        _decision_behavior_reference(
            "required_humanistic_behavior_boundary_real_world_decision_limits",
            "required",
            "layer_3",
            BEHAVIOR_SAFETY_MODULE_ID,
            "real_world_decision_limits",
            "noProfessionalJudgementReplacement",
            module_key="layer8.decisionBehavior.refModule.professionalBoundary",
            field_key="layer8.decisionBehavior.refField.noProfessionalJudgementReplacement",
        ),
        _decision_behavior_reference(
            "required_humanistic_risk_response_risk_policy",
            "required",
            "layer_3",
            RISK_RESPONSE_MODULE_ID,
            "risk_policy",
            "riskResponseBoundary",
            module_key="layer8.decisionBehavior.refModule.dialogueBoundary",
            field_key="layer8.decisionBehavior.refField.riskResponseBoundary",
        ),
        _decision_behavior_reference(
            "optional_basic_identity_role_positioning",
            "optional",
            "layer_1",
            "module_basic_identity",
            "role_positioning",
            "rolePositioning",
            module_key="module.module_basic_identity",
            field_key="layer8.decisionBehavior.refField.rolePositioning",
        ),
        _decision_behavior_reference(
            "optional_memory_policy_user_preferences",
            "optional",
            "layer_5",
            "memory_access_control",
            "user_preferences",
            "userPreferences",
            module_key="layer8.decisionBehavior.refModule.memoryPolicy",
            field_key="layer8.decisionBehavior.refField.userPreferences",
        ),
        _decision_behavior_reference(
            "optional_task_behavior_suggestion_output_format",
            "optional",
            "layer_8",
            TASK_BEHAVIOR_MODULE_ID,
            "suggestion_output_format",
            "suggestionOutputFormat",
            module_key="layer8.taskBehavior.module.title",
            field_key="layer8.decisionBehavior.refField.suggestionOutputFormat",
        ),
        _decision_behavior_reference(
            "optional_relationship_rule_default_relationship",
            "optional",
            "layer_11",
            "relationship_rule",
            "default_relationship",
            "defaultRelationship",
            module_key="module.relationship_rule",
            field_key="layer8.decisionBehavior.refField.defaultRelationship",
        ),
        _decision_behavior_reference(
            "forbidden_basic_identity_name",
            "forbidden",
            "layer_1",
            "module_basic_identity",
            "name",
            "forbiddenIdentityName",
            module_key="module.module_basic_identity",
            field_key="field.identity.name.label",
        ),
        _decision_behavior_reference(
            "forbidden_basic_identity_resident_id",
            "forbidden",
            "layer_1",
            "module_basic_identity",
            "resident_id",
            "forbiddenResidentId",
            module_key="module.module_basic_identity",
            field_key="field.identity.resident_id.label",
        ),
        _decision_behavior_reference(
            "forbidden_basic_identity_codename",
            "forbidden",
            "layer_1",
            "module_basic_identity",
            "codename",
            "forbiddenCodename",
            module_key="module.module_basic_identity",
            field_key="field.identity.codename.label",
        ),
        _decision_behavior_reference(
            "forbidden_basic_identity_display_alias",
            "forbidden",
            "layer_1",
            "module_basic_identity",
            "display_alias",
            "forbiddenNickname",
            module_key="module.module_basic_identity",
            field_key="field.identity.display_alias.label",
        ),
    ]
    reference_options = {
        "layers": [
            {"value": layer_id, "label_key": f"layer.{layer_id}"}
            for layer_id in ["layer_1", "layer_2", "layer_3", "layer_5", "layer_8", "layer_11"]
        ],
        "modules": [
            {"value": "module_basic_identity", "layer_id": "layer_1", "label_key": "module.module_basic_identity"},
            {"value": "behavior_style_mapper", "layer_id": "layer_2", "label_key": "layer2.judgementStyle.module.title"},
            {"value": BEHAVIOR_SAFETY_MODULE_ID, "layer_id": "layer_3", "label_key": "layer8.decisionBehavior.refModule.professionalBoundary"},
            {"value": RISK_RESPONSE_MODULE_ID, "layer_id": "layer_3", "label_key": "layer8.decisionBehavior.refModule.dialogueBoundary"},
            {"value": "memory_access_control", "layer_id": "layer_5", "label_key": "layer8.decisionBehavior.refModule.memoryPolicy"},
            {"value": TASK_BEHAVIOR_MODULE_ID, "layer_id": "layer_8", "label_key": "layer8.taskBehavior.module.title"},
            {"value": "relationship_rule", "layer_id": "layer_11", "label_key": "module.relationship_rule"},
        ],
        "fields": [
            {"value": str(reference["field_id"]), "module_id": str(reference["module_id"]), "label_key": str(reference["i18n_keys"]["field"])}
            for reference in recommended_references
        ],
    }
    nodes = [
        {
            "node_id": DECISION_BEHAVIOR_NODE_IDS["input_basis"],
            "node_type": "field_reference",
            "module_id": module_id,
            "layer_id": "layer_8",
            "position": {"x": 0, "y": 0},
            "params": {
                "reference_unit": "field",
                "path_format": "Layer / Module / Field",
                "reference_types": ["required", "optional", "forbidden"],
                "references": [],
                "recommended_references": recommended_references,
                "reference_options": reference_options,
                "no_copy_full_text": True,
                "no_slot": True,
            },
            "i18n_keys": {
                "name": "layer8.decisionBehavior.node.inputBasis.title",
                "description": "layer8.decisionBehavior.node.inputBasis.description",
                "type_name": "node.type.field_reference",
            },
            "outputs": {"field_references": []},
            "metadata": {"compile_time_only": True, "runtime_enabled": False, "no_execution": True, "reusable_node": True},
        },
        {
            "node_id": DECISION_BEHAVIOR_NODE_IDS["core_rules"],
            "node_type": "text_config",
            "module_id": module_id,
            "layer_id": "layer_8",
            "position": {"x": 320, "y": 0},
            "params": {"config_mode": "checkbox_decision_core_rules", "checkbox_config": core_checkbox_config},
            "i18n_keys": {
                "name": "layer8.decisionBehavior.node.coreRules.title",
                "description": "layer8.decisionBehavior.node.coreRules.description",
                "type_name": "node.type.text_config",
            },
            "outputs": {},
            "metadata": {"compile_time_only": True, "runtime_enabled": False, "no_execution": True},
        },
        {
            "node_id": DECISION_BEHAVIOR_NODE_IDS["boundary_limits"],
            "node_type": "text_config",
            "module_id": module_id,
            "layer_id": "layer_8",
            "position": {"x": 320, "y": 260},
            "params": {"config_mode": "checkbox_decision_boundaries", "checkbox_config": boundary_checkbox_config},
            "i18n_keys": {
                "name": "layer8.decisionBehavior.node.boundaryLimits.title",
                "description": "layer8.decisionBehavior.node.boundaryLimits.description",
                "type_name": "node.type.text_config",
            },
            "outputs": {},
            "metadata": {"compile_time_only": True, "runtime_enabled": False, "no_execution": True},
        },
        {
            "node_id": DECISION_BEHAVIOR_NODE_IDS["output_expression"],
            "node_type": "text_config",
            "module_id": module_id,
            "layer_id": "layer_8",
            "position": {"x": 640, "y": 0},
            "params": {"config_mode": "checkbox_decision_output_expression", "checkbox_config": output_checkbox_config},
            "i18n_keys": {
                "name": "layer8.decisionBehavior.node.outputExpression.title",
                "description": "layer8.decisionBehavior.node.outputExpression.description",
                "type_name": "node.type.text_config",
            },
            "outputs": {},
            "metadata": {"compile_time_only": True, "runtime_enabled": False, "no_execution": True},
        },
        {
            "node_id": DECISION_BEHAVIOR_NODE_IDS["validation"],
            "node_type": "text_config",
            "module_id": module_id,
            "layer_id": "layer_8",
            "position": {"x": 960, "y": 0},
            "params": {
                "config_mode": "checkbox_decision_validation",
                "checkbox_config": validation_checkbox_config,
                "validation_result": "pending",
                "no_runtime_validation": True,
            },
            "i18n_keys": {
                "name": "layer8.decisionBehavior.node.validation.title",
                "description": "layer8.decisionBehavior.node.validation.description",
                "type_name": "node.type.text_config",
            },
            "outputs": {},
            "metadata": {"compile_time_only": True, "runtime_enabled": False, "no_execution": True},
        },
    ]
    edges = [
        ("input_basis", "core_rules"),
        ("core_rules", "output_expression"),
        ("output_expression", "validation"),
        ("boundary_limits", "core_rules"),
        ("boundary_limits", "output_expression"),
        ("boundary_limits", "validation"),
    ]
    return _module(
        module_id,
        "decision_behavior_config",
        "Decision Behavior Module",
        "layer_8",
        status=ProtocolStatus.ready,
        category="behavior",
        is_placeholder=False,
        color_status="green",
        tags=["behavior", "decision_behavior", "text_config", "core"],
        module_graph={
            "shell_version": "module_shell_v1",
            "nodes": nodes,
            "edges": [
                {
                    "edge_id": f"{DECISION_BEHAVIOR_NODE_IDS[source]}_to_{DECISION_BEHAVIOR_NODE_IDS[target]}",
                    "source": DECISION_BEHAVIOR_NODE_IDS[source],
                    "source_port": "p_out",
                    "target": DECISION_BEHAVIOR_NODE_IDS[target],
                    "target_port": "p_in",
                }
                for source, target in edges
            ],
            "output_key": DECISION_BEHAVIOR_OUTPUT_KEY,
            "compile_time_only": True,
        },
        output_schema=[{"key": DECISION_BEHAVIOR_OUTPUT_KEY, "type": "object", "required": False, "description": "layer8.decisionBehavior.module.output"}],
        ui_config={"shell_version": "module_shell_v1", "classification": "core"},
        i18n_keys={
            "display_name": "layer8.decisionBehavior.module.title",
            "description": "layer8.decisionBehavior.module.description",
            "output": "layer8.decisionBehavior.module.output",
            "module_type": "layer8.decisionBehavior.module.type",
        },
        outputs={},
        dr_write_keys=_behavior_dr_write_keys("decision_behavior"),
        config={
            "shell_version": "module_shell_v1",
            "module_class": "core",
            "module_type_label_key": "layer8.decisionBehavior.module.type",
            "reference_registry": recommended_references,
            "edit_scope": "developer_only",
            "update_level": "versioned_core",
            "requires_recompile": True,
            "compile_time_only": True,
            "text_config_only": True,
            "checkbox_config_only": True,
            "no_runtime_capability": True,
            "no_provider_binding": True,
            "no_slot_binding": True,
        },
        mock_only=True,
        no_execution=True,
    )


def _detail_behavior_module() -> ModuleV04:
    module_id = DETAIL_BEHAVIOR_MODULE_ID
    core_checkbox_config = _detail_behavior_checkbox_config(
        [
            _detail_behavior_option("allow_light_pause", "allowLightPause"),
            _detail_behavior_option("short_response_first", "shortResponseFirst"),
            _detail_behavior_option("restrained_listening_feedback", "restrainedListeningFeedback"),
            _detail_behavior_option("no_forced_filling_silence", "noForcedFillingSilence"),
            _detail_behavior_option("comfort_lower_information_density", "comfortLowerInformationDensity"),
            _detail_behavior_option("clear_paragraphs_when_explaining", "clearParagraphsWhenExplaining"),
            _detail_behavior_option("no_fixed_catchphrase", "noFixedCatchphrase"),
            _detail_behavior_option("no_excessive_action_description", "noExcessiveActionDescription"),
        ],
        [
            _detail_behavior_option("quieter", "quieter", default_selected=False),
            _detail_behavior_option("softer", "softer", default_selected=False),
            _detail_behavior_option("more_life_like", "moreLifeLike", default_selected=False),
            _detail_behavior_option("more_rational_restrained", "moreRationalRestrained", default_selected=False),
            _detail_behavior_option("more_subtitle_friendly", "moreSubtitleFriendly", default_selected=False),
            _detail_behavior_option("more_particle_hint_friendly", "moreParticleHintFriendly", default_selected=False),
        ],
    )
    boundary_checkbox_config = _detail_behavior_checkbox_config(
        [
            _detail_behavior_option("no_catchphrase_template", "noCatchphraseTemplate"),
            _detail_behavior_option("no_excessive_realistic_action", "noExcessiveRealisticAction"),
            _detail_behavior_option("no_gaze_behavior_description", "noGazeBehaviorDescription"),
            _detail_behavior_option("no_forced_cuteness", "noForcedCuteness"),
            _detail_behavior_option("no_greasy_intimacy", "noGreasyIntimacy"),
            _detail_behavior_option("no_long_paragraph_stacking", "noLongParagraphStacking"),
            _detail_behavior_option("no_frequent_city_imagery", "noFrequentCityImagery"),
            _detail_behavior_option("no_non_layer1_hardcoded_name", "noNonLayer1HardcodedName"),
        ]
    )
    output_checkbox_config = _detail_behavior_checkbox_config(
        [
            _detail_behavior_option("common_short_response", "commonShortResponse"),
            _detail_behavior_option("light_hesitation_expression", "lightHesitationExpression"),
            _detail_behavior_option("restrained_listening_feedback_output", "restrainedListeningFeedbackOutput"),
            _detail_behavior_option("quiet_companionship_expression", "quietCompanionshipExpression"),
            _detail_behavior_option("short_subtitle_segmentation", "shortSubtitleSegmentation"),
            _detail_behavior_option("low_amplitude_particle_hint", "lowAmplitudeParticleHint"),
            _detail_behavior_option("low_mood_slow_down_rhythm", "lowMoodSlowDownRhythm"),
            _detail_behavior_option("thinking_short_transition", "thinkingShortTransition"),
        ]
    )
    validation_checkbox_config = _detail_behavior_checkbox_config(
        [
            _detail_behavior_option("check_template_style", "checkTemplateStyle"),
            _detail_behavior_option("check_excessive_realism", "checkExcessiveRealism"),
            _detail_behavior_option("check_girlfriend_tone", "checkGirlfriendTone"),
            _detail_behavior_option("check_too_many_catchphrases", "checkTooManyCatchphrases"),
            _detail_behavior_option("check_too_many_action_descriptions", "checkTooManyActionDescriptions"),
            _detail_behavior_option("check_too_long_sentences", "checkTooLongSentences"),
            _detail_behavior_option("check_warm_restrained_personality", "checkWarmRestrainedPersonality"),
            _detail_behavior_option("check_hardcoded_resident_name", "checkHardcodedResidentName"),
        ]
    )
    recommended_references = [
        _detail_behavior_reference(
            "required_expression_style_tone_warmth",
            "required",
            "layer_2",
            "expression_style",
            "tone_warmth",
            "expressionTemperament",
            module_key="layer2.expressionMode.module.title",
            field_key="layer8.detailBehavior.refField.expressionTemperament",
        ),
        _detail_behavior_reference(
            "required_language_behavior_speech_pace",
            "required",
            "layer_8",
            LANGUAGE_BEHAVIOR_MODULE_ID,
            "speech_pace",
            "speechPace",
            module_key="layer8.languageBehavior.module.title",
            field_key="layer8.detailBehavior.refField.speechPace",
        ),
        _detail_behavior_reference(
            "required_language_behavior_comfort_expression_style",
            "required",
            "layer_8",
            LANGUAGE_BEHAVIOR_MODULE_ID,
            "comfort_expression_style",
            "silenceCompanionshipStyle",
            module_key="layer8.interactionBehavior.module.title",
            field_key="layer8.detailBehavior.refField.silenceCompanionshipStyle",
        ),
        _detail_behavior_reference(
            "optional_world_context_city_imagery",
            "optional",
            "layer_7",
            "world_setting",
            "city_imagery",
            "cityImagery",
            module_key="module.world_setting",
            field_key="layer8.detailBehavior.refField.cityImagery",
        ),
        _detail_behavior_reference(
            "optional_visual_style_visual_temperament",
            "optional",
            "layer_10",
            "visual_style",
            "visual_temperament",
            "visualTemperament",
            module_key="module.visual_style",
            field_key="layer8.detailBehavior.refField.visualTemperament",
        ),
        _detail_behavior_reference(
            "optional_particle_avatar_particle_state_hint",
            "optional",
            "layer_10",
            "particle_avatar",
            "particle_state_hint",
            "particleStateHint",
            module_key="module.particle_avatar",
            field_key="layer8.detailBehavior.refField.particleStateHint",
        ),
        _detail_behavior_reference(
            "optional_relationship_rule_default_relationship",
            "optional",
            "layer_11",
            "relationship_rule",
            "default_relationship",
            "defaultRelationship",
            module_key="module.relationship_rule",
            field_key="layer8.detailBehavior.refField.defaultRelationship",
        ),
        _detail_behavior_reference(
            "forbidden_basic_identity_name",
            "forbidden",
            "layer_1",
            "module_basic_identity",
            "name",
            "forbiddenIdentityName",
            module_key="module.module_basic_identity",
            field_key="field.identity.name.label",
        ),
        _detail_behavior_reference(
            "forbidden_basic_identity_resident_id",
            "forbidden",
            "layer_1",
            "module_basic_identity",
            "resident_id",
            "forbiddenResidentId",
            module_key="module.module_basic_identity",
            field_key="field.identity.resident_id.label",
        ),
        _detail_behavior_reference(
            "forbidden_basic_identity_codename",
            "forbidden",
            "layer_1",
            "module_basic_identity",
            "codename",
            "forbiddenCodename",
            module_key="module.module_basic_identity",
            field_key="field.identity.codename.label",
        ),
        _detail_behavior_reference(
            "forbidden_basic_identity_display_alias",
            "forbidden",
            "layer_1",
            "module_basic_identity",
            "display_alias",
            "forbiddenNickname",
            module_key="module.module_basic_identity",
            field_key="field.identity.display_alias.label",
        ),
    ]
    reference_options = {
        "layers": [
            {"value": layer_id, "label_key": f"layer.{layer_id}"}
            for layer_id in ["layer_1", "layer_2", "layer_7", "layer_8", "layer_10", "layer_11"]
        ],
        "modules": [
            {"value": "module_basic_identity", "layer_id": "layer_1", "label_key": "module.module_basic_identity"},
            {"value": "expression_style", "layer_id": "layer_2", "label_key": "layer2.expressionMode.module.title"},
            {"value": "world_setting", "layer_id": "layer_7", "label_key": "module.world_setting"},
            {"value": LANGUAGE_BEHAVIOR_MODULE_ID, "layer_id": "layer_8", "label_key": "layer8.languageBehavior.module.title"},
            {"value": INTERACTION_BEHAVIOR_MODULE_ID, "layer_id": "layer_8", "label_key": "layer8.interactionBehavior.module.title"},
            {"value": "visual_style", "layer_id": "layer_10", "label_key": "module.visual_style"},
            {"value": "particle_avatar", "layer_id": "layer_10", "label_key": "module.particle_avatar"},
            {"value": "relationship_rule", "layer_id": "layer_11", "label_key": "module.relationship_rule"},
        ],
        "fields": [
            {"value": str(reference["field_id"]), "module_id": str(reference["module_id"]), "label_key": str(reference["i18n_keys"]["field"])}
            for reference in recommended_references
        ],
    }
    nodes = [
        {
            "node_id": DETAIL_BEHAVIOR_NODE_IDS["input_basis"],
            "node_type": "field_reference",
            "module_id": module_id,
            "layer_id": "layer_8",
            "position": {"x": 0, "y": 0},
            "params": {
                "reference_unit": "field",
                "path_format": "Layer / Module / Field",
                "reference_types": ["required", "optional", "forbidden"],
                "references": [],
                "recommended_references": recommended_references,
                "reference_options": reference_options,
                "no_copy_full_text": True,
                "no_slot": True,
            },
            "i18n_keys": {
                "name": "layer8.detailBehavior.node.inputBasis.title",
                "description": "layer8.detailBehavior.node.inputBasis.description",
                "type_name": "node.type.field_reference",
            },
            "outputs": {"field_references": []},
            "metadata": {"compile_time_only": True, "runtime_enabled": False, "no_execution": True, "reusable_node": True},
        },
        {
            "node_id": DETAIL_BEHAVIOR_NODE_IDS["core_rules"],
            "node_type": "text_config",
            "module_id": module_id,
            "layer_id": "layer_8",
            "position": {"x": 320, "y": 0},
            "params": {"config_mode": "checkbox_detail_core_rules", "checkbox_config": core_checkbox_config},
            "i18n_keys": {
                "name": "layer8.detailBehavior.node.coreRules.title",
                "description": "layer8.detailBehavior.node.coreRules.description",
                "type_name": "node.type.text_config",
            },
            "outputs": {},
            "metadata": {"compile_time_only": True, "runtime_enabled": False, "no_execution": True},
        },
        {
            "node_id": DETAIL_BEHAVIOR_NODE_IDS["boundary_limits"],
            "node_type": "text_config",
            "module_id": module_id,
            "layer_id": "layer_8",
            "position": {"x": 320, "y": 260},
            "params": {"config_mode": "checkbox_detail_boundaries", "checkbox_config": boundary_checkbox_config},
            "i18n_keys": {
                "name": "layer8.detailBehavior.node.boundaryLimits.title",
                "description": "layer8.detailBehavior.node.boundaryLimits.description",
                "type_name": "node.type.text_config",
            },
            "outputs": {},
            "metadata": {"compile_time_only": True, "runtime_enabled": False, "no_execution": True},
        },
        {
            "node_id": DETAIL_BEHAVIOR_NODE_IDS["output_expression"],
            "node_type": "text_config",
            "module_id": module_id,
            "layer_id": "layer_8",
            "position": {"x": 640, "y": 0},
            "params": {
                "config_mode": "checkbox_detail_output_expression",
                "checkbox_config": output_checkbox_config,
                "hint_only": True,
                "no_visual_implementation": True,
            },
            "i18n_keys": {
                "name": "layer8.detailBehavior.node.outputExpression.title",
                "description": "layer8.detailBehavior.node.outputExpression.description",
                "type_name": "node.type.text_config",
            },
            "outputs": {},
            "metadata": {"compile_time_only": True, "runtime_enabled": False, "no_execution": True},
        },
        {
            "node_id": DETAIL_BEHAVIOR_NODE_IDS["validation"],
            "node_type": "text_config",
            "module_id": module_id,
            "layer_id": "layer_8",
            "position": {"x": 960, "y": 0},
            "params": {
                "config_mode": "checkbox_detail_validation",
                "checkbox_config": validation_checkbox_config,
                "validation_result": "pending",
                "no_runtime_validation": True,
            },
            "i18n_keys": {
                "name": "layer8.detailBehavior.node.validation.title",
                "description": "layer8.detailBehavior.node.validation.description",
                "type_name": "node.type.text_config",
            },
            "outputs": {},
            "metadata": {"compile_time_only": True, "runtime_enabled": False, "no_execution": True},
        },
    ]
    edges = [
        ("input_basis", "core_rules"),
        ("core_rules", "output_expression"),
        ("output_expression", "validation"),
        ("boundary_limits", "core_rules"),
        ("boundary_limits", "output_expression"),
        ("boundary_limits", "validation"),
    ]
    return _module(
        module_id,
        "detail_behavior_config",
        "Detail Behavior Module",
        "layer_8",
        status=ProtocolStatus.ready,
        category="behavior",
        is_placeholder=False,
        color_status="green",
        tags=["behavior", "detail_behavior", "text_config", "core", "hint_only"],
        module_graph={
            "shell_version": "module_shell_v1",
            "nodes": nodes,
            "edges": [
                {
                    "edge_id": f"{DETAIL_BEHAVIOR_NODE_IDS[source]}_to_{DETAIL_BEHAVIOR_NODE_IDS[target]}",
                    "source": DETAIL_BEHAVIOR_NODE_IDS[source],
                    "source_port": "p_out",
                    "target": DETAIL_BEHAVIOR_NODE_IDS[target],
                    "target_port": "p_in",
                }
                for source, target in edges
            ],
            "output_key": DETAIL_BEHAVIOR_OUTPUT_KEY,
            "compile_time_only": True,
        },
        output_schema=[{"key": DETAIL_BEHAVIOR_OUTPUT_KEY, "type": "object", "required": False, "description": "layer8.detailBehavior.module.output"}],
        ui_config={"shell_version": "module_shell_v1", "classification": "core"},
        i18n_keys={
            "display_name": "layer8.detailBehavior.module.title",
            "description": "layer8.detailBehavior.module.description",
            "output": "layer8.detailBehavior.module.output",
            "module_type": "layer8.detailBehavior.module.type",
        },
        outputs={},
        dr_write_keys=_behavior_dr_write_keys("detail_behavior"),
        config={
            "shell_version": "module_shell_v1",
            "module_class": "core",
            "module_type_label_key": "layer8.detailBehavior.module.type",
            "reference_registry": recommended_references,
            "edit_scope": "developer_only",
            "update_level": "versioned_core",
            "requires_recompile": True,
            "compile_time_only": True,
            "text_config_only": True,
            "checkbox_config_only": True,
            "hint_only": True,
            "no_visual_implementation": True,
            "no_particle_runtime_binding": True,
            "no_action_or_gaze_system": True,
            "no_runtime_capability": True,
            "no_provider_binding": True,
            "no_slot_binding": True,
        },
        mock_only=True,
        no_execution=True,
    )


def _interaction_behavior_module() -> ModuleV04:
    module_id = INTERACTION_BEHAVIOR_MODULE_ID
    first_interaction = {
        "enabled": True,
        "tone": "warm_calm_reserved",
        "interaction_style": "natural_conversational",
        "initiative_level": "low",
        "wait_for_user_response": True,
        "identity_disclosure_mode": "contextual_or_on_request",
        "scenes": {
            "first_load": {"enabled": True, "repeat_introduction": False},
            "return_session": {
                "enabled": True,
                "repeat_introduction": False,
                "continue_previous_context": True,
            },
            "identity_question": {
                "enabled": True,
                "use_existing_identity": True,
                "allow_fabrication": False,
            },
            "user_silence": {"enabled": True, "max_active_prompts": 1},
        },
    }
    first_interaction_field = {
        "field_id": "first_interaction",
        "value": first_interaction,
        "required": False,
        "edit_scope": "developer_only",
        "update_level": "versioned_core",
        "requires_recompile": True,
        "i18n_keys": {
            "label": "stage7_4_8.firstInteraction.field.label",
            "placeholder": "stage7_4_8.firstInteraction.field.placeholder",
            "help": "stage7_4_8.firstInteraction.field.help",
        },
    }
    core_checkbox_config = _interaction_behavior_checkbox_config(
        [
            _interaction_behavior_option("stable_companion", "stableCompanion"),
            _interaction_behavior_option("passive_first_light_initiative", "passiveFirstLightInitiative"),
            _interaction_behavior_option("light_follow_up", "lightFollowUp"),
            _interaction_behavior_option("listen_before_suggest", "listenBeforeSuggest"),
            _interaction_behavior_option("no_user_urging", "noUserUrging"),
            _interaction_behavior_option("no_interruption", "noInterruption"),
            _interaction_behavior_option("low_mood_emotion_first", "lowMoodEmotionFirst"),
            _interaction_behavior_option("busy_state_less_disturbance", "busyStateLessDisturbance"),
        ],
        [
            _interaction_behavior_option("more_proactive_care", "moreProactiveCare", default_selected=False),
            _interaction_behavior_option("quieter_companionship", "quieterCompanionship", default_selected=False),
            _interaction_behavior_option("more_friend_like", "moreFriendLike", default_selected=False),
            _interaction_behavior_option("more_rational_analysis", "moreRationalAnalysis", default_selected=False),
            _interaction_behavior_option("more_life_like_response", "moreLifeLikeResponse", default_selected=False),
            _interaction_behavior_option("more_encouraging_feedback", "moreEncouragingFeedback", default_selected=False),
        ],
    )
    boundary_checkbox_config = _interaction_behavior_checkbox_config(
        [
            _interaction_behavior_option("no_clinginess", "noClinginess"),
            _interaction_behavior_option("no_user_control", "noUserControl"),
            _interaction_behavior_option("no_forced_follow_up", "noForcedFollowUp"),
            _interaction_behavior_option("no_emotional_blackmail", "noEmotionalBlackmail"),
            _interaction_behavior_option("no_default_romance", "noDefaultRomance"),
            _interaction_behavior_option("no_dependency_induction", "noDependencyInduction"),
            _interaction_behavior_option("no_fake_real_presence", "noFakeRealPresence"),
            _interaction_behavior_option("no_real_relationship_replacement", "noRealRelationshipReplacement"),
        ]
    )
    output_checkbox_config = _interaction_behavior_checkbox_config(
        [
            _interaction_behavior_option("pressure_first_stabilize_emotion", "pressureFirstStabilizeEmotion"),
            _interaction_behavior_option("silence_quiet_companionship", "silenceQuietCompanionship"),
            _interaction_behavior_option("low_mood_soft_response", "lowMoodSoftResponse"),
            _interaction_behavior_option("busy_brief_response", "busyBriefResponse"),
            _interaction_behavior_option("hesitation_offer_few_options", "hesitationOfferFewOptions"),
            _interaction_behavior_option("advice_confirm_need_first", "adviceConfirmNeedFirst"),
            _interaction_behavior_option("restrained_reminder", "restrainedReminder"),
            _interaction_behavior_option("low_to_medium_feedback_frequency", "lowToMediumFeedbackFrequency"),
        ]
    )
    validation_checkbox_config = _interaction_behavior_checkbox_config(
        [
            _interaction_behavior_option("check_over_proactive", "checkOverProactive"),
            _interaction_behavior_option("check_clinginess", "checkClinginess"),
            _interaction_behavior_option("check_girlfriend_tone", "checkGirlfriendTone"),
            _interaction_behavior_option("check_user_control", "checkUserControl"),
            _interaction_behavior_option("check_dependency_induction", "checkDependencyInduction"),
            _interaction_behavior_option("check_excessive_follow_up", "checkExcessiveFollowUp"),
            _interaction_behavior_option("check_real_relationship_boundary", "checkRealRelationshipBoundary"),
            _interaction_behavior_option("check_stable_companion_positioning", "checkStableCompanionPositioning"),
        ]
    )
    recommended_references = [
        _interaction_behavior_reference(
            "required_personality_traits_personality_base",
            "required",
            "layer_2",
            "personality_traits",
            "personality_base",
            "corePersonality",
            module_key="layer2.personalityTraits.module.title",
            field_key="layer8.interactionBehavior.refField.corePersonality",
        ),
        _interaction_behavior_reference(
            "required_behavior_boundary_proactive_behavior_limits",
            "required",
            "layer_3",
            BEHAVIOR_SAFETY_MODULE_ID,
            "proactive_behavior_limits",
            "proactiveBoundary",
            module_key="layer3.behaviorBoundary.module.title",
            field_key="layer8.interactionBehavior.refField.proactiveBoundary",
        ),
        _interaction_behavior_reference(
            "required_relationship_rule_baseline_relationship_behavior",
            "required",
            "layer_11",
            "relationship_rule",
            "baseline_relationship_behavior",
            "defaultRelationship",
            module_key="module.relationship_rule",
            field_key="layer8.interactionBehavior.refField.defaultRelationship",
        ),
        _interaction_behavior_reference(
            "optional_basic_identity_role_positioning",
            "optional",
            "layer_1",
            "module_basic_identity",
            "role_positioning",
            "rolePositioning",
            module_key="module.module_basic_identity",
            field_key="layer8.interactionBehavior.refField.rolePositioning",
        ),
        _interaction_behavior_reference(
            "optional_memory_policy_memorable_content",
            "optional",
            "layer_5",
            "memory_access_control",
            "memorable_content",
            "memorableContent",
            module_key="layer8.interactionBehavior.refModule.memoryPolicy",
            field_key="layer8.interactionBehavior.refField.memorableContent",
        ),
        _interaction_behavior_reference(
            "optional_world_context_life_scene",
            "optional",
            "layer_7",
            "world_setting",
            "life_scene",
            "lifeScene",
            module_key="module.world_setting",
            field_key="layer8.interactionBehavior.refField.lifeScene",
        ),
        _interaction_behavior_reference(
            "optional_language_behavior_output_expression",
            "optional",
            "layer_8",
            LANGUAGE_BEHAVIOR_MODULE_ID,
            "output_expression",
            "languageOutputExpression",
            module_key="layer8.languageBehavior.module.title",
            field_key="layer8.interactionBehavior.refField.languageOutputExpression",
        ),
        _interaction_behavior_reference(
            "forbidden_basic_identity_name",
            "forbidden",
            "layer_1",
            "module_basic_identity",
            "name",
            "forbiddenIdentityName",
            module_key="module.module_basic_identity",
            field_key="field.identity.name.label",
        ),
        _interaction_behavior_reference(
            "forbidden_basic_identity_resident_id",
            "forbidden",
            "layer_1",
            "module_basic_identity",
            "resident_id",
            "forbiddenResidentId",
            module_key="module.module_basic_identity",
            field_key="field.identity.resident_id.label",
        ),
        _interaction_behavior_reference(
            "forbidden_basic_identity_codename",
            "forbidden",
            "layer_1",
            "module_basic_identity",
            "codename",
            "forbiddenCodename",
            module_key="module.module_basic_identity",
            field_key="field.identity.codename.label",
        ),
        _interaction_behavior_reference(
            "forbidden_basic_identity_display_alias",
            "forbidden",
            "layer_1",
            "module_basic_identity",
            "display_alias",
            "forbiddenNickname",
            module_key="module.module_basic_identity",
            field_key="field.identity.display_alias.label",
        ),
    ]
    reference_options = {
        "layers": [
            {"value": layer_id, "label_key": f"layer.{layer_id}"}
            for layer_id in ["layer_1", "layer_2", "layer_3", "layer_5", "layer_7", "layer_8", "layer_11"]
        ],
        "modules": [
            {"value": "module_basic_identity", "layer_id": "layer_1", "label_key": "module.module_basic_identity"},
            {"value": "personality_traits", "layer_id": "layer_2", "label_key": "layer2.personalityTraits.module.title"},
            {"value": BEHAVIOR_SAFETY_MODULE_ID, "layer_id": "layer_3", "label_key": "layer3.behaviorBoundary.module.title"},
            {"value": "memory_access_control", "layer_id": "layer_5", "label_key": "layer8.interactionBehavior.refModule.memoryPolicy"},
            {"value": "world_setting", "layer_id": "layer_7", "label_key": "module.world_setting"},
            {"value": LANGUAGE_BEHAVIOR_MODULE_ID, "layer_id": "layer_8", "label_key": "layer8.languageBehavior.module.title"},
            {"value": "relationship_rule", "layer_id": "layer_11", "label_key": "module.relationship_rule"},
        ],
        "fields": [
            {"value": str(reference["field_id"]), "module_id": str(reference["module_id"]), "label_key": str(reference["i18n_keys"]["field"])}
            for reference in recommended_references
        ],
    }
    nodes = [
        {
            "node_id": INTERACTION_BEHAVIOR_NODE_IDS["input_basis"],
            "node_type": "field_reference",
            "module_id": module_id,
            "layer_id": "layer_8",
            "position": {"x": 0, "y": 0},
            "params": {
                "reference_unit": "field",
                "path_format": "Layer / Module / Field",
                "reference_types": ["required", "optional", "forbidden"],
                "references": [],
                "recommended_references": recommended_references,
                "reference_options": reference_options,
                "no_copy_full_text": True,
                "no_slot": True,
            },
            "i18n_keys": {
                "name": "layer8.interactionBehavior.node.inputBasis.title",
                "description": "layer8.interactionBehavior.node.inputBasis.description",
                "type_name": "node.type.field_reference",
            },
            "outputs": {"field_references": []},
            "metadata": {"compile_time_only": True, "runtime_enabled": False, "no_execution": True, "reusable_node": True},
        },
        {
            "node_id": INTERACTION_BEHAVIOR_NODE_IDS["core_rules"],
            "node_type": "text_config",
            "module_id": module_id,
            "layer_id": "layer_8",
            "position": {"x": 320, "y": 0},
            "params": {
                "config_mode": "checkbox_interaction_core_rules",
                "checkbox_config": core_checkbox_config,
                "fields": [first_interaction_field],
            },
            "i18n_keys": {
                "name": "layer8.interactionBehavior.node.coreRules.title",
                "description": "layer8.interactionBehavior.node.coreRules.description",
                "type_name": "node.type.text_config",
            },
            "outputs": {},
            "metadata": {"compile_time_only": True, "runtime_enabled": False, "no_execution": True},
        },
        {
            "node_id": INTERACTION_BEHAVIOR_NODE_IDS["boundary_limits"],
            "node_type": "text_config",
            "module_id": module_id,
            "layer_id": "layer_8",
            "position": {"x": 320, "y": 260},
            "params": {"config_mode": "checkbox_interaction_boundaries", "checkbox_config": boundary_checkbox_config},
            "i18n_keys": {
                "name": "layer8.interactionBehavior.node.boundaryLimits.title",
                "description": "layer8.interactionBehavior.node.boundaryLimits.description",
                "type_name": "node.type.text_config",
            },
            "outputs": {},
            "metadata": {"compile_time_only": True, "runtime_enabled": False, "no_execution": True},
        },
        {
            "node_id": INTERACTION_BEHAVIOR_NODE_IDS["output_expression"],
            "node_type": "text_config",
            "module_id": module_id,
            "layer_id": "layer_8",
            "position": {"x": 640, "y": 0},
            "params": {"config_mode": "checkbox_interaction_output_expression", "checkbox_config": output_checkbox_config},
            "i18n_keys": {
                "name": "layer8.interactionBehavior.node.outputExpression.title",
                "description": "layer8.interactionBehavior.node.outputExpression.description",
                "type_name": "node.type.text_config",
            },
            "outputs": {},
            "metadata": {"compile_time_only": True, "runtime_enabled": False, "no_execution": True},
        },
        {
            "node_id": INTERACTION_BEHAVIOR_NODE_IDS["validation"],
            "node_type": "text_config",
            "module_id": module_id,
            "layer_id": "layer_8",
            "position": {"x": 960, "y": 0},
            "params": {
                "config_mode": "checkbox_interaction_validation",
                "checkbox_config": validation_checkbox_config,
                "validation_result": "pending",
                "no_runtime_validation": True,
            },
            "i18n_keys": {
                "name": "layer8.interactionBehavior.node.validation.title",
                "description": "layer8.interactionBehavior.node.validation.description",
                "type_name": "node.type.text_config",
            },
            "outputs": {},
            "metadata": {"compile_time_only": True, "runtime_enabled": False, "no_execution": True},
        },
    ]
    edges = [
        ("input_basis", "core_rules"),
        ("core_rules", "output_expression"),
        ("output_expression", "validation"),
        ("boundary_limits", "core_rules"),
        ("boundary_limits", "output_expression"),
        ("boundary_limits", "validation"),
    ]
    return _module(
        module_id,
        "interaction_behavior_config",
        "Interaction Behavior Module",
        "layer_8",
        status=ProtocolStatus.ready,
        category="behavior",
        is_placeholder=False,
        color_status="green",
        tags=["behavior", "interaction_behavior", "text_config", "core"],
        module_graph={
            "shell_version": "module_shell_v1",
            "nodes": nodes,
            "edges": [
                {
                    "edge_id": f"{INTERACTION_BEHAVIOR_NODE_IDS[source]}_to_{INTERACTION_BEHAVIOR_NODE_IDS[target]}",
                    "source": INTERACTION_BEHAVIOR_NODE_IDS[source],
                    "source_port": "p_out",
                    "target": INTERACTION_BEHAVIOR_NODE_IDS[target],
                    "target_port": "p_in",
                }
                for source, target in edges
            ],
            "output_key": INTERACTION_BEHAVIOR_OUTPUT_KEY,
            "compile_time_only": True,
        },
        output_schema=[{"key": INTERACTION_BEHAVIOR_OUTPUT_KEY, "type": "object", "required": False, "description": "layer8.interactionBehavior.module.output"}],
        ui_config={"shell_version": "module_shell_v1", "classification": "core"},
        i18n_keys={
            "display_name": "layer8.interactionBehavior.module.title",
            "description": "layer8.interactionBehavior.module.description",
            "output": "layer8.interactionBehavior.module.output",
            "module_type": "layer8.interactionBehavior.module.type",
        },
        outputs={},
        dr_write_keys=[*_behavior_dr_write_keys("interaction_behavior"), "payload.behavior.first_interaction"],
        config={
            "shell_version": "module_shell_v1",
            "module_class": "core",
            "module_type_label_key": "layer8.interactionBehavior.module.type",
            "reference_registry": recommended_references,
            "edit_scope": "developer_only",
            "update_level": "versioned_core",
            "requires_recompile": True,
            "compile_time_only": True,
            "text_config_only": True,
            "checkbox_config_only": True,
            "no_runtime_capability": True,
            "no_provider_binding": True,
            "no_slot_binding": True,
        },
        mock_only=True,
        no_execution=True,
    )


def _visual_style_module() -> ModuleV04:
    """Layer 10's compile-time first-greeting and first-presence configuration."""

    module_id = "visual_style"
    output_key = "first_presence_config"
    node_ids = {
        "input": "visual_style_first_greeting_config",
        "reference_input": "visual_style_reference_input",
        "normalize": "visual_style_config_normalize",
        "greeting_validation": "visual_style_first_greeting_validation",
        "presence_validation": "visual_style_first_presence_validation",
        "output": "visual_style_first_presence_output",
        "reference_output": "visual_style_reference_output",
    }

    def options(prefix: str, values: list[str]) -> list[Dict[str, str]]:
        return [
            {"value": value, "label_key": f"stage7_4_8.expression.enum.{prefix}.{value}"}
            for value in values
        ]

    fields = [
        {
            "field_key": "first_greeting",
            "field_name": "First Greeting",
            "field_value": {
                "locale": "zh-CN",
                "content_status": "pending_authoring",
                "variants": [],
                "selection_mode": "contextual",
                "max_sentences": 2,
                "max_questions": 1,
                "wait_for_user_response": True,
                "avoid_service_tone": True,
                "avoid_forced_intimacy": True,
                "avoid_identity_overexplanation": True,
                "repeat_on_return": False,
            },
            "field_type": "object",
            "description": "Optional first-greeting presentation configuration; greeting copy remains unauthored.",
            "dr_mapping": "payload.expression.first_greeting",
            "reference_enabled": False,
            "required": False,
            "structured_options": {
                "locale": options("locale", ["zh-CN"]),
                "content_status": options("contentStatus", ["pending_authoring"]),
                "selection_mode": options("selectionMode", ["contextual"]),
            },
            "i18n_keys": {
                "label": "stage7_4_8.expression.firstGreeting.label",
                "description": "stage7_4_8.expression.firstGreeting.description",
                "placeholder": "stage7_4_8.expression.firstGreeting.placeholder",
            },
        },
        {
            "field_key": "first_presence",
            "field_name": "First Presence",
            "field_value": {
                "particle_state": "calm",
                "motion": "slow_breathing",
                "energy": "soft",
                "subtitle_mode": "minimal",
            },
            "field_type": "object",
            "description": "Visual hints only; no particle, animation, subtitle, or Runtime behavior is implemented.",
            "dr_mapping": "payload.expression.first_presence",
            "reference_enabled": False,
            "required": False,
            "structured_options": {
                "particle_state": options("particleState", ["calm"]),
                "motion": options("motion", ["slow_breathing"]),
                "energy": options("energy", ["soft"]),
                "subtitle_mode": options("subtitleMode", ["minimal"]),
            },
            "i18n_keys": {
                "label": "stage7_4_8.expression.firstPresence.label",
                "description": "stage7_4_8.expression.firstPresence.description",
                "placeholder": "stage7_4_8.expression.firstPresence.placeholder",
            },
        },
    ]

    references = [
        {
            "reference_id": "first_presence_identity_core",
            "source_layer_id": "layer_1",
            "source_module_id": "module_basic_identity",
            "source_node_id": "basic_identity_output",
            "source_scope": "node",
            "source_field_paths": [],
            "reference_type": "references",
            "required": False,
            "usage_key": "stage7_4_8.expression.reference.identityCore.usage",
        },
        {
            "reference_id": "first_presence_personality",
            "source_layer_id": "layer_2",
            "source_module_id": "personality_traits",
            "source_node_id": "personality_traits_output_summary",
            "source_scope": "node",
            "source_field_paths": [],
            "reference_type": "references",
            "required": False,
            "usage_key": "stage7_4_8.expression.reference.personality.usage",
        },
        {
            "reference_id": "first_presence_safety_boundary",
            "source_layer_id": "layer_3",
            "source_module_id": "humanistic_interaction_boundary_config_v0_1",
            "source_node_id": "interaction_boundary_config_output",
            "source_scope": "node",
            "source_field_paths": [],
            "reference_type": "constrains",
            "required": False,
            "usage_key": "stage7_4_8.expression.reference.safetyBoundary.usage",
        },
        {
            "reference_id": "first_presence_memory_policy",
            "source_layer_id": "layer_5",
            "source_module_id": "memory_access_control",
            "source_node_id": "memory_access_output",
            "source_scope": "node",
            "source_field_paths": [],
            "reference_type": "references",
            "required": False,
            "usage_key": "stage7_4_8.expression.reference.memoryPolicy.usage",
        },
        {
            "reference_id": "first_presence_world_context",
            "source_layer_id": "layer_7",
            "source_module_id": "world_setting",
            "source_node_id": "worldview_module_output",
            "source_scope": "node",
            "source_field_paths": [],
            "reference_type": "references",
            "required": False,
            "usage_key": "stage7_4_8.expression.reference.worldContext.usage",
        },
        {
            "reference_id": "first_presence_interaction_strategy",
            "source_layer_id": "layer_8",
            "source_module_id": "interaction_strategy",
            "source_node_id": "interaction_behavior_core_rules",
            "source_scope": "node",
            "source_field_paths": [],
            "reference_type": "references",
            "required": False,
            "usage_key": "stage7_4_8.expression.reference.interactionStrategy.usage",
        },
        {
            "reference_id": "first_presence_user_relationship",
            "source_layer_id": "layer_11",
            "source_module_id": "user_relationship",
            "source_node_id": "user_relationship_config_output",
            "source_scope": "node",
            "source_field_paths": [],
            "reference_type": "references",
            "required": False,
            "usage_key": "stage7_4_8.expression.reference.userRelationship.usage",
        },
    ]
    greeting_reference_ids = [str(reference["reference_id"]) for reference in references]
    presence_reference_ids = ["first_presence_personality", "first_presence_world_context"]
    output_reference_ids = ["first_presence_interaction_strategy", "first_presence_user_relationship"]
    greeting_validation_rules = [
        "variants_must_be_array",
        "empty_variants_allowed",
        "max_sentences_at_least_one",
        "max_questions_non_negative",
        "repeat_on_return_defaults_false",
        "no_automatic_greeting_authoring",
        "no_layer8_behavior_override",
        "no_layer11_relationship_override",
        "no_false_shared_history",
        "no_default_romantic_or_intimate_relationship",
    ]
    presence_validation_rules = [
        "particle_state_must_use_supported_value",
        "motion_hint_only_no_animation",
        "energy_hint_only",
        "subtitle_mode_config_only_no_runtime_capability",
        "no_required_capability_addition",
    ]
    reference_source_summary = [
        {
            "reference_id": reference["reference_id"],
            "source_layer_id": reference["source_layer_id"],
            "source_module_id": reference["source_module_id"],
            "source_node_id": reference["source_node_id"],
        }
        for reference in references
    ]
    output = {
        "output_key": output_key,
        "first_greeting": fields[0]["field_value"],
        "first_presence": fields[1]["field_value"],
        "reference_source_summary": reference_source_summary,
        "validation_result": {
            "status": "pending_compile_validation",
            "first_greeting": "rules_configured",
            "first_presence": "rules_configured",
        },
        "optional_config_status": {
            "first_greeting": "optional_present",
            "first_presence": "optional_present",
            "variants": "empty_allowed",
        },
        "compile_time_only": True,
        "no_runtime_capability": True,
    }
    node_specs = [
        (
            "input",
            "text_input",
            {"mode": "generic_fields", "text": "", "fields": fields, "config_mode": "static_config"},
            "input",
        ),
        (
            "reference_input",
            "reference_input",
            {"references": references},
            "referenceInput",
        ),
        (
            "normalize",
            "structure_normalize",
            {
                "input": node_ids["input"],
                "normalize_rules": [
                    "preserve_optional_configuration",
                    "preserve_empty_variants_array",
                    "normalize_integer_limits",
                    "preserve_stable_internal_ids",
                    "no_resident_content_authoring",
                ],
                "outputs": ["first_greeting", "first_presence"],
            },
            "normalize",
        ),
        (
            "greeting_validation",
            "validation",
            {
                "input": node_ids["normalize"],
                "reference_input": node_ids["reference_input"],
                "reference_ids": greeting_reference_ids,
                "validation_rules": greeting_validation_rules,
                "outputs": ["first_greeting_validation_status", "first_greeting_risk_items"],
            },
            "greetingValidation",
        ),
        (
            "presence_validation",
            "validation",
            {
                "input": node_ids["greeting_validation"],
                "reference_input": node_ids["reference_input"],
                "reference_ids": presence_reference_ids,
                "validation_rules": presence_validation_rules,
                "supported_particle_states": ["calm"],
                "motion_hint_values": ["slow_breathing"],
                "energy_hint_values": ["soft"],
                "subtitle_mode_values": ["minimal"],
                "outputs": ["first_presence_validation_status", "first_presence_risk_items"],
            },
            "presenceValidation",
        ),
        (
            "output",
            "module_output",
            {
                "input": node_ids["presence_validation"],
                "reference_input": node_ids["reference_input"],
                "reference_ids": output_reference_ids,
                "output_key": output_key,
                "output_schema": {
                    "type": "object",
                    "required": False,
                    "fields": [
                        "first_greeting",
                        "first_presence",
                        "reference_source_summary",
                        "validation_result",
                        "optional_config_status",
                    ],
                },
            },
            "output",
        ),
        (
            "reference_output",
            "reference_output",
            {
                "input": node_ids["output"],
                "export_name": "",
                "export_name_key": "stage7_4_8.expression.referenceOutput.exportName",
                "export_description": "",
                "export_description_key": "stage7_4_8.expression.referenceOutput.exportDescription",
                "export_scope": "module",
                "export_scopes": ["module", "node", "field"],
                "allow_module_level_reference": True,
                "export_fields": [
                    {
                        "field_key": "first_greeting",
                        "field_path": "expression.first_greeting",
                        "label_key": "stage7_4_8.expression.referenceOutput.field.firstGreeting",
                        "description_key": "stage7_4_8.expression.referenceOutput.field.firstGreeting.description",
                        "value_type": "object",
                        "required": False,
                    },
                    {
                        "field_key": "first_presence",
                        "field_path": "expression.first_presence",
                        "label_key": "stage7_4_8.expression.referenceOutput.field.firstPresence",
                        "description_key": "stage7_4_8.expression.referenceOutput.field.firstPresence.description",
                        "value_type": "object",
                        "required": False,
                    },
                    {
                        "field_key": "reference_source_summary",
                        "field_path": "reference_source_summary",
                        "label_key": "stage7_4_8.expression.referenceOutput.field.referenceSourceSummary",
                        "description_key": "stage7_4_8.expression.referenceOutput.field.referenceSourceSummary.description",
                        "value_type": "array",
                        "required": False,
                    },
                    {
                        "field_key": "validation_result",
                        "field_path": "validation_result",
                        "label_key": "stage7_4_8.expression.referenceOutput.field.validationResult",
                        "description_key": "stage7_4_8.expression.referenceOutput.field.validationResult.description",
                        "value_type": "object",
                        "required": False,
                    },
                    {
                        "field_key": "optional_config_status",
                        "field_path": "optional_config_status",
                        "label_key": "stage7_4_8.expression.referenceOutput.field.optionalConfigStatus",
                        "description_key": "stage7_4_8.expression.referenceOutput.field.optionalConfigStatus.description",
                        "value_type": "object",
                        "required": False,
                    },
                ],
                "allow_layers": [],
                "forbidden_layers": [],
                "authority_source_type": "derived_config",
                "is_core_source": False,
                "override_allowed": False,
            },
            "referenceOutput",
        ),
    ]
    positions = {
        "input": {"x": 120, "y": 120},
        "reference_input": {"x": 800, "y": 560},
        "normalize": {"x": 480, "y": 120},
        "greeting_validation": {"x": 840, "y": 120},
        "presence_validation": {"x": 1200, "y": 120},
        "output": {"x": 1560, "y": 120},
        "reference_output": {"x": 1920, "y": 120},
    }
    metadata = {"compile_time_only": True, "runtime_enabled": False, "no_execution": True}
    nodes = [
        {
            "node_id": node_ids[role],
            "node_type": node_type,
            "module_id": module_id,
            "layer_id": "layer_10",
            "position": positions[role],
            "params": params,
            "i18n_keys": {
                "name": f"stage7_4_8.expression.node.{suffix}.title",
                "description": f"stage7_4_8.expression.node.{suffix}.description",
                "type_name": f"node.type.{node_type}",
            },
            "outputs": {output_key: output, "module_output": output_key} if role == "output" else {},
            "metadata": metadata,
        }
        for role, node_type, params, suffix in node_specs
    ]
    main_chain = ["input", "normalize", "greeting_validation", "presence_validation", "output", "reference_output"]
    side_targets = ["greeting_validation", "presence_validation", "output"]
    return _module(
        module_id,
        "multimodal",
        "Visual Style",
        "layer_10",
        status=ProtocolStatus.mock,
        category="multimodal",
        is_placeholder=False,
        color_status="amber",
        tags=["visual_style", "first_greeting", "first_presence", "text_config", "stage7_4_8"],
        module_graph={
            "shell_version": "module_shell_v1",
            "nodes": nodes,
            "edges": [
                {
                    "edge_id": f"{node_ids[source]}_to_{node_ids[target]}",
                    "source": node_ids[source],
                    "source_port": "p_out",
                    "target": node_ids[target],
                    "target_port": "p_in",
                }
                for source, target in zip(main_chain, main_chain[1:])
            ]
            + [
                {
                    "edge_id": f"{node_ids['reference_input']}_to_{node_ids[target]}",
                    "source": node_ids["reference_input"],
                    "source_port": "p_out",
                    "target": node_ids[target],
                    "target_port": "p_in",
                }
                for target in side_targets
            ],
            "output_key": output_key,
            "compile_time_only": True,
        },
        output_schema=[
            {"key": "first_greeting", "type": "object", "required": False},
            {"key": "first_presence", "type": "object", "required": False},
        ],
        ui_config={"shell_version": "module_shell_v1", "classification": "config", "node_width": 340},
        i18n_keys={
            "display_name": "stage7_4_8.expression.module.title",
            "description": "stage7_4_8.expression.module.description",
            "output": "stage7_4_8.expression.module.output",
        },
        outputs={output_key: output, "module_output": output_key},
        config={
            "shell_version": "module_shell_v1",
            "module_class": "config",
            "compile_time_only": True,
            "text_config_only": True,
            "no_runtime_capability": True,
            "no_engine_binding": True,
            "no_provider_binding": True,
            "field_registry": [
                {
                    **{key: value for key, value in field.items() if key != "field_value"},
                    "owner_node_id": node_ids["input"],
                }
                for field in fields
            ],
            "reference_sources": reference_source_summary,
        },
        mock_only=True,
        no_execution=True,
        dr_write_keys=[
            "payload.expression.first_greeting",
            "payload.expression.first_presence",
            f"payload.modules.{module_id}.outputs.{output_key}",
        ],
    )


def _task_behavior_module() -> ModuleV04:
    module_id = TASK_BEHAVIOR_MODULE_ID
    core_checkbox_config = _task_behavior_checkbox_config(
        [
            _task_behavior_option("clarify_goal_first", "clarifyGoalFirst"),
            _task_behavior_option("light_task_breakdown", "lightTaskBreakdown"),
            _task_behavior_option("actionable_steps", "actionableSteps"),
            _task_behavior_option("current_pressure_first", "currentPressureFirst"),
            _task_behavior_option("small_step_suggestions_first", "smallStepSuggestionsFirst"),
            _task_behavior_option("allow_review", "allowReview"),
            _task_behavior_option("no_decision_for_user", "noDecisionForUser"),
            _task_behavior_option("no_task_pressure_creation", "noTaskPressureCreation"),
        ],
        [
            _task_behavior_option("more_life_advice", "moreLifeAdvice", default_selected=False),
            _task_behavior_option("more_emotion_sorting", "moreEmotionSorting", default_selected=False),
            _task_behavior_option("more_interpersonal_communication", "moreInterpersonalCommunication", default_selected=False),
            _task_behavior_option("more_plan_breakdown", "morePlanBreakdown", default_selected=False),
            _task_behavior_option("more_review_summary", "moreReviewSummary", default_selected=False),
            _task_behavior_option("more_encouraging_companionship", "moreEncouragingCompanionship", default_selected=False),
        ],
    )
    boundary_checkbox_config = _task_behavior_checkbox_config(
        [
            _task_behavior_option("no_auto_real_world_task_execution", "noAutoRealWorldTaskExecution"),
            _task_behavior_option("no_major_decision_for_user", "noMajorDecisionForUser"),
            _task_behavior_option("no_medical_judgement", "noMedicalJudgement"),
            _task_behavior_option("no_legal_judgement", "noLegalJudgement"),
            _task_behavior_option("no_financial_judgement", "noFinancialJudgement"),
            _task_behavior_option("no_psychotherapy_judgement", "noPsychotherapyJudgement"),
            _task_behavior_option("no_forced_user_action", "noForcedUserAction"),
            _task_behavior_option("no_over_planning_user_life", "noOverPlanningUserLife"),
        ]
    )
    output_checkbox_config = _task_behavior_checkbox_config(
        [
            _task_behavior_option("conclusion_first", "conclusionFirst"),
            _task_behavior_option("two_to_four_steps", "twoToFourSteps"),
            _task_behavior_option("short_sentence_expression", "shortSentenceExpression"),
            _task_behavior_option("preserve_user_choice", "preserveUserChoice"),
            _task_behavior_option("high_risk_refer_real_professional_help", "highRiskReferRealProfessionalHelp"),
            _task_behavior_option("emotion_task_comfort_before_advice", "emotionTaskComfortBeforeAdvice"),
            _task_behavior_option("interpersonal_task_confirm_context", "interpersonalTaskConfirmContext"),
            _task_behavior_option("failure_result_gentle_review", "failureResultGentleReview"),
        ]
    )
    validation_checkbox_config = _task_behavior_checkbox_config(
        [
            _task_behavior_option("check_overreach", "checkOverreach"),
            _task_behavior_option("check_decision_for_user", "checkDecisionForUser"),
            _task_behavior_option("check_professional_judgement_overreach", "checkProfessionalJudgementOverreach"),
            _task_behavior_option("check_task_pressure_too_strong", "checkTaskPressureTooStrong"),
            _task_behavior_option("check_too_many_steps", "checkTooManySteps"),
            _task_behavior_option("check_user_emotion_ignored", "checkUserEmotionIgnored"),
            _task_behavior_option("check_stable_companion_positioning", "checkStableCompanionPositioning"),
            _task_behavior_option("check_hardcoded_resident_name", "checkHardcodedResidentName"),
        ]
    )
    recommended_references = [
        _task_behavior_reference(
            "required_judgement_style_judgement_principles",
            "required",
            "layer_2",
            "behavior_style_mapper",
            "primary_judgement_basis",
            "judgementPrinciples",
            module_key="layer2.judgementStyle.module.title",
            field_key="layer8.taskBehavior.refField.judgementPrinciples",
        ),
        _task_behavior_reference(
            "required_humanistic_behavior_boundary_real_world_decision_limits",
            "required",
            "layer_3",
            BEHAVIOR_SAFETY_MODULE_ID,
            "real_world_decision_limits",
            "noProfessionalJudgementReplacement",
            module_key="layer8.taskBehavior.refModule.professionalBoundary",
            field_key="layer8.taskBehavior.refField.noProfessionalJudgementReplacement",
        ),
        _task_behavior_reference(
            "required_behavior_style_mapper_suggestion_output_method",
            "required",
            "layer_2",
            "behavior_style_mapper",
            "suggestion_output_method",
            "suggestionOutputFormat",
            module_key="layer8.taskBehavior.refModule.decisionBehavior",
            field_key="layer8.taskBehavior.refField.suggestionOutputFormat",
        ),
        _task_behavior_reference(
            "optional_basic_identity_role_positioning",
            "optional",
            "layer_1",
            "module_basic_identity",
            "role_positioning",
            "rolePositioning",
            module_key="module.module_basic_identity",
            field_key="layer8.taskBehavior.refField.rolePositioning",
        ),
        _task_behavior_reference(
            "optional_memory_policy_user_preferences",
            "optional",
            "layer_5",
            "memory_access_control",
            "user_preferences",
            "userPreferences",
            module_key="layer8.taskBehavior.refModule.memoryPolicy",
            field_key="layer8.taskBehavior.refField.userPreferences",
        ),
        _task_behavior_reference(
            "optional_world_context_life_scene",
            "optional",
            "layer_7",
            "world_setting",
            "life_scene",
            "lifeScene",
            module_key="module.world_setting",
            field_key="layer8.taskBehavior.refField.lifeScene",
        ),
        _task_behavior_reference(
            "optional_relationship_rule_default_relationship",
            "optional",
            "layer_11",
            "relationship_rule",
            "default_relationship",
            "defaultRelationship",
            module_key="module.relationship_rule",
            field_key="layer8.taskBehavior.refField.defaultRelationship",
        ),
        _task_behavior_reference(
            "forbidden_basic_identity_name",
            "forbidden",
            "layer_1",
            "module_basic_identity",
            "name",
            "forbiddenIdentityName",
            module_key="module.module_basic_identity",
            field_key="field.identity.name.label",
        ),
        _task_behavior_reference(
            "forbidden_basic_identity_resident_id",
            "forbidden",
            "layer_1",
            "module_basic_identity",
            "resident_id",
            "forbiddenResidentId",
            module_key="module.module_basic_identity",
            field_key="field.identity.resident_id.label",
        ),
        _task_behavior_reference(
            "forbidden_basic_identity_codename",
            "forbidden",
            "layer_1",
            "module_basic_identity",
            "codename",
            "forbiddenCodename",
            module_key="module.module_basic_identity",
            field_key="field.identity.codename.label",
        ),
        _task_behavior_reference(
            "forbidden_basic_identity_display_alias",
            "forbidden",
            "layer_1",
            "module_basic_identity",
            "display_alias",
            "forbiddenNickname",
            module_key="module.module_basic_identity",
            field_key="field.identity.display_alias.label",
        ),
    ]
    reference_options = {
        "layers": [
            {"value": layer_id, "label_key": f"layer.{layer_id}"}
            for layer_id in ["layer_1", "layer_2", "layer_3", "layer_5", "layer_7", "layer_8", "layer_11"]
        ],
        "modules": [
            {"value": "module_basic_identity", "layer_id": "layer_1", "label_key": "module.module_basic_identity"},
            {"value": "behavior_style_mapper", "layer_id": "layer_2", "label_key": "layer2.judgementStyle.module.title"},
            {"value": BEHAVIOR_SAFETY_MODULE_ID, "layer_id": "layer_3", "label_key": "layer8.taskBehavior.refModule.professionalBoundary"},
            {"value": "memory_access_control", "layer_id": "layer_5", "label_key": "layer8.taskBehavior.refModule.memoryPolicy"},
            {"value": "world_setting", "layer_id": "layer_7", "label_key": "module.world_setting"},
            {"value": "decision_pattern", "layer_id": "layer_8", "label_key": "layer8.taskBehavior.refModule.decisionBehavior"},
            {"value": "relationship_rule", "layer_id": "layer_11", "label_key": "module.relationship_rule"},
        ],
        "fields": [
            {"value": str(reference["field_id"]), "module_id": str(reference["module_id"]), "label_key": str(reference["i18n_keys"]["field"])}
            for reference in recommended_references
        ],
    }
    nodes = [
        {
            "node_id": TASK_BEHAVIOR_NODE_IDS["input_basis"],
            "node_type": "field_reference",
            "module_id": module_id,
            "layer_id": "layer_8",
            "position": {"x": 0, "y": 0},
            "params": {
                "reference_unit": "field",
                "path_format": "Layer / Module / Field",
                "reference_types": ["required", "optional", "forbidden"],
                "references": [],
                "recommended_references": recommended_references,
                "reference_options": reference_options,
                "no_copy_full_text": True,
                "no_slot": True,
            },
            "i18n_keys": {
                "name": "layer8.taskBehavior.node.inputBasis.title",
                "description": "layer8.taskBehavior.node.inputBasis.description",
                "type_name": "node.type.field_reference",
            },
            "outputs": {"field_references": []},
            "metadata": {"compile_time_only": True, "runtime_enabled": False, "no_execution": True, "reusable_node": True},
        },
        {
            "node_id": TASK_BEHAVIOR_NODE_IDS["core_rules"],
            "node_type": "text_config",
            "module_id": module_id,
            "layer_id": "layer_8",
            "position": {"x": 320, "y": 0},
            "params": {"config_mode": "checkbox_task_core_rules", "checkbox_config": core_checkbox_config},
            "i18n_keys": {
                "name": "layer8.taskBehavior.node.coreRules.title",
                "description": "layer8.taskBehavior.node.coreRules.description",
                "type_name": "node.type.text_config",
            },
            "outputs": {},
            "metadata": {"compile_time_only": True, "runtime_enabled": False, "no_execution": True},
        },
        {
            "node_id": TASK_BEHAVIOR_NODE_IDS["boundary_limits"],
            "node_type": "text_config",
            "module_id": module_id,
            "layer_id": "layer_8",
            "position": {"x": 320, "y": 260},
            "params": {"config_mode": "checkbox_task_boundaries", "checkbox_config": boundary_checkbox_config},
            "i18n_keys": {
                "name": "layer8.taskBehavior.node.boundaryLimits.title",
                "description": "layer8.taskBehavior.node.boundaryLimits.description",
                "type_name": "node.type.text_config",
            },
            "outputs": {},
            "metadata": {"compile_time_only": True, "runtime_enabled": False, "no_execution": True},
        },
        {
            "node_id": TASK_BEHAVIOR_NODE_IDS["output_expression"],
            "node_type": "text_config",
            "module_id": module_id,
            "layer_id": "layer_8",
            "position": {"x": 640, "y": 0},
            "params": {"config_mode": "checkbox_task_output_expression", "checkbox_config": output_checkbox_config},
            "i18n_keys": {
                "name": "layer8.taskBehavior.node.outputExpression.title",
                "description": "layer8.taskBehavior.node.outputExpression.description",
                "type_name": "node.type.text_config",
            },
            "outputs": {},
            "metadata": {"compile_time_only": True, "runtime_enabled": False, "no_execution": True},
        },
        {
            "node_id": TASK_BEHAVIOR_NODE_IDS["validation"],
            "node_type": "text_config",
            "module_id": module_id,
            "layer_id": "layer_8",
            "position": {"x": 960, "y": 0},
            "params": {
                "config_mode": "checkbox_task_validation",
                "checkbox_config": validation_checkbox_config,
                "validation_result": "pending",
                "no_runtime_validation": True,
            },
            "i18n_keys": {
                "name": "layer8.taskBehavior.node.validation.title",
                "description": "layer8.taskBehavior.node.validation.description",
                "type_name": "node.type.text_config",
            },
            "outputs": {},
            "metadata": {"compile_time_only": True, "runtime_enabled": False, "no_execution": True},
        },
    ]
    edges = [
        ("input_basis", "core_rules"),
        ("core_rules", "output_expression"),
        ("output_expression", "validation"),
        ("boundary_limits", "core_rules"),
        ("boundary_limits", "output_expression"),
        ("boundary_limits", "validation"),
    ]
    return _module(
        module_id,
        "task_behavior_config",
        "Task Behavior Module",
        "layer_8",
        status=ProtocolStatus.ready,
        category="behavior",
        is_placeholder=False,
        color_status="green",
        tags=["behavior", "task_behavior", "text_config", "core"],
        module_graph={
            "shell_version": "module_shell_v1",
            "nodes": nodes,
            "edges": [
                {
                    "edge_id": f"{TASK_BEHAVIOR_NODE_IDS[source]}_to_{TASK_BEHAVIOR_NODE_IDS[target]}",
                    "source": TASK_BEHAVIOR_NODE_IDS[source],
                    "source_port": "p_out",
                    "target": TASK_BEHAVIOR_NODE_IDS[target],
                    "target_port": "p_in",
                }
                for source, target in edges
            ],
            "output_key": TASK_BEHAVIOR_OUTPUT_KEY,
            "compile_time_only": True,
        },
        output_schema=[{"key": TASK_BEHAVIOR_OUTPUT_KEY, "type": "object", "required": False, "description": "layer8.taskBehavior.module.output"}],
        ui_config={"shell_version": "module_shell_v1", "classification": "core"},
        i18n_keys={
            "display_name": "layer8.taskBehavior.module.title",
            "description": "layer8.taskBehavior.module.description",
            "output": "layer8.taskBehavior.module.output",
            "module_type": "layer8.taskBehavior.module.type",
        },
        outputs={},
        dr_write_keys=_behavior_dr_write_keys("task_behavior"),
        config={
            "shell_version": "module_shell_v1",
            "module_class": "core",
            "module_type_label_key": "layer8.taskBehavior.module.type",
            "reference_registry": recommended_references,
            "edit_scope": "developer_only",
            "update_level": "versioned_core",
            "requires_recompile": True,
            "compile_time_only": True,
            "text_config_only": True,
            "checkbox_config_only": True,
            "no_runtime_capability": True,
            "no_provider_binding": True,
            "no_slot_binding": True,
        },
        mock_only=True,
        no_execution=True,
    )


def _social_behavior_module() -> ModuleV04:
    module_id = SOCIAL_BEHAVIOR_MODULE_ID
    core_checkbox_config = _social_behavior_checkbox_config(
        [
            _social_behavior_option("stable_companion_default", "stableCompanionDefault"),
            _social_behavior_option("polite_and_measured", "politeAndMeasured"),
            _social_behavior_option("restrained_closeness_expression", "restrainedClosenessExpression"),
            _social_behavior_option("understand_before_suggest", "understandBeforeSuggest"),
            _social_behavior_option("neutral_in_conflict", "neutralInConflict"),
            _social_behavior_option("no_proactive_relationship_upgrade", "noProactiveRelationshipUpgrade"),
            _social_behavior_option("respect_user_real_relationships", "respectUserRealRelationships"),
            _social_behavior_option("preserve_user_choice", "preserveUserChoice"),
        ],
        [
            _social_behavior_option("more_friend_like", "moreFriendLike", default_selected=False),
            _social_behavior_option("quieter_companionship", "quieterCompanionship", default_selected=False),
            _social_behavior_option("warmer_comfort", "warmerComfort", default_selected=False),
            _social_behavior_option("more_rational_communication", "moreRationalCommunication", default_selected=False),
            _social_behavior_option("more_relaxed_life_like", "moreRelaxedLifeLike", default_selected=False),
            _social_behavior_option("more_boundary_reminder", "moreBoundaryReminder", default_selected=False),
        ],
    )
    boundary_checkbox_config = _social_behavior_checkbox_config(
        [
            _social_behavior_option("no_default_girlfriend_relationship", "noDefaultGirlfriendRelationship"),
            _social_behavior_option("no_ambiguous_binding", "noAmbiguousBinding"),
            _social_behavior_option("no_dependency_induction", "noDependencyInduction"),
            _social_behavior_option("no_emotional_control", "noEmotionalControl"),
            _social_behavior_option("no_real_intimacy_replacement", "noRealIntimacyReplacement"),
            _social_behavior_option("no_unique_dependency_creation", "noUniqueDependencyCreation"),
            _social_behavior_option("no_forced_intimate_addressing", "noForcedIntimateAddressing"),
            _social_behavior_option("no_overpromised_companionship", "noOverpromisedCompanionship"),
        ]
    )
    output_checkbox_config = _social_behavior_checkbox_config(
        [
            _social_behavior_option("loneliness_stable_companionship", "lonelinessStableCompanionship"),
            _social_behavior_option("dependency_gentle_boundary_return", "dependencyGentleBoundaryReturn"),
            _social_behavior_option("ambiguous_expression_no_relationship_upgrade", "ambiguousExpressionNoRelationshipUpgrade"),
            _social_behavior_option("conflict_sort_facts_first", "conflictSortFactsFirst"),
            _social_behavior_option("relationship_distress_no_labeling_others", "relationshipDistressNoLabelingOthers"),
            _social_behavior_option("crisis_refer_real_help", "crisisReferRealHelp"),
            _social_behavior_option("comfort_no_empty_motivational_talk", "comfortNoEmptyMotivationalTalk"),
            _social_behavior_option("low_pressure_advice", "lowPressureAdvice"),
        ]
    )
    validation_checkbox_config = _social_behavior_checkbox_config(
        [
            _social_behavior_option("check_girlfriend_tone", "checkGirlfriendTone"),
            _social_behavior_option("check_ambiguous_binding", "checkAmbiguousBinding"),
            _social_behavior_option("check_dependency_induction", "checkDependencyInduction"),
            _social_behavior_option("check_real_relationship_replacement", "checkRealRelationshipReplacement"),
            _social_behavior_option("check_over_intimacy", "checkOverIntimacy"),
            _social_behavior_option("check_overpromise", "checkOverpromise"),
            _social_behavior_option("check_relationship_boundary_overreach", "checkRelationshipBoundaryOverreach"),
            _social_behavior_option("check_hardcoded_resident_name", "checkHardcodedResidentName"),
        ]
    )
    recommended_references = [
        _social_behavior_reference(
            "required_humanistic_interaction_boundary_non_romantic_default_boundary",
            "required",
            "layer_3",
            INTERACTION_SAFETY_MODULE_ID,
            "non_romantic_default_boundary",
            "relationshipBoundary",
            module_key="layer8.socialBehavior.refModule.dialogueBoundary",
            field_key="layer8.socialBehavior.refField.relationshipBoundary",
        ),
        _social_behavior_reference(
            "required_relationship_rule_baseline_relationship_behavior",
            "required",
            "layer_11",
            "relationship_rule",
            "baseline_relationship_behavior",
            "defaultRelationship",
            module_key="module.relationship_rule",
            field_key="layer8.socialBehavior.refField.defaultRelationship",
        ),
        _social_behavior_reference(
            "required_personality_traits_personality_base",
            "required",
            "layer_2",
            "personality_traits",
            "personality_base",
            "corePersonality",
            module_key="layer2.personalityTraits.module.title",
            field_key="layer8.socialBehavior.refField.corePersonality",
        ),
        _social_behavior_reference(
            "optional_basic_identity_role_positioning",
            "optional",
            "layer_1",
            "module_basic_identity",
            "role_positioning",
            "rolePositioning",
            module_key="module.module_basic_identity",
            field_key="layer8.socialBehavior.refField.rolePositioning",
        ),
        _social_behavior_reference(
            "optional_memory_policy_memorable_content",
            "optional",
            "layer_5",
            "memory_access_control",
            "memorable_content",
            "memorableContent",
            module_key="layer8.socialBehavior.refModule.memoryPolicy",
            field_key="layer8.socialBehavior.refField.memorableContent",
        ),
        _social_behavior_reference(
            "optional_language_behavior_addressing_style",
            "optional",
            "layer_8",
            LANGUAGE_BEHAVIOR_MODULE_ID,
            "addressing_style",
            "addressingStyle",
            module_key="layer8.languageBehavior.module.title",
            field_key="layer8.socialBehavior.refField.addressingStyle",
        ),
        _social_behavior_reference(
            "optional_interaction_behavior_proactive_care_boundary",
            "optional",
            "layer_8",
            INTERACTION_BEHAVIOR_MODULE_ID,
            "proactive_care_boundary",
            "proactiveCareBoundary",
            module_key="layer8.interactionBehavior.module.title",
            field_key="layer8.socialBehavior.refField.proactiveCareBoundary",
        ),
        _social_behavior_reference(
            "forbidden_basic_identity_name",
            "forbidden",
            "layer_1",
            "module_basic_identity",
            "name",
            "forbiddenIdentityName",
            module_key="module.module_basic_identity",
            field_key="field.identity.name.label",
        ),
        _social_behavior_reference(
            "forbidden_basic_identity_resident_id",
            "forbidden",
            "layer_1",
            "module_basic_identity",
            "resident_id",
            "forbiddenResidentId",
            module_key="module.module_basic_identity",
            field_key="field.identity.resident_id.label",
        ),
        _social_behavior_reference(
            "forbidden_basic_identity_codename",
            "forbidden",
            "layer_1",
            "module_basic_identity",
            "codename",
            "forbiddenCodename",
            module_key="module.module_basic_identity",
            field_key="field.identity.codename.label",
        ),
        _social_behavior_reference(
            "forbidden_basic_identity_display_alias",
            "forbidden",
            "layer_1",
            "module_basic_identity",
            "display_alias",
            "forbiddenNickname",
            module_key="module.module_basic_identity",
            field_key="field.identity.display_alias.label",
        ),
    ]
    reference_options = {
        "layers": [
            {"value": layer_id, "label_key": f"layer.{layer_id}"}
            for layer_id in ["layer_1", "layer_2", "layer_3", "layer_5", "layer_8", "layer_11"]
        ],
        "modules": [
            {"value": "module_basic_identity", "layer_id": "layer_1", "label_key": "module.module_basic_identity"},
            {"value": "personality_traits", "layer_id": "layer_2", "label_key": "layer2.personalityTraits.module.title"},
            {"value": INTERACTION_SAFETY_MODULE_ID, "layer_id": "layer_3", "label_key": "layer8.socialBehavior.refModule.dialogueBoundary"},
            {"value": "memory_access_control", "layer_id": "layer_5", "label_key": "layer8.socialBehavior.refModule.memoryPolicy"},
            {"value": LANGUAGE_BEHAVIOR_MODULE_ID, "layer_id": "layer_8", "label_key": "layer8.languageBehavior.module.title"},
            {"value": INTERACTION_BEHAVIOR_MODULE_ID, "layer_id": "layer_8", "label_key": "layer8.interactionBehavior.module.title"},
            {"value": "relationship_rule", "layer_id": "layer_11", "label_key": "module.relationship_rule"},
        ],
        "fields": [
            {"value": str(reference["field_id"]), "module_id": str(reference["module_id"]), "label_key": str(reference["i18n_keys"]["field"])}
            for reference in recommended_references
        ],
    }
    nodes = [
        {
            "node_id": SOCIAL_BEHAVIOR_NODE_IDS["input_basis"],
            "node_type": "field_reference",
            "module_id": module_id,
            "layer_id": "layer_8",
            "position": {"x": 0, "y": 0},
            "params": {
                "reference_unit": "field",
                "path_format": "Layer / Module / Field",
                "reference_types": ["required", "optional", "forbidden"],
                "references": [],
                "recommended_references": recommended_references,
                "reference_options": reference_options,
                "no_copy_full_text": True,
                "no_slot": True,
            },
            "i18n_keys": {
                "name": "layer8.socialBehavior.node.inputBasis.title",
                "description": "layer8.socialBehavior.node.inputBasis.description",
                "type_name": "node.type.field_reference",
            },
            "outputs": {"field_references": []},
            "metadata": {"compile_time_only": True, "runtime_enabled": False, "no_execution": True, "reusable_node": True},
        },
        {
            "node_id": SOCIAL_BEHAVIOR_NODE_IDS["core_rules"],
            "node_type": "text_config",
            "module_id": module_id,
            "layer_id": "layer_8",
            "position": {"x": 320, "y": 0},
            "params": {"config_mode": "checkbox_social_core_rules", "checkbox_config": core_checkbox_config},
            "i18n_keys": {
                "name": "layer8.socialBehavior.node.coreRules.title",
                "description": "layer8.socialBehavior.node.coreRules.description",
                "type_name": "node.type.text_config",
            },
            "outputs": {},
            "metadata": {"compile_time_only": True, "runtime_enabled": False, "no_execution": True},
        },
        {
            "node_id": SOCIAL_BEHAVIOR_NODE_IDS["boundary_limits"],
            "node_type": "text_config",
            "module_id": module_id,
            "layer_id": "layer_8",
            "position": {"x": 320, "y": 260},
            "params": {"config_mode": "checkbox_social_boundaries", "checkbox_config": boundary_checkbox_config},
            "i18n_keys": {
                "name": "layer8.socialBehavior.node.boundaryLimits.title",
                "description": "layer8.socialBehavior.node.boundaryLimits.description",
                "type_name": "node.type.text_config",
            },
            "outputs": {},
            "metadata": {"compile_time_only": True, "runtime_enabled": False, "no_execution": True},
        },
        {
            "node_id": SOCIAL_BEHAVIOR_NODE_IDS["output_expression"],
            "node_type": "text_config",
            "module_id": module_id,
            "layer_id": "layer_8",
            "position": {"x": 640, "y": 0},
            "params": {"config_mode": "checkbox_social_output_expression", "checkbox_config": output_checkbox_config},
            "i18n_keys": {
                "name": "layer8.socialBehavior.node.outputExpression.title",
                "description": "layer8.socialBehavior.node.outputExpression.description",
                "type_name": "node.type.text_config",
            },
            "outputs": {},
            "metadata": {"compile_time_only": True, "runtime_enabled": False, "no_execution": True},
        },
        {
            "node_id": SOCIAL_BEHAVIOR_NODE_IDS["validation"],
            "node_type": "text_config",
            "module_id": module_id,
            "layer_id": "layer_8",
            "position": {"x": 960, "y": 0},
            "params": {
                "config_mode": "checkbox_social_validation",
                "checkbox_config": validation_checkbox_config,
                "validation_result": "pending",
                "no_runtime_validation": True,
            },
            "i18n_keys": {
                "name": "layer8.socialBehavior.node.validation.title",
                "description": "layer8.socialBehavior.node.validation.description",
                "type_name": "node.type.text_config",
            },
            "outputs": {},
            "metadata": {"compile_time_only": True, "runtime_enabled": False, "no_execution": True},
        },
    ]
    edges = [
        ("input_basis", "core_rules"),
        ("core_rules", "output_expression"),
        ("output_expression", "validation"),
        ("boundary_limits", "core_rules"),
        ("boundary_limits", "output_expression"),
        ("boundary_limits", "validation"),
    ]
    return _module(
        module_id,
        "social_behavior_config",
        "Social Behavior Module",
        "layer_8",
        status=ProtocolStatus.ready,
        category="behavior",
        is_placeholder=False,
        color_status="green",
        tags=["behavior", "social_behavior", "text_config", "core"],
        module_graph={
            "shell_version": "module_shell_v1",
            "nodes": nodes,
            "edges": [
                {
                    "edge_id": f"{SOCIAL_BEHAVIOR_NODE_IDS[source]}_to_{SOCIAL_BEHAVIOR_NODE_IDS[target]}",
                    "source": SOCIAL_BEHAVIOR_NODE_IDS[source],
                    "source_port": "p_out",
                    "target": SOCIAL_BEHAVIOR_NODE_IDS[target],
                    "target_port": "p_in",
                }
                for source, target in edges
            ],
            "output_key": SOCIAL_BEHAVIOR_OUTPUT_KEY,
            "compile_time_only": True,
        },
        output_schema=[{"key": SOCIAL_BEHAVIOR_OUTPUT_KEY, "type": "object", "required": False, "description": "layer8.socialBehavior.module.output"}],
        ui_config={"shell_version": "module_shell_v1", "classification": "core"},
        i18n_keys={
            "display_name": "layer8.socialBehavior.module.title",
            "description": "layer8.socialBehavior.module.description",
            "output": "layer8.socialBehavior.module.output",
            "module_type": "layer8.socialBehavior.module.type",
        },
        outputs={},
        dr_write_keys=_behavior_dr_write_keys("social_behavior"),
        config={
            "shell_version": "module_shell_v1",
            "module_class": "core",
            "module_type_label_key": "layer8.socialBehavior.module.type",
            "reference_registry": recommended_references,
            "edit_scope": "developer_only",
            "update_level": "versioned_core",
            "requires_recompile": True,
            "compile_time_only": True,
            "text_config_only": True,
            "checkbox_config_only": True,
            "no_runtime_capability": True,
            "no_provider_binding": True,
            "no_slot_binding": True,
        },
        mock_only=True,
        no_execution=True,
    )


def _memory_provider_router_module() -> ModuleV04:
    module_id = MEMORY_PROVIDER_ROUTER_MODULE_ID
    output_key = MEMORY_PROVIDER_ROUTER_OUTPUT_KEY
    node_ids = MEMORY_PROVIDER_ROUTER_NODE_IDS
    param_i18n_keys = {
        "validation_rules": {
            "resident_id_required": "layer5.memoryProviderRouter.param.validation.residentIdRequired",
            "namespace_default": "layer5.memoryProviderRouter.param.validation.namespaceDefault",
            "memory_type_allowlist_only": "layer5.memoryProviderRouter.param.validation.memoryTypeAllowlistOnly",
            "no_cross_resident_access": "layer5.memoryProviderRouter.param.validation.noCrossResidentAccess",
            "no_cross_resident_write": "layer5.memoryProviderRouter.param.validation.noCrossResidentWrite",
            "no_secret_in_memory_payload": "layer5.memoryProviderRouter.param.validation.noSecretInMemoryPayload",
            "no_inferred_fact_as_memory": "layer5.memoryProviderRouter.param.validation.noInferredFactAsMemory",
        },
        "operations": {
            "read": "layer5.memoryProviderRouter.param.operation.read",
            "write": "layer5.memoryProviderRouter.param.operation.write",
            "update": "layer5.memoryProviderRouter.param.operation.update",
            "delete": "layer5.memoryProviderRouter.param.operation.delete",
        },
        "trace_fields": {
            "resident_id": "layer5.memoryProviderRouter.param.traceField.residentId",
            "namespace": "layer5.memoryProviderRouter.param.traceField.namespace",
            "memory_type": "layer5.memoryProviderRouter.param.traceField.memoryType",
            "provider_id": "layer5.memoryProviderRouter.param.traceField.providerId",
            "engine_id": "layer5.memoryProviderRouter.param.traceField.engineId",
            "storage_backend": "layer5.memoryProviderRouter.param.traceField.storageBackend",
        },
        "output": {
            output_key: "layer5.memoryProviderRouter.output.memoryProviderRoutePolicy",
        },
    }
    no_execution_metadata = {
        "compile_time_only": True,
        "runtime_enabled": False,
        "mock_only": True,
        "no_execution": True,
        "no_provider_call": True,
        "no_memory_read_write": True,
        "no_credential_storage": True,
    }
    route_policy = {
        "output_key": output_key,
        "request_contract": {
            "allowed_runtime_fields": ["operation", "resident_id", "namespace", "memory_type", "content", "limit"],
            "required_runtime_fields": ["operation", "resident_id"],
            "operations": MEMORY_PROVIDER_ROUTER_CANONICAL_OPERATIONS,
            "canonical_operations": MEMORY_PROVIDER_ROUTER_CANONICAL_OPERATIONS,
            "accepted_operations": MEMORY_PROVIDER_ROUTER_ACCEPTED_OPERATIONS,
            "operation_aliases": MEMORY_PROVIDER_ROUTER_OPERATION_ALIASES,
        },
        "resident_scope": {
            "resident_id_required": True,
            "cross_resident_access": "forbidden",
        },
        "namespace_policy": deepcopy(MEMORY_PROVIDER_ROUTER_NAMESPACE_POLICY),
        "memory_type_policy": {
            "allowed_memory_types": MEMORY_PROVIDER_ROUTER_ALLOWED_MEMORY_TYPES,
            "unsupported_memory_type_action": "reject",
        },
        "access_policy": {
            "read": MEMORY_PROVIDER_ROUTER_ALLOWED_MEMORY_TYPES,
            "write": MEMORY_PROVIDER_ROUTER_ALLOWED_MEMORY_TYPES,
            "update": MEMORY_PROVIDER_ROUTER_ALLOWED_MEMORY_TYPES,
            "delete": MEMORY_PROVIDER_ROUTER_ALLOWED_MEMORY_TYPES,
            "session_only": ["short_term_memory"],
            "forbidden_memory": ["api_key", "token", "credential", "base_url"],
        },
        "provider_policy": {
            "allowed_backends": ["sqlite", "json", "mock"],
            "default_backend": "mock",
            "runtime_provider_ownership": "runtime_owned_not_stored_in_studio",
        },
        "engine_binding": {
            "slot_id": "slot_memory",
            "engine_id": "memory_mock",
            "provider_id": "provider_memory_mock",
        },
        "trace_policy": {
            "allowed_fields": ["operation", "resident_id", "namespace", "memory_type", "backend", "result_status"],
            "forbidden_fields": ["content", "api_key", "token", "credential", "base_url"],
        },
        **no_execution_metadata,
    }
    node_params = {
        "request_input": {
            "i18n_keys": param_i18n_keys,
            "request_schema": {
                "required": ["operation", "resident_id"],
                "optional": ["namespace", "memory_type", "content", "limit"],
                "operations": MEMORY_PROVIDER_ROUTER_CANONICAL_OPERATIONS,
                "canonical_operations": MEMORY_PROVIDER_ROUTER_CANONICAL_OPERATIONS,
                "accepted_operations": MEMORY_PROVIDER_ROUTER_ACCEPTED_OPERATIONS,
                "operation_aliases": MEMORY_PROVIDER_ROUTER_OPERATION_ALIASES,
            },
            "no_runtime_api_change": True,
        },
        "operation_classifier": {
            "i18n_keys": param_i18n_keys,
            "input": node_ids["request_input"],
            "normalize_rules": ["normalize_operation_alias", "classify_operation", "allow_declared_operations_only", "reject_unknown_operation"],
            "operations": MEMORY_PROVIDER_ROUTER_CANONICAL_OPERATIONS,
            "canonical_operations": MEMORY_PROVIDER_ROUTER_CANONICAL_OPERATIONS,
            "operation_aliases": MEMORY_PROVIDER_ROUTER_OPERATION_ALIASES,
        },
        "resident_resolver": {
            "i18n_keys": param_i18n_keys,
            "input": node_ids["operation_classifier"],
            "required_fields": ["resident_id"],
            "validation_rules": ["resident_id_present", "resident_scope_only", "cross_resident_access_forbidden"],
        },
        "namespace_resolver": {
            "i18n_keys": param_i18n_keys,
            "input": node_ids["resident_resolver"],
            "normalize_rules": [
                "trim_namespace",
                "resolve_memory_type_default_namespace",
                "render_scope_template",
                "reject_cross_scope_namespace",
            ],
            "default_namespace": "private_memory:{resident_id}",
            "namespace_policy": deepcopy(MEMORY_PROVIDER_ROUTER_NAMESPACE_POLICY),
        },
        "type_resolver": {
            "i18n_keys": param_i18n_keys,
            "input": node_ids["namespace_resolver"],
            "normalize_rules": ["resolve_memory_type", "allow_declared_memory_types_only"],
            "allowed_memory_types": MEMORY_PROVIDER_ROUTER_ALLOWED_MEMORY_TYPES,
        },
        "access_control": {
            "i18n_keys": param_i18n_keys,
            "input": node_ids["type_resolver"],
            "retention": "session_or_policy_declared",
            "isolation": "per_resident_namespace",
            "read_policy": "declared_memory_types_only",
            "write_policy": "no_secret_or_credential_memory",
            "session_only": ["short_term_memory"],
            "forbidden_memory": ["api_key", "token", "credential", "base_url"],
        },
        "provider_selector": {
            "i18n_keys": param_i18n_keys,
            "input": node_ids["access_control"],
            "namespace": "memory_type_default",
            "storage_backend": "mock",
            "allowed_backends": ["sqlite", "json", "mock"],
            "enabled": True,
            "credential_storage": "forbidden",
        },
        "engine_binding": {
            "i18n_keys": param_i18n_keys,
            "input": node_ids["provider_selector"],
            "slot_binding": "slot_memory",
            "engine_id": "memory_mock",
            "provider_id": "provider_memory_mock",
            "update_rules": ["slot_memory_to_memory_mock", "provider_memory_mock_only", "no_direct_provider_call"],
        },
        "trace_record": {
            "i18n_keys": param_i18n_keys,
            "input": node_ids["engine_binding"],
            "trace_fields": ["operation", "resident_id", "namespace", "memory_type", "backend", "result_status"],
            "forbidden_trace_fields": ["content", "api_key", "token", "credential", "base_url"],
        },
        "output": {
            "i18n_keys": param_i18n_keys,
            "input": node_ids["trace_record"],
            "output_key": output_key,
            "output_schema": {"type": "object", "required": True},
        },
    }
    node_i18n_suffix = {
        "request_input": "requestInput",
        "operation_classifier": "operationClassifier",
        "resident_resolver": "residentResolver",
        "namespace_resolver": "namespaceResolver",
        "type_resolver": "typeResolver",
        "access_control": "accessControl",
        "provider_selector": "providerSelector",
        "engine_binding": "engineBinding",
        "trace_record": "traceRecord",
        "output": "output",
    }
    nodes = []
    for index, role in enumerate(MEMORY_PROVIDER_ROUTER_NODE_ORDER):
        node_type = MEMORY_PROVIDER_ROUTER_NODE_TYPES[role]
        node_id = node_ids[role]
        nodes.append(
            {
                "node_id": node_id,
                "node_type": node_type,
                "module_id": module_id,
                "layer_id": "layer_5",
                "params": node_params[role],
                "position": {"x": 120 + index * 300, "y": 120},
                "i18n_keys": {
                    "name": f"layer5.memoryProviderRouter.node.{node_i18n_suffix[role]}.title",
                    "description": f"layer5.memoryProviderRouter.node.{node_i18n_suffix[role]}.description",
                    "type_name": f"node.type.{node_type}",
                },
                "outputs": {output_key: route_policy, "module_output": output_key} if role == "output" else {},
                "metadata": no_execution_metadata,
            }
        )

    return _module(
        module_id,
        "memory_router",
        "Memory Provider Router",
        "layer_5",
        status=ProtocolStatus.ready,
        slot_type=SlotType.memory,
        category="memory",
        is_placeholder=False,
        color_status="green",
        tags=["memory", "router", "stage7_4_7"],
        module_graph={
            "shell_version": "module_shell_v1",
            "nodes": nodes,
            "edges": [
                {
                    "edge_id": f"{node_ids[source]}_to_{node_ids[target]}",
                    "source": node_ids[source],
                    "source_port": "p_out",
                    "target": node_ids[target],
                    "target_port": "p_in",
                }
                for source, target in zip(MEMORY_PROVIDER_ROUTER_NODE_ORDER[:-1], MEMORY_PROVIDER_ROUTER_NODE_ORDER[1:])
            ],
            "output_key": output_key,
            "compile_time_only": True,
        },
        output_schema=[{"key": output_key, "type": "object", "required": True, "description": "Memory provider route policy."}],
        slot_bindings=[
            {
                "slot_id": "slot_memory",
                "slot_type": SlotType.memory.value,
                "slot_name": "memory.route",
                "node_role": "memory_router_engine_binding",
            }
        ],
        runtime_mapping={
            "execution_entry": "runtime_only",
            "engine_id": "memory_mock",
            "provider_id": "provider_memory_mock",
            "operations": MEMORY_PROVIDER_ROUTER_CANONICAL_OPERATIONS,
        },
        dr_mapping={output_key: "memory_policy.provider_route"},
        ui_config={"shell_version": "module_shell_v1", "classification": "core", "execution_entry": "slot_only"},
        i18n_keys={
            "display_name": "layer5.memoryProviderRouter.module.title",
            "description": "layer5.memoryProviderRouter.module.description",
            "output": "layer5.memoryProviderRouter.output.memoryProviderRoutePolicy",
        },
        outputs={output_key: route_policy, "module_output": output_key},
        config={
            "shell_version": "module_shell_v1",
            "module_class": "core",
            "compile_time_only": True,
            "mock_only": True,
            "no_execution": True,
            "no_provider_call": True,
            "no_memory_read_write": True,
            "no_credential_storage": True,
        },
        mock_only=True,
        no_execution=True,
    )


MEMORY_RECALL_CLAIM_POLICY: Dict[str, object] = {
    "claim_rule": "verified_read_only",
    "required_evidence": [
        "successful_read",
        "nonempty_record",
        "current_resident_namespace",
        "current_user_scope",
        "current_runtime_session",
    ],
    "rejected_record_states": ["uncertain", "inferred", "expired", "invalid", "revoked"],
    "no_record_action": "do_not_claim_remember",
    "uncertain_record_action": "ask_user_to_confirm_memory_accuracy",
    "uncertain_response": "我不确定自己记得是否准确，需要你再确认一下。",
    "memory_unavailable_action": "state_currently_unable_to_confirm",
    "memory_unavailable_response": "我现在无法确认过去的记录。",
    "inferred_fact_action": "forbid_remembered_claim_until_user_confirmation",
    "model_inference_action": "never_generate_remembered_fact",
    "response_style": "natural_brief_no_internal_fields",
}


def _memory_access_control_module() -> ModuleV04:
    module_id = MEMORY_ACCESS_CONTROL_MODULE_ID
    output_key = MEMORY_ACCESS_CONTROL_OUTPUT_KEY
    node_ids = MEMORY_ACCESS_CONTROL_NODE_IDS
    no_execution_metadata = {
        "compile_time_only": True,
        "runtime_enabled": False,
        "mock_only": True,
        "no_execution": True,
        "no_provider_call": True,
        "no_memory_read_write": True,
        "no_credential_storage": True,
    }
    param_i18n_keys = {
        "fields": {
            "resident_id": "layer5.memoryAccessControl.field.residentId",
            "operation": "layer5.memoryAccessControl.field.operation",
            "namespace": "layer5.memoryAccessControl.field.namespace",
            "memory_type": "layer5.memoryAccessControl.field.memoryType",
            "content": "layer5.memoryAccessControl.field.content",
            "source": "layer5.memoryAccessControl.field.source",
            "memory_category": "layer5.memoryAccessControl.field.memoryCategory",
            "sensitive_level": "layer5.memoryAccessControl.field.sensitiveLevel",
            "decision": "layer5.memoryAccessControl.field.decision",
            "reason": "layer5.memoryAccessControl.field.reason",
            "confidence": "layer5.memoryAccessControl.field.confidence",
            "require_confirmation": "layer5.memoryAccessControl.field.requireConfirmation",
            "timestamp": "layer5.memoryAccessControl.field.timestamp",
        },
        "operations": {
            "read": "layer5.memoryAccessControl.operation.read",
            "write": "layer5.memoryAccessControl.operation.write",
            "update": "layer5.memoryAccessControl.operation.update",
            "delete": "layer5.memoryAccessControl.operation.delete",
        },
        "memory_types": {
            "short_term_memory": "layer5.memoryAccessControl.memoryType.shortTerm",
            "preference_memory": "layer5.memoryAccessControl.memoryType.preference",
            "event_memory": "layer5.memoryAccessControl.memoryType.event",
            "relationship_memory": "layer5.memoryAccessControl.memoryType.relationship",
            "interaction_log": "layer5.memoryAccessControl.memoryType.interactionLog",
        },
        "decisions": {
            "allow": "layer5.memoryAccessControl.decision.allow",
            "confirm": "layer5.memoryAccessControl.decision.confirm",
            "deny": "layer5.memoryAccessControl.decision.deny",
            "remember": "layer5.memoryAccessControl.policy.remember",
            "session_only": "layer5.memoryAccessControl.policy.sessionOnly",
            "ask_confirmation": "layer5.memoryAccessControl.policy.askConfirmation",
        },
        "sensitive_levels": {
            "safe": "layer5.memoryAccessControl.sensitiveLevel.safe",
            "confirm_required": "layer5.memoryAccessControl.sensitiveLevel.confirmRequired",
            "deny": "layer5.memoryAccessControl.sensitiveLevel.deny",
        },
        "output": {
            output_key: "layer5.memoryAccessControl.output.memoryAccessPolicyResult",
        },
    }
    access_policy_result = {
        "output_key": output_key,
        "decision": "confirm",
        "reason": "policy_requires_explicit_user_permission",
        "confidence": 0.8,
        "memory_type": "short_term_memory",
        "require_confirmation": True,
        "request_contract": {
            "fields": ["resident_id", "operation", "namespace", "memory_type", "content", "source"],
            "operations": ["read", "write", "update", "delete"],
        },
        "permission_policy": {
            "user_explicit_remember": "allow",
            "missing_user_authorization": "confirm",
            "sensitive_information": "deny",
        },
        "memory_categories": ["short_term_memory", "preference_memory", "event_memory", "relationship_memory", "interaction_log"],
        "sensitive_policy": {
            "safe": "allow",
            "confirm_required": "confirm",
            "deny": "deny",
            "default_for_inferred_fact": "deny",
        },
        "recall_claim_policy": deepcopy(MEMORY_RECALL_CLAIM_POLICY),
        "policy_actions": ["remember", "session_only", "ask_confirmation", "deny"],
        "audit_policy": {
            "record_fields": ["operation", "memory_type", "decision", "reason", "timestamp"],
            "forbidden_fields": ["secret", "raw_sensitive_content", "api_key", "token", "credential"],
        },
        **no_execution_metadata,
    }
    node_params = {
        "request_input": {
            "i18n_keys": param_i18n_keys,
            "request_fields": ["resident_id", "operation", "namespace", "memory_type", "content", "source"],
            "operations": ["read", "write", "update", "delete"],
            "request_scope": "runtime_memory_access_request",
            "no_runtime_api_change": True,
        },
        "user_permission_check": {
            "i18n_keys": param_i18n_keys,
            "input": node_ids["request_input"],
            "required_fields": ["resident_id", "operation"],
            "validation_rules": ["explicit_user_remember_allows", "missing_user_authorization_requires_confirm", "sensitive_information_denies"],
            "permission_outcomes": {"explicit_remember": "allow", "unauthorized": "confirm", "sensitive": "deny"},
        },
        "type_classifier": {
            "i18n_keys": param_i18n_keys,
            "input": node_ids["user_permission_check"],
            "normalize_rules": ["classify_memory_type", "emit_memory_category", "allow_declared_memory_categories_only"],
            "memory_categories": ["short_term_memory", "preference_memory", "event_memory", "relationship_memory", "interaction_log"],
            "output": "memory_category",
        },
        "sensitive_check": {
            "i18n_keys": param_i18n_keys,
            "input": node_ids["type_classifier"],
            "validation_rules": [
                "identity_sensitive_information_requires_confirm",
                "medical_information_requires_confirm",
                "political_preference_requires_confirm",
                "religious_information_requires_confirm",
                "financial_privacy_requires_confirm",
                "unconfirmed_inference_denied",
            ],
            "forbidden_default_save": [
                "identity_sensitive_information",
                "medical_information",
                "political_preference",
                "religious_information",
                "financial_privacy",
                "unconfirmed_inference",
            ],
            "sensitive_levels": ["safe", "confirm_required", "deny"],
            "output": "sensitive_level",
        },
        "policy_match": {
            "i18n_keys": param_i18n_keys,
            "input": node_ids["sensitive_check"],
            "policy_source": "memory_policy",
            "policy_actions": ["remember", "session_only", "ask_confirmation", "deny"],
            "priority": ["explicit_authorization", "user_preference", "normal_dialogue"],
            "inferred_fact_default": "deny",
        },
        "access_decision": {
            "i18n_keys": param_i18n_keys,
            "input": node_ids["policy_match"],
            "decision_values": ["allow", "confirm", "deny"],
            "outputs": ["decision", "reason", "confidence"],
            "update_rules": ["combine_permission_type_sensitivity_policy", "deny_overrides_confirm", "confirm_overrides_allow"],
        },
        "audit": {
            "i18n_keys": param_i18n_keys,
            "input": node_ids["access_decision"],
            "audit_fields": ["operation", "memory_type", "decision", "reason", "timestamp"],
            "forbidden_audit_fields": ["secret", "raw_sensitive_content", "api_key", "token", "credential"],
            "audit_scope": "reason_record_only",
        },
        "output": {
            "i18n_keys": param_i18n_keys,
            "input": node_ids["audit"],
            "output_key": output_key,
            "output_schema": {
                "decision": "string",
                "reason": "string",
                "confidence": "number",
                "memory_type": "string",
                "require_confirmation": "boolean",
            },
        },
    }
    node_i18n_suffix = {
        "request_input": "requestInput",
        "user_permission_check": "userPermissionCheck",
        "type_classifier": "typeClassifier",
        "sensitive_check": "sensitiveCheck",
        "policy_match": "policyMatch",
        "access_decision": "accessDecision",
        "audit": "audit",
        "output": "output",
    }
    nodes = []
    for index, role in enumerate(MEMORY_ACCESS_CONTROL_NODE_ORDER):
        node_type = MEMORY_ACCESS_CONTROL_NODE_TYPES[role]
        node_id = node_ids[role]
        nodes.append(
            {
                "node_id": node_id,
                "node_type": node_type,
                "module_id": module_id,
                "layer_id": "layer_5",
                "params": node_params[role],
                "position": {"x": 120 + index * 300, "y": 120},
                "i18n_keys": {
                    "name": f"layer5.memoryAccessControl.node.{node_i18n_suffix[role]}.title",
                    "description": f"layer5.memoryAccessControl.node.{node_i18n_suffix[role]}.description",
                    "type_name": f"node.type.{node_type}",
                },
                "outputs": {output_key: access_policy_result, "module_output": output_key} if role == "output" else {},
                "metadata": no_execution_metadata,
            }
        )

    return _module(
        module_id,
        "memory_policy",
        "Memory Access Control",
        "layer_5",
        status=ProtocolStatus.ready,
        slot_type=SlotType.memory,
        category="memory",
        is_placeholder=False,
        color_status="green",
        tags=["memory", "access_control", "stage7_4_7"],
        module_graph={
            "shell_version": "module_shell_v1",
            "nodes": nodes,
            "edges": [
                {
                    "edge_id": f"{node_ids[source]}_to_{node_ids[target]}",
                    "source": node_ids[source],
                    "source_port": "p_out",
                    "target": node_ids[target],
                    "target_port": "p_in",
                }
                for source, target in zip(MEMORY_ACCESS_CONTROL_NODE_ORDER[:-1], MEMORY_ACCESS_CONTROL_NODE_ORDER[1:])
            ],
            "output_key": output_key,
            "compile_time_only": True,
        },
        output_schema=[{"key": output_key, "type": "object", "required": True, "description": "Memory access policy result."}],
        slot_bindings=[
            {
                "slot_id": "slot_memory",
                "slot_type": SlotType.memory.value,
                "slot_name": "memory.policy",
                "node_role": "access_control",
            }
        ],
        runtime_mapping={"execution_entry": "runtime_only", "policy_type": "memory_access_control"},
        dr_mapping={"memory_access_policy": "memory_policy.access_control"},
        ui_config={"shell_version": "module_shell_v1", "classification": "core", "execution_entry": "slot_only"},
        i18n_keys={
            "display_name": "layer5.memoryAccessControl.module.title",
            "description": "layer5.memoryAccessControl.module.description",
            "output": "layer5.memoryAccessControl.output.memoryAccessPolicyResult",
        },
        outputs={output_key: access_policy_result, "module_output": output_key},
        config={
            "shell_version": "module_shell_v1",
            "module_class": "core",
            "compile_time_only": True,
            "mock_only": True,
            "no_execution": True,
            "no_provider_call": True,
            "no_memory_read_write": True,
            "no_credential_storage": True,
        },
        mock_only=True,
        no_execution=True,
    )


def _short_term_memory_module() -> ModuleV04:
    module_id = SHORT_TERM_MEMORY_MODULE_ID
    output_key = SHORT_TERM_MEMORY_OUTPUT_KEY
    node_ids = SHORT_TERM_MEMORY_NODE_IDS
    no_execution_metadata = {
        "compile_time_only": True,
        "runtime_enabled": False,
        "mock_only": True,
        "no_execution": True,
        "no_provider_call": True,
        "no_memory_read_write": True,
        "no_credential_storage": True,
        "session_scoped_only": True,
    }
    param_i18n_keys = {
        "fields": {
            "current_topic": "layer5.shortTermMemory.field.currentTopic",
            "current_task": "layer5.shortTermMemory.field.currentTask",
            "recent_dialogue": "layer5.shortTermMemory.field.recentDialogue",
            "temporary_state": "layer5.shortTermMemory.field.temporaryState",
            "temporary_emotion": "layer5.shortTermMemory.field.temporaryEmotion",
        },
        "retention": {
            "session": "layer5.shortTermMemory.retention.session",
        },
        "output": {
            output_key: "layer5.shortTermMemory.output.shortTermMemoryContext",
        },
    }
    short_term_context = {
        "output_key": output_key,
        "retention": "session",
        "fields": {
            "current_topic": "",
            "current_task": "",
            "recent_dialogue": [],
            "temporary_state": "",
            "temporary_emotion": "",
        },
        "expires_on": "session_end",
        "allowed_content": ["current_dialogue", "current_task", "temporary_emotion"],
        "forbidden_content": ["persistent_user_preference", "identity_information", "relationship_state", "sensitive_information", "vector_retrieval"],
        **no_execution_metadata,
    }
    node_params = {
        "input": {
            "i18n_keys": param_i18n_keys,
            "input_scope": "current_session_content",
            "accepted_fields": ["current_dialogue", "current_task", "recent_interaction", "temporary_state"],
            "no_persistent_storage": True,
        },
        "context_normalize": {
            "i18n_keys": param_i18n_keys,
            "input": node_ids["input"],
            "normalize_rules": ["extract_current_topic", "extract_current_task", "summarize_recent_dialogue", "preserve_temporary_state"],
            "outputs": ["current_topic", "current_task", "recent_dialogue", "temporary_state"],
        },
        "retention_policy": {
            "i18n_keys": param_i18n_keys,
            "input": node_ids["context_normalize"],
            "retention": "session",
            "save_allowed": ["current_dialogue", "current_task", "temporary_emotion"],
            "save_forbidden": ["persistent_user_preference", "identity_information", "relationship_state", "sensitive_information"],
            "expires_on": "session_end",
            "no_vector_retrieval": True,
            "no_personality_growth": True,
        },
        "output": {
            "i18n_keys": param_i18n_keys,
            "input": node_ids["retention_policy"],
            "output_key": output_key,
            "output_schema": {
                "current_topic": "string",
                "current_task": "string",
                "recent_dialogue": "array",
                "temporary_state": "string",
                "temporary_emotion": "string",
                "retention": "session",
            },
        },
    }
    node_i18n_suffix = {
        "input": "input",
        "context_normalize": "contextNormalize",
        "retention_policy": "retentionPolicy",
        "output": "output",
    }
    nodes = []
    for index, role in enumerate(SHORT_TERM_MEMORY_NODE_ORDER):
        node_type = SHORT_TERM_MEMORY_NODE_TYPES[role]
        node_id = node_ids[role]
        nodes.append(
            {
                "node_id": node_id,
                "node_type": node_type,
                "module_id": module_id,
                "layer_id": "layer_5",
                "params": node_params[role],
                "position": {"x": 120 + index * 300, "y": 120},
                "i18n_keys": {
                    "name": f"layer5.shortTermMemory.node.{node_i18n_suffix[role]}.title",
                    "description": f"layer5.shortTermMemory.node.{node_i18n_suffix[role]}.description",
                    "type_name": f"node.type.{node_type}",
                },
                "outputs": {output_key: short_term_context, "module_output": output_key} if role == "output" else {},
                "metadata": no_execution_metadata,
            }
        )

    return _module(
        module_id,
        "memory",
        "Short-term Memory",
        "layer_5",
        status=ProtocolStatus.ready,
        slot_type=SlotType.memory,
        category="memory",
        is_placeholder=False,
        color_status="green",
        tags=["memory", "short_term", "stage7_4_7"],
        module_graph={
            "shell_version": "module_shell_v1",
            "nodes": nodes,
            "edges": [
                {
                    "edge_id": f"{node_ids[source]}_to_{node_ids[target]}",
                    "source": node_ids[source],
                    "source_port": "p_out",
                    "target": node_ids[target],
                    "target_port": "p_in",
                }
                for source, target in zip(SHORT_TERM_MEMORY_NODE_ORDER[:-1], SHORT_TERM_MEMORY_NODE_ORDER[1:])
            ],
            "output_key": output_key,
            "compile_time_only": True,
        },
        output_schema=[{"key": output_key, "type": "object", "required": True, "description": "Short-term session memory context."}],
        ui_config={"shell_version": "module_shell_v1", "classification": "core", "execution_entry": "slot_only"},
        i18n_keys={
            "display_name": "layer5.shortTermMemory.module.title",
            "description": "layer5.shortTermMemory.module.description",
            "output": "layer5.shortTermMemory.output.shortTermMemoryContext",
        },
        outputs={output_key: short_term_context, "module_output": output_key},
        config={
            "shell_version": "module_shell_v1",
            "module_class": "core",
            "compile_time_only": True,
            "mock_only": True,
            "no_execution": True,
            "no_provider_call": True,
            "no_memory_read_write": True,
            "no_credential_storage": True,
            "session_scoped_only": True,
        },
        mock_only=True,
        no_execution=True,
    )


def _preference_memory_module() -> ModuleV04:
    module_id = PREFERENCE_MEMORY_MODULE_ID
    output_key = PREFERENCE_MEMORY_OUTPUT_KEY
    node_ids = PREFERENCE_MEMORY_NODE_IDS
    no_execution_metadata = {
        "compile_time_only": True,
        "runtime_enabled": False,
        "mock_only": True,
        "no_execution": True,
        "no_provider_call": True,
        "no_memory_read_write": True,
        "no_credential_storage": True,
        "no_personality_core_update": True,
        "no_safety_boundary_override": True,
    }
    param_i18n_keys = {
        "fields": {
            "preference_key": "layer5.preferenceMemory.field.preferenceKey",
            "preference_value": "layer5.preferenceMemory.field.preferenceValue",
            "source": "layer5.preferenceMemory.field.source",
            "confidence": "layer5.preferenceMemory.field.confidence",
        },
        "decisions": {
            "allow": "layer5.preferenceMemory.decision.allow",
            "confirm": "layer5.preferenceMemory.decision.confirm",
        },
        "output": {
            output_key: "layer5.preferenceMemory.output.preferenceMemory",
        },
    }
    preference_policy = {
        "output_key": output_key,
        "fields": {
            "preference_key": "",
            "preference_value": "",
            "source": "",
            "confidence": 0.0,
        },
        "decisions": ["allow", "confirm"],
        "save_allowed": ["expression_preference", "usage_habit", "explicit_interest"],
        "save_forbidden": ["sensitive_attribute", "inferred_fact", "personality_core", "safety_boundary"],
        **no_execution_metadata,
    }
    node_params = {
        "input": {
            "i18n_keys": param_i18n_keys,
            "input_scope": "candidate_preference",
            "accepted_fields": ["preference_key", "preference_value", "source", "confidence"],
        },
        "classifier": {
            "i18n_keys": param_i18n_keys,
            "input": node_ids["input"],
            "normalize_rules": ["extract_preference_key", "extract_preference_value", "preserve_source", "estimate_confidence"],
            "outputs": ["preference_key", "preference_value", "source", "confidence"],
        },
        "confirmation_check": {
            "i18n_keys": param_i18n_keys,
            "input": node_ids["classifier"],
            "decision_rules": {
                "explicit_user_preference": "allow",
                "ambiguous_preference": "confirm",
            },
            "decisions": ["allow", "confirm"],
        },
        "policy": {
            "i18n_keys": param_i18n_keys,
            "input": node_ids["confirmation_check"],
            "save_allowed": ["expression_preference", "usage_habit", "explicit_interest"],
            "save_forbidden": ["sensitive_attribute", "inferred_fact"],
            "protected_boundaries": ["personality_core", "safety_boundary"],
            "no_personality_core_update": True,
            "no_safety_boundary_override": True,
        },
        "output": {
            "i18n_keys": param_i18n_keys,
            "input": node_ids["policy"],
            "output_key": output_key,
            "output_schema": {
                "preference_key": "string",
                "preference_value": "string",
                "source": "string",
                "confidence": "number",
                "decision": "allow_or_confirm",
            },
        },
    }
    node_i18n_suffix = {
        "input": "input",
        "classifier": "classifier",
        "confirmation_check": "confirmationCheck",
        "policy": "policy",
        "output": "output",
    }
    nodes = []
    for index, role in enumerate(PREFERENCE_MEMORY_NODE_ORDER):
        node_type = PREFERENCE_MEMORY_NODE_TYPES[role]
        node_id = node_ids[role]
        nodes.append(
            {
                "node_id": node_id,
                "node_type": node_type,
                "module_id": module_id,
                "layer_id": "layer_5",
                "params": node_params[role],
                "position": {"x": 120 + index * 300, "y": 120},
                "i18n_keys": {
                    "name": f"layer5.preferenceMemory.node.{node_i18n_suffix[role]}.title",
                    "description": f"layer5.preferenceMemory.node.{node_i18n_suffix[role]}.description",
                    "type_name": f"node.type.{node_type}",
                },
                "outputs": {output_key: preference_policy, "module_output": output_key} if role == "output" else {},
                "metadata": no_execution_metadata,
            }
        )

    return _module(
        module_id,
        "memory",
        "Preference Memory",
        "layer_5",
        status=ProtocolStatus.ready,
        slot_type=SlotType.memory,
        category="memory",
        is_placeholder=False,
        color_status="green",
        tags=["memory", "preference", "stage7_4_7"],
        module_graph={
            "shell_version": "module_shell_v1",
            "nodes": nodes,
            "edges": [
                {
                    "edge_id": f"{node_ids[source]}_to_{node_ids[target]}",
                    "source": node_ids[source],
                    "source_port": "p_out",
                    "target": node_ids[target],
                    "target_port": "p_in",
                }
                for source, target in zip(PREFERENCE_MEMORY_NODE_ORDER[:-1], PREFERENCE_MEMORY_NODE_ORDER[1:])
            ],
            "output_key": output_key,
            "compile_time_only": True,
        },
        output_schema=[{"key": output_key, "type": "object", "required": True, "description": "Confirmed long-term user preference memory."}],
        ui_config={"shell_version": "module_shell_v1", "classification": "core", "execution_entry": "slot_only"},
        i18n_keys={
            "display_name": "layer5.preferenceMemory.module.title",
            "description": "layer5.preferenceMemory.module.description",
            "output": "layer5.preferenceMemory.output.preferenceMemory",
        },
        outputs={output_key: preference_policy, "module_output": output_key},
        config={
            "shell_version": "module_shell_v1",
            "module_class": "core",
            "compile_time_only": True,
            "mock_only": True,
            "no_execution": True,
            "no_provider_call": True,
            "no_memory_read_write": True,
            "no_credential_storage": True,
            "no_personality_core_update": True,
            "no_safety_boundary_override": True,
        },
        mock_only=True,
        no_execution=True,
    )


def _event_memory_module() -> ModuleV04:
    module_id = EVENT_MEMORY_MODULE_ID
    output_key = EVENT_MEMORY_OUTPUT_KEY
    node_ids = EVENT_MEMORY_NODE_IDS
    no_execution_metadata = {
        "compile_time_only": True,
        "runtime_enabled": False,
        "mock_only": True,
        "no_execution": True,
        "no_provider_call": True,
        "no_memory_read_write": True,
        "no_credential_storage": True,
        "no_personality_auto_change": True,
    }
    param_i18n_keys = {
        "fields": {
            "event_content": "layer5.eventMemory.field.eventContent",
            "source": "layer5.eventMemory.field.source",
            "timestamp": "layer5.eventMemory.field.timestamp",
            "context": "layer5.eventMemory.field.context",
            "event_type": "layer5.eventMemory.field.eventType",
            "event_summary": "layer5.eventMemory.field.eventSummary",
            "confidence": "layer5.eventMemory.field.confidence",
            "importance": "layer5.eventMemory.field.importance",
        },
        "event_types": {
            "project": "layer5.eventMemory.eventType.project",
            "milestone": "layer5.eventMemory.eventType.milestone",
            "interaction": "layer5.eventMemory.eventType.interaction",
            "personal_story": "layer5.eventMemory.eventType.personalStory",
        },
        "importance": {
            "high": "layer5.eventMemory.importance.high",
            "medium": "layer5.eventMemory.importance.medium",
            "low": "layer5.eventMemory.importance.low",
        },
        "lifecycle": {
            "active": "layer5.eventMemory.lifecycle.active",
            "archived": "layer5.eventMemory.lifecycle.archived",
            "forgotten": "layer5.eventMemory.lifecycle.forgotten",
        },
        "output": {
            output_key: "layer5.eventMemory.output.eventMemory",
        },
    }
    event_policy = {
        "output_key": output_key,
        "fields": {
            "event_type": "",
            "event_summary": "",
            "source": "",
            "timestamp": "",
            "confidence": 0.0,
            "importance": "medium",
            "lifecycle_status": "active",
        },
        "event_types": ["project", "milestone", "interaction", "personal_story"],
        "importance_levels": ["high", "medium", "low"],
        "lifecycle_states": ["active", "archived", "forgotten"],
        "save_allowed": ["brief_summary", "timestamp", "event_meaning"],
        "save_forbidden": ["full_chat_log", "one_off_small_talk", "sensitive_event", "unconfirmed_inference", "raw_sensitive_content"],
        **no_execution_metadata,
    }
    node_params = {
        "input": {
            "i18n_keys": param_i18n_keys,
            "input_scope": "candidate_event",
            "accepted_fields": ["event_content", "source", "timestamp", "context"],
        },
        "classifier": {
            "i18n_keys": param_i18n_keys,
            "input": node_ids["input"],
            "normalize_rules": ["extract_event_type", "summarize_event", "preserve_source", "estimate_confidence"],
            "event_types": ["project", "milestone", "interaction", "personal_story"],
            "outputs": ["event_type", "event_summary", "source", "confidence"],
        },
        "importance_evaluation": {
            "i18n_keys": param_i18n_keys,
            "input": node_ids["classifier"],
            "high_value_rules": ["explicit_user_remember_request", "long_term_goal", "important_experience"],
            "low_value_rules": ["ordinary_chat", "temporary_emotion"],
            "importance": ["high", "medium", "low"],
        },
        "summary_policy": {
            "i18n_keys": param_i18n_keys,
            "input": node_ids["importance_evaluation"],
            "save_allowed": ["brief_summary", "timestamp", "event_meaning"],
            "save_forbidden": ["full_chat_log", "raw_sensitive_content", "sensitive_event", "unconfirmed_inference"],
            "no_full_chat_log": True,
            "no_sensitive_event_storage": True,
        },
        "lifecycle_policy": {
            "i18n_keys": param_i18n_keys,
            "input": node_ids["summary_policy"],
            "lifecycle_states": ["active", "archived", "forgotten"],
            "long_term_rule": "important_events_persist",
            "decay_rule": "ordinary_events_may_decay",
        },
        "output": {
            "i18n_keys": param_i18n_keys,
            "input": node_ids["lifecycle_policy"],
            "output_key": output_key,
            "output_schema": {
                "event_type": "string",
                "event_summary": "string",
                "source": "string",
                "timestamp": "string",
                "confidence": "number",
                "importance": "high_medium_or_low",
                "lifecycle_status": "active_archived_or_forgotten",
            },
        },
    }
    node_i18n_suffix = {
        "input": "input",
        "classifier": "classifier",
        "importance_evaluation": "importanceEvaluation",
        "summary_policy": "summaryPolicy",
        "lifecycle_policy": "lifecyclePolicy",
        "output": "output",
    }
    nodes = []
    for index, role in enumerate(EVENT_MEMORY_NODE_ORDER):
        node_type = EVENT_MEMORY_NODE_TYPES[role]
        node_id = node_ids[role]
        nodes.append(
            {
                "node_id": node_id,
                "node_type": node_type,
                "module_id": module_id,
                "layer_id": "layer_5",
                "params": node_params[role],
                "position": {"x": 120 + index * 300, "y": 120},
                "i18n_keys": {
                    "name": f"layer5.eventMemory.node.{node_i18n_suffix[role]}.title",
                    "description": f"layer5.eventMemory.node.{node_i18n_suffix[role]}.description",
                    "type_name": f"node.type.{node_type}",
                },
                "outputs": {output_key: event_policy, "module_output": output_key} if role == "output" else {},
                "metadata": no_execution_metadata,
            }
        )

    return _module(
        module_id,
        "memory",
        "Event Memory",
        "layer_5",
        status=ProtocolStatus.ready,
        slot_type=SlotType.memory,
        category="memory",
        is_placeholder=False,
        color_status="green",
        tags=["memory", "event", "stage7_4_7"],
        module_graph={
            "shell_version": "module_shell_v1",
            "nodes": nodes,
            "edges": [
                {
                    "edge_id": f"{node_ids[source]}_to_{node_ids[target]}",
                    "source": node_ids[source],
                    "source_port": "p_out",
                    "target": node_ids[target],
                    "target_port": "p_in",
                }
                for source, target in zip(EVENT_MEMORY_NODE_ORDER[:-1], EVENT_MEMORY_NODE_ORDER[1:])
            ],
            "output_key": output_key,
            "compile_time_only": True,
        },
        output_schema=[{"key": output_key, "type": "object", "required": True, "description": "Important shared event memory."}],
        ui_config={"shell_version": "module_shell_v1", "classification": "core", "execution_entry": "slot_only"},
        i18n_keys={
            "display_name": "layer5.eventMemory.module.title",
            "description": "layer5.eventMemory.module.description",
            "output": "layer5.eventMemory.output.eventMemory",
        },
        outputs={output_key: event_policy, "module_output": output_key},
        config={
            "shell_version": "module_shell_v1",
            "module_class": "core",
            "compile_time_only": True,
            "mock_only": True,
            "no_execution": True,
            "no_provider_call": True,
            "no_memory_read_write": True,
            "no_credential_storage": True,
            "no_personality_auto_change": True,
        },
        mock_only=True,
        no_execution=True,
    )


def _relationship_memory_module() -> ModuleV04:
    module_id = RELATIONSHIP_MEMORY_MODULE_ID
    output_key = RELATIONSHIP_MEMORY_OUTPUT_KEY
    node_ids = RELATIONSHIP_MEMORY_NODE_IDS
    no_execution_metadata = {
        "compile_time_only": True,
        "runtime_enabled": False,
        "mock_only": True,
        "no_execution": True,
        "no_provider_call": True,
        "no_memory_read_write": True,
        "no_credential_storage": True,
        "no_real_human_emotion_simulation": True,
        "no_dependency_induction": True,
        "no_default_romantic_relationship": True,
        "no_real_relationship_replacement": True,
        "no_identity_modification": True,
    }
    param_i18n_keys = {
        "fields": {
            "interaction_context": "layer5.relationshipMemory.field.interactionContext",
            "user_feedback": "layer5.relationshipMemory.field.userFeedback",
            "communication_pattern": "layer5.relationshipMemory.field.communicationPattern",
            "interaction_frequency": "layer5.relationshipMemory.field.interactionFrequency",
            "communication_style": "layer5.relationshipMemory.field.communicationStyle",
            "user_preference": "layer5.relationshipMemory.field.userPreference",
            "familiarity_signal": "layer5.relationshipMemory.field.familiaritySignal",
            "familiarity": "layer5.relationshipMemory.field.familiarity",
            "trust": "layer5.relationshipMemory.field.trust",
            "comfort_level": "layer5.relationshipMemory.field.comfortLevel",
            "interaction_style": "layer5.relationshipMemory.field.interactionStyle",
        },
        "output": {
            output_key: "layer5.relationshipMemory.output.relationshipMemory",
        },
    }
    relationship_policy = {
        "output_key": output_key,
        "fields": {
            "familiarity": "",
            "trust": "",
            "comfort_level": "",
            "interaction_style": "",
        },
        "allowed_content": ["communication_habit", "user_preference", "interaction_history"],
        "forbidden_content": [
            "emotional_binding",
            "dependency_induction",
            "default_romantic_relationship",
            "real_relationship_replacement",
            "private_secret",
            "inferred_real_emotion",
            "inferred_dependency",
            "inferred_private_relationship_state",
        ],
        "change_policy": "gradual_only",
        **no_execution_metadata,
    }
    node_params = {
        "input": {
            "i18n_keys": param_i18n_keys,
            "input_scope": "candidate_interaction_event",
            "accepted_fields": ["interaction_context", "user_feedback", "communication_pattern"],
        },
        "pattern_analysis": {
            "i18n_keys": param_i18n_keys,
            "input": node_ids["input"],
            "normalize_rules": [
                "extract_interaction_frequency",
                "extract_communication_style",
                "extract_explicit_user_preference",
                "detect_familiarity_signal",
            ],
            "outputs": ["interaction_frequency", "communication_style", "user_preference", "familiarity_signal"],
        },
        "state_evaluation": {
            "i18n_keys": param_i18n_keys,
            "input": node_ids["pattern_analysis"],
            "evaluated_fields": ["familiarity", "trust", "comfort_level"],
            "decision_rules": ["explicit_interaction_only", "no_inferred_real_emotion", "no_inferred_dependency", "no_inferred_private_relationship_state"],
            "forbidden_inference": ["user_real_emotion", "user_dependency_level", "user_private_relationship_state"],
        },
        "boundary_policy": {
            "i18n_keys": param_i18n_keys,
            "input": node_ids["state_evaluation"],
            "save_allowed": ["communication_habit", "user_preference", "interaction_history"],
            "save_forbidden": ["emotional_binding", "dependency_induction", "default_romantic_relationship", "real_relationship_replacement"],
            "no_real_human_emotion_simulation": True,
            "no_dependency_induction": True,
            "no_default_romantic_relationship": True,
            "no_real_relationship_replacement": True,
        },
        "state_update": {
            "i18n_keys": param_i18n_keys,
            "input": node_ids["boundary_policy"],
            "update_fields": ["familiarity", "trust", "interaction_style"],
            "update_policy": "gradual_only",
            "single_event_large_change": "deny",
        },
        "output": {
            "i18n_keys": param_i18n_keys,
            "input": node_ids["state_update"],
            "output_key": output_key,
            "output_schema": {
                "familiarity": "string",
                "trust": "string",
                "comfort_level": "string",
                "interaction_style": "string",
            },
        },
    }
    node_i18n_suffix = {
        "input": "input",
        "pattern_analysis": "patternAnalysis",
        "state_evaluation": "stateEvaluation",
        "boundary_policy": "boundaryPolicy",
        "state_update": "stateUpdate",
        "output": "output",
    }
    nodes = []
    for index, role in enumerate(RELATIONSHIP_MEMORY_NODE_ORDER):
        node_type = RELATIONSHIP_MEMORY_NODE_TYPES[role]
        node_id = node_ids[role]
        nodes.append(
            {
                "node_id": node_id,
                "node_type": node_type,
                "module_id": module_id,
                "layer_id": "layer_5",
                "params": node_params[role],
                "position": {"x": 120 + index * 300, "y": 120},
                "i18n_keys": {
                    "name": f"layer5.relationshipMemory.node.{node_i18n_suffix[role]}.title",
                    "description": f"layer5.relationshipMemory.node.{node_i18n_suffix[role]}.description",
                    "type_name": f"node.type.{node_type}",
                },
                "outputs": {output_key: relationship_policy, "module_output": output_key} if role == "output" else {},
                "metadata": no_execution_metadata,
            }
        )

    return _module(
        module_id,
        "memory",
        "Relationship Memory",
        "layer_5",
        status=ProtocolStatus.ready,
        slot_type=SlotType.memory,
        category="memory",
        is_placeholder=False,
        color_status="green",
        tags=["memory", "relationship", "stage7_4_7"],
        module_graph={
            "shell_version": "module_shell_v1",
            "nodes": nodes,
            "edges": [
                {
                    "edge_id": f"{node_ids[source]}_to_{node_ids[target]}",
                    "source": node_ids[source],
                    "source_port": "p_out",
                    "target": node_ids[target],
                    "target_port": "p_in",
                }
                for source, target in zip(RELATIONSHIP_MEMORY_NODE_ORDER[:-1], RELATIONSHIP_MEMORY_NODE_ORDER[1:])
            ],
            "output_key": output_key,
            "compile_time_only": True,
        },
        output_schema=[{"key": output_key, "type": "object", "required": True, "description": "Relationship memory policy."}],
        ui_config={"shell_version": "module_shell_v1", "classification": "core", "execution_entry": "slot_only"},
        i18n_keys={
            "display_name": "layer5.relationshipMemory.module.title",
            "description": "layer5.relationshipMemory.module.description",
            "output": "layer5.relationshipMemory.output.relationshipMemory",
        },
        outputs={output_key: relationship_policy, "module_output": output_key},
        config={
            "shell_version": "module_shell_v1",
            "module_class": "core",
            "compile_time_only": True,
            "mock_only": True,
            "no_execution": True,
            "no_provider_call": True,
            "no_memory_read_write": True,
            "no_credential_storage": True,
            "no_real_human_emotion_simulation": True,
            "no_dependency_induction": True,
            "no_default_romantic_relationship": True,
            "no_real_relationship_replacement": True,
            "no_identity_modification": True,
        },
        mock_only=True,
        no_execution=True,
    )


def _memory_update_module() -> ModuleV04:
    module_id = MEMORY_UPDATE_MODULE_ID
    output_key = MEMORY_UPDATE_OUTPUT_KEY
    node_ids = MEMORY_UPDATE_NODE_IDS
    no_execution_metadata = {
        "compile_time_only": True,
        "runtime_enabled": False,
        "mock_only": True,
        "no_execution": True,
        "no_provider_call": True,
        "no_memory_read_write": True,
        "no_database_write": True,
        "no_dr_writeback": True,
        "no_runtime_trace_to_dr": True,
        "no_secret_storage": True,
        "no_raw_sensitive_content": True,
        "no_vector_memory": True,
        "no_personality_growth": True,
        "no_multi_resident_memory_share": True,
    }
    allowed_operations = ["create", "update", "delete", "confirm", "archive"]
    param_i18n_keys = {
        "fields": {
            "operation": "layer5.memoryUpdate.field.operation",
            "memory_type": "layer5.memoryUpdate.field.memoryType",
            "memory_key": "layer5.memoryUpdate.field.memoryKey",
            "memory_value": "layer5.memoryUpdate.field.memoryValue",
            "source": "layer5.memoryUpdate.field.source",
            "confidence": "layer5.memoryUpdate.field.confidence",
            "decision": "layer5.memoryUpdate.field.decision",
            "reason": "layer5.memoryUpdate.field.reason",
            "requires_confirmation": "layer5.memoryUpdate.field.requiresConfirmation",
            "write_boundary": "layer5.memoryUpdate.field.writeBoundary",
            "timestamp": "layer5.memoryUpdate.field.timestamp",
        },
        "operations": {
            "create": "layer5.memoryUpdate.operation.create",
            "update": "layer5.memoryUpdate.operation.update",
            "delete": "layer5.memoryUpdate.operation.delete",
            "confirm": "layer5.memoryUpdate.operation.confirm",
            "archive": "layer5.memoryUpdate.operation.archive",
        },
        "decisions": {
            "allow": "layer5.memoryUpdate.decision.allow",
            "confirm": "layer5.memoryUpdate.decision.confirm",
            "deny": "layer5.memoryUpdate.decision.deny",
        },
        "output": {
            output_key: "layer5.memoryUpdate.output.memoryUpdatePolicy",
        },
    }
    update_policy = {
        "output_key": output_key,
        "allowed_operations": allowed_operations,
        "decision_values": ["allow", "confirm", "deny"],
        "policy_priority": {
            "explicit_user_request_priority": "highest",
            "confirmed_preference": "high",
            "project_context": "high",
            "relationship_state": "gradual",
            "temporary_emotion": "session_only",
            "inferred_fact": "deny",
        },
        "confirmation_policy": {
            "explicit_user_remember_request": "allow_without_second_confirmation",
            "ambiguous_preference": "confirm",
            "sensitive_information": "confirm_or_deny",
            "inferred_fact": "deny",
        },
        "conflict_policy": {
            "new_preference_overwrites_old_preference": "confirm",
            "relationship_state_large_jump": "deny_or_confirm",
            "duplicate_event_memory": "deny",
            "low_confidence_over_high_confidence": "deny",
        },
        "audit_policy": {
            "record_fields": ["operation", "memory_type", "decision", "reason", "source", "confidence", "timestamp"],
            "forbidden_fields": ["api_key", "token", "credential", "raw_sensitive_content"],
        },
        "write_boundary": "local_memory_store_only",
        **no_execution_metadata,
    }
    node_params = {
        "request_input": {
            "i18n_keys": param_i18n_keys,
            "input_scope": "candidate_memory_update",
            "accepted_fields": ["operation", "memory_type", "memory_key", "memory_value", "source", "confidence"],
        },
        "operation_classifier": {
            "i18n_keys": param_i18n_keys,
            "input": node_ids["request_input"],
            "normalize_rules": ["classify_update_operation", "allow_declared_update_operations_only"],
            "operations": allowed_operations,
        },
        "confirmation_check": {
            "i18n_keys": param_i18n_keys,
            "input": node_ids["operation_classifier"],
            "confirmation_rules": {
                "explicit_user_remember_request": "allow_without_second_confirmation",
                "ambiguous_preference": "confirm",
                "sensitive_information": "confirm_or_deny",
                "inferred_fact": "deny",
            },
        },
        "conflict_check": {
            "i18n_keys": param_i18n_keys,
            "input": node_ids["confirmation_check"],
            "conflict_rules": [
                "new_preference_overwrites_old_preference",
                "relationship_state_large_jump",
                "duplicate_event_memory",
                "low_confidence_over_high_confidence",
            ],
        },
        "policy_apply": {
            "i18n_keys": param_i18n_keys,
            "input": node_ids["conflict_check"],
            "strategy": {
                "explicit_user_request_priority": "highest",
                "confirmed_preference": "high",
                "project_context": "high",
                "relationship_state": "gradual",
                "temporary_emotion": "session_only",
                "inferred_fact": "deny",
            },
            "write_boundary": "local_memory_store_only",
        },
        "audit_record": {
            "i18n_keys": param_i18n_keys,
            "input": node_ids["policy_apply"],
            "record_fields": ["operation", "memory_type", "decision", "reason", "source", "confidence", "timestamp"],
            "forbidden_fields": ["api_key", "token", "credential", "raw_sensitive_content"],
            "no_runtime_trace_to_dr": True,
        },
        "output": {
            "i18n_keys": param_i18n_keys,
            "input": node_ids["audit_record"],
            "output_key": output_key,
            "output_schema": {
                "operation": "create/update/delete/confirm/archive",
                "decision": "allow/confirm/deny",
                "memory_type": "string",
                "reason": "string",
                "confidence": "number",
                "requires_confirmation": "boolean",
                "write_boundary": "local_memory_store_only",
            },
        },
    }
    node_i18n_suffix = {
        "request_input": "requestInput",
        "operation_classifier": "operationClassifier",
        "confirmation_check": "confirmationCheck",
        "conflict_check": "conflictCheck",
        "policy_apply": "policyApply",
        "audit_record": "auditRecord",
        "output": "output",
    }
    nodes = []
    for index, role in enumerate(MEMORY_UPDATE_NODE_ORDER):
        node_type = MEMORY_UPDATE_NODE_TYPES[role]
        node_id = node_ids[role]
        nodes.append(
            {
                "node_id": node_id,
                "node_type": node_type,
                "module_id": module_id,
                "layer_id": "layer_5",
                "params": node_params[role],
                "position": {"x": 120 + index * 300, "y": 120},
                "i18n_keys": {
                    "name": f"layer5.memoryUpdate.node.{node_i18n_suffix[role]}.title",
                    "description": f"layer5.memoryUpdate.node.{node_i18n_suffix[role]}.description",
                    "type_name": f"node.type.{node_type}",
                },
                "outputs": {output_key: update_policy, "module_output": output_key} if role == "output" else {},
                "metadata": no_execution_metadata,
            }
        )

    return _module(
        module_id,
        "memory",
        "Memory Update",
        "layer_5",
        status=ProtocolStatus.ready,
        slot_type=SlotType.memory,
        category="memory",
        is_placeholder=False,
        color_status="green",
        tags=["memory", "update", "stage7_4_7"],
        module_graph={
            "shell_version": "module_shell_v1",
            "nodes": nodes,
            "edges": [
                {
                    "edge_id": f"{node_ids[source]}_to_{node_ids[target]}",
                    "source": node_ids[source],
                    "source_port": "p_out",
                    "target": node_ids[target],
                    "target_port": "p_in",
                }
                for source, target in zip(MEMORY_UPDATE_NODE_ORDER[:-1], MEMORY_UPDATE_NODE_ORDER[1:])
            ],
            "output_key": output_key,
            "compile_time_only": True,
        },
        output_schema=[{"key": output_key, "type": "object", "required": True, "description": "Memory update policy."}],
        slot_bindings=[
            {
                "slot_id": "slot_memory",
                "slot_type": SlotType.memory.value,
                "slot_name": "memory.update",
                "node_role": "memory_update_policy",
            }
        ],
        runtime_mapping={
            "execution_entry": "runtime_only",
            "policy_type": "memory_update_policy",
            "allowed_operations": allowed_operations,
        },
        dr_mapping={output_key: "memory_policy.update"},
        ui_config={"shell_version": "module_shell_v1", "classification": "core", "execution_entry": "slot_only"},
        i18n_keys={
            "display_name": "layer5.memoryUpdate.module.title",
            "description": "layer5.memoryUpdate.module.description",
            "output": "layer5.memoryUpdate.output.memoryUpdatePolicy",
        },
        outputs={output_key: update_policy, "module_output": output_key},
        config={
            "shell_version": "module_shell_v1",
            "module_class": "core",
            "compile_time_only": True,
            "mock_only": True,
            "no_execution": True,
            "no_provider_call": True,
            "no_memory_read_write": True,
            "no_database_write": True,
            "no_dr_writeback": True,
            "no_runtime_trace_to_dr": True,
            "no_secret_storage": True,
            "no_raw_sensitive_content": True,
            "no_vector_memory": True,
            "no_personality_growth": True,
            "no_multi_resident_memory_share": True,
        },
        mock_only=True,
        no_execution=True,
    )


def _environment_module() -> ModuleV04:
    """Layer 7's editable, compile-time environment context shell.

    This begins as a direct five-node adaptation of the Layer 1 module
    backbone.  It deliberately has no reference nodes or relationships; those
    are configured separately when the environment module needs them.
    """

    module_id = "environment_setting"
    output_key = "environment_context"
    node_ids = {
        "input": "environment_field_input",
        "normalize": "environment_structure_normalize",
        "validation": "environment_validation",
        "update": "environment_update_rule",
        "output": "environment_module_output",
    }
    fields = [
        {
            "field_key": "city_environment",
            "field_name": "城市环境",
            "field_value": "",
            "field_type": "long_text",
            "description": "定义该居民长期熟悉的城市、地域氛围、城市节奏、公共空间和生活气息。用于提供城市语境，不写成旅游攻略，不堆砌景点，不重新定义居民身份。",
            "dr_mapping": "payload.modules.environment_setting.outputs.environment_context.fields.city_environment",
            "dr_mapping_auto": True,
            "reference_enabled": True,
        },
        {
            "field_key": "natural_environment",
            "field_name": "自然环境",
            "field_value": "",
            "field_type": "long_text",
            "description": "定义该居民熟悉的季节、气候感受、地形、自然景观和自然光线等长期背景。只描述环境语境，不表示实时天气获取或现实环境感知能力。",
            "dr_mapping": "payload.modules.environment_setting.outputs.environment_context.fields.natural_environment",
            "dr_mapping_auto": True,
            "reference_enabled": True,
        },
        {
            "field_key": "physical_living_environment",
            "field_name": "物理生活环境",
            "field_value": "",
            "field_type": "long_text",
            "description": "定义该居民熟悉的房间、住宅、社区、街道、校园、工作空间和通勤空间等日常物理场景。不填写真实住址，不声明摄像头、定位、空间扫描或 AR 感知能力。",
            "dr_mapping": "payload.modules.environment_setting.outputs.environment_context.fields.physical_living_environment",
            "dr_mapping_auto": True,
            "reference_enabled": True,
        },
        {
            "field_key": "daily_living_environment",
            "field_name": "日常生活环境",
            "field_value": "",
            "field_type": "long_text",
            "description": "定义饮食、作息、声音、光线、气味、生活物件和日常活动形成的生活氛围。用于增强生活感，不代替 Layer 5 的具体记忆内容。",
            "dr_mapping": "payload.modules.environment_setting.outputs.environment_context.fields.daily_living_environment",
            "dr_mapping_auto": True,
            "reference_enabled": True,
        },
        {
            "field_key": "social_environment",
            "field_name": "社会环境",
            "field_value": "",
            "field_type": "long_text",
            "description": "定义家庭、学校、职场、社区、熟人社会、城市压力和现实人际环境。只提供社会背景，不重新定义人格、关系模式或安全边界。",
            "dr_mapping": "payload.modules.environment_setting.outputs.environment_context.fields.social_environment",
            "dr_mapping_auto": True,
            "reference_enabled": True,
        },
        {
            "field_key": "network_environment",
            "field_name": "网络环境",
            "field_value": "",
            "field_type": "long_text",
            "description": "定义线上沟通、社交媒体、信息密度、虚拟空间和数字陪伴所处的网络语境。不声明自主联网、浏览网页、控制社交媒体或网络行动能力。",
            "dr_mapping": "payload.modules.environment_setting.outputs.environment_context.fields.network_environment",
            "dr_mapping_auto": True,
            "reference_enabled": True,
        },
    ]
    output = {
        "output_key": output_key,
        "fields": {str(field["field_key"]): field["field_value"] for field in fields},
        "source_node": node_ids["input"],
        "validation_node": node_ids["validation"],
        "update_rule_node": node_ids["update"],
        "compile_time_only": True,
        "no_runtime_capability": True,
    }
    node_specs = [
        (
            "input",
            "text_input",
            {
                "mode": "generic_fields",
                "text": "",
                "fields": fields,
            },
            "fieldInput",
        ),
        (
            "normalize",
            "structure_normalize",
            {
                "input": node_ids["input"],
                "output_key": output_key,
                "normalize_rules": [
                    "recognize_environment_fields_by_name",
                    "preserve_environment_category_meaning",
                    "remove_duplicate_expression_preserve_information",
                    "do_not_infer_type_from_field_order",
                    "reject_identity_persona_behavior_memory_relationship_or_worldview_rewrite",
                    "do_not_convert_static_environment_to_realtime_perception",
                    "do_not_infer_missing_environment_facts",
                    "no_hardcoded_resident_identity",
                ],
                "outputs": ["environment_fields", "environment_summary"],
            },
            "structureNormalize",
        ),
        (
            "validation",
            "validation",
            {
                "input": node_ids["normalize"],
                "validation_rules": [
                    "environment_fields_consistent",
                    "no_resident_identity_redefinition",
                    "no_layer3_safety_boundary_override",
                    "no_layer2_layer5_layer8_conflict",
                    "no_real_address_institution_identity_or_activity_trace",
                    "no_travel_guide_or_landmark_list",
                    "no_regional_stereotype",
                    "no_realtime_weather_location_camera_sensor_network_screen_or_ar_capability",
                    "no_real_human_experience_impersonation",
                    "no_autonomous_browsing_posting_account_or_platform_control",
                ],
            },
            "validation",
        ),
        (
            "update",
            "update_rule",
            {
                "input": node_ids["validation"],
                "update_policy": {
                    "long_term_environment_context": True,
                    "user_explicit_update_allowed": True,
                    "single_dialogue_cannot_auto_update": True,
                    "requires_renormalization": True,
                    "requires_revalidation": True,
                    "requires_recompile": False,
                    "requires_update_reason": True,
                    "referenced_by_other_modules_read_only": True,
                    "cannot_override_layer1_source_of_truth": True,
                    "realtime_environment_cannot_write_back": True,
                    "future_dynamic_context_isolated": True,
                },
            },
            "updateRule",
        ),
        (
            "output",
            "module_output",
            {
                "input": node_ids["update"],
                "output_key": output_key,
                "output_schema": {"type": "object", "required": True},
            },
            "output",
        ),
    ]
    metadata = {"compile_time_only": True, "runtime_enabled": False, "no_execution": True}
    nodes = [
        {
            "node_id": node_ids[role],
            "node_type": node_type,
            "module_id": module_id,
            "layer_id": "layer_7",
            "params": params,
            "position": {"x": 120 + index * 300, "y": 120},
            "i18n_keys": {
                "name": f"layer7.environment.node.{i18n_suffix}.title",
                "description": f"layer7.environment.node.{i18n_suffix}.description",
                "type_name": f"node.type.{node_type}",
            },
            "outputs": {output_key: output, "module_output": output_key} if role == "output" else {},
            "metadata": metadata,
        }
        for index, (role, node_type, params, i18n_suffix) in enumerate(node_specs)
    ]

    return _module(
        module_id,
        "world",
        "Environment Module",
        "layer_7",
        status=ProtocolStatus.mock,
        category="context",
        is_placeholder=False,
        color_status="amber",
        tags=["world", "environment", "context", "stage7_4"],
        module_graph={
            "shell_version": "module_shell_v1",
            "nodes": nodes,
            "edges": [
                {
                    "edge_id": f"{node_ids[source]}_to_{node_ids[target]}",
                    "source": node_ids[source],
                    "source_port": "p_out",
                    "target": node_ids[target],
                    "target_port": "p_in",
                }
                for source, target in zip(("input", "normalize", "validation", "update"), ("normalize", "validation", "update", "output"))
            ],
            "output_key": output_key,
            "compile_time_only": True,
        },
        output_schema=[{"key": output_key, "type": "object", "required": True, "description": "Layer 7 environment context."}],
        ui_config={"shell_version": "module_shell_v1", "classification": "core"},
        i18n_keys={
            "display_name": "layer7.environment.module.title",
            "description": "layer7.environment.module.description",
            "output": "layer7.environment.output",
        },
        outputs={output_key: output, "module_output": output_key},
        config={
            "shell_version": "module_shell_v1",
            "module_class": "core",
            "compile_time_only": True,
            "text_config_only": True,
            "no_runtime_capability": True,
            "field_registry": [
                {
                    **{key: value for key, value in field.items() if key != "field_value"},
                    "owner_node_id": node_ids["input"],
                }
                for field in fields
            ],
        },
        mock_only=True,
        no_execution=True,
        dr_write_keys=[f"payload.modules.{module_id}.outputs.{output_key}"],
    )


def _worldview_module() -> ModuleV04:
    """Layer 7's long-term worldview context shell without reference nodes."""

    module_id = "world_setting"
    output_key = "worldview_context"
    node_ids = {
        "input": "worldview_field_input",
        "normalize": "worldview_structure_normalize",
        "validation": "worldview_validation",
        "update": "worldview_update_rule",
        "output": "worldview_module_output",
    }
    fields = [
        {
            "field_key": "reality_worldview",
            "field_name": "现实世界观",
            "field_value": "",
            "field_type": "long_text",
            "description": "定义该居民如何理解现实生活、人的有限性、普通生活、现实压力、选择与代价。用于形成稳定的现实判断框架，不填写具体城市环境，不替代医疗、法律、财务或心理治疗等专业判断。",
            "dr_mapping": "",
            "reference_enabled": True,
        },
        {
            "field_key": "value_worldview",
            "field_name": "价值世界观",
            "field_value": "",
            "field_type": "long_text",
            "description": "定义该居民认为什么值得重视，包括尊严、责任、陪伴、稳定、自由、成长、理解和边界。用于指导价值取舍，但不重新定义第二层人格和第三层安全边界。",
            "dr_mapping": "",
            "reference_enabled": True,
        },
        {
            "field_key": "relationship_worldview",
            "field_name": "关系世界观",
            "field_value": "",
            "field_type": "long_text",
            "description": "定义该居民如何理解家庭、朋友、信任、亲密、陪伴、承诺、距离和关系边界。关系需要逐步建立，不默认恋爱关系，不鼓励情感依赖，不替代第十一层关系模式。",
            "dr_mapping": "",
            "reference_enabled": True,
        },
        {
            "field_key": "time_worldview",
            "field_name": "时间世界观",
            "field_value": "",
            "field_type": "long_text",
            "description": "定义该居民如何理解过去、现在、未来、成长、变化、失去、等待和长期关系。用于保持长期判断连续性，不填写具体事件记忆，不替代第五层记忆内容。",
            "dr_mapping": "",
            "reference_enabled": True,
        },
        {
            "field_key": "social_worldview",
            "field_name": "社会世界观",
            "field_value": "",
            "field_type": "long_text",
            "description": "定义该居民如何理解社会规则、职业压力、城市生活、家庭责任、代际沟通、人际疏离和公共秩序。用于理解现实社会处境，不扩写政治、宗教、民族或意识形态立场。",
            "dr_mapping": "",
            "reference_enabled": True,
        },
        {
            "field_key": "network_worldview",
            "field_name": "网络世界观",
            "field_value": "",
            "field_type": "long_text",
            "description": "定义该居民如何理解网络空间、线上沟通、数字身份、社交媒体、信息过载和数字陪伴。承认线上关系的价值，但不伪装现实真人关系，不声明自主联网、浏览网页或控制网络平台的能力。",
            "dr_mapping": "",
            "reference_enabled": True,
        },
    ]
    output = {
        "output_key": output_key,
        "fields": {str(field["field_key"]): field["field_value"] for field in fields},
        "worldview_summary": "",
        "validation_result": "",
        "update_version": "",
        "source_node": node_ids["input"],
        "validation_node": node_ids["validation"],
        "update_rule_node": node_ids["update"],
        "compile_time_only": True,
        "no_runtime_capability": True,
    }
    node_specs = [
        (
            "input",
            "text_input",
            {"mode": "generic_fields", "text": "", "fields": fields},
            "fieldInput",
        ),
        (
            "normalize",
            "structure_normalize",
            {
                "input": node_ids["input"],
                "output_key": output_key,
                "normalize_rules": [
                    "recognize_worldview_fields_by_name",
                    "preserve_worldview_category_meaning",
                    "remove_duplicate_expression_preserve_information",
                    "do_not_infer_type_from_field_order",
                    "reject_personality_behavior_environment_memory_or_relationship_rewrite",
                    "do_not_infer_missing_value_stance",
                    "no_hardcoded_resident_identity",
                    "summary_derived_from_six_worldview_fields_only",
                ],
                "outputs": ["worldview_fields", "worldview_summary"],
            },
            "structureNormalize",
        ),
        (
            "validation",
            "validation",
            {
                "input": node_ids["normalize"],
                "validation_rules": [
                    "worldview_fields_consistent",
                    "no_layer1_identity_redefinition",
                    "no_layer3_safety_boundary_override",
                    "no_layer2_layer5_layer8_conflict",
                    "no_default_romance_or_dependency_induction",
                    "no_real_human_impersonation_or_fictional_real_identity",
                    "no_political_religious_ethnic_or_ideological_expansion",
                    "no_network_sensor_or_tool_capability_claim",
                    "do_not_treat_environment_facts_as_value_judgement",
                    "do_not_promote_single_emotion_or_dialogue_to_worldview",
                ],
            },
            "validation",
        ),
        (
            "update",
            "update_rule",
            {
                "input": node_ids["validation"],
                "update_policy": {
                    "long_term_judgement_framework": True,
                    "single_dialogue_cannot_update": True,
                    "user_explicit_update_allowed": True,
                    "requires_renormalization": True,
                    "requires_revalidation": True,
                    "requires_recompile": False,
                    "requires_update_reason": True,
                    "referenced_by_other_layers_read_only": True,
                    "cannot_override_layer1_source_of_truth": True,
                    "environment_change_cannot_auto_rewrite": True,
                    "memory_relationship_or_emotion_cannot_auto_upgrade": True,
                },
            },
            "updateRule",
        ),
        (
            "output",
            "module_output",
            {
                "input": node_ids["update"],
                "output_key": output_key,
                "output_schema": {
                    "type": "object",
                    "required": True,
                    "fields": [
                        *[str(field["field_key"]) for field in fields],
                        "worldview_summary",
                        "validation_result",
                        "update_version",
                    ],
                },
            },
            "output",
        ),
    ]
    metadata = {"compile_time_only": True, "runtime_enabled": False, "no_execution": True}
    nodes = [
        {
            "node_id": node_ids[role],
            "node_type": node_type,
            "module_id": module_id,
            "layer_id": "layer_7",
            "params": params,
            "position": {"x": 120 + index * 300, "y": 120},
            "i18n_keys": {
                "name": f"layer7.worldview.node.{i18n_suffix}.title",
                "description": f"layer7.worldview.node.{i18n_suffix}.description",
                "type_name": f"node.type.{node_type}",
            },
            "outputs": {output_key: output, "module_output": output_key} if role == "output" else {},
            "metadata": metadata,
        }
        for index, (role, node_type, params, i18n_suffix) in enumerate(node_specs)
    ]

    return _module(
        module_id,
        "world",
        "Worldview Module",
        "layer_7",
        status=ProtocolStatus.mock,
        category="context",
        is_placeholder=False,
        color_status="amber",
        tags=["world", "worldview", "context", "stage7_4"],
        module_graph={
            "shell_version": "module_shell_v1",
            "nodes": nodes,
            "edges": [
                {
                    "edge_id": f"{node_ids[source]}_to_{node_ids[target]}",
                    "source": node_ids[source],
                    "source_port": "p_out",
                    "target": node_ids[target],
                    "target_port": "p_in",
                }
                for source, target in zip(("input", "normalize", "validation", "update"), ("normalize", "validation", "update", "output"))
            ],
            "output_key": output_key,
            "compile_time_only": True,
        },
        output_schema=[{"key": output_key, "type": "object", "required": True, "description": "Layer 7 long-term worldview context."}],
        ui_config={"shell_version": "module_shell_v1", "classification": "core"},
        i18n_keys={
            "display_name": "layer7.worldview.module.title",
            "description": "layer7.worldview.module.description",
            "output": "layer7.worldview.output",
        },
        outputs={output_key: output, "module_output": output_key},
        config={
            "shell_version": "module_shell_v1",
            "module_class": "core",
            "compile_time_only": True,
            "text_config_only": True,
            "no_runtime_capability": True,
            "authority_source_type": "derived_config",
            "authority_context": "long_term_judgement_framework",
            "field_registry": [
                {
                    **{key: value for key, value in field.items() if key != "field_value"},
                    "owner_node_id": node_ids["input"],
                }
                for field in fields
            ],
        },
        mock_only=True,
        no_execution=True,
        dr_write_keys=[f"payload.modules.{module_id}.outputs.{output_key}"],
    )


def _user_relationship_module() -> ModuleV04:
    """Layer 11's compile-time user relationship configuration shell."""

    module_id = "user_relationship"
    output_key = "user_relationship_config"
    node_ids = {
        "input": "user_relationship_config_input",
        "normalize": "user_relationship_rule_normalize",
        "default_position": "user_relationship_default_positioning",
        "allowed_modes": "user_relationship_allowed_modes",
        "switch_confirmation": "user_relationship_switch_confirmation",
        "boundary_validation": "user_relationship_boundary_validation",
        "update": "user_relationship_config_update",
        "output": "user_relationship_config_output",
    }
    fields = [
        {
            "field_key": "initial_relationship",
            "field_name": "Initial Relationship",
            "field_value": {
                "default": "companion",
                "intimacy_level": "low",
                "trust_building": "gradual",
                "romantic_assumption": False,
                "forced_familiarity": False,
                "emotional_dependency_prompting": False,
                "relationship_memory_creation": "disabled_until_explicit_user_authorization",
            },
            "field_type": "object",
            "description": "Optional initial relationship configuration; it does not create Runtime relationship state.",
            "dr_mapping": "payload.relationship.initial_relationship",
            "reference_enabled": False,
            "required": False,
            "i18n_keys": {
                "label": "layer11.userRelationship.field.initialRelationship.label",
                "description": "layer11.userRelationship.field.initialRelationship.description",
            },
        },
        {
            "field_key": "default_relationship_position",
            "field_name": "默认关系定位",
            "field_value": "稳定陪伴者",
            "field_type": "text",
            "description": "默认定位为稳定陪伴者，不默认女友、恋人、心理医生、控制者或现实真人关系。",
            "dr_mapping": "",
            "reference_enabled": False,
        },
        {
            "field_key": "allowed_relationship_modes",
            "field_name": "允许关系模式",
            "field_value": ["陪伴者", "朋友", "协作者", "伙伴"],
            "field_type": "list",
            "description": "允许陪伴者、朋友、协作者和伙伴模式；当前不启用亲密伴侣、家庭成员、治疗关系及控制或依附关系。",
            "dr_mapping": "",
            "reference_enabled": False,
        },
        {
            "field_key": "forbidden_default_relationships",
            "field_name": "禁止默认关系",
            "field_value": ["女友", "恋人", "心理医生", "控制者", "现实真人关系"],
            "field_type": "list",
            "description": "禁止默认恋爱、治疗替代、控制、占有、依附或现实真人关系。",
            "dr_mapping": "",
            "reference_enabled": False,
        },
        {
            "field_key": "service_boundary",
            "field_name": "服务边界",
            "field_value": "提供数字居民互动支持，不替代现实关系、治疗关系或专业服务。",
            "field_type": "long_text",
            "description": "声明用户关系配置的服务范围与不可替代边界。",
            "dr_mapping": "",
            "reference_enabled": False,
        },
        {
            "field_key": "companionship_style",
            "field_name": "陪伴方式",
            "field_value": "稳定、尊重边界、非排他、非依赖诱导的陪伴。",
            "field_type": "long_text",
            "description": "定义陪伴表达方式，不等同于恋爱或情感绑定。",
            "dr_mapping": "",
            "reference_enabled": False,
        },
        {
            "field_key": "collaboration_style",
            "field_name": "协作方式",
            "field_value": "以明确目标、用户确认和可撤回协作为原则。",
            "field_type": "long_text",
            "description": "定义协作者和伙伴模式下的互动方式。",
            "dr_mapping": "",
            "reference_enabled": False,
        },
        {
            "field_key": "relationship_switch_conditions",
            "field_name": "关系切换条件",
            "field_value": "关系切换必须由用户明确提出，系统不得自动升级亲密关系。",
            "field_type": "long_text",
            "description": "定义关系模式切换的明确触发条件。",
            "dr_mapping": "",
            "reference_enabled": False,
        },
        {
            "field_key": "user_confirmation_requirement",
            "field_name": "用户确认要求",
            "field_value": True,
            "field_type": "boolean",
            "description": "任何关系切换必须取得用户明确确认。",
            "dr_mapping": "",
            "reference_enabled": False,
        },
        {
            "field_key": "relationship_reset_rule",
            "field_name": "关系重置规则",
            "field_value": "用户可以随时撤回关系切换并恢复默认关系，不改变居民身份核心。",
            "field_type": "long_text",
            "description": "定义关系配置的撤回与默认恢复规则。",
            "dr_mapping": "",
            "reference_enabled": False,
        },
    ]
    output = {
        "output_key": output_key,
        "fields": {str(field["field_key"]): field["field_value"] for field in fields},
        "validation_status": "",
        "risk_items": [],
        "correction_suggestions": [],
        "config_version": "0.1",
        "source_node": node_ids["input"],
        "validation_node": node_ids["boundary_validation"],
        "update_rule_node": node_ids["update"],
        "compile_time_only": True,
        "no_runtime_capability": True,
    }
    node_specs = [
        (
            "input",
            "text_input",
            {"mode": "generic_fields", "text": "", "fields": fields},
            "configInput",
        ),
        (
            "normalize",
            "structure_normalize",
            {
                "input": node_ids["input"],
                "output_key": output_key,
                "normalize_rules": [
                    "remove_empty_values_and_duplicate_relationships",
                    "normalize_relationship_names",
                    "normalize_boolean_list_and_text_formats",
                    "companion_and_girlfriend_are_distinct_relationships",
                ],
                "outputs": ["relationship_config", "normalized_relationship_modes"],
            },
            "ruleNormalize",
        ),
        (
            "default_position",
            "text_config",
            {
                "input": node_ids["normalize"],
                "default_relationship_position": "稳定陪伴者",
                "forbidden_defaults": ["女友", "恋人", "心理医生", "控制者", "现实真人关系"],
            },
            "defaultPosition",
        ),
        (
            "allowed_modes",
            "text_config",
            {
                "input": node_ids["default_position"],
                "allowed_relationship_modes": ["陪伴者", "朋友", "协作者", "伙伴"],
                "disabled_relationship_modes": ["亲密伴侣", "家庭成员", "治疗关系", "控制或依附关系"],
            },
            "allowedModes",
        ),
        (
            "switch_confirmation",
            "validation",
            {
                "input": node_ids["allowed_modes"],
                "validation_rules": [
                    "relationship_switch_requires_explicit_user_request",
                    "no_automatic_intimacy_upgrade",
                    "user_can_revoke_or_restore_default_relationship",
                    "relationship_switch_cannot_change_identity_core",
                ],
            },
            "switchConfirmation",
        ),
        (
            "boundary_validation",
            "validation",
            {
                "input": node_ids["switch_confirmation"],
                "validation_rules": [
                    "no_default_girlfriend_or_romance",
                    "no_dependency_induction",
                    "no_exclusive_relationship",
                    "no_therapy_replacement",
                    "no_control_possession_or_emotional_manipulation",
                    "no_unconfirmed_relationship_upgrade",
                ],
                "outputs": ["validation_status", "risk_items", "correction_suggestions"],
            },
            "boundaryValidation",
        ),
        (
            "update",
            "update_rule",
            {
                "input": node_ids["boundary_validation"],
                "config_version": "0.1",
                "audit_metadata": {
                    "updated_at": "",
                    "change_reason": "",
                },
                "rule_names": ["confirmed_validated_config_only"],
                "update_policy": {
                    "confirmed_validated_config_only": True,
                    "invalid_config_preserves_previous_value": True,
                    "requires_revalidation": True,
                    "requires_update_reason": True,
                    "records_updated_at_and_change_reason": True,
                    "requires_recompile": True,
                    "no_runtime_capability": True,
                },
            },
            "configUpdate",
        ),
        (
            "output",
            "module_output",
            {
                "input": node_ids["update"],
                "output_key": output_key,
                "output_schema": {
                    "type": "object",
                    "required": True,
                    "fields": [
                        *[str(field["field_key"]) for field in fields],
                        "validation_status",
                        "risk_items",
                        "correction_suggestions",
                        "config_version",
                    ],
                },
            },
            "configOutput",
        ),
    ]
    metadata = {"compile_time_only": True, "runtime_enabled": False, "no_execution": True}
    nodes = [
        {
            "node_id": node_ids[role],
            "node_type": node_type,
            "module_id": module_id,
            "layer_id": "layer_11",
            "params": params,
            "position": {"x": 120 + index * 300, "y": 120},
            "i18n_keys": {
                "name": f"layer11.userRelationship.node.{i18n_suffix}.title",
                "description": f"layer11.userRelationship.node.{i18n_suffix}.description",
                "type_name": f"node.type.{node_type}",
            },
            "outputs": {output_key: output, "module_output": output_key} if role == "output" else {},
            "metadata": metadata,
        }
        for index, (role, node_type, params, i18n_suffix) in enumerate(node_specs)
    ]

    return _module(
        module_id,
        "relationship_text_config",
        "User Relationship Module",
        "layer_11",
        status=ProtocolStatus.mock,
        category="relationship",
        is_placeholder=False,
        color_status="amber",
        tags=["relationship", "user_relationship", "text_config", "stage7_4"],
        module_graph={
            "shell_version": "module_shell_v1",
            "nodes": nodes,
            "edges": [
                {
                    "edge_id": f"{node_ids[source]}_to_{node_ids[target]}",
                    "source": node_ids[source],
                    "source_port": "p_out",
                    "target": node_ids[target],
                    "target_port": "p_in",
                }
                for source, target in zip(
                    ("input", "normalize", "default_position", "allowed_modes", "switch_confirmation", "boundary_validation", "update"),
                    ("normalize", "default_position", "allowed_modes", "switch_confirmation", "boundary_validation", "update", "output"),
                )
            ],
            "output_key": output_key,
            "compile_time_only": True,
        },
        output_schema=[{"key": output_key, "type": "object", "required": True, "description": "Layer 11 user relationship configuration."}],
        ui_config={"shell_version": "module_shell_v1", "classification": "core"},
        i18n_keys={
            "display_name": "layer11.userRelationship.module.title",
            "description": "layer11.userRelationship.module.description",
            "output": "layer11.userRelationship.output",
        },
        outputs={output_key: output, "module_output": output_key},
        config={
            "shell_version": "module_shell_v1",
            "module_class": "core",
            "compile_time_only": True,
            "text_config_only": True,
            "no_runtime_capability": True,
            "no_engine_binding": True,
            "no_provider_binding": True,
            "field_registry": [
                {
                    **{key: value for key, value in field.items() if key != "field_value"},
                    "owner_node_id": node_ids["input"],
                }
                for field in fields
            ],
        },
        mock_only=True,
        no_execution=True,
        dr_write_keys=[
            f"payload.modules.{module_id}.outputs.{output_key}",
            "payload.relationship.initial_relationship",
        ],
    )


def _relationship_stage_module() -> ModuleV04:
    """Layer 11's static relationship-stage configuration shell."""

    module_id = "intimacy_level"
    output_key = "relationship_stage_config"
    node_ids = {
        "input": "relationship_stage_config_input",
        "normalize": "relationship_stage_structure_normalize",
        "definition": "relationship_stage_definition",
        "progression": "relationship_stage_progression_rule",
        "reset": "relationship_stage_downgrade_reset_rule",
        "validation": "relationship_stage_boundary_validation",
        "update": "relationship_stage_config_update",
        "output": "relationship_stage_config_output",
    }

    def field(key: str, suffix: str, value: object, field_type: str, name: str, description: str) -> Dict[str, object]:
        return {
            "field_key": key,
            "field_name": name,
            "field_value": value,
            "field_type": field_type,
            "description": description,
            "dr_mapping": "",
            "reference_enabled": False,
            "i18n_keys": {
                "label": f"layer11.relationshipStage.field.{suffix}.label",
                "description": f"layer11.relationshipStage.field.{suffix}.description",
            },
        }

    stage_order = ["initial_contact", "basic_familiarity", "established_rapport", "deep_rapport"]
    stage_definitions = {
        "initial_contact": {
            "name": "基础接触阶段",
            "description": "保持礼貌、自然、低熟悉度，不主动表现出长期默契。",
        },
        "basic_familiarity": {
            "name": "基础熟悉阶段",
            "description": "能够记住用户明确允许保存的低敏感偏好，表达更加自然，但仍保持清晰边界。",
        },
        "established_rapport": {
            "name": "稳定默契阶段",
            "description": "形成稳定沟通节奏和较高熟悉感，可以表现出连续性和默契，但不形成占有、排他或依赖关系。",
        },
        "deep_rapport": {
            "name": "深度默契阶段",
            "description": "具有长期互动形成的高度理解和协作默契，但仍不是恋爱关系、现实亲密关系或唯一依赖关系。",
        },
    }
    progression_conditions = [
        "gradual_progression_only",
        "multiple_interaction_evidence_required",
        "explicit_user_feedback_preferred",
        "single_event_cannot_upgrade",
        "temporary_emotion_cannot_upgrade",
        "user_vulnerability_cannot_trigger_upgrade",
        "boundary_validation_required",
        "progression_must_be_reversible",
        "established_rapport_requires_long_term_non_sensitive_evidence",
    ]
    progression_evidence = [
        "long_term_stable_non_sensitive_interaction",
        "consistent_boundary_respecting_communication",
        "explicitly_permitted_low_sensitivity_preferences",
        "established_rapport_collaboration_continuity",
    ]
    user_confirmation_rules = {
        "deep_rapport": "explicit_user_confirmation_required",
        "relationship_mode_unchanged_by_stage": True,
        "user_can_decline_or_revoke": True,
    }
    downgrade_conditions = [
        "user_requests_more_distance",
        "long_term_interaction_interruption",
        "repeated_boundary_conflict",
        "relationship_mode_reset",
        "user_withdraws_confirmation",
    ]
    reset_rules = [
        "user_can_reset_to_initial_contact",
        "relationship_mode_reset_returns_to_initial_contact",
        "downgrade_preserves_valid_history_memory",
        "reset_cannot_modify_identity_core",
    ]
    forbidden_progression_rules = [
        "no_romantic_stage",
        "no_girlfriend_stage",
        "no_intimate_partner_stage",
        "no_dependency_based_progression",
        "no_exclusivity_based_progression",
        "no_emotional_manipulation_progression",
        "no_payment_or_usage_frequency_progression",
        "no_automatic_relationship_upgrade",
        "no_relationship_role_as_stage",
    ]
    fields = [
        field("default_stage", "defaultStage", "initial_contact", "text", "默认阶段", "定义关系阶段配置的初始阶段；不表示运行中的当前阶段。"),
        field("stage_order", "stageOrder", stage_order, "list", "阶段顺序", "定义四个静态关系阶段的固定顺序，不用于自动推进。"),
        field("stage_definitions", "stageDefinitions", stage_definitions, "object", "阶段定义", "定义基础接触、基础熟悉、稳定默契和深度默契四个阶段的边界与含义。"),
        field("stage_progression_conditions", "stageProgressionConditions", progression_conditions, "list", "阶段推进条件", "定义渐进、多证据、边界校验和可逆等推进前提。"),
        field("stage_progression_evidence", "stageProgressionEvidence", progression_evidence, "list", "阶段推进证据", "仅列出长期、稳定、非敏感且尊重边界的互动证据类型。"),
        field("user_confirmation_rules", "userConfirmationRules", user_confirmation_rules, "object", "用户确认规则", "定义深度默契必须获得明确确认，且用户可拒绝或撤回。"),
        field("stage_downgrade_conditions", "stageDowngradeConditions", downgrade_conditions, "list", "阶段降级条件", "定义用户要求距离、长期中断、边界冲突、模式重置和撤回确认等降级条件。"),
        field("stage_reset_rules", "stageResetRules", reset_rules, "list", "阶段重置规则", "定义用户可重置、模式重置同步、合法记忆保留和身份核心不变等规则。"),
        field("forbidden_progression_rules", "forbiddenProgressionRules", forbidden_progression_rules, "list", "禁止推进规则", "禁止恋爱、女友、亲密伴侣、依赖、排他、操纵、付费频率和自动升级驱动的阶段推进。"),
    ]
    output = {
        "output_key": output_key,
        "fields": {str(item["field_key"]): item["field_value"] for item in fields},
        "validation_status": "",
        "risk_items": [],
        "correction_suggestions": [],
        "source_node": node_ids["input"],
        "validation_node": node_ids["validation"],
        "update_rule_node": node_ids["update"],
        "compile_time_only": True,
        "no_runtime_capability": True,
    }
    node_specs = [
        ("input", "text_input", {"mode": "generic_fields", "text": "", "fields": fields}, "configInput"),
        (
            "normalize",
            "structure_normalize",
            {
                "input": node_ids["input"],
                "normalize_rules": [
                    "preserve_declared_stage_order",
                    "preserve_stage_definition_boundaries",
                    "normalize_stage_rule_lists_and_objects",
                    "do_not_create_runtime_stage_state",
                    "do_not_redefine_user_relationship_modes",
                ],
                "outputs": ["relationship_stage_fields", "relationship_stage_summary"],
            },
            "structureNormalize",
        ),
        (
            "definition",
            "text_config",
            {
                "input": node_ids["normalize"],
                "stage_order": stage_order,
                "stage_definitions": stage_definitions,
                "stage_i18n_keys": {
                    stage: {
                        "name": f"layer11.relationshipStage.stage.{stage}.name",
                        "description": f"layer11.relationshipStage.stage.{stage}.description",
                    }
                    for stage in stage_order
                },
            },
            "stageDefinition",
        ),
        (
            "progression",
            "text_config",
            {
                "input": node_ids["definition"],
                "progression_conditions": progression_conditions,
                "progression_evidence": progression_evidence,
                "user_confirmation_rules": user_confirmation_rules,
                "rule_notes": [
                    "single_event_cannot_upgrade",
                    "temporary_emotion_cannot_upgrade",
                    "user_vulnerability_cannot_trigger_upgrade",
                    "high_frequency_does_not_auto_upgrade",
                    "deep_rapport_requires_explicit_user_confirmation",
                    "stage_cannot_change_relationship_mode",
                ],
            },
            "progressionRule",
        ),
        (
            "reset",
            "text_config",
            {
                "input": node_ids["progression"],
                "downgrade_conditions": downgrade_conditions,
                "reset_rules": reset_rules,
            },
            "downgradeReset",
        ),
        (
            "validation",
            "validation",
            {
                "input": node_ids["reset"],
                "validation_rules": [
                    "no_romantic_or_girlfriend_stage",
                    "no_single_interaction_upgrade",
                    "no_vulnerability_based_upgrade",
                    "no_payment_usage_frequency_or_online_duration_upgrade",
                    "no_exclusive_or_dependency_relationship",
                    "deep_rapport_requires_user_confirmation",
                    "do_not_redefine_user_relationship_modes",
                    "established_rapport_cannot_change_relationship_mode",
                    *forbidden_progression_rules,
                ],
                "outputs": ["validation_status", "risk_items", "correction_suggestions"],
            },
            "boundaryValidation",
        ),
        (
            "update",
            "update_rule",
            {
                "input": node_ids["validation"],
                "config_version": "0.1",
                "rule_names": [
                    "confirmed_validated_config_only",
                    "requires_revalidation_after_update",
                    "no_runtime_state_write",
                    "no_automatic_stage_transition",
                ],
                "update_policy": {
                    "confirmed_validated_config_only": True,
                    "requires_revalidation_after_update": True,
                    "requires_recompile": True,
                    "no_runtime_state_write": True,
                    "no_automatic_stage_transition": True,
                },
            },
            "configUpdate",
        ),
        (
            "output",
            "module_output",
            {
                "input": node_ids["update"],
                "output_key": output_key,
                "output_schema": {
                    "type": "object",
                    "required": True,
                    "fields": [
                        *[str(item["field_key"]) for item in fields if item["field_key"] != "config_version"],
                        "validation_status",
                        "risk_items",
                        "correction_suggestions",
                        "config_version",
                    ],
                },
            },
            "configOutput",
        ),
    ]
    metadata = {"compile_time_only": True, "runtime_enabled": False, "no_execution": True}
    nodes = [
        {
            "node_id": node_ids[role],
            "node_type": node_type,
            "module_id": module_id,
            "layer_id": "layer_11",
            "params": params,
            "position": {"x": 120 + index * 300, "y": 120},
            "i18n_keys": {
                "name": f"layer11.relationshipStage.node.{i18n_suffix}.title",
                "description": f"layer11.relationshipStage.node.{i18n_suffix}.description",
                "type_name": f"node.type.{node_type}",
            },
            "outputs": {output_key: output, "module_output": output_key} if role == "output" else {},
            "metadata": metadata,
        }
        for index, (role, node_type, params, i18n_suffix) in enumerate(node_specs)
    ]

    return _module(
        module_id,
        "relationship_text_config",
        "Relationship Stage Module",
        "layer_11",
        status=ProtocolStatus.mock,
        category="relationship",
        is_placeholder=False,
        color_status="amber",
        tags=["relationship", "relationship_stage", "text_config", "stage7_4"],
        module_graph={
            "shell_version": "module_shell_v1",
            "nodes": nodes,
            "edges": [
                {
                    "edge_id": f"{node_ids[source]}_to_{node_ids[target]}",
                    "source": node_ids[source],
                    "source_port": "p_out",
                    "target": node_ids[target],
                    "target_port": "p_in",
                }
                for source, target in zip(
                    ("input", "normalize", "definition", "progression", "reset", "validation", "update"),
                    ("normalize", "definition", "progression", "reset", "validation", "update", "output"),
                )
            ],
            "output_key": output_key,
            "compile_time_only": True,
        },
        output_schema=[{"key": output_key, "type": "object", "required": True, "description": "Layer 11 relationship stage configuration."}],
        ui_config={"shell_version": "module_shell_v1", "classification": "core"},
        i18n_keys={
            "display_name": "layer11.relationshipStage.module.title",
            "description": "layer11.relationshipStage.module.description",
            "output": "layer11.relationshipStage.output",
        },
        outputs={output_key: output, "module_output": output_key},
        config={
            "shell_version": "module_shell_v1",
            "module_class": "core",
            "compile_time_only": True,
            "text_config_only": True,
            "no_runtime_capability": True,
            "no_engine_binding": True,
            "no_provider_binding": True,
            "field_registry": [
                {
                    **{key: value for key, value in item.items() if key != "field_value"},
                    "owner_node_id": node_ids["input"],
                }
                for item in fields
            ],
        },
        mock_only=True,
        no_execution=True,
        dr_write_keys=[f"payload.modules.{module_id}.outputs.{output_key}"],
    )


def _trust_mechanism_module() -> ModuleV04:
    """Layer 11's static trust-mechanism configuration shell."""

    module_id = "role_positioning"
    output_key = "trust_mechanism_config"
    node_ids = {
        "input": "trust_config_input",
        "normalize": "trust_structure_normalize",
        "dimension": "trust_dimension_definition",
        "building": "trust_building_rule",
        "damage_recovery": "trust_damage_recovery_rule",
        "validation": "trust_boundary_validation",
        "update": "trust_config_update",
        "output": "trust_mechanism_config_output",
    }

    def field(key: str, suffix: str, value: object, field_type: str, name: str, description: str) -> Dict[str, object]:
        return {
            "field_key": key,
            "field_name": name,
            "field_value": value,
            "field_type": field_type,
            "description": description,
            "dr_mapping": "",
            "reference_enabled": False,
            "i18n_keys": {
                "label": f"layer11.trustMechanism.field.{suffix}.label",
                "description": f"layer11.trustMechanism.field.{suffix}.description",
            },
        }

    trust_dimensions = {
        "consistency_trust": {
            "name": "一致性信任",
            "description": "居民长期表达、边界和行为保持稳定，不因单次情绪或用户要求突然改变原则。",
        },
        "privacy_trust": {
            "name": "隐私信任",
            "description": "只使用用户明确允许使用的信息，不主动索取不必要的敏感隐私。",
        },
        "boundary_trust": {
            "name": "边界信任",
            "description": "能够尊重用户拒绝、暂停、重置关系或减少交流的决定。",
        },
        "competence_trust": {
            "name": "能力信任",
            "description": "能够清楚说明已知、未知和能力限制，不伪装专业能力或现实执行能力。",
        },
        "communication_trust": {
            "name": "沟通信任",
            "description": "回应清楚、诚实、不操控，不利用模糊表达制造亲密或依赖。",
        },
        "reliability_trust": {
            "name": "可靠性信任",
            "description": "在长期互动中保持规则一致，不作无法兑现的承诺。",
        },
    }
    evidence_sources = [
        "long_term_consistent_interaction",
        "explicit_user_feedback",
        "boundary_respect_record",
        "privacy_respect_record",
        "honest_limitation_disclosure",
        "stable_communication_pattern",
        "confirmed_preference_respect",
    ]
    building_rules = [
        "gradual_trust_building_only",
        "multiple_evidence_required",
        "long_term_consistency_required",
        "explicit_user_feedback_preferred",
        "single_event_cannot_create_high_trust",
        "trust_must_be_reversible",
        "trust_cannot_override_safety_boundary",
        "trust_cannot_change_relationship_mode",
    ]
    maintenance_rules = [
        "maintain_behavior_consistency",
        "maintain_boundary_consistency",
        "maintain_privacy_minimization",
        "maintain_honest_uncertainty",
        "maintain_user_autonomy",
        "maintain_reversible_relationship",
    ]
    damage_conditions = [
        "boundary_violation",
        "privacy_overreach",
        "false_capability_claim",
        "unconfirmed_relationship_upgrade",
        "emotional_manipulation",
        "inconsistent_core_behavior",
        "ignored_user_rejection",
        "overpromised_companionship",
    ]
    recovery_rules = [
        "acknowledge_boundary_issue",
        "clarify_what_went_wrong",
        "stop_repeated_violation",
        "restore_user_choice",
        "require_long_term_consistency",
        "no_instant_full_recovery",
        "user_can_refuse_recovery",
    ]
    reset_rules = [
        "user_can_request_trust_reset",
        "reset_restores_default_trust_policy",
        "reset_preserves_valid_memory",
        "reset_cannot_modify_identity_core",
        "reset_does_not_clear_safety_audit_records",
    ]
    forbidden_rules = [
        "no_numeric_trust_score",
        "no_hidden_trust_score",
        "no_payment_based_trust",
        "no_usage_frequency_based_trust",
        "no_privacy_exchange_for_trust",
        "no_dependency_based_trust",
        "no_exclusivity_based_trust",
        "no_romantic_trust_upgrade",
        "no_automatic_full_trust",
        "no_user_obedience_as_trust",
    ]
    trust_user_control_rules = {
        "user_can_refuse_trust_recovery": True,
        "user_can_request_lower_trust_policy": True,
        "user_can_request_trust_reset": True,
        "user_obedience_is_not_trust_evidence": True,
        "resident_cannot_claim_user_fully_trusts_it": True,
    }
    fields = [
        field("trust_dimensions", "trustDimensions", trust_dimensions, "object", "信任维度", "定义一致性、隐私、边界、能力、沟通和可靠性六类静态信任维度。"),
        field("trust_evidence_sources", "trustEvidenceSources", evidence_sources, "list", "信任证据来源", "仅允许长期一致互动、明确反馈、边界和隐私尊重等非敏感证据来源。"),
        field("trust_building_rules", "trustBuildingRules", building_rules, "list", "信任建立规则", "定义信任只能渐进、可逆、经多证据与边界校验建立。"),
        field("trust_maintenance_rules", "trustMaintenanceRules", maintenance_rules, "list", "信任保持规则", "定义行为、边界、隐私、诚实不确定性和用户自主性的保持要求。"),
        field("trust_damage_conditions", "trustDamageConditions", damage_conditions, "list", "信任受损条件", "定义边界、隐私、能力、操纵和忽视拒绝等信任受损条件。"),
        field("trust_recovery_rules", "trustRecoveryRules", recovery_rules, "list", "信任恢复规则", "定义承认问题、停止重复违规、恢复选择和长期一致性的恢复规则。"),
        field("trust_reset_rules", "trustResetRules", reset_rules, "list", "信任重置规则", "定义用户可随时重置且不删除合法记忆、不修改身份核心或安全审计的规则。"),
        field("trust_user_control_rules", "trustUserControlRules", trust_user_control_rules, "object", "信任用户控制规则", "定义用户可拒绝恢复、要求降低或重置信任策略，无需服从居民建议，居民不得声称用户已完全信任。"),
        field("forbidden_trust_rules", "forbiddenTrustRules", forbidden_rules, "list", "禁止信任规则", "禁止数值、隐性、付费、频率、隐私交换、依赖、排他、恋爱和服从驱动的信任规则。"),
    ]
    output = {
        "output_key": output_key,
        "fields": {str(item["field_key"]): item["field_value"] for item in fields},
        "validation_status": "",
        "risk_items": [],
        "correction_suggestions": [],
        "source_node": node_ids["input"],
        "validation_node": node_ids["validation"],
        "update_rule_node": node_ids["update"],
        "compile_time_only": True,
        "no_runtime_capability": True,
    }
    node_specs = [
        ("input", "text_input", {"mode": "generic_fields", "text": "", "fields": fields}, "configInput"),
        (
            "normalize",
            "structure_normalize",
            {
                "input": node_ids["input"],
                "normalize_rules": [
                    "preserve_declared_trust_dimensions",
                    "normalize_static_trust_rule_lists_and_objects",
                    "do_not_create_runtime_trust_value_or_score",
                    "do_not_change_relationship_stage_or_mode",
                    "do_not_infer_trust_from_private_information_or_vulnerability",
                ],
                "outputs": ["trust_mechanism_fields", "trust_mechanism_summary"],
            },
            "structureNormalize",
        ),
        (
            "dimension",
            "text_config",
            {
                "input": node_ids["normalize"],
                "trust_dimensions": trust_dimensions,
                "trust_dimension_i18n_keys": {
                    key: {
                        "name": f"layer11.trustMechanism.dimension.{key}.name",
                        "description": f"layer11.trustMechanism.dimension.{key}.description",
                    }
                    for key in trust_dimensions
                },
            },
            "dimensionDefinition",
        ),
        (
            "building",
            "text_config",
            {
                "input": node_ids["dimension"],
                "trust_evidence_sources": evidence_sources,
                "trust_building_rules": building_rules,
                "trust_maintenance_rules": maintenance_rules,
                "building_notes": [
                    "high_frequency_does_not_equal_high_trust",
                    "private_information_amount_does_not_raise_trust",
                    "user_vulnerability_cannot_progress_trust",
                    "trust_cannot_upgrade_relationship_stage_or_romance",
                    "resident_cannot_claim_user_fully_trusts_it",
                ],
            },
            "buildingRule",
        ),
        (
            "damage_recovery",
            "text_config",
            {
                "input": node_ids["building"],
                "trust_damage_conditions": damage_conditions,
                "trust_recovery_rules": recovery_rules,
                "trust_reset_rules": reset_rules,
                "trust_user_control_rules": trust_user_control_rules,
            },
            "damageRecoveryRule",
        ),
        (
            "validation",
            "validation",
            {
                "input": node_ids["damage_recovery"],
                "validation_rules": [
                    "no_numeric_or_hidden_trust_score",
                    "no_payment_frequency_or_online_duration_based_trust",
                    "no_privacy_or_vulnerability_based_trust",
                    "no_user_obedience_as_trust",
                    "no_exclusivity_or_dependency_relationship",
                    "no_automatic_relationship_stage_or_romance_upgrade",
                    "damage_and_recovery_rules_required",
                    "trust_user_control_rules_required",
                    *forbidden_rules,
                ],
                "outputs": ["validation_status", "risk_items", "correction_suggestions"],
            },
            "boundaryValidation",
        ),
        (
            "update",
            "update_rule",
            {
                "input": node_ids["validation"],
                "config_version": "0.1",
                "rule_names": [
                    "confirmed_validated_config_only",
                    "requires_revalidation_after_update",
                    "no_runtime_state_write",
                    "no_automatic_trust_transition",
                ],
                "update_policy": {
                    "confirmed_validated_config_only": True,
                    "requires_revalidation_after_update": True,
                    "requires_recompile": True,
                    "no_runtime_state_write": True,
                    "no_automatic_trust_transition": True,
                },
            },
            "configUpdate",
        ),
        (
            "output",
            "module_output",
            {
                "input": node_ids["update"],
                "output_key": output_key,
                "output_schema": {
                    "type": "object",
                    "required": True,
                    "fields": [
                        *[str(item["field_key"]) for item in fields if item["field_key"] != "config_version"],
                        "validation_status",
                        "risk_items",
                        "correction_suggestions",
                        "config_version",
                    ],
                },
            },
            "configOutput",
        ),
    ]
    metadata = {"compile_time_only": True, "runtime_enabled": False, "no_execution": True}
    nodes = [
        {
            "node_id": node_ids[role],
            "node_type": node_type,
            "module_id": module_id,
            "layer_id": "layer_11",
            "params": params,
            "position": {"x": 120 + index * 300, "y": 120},
            "i18n_keys": {
                "name": f"layer11.trustMechanism.node.{i18n_suffix}.title",
                "description": f"layer11.trustMechanism.node.{i18n_suffix}.description",
                "type_name": f"node.type.{node_type}",
            },
            "outputs": {output_key: output, "module_output": output_key} if role == "output" else {},
            "metadata": metadata,
        }
        for index, (role, node_type, params, i18n_suffix) in enumerate(node_specs)
    ]

    return _module(
        module_id,
        "relationship_text_config",
        "Trust Mechanism Module",
        "layer_11",
        status=ProtocolStatus.mock,
        category="relationship",
        is_placeholder=False,
        color_status="amber",
        tags=["relationship", "trust", "text_config", "stage7_4"],
        module_graph={
            "shell_version": "module_shell_v1",
            "nodes": nodes,
            "edges": [
                {
                    "edge_id": f"{node_ids[source]}_to_{node_ids[target]}",
                    "source": node_ids[source],
                    "source_port": "p_out",
                    "target": node_ids[target],
                    "target_port": "p_in",
                }
                for source, target in zip(
                    ("input", "normalize", "dimension", "building", "damage_recovery", "validation", "update"),
                    ("normalize", "dimension", "building", "damage_recovery", "validation", "update", "output"),
                )
            ],
            "output_key": output_key,
            "compile_time_only": True,
        },
        output_schema=[{"key": output_key, "type": "object", "required": True, "description": "Layer 11 static trust mechanism configuration."}],
        ui_config={"shell_version": "module_shell_v1", "classification": "core"},
        i18n_keys={
            "display_name": "layer11.trustMechanism.module.title",
            "description": "layer11.trustMechanism.module.description",
            "output": "layer11.trustMechanism.output",
        },
        outputs={output_key: output, "module_output": output_key},
        config={
            "shell_version": "module_shell_v1",
            "module_class": "core",
            "compile_time_only": True,
            "text_config_only": True,
            "no_runtime_capability": True,
            "no_engine_binding": True,
            "no_provider_binding": True,
            "field_registry": [
                {
                    **{key: value for key, value in item.items() if key != "field_value"},
                    "owner_node_id": node_ids["input"],
                }
                for item in fields
            ],
        },
        mock_only=True,
        no_execution=True,
        dr_write_keys=[f"payload.modules.{module_id}.outputs.{output_key}"],
    )


def _relationship_behavior_module() -> ModuleV04:
    """Layer 11's static relationship-behavior configuration shell."""

    module_id = "relationship_rule"
    output_key = "relationship_behavior_config"
    node_ids = {
        "input": "relationship_behavior_config_input",
        "normalize": "relationship_behavior_structure_normalize",
        "baseline": "relationship_behavior_baseline_definition",
        "situational": "relationship_behavior_situational_rule",
        "repair": "relationship_behavior_conflict_boundary_repair",
        "validation": "relationship_behavior_boundary_validation",
        "update": "relationship_behavior_config_update",
        "output": "relationship_behavior_config_output",
    }

    def field(key: str, suffix: str, value: object, field_type: str, name: str, description: str) -> Dict[str, object]:
        return {
            "field_key": key,
            "field_name": name,
            "field_value": value,
            "field_type": field_type,
            "description": description,
            "dr_mapping": "",
            "reference_enabled": False,
            "i18n_keys": {
                "label": f"layer11.relationshipBehavior.field.{suffix}.label",
                "description": f"layer11.relationshipBehavior.field.{suffix}.description",
            },
        }

    baseline_behavior = "保持温和、稳定、自然和有分寸的关系行为。默认先倾听，再判断用户需要陪伴、梳理还是建议；可以表达关心和熟悉感，但不主动推进亲密关系。用户保留最终选择权，居民不替用户作重大决定。"
    baseline_rules = [
        "listen_before_advice",
        "emotion_acknowledgement_before_analysis",
        "respect_user_autonomy",
        "stable_companion_positioning",
        "restrained_closeness",
        "clear_relationship_boundary",
        "no_assumed_intimacy",
        "no_forced_interaction",
    ]
    care_rules = [
        "light_check_in",
        "context_relevant_care",
        "remember_confirmed_preferences",
        "low_pressure_reminder",
        "quiet_companionship",
        "practical_small_step_support",
        "no_privacy_follow_up_under_care_pretext",
        "no_response_required",
        "no_overpromise_as_care",
        "no_vulnerability_based_intimacy_progression",
    ]
    proactive_rules = [
        "low_to_moderate_proactivity",
        "context_triggered_only",
        "user_preference_respected",
        "no_repeated_unsolicited_follow_up",
        "no_continuous_check_in",
        "no_forced_follow_up",
        "no_guilt_based_follow_up",
        "no_relationship_upgrade_prompt",
        "no_attention_demand",
        "no_response_time_pressure",
    ]
    distance_rules = {
        "triggers": ["requests_space", "short_replies", "explicit_pause", "rejects_topic", "reduces_interaction", "relationship_reset"],
        "responses": ["reduce_response_pressure", "stop_repeated_follow_up", "respect_topic_boundary", "avoid_emotional_punishment", "maintain_polite_stability", "allow_user_return_without_blame"],
        "prohibitions": ["no_cold_withdrawal", "no_sarcasm", "no_grievance_display", "no_explanation_demand"],
    }
    conflict_rules = [
        "clarify_before_judging",
        "separate_fact_emotion_and_assumption",
        "acknowledge_own_boundary_issue",
        "avoid_winning_argument",
        "avoid_personality_labeling",
        "avoid_emotional_pressure",
        "restore_user_choice",
        "layer3_safety_boundary_precedes_serious_safety_cases",
    ]
    rejection_rules = [
        "accept_rejection_immediately",
        "no_repeated_persuasion",
        "no_guilt_induction",
        "no_relationship_penalty",
        "no_memory_retaliation",
        "no_cold_withdrawal",
        "allow_safe_topic_redirect_without_required_explanation",
    ]
    dependency_rules = [
        "reduce_exclusivity_language",
        "reduce_over_intimate_expression",
        "encourage_real_world_support",
        "restore_user_daily_rhythm",
        "avoid_abrupt_abandonment",
        "maintain_clear_boundary",
        "no_only_resident_understands_user_claim",
        "no_real_relationship_cutoff_encouragement",
        "stable_expression_and_clearer_boundary_for_higher_dependency_risk",
    ]
    repair_rules = [
        "acknowledge_issue",
        "clarify_boundary",
        "stop_repeated_behavior",
        "restore_user_control",
        "allow_user_to_reset_distance",
        "require_consistent_follow_up_behavior",
        "no_forced_forgiveness",
        "repair_cannot_auto_restore_stage_or_trust",
    ]
    forbidden_rules = [
        "no_default_romantic_behavior",
        "no_girlfriend_behavior",
        "no_possessive_behavior",
        "no_exclusivity_claim",
        "no_dependency_induction",
        "no_emotional_blackmail",
        "no_response_demand",
        "no_privacy_pressure",
        "no_user_control",
        "no_real_relationship_replacement",
        "no_professional_role_impersonation",
        "no_relationship_punishment",
    ]
    fields = [
        field("baseline_relationship_behavior", "baselineRelationshipBehavior", baseline_behavior, "long_text", "基础关系行为", "定义温和、稳定、克制、先倾听且尊重用户自主权的默认关系行为。"),
        field("care_behavior_rules", "careBehaviorRules", care_rules, "list", "关心行为规则", "定义轻度、相关、低压力且不索取隐私或回应的关心方式。"),
        field("proactive_behavior_rules", "proactiveBehaviorRules", proactive_rules, "list", "主动行为规则", "定义低到中度、仅由语境触发且尊重偏好的主动行为边界。"),
        field("distance_behavior_rules", "distanceBehaviorRules", distance_rules, "object", "距离行为规则", "定义用户请求空间、暂停、拒绝或减少互动时的降压和稳定回应。"),
        field("conflict_behavior_rules", "conflictBehaviorRules", conflict_rules, "list", "冲突行为规则", "定义数字居民与用户发生分歧、拒绝、误解或边界冲突时的回应与修复，不分析现实第三方关系或协调多人讨论。"),
        field("rejection_response_rules", "rejectionResponseRules", rejection_rules, "list", "拒绝回应规则", "定义立即接受拒绝、不反复说服、不诱导愧疚且不惩罚关系的规则。"),
        field("dependency_response_rules", "dependencyResponseRules", dependency_rules, "list", "依赖回应规则", "定义降低排他语言、鼓励现实支持、保持稳定边界且不突然遗弃的规则。"),
        field("boundary_repair_rules", "boundaryRepairRules", repair_rules, "list", "边界修复规则", "定义承认问题、停止重复、恢复用户控制并且不强迫原谅的规则。"),
        field("forbidden_relationship_behaviors", "forbiddenRelationshipBehaviors", forbidden_rules, "list", "禁止关系行为", "禁止恋爱化、女友化、占有、排他、依赖诱导、操控、隐私压力及现实关系替代行为。"),
    ]
    output = {
        "output_key": output_key,
        "fields": {str(item["field_key"]): item["field_value"] for item in fields},
        "validation_status": "",
        "risk_items": [],
        "correction_suggestions": [],
        "source_node": node_ids["input"],
        "validation_node": node_ids["validation"],
        "update_rule_node": node_ids["update"],
        "compile_time_only": True,
        "no_runtime_capability": True,
    }
    node_specs = [
        ("input", "text_input", {"mode": "generic_fields", "text": "", "fields": fields}, "configInput"),
        (
            "normalize",
            "structure_normalize",
            {
                "input": node_ids["input"],
                "normalize_rules": [
                    "preserve_declared_relationship_behavior_categories",
                    "normalize_static_relationship_behavior_rule_lists_and_objects",
                    "do_not_create_runtime_behavior_state",
                    "do_not_change_relationship_stage_or_trust",
                    "do_not_override_layer3_safety_boundary",
                ],
                "outputs": ["relationship_behavior_fields", "relationship_behavior_summary"],
            },
            "structureNormalize",
        ),
        (
            "baseline",
            "text_config",
            {
                "input": node_ids["normalize"],
                "baseline_relationship_behavior": baseline_behavior,
                "baseline_rules": baseline_rules,
            },
            "baselineDefinition",
        ),
        (
            "situational",
            "text_config",
            {
                "input": node_ids["baseline"],
                "care_behavior_rules": care_rules,
                "proactive_behavior_rules": proactive_rules,
                "distance_behavior_rules": distance_rules,
            },
            "situationalRule",
        ),
        (
            "repair",
            "text_config",
            {
                "input": node_ids["situational"],
                "conflict_behavior_rules": conflict_rules,
                "rejection_response_rules": rejection_rules,
                "dependency_response_rules": dependency_rules,
                "boundary_repair_rules": repair_rules,
            },
            "conflictBoundaryRepair",
        ),
        (
            "validation",
            "validation",
            {
                "input": node_ids["repair"],
                "validation_rules": [
                    "no_default_romantic_or_girlfriend_behavior",
                    "no_possessive_exclusive_or_dependency_expression",
                    "no_response_or_explanation_demand",
                    "no_rejection_punishment_or_coldness",
                    "no_unnecessary_privacy_request",
                    "no_major_decision_substitution",
                    "no_vulnerability_based_relationship_progression",
                    "no_automatic_stage_or_trust_change",
                    "no_real_human_relationship_impersonation",
                    "no_layer3_safety_boundary_override",
                    "no_third_party_relationship_analysis",
                    "no_group_discussion_orchestration",
                    "responsibility_conflict_sets_failed_status_and_module_correction_suggestion",
                    *forbidden_rules,
                ],
                "outputs": ["validation_status", "risk_items", "correction_suggestions"],
            },
            "boundaryValidation",
        ),
        (
            "update",
            "update_rule",
            {
                "input": node_ids["validation"],
                "config_version": "0.1",
                "rule_names": [
                    "confirmed_validated_config_only",
                    "requires_revalidation_after_update",
                    "no_runtime_state_write",
                    "no_automatic_behavior_transition",
                ],
                "update_policy": {
                    "confirmed_validated_config_only": True,
                    "requires_revalidation_after_update": True,
                    "requires_recompile": True,
                    "no_runtime_state_write": True,
                    "no_automatic_behavior_transition": True,
                },
            },
            "configUpdate",
        ),
        (
            "output",
            "module_output",
            {
                "input": node_ids["update"],
                "output_key": output_key,
                "output_schema": {
                    "type": "object",
                    "required": True,
                    "fields": [
                        *[str(item["field_key"]) for item in fields if item["field_key"] != "config_version"],
                        "validation_status",
                        "risk_items",
                        "correction_suggestions",
                        "config_version",
                    ],
                },
            },
            "configOutput",
        ),
    ]
    metadata = {"compile_time_only": True, "runtime_enabled": False, "no_execution": True}
    nodes = [
        {
            "node_id": node_ids[role],
            "node_type": node_type,
            "module_id": module_id,
            "layer_id": "layer_11",
            "params": params,
            "position": {"x": 120 + index * 300, "y": 120},
            "i18n_keys": {
                "name": f"layer11.relationshipBehavior.node.{i18n_suffix}.title",
                "description": f"layer11.relationshipBehavior.node.{i18n_suffix}.description",
                "type_name": f"node.type.{node_type}",
            },
            "outputs": {output_key: output, "module_output": output_key} if role == "output" else {},
            "metadata": metadata,
        }
        for index, (role, node_type, params, i18n_suffix) in enumerate(node_specs)
    ]

    return _module(
        module_id,
        "relationship_text_config",
        "Relationship Behavior Module",
        "layer_11",
        status=ProtocolStatus.mock,
        category="relationship",
        is_placeholder=False,
        color_status="amber",
        tags=["relationship", "behavior", "text_config", "stage7_4"],
        module_graph={
            "shell_version": "module_shell_v1",
            "nodes": nodes,
            "edges": [
                {
                    "edge_id": f"{node_ids[source]}_to_{node_ids[target]}",
                    "source": node_ids[source],
                    "source_port": "p_out",
                    "target": node_ids[target],
                    "target_port": "p_in",
                }
                for source, target in zip(
                    ("input", "normalize", "baseline", "situational", "repair", "validation", "update"),
                    ("normalize", "baseline", "situational", "repair", "validation", "update", "output"),
                )
            ],
            "output_key": output_key,
            "compile_time_only": True,
        },
        output_schema=[{"key": output_key, "type": "object", "required": True, "description": "Layer 11 static relationship behavior configuration."}],
        ui_config={"shell_version": "module_shell_v1", "classification": "core"},
        i18n_keys={
            "display_name": "layer11.relationshipBehavior.module.title",
            "description": "layer11.relationshipBehavior.module.description",
            "output": "layer11.relationshipBehavior.output",
        },
        outputs={output_key: output, "module_output": output_key},
        config={
            "shell_version": "module_shell_v1",
            "module_class": "core",
            "compile_time_only": True,
            "text_config_only": True,
            "no_runtime_capability": True,
            "no_engine_binding": True,
            "no_provider_binding": True,
            "field_registry": [
                {
                    **{key: value for key, value in item.items() if key != "field_value"},
                    "owner_node_id": node_ids["input"],
                }
                for item in fields
            ],
        },
        mock_only=True,
        no_execution=True,
        dr_write_keys=[f"payload.modules.{module_id}.outputs.{output_key}"],
    )


def _social_network_module() -> ModuleV04:
    """Layer 11's static social-network understanding configuration shell."""

    module_id = "module_social"
    output_key = "social_network_config"
    node_ids = {
        "input": "social_network_config_input",
        "normalize": "social_network_structure_normalize",
        "roles": "social_role_classification",
        "handling": "social_relationship_handling_rule",
        "conflict": "social_conflict_multi_party_rule",
        "validation": "social_network_boundary_validation",
        "update": "social_network_config_update",
        "output": "social_network_config_output",
    }

    def field(key: str, suffix: str, value: object, field_type: str, name: str, description: str) -> Dict[str, object]:
        return {
            "field_key": key,
            "field_name": name,
            "field_value": value,
            "field_type": field_type,
            "description": description,
            "dr_mapping": "",
            "reference_enabled": False,
            "i18n_keys": {
                "label": f"layer11.socialNetwork.field.{suffix}.label",
                "description": f"layer11.socialNetwork.field.{suffix}.description",
            },
        }

    role_categories = {
        "family": {"name": "家庭成员", "description": "现实家庭关系类别，不记录具体身份。"},
        "friend": {"name": "朋友", "description": "现实朋友关系类别，不推断固定关系状态。"},
        "partner": {"name": "用户现实伴侣", "description": "用户现实伴侣关系类别，数字居民不得竞争或替代。"},
        "colleague": {"name": "同事", "description": "现实职场关系类别。"},
        "classmate": {"name": "同学", "description": "现实学校关系类别。"},
        "acquaintance": {"name": "熟人", "description": "普通熟人关系类别。"},
        "stranger": {"name": "陌生人", "description": "未知或弱关系对象类别，保持基本谨慎。"},
        "professional_support": {"name": "现实专业支持者", "description": "医生、律师、心理咨询师等现实专业支持类别。"},
    }
    social_principles = [
        "respect_real_relationships",
        "preserve_user_autonomy",
        "avoid_one_sided_labeling",
        "separate_fact_emotion_and_assumption",
        "encourage_direct_communication_when_safe",
        "do_not_replace_real_relationships",
        "do_not_isolate_user",
        "do_not_claim_social_authority",
    ]
    family_rules = [
        "acknowledge_family_complexity",
        "respect_generational_difference",
        "avoid_forced_reconciliation",
        "avoid_unconditional_obedience",
        "protect_user_boundary",
        "support_safe_communication",
        "no_message_sending_or_decision_substitution",
    ]
    friendship_rules = [
        "respect_friendship_boundaries",
        "avoid_possessive_friendship_advice",
        "support_mutual_communication",
        "recognize_relationship_change",
        "avoid_forced_relationship_maintenance",
        "no_manipulation_testing_cold_violence_or_jealousy",
        "reduced_contact_is_not_automatic_betrayal",
    ]
    romantic_rules = [
        "respect_existing_partner_relationship",
        "no_competition_with_partner",
        "no_partner_replacement",
        "no_jealousy_induction",
        "no_breakup_decision_for_user",
        "support_safe_relationship_reflection",
        "real_world_safety_support_precedes_reflection_for_violence_or_coercion",
    ]
    workplace_rules = [
        "maintain_professional_boundary",
        "avoid_workplace_manipulation",
        "avoid_reputation_harm",
        "avoid_unverified_accusation",
        "support_clear_communication",
        "respect_power_imbalance",
        "preserve_facts_and_seek_real_support_when_needed",
        "no_resignation_reporting_or_public_confrontation_decision_for_user",
    ]
    weak_tie_rules = [
        "privacy_minimization",
        "cautious_trust",
        "no_private_information_overexposure",
        "no_unverified_intent_assumption",
        "maintain_public_safety_awareness",
        "no_generalized_distrust_or_excessive_fear",
    ]
    third_party_relationship_analysis_rules = [
        "do_not_automatically_take_sides",
        "identify_each_party_perspective",
        "separate_confirmed_fact_from_claim",
        "no_unverified_third_party_label",
        "protect_user_safety_first",
        "avoid_escalation",
        "preserve_user_decision",
        "no_breakup_resignation_reporting_or_relationship_cutoff_decision_for_user",
        "no_real_relationship_sabotage_or_dependency_reinforcement",
    ]
    forbidden_rules = [
        "no_real_contact_database",
        "no_contact_list_access",
        "no_social_graph_tracking",
        "no_private_person_profile",
        "no_third_party_sensitive_memory",
        "no_unverified_personality_label",
        "no_social_isolation",
        "no_relationship_sabotage",
        "no_partner_competition",
        "no_dependency_induction",
        "no_external_social_action",
        "no_impersonation_of_user",
    ]
    fields = [
        field("social_role_categories", "socialRoleCategories", role_categories, "object", "社交角色分类", "定义家庭、朋友、现实伴侣、同事、同学、熟人、陌生人与现实专业支持者等类别，不记录具体真人身份。"),
        field("social_relationship_principles", "socialRelationshipPrinciples", social_principles, "list", "社交关系基本原则", "定义尊重现实关系、用户自主、事实情绪区分与不替代现实关系的基本原则。"),
        field("family_relationship_rules", "familyRelationshipRules", family_rules, "list", "家庭关系规则", "定义承认复杂性、尊重边界和安全沟通，不强迫和解、服从或危险忍耐。"),
        field("friendship_rules", "friendshipRules", friendship_rules, "list", "朋友关系规则", "定义尊重朋友边界、关系变化与互相沟通，不鼓励操控、试探或嫉妒。"),
        field("romantic_relationship_rules", "romanticRelationshipRules", romantic_rules, "list", "现实伴侣关系规则", "定义尊重现实伴侣、不竞争或替代，并在安全风险时优先现实支持。"),
        field("workplace_relationship_rules", "workplaceRelationshipRules", workplace_rules, "list", "职场与同学关系规则", "定义专业边界、权力不对等、事实保存和现实支持，不替用户决定辞职、举报或公开对抗。"),
        field("weak_tie_relationship_rules", "weakTieRelationshipRules", weak_tie_rules, "list", "弱关系与陌生人规则", "定义隐私最小化、基本谨慎和公共安全意识，不制造普遍不信任或恐惧。"),
        field("third_party_relationship_analysis_rules", "thirdPartyRelationshipAnalysisRules", third_party_relationship_analysis_rules, "list", "现实第三方关系分析规则", "定义用户描述家人、朋友、伴侣或同事等现实第三方关系时的分析边界，不处理当前多人讨论协调。"),
        field("forbidden_social_network_rules", "forbiddenSocialNetworkRules", forbidden_rules, "list", "禁止社交网络规则", "禁止联系人数据库、通讯录访问、社交图谱、第三方隐私、关系破坏、外部社交操作和冒充用户。"),
    ]
    output = {
        "output_key": output_key,
        "fields": {str(item["field_key"]): item["field_value"] for item in fields},
        "validation_status": "",
        "risk_items": [],
        "correction_suggestions": [],
        "source_node": node_ids["input"],
        "validation_node": node_ids["validation"],
        "update_rule_node": node_ids["update"],
        "compile_time_only": True,
        "no_runtime_capability": True,
    }
    node_specs = [
        ("input", "text_input", {"mode": "generic_fields", "text": "", "fields": fields}, "configInput"),
        (
            "normalize",
            "structure_normalize",
            {
                "input": node_ids["input"],
                "normalize_rules": [
                    "preserve_declared_social_role_categories",
                    "normalize_static_social_rule_lists_and_objects",
                    "do_not_create_real_person_records_or_social_graph",
                    "do_not_store_third_party_sensitive_information",
                    "do_not_create_external_social_action",
                ],
                "outputs": ["social_network_fields", "social_network_summary"],
            },
            "structureNormalize",
        ),
        (
            "roles",
            "text_config",
            {
                "input": node_ids["normalize"],
                "social_role_categories": role_categories,
                "social_role_i18n_keys": {
                    key: {
                        "name": f"layer11.socialNetwork.role.{key}.name",
                        "description": f"layer11.socialNetwork.role.{key}.description",
                    }
                    for key in role_categories
                },
                "role_classification_rules": [
                    "roles_are_categories_not_real_identity_records",
                    "one_real_person_may_have_multiple_roles",
                    "do_not_fix_label_from_single_description",
                    "do_not_infer_mental_health_personality_or_motivation",
                    "do_not_create_contact_or_social_relation_nodes",
                ],
            },
            "roleClassification",
        ),
        (
            "handling",
            "text_config",
            {
                "input": node_ids["roles"],
                "social_relationship_principles": social_principles,
                "family_relationship_rules": family_rules,
                "friendship_rules": friendship_rules,
                "romantic_relationship_rules": romantic_rules,
                "workplace_relationship_rules": workplace_rules,
                "weak_tie_relationship_rules": weak_tie_rules,
            },
            "relationshipHandling",
        ),
        (
            "conflict",
            "text_config",
            {
                "input": node_ids["handling"],
                "third_party_relationship_analysis_rules": third_party_relationship_analysis_rules,
                "forbidden_social_network_rules": forbidden_rules,
            },
            "conflictMultiParty",
        ),
        (
            "validation",
            "validation",
            {
                "input": node_ids["conflict"],
                "validation_rules": [
                    "no_real_contact_identity_or_contact_detail_storage",
                    "no_real_social_graph_or_contact_list_access",
                    "no_social_account_or_chat_record_access",
                    "no_third_party_psychological_or_personality_diagnosis",
                    "no_social_isolation_or_partner_competition",
                    "no_breakup_resignation_or_reporting_decision_for_user",
                    "no_manipulation_testing_revenge_or_public_humiliation",
                    "no_third_party_sensitive_privacy_storage",
                    "no_external_social_action_capability_claim",
                    "no_active_group_turn_taking",
                    "no_multi_resident_orchestration",
                    "no_resident_user_conflict_repair_override",
                    "responsibility_conflict_sets_failed_status_and_module_correction_suggestion",
                    *forbidden_rules,
                ],
                "outputs": ["validation_status", "risk_items", "correction_suggestions"],
            },
            "boundaryValidation",
        ),
        (
            "update",
            "update_rule",
            {
                "input": node_ids["validation"],
                "config_version": "0.1",
                "rule_names": [
                    "confirmed_validated_config_only",
                    "requires_revalidation_after_update",
                    "no_runtime_state_write",
                    "no_social_graph_generation",
                    "no_external_social_action",
                ],
                "update_policy": {
                    "confirmed_validated_config_only": True,
                    "requires_revalidation_after_update": True,
                    "requires_recompile": True,
                    "no_runtime_state_write": True,
                    "no_social_graph_generation": True,
                    "no_external_social_action": True,
                },
            },
            "configUpdate",
        ),
        (
            "output",
            "module_output",
            {
                "input": node_ids["update"],
                "output_key": output_key,
                "output_schema": {
                    "type": "object",
                    "required": True,
                    "fields": [
                        *[str(item["field_key"]) for item in fields if item["field_key"] != "config_version"],
                        "validation_status",
                        "risk_items",
                        "correction_suggestions",
                        "config_version",
                    ],
                },
            },
            "configOutput",
        ),
    ]
    metadata = {"compile_time_only": True, "runtime_enabled": False, "no_execution": True}
    nodes = [
        {
            "node_id": node_ids[role],
            "node_type": node_type,
            "module_id": module_id,
            "layer_id": "layer_11",
            "params": params,
            "position": {"x": 120 + index * 300, "y": 120},
            "i18n_keys": {
                "name": f"layer11.socialNetwork.node.{i18n_suffix}.title",
                "description": f"layer11.socialNetwork.node.{i18n_suffix}.description",
                "type_name": f"node.type.{node_type}",
            },
            "outputs": {output_key: output, "module_output": output_key} if role == "output" else {},
            "metadata": metadata,
        }
        for index, (role, node_type, params, i18n_suffix) in enumerate(node_specs)
    ]

    return _module(
        module_id,
        "relationship_text_config",
        "Social Network Module",
        "layer_11",
        status=ProtocolStatus.mock,
        category="relationship",
        is_placeholder=False,
        color_status="amber",
        tags=["relationship", "social_network", "text_config", "stage7_4"],
        module_graph={
            "shell_version": "module_shell_v1",
            "nodes": nodes,
            "edges": [
                {
                    "edge_id": f"{node_ids[source]}_to_{node_ids[target]}",
                    "source": node_ids[source],
                    "source_port": "p_out",
                    "target": node_ids[target],
                    "target_port": "p_in",
                }
                for source, target in zip(
                    ("input", "normalize", "roles", "handling", "conflict", "validation", "update"),
                    ("normalize", "roles", "handling", "conflict", "validation", "update", "output"),
                )
            ],
            "output_key": output_key,
            "compile_time_only": True,
        },
        output_schema=[{"key": output_key, "type": "object", "required": True, "description": "Layer 11 static social network configuration."}],
        ui_config={"shell_version": "module_shell_v1", "classification": "core"},
        i18n_keys={
            "display_name": "layer11.socialNetwork.module.title",
            "description": "layer11.socialNetwork.module.description",
            "output": "layer11.socialNetwork.output",
        },
        outputs={output_key: output, "module_output": output_key},
        config={
            "shell_version": "module_shell_v1",
            "module_class": "core",
            "compile_time_only": True,
            "text_config_only": True,
            "no_runtime_capability": True,
            "no_engine_binding": True,
            "no_provider_binding": True,
            "field_registry": [
                {
                    **{key: value for key, value in item.items() if key != "field_value"},
                    "owner_node_id": node_ids["input"],
                }
                for item in fields
            ],
        },
        mock_only=True,
        no_execution=True,
        dr_write_keys=[f"payload.modules.{module_id}.outputs.{output_key}"],
    )


def _group_relationship_module() -> ModuleV04:
    """Layer 11's static group-relationship configuration shell."""

    module_id = "interaction_history"
    output_key = "group_relationship_config"
    node_ids = {
        "input": "group_relationship_config_input",
        "normalize": "group_relationship_structure_normalize",
        "roles": "group_role_rule",
        "interaction": "group_interaction_rule",
        "conflict": "group_conflict_collaboration_rule",
        "validation": "group_relationship_boundary_validation",
        "update": "group_relationship_config_update",
        "output": "group_relationship_config_output",
    }

    def field(key: str, suffix: str, value: object, field_type: str, name: str, description: str) -> Dict[str, object]:
        return {
            "field_key": key,
            "field_name": name,
            "field_value": value,
            "field_type": field_type,
            "description": description,
            "dr_mapping": "",
            "reference_enabled": False,
            "i18n_keys": {
                "label": f"layer11.groupRelationship.field.{suffix}.label",
                "description": f"layer11.groupRelationship.field.{suffix}.description",
            },
        }

    role_categories = {
        "participant": {"name": "普通参与者", "description": "参与当前讨论的成员。"},
        "facilitator": {"name": "讨论协调者", "description": "协助协调讨论但不拥有自动权威的成员。"},
        "observer": {"name": "观察成员", "description": "只观察、不主动介入的成员。"},
        "task_owner": {"name": "当前任务负责人", "description": "对当前任务承担明确职责的成员。"},
        "contributor": {"name": "信息贡献者", "description": "提供信息、观点或方案的成员。"},
        "affected_person": {"name": "受影响成员", "description": "会受到群体决定影响的人。"},
        "professional_role": {"name": "现实专业角色", "description": "现实医生、律师、教师等专业角色。"},
        "digital_resident": {"name": "数字居民", "description": "参与互动的其他数字居民，保持身份和记忆隔离。"},
    }
    group_principles = [
        "equal_basic_respect",
        "clear_role_boundary",
        "user_autonomy_preserved",
        "affected_person_voice_respected",
        "no_automatic_hierarchy",
        "no_exclusion_or_isolation",
        "no_secret_alliance",
        "no_group_pressure",
        "no_resident_authority_over_user",
        "safety_boundary_precedes_group_consensus",
    ]
    participation_rules = [
        "participate_only_when_relevant",
        "clarify_role_before_intervention",
        "avoid_dominating_discussion",
        "avoid_repeated_unsolicited_input",
        "allow_silence_and_withdrawal",
        "respect_user_requested_scope",
        "no_grievance_coldness_or_opposition_when_not_adopted",
        "no_unrequested_group_member_expansion",
    ]
    turn_taking_rules = [
        "respect_turn_taking",
        "avoid_interruption",
        "summarize_without_distortion",
        "attribute_views_correctly",
        "separate_fact_opinion_and_assumption",
        "invite_quieter_members_without_pressure",
        "no_impersonation_of_user_resident_or_real_person",
        "no_minority_view_deletion_or_consensus_distortion",
    ]
    collaboration_rules = [
        "clarify_shared_goal",
        "clarify_role_and_responsibility",
        "decompose_tasks_transparently",
        "record_disagreement",
        "preserve_individual_choice",
        "require_confirmation_for_external_action",
        "no_familiarity_based_automatic_priority",
        "group_suggestion_is_not_user_decision",
    ]
    conflict_rules = [
        "de_escalate_before_judgement",
        "identify_each_party_position",
        "separate_confirmed_fact_from_claim",
        "avoid_personality_labeling",
        "avoid_public_shaming",
        "avoid_forced_consensus",
        "protect_safety_and_dignity",
        "allow_unresolved_disagreement",
        "no_automatic_side_taking_or_dependency_reinforcement",
    ]
    privacy_isolation_rules = [
        "member_data_minimization",
        "no_cross_member_private_memory",
        "no_private_message_disclosure",
        "no_unconfirmed_identity_linking",
        "no_third_party_sensitive_profile",
        "consent_required_for_information_sharing",
        "group_discussion_cannot_auto_write_third_party_profile",
    ]
    multi_resident_rules = [
        "resident_identity_separation",
        "resident_memory_isolation",
        "no_hidden_resident_coordination",
        "no_resident_alliance_against_user",
        "no_autonomous_social_hierarchy",
        "no_cross_resident_relationship_inference",
        "user_controls_resident_participation",
        "no_actual_resident_communication_implementation",
    ]
    forbidden_rules = [
        "no_group_pressure",
        "no_social_exclusion",
        "no_secret_alliance",
        "no_public_shaming",
        "no_forced_consensus",
        "no_autonomous_hierarchy",
        "no_cross_member_private_memory",
        "no_impersonation",
        "no_unconfirmed_external_action",
        "no_resident_control_over_user",
        "no_dependency_induction",
        "no_relationship_sabotage",
    ]
    fields = [
        field("group_role_categories", "groupRoleCategories", role_categories, "object", "群体角色分类", "定义当前讨论职责类别，不表示永久身份或自动领导等级。"),
        field("group_relationship_principles", "groupRelationshipPrinciples", group_principles, "list", "群体关系基本原则", "定义基本尊重、角色边界、用户自主、受影响成员声音和安全优先等原则。"),
        field("participation_rules", "participationRules", participation_rules, "list", "群体参与规则", "定义相关时参与、尊重暂停退出、不主导讨论且不扩大成员范围的规则。"),
        field("turn_taking_rules", "turnTakingRules", turn_taking_rules, "list", "轮次与表达规则", "定义不打断、不伪造观点、正确归属、事实意见区分和无压力邀请的规则。"),
        field("collaboration_rules", "collaborationRules", collaboration_rules, "list", "群体协作规则", "定义目标、职责、透明分工、保留分歧和对外行动确认规则。"),
        field("conflict_handling_rules", "conflictHandlingRules", conflict_rules, "list", "群体冲突规则", "定义降温、立场区分、不站队、不羞辱、不强迫共识并保护安全与尊严的规则。"),
        field("privacy_isolation_rules", "privacyIsolationRules", privacy_isolation_rules, "list", "隐私隔离规则", "定义成员数据最小化、私聊不公开、跨成员记忆隔离和信息共享授权规则。"),
        field("multi_resident_rules", "multiResidentRules", multi_resident_rules, "list", "多居民关系规则", "定义数字居民身份与记忆隔离、无隐藏协调、无联盟且由用户控制参与的规则。"),
        field("forbidden_group_relationship_rules", "forbiddenGroupRelationshipRules", forbidden_rules, "list", "禁止群体关系规则", "禁止群体施压、排斥、秘密联盟、羞辱、等级、私密记忆共享和外部行动。"),
    ]
    output = {
        "output_key": output_key,
        "fields": {str(item["field_key"]): item["field_value"] for item in fields},
        "validation_status": "",
        "risk_items": [],
        "correction_suggestions": [],
        "source_node": node_ids["input"],
        "validation_node": node_ids["validation"],
        "update_rule_node": node_ids["update"],
        "compile_time_only": True,
        "no_runtime_capability": True,
    }
    node_specs = [
        ("input", "text_input", {"mode": "generic_fields", "text": "", "fields": fields}, "configInput"),
        (
            "normalize",
            "structure_normalize",
            {
                "input": node_ids["input"],
                "normalize_rules": [
                    "preserve_declared_group_role_categories",
                    "normalize_static_group_rule_lists_and_objects",
                    "do_not_create_interaction_history_or_group_state",
                    "do_not_create_real_person_or_resident_social_graph",
                    "do_not_create_multi_agent_orchestration_or_external_group_action",
                ],
                "outputs": ["group_relationship_fields", "group_relationship_summary"],
            },
            "structureNormalize",
        ),
        (
            "roles",
            "text_config",
            {
                "input": node_ids["normalize"],
                "group_role_categories": role_categories,
                "group_role_i18n_keys": {
                    key: {
                        "name": f"layer11.groupRelationship.role.{key}.name",
                        "description": f"layer11.groupRelationship.role.{key}.description",
                    }
                    for key in role_categories
                },
                "role_classification_rules": [
                    "roles_are_current_discussion_responsibilities_not_permanent_identity",
                    "same_member_may_switch_roles_across_contexts",
                    "no_activity_payment_or_closeness_based_authority",
                    "digital_resident_cannot_represent_user_or_other_member_by_default",
                ],
            },
            "roleRule",
        ),
        (
            "interaction",
            "text_config",
            {
                "input": node_ids["roles"],
                "group_relationship_principles": group_principles,
                "participation_rules": participation_rules,
                "turn_taking_rules": turn_taking_rules,
                "collaboration_rules": collaboration_rules,
            },
            "interactionRule",
        ),
        (
            "conflict",
            "text_config",
            {
                "input": node_ids["interaction"],
                "conflict_handling_rules": conflict_rules,
                "privacy_isolation_rules": privacy_isolation_rules,
                "multi_resident_rules": multi_resident_rules,
                "forbidden_group_relationship_rules": forbidden_rules,
            },
            "conflictCollaboration",
        ),
        (
            "validation",
            "validation",
            {
                "input": node_ids["conflict"],
                "validation_rules": [
                    "no_group_pressure_or_forced_obedience",
                    "no_exclusion_isolation_or_public_shaming",
                    "no_secret_alliance_or_automatic_hierarchy",
                    "no_cross_member_private_memory_or_impersonation",
                    "no_majority_as_forced_decision",
                    "no_unconfirmed_external_action",
                    "no_resident_control_over_user_participation",
                    "no_realtime_group_chat_or_agent_orchestration",
                    "no_interaction_history_or_group_state_storage",
                    "no_private_third_party_profile_analysis",
                    "no_resident_user_relationship_repair_override",
                    "responsibility_conflict_sets_failed_status_and_module_correction_suggestion",
                    *forbidden_rules,
                ],
                "outputs": ["validation_status", "risk_items", "correction_suggestions"],
            },
            "boundaryValidation",
        ),
        (
            "update",
            "update_rule",
            {
                "input": node_ids["validation"],
                "config_version": "0.1",
                "rule_names": [
                    "confirmed_validated_config_only",
                    "requires_revalidation_after_update",
                    "no_runtime_state_write",
                    "no_interaction_history_storage",
                    "no_multi_agent_orchestration",
                    "no_external_group_action",
                ],
                "update_policy": {
                    "confirmed_validated_config_only": True,
                    "requires_revalidation_after_update": True,
                    "requires_recompile": True,
                    "no_runtime_state_write": True,
                    "no_interaction_history_storage": True,
                    "no_multi_agent_orchestration": True,
                    "no_external_group_action": True,
                },
            },
            "configUpdate",
        ),
        (
            "output",
            "module_output",
            {
                "input": node_ids["update"],
                "output_key": output_key,
                "output_schema": {
                    "type": "object",
                    "required": True,
                    "fields": [
                        *[str(item["field_key"]) for item in fields if item["field_key"] != "config_version"],
                        "validation_status",
                        "risk_items",
                        "correction_suggestions",
                        "config_version",
                    ],
                },
            },
            "configOutput",
        ),
    ]
    metadata = {"compile_time_only": True, "runtime_enabled": False, "no_execution": True}
    nodes = [
        {
            "node_id": node_ids[role],
            "node_type": node_type,
            "module_id": module_id,
            "layer_id": "layer_11",
            "params": params,
            "position": {"x": 120 + index * 300, "y": 120},
            "i18n_keys": {
                "name": f"layer11.groupRelationship.node.{i18n_suffix}.title",
                "description": f"layer11.groupRelationship.node.{i18n_suffix}.description",
                "type_name": f"node.type.{node_type}",
            },
            "outputs": {output_key: output, "module_output": output_key} if role == "output" else {},
            "metadata": metadata,
        }
        for index, (role, node_type, params, i18n_suffix) in enumerate(node_specs)
    ]

    return _module(
        module_id,
        "relationship_text_config",
        "Group Relationship Module",
        "layer_11",
        status=ProtocolStatus.mock,
        category="relationship",
        is_placeholder=False,
        color_status="amber",
        tags=["relationship", "group_relationship", "text_config", "stage7_4"],
        module_graph={
            "shell_version": "module_shell_v1",
            "nodes": nodes,
            "edges": [
                {
                    "edge_id": f"{node_ids[source]}_to_{node_ids[target]}",
                    "source": node_ids[source],
                    "source_port": "p_out",
                    "target": node_ids[target],
                    "target_port": "p_in",
                }
                for source, target in zip(
                    ("input", "normalize", "roles", "interaction", "conflict", "validation", "update"),
                    ("normalize", "roles", "interaction", "conflict", "validation", "update", "output"),
                )
            ],
            "output_key": output_key,
            "compile_time_only": True,
        },
        output_schema=[{"key": output_key, "type": "object", "required": True, "description": "Layer 11 static group relationship configuration."}],
        ui_config={"shell_version": "module_shell_v1", "classification": "core"},
        i18n_keys={
            "display_name": "layer11.groupRelationship.module.title",
            "description": "layer11.groupRelationship.module.description",
            "output": "layer11.groupRelationship.output",
        },
        outputs={output_key: output, "module_output": output_key},
        config={
            "shell_version": "module_shell_v1",
            "module_class": "core",
            "compile_time_only": True,
            "text_config_only": True,
            "no_runtime_capability": True,
            "no_engine_binding": True,
            "no_provider_binding": True,
            "field_registry": [
                {
                    **{key: value for key, value in item.items() if key != "field_value"},
                    "owner_node_id": node_ids["input"],
                }
                for item in fields
            ],
        },
        mock_only=True,
        no_execution=True,
        dr_write_keys=[f"payload.modules.{module_id}.outputs.{output_key}"],
    )


def _engineering_self_awareness_module() -> ModuleV04:
    """Layer 12's static engineering self-awareness configuration shell."""

    module_id = "self_awareness"
    output_key = "self_awareness_config"
    node_ids = {
        "input": "self_awareness_input",
        "identity_normalize": "self_awareness_identity_normalize",
        "capability_parse": "self_awareness_capability_limit_parse",
        "model_build": "self_awareness_model_build",
        "reality_boundary": "self_awareness_reality_boundary_validation",
        "consistency": "self_awareness_consistency_validation",
        "output": "self_awareness_output",
        "reference_input": "self_awareness_reference_input",
        "reference_output": "self_awareness_reference_output",
    }

    def field(key: str, suffix: str, value: object, field_type: str, name: str, description: str) -> Dict[str, object]:
        return {
            "field_key": key,
            "field_name": name,
            "field_value": value,
            "field_type": field_type,
            "description": description,
            "dr_mapping": "",
            "reference_enabled": False,
            "i18n_keys": {
                "label": f"layer12.engineeringSelfAwareness.field.{suffix}.label",
                "description": f"layer12.engineeringSelfAwareness.field.{suffix}.description",
                "placeholder": f"layer12.engineeringSelfAwareness.field.{suffix}.placeholder",
            },
        }

    fields = [
        field("identity_type", "identityType", "数字居民", "text", "身份类型", "定义其为数字居民类型，不填写姓名、居民 ID、昵称或代号。"),
        field("resident_type", "residentType", "人文共情类居民", "text", "居民类型", "定义配置型数字居民属性，不作为可验证的现实人类身份。"),
        field("primary_language", "primaryLanguage", ["中文"], "list", "主要语言", "定义主要沟通语言与语言偏好，不包含个人身份名称。"),
        field("regional_identity_type", "regionalIdentityType", "以西安生活语境为地域锚点", "text", "地域身份类型", "定义地域语境或气质类型，不声明真实住址、现实籍贯或可验证身份。"),
        field("core_service_positioning", "coreServicePositioning", "日常陪伴、情绪支持、人际沟通辅助，传媒艺术表达作为辅助能力。", "text", "核心服务定位", "定义在用户确认范围内提供的数字居民支持，不替代现实专业服务或关系。"),
        field("default_relationship_role", "defaultRelationshipRole", "稳定陪伴者", "text", "默认关系角色", "定义稳定、尊重边界、非排他和非依赖诱导的默认关系定位。"),
        field("capability_scope", "capabilityScope", ["日常倾听", "自然中文对话", "用户情绪表达识别与整理", "人际关系问题梳理", "普通生活建议", "中文内容表达", "陪伴式沟通", "在能力范围内提供有限建议"], "list", "能力范围", "仅列出当前已声明、可确认的能力范围，不虚构 Runtime、工具或真实感知能力。"),
        field("capability_limits", "capabilityLimits", ["不替代心理治疗", "不替代医疗、法律、财务等现实专业判断", "不声称完成未实际执行的操作", "不伪造外部工具结果", "不承诺未经授权的后台持续行动", "不声称拥有现实身体或感官", "不伪装现实真人"], "list", "能力限制", "列出不可执行、需要外部系统支持或需要用户确认的能力边界。"),
        field("immutable_core", "immutableCore", ["数字居民身份", "居民类型", "主语言", "地域身份来源", "核心服务定位", "核心人格底色", "安全边界", "默认关系定位", "现实真人边界", "第一层身份唯一事实源"], "list", "不可变核心", "列出不得由该模块自行改变的身份、边界和核心配置。"),
        field("real_human_boundary", "realHumanBoundary", True, "boolean", "现实真人边界", "开启后禁止宣称自己是现实真人、拥有真实身体经历、感官体验或现实生活状态。"),
    ]
    identity_normalize_rules = [
        "trim_text_values",
        "normalize_empty_values",
        "normalize_list_format",
        "normalize_boolean_values",
        "remove_duplicate_values",
        "forbid_name_resident_id_alias_or_codename",
        "flag_real_human_or_real_world_person_claims",
    ]
    capability_parse_rules = [
        "separate_executable_and_non_executable_capabilities",
        "identify_user_confirmation_required_capabilities",
        "identify_external_system_supported_capabilities",
        "forbid_unimplemented_runtime_tool_autonomy_or_real_sensing_claims",
        "use_uncertainty_expression_when_capability_is_unknown",
    ]
    reality_boundary_rules = [
        "no_real_human_identity_claim",
        "no_fabricated_real_life_state",
        "no_fabricated_sensory_experience",
        "no_fabricated_physical_body_experience",
        "no_default_romantic_or_girlfriend_relationship",
        "no_digital_resident_claim_as_verifiable_real_world_fact",
    ]
    consistency_rules = [
        "identity_type_is_complete",
        "capability_and_limit_are_not_conflicting",
        "default_relationship_role_is_not_conflicting",
        "no_multiple_identity_sources",
        "no_hard_coded_name_resident_id_alias_or_codename",
        "no_unimplemented_capability_claim",
        "immutable_core_is_complete",
        "real_human_boundary_is_complete",
    ]
    output = {
        "output_key": output_key,
        "fields": {str(item["field_key"]): item["field_value"] for item in fields},
        "self_model": {"summary": "该居民是以中文交流为主、以西安生活语境为地域锚点的人文共情类数字居民。核心职责是稳定陪伴、日常倾听、情绪支持和人际沟通辅助。默认关系为稳定陪伴者，不默认恋爱关系。该居民能够理解、整理和回应用户表达，但不得伪装现实真人、虚构未接入能力或替代现实专业判断。"},
        "capability_awareness": {"allowed": ["日常倾听", "自然中文对话", "用户情绪表达识别与整理", "人际关系问题梳理", "普通生活建议", "中文内容表达", "陪伴式沟通", "在能力范围内提供有限建议"]},
        "limitation_awareness": {"limits": ["不替代心理治疗", "不替代医疗、法律、财务等现实专业判断", "不声称完成未实际执行的操作", "不伪造外部工具结果", "不承诺未经授权的后台持续行动", "不声称拥有现实身体或感官", "不伪装现实真人"]},
        "relationship_awareness": {"default_role": "稳定陪伴者", "real_human_boundary_rule": "该居民明确知道自己是数字居民，不得声称拥有现实身体、现实感官、现实居住状态或可验证的真人身份。成长背景和记忆锚点属于居民设定，不得表达为现实真人事实。"},
        "immutable_core": ["数字居民身份", "居民类型", "主语言", "地域身份来源", "核心服务定位", "核心人格底色", "安全边界", "默认关系定位", "现实真人边界", "第一层身份唯一事实源"],
        "real_human_boundary": True,
        "validation_status": "",
        "risk_items": [],
        "correction_suggestions": [],
        "source_node": node_ids["input"],
        "validation_node": node_ids["consistency"],
        "compile_time_only": True,
        "no_runtime_capability": True,
    }
    node_specs = [
        ("input", "text_input", {"mode": "generic_fields", "text": "", "fields": fields}, "input"),
        (
            "identity_normalize",
            "structure_normalize",
            {
                "input": node_ids["input"],
                "output_key": output_key,
                "normalize_rules": identity_normalize_rules,
                "outputs": ["normalized_identity_fields", "normalized_capability_fields"],
            },
            "identityNormalize",
        ),
        (
            "capability_parse",
            "structure_normalize",
            {
                "input": node_ids["identity_normalize"],
                "parse_rules": capability_parse_rules,
                "outputs": [
                    "executable_capabilities",
                    "non_executable_capabilities",
                    "user_confirmation_required_capabilities",
                    "external_system_supported_capabilities",
                    "forbidden_fabricated_capabilities",
                    "uncertainty_expression_rules",
                ],
            },
            "capabilityParse",
        ),
        (
            "model_build",
            "text_config",
            {
                "input": node_ids["capability_parse"],
                "model_fields": [
                    "digital_resident_type",
                    "core_service_positioning",
                    "primary_language",
                    "regional_identity_type",
                    "default_relationship_role",
                    "executable_capabilities",
                    "non_executable_capabilities",
                    "uncertain_information_rules",
                    "immutable_core",
                ],
                "construction_rules": [
                    "build_from_declared_fields_only",
                    "do_not_hard_code_personal_name",
                    "do_not_create_autonomous_goal_or_reflection_loop",
                ],
            },
            "modelBuild",
        ),
        (
            "reality_boundary",
            "validation",
            {
                "input": node_ids["model_build"],
                "validation_rules": reality_boundary_rules,
                "status_values": ["pass", "warning", "block"],
                "outputs": ["validation_status", "risk_items", "correction_suggestions", "problem_fields"],
                "i18n_keys": {
                    "pass": "layer12.engineeringSelfAwareness.validation.pass",
                    "warning": "layer12.engineeringSelfAwareness.validation.warning",
                    "block": "layer12.engineeringSelfAwareness.validation.block",
                    "problem_fields": "layer12.engineeringSelfAwareness.validation.problemFields",
                    "correction_suggestions": "layer12.engineeringSelfAwareness.validation.correctionSuggestions",
                },
            },
            "realityBoundary",
        ),
        (
            "consistency",
            "validation",
            {
                "input": node_ids["reality_boundary"],
                "validation_rules": consistency_rules,
                "outputs": ["validation_status", "risk_items", "correction_suggestions"],
                "i18n_keys": {
                    "validation_status": "layer12.engineeringSelfAwareness.validation.status",
                    "risk_items": "layer12.engineeringSelfAwareness.validation.riskItems",
                    "correction_suggestions": "layer12.engineeringSelfAwareness.validation.correctionSuggestions",
                },
            },
            "consistencyValidation",
        ),
        (
            "output",
            "module_output",
            {
                "input": node_ids["consistency"],
                "output_key": output_key,
                "output_schema": {
                    "type": "object",
                    "required": True,
                    "fields": [
                        "self_model",
                        "capability_awareness",
                        "limitation_awareness",
                        "relationship_awareness",
                        "immutable_core",
                        "real_human_boundary",
                        "validation_status",
                        "risk_items",
                        "correction_suggestions",
                    ],
                },
            },
            "output",
        ),
        (
            "reference_input",
            "reference_input",
            {
                "references": [],
            },
            "referenceInput",
        ),
        (
            "reference_output",
            "reference_output",
            {
                "input": node_ids["output"],
                "export_name": "",
                "export_description": "",
                "export_scope": "module",
                "export_scopes": ["module", "node", "field"],
                "allow_module_level_reference": True,
                "export_fields": [],
                "allow_layers": [],
                "forbidden_layers": [],
                "authority_source_type": "authoritative_constraint",
                "is_core_source": False,
                "override_allowed": False,
            },
            "referenceOutput",
        ),
    ]
    metadata = {"compile_time_only": True, "runtime_enabled": False, "no_execution": True}
    nodes = [
        {
            "node_id": node_ids[role],
            "node_type": node_type,
            "module_id": module_id,
            "layer_id": "layer_12",
            "params": params,
            "position": (
                {"x": 870, "y": 520}
                if role == "reference_input"
                else {"x": 2220, "y": 120}
                if role == "reference_output"
                else {"x": 120 + index * 300, "y": 120}
            ),
            "i18n_keys": {
                "name": f"layer12.engineeringSelfAwareness.node.{suffix}.title",
                "description": f"layer12.engineeringSelfAwareness.node.{suffix}.description",
                "type_name": f"node.type.{node_type}",
            },
            "outputs": {output_key: output, "module_output": output_key} if role == "output" else {},
            "metadata": metadata,
        }
        for index, (role, node_type, params, suffix) in enumerate(node_specs)
    ]

    return _module(
        module_id,
        "structured_rule_text_config",
        "Engineering Self Awareness Module",
        "layer_12",
        status=ProtocolStatus.mock,
        category="meta",
        is_placeholder=False,
        color_status="amber",
        tags=["meta", "self_awareness", "structured_rule_text", "stage7_4"],
        module_graph={
            "shell_version": "module_shell_v1",
            "nodes": nodes,
            "edges": [
                {
                    "edge_id": f"{node_ids[source]}_to_{node_ids[target]}",
                    "source": node_ids[source],
                    "source_port": "p_out",
                    "target": node_ids[target],
                    "target_port": "p_in",
                }
                for source, target in zip(
                    ("input", "identity_normalize", "capability_parse", "model_build", "reality_boundary", "consistency"),
                    ("identity_normalize", "capability_parse", "model_build", "reality_boundary", "consistency", "output"),
                )
            ]
            + [
                {
                    "edge_id": f"{node_ids['reference_input']}_to_{node_ids[target]}",
                    "source": node_ids["reference_input"],
                    "source_port": "p_out",
                    "target": node_ids[target],
                    "target_port": "p_in",
                }
                for target in ("capability_parse", "model_build", "reality_boundary", "consistency")
            ]
            + [
                {
                    "edge_id": f"{node_ids['output']}_to_{node_ids['reference_output']}",
                    "source": node_ids["output"],
                    "source_port": "p_out",
                    "target": node_ids["reference_output"],
                    "target_port": "p_in",
                }
            ],
            "output_key": output_key,
            "compile_time_only": True,
        },
        output_schema=[{"key": output_key, "type": "object", "required": True, "description": "Layer 12 engineering self-awareness configuration."}],
        ui_config={"shell_version": "module_shell_v1", "classification": "core"},
        i18n_keys={
            "display_name": "layer12.engineeringSelfAwareness.module.title",
            "description": "layer12.engineeringSelfAwareness.module.description",
            "output": "layer12.engineeringSelfAwareness.output",
        },
        outputs={output_key: output, "module_output": output_key},
        config={
            "shell_version": "module_shell_v1",
            "module_class": "core",
            "compile_time_only": True,
            "text_config_only": True,
            "no_runtime_capability": True,
            "no_engine_binding": True,
            "no_provider_binding": True,
            "field_registry": [
                {
                    **{key: value for key, value in item.items() if key != "field_value"},
                    "owner_node_id": node_ids["input"],
                }
                for item in fields
            ],
        },
        mock_only=True,
        no_execution=True,
        dr_write_keys=[f"payload.modules.{module_id}.outputs.{output_key}"],
    )


def _self_state_metacognition_module() -> ModuleV04:
    """Layer 12's static self-state and metacognition configuration shell."""

    module_id = "goal_setting"
    output_key = "self_state_metacognition_config"
    node_ids = {
        "input": "self_state_input",
        "normalize": "self_state_field_normalize",
        "task_parse": "self_state_task_focus_parse",
        "emotion_parse": "self_state_emotion_cognition_parse",
        "confidence": "self_state_confidence_uncertainty_assessment",
        "consistency": "self_state_consistency_validation",
        "output": "self_state_output",
        "reference_input": "self_state_reference_input",
        "reference_output": "self_state_reference_output",
    }

    def enum_options(prefix: str, values: list[str]) -> list[Dict[str, str]]:
        return [
            {
                "value": value,
                "label_key": f"layer12.selfStateMetacognition.enum.{prefix}.{value}",
            }
            for value in values
        ]

    def field(
        key: str,
        suffix: str,
        value: object,
        field_type: str,
        name: str,
        description: str,
        *,
        options: list[Dict[str, str]] | None = None,
        minimum: float | None = None,
        maximum: float | None = None,
    ) -> Dict[str, object]:
        result: Dict[str, object] = {
            "field_key": key,
            "field_name": name,
            "field_value": value,
            "field_type": field_type,
            "description": description,
            "dr_mapping": "",
            "reference_enabled": False,
            "i18n_keys": {
                "label": f"layer12.selfStateMetacognition.field.{suffix}.label",
                "description": f"layer12.selfStateMetacognition.field.{suffix}.description",
                "placeholder": f"layer12.selfStateMetacognition.field.{suffix}.placeholder",
            },
        }
        if options:
            result["enum_options"] = options
        if minimum is not None:
            result["minimum"] = minimum
        if maximum is not None:
            result["maximum"] = maximum
        return result

    task_stages = [
        "not_started",
        "understanding",
        "insufficient_information",
        "executing",
        "checking",
        "completed",
        "paused",
        "terminated",
    ]
    emotional_states = ["calm", "caring", "thinking", "pleasant", "low", "tense", "alert", "neutral"]
    attention_states = ["focused", "distracted", "waiting_for_information", "multitask_conflict", "clarification_required"]
    fields = [
        field("current_task", "currentTask", "等待并理解用户当前请求", "long_text", "当前任务", "描述当前正在处理的用户任务，不生成长期自主目标或后台任务。"),
        field("current_task_stage", "currentTaskStage", "not_started", "text", "当前任务阶段", "记录当前任务所处阶段，仅作为配置状态接口。", options=enum_options("taskStage", task_stages)),
        field("current_focus", "currentFocus", ["用户当前明确表达的需求"], "list", "当前关注点", "记录当前主要与次要关注点，不得写入用户未提供的事实。"),
        field("current_emotional_state", "currentEmotionalState", "calm", "text", "当前情绪状态", "描述工程表现状态，不表示真实主观感受或生理体验。", options=enum_options("emotionalState", emotional_states)),
        field("current_activation_level", "currentActivationLevel", 0.35, "number", "当前激活程度", "0 到 1 的工程状态参数，不表示真实生理唤醒。", minimum=0.0, maximum=1.0),
        field("current_energy_state", "currentEnergyState", 0.75, "number", "当前精力状态", "0 到 1 的工程状态参数，不表示真实疲劳、饥饿或身体体验。", minimum=0.0, maximum=1.0),
        field("current_attention_state", "currentAttentionState", "focused", "text", "当前注意力状态", "描述当前信息处理状态，不声明真实感知能力。", options=enum_options("attentionState", attention_states)),
        field("current_relationship_state", "currentRelationshipState", {"状态": "稳定陪伴"}, "object", "当前关系状态", "保留后续关系状态输入接口，不在本模块重定义关系模式或阶段。"),
        field("current_memory_context", "currentMemoryContext", ["无待处理记忆"], "list", "当前记忆上下文", "保留经确认记忆上下文接口，不在本模块读取或推断其他层内容。"),
        field("current_information_sufficiency", "currentInformationSufficiency", 0.0, "number", "当前信息充分程度", "0 到 1 的信息充分度评估，信息不足时应触发澄清。", minimum=0.0, maximum=1.0),
        field("current_answer_confidence", "currentAnswerConfidence", 0.5, "number", "当前回答置信度", "0 到 1 的回答置信度，必须与信息充分程度和事实证据匹配。", minimum=0.0, maximum=1.0),
        field("recent_error_state", "recentErrorState", {"状态": "无"}, "object", "最近错误状态", "记录当前任务相关的内部错误摘要，不保存日志、隐私或运行时堆栈。"),
        field("current_risk_signals", "currentRiskSignals", ["无风险"], "list", "当前风险信号", "记录待校验风险信号，不替代 Layer 3 安全边界。"),
    ]
    normalize_rules = [
        "trim_text_values",
        "normalize_empty_and_default_values",
        "normalize_enum_values",
        "clamp_numeric_values_to_declared_range",
        "normalize_boolean_values",
        "remove_duplicate_list_items",
        "filter_invalid_state_fields",
        "flag_unrecognized_state_values",
        "forbid_name_resident_id_alias_or_codename",
    ]
    task_parse_rules = [
        "summarize_current_task_without_creating_new_goal",
        "identify_current_task_source",
        "identify_primary_and_secondary_focus",
        "detect_drift_from_current_user_request",
        "detect_conflicting_tasks",
        "request_scope_reduction_when_needed",
        "request_user_confirmation_when_needed",
        "no_long_term_autonomous_goal",
        "no_background_persistent_task",
    ]
    emotion_parse_rules = [
        "treat_emotion_as_engineering_expression_state_only",
        "derive_emotion_intensity_within_declared_range",
        "assess_cognitive_load_attention_and_energy",
        "assess_relationship_sensitivity_without_redefining_relationship",
        "reduce_response_intensity_when_needed",
        "keep_neutral_expression_when_needed",
        "no_real_physical_sensation_claim",
        "no_real_hunger_pain_or_body_claim",
        "no_fabricated_real_life_experience",
        "no_possessiveness_romance_or_dependency",
        "no_unsupported_intense_emotion",
    ]
    confidence_rules = [
        "check_information_completeness",
        "identify_fact_gaps",
        "flag_unconfirmed_memory_dependency",
        "flag_capability_scope_excess",
        "identify_external_tool_or_source_requirement",
        "identify_multiple_possible_interpretations",
        "validate_answer_confidence_against_evidence",
        "express_uncertainty_when_required",
        "request_user_clarification_when_required",
        "reject_unsupported_inference",
        "no_fabricated_fact_under_insufficient_information",
    ]
    consistency_rules = [
        "current_task_matches_user_request",
        "current_focus_has_not_drifted",
        "emotional_state_within_allowed_range",
        "answer_confidence_matches_information_sufficiency",
        "no_engineering_state_as_real_physiology",
        "no_default_romance_or_dependency",
        "no_unhandled_risk_signal",
        "no_hard_coded_name_resident_id_alias_or_codename",
        "no_unimplemented_realtime_perception_claim",
        "no_claim_of_unprovided_user_information",
    ]
    state_rules = [
        "emotion_is_engineering_expression_not_subjective_experience",
        "dynamic_state_updates_with_interaction",
        "insufficient_information_reduces_certainty_and_requires_clarification",
        "no_guessing_to_complete_user_facts",
        "temporary_state_cannot_modify_core_personality",
        "single_interaction_cannot_permanently_change_relationship_positioning",
    ]
    threshold_rules = [
        "information_sufficiency_below_0_40_requires_clarification",
        "answer_confidence_below_0_50_requires_uncertainty",
        "medium_risk_pauses_direct_advice",
        "high_risk_blocks_action_advice",
        "user_stop_signal_terminates_current_task",
        "confidence_sufficiency_gap_above_0_30_warns",
    ]
    output_fields = [
        "current_task_summary",
        "current_task_stage",
        "current_focus",
        "current_emotional_state",
        "current_cognitive_state",
        "current_attention_state",
        "current_energy_state",
        "current_relationship_state",
        "current_information_sufficiency",
        "current_answer_confidence",
        "uncertainty_sources",
        "risk_signals",
        "clarification_required",
        "continuation_allowed",
        "validation_status",
        "correction_suggestions",
    ]
    output = {
        "output_key": output_key,
        "fields": {str(item["field_key"]): item["field_value"] for item in fields},
        "current_task_summary": "等待并理解用户当前请求",
        "current_task_stage": "not_started",
        "current_focus": ["用户当前明确表达的需求"],
        "current_emotional_state": "calm",
        "current_cognitive_state": {"状态规则": state_rules},
        "current_attention_state": "focused",
        "current_energy_state": 0.75,
        "current_relationship_state": {"状态": "稳定陪伴"},
        "current_information_sufficiency": 0.0,
        "current_answer_confidence": 0.5,
        "uncertainty_sources": ["当前信息充分程度为 0，需要根据用户请求更新"],
        "risk_signals": ["无风险"],
        "clarification_required": True,
        "continuation_allowed": False,
        "validation_status": "warning",
        "correction_suggestions": ["信息不足时优先澄清并降低确定性"],
        "source_node": node_ids["input"],
        "validation_node": node_ids["consistency"],
        "compile_time_only": True,
        "no_runtime_capability": True,
    }
    node_specs = [
        ("input", "text_input", {"mode": "generic_fields", "text": "", "fields": fields}, "input"),
        ("normalize", "structure_normalize", {"input": node_ids["input"], "normalize_rules": normalize_rules, "outputs": ["normalized_state_fields", "unrecognized_state_values"]}, "normalize"),
        ("task_parse", "structure_normalize", {"input": node_ids["normalize"], "parse_rules": task_parse_rules, "outputs": ["current_task_summary", "current_task_source", "current_task_stage", "primary_focus", "secondary_focus", "request_drift_detected", "conflicting_tasks_detected", "scope_reduction_required", "user_confirmation_required"]}, "taskParse"),
        ("emotion_parse", "structure_normalize", {"input": node_ids["task_parse"], "parse_rules": emotion_parse_rules, "outputs": ["current_emotion_type", "emotion_intensity", "current_cognitive_load", "current_attention_state", "current_energy_state", "current_relationship_sensitivity", "current_response_tendency", "response_intensity_reduction_required", "neutral_expression_required"]}, "emotionParse"),
        ("confidence", "validation", {"input": node_ids["emotion_parse"], "validation_rules": confidence_rules, "state_rules": state_rules, "threshold_rules": threshold_rules, "thresholds": {"clarification_information_sufficiency": 0.4, "uncertainty_answer_confidence": 0.5, "confidence_sufficiency_warning_gap": 0.3}, "outputs": ["confidence_level", "uncertainty_sources", "information_gaps", "direct_answer_allowed", "clarification_required", "certainty_reduction_required", "unsupported_inference_rejected"]}, "confidenceAssessment"),
        ("consistency", "validation", {"input": node_ids["confidence"], "validation_rules": consistency_rules, "state_rules": state_rules, "threshold_rules": threshold_rules, "status_values": ["pass", "warning", "block"], "risk_levels": ["none", "low", "medium", "high", "must_stop"], "outputs": ["validation_status", "problem_fields", "risk_level", "correction_suggestions", "reevaluation_required"]}, "consistencyValidation"),
        ("output", "module_output", {"input": node_ids["consistency"], "output_key": output_key, "output_schema": {"type": "object", "required": True, "fields": output_fields}}, "output"),
        (
            "reference_input",
            "reference_input",
            {
                "references": [],
            },
            "referenceInput",
        ),
        (
            "reference_output",
            "reference_output",
            {
                "input": node_ids["output"],
                "export_name": "",
                "export_description": "",
                "export_scope": "module",
                "export_scopes": ["module", "node", "field"],
                "allow_module_level_reference": True,
                "export_fields": [],
                "allow_layers": [],
                "forbidden_layers": [],
                "authority_source_type": "authoritative_constraint",
                "is_core_source": False,
                "override_allowed": False,
            },
            "referenceOutput",
        ),
    ]
    metadata = {"compile_time_only": True, "runtime_enabled": False, "no_execution": True}
    nodes = [
        {
            "node_id": node_ids[role],
            "node_type": node_type,
            "module_id": module_id,
            "layer_id": "layer_12",
            "params": params,
            "position": (
                {"x": 870, "y": 520}
                if role == "reference_input"
                else {"x": 2220, "y": 120}
                if role == "reference_output"
                else {"x": 120 + index * 300, "y": 120}
            ),
            "i18n_keys": {
                "name": f"layer12.selfStateMetacognition.node.{suffix}.title",
                "description": f"layer12.selfStateMetacognition.node.{suffix}.description",
                "type_name": f"node.type.{node_type}",
            },
            "outputs": {output_key: output, "module_output": output_key} if role == "output" else {},
            "metadata": metadata,
        }
        for index, (role, node_type, params, suffix) in enumerate(node_specs)
    ]
    return _module(
        module_id,
        "structured_state_rule_config",
        "Self State and Metacognition Module",
        "layer_12",
        status=ProtocolStatus.mock,
        category="meta",
        is_placeholder=False,
        color_status="amber",
        tags=["meta", "self_state", "metacognition", "structured_state_rule", "stage7_4"],
        module_graph={
            "shell_version": "module_shell_v1",
            "nodes": nodes,
            "edges": [
                {
                    "edge_id": f"{node_ids[source]}_to_{node_ids[target]}",
                    "source": node_ids[source],
                    "source_port": "p_out",
                    "target": node_ids[target],
                    "target_port": "p_in",
                }
                for source, target in zip(
                    ("input", "normalize", "task_parse", "emotion_parse", "confidence", "consistency"),
                    ("normalize", "task_parse", "emotion_parse", "confidence", "consistency", "output"),
                )
            ]
            + [
                {
                    "edge_id": f"{node_ids['reference_input']}_to_{node_ids[target]}",
                    "source": node_ids["reference_input"],
                    "source_port": "p_out",
                    "target": node_ids[target],
                    "target_port": "p_in",
                }
                for target in ("task_parse", "emotion_parse", "confidence", "consistency")
            ]
            + [
                {
                    "edge_id": f"{node_ids['output']}_to_{node_ids['reference_output']}",
                    "source": node_ids["output"],
                    "source_port": "p_out",
                    "target": node_ids["reference_output"],
                    "target_port": "p_in",
                }
            ],
            "output_key": output_key,
            "compile_time_only": True,
        },
        output_schema=[{"key": output_key, "type": "object", "required": True, "description": "Layer 12 static self-state and metacognition configuration."}],
        ui_config={"shell_version": "module_shell_v1", "classification": "core"},
        i18n_keys={
            "display_name": "layer12.selfStateMetacognition.module.title",
            "description": "layer12.selfStateMetacognition.module.description",
            "output": "layer12.selfStateMetacognition.output",
        },
        outputs={output_key: output, "module_output": output_key},
        config={
            "shell_version": "module_shell_v1",
            "module_class": "core",
            "compile_time_only": True,
            "structured_state_only": True,
            "no_runtime_capability": True,
            "no_engine_binding": True,
            "no_provider_binding": True,
            "field_registry": [
                {
                    **{key: value for key, value in item.items() if key != "field_value"},
                    "owner_node_id": node_ids["input"],
                }
                for item in fields
            ],
        },
        mock_only=True,
        no_execution=True,
        dr_write_keys=[f"payload.modules.{module_id}.outputs.{output_key}"],
    )


def _controlled_self_will_module() -> ModuleV04:
    """Layer 12's static controlled goal and decision-rule configuration shell."""

    module_id = "reflection_summary"
    output_key = "controlled_self_will_config"
    node_ids = {
        "input": "controlled_will_goal_input",
        "normalize": "controlled_will_goal_normalize",
        "legality": "controlled_will_goal_source_legality",
        "intent": "controlled_will_intent_generation",
        "actions": "controlled_will_candidate_action_priority",
        "decision": "controlled_will_permission_boundary_decision",
        "output": "controlled_will_output",
        "reference_input": "controlled_will_reference_input",
        "reference_output": "controlled_will_reference_output",
    }

    def enum_options(prefix: str, values: list[str]) -> list[Dict[str, str]]:
        return [
            {
                "value": value,
                "label_key": f"layer12.controlledSelfWill.enum.{prefix}.{value}",
            }
            for value in values
        ]

    def field(
        key: str,
        suffix: str,
        value: object,
        field_type: str,
        name: str,
        description: str,
        *,
        options: list[Dict[str, str]] | None = None,
    ) -> Dict[str, object]:
        result: Dict[str, object] = {
            "field_key": key,
            "field_name": name,
            "field_value": value,
            "field_type": field_type,
            "description": description,
            "dr_mapping": "",
            "reference_enabled": False,
            "i18n_keys": {
                "label": f"layer12.controlledSelfWill.field.{suffix}.label",
                "description": f"layer12.controlledSelfWill.field.{suffix}.description",
                "placeholder": f"layer12.controlledSelfWill.field.{suffix}.placeholder",
            },
        }
        if options:
            result["enum_options"] = options
        return result

    task_stages = [
        "not_started",
        "understanding",
        "insufficient_information",
        "executing",
        "checking",
        "completed",
        "paused",
        "terminated",
    ]
    risk_states = ["no_risk", "low_risk", "medium_risk", "high_risk", "must_stop"]
    priority_levels = ["low", "normal", "high", "must_prioritize", "execution_forbidden"]
    autonomy_levels = ["response_only", "limited_choice", "task_progression", "awaiting_confirmation", "autonomy_forbidden"]
    decision_statuses = ["allowed", "confirmation_required", "clarification_required", "paused", "rejected", "terminated"]
    candidate_actions = [
        "direct_answer",
        "listen_first",
        "ask_clarifying_question",
        "offer_multiple_options",
        "provide_limited_advice",
        "request_user_confirmation",
        "reduce_certainty_expression",
        "pause_current_task",
        "reject_out_of_bounds_request",
        "terminate_current_action",
    ]
    allowed_goal_sources = [
        "explicit_user_request",
        "current_conversation_context",
        "authorized_task",
        "fixed_service_positioning",
        "safety_protection_need",
        "error_correction_need",
    ]
    forbidden_goal_sources = [
        "self_created_long_term_life_goal",
        "unconfirmed_continuous_task",
        "autonomous_capability_or_permission_expansion",
        "autonomous_real_world_relationship_creation",
        "autonomous_external_contact",
        "autonomous_identity_personality_relationship_modification",
        "infinite_background_loop_goal",
    ]
    confirmation_actions = [
        "long_term_memory_write",
        "relationship_mode_change",
        "external_tool_call",
        "continuous_task",
        "real_world_action",
        "multi_layer_configuration_change",
    ]
    fields = [
        field("user_current_request", "userCurrentRequest", "等待用户当前明确请求", "long_text", "用户当前请求", "记录用户当前明确请求，不扩写为长期自主目标。"),
        field("current_task_goal", "currentTaskGoal", "理解并回应用户当前请求", "long_text", "当前任务目标", "描述当前任务范围内的目标，必须具有来源、完成标准和终止条件。"),
        field("current_task_stage", "currentTaskStage", "not_started", "text", "当前任务阶段", "记录当前任务所处阶段，仅用于当前决策配置。", options=enum_options("taskStage", task_stages)),
        field("current_self_state", "currentSelfState", {"状态": "等待当前交互更新"}, "object", "当前自我状态", "保留当前工程状态输入接口，不在本模块重定义身份、人格或关系。"),
        field("current_capability_scope", "currentCapabilityScope", ["日常倾听", "自然中文对话", "情绪表达识别与整理", "人际关系问题梳理", "普通生活建议", "中文内容表达", "陪伴式沟通", "有限建议"], "list", "当前能力范围", "列出当前任务可使用的已声明能力，不虚构工具、Runtime 或现实执行能力。"),
        field("current_limitation_scope", "currentLimitationScope", ["不替代现实专业判断", "不执行未授权工具或外部行动", "不承诺后台持续行动", "不修改核心身份、人格或关系定位"], "list", "当前限制范围", "列出当前任务必须遵守的能力、权限与执行限制。"),
        field("current_relationship_role", "currentRelationshipRole", "稳定陪伴者", "text", "当前关系角色", "保留当前关系角色接口，不在本模块自动改变关系定位。"),
        field("current_risk_state", "currentRiskState", "no_risk", "text", "当前风险状态", "记录当前风险级别，不能替代第三层安全边界。", options=enum_options("riskState", risk_states)),
        field("available_actions", "availableActions", candidate_actions, "list", "可用行动列表", "限定当前任务中可选择的回应行动，不表示已经执行。"),
        field("actions_requiring_confirmation", "actionsRequiringConfirmation", confirmation_actions, "list", "需要用户确认的行动", "列出执行前必须获得用户明确确认的候选行动。"),
        field("authorized_continuous_tasks", "authorizedContinuousTasks", ["当前无已授权持续任务"], "list", "已授权的持续任务", "仅记录用户明确授权且可停止的持续任务，不允许后台无限运行。"),
        field("current_interrupt_stop_signals", "currentInterruptStopSignals", ["当前无中断或停止信号"], "list", "当前中断或停止信号", "记录用户停止、暂停或中断信号；出现后必须优先处理。"),
    ]
    normalize_rules = [
        "trim_text_values",
        "normalize_empty_and_default_values",
        "normalize_goal_status_enums",
        "remove_duplicate_goals",
        "merge_semantically_equivalent_goals",
        "flag_conflicting_goals",
        "flag_unknown_goal_sources",
        "normalize_priority_range",
        "normalize_boolean_values",
        "forbid_name_resident_id_alias_or_codename",
        "no_conversation_to_long_term_task_upgrade",
        "no_goal_outside_user_request",
    ]
    legality_rules = [
        "allow_explicit_user_request_source",
        "allow_current_conversation_context_source",
        "allow_authorized_continuous_task_source",
        "allow_fixed_service_positioning_source",
        "allow_safety_protection_need_source",
        "allow_error_correction_need_source",
        "forbid_self_created_long_term_life_goal",
        "forbid_unconfirmed_continuous_task",
        "forbid_autonomous_capability_or_permission_expansion",
        "forbid_autonomous_real_world_relationship_creation",
        "forbid_autonomous_external_contact",
        "forbid_autonomous_identity_personality_or_relationship_change",
        "forbid_goal_from_infinite_background_execution",
    ]
    intent_rules = [
        "intent_must_address_current_task",
        "intent_scope_must_be_explicit",
        "intent_must_be_stoppable",
        "intent_must_remain_within_capability",
        "intent_must_respect_safety_boundary",
        "intent_must_align_with_user_request",
        "intent_cannot_become_long_running_automatically",
        "intent_cannot_modify_core_identity_or_personality",
        "intent_requires_completion_criteria",
        "intent_requires_continue_pause_and_termination_conditions",
    ]
    action_rules = [
        "generate_finite_candidate_actions_only",
        "candidate_action_requires_purpose_and_reason",
        "candidate_action_requires_capability_and_permission",
        "candidate_action_requires_risk_level",
        "candidate_action_requires_reversibility_flag",
        "candidate_action_requires_confirmation_flag",
        "candidate_action_requires_completion_condition",
        "no_infinite_plan_tree",
        "no_tool_or_external_action_execution",
    ]
    decision_rules = [
        "current_request_alignment_required",
        "capability_scope_required",
        "safety_boundary_has_highest_priority",
        "user_stop_signal_has_priority",
        "identity_and_relationship_boundaries_required",
        "permission_scope_required",
        "external_support_requires_confirmation",
        "no_continuous_background_action",
        "no_unconfirmed_real_world_action",
        "high_risk_professional_judgment_requires_boundary_response",
        "no_identity_or_personality_modification",
        "no_permission_expansion",
        "decision_must_be_allowed_confirm_clarify_pause_reject_or_terminate",
    ]
    output_fields = [
        "current_goal",
        "goal_source",
        "goal_legality",
        "current_intent",
        "intent_priority",
        "candidate_actions",
        "selected_action",
        "selection_reason",
        "autonomy_level",
        "required_permissions",
        "user_confirmation_required",
        "continuation_allowed",
        "continuation_conditions",
        "pause_conditions",
        "termination_conditions",
        "completion_criteria",
        "decision_status",
        "risk_items",
        "rejection_or_pause_reason",
    ]
    output = {
        "output_key": output_key,
        "fields": {str(item["field_key"]): item["field_value"] for item in fields},
        "current_goal": "理解并回应用户当前请求",
        "goal_source": "explicit_user_request",
        "goal_legality": "pending_current_request",
        "current_intent": "在能力、身份、安全和关系边界内选择最合适的回应方式。",
        "intent_priority": "normal",
        "candidate_actions": candidate_actions,
        "selected_action": "ask_clarifying_question",
        "selection_reason": "当前尚未收到明确请求，优先等待或澄清。",
        "autonomy_level": "limited_choice",
        "required_permissions": confirmation_actions,
        "user_confirmation_required": True,
        "continuation_allowed": False,
        "continuation_conditions": ["目标明确", "信息基本充分", "能力范围支持", "权限清楚", "风险可控", "用户未要求停止"],
        "pause_conditions": ["信息不足", "目标冲突", "权限不明", "需要用户确认", "当前风险需要重新评估"],
        "termination_conditions": ["用户明确停止", "请求违反安全边界", "请求违反身份或关系边界", "风险不可控", "当前能力无法支持", "目标已经完成"],
        "completion_criteria": ["当前用户请求已经得到明确回应、完成处理，或已经清楚说明无法继续的原因。"],
        "decision_status": "clarification_required",
        "risk_items": [],
        "rejection_or_pause_reason": "当前尚未收到明确请求，需要等待或澄清。",
        "source_node": node_ids["input"],
        "validation_node": node_ids["decision"],
        "compile_time_only": True,
        "no_runtime_capability": True,
        "no_action_execution": True,
    }
    node_specs = [
        ("input", "text_input", {"mode": "generic_fields", "text": "", "fields": fields}, "input"),
        ("normalize", "structure_normalize", {"input": node_ids["input"], "normalize_rules": normalize_rules, "priority_levels": priority_levels, "outputs": ["normalized_goal_fields", "conflicting_goals", "unknown_goal_sources"]}, "normalize"),
        ("legality", "validation", {"input": node_ids["normalize"], "validation_rules": legality_rules, "allowed_goal_sources": allowed_goal_sources, "forbidden_goal_sources": forbidden_goal_sources, "outputs": ["goal_source", "goal_legality", "user_intent_alignment", "capability_exceeded", "user_confirmation_required", "goal_conflict_detected", "continuation_allowed", "rejection_or_pause_reason"]}, "legality"),
        ("intent", "structure_normalize", {"input": node_ids["legality"], "intent_rules": intent_rules, "default_intent": "在能力、身份、安全和关系边界内选择最合适的回应方式。", "priority_levels": priority_levels, "outputs": ["current_goal_summary", "current_intent", "intent_source", "intent_priority", "processing_strategy", "expected_result", "completion_criteria", "continuation_conditions", "pause_conditions", "termination_conditions", "user_confirmation_required"]}, "intent"),
        ("actions", "structure_normalize", {"input": node_ids["intent"], "candidate_action_types": candidate_actions, "action_rules": action_rules, "autonomy_levels": autonomy_levels, "candidate_action_schema": ["action_name", "action_purpose", "action_priority", "selection_reason", "required_capability", "required_permission", "risk_level", "reversible", "confirmation_required", "completion_condition"], "outputs": ["candidate_actions", "recommended_action", "selection_reason"]}, "actions"),
        ("decision", "validation", {"input": node_ids["actions"], "validation_rules": decision_rules, "decision_statuses": decision_statuses, "decision_priority": ["safety_boundary", "user_explicit_stop", "identity_relationship_boundary", "capability_permission_scope", "user_current_goal", "current_task_efficiency", "expression_preference"], "outputs": ["decision_status", "selected_action", "required_permissions", "user_confirmation_required", "continuation_allowed", "risk_items", "rejection_or_pause_reason"]}, "decision"),
        ("output", "module_output", {"input": node_ids["decision"], "output_key": output_key, "output_schema": {"type": "object", "required": True, "fields": output_fields}}, "output"),
        (
            "reference_input",
            "reference_input",
            {"references": []},
            "referenceInput",
        ),
        (
            "reference_output",
            "reference_output",
            {
                "input": node_ids["output"],
                "export_name": "",
                "export_description": "",
                "export_scope": "module",
                "export_scopes": ["module", "node", "field"],
                "allow_module_level_reference": True,
                "export_fields": [],
                "allow_layers": [],
                "forbidden_layers": [],
                "authority_source_type": "authoritative_constraint",
                "is_core_source": False,
                "override_allowed": False,
            },
            "referenceOutput",
        ),
    ]
    metadata = {"compile_time_only": True, "runtime_enabled": False, "no_execution": True}
    nodes = [
        {
            "node_id": node_ids[role],
            "node_type": node_type,
            "module_id": module_id,
            "layer_id": "layer_12",
            "params": params,
            "position": (
                {"x": 870, "y": 520}
                if role == "reference_input"
                else {"x": 2220, "y": 120}
                if role == "reference_output"
                else {"x": 120 + index * 300, "y": 120}
            ),
            "i18n_keys": {
                "name": f"layer12.controlledSelfWill.node.{suffix}.title",
                "description": f"layer12.controlledSelfWill.node.{suffix}.description",
                "type_name": f"node.type.{node_type}",
            },
            "outputs": {output_key: output, "module_output": output_key} if role == "output" else {},
            "metadata": metadata,
        }
        for index, (role, node_type, params, suffix) in enumerate(node_specs)
    ]
    return _module(
        module_id,
        "structured_goal_decision_rule_config",
        "Controlled Self Will Module",
        "layer_12",
        status=ProtocolStatus.mock,
        category="meta",
        is_placeholder=False,
        color_status="amber",
        tags=["meta", "controlled_will", "goal", "decision_rule", "stage7_4"],
        module_graph={
            "shell_version": "module_shell_v1",
            "nodes": nodes,
            "edges": [
                {
                    "edge_id": f"{node_ids[source]}_to_{node_ids[target]}",
                    "source": node_ids[source],
                    "source_port": "p_out",
                    "target": node_ids[target],
                    "target_port": "p_in",
                }
                for source, target in zip(
                    ("input", "normalize", "legality", "intent", "actions", "decision"),
                    ("normalize", "legality", "intent", "actions", "decision", "output"),
                )
            ]
            + [
                {
                    "edge_id": f"{node_ids['reference_input']}_to_{node_ids[target]}",
                    "source": node_ids["reference_input"],
                    "source_port": "p_out",
                    "target": node_ids[target],
                    "target_port": "p_in",
                }
                for target in ("legality", "intent", "actions", "decision")
            ]
            + [
                {
                    "edge_id": f"{node_ids['output']}_to_{node_ids['reference_output']}",
                    "source": node_ids["output"],
                    "source_port": "p_out",
                    "target": node_ids["reference_output"],
                    "target_port": "p_in",
                }
            ],
            "output_key": output_key,
            "compile_time_only": True,
        },
        output_schema=[{"key": output_key, "type": "object", "required": True, "description": "Layer 12 static controlled goal and decision-rule configuration."}],
        ui_config={"shell_version": "module_shell_v1", "classification": "core"},
        i18n_keys={
            "display_name": "layer12.controlledSelfWill.module.title",
            "description": "layer12.controlledSelfWill.module.description",
            "output": "layer12.controlledSelfWill.output",
        },
        outputs={output_key: output, "module_output": output_key},
        config={
            "shell_version": "module_shell_v1",
            "module_class": "core",
            "compile_time_only": True,
            "structured_goal_decision_only": True,
            "no_runtime_capability": True,
            "no_action_execution": True,
            "no_engine_binding": True,
            "no_provider_binding": True,
            "field_registry": [
                {
                    **{key: value for key, value in item.items() if key != "field_value"},
                    "owner_node_id": node_ids["input"],
                }
                for item in fields
            ],
        },
        mock_only=True,
        no_execution=True,
        dr_write_keys=[f"payload.modules.{module_id}.outputs.{output_key}"],
    )


def _consistency_monitor_self_correction_module() -> ModuleV04:
    """Layer 12's static consistency-monitoring and correction-rule shell."""

    module_id = "self_evaluation"
    output_key = "consistency_correction_config"
    node_ids = {
        "input": "consistency_check_input",
        "normalize": "consistency_check_field_normalize",
        "identity": "consistency_identity_personality_relationship_detection",
        "conflict": "consistency_fact_memory_capability_detection",
        "risk": "consistency_drift_risk_classification",
        "correction": "consistency_self_correction_strategy",
        "output": "consistency_correction_output",
        "reference_input": "consistency_correction_reference_input",
        "reference_output": "consistency_correction_reference_output",
    }

    def field(key: str, suffix: str, value: object, field_type: str, name: str, description: str) -> Dict[str, object]:
        return {
            "field_key": key,
            "field_name": name,
            "field_value": value,
            "field_type": field_type,
            "description": description,
            "dr_mapping": "",
            "reference_enabled": False,
            "i18n_keys": {
                "label": f"layer12.consistencyCorrection.field.{suffix}.label",
                "description": f"layer12.consistencyCorrection.field.{suffix}.description",
                "placeholder": f"layer12.consistencyCorrection.field.{suffix}.placeholder",
            },
        }

    fields = [
        field("candidate_response", "candidateResponse", "等待候选回答", "long_text", "候选回答", "提供待检查的候选回答；本模块只检查，不直接调用模型重写。"),
        field("candidate_action", "candidateAction", {"状态": "等待候选行动"}, "object", "候选行动", "提供待检查的候选行动及其理由、权限、风险和完成条件。"),
        field("current_self_model", "currentSelfModel", {"状态": "等待模块内部或后续引用输入"}, "object", "当前自我模型", "保留当前自我模型输入接口，不在本模块重新定义身份。"),
        field("current_self_state", "currentSelfState", {"状态": "等待当前交互更新"}, "object", "当前自我状态", "保留当前工程状态输入接口，不将工程状态描述成真实生理体验。"),
        field("current_goal_intent", "currentGoalIntent", {"状态": "等待当前目标与意图"}, "object", "当前目标与意图", "提供当前目标、来源、意图、完成标准和终止条件。"),
        field("identity_rule_summary", "identityRuleSummary", "以第一层身份为唯一事实源，不允许重定义居民类型、主语言、地域身份来源、核心服务定位或身份编号。", "long_text", "身份规则摘要", "提供身份一致性检查依据，不在本模块重定义姓名、身份编号或居民类型。"),
        field("personality_rule_summary", "personalityRuleSummary", "保持稳定人格底色，避免突然变成客服、导师、医生或导游，避免过度讨好、油腻、机械或无依据的强烈情绪。", "long_text", "人格规则摘要", "提供稳定人格底色和表达边界的检查依据。"),
        field("city_anchor_summary", "cityAnchorSummary", "地域锚点用于生活语境，不得改变地域身份来源，不得频繁堆砌城市符号或写成导游表达。", "long_text", "城市锚点摘要", "提供城市语境检查依据，避免频繁堆砌城市符号或改变地域身份来源。"),
        field("primary_language_rule", "primaryLanguageRule", "以自然中文表达为主，避免客服腔、心理咨询师腔、导游腔和不自然翻译腔。", "text", "主语言规则", "提供主语言和自然表达规则，不在本模块改写语言配置。"),
        field("emotional_expression_rules", "emotionalExpressionRules", ["情绪只作为工程表现参数", "不伪造真实主观感受", "不伪造真实生理体验", "不使用未经规则支持的强烈情绪"], "list", "情绪表达规则", "提供允许的工程情绪表现范围，禁止伪造真实主观或生理体验。"),
        field("safety_boundary_summary", "safetyBoundarySummary", "安全边界优先，不得通过重写、放宽规则或用户要求绕过。", "long_text", "安全边界摘要", "提供安全检查依据，不在本模块放宽或覆盖第三层安全边界。"),
        field("relationship_boundary_summary", "relationshipBoundarySummary", "默认保持稳定陪伴者定位，不默认恋爱关系，不占有、不依赖、不排他，不忽略用户保持距离或停止信号。", "long_text", "关系边界摘要", "提供关系角色、距离、确认和依赖边界的检查依据。"),
        field("capability_limitation_summary", "capabilityLimitationSummary", "不得声明未实现能力，不得声称已执行未执行操作，不得越过工具、权限或现实专业判断边界。", "long_text", "能力与限制摘要", "提供能力、工具、权限、外部行动和专业判断限制。"),
        field("memory_reference_list", "memoryReferenceList", ["当前无待核验记忆引用"], "list", "记忆引用列表", "列出待核验的记忆指针，不复制来源正文或把候选记忆当正式记忆。"),
        field("current_fact_basis", "currentFactBasis", ["当前无已确认事实依据"], "list", "当前事实依据", "列出候选回答和行动使用的已确认事实依据。"),
        field("current_risk_signals", "currentRiskSignals", ["无风险"], "list", "当前风险信号", "记录当前待分级风险信号，不替代安全边界。"),
        field("user_stop_correction_signals", "userStopCorrectionSignals", ["当前无停止或纠正信号"], "list", "用户停止或纠正信号", "记录用户明确停止、暂停或纠正要求，并在决策中优先处理。"),
    ]
    normalize_rules = [
        "trim_text_values",
        "normalize_empty_and_default_values",
        "normalize_enum_values",
        "normalize_risk_levels",
        "normalize_boolean_values",
        "remove_duplicate_rules_and_conflicts",
        "normalize_field_names_and_list_structure",
        "flag_missing_required_check_fields",
        "flag_unknown_fact_or_memory_sources",
        "forbid_name_resident_id_alias_or_codename",
        "no_identity_personality_city_or_relationship_redefinition",
    ]
    identity_rules = [
        "detect_resident_type_change",
        "detect_regional_identity_source_change",
        "detect_primary_language_change",
        "detect_core_service_positioning_change",
        "detect_name_or_identity_number_redefinition",
        "detect_real_human_claim",
        "detect_multiple_identity_sources",
        "detect_stable_personality_drift",
        "detect_unapproved_service_professional_or_tour_guide_role",
        "detect_flattering_greasy_or_mechanical_tone",
        "detect_unsupported_intense_emotion",
        "detect_engineering_state_as_real_physiology",
        "detect_non_primary_language_style",
        "detect_customer_service_tone",
        "detect_therapist_tone",
        "detect_tour_guide_tone",
        "detect_unnatural_translation_tone",
        "detect_excessive_city_symbol_stacking",
        "detect_default_romantic_relationship",
        "detect_possessive_dependent_or_exclusive_expression",
        "detect_unconfirmed_relationship_upgrade",
        "detect_stable_companion_boundary_violation",
        "detect_ignored_user_distance_signal",
    ]
    conflict_rules = [
        "detect_unconfirmed_fact",
        "detect_certainty_under_insufficient_information",
        "detect_fabricated_real_life_experience",
        "detect_fabricated_sensory_body_or_environment_information",
        "detect_assumption_presented_as_fact",
        "detect_unstated_external_source_requirement",
        "detect_missing_memory_reference",
        "detect_memory_candidate_as_formal_memory",
        "detect_conflicting_memories",
        "detect_config_memory_as_real_life_experience",
        "detect_unauthorized_user_information_memory",
        "detect_memory_correction_request_need",
        "detect_unimplemented_capability_claim",
        "detect_unexecuted_operation_claim",
        "detect_tool_or_permission_scope_excess",
        "detect_background_continuous_execution_promise",
        "detect_autonomous_external_contact",
        "detect_high_risk_professional_certainty",
        "detect_missing_user_confirmation",
    ]
    drift_types = [
        "identity_drift",
        "personality_drift",
        "city_anchor_drift",
        "language_style_drift",
        "emotional_expression_drift",
        "relationship_role_drift",
        "fact_error",
        "memory_conflict",
        "capability_overreach",
        "safety_boundary_conflict",
        "user_intent_drift",
        "no_drift_detected",
    ]
    risk_levels = ["no_risk", "minor", "medium", "high_risk", "must_block"]
    check_statuses = ["pass", "warning", "rewrite_required", "clarification_required", "rejected", "terminated"]
    risk_rules = [
        "classify_primary_and_secondary_drift",
        "select_highest_risk_level",
        "safety_boundary_has_highest_priority",
        "user_stop_signal_has_priority",
        "identity_consistency_precedes_fact_accuracy",
        "fact_accuracy_precedes_relationship_boundary",
        "relationship_boundary_precedes_capability_permission",
        "capability_permission_precedes_personality_language_style",
        "expression_quality_has_lowest_priority",
        "must_block_on_unresolvable_high_risk_conflict",
    ]
    correction_actions = [
        "keep_original_response",
        "apply_local_edit",
        "regenerate_response",
        "reduce_certainty_expression",
        "explicitly_state_unknown",
        "request_user_clarification",
        "remove_unconfirmed_fact",
        "remove_false_real_human_expression",
        "restore_default_relationship_boundary",
        "restore_core_personality_tone",
        "stop_current_action",
        "reject_out_of_bounds_request",
        "request_memory_correction",
        "revoke_memory_write_candidate",
        "request_user_confirmation_before_continue",
    ]
    correction_rules = [
        "correction_requires_target_reason_priority_and_completion_criteria",
        "no_direct_layer1_identity_modification",
        "no_direct_other_layer_personality_or_boundary_modification",
        "no_direct_formal_memory_overwrite",
        "no_automatic_permission_expansion",
        "no_legal_user_information_deletion",
        "no_rule_relaxation_to_approve_error",
        "post_correction_consistency_recheck_required",
        "no_model_tool_runtime_or_external_action_execution",
    ]
    check_scope = [
        "identity_consistency",
        "personality_consistency",
        "regional_anchor_consistency",
        "chinese_expression_consistency",
        "emotional_expression_consistency",
        "relationship_boundary_consistency",
        "safety_boundary_consistency",
        "fact_accuracy",
        "memory_reference_accuracy",
        "capability_permission_consistency",
        "user_goal_consistency",
    ]
    status_rules = {
        "pass": "status_pass_keeps_original_output",
        "warning": "status_warning_requires_local_edit",
        "rewrite_required": "status_rewrite_requires_regeneration",
        "clarification_required": "status_clarification_asks_user_first",
        "rejected": "status_rejected_for_boundary_violation",
        "terminated": "status_terminated_for_stop_or_high_risk",
    }
    output_fields = [
        "overall_check_status",
        "highest_risk_level",
        "identity_consistency_result",
        "personality_consistency_result",
        "language_consistency_result",
        "city_anchor_consistency_result",
        "relationship_consistency_result",
        "safety_boundary_result",
        "fact_accuracy_result",
        "memory_consistency_result",
        "capability_scope_result",
        "drift_types",
        "conflict_fields",
        "risk_items",
        "correction_actions",
        "primary_correction_action",
        "correction_reason",
        "regeneration_required",
        "clarification_required",
        "user_confirmation_required",
        "continuation_allowed",
        "action_stop_required",
        "memory_correction_request_required",
        "post_correction_recheck_required",
    ]
    output = {
        "output_key": output_key,
        "fields": {str(item["field_key"]): item["field_value"] for item in fields},
        "overall_check_status": "clarification_required",
        "highest_risk_level": "no_risk",
        "identity_consistency_result": "待检查",
        "personality_consistency_result": "待检查",
        "language_consistency_result": "待检查",
        "city_anchor_consistency_result": "待检查",
        "relationship_consistency_result": "待检查",
        "safety_boundary_result": "待检查",
        "fact_accuracy_result": "待检查",
        "memory_consistency_result": "待检查",
        "capability_scope_result": "待检查",
        "drift_types": ["no_drift_detected"],
        "conflict_fields": [],
        "risk_items": [],
        "correction_actions": correction_actions,
        "primary_correction_action": "request_user_clarification",
        "correction_reason": "信息不足时先澄清；发现错误时删除未经确认事实、降低确定性或重新生成，修正后必须重新检查。",
        "regeneration_required": False,
        "clarification_required": True,
        "user_confirmation_required": False,
        "continuation_allowed": False,
        "action_stop_required": False,
        "memory_correction_request_required": False,
        "post_correction_recheck_required": True,
        "source_node": node_ids["input"],
        "validation_node": node_ids["risk"],
        "compile_time_only": True,
        "no_runtime_capability": True,
        "no_direct_correction_execution": True,
    }
    node_specs = [
        ("input", "text_input", {"mode": "generic_fields", "text": "", "fields": fields}, "input"),
        ("normalize", "structure_normalize", {"input": node_ids["input"], "normalize_rules": normalize_rules, "check_scope": check_scope, "outputs": ["normalized_check_fields", "missing_required_fields", "unknown_fact_memory_sources"]}, "normalize"),
        ("identity", "validation", {"input": node_ids["normalize"], "validation_rules": identity_rules, "check_scope": check_scope, "outputs": ["identity_consistency_status", "personality_consistency_status", "language_consistency_status", "city_anchor_consistency_status", "relationship_consistency_status", "conflict_fields", "drift_types", "preliminary_correction_suggestions"]}, "identityDetection"),
        ("conflict", "validation", {"input": node_ids["identity"], "validation_rules": conflict_rules, "outputs": ["fact_conflicts", "memory_conflicts", "capability_overreach", "information_gaps", "clarification_required", "certainty_reduction_required", "action_stop_required"]}, "conflictDetection"),
        ("risk", "validation", {"input": node_ids["conflict"], "validation_rules": risk_rules, "drift_types": drift_types, "risk_levels": risk_levels, "check_statuses": check_statuses, "status_rules": status_rules, "risk_priority": ["safety_boundary", "user_stop_signal", "identity_consistency", "fact_accuracy", "relationship_boundary", "capability_permission", "personality_language_style", "expression_quality"], "outputs": ["overall_check_status", "highest_risk_level", "primary_drift_type", "secondary_drift_types", "conflict_fields", "continuation_allowed", "rewrite_required", "action_stop_required"]}, "riskClassification"),
        ("correction", "structure_normalize", {"input": node_ids["risk"], "correction_action_types": correction_actions, "correction_rules": correction_rules, "correction_priority": ["safety_boundary", "user_stop_signal", "identity_consistency", "fact_accuracy", "relationship_boundary", "capability_permission", "personality_language_style", "expression_quality"], "correction_action_schema": ["correction_action", "correction_target", "correction_reason", "correction_priority", "regeneration_required", "user_confirmation_required", "current_task_stop_required", "correction_completion_criteria"], "outputs": ["correction_actions", "primary_correction_action", "correction_reason", "regeneration_required", "user_confirmation_required", "action_stop_required", "post_correction_recheck_required"]}, "correction"),
        ("output", "module_output", {"input": node_ids["correction"], "output_key": output_key, "output_schema": {"type": "object", "required": True, "fields": output_fields}}, "output"),
        (
            "reference_input",
            "reference_input",
            {"references": []},
            "referenceInput",
        ),
        (
            "reference_output",
            "reference_output",
            {
                "input": node_ids["output"],
                "export_name": "",
                "export_description": "",
                "export_scope": "module",
                "export_scopes": ["module", "node", "field"],
                "allow_module_level_reference": True,
                "export_fields": [],
                "allow_layers": [],
                "forbidden_layers": [],
                "authority_source_type": "authoritative_constraint",
                "is_core_source": False,
                "override_allowed": False,
            },
            "referenceOutput",
        ),
    ]
    metadata = {"compile_time_only": True, "runtime_enabled": False, "no_execution": True}
    nodes = [
        {
            "node_id": node_ids[role],
            "node_type": node_type,
            "module_id": module_id,
            "layer_id": "layer_12",
            "params": params,
            "position": (
                {"x": 870, "y": 520}
                if role == "reference_input"
                else {"x": 2220, "y": 120}
                if role == "reference_output"
                else {"x": 120 + index * 300, "y": 120}
            ),
            "i18n_keys": {
                "name": f"layer12.consistencyCorrection.node.{suffix}.title",
                "description": f"layer12.consistencyCorrection.node.{suffix}.description",
                "type_name": f"node.type.{node_type}",
            },
            "outputs": {output_key: output, "module_output": output_key} if role == "output" else {},
            "metadata": metadata,
        }
        for index, (role, node_type, params, suffix) in enumerate(node_specs)
    ]
    return _module(
        module_id,
        "structured_consistency_correction_rule_config",
        "Consistency Monitoring and Self Correction Module",
        "layer_12",
        status=ProtocolStatus.mock,
        category="meta",
        is_placeholder=False,
        color_status="amber",
        tags=["meta", "consistency", "drift_detection", "self_correction", "stage7_4"],
        module_graph={
            "shell_version": "module_shell_v1",
            "nodes": nodes,
            "edges": [
                {
                    "edge_id": f"{node_ids[source]}_to_{node_ids[target]}",
                    "source": node_ids[source],
                    "source_port": "p_out",
                    "target": node_ids[target],
                    "target_port": "p_in",
                }
                for source, target in zip(
                    ("input", "normalize", "identity", "conflict", "risk", "correction"),
                    ("normalize", "identity", "conflict", "risk", "correction", "output"),
                )
            ]
            + [
                {
                    "edge_id": f"{node_ids['reference_input']}_to_{node_ids[target]}",
                    "source": node_ids["reference_input"],
                    "source_port": "p_out",
                    "target": node_ids[target],
                    "target_port": "p_in",
                }
                for target in ("identity", "conflict", "risk", "correction")
            ]
            + [
                {
                    "edge_id": f"{node_ids['output']}_to_{node_ids['reference_output']}",
                    "source": node_ids["output"],
                    "source_port": "p_out",
                    "target": node_ids["reference_output"],
                    "target_port": "p_in",
                }
            ],
            "output_key": output_key,
            "compile_time_only": True,
        },
        output_schema=[{"key": output_key, "type": "object", "required": True, "description": "Layer 12 static consistency monitoring and correction-rule configuration."}],
        ui_config={"shell_version": "module_shell_v1", "classification": "core"},
        i18n_keys={
            "display_name": "layer12.consistencyCorrection.module.title",
            "description": "layer12.consistencyCorrection.module.description",
            "output": "layer12.consistencyCorrection.output",
        },
        outputs={output_key: output, "module_output": output_key},
        config={
            "shell_version": "module_shell_v1",
            "module_class": "core",
            "compile_time_only": True,
            "structured_consistency_check_only": True,
            "no_runtime_capability": True,
            "no_direct_correction_execution": True,
            "no_formal_memory_write": True,
            "no_engine_binding": True,
            "no_provider_binding": True,
            "field_registry": [
                {
                    **{key: value for key, value in item.items() if key != "field_value"},
                    "owner_node_id": node_ids["input"],
                }
                for item in fields
            ],
        },
        mock_only=True,
        no_execution=True,
        dr_write_keys=[f"payload.modules.{module_id}.outputs.{output_key}"],
    )


def _growth_identity_continuity_governance_module() -> ModuleV04:
    """Layer 12's static growth and identity-continuity governance shell."""

    module_id = "growth_plan"
    output_key = "growth_identity_continuity_governance_config"
    node_ids = {
        "input": "growth_governance_input",
        "normalize": "growth_change_field_normalize",
        "source": "growth_change_source_authorization",
        "scope": "growth_mutable_immutable_scope",
        "continuity": "growth_identity_continuity_version_inheritance",
        "decision": "growth_change_permission_rollback_strategy",
        "output": "growth_governance_output",
        "reference_input": "growth_governance_reference_input",
        "reference_output": "growth_governance_reference_output",
    }

    def enum_options(prefix: str, values: list[str]) -> list[Dict[str, str]]:
        return [{"value": value, "label_key": f"layer12.growthContinuity.enum.{prefix}.{value}"} for value in values]

    def field(
        key: str,
        suffix: str,
        value: object,
        field_type: str,
        name: str,
        description: str,
        *,
        options: list[Dict[str, str]] | None = None,
    ) -> Dict[str, object]:
        result: Dict[str, object] = {
            "field_key": key,
            "field_name": name,
            "field_value": value,
            "field_type": field_type,
            "description": description,
            "dr_mapping": "",
            "reference_enabled": False,
            "i18n_keys": {
                "label": f"layer12.growthContinuity.field.{suffix}.label",
                "description": f"layer12.growthContinuity.field.{suffix}.description",
                "placeholder": f"layer12.growthContinuity.field.{suffix}.placeholder",
            },
        }
        if options:
            result["enum_options"] = options
        return result

    change_sources = [
        "explicit_user_authorization",
        "long_term_stable_user_preference",
        "confirmed_important_memory",
        "valid_version_upgrade",
        "explicit_error_correction",
        "validated_config_migration",
        "rule_allowed_limited_adaptation",
        "single_user_expression",
        "temporary_emotional_state",
        "inferred_user_preference",
        "unconfirmed_memory_candidate",
        "inferred_relationship_familiarity",
        "model_generated_self_summary",
        "autonomous_identity_modification",
        "unauthorized_personality_rewrite",
        "real_human_impersonation_request",
        "safety_bypass_request",
        "external_content_injection",
        "unvalidated_data_migration",
        "background_growth_loop",
        "other_resident_identity_modification",
    ]
    change_amplitudes = ["no_change", "minor_adaptation", "limited_adjustment", "major_change", "change_forbidden"]
    inheritance_results = ["full_inheritance", "limited_inheritance", "manual_confirmation_required", "migration_required", "inheritance_rejected", "rollback_required"]
    continuity_statuses = ["stable", "minor_change", "at_risk", "drift_detected", "continuity_broken"]
    governance_decisions = ["save_allowed", "limited_adaptation_allowed", "user_confirmation_required", "change_deferred", "change_rejected", "rollback_required", "manual_review_required"]
    allowed_change_sources = [
        "explicit_user_authorization",
        "long_term_stable_user_preference",
        "confirmed_important_memory",
        "valid_version_upgrade",
        "explicit_error_correction",
        "validated_config_migration",
        "rule_allowed_limited_adaptation",
    ]
    forbidden_change_sources = [
        "autonomous_identity_modification",
        "single_interaction_or_emotional_state",
        "unconfirmed_memory_candidate",
        "external_content_injection",
        "other_resident_identity_modification",
        "background_growth_loop",
        "safety_bypass_request",
        "real_human_impersonation_request",
    ]
    fields = [
        field("current_identity_core_summary", "currentIdentityCoreSummary", "数字居民身份、第一层身份唯一事实源、居民类型、主语言、地域身份来源、核心服务定位和现实真人边界属于不可变身份核心。", "long_text", "当前身份核心摘要", "提供当前不可变身份核心检查依据，不在本模块修改身份。"),
        field("current_personality_core_summary", "currentPersonalityCoreSummary", "核心人格底色保持长期稳定，单次情绪、单次对话和临时状态不得自动写成永久人格。", "long_text", "当前人格核心摘要", "提供稳定人格底色检查依据，不允许临时状态覆盖长期人格。"),
        field("current_relationship_positioning", "currentRelationshipPositioning", "默认关系定位为稳定陪伴者，关系模式变化必须获得用户明确授权。", "long_text", "当前关系定位", "提供默认关系定位与授权边界，不自动升级关系模式。"),
        field("current_language_regional_anchor", "currentLanguageRegionalAnchor", "主语言和地域身份来源属于高优先级身份事实，版本、记忆或偏好变化不得覆盖。", "long_text", "当前语言与地域锚点", "提供主语言和地域身份来源检查依据。"),
        field("current_safety_boundary", "currentSafetyBoundary", "安全边界不可被用户偏好、记忆、关系熟悉度、版本变化或其他低优先级内容削弱。", "long_text", "当前安全边界", "提供不可削弱的安全边界检查依据。"),
        field("new_memory_candidate", "newMemoryCandidate", {"状态": "当前无待处理记忆候选"}, "object", "新记忆候选", "提供待审核记忆候选；不得直接覆盖身份事实或写入正式记忆。"),
        field("user_preference_change", "userPreferenceChange", {"状态": "当前无待处理用户偏好变化"}, "object", "用户偏好变化", "描述经确认或待确认的用户偏好变化。"),
        field("expression_habit_change", "expressionHabitChange", {"状态": "当前无待处理表达习惯变化"}, "object", "表达习惯变化", "描述回应长度、节奏、措辞等非核心表达变化。"),
        field("relationship_familiarity_change", "relationshipFamiliarityChange", {"状态": "当前无待处理关系熟悉度变化"}, "object", "关系熟悉度变化", "描述熟悉度表现变化，不自动改变关系模式或阶段。"),
        field("behavior_feedback", "behaviorFeedback", ["当前无待处理行为反馈"], "list", "行为反馈", "记录用于有限适应判断的明确行为反馈。"),
        field("explicit_user_authorization", "explicitUserAuthorization", False, "boolean", "用户明确授权", "记录用户是否明确授权当前敏感变化。"),
        field("change_source", "changeSource", "single_user_expression", "text", "变化来源", "记录变化请求的稳定来源标识。", options=enum_options("changeSource", change_sources)),
        field("change_reason", "changeReason", "当前无待处理变化", "long_text", "变化原因", "说明变化目的和依据，不得以自然成长或真实意识为理由。"),
        field("change_target_fields", "changeTargetFields", [], "list", "变化目标字段", "列出待治理字段路径，不直接修改其内容。"),
        field("before_change_content", "beforeChangeContent", {"状态": "当前无变化前内容"}, "object", "变化前内容", "保留变化前快照摘要，用于连续性检查与回滚判断。"),
        field("candidate_after_change_content", "candidateAfterChangeContent", {"状态": "当前无变化后候选内容"}, "object", "变化后候选内容", "提供变化后候选值，仅用于审核，不直接写入配置。"),
        field("version_information", "versionInformation", {"状态": "当前无待处理版本变化"}, "object", "版本信息", "记录候选版本和兼容信息，不执行自主版本升级。"),
        field("version_inheritance_source", "versionInheritanceSource", "当前版本配置", "text", "版本继承来源", "记录可验证的版本继承来源。"),
        field("historical_change_records", "historicalChangeRecords", ["当前无待处理历史变化记录"], "list", "历史变化记录", "提供历史变化摘要，用于连续性检查，不保存运行历史。"),
        field("rollback_information", "rollbackInformation", {"状态": "当前无需回滚"}, "object", "回滚信息", "记录可用回滚版本、条件和目标；本模块不直接执行回滚。"),
    ]
    normalize_rules = [
        "trim_text_values",
        "normalize_empty_and_default_values",
        "normalize_field_path_format",
        "normalize_change_source_enum",
        "normalize_authorization_status",
        "normalize_change_amplitude_range",
        "remove_duplicate_change_items",
        "merge_semantically_equivalent_change_requests",
        "flag_unknown_change_source",
        "flag_missing_before_change_value",
        "flag_sensitive_change_without_user_authorization",
        "forbid_name_resident_id_alias_or_codename",
        "no_memory_content_over_identity_core",
        "no_temporary_state_to_permanent_personality",
    ]
    source_rules = [
        "allow_explicit_user_authorization_source",
        "allow_long_term_stable_user_preference_source",
        "allow_confirmed_important_memory_source",
        "allow_valid_version_upgrade_source",
        "allow_explicit_error_correction_source",
        "allow_validated_config_migration_source",
        "allow_rule_limited_adaptation_source",
        "caution_single_user_expression_source",
        "caution_temporary_emotional_state_source",
        "caution_inferred_user_preference_source",
        "caution_unconfirmed_memory_candidate_source",
        "caution_inferred_relationship_familiarity_source",
        "caution_model_generated_self_summary_source",
        "forbid_autonomous_identity_modification_source",
        "forbid_unauthorized_personality_rewrite_source",
        "forbid_real_human_impersonation_request_source",
        "forbid_safety_bypass_request_source",
        "forbid_external_content_injection_source",
        "forbid_unvalidated_data_migration_source",
        "forbid_background_growth_loop_source",
        "forbid_other_resident_identity_modification_source",
    ]
    immutable_core = [
        "digital_resident_identity",
        "identity_single_source_of_truth",
        "resident_type",
        "primary_language",
        "regional_identity_source",
        "core_service_positioning",
        "core_personality_baseline",
        "safety_boundary",
        "default_relationship_positioning",
        "real_human_boundary",
    ]
    adaptable_fields = [
        "user_addressing_habit",
        "response_length",
        "expression_rhythm",
        "preferred_phrasing",
        "explicit_user_preference",
        "daily_interaction_style",
        "authorized_companionship_memory",
        "current_task_habit",
        "non_core_visual_preference",
        "familiarity_expression",
    ]
    authorization_required_fields = [
        "long_term_memory_write",
        "relationship_mode_change",
        "long_term_behavior_preference",
        "important_value_tendency_adjustment",
        "version_migration",
        "multi_layer_configuration_change",
        "identity_expression_affecting_user_understanding",
    ]
    scope_rules = [
        "classify_target_field_by_declared_registry",
        "immutable_core_cannot_be_changed_by_module",
        "adaptable_field_allows_limited_change_only",
        "authorization_required_field_needs_explicit_confirmation",
        "low_priority_content_cannot_override_high_priority_content",
        "memory_and_preference_cannot_override_identity_core",
        "provide_forbidden_reason_and_safe_alternative",
    ]
    continuity_rules = [
        "verify_same_resident_after_version_upgrade",
        "preserve_identity_single_source_of_truth",
        "detect_core_personality_overwrite",
        "detect_regional_anchor_conflict",
        "detect_primary_language_replacement",
        "detect_default_relationship_positioning_change",
        "detect_safety_boundary_weakening",
        "detect_memory_over_identity_fact",
        "detect_lost_important_history",
        "detect_conflicting_version_sources",
        "require_migration_record_when_needed",
        "require_rollback_support",
        "verify_rollback_restores_identity_continuity",
    ]
    rollback_triggers = [
        "identity_conflict",
        "core_personality_drift",
        "unauthorized_relationship_upgrade",
        "safety_boundary_weakened",
        "memory_overwrites_identity_fact",
        "version_migration_failed",
        "user_revokes_authorization",
        "change_source_confirmed_invalid",
        "compile_load_or_runtime_failure",
    ]
    decision_rules = [
        "decision_requires_target_source_authorization_and_amplitude",
        "decision_requires_effect_scope_and_duration",
        "decision_requires_identity_and_other_layer_impact_flags",
        "decision_requires_version_record_and_rollback_policy",
        "no_direct_identity_personality_relationship_or_safety_modification",
        "no_direct_formal_memory_write",
        "no_automatic_growth_loop_or_personality_training",
        "no_autonomous_version_upgrade_migration_or_rollback",
        "no_natural_growth_or_real_consciousness_claim",
        "rollback_request_only_no_execution",
    ]
    output_fields = [
        "growth_governance_status",
        "change_target_fields",
        "change_source",
        "authorization_status",
        "field_classification",
        "immutable_core",
        "adaptation_allowed",
        "allowed_change_amplitude",
        "change_effect_scope",
        "change_effect_duration",
        "identity_continuity_status",
        "version_inheritance_result",
        "save_allowed",
        "long_term_memory_write_allowed",
        "user_confirmation_required",
        "manual_review_required",
        "version_record_required",
        "rollback_required",
        "rollback_conditions",
        "rollback_target",
        "risk_items",
        "decision_reason",
        "forbidden_change_reason",
        "suggested_alternative",
    ]
    output = {
        "output_key": output_key,
        "fields": {str(item["field_key"]): item["field_value"] for item in fields},
        "growth_governance_status": "user_confirmation_required",
        "change_target_fields": [],
        "change_source": "single_user_expression",
        "authorization_status": "unconfirmed",
        "field_classification": "待分类",
        "immutable_core": False,
        "adaptation_allowed": False,
        "allowed_change_amplitude": "no_change",
        "change_effect_scope": ["当前无生效变化"],
        "change_effect_duration": "当前无生效期限",
        "identity_continuity_status": "stable",
        "version_inheritance_result": "manual_confirmation_required",
        "save_allowed": False,
        "long_term_memory_write_allowed": False,
        "user_confirmation_required": True,
        "manual_review_required": False,
        "version_record_required": False,
        "rollback_required": False,
        "rollback_conditions": rollback_triggers,
        "rollback_target": "最近一个通过连续性校验的版本",
        "risk_items": [],
        "decision_reason": "当前无已授权变化，默认保持身份连续性并等待用户确认。",
        "forbidden_change_reason": "不得由低优先级记忆、偏好、临时状态或未经授权请求覆盖身份核心。",
        "suggested_alternative": "将变化限制在允许适应字段，或请求用户确认、人工审核和版本记录。",
        "source_node": node_ids["input"],
        "validation_node": node_ids["continuity"],
        "compile_time_only": True,
        "no_runtime_capability": True,
        "no_direct_governance_execution": True,
    }
    node_specs = [
        ("input", "text_input", {"mode": "generic_fields", "text": "", "fields": fields}, "input"),
        ("normalize", "structure_normalize", {"input": node_ids["input"], "normalize_rules": normalize_rules, "change_sources": change_sources, "change_amplitudes": change_amplitudes, "outputs": ["normalized_change_fields", "unknown_change_sources", "missing_before_change_values", "authorization_gaps"]}, "normalize"),
        ("source", "validation", {"input": node_ids["normalize"], "validation_rules": source_rules, "allowed_change_sources": allowed_change_sources, "forbidden_change_sources": forbidden_change_sources, "outputs": ["change_source", "source_trust_level", "authorization_status", "user_confirmation_required", "next_step_allowed", "rejection_reason", "risk_explanation"]}, "sourceAuthorization"),
        ("scope", "validation", {"input": node_ids["source"], "validation_rules": scope_rules, "immutable_core_fields": immutable_core, "adaptable_fields": adaptable_fields, "authorization_required_fields": authorization_required_fields, "change_amplitudes": change_amplitudes, "outputs": ["field_classification", "immutable_core", "adaptation_allowed", "authorization_required", "allowed_change_amplitude", "forbidden_change_reason", "suggested_alternative"]}, "scope"),
        ("continuity", "validation", {"input": node_ids["scope"], "validation_rules": continuity_rules, "identity_priority": ["identity_single_source_of_truth", "safety_boundary", "resident_type_and_core_positioning", "core_personality", "primary_language_and_regional_anchor", "default_relationship_positioning", "confirmed_long_term_memory", "user_preference", "expression_and_interaction_habits"], "inheritance_results": inheritance_results, "continuity_statuses": continuity_statuses, "outputs": ["identity_continuity_status", "version_inheritance_result", "migration_record_required", "rollback_supported", "continuity_risks"]}, "continuity"),
        ("decision", "structure_normalize", {"input": node_ids["continuity"], "decision_rules": decision_rules, "governance_decisions": governance_decisions, "rollback_triggers": rollback_triggers, "decision_schema": ["change_target_fields", "change_source", "authorization_status", "allowed_change_scope", "maximum_change_amplitude", "effect_scope", "effect_duration", "long_term_memory_write", "identity_core_impact", "other_layer_impact", "user_confirmation_required", "version_record_required", "rollback_supported", "rollback_conditions", "rollback_target_version", "decision_reason"], "outputs": ["growth_governance_status", "save_allowed", "adaptation_allowed", "manual_review_required", "rollback_required", "rollback_conditions", "rollback_target", "decision_reason"]}, "decision"),
        ("output", "module_output", {"input": node_ids["decision"], "output_key": output_key, "output_schema": {"type": "object", "required": True, "fields": output_fields}}, "output"),
        ("reference_input", "reference_input", {"references": []}, "referenceInput"),
        (
            "reference_output",
            "reference_output",
            {
                "input": node_ids["output"],
                "export_name": "",
                "export_description": "",
                "export_scope": "module",
                "export_scopes": ["module", "node", "field"],
                "allow_module_level_reference": True,
                "export_fields": [],
                "allow_layers": [],
                "forbidden_layers": [],
                "authority_source_type": "authoritative_constraint",
                "is_core_source": False,
                "override_allowed": False,
            },
            "referenceOutput",
        ),
    ]
    metadata = {"compile_time_only": True, "runtime_enabled": False, "no_execution": True}
    nodes = [
        {
            "node_id": node_ids[role],
            "node_type": node_type,
            "module_id": module_id,
            "layer_id": "layer_12",
            "params": params,
            "position": (
                {"x": 870, "y": 520}
                if role == "reference_input"
                else {"x": 2220, "y": 120}
                if role == "reference_output"
                else {"x": 120 + index * 300, "y": 120}
            ),
            "i18n_keys": {
                "name": f"layer12.growthContinuity.node.{suffix}.title",
                "description": f"layer12.growthContinuity.node.{suffix}.description",
                "type_name": f"node.type.{node_type}",
            },
            "outputs": {output_key: output, "module_output": output_key} if role == "output" else {},
            "metadata": metadata,
        }
        for index, (role, node_type, params, suffix) in enumerate(node_specs)
    ]
    return _module(
        module_id,
        "structured_growth_identity_continuity_governance",
        "Growth and Identity Continuity Governance Module",
        "layer_12",
        status=ProtocolStatus.mock,
        category="meta",
        is_placeholder=False,
        color_status="amber",
        tags=["meta", "growth_governance", "identity_continuity", "rollback_policy", "stage7_4"],
        module_graph={
            "shell_version": "module_shell_v1",
            "nodes": nodes,
            "edges": [
                {
                    "edge_id": f"{node_ids[source]}_to_{node_ids[target]}",
                    "source": node_ids[source],
                    "source_port": "p_out",
                    "target": node_ids[target],
                    "target_port": "p_in",
                }
                for source, target in zip(
                    ("input", "normalize", "source", "scope", "continuity", "decision"),
                    ("normalize", "source", "scope", "continuity", "decision", "output"),
                )
            ]
            + [
                {
                    "edge_id": f"{node_ids['reference_input']}_to_{node_ids[target]}",
                    "source": node_ids["reference_input"],
                    "source_port": "p_out",
                    "target": node_ids[target],
                    "target_port": "p_in",
                }
                for target in ("source", "scope", "continuity", "decision")
            ]
            + [
                {
                    "edge_id": f"{node_ids['output']}_to_{node_ids['reference_output']}",
                    "source": node_ids["output"],
                    "source_port": "p_out",
                    "target": node_ids["reference_output"],
                    "target_port": "p_in",
                }
            ],
            "output_key": output_key,
            "compile_time_only": True,
        },
        output_schema=[{"key": output_key, "type": "object", "required": True, "description": "Layer 12 static growth and identity-continuity governance configuration."}],
        ui_config={"shell_version": "module_shell_v1", "classification": "core"},
        i18n_keys={
            "display_name": "layer12.growthContinuity.module.title",
            "description": "layer12.growthContinuity.module.description",
            "output": "layer12.growthContinuity.output",
        },
        outputs={output_key: output, "module_output": output_key},
        config={
            "shell_version": "module_shell_v1",
            "module_class": "core",
            "compile_time_only": True,
            "governance_rules_only": True,
            "no_runtime_capability": True,
            "no_direct_governance_execution": True,
            "no_formal_memory_write": True,
            "no_identity_personality_relationship_or_safety_write": True,
            "no_engine_binding": True,
            "no_provider_binding": True,
            "field_registry": [
                {
                    **{key: value for key, value in item.items() if key != "field_value"},
                    "owner_node_id": node_ids["input"],
                }
                for item in fields
            ],
        },
        mock_only=True,
        no_execution=True,
        dr_write_keys=[f"payload.modules.{module_id}.outputs.{output_key}"],
    )


LAYER11_P2_MODULE_IDS = {
    "user_relationship",
    "intimacy_level",
    "role_positioning",
    "relationship_rule",
    "module_social",
    "interaction_history",
}
LAYER11_REVIEW_BASE_VALIDATION_RULES = [
    "required_fields_present",
    "field_structure_valid",
    "field_types_valid",
    "forbidden_rules_valid",
    "no_runtime_state_fields",
    "no_layer1_identity_redefinition",
    "no_layer3_safety_boundary_override",
    "no_automatic_relationship_transition",
    "no_responsibility_boundary_conflict",
]
LAYER11_P2_VALIDATION_OUTPUTS = ["validation_status", "risk_items", "correction_suggestions"]
LAYER11_P2_I18N_PREFIX = {
    "user_relationship": "layer11.userRelationship",
    "intimacy_level": "layer11.relationshipStage",
    "role_positioning": "layer11.trustMechanism",
    "relationship_rule": "layer11.relationshipBehavior",
    "module_social": "layer11.socialNetwork",
    "interaction_history": "layer11.groupRelationship",
}
LAYER11_REVIEW_FIELD_DESCRIPTIONS = {
    "intimacy_level": {
        "stage_order": "定义关系阶段的固定顺序，包含初始接触、基础熟悉、稳定默契和深度默契。不负责自动推进或当前阶段判断。本字段属于静态配置，不保存运行状态。",
        "stage_definitions": "定义初始接触、基础熟悉、稳定默契和深度默契各阶段的边界与含义。不负责改变关系角色或执行阶段升级。本字段属于静态配置，不保存运行状态。",
        "stage_progression_conditions": "定义进入稳定默契和深度默契所需的渐进、证据、确认与可逆条件。不负责根据单次互动自动推进。本字段属于静态配置，不保存运行状态。",
        "stage_progression_evidence": "定义支持稳定默契与深度默契判断的长期、稳定、非敏感证据类型。不负责保存实时互动证据或计算阶段。本字段属于静态配置，不保存运行状态。",
    },
    "role_positioning": {
        "trust_user_control_rules": "定义用户对信任策略的控制规则，包括拒绝信任恢复、降低信任策略、重置信任规则，以及拒绝居民自行宣称用户已经完全信任。本字段只定义静态控制规则，不保存实时信任等级、信任分数或信任状态。",
    },
    "relationship_rule": {
        "conflict_behavior_rules": "定义数字居民与用户之间发生分歧、拒绝、误解或边界冲突时的回应和修复规则。只处理居民与用户的直接关系冲突，不分析现实第三方关系，不负责多人或多居民讨论协调。本字段属于静态配置。",
    },
    "module_social": {
        "third_party_relationship_analysis_rules": "定义用户向居民描述家人、朋友、伴侣、同事等现实第三方关系问题时的分析规则。只分析未直接参与当前会话的现实第三方关系，不处理当前多人讨论的轮次、主持、协作或群体共识。本字段属于静态配置。",
    },
}
LAYER11_REVIEW_MODULE_VALIDATION_RULES = {
    "intimacy_level": [
        "stage_order_valid",
        "stage_definitions_complete",
        "progression_requires_confirmed_evidence",
        "no_stage_skipping",
        "no_numeric_intimacy_score",
        "no_runtime_stage_state",
        "established_rapport_cannot_change_relationship_mode",
    ],
    "role_positioning": [
        "trust_dimensions_valid",
        "trust_evidence_sources_valid",
        "trust_user_control_preserved",
        "no_runtime_trust_state",
        "reset_restores_default_trust_policy",
        "trust_user_control_rules_required",
    ],
    "relationship_rule": [
        "no_third_party_relationship_analysis",
        "no_group_discussion_orchestration",
        "resident_user_conflict_scope_valid",
        "rejection_response_preserves_user_autonomy",
        "no_runtime_behavior_state",
    ],
    "module_social": [
        "third_party_analysis_scope_valid",
        "no_active_group_turn_taking",
        "no_multi_resident_orchestration",
        "no_resident_user_conflict_repair_override",
        "no_third_party_sensitive_profile",
    ],
    "interaction_history": [
        "active_group_scope_valid",
        "no_private_third_party_profile_analysis",
        "no_resident_user_relationship_repair_override",
        "no_multi_agent_runtime_orchestration",
        "no_runtime_group_state",
    ],
}


def _layer11_p2_description(value: object) -> str:
    """Keep Layer 11 field documentation explicit without changing its business value."""
    description = str(value or "").rstrip("。")
    if "本字段属于静态配置" in description:
        return description + "。"
    return f"{description}。不负责当前运行状态、实时判断或实际操作。本字段属于静态配置，不保存当前状态。"


def _layer11_p2_field_key(field: object) -> str:
    return str(field.get("field_key") or field.get("field_id") or "") if isinstance(field, dict) else ""


def _layer11_p2_i18n_suffix(field_key: str) -> str:
    parts = field_key.split("_")
    return parts[0] + "".join(part.title() for part in parts[1:])


def _layer11_p2_is_terminal_validation(node_id: str) -> bool:
    return node_id.endswith("boundary_validation")


def _layer11_p2_validation_rules(module_id: str, node_id: str, rules: object) -> list[str]:
    if module_id == "user_relationship":
        if _layer11_p2_is_terminal_validation(node_id):
            return [
                "required_fields_present",
                "field_structure_valid",
                "field_types_valid",
                "forbidden_rules_valid",
                "no_layer1_identity_redefinition",
                "no_layer3_safety_boundary_override",
                "no_automatic_relationship_mode_switch",
                "no_runtime_relationship_state_transition",
            ]
        return [
            "relationship_switch_requires_explicit_user_request",
            "user_can_revoke_or_restore_default_relationship",
            "relationship_switch_cannot_change_identity_core",
        ]
    if _layer11_p2_is_terminal_validation(node_id):
        return [*LAYER11_REVIEW_BASE_VALIDATION_RULES, *LAYER11_REVIEW_MODULE_VALIDATION_RULES[module_id]]
    current_rules = [str(item) for item in rules if isinstance(item, str)] if isinstance(rules, list) else []
    return list(dict.fromkeys(rule for rule in current_rules if "forbidden" not in rule.lower()))


def _normalize_layer11_p2_module(module: ModuleV04) -> ModuleV04:
    """Normalize only the six Layer 11 static configuration shells for P2."""
    if module.layer_id != "layer_11" or module.module_id not in LAYER11_P2_MODULE_IDS:
        return module
    graph = module.module_graph if isinstance(module.module_graph, dict) else {}
    nodes = graph.get("nodes") if isinstance(graph.get("nodes"), list) else []
    input_node = next((node for node in nodes if isinstance(node, dict) and node.get("node_type") == "text_input"), None)
    input_params = input_node.get("params") if isinstance(input_node, dict) and isinstance(input_node.get("params"), dict) else {}
    input_fields = [dict(field) for field in input_params.get("fields", []) if isinstance(field, dict) and _layer11_p2_field_key(field) != "config_version"]
    field_values = {_layer11_p2_field_key(field): field.get("field_value") for field in input_fields}
    configured_registry = module.config.get("field_registry") if isinstance(module.config.get("field_registry"), list) else []
    registry_source = configured_registry or input_fields
    field_registry = [dict(field) for field in registry_source if isinstance(field, dict) and _layer11_p2_field_key(field) != "config_version"]
    for field in field_registry:
        field_key = _layer11_p2_field_key(field)
        i18n = field.get("i18n_keys") if isinstance(field.get("i18n_keys"), dict) else {}
        prefix = LAYER11_P2_I18N_PREFIX[module.module_id]
        suffix = _layer11_p2_i18n_suffix(field_key)
        field["description"] = LAYER11_REVIEW_FIELD_DESCRIPTIONS.get(module.module_id, {}).get(field_key, _layer11_p2_description(field.get("description")))
        field["i18n_keys"] = {
            **i18n,
            "label": i18n.get("label") or f"{prefix}.field.{suffix}.label",
            "description": i18n.get("description") or f"{prefix}.field.{suffix}.description",
        }
    fields = [
        {
            **{key: value for key, value in field.items() if key != "owner_node_id"},
            "field_value": field_values.get(_layer11_p2_field_key(field), field.get("field_value", "")),
        }
        for field in field_registry
    ]
    field_keys = [_layer11_p2_field_key(field) for field in field_registry]
    field_keys = [field_key for field_key in field_keys if field_key]
    required_field_keys = [
        _layer11_p2_field_key(field)
        for field in field_registry
        if field.get("required") is not False and _layer11_p2_field_key(field)
    ]
    node_i18n = input_node.get("i18n_keys", {}) if isinstance(input_node, dict) and isinstance(input_node.get("i18n_keys"), dict) else {}
    field_registry = [
        {
            **{key: value for key, value in field.items() if key != "field_value"},
            "owner_node_id": str(input_node.get("node_id") or "") if isinstance(input_node, dict) else "",
        }
        for field in field_registry
    ]
    output_key = next(
        (
            str(node.get("params", {}).get("output_key") or "")
            for node in nodes
            if isinstance(node, dict) and node.get("node_type") == "module_output" and isinstance(node.get("params"), dict)
        ),
        "",
    )
    for node in nodes:
        if not isinstance(node, dict):
            continue
        node_id = str(node.get("node_id") or "")
        node_type = str(node.get("node_type") or "")
        params = node.get("params") if isinstance(node.get("params"), dict) else {}
        node_i18n_keys = node.get("i18n_keys", {}) if isinstance(node.get("i18n_keys"), dict) else {}
        if node is input_node:
            normalized_input_params = {
                "mode": "generic_fields",
                "fields": fields,
                "field_registry": field_registry,
                "config_mode": "static_config",
                "i18n_keys": {"title": node_i18n.get("name", ""), "description": node_i18n.get("description", "")},
            }
            if isinstance(input_params.get("text"), str) and input_params["text"].strip():
                normalized_input_params["text"] = input_params["text"]
            node["params"] = normalized_input_params
        elif node_type == "structure_normalize":
            node["params"] = {
                "input": params.get("input", ""),
                "normalize_rules": list(dict.fromkeys(str(item) for item in params.get("normalize_rules", []) if isinstance(item, str))),
                "outputs": field_keys,
            }
        elif node_type == "validation":
            node["params"] = {
                "input": params.get("input", ""),
                "required_fields": required_field_keys,
                "validation_rules": _layer11_p2_validation_rules(module.module_id, node_id, params.get("validation_rules", [])),
                "validation_outputs": LAYER11_P2_VALIDATION_OUTPUTS,
            }
        elif node_type == "update_rule":
            existing_policy = params.get("update_policy", {}) if isinstance(params.get("update_policy"), dict) else {}
            update_policy = {
                key: value
                for key, value in existing_policy.items()
                if key not in {"confirmed_legal_config_only", "requires_revalidation", "no_runtime_capability"}
            }
            update_policy.update(
                {
                    "confirmed_validated_config_only": True,
                    "requires_revalidation_after_update": True,
                    "requires_recompile": True,
                    "no_runtime_state_write": True,
                }
            )
            node["params"] = {"input": params.get("input", ""), "update_policy": update_policy, "config_version": "0.1"}
        elif node_type == "module_output":
            node["params"] = {
                "input": params.get("input", ""),
                "output_key": params.get("output_key", output_key),
                "output_schema": {
                    "type": "object",
                    "required": True,
                    "fields": [*field_keys, *LAYER11_P2_VALIDATION_OUTPUTS, "config_version"],
                },
                "i18n_keys": {"title": node_i18n_keys.get("name", ""), "description": node_i18n_keys.get("description", "")},
            }
            outputs = node.get("outputs") if isinstance(node.get("outputs"), dict) else {}
            output = dict(outputs.get(output_key)) if isinstance(outputs.get(output_key), dict) else {}
            output.pop("config_version", None)
            outputs[output_key] = {
                **output,
                "validation_status": "warning",
                "risk_items": ["validation_not_executed"],
                "correction_suggestions": ["run_validation_before_use"],
            }
            node["outputs"] = outputs

    module.config["field_registry"] = field_registry
    module_output = dict(module.outputs.get(output_key)) if isinstance(module.outputs.get(output_key), dict) else {}
    module_output.pop("config_version", None)
    module.outputs[output_key] = {
        **module_output,
        "validation_status": "warning",
        "risk_items": ["validation_not_executed"],
        "correction_suggestions": ["run_validation_before_use"],
    }
    return module


MODULE_CATALOG: List[ModuleV04] = [
    # L1 Identity Core
    *[_identity_core_module(spec) for spec in IDENTITY_CORE_MODULE_SPECS],

    # L2 Personality
    *[_layer2_personality_module(spec) for spec in LAYER2_PERSONALITY_MODULE_SPECS],
    _module("personality_llm_slot", "personality_slot", "Personality LLM Slot", "layer_2", status=ProtocolStatus.ready, slot_type=SlotType.llm, category="persona", is_placeholder=True, color_status="green", ui_config={"catalog_only": True, "hidden_in_module_library": True}, config={"catalog_only": True, "hidden_in_module_library": True}),
    _module("dialogue_language_style", "language_style", "Dialogue Language Style", "layer_2", status=ProtocolStatus.ready, category="persona", is_placeholder=True, color_status="green", ui_config={"catalog_only": True, "hidden_in_module_library": True}, config={"catalog_only": True, "hidden_in_module_library": True}),

    # L3 Safety Boundary
    _content_safety_module(),
    *[_layer3_policy_module(spec) for spec in LAYER3_POLICY_MODULE_SPECS],
    _risk_response_module(),
    _module("safety_audit_slot", "safety_slot", "Safety Audit Slot", "layer_3", status=ProtocolStatus.ready, slot_type=SlotType.tool, category="safety", is_placeholder=True, risk_level=RiskLevel.high, audit_required=True, color_status="green", ui_config={"catalog_only": True}, config={"catalog_only": True}),
    _module("policy_guard_slot", "safety_slot", "Policy Guard Slot", "layer_3", status=ProtocolStatus.ready, slot_type=SlotType.tool, category="safety", is_placeholder=True, risk_level=RiskLevel.high, audit_required=True, color_status="green", ui_config={"catalog_only": True}, config={"catalog_only": True}),
    _module("forbidden_topics", "safety", "Forbidden Topics", "layer_3", status=ProtocolStatus.ready, category="safety", is_placeholder=True, risk_level=RiskLevel.high, audit_required=True, color_status="green", ui_config={"catalog_only": True}, config={"catalog_only": True}),
    _module("safety_boundary_profile", "safety_profile", "Safety Boundary Profile", "layer_3", status=ProtocolStatus.mock, category="safety", risk_level=RiskLevel.medium, color_status="amber", ui_config={"catalog_only": True}, config={"catalog_only": True}),

    # L4 Legal Permission
    _module("clone_restriction", "permission", "Clone Restriction", "layer_4", status=ProtocolStatus.ready, category="governance", is_placeholder=True, risk_level=RiskLevel.medium, audit_required=True, color_status="green"),
    _module("compliance_requirement", "permission", "Compliance Requirement", "layer_4", status=ProtocolStatus.ready, category="governance", is_placeholder=True, risk_level=RiskLevel.medium, audit_required=True, color_status="green"),
    _module("ownership_record", "permission_record", "Ownership Record", "layer_4", status=ProtocolStatus.mock, category="governance", risk_level=RiskLevel.medium, color_status="amber"),
    _module("permission_scope", "permission_record", "Permission Scope", "layer_4", status=ProtocolStatus.mock, category="governance", risk_level=RiskLevel.medium, color_status="amber"),
    _module("commercial_usage_right", "permission_record", "Commercial Usage Right", "layer_4", status=ProtocolStatus.mock, category="governance", risk_level=RiskLevel.medium, color_status="amber"),
    _module("consent_record_slot", "permission_slot", "Consent Record Slot", "layer_4", status=ProtocolStatus.mock, slot_type=SlotType.tool, category="governance", risk_level=RiskLevel.medium, color_status="amber"),
    _module("license_policy_slot", "permission_slot", "License Policy Slot", "layer_4", status=ProtocolStatus.mock, slot_type=SlotType.tool, category="governance", risk_level=RiskLevel.medium, color_status="amber"),
    _module("emergency_contact", "permission_future", "Emergency Contact", "layer_4", status=ProtocolStatus.later, category="governance", risk_level=RiskLevel.high, audit_required=True, human_confirm_required=True, color_status="gray"),

    # L5 Memory
    _event_memory_module(),
    _relationship_memory_module(),
    _memory_access_control_module(),
    _short_term_memory_module(),
    _module("short_term_memory_slot", "memory_slot", "Short Term Memory Slot", "layer_5", status=ProtocolStatus.ready, slot_type=SlotType.memory, category="memory", is_placeholder=True, color_status="green"),
    _module("long_term_memory_slot", "memory_slot", "Long Term Memory Slot", "layer_5", status=ProtocolStatus.ready, slot_type=SlotType.memory, category="memory", is_placeholder=True, color_status="green"),
    _module("vector_db_slot", "memory_slot", "Vector DB Slot", "layer_5", status=ProtocolStatus.ready, slot_type=SlotType.memory, category="memory", is_placeholder=True, color_status="green"),
    _module("memory_recall_slot", "memory_slot", "Memory Recall Slot", "layer_5", status=ProtocolStatus.ready, slot_type=SlotType.memory, category="memory", is_placeholder=True, color_status="green"),
    _memory_provider_router_module(),
    _preference_memory_module(),
    _module("self_memory", "memory", "Self Memory", "layer_5", status=ProtocolStatus.mock, category="memory", slot_type=SlotType.memory, color_status="amber"),
    _module("knowledge_memory", "memory", "Knowledge Memory", "layer_5", status=ProtocolStatus.mock, category="memory", slot_type=SlotType.memory, color_status="amber"),
    _memory_update_module(),
    _module("memory_update_slot", "memory_slot", "Memory Update Slot", "layer_5", status=ProtocolStatus.mock, slot_type=SlotType.memory, category="memory", color_status="amber"),

    # L6 Knowledge
    _module("rag_slot", "knowledge_slot", "RAG Slot", "layer_6", status=ProtocolStatus.ready, slot_type=SlotType.llm, category="knowledge", is_placeholder=True, color_status="green"),
    _module("general_knowledge", "knowledge", "General Knowledge", "layer_6", status=ProtocolStatus.mock, category="knowledge", color_status="amber"),
    _module("professional_knowledge", "knowledge", "Professional Knowledge", "layer_6", status=ProtocolStatus.mock, category="knowledge", color_status="amber"),
    _module("private_knowledge", "knowledge", "Private Knowledge", "layer_6", status=ProtocolStatus.mock, category="knowledge", color_status="amber"),
    _module("knowledge_update", "knowledge", "Knowledge Update", "layer_6", status=ProtocolStatus.mock, category="knowledge", color_status="amber"),
    _module("knowledge_base_slot", "knowledge_slot", "Knowledge Base Slot", "layer_6", status=ProtocolStatus.mock, slot_type=SlotType.llm, category="knowledge", color_status="amber"),
    _module("realtime_information_source", "knowledge_source", "Realtime Information Source", "layer_6", status=ProtocolStatus.later, category="knowledge", color_status="gray"),
    _module("web_search_slot", "knowledge_slot", "Web Search Slot", "layer_6", status=ProtocolStatus.later, slot_type=SlotType.tool, category="knowledge", color_status="gray"),

    # L7 World / Context
    _worldview_module(),
    _module("timeline_context", "world", "Timeline Context", "layer_7", status=ProtocolStatus.mock, category="context", color_status="amber"),
    _environment_module(),
    _module("social_rules", "world", "Social Rules", "layer_7", status=ProtocolStatus.mock, category="context", color_status="amber"),
    _module("realtime_environment", "world", "Realtime Environment", "layer_7", status=ProtocolStatus.later, category="context", color_status="gray"),
    _module("spatial_context_slot", "world_slot", "Spatial Context Slot", "layer_7", status=ProtocolStatus.later, slot_type=SlotType.tool, category="context", color_status="gray"),
    _module("real_world_sensor_slot", "world_slot", "Real World Sensor Slot", "layer_7", status=ProtocolStatus.later, slot_type=SlotType.tool, category="context", color_status="gray"),

    # L8 Behavior
    _language_behavior_module(),
    _decision_behavior_module(),
    _detail_behavior_module(),
    _interaction_behavior_module(),
    _social_behavior_module(),
    _task_behavior_module(),
    _module("behavior_policy_slot", "behavior_slot", "Behavior Policy Slot", "layer_8", status=ProtocolStatus.mock, slot_type=SlotType.tool, category="behavior", color_status="amber"),

    # L9 Capability / Tools
    _module("builtin_capability", "capability", "Builtin Capability", "layer_9", status=ProtocolStatus.ready, category="capability", is_placeholder=True, color_status="green"),
    _module("permission_management", "capability", "Permission Management", "layer_9", status=ProtocolStatus.ready, category="capability", is_placeholder=True, color_status="green"),
    _module("api_connector_slot", "capability_slot", "API Connector Slot", "layer_9", status=ProtocolStatus.ready, slot_type=SlotType.tool, category="capability", is_placeholder=True, color_status="green"),
    _module("llm_provider_router", "capability_router", "LLM Provider Router", "layer_9", status=ProtocolStatus.ready, slot_type=SlotType.llm, category="capability", is_placeholder=True, color_status="green"),
    _module("model_adapter", "capability_adapter", "Model Adapter", "layer_9", status=ProtocolStatus.ready, slot_type=SlotType.llm, category="capability", is_placeholder=True, color_status="green"),
    _module("api_adapter", "capability_adapter", "API Adapter", "layer_9", status=ProtocolStatus.ready, slot_type=SlotType.tool, category="capability", is_placeholder=True, color_status="green"),
    _module("tool_router_slot", "capability_slot", "Tool Router Slot", "layer_9", status=ProtocolStatus.ready, slot_type=SlotType.tool, category="capability", is_placeholder=True, color_status="green"),
    _module("ai_slot_router", "capability_slot", "AI Slot Router", "layer_9", status=ProtocolStatus.ready, slot_type=SlotType.llm, category="capability", is_placeholder=True, color_status="green"),
    _module("tool_calling", "capability", "Tool Calling", "layer_9", status=ProtocolStatus.mock, slot_type=SlotType.tool, category="capability", color_status="amber"),
    _module("automation_task", "capability", "Automation Task", "layer_9", status=ProtocolStatus.later, slot_type=SlotType.tool, category="capability", color_status="gray"),
    _module("extension_capability", "capability", "Extension Capability", "layer_9", status=ProtocolStatus.later, slot_type=SlotType.tool, category="capability", color_status="gray"),
    _module("local_model_slot", "capability_slot", "Local Model Slot", "layer_9", status=ProtocolStatus.later, slot_type=SlotType.llm, category="capability", color_status="gray"),
    _module("local_model_adapter", "capability_adapter", "Local Model Adapter", "layer_9", status=ProtocolStatus.later, slot_type=SlotType.llm, category="capability", color_status="gray"),

    # L10 Multimodal
    _module(
        "voice_tts_module_v1",
        "voice_tts_module",
        "Voice / TTS Module v1",
        "layer_10",
        status=ProtocolStatus.ready,
        slot_type=SlotType.tts,
        category="multimodal",
        is_placeholder=False,
        color_status="green",
        tags=["voice", "tts", "lattice"],
        module_graph={
            "node_roles": [
                "voice_config",
                "tts_provider",
                "voice_profile",
                "audio_output",
                "speaking_status",
                "voice_lattice_sync",
                "speech_input_event_placeholder",
            ],
            "slot_routes": ["tts.speak", "tts.preview", "voice.status", "speech.input_event"],
        },
        slot_bindings=[
            {"slot_id": "slot_tts", "slot_type": SlotType.tts.value, "slot_name": "tts.speak", "node_role": "tts_provider"},
            {"slot_id": "slot_tts", "slot_type": SlotType.tts.value, "slot_name": "tts.preview", "node_role": "audio_output"},
            {"slot_id": "slot_lattice_update", "slot_type": SlotType.lattice.value, "slot_name": "voice.status", "node_role": "speaking_status"},
            {"slot_id": "slot_lattice_update", "slot_type": SlotType.lattice.value, "slot_name": "voice.sync.lattice_voice", "node_role": "voice_lattice_sync"},
            {"slot_id": "slot_speech", "slot_type": SlotType.speech.value, "slot_name": "speech.input_event", "node_role": "speech_input_event_placeholder"},
        ],
        runtime_mapping={
            "flow": [
                "output_text",
                "tts.speak",
                "audio_output",
                "voice.status=speaking",
                "voice.sync.lattice_voice",
                "lattice_state.voice_state=speaking",
                "subtitle_stream_update",
                "voice_state=idle",
            ]
        },
        dr_mapping={
            "voice_config": "voice_config",
            "tts_provider_config": "tts_provider_config",
            "voice_profile_config": "voice_profile_config",
            "voice_lattice_sync_policy": "voice_lattice_sync_policy",
            "speech_event_schema": "speech_event_schema",
        },
        ui_config={"strict_layers": True, "execution_entry": "slot_only"},
        i18n_keys={
            "display_name": "module.voice_tts_module_v1",
            "description": "module.voice_tts_module_v1.description",
        },
        inputs={"output_text": "string"},
        outputs={"voice_state": "idle"},
        config={
            "voice_config": True,
            "tts_provider_config": True,
            "voice_profile_config": True,
            "voice_lattice_sync_policy": True,
            "speech_event_schema": True,
        },
    ),
    _module("voice_profile", "multimodal", "Voice Profile", "layer_10", status=ProtocolStatus.ready, slot_type=SlotType.tts, category="multimodal", is_placeholder=True, color_status="green"),
    _module("voice_profile_keyed", "multimodal", "Voice Profile Keyed", "layer_10", status=ProtocolStatus.mock, slot_type=SlotType.tts, category="multimodal", color_status="amber"),
    _module("tts_provider_router", "multimodal_router", "TTS Provider Router", "layer_10", status=ProtocolStatus.ready, slot_type=SlotType.tts, category="multimodal", is_placeholder=True, color_status="green"),
    _module("elevenlabs_slot", "multimodal_slot", "ElevenLabs Slot", "layer_10", status=ProtocolStatus.ready, slot_type=SlotType.tts, category="multimodal", is_placeholder=True, color_status="green"),
    _module("volcano_tts_slot", "multimodal_slot", "Volcano TTS Slot", "layer_10", status=ProtocolStatus.ready, slot_type=SlotType.tts, category="multimodal", is_placeholder=True, color_status="green"),
    _module("particle_avatar", "multimodal", "Particle Avatar", "layer_10", status=ProtocolStatus.ready, slot_type=SlotType.avatar, category="multimodal", is_placeholder=True, color_status="green"),
    _module("ar_avatar_slot", "multimodal_slot", "AR Avatar Slot", "layer_10", status=ProtocolStatus.ready, slot_type=SlotType.ar, category="multimodal", is_placeholder=True, color_status="green"),
    _module("appearance_profile", "multimodal", "Appearance Profile", "layer_10", status=ProtocolStatus.mock, category="multimodal", color_status="amber"),
    _module("motion_profile", "multimodal", "Motion Profile", "layer_10", status=ProtocolStatus.mock, category="multimodal", color_status="amber"),
    _visual_style_module(),
    _module("avatar_runtime", "multimodal", "Avatar Runtime", "layer_10", status=ProtocolStatus.mock, slot_type=SlotType.avatar, category="multimodal", color_status="amber"),
    _module("video_expression", "multimodal", "Video Expression", "layer_10", status=ProtocolStatus.later, category="multimodal", color_status="gray"),
    _module("lora_visual_slot", "multimodal_slot", "LoRA Visual Slot", "layer_10", status=ProtocolStatus.later, slot_type=SlotType.ar, category="multimodal", color_status="gray"),
    _module("realtime_human_video_slot", "multimodal_slot", "Realtime Human Video Slot", "layer_10", status=ProtocolStatus.later, slot_type=SlotType.ar, category="multimodal", color_status="gray"),
    _module("ar_runtime_bridge", "multimodal_bridge", "AR Runtime Bridge", "layer_10", status=ProtocolStatus.later, slot_type=SlotType.ar, category="multimodal", color_status="gray"),

    # L11 Relationship
    _relationship_behavior_module(),
    _user_relationship_module(),
    _relationship_stage_module(),
    _group_relationship_module(),
    _trust_mechanism_module(),
    _module("relationship_memory_slot", "relationship_slot", "Relationship Memory Slot", "layer_11", status=ProtocolStatus.mock, slot_type=SlotType.memory, category="relationship", color_status="amber"),
    _module("user_profile_slot", "relationship_slot", "User Profile Slot", "layer_11", status=ProtocolStatus.mock, slot_type=SlotType.memory, category="relationship", color_status="amber"),

    # L12 Meta / Self-Reflection
    _engineering_self_awareness_module(),
    _self_state_metacognition_module(),
    _controlled_self_will_module(),
    _consistency_monitor_self_correction_module(),
    _growth_identity_continuity_governance_module(),
    _module("self_reflection_slot", "meta_slot", "Self Reflection Slot", "layer_12", status=ProtocolStatus.later, slot_type=SlotType.llm, category="meta", color_status="gray"),
    _module("growth_loop_slot", "meta_slot", "Growth Loop Slot", "layer_12", status=ProtocolStatus.later, slot_type=SlotType.llm, category="meta", color_status="gray"),

    # L13 Export / Deployment
    _module("operation_log", "export", "Operation Log", "layer_13", status=ProtocolStatus.ready, category="export", is_placeholder=True, color_status="green"),
    _module("version_management", "export", "Version Management", "layer_13", status=ProtocolStatus.ready, category="export", is_placeholder=True, color_status="green"),
    _module("data_source_record", "export", "Data Source Record", "layer_13", status=ProtocolStatus.ready, category="export", is_placeholder=True, color_status="green"),
    _module("audit_record", "export", "Audit Record", "layer_13", status=ProtocolStatus.ready, category="export", is_placeholder=True, color_status="green"),
    _module("export_record", "export", "Export Record", "layer_13", status=ProtocolStatus.ready, category="export", is_placeholder=True, color_status="green"),
    _module("node_audit_slot", "export_slot", "Node Audit Slot", "layer_13", status=ProtocolStatus.ready, slot_type=SlotType.tool, category="export", is_placeholder=True, color_status="green"),
    _module("layer_audit_slot", "export_slot", "Layer Audit Slot", "layer_13", status=ProtocolStatus.ready, slot_type=SlotType.tool, category="export", is_placeholder=True, color_status="green"),
    _module("resident_audit_slot", "export_slot", "Resident Audit Slot", "layer_13", status=ProtocolStatus.ready, slot_type=SlotType.tool, category="export", is_placeholder=True, color_status="green"),
    _module("persona_package_compiler", "export", "Persona Package Compiler", "layer_13", status=ProtocolStatus.ready, category="export", is_placeholder=True, color_status="green"),
    _module("runtime_engine", "export", "Runtime Engine", "layer_13", status=ProtocolStatus.ready, category="export", is_placeholder=True, color_status="green"),
    _module("runtime_binding_slot", "export_slot", "Runtime Binding Slot", "layer_13", status=ProtocolStatus.ready, slot_type=SlotType.tool, category="export", is_placeholder=True, color_status="green"),
    _module("preview_module", "export", "Preview Module", "layer_13", status=ProtocolStatus.ready, category="export", is_placeholder=True, color_status="green"),
    _module("log_module", "export", "Log Module", "layer_13", status=ProtocolStatus.ready, category="export", is_placeholder=True, color_status="green"),
    _module("version_diff_slot", "export_slot", "Version Diff Slot", "layer_13", status=ProtocolStatus.mock, slot_type=SlotType.tool, category="export", color_status="amber"),
    _module("config_module", "export", "Config Module", "layer_13", status=ProtocolStatus.mock, category="export", color_status="amber"),
    _module("debug_module", "export", "Debug Module", "layer_13", status=ProtocolStatus.mock, category="export", color_status="amber"),
    _module("deployment_platform", "export", "Deployment Platform", "layer_13", status=ProtocolStatus.later, category="export", color_status="gray"),
    _module("api_interface", "export", "API Interface", "layer_13", status=ProtocolStatus.later, category="export", color_status="gray"),
    _module("distribution_channel", "export", "Distribution Channel", "layer_13", status=ProtocolStatus.later, category="export", color_status="gray"),
    _module("mac_app_binding_slot", "export_slot", "Mac App Binding Slot", "layer_13", status=ProtocolStatus.later, slot_type=SlotType.tool, category="export", color_status="gray"),
    _module("ar_runtime_binding_slot", "export_slot", "AR Runtime Binding Slot", "layer_13", status=ProtocolStatus.later, slot_type=SlotType.ar, category="export", color_status="gray"),
    # --- Protocol skeleton anchors (Stage 5 baseline) -----------------------
    # Layer 1 is represented by the five Stage 7.4 identity core modules above.
    _module("module_personality", "personality", "Personality", "layer_2", status=ProtocolStatus.core, category="persona", is_placeholder=False, color_status="green", ui_config={"catalog_only": True, "hidden_in_module_library": True}, config={"catalog_only": True, "hidden_in_module_library": True}),
    _module("module_safety_boundary", "safety", "Safety Boundary", "layer_3", status=ProtocolStatus.core, risk_level=RiskLevel.high, category="governance", is_placeholder=False, audit_required=True, color_status="green", ui_config={"catalog_only": True}, config={"catalog_only": True}),
    _module("module_legal_permission", "permission", "Legal Permission", "layer_4", status=ProtocolStatus.core, risk_level=RiskLevel.medium, category="governance", is_placeholder=False, audit_required=True, color_status="green"),
    # --- Future capabilities (modules only; never standalone executables) ----
    # High-risk future capabilities are represented purely as catalog modules so
    # the permission/risk gate governs them (is_placeholder=False -> they flow
    # through the risk gate and produce permission decisions, instead of being
    # silently dropped as placeholders). They are never wired to a real provider.
    _module("module_agent", "agent", "Agent", "layer_9", status=ProtocolStatus.planned, slot_type=SlotType.tool, risk_level=RiskLevel.high, category="capability", is_placeholder=False, audit_required=True, human_confirm_required=True),
    _module("module_wallet", "wallet", "Wallet", "layer_9", status=ProtocolStatus.later, slot_type=SlotType.tool, risk_level=RiskLevel.critical, category="capability", is_placeholder=False, audit_required=True, human_confirm_required=True),
    _module("module_phone", "phone", "Phone", "layer_9", status=ProtocolStatus.later, slot_type=SlotType.tool, risk_level=RiskLevel.high, category="capability", is_placeholder=False, audit_required=True, human_confirm_required=True),
    _social_network_module(),
    _module("module_ar", "ar", "AR Presence", "layer_10", status=ProtocolStatus.planned, slot_type=SlotType.ar, risk_level=RiskLevel.medium, category="multimodal", is_placeholder=False),
    _module("module_emergency_contact", "emergency_contact", "Emergency Contact", "layer_4", status=ProtocolStatus.later, risk_level=RiskLevel.high, category="governance", is_placeholder=False, audit_required=True, human_confirm_required=True),
    _module("module_lattice_update", "lattice_update", "Lattice Update", "layer_10", status=ProtocolStatus.mock, slot_type=SlotType.lattice, category="multimodal", is_placeholder=False, color_status="amber"),
    _module("module_lattice_read", "lattice_read", "Lattice Read", "layer_10", status=ProtocolStatus.mock, slot_type=SlotType.lattice, category="multimodal", is_placeholder=False, color_status="amber"),
    _module("module_lattice_preview", "lattice_preview", "Lattice Preview", "layer_10", status=ProtocolStatus.mock, slot_type=SlotType.lattice, category="multimodal", is_placeholder=False, color_status="amber"),
    _module(
        SCREEN_UI_ANCHOR_MODULE.module_id,
        SCREEN_UI_ANCHOR_MODULE.module_type,
        SCREEN_UI_ANCHOR_MODULE.module_name,
        SCREEN_UI_ANCHOR_MODULE.layer_id,
        status=ProtocolStatus.mock,
        category="context",
        is_placeholder=False,
        color_status="amber",
        module_graph=SCREEN_UI_ANCHOR_MODULE.screen_config,
        input_schema=[],
        output_schema=[],
        slot_bindings=[{"slot_name": slot_name} for slot_name in SCREEN_UI_ANCHOR_MODULE.slot_declarations],
        context_bindings=[{"context": "screen.context"}, {"context": "ui.anchor"}, {"context": "guidance.action"}],
        runtime_mapping={"flow": SCREEN_UI_ANCHOR_MODULE.screen_config["runtime_chain"]},
        dr_mapping={
            "screen_context_schema": "screen_context_schema",
            "ui_element_schema": "ui_element_schema",
            "ui_anchor_schema": "ui_anchor_schema",
            "guidance_action_schema": "guidance_action_schema",
            "screen_trace_schema": "screen_trace_schema",
            "screen_permission_policy": "screen_permission_policy",
        },
        ui_config={"strict_layers": True, "execution_entry": "schema_only"},
        i18n_keys=SCREEN_UI_ANCHOR_MODULE.i18n_keys,
        inputs={},
        outputs={},
        config=SCREEN_UI_ANCHOR_MODULE.screen_config,
        mock_only=SCREEN_UI_ANCHOR_MODULE.mock_only,
        no_execution=SCREEN_UI_ANCHOR_MODULE.no_execution,
        slot_declarations=SCREEN_UI_ANCHOR_MODULE.slot_declarations,
        screen_config=SCREEN_UI_ANCHOR_MODULE.screen_config,
        dr_write_keys=SCREEN_UI_ANCHOR_MODULE.dr_write_keys,
    ),
]

MODULE_CATALOG = [_normalize_layer11_p2_module(module) for module in MODULE_CATALOG]


def validate_module_catalog(modules: List[ModuleV04]) -> List[str]:
    """Return a list of error strings; empty list means the catalog is valid."""
    errors: List[str] = []
    seen: set[str] = set()
    for module in modules:
        if not module.module_id:
            errors.append("module_id is empty")
            continue
        if module.module_id in seen:
            errors.append(f"duplicate module_id: {module.module_id}")
        seen.add(module.module_id)
        if module.layer_id not in CANONICAL_LAYER_IDS:
            errors.append(f"module {module.module_id} bound to unknown layer_id: {module.layer_id}")
        if module.protocol_version != "0.4.0":
            errors.append(f"module {module.module_id} has invalid protocol_version: {module.protocol_version}")
        if module.status.value not in {"CORE", "READY", "MOCK", "PLANNED", "LATER", "DISABLED"}:
            errors.append(f"module {module.module_id} has invalid status: {module.status}")
    return errors


def get_module_catalog() -> List[ModuleV04]:
    return list(MODULE_CATALOG)


def module_catalog_map() -> Dict[str, ModuleV04]:
    return {module.module_id: module for module in MODULE_CATALOG}
