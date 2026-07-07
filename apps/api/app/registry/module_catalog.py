"""Built-in Module catalog for Protocol v0.4.

Modules are capability containers bound to an existing 13-layer layer_id. They
do not execute and never write into resident_instance. Future capabilities and
planned placeholders are registered here only — no real logic this stage.
"""

from __future__ import annotations

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
                "no_api_key_or_provider",
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
            _language_behavior_option("occasional_city_imagery", "occasionalCityImagery"),
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
            "required_expression_style_expression_temperament",
            "required",
            "layer_2",
            "expression_style",
            "expression_temperament",
            "expressionTemperament",
            module_key="layer2.expressionMode.module.title",
            field_key="layer8.languageBehavior.refField.expressionTemperament",
        ),
        _language_behavior_reference(
            "required_dialogue_boundary_forbidden_tone",
            "required",
            "layer_3",
            "dialogue_boundary",
            "forbidden_tone",
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
            {"value": "dialogue_boundary", "layer_id": "layer_3", "label_key": "layer8.languageBehavior.refModule.dialogueBoundary"},
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
            "required_professional_boundary_no_professional_judgement_replacement",
            "required",
            "layer_3",
            "professional_boundary",
            "no_professional_judgement_replacement",
            "noProfessionalJudgementReplacement",
            module_key="layer8.decisionBehavior.refModule.professionalBoundary",
            field_key="layer8.decisionBehavior.refField.noProfessionalJudgementReplacement",
        ),
        _decision_behavior_reference(
            "required_dialogue_boundary_risk_response_boundary",
            "required",
            "layer_3",
            "dialogue_boundary",
            "risk_response_boundary",
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
            {"value": "professional_boundary", "layer_id": "layer_3", "label_key": "layer8.decisionBehavior.refModule.professionalBoundary"},
            {"value": "dialogue_boundary", "layer_id": "layer_3", "label_key": "layer8.decisionBehavior.refModule.dialogueBoundary"},
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
            "required_expression_style_expression_temperament",
            "required",
            "layer_2",
            "expression_style",
            "expression_temperament",
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
            "required_interaction_behavior_silence_companionship_style",
            "required",
            "layer_8",
            INTERACTION_BEHAVIOR_MODULE_ID,
            "silence_companionship_style",
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
            "required_personality_traits_core_personality",
            "required",
            "layer_2",
            "personality_traits",
            "core_personality",
            "corePersonality",
            module_key="layer2.personalityTraits.module.title",
            field_key="layer8.interactionBehavior.refField.corePersonality",
        ),
        _interaction_behavior_reference(
            "required_interaction_boundary_proactive_boundary",
            "required",
            "layer_3",
            INTERACTION_SAFETY_MODULE_ID,
            "proactive_boundary",
            "proactiveBoundary",
            module_key="layer3.interactionBoundary.module.title",
            field_key="layer8.interactionBehavior.refField.proactiveBoundary",
        ),
        _interaction_behavior_reference(
            "required_relationship_rule_default_relationship",
            "required",
            "layer_11",
            "relationship_rule",
            "default_relationship",
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
            {"value": INTERACTION_SAFETY_MODULE_ID, "layer_id": "layer_3", "label_key": "layer3.interactionBoundary.module.title"},
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
            "params": {"config_mode": "checkbox_interaction_core_rules", "checkbox_config": core_checkbox_config},
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
            "required_professional_boundary_no_professional_judgement_replacement",
            "required",
            "layer_3",
            "professional_boundary",
            "no_professional_judgement_replacement",
            "noProfessionalJudgementReplacement",
            module_key="layer8.taskBehavior.refModule.professionalBoundary",
            field_key="layer8.taskBehavior.refField.noProfessionalJudgementReplacement",
        ),
        _task_behavior_reference(
            "required_decision_behavior_suggestion_output_format",
            "required",
            "layer_8",
            "decision_pattern",
            "suggestion_output_format",
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
            {"value": "professional_boundary", "layer_id": "layer_3", "label_key": "layer8.taskBehavior.refModule.professionalBoundary"},
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
            "required_dialogue_boundary_relationship_boundary",
            "required",
            "layer_3",
            "dialogue_boundary",
            "relationship_boundary",
            "relationshipBoundary",
            module_key="layer8.socialBehavior.refModule.dialogueBoundary",
            field_key="layer8.socialBehavior.refField.relationshipBoundary",
        ),
        _social_behavior_reference(
            "required_relationship_rule_default_relationship",
            "required",
            "layer_11",
            "relationship_rule",
            "default_relationship",
            "defaultRelationship",
            module_key="module.relationship_rule",
            field_key="layer8.socialBehavior.refField.defaultRelationship",
        ),
        _social_behavior_reference(
            "required_personality_traits_core_personality",
            "required",
            "layer_2",
            "personality_traits",
            "core_personality",
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
            {"value": "dialogue_boundary", "layer_id": "layer_3", "label_key": "layer8.socialBehavior.refModule.dialogueBoundary"},
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
    _module("event_memory", "memory", "Event Memory", "layer_5", status=ProtocolStatus.ready, category="memory", slot_type=SlotType.memory, is_placeholder=True, color_status="green"),
    _module("relationship_memory", "memory", "Relationship Memory", "layer_5", status=ProtocolStatus.ready, category="memory", slot_type=SlotType.memory, is_placeholder=True, color_status="green"),
    _module("memory_access_control", "memory", "Memory Access Control", "layer_5", status=ProtocolStatus.ready, category="memory", is_placeholder=True, color_status="green"),
    _module("short_term_memory_slot", "memory_slot", "Short Term Memory Slot", "layer_5", status=ProtocolStatus.ready, slot_type=SlotType.memory, category="memory", is_placeholder=True, color_status="green"),
    _module("long_term_memory_slot", "memory_slot", "Long Term Memory Slot", "layer_5", status=ProtocolStatus.ready, slot_type=SlotType.memory, category="memory", is_placeholder=True, color_status="green"),
    _module("vector_db_slot", "memory_slot", "Vector DB Slot", "layer_5", status=ProtocolStatus.ready, slot_type=SlotType.memory, category="memory", is_placeholder=True, color_status="green"),
    _module("memory_recall_slot", "memory_slot", "Memory Recall Slot", "layer_5", status=ProtocolStatus.ready, slot_type=SlotType.memory, category="memory", is_placeholder=True, color_status="green"),
    _module("memory_provider_router", "memory_router", "Memory Provider Router", "layer_5", status=ProtocolStatus.ready, slot_type=SlotType.memory, category="memory", is_placeholder=True, color_status="green"),
    _module("preference_memory", "memory", "Preference Memory", "layer_5", status=ProtocolStatus.mock, category="memory", slot_type=SlotType.memory, color_status="amber"),
    _module("self_memory", "memory", "Self Memory", "layer_5", status=ProtocolStatus.mock, category="memory", slot_type=SlotType.memory, color_status="amber"),
    _module("knowledge_memory", "memory", "Knowledge Memory", "layer_5", status=ProtocolStatus.mock, category="memory", slot_type=SlotType.memory, color_status="amber"),
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
    _module("world_setting", "world", "World Setting", "layer_7", status=ProtocolStatus.mock, category="context", color_status="amber"),
    _module("timeline_context", "world", "Timeline Context", "layer_7", status=ProtocolStatus.mock, category="context", color_status="amber"),
    _module("environment_setting", "world", "Environment Setting", "layer_7", status=ProtocolStatus.mock, category="context", color_status="amber"),
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
    _module("visual_style", "multimodal", "Visual Style", "layer_10", status=ProtocolStatus.mock, category="multimodal", color_status="amber"),
    _module("avatar_runtime", "multimodal", "Avatar Runtime", "layer_10", status=ProtocolStatus.mock, slot_type=SlotType.avatar, category="multimodal", color_status="amber"),
    _module("video_expression", "multimodal", "Video Expression", "layer_10", status=ProtocolStatus.later, category="multimodal", color_status="gray"),
    _module("lora_visual_slot", "multimodal_slot", "LoRA Visual Slot", "layer_10", status=ProtocolStatus.later, slot_type=SlotType.ar, category="multimodal", color_status="gray"),
    _module("realtime_human_video_slot", "multimodal_slot", "Realtime Human Video Slot", "layer_10", status=ProtocolStatus.later, slot_type=SlotType.ar, category="multimodal", color_status="gray"),
    _module("ar_runtime_bridge", "multimodal_bridge", "AR Runtime Bridge", "layer_10", status=ProtocolStatus.later, slot_type=SlotType.ar, category="multimodal", color_status="gray"),

    # L11 Relationship
    _module("relationship_rule", "relationship", "Relationship Rule", "layer_11", status=ProtocolStatus.ready, category="relationship", is_placeholder=True, color_status="green"),
    _module("user_relationship", "relationship", "User Relationship", "layer_11", status=ProtocolStatus.mock, category="relationship", color_status="amber"),
    _module("intimacy_level", "relationship", "Intimacy Level", "layer_11", status=ProtocolStatus.mock, category="relationship", color_status="amber"),
    _module("interaction_history", "relationship", "Interaction History", "layer_11", status=ProtocolStatus.mock, category="relationship", color_status="amber"),
    _module("role_positioning", "relationship", "Role Positioning", "layer_11", status=ProtocolStatus.mock, category="relationship", color_status="amber"),
    _module("relationship_memory_slot", "relationship_slot", "Relationship Memory Slot", "layer_11", status=ProtocolStatus.mock, slot_type=SlotType.memory, category="relationship", color_status="amber"),
    _module("user_profile_slot", "relationship_slot", "User Profile Slot", "layer_11", status=ProtocolStatus.mock, slot_type=SlotType.memory, category="relationship", color_status="amber"),

    # L12 Meta / Self-Reflection
    _module("self_awareness", "meta", "Self Awareness", "layer_12", status=ProtocolStatus.mock, category="meta", color_status="amber"),
    _module("goal_setting", "meta", "Goal Setting", "layer_12", status=ProtocolStatus.mock, category="meta", color_status="amber"),
    _module("reflection_summary", "meta", "Reflection Summary", "layer_12", status=ProtocolStatus.mock, category="meta", color_status="amber"),
    _module("self_evaluation", "meta", "Self Evaluation", "layer_12", status=ProtocolStatus.mock, category="meta", color_status="amber"),
    _module("growth_plan", "meta", "Growth Plan", "layer_12", status=ProtocolStatus.later, category="meta", color_status="gray"),
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
    _module("module_social", "social", "Social", "layer_11", status=ProtocolStatus.planned, slot_type=SlotType.tool, risk_level=RiskLevel.medium, category="relationship", is_placeholder=False, audit_required=True),
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
