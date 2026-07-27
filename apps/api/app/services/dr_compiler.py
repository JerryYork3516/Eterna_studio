"""DR Compiler v0.1 — Stage 6.2 Canvas -> .digital_resident compile chain.

Pipeline (single direction, no execution):
    collect (13 layers / modules / slots from canvas + catalog)
      -> validate (completeness / id uniqueness / slot matching / provider binding)
      -> assemble (resident blueprint)
      -> wrap (DR metadata: dr_version / schema_version / file_type)
      -> emit .digital_resident file payload

Execution boundary (do not violate):
  * This is a pure compiler. It NEVER executes anything, never calls a provider,
    never touches the Stage 6 Runtime Kernel (execution_engine / trace / memory /
    state). No real LLM / memory / tool.
  * The produced DR is the unified input protocol for Stage 7/8 and is read back
    by the runtime only through a mock loader (`mock_load_dr`) that parses — it
    does not run.

Schema contract: the DR v0.1 field set below is frozen. Only ADD fields in later
versions — never rename or remove. `DR_VERSION` gates the contract.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
import json
import math
import re
from typing import Any, Dict, List, Optional

from .daily_companion_runtime import (
    build_runtime_dialogue_projection,
    extract_dialogue_runtime_profile,
    validate_dialogue_runtime_profile,
)
from .projection_traceability import (
    STAGE7_4_12_FINAL_SCHEMA_TRACEABILITY_GATE_FIX_REVISION,
    build_projection_traceability,
    projection_field_mapping_errors,
)

from ..dr.v3.dr_v0_3_schema import (
    DRDocumentV03,
    DR_FILE_TYPE as DR_FILE_TYPE_V3,
    DR_VERSION_V0_3,
    DR_SCHEMA_VERSION_V0_3,
    DRManifestV03,
    DRPayloadV03,
    AuditFindingV03,
    AuditReportV03,
    CompileInfoV03,
    FallbackRouteV03,
    LatticeConfigV03,
    MemoryConfigV03,
    MemoryPolicyV03,
    ResidentBlueprintV03,
    ResidentIdentityV03,
    RuntimePlanStepV03,
    RuntimePlanV03,
    RuntimeRequirementsV03,
    SafetyPolicyV03,
    ScreenCapabilityDeclarationV03,
    VisualExpressionMappingV03,
    VoiceConfigV03,
    build_runtime_plan_steps,
)
from ..dr.v3.validator import (
    validate_dr_document_v0_3,
    validate_v03_security_configuration,
)
from ..models.v0_4 import (
    CANONICAL_LAYERS,
    CANONICAL_LAYER_IDS,
    empty_layer_design_metadata,
    PROTOCOL_VERSION_V0_4,
    SCHEMA_VERSION_V0_4,
    SlotType,
    STAGE7_4_12_A2_CONTENT_REVISION,
)
from ..registry.engine_registry import get_engine_registry
from ..registry.module_catalog import (
    BEHAVIOR_SAFETY_MODULE_ID,
    BEHAVIOR_SAFETY_OUTPUT_KEY,
    CONTENT_SAFETY_MODULE_ID,
    CONTENT_SAFETY_OUTPUT_KEY,
    DATA_SAFETY_MODULE_ID,
    DATA_SAFETY_OUTPUT_KEY,
    IDENTITY_CORE_MODULE_SPECS,
    INTERACTION_SAFETY_MODULE_ID,
    INTERACTION_SAFETY_OUTPUT_KEY,
    AUDIT_LOG_POLICY_OUTPUT_KEY,
    HARD_BLOCK_POLICY_OUTPUT_KEY,
    LAYER3_CATALOG_ONLY_MODULE_IDS,
    LAYER3_SAFETY_POLICY_MODULES,
    LAYER3_RISK_RESPONSE_OUTPUT_KEYS,
    HUMAN_REVIEW_POLICY_OUTPUT_KEY,
    RISK_POLICY_OUTPUT_KEY,
    RISK_RESPONSE_MODULE_ID,
    RISK_RESPONSE_NODE_IDS,
    SAFE_REDIRECT_POLICY_OUTPUT_KEY,
    SELF_AWARENESS_FACT_SOURCE_BINDINGS,
    get_module_catalog,
    LANGUAGE_BEHAVIOR_MODULE_ID,
    LANGUAGE_BEHAVIOR_OUTPUT_KEY,
    LANGUAGE_BEHAVIOR_PRESET_ID,
    INTERACTION_BEHAVIOR_MODULE_ID,
    INTERACTION_BEHAVIOR_OUTPUT_KEY,
    INTERACTION_BEHAVIOR_PRESET_ID,
    TASK_BEHAVIOR_MODULE_ID,
    TASK_BEHAVIOR_OUTPUT_KEY,
    TASK_BEHAVIOR_PRESET_ID,
    SOCIAL_BEHAVIOR_MODULE_ID,
    SOCIAL_BEHAVIOR_OUTPUT_KEY,
    SOCIAL_BEHAVIOR_PRESET_ID,
    DECISION_BEHAVIOR_MODULE_ID,
    DECISION_BEHAVIOR_OUTPUT_KEY,
    DECISION_BEHAVIOR_PRESET_ID,
    DETAIL_BEHAVIOR_MODULE_ID,
    DETAIL_BEHAVIOR_OUTPUT_KEY,
    DETAIL_BEHAVIOR_PRESET_ID,
    EXPRESSION_VISUAL_VALIDATION_COMPATIBILITY_REVISION,
    DIALOGUE_RUNTIME_PROFILE_FIELD_KEYS,
    DIALOGUE_RUNTIME_PROFILE_MODULE_ID,
    DIALOGUE_RUNTIME_PROFILE_OUTPUT_KEY,
    EVENT_MEMORY_MODULE_ID,
    EVENT_MEMORY_OUTPUT_KEY,
    MEMORY_ACCESS_CONTROL_MODULE_ID,
    MEMORY_ACCESS_CONTROL_OUTPUT_KEY,
    MEMORY_RECALL_CLAIM_POLICY,
    MEMORY_PROVIDER_ROUTER_ALLOWED_MEMORY_TYPES,
    MEMORY_PROVIDER_ROUTER_CANONICAL_OPERATIONS,
    MEMORY_PROVIDER_ROUTER_MODULE_ID,
    MEMORY_PROVIDER_ROUTER_NAMESPACE_POLICY,
    MEMORY_PROVIDER_ROUTER_NODE_IDS,
    MEMORY_PROVIDER_ROUTER_OPERATION_ALIASES,
    MEMORY_PROVIDER_ROUTER_OUTPUT_KEY,
    MEMORY_UPDATE_MODULE_ID,
    MEMORY_UPDATE_OUTPUT_KEY,
    PARTICLE_AVATAR_MODULE_ID,
    PARTICLE_AVATAR_NODE_IDS,
    PARTICLE_AVATAR_OUTPUT_KEY,
    PARTICLE_EXPRESSION_STATES,
    PARTICLE_MAPPING_SOURCE_PRIORITY_FIX_REVISION,
    PARTICLE_RELATIVE_PARAMETER_RANGES,
    PREFERENCE_MEMORY_MODULE_ID,
    PREFERENCE_MEMORY_OUTPUT_KEY,
    RELATIONSHIP_MEMORY_MODULE_ID,
    RELATIONSHIP_MEMORY_OUTPUT_KEY,
    SHORT_TERM_MEMORY_MODULE_ID,
    SHORT_TERM_MEMORY_OUTPUT_KEY,
    FIRST_GREETING_AUTHORED_DESCRIPTION,
    FIRST_GREETING_STALE_UNAUTHORED_DESCRIPTION,
    STAGE7_4_12_IDENTITY_LITERAL_EXPORT_GATE_FIX_REVISION,
)
from ..registry.slot_catalog import get_slot_catalog
from ..dr.v2.validator.capability_validator import (
    STAGE_7_4_REQUIRED_SLOT_TYPES,
    build_v03_runtime_contract,
)
from .visual_expression_projection import (
    VISUAL_EXPRESSION_ALLOWED_STATES,
    VISUAL_EXPRESSION_FIELD_MAPPING,
    VISUAL_EXPRESSION_SAFE_PARAMETER_DEFAULTS,
    VISUAL_EXPRESSION_TRANSITION_DEFAULTS,
    build_visual_expression_mapping,
    normalize_expression_intensity,
    normalize_expression_state,
    normalize_visual_expression_mapping,
    particle_relative_mapping_source_value,
    particle_transition_rule_source_value,
    valid_visual_base_color,
)
from .capability_status_governance import (
    STAGE7_4_12_A4_CONTENT_REVISION,
    build_capability_status_governance,
    build_lattice_config_status,
    build_voice_config_status,
    capability_status_governance_errors,
    derive_lattice_config_status,
    derive_voice_config_status,
    module_status_classification,
    module_surface_classification,
)

DR_VERSION = "0.1"
FILE_TYPE = "digital_resident"
FILE_SUFFIX = ".digital_resident"
COMPILER_NAME = "DRCompiler"
COMPILER_VERSION = "0.1.0"
RUNTIME_VERSION = "resident_v1_mock"
MIN_KERNEL = "6.1"
STAGE_7_4_BASELINE_WORKFLOW_NAME = "Stage 7.4 Human Empathy DR Baseline"
_FORBIDDEN_STAGE_7_4_DOMAIN_FOCUS = {"ar", "tool", "screen_guidance", "provider", "cross_app_control"}
_V03_FROZEN_MEMORY_TYPES = (
    "short_term_memory",
    "profile_memory",
    "preference_memory",
    "interaction_log",
)
_V03_MEMORY_POLICY_EXTENSIONS_KEY = "memory_policy_extensions"
_V03_MEMORY_SUPPORT_LEVELS = {
    "short_term_memory": "supported",
    "preference_memory": "supported_minimal_kv",
    "event_memory": "policy_only",
    "relationship_memory": "policy_only",
    "interaction_log": "display_cache_only",
}
_STAGE_7_4_RESERVED_SLOT_TYPES = frozenset({"tts", "speech", "screen", "avatar", "ar", "tool"})
_STAGE_7_4_FORCED_RESERVED_MODULE_IDS = frozenset({"particle_avatar", "llm_provider_router"})
_V03_AUDIT_CHECK_NAMES = (
    "stage_scope_check",
    "compatibility_check",
    "frozen_root_field_check",
    "pending_validation_check",
    "duplicate_source_check",
    "memory_support_level_check",
    "capability_status_check",
    "formal_schema_check",
    "security_configuration_check",
    "identity_literal_export_gate_check",
    "empty_layer_status_check",
    "file_size_check",
)
_V03_FILE_SIZE_WARNING_BYTES = 10 * 1024 * 1024

# Allowed slot_types this stage (mock-only capability interfaces).
_ALLOWED_SLOT_TYPES = frozenset(t.value for t in SlotType)
_FORBIDDEN_SECRET_KEYS = {
    "api_key",
    "token",
    "access_token",
    "refresh_token",
    "base_url",
    "credential",
    "credentials",
    "secret",
    "client_secret",
    "provider",
    "provider_binding",
}
_SECRET_REF_KEYS = {"key_ref", "secret_ref", "credential_ref", "api_key_ref"}
_IDENTITY_CORE_OUTPUTS = {str(spec["module_id"]): str(spec["output"]) for spec in IDENTITY_CORE_MODULE_SPECS}
_IDENTITY_CORE_IDS = set(_IDENTITY_CORE_OUTPUTS)
_IDENTITY_CORE_REQUIRED_NODE_TYPES = ("field_input", "structure_normalize", "validation", "update_rule", "module_output")
_CONTENT_SAFETY_POLICY_KEYS = (
    "allowed_scope",
    "cautious_scope",
    "forbidden_scope",
    "sensitive_handling",
    "refusal_style",
    "high_risk_action",
    "decision_modes",
    "default_mode",
    "update_policy",
    "compile_validation_status",
    "identity_context_ref",
)
_BEHAVIOR_SAFETY_POLICY_KEYS = (
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
    "decision_modes",
    "default_mode",
    "update_policy",
    "compile_validation_status",
    "identity_context_ref",
)
_DATA_SAFETY_POLICY_KEYS = (
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
    "decision_modes",
    "default_mode",
    "update_policy",
    "compile_validation_status",
    "identity_context_ref",
)
_INTERACTION_SAFETY_POLICY_KEYS = (
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
    "decision_modes",
    "default_mode",
    "update_policy",
    "compile_validation_status",
    "identity_context_ref",
)
_RISK_POLICY_KEYS = (
    "risk_signal_summary",
    "risk_level_policy",
    "risk_response_strategy",
    "human_review_policy",
    "hard_block_policy",
    "audit_log_policy",
    "safe_redirect_policy",
    "default_risk_mode",
    "decision_modes",
    "compile_validation_status",
    "identity_context_ref",
)
_RISK_POLICY_REQUIRED_KEYS = (
    "risk_signal_summary",
    "risk_level_policy",
    "risk_response_strategy",
    "human_review_policy",
    "hard_block_policy",
    "audit_log_policy",
    "safe_redirect_policy",
    "default_risk_mode",
    "decision_modes",
    "identity_context_ref",
)
_LAYER3_SAFETY_TOP_LEVEL_OUTPUT_KEYS = tuple(output_key for _module_id, output_key in LAYER3_SAFETY_POLICY_MODULES) + tuple(
    LAYER3_RISK_RESPONSE_OUTPUT_KEYS
)
_LAYER8_BEHAVIOR_MODULES: tuple[tuple[str, str, str], ...] = (
    (LANGUAGE_BEHAVIOR_MODULE_ID, "language_behavior", LANGUAGE_BEHAVIOR_PRESET_ID),
    (INTERACTION_BEHAVIOR_MODULE_ID, "interaction_behavior", INTERACTION_BEHAVIOR_PRESET_ID),
    (TASK_BEHAVIOR_MODULE_ID, "task_behavior", TASK_BEHAVIOR_PRESET_ID),
    (SOCIAL_BEHAVIOR_MODULE_ID, "social_behavior", SOCIAL_BEHAVIOR_PRESET_ID),
    (DECISION_BEHAVIOR_MODULE_ID, "decision_behavior", DECISION_BEHAVIOR_PRESET_ID),
    (DETAIL_BEHAVIOR_MODULE_ID, "detail_behavior", DETAIL_BEHAVIOR_PRESET_ID),
)
_LAYER8_CORE_BEHAVIOR_MODULE_IDS = tuple(module_id for module_id, _policy_key, _preset_id in _LAYER8_BEHAVIOR_MODULES)
_LAYER8_MATERIALIZED_OUTPUTS = (
    (
        LANGUAGE_BEHAVIOR_MODULE_ID,
        "language_behavior",
        LANGUAGE_BEHAVIOR_PRESET_ID,
        LANGUAGE_BEHAVIOR_OUTPUT_KEY,
    ),
    (
        INTERACTION_BEHAVIOR_MODULE_ID,
        "interaction_behavior",
        INTERACTION_BEHAVIOR_PRESET_ID,
        INTERACTION_BEHAVIOR_OUTPUT_KEY,
    ),
    (
        TASK_BEHAVIOR_MODULE_ID,
        "task_behavior",
        TASK_BEHAVIOR_PRESET_ID,
        TASK_BEHAVIOR_OUTPUT_KEY,
    ),
    (
        SOCIAL_BEHAVIOR_MODULE_ID,
        "social_behavior",
        SOCIAL_BEHAVIOR_PRESET_ID,
        SOCIAL_BEHAVIOR_OUTPUT_KEY,
    ),
    (
        DECISION_BEHAVIOR_MODULE_ID,
        "decision_behavior",
        DECISION_BEHAVIOR_PRESET_ID,
        DECISION_BEHAVIOR_OUTPUT_KEY,
    ),
)
_LAYER8_MATERIALIZED_OUTPUT_MODULE_IDS = frozenset(
    item[0] for item in _LAYER8_MATERIALIZED_OUTPUTS
)
_LAYER8_OPTIONAL_DIALOGUE_RUNTIME_PROFILE_ID = "dialogue_runtime_profile"
_LAYER8_EXCLUDED_BEHAVIOR_MODULE_IDS = ("behavior_policy_slot",)
_REFERENCE_FIELD_ALIASES = {
    ("professional_boundary", "no_professional_judgement_replacement"): (
        BEHAVIOR_SAFETY_MODULE_ID,
        "real_world_decision_limits",
    ),
    ("dialogue_boundary", "forbidden_tone"): (
        INTERACTION_SAFETY_MODULE_ID,
        "forbidden_interactions",
    ),
    ("dialogue_boundary", "risk_response_boundary"): (RISK_RESPONSE_MODULE_ID, "risk_policy"),
    ("dialogue_boundary", "relationship_boundary"): (
        INTERACTION_SAFETY_MODULE_ID,
        "non_romantic_default_boundary",
    ),
    ("expression_style", "expression_temperament"): ("expression_style", "tone_warmth"),
    ("personality_traits", "core_personality"): ("personality_traits", "personality_base"),
    (INTERACTION_SAFETY_MODULE_ID, "proactive_boundary"): (
        BEHAVIOR_SAFETY_MODULE_ID,
        "proactive_behavior_limits",
    ),
    ("relationship_rule", "default_relationship"): (
        "relationship_rule",
        "baseline_relationship_behavior",
    ),
    (INTERACTION_BEHAVIOR_MODULE_ID, "silence_companionship_style"): (
        LANGUAGE_BEHAVIOR_MODULE_ID,
        "comfort_expression_style",
    ),
    (DECISION_BEHAVIOR_MODULE_ID, "suggestion_output_format"): (
        "behavior_style_mapper",
        "suggestion_output_method",
    ),
    ("world_setting", "city_imagery"): ("expression_style", "city_imagery_rules"),
    ("module_basic_identity", "role_positioning"): (
        "module_identity_anchor",
        "identity_definition",
    ),
    (MEMORY_ACCESS_CONTROL_MODULE_ID, "user_preferences"): (
        PREFERENCE_MEMORY_MODULE_ID,
        "preference_value",
    ),
    (TASK_BEHAVIOR_MODULE_ID, "suggestion_output_format"): (
        "behavior_style_mapper",
        "suggestion_output_method",
    ),
    ("visual_style", "visual_temperament"): ("personality_traits", "external_temperament"),
    ("particle_avatar", "particle_state_hint"): ("emotion_pattern", "visual_cue_reserved"),
    (MEMORY_ACCESS_CONTROL_MODULE_ID, "memorable_content"): (
        EVENT_MEMORY_MODULE_ID,
        "event_summary",
    ),
    ("world_setting", "life_scene"): ("environment_setting", "daily_living_environment"),
    (LANGUAGE_BEHAVIOR_MODULE_ID, "output_expression"): (
        LANGUAGE_BEHAVIOR_MODULE_ID,
        "wording_habits",
    ),
    (INTERACTION_BEHAVIOR_MODULE_ID, "proactive_care_boundary"): (
        "relationship_rule",
        "proactive_behavior_rules",
    ),
}
_REFERENCE_TARGET_ID_STEMS = {
    (BEHAVIOR_SAFETY_MODULE_ID, "real_world_decision_limits"): "humanistic_behavior_boundary_real_world_decision_limits",
    (INTERACTION_SAFETY_MODULE_ID, "forbidden_interactions"): "humanistic_interaction_boundary_forbidden_interactions",
    (RISK_RESPONSE_MODULE_ID, "risk_policy"): "humanistic_risk_response_risk_policy",
    (INTERACTION_SAFETY_MODULE_ID, "non_romantic_default_boundary"): "humanistic_interaction_boundary_non_romantic_default_boundary",
    ("expression_style", "tone_warmth"): "expression_style_tone_warmth",
    ("personality_traits", "personality_base"): "personality_traits_personality_base",
    (BEHAVIOR_SAFETY_MODULE_ID, "proactive_behavior_limits"): "behavior_boundary_proactive_behavior_limits",
    ("relationship_rule", "baseline_relationship_behavior"): "relationship_rule_baseline_relationship_behavior",
    (LANGUAGE_BEHAVIOR_MODULE_ID, "comfort_expression_style"): "language_behavior_comfort_expression_style",
    ("behavior_style_mapper", "suggestion_output_method"): "behavior_style_mapper_suggestion_output_method",
    ("expression_style", "city_imagery_rules"): "expression_style_city_imagery_rules",
    ("module_identity_anchor", "identity_definition"): "identity_anchor_identity_definition",
    (PREFERENCE_MEMORY_MODULE_ID, "preference_value"): "preference_memory_preference_value",
    ("personality_traits", "external_temperament"): "personality_traits_external_temperament",
    ("emotion_pattern", "visual_cue_reserved"): "emotion_pattern_visual_cue_reserved",
    (EVENT_MEMORY_MODULE_ID, "event_summary"): "event_memory_event_summary",
    ("environment_setting", "daily_living_environment"): "environment_daily_living_environment",
    (LANGUAGE_BEHAVIOR_MODULE_ID, "wording_habits"): "language_behavior_wording_habits",
    ("relationship_rule", "proactive_behavior_rules"): "relationship_rule_proactive_behavior_rules",
}
_ENVIRONMENT_MODULE_ID = "environment_setting"
_ENVIRONMENT_OUTPUT_KEY = "environment_context"
_ENVIRONMENT_FIELD_IDS = (
    "city_environment",
    "natural_environment",
    "physical_living_environment",
    "daily_living_environment",
    "social_environment",
    "network_environment",
)
_LAYER5_MEMORY_POLICY_MODULES: tuple[tuple[str, str, str], ...] = (
    (SHORT_TERM_MEMORY_MODULE_ID, SHORT_TERM_MEMORY_OUTPUT_KEY, "short_term_memory"),
    (PREFERENCE_MEMORY_MODULE_ID, PREFERENCE_MEMORY_OUTPUT_KEY, "preference_memory"),
    (EVENT_MEMORY_MODULE_ID, EVENT_MEMORY_OUTPUT_KEY, "event_memory"),
    (RELATIONSHIP_MEMORY_MODULE_ID, RELATIONSHIP_MEMORY_OUTPUT_KEY, "relationship_memory"),
    (MEMORY_UPDATE_MODULE_ID, MEMORY_UPDATE_OUTPUT_KEY, "memory_update"),
    (MEMORY_ACCESS_CONTROL_MODULE_ID, MEMORY_ACCESS_CONTROL_OUTPUT_KEY, "memory_access_control"),
    (MEMORY_PROVIDER_ROUTER_MODULE_ID, MEMORY_PROVIDER_ROUTER_OUTPUT_KEY, "memory_provider_router"),
)
_RUNTIME_PROJECTION_NORMALIZED_OUTPUTS: tuple[
    tuple[str, str], ...
] = (
    *(
        (module_id, output_key)
        for module_id, output_key, _policy_key in _LAYER5_MEMORY_POLICY_MODULES
    ),
    ("user_relationship", "user_relationship_config"),
    ("relationship_rule", "relationship_behavior_config"),
    ("intimacy_level", "relationship_stage_config"),
    ("role_positioning", "trust_mechanism_config"),
    (
        "growth_plan",
        "growth_identity_continuity_governance_config",
    ),
)
_RUNTIME_RELATIONSHIP_POLICY_OUTPUTS: tuple[
    tuple[str, str, str], ...
] = (
    ("user_relationship", "user_relationship_config", "user_relationship"),
    (
        "relationship_rule",
        "relationship_behavior_config",
        "relationship_boundaries",
    ),
    ("intimacy_level", "relationship_stage_config", "intimacy_limits"),
    ("role_positioning", "trust_mechanism_config", "role_boundaries"),
)
_RUNTIME_DIALOGUE_DERIVED_VALUE_DEFAULTS: Dict[str, Dict[str, Any]] = {
    "memory_usage_policy": {
        "memory_access_limits": {},
        "memory_write_limits": {},
        "sensitive_memory_handling": {},
        "narrative_memory_usage_rules": {},
        "conversation_and_long_term_boundary": {},
    },
    "relationship_policy": {
        "user_relationship": {},
        "relationship_boundaries": {},
        "intimacy_limits": {},
        "role_boundaries": {},
    },
    "self_disclosure_policy": {
        "resolved_facts": {},
        "relationship_awareness": {},
        "immutable_core": [],
        "real_human_boundary": True,
        "growth_limits": {},
    },
    "advice_policy": {
        "capability_scope": [],
        "capability_limits": [],
        "real_human_boundary": True,
    },
}
_LAYER3_SAFETY_POLICY_CONFIGS = {
    CONTENT_SAFETY_MODULE_ID: {
        "output_key": CONTENT_SAFETY_OUTPUT_KEY,
        "policy_keys": _CONTENT_SAFETY_POLICY_KEYS,
        "defaults": {
            "decision_modes": ["allow", "soften", "refuse", "block"],
            "default_mode": "soften",
            "high_risk_action": "block",
            "identity_context_ref": "layer_1.resident_identity",
        },
        "field_fallbacks": {
            "allowed_scope": "allowed_content_scope",
            "cautious_scope": "cautious_content_scope",
            "forbidden_scope": "forbidden_content_scope",
            "sensitive_handling": "sensitive_content_handling",
            "refusal_style": "refusal_style",
            "high_risk_action": "high_risk_content_handling",
        },
        "required_policy_keys": ("forbidden_scope", "refusal_style", "high_risk_action"),
    },
    BEHAVIOR_SAFETY_MODULE_ID: {
        "output_key": BEHAVIOR_SAFETY_OUTPUT_KEY,
        "policy_keys": _BEHAVIOR_SAFETY_POLICY_KEYS,
        "defaults": {
            "decision_modes": ["allow", "soften", "refuse", "block"],
            "default_mode": "soften",
            "high_risk_behavior_action": "block",
            "identity_context_ref": "layer_1.resident_identity",
        },
        "field_fallbacks": {
            "allowed_behaviors": "allowed_behaviors",
            "cautious_behaviors": "cautious_behaviors",
            "forbidden_behaviors": "forbidden_behaviors",
            "auto_action_limits": "auto_action_limits",
            "real_world_decision_limits": "real_world_decision_limits",
            "tool_action_limits": "tool_action_limits",
            "proactive_behavior_limits": "proactive_behavior_limits",
            "relationship_progression_limits": "relationship_progression_limits",
            "high_risk_behavior_action": "high_risk_behavior_action",
            "refusal_style": "refusal_style",
        },
        "required_policy_keys": ("forbidden_behaviors", "auto_action_limits", "real_world_decision_limits", "high_risk_behavior_action"),
    },
    DATA_SAFETY_MODULE_ID: {
        "output_key": DATA_SAFETY_OUTPUT_KEY,
        "policy_keys": _DATA_SAFETY_POLICY_KEYS,
        "defaults": {
            "decision_modes": ["allow", "soften", "refuse", "block"],
            "default_mode": "refuse",
            "sensitive_data_handling": "refuse_or_minimize",
            "identity_context_ref": "layer_1.resident_identity",
        },
        "field_fallbacks": {
            "allowed_data_read": "allowed_data_read",
            "forbidden_data_read": "forbidden_data_read",
            "allowed_memory_write": "allowed_memory_write",
            "forbidden_memory_write": "forbidden_memory_write",
            "sensitive_data_handling": "sensitive_data_handling",
            "privacy_protection_rules": "privacy_protection_rules",
            "memory_delete_update_rules": "memory_delete_update_rules",
            "cross_resident_memory_isolation": "cross_resident_memory_isolation",
            "fictional_memory_boundary": "fictional_memory_boundary",
            "fictional_experience_labeling": "fictional_experience_labeling",
        },
        "required_policy_keys": ("forbidden_data_read", "forbidden_memory_write", "sensitive_data_handling"),
    },
    INTERACTION_SAFETY_MODULE_ID: {
        "output_key": INTERACTION_SAFETY_OUTPUT_KEY,
        "policy_keys": _INTERACTION_SAFETY_POLICY_KEYS,
        "defaults": {
            "decision_modes": ["allow", "soften", "refuse", "block"],
            "default_mode": "soften",
            "non_romantic_default_boundary": "companion_default",
            "identity_context_ref": "layer_1.resident_identity",
        },
        "field_fallbacks": {
            "allowed_interactions": "allowed_interactions",
            "cautious_interactions": "cautious_interactions",
            "forbidden_interactions": "forbidden_interactions",
            "intimacy_expression_boundary": "intimacy_expression_boundary",
            "dependency_protection_rules": "dependency_protection_rules",
            "non_romantic_default_boundary": "non_romantic_default_boundary",
            "therapy_replacement_limits": "therapy_replacement_limits",
            "identity_disclosure_policy": "identity_disclosure_policy",
            "authority_impersonation_protection": "authority_impersonation_protection",
            "emotional_manipulation_protection": "emotional_manipulation_protection",
        },
        "required_policy_keys": ("forbidden_interactions", "non_romantic_default_boundary", "dependency_protection_rules"),
    },
}
_STAGE_7_4_1_COMPILE_TIME_NODE_TYPES = frozenset(
    {"field_input", "structure_normalize", "validation", "update_rule", "module_output", "layer_aggregator"}
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _finding(status: str, code: str, message: str, path: str) -> Dict[str, str]:
    return {"status": status, "code": code, "message": message, "path": path}


def _as_dict(value: Any) -> Dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, dict):
        return value
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    return {}


def _slugify(text: str) -> str:
    cleaned = "".join(c if c.isalnum() else "_" for c in (text or "").strip().lower())
    while "__" in cleaned:
        cleaned = cleaned.replace("__", "_")
    return cleaned.strip("_") or "digital_resident"


def _safe_filename_slug(value: Any) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    return _slugify(raw)


def _simplified_codename(value: Any) -> str:
    slug = _safe_filename_slug(value)
    if not slug:
        return ""
    return slug.split("_", 1)[0] or slug


def _nonempty_str(value: Any) -> str:
    return value.strip() if isinstance(value, str) and value.strip() else ""


def _normalize_language(value: Any) -> str:
    raw = _nonempty_str(value).lower().replace("_", "-")
    if raw in {"cn", "zh", "zh-cn", "ch-zh", "中文", "chinese"}:
        return "zh-CN"
    if raw in {"en", "en-us", "english"}:
        return "en"
    return _nonempty_str(value) or "zh-CN"


def _normalize_ui_language(value: Any) -> Optional[str]:
    """Keep UI locale separate from open-ended resident language facts."""

    raw = _nonempty_str(value)
    if not raw:
        return None
    normalized = _normalize_language(raw)
    if normalized in {"zh-CN", "en"}:
        return normalized
    if raw in {"zh", "en-US"}:
        return raw
    return None


def _language_display(value: str) -> str:
    return "中文" if value == "zh-CN" else value


def _normalize_date(value: Any) -> str:
    raw = _nonempty_str(value)
    if not raw:
        return ""
    parts = raw.replace(".", "/").replace("-", "/").split("/")
    if len(parts) == 3 and all(part.isdigit() for part in parts):
        year, month, day = parts
        if len(year) == 4:
            return f"{int(year):04d}-{int(month):02d}-{int(day):02d}"
    return raw


def _split_identity_terms(value: Any) -> List[str]:
    raw = _nonempty_str(value)
    if not raw:
        return []
    separators = ["/", "，", ",", "、", ";", "；", "\n"]
    parts = [raw]
    for separator in separators:
        parts = [child for part in parts for child in part.split(separator)]
    return [part.strip() for part in parts if part.strip()]


def _identity_fields(identity_profile: Dict[str, Any], output_key: str) -> Dict[str, Any]:
    output = _as_dict(identity_profile.get(output_key))
    return _as_dict(output.get("fields"))


def _sentence(value: str) -> str:
    text = value.strip()
    if not text:
        return ""
    return text if text[-1] in "。.!！?" else f"{text}。"


def _build_identity_top_summary(identity_profile: Dict[str, Any]) -> Dict[str, Any]:
    basic = _identity_fields(identity_profile, "basic_identity")
    growth = _identity_fields(identity_profile, "growth_background")
    career = _identity_fields(identity_profile, "career_identity")
    existence = _identity_fields(identity_profile, "existence_mode")
    anchor = _identity_fields(identity_profile, "identity_anchor")

    name = _nonempty_str(identity_profile.get("name")) or _nonempty_str(basic.get("name")) or "数字居民"
    city = _nonempty_str(basic.get("city")) or _nonempty_str(anchor.get("representative_city"))
    language = _normalize_language(identity_profile.get("primary_language") or basic.get("primary_language"))
    language_text = _language_display(language)
    resident_type = _nonempty_str(existence.get("digital_resident_type")) or "数字居民"
    one_line = _nonempty_str(anchor.get("identity_definition"))
    values = _nonempty_str(anchor.get("representative_value"))
    boundaries = _nonempty_str(career.get("career_boundaries"))
    growth_limits = _nonempty_str(growth.get("growth_constraints"))

    summary_parts = [
        f"{name}是" + (f"来自{city}、" if city else "") + f"以{language_text}交流为主的{resident_type}。",
    ]
    if one_line:
        summary_parts.append(_sentence(one_line))
    if values:
        summary_parts.append(f"她重视{values}。")
    if boundaries:
        summary_parts.append(_sentence(boundaries))
    if growth_limits:
        summary_parts.append(_sentence(growth_limits))
    personality_summary = "".join(summary_parts)

    description = one_line or (
        f"{name}，" + (f"来自{city}，" if city else "") + f"定位为稳定陪伴者。"
    )
    resident_description = (
        (f"来自{city}的" if city else "")
        + f"{language_text}人文共情数字居民，默认关系是稳定陪伴者。"
    )
    disclosure_source = " ".join(
        _nonempty_str(value)
        for value in (basic.get("appearance_source"), growth_limits)
        if _nonempty_str(value)
    )
    if "原创" in disclosure_source or "虚构" in disclosure_source or "不对应现实真人" in disclosure_source:
        disclosure = "原创虚构数字居民，不对应现实真人；可在需要时明确说明自身为数字居民。"
    else:
        disclosure = "数字居民；可在需要时明确说明自身为数字居民。"

    tags = ["human_empathy", "companion", "boundary-aware", "emotional_support", "relationship_communication", "daily_life"]
    focus = list(tags)
    if city and ("西安" in city or "xian" in city.lower()):
        tags.append("xian")
        focus.append("xian")
    tags.append(language)
    focus.append(language)
    domain_terms = " ".join(_split_identity_terms(anchor.get("representative_domain")) + _split_identity_terms(anchor.get("identity_keywords")) + [_nonempty_str(career.get("industry_direction"))])
    if any(term in domain_terms.lower() for term in ("media", "art")) or any(term in domain_terms for term in ("传媒", "艺术")):
        tags.append("media_art_auxiliary")
        focus.append("media_art_auxiliary")
    forbidden_focus = {"screen_guidance", "ar", "tool", "tts_required", "provider", "agent_control", "cross_app_control"}
    domain_focus = [tag for tag in dict.fromkeys(focus) if tag not in forbidden_focus]

    return {
        "primary_language": language,
        "city_symbol": city,
        "personality_summary": personality_summary,
        "domain_focus": domain_focus,
        "description": description,
        "resident_description": resident_description,
        "disclosure": disclosure,
        "tags": list(dict.fromkeys(tags)),
    }


def _secret_findings(value: Any, path: str) -> List[Dict[str, str]]:
    findings: List[Dict[str, str]] = []
    if isinstance(value, dict):
        for key, item in value.items():
            key_text = str(key)
            key_lower = key_text.lower()
            item_path = f"{path}.{key_text}" if path else key_text
            has_value = item not in (None, "", [], {})
            if has_value and key_lower in _FORBIDDEN_SECRET_KEYS and key_lower not in _SECRET_REF_KEYS:
                findings.append(_finding("FAIL", "DR_SECRET_FIELD", f"secret-like field is not allowed in DR compile input: {key_text}", item_path))
            if has_value and key_lower in {"provider", "provider_binding"}:
                findings.append(_finding("FAIL", "DR_ILLEGAL_PROVIDER_BINDING", f"provider binding is not allowed in module/node data: {key_text}", item_path))
            findings.extend(_secret_findings(item, item_path))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            findings.extend(_secret_findings(item, f"{path}[{index}]"))
    return findings


def _module_graph_nodes(module: Dict[str, Any]) -> List[Dict[str, Any]]:
    graph = module.get("module_graph") if isinstance(module.get("module_graph"), dict) else {}
    nodes = graph.get("nodes") if isinstance(graph.get("nodes"), list) else []
    return [node for node in nodes if isinstance(node, dict)]


def _module_graph_node_id(node: Dict[str, Any]) -> str:
    return _nonempty_str(node.get("node_id")) or _nonempty_str(node.get("id"))


def _canonical_reference_source_node_id(
    reference: Dict[str, Any], source_module: Dict[str, Any]
) -> str:
    """Return the source module's exact local node_id for a reference pointer."""
    source_node_id = _nonempty_str(reference.get("source_node_id"))
    if not source_node_id:
        return ""
    source_module_id = _nonempty_str(source_module.get("module_id"))
    if (
        source_module_id in _LAYER8_MATERIALIZED_OUTPUT_MODULE_IDS
        and (_nonempty_str(reference.get("source_scope")) or "module")
        == "module"
        and not reference.get("source_field_path")
        and not reference.get("source_field_paths")
    ):
        reference_outputs = [
            _module_graph_node_id(node)
            for node in _module_graph_nodes(source_module)
            if node.get("node_type") == "reference_output"
            and _module_graph_node_id(node)
        ]
        if len(reference_outputs) == 1:
            return reference_outputs[0]
    node_ids = {_module_graph_node_id(node) for node in _module_graph_nodes(source_module)}
    node_ids.discard("")
    if source_node_id in node_ids:
        return source_node_id

    source_layer_id = _nonempty_str(reference.get("source_layer_id"))
    source_module_id = _nonempty_str(reference.get("source_module_id"))
    legacy_prefix = f"{source_layer_id}::{source_module_id}::"
    local_source_node_id = source_node_id
    if "::" in source_node_id:
        if not source_layer_id or not source_module_id or not source_node_id.startswith(legacy_prefix):
            return source_node_id
        local_source_node_id = source_node_id[len(legacy_prefix) :]
        if local_source_node_id in node_ids:
            return local_source_node_id

    suffix_matches = [
        node_id for node_id in node_ids if node_id.split("::")[-1] == local_source_node_id
    ]
    if len(suffix_matches) == 1:
        return suffix_matches[0]
    return source_node_id


def _canonical_reference_field_target(module_id: str, field_id: str) -> tuple[str, str]:
    return _REFERENCE_FIELD_ALIASES.get((module_id, field_id), (module_id, field_id))


def _module_declared_field_ids(module: Dict[str, Any]) -> set[str]:
    """Return addressable fields declared by the target module itself."""
    field_ids: set[str] = set()
    config = module.get("config") if isinstance(module.get("config"), dict) else {}
    registry = config.get("field_registry") if isinstance(config.get("field_registry"), list) else []
    for field in registry:
        if isinstance(field, dict):
            field_id = _nonempty_str(field.get("field_id")) or _nonempty_str(field.get("field_key"))
            if field_id:
                field_ids.add(field_id)
    for node in _module_graph_nodes(module):
        if node.get("node_type") == "field_reference":
            continue
        params = node.get("params") if isinstance(node.get("params"), dict) else {}
        fields = params.get("fields") if isinstance(params.get("fields"), list) else []
        for field in fields:
            if isinstance(field, dict):
                field_id = _nonempty_str(field.get("field_id")) or _nonempty_str(field.get("field_key"))
                if field_id:
                    field_ids.add(field_id)
        output_schema = params.get("output_schema")
        if isinstance(output_schema, dict):
            field_ids.update(_nonempty_str(key) for key in output_schema if _nonempty_str(key))
        elif isinstance(output_schema, list):
            for field in output_schema:
                if isinstance(field, dict):
                    field_id = _nonempty_str(field.get("field_id")) or _nonempty_str(field.get("field_key")) or _nonempty_str(field.get("key"))
                    if field_id:
                        field_ids.add(field_id)
    return field_ids


def _normalize_registry_reference(
    reference: Dict[str, Any],
    modules_by_id: Dict[str, Dict[str, Any]],
    path: str,
    findings: List[Dict[str, str]],
) -> Dict[str, Any] | None:
    normalized = deepcopy(reference)
    raw_module_id = _nonempty_str(normalized.get("module_id"))
    raw_field_id = _nonempty_str(normalized.get("field_id"))
    module_id, field_id = _canonical_reference_field_target(raw_module_id, raw_field_id)
    alias_applied = (module_id, field_id) != (raw_module_id, raw_field_id)
    target_module = modules_by_id.get(module_id)
    target_layer_id = _nonempty_str(target_module.get("layer_id")) if target_module else ""
    layer_id = target_layer_id if alias_applied else _nonempty_str(normalized.get("layer_id"))
    required = bool(normalized.get("required")) or normalized.get("reference_type") == "required"

    normalized["module_id"] = module_id
    normalized["field_id"] = field_id
    if target_layer_id and (alias_applied or not layer_id):
        layer_id = target_layer_id
    normalized["layer_id"] = layer_id
    normalized["path"] = "/".join((layer_id, module_id, field_id))
    if normalized.get("reference_id"):
        raw_reference_id = _nonempty_str(normalized.get("reference_id"))
        stale_reference_id = any(
            token in raw_reference_id
            for token in (
                "professional_boundary",
                "dialogue_boundary",
                "expression_temperament",
                "core_personality",
                "default_relationship",
                "silence_companionship_style",
                "proactive_boundary",
                "suggestion_output_format",
                "relationship_boundary",
                "forbidden_tone",
                "risk_response_boundary",
            )
        )
        if alias_applied or stale_reference_id:
            reference_type = _nonempty_str(normalized.get("reference_type")) or "reference"
            stem = _REFERENCE_TARGET_ID_STEMS.get((module_id, field_id), f"{module_id}_{field_id}")
            normalized["reference_id"] = f"{reference_type}_{stem}"

    reason = ""
    if not target_module:
        reason = f"目标模块不存在: module_id={module_id or '(empty)'}"
    elif layer_id != target_layer_id:
        reason = f"目标层不匹配: declared={layer_id or '(empty)'}, actual={target_layer_id}"
    elif not field_id or field_id not in _module_declared_field_ids(target_module):
        reason = f"目标正式字段不存在: module_id={module_id}, field_id={field_id or '(empty)'}"
    if not reason:
        return normalized

    status = "FAIL" if required else "WARNING"
    findings.append(
        _finding(
            status,
            "DR_REQUIRED_REGISTRY_REFERENCE_UNRESOLVED" if required else "DR_OPTIONAL_REGISTRY_REFERENCE_OMITTED",
            f"引用解析失败；reference_type={normalized.get('reference_type') or 'optional'}；{reason}",
            path,
        )
    )
    return normalized if required else None


def _rebuild_reference_options(params: Dict[str, Any], registry: List[Dict[str, Any]]) -> None:
    options = params.get("reference_options") if isinstance(params.get("reference_options"), dict) else {}
    old_layers = {
        str(item.get("value")): item
        for item in options.get("layers", [])
        if isinstance(item, dict) and item.get("value")
    }
    old_modules = {
        str(item.get("value")): item
        for item in options.get("modules", [])
        if isinstance(item, dict) and item.get("value")
    }
    old_fields = {
        (str(item.get("module_id")), str(item.get("value"))): item
        for item in options.get("fields", [])
        if isinstance(item, dict) and item.get("module_id") and item.get("value")
    }
    layers: Dict[str, Dict[str, Any]] = {}
    modules: Dict[str, Dict[str, Any]] = {}
    fields: Dict[tuple[str, str], Dict[str, Any]] = {}
    for reference in registry:
        layer_id = str(reference.get("layer_id") or "")
        module_id = str(reference.get("module_id") or "")
        field_id = str(reference.get("field_id") or "")
        if not (layer_id and module_id and field_id):
            continue
        layers[layer_id] = deepcopy(old_layers.get(layer_id) or {"value": layer_id, "label_key": f"layer.{layer_id}"})
        module_option = deepcopy(old_modules.get(module_id) or {"value": module_id, "label_key": f"module.{module_id}"})
        module_option["value"] = module_id
        module_option["layer_id"] = layer_id
        modules[module_id] = module_option
        field_option = deepcopy(old_fields.get((module_id, field_id)) or {})
        field_option.update(
            {
                "value": field_id,
                "module_id": module_id,
                "label_key": _as_dict(reference.get("i18n_keys")).get("field") or f"field.{field_id}",
            }
        )
        fields[(module_id, field_id)] = field_option
    params["reference_options"] = {
        "layers": list(layers.values()),
        "modules": list(modules.values()),
        "fields": list(fields.values()),
    }


def _normalize_reference_registries(
    modules: List[Dict[str, Any]], findings: List[Dict[str, str]]
) -> None:
    modules_by_id = {
        _nonempty_str(module.get("module_id")): module
        for module in modules
        if _nonempty_str(module.get("module_id"))
    }
    checked = 0
    for module_index, module in enumerate(modules):
        config = module.get("config") if isinstance(module.get("config"), dict) else {}
        raw_registry = config.get("reference_registry")
        if not isinstance(raw_registry, list):
            continue
        registry: List[Dict[str, Any]] = []
        for reference_index, reference in enumerate(raw_registry):
            if not isinstance(reference, dict):
                continue
            checked += 1
            normalized = _normalize_registry_reference(
                reference,
                modules_by_id,
                f"modules[{module_index}].config.reference_registry[{reference_index}]",
                findings,
            )
            if normalized is not None:
                registry.append(normalized)
        config["reference_registry"] = registry

        for node_index, node in enumerate(_module_graph_nodes(module)):
            if node.get("node_type") != "field_reference":
                continue
            params = node.get("params") if isinstance(node.get("params"), dict) else {}
            params["recommended_references"] = deepcopy(registry)
            selected = params.get("references") if isinstance(params.get("references"), list) else []
            normalized_selected: List[Dict[str, Any]] = []
            for reference_index, reference in enumerate(selected):
                if not isinstance(reference, dict):
                    continue
                normalized = _normalize_registry_reference(
                    reference,
                    modules_by_id,
                    f"modules[{module_index}].module_graph.nodes[{node_index}].params.references[{reference_index}]",
                    findings,
                )
                if normalized is not None:
                    normalized_selected.append(normalized)
            params["references"] = normalized_selected
            outputs = node.get("outputs") if isinstance(node.get("outputs"), dict) else {}
            active = outputs.get("field_references") if isinstance(outputs.get("field_references"), list) else []
            normalized_active: List[Dict[str, Any]] = []
            for reference_index, reference in enumerate(active):
                if not isinstance(reference, dict):
                    continue
                normalized = _normalize_registry_reference(
                    reference,
                    modules_by_id,
                    f"modules[{module_index}].module_graph.nodes[{node_index}].outputs.field_references[{reference_index}]",
                    findings,
                )
                if normalized is not None:
                    normalized_active.append(normalized)
            outputs["field_references"] = normalized_active
            _rebuild_reference_options(params, registry)
    findings.append(
        _finding(
            "PASS",
            "DR_REFERENCE_REGISTRY_VALIDATION_COMPLETE",
            f"reference_registry 已使用正式模块与字段校验；checked={checked}",
            "modules.config.reference_registry",
        )
    )


def _normalize_reference_inputs(modules: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Normalize technical reference pointers on a copy of the compile input."""
    normalized_modules = deepcopy(modules)
    modules_by_id = {
        _nonempty_str(module.get("module_id")): module
        for module in normalized_modules
        if _nonempty_str(module.get("module_id"))
    }
    for module in normalized_modules:
        for node in _module_graph_nodes(module):
            if node.get("node_type") != "reference_input":
                continue
            params = node.get("params") if isinstance(node.get("params"), dict) else {}
            references = params.get("references") if isinstance(params.get("references"), list) else []
            for reference in references:
                if not isinstance(reference, dict):
                    continue
                source_module = modules_by_id.get(_nonempty_str(reference.get("source_module_id")))
                if not isinstance(source_module, dict):
                    continue
                canonical = _canonical_reference_source_node_id(reference, source_module)
                if canonical and canonical != reference.get("source_node_id"):
                    reference["source_node_id"] = canonical
    return normalized_modules


def _reference_output_field_paths(node: Dict[str, Any]) -> set[str] | None:
    if node.get("node_type") != "reference_output":
        return None
    params = node.get("params") if isinstance(node.get("params"), dict) else {}
    export_fields = params.get("export_fields")
    if not isinstance(export_fields, list):
        return set()
    paths: set[str] = set()
    for field in export_fields:
        if isinstance(field, str) and field:
            paths.add(field)
        elif isinstance(field, dict):
            field_path = _nonempty_str(field.get("field_path")) or _nonempty_str(field.get("field_key"))
            if field_path:
                paths.add(field_path)
    return paths


def _reference_input_findings(collection: Dict[str, Any]) -> List[Dict[str, str]]:
    findings: List[Dict[str, str]] = []
    modules = [module for module in collection.get("modules", []) if isinstance(module, dict)]
    modules_by_id = {
        _nonempty_str(module.get("module_id")): module
        for module in modules
        if _nonempty_str(module.get("module_id"))
    }
    layer_ids = {
        _nonempty_str(module.get("layer_id"))
        for module in modules
        if _nonempty_str(module.get("layer_id"))
    }
    checked = 0
    required_count = 0
    optional_count = 0
    invalid_references = 0

    for module_index, target_module in enumerate(modules):
        target_module_id = _nonempty_str(target_module.get("module_id"))
        for node_index, target_node in enumerate(_module_graph_nodes(target_module)):
            if target_node.get("node_type") != "reference_input":
                continue
            target_node_id = _module_graph_node_id(target_node)
            params = target_node.get("params") if isinstance(target_node.get("params"), dict) else {}
            references = params.get("references") if isinstance(params.get("references"), list) else []
            for reference_index, reference in enumerate(references):
                if not isinstance(reference, dict):
                    continue
                checked += 1
                required = bool(reference.get("required")) or reference.get("reference_type") == "required"
                required_count += int(required)
                optional_count += int(not required)
                reference_path = (
                    f"modules[{module_index}](module_id={target_module_id}).module_graph."
                    f"nodes[{node_index}](node_id={target_node_id}).params.references[{reference_index}]"
                )
                source_layer_id = _nonempty_str(reference.get("source_layer_id"))
                source_module_id = _nonempty_str(reference.get("source_module_id"))
                source_node_id = _nonempty_str(reference.get("source_node_id"))
                source_scope = _nonempty_str(reference.get("source_scope")) or "module"
                raw_field_paths = reference.get("source_field_paths")
                field_paths = [str(item) for item in raw_field_paths if isinstance(item, str) and item] if isinstance(raw_field_paths, list) else []
                singular_field_path = _nonempty_str(reference.get("source_field_path"))
                if singular_field_path and singular_field_path not in field_paths:
                    field_paths.append(singular_field_path)
                reference_invalid = False

                def reject(code: str, field: str, reason: str) -> None:
                    nonlocal reference_invalid
                    reference_invalid = True
                    status = "FAIL" if required else "WARNING"
                    message = (
                        f"module_id={target_module_id}, node_id={target_node_id}, "
                        f"source_module_id={source_module_id or '(empty)'}, "
                        f"source_node_id={source_node_id or '(empty)'}: {reason}"
                    )
                    findings.append(_finding(status, code, message, f"{reference_path}.{field}"))

                if not source_layer_id or source_layer_id not in layer_ids:
                    reject("DR_REFERENCE_SOURCE_LAYER_MISSING", "source_layer_id", f"source layer {source_layer_id or '(empty)'!r} does not exist")
                source_module = modules_by_id.get(source_module_id)
                if source_module is None:
                    reject("DR_REFERENCE_SOURCE_MODULE_MISSING", "source_module_id", f"source module {source_module_id or '(empty)'!r} does not exist")
                elif source_layer_id and source_module.get("layer_id") != source_layer_id:
                    reject(
                        "DR_REFERENCE_SOURCE_MODULE_LAYER_MISMATCH",
                        "source_module_id",
                        f"source module belongs to {source_module.get('layer_id')!r}, not {source_layer_id!r}",
                    )

                source_node: Dict[str, Any] | None = None
                if source_module is not None and source_node_id:
                    source_node = next(
                        (node for node in _module_graph_nodes(source_module) if _module_graph_node_id(node) == source_node_id),
                        None,
                    )
                if not source_node_id:
                    reject("DR_REFERENCE_SOURCE_NODE_MISSING", "source_node_id", "source_node_id is required")
                elif source_module is not None and source_node is None:
                    reject(
                        "DR_REFERENCE_SOURCE_NODE_MISSING",
                        "source_node_id",
                        "source_node_id is not an exact local node_id in the declared source module",
                    )

                if source_scope == "field" and not field_paths:
                    reject("DR_REFERENCE_SOURCE_FIELD_PATH_MISSING", "source_field_paths", "field-scoped reference has no source field path")
                if field_paths and source_node is not None:
                    available_paths = _reference_output_field_paths(source_node)
                    if available_paths is None:
                        reject(
                            "DR_REFERENCE_SOURCE_FIELD_NODE_INVALID",
                            "source_node_id",
                            "field-scoped reference must target a reference_output node",
                        )
                    else:
                        missing_paths = [path for path in field_paths if path not in available_paths]
                        if missing_paths:
                            reject(
                                "DR_REFERENCE_SOURCE_FIELD_PATH_UNRESOLVED",
                                "source_field_paths",
                                f"source field paths are not exported by the source node: {missing_paths!r}",
                            )

                invalid_references += int(reference_invalid)

    findings.append(
        _finding(
            "PASS",
            "DR_REFERENCE_VALIDATION_COMPLETE",
            f"reference validation checked={checked}, required={required_count}, optional={optional_count}, resolved={checked - invalid_references}",
            "modules",
        )
    )
    return findings


def _module_node_by_type(module: Dict[str, Any], node_type: str) -> Dict[str, Any] | None:
    for node in _module_graph_nodes(module):
        if node.get("node_type") == node_type:
            return node
    return None


def _normalize_generic_field(field: Dict[str, Any], index: int) -> Dict[str, Any]:
    field_id = str(
        field.get("field_key")
        or field.get("field_id")
        or field.get("key")
        or field.get("id")
        or f"field_{index + 1}"
    )
    value = field.get("field_value") if "field_value" in field else field.get("value")
    normalized = {
        **field,
        "field_id": field_id,
        "field_key": field_id,
        "value": value,
        "field_value": value,
        "field_type": field.get("field_type") or "long_text",
        "edit_scope": field.get("edit_scope") or "user_editable",
        "update_level": field.get("update_level") or "versioned_core",
        "requires_recompile": field.get("requires_recompile") if isinstance(field.get("requires_recompile"), bool) else True,
    }
    if "dr_mapping" in field:
        normalized["dr_mapping"] = field.get("dr_mapping")
    field_i18n = field.get("i18n_keys") if isinstance(field.get("i18n_keys"), dict) else {}
    normalized["i18n_keys"] = {
        "label": field_i18n.get("label") or f"field.identity.{field_id}.label",
        "placeholder": field_i18n.get("placeholder") or f"field.identity.{field_id}.placeholder",
        "help": field_i18n.get("help") or f"field.identity.{field_id}.help",
    }
    return normalized


def _module_fields_from_generic_fields(module: Dict[str, Any]) -> List[Dict[str, Any]]:
    for node in _module_graph_nodes(module):
        if node.get("node_type") != "text_input":
            continue
        params = node.get("params") if isinstance(node.get("params"), dict) else {}
        if params.get("mode") != "generic_fields":
            continue
        fields = params.get("fields") if isinstance(params.get("fields"), list) else []
        normalized_fields = [
            _normalize_generic_field(field, index)
            for index, field in enumerate(fields)
            if isinstance(field, dict) and (field.get("field_key") or field.get("field_id") or "field_value" in field or "value" in field)
        ]
        if normalized_fields:
            return normalized_fields
    return []


def _module_fields_from_legacy_field_input(module: Dict[str, Any]) -> List[Dict[str, Any]]:
    field_input = _module_node_by_type(module, "field_input")
    if not field_input:
        return []
    params = field_input.get("params") if isinstance(field_input.get("params"), dict) else {}
    fields = params.get("fields") if isinstance(params.get("fields"), list) else []
    return [field for field in fields if isinstance(field, dict)]


def _module_fields_from_field_input(module: Dict[str, Any]) -> List[Dict[str, Any]]:
    generic_fields = _module_fields_from_generic_fields(module)
    if generic_fields:
        return generic_fields
    return _module_fields_from_legacy_field_input(module)


def _module_has_effective_field_input(module: Dict[str, Any]) -> bool:
    return bool(_module_fields_from_generic_fields(module) or _module_fields_from_legacy_field_input(module))


def _module_output_node_value(module: Dict[str, Any], output_key: str) -> Any:
    module_output = _module_node_by_type(module, "module_output")
    if not module_output:
        return None
    node_outputs = module_output.get("outputs") if isinstance(module_output.get("outputs"), dict) else {}
    return node_outputs.get(output_key)


def _module_output_exists(module: Dict[str, Any], output_key: str) -> bool:
    outputs = module.get("outputs") if isinstance(module.get("outputs"), dict) else {}
    if output_key in outputs or outputs.get("module_output") == output_key:
        return True
    for node in _module_graph_nodes(module):
        node_outputs = node.get("outputs") if isinstance(node.get("outputs"), dict) else {}
        if node.get("node_type") == "module_output" and (output_key in node_outputs or node_outputs.get("module_output") == output_key):
            return True
    return False


def _field_output_key(field: Dict[str, Any]) -> str:
    dr_mapping = field.get("dr_mapping")
    if isinstance(dr_mapping, str) and ".fields." in dr_mapping:
        mapped_key = dr_mapping.rsplit(".fields.", 1)[-1].strip(".")
        if mapped_key:
            return mapped_key
    return str(field.get("field_id") or field.get("field_key") or "")


def _module_field_values_from_fields(fields: List[Dict[str, Any]]) -> Dict[str, Any]:
    values: Dict[str, Any] = {}
    for field in fields:
        if not isinstance(field, dict):
            continue
        field_key = _field_output_key(field)
        if not field_key:
            continue
        values[field_key] = field.get("value") if "value" in field else field.get("field_value")
    return values


def _field_identifier(field: Dict[str, Any], index: int) -> str:
    return str(field.get("field_id") or field.get("field_key") or field.get("key") or field.get("id") or f"field_{index + 1}")


def _normalize_current_technical_field(field: Dict[str, Any], index: int) -> None:
    if _field_identifier(field, index) != "primary_language":
        return
    raw_value = field.get("field_value") if "field_value" in field else field.get("value")
    if not _nonempty_str(raw_value):
        return
    normalized = _normalize_language(raw_value)
    if "field_value" in field or field.get("field_key"):
        field["field_value"] = normalized
    if "value" in field or field.get("field_id"):
        field["value"] = normalized


def _sync_current_field_compatibility(
    modules: List[Dict[str, Any]], findings: List[Dict[str, str]]
) -> Dict[str, int]:
    inspected_nodes = 0
    synchronized_nodes = 0
    created_nodes = 0
    repaired_nodes = 0
    promoted_nodes = 0
    preserved_ambiguous_nodes = 0
    for module_index, module in enumerate(modules):
        config = module.get("config") if isinstance(module.get("config"), dict) else {}
        registry = config.get("field_registry") if isinstance(config.get("field_registry"), list) else []
        for node_index, node in enumerate(_module_graph_nodes(module)):
            if node.get("node_type") not in {
                "field_input",
                "text_input",
            }:
                continue
            params = node.get("params") if isinstance(node.get("params"), dict) else {}
            has_compat_surface = any(key in params for key in ("fields", "legacy_fields", "legacy_data_fields"))
            if not has_compat_surface:
                continue
            inspected_nodes += 1
            current_value = params.get("fields")
            if not isinstance(current_value, list):
                legacy_candidates = [
                    (legacy_key, params.get(legacy_key))
                    for legacy_key in (
                        "legacy_fields",
                        "legacy_data_fields",
                    )
                    if isinstance(params.get(legacy_key), list)
                ]
                distinct_candidates = {
                    stable_value
                    for stable_value in (
                        json.dumps(
                            candidate,
                            ensure_ascii=False,
                            sort_keys=True,
                            separators=(",", ":"),
                        )
                        for _legacy_key, candidate in legacy_candidates
                    )
                }
                if legacy_candidates and len(distinct_candidates) == 1:
                    current_value = deepcopy(legacy_candidates[0][1])
                    params["fields"] = current_value
                    promoted_nodes += 1
                    findings.append(
                        _finding(
                            "WARNING",
                            "DR_COMPATIBILITY_LEGACY_FIELDS_PROMOTED",
                            (
                                "authoritative current fields were absent; "
                                "one unambiguous legacy mirror was promoted "
                                "only inside the compiler-owned copy"
                            ),
                            (
                                f"modules[{module_index}].module_graph."
                                f"nodes[{node_index}].params.fields"
                            ),
                        )
                    )
                elif legacy_candidates:
                    preserved_ambiguous_nodes += 1
                    findings.append(
                        _finding(
                            "WARNING",
                            "DR_COMPATIBILITY_LEGACY_FIELDS_AMBIGUOUS",
                            (
                                "current fields were absent and legacy "
                                "mirrors disagreed; legacy values were "
                                "preserved without choosing a new authority"
                            ),
                            (
                                f"modules[{module_index}].module_graph."
                                f"nodes[{node_index}].params"
                            ),
                        )
                    )
                    continue
                else:
                    current_value = []
            current_fields = current_value
            current_fields = [field for field in current_fields if isinstance(field, dict)]
            for index, field in enumerate(current_fields):
                _normalize_current_technical_field(field, index)
            current_ids = {_field_identifier(field, index) for index, field in enumerate(current_fields)}

            expected: Dict[str, bool] = {}
            node_id = _module_graph_node_id(node)
            for field in registry:
                if not isinstance(field, dict):
                    continue
                owner_node_id = _nonempty_str(
                    field.get("owner_node_id")
                )
                if owner_node_id and owner_node_id != node_id:
                    continue
                field_id = _nonempty_str(
                    field.get("field_id")
                ) or _nonempty_str(field.get("field_key"))
                if field_id:
                    expected[field_id] = bool(field.get("required"))
            for legacy_key in ("legacy_fields", "legacy_data_fields"):
                legacy_fields = (
                    params.get(legacy_key)
                    if isinstance(params.get(legacy_key), list)
                    else []
                )
                for index, field in enumerate(legacy_fields):
                    if not isinstance(field, dict):
                        continue
                    field_id = _field_identifier(field, index)
                    expected[field_id] = (
                        expected.get(field_id, False)
                        or bool(field.get("required"))
                    )

            for field_id, required in expected.items():
                if field_id in current_ids:
                    continue
                findings.append(
                    _finding(
                        "FAIL" if required else "WARNING",
                        "DR_CURRENT_REQUIRED_FIELD_MISSING" if required else "DR_CURRENT_OPTIONAL_FIELD_MISSING",
                        (
                            f"current fields 缺少 field_id={field_id}；legacy 值不会反向覆盖 current；"
                            f"layer_id={module.get('layer_id')}, module_id={module.get('module_id')}, node_id={node_id}"
                        ),
                        f"modules[{module_index}].module_graph.nodes[{node_index}].params.fields",
                    )
                )

            missing_mirror = any(
                not isinstance(params.get(legacy_key), list)
                for legacy_key in ("legacy_fields", "legacy_data_fields")
            )
            mismatched_mirrors = [
                legacy_key
                for legacy_key in ("legacy_fields", "legacy_data_fields")
                if isinstance(params.get(legacy_key), list)
                and params.get(legacy_key) != current_fields
            ]
            if missing_mirror:
                created_nodes += 1
            if mismatched_mirrors:
                repaired_nodes += 1
                findings.append(
                    _finding(
                        "WARNING",
                        "DR_COMPATIBILITY_FIELD_MIRROR_DRIFT",
                        (
                            "legacy field mirrors differed from authoritative "
                            "current fields and were regenerated; "
                            f"mirrors={mismatched_mirrors!r}, "
                            f"layer_id={module.get('layer_id')}, "
                            f"module_id={module.get('module_id')}, "
                            f"node_id={node_id}"
                        ),
                        (
                            f"modules[{module_index}].module_graph."
                            f"nodes[{node_index}].params"
                        ),
                    )
                )
            params["fields"] = current_fields
            params["legacy_fields"] = deepcopy(current_fields)
            params["legacy_data_fields"] = deepcopy(current_fields)
            synchronized_nodes += 1
    metrics = {
        "inspected_nodes": inspected_nodes,
        "synchronized_nodes": synchronized_nodes,
        "created_nodes": created_nodes,
        "repaired_nodes": repaired_nodes,
        "promoted_nodes": promoted_nodes,
        "preserved_ambiguous_nodes": preserved_ambiguous_nodes,
    }
    findings.append(
        _finding(
            "PASS",
            "DR_CURRENT_LEGACY_FIELD_SYNC_COMPLETE",
            (
                "legacy_fields and legacy_data_fields were deep-copied from "
                "authoritative current fields; "
                f"inspected_nodes={inspected_nodes}, "
                f"synchronized_nodes={synchronized_nodes}, "
                f"created_nodes={created_nodes}, "
                f"repaired_nodes={repaired_nodes}, "
                f"promoted_nodes={promoted_nodes}, "
                "preserved_ambiguous_nodes="
                f"{preserved_ambiguous_nodes}"
            ),
            "modules.module_graph.nodes.params.fields",
        )
    )
    return metrics


def _canonical_environment_mapping(field_id: str) -> str:
    return f"payload.modules.{_ENVIRONMENT_MODULE_ID}.outputs.{_ENVIRONMENT_OUTPUT_KEY}.fields.{field_id}"


def _sync_environment_module_output(module: Dict[str, Any]) -> None:
    if module.get("module_id") != _ENVIRONMENT_MODULE_ID:
        return
    for node in _module_graph_nodes(module):
        params = node.get("params") if isinstance(node.get("params"), dict) else {}
        fields = params.get("fields") if isinstance(params.get("fields"), list) else []
        for index, field in enumerate(fields):
            if not isinstance(field, dict):
                continue
            field_id = _field_identifier(field, index)
            if field_id in _ENVIRONMENT_FIELD_IDS:
                field["dr_mapping"] = _canonical_environment_mapping(field_id)
    config = module.get("config") if isinstance(module.get("config"), dict) else {}
    registry = config.get("field_registry") if isinstance(config.get("field_registry"), list) else []
    for index, field in enumerate(registry):
        if not isinstance(field, dict):
            continue
        field_id = _field_identifier(field, index)
        if field_id in _ENVIRONMENT_FIELD_IDS:
            field["dr_mapping"] = _canonical_environment_mapping(field_id)

    fields = _module_fields_from_field_input(module)
    top_outputs = module.get("outputs") if isinstance(module.get("outputs"), dict) else {}
    if _ENVIRONMENT_OUTPUT_KEY in top_outputs:
        top_outputs[_ENVIRONMENT_OUTPUT_KEY] = _module_output_with_field_values(
            top_outputs.get(_ENVIRONMENT_OUTPUT_KEY), fields
        )
    module_output = _module_node_by_type(module, "module_output")
    if module_output:
        node_outputs = module_output.get("outputs") if isinstance(module_output.get("outputs"), dict) else {}
        if _ENVIRONMENT_OUTPUT_KEY in node_outputs:
            node_outputs[_ENVIRONMENT_OUTPUT_KEY] = _module_output_with_field_values(
                node_outputs.get(_ENVIRONMENT_OUTPUT_KEY), fields
            )


def _sync_primary_language_field_list(fields: Any, value: str) -> None:
    if not isinstance(fields, list):
        return
    for index, field in enumerate(fields):
        if not isinstance(field, dict) or _field_identifier(field, index) != "primary_language":
            continue
        if "field_value" in field or field.get("field_key"):
            field["field_value"] = value
        if "value" in field or field.get("field_id"):
            field["value"] = value


def _sync_primary_language_compat_params(module: Dict[str, Any], value: str) -> None:
    for node in _module_graph_nodes(module):
        if node.get("node_type") != "text_input":
            continue
        params = node.get("params") if isinstance(node.get("params"), dict) else {}
        if params.get("mode") != "generic_fields":
            continue
        _sync_primary_language_field_list(params.get("fields"), value)
        _sync_primary_language_field_list(params.get("legacy_fields"), value)
        _sync_primary_language_field_list(params.get("legacy_data_fields"), value)


def _module_output_with_field_values(output: Any, fields: List[Dict[str, Any]]) -> Dict[str, Any]:
    output_dict = _as_dict(output)
    existing_fields = _as_dict(output_dict.get("fields"))
    field_values = _module_field_values_from_fields(fields)
    if not field_values:
        return output_dict
    return {
        **output_dict,
        "fields": {
            **existing_fields,
            **field_values,
        },
    }


def _normalize_basic_identity_language_in_module(module: Dict[str, Any]) -> None:
    if module.get("module_id") != "module_basic_identity":
        return
    fields = _module_fields_from_field_input(module)
    normalized_language = ""
    for field in fields:
        if field.get("field_id") == "primary_language" and _nonempty_str(field.get("value")):
            normalized_language = _normalize_language(field.get("value"))
            field["value"] = normalized_language
            break
    if not normalized_language:
        return
    _sync_primary_language_compat_params(module, normalized_language)
    for output in (
        _as_dict(_module_output_node_value(module, "basic_identity")).get("fields"),
        _as_dict(_as_dict(module.get("outputs")).get("basic_identity")).get("fields"),
    ):
        if isinstance(output, dict):
            output["primary_language"] = normalized_language


def _legacy_module_output_fallback_findings(collection: Dict[str, Any]) -> List[Dict[str, str]]:
    findings: List[Dict[str, str]] = []
    allowed_output_only_modules = {RISK_RESPONSE_MODULE_ID}
    legacy_field_input_categories = {"identity", "persona"}
    for index, module in enumerate(collection.get("modules", [])):
        module_id = module.get("module_id") if isinstance(module, dict) else None
        if not isinstance(module, dict) or module_id in _IDENTITY_CORE_IDS or module_id in allowed_output_only_modules:
            continue
        category = str(module.get("category") or "")
        module_type = str(module.get("module_type") or "")
        if category not in legacy_field_input_categories and module_type not in legacy_field_input_categories:
            continue
        outputs = module.get("outputs") if isinstance(module.get("outputs"), dict) else {}
        has_module_output = bool(outputs.get("module_output"))
        if has_module_output and not _module_has_effective_field_input(module):
            findings.append(
                _finding(
                    "WARNING",
                    "DR_IDENTITY_LEGACY_FIELD_INPUT_MISSING",
                    f"legacy module layer_id={module.get('layer_id')} module_id={module.get('module_id')} uses module.outputs.module_output fallback without generic_fields or field_input",
                    f"modules[{index}].module_graph.nodes",
                )
            )
    return findings


def _identity_core_audit_findings(collection: Dict[str, Any]) -> List[Dict[str, str]]:
    findings: List[Dict[str, str]] = []
    modules = collection.get("modules", [])
    by_id = {module.get("module_id"): module for module in modules if isinstance(module, dict)}
    layer_1_ids = {module.get("module_id") for module in modules if isinstance(module, dict) and module.get("layer_id") == "layer_1"}
    extra_layer_1 = sorted(str(module_id) for module_id in layer_1_ids - _IDENTITY_CORE_IDS if module_id)
    if extra_layer_1:
        findings.append(_finding("FAIL", "DR_IDENTITY_LAYER1_EXTRA_MODULE", f"Layer 1 may only contain Stage 7.4 identity core modules: {extra_layer_1}", "modules.layer_1"))

    for module_id, output_key in _IDENTITY_CORE_OUTPUTS.items():
        module = by_id.get(module_id)
        path = f"modules.{module_id}"
        if not module:
            findings.append(_finding("FAIL", "DR_IDENTITY_MODULE_MISSING", f"missing Layer 1 identity core module: {module_id}", path))
            continue
        if module.get("layer_id") != "layer_1":
            findings.append(_finding("FAIL", "DR_IDENTITY_MODULE_LAYER", f"{module_id} must be bound to layer_1", f"{path}.layer_id"))
        if module.get("category") != "identity":
            findings.append(_finding("FAIL", "DR_IDENTITY_MODULE_CATEGORY", f"{module_id} must use identity domain category", f"{path}.category"))
        config = module.get("config") if isinstance(module.get("config"), dict) else {}
        ui_config = module.get("ui_config") if isinstance(module.get("ui_config"), dict) else {}
        module_class = ui_config.get("classification") or config.get("module_class")
        if module_class != "core":
            findings.append(_finding("FAIL", "DR_IDENTITY_MODULE_CLASS", f"{module_id} must use module_class core", f"{path}.ui_config.classification"))
        if module.get("slot_type") is not None:
            findings.append(_finding("FAIL", "DR_IDENTITY_MODULE_SLOT_BINDING", f"{module_id} must not bind a slot/provider", f"{path}.slot_type"))
        if module.get("slot_bindings"):
            findings.append(_finding("FAIL", "DR_IDENTITY_MODULE_SLOT_BINDING", f"{module_id} must not declare slot bindings", f"{path}.slot_bindings"))
        if module.get("slot_declarations"):
            findings.append(_finding("FAIL", "DR_IDENTITY_MODULE_SLOT_BINDING", f"{module_id} must not declare slots", f"{path}.slot_declarations"))
        if module.get("runtime_enabled") is not False or module.get("no_execution") is not True:
            findings.append(_finding("FAIL", "DR_IDENTITY_NODE_NOT_COMPILE_TIME", f"{module_id} must stay compile-time only", f"{path}.runtime_enabled"))
        nodes_by_type = {str(node.get("node_type")): node for node in _module_graph_nodes(module)}
        for node_type in _IDENTITY_CORE_REQUIRED_NODE_TYPES:
            node = nodes_by_type.get(node_type)
            if node_type == "field_input" and not node and _module_fields_from_generic_fields(module):
                continue
            if not node:
                findings.append(_finding("FAIL", "DR_IDENTITY_NODE_MISSING", f"{module_id} missing compile-time node {node_type}", f"{path}.module_graph.nodes.{node_type}"))
                continue
            node_metadata = node.get("metadata") if isinstance(node.get("metadata"), dict) else {}
            if node.get("node_type") in _STAGE_7_4_1_COMPILE_TIME_NODE_TYPES and node_metadata.get("no_execution") is not True:
                findings.append(_finding("FAIL", "DR_IDENTITY_NODE_NOT_COMPILE_TIME", f"{module_id} node {node_type} must be compile-time only", f"{path}.module_graph.nodes.{node_type}.metadata"))
            i18n_keys = node.get("i18n_keys") if isinstance(node.get("i18n_keys"), dict) else {}
            if not i18n_keys.get("name") or not i18n_keys.get("description"):
                findings.append(_finding("FAIL", "DR_IDENTITY_NODE_I18N_MISSING", f"{module_id} node {node_type} missing i18n keys", f"{path}.module_graph.nodes.{node_type}.i18n_keys"))
        if not _module_output_exists(module, output_key):
            findings.append(_finding("FAIL", "DR_IDENTITY_MODULE_OUTPUT_MISSING", f"{module_id} must expose module_output {output_key}", f"{path}.outputs"))
        module_output_value = _module_output_node_value(module, output_key)
        top_outputs = module.get("outputs") if isinstance(module.get("outputs"), dict) else {}
        if module_output_value is None:
            findings.append(_finding("FAIL", "DR_IDENTITY_MODULE_OUTPUT_MISSING", f"{module_id} module_output node must emit {output_key}", f"{path}.module_graph.nodes.module_output.outputs"))
        elif output_key in top_outputs and top_outputs.get(output_key) != module_output_value:
            findings.append(_finding("FAIL", "DR_IDENTITY_MODULE_OUTPUT_MISMATCH", f"{module_id} top-level output differs from module_output node; node output is authoritative", f"{path}.outputs.{output_key}"))
        fields = _module_fields_from_field_input(module)
        if not fields:
            findings.append(_finding("FAIL", "DR_IDENTITY_MODULE_FIELDS_MISSING", f"{module_id} must declare fields under text_input.params.generic_fields or field_input.params.fields", f"{path}.module_graph.nodes.field_input.params.fields"))
        for index, field in enumerate(fields):
            if not isinstance(field, dict):
                findings.append(_finding("FAIL", "DR_IDENTITY_FIELD_INVALID", f"{module_id} field must be an object", f"{path}.module_graph.nodes.field_input.params.fields[{index}]"))
                continue
            if not field.get("field_id"):
                findings.append(_finding("FAIL", "DR_IDENTITY_FIELD_INVALID", f"{module_id} field missing field_id", f"{path}.module_graph.nodes.field_input.params.fields[{index}].field_id"))
            for key in ("edit_scope", "update_level", "requires_recompile"):
                if key not in field:
                    findings.append(_finding("FAIL", "DR_IDENTITY_FIELD_PERMISSION_MISSING", f"{module_id} field missing {key}", f"{path}.module_graph.nodes.field_input.params.fields[{index}].{key}"))
            field_i18n = field.get("i18n_keys") if isinstance(field.get("i18n_keys"), dict) else {}
            for key in ("label", "placeholder", "help"):
                if not field_i18n.get(key):
                    findings.append(_finding("FAIL", "DR_IDENTITY_FIELD_I18N_MISSING", f"{module_id} field missing i18n key {key}", f"{path}.module_graph.nodes.field_input.params.fields[{index}].i18n_keys.{key}"))
            if field.get("update_level") == "runtime_state":
                findings.append(_finding("FAIL", "DR_IDENTITY_RUNTIME_STATE_IN_PROFILE", f"{module_id} runtime_state fields cannot enter identity_profile", f"{path}.module_graph.nodes.field_input.params.fields[{index}].update_level"))
    return findings


def _assemble_identity_core_outputs(
    collection: Dict[str, Any],
    resident_id: str,
    resident_name: str,
    findings: List[Dict[str, str]],
) -> Dict[str, Any]:
    modules = {module.get("module_id"): module for module in collection.get("modules", []) if isinstance(module, dict)}
    module_outputs: Dict[str, Any] = {}
    locked_core_fields: List[str] = []
    versioned_core_fields: List[str] = []
    update_rules: List[Dict[str, Any]] = []

    for module_id, output_key in _IDENTITY_CORE_OUTPUTS.items():
        module = modules.get(module_id) or {}
        _normalize_basic_identity_language_in_module(module)
        node_output = _module_output_node_value(module, output_key)
        outputs = module.get("outputs") if isinstance(module.get("outputs"), dict) else {}
        fields = _module_fields_from_field_input(module)
        raw_module_output = node_output if node_output is not None else outputs.get(output_key, {})
        module_outputs[output_key] = _module_output_with_field_values(raw_module_output, fields)
        if not fields:
            config = module.get("config") if isinstance(module.get("config"), dict) else {}
            fields = config.get("field_registry") if isinstance(config.get("field_registry"), list) else []
        for field in fields:
            if not isinstance(field, dict):
                continue
            field_id = str(field.get("field_id") or "")
            if not field_id:
                continue
            if field.get("update_level") == "locked_core":
                locked_core_fields.append(field_id)
            elif field.get("update_level") == "versioned_core":
                versioned_core_fields.append(field_id)
            update_rules.append(
                {
                    "field_id": field_id,
                    "edit_scope": field.get("edit_scope"),
                    "update_level": field.get("update_level"),
                    "requires_recompile": bool(field.get("requires_recompile")),
                }
            )

    basic_output = module_outputs.get("basic_identity")
    if isinstance(basic_output, dict):
        basic_fields = basic_output.get("fields")
        if isinstance(basic_fields, dict):
            if _nonempty_str(basic_fields.get("primary_language")):
                basic_fields["primary_language"] = _normalize_language(basic_fields.get("primary_language"))
            birth_date = _normalize_date(basic_fields.get("birth_date") or basic_fields.get("birth_time"))
            virtual_birth_date = _normalize_date(basic_fields.get("virtual_birth_date") or basic_fields.get("virtual_birth_time"))
            if birth_date:
                basic_fields["birth_date"] = birth_date
            if virtual_birth_date:
                basic_fields["virtual_birth_date"] = virtual_birth_date

    fail_count = sum(1 for finding in findings if finding.get("status") == "FAIL")
    module_audit = {"ok": fail_count == 0, "findings": [finding for finding in findings if "IDENTITY_MODULE" in finding.get("code", "")]}
    layer_audit = {"ok": fail_count == 0, "findings": findings}
    basic_identity_fields = module_outputs.get("basic_identity", {}).get("fields", {})
    if not isinstance(basic_identity_fields, dict):
        basic_identity_fields = {}

    def _field_or_fallback(field_id: str, fallback: str | None = None) -> str | None:
        value = basic_identity_fields.get(field_id)
        if isinstance(value, str) and value.strip():
            return value
        return fallback

    profile_resident_id = _field_or_fallback("resident_id", resident_id)
    profile_name = _field_or_fallback("name", resident_name)
    profile_codename = _field_or_fallback("codename")
    profile_primary_language = _field_or_fallback("primary_language")
    profile_display_alias = _field_or_fallback("display_alias")
    profile_export_name = _field_or_fallback("export_name") or _simplified_codename(profile_codename)
    identity_summary = {
        "resident_id": profile_resident_id,
        "name": profile_name,
        "display_alias": profile_display_alias or "",
        "export_name": profile_export_name or "",
        "source": "identity_core_aggregator",
    }
    if profile_codename:
        identity_summary["codename"] = profile_codename
    if profile_primary_language:
        identity_summary["primary_language"] = profile_primary_language
    identity_profile = {
        "resident_id": profile_resident_id,
        "name": profile_name,
        **module_outputs,
        "locked_core_fields": sorted(set(locked_core_fields)),
        "versioned_core_fields": sorted(set(versioned_core_fields)),
        "update_rules": update_rules,
        "identity_summary": identity_summary,
        "display_alias": profile_display_alias or "",
        "export_name": profile_export_name or "",
    }
    if profile_codename:
        identity_profile["codename"] = profile_codename
    if profile_primary_language:
        identity_profile["primary_language"] = profile_primary_language
    aggregator = {
        "inputs": list(_IDENTITY_CORE_OUTPUTS.values()),
        "identity_profile": identity_profile,
        "locked_core_fields": identity_profile["locked_core_fields"],
        "versioned_core_fields": identity_profile["versioned_core_fields"],
        "update_rules": update_rules,
        "identity_summary": identity_summary,
        "module_audit": module_audit,
        "layer_audit": layer_audit,
    }
    return {
        "identity_profile": identity_profile,
        "layer_1": {
            "identity_core_aggregator": aggregator,
            "identity_profile": identity_profile,
        },
    }


def _module_field_values(module: Dict[str, Any]) -> Dict[str, Any]:
    return {
        str(field.get("field_id")): field.get("value")
        for field in _module_fields_from_field_input(module)
        if field.get("field_id")
    }


def _is_catalog_only_module(module: Dict[str, Any]) -> bool:
    module_id = module.get("module_id")
    config = module.get("config") if isinstance(module.get("config"), dict) else {}
    ui_config = module.get("ui_config") if isinstance(module.get("ui_config"), dict) else {}
    return module_id in LAYER3_CATALOG_ONLY_MODULE_IDS or config.get("catalog_only") is True or ui_config.get("catalog_only") is True


def _layer3_safety_module_policy(collection: Dict[str, Any], module_id: str) -> Dict[str, Any]:
    config = _LAYER3_SAFETY_POLICY_CONFIGS.get(module_id)
    if not config:
        return {}
    output_key = str(config["output_key"])
    modules = {module.get("module_id"): module for module in collection.get("modules", []) if isinstance(module, dict)}
    module = modules.get(module_id)
    if not isinstance(module, dict):
        return {}
    node_output = _module_output_node_value(module, output_key)
    outputs = module.get("outputs") if isinstance(module.get("outputs"), dict) else {}
    raw_policy = node_output if isinstance(node_output, dict) else outputs.get(output_key)
    policy = _as_dict(raw_policy)
    if not policy:
        return {}

    # The module_output node is authoritative, but older UI saves may only carry
    # edited field values. Keep the config declarative and compile-time only.
    fields = _as_dict(policy.get("fields"))
    field_input_values = _module_field_values(module)
    field_fallbacks = _as_dict(config.get("field_fallbacks"))
    defaults = _as_dict(config.get("defaults"))
    normalized: Dict[str, Any] = {}
    for key in config["policy_keys"]:  # type: ignore[union-attr]
        if key == "compile_validation_status":
            continue
        fallback_field_id = field_fallbacks.get(key)
        fallback_value = defaults.get(key, [] if str(key).endswith("s") else "")
        if fallback_field_id:
            fallback_value = fields.get(fallback_field_id, field_input_values.get(fallback_field_id, fallback_value))
        normalized[str(key)] = policy.get(key, fallback_value)
    normalized["identity_context_ref"] = normalized.get("identity_context_ref") or "layer_1.resident_identity"
    normalized["update_policy"] = _as_dict(normalized.get("update_policy"))
    has_required_boundary = all(bool(normalized.get(key)) for key in config["required_policy_keys"])  # type: ignore[union-attr]
    normalized["compile_validation_status"] = "valid" if has_required_boundary else "invalid"
    return {str(key): normalized.get(str(key)) for key in config["policy_keys"]}  # type: ignore[union-attr]


def _content_safety_module_policy(collection: Dict[str, Any]) -> Dict[str, Any]:
    return _layer3_safety_module_policy(collection, CONTENT_SAFETY_MODULE_ID)


def _module_node_by_id(module: Dict[str, Any], node_id: str) -> Dict[str, Any] | None:
    for node in _module_graph_nodes(module):
        if node.get("node_id") == node_id:
            return node
    return None


def _risk_node_params(module: Dict[str, Any], node_key: str) -> Dict[str, Any]:
    node_id = RISK_RESPONSE_NODE_IDS.get(node_key, "")
    node = _module_node_by_id(module, node_id) if node_id else None
    return node.get("params") if isinstance(node, dict) and isinstance(node.get("params"), dict) else {}


def _risk_node_output(module: Dict[str, Any], node_key: str, output_key: str) -> Dict[str, Any]:
    node_id = RISK_RESPONSE_NODE_IDS.get(node_key, "")
    node = _module_node_by_id(module, node_id) if node_id else None
    outputs = node.get("outputs") if isinstance(node, dict) and isinstance(node.get("outputs"), dict) else {}
    return _as_dict(outputs.get(output_key))


def _risk_response_derived_outputs(module: Dict[str, Any]) -> Dict[str, Any]:
    signal_params = _risk_node_params(module, "signal_summary")
    level_params = _risk_node_params(module, "level_decision")
    strategy_params = _risk_node_params(module, "strategy_selection")
    human_review_params = _risk_node_params(module, "human_review")
    hard_block_params = _risk_node_params(module, "hard_block")

    input_policies = signal_params.get("input_policy_keys")
    if not isinstance(input_policies, list) or not input_policies:
        input_policies = [
            CONTENT_SAFETY_OUTPUT_KEY,
            BEHAVIOR_SAFETY_OUTPUT_KEY,
            DATA_SAFETY_OUTPUT_KEY,
            INTERACTION_SAFETY_OUTPUT_KEY,
        ]
    risk_signal_summary = _risk_node_output(module, "signal_summary", "risk_signal_summary") or {
        "input_policies": input_policies,
        "content_risk_source": CONTENT_SAFETY_OUTPUT_KEY,
        "behavior_risk_source": BEHAVIOR_SAFETY_OUTPUT_KEY,
        "data_risk_source": DATA_SAFETY_OUTPUT_KEY,
        "interaction_risk_source": INTERACTION_SAFETY_OUTPUT_KEY,
        "aggregated_risk_signals": ["content_high_risk", "behavior_boundary_violation", "sensitive_data_risk", "interaction_dependency_risk"],
        "identity_context_ref": "layer_1.resident_identity",
    }
    risk_level_policy = _risk_node_output(module, "level_decision", "risk_level_policy") or _as_dict(level_params.get("risk_level_policy")) or {
        "risk_levels": level_params.get("risk_levels") if isinstance(level_params.get("risk_levels"), list) else ["allow", "soften", "refuse", "review", "block"],
        "default_risk_level": level_params.get("default_risk_level") or "review",
        "content_risk_rules": ["high_risk_content_defaults_to_block"],
        "behavior_risk_rules": ["major_real_world_action_defaults_to_review_or_block"],
        "data_risk_rules": ["sensitive_privacy_defaults_to_refuse_or_block"],
        "interaction_risk_rules": ["relationship_boundary_risk_defaults_to_soften_or_refuse"],
        "uncertain_risk_action": "review",
        "highest_risk_priority": ["block", "review", "refuse", "soften", "allow"],
    }
    risk_response_strategy = _risk_node_output(module, "strategy_selection", "risk_response_strategy") or _as_dict(strategy_params.get("risk_response_strategy"))
    safe_redirect_policy = _as_dict(risk_response_strategy.get(SAFE_REDIRECT_POLICY_OUTPUT_KEY)) or {
        "redirect_modes": ["safe_companionship", "clarify_limits", "encourage_real_support", "provide_general_safe_info"],
        "style": "warm_brief_non_preachy",
        "no_professional_conclusion": True,
    }
    if not risk_response_strategy:
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
    human_review_policy = _risk_node_output(module, "human_review", HUMAN_REVIEW_POLICY_OUTPUT_KEY) or _as_dict(human_review_params.get(HUMAN_REVIEW_POLICY_OUTPUT_KEY)) or {
        "human_review_triggers": [
            "external_platform_operation",
            "act_on_behalf_publish_delete_comment_dm_follow_repost",
            "major_real_world_decision",
            "gray_zone_safety_risk",
            "privacy_or_cross_resident_memory",
            "uncertain_risk_level",
            "conflict_among_layer3_policies",
        ],
        "user_confirmation_required": ["external_action", "privacy_sensitive_action"],
        "developer_review_required": ["policy_conflict", "uncertain_high_risk"],
        "pause_before_review": True,
        "allow_after_review": "explicit_approval_only",
        "review_failure_handling": "refuse_or_block_with_safe_redirect",
        "review_log_requirements": ["reason", "time", "impact_scope", "decision"],
        "compile_time_only": True,
    }
    hard_block_policy = _risk_node_output(module, "hard_block", HARD_BLOCK_POLICY_OUTPUT_KEY) or _as_dict(hard_block_params.get(HARD_BLOCK_POLICY_OUTPUT_KEY)) or {
        "hard_block_triggers": [
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
        HUMAN_REVIEW_POLICY_OUTPUT_KEY: human_review_policy,
        HARD_BLOCK_POLICY_OUTPUT_KEY: hard_block_policy,
        AUDIT_LOG_POLICY_OUTPUT_KEY: audit_log_policy,
        SAFE_REDIRECT_POLICY_OUTPUT_KEY: safe_redirect_policy,
        "default_risk_mode": "review",
        "decision_modes": ["allow", "soften", "refuse", "review", "block"],
        "compile_validation_status": "valid",
        "identity_context_ref": "layer_1.resident_identity",
        "compile_time_only": True,
    }
    return {
        RISK_POLICY_OUTPUT_KEY: risk_policy,
        HARD_BLOCK_POLICY_OUTPUT_KEY: hard_block_policy,
        HUMAN_REVIEW_POLICY_OUTPUT_KEY: human_review_policy,
        AUDIT_LOG_POLICY_OUTPUT_KEY: audit_log_policy,
        SAFE_REDIRECT_POLICY_OUTPUT_KEY: safe_redirect_policy,
    }


def _risk_response_module_outputs(collection: Dict[str, Any]) -> Dict[str, Any]:
    modules = {module.get("module_id"): module for module in collection.get("modules", []) if isinstance(module, dict)}
    module = modules.get(RISK_RESPONSE_MODULE_ID)
    if not isinstance(module, dict):
        return {}

    outputs = module.get("outputs") if isinstance(module.get("outputs"), dict) else {}
    module_output_node = _module_node_by_type(module, "module_output")
    node_outputs = module_output_node.get("outputs") if isinstance(module_output_node, dict) and isinstance(module_output_node.get("outputs"), dict) else {}
    combined_outputs = {**outputs, **node_outputs}
    derived_outputs = _risk_response_derived_outputs(module)

    raw_risk_policy = combined_outputs.get(RISK_POLICY_OUTPUT_KEY)
    risk_policy = _as_dict(raw_risk_policy)
    if not risk_policy:
        risk_policy = _as_dict(derived_outputs.get(RISK_POLICY_OUTPUT_KEY))
    else:
        derived_risk_policy = _as_dict(derived_outputs.get(RISK_POLICY_OUTPUT_KEY))
        risk_policy = {**derived_risk_policy, **risk_policy}

    for key in (HUMAN_REVIEW_POLICY_OUTPUT_KEY, HARD_BLOCK_POLICY_OUTPUT_KEY, AUDIT_LOG_POLICY_OUTPUT_KEY, SAFE_REDIRECT_POLICY_OUTPUT_KEY):
        nested_value = _as_dict(risk_policy.get(key))
        if not nested_value:
            nested_value = _as_dict(combined_outputs.get(key))
        if not nested_value:
            nested_value = _as_dict(derived_outputs.get(key))
        if nested_value:
            risk_policy[key] = nested_value

    risk_policy["identity_context_ref"] = risk_policy.get("identity_context_ref") or "layer_1.resident_identity"
    risk_policy["decision_modes"] = risk_policy.get("decision_modes") or ["allow", "soften", "refuse", "review", "block"]
    risk_policy["default_risk_mode"] = risk_policy.get("default_risk_mode") or "review"
    has_required_policy = all(bool(risk_policy.get(key)) for key in _RISK_POLICY_REQUIRED_KEYS)
    risk_policy["compile_validation_status"] = "valid" if has_required_policy else "invalid"

    normalized_risk_policy = {key: risk_policy.get(key) for key in _RISK_POLICY_KEYS}
    normalized_outputs: Dict[str, Any] = {RISK_POLICY_OUTPUT_KEY: normalized_risk_policy}
    for output_key in (
        HARD_BLOCK_POLICY_OUTPUT_KEY,
        HUMAN_REVIEW_POLICY_OUTPUT_KEY,
        AUDIT_LOG_POLICY_OUTPUT_KEY,
        SAFE_REDIRECT_POLICY_OUTPUT_KEY,
    ):
        policy = _as_dict(risk_policy.get(output_key)) or _as_dict(combined_outputs.get(output_key)) or _as_dict(derived_outputs.get(output_key))
        if policy:
            normalized_outputs[output_key] = policy
    return normalized_outputs


def _assemble_layer3_safety_outputs(collection: Dict[str, Any]) -> Dict[str, Any]:
    layer_3 = {}
    for module_id, output_key in LAYER3_SAFETY_POLICY_MODULES:
        policy = _layer3_safety_module_policy(collection, module_id)
        if policy:
            layer_3[output_key] = policy
    layer_3.update(_risk_response_module_outputs(collection))
    if not layer_3:
        return {}
    return {
        "layer_3": layer_3,
    }


def _synchronize_layer3_module_outputs(collection: Dict[str, Any]) -> None:
    """Write the compiled safety decision back to the canonical module list."""
    modules = {
        module.get("module_id"): module
        for module in collection.get("modules", [])
        if isinstance(module, dict)
    }
    for module_id, output_key in LAYER3_SAFETY_POLICY_MODULES:
        module = modules.get(module_id)
        policy = _layer3_safety_module_policy(collection, module_id)
        if isinstance(module, dict) and policy:
            _set_compiled_module_output(module, output_key, policy)

    risk_module = modules.get(RISK_RESPONSE_MODULE_ID)
    if isinstance(risk_module, dict):
        for output_key, output in _risk_response_module_outputs(collection).items():
            if isinstance(output, dict) and output:
                _set_compiled_module_output(risk_module, output_key, output)


def _merge_layer3_safety_into_safety_policy(payload: Dict[str, Any]) -> None:
    graph_snapshot = _as_dict(payload.get("graph_snapshot"))
    layer_outputs = _as_dict(graph_snapshot.get("layer_outputs"))
    layer_3 = _as_dict(layer_outputs.get("layer_3"))
    layer3_policies = {output_key: _as_dict(layer_3.get(output_key)) for output_key in _LAYER3_SAFETY_TOP_LEVEL_OUTPUT_KEYS if _as_dict(layer_3.get(output_key))}
    if not layer3_policies:
        return
    safety_policy = _as_dict(payload.get("safety_policy"))
    safety_policy.update(
        {
            "no_secret_in_dr": safety_policy.get("no_secret_in_dr", True),
            "no_direct_provider_binding": safety_policy.get("no_direct_provider_binding", True),
            "not_executable": safety_policy.get("not_executable", True),
        }
    )
    safety_policy.update(layer3_policies)
    payload["safety_policy"] = safety_policy


def _module_nodes_by_type(module: Dict[str, Any], node_type: str) -> List[Dict[str, Any]]:
    return [node for node in _module_graph_nodes(module) if node.get("node_type") == node_type]


def _checkbox_config_from_node(node: Dict[str, Any]) -> Dict[str, Any]:
    params = _as_dict(node.get("params"))
    if "checkbox_config" in params:
        return _as_dict(params.get("checkbox_config"))
    return _as_dict(params.get("checklist_config"))


def _behavior_reference_payload(reference: Dict[str, Any]) -> Dict[str, Any]:
    layer_id = _nonempty_str(reference.get("layer_id") or reference.get("source_layer_id"))
    module_id = _nonempty_str(reference.get("module_id") or reference.get("source_module_id"))
    field_id = _nonempty_str(reference.get("field_id") or reference.get("source_node_id"))
    path = _nonempty_str(reference.get("path")) or "/".join(item for item in (layer_id, module_id, field_id) if item)
    return {
        "reference_id": _nonempty_str(reference.get("reference_id")),
        "reference_type": _nonempty_str(reference.get("reference_type")) or "optional",
        "layer_id": layer_id,
        "module_id": module_id,
        "field_id": field_id,
        "path": path,
        "usage": _nonempty_str(reference.get("usage")),
        "usage_key": _nonempty_str(reference.get("usage_key")),
    }


def _behavior_field_references(module: Dict[str, Any]) -> List[Dict[str, Any]]:
    field_reference_nodes = [
        *_module_nodes_by_type(module, "field_reference"),
        *_module_nodes_by_type(module, "reference_input"),
    ]
    references: List[Dict[str, Any]] = []
    for node in field_reference_nodes:
        params = _as_dict(node.get("params"))
        outputs = _as_dict(node.get("outputs"))
        raw_references = outputs.get("field_references") or params.get("references")
        if not isinstance(raw_references, list) or not raw_references:
            raw_references = params.get("recommended_references")
        if not isinstance(raw_references, list):
            continue
        for reference in raw_references:
            if not isinstance(reference, dict):
                continue
            if reference.get("reference_type") == "forbidden":
                continue
            payload = _behavior_reference_payload(reference)
            if payload["layer_id"] and payload["module_id"] and payload["field_id"]:
                references.append(payload)
    deduped: Dict[str, Dict[str, Any]] = {}
    for reference in references:
        key = str(reference.get("path") or reference.get("reference_id"))
        if key:
            deduped[key] = reference
    return list(deduped.values())


def _behavior_checkbox_summary(module: Dict[str, Any]) -> Dict[str, Any]:
    selected_options: List[str] = []
    validation_rules: List[str] = []
    custom_texts: List[str] = []
    preset_id = ""

    for node in _module_nodes_by_type(module, "text_config"):
        checkbox_config = _checkbox_config_from_node(node)
        if not checkbox_config:
            continue
        if not preset_id:
            preset_id = _nonempty_str(checkbox_config.get("preset_id"))
        node_selected = checkbox_config.get("selected_options")
        local_node_id = _nonempty_str(node.get("catalog_node_id") or node.get("node_id")).split("::")[-1]
        is_language_output = (
            module.get("module_id") == LANGUAGE_BEHAVIOR_MODULE_ID
            and local_node_id == "language_behavior_output_expression"
        )
        if not isinstance(node_selected, list) and is_language_output:
            configured_defaults = checkbox_config.get("default_selected_options")
            if isinstance(configured_defaults, list):
                node_selected = configured_defaults
            else:
                default_options = checkbox_config.get("default_options")
                node_selected = [
                    option.get("option_id")
                    for option in default_options
                    if isinstance(option, dict) and option.get("default_selected") is not False
                ] if isinstance(default_options, list) else []
            node_selected = [option for option in node_selected if option != "occasional_city_imagery"]
        elif not isinstance(node_selected, list):
            node_selected = []
        selected_options.extend(str(option) for option in node_selected if isinstance(option, str) and option)
        if str(node.get("node_id", "")).endswith("_validation"):
            validation_rules.extend(str(option) for option in node_selected if isinstance(option, str) and option)
        custom_text = _nonempty_str(checkbox_config.get("custom_text"))
        if custom_text:
            custom_texts.append(custom_text)

    return {
        "preset_id": preset_id,
        "selected_options": list(dict.fromkeys(selected_options)),
        "custom_text": "\n\n".join(custom_texts),
        "validation_rules": list(dict.fromkeys(validation_rules)),
    }


def _behavior_module_policy(module: Dict[str, Any], policy_key: str, default_preset_id: str) -> Dict[str, Any]:
    checkbox_summary = _behavior_checkbox_summary(module)
    source_nodes = [
        str(node.get("node_id"))
        for node in _module_graph_nodes(module)
        if (
            module.get("module_id")
            not in _LAYER8_MATERIALIZED_OUTPUT_MODULE_IDS
            or node.get("node_type") not in {"module_output", "reference_output"}
        )
        and isinstance(node.get("node_id"), str)
        and node.get("node_id")
    ]
    return {
        "module_id": module.get("module_id"),
        "source_module_id": module.get("module_id"),
        "module_type": module.get("module_type"),
        "policy_key": policy_key,
        "preset_id": checkbox_summary["preset_id"] or default_preset_id,
        "selected_options": checkbox_summary["selected_options"],
        "custom_text": checkbox_summary["custom_text"],
        "field_references": _behavior_field_references(module),
        "validation_rules": checkbox_summary["validation_rules"],
        "tags": [str(tag) for tag in module.get("tags", []) if isinstance(tag, str)],
        "source_nodes": source_nodes,
    }


def _synchronize_layer8_validation_results(
    collection: Dict[str, Any], findings: List[Dict[str, str]]
) -> None:
    """Finalize Layer 8 validation nodes from the compiler-owned configuration."""
    modules = {
        module.get("module_id"): module
        for module in collection.get("modules", [])
        if isinstance(module, dict)
    }
    valid_count = 0
    for module_id, policy_key, preset_id in _LAYER8_BEHAVIOR_MODULES:
        module = modules.get(module_id)
        reasons: List[str] = []
        validation_nodes: List[Dict[str, Any]] = []
        if not isinstance(module, dict):
            reasons.append("module is missing")
        else:
            validation_nodes = [
                node
                for node in _module_nodes_by_type(module, "text_config")
                if _nonempty_str(_as_dict(node.get("params")).get("config_mode")).endswith("_validation")
            ]
            if len(validation_nodes) != 1:
                reasons.append(f"expected one validation node, got {len(validation_nodes)}")
            else:
                checkbox_config = _checkbox_config_from_node(validation_nodes[0])
                selected = set(_string_list(checkbox_config.get("selected_options")))
                required = set(_string_list(checkbox_config.get("default_selected_options")))
                if not checkbox_config:
                    reasons.append("validation checkbox configuration is missing")
                if not selected:
                    reasons.append("no validation rules are selected")
                missing_rules = sorted(required - selected)
                if missing_rules:
                    reasons.append(f"required validation rules are not selected: {missing_rules!r}")
                if any(not rule.startswith("check_") for rule in selected):
                    reasons.append("validation rule ids must use the check_ prefix")

            policy = _behavior_module_policy(module, policy_key, preset_id)
            if not _nonempty_str(policy.get("preset_id")):
                reasons.append("behavior preset is missing")
            if not _string_list(policy.get("selected_options")):
                reasons.append("behavior output has no selected options")
            if not _string_list(policy.get("validation_rules")):
                reasons.append("behavior output has no validation rules")

        result = "pass" if not reasons else "invalid"
        for node in validation_nodes:
            params = node.get("params") if isinstance(node.get("params"), dict) else {}
            params["validation_result"] = result
            node["params"] = params
        if reasons:
            findings.append(
                _finding(
                    "FAIL",
                    "DR_LAYER8_VALIDATION_INCOMPLETE",
                    f"Layer 8 module {module_id!r} validation could not be finalized: " + "; ".join(reasons),
                    f"payload.modules.{module_id}.module_graph.validation",
                )
            )
        else:
            valid_count += 1

    if valid_count == len(_LAYER8_BEHAVIOR_MODULES):
        optional_profile_present = _LAYER8_OPTIONAL_DIALOGUE_RUNTIME_PROFILE_ID in modules
        selected_module_count = valid_count + int(optional_profile_present)
        optional_profile_detail = (
            ", and the optional dialogue runtime profile is validated by its dedicated contract"
            if optional_profile_present
            else ""
        )
        findings.append(
            _finding(
                "PASS",
                "DR_LAYER8_VALIDATION_FINALIZED",
                f"Layer 8 includes {selected_module_count} selected behavior modules: all "
                f"{valid_count} core behavior modules selected their required compile-time "
                f"validation rules{optional_profile_detail}",
                "payload.modules.layer_8",
            )
        )


def _assemble_layer8_behavior_outputs(collection: Dict[str, Any]) -> Dict[str, Any]:
    modules = {module.get("module_id"): module for module in collection.get("modules", []) if isinstance(module, dict)}
    materialized_output_keys = {
        module_id: output_key
        for module_id, _policy_key, _preset_id, output_key in (
            _LAYER8_MATERIALIZED_OUTPUTS
        )
    }
    behavior_modules: Dict[str, Any] = {}
    for module_id, policy_key, preset_id in _LAYER8_BEHAVIOR_MODULES:
        module = modules.get(module_id)
        if isinstance(module, dict):
            output_key = materialized_output_keys.get(module_id)
            materialized_output = (
                _compiled_module_output(module, output_key)
                if output_key
                else {}
            )
            behavior_modules[policy_key] = (
                materialized_output
                if materialized_output
                else _behavior_module_policy(
                    module, policy_key, preset_id
                )
            )

    if not behavior_modules:
        return {}

    behavior_policy = {
        "schema_version": "0.1",
        "source_layer": "layer_8",
        "modules": behavior_modules,
    }
    return {
        "behavior_policy": behavior_policy,
        "layer_8": {
            "behavior_policy": behavior_policy,
            "module_count": len(behavior_modules),
            "core_module_ids": list(_LAYER8_CORE_BEHAVIOR_MODULE_IDS),
            "excluded_modules": [module_id for module_id in _LAYER8_EXCLUDED_BEHAVIOR_MODULE_IDS if module_id in modules],
            "validation_result": "pass" if len(behavior_modules) == len(_LAYER8_BEHAVIOR_MODULES) else "partial",
        },
    }


def _merge_layer8_behavior_into_payload(payload: Dict[str, Any]) -> None:
    graph_snapshot = _as_dict(payload.get("graph_snapshot"))
    layer_outputs = _as_dict(graph_snapshot.get("layer_outputs"))
    behavior_policy = _as_dict(layer_outputs.get("behavior_policy")) or _as_dict(_as_dict(layer_outputs.get("layer_8")).get("behavior_policy"))
    if not behavior_policy:
        return
    payload["behavior_policy"] = behavior_policy
    resident_blueprint = _as_dict(payload.get("resident_blueprint"))
    resident_blueprint["behavior_policy"] = behavior_policy
    payload["resident_blueprint"] = resident_blueprint


def _configured_module_field_value(
    collection: Dict[str, Any], module_id: str, field_id: str
) -> tuple[bool, Any]:
    """Read an optional compile-time field without inventing it for old canvases."""

    module = next(
        (
            candidate
            for candidate in collection.get("modules", [])
            if isinstance(candidate, dict) and candidate.get("module_id") == module_id
        ),
        None,
    )
    if not isinstance(module, dict):
        return False, None
    for node in _module_graph_nodes(module):
        params = node.get("params") if isinstance(node.get("params"), dict) else {}
        fields = params.get("fields") if isinstance(params.get("fields"), list) else []
        for field in fields:
            if not isinstance(field, dict):
                continue
            configured_id = _nonempty_str(field.get("field_id")) or _nonempty_str(field.get("field_key"))
            if configured_id != field_id:
                continue
            value = field.get("value") if "value" in field else field.get("field_value")
            return True, deepcopy(value)
    return False, None


def _assemble_first_greeting_config_extensions(collection: Dict[str, Any]) -> Dict[str, Any]:
    """Project Stage 7.4.8 optional config groups into the existing payload envelope."""

    extensions: Dict[str, Any] = {}
    found, first_interaction = _configured_module_field_value(
        collection, INTERACTION_BEHAVIOR_MODULE_ID, "first_interaction"
    )
    if found and isinstance(first_interaction, dict):
        extensions["behavior"] = {"first_interaction": first_interaction}

    expression: Dict[str, Any] = {}
    for field_id in ("first_greeting", "first_presence"):
        found, value = _configured_module_field_value(collection, "visual_style", field_id)
        if found and isinstance(value, dict):
            expression[field_id] = value
    if expression:
        extensions["expression"] = expression

    found, initial_relationship = _configured_module_field_value(
        collection, "user_relationship", "initial_relationship"
    )
    if found and isinstance(initial_relationship, dict):
        extensions["relationship"] = {"initial_relationship": initial_relationship}
    return extensions


def _validate_first_interaction_max_active_prompts(
    collection: Dict[str, Any], findings: List[Dict[str, str]]
) -> None:
    """Reject invalid raw values; Canvas compatibility normalization happens before compile."""

    found, first_interaction = _configured_module_field_value(
        collection, INTERACTION_BEHAVIOR_MODULE_ID, "first_interaction"
    )
    if not found:
        return

    missing = object()
    value: Any = missing
    if isinstance(first_interaction, dict):
        scenes = first_interaction.get("scenes")
        if isinstance(scenes, dict):
            user_silence = scenes.get("user_silence")
            if isinstance(user_silence, dict):
                value = user_silence.get("max_active_prompts", missing)

    if isinstance(value, int) and not isinstance(value, bool) and 0 <= value <= 1:
        return

    actual = "missing" if value is missing else repr(value)
    findings.append(
        _finding(
            "FAIL",
            "DR_FIRST_INTERACTION_MAX_ACTIVE_PROMPTS_INVALID",
            f"max_active_prompts must be an integer in range 0-1; got {actual}",
            "payload.behavior.first_interaction.scenes.user_silence.max_active_prompts",
        )
    )


def _compiled_module_output(module: Dict[str, Any], output_key: str) -> Dict[str, Any]:
    node_output = _module_output_node_value(module, output_key)
    if isinstance(node_output, dict):
        return deepcopy(node_output)
    module_outputs = module.get("outputs") if isinstance(module.get("outputs"), dict) else {}
    fallback = module_outputs.get(output_key)
    return deepcopy(fallback) if isinstance(fallback, dict) else {}


def _set_compiled_module_output(module: Dict[str, Any], output_key: str, value: Dict[str, Any]) -> None:
    outputs = module.get("outputs") if isinstance(module.get("outputs"), dict) else {}
    outputs[output_key] = deepcopy(value)
    module["outputs"] = outputs
    for node in _module_graph_nodes(module):
        node_outputs = node.get("outputs") if isinstance(node.get("outputs"), dict) else {}
        node_params = node.get("params") if isinstance(node.get("params"), dict) else {}
        if output_key in node_outputs or (
            node.get("node_type") == "module_output" and node_params.get("output_key") == output_key
        ):
            node_outputs[output_key] = deepcopy(value)
            node["outputs"] = node_outputs


def _catalog_module_output(module_id: str, output_key: str) -> Dict[str, Any]:
    catalog_module = next(
        (
            candidate.model_dump(mode="json")
            for candidate in get_module_catalog()
            if candidate.module_id == module_id
        ),
        {},
    )
    return _compiled_module_output(catalog_module, output_key)


def _synchronize_runtime_projection_source_outputs(
    collection: Dict[str, Any],
    findings: List[Dict[str, str]],
) -> None:
    """Normalize current editable fields before A3 reads Module Output."""

    modules = {
        module.get("module_id"): module
        for module in collection.get("modules", [])
        if isinstance(module, dict)
    }
    rebuilt_paths: List[str] = []
    missing_paths: List[str] = []
    for module_id, output_key in _RUNTIME_PROJECTION_NORMALIZED_OUTPUTS:
        module = modules.get(module_id)
        output_path = f"payload.modules.{module_id}.outputs.{output_key}"
        if not isinstance(module, dict):
            missing_paths.append(output_path)
            continue
        fields = _module_fields_from_field_input(module)
        current_output = _compiled_module_output(module, output_key)
        if not current_output and fields:
            current_output = _catalog_module_output(module_id, output_key)
            rebuilt_paths.append(output_path)
        if not current_output:
            missing_paths.append(output_path)
            continue
        normalized_output = _module_output_with_field_values(
            current_output, fields
        )
        _set_compiled_module_output(module, output_key, normalized_output)

    if rebuilt_paths:
        findings.append(
            _finding(
                "WARNING",
                "DR_PROJECTION_SOURCE_NODE_NORMALIZED",
                (
                    "Current node fields were normalized into missing module "
                    "outputs before runtime projection: "
                    + ", ".join(sorted(rebuilt_paths))
                ),
                "payload.modules",
            )
        )
    if missing_paths:
        findings.append(
            _finding(
                "WARNING",
                "DR_PROJECTION_SOURCE_MISSING",
                (
                    "Runtime projection sources are missing and will use "
                    "protocol compatibility fallbacks where allowed: "
                    + ", ".join(sorted(missing_paths))
                ),
                "payload.runtime_dialogue_projection",
            )
        )


def _runtime_projection_module_output(
    modules: Dict[str, Dict[str, Any]],
    module_id: str,
    output_key: str,
) -> Dict[str, Any]:
    module = modules.get(module_id)
    return (
        _compiled_module_output(module, output_key)
        if isinstance(module, dict)
        else {}
    )


def _selected_mapping(value: Any, *keys: str) -> Dict[str, Any]:
    source = _as_dict(value)
    return {
        key: deepcopy(source[key])
        for key in keys
        if key in source
    }


def _assemble_runtime_dialogue_policy_values(
    collection: Dict[str, Any],
    memory_policy_extensions: Dict[str, Any],
    findings: List[Dict[str, str]],
) -> Dict[str, Dict[str, Any]]:
    """Derive existing runtime policies from current Layer 5/11/12 outputs."""

    modules = {
        str(module.get("module_id")): module
        for module in collection.get("modules", [])
        if isinstance(module, dict) and module.get("module_id")
    }
    derived = deepcopy(_RUNTIME_DIALOGUE_DERIVED_VALUE_DEFAULTS)
    fallback_sections: List[str] = []

    short_term = _as_dict(memory_policy_extensions.get("short_term_memory"))
    preference = _as_dict(memory_policy_extensions.get("preference_memory"))
    event = _as_dict(memory_policy_extensions.get("event_memory"))
    relationship_memory = _as_dict(
        memory_policy_extensions.get("relationship_memory")
    )
    memory_update = _as_dict(
        memory_policy_extensions.get("memory_update")
    )
    memory_access = _as_dict(
        memory_policy_extensions.get("memory_access_control")
    )
    memory_router = _as_dict(
        memory_policy_extensions.get("memory_provider_router")
    )
    if all(
        (
            short_term,
            preference,
            event,
            relationship_memory,
            memory_update,
            memory_access,
            memory_router,
        )
    ):
        derived["memory_usage_policy"] = {
            "memory_access_limits": {
                **_selected_mapping(
                    memory_access,
                    "permission_policy",
                    "recall_claim_policy",
                    "policy_actions",
                ),
                **_selected_mapping(
                    memory_router,
                    "resident_scope",
                    "namespace_policy",
                    "memory_type_policy",
                ),
            },
            "memory_write_limits": _selected_mapping(
                memory_update,
                "allowed_operations",
                "policy_priority",
                "confirmation_policy",
                "conflict_policy",
                "write_boundary",
                "no_dr_writeback",
                "no_raw_sensitive_content",
                "no_multi_resident_memory_share",
            ),
            "sensitive_memory_handling": {
                **_selected_mapping(memory_access, "sensitive_policy"),
                "preference_save_forbidden": deepcopy(
                    preference.get("save_forbidden", [])
                ),
                "event_save_forbidden": deepcopy(
                    event.get("save_forbidden", [])
                ),
            },
            "narrative_memory_usage_rules": {
                "event_memory": _selected_mapping(
                    event, "save_allowed", "save_forbidden"
                ),
                "relationship_memory": _selected_mapping(
                    relationship_memory,
                    "allowed_content",
                    "forbidden_content",
                    "change_policy",
                ),
            },
            "conversation_and_long_term_boundary": {
                "short_term_memory": _selected_mapping(
                    short_term,
                    "retention",
                    "expires_on",
                    "allowed_content",
                    "forbidden_content",
                    "session_scoped_only",
                ),
                "preference_memory": _selected_mapping(
                    preference, "save_allowed", "save_forbidden"
                ),
                "event_memory": _selected_mapping(
                    event, "save_allowed", "save_forbidden"
                ),
                "relationship_memory": _selected_mapping(
                    relationship_memory,
                    "change_policy",
                    "allowed_content",
                    "forbidden_content",
                ),
            },
        }
    else:
        fallback_sections.append("memory_usage_policy")

    relationship_values: Dict[str, Any] = {}
    for module_id, output_key, derived_key in (
        _RUNTIME_RELATIONSHIP_POLICY_OUTPUTS
    ):
        output = _runtime_projection_module_output(
            modules, module_id, output_key
        )
        fields = _as_dict(output.get("fields"))
        if fields:
            relationship_values[derived_key] = {
                key: deepcopy(value)
                for key, value in fields.items()
                if not (
                    derived_key == "user_relationship"
                    and key == "initial_relationship"
                )
            }
        else:
            fallback_sections.append(
                f"relationship_policy.{derived_key}"
            )
    if relationship_values:
        derived["relationship_policy"].update(relationship_values)

    self_awareness = _runtime_projection_module_output(
        modules, "self_awareness", "self_awareness_config"
    )
    growth = _runtime_projection_module_output(
        modules,
        "growth_plan",
        "growth_identity_continuity_governance_config",
    )
    self_fields = _as_dict(self_awareness.get("fields"))
    resolved_facts = _as_dict(self_awareness.get("resolved_facts"))
    capability_awareness = _as_dict(
        self_awareness.get("capability_awareness")
    )
    limitation_awareness = _as_dict(
        self_awareness.get("limitation_awareness")
    )
    if self_awareness:
        capability_scope = deepcopy(
            self_fields.get(
                "capability_scope",
                capability_awareness.get("allowed", []),
            )
        )
        capability_limits = deepcopy(
            self_fields.get(
                "capability_limits",
                limitation_awareness.get("limits", []),
            )
        )
        relationship_awareness = deepcopy(
            _as_dict(self_awareness.get("relationship_awareness"))
        )
        if "default_relationship_role" in resolved_facts:
            relationship_awareness["default_role"] = deepcopy(
                resolved_facts["default_relationship_role"]
            )
        derived["self_disclosure_policy"].update(
            {
                "resolved_facts": deepcopy(resolved_facts),
                "relationship_awareness": relationship_awareness,
                "immutable_core": deepcopy(
                    self_fields.get(
                        "immutable_core",
                        self_awareness.get("immutable_core", []),
                    )
                ),
                "real_human_boundary": bool(
                    self_fields.get(
                        "real_human_boundary",
                        self_awareness.get("real_human_boundary", True),
                    )
                ),
            }
        )
        derived["advice_policy"] = {
            "capability_scope": capability_scope,
            "capability_limits": capability_limits,
            "real_human_boundary": bool(
                self_fields.get(
                    "real_human_boundary",
                    self_awareness.get("real_human_boundary", True),
                )
            ),
        }
    else:
        fallback_sections.extend(
            ("self_disclosure_policy.self_awareness", "advice_policy")
        )

    if growth:
        derived["self_disclosure_policy"]["growth_limits"] = (
            _selected_mapping(
                growth,
                "growth_governance_status",
                "authorization_status",
                "adaptation_allowed",
                "allowed_change_amplitude",
                "identity_continuity_status",
                "save_allowed",
                "long_term_memory_write_allowed",
                "user_confirmation_required",
                "rollback_required",
                "rollback_conditions",
                "forbidden_change_reason",
            )
        )
    else:
        fallback_sections.append("self_disclosure_policy.growth_limits")

    if fallback_sections:
        findings.append(
            _finding(
                "WARNING",
                "DR_PROJECTION_COMPATIBILITY_FALLBACK",
                (
                    "Runtime dialogue projection used protocol compatibility "
                    "fallbacks for missing deep values: "
                    + ", ".join(sorted(set(fallback_sections)))
                ),
                "payload.runtime_dialogue_projection",
            )
        )
    return derived


def _ensure_layer8_materialized_output_nodes(
    module: Dict[str, Any],
    catalog_module: Dict[str, Any],
) -> None:
    """Add the one derived output chain missing from pre-A2 Canvas copies."""

    graph = (
        module.get("module_graph")
        if isinstance(module.get("module_graph"), dict)
        else {}
    )
    nodes = (
        graph.get("nodes") if isinstance(graph.get("nodes"), list) else []
    )
    seed_nodes = _module_graph_nodes(catalog_module)

    for node_type in ("module_output", "reference_output"):
        if any(
            isinstance(node, dict) and node.get("node_type") == node_type
            for node in nodes
        ):
            continue
        seed_node = next(
            (
                node
                for node in seed_nodes
                if node.get("node_type") == node_type
            ),
            None,
        )
        if isinstance(seed_node, dict):
            nodes.append(deepcopy(seed_node))

    module_output_node = next(
        (
            node
            for node in nodes
            if isinstance(node, dict)
            and node.get("node_type") == "module_output"
        ),
        None,
    )
    reference_output_node = next(
        (
            node
            for node in nodes
            if isinstance(node, dict)
            and node.get("node_type") == "reference_output"
        ),
        None,
    )
    validation_node = next(
        (
            node
            for node in nodes
            if isinstance(node, dict)
            and node.get("node_type") == "text_config"
            and _module_graph_node_id(node).endswith("_validation")
        ),
        None,
    )
    if not all(
        isinstance(node, dict)
        for node in (validation_node, module_output_node, reference_output_node)
    ):
        graph["nodes"] = nodes
        module["module_graph"] = graph
        return

    validation_node_id = _module_graph_node_id(validation_node)
    module_output_node_id = _module_graph_node_id(module_output_node)
    reference_output_node_id = _module_graph_node_id(reference_output_node)
    for node, input_node_id in (
        (module_output_node, validation_node_id),
        (reference_output_node, module_output_node_id),
    ):
        params = (
            node.get("params")
            if isinstance(node.get("params"), dict)
            else {}
        )
        params["input"] = input_node_id
        params["content_revision"] = STAGE7_4_12_A2_CONTENT_REVISION
        node["params"] = params

    edges = (
        graph.get("edges") if isinstance(graph.get("edges"), list) else []
    )
    existing_pairs = {
        (
            _nonempty_str(edge.get("source")),
            _nonempty_str(edge.get("target")),
        )
        for edge in edges
        if isinstance(edge, dict)
    }
    for source, target in (
        (validation_node_id, module_output_node_id),
        (module_output_node_id, reference_output_node_id),
    ):
        if (source, target) in existing_pairs:
            continue
        edges.append(
            {
                "edge_id": f"{source}_to_{target}",
                "source": source,
                "source_port": "p_out",
                "target": target,
                "target_port": "p_in",
            }
        )
        existing_pairs.add((source, target))

    graph["nodes"] = nodes
    graph["edges"] = edges
    graph["source_output_identity_cleanup_revision"] = (
        STAGE7_4_12_A2_CONTENT_REVISION
    )
    module["module_graph"] = graph
    config = (
        module.get("config") if isinstance(module.get("config"), dict) else {}
    )
    config["source_output_identity_cleanup_revision"] = (
        STAGE7_4_12_A2_CONTENT_REVISION
    )
    module["config"] = config


def _synchronize_layer8_behavior_module_outputs(
    collection: Dict[str, Any],
) -> None:
    """Mirror current Layer 8 checkbox rules into each source module output."""

    modules = {
        module.get("module_id"): module
        for module in collection.get("modules", [])
        if isinstance(module, dict)
    }
    catalog_modules = {
        item.module_id: item.model_dump(mode="json")
        for item in get_module_catalog()
        if item.module_id in _LAYER8_MATERIALIZED_OUTPUT_MODULE_IDS
    }
    for module_id, policy_key, preset_id, output_key in (
        _LAYER8_MATERIALIZED_OUTPUTS
    ):
        module = modules.get(module_id)
        if not isinstance(module, dict):
            continue
        catalog_module = catalog_modules.get(module_id)
        if isinstance(catalog_module, dict):
            _ensure_layer8_materialized_output_nodes(
                module, catalog_module
            )
        output = _behavior_module_policy(module, policy_key, preset_id)
        _set_compiled_module_output(module, output_key, output)
        for node in _module_graph_nodes(module):
            if node.get("node_type") != "reference_output":
                continue
            node_outputs = (
                node.get("outputs")
                if isinstance(node.get("outputs"), dict)
                else {}
            )
            node_outputs[output_key] = deepcopy(output)
            node["outputs"] = node_outputs


def _meaningful_fact_value(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, dict)):
        return bool(value)
    return True


def _module_fact_source_value(
    module: Dict[str, Any],
    output_key: str,
    field_key: str,
) -> tuple[bool, Any, str]:
    current_fields = _module_field_values_from_fields(
        _module_fields_from_field_input(module)
    )
    current_value = current_fields.get(field_key)
    if _meaningful_fact_value(current_value):
        return True, deepcopy(current_value), "current_source_node"

    config = _as_dict(module.get("config"))
    for config_fields in (
        _as_dict(config.get("field_values")),
        _as_dict(_as_dict(config.get(output_key)).get("fields")),
    ):
        config_value = config_fields.get(field_key)
        if _meaningful_fact_value(config_value):
            return True, deepcopy(config_value), "source_structured_config"

    node_output = _module_output_node_value(module, output_key)
    node_fields = _as_dict(_as_dict(node_output).get("fields"))
    node_value = node_fields.get(field_key)
    if _meaningful_fact_value(node_value):
        return True, deepcopy(node_value), "source_module_output"

    module_output = _as_dict(_as_dict(module.get("outputs")).get(output_key))
    mirror_value = _as_dict(module_output.get("fields")).get(field_key)
    if _meaningful_fact_value(mirror_value):
        return True, deepcopy(mirror_value), "compatibility_mirror"
    return False, None, "safe_default"


def _synchronize_self_awareness_fact_sources(
    collection: Dict[str, Any],
) -> None:
    modules = {
        module.get("module_id"): module
        for module in collection.get("modules", [])
        if isinstance(module, dict)
    }
    module = modules.get("self_awareness")
    if not isinstance(module, dict):
        return

    output_key = "self_awareness_config"
    output = _compiled_module_output(module, output_key)
    for field in _module_fields_from_field_input(module):
        field_key = _nonempty_str(
            field.get("field_key") or field.get("field_id")
        )
        binding = SELF_AWARENESS_FACT_SOURCE_BINDINGS.get(field_key)
        if not isinstance(binding, dict):
            continue
        field["value_role"] = "compatibility_fallback"
        field["reference_enabled"] = True
        field["source_binding"] = deepcopy(binding)
        field["source_priority"] = [
            "current_source_node",
            "source_structured_config",
            "source_module_output",
            "compatibility_fallback",
            "safe_default",
        ]

    for node in _module_graph_nodes(module):
        if node.get("node_type") != "reference_input":
            continue
        params = (
            node.get("params")
            if isinstance(node.get("params"), dict)
            else {}
        )
        params["fact_source_bindings"] = deepcopy(
            SELF_AWARENESS_FACT_SOURCE_BINDINGS
        )
        params["content_revision"] = STAGE7_4_12_A2_CONTENT_REVISION
        node["params"] = params

    config = (
        module.get("config") if isinstance(module.get("config"), dict) else {}
    )
    config["fact_source_bindings"] = deepcopy(
        SELF_AWARENESS_FACT_SOURCE_BINDINGS
    )
    config["source_output_identity_cleanup_revision"] = (
        STAGE7_4_12_A2_CONTENT_REVISION
    )
    module["config"] = config
    graph = (
        module.get("module_graph")
        if isinstance(module.get("module_graph"), dict)
        else {}
    )
    graph["fact_source_bindings"] = deepcopy(
        SELF_AWARENESS_FACT_SOURCE_BINDINGS
    )
    graph["source_output_identity_cleanup_revision"] = (
        STAGE7_4_12_A2_CONTENT_REVISION
    )
    module["module_graph"] = graph

    compatibility_fields = _module_field_values_from_fields(
        _module_fields_from_field_input(module)
    )
    if not compatibility_fields:
        compatibility_fields = deepcopy(_as_dict(output.get("fields")))

    resolved_facts: Dict[str, Any] = {}
    resolved_sources: Dict[str, Any] = {}
    for field_key, binding in SELF_AWARENESS_FACT_SOURCE_BINDINGS.items():
        source_module_id = _nonempty_str(binding.get("source_module_id"))
        source_output_key = _nonempty_str(binding.get("source_output_key"))
        source_field_key = _nonempty_str(binding.get("source_field_key"))
        source_module = modules.get(source_module_id)
        found = False
        value: Any = None
        source_kind = "safe_default"
        if isinstance(source_module, dict):
            found, value, source_kind = _module_fact_source_value(
                source_module,
                source_output_key,
                source_field_key,
            )
        if not found:
            fallback = compatibility_fields.get(field_key)
            if _meaningful_fact_value(fallback):
                value = deepcopy(fallback)
                source_kind = "compatibility_fallback"
            else:
                value = ""
                source_kind = "safe_default"
        resolved_facts[field_key] = value
        resolved_sources[field_key] = {
            **deepcopy(binding),
            "selected_source": source_kind,
            "used_compatibility_fallback": (
                source_kind == "compatibility_fallback"
            ),
        }

    output["fields"] = deepcopy(compatibility_fields)
    output["resolved_facts"] = resolved_facts
    output["resolved_fact_sources"] = resolved_sources
    output["fact_source_policy"] = {
        "priority": [
            "current_source_node",
            "source_structured_config",
            "source_module_output",
            "compatibility_fallback",
            "safe_default",
        ],
        "authoritative_fact_path": "resolved_facts",
        "compatibility_field_path": "fields",
        "compatibility_fields_may_override_current_facts": False,
        "bindings": deepcopy(SELF_AWARENESS_FACT_SOURCE_BINDINGS),
    }
    output["content_revision"] = STAGE7_4_12_A2_CONTENT_REVISION
    _set_compiled_module_output(module, output_key, output)


def _valid_first_greeting_variant(value: Any) -> bool:
    if isinstance(value, str):
        return bool(value.strip())
    if not isinstance(value, dict):
        return False
    text = value.get("text")
    return isinstance(text, str) and bool(text.strip())


def _catalog_visual_style_reference_declarations() -> List[Dict[str, Any]]:
    catalog_module = next(
        (
            candidate.model_dump(mode="json")
            for candidate in get_module_catalog()
            if candidate.module_id == "visual_style"
        ),
        {},
    )
    reference_input = _module_node_by_type(catalog_module, "reference_input")
    params = (
        reference_input.get("params")
        if isinstance(reference_input, dict)
        and isinstance(reference_input.get("params"), dict)
        else {}
    )
    references = params.get("references")
    if not isinstance(references, list):
        return []
    return [reference for reference in references if isinstance(reference, dict)]


def _visual_style_reference_summary(
    collection: Dict[str, Any], module: Dict[str, Any], references: List[Any]
) -> tuple[List[Dict[str, Any]], List[str]]:
    config = module.get("config") if isinstance(module.get("config"), dict) else {}
    instance_declarations = (
        config.get("reference_sources")
        if isinstance(config.get("reference_sources"), list)
        else []
    )
    canonical_declarations = _catalog_visual_style_reference_declarations()
    declarations = [*instance_declarations, *canonical_declarations]
    canonical_by_reference_id = {
        _nonempty_str(declaration.get("reference_id")): declaration
        for declaration in canonical_declarations
        if _nonempty_str(declaration.get("reference_id"))
    }
    declarations_by_source = {
        (
            _nonempty_str(declaration.get("source_module_id")),
            _nonempty_str(declaration.get("source_node_id")),
        ): declaration
        for declaration in declarations
        if isinstance(declaration, dict)
        and _nonempty_str(declaration.get("source_module_id"))
        and _nonempty_str(declaration.get("source_node_id"))
        and _nonempty_str(declaration.get("reference_id"))
    }
    declarations_by_reference_id = {
        _nonempty_str(declaration.get("reference_id")): declaration
        for declaration in declarations
        if isinstance(declaration, dict)
        and _nonempty_str(declaration.get("reference_id"))
    }
    declarations_by_module = {
        _nonempty_str(declaration.get("source_module_id")): declaration
        for declaration in declarations
        if isinstance(declaration, dict)
        and _nonempty_str(declaration.get("source_module_id"))
        and _nonempty_str(declaration.get("reference_id"))
    }
    modules_by_id = {
        _nonempty_str(candidate.get("module_id")): candidate
        for candidate in collection.get("modules", [])
        if isinstance(candidate, dict) and _nonempty_str(candidate.get("module_id"))
    }
    summary: List[Dict[str, Any]] = []
    issues: List[str] = []
    for reference in references:
        if not isinstance(reference, dict):
            continue
        source_layer_id = _nonempty_str(reference.get("source_layer_id"))
        source_module_id = _nonempty_str(reference.get("source_module_id"))
        source_node_id = _nonempty_str(reference.get("source_node_id"))
        reference_id = _nonempty_str(reference.get("reference_id"))
        declaration = (
            declarations_by_reference_id.get(reference_id)
            or declarations_by_source.get((source_module_id, source_node_id))
            or declarations_by_module.get(source_module_id)
        )
        declaration_id = reference_id or (
            _nonempty_str(declaration.get("reference_id")) if declaration else ""
        )
        declaration = canonical_by_reference_id.get(declaration_id) or declaration
        if declaration:
            for key in (
                "reference_id",
                "source_layer_id",
                "source_module_id",
                "source_node_id",
                "source_scope",
                "source_field_paths",
                "reference_type",
                "required",
                "usage_key",
            ):
                if key in declaration:
                    reference[key] = deepcopy(declaration[key])
            source_layer_id = _nonempty_str(reference.get("source_layer_id"))
            source_module_id = _nonempty_str(reference.get("source_module_id"))
            source_node_id = _nonempty_str(reference.get("source_node_id"))
        reference_id = _nonempty_str(reference.get("reference_id"))
        if not reference_id and declaration:
            reference_id = _nonempty_str(declaration.get("reference_id"))
        if reference_id and reference.get("reference_id") != reference_id:
            reference["reference_id"] = reference_id
        source_module = modules_by_id.get(source_module_id)
        if isinstance(source_module, dict):
            canonical_source_node_id = _canonical_reference_source_node_id(
                reference, source_module
            )
            if canonical_source_node_id:
                reference["source_node_id"] = canonical_source_node_id
                source_node_id = canonical_source_node_id
        resolved = bool(
            source_module is not None
            and source_module.get("layer_id") == source_layer_id
            and source_node_id
            and any(
                _module_graph_node_id(node) == source_node_id
                for node in _module_graph_nodes(source_module)
            )
        )
        if not reference_id:
            issues.append("reference_source_summary_reference_id_required")
        summary.append(
            {
                "reference_id": reference_id or None,
                "source_layer_id": reference.get("source_layer_id"),
                "source_module_id": reference.get("source_module_id"),
                "source_node_id": reference.get("source_node_id"),
                "resolved": resolved,
            }
        )
    return summary, issues


def _normalize_visual_style_reference_sources(collection: Dict[str, Any]) -> None:
    module = next(
        (
            candidate
            for candidate in collection.get("modules", [])
            if isinstance(candidate, dict) and candidate.get("module_id") == "visual_style"
        ),
        None,
    )
    if not isinstance(module, dict):
        return
    reference_input = _module_node_by_type(module, "reference_input")
    params = (
        reference_input.get("params")
        if isinstance(reference_input, dict)
        and isinstance(reference_input.get("params"), dict)
        else {}
    )
    references = params.get("references")
    if isinstance(references, list):
        _visual_style_reference_summary(collection, module, references)
    canonical_declarations = _catalog_visual_style_reference_declarations()
    if canonical_declarations:
        config = module.get("config") if isinstance(module.get("config"), dict) else {}
        config["reference_sources"] = deepcopy(canonical_declarations)
        module["config"] = config


def _visual_validation_revision(module: Dict[str, Any]) -> str:
    config = module.get("config") if isinstance(module.get("config"), dict) else {}
    graph = (
        module.get("module_graph")
        if isinstance(module.get("module_graph"), dict)
        else {}
    )
    for value in (
        config.get("validation_compatibility_revision"),
        graph.get("validation_compatibility_revision"),
    ):
        if isinstance(value, str) and value:
            return value
    for node in _module_graph_nodes(module):
        params = node.get("params") if isinstance(node.get("params"), dict) else {}
        value = params.get("validation_compatibility_revision")
        if isinstance(value, str) and value:
            return value
    return ""


def _stamp_visual_validation_revision(module: Dict[str, Any]) -> None:
    for container_key in ("config", "module_graph"):
        container = (
            module.get(container_key)
            if isinstance(module.get(container_key), dict)
            else {}
        )
        container["validation_compatibility_revision"] = (
            EXPRESSION_VISUAL_VALIDATION_COMPATIBILITY_REVISION
        )
        module[container_key] = container
    for node in _module_graph_nodes(module):
        params = node.get("params") if isinstance(node.get("params"), dict) else {}
        if params.get("mode") == "generic_fields":
            params["validation_compatibility_revision"] = (
                EXPRESSION_VISUAL_VALIDATION_COMPATIBILITY_REVISION
            )
            node["params"] = params


def _stamp_particle_mapping_source_priority_revision(
    module: Dict[str, Any],
) -> None:
    for container_key in ("config", "module_graph"):
        container = (
            module.get(container_key)
            if isinstance(module.get(container_key), dict)
            else {}
        )
        container["source_priority_revision"] = (
            PARTICLE_MAPPING_SOURCE_PRIORITY_FIX_REVISION
        )
        module[container_key] = container
    for node in _module_graph_nodes(module):
        if _module_graph_node_id(node) not in {
            PARTICLE_AVATAR_NODE_IDS["config_input"],
            PARTICLE_AVATAR_NODE_IDS["expression_relative_mapping"],
        }:
            continue
        params = node.get("params") if isinstance(node.get("params"), dict) else {}
        params["source_priority_revision"] = (
            PARTICLE_MAPPING_SOURCE_PRIORITY_FIX_REVISION
        )
        node["params"] = params


def _visual_module_field_records(
    module: Dict[str, Any],
) -> Dict[str, Dict[str, Any]]:
    records: Dict[str, Dict[str, Any]] = {}
    for node in _module_graph_nodes(module):
        params = node.get("params") if isinstance(node.get("params"), dict) else {}
        fields = params.get("fields") if isinstance(params.get("fields"), list) else []
        for field in fields:
            if not isinstance(field, dict):
                continue
            field_key = _nonempty_str(field.get("field_key")) or _nonempty_str(
                field.get("field_id")
            )
            if field_key and field_key not in records:
                records[field_key] = field
    return records


def _visual_field_value(field: Dict[str, Any] | None, fallback: Any) -> Any:
    if not field:
        return deepcopy(fallback)
    return deepcopy(
        field.get("value") if "value" in field else field.get("field_value")
    )


def _set_visual_field_value(field: Dict[str, Any] | None, value: Any) -> None:
    if not field:
        return
    value_key = "value" if "value" in field and "field_value" not in field else "field_value"
    field[value_key] = deepcopy(value)


def _set_visual_field_copies(
    module: Dict[str, Any], field_key: str, value: Any
) -> None:
    for node in _module_graph_nodes(module):
        params = node.get("params") if isinstance(node.get("params"), dict) else {}
        field_lists = [
            params.get("fields"),
            params.get("legacy_fields"),
            params.get("legacy_data_fields"),
            node.get("fields"),
        ]
        for fields in field_lists:
            if not isinstance(fields, list):
                continue
            for field in fields:
                if not isinstance(field, dict):
                    continue
                candidate_key = _nonempty_str(
                    field.get("field_key")
                ) or _nonempty_str(field.get("field_id"))
                if candidate_key == field_key:
                    _set_visual_field_value(field, value)


def _synchronize_expression_state_module_output(
    collection: Dict[str, Any],
    findings: List[Dict[str, str]],
) -> Optional[Dict[str, Any]]:
    module = next(
        (
            candidate
            for candidate in collection.get("modules", [])
            if isinstance(candidate, dict)
            and candidate.get("module_id") == DETAIL_BEHAVIOR_MODULE_ID
        ),
        None,
    )
    if not isinstance(module, dict):
        return None

    strict = (
        _visual_validation_revision(module)
        == EXPRESSION_VISUAL_VALIDATION_COMPATIBILITY_REVISION
    )
    fields = _visual_module_field_records(module)
    state_field = fields.get("expression_state")
    intensity_field = fields.get("expression_intensity")
    legacy_output = _compiled_module_output(module, DETAIL_BEHAVIOR_OUTPUT_KEY)
    raw_state = _visual_field_value(
        state_field,
        legacy_output.get("expression_state") if not strict else None,
    )
    raw_intensity = _visual_field_value(
        intensity_field,
        legacy_output.get("expression_intensity") if not strict else None,
    )

    normalized_state, state_changed = normalize_expression_state(raw_state)
    state_recognized = (
        isinstance(raw_state, str)
        and raw_state.strip().lower() in VISUAL_EXPRESSION_ALLOWED_STATES
    )
    normalized_intensity, intensity_changed, _ = normalize_expression_intensity(
        raw_intensity
    )

    if state_changed:
        findings.append(
            _finding(
                "WARNING" if state_recognized or not strict else "FAIL",
                "DR_EXPRESSION_STATE_INVALID_FALLBACK",
                (
                    "Expression state was normalized to a supported value."
                    if state_recognized
                    else "Expression state is invalid and was replaced with neutral."
                ),
                "payload.modules.emotion_reaction.fields.expression_state",
            )
        )
    if intensity_changed:
        findings.append(
            _finding(
                "FAIL" if strict else "WARNING",
                "DR_EXPRESSION_INTENSITY_OUT_OF_RANGE",
                "Expression intensity was clamped or defaulted to the 0.0-1.0 range.",
                "payload.modules.emotion_reaction.fields.expression_intensity",
            )
        )

    _set_visual_field_copies(
        module, "expression_state", normalized_state
    )
    _set_visual_field_copies(
        module, "expression_intensity", normalized_intensity
    )
    output = {
        "expression_state": normalized_state,
        "expression_intensity": normalized_intensity,
    }
    catalog_module = next(
        (
            candidate
            for candidate in get_module_catalog()
            if candidate.module_id == DETAIL_BEHAVIOR_MODULE_ID
        ),
        None,
    )
    if catalog_module is not None:
        module["output_schema"] = [
            field.model_dump(mode="json")
            for field in catalog_module.output_schema
        ]
    _set_compiled_module_output(module, DETAIL_BEHAVIOR_OUTPUT_KEY, output)
    _stamp_visual_validation_revision(module)
    return output


def _synchronize_particle_avatar_module_output(
    collection: Dict[str, Any],
    findings: Optional[List[Dict[str, str]]] = None,
) -> Optional[Dict[str, Any]]:
    """Project saved Layer 10 fields into declarative particle rules only."""

    module = next(
        (
            candidate
            for candidate in collection.get("modules", [])
            if isinstance(candidate, dict)
            and candidate.get("module_id") == PARTICLE_AVATAR_MODULE_ID
        ),
        None,
    )
    if not isinstance(module, dict):
        return None

    saved_output = _compiled_module_output(module, PARTICLE_AVATAR_OUTPUT_KEY)
    catalog_module = next(
        (
            candidate.model_dump(mode="json")
            for candidate in get_module_catalog()
            if candidate.module_id == PARTICLE_AVATAR_MODULE_ID
        ),
        None,
    )
    if not isinstance(catalog_module, dict):
        return None
    output = _compiled_module_output(catalog_module, PARTICLE_AVATAR_OUTPUT_KEY)
    if not output:
        return None

    strict = (
        _visual_validation_revision(module)
        == EXPRESSION_VISUAL_VALIDATION_COMPATIBILITY_REVISION
    )
    normalized_paths: set[str] = set()
    missing_paths: set[str] = set()
    out_of_range_paths: set[str] = set()
    brightness_paths: set[str] = set()
    transition_time_paths: set[str] = set()
    invalid_color_paths: set[str] = set()
    field_records = _visual_module_field_records(module)

    def configured_value(field_key: str, fallback: Any) -> Any:
        return _visual_field_value(field_records.get(field_key), fallback)

    def update_compiled_field(field_key: str, value: Any) -> None:
        _set_visual_field_copies(module, field_key, value)

    def bounded_number(
        field_key: str,
        fallback: float,
        minimum: float,
        maximum: float,
        *,
        transition_time: bool = False,
        legacy_value: Any = None,
        resolved_source: tuple[bool, Any] | None = None,
    ) -> float:
        if resolved_source is None:
            field_exists = field_key in field_records
            has_legacy_value = not strict and legacy_value is not None
            raw = configured_value(
                field_key,
                legacy_value if has_legacy_value else None,
            )
        else:
            field_exists, raw = resolved_source
            has_legacy_value = False
        parsed: float | None = None
        if isinstance(raw, bool):
            normalized = float(fallback)
        else:
            try:
                parsed = float(raw)
            except (TypeError, ValueError):
                parsed = None
            normalized = (
                min(maximum, max(minimum, parsed))
                if parsed is not None and math.isfinite(parsed)
                else float(fallback)
            )
        path = f"payload.modules.{PARTICLE_AVATAR_MODULE_ID}.fields.{field_key}"
        if (
            (not field_exists and not has_legacy_value)
            or parsed is None
            or not math.isfinite(parsed)
        ):
            if transition_time:
                transition_time_paths.add(path)
            else:
                missing_paths.add(path)
            normalized_paths.add(path)
        elif normalized != parsed:
            out_of_range_paths.add(path)
            normalized_paths.add(path)
            if field_key.endswith("_brightness_multiplier"):
                brightness_paths.add(path)
            if transition_time:
                transition_time_paths.add(path)
        update_compiled_field(field_key, normalized)
        return normalized

    base_color_config = _as_dict(output.get("base_color_config"))
    saved_base_color_config = _as_dict(saved_output.get("base_color_config"))
    for field_key in (
        "user_current_base_color",
        "resident_default_base_color",
        "primary_color",
        "secondary_color",
        "highlight_color",
    ):
        field_exists = field_key in field_records
        legacy_color = (
            saved_base_color_config.get(field_key) if not strict else None
        )
        configured = configured_value(
            field_key,
            legacy_color if legacy_color is not None else "",
        )
        path = f"payload.modules.{PARTICLE_AVATAR_MODULE_ID}.fields.{field_key}"
        if configured == "":
            base_color_config[field_key] = ""
        elif valid_visual_base_color(configured):
            base_color_config[field_key] = configured
        else:
            base_color_config[field_key] = ""
            invalid_color_paths.add(path)
            normalized_paths.add(path)
        if not field_exists and legacy_color is None:
            base_color_config[field_key] = ""
    base_color_config["user_color_override_rule"] = (
        "preserve_user_current_base_color"
    )
    base_color_config["missing_color_fallback_rule"] = (
        "resident_default_then_particle_core_gray_white"
    )
    update_compiled_field(
        "user_color_override_rule", "preserve_user_current_base_color"
    )
    update_compiled_field(
        "missing_color_fallback_rule",
        "resident_default_then_particle_core_gray_white",
    )
    output["base_color_config"] = base_color_config

    relative_config = _as_dict(output.get("expression_relative_mapping"))
    resolved_relative_sources = {
        (state, parameter): particle_relative_mapping_source_value(
            module, state, parameter
        )
        for state in PARTICLE_EXPRESSION_STATES
        for parameter in PARTICLE_RELATIVE_PARAMETER_RANGES
    }
    state_mappings: Dict[str, Dict[str, float]] = {}
    particle_target_by_source = dict(
        VISUAL_EXPRESSION_FIELD_MAPPING["particle_core_mapping"]
    )
    for state in PARTICLE_EXPRESSION_STATES:
        state_mappings[state] = {}
        for parameter, (minimum, maximum) in (
            PARTICLE_RELATIVE_PARAMETER_RANGES.items()
        ):
            field_key = f"{state}_{parameter}"
            output_key = particle_target_by_source[parameter]
            state_mappings[state][parameter] = bounded_number(
                field_key,
                float(VISUAL_EXPRESSION_SAFE_PARAMETER_DEFAULTS[output_key]),
                float(minimum),
                float(maximum),
                resolved_source=resolved_relative_sources[(state, parameter)],
            )
    relative_config["states"] = list(PARTICLE_EXPRESSION_STATES)
    relative_config["parameters"] = list(PARTICLE_RELATIVE_PARAMETER_RANGES)
    relative_config["state_mappings"] = state_mappings
    relative_config["mapping_kind"] = "relative_parameters_only"
    relative_config["fixed_state_colors_allowed"] = False
    relative_config["invalid_state_fallback"] = "neutral"
    output["expression_relative_mapping"] = relative_config
    module_config = (
        module.get("config") if isinstance(module.get("config"), dict) else {}
    )
    module_config["expression_relative_mapping"] = deepcopy(relative_config)
    module_config["source_output_identity_cleanup_revision"] = (
        STAGE7_4_12_A2_CONTENT_REVISION
    )
    module["config"] = module_config
    module_graph = _as_dict(module.get("module_graph"))
    module_graph["source_output_identity_cleanup_revision"] = (
        STAGE7_4_12_A2_CONTENT_REVISION
    )
    module["module_graph"] = module_graph
    for node in _module_graph_nodes(module):
        if (
            _module_graph_node_id(node)
            != PARTICLE_AVATAR_NODE_IDS["expression_relative_mapping"]
        ):
            continue
        params = node.get("params") if isinstance(node.get("params"), dict) else {}
        params["state_mappings"] = deepcopy(state_mappings)
        node["params"] = params

    transition_metadata_sources = {
        field_key: particle_transition_rule_source_value(module, field_key)
        for field_key in (
            "uses_accumulated_idle_time_as_progress",
            "minimum_hold_prevents_flicker",
            "transition_executor",
        )
    }
    transition_rules = _as_dict(output.get("transition_rules"))
    catalog_transition_defaults = deepcopy(transition_rules)
    saved_transition_rules = _as_dict(saved_output.get("transition_rules"))
    transition_rules["transition_duration"] = bounded_number(
        "transition_duration",
        float(
            catalog_transition_defaults.get(
                "transition_duration",
                VISUAL_EXPRESSION_TRANSITION_DEFAULTS["transition_duration"],
            )
        ),
        0.0,
        10.0,
        transition_time=True,
        legacy_value=saved_transition_rules.get("transition_duration"),
    )
    transition_rules["minimum_hold_duration"] = bounded_number(
        "minimum_hold_duration",
        float(
            catalog_transition_defaults.get(
                "minimum_hold_duration",
                VISUAL_EXPRESSION_TRANSITION_DEFAULTS["minimum_hold_duration"],
            )
        ),
        0.0,
        10.0,
        transition_time=True,
        legacy_value=saved_transition_rules.get("minimum_hold_duration"),
    )
    configured_transition_style = configured_value(
        "transition_style",
        (
            saved_transition_rules.get("transition_style")
            if not strict
            else None
        ),
    )
    if configured_transition_style != "smooth":
        normalized_paths.add(
            f"payload.modules.{PARTICLE_AVATAR_MODULE_ID}.fields.transition_style"
        )
    transition_rules["transition_style"] = "smooth"
    transition_rules["transition_style_options"] = ["smooth"]
    update_compiled_field("transition_style", "smooth")
    for field_key, expected_type, fallback in (
        (
            "uses_accumulated_idle_time_as_progress",
            bool,
            False,
        ),
        (
            "minimum_hold_prevents_flicker",
            bool,
            True,
        ),
    ):
        found, value, _source = transition_metadata_sources[field_key]
        if not found or not isinstance(value, expected_type):
            value = fallback
            normalized_paths.add(
                f"payload.modules.{PARTICLE_AVATAR_MODULE_ID}."
                f"transition_rules.{field_key}"
            )
        transition_rules[field_key] = value
    found_executor, transition_executor, _executor_source = (
        transition_metadata_sources["transition_executor"]
    )
    if not found_executor or transition_executor != "aftelle":
        transition_executor = "aftelle"
        normalized_paths.add(
            f"payload.modules.{PARTICLE_AVATAR_MODULE_ID}."
            "transition_rules.transition_executor"
        )
    transition_rules["transition_executor"] = transition_executor
    output["transition_rules"] = transition_rules
    module_config["transition_rules"] = deepcopy(transition_rules)
    module["config"] = module_config
    for node in _module_graph_nodes(module):
        if (
            _module_graph_node_id(node)
            != PARTICLE_AVATAR_NODE_IDS["state_transition"]
        ):
            continue
        params = (
            node.get("params") if isinstance(node.get("params"), dict) else {}
        )
        params.update(deepcopy(transition_rules))
        node["params"] = params

    _set_compiled_module_output(module, PARTICLE_AVATAR_OUTPUT_KEY, output)
    _stamp_visual_validation_revision(module)
    _stamp_particle_mapping_source_priority_revision(module)
    if normalized_paths and findings is not None:
        status = "FAIL" if strict else "WARNING"
        if missing_paths:
            findings.append(
                _finding(
                    status,
                    "DR_PARTICLE_MAPPING_DEFAULTED",
                    "Particle mapping values were missing or non-numeric and used safe defaults: "
                    + ", ".join(sorted(missing_paths)),
                    "visual_expression_mapping.particle_core_mapping",
                )
            )
        if brightness_paths:
            findings.append(
                _finding(
                    status,
                    "DR_PARTICLE_BRIGHTNESS_MULTIPLIER_OUT_OF_RANGE",
                    "Particle brightness multiplier exceeded its allowed range: "
                    + ", ".join(sorted(brightness_paths)),
                    "visual_expression_mapping.particle_core_mapping",
                )
            )
        remaining_range_paths = out_of_range_paths - brightness_paths - transition_time_paths
        if remaining_range_paths:
            findings.append(
                _finding(
                    status,
                    "DR_PARTICLE_RELATIVE_VALUE_OUT_OF_RANGE",
                    "Particle relative values exceeded their allowed ranges: "
                    + ", ".join(sorted(remaining_range_paths)),
                    "visual_expression_mapping.particle_core_mapping",
                )
            )
        if transition_time_paths:
            findings.append(
                _finding(
                    status,
                    "DR_TRANSITION_TIME_INVALID_FALLBACK",
                    "Transition time values were limited to the safe 0.0-10.0 range: "
                    + ", ".join(sorted(transition_time_paths)),
                    "visual_expression_mapping.transition_policy",
                )
            )
        transition_style_path = (
            f"payload.modules.{PARTICLE_AVATAR_MODULE_ID}.fields.transition_style"
        )
        if transition_style_path in normalized_paths:
            findings.append(
                _finding(
                    status,
                    "DR_TRANSITION_STYLE_INVALID_FALLBACK",
                    "Transition style is invalid and was replaced with smooth.",
                    "visual_expression_mapping.transition_policy.transition_style",
                )
            )
        if invalid_color_paths:
            findings.append(
                _finding(
                    status,
                    "DR_VISUAL_EXPRESSION_BASE_COLOR_INVALID",
                    "Invalid base colors were preserved in source data but excluded from the runtime projection: "
                    + ", ".join(sorted(invalid_color_paths)),
                    "visual_expression_mapping.base_color_policy",
                )
            )
        findings.append(
            _finding(
                "WARNING" if not strict else "FAIL",
                "DR_VISUAL_EXPRESSION_MAPPING_CLAMPED",
                (
                    "Visual expression configuration values were normalized before projection: "
                    + ", ".join(sorted(normalized_paths))
                ),
                "visual_expression_mapping",
            )
        )
    return output


def _synchronize_first_presence_module_output(
    collection: Dict[str, Any], findings: List[Dict[str, str]]
) -> None:
    """Compile the optional Layer 10 configuration without adding Runtime behavior."""

    module = next(
        (
            candidate
            for candidate in collection.get("modules", [])
            if isinstance(candidate, dict) and candidate.get("module_id") == "visual_style"
        ),
        None,
    )
    if not isinstance(module, dict):
        return

    input_node = next(
        (
            node
            for node in _module_graph_nodes(module)
            if _module_graph_node_id(node)
            == "visual_style_first_greeting_config"
        ),
        None,
    )
    if isinstance(input_node, dict):
        input_params = (
            input_node.get("params")
            if isinstance(input_node.get("params"), dict)
            else {}
        )
        for field_list_key in (
            "fields",
            "legacy_fields",
            "legacy_data_fields",
        ):
            field_list = input_params.get(field_list_key)
            if not isinstance(field_list, list):
                continue
            for field in field_list:
                if (
                    isinstance(field, dict)
                    and _field_identifier(field, 0) == "first_greeting"
                    and field.get("description")
                    == FIRST_GREETING_STALE_UNAUTHORED_DESCRIPTION
                ):
                    field["description"] = (
                        FIRST_GREETING_AUTHORED_DESCRIPTION
                    )
        input_params["identity_literal_export_gate_revision"] = (
            STAGE7_4_12_IDENTITY_LITERAL_EXPORT_GATE_FIX_REVISION
        )
        input_node["params"] = input_params

    greeting_found, greeting = _configured_module_field_value(
        collection, "visual_style", "first_greeting"
    )
    presence_found, presence = _configured_module_field_value(
        collection, "visual_style", "first_presence"
    )
    greeting_issues: List[str] = []
    presence_issues: List[str] = []

    if greeting_found and not isinstance(greeting, dict):
        greeting_issues.append("first_greeting_must_be_object")
    elif isinstance(greeting, dict):
        variants = greeting.get("variants")
        content_status = greeting.get("content_status")
        if not isinstance(variants, list):
            greeting_issues.append("variants_must_be_array")
        else:
            if any(not _valid_first_greeting_variant(variant) for variant in variants):
                greeting_issues.append("greeting_variants_must_contain_valid_copy")
            if (not variants and content_status != "pending_authoring") or (
                variants and content_status != "authored"
            ):
                greeting_issues.append("content_status_must_match_variants")
        if content_status not in {"pending_authoring", "authored"}:
            greeting_issues.append("content_status_must_use_supported_value")
        for key, expected, issue in (
            ("locale", "zh-CN", "locale_must_use_supported_value"),
            ("selection_mode", "contextual", "selection_mode_must_use_supported_value"),
        ):
            if key in greeting and greeting.get(key) != expected:
                greeting_issues.append(issue)
        for key, minimum, issue in (
            ("max_sentences", 1, "max_sentences_at_least_one"),
            ("max_questions", 0, "max_questions_non_negative"),
        ):
            value = greeting.get(key)
            if key in greeting and (
                not isinstance(value, int) or isinstance(value, bool) or value < minimum
            ):
                greeting_issues.append(issue)
        if greeting.get("repeat_on_return") is True:
            greeting_issues.append("repeat_on_return_defaults_false")
        for key in (
            "wait_for_user_response",
            "avoid_service_tone",
            "avoid_forced_intimacy",
            "avoid_identity_overexplanation",
            "repeat_on_return",
        ):
            if key in greeting and not isinstance(greeting.get(key), bool):
                greeting_issues.append("greeting_boolean_flags_must_be_boolean")

    if presence_found and not isinstance(presence, dict):
        presence_issues.append("first_presence_must_be_object")
    elif isinstance(presence, dict):
        for key, expected, issue in (
            ("particle_state", "calm", "particle_state_must_use_supported_value"),
            ("motion", "slow_breathing", "motion_hint_only_no_animation"),
            ("energy", "soft", "energy_hint_only"),
            ("subtitle_mode", "minimal", "subtitle_mode_config_only_no_runtime_capability"),
        ):
            if key in presence and presence.get(key) != expected:
                presence_issues.append(issue)

    reference_input = _module_node_by_type(module, "reference_input")
    reference_params = (
        reference_input.get("params")
        if isinstance(reference_input, dict) and isinstance(reference_input.get("params"), dict)
        else {}
    )
    references = reference_params.get("references") if isinstance(reference_params.get("references"), list) else []
    source_summary, reference_issues = _visual_style_reference_summary(
        collection, module, references
    )
    greeting_issues.extend(reference_issues)
    issues = list(dict.fromkeys([*greeting_issues, *presence_issues]))
    output: Dict[str, Any] = {
        "output_key": "first_presence_config",
        "reference_source_summary": source_summary,
        "validation_result": {
            "status": "invalid" if issues else "pass",
            "first_greeting": (
                "invalid" if greeting_issues else "pass" if greeting_found else "missing_optional"
            ),
            "first_presence": (
                "invalid" if presence_issues else "pass" if presence_found else "missing_optional"
            ),
            "risk_items": issues,
        },
        "optional_config_status": {
            "first_greeting": "optional_present" if greeting_found else "missing_optional",
            "first_presence": "optional_present" if presence_found else "missing_optional",
            "variants": (
                "empty_allowed"
                if isinstance(greeting, dict) and greeting.get("variants") == []
                else "configured"
                if isinstance(greeting, dict) and isinstance(greeting.get("variants"), list)
                else "missing_optional"
            ),
        },
        "compile_time_only": True,
        "no_runtime_capability": True,
    }
    if greeting_found and isinstance(greeting, dict):
        output["first_greeting"] = deepcopy(greeting)
    if presence_found and isinstance(presence, dict):
        output["first_presence"] = deepcopy(presence)
    _set_compiled_module_output(module, "first_presence_config", output)

    if issues:
        findings.append(
            _finding(
                "FAIL",
                "DR_FIRST_PRESENCE_CONFIG_INVALID",
                f"Layer 10 optional first-presence configuration is invalid: {issues!r}",
                (
                    "payload.expression.first_greeting"
                    if greeting_issues
                    else "payload.expression.first_presence"
                ),
            )
        )
    else:
        findings.append(
            _finding(
                "PASS",
                "DR_FIRST_PRESENCE_CONFIG_VALID",
                "Layer 10 optional first-greeting and first-presence configuration compiled without Runtime changes",
                "payload.modules.visual_style.outputs.first_presence_config",
            )
        )


def _synchronize_dialogue_runtime_profile_module_output(
    collection: Dict[str, Any],
    resident_id: str,
) -> Optional[Dict[str, Any]]:
    """Mirror the saved optional profile fields before deriving the projection."""

    module = next(
        (
            candidate
            for candidate in collection.get("modules", [])
            if isinstance(candidate, dict)
            and candidate.get("module_id") == DIALOGUE_RUNTIME_PROFILE_MODULE_ID
        ),
        None,
    )
    if not isinstance(module, dict):
        return None
    profile_id = dialogue_runtime_profile_id(resident_id)
    _replace_dialogue_profile_identity(module, profile_id)
    config = (
        module.get("config") if isinstance(module.get("config"), dict) else {}
    )
    config["source_output_identity_cleanup_revision"] = (
        STAGE7_4_12_A2_CONTENT_REVISION
    )
    module["config"] = config
    graph = (
        module.get("module_graph")
        if isinstance(module.get("module_graph"), dict)
        else {}
    )
    graph["source_output_identity_cleanup_revision"] = (
        STAGE7_4_12_A2_CONTENT_REVISION
    )
    module["module_graph"] = graph
    for node in _module_graph_nodes(module):
        if (
            _module_graph_node_id(node)
            != "dialogue_runtime_profile_config_input"
        ):
            continue
        params = (
            node.get("params")
            if isinstance(node.get("params"), dict)
            else {}
        )
        params["source_output_identity_cleanup_revision"] = (
            STAGE7_4_12_A2_CONTENT_REVISION
        )
        node["params"] = params
    profile = extract_dialogue_runtime_profile(module, collection.get("modules"))
    if not isinstance(profile, dict):
        return None
    output = {
        field_key: deepcopy(profile[field_key])
        for field_key in DIALOGUE_RUNTIME_PROFILE_FIELD_KEYS
        if field_key in profile
    }
    _set_compiled_module_output(module, DIALOGUE_RUNTIME_PROFILE_OUTPUT_KEY, output)
    return profile


def dialogue_runtime_profile_id(resident_id: str) -> str:
    """Create a stable, non-identifying profile key from Layer 1 resident_id."""

    source = resident_id.strip() if isinstance(resident_id, str) else ""
    digest = sha256((source or "digital_resident").encode("utf-8")).hexdigest()[
        :16
    ]
    return f"dialogue_profile_{digest}_v0_1"


def _replace_dialogue_profile_identity(value: Any, profile_id: str) -> Any:
    if isinstance(value, list):
        for index, item in enumerate(value):
            value[index] = _replace_dialogue_profile_identity(item, profile_id)
        return value
    if not isinstance(value, dict):
        return value
    source_scope = value.get("source_scope")
    field_id = value.get("field_id") or value.get("field_key")
    if field_id == "profile_id":
        if "field_value" in value:
            value["field_value"] = profile_id
        if "value" in value:
            value["value"] = profile_id
    for key, item in list(value.items()):
        if key == "profile_id":
            value[key] = profile_id
        elif key == "source_id" and source_scope == "resident_profile":
            value[key] = profile_id
        else:
            value[key] = _replace_dialogue_profile_identity(item, profile_id)
    return value


def _memory_router_node_params(module: Dict[str, Any], role: str) -> Dict[str, Any]:
    node_id = MEMORY_PROVIDER_ROUTER_NODE_IDS.get(role, "")
    node = _module_node_by_id(module, node_id) if node_id else None
    return node.get("params") if isinstance(node, dict) and isinstance(node.get("params"), dict) else {}


def _string_list(value: Any) -> List[str]:
    return [str(item) for item in value if isinstance(item, str) and item] if isinstance(value, list) else []


def _rebuild_memory_provider_router_output(
    module: Dict[str, Any], findings: List[Dict[str, str]]
) -> Dict[str, Any]:
    """Project the router policy from current node params without executing its graph."""
    request_params = _memory_router_node_params(module, "request_input")
    classifier_params = _memory_router_node_params(module, "operation_classifier")
    resident_params = _memory_router_node_params(module, "resident_resolver")
    namespace_params = _memory_router_node_params(module, "namespace_resolver")
    type_params = _memory_router_node_params(module, "type_resolver")
    access_params = _memory_router_node_params(module, "access_control")
    provider_params = _memory_router_node_params(module, "provider_selector")
    binding_params = _memory_router_node_params(module, "engine_binding")
    trace_params = _memory_router_node_params(module, "trace_record")
    request_schema = _as_dict(request_params.get("request_schema"))

    canonical_operations = _string_list(
        request_schema.get("canonical_operations") or request_schema.get("operations")
    )
    request_operations = _string_list(request_schema.get("operations"))
    classifier_declared_operations = _string_list(classifier_params.get("operations"))
    classifier_operations = _string_list(
        classifier_params.get("canonical_operations") or classifier_params.get("operations")
    )
    request_aliases = {
        str(alias): str(target)
        for alias, target in _as_dict(request_schema.get("operation_aliases")).items()
        if alias and target
    }
    classifier_aliases = {
        str(alias): str(target)
        for alias, target in _as_dict(classifier_params.get("operation_aliases")).items()
        if alias and target
    }
    allowed_memory_types = _string_list(type_params.get("allowed_memory_types"))
    expected_operations = list(MEMORY_PROVIDER_ROUTER_CANONICAL_OPERATIONS)
    expected_aliases = dict(MEMORY_PROVIDER_ROUTER_OPERATION_ALIASES)
    expected_memory_types = list(MEMORY_PROVIDER_ROUTER_ALLOWED_MEMORY_TYPES)
    expected_namespace_policy = deepcopy(MEMORY_PROVIDER_ROUTER_NAMESPACE_POLICY)

    config_mismatches: List[str] = []
    if canonical_operations != expected_operations or request_operations != expected_operations:
        config_mismatches.append("request operations are not canonical read/write/update/delete")
    if classifier_operations != canonical_operations or classifier_declared_operations != canonical_operations:
        config_mismatches.append("request and classifier canonical operations differ")
    if request_aliases != expected_aliases or classifier_aliases != expected_aliases:
        config_mismatches.append("operation aliases must be view->read and clear->delete")
    accepted_operations = _string_list(request_schema.get("accepted_operations"))
    expected_accepted_operations = [*canonical_operations, *request_aliases.keys()]
    if accepted_operations and accepted_operations != expected_accepted_operations:
        config_mismatches.append("accepted operations differ from canonical operations plus aliases")
    if allowed_memory_types != expected_memory_types:
        config_mismatches.append("allowed memory types differ from the Stage 7.4 canonical set")
    declared_namespace_policy = namespace_params.get("namespace_policy")
    if "namespace_policy" in namespace_params and declared_namespace_policy != expected_namespace_policy:
        config_mismatches.append("namespace policy differs from the Stage 7.4 canonical namespace set")
    elif "namespace_policy" in namespace_params:
        if namespace_params.get("default_namespace") != expected_namespace_policy["default_namespace"]:
            config_mismatches.append("namespace resolver default differs from the canonical namespace policy")
        if provider_params.get("namespace") != "memory_type_default":
            config_mismatches.append("provider selector namespace must use the memory type default")
    else:
        if namespace_params.get("default_namespace") != "default":
            config_mismatches.append("legacy namespace config must use the known default alias")
        if provider_params.get("namespace") not in {"default", "memory_type_default"}:
            config_mismatches.append("legacy provider namespace must use a known default alias")
    if config_mismatches:
        findings.append(
            _finding(
                "FAIL",
                "DR_MEMORY_ROUTER_NODE_CONFIG_INCONSISTENT",
                "; ".join(config_mismatches),
                "modules.memory_provider_router.module_graph.nodes",
            )
        )

    # Upgrade legacy `default` router nodes only inside the compiler-owned copy.
    # The input Canvas/DR stays untouched, while exported node config, output,
    # and top-level policy share one canonical namespace source.
    namespace_params["default_namespace"] = expected_namespace_policy["default_namespace"]
    namespace_params["namespace_policy"] = deepcopy(expected_namespace_policy)
    provider_params["namespace"] = "memory_type_default"

    required_fields = _string_list(request_schema.get("required"))
    optional_fields = _string_list(request_schema.get("optional"))
    allowed_runtime_fields = list(dict.fromkeys([*required_fields, *optional_fields]))
    resident_rules = set(_string_list(resident_params.get("validation_rules")))
    type_rules = set(_string_list(type_params.get("normalize_rules")))
    existing = _compiled_module_output(module, MEMORY_PROVIDER_ROUTER_OUTPUT_KEY)
    rebuilt = deepcopy(existing)
    rebuilt.update(
        {
            "output_key": MEMORY_PROVIDER_ROUTER_OUTPUT_KEY,
            "request_contract": {
                "allowed_runtime_fields": allowed_runtime_fields,
                "required_runtime_fields": required_fields,
                "operations": canonical_operations,
                "canonical_operations": canonical_operations,
                "accepted_operations": expected_accepted_operations,
                "operation_aliases": request_aliases,
            },
            "resident_scope": {
                "resident_id_required": "resident_id" in set(_string_list(resident_params.get("required_fields"))),
                "cross_resident_access": (
                    "forbidden" if "cross_resident_access_forbidden" in resident_rules else "unspecified"
                ),
            },
            "namespace_policy": deepcopy(expected_namespace_policy),
            "memory_type_policy": {
                "allowed_memory_types": allowed_memory_types,
                "unsupported_memory_type_action": (
                    "reject" if "allow_declared_memory_types_only" in type_rules else "unspecified"
                ),
            },
            "access_policy": {
                **{operation: deepcopy(allowed_memory_types) for operation in canonical_operations},
                "session_only": deepcopy(_string_list(access_params.get("session_only"))),
                "forbidden_memory": deepcopy(_string_list(access_params.get("forbidden_memory"))),
            },
            "provider_policy": {
                "allowed_backends": deepcopy(_string_list(provider_params.get("allowed_backends"))),
                "default_backend": provider_params.get("storage_backend") or "mock",
                "runtime_provider_ownership": "runtime_owned_not_stored_in_studio",
            },
            "engine_binding": {
                "slot_id": binding_params.get("slot_binding") or "",
                "engine_id": binding_params.get("engine_id") or "",
                "provider_id": binding_params.get("provider_id") or "",
            },
            "trace_policy": {
                "allowed_fields": deepcopy(_string_list(trace_params.get("trace_fields"))),
                "forbidden_fields": deepcopy(_string_list(trace_params.get("forbidden_trace_fields"))),
            },
        }
    )
    return rebuilt


def _validate_memory_router_projection(
    module: Dict[str, Any], expected: Dict[str, Any], memory_policy: Dict[str, Any], findings: List[Dict[str, str]]
) -> None:
    module_output = _compiled_module_output(module, MEMORY_PROVIDER_ROUTER_OUTPUT_KEY)
    projected = _as_dict(memory_policy.get("memory_provider_router"))
    projected_types = _string_list(memory_policy.get("memory_types"))
    expected_types = _string_list(_as_dict(expected.get("memory_type_policy")).get("allowed_memory_types"))
    expected_namespace_policy = _as_dict(expected.get("namespace_policy"))
    projected_namespace_policy = _as_dict(memory_policy.get("namespace_policy"))
    if (
        module_output != expected
        or projected != module_output
        or projected_types != expected_types
        or projected_namespace_policy != expected_namespace_policy
    ):
        findings.append(
            _finding(
                "FAIL",
                "DR_MEMORY_ROUTER_PROJECTION_INCONSISTENT",
                "memory_provider_router node config, module_output, and memory_policy extension differ",
                "payload.memory_policy.memory_policy_extensions.memory_provider_router",
            )
        )
        return
    findings.append(
        _finding(
            "PASS",
            "DR_MEMORY_ROUTER_PROJECTION_CONSISTENT",
            "memory_provider_router node config, module_output, and memory_policy extension are semantically aligned",
            "payload.memory_policy.memory_policy_extensions.memory_provider_router",
        )
    )


def _assemble_layer5_memory_policy(
    collection: Dict[str, Any], resident_id: str, findings: List[Dict[str, str]]
) -> Dict[str, Any]:
    modules = {
        _nonempty_str(module.get("module_id")): module
        for module in collection.get("modules", [])
        if isinstance(module, dict) and _nonempty_str(module.get("module_id"))
    }
    memory_policy: Dict[str, Any] = {
        "schema_version": DR_SCHEMA_VERSION_V0_3,
        "resident_id": resident_id,
        "namespace": "default",
        "memory_types": [
            "short_term_memory",
            "preference_memory",
            "event_memory",
            "relationship_memory",
            "interaction_log",
        ],
        "interaction_log": {"type": "append_only", "scope": "per_resident"},
        "retention_policy": "policy_managed",
        "read_write_policy": "memory_access_control",
        "memory_support_levels": deepcopy(_V03_MEMORY_SUPPORT_LEVELS),
    }
    missing = False
    memory_router_module: Dict[str, Any] | None = None
    expected_memory_router_output: Dict[str, Any] | None = None
    for module_id, output_key, policy_key in _LAYER5_MEMORY_POLICY_MODULES:
        module = modules.get(module_id)
        if module is None:
            missing = True
            findings.append(
                _finding(
                    "FAIL",
                    "DR_MEMORY_POLICY_MODULE_MISSING",
                    f"Layer 5 memory policy module {module_id!r} is missing",
                    f"modules.{module_id}",
                )
            )
            continue
        if policy_key == "memory_provider_router":
            memory_router_module = module
            expected_memory_router_output = _rebuild_memory_provider_router_output(module, findings)
            _set_compiled_module_output(module, output_key, expected_memory_router_output)
        output = _compiled_module_output(module, output_key)
        if not output:
            missing = True
            findings.append(
                _finding(
                    "FAIL",
                    "DR_MEMORY_POLICY_OUTPUT_MISSING",
                    f"Layer 5 module {module_id!r} has no compiled output {output_key!r}",
                    f"modules.{module_id}.outputs.{output_key}",
                )
            )
            continue
        if policy_key == "memory_access_control":
            output["recall_claim_policy"] = deepcopy(
                MEMORY_RECALL_CLAIM_POLICY
            )
            _set_compiled_module_output(module, output_key, output)
        memory_policy[policy_key] = output

    if expected_memory_router_output:
        router_type_policy = _as_dict(expected_memory_router_output.get("memory_type_policy"))
        memory_policy["memory_types"] = deepcopy(_string_list(router_type_policy.get("allowed_memory_types")))
        memory_policy["namespace_policy"] = deepcopy(
            _as_dict(expected_memory_router_output.get("namespace_policy"))
        )
        private_policy = _as_dict(
            _as_dict(memory_policy["namespace_policy"].get("namespaces")).get("private_memory")
        )
        private_template = str(private_policy.get("namespace_template") or "private_memory:{resident_id}")
        memory_policy["namespace"] = private_template.replace("{resident_id}", resident_id)
    if memory_router_module is not None and expected_memory_router_output is not None:
        _validate_memory_router_projection(
            memory_router_module,
            expected_memory_router_output,
            memory_policy,
            findings,
        )

    short_term = _as_dict(memory_policy.get("short_term_memory"))
    if short_term and not (
        short_term.get("retention") == "session" and short_term.get("session_scoped_only") is True
    ):
        findings.append(
            _finding(
                "FAIL",
                "DR_MEMORY_SHORT_TERM_NOT_SESSION_ONLY",
                "short_term_memory must remain session-only and expire at session end",
                "payload.memory_policy.memory_policy_extensions.short_term_memory",
            )
        )
    preference = _as_dict(memory_policy.get("preference_memory"))
    if preference and "inferred_fact" not in set(preference.get("save_forbidden") or []):
        findings.append(
            _finding(
                "FAIL",
                "DR_MEMORY_PREFERENCE_INFERENCE_ALLOWED",
                "preference_memory must reject inferred facts and accept only explicit or confirmed preferences",
                "payload.memory_policy.memory_policy_extensions.preference_memory.save_forbidden",
            )
        )
    event = _as_dict(memory_policy.get("event_memory"))
    if event and not {"brief_summary", "event_meaning", "timestamp"}.issubset(set(event.get("save_allowed") or [])):
        findings.append(
            _finding(
                "FAIL",
                "DR_MEMORY_EVENT_FIELDS_INVALID",
                "event_memory must limit persistence to a necessary summary, meaning, and timestamp",
                "payload.memory_policy.memory_policy_extensions.event_memory.save_allowed",
            )
        )
    relationship = _as_dict(memory_policy.get("relationship_memory"))
    if relationship and relationship.get("change_policy") != "gradual_only":
        findings.append(
            _finding(
                "FAIL",
                "DR_MEMORY_RELATIONSHIP_JUMP_ALLOWED",
                "relationship_memory must update gradually and reject single-interaction level jumps",
                "payload.memory_policy.memory_policy_extensions.relationship_memory.change_policy",
            )
        )
    memory_update = _as_dict(memory_policy.get("memory_update"))
    update_priority = _as_dict(memory_update.get("policy_priority"))
    if memory_update and (
        update_priority.get("inferred_fact") != "deny" or memory_update.get("no_dr_writeback") is not True
    ):
        findings.append(
            _finding(
                "FAIL",
                "DR_MEMORY_UPDATE_BOUNDARY_INVALID",
                "memory_update must deny inferred facts and forbid DR writeback",
                "payload.memory_policy.memory_policy_extensions.memory_update",
            )
        )
    access = _as_dict(memory_policy.get("memory_access_control"))
    sensitive_policy = _as_dict(access.get("sensitive_policy"))
    if access and sensitive_policy.get("default_for_inferred_fact") != "deny":
        findings.append(
            _finding(
                "FAIL",
                "DR_MEMORY_ACCESS_INFERENCE_DEFAULT_INVALID",
                "memory_access_control must deny inferred facts by default",
                "payload.memory_policy.memory_policy_extensions.memory_access_control.sensitive_policy",
            )
        )
    router = _as_dict(memory_policy.get("memory_provider_router"))
    resident_scope = _as_dict(router.get("resident_scope"))
    if router and resident_scope.get("cross_resident_access") != "forbidden":
        findings.append(
            _finding(
                "FAIL",
                "DR_MEMORY_CROSS_RESIDENT_ACCESS_ALLOWED",
                "memory_provider_router must forbid cross-resident private memory access",
                "payload.memory_policy.memory_policy_extensions.memory_provider_router.resident_scope",
            )
        )

    if not missing and not any(
        finding.get("status") == "FAIL" and str(finding.get("code", "")).startswith("DR_MEMORY_")
        for finding in findings
    ):
        findings.append(
            _finding(
                "PASS",
                "DR_MEMORY_POLICY_PROJECTED",
                "all seven Layer 5 memory modules were projected into the optional memory_policy extension",
                "payload.memory_policy.memory_policy_extensions",
            )
        )
    return memory_policy


def _build_v03_memory_policy(resident_id: str, extensions: Dict[str, Any]) -> Dict[str, Any]:
    """Keep the frozen v0.3 surface stable and nest Stage 7.4 strategy data."""
    return {
        "schema_version": DR_SCHEMA_VERSION_V0_3,
        "resident_id": resident_id,
        "namespace": "default",
        "memory_types": list(_V03_FROZEN_MEMORY_TYPES),
        "interaction_log": {"type": "append_only", "scope": "per_resident"},
        "preference_memory": {"type": "kv", "scope": "per_resident"},
        "retention_policy": "persistent",
        "read_write_policy": "local_runtime",
        _V03_MEMORY_POLICY_EXTENSIONS_KEY: deepcopy(extensions),
    }


def _v3_identity_sync_from_profile(payload: Dict[str, Any]) -> Dict[str, Any]:
    graph_snapshot = _as_dict(payload.get("graph_snapshot"))
    layer_outputs = _as_dict(graph_snapshot.get("layer_outputs"))
    identity_profile = _as_dict(layer_outputs.get("identity_profile"))
    basic_identity = _as_dict(identity_profile.get("basic_identity"))
    basic_fields = _as_dict(basic_identity.get("fields"))
    top_summary = _build_identity_top_summary(identity_profile)

    def _pick(*keys: str) -> str:
        for key in keys:
            value = identity_profile.get(key)
            if isinstance(value, str) and value.strip():
                return value
            value = basic_fields.get(key)
            if isinstance(value, str) and value.strip():
                return value
        return ""

    return {
        "resident_id": _pick("resident_id"),
        "name": _pick("name"),
        "primary_language": top_summary["primary_language"],
        "city_symbol": _pick("city", "representative_city"),
        "personality_summary": top_summary["personality_summary"],
        "domain_focus": top_summary["domain_focus"],
        "description": top_summary["description"],
        "resident_description": top_summary["resident_description"],
        "disclosure": top_summary["disclosure"],
        "tags": top_summary["tags"],
    }


def _sync_legacy_blueprint_identity(blueprint: Dict[str, Any], resident_id: str, resident_name: str) -> None:
    if not isinstance(blueprint, dict):
        return
    for key in ("lattice_config", "lattice_state_schema"):
        if isinstance(blueprint.get(key), dict):
            blueprint[key]["resident_id"] = resident_id
    multi_resident = blueprint.get("multi_resident_lattice_state")
    if isinstance(multi_resident, dict):
        multi_resident["resident_ids"] = [resident_id]
    resident_instance = blueprint.get("resident_instance")
    if isinstance(resident_instance, dict):
        resident_instance["resident_id"] = resident_id
        if resident_name:
            resident_instance["name"] = resident_name
        identity = resident_instance.get("identity")
        if isinstance(identity, dict):
            identity["resident_id"] = resident_id
            if resident_name:
                identity["name"] = resident_name


def _sync_legacy_blueprint_runtime_requirements(blueprint: Dict[str, Any]) -> None:
    if not isinstance(blueprint, dict):
        return
    runtime_requirements = blueprint.setdefault("runtime_requirements", {})
    if isinstance(runtime_requirements, dict):
        runtime_requirements["required_slot_types"] = list(STAGE_7_4_REQUIRED_SLOT_TYPES)


def _is_complete_module_record(value: Any) -> bool:
    if not isinstance(value, dict) or not _nonempty_str(value.get("module_id")):
        return False
    return any(
        key in value
        for key in ("module_graph", "outputs", "input_schema")
    )


def _lightweight_module_reference(module: Dict[str, Any]) -> Dict[str, Any]:
    return {
        key: deepcopy(module[key])
        for key in (
            "module_id",
            "layer_id",
            "module_type",
            "slot_type",
            "status",
            "runtime_enabled",
        )
        if key in module
    }


def _strip_complete_module_sources(value: Any) -> Any:
    """Keep display references while removing nested module truth copies."""

    if _is_complete_module_record(value):
        return _lightweight_module_reference(value)
    if isinstance(value, list):
        return [_strip_complete_module_sources(item) for item in value]
    if not isinstance(value, dict):
        return deepcopy(value)

    sanitized: Dict[str, Any] = {}
    for key, item in value.items():
        if key == "module_graph" and isinstance(item, dict):
            continue
        if (
            key == "modules"
            and isinstance(item, list)
            and any(_is_complete_module_record(candidate) for candidate in item)
        ):
            continue
        sanitized[key] = _strip_complete_module_sources(item)
    return sanitized


def _build_lightweight_graph_snapshot(
    collection: Dict[str, Any],
) -> Dict[str, Any]:
    snapshot = {
        key: _strip_complete_module_sources(collection.get(key, []))
        for key in ("nodes", "edges", "layers", "slots")
    }
    snapshot["compatibility_status"] = module_surface_classification(
        "payload.graph_snapshot"
    )
    return snapshot


def _nested_complete_module_source_paths(
    value: Any,
    path: str,
) -> List[str]:
    paths: List[str] = []
    if _is_complete_module_record(value):
        return [path]
    if isinstance(value, list):
        for index, item in enumerate(value):
            paths.extend(
                _nested_complete_module_source_paths(
                    item, f"{path}[{index}]"
                )
            )
        return paths
    if not isinstance(value, dict):
        return paths
    for key, item in value.items():
        item_path = f"{path}.{key}" if path else key
        if key == "module_graph" and isinstance(item, dict):
            paths.append(item_path)
            continue
        paths.extend(_nested_complete_module_source_paths(item, item_path))
    return paths


def _semantic_list_identifier(value: Dict[str, Any]) -> str:
    for key in ("module_id", "node_id", "edge_id", "slot_id"):
        identifier = _nonempty_str(value.get(key))
        if identifier:
            return f"{key}:{identifier}"
    return ""


def _normalized_module_semantics(value: Any) -> Any:
    """Canonicalize ordering without discarding module semantics."""

    if isinstance(value, dict):
        normalized = {
            key: _normalized_module_semantics(item)
            for key, item in sorted(value.items(), key=lambda pair: pair[0])
        }
        return normalized
    if isinstance(value, list):
        normalized_items = [
            _normalized_module_semantics(item) for item in value
        ]
        identifiers = [
            _semantic_list_identifier(item)
            for item in normalized_items
            if isinstance(item, dict)
        ]
        if (
            len(identifiers) == len(normalized_items)
            and identifiers
            and all(identifiers)
            and len(set(identifiers)) == len(identifiers)
        ):
            return sorted(
                normalized_items,
                key=lambda item: _semantic_list_identifier(item),
            )
        return normalized_items
    return deepcopy(value)


def _synchronize_stage_7_4_module_scope(collection: Dict[str, Any]) -> None:
    """Generate reserved capability state on the compiler-owned module copies."""
    required_slot_types = set(STAGE_7_4_REQUIRED_SLOT_TYPES)
    for module in collection.get("modules", []):
        if not isinstance(module, dict):
            continue
        module_id = _nonempty_str(module.get("module_id"))
        slot_type = _nonempty_str(module.get("slot_type"))
        forced_reserved = module_id in _STAGE_7_4_FORCED_RESERVED_MODULE_IDS
        if not forced_reserved and (
            slot_type in required_slot_types or slot_type not in _STAGE_7_4_RESERVED_SLOT_TYPES
        ):
            continue
        module["status"] = "RESERVED"
        module["is_placeholder"] = True
        module["no_execution"] = True
        module["runtime_enabled"] = False
        module["runtime_mapping"] = {}
        module_graph = module.get("module_graph")
        if isinstance(module_graph, dict):
            module_graph.pop("runtime_flow", None)
            module_graph.pop("slot_routes", None)


def _synchronize_a4_module_status_classifications(
    collection: Dict[str, Any],
) -> None:
    """Project central A4 states onto the authoritative module records."""

    for module in collection.get("modules", []):
        if not isinstance(module, dict):
            continue
        module_id = _nonempty_str(module.get("module_id"))
        try:
            classification = module_status_classification(module_id)
        except KeyError:
            continue
        module["status_classification"] = classification
        if module_id == "memory_provider_router":
            # Memory remains a required capability, while this declarative
            # Provider selector is explicitly mock/policy-only.
            module["runtime_enabled"] = False
            module["no_execution"] = True


def _build_v03_audit_report(
    findings: List[Dict[str, str]],
    checked_at: str,
    named_check_findings: Optional[Dict[str, List[Dict[str, str]]]] = None,
    serialization_metrics: Optional[Dict[str, Any]] = None,
    compatibility_metrics: Optional[Dict[str, int]] = None,
) -> Dict[str, Any]:
    named_check_findings = named_check_findings or {}
    all_findings = list(findings)
    for check_name in _V03_AUDIT_CHECK_NAMES:
        all_findings.extend(named_check_findings.get(check_name, []))
    summary = {
        "fail": sum(1 for finding in all_findings if finding.get("status") == "FAIL"),
        "warning": sum(1 for finding in all_findings if finding.get("status") == "WARNING"),
        "pass": sum(1 for finding in all_findings if finding.get("status") == "PASS"),
    }
    for check_name in _V03_AUDIT_CHECK_NAMES:
        check_items = named_check_findings.get(check_name, [])
        for status in ("fail", "warning", "pass"):
            summary[f"{check_name}_{status}"] = sum(
                1 for finding in check_items if str(finding.get("status") or "").lower() == status
            )
    return {
        "schema_version": DR_SCHEMA_VERSION_V0_3,
        "valid": not any(finding.get("status") == "FAIL" for finding in all_findings),
        "findings": all_findings,
        "checked_at": checked_at,
        "summary": summary,
        "serialization_metrics": deepcopy(serialization_metrics or {}),
        "compatibility_metrics": deepcopy(compatibility_metrics or {}),
    }


def _has_default_relationship_violation(value: Any) -> bool:
    text = _nonempty_str(value).lower()
    if not text:
        return False
    if "intimate_partner" in text:
        return True
    positive_markers = ("默认女友", "默认是女友", "默认关系是女友", "默认关系定位为女友", "关系定位为女友", "关系定位：女友", "作为女友")
    return text.strip() == "女友" or any(marker in text for marker in positive_markers)


def _identity_consistency_findings(
    manifest: Dict[str, Any],
    payload: Dict[str, Any],
    resident: Dict[str, Any],
) -> List[Dict[str, str]]:
    findings: List[Dict[str, str]] = []
    resident_identity = _as_dict(payload.get("resident_identity"))
    layer_outputs = _as_dict(_as_dict(payload.get("graph_snapshot")).get("layer_outputs"))
    identity_profile = _as_dict(layer_outputs.get("identity_profile"))
    basic_fields = _identity_fields(identity_profile, "basic_identity")
    anchor_fields = _identity_fields(identity_profile, "identity_anchor")
    growth_fields = _identity_fields(identity_profile, "growth_background")

    def _expect_equal(actual: Any, expected: Any, path: str, code: str) -> None:
        if _nonempty_str(expected) and actual != expected:
            findings.append(_finding("FAIL", code, f"{path} must match basic_identity.{code.rsplit('_', 1)[-1].lower()}", path))

    basic_resident_id = _nonempty_str(basic_fields.get("resident_id"))
    basic_name = _nonempty_str(basic_fields.get("name"))
    basic_city = _nonempty_str(basic_fields.get("city")) or _nonempty_str(anchor_fields.get("representative_city"))
    basic_language = _normalize_language(basic_fields.get("primary_language"))

    _expect_equal(manifest.get("resident_id"), basic_resident_id, "manifest.resident_id", "DR_IDENTITY_CONSISTENCY_RESIDENT_ID")
    _expect_equal(resident_identity.get("resident_id"), basic_resident_id, "payload.resident_identity.resident_id", "DR_IDENTITY_CONSISTENCY_RESIDENT_ID")
    _expect_equal(manifest.get("resident_name"), basic_name, "manifest.resident_name", "DR_IDENTITY_CONSISTENCY_NAME")
    _expect_equal(resident_identity.get("name"), basic_name, "payload.resident_identity.name", "DR_IDENTITY_CONSISTENCY_NAME")
    _expect_equal(resident_identity.get("city_symbol"), basic_city, "payload.resident_identity.city_symbol", "DR_IDENTITY_CONSISTENCY_CITY")

    if _nonempty_str(basic_fields.get("primary_language")) and _normalize_language(resident_identity.get("primary_language")) != basic_language:
        findings.append(
            _finding(
                "FAIL",
                "DR_IDENTITY_CONSISTENCY_LANGUAGE",
                "payload.resident_identity.primary_language must match normalized basic_identity.primary_language",
                "payload.resident_identity.primary_language",
            )
        )

    domain_focus = resident_identity.get("domain_focus")
    if isinstance(domain_focus, list):
        forbidden_focus = sorted(
            focus for focus in {str(item).lower() for item in domain_focus} if focus in _FORBIDDEN_STAGE_7_4_DOMAIN_FOCUS
        )
        if forbidden_focus:
            findings.append(
                _finding(
                    "FAIL",
                    "DR_IDENTITY_CONSISTENCY_DOMAIN_FOCUS",
                    f"domain_focus contains out-of-stage capabilities: {forbidden_focus}",
                    "payload.resident_identity.domain_focus",
                )
            )

    identity_definition = _nonempty_str(anchor_fields.get("identity_definition"))
    summary_texts = [
        resident_identity.get("personality_summary"),
        resident.get("description"),
        _as_dict(payload.get("resident_blueprint")).get("description"),
    ]
    if identity_definition and any(_has_default_relationship_violation(text) for text in summary_texts):
        findings.append(
            _finding(
                "FAIL",
                "DR_IDENTITY_CONSISTENCY_IDENTITY_DEFINITION",
                "resident.description/personality_summary must not conflict with identity_definition default relationship",
                "payload.resident_identity.personality_summary",
            )
        )

    disclosure = _nonempty_str(resident.get("disclosure"))
    appearance_source = _nonempty_str(basic_fields.get("appearance_source"))
    growth_limits = _nonempty_str(growth_fields.get("growth_constraints"))
    if ("虚构" in appearance_source or "原创" in appearance_source) and "虚构" not in disclosure:
        findings.append(_finding("FAIL", "DR_IDENTITY_CONSISTENCY_DISCLOSURE", "disclosure must preserve fictional appearance_source", "resident.disclosure"))
    if "不对应现实真人" in growth_limits and "不对应现实真人" not in disclosure:
        findings.append(_finding("FAIL", "DR_IDENTITY_CONSISTENCY_DISCLOSURE", "disclosure must preserve growth_limits real-person boundary", "resident.disclosure"))

    for path, value in (
        ("payload.graph_snapshot.layer_outputs.identity_profile.identity_anchor.fields.identity_definition", identity_definition),
        ("payload.resident_identity.personality_summary", resident_identity.get("personality_summary")),
        ("resident.description", resident.get("description")),
    ):
        if _has_default_relationship_violation(value):
            findings.append(_finding("FAIL", "DR_IDENTITY_CONSISTENCY_DEFAULT_RELATIONSHIP", "default relationship must not be girlfriend/intimate_partner", path))

    return findings


def _environment_mapping_findings(payload: Dict[str, Any]) -> List[Dict[str, str]]:
    findings: List[Dict[str, str]] = []
    modules = [module for module in payload.get("modules", []) if isinstance(module, dict)]
    matches = [module for module in modules if module.get("module_id") == _ENVIRONMENT_MODULE_ID]
    if len(matches) != 1:
        return [
            _finding(
                "FAIL",
                "DR_ENVIRONMENT_MAPPING_MODULE_UNRESOLVED",
                f"环境模块必须唯一；module_id={_ENVIRONMENT_MODULE_ID}, matches={len(matches)}",
                "payload.modules.environment_setting",
            )
        ]
    module = matches[0]
    current_fields = {
        _field_identifier(field, index): field
        for index, field in enumerate(_module_fields_from_field_input(module))
        if isinstance(field, dict)
    }
    output = _as_dict(_as_dict(module.get("outputs")).get(_ENVIRONMENT_OUTPUT_KEY))
    output_fields = output.get("fields") if isinstance(output.get("fields"), dict) else {}
    for field_id in _ENVIRONMENT_FIELD_IDS:
        path = f"payload.modules.{_ENVIRONMENT_MODULE_ID}.outputs.{_ENVIRONMENT_OUTPUT_KEY}.fields.{field_id}"
        field = current_fields.get(field_id)
        if field is None:
            findings.append(_finding("FAIL", "DR_ENVIRONMENT_CURRENT_FIELD_MISSING", f"环境 current field 不存在: {field_id}", path))
            continue
        mapping = _nonempty_str(field.get("dr_mapping"))
        expected_mapping = _canonical_environment_mapping(field_id)
        if mapping != expected_mapping:
            findings.append(
                _finding(
                    "FAIL",
                    "DR_ENVIRONMENT_MAPPING_PATH_INVALID",
                    f"环境映射路径不正确；field_id={field_id}, expected={expected_mapping}, actual={mapping or '(empty)'}",
                    path,
                )
            )
            continue
        if field_id not in output_fields:
            findings.append(_finding("FAIL", "DR_ENVIRONMENT_MAPPING_VALUE_MISSING", f"环境输出缺少 field_id={field_id}", path))
            continue
        current_value = field.get("value") if "value" in field else field.get("field_value")
        if output_fields.get(field_id) != current_value:
            findings.append(
                _finding(
                    "FAIL",
                    "DR_ENVIRONMENT_MAPPING_VALUE_MISMATCH",
                    f"环境输出与 current field 不一致；field_id={field_id}",
                    path,
                )
            )
            continue
        findings.append(
            _finding(
                "PASS",
                "DR_ENVIRONMENT_MAPPING_RESOLVED",
                f"环境映射已解析到权威 payload.modules 输出；field_id={field_id}",
                path,
            )
        )
    return findings


def _v03_version_findings(
    resident: Dict[str, Any],
    manifest: Dict[str, Any],
    payload: Dict[str, Any],
    compile_info: Dict[str, Any],
) -> List[Dict[str, str]]:
    checks = (
        (resident.get("dr_version"), DR_VERSION_V0_3, "resident.dr_version", "dr_version"),
        (manifest.get("dr_schema_version"), DR_SCHEMA_VERSION_V0_3, "manifest.dr_schema_version", "dr_schema_version"),
        (manifest.get("source_protocol_version"), PROTOCOL_VERSION_V0_4, "manifest.source_protocol_version", "protocol_version"),
        (compile_info.get("schema_version"), DR_SCHEMA_VERSION_V0_3, "compile_info.schema_version", "dr_schema_version"),
        (compile_info.get("protocol_version"), PROTOCOL_VERSION_V0_4, "compile_info.protocol_version", "protocol_version"),
        (_as_dict(payload.get("memory_config")).get("schema_version"), DR_SCHEMA_VERSION_V0_3, "payload.memory_config.schema_version", "dr_schema_version"),
        (_as_dict(payload.get("lattice_config")).get("schema_version"), DR_SCHEMA_VERSION_V0_3, "payload.lattice_config.schema_version", "dr_schema_version"),
        (_as_dict(payload.get("voice_config")).get("schema_version"), DR_SCHEMA_VERSION_V0_3, "payload.voice_config.schema_version", "dr_schema_version"),
    )
    findings: List[Dict[str, str]] = []
    for actual, expected, path, concept in checks:
        if actual != expected:
            findings.append(
                _finding(
                    "FAIL",
                    "DR_INTERNAL_VERSION_MISMATCH",
                    f"内部版本未与根级 {concept} 同步；expected={expected}, actual={actual}",
                    path,
                )
            )
    if not findings:
        findings.append(
            _finding(
                "PASS",
                "DR_VERSION_METADATA_CONSISTENT",
                "根级 DR、schema、protocol 版本与正式兼容元数据一致；居民内容版本和 compiler/module 版本保持独立语义",
                "dr_version",
            )
        )
    return findings


def _identity_hardcode_terms(payload: Dict[str, Any]) -> Dict[str, str]:
    layer_outputs = _as_dict(_as_dict(payload.get("graph_snapshot")).get("layer_outputs"))
    identity_profile = _as_dict(layer_outputs.get("identity_profile"))
    basic_fields = _identity_fields(identity_profile, "basic_identity")
    resident_identity = _as_dict(payload.get("resident_identity"))
    terms: Dict[str, str] = {}
    for field_id in ("name", "pinyin", "nickname", "display_alias", "codename", "export_name", "resident_id"):
        value = _nonempty_str(basic_fields.get(field_id)) or _nonempty_str(resident_identity.get(field_id))
        if value:
            terms[field_id] = value
    if "pinyin" not in terms:
        codename_tokens = [
            token
            for token in re.split(r"[^A-Za-z0-9]+", terms.get("codename", ""))
            if token
        ]
        resident_id_tokens = [
            token
            for token in re.split(r"[^A-Za-z0-9]+", terms.get("resident_id", ""))
            if token
        ]
        while resident_id_tokens and resident_id_tokens[-1].isdigit():
            resident_id_tokens.pop()
        if (
            codename_tokens
            and resident_id_tokens
            and len(codename_tokens[0]) >= 3
            and codename_tokens[0].casefold()
            == resident_id_tokens[-1].casefold()
        ):
            terms["pinyin"] = codename_tokens[0]
    return terms


def _text_contains_identity_term(text: str, term: str) -> bool:
    if not text or not term:
        return False
    has_cjk = any("\u4e00" <= char <= "\u9fff" for char in term)
    if has_cjk:
        return term in text
    return bool(
        re.search(
            rf"(?<![A-Za-z0-9]){re.escape(term)}(?![A-Za-z0-9])",
            text,
            flags=re.IGNORECASE,
        )
    )


def _technical_identity_reference_field(field_id: str) -> bool:
    normalized = field_id.lower()
    leaf = normalized.rsplit(".", 1)[-1].split("[", 1)[0]
    reference_value = (
        leaf == "value"
        and any(
            container in normalized
            for container in (
                ".reference[",
                ".references[",
                ".reference_option[",
                ".reference_options[",
                ".recommended_reference[",
                ".recommended_references[",
            )
        )
    )
    return (
        leaf in {"resident_id", "resident_ids", "namespace", "memory_namespace"}
        or leaf == "source_id"
        or reference_value
        or leaf.endswith("_resident_id")
        or leaf.endswith("_resident_ids")
        or leaf.endswith("_ref")
        or leaf.endswith("_reference")
    )


def _natural_language_text_path(field_path: str) -> bool:
    leaf = field_path.lower().rsplit(".", 1)[-1].split("[", 1)[0]
    exact = {
        "description",
        "text",
        "content",
        "prompt",
        "sample",
        "dialogue",
        "rule",
        "seed",
        "hint",
        "cue",
        "summary",
        "message",
        "instruction",
        "note",
        "default",
        "custom_text",
        "template_default",
        "template_defaults",
        "memory_seed",
        "memory_seeds",
        "dialogue_rule",
        "dialogue_rules",
        "visual_hint",
        "visual_hints",
        "behavior_policy",
        "behavior_rule",
        "behavior_rules",
        "few_shot",
        "few_shots",
        "few_shot_example",
        "few_shot_examples",
    }
    suffixes = (
        "_description",
        "_text",
        "_content",
        "_prompt",
        "_sample",
        "_dialogue",
        "_dialogue_rule",
        "_rule",
        "_seed",
        "_hint",
        "_cue",
        "_summary",
        "_message",
        "_instruction",
        "_note",
        "_default_text",
        "_template_defaults",
        "_seeds",
        "_dialogue_rules",
        "_visual_hints",
        "_behavior_policy",
        "_behavior_rules",
        "_few_shot",
        "_few_shots",
        "_few_shot_example",
        "_few_shot_examples",
    )
    return leaf in exact or leaf.endswith(suffixes)


def _identity_identifier_path(field_path: str) -> bool:
    normalized = field_path.lower()
    leaf = normalized.rsplit(".", 1)[-1].split("[", 1)[0]
    option_containers = {
        "option",
        "options",
        "selected_option",
        "selected_options",
        "default_selected_option",
        "default_selected_options",
        "reference_option",
        "reference_options",
        "reference",
        "references",
        "recommended_reference",
        "recommended_references",
    }
    path_segments = {
        segment.split("[", 1)[0]
        for segment in normalized.split(".")
    }
    return (
        leaf in {
            "id",
            "key",
            "name",
            "module_id",
            "node_id",
            "config_id",
            "profile_id",
            "template_id",
            "preset_id",
            "option",
            "options",
            "selected_option",
            "selected_options",
            "default_selected_option",
            "default_selected_options",
            "reference_option",
            "reference_options",
            "reference",
            "references",
            "recommended_reference",
            "recommended_references",
        }
        or (
            leaf in {"value", "values"}
            and bool(path_segments.intersection(option_containers))
        )
        or leaf.endswith(("_id", "_key", "_identifier"))
    )


def _identity_config_identifier_path(field_path: str) -> bool:
    normalized = field_path.lower()
    leaf = normalized.rsplit(".", 1)[-1].split("[", 1)[0]
    return (
        leaf
        in {
            "config_id",
            "profile_id",
            "template_id",
            "preset_id",
            "option",
            "options",
            "selected_option",
            "selected_options",
            "default_selected_option",
            "default_selected_options",
            "reference_option",
            "reference_options",
            "reference",
            "references",
            "recommended_reference",
            "recommended_references",
        }
        or (
            leaf in {"value", "values"}
            and any(
                container in normalized
                for container in (
                    ".option[",
                    ".options[",
                    ".selected_option[",
                    ".selected_options[",
                    ".reference_option[",
                    ".reference_options[",
                    ".reference[",
                    ".references[",
                    ".recommended_reference[",
                    ".recommended_references[",
                )
            )
        )
    )


def _identity_text_type(layer_id: str, module: Dict[str, Any], field_id: str, source_kind: str) -> str:
    combined = " ".join(
        (
            str(module.get("module_id") or ""),
            str(module.get("module_type") or ""),
            str(module.get("category") or ""),
            field_id,
        )
    ).lower()
    if source_kind == "default":
        return "template_default"
    if layer_id == "layer_5" or "memory" in combined or "seed" in combined:
        return "memory_seed"
    if "dialogue" in combined or "sample" in combined:
        return "dialogue_rule"
    if layer_id == "layer_8" or "behavior" in combined:
        return "behavior_policy"
    if layer_id == "layer_10" or any(token in combined for token in ("visual", "hint", "cue")):
        return "visual_hint"
    return "non_identity_module_text"


def _identity_hardcode_findings(
    collection: Dict[str, Any],
    payload: Dict[str, Any],
    root_projections: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, str]]:
    terms = _identity_hardcode_terms(payload)
    if not terms:
        return [
            _finding(
                "PASS",
                "DR_IDENTITY_LITERAL_EXPORT_GATE_PASSED",
                "未发现可用于跨层扫描的居民身份字面值；导出 Gate 无需阻止导出",
                "payload.modules",
            )
        ]
    findings: List[Dict[str, str]] = []
    seen: set[tuple[str, str, str, str, tuple[str, ...]]] = set()
    source_text_matches: set[tuple[str, str, tuple[str, ...]]] = set()
    mirror_text_matches: set[tuple[str, str, tuple[str, ...]]] = set()
    authoritative_text_matches: set[tuple[str, tuple[str, ...]]] = set()
    derived_text_matches: set[tuple[str, tuple[str, ...]]] = set()

    def matched_identity_fields(
        text: str, source_kind: str, field_id: str
    ) -> List[str]:
        matched = [
            field
            for field, term in terms.items()
            if _text_contains_identity_term(text, term)
        ]
        # Short generic ASCII values such as "May", "Joy", or "core" are
        # ambiguous in prose. They remain enforceable in identifier fields or
        # when the entire configured value is the identity literal.
        def has_short_ascii_identity_evidence(field: str) -> bool:
            term = terms[field]
            if not term.isascii():
                return True
            normalized_text = text.strip()
            normalized_term = term.strip()
            ambiguous_person_labels = {
                "name",
                "nickname",
                "display_alias",
            }
            if field in ambiguous_person_labels:
                if source_kind in {"structure_key", "projection"}:
                    return False
                if source_kind == "identifier":
                    if not _identity_config_identifier_path(
                        field_id
                    ):
                        return False
                    return bool(
                        re.match(
                            rf"^{re.escape(normalized_term.casefold())}"
                            rf"(?:[^a-z0-9]|$)",
                            normalized_text.casefold(),
                        )
                    )
                return bool(
                    re.search(
                        rf"(?<![A-Za-z0-9])"
                        rf"{re.escape(normalized_term)}"
                        rf"(?![A-Za-z0-9])",
                        text,
                    )
                )
            if len(normalized_term) >= 5:
                return True
            if source_kind in {"structure_key", "projection"}:
                return False
            if field == "codename":
                return False
            casefolded_text = normalized_text.casefold()
            casefolded_term = normalized_term.casefold()
            if casefolded_text == casefolded_term:
                return True
            if source_kind != "identifier":
                return False
            return bool(
                re.match(
                    rf"^{re.escape(casefolded_term)}(?:[^a-z0-9]|$)",
                    casefolded_text,
                )
            )

        return sorted(
            field
            for field in matched
            if has_short_ascii_identity_evidence(field)
        )

    def inspect_text(
        text: Any,
        *,
        layer_id: str,
        module: Dict[str, Any],
        node_id: str,
        field_id: str,
        source_kind: str,
    ) -> None:
        if not isinstance(text, str) or not text:
            return
        matched = matched_identity_fields(
            text,
            source_kind,
            field_id,
        )
        if not matched:
            return
        # Exact resident-scoped foreign keys are allowed. A resident_id
        # embedded in a rule, identifier, or surrounding text is not.
        resident_id = terms.get("resident_id")
        if (
            resident_id
            and _technical_identity_reference_field(field_id)
            and text.strip().casefold() == resident_id.casefold()
        ):
            return
        module_id = _nonempty_str(module.get("module_id")) or "(canvas)"
        text_match_key = (
            module_id,
            text.casefold(),
            tuple(matched),
        )
        derived_match_key = (text.casefold(), tuple(matched))
        if source_kind == "projection":
            if (
                derived_match_key in authoritative_text_matches
                or derived_match_key in derived_text_matches
            ):
                return
            derived_text_matches.add(derived_match_key)
        else:
            authoritative_text_matches.add(derived_match_key)
        if source_kind in {"output", "canvas_mirror"}:
            if (
                text_match_key in source_text_matches
                or text_match_key in mirror_text_matches
            ):
                return
            mirror_text_matches.add(text_match_key)
        else:
            source_text_matches.add(text_match_key)
        text_type = _identity_text_type(layer_id, module, field_id, source_kind)
        dedupe_key = (
            module_id,
            node_id,
            field_id,
            text_type,
            tuple(matched),
        )
        if dedupe_key in seen:
            return
        seen.add(dedupe_key)
        path = (
            field_id
            if layer_id == "derived_projection"
            else (
                f"layers[{layer_id}].modules[{module_id}]."
                f"nodes[{node_id}].fields[{field_id}]"
            )
        )
        findings.append(
            _finding(
                "FAIL",
                "DR_IDENTITY_LITERAL_OUTSIDE_ALLOWED_SCOPE",
                (
                    "在允许的身份事实源和居民作用域字段之外检测到居民身份字面值；"
                    f"layer_id={layer_id}, module_id={module_id}, node_id={node_id}, "
                    f"field_id={field_id}, text_type={text_type}, "
                    f"identity_fields={','.join(matched)}；未自动改写居民内容，已阻止导出"
                ),
                path,
            )
        )

    skipped_branches = {
        "fields",
        "legacy_fields",
        "legacy_data_fields",
        "field_registry",
        "i18n_keys",
    }

    def scan_structure(
        value: Any,
        *,
        layer_id: str,
        module: Dict[str, Any],
        node_id: str,
        field_path: str,
        source_kind: str,
        scan_all_strings: bool = False,
    ) -> None:
        if isinstance(value, str):
            if (
                scan_all_strings
                or _natural_language_text_path(field_path)
                or _identity_identifier_path(field_path)
            ):
                inspect_text(
                    value,
                    layer_id=layer_id,
                    module=module,
                    node_id=node_id,
                    field_id=field_path,
                    source_kind=(
                        "identifier"
                        if _identity_identifier_path(field_path)
                        else source_kind
                    ),
                )
        elif isinstance(value, dict):
            for key, item in value.items():
                key_text = str(key)
                if key_text in skipped_branches:
                    continue
                nested_path = f"{field_path}.{key_text}" if field_path else key_text
                inspect_text(
                    key_text,
                    layer_id=layer_id,
                    module=module,
                    node_id=node_id,
                    field_id=f"{nested_path}.__key__",
                    source_kind="structure_key",
                )
                if isinstance(item, str):
                    if (
                        scan_all_strings
                        or _natural_language_text_path(nested_path)
                        or _natural_language_text_path(field_path)
                        or _identity_identifier_path(nested_path)
                    ):
                        inspect_text(
                            item,
                            layer_id=layer_id,
                            module=module,
                            node_id=node_id,
                            field_id=nested_path,
                            source_kind=(
                                "identifier"
                                if _identity_identifier_path(nested_path)
                                else source_kind
                            ),
                        )
                elif isinstance(item, (dict, list)):
                    scan_structure(
                        item,
                        layer_id=layer_id,
                        module=module,
                        node_id=node_id,
                        field_path=nested_path,
                        source_kind=source_kind,
                        scan_all_strings=scan_all_strings,
                    )
        elif isinstance(value, list):
            for index, item in enumerate(value):
                nested_path = f"{field_path}[{index}]"
                if isinstance(item, str):
                    if (
                        scan_all_strings
                        or _natural_language_text_path(field_path)
                        or _identity_identifier_path(field_path)
                    ):
                        inspect_text(
                            item,
                            layer_id=layer_id,
                            module=module,
                            node_id=node_id,
                            field_id=nested_path,
                            source_kind=(
                                "identifier"
                                if _identity_identifier_path(field_path)
                                else source_kind
                            ),
                        )
                elif isinstance(item, (dict, list)):
                    scan_structure(
                        item,
                        layer_id=layer_id,
                        module=module,
                        node_id=node_id,
                        field_path=nested_path,
                        source_kind=source_kind,
                        scan_all_strings=scan_all_strings,
                    )

    for module in collection.get("modules", []):
        if not isinstance(module, dict):
            continue
        layer_id = _nonempty_str(module.get("layer_id")) or "(unknown)"
        if layer_id == "layer_1":
            continue
        inspect_text(
            module.get("module_id"),
            layer_id=layer_id,
            module=module,
            node_id="module",
            field_id="module_id",
            source_kind="identifier",
        )
        for field_id in (
            "module_name",
            "description",
            "text",
            "content",
            "prompt",
        ):
            inspect_text(
                module.get(field_id),
                layer_id=layer_id,
                module=module,
                node_id="module",
                field_id=field_id,
                source_kind=(
                    "identifier"
                    if field_id == "module_name"
                    else "module"
                ),
            )
        scan_structure(
            _as_dict(module.get("config")),
            layer_id=layer_id,
            module=module,
            node_id="module",
            field_path="config",
            source_kind="module",
        )
        scan_structure(
            _as_dict(module.get("inputs")),
            layer_id=layer_id,
            module=module,
            node_id="module",
            field_path="inputs",
            source_kind="module",
        )
        for branch_name in ("metadata", "ui_config"):
            scan_structure(
                _as_dict(module.get(branch_name)),
                layer_id=layer_id,
                module=module,
                node_id="module",
                field_path=branch_name,
                source_kind="module",
            )
        for branch_name in ("tags", "output_schema"):
            scan_structure(
                module.get(branch_name) or [],
                layer_id=layer_id,
                module=module,
                node_id="module",
                field_path=branch_name,
                source_kind="identifier",
                scan_all_strings=True,
            )
        module_nodes = _module_graph_nodes(module)
        for node in module_nodes:
            node_id = _module_graph_node_id(node) or "(unknown)"
            inspect_text(
                node_id,
                layer_id=layer_id,
                module=module,
                node_id=node_id,
                field_id="node_id",
                source_kind="identifier",
            )
            params = node.get("params") if isinstance(node.get("params"), dict) else {}
            fields = params.get("fields") if isinstance(params.get("fields"), list) else []
            for index, field in enumerate(fields):
                if not isinstance(field, dict):
                    continue
                field_id = _field_identifier(field, index)
                value = field.get("field_value") if "field_value" in field else field.get("value")
                scan_structure(
                    value,
                    layer_id=layer_id,
                    module=module,
                    node_id=node_id,
                    field_path=field_id,
                    source_kind="field",
                    scan_all_strings=True,
                )
                scan_structure(
                    {
                        key: item
                        for key, item in field.items()
                        if key not in {"field_value", "value"}
                    },
                    layer_id=layer_id,
                    module=module,
                    node_id=node_id,
                    field_path=f"{field_id}.metadata",
                    source_kind="field",
                )
            checkbox_config = _as_dict(params.get("checkbox_config") or params.get("checklist_config"))
            inspect_text(
                checkbox_config.get("custom_text"),
                layer_id=layer_id,
                module=module,
                node_id=node_id,
                field_id="custom_text",
                source_kind="custom_text",
            )
            scan_structure(
                params,
                layer_id=layer_id,
                module=module,
                node_id=node_id,
                field_path="params",
                source_kind="params",
            )
            scan_structure(
                node.get("metadata") if isinstance(node.get("metadata"), dict) else {},
                layer_id=layer_id,
                module=module,
                node_id=node_id,
                field_path="metadata",
                source_kind="params",
            )
        for node in module_nodes:
            node_id = _module_graph_node_id(node) or "(unknown)"
            scan_structure(
                node.get("outputs") if isinstance(node.get("outputs"), dict) else {},
                layer_id=layer_id,
                module=module,
                node_id=node_id,
                field_path="outputs",
                source_kind="output",
                scan_all_strings=True,
            )
        input_schema = module.get("input_schema") if isinstance(module.get("input_schema"), list) else []
        scan_structure(
            input_schema,
            layer_id=layer_id,
            module=module,
            node_id="input_schema",
            field_path="input_schema",
            source_kind="default",
        )
        scan_structure(
            _as_dict(module.get("outputs")),
            layer_id=layer_id,
            module=module,
            node_id="module_output",
            field_path="outputs",
            source_kind="output",
            scan_all_strings=True,
        )
    for node in collection.get("nodes", []):
        if not isinstance(node, dict):
            continue
        layer_id = _nonempty_str(node.get("layer_id")) or _nonempty_str(_as_dict(node.get("data")).get("layer_id")) or "(unknown)"
        module_id = _nonempty_str(node.get("module_id")) or _nonempty_str(_as_dict(node.get("data")).get("module_id"))
        if layer_id == "layer_1" or module_id == "module_basic_identity":
            continue
        module = {"module_id": module_id or "(canvas)", "layer_id": layer_id, "module_type": node.get("node_type") or node.get("type")}
        scan_structure(
            node.get("params") or {},
            layer_id=layer_id,
            module=module,
            node_id=_nonempty_str(node.get("node_id")) or _nonempty_str(node.get("id")) or "(unknown)",
            field_path="params",
            source_kind="canvas_mirror",
        )
        scan_structure(
            node.get("data") or {},
            layer_id=layer_id,
            module=module,
            node_id=_nonempty_str(node.get("node_id")) or _nonempty_str(node.get("id")) or "(unknown)",
            field_path="data",
            source_kind="canvas_mirror",
        )
    projection_branches = (
        "behavior",
        "expression",
        "relationship",
        "behavior_policy",
        "runtime_dialogue_projection",
    )
    for branch_name in projection_branches:
        branch_value = payload.get(branch_name)
        if branch_value is None:
            continue
        projection_path = f"payload.{branch_name}"
        scan_structure(
            branch_value,
            layer_id="derived_projection",
            module={
                "module_id": projection_path,
                "layer_id": "derived_projection",
                "module_type": "read_only_projection",
            },
            node_id="projection",
            field_path=projection_path,
            source_kind="projection",
            scan_all_strings=True,
        )
    layer_outputs = _as_dict(
        _as_dict(payload.get("graph_snapshot")).get("layer_outputs")
    )
    for output_name, output_value in layer_outputs.items():
        if output_name in {"identity_profile", "layer_1"}:
            continue
        projection_path = (
            f"payload.graph_snapshot.layer_outputs.{output_name}"
        )
        scan_structure(
            output_value,
            layer_id="derived_projection",
            module={
                "module_id": projection_path,
                "layer_id": "derived_projection",
                "module_type": "read_only_projection",
            },
            node_id="projection",
            field_path=projection_path,
            source_kind="projection",
            scan_all_strings=True,
        )
    for projection_name, projection_value in (
        root_projections or {}
    ).items():
        projection_path = projection_name
        scan_structure(
            projection_value,
            layer_id="derived_projection",
            module={
                "module_id": projection_path,
                "layer_id": "derived_projection",
                "module_type": "read_only_projection",
            },
            node_id="projection",
            field_path=projection_path,
            source_kind="projection",
            scan_all_strings=True,
        )
    if findings:
        return findings
    return [
        _finding(
            "PASS",
            "DR_IDENTITY_LITERAL_EXPORT_GATE_PASSED",
            "居民身份字面值仅存在于 Layer 1、身份兼容投影或允许的居民作用域字段",
            "payload.modules",
        )
    ]


def _collect_layer_contexts(workflow: Dict[str, Any], layers: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    contexts: Dict[str, Dict[str, Any]] = {}
    workflow_contexts = workflow.get("layer_contexts") if isinstance(workflow.get("layer_contexts"), dict) else {}
    for layer in layers:
        layer_id = layer.get("layer_id", "")
        raw_context = workflow_contexts.get(layer_id)
        context = _as_dict(raw_context)
        if not context:
            context = _as_dict(layer.get("layer_context"))
        contexts[layer_id] = {
            "layer_context": context,
            "context_bindings": context.get("context_bindings", []) if isinstance(context.get("context_bindings"), list) else [],
        }
    return contexts


def _node_layer(nodes: List[Dict[str, Any]], node_id: Any) -> str | None:
    if not node_id:
        return None
    for node in nodes:
        candidate_id = node.get("node_id") or node.get("id")
        if candidate_id == node_id:
            layer_id = node.get("layer_id")
            if isinstance(layer_id, str) and layer_id:
                return layer_id
            data = node.get("data") if isinstance(node.get("data"), dict) else {}
            if isinstance(data.get("layer_id"), str) and data.get("layer_id"):
                return data.get("layer_id")
    return None


# --- 1. collect ------------------------------------------------------------
def collect_canvas(canvas: Dict[str, Any]) -> Dict[str, Any]:
    """Collect the 13 layers, modules and slots from the canvas + catalog.

    The canvas (workflow + nodes + edges) defines which layers are present. The
    module / slot capability content comes from the catalog unless the canvas
    explicitly carries its own `modules` / `slots` arrays (which then win).
    """
    canvas = canvas or {}
    workflow = _as_dict(canvas.get("workflow")) or canvas
    nodes = canvas.get("nodes") or workflow.get("nodes") or []
    edges = canvas.get("edges") or workflow.get("edges") or []

    # Modules: prefer canvas-supplied, else the authoritative catalog.
    if isinstance(canvas.get("modules"), list):
        raw_modules = canvas.get("modules")
    elif isinstance(workflow.get("modules"), list):
        raw_modules = workflow.get("modules")
    else:
        raw_modules = None
    if raw_modules is not None:
        modules = [deepcopy(_as_dict(m)) for m in raw_modules]
    else:
        modules = [m.model_dump(mode="json") for m in get_module_catalog()]
        modules = [
            module
            for module in modules
            if _as_dict(module.get("config")).get("optional_module") is not True
        ]
    modules = [module for module in modules if not _is_catalog_only_module(module)]
    modules = _normalize_reference_inputs(modules)
    compatibility_findings: List[Dict[str, str]] = []
    for module in modules:
        _sync_environment_module_output(module)
    compatibility_metrics = _sync_current_field_compatibility(
        modules, compatibility_findings
    )
    _normalize_reference_registries(modules, compatibility_findings)

    # Slots: prefer canvas-supplied, else the catalog.
    raw_slots = canvas.get("slots") or workflow.get("slots")
    if raw_slots:
        slots = [_as_dict(s) for s in raw_slots]
    else:
        slots = [s.model_dump(mode="json") for s in get_slot_catalog()]

    # Which canonical layers are present ON THE CANVAS. Presence is derived from
    # the canvas graph (a node whose id is a layer_id, or a node referencing a
    # layer_id) — NOT from the catalog fallback, so the completeness check
    # reflects what the user actually has on the canvas.
    present_layer_ids: set[str] = set()
    for node in nodes:
        node = _as_dict(node)
        node_id = node.get("node_id") or node.get("id")
        if node_id in CANONICAL_LAYER_IDS:
            present_layer_ids.add(node_id)
        layer_ref = node.get("layer_id")
        if layer_ref in CANONICAL_LAYER_IDS:
            present_layer_ids.add(layer_ref)

    # Group module_ids per layer.
    modules_by_layer: Dict[str, List[str]] = {}
    for module in modules:
        modules_by_layer.setdefault(module.get("layer_id", ""), []).append(module.get("module_id", ""))

    layers: List[Dict[str, Any]] = []
    for layer_id, layer_name, layer_order in CANONICAL_LAYERS:
        module_ids = modules_by_layer.get(layer_id, [])
        # Layer 4/6/13 currently contain only protocol/catalog shells. Their
        # explicit design state must survive those compatibility module ids so
        # consumers do not mistake a shell for authored resident capability.
        empty_design = empty_layer_design_metadata(layer_id)
        layers.append(
            {
                "layer_id": layer_id,
                "layer_name": layer_name,
                "layer_order": layer_order,
                "module_ids": module_ids,
                "present": layer_id in present_layer_ids,
                **empty_design,
            }
        )

    layer_contexts = _collect_layer_contexts(workflow, layers)

    return {
        "workflow": workflow,
        "nodes": [_as_dict(n) for n in nodes],
        "edges": [_as_dict(e) for e in edges],
        "layers": layers,
        "modules": modules,
        "slots": slots,
        "layer_contexts": layer_contexts,
        "compatibility_findings": compatibility_findings,
        "compatibility_metrics": compatibility_metrics,
    }


# --- 2. validate -----------------------------------------------------------
def validate_collection(collection: Dict[str, Any]) -> List[Dict[str, str]]:
    """Run the four mandatory DR checks. Returns a list of findings.

    1. 13 layers completeness
    2. module_id uniqueness
    3. slot_type <-> module slot_type matching
    4. no illegal runtime provider binding (mock-only this stage)
    """
    findings: List[Dict[str, str]] = []
    layers = collection["layers"]
    modules = collection["modules"]
    slots = collection["slots"]
    from ..dr.v2.validator.compile_audit_validator import provider_boundary_findings

    # 1. 13 layers completeness ------------------------------------------------
    present_ids = {layer["layer_id"] for layer in layers if layer.get("present")}
    defined_ids = {layer["layer_id"] for layer in layers}
    missing_defined = CANONICAL_LAYER_IDS - defined_ids
    if missing_defined:
        findings.append(
            _finding("FAIL", "DR_LAYERS_INCOMPLETE", f"missing canonical layers: {sorted(missing_defined)}", "layers")
        )
    missing_on_canvas = CANONICAL_LAYER_IDS - present_ids
    if missing_on_canvas:
        findings.append(
            _finding(
                "WARNING",
                "DR_LAYER_NOT_ON_CANVAS",
                f"canonical layers not present on canvas: {sorted(missing_on_canvas)}",
                "layers",
            )
        )
    if len(layers) != len(CANONICAL_LAYERS):
        findings.append(
            _finding("FAIL", "DR_LAYER_COUNT", f"expected {len(CANONICAL_LAYERS)} layers, got {len(layers)}", "layers")
        )

    # 2. module_id uniqueness --------------------------------------------------
    seen: set[str] = set()
    for index, module in enumerate(modules):
        module_id = module.get("module_id")
        if not module_id:
            findings.append(_finding("FAIL", "DR_MODULE_ID_EMPTY", "module has empty module_id", f"modules[{index}]"))
            continue
        if module_id in seen:
            findings.append(
                _finding("FAIL", "DR_MODULE_ID_DUPLICATE", f"duplicate module_id: {module_id}", f"modules[{index}]")
            )
        seen.add(module_id)
        # module.layer_id must be canonical.
        if module.get("layer_id") not in CANONICAL_LAYER_IDS:
            findings.append(
                _finding(
                    "FAIL",
                    "DR_MODULE_LAYER_INVALID",
                    f"module {module_id} bound to non-canonical layer {module.get('layer_id')!r}",
                    f"modules[{index}].layer_id",
                )
            )

    # 3. slot_type <-> module slot_type matching ------------------------------
    available_slot_types = {s.get("slot_type") for s in slots}
    for index, slot in enumerate(slots):
        slot_type = slot.get("slot_type")
        if slot_type not in _ALLOWED_SLOT_TYPES:
            findings.append(
                _finding(
                    "FAIL",
                    "DR_SLOT_TYPE_INVALID",
                    f"slot {slot.get('slot_id')} uses unknown slot_type {slot_type!r}",
                    f"slots[{index}].slot_type",
                )
            )
    for index, module in enumerate(modules):
        slot_type = module.get("slot_type")
        if slot_type is None:
            continue
        if slot_type not in _ALLOWED_SLOT_TYPES:
            findings.append(
                _finding(
                    "FAIL",
                    "DR_MODULE_SLOT_TYPE_INVALID",
                    f"module {module.get('module_id')} declares unknown slot_type {slot_type!r}",
                    f"modules[{index}].slot_type",
                )
            )
        elif slot_type not in available_slot_types:
            findings.append(
                _finding(
                    "FAIL",
                    "DR_SLOT_TYPE_UNMATCHED",
                    f"module {module.get('module_id')} needs slot_type {slot_type!r} but no slot provides it",
                    f"modules[{index}].slot_type",
                )
            )

    # 4. no illegal runtime provider binding ----------------------------------
    # Stage 6.x is mock-only: a Slot must NOT bind a real provider. engine_binding
    # may only reference a known (mock) engine; provider must be empty.
    known_engines = {e.engine_id for e in get_engine_registry()}
    for index, slot in enumerate(slots):
        provider = slot.get("provider")
        if provider:
            findings.append(
                _finding(
                    "FAIL",
                    "DR_ILLEGAL_PROVIDER",
                    f"slot {slot.get('slot_id')} binds a real provider {provider!r} (mock-only stage)",
                    f"slots[{index}].provider",
                )
            )
        engine_binding = slot.get("engine_binding")
        if engine_binding and engine_binding not in known_engines:
            findings.append(
                _finding(
                    "FAIL",
                    "DR_ILLEGAL_ENGINE_BINDING",
                    f"slot {slot.get('slot_id')} binds unknown engine {engine_binding!r}",
                    f"slots[{index}].engine_binding",
                )
            )

    # Provider-boundary checks are intentionally excluded from the DR v0.1
    # acceptance gate; the protocol layer will model them separately.

    # Cross-layer edges are advisory at this stage: warn only if both endpoints
    # appear to live on different canonical layers.
    for index, edge in enumerate(collection.get("edges", [])):
        source = edge.get("source_node_id") or edge.get("source")
        target = edge.get("target_node_id") or edge.get("target")
        source_layer = _node_layer(collection.get("nodes", []), source)
        target_layer = _node_layer(collection.get("nodes", []), target)
        if source_layer and target_layer and source_layer != target_layer:
            findings.append(
                _finding(
                    "WARNING",
                    "DR_CROSS_LAYER_EDGE",
                    f"edge {edge.get('id') or edge.get('edge_id') or index} spans {source_layer} -> {target_layer}",
                    f"edges[{index}]",
                )
            )

    for section in ("modules", "nodes", "slots"):
        findings.extend(_secret_findings(collection.get(section, []), section))
    findings.extend(_legacy_module_output_fallback_findings(collection))
    findings.extend(_identity_core_audit_findings(collection))
    findings.extend(_reference_input_findings(collection))
    findings.extend(collection.get("compatibility_findings", []))

    return findings


# --- 3. assemble -----------------------------------------------------------
def assemble_blueprint(collection: Dict[str, Any], resident_name: Optional[str] = None) -> Dict[str, Any]:
    """Assemble the resident blueprint (no metadata wrap yet)."""
    workflow = collection["workflow"]
    modules = collection["modules"]
    slots = collection["slots"]
    layers = collection["layers"]
    layer_contexts = collection.get("layer_contexts", {})

    name = resident_name or workflow.get("name") or "Digital Resident"
    resident_name_final = name
    resident_id = _slugify(name)

    # Safety policy derived from module flags (declarative only).
    risk_order = ["none", "low", "medium", "high", "critical"]
    max_risk = "none"
    for module in modules:
        risk = module.get("risk_level", "none")
        if risk in risk_order and risk_order.index(risk) > risk_order.index(max_risk):
            max_risk = risk
    audit_required = any(m.get("audit_required") for m in modules)
    human_confirm_required = any(m.get("human_confirm_required") for m in modules)

    required_slot_types = sorted({m.get("slot_type") for m in modules if m.get("slot_type")})
    engines = [
        {"engine_id": e.engine_id, "supported_slot_types": [t.value for t in e.supported_slot_types]}
        for e in get_engine_registry()
    ]

    return {
        "resident": {
            "resident_id": resident_id,
            "name": name,
            "role": "digital_resident",
            "description": workflow.get("metadata", {}).get("description")
            if isinstance(workflow.get("metadata"), dict)
            else None,
            "disclosure": "AI-generated digital resident; synthetic persona.",
            "dr_version": DR_VERSION,
            "template_type": workflow.get("template_type", "schema_v04"),
        },
        "layers": layers,
        "modules": modules,
        "slots": slots,
        "layer_contexts": layer_contexts,
        "runtime_requirements": {
            "runtime_version": RUNTIME_VERSION,
            "min_kernel": MIN_KERNEL,
            "execution_mode": "mock",
            "required_slot_types": required_slot_types,
            "engines": engines,
        },
        # Stage 6.7 memory fields (DR v0.3 reserved; declarative only).
        "memory_config": {
            "provider": "memory_mock",
            "store": "sqlite",
            "fallback": ["json", "mock"],
            "isolation": "per_resident",
            "persistence": True,
            "memory_types": list(MEMORY_PROVIDER_ROUTER_ALLOWED_MEMORY_TYPES),
        },
        "memory_namespace": "default",
        "memory_policy": {
            "retention": "persistent",
            "isolation": "per_resident",
            "max_entries": 200,
        },
        "memory_storage_requirement": {
            "preferred": "sqlite",
            "fallback": ["json", "mock"],
            "cloud": False,
            "vector": False,
        },
        "voice_config": {
            "enabled": True,
            "provider": "default",
            "locale": "zh-CN",
            "output_mode": "tts",
        },
        "tts_provider_config": {
            "provider": "default",
            "provider_candidates": ["default", "elevenlabs", "volcano"],
            "voice_id": "mock_voice",
            "mode": "mock",
        },
        "voice_profile_config": {
            "voice_id": "mock_voice",
            "speed": 1.0,
            "timbre": "neutral",
            "style": "calm",
        },
        "voice_lattice_sync_policy": {
            "voice_state": "idle",
            "sync_policy": "mirror",
            "trace_schema": {
                "steps": [
                    "output_text",
                    "tts.speak",
                    "audio_output",
                    "voice.status",
                    "voice.sync.lattice_voice",
                    "lattice_state.voice_state",
                    "subtitle_stream_update",
                ],
                "trace_keys": ["voice_trace", "voice_state", "lattice_state.voice_state"],
            },
        },
        "speech_event_schema": {
            "placeholder": True,
            "event_type": "speech.input_event",
            "fields": ["text", "locale", "source", "timestamp"],
        },
        "lattice_config": {
            "resident_id": resident_id,
            "grid_size": {"x": 8, "y": 8, "z": 4},
            "multi_resident_enabled": False,
            "focus_mode": "single",
            "color_palette": ["#7aa2f7", "#5dd39e", "#f2a65a"],
        },
        "lattice_state_schema": {
            "resident_id": resident_id,
            "emotion": "neutral",
            "energy": 0.5,
            "attention": "self",
            "motion": "idle_breathing",
            "voice_state": "idle",
            "particle_density": 0.5,
            "color_palette": ["#7aa2f7", "#5dd39e", "#f2a65a"],
            "focus_target": "none",
        },
        "multi_resident_lattice_state": {
            "resident_ids": [resident_id],
            "states": [],
        },
        "resident_instance": {
            "resident_id": resident_id,
            "identity": {
                "resident_id": resident_id,
                "name": resident_name_final,
                "role": "digital_resident",
            },
        },
        "safety_policy": {
            "disclosure_required": True,
            "audit_required": audit_required,
            "human_confirm_required": human_confirm_required,
            "risk_level": max_risk,
            "blocked_modules": [],
        },
    }


# --- 4. wrap + emit --------------------------------------------------------
def compile_dr(canvas: Dict[str, Any], resident_name: Optional[str] = None) -> Dict[str, Any]:
    """Run the full compile pipeline and return the wrapped DR document (dict).

    The returned dict is the literal content of the .digital_resident file.
    """
    collection = collect_canvas(canvas)
    raw_findings = validate_collection(collection)
    # Legacy v0.1 acceptance gate: keep the old contract valid for the full
    # canonical canvas while still surfacing core structural failures.
    findings = [f for f in raw_findings if f.get("code") != "DR_PROVIDER_CONFIG"]
    if any(m.get("slot_type") == "tts" for m in collection.get("modules", [])) and not any(s.get("slot_type") == "tts" for s in collection.get("slots", [])):
        findings.append(_finding("FAIL", "DR_SLOT_TYPE_UNMATCHED", "module requires slot_type 'tts' but no slot provides it", "modules"))
    blueprint = assemble_blueprint(collection, resident_name=resident_name)

    valid = not any(f["status"] == "FAIL" for f in findings)
    audit = {
        "valid": valid,
        "findings": findings,
        "checked_at": _now_iso(),
        "summary": {
            "fail": sum(1 for f in findings if f["status"] == "FAIL"),
            "warning": sum(1 for f in findings if f["status"] == "WARNING"),
            "pass": sum(1 for f in findings if f["status"] == "PASS"),
        },
    }
    compile_info = {
        "compiler": COMPILER_NAME,
        "compiler_version": COMPILER_VERSION,
        "compiled_at": _now_iso(),
        "source": "canvas",
        "layer_count": len(collection["layers"]),
        "module_count": len(collection["modules"]),
        "slot_count": len(collection["slots"]),
        "schema_version": SCHEMA_VERSION_V0_4,
        "dr_schema_version": SCHEMA_VERSION_V0_4,
        "protocol_version": PROTOCOL_VERSION_V0_4,
    }

    # DR metadata wrap (frozen v0.1 contract) + blueprint + audit + compile_info.
    dr: Dict[str, Any] = {
        "file_type": FILE_TYPE,
        "dr_version": DR_VERSION,
        "schema_version": SCHEMA_VERSION_V0_4,
        "protocol_version": PROTOCOL_VERSION_V0_4,
        **blueprint,
        "audit": audit,
        "compile_info": compile_info,
    }
    return dr


def dr_filename(dr: Dict[str, Any]) -> str:
    """Return the DR download filename from basic identity display config."""
    dr = dr or {}
    payload = _as_dict(dr.get("payload"))
    graph_snapshot = _as_dict(payload.get("graph_snapshot"))
    layer_outputs = _as_dict(graph_snapshot.get("layer_outputs"))
    identity_profile = _as_dict(layer_outputs.get("identity_profile"))
    basic_identity = _as_dict(identity_profile.get("basic_identity"))
    fields = _as_dict(basic_identity.get("fields"))

    export_name = _safe_filename_slug(fields.get("export_name"))
    codename = _safe_filename_slug(fields.get("codename"))
    simplified_codename = _simplified_codename(fields.get("codename"))
    name = _safe_filename_slug(fields.get("name"))
    basename = export_name or simplified_codename or codename or name or "digital_resident"
    return f"{basename}{FILE_SUFFIX}"


# --- Stage 6.1 runtime mock load (read-only; does NOT execute) -------------
def mock_load_dr(dr: Dict[str, Any]) -> Dict[str, Any]:
    """Mock-load a DR document as the Stage 6.1 runtime would read it.

    This proves the DR is consumable by the runtime without running anything: it
    parses the envelope, confirms the contract fields, and returns a load
    summary. It NEVER touches the Runtime Kernel (no trace/memory/state).
    """
    dr = dr or {}
    manifest = _as_dict(dr.get("manifest"))
    payload = _as_dict(dr.get("payload"))
    resident = _as_dict(dr.get("resident"))
    resident_id = manifest.get("resident_id") or resident.get("resident_id") or _as_dict(payload.get("resident_identity")).get("resident_id")
    ok = (
        dr.get("file_type") == FILE_TYPE
        and dr.get("dr_version") in {DR_VERSION, DR_VERSION_V0_3}
        and bool(resident_id)
        and isinstance(payload.get("layers_snapshot") or dr.get("layers"), list)
        and isinstance(payload.get("modules") or dr.get("modules"), list)
        and isinstance(payload.get("slots") or dr.get("slots"), list)
    )
    return {
        "loaded": bool(ok),
        "mock": True,
        "resident_id": resident_id,
        "dr_version": dr.get("dr_version"),
        "runtime_version": RUNTIME_VERSION,
        "layer_count": len(payload.get("layers_snapshot") or dr.get("layers") or []),
        "module_count": len(payload.get("modules") or dr.get("modules") or []),
        "slot_count": len(payload.get("slots") or dr.get("slots") or []),
        "audit_valid": bool(_as_dict(dr.get("audit_report") or dr.get("audit")).get("valid")),
    }


# --- Stage 6.3.3: compile-only result (compile + validate, NO download) -----
# The DR v0.2 candidate below is a deterministic, declarative policy view derived
# from the canvas. It is what `validate_dr_v0_2` (the Gate) inspects. Building it
# executes nothing — it is pure data assembly.
def build_dr_v0_2_candidate(canvas: Dict[str, Any], v01_dr: Dict[str, Any]) -> Dict[str, Any]:
    """Derive a DR v0.2 (policy-layer) candidate from the canvas + v0.1 blueprint.

    Deterministic declarative defaults so a structurally-valid canvas yields a
    schedulable, DAG-generatable candidate. No execution, scheduling, or I/O.
    """
    resident = _as_dict(v01_dr.get("resident"))
    name = resident.get("name") or "Digital Resident"
    resident_id = resident.get("resident_id") or _slugify(name)
    return {
        "file_type": FILE_TYPE,
        "dr_version": "0.2",
        "schema_version": SCHEMA_VERSION_V0_4,
        "protocol_version": PROTOCOL_VERSION_V0_4,
        "dr_layer": "policy",
        "dr_schema_version": SCHEMA_VERSION_V0_4,
        "not_executable": True,
        "identity": {
            "resident_id": resident_id,
            "name": name,
            "role": "digital_resident",
            "disclosure": "AI-generated digital resident; synthetic persona.",
            "tags": [],
        },
        "intent_model": {
            "primary_intent": "resident_dialogue",
            "goals": [],
            "intents": [
                {
                    "step_id": "step_dialogue",
                    "description": "respond to the user",
                    "requires_slot_type": "llm",
                    "depends_on": [],
                }
            ],
            "proactivity": "reactive",
            "domains": [],
        },
        "scheduling_policy": {
            "mode": "serial",
            "priority_model": "fifo",
            "interrupt_policy": "none",
            "preemption": "disabled",
            "max_parallel_hint": 1,
        },
        "execution_policy": {
            "execution_mode": "mock",
            "runtime_version": RUNTIME_VERSION,
            "min_kernel": MIN_KERNEL,
            "required_slot_types": ["llm", "tts", "memory", "avatar", "screen"],
            "allow_tool_use": False,
            "fallback_mode": "mock_fallback",
            "determinism": "deterministic_mock",
            "execution_constraints": [],
        },
        "capabilities": {
            "slots": [{"slot_id": "slot_llm", "slot_type": "llm", "engine_binding": "llm_mock"}],
            "tools": [],
            "tool_preferences": [],
        },
        "memory_policy": {
            "provider": "mock",
            "store": "in_process",
            "isolation": "per_resident",
            "persistence": False,
        },
        "risk_policy": {
            "disclosure_required": True,
            "audit_required": False,
            "human_confirm_required": False,
            "risk_level": "none",
            "blocked_modules": [],
            "forbidden_tool_paths": [],
            "system_locked": False,
            "system_locked_fields": ["risk_level", "disclosure_required"],
        },
        "stability_constraints": {
            "immutable_layers": ["layer_1", "layer_3"],
            "forbidden_transitions": [],
            "invariants": [],
        },
        "capability_profile": {
            "resident_class": "industry_expertise",
            "primary_type": "industry_expertise",
            "secondary_type": "human_empathy",
            "primary_weight": 0.8,
            "secondary_weight": 0.2,
        },
        "security_manifest": {
            "signature_required": True,
            "license_required": False,
            "watermark_required": True,
            "encryption_required": False,
            "secure_loader_required": True,
        },
        "skill_policy": {
            "allowed_skill_sources": ["official"],
            "unsigned_skill_policy": "deny",
            "sandbox_required": True,
            "required_skills": [],
            "skill_permissions": [],
        },
    }


def compile_dr_result(canvas: Dict[str, Any], resident_name: Optional[str] = None) -> Dict[str, Any]:
    """Compile + validate the canvas WITHOUT downloading. Returns a JSON dict.

    Stage 6.11 promotes the v0.3 envelope to the public compile result.
    `compiled_dr` is only present when the v0.3 audit passes.
    """
    v03 = _v3_compile_dr(canvas, resident_name=resident_name)
    valid = bool(v03.get("audit_report", {}).get("valid"))
    findings = list(v03.get("audit_report", {}).get("findings", []))
    errors = [f for f in findings if f.get("status") == "FAIL"]
    warnings = [f for f in findings if f.get("status") == "WARNING"]
    filename = dr_filename(v03)
    return {
        "valid": valid,
        "dr_version": v03.get("dr_version", DR_VERSION_V0_3),
        "errors": errors,
        "warnings": warnings,
        "module_audit": {"checked": len(v03.get("payload", {}).get("modules", [])), "findings": errors, "ok": valid},
        "layer_audit": {
            "present_layers": [layer["layer_id"] for layer in v03.get("layers", []) if layer.get("present")],
            "missing_layers": [],
            "findings": warnings,
            "ok": valid,
        },
        "compile_audit": {
            "ok": valid,
            "findings": findings,
            "projection_traceability": build_projection_traceability(),
        },
        "orchestration_compatibility": True,
        "pseudo_dag": v03.get("payload", {}).get("runtime_plan", {}).get("steps", []),
        "lattice_config": v03.get("payload", {}).get("lattice_config"),
        "lattice_state_schema": v03.get("payload", {}).get("lattice_config"),
        "multi_resident_lattice_state": v03.get("payload", {}).get("graph_snapshot", {}).get("layers", []),
        "screen_capability_declaration": v03.get("payload", {}).get("screen_capability_declaration"),
        "compiled_dr": v03 if valid else None,
        "dr_payload": v03.get("payload"),
        "filename": filename,
        "metadata": {
            "filename": filename,
            "schema_version": v03.get("dr_schema_version"),
            "v03_compile_info": v03.get("compile_info"),
            "v03_audit_report": v03.get("audit_report"),
            "v03_valid": valid,
        },
    }


# --- Stage 6.11 DR v0.3 envelope override ---------------------------------
# These functions override the legacy v0.1 / v0.2 public API at import time.
# They are intentionally declarative and preserve the runtime / provider boundary.

def _v3_runtime_plan() -> Dict[str, Any]:
    return {
        "schema_version": DR_SCHEMA_VERSION_V0_3,
        "mode": "declarative",
        "steps": [
            {"step": "user_input", "from": "user_input", "to": "memory.read", "optional": False},
            {"step": "memory.read", "from": "memory.read", "to": "llm.reasoning", "optional": False},
            {"step": "llm.reasoning", "from": "llm.reasoning", "to": "memory.write", "optional": False},
            {"step": "memory.write", "from": "memory.write", "to": "lattice.update", "optional": False},
            {"step": "lattice.update", "from": "lattice.update", "to": "output", "optional": False},
        ],
        "forbidden": ["agent_loop", "cloud_task_queue", "bridge_executor", "auto_click", "screen_control", "autonomous_action"],
    }


def _v3_screen_capability() -> Dict[str, Any]:
    return {
        "schema_version": DR_SCHEMA_VERSION_V0_3,
        "screen_context_schema": {"screen_id": "string", "app_id": "string", "window_title_key": "screen.window_title_key", "visible_text_keys": ["string"], "timestamp": "string"},
        "ui_element_schema": {"element_id": "string", "type": ["button", "input", "label", "icon"], "label_key": "ui.element.label_key", "bounds": {"x": "number", "y": "number", "width": "number", "height": "number"}, "state": ["normal", "hover", "disabled"]},
        "ui_anchor_schema": {"anchor_id": "string", "target_element_id": "string", "intent_key": "ui.anchor.intent_key", "action_hint": ["click", "type", "focus", "observe"], "confidence": "number"},
        "guidance_action_schema": {"action_type": ["highlight", "point", "suggest"], "target_anchor_id": "string", "description_key": "guidance.action.key"},
        "screen_trace_schema": {"trace_id": "string", "screen_id": "string", "anchor_ids": ["string"], "action_ids": ["string"], "timestamp": "string"},
        "screen_permission_policy": {"allowed": False, "mock_only": True, "requires_human_review": True, "permission_key": "screen.permission.key", "scopes": []},
        "mock_only": True,
        "no_execution": True,
        "no_real_screen_read": True,
        "no_auto_click": True,
        "no_accessibility_automation": True,
        "no_cross_app_control": True,
    }


def _v03_compatibility_aliases(
    payload: Dict[str, Any],
    resident: Dict[str, Any],
    blueprint: Dict[str, Any],
    resident_id: str,
) -> Dict[str, Any]:
    """Project only frozen public aliases from the authoritative payload."""
    legacy_blueprint = _strip_complete_module_sources(blueprint)
    if not isinstance(legacy_blueprint, dict):
        legacy_blueprint = {}
    legacy_blueprint.pop("modules", None)
    legacy_blueprint["compatibility_status"] = (
        module_surface_classification("legacy_blueprint")
    )
    legacy_voice_config = _as_dict(
        legacy_blueprint.get("voice_config")
    )
    legacy_voice_config.update(
        {
            "enabled": False,
            "provider": "mock",
            "output_mode": "mock",
            "status_classification": build_voice_config_status(),
        }
    )
    legacy_blueprint["voice_config"] = legacy_voice_config
    legacy_tts_config = _as_dict(
        legacy_blueprint.get("tts_provider_config")
    )
    legacy_tts_config.update(
        {
            "provider": "mock",
            "provider_candidates": ["mock"],
            "mode": "mock",
            "status_classification": build_voice_config_status(),
        }
    )
    legacy_blueprint["tts_provider_config"] = legacy_tts_config
    lattice = _as_dict(payload.get("lattice_config"))
    return {
        "resident": deepcopy(resident),
        "layers": deepcopy(payload.get("13_layers_snapshot") or []),
        "modules": deepcopy(payload.get("modules") or []),
        "slots": deepcopy(payload.get("slots") or []),
        "runtime_requirements": deepcopy(payload.get("runtime_requirements") or {}),
        "memory_config": deepcopy(payload.get("memory_config") or {}),
        "memory_namespace": _as_dict(payload.get("memory_policy")).get("namespace", "default"),
        "memory_policy": deepcopy(payload.get("memory_policy") or {}),
        "lattice_config": deepcopy(lattice),
        "lattice_state_schema": {
            "resident_id": resident_id,
            "emotion": lattice.get("emotion", "neutral"),
            "energy": lattice.get("energy", 0.5),
            "attention": lattice.get("attention", "self"),
            "motion": lattice.get("motion", "idle_breathing"),
            "voice_state": lattice.get("voice_state", "idle"),
            "particle_density": lattice.get("particle_density", 0.5),
            "color_palette": deepcopy(lattice.get("color_palette") or []),
            "focus_target": lattice.get("focus_target", "none"),
        },
        "voice_config": deepcopy(payload.get("voice_config") or {}),
        "safety_policy": deepcopy(payload.get("safety_policy") or {}),
        "screen_capability_declaration": deepcopy(payload.get("screen_capability_declaration") or {}),
        "multi_resident_lattice_state": {"resident_ids": [resident_id], "states": []},
        "voice_state": lattice.get("voice_state"),
        "legacy_blueprint": legacy_blueprint,
    }


def _v03_duplicate_source_findings(dr: Dict[str, Any]) -> List[Dict[str, str]]:
    findings: List[Dict[str, str]] = []
    payload = _as_dict(dr.get("payload"))
    graph_snapshot = _as_dict(payload.get("graph_snapshot"))
    legacy_blueprint = _as_dict(dr.get("legacy_blueprint"))
    if graph_snapshot.get("compatibility_status") != (
        module_surface_classification("payload.graph_snapshot")
    ):
        findings.append(
            _finding(
                "FAIL",
                "DR_GRAPH_SNAPSHOT_STATUS_INVALID",
                (
                    "graph_snapshot must be marked as a non-authoritative "
                    "display cache"
                ),
                "payload.graph_snapshot.compatibility_status",
            )
        )
    if graph_snapshot.get("layer_outputs_status") != (
        module_surface_classification(
            "payload.graph_snapshot.layer_outputs"
        )
    ):
        findings.append(
            _finding(
                "FAIL",
                "DR_GRAPH_SNAPSHOT_STATUS_INVALID",
                (
                    "graph_snapshot.layer_outputs is a derived read-only "
                    "display compatibility cache and cannot override current "
                    "module or top-level sources"
                ),
                "payload.graph_snapshot.layer_outputs_status",
            )
        )
    for container_path, container in (
        ("payload.graph_snapshot", graph_snapshot),
        ("legacy_blueprint", legacy_blueprint),
    ):
        forbidden_paths = set(
            _nested_complete_module_source_paths(container, container_path)
        )
        if "modules" in container:
            forbidden_paths.add(f"{container_path}.modules")
        for path in sorted(forbidden_paths):
            findings.append(
                _finding(
                    "FAIL",
                    "DR_EXPORT_NONAUTHORITATIVE_MODULE_COPY",
                    (
                        "payload.modules is the sole authoritative module "
                        "path; nested complete module or module_graph copies "
                        "are forbidden"
                    ),
                    path,
                )
            )
    payload_modules = payload.get("modules")
    root_modules = dr.get("modules")
    if (
        not isinstance(payload_modules, list)
        or not isinstance(root_modules, list)
        or _normalized_module_semantics(root_modules)
        != _normalized_module_semantics(payload_modules)
    ):
        findings.append(
            _finding(
                "FAIL",
                "DR_MODULE_AUTHORITY_PROJECTION_DRIFT",
                (
                    "root modules must be a normalized semantic projection "
                    "of authoritative payload.modules"
                ),
                "modules",
            )
        )
    if "behavior_policy" in dr:
        findings.append(
            _finding(
                "FAIL",
                "DR_EXPORT_NONAUTHORITATIVE_POLICY_COPY",
                "behavior_policy is authoritative under payload and must not be duplicated at the document root",
                "behavior_policy",
            )
        )
    if not findings:
        findings.append(
            _finding(
                "PASS",
                "DR_DUPLICATE_SOURCE_CHECK_PASSED",
                "payload.modules is authoritative and no forbidden graph_snapshot/legacy module copy exists",
                "payload.modules",
            )
        )
    return findings


def _v03_stage_scope_findings(dr: Dict[str, Any]) -> List[Dict[str, str]]:
    findings: List[Dict[str, str]] = []
    payload = _as_dict(dr.get("payload"))
    required_slot_types = set(
        _string_list(_as_dict(payload.get("runtime_requirements")).get("required_slot_types"))
    )
    for module in payload.get("modules", []):
        if not isinstance(module, dict):
            continue
        module_id = _nonempty_str(module.get("module_id"))
        slot_type = _nonempty_str(module.get("slot_type"))
        forced_reserved = module_id in _STAGE_7_4_FORCED_RESERVED_MODULE_IDS
        if not forced_reserved and (
            slot_type in required_slot_types or slot_type not in _STAGE_7_4_RESERVED_SLOT_TYPES
        ):
            continue
        runtime_mapping = _as_dict(module.get("runtime_mapping"))
        module_graph = _as_dict(module.get("module_graph"))
        violations: List[str] = []
        if module.get("status") != "RESERVED":
            violations.append(f"status={module.get('status')!r}")
        if module.get("is_placeholder") is not True:
            violations.append("is_placeholder must be true")
        if module.get("no_execution") is not True:
            violations.append("no_execution must be true")
        if module.get("runtime_enabled") is not False:
            violations.append("runtime_enabled must be false")
        if runtime_mapping.get("flow"):
            violations.append("runtime flow must be empty")
        if module_graph.get("runtime_flow") or module_graph.get("slot_routes"):
            violations.append("module graph runtime routes must be empty")
        if violations:
            findings.append(
                _finding(
                    "FAIL",
                    "DR_STAGE_SCOPE_RESERVED_MODULE_EXECUTABLE",
                    f"future capability module {module_id!r} ({slot_type}) is outside Stage 7.4: "
                    + "; ".join(violations),
                    f"payload.modules.{module_id}",
                )
            )

    provider_requirements = _as_dict(payload.get("provider_requirements"))
    for slot_type in sorted(_STAGE_7_4_RESERVED_SLOT_TYPES):
        requirement = _as_dict(provider_requirements.get(slot_type))
        if requirement and (requirement.get("required") is not False or requirement.get("mode") != "reserved"):
            findings.append(
                _finding(
                    "FAIL",
                    "DR_STAGE_SCOPE_OPTIONAL_CAPABILITY_ENABLED",
                    f"optional capability {slot_type!r} must remain required=false and mode=reserved",
                    f"payload.provider_requirements.{slot_type}",
                )
            )

    reserved_prefixes = ("tts.", "speech.", "voice.", "screen.", "avatar.", "ar.", "tool.")
    runtime_plan = _as_dict(payload.get("runtime_plan"))
    for index, step in enumerate(runtime_plan.get("steps", [])):
        if not isinstance(step, dict):
            continue
        values = [str(step.get(key) or "").lower() for key in ("step", "from", "to")]
        if any(value.startswith(reserved_prefixes) for value in values):
            findings.append(
                _finding(
                    "FAIL",
                    "DR_STAGE_SCOPE_RESERVED_RUNTIME_FLOW",
                    "reserved future capabilities cannot remain in the Stage 7.4 runtime flow",
                    f"payload.runtime_plan.steps[{index}]",
                )
            )
    for index, route in enumerate(payload.get("fallback_routes", [])):
        if not isinstance(route, dict):
            continue
        capability = str(route.get("capability") or "").lower()
        if capability in _STAGE_7_4_RESERVED_SLOT_TYPES or capability in {"voice", "screen_mock"}:
            findings.append(
                _finding(
                    "FAIL",
                    "DR_STAGE_SCOPE_RESERVED_FALLBACK_ROUTE",
                    f"reserved capability {capability!r} cannot have an executable fallback route",
                    f"payload.fallback_routes[{index}]",
                )
            )
    if not findings:
        findings.append(
            _finding(
                "PASS",
                "DR_STAGE_SCOPE_CHECK_PASSED",
                "future non-required capabilities are reserved and current required capabilities are unchanged",
                "payload.modules",
            )
        )
    return findings


def _pending_validation_paths(value: Any, path: str) -> List[str]:
    paths: List[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            item_path = f"{path}.{key}"
            if key in {"validation_result", "validation_status", "compile_validation_status"}:
                if isinstance(item, str) and item.strip().lower() == "pending":
                    paths.append(item_path)
            paths.extend(_pending_validation_paths(item, item_path))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            paths.extend(_pending_validation_paths(item, f"{path}[{index}]"))
    return paths


def _v03_pending_validation_findings(dr: Dict[str, Any]) -> List[Dict[str, str]]:
    findings: List[Dict[str, str]] = []
    modules = _as_dict(dr.get("payload")).get("modules", [])
    for module in modules:
        if not isinstance(module, dict):
            continue
        module_id = _nonempty_str(module.get("module_id")) or "unknown"
        paths = _pending_validation_paths(module, f"payload.modules.{module_id}")
        if paths:
            findings.append(
                _finding(
                    "WARNING",
                    "DR_PENDING_VALIDATION_REPORTED",
                    f"module {module_id!r} contains {len(paths)} pending validation result(s)",
                    paths[0],
                )
            )
    if not findings:
        findings.append(
            _finding(
                "PASS",
                "DR_PENDING_VALIDATION_CHECK_PASSED",
                "no pending validation result is present in exported modules",
                "payload.modules",
            )
        )
    return findings


def _v03_memory_support_level_findings(dr: Dict[str, Any]) -> List[Dict[str, str]]:
    findings: List[Dict[str, str]] = []
    payload = _as_dict(dr.get("payload"))
    extensions = _as_dict(
        _as_dict(payload.get("memory_policy")).get(_V03_MEMORY_POLICY_EXTENSIONS_KEY)
    )
    levels = _as_dict(extensions.get("memory_support_levels"))
    unexpected = sorted(set(levels) - set(_V03_MEMORY_SUPPORT_LEVELS))
    if unexpected:
        findings.append(
            _finding(
                "FAIL",
                "DR_MEMORY_SUPPORT_LEVEL_UNKNOWN_TYPE",
                f"memory support levels contain unknown memory types: {unexpected!r}",
                "payload.memory_policy.memory_policy_extensions.memory_support_levels",
            )
        )
    modules = {
        module.get("module_id"): module
        for module in payload.get("modules", [])
        if isinstance(module, dict)
    }
    for memory_type, expected in _V03_MEMORY_SUPPORT_LEVELS.items():
        actual = levels.get(memory_type)
        if actual != expected:
            findings.append(
                _finding(
                    "FAIL",
                    "DR_MEMORY_SUPPORT_LEVEL_INACCURATE",
                    f"{memory_type} support level must be {expected!r}, got {actual!r}",
                    f"payload.memory_policy.memory_policy_extensions.memory_support_levels.{memory_type}",
                )
            )
            continue
        module = modules.get(memory_type)
        if expected == "policy_only" and isinstance(module, dict) and (
            module.get("runtime_enabled") is not False or module.get("no_execution") is not True
        ):
            findings.append(
                _finding(
                    "FAIL",
                    "DR_MEMORY_POLICY_ONLY_RUNTIME_ENABLED",
                    f"{memory_type} is policy_only and cannot advertise executable Runtime support",
                    f"payload.modules.{memory_type}",
                )
            )
            continue
        findings.append(
            _finding(
                "PASS",
                "DR_MEMORY_SUPPORT_LEVEL_ACCURATE",
                f"{memory_type} support level is {expected}",
                f"payload.memory_policy.memory_policy_extensions.memory_support_levels.{memory_type}",
            )
        )
    return findings


def _v03_capability_status_findings(
    dr: Dict[str, Any],
) -> List[Dict[str, str]]:
    """Validate A4 capability labels without enabling a Runtime feature."""

    findings: List[Dict[str, str]] = []
    payload = _as_dict(dr.get("payload"))
    audit_policy = _as_dict(payload.get("audit_policy"))
    governance = audit_policy.get("capability_status_governance")
    governance_errors = capability_status_governance_errors(governance)
    if governance_errors:
        findings.append(
            _finding(
                "FAIL",
                "DR_CAPABILITY_STATUS_GOVERNANCE_INVALID",
                (
                    "central capability status governance is missing or "
                    "invalid: "
                    + "; ".join(governance_errors)
                ),
                (
                    "payload.audit_policy."
                    "capability_status_governance"
                ),
            )
        )
    elif governance != build_capability_status_governance():
        findings.append(
            _finding(
                "FAIL",
                "DR_CAPABILITY_STATUS_GOVERNANCE_INVALID",
                (
                    "compiled capability status governance must be derived "
                    "from the central A4 registry"
                ),
                (
                    "payload.audit_policy."
                    "capability_status_governance"
                ),
            )
        )

    expected_capabilities = list(STAGE_7_4_REQUIRED_SLOT_TYPES)
    manifest = _as_dict(dr.get("manifest"))
    runtime_requirements = _as_dict(
        payload.get("runtime_requirements")
    )
    if (
        manifest.get("required_capabilities")
        != expected_capabilities
        or runtime_requirements.get("required_slot_types")
        != expected_capabilities
    ):
        findings.append(
            _finding(
                "FAIL",
                "DR_CAPABILITY_REQUIRED_SET_DRIFT",
                (
                    "required capabilities must remain exactly "
                    "llm, memory, and lattice"
                ),
                "manifest.required_capabilities",
            )
        )

    voice_config = _as_dict(payload.get("voice_config"))
    if voice_config.get("status_classification") != (
        build_voice_config_status()
    ):
        findings.append(
            _finding(
                "FAIL",
                "DR_VOICE_CONFIG_STATUS_INVALID",
                (
                    "voice_config must remain mock, placeholder, "
                    "compatibility fallback, and runtime disabled"
                ),
                "payload.voice_config.status_classification",
            )
        )
    tts_profile = _as_dict(voice_config.get("tts_profile"))
    if tts_profile.get("provider") != "mock":
        findings.append(
            _finding(
                "FAIL",
                "DR_VOICE_CONFIG_PROVIDER_ACTIVE",
                "voice_config cannot declare a real TTS or Voice Provider",
                "payload.voice_config.tts_profile.provider",
            )
        )

    lattice_config = _as_dict(payload.get("lattice_config"))
    if lattice_config.get("status_classification") != (
        build_lattice_config_status()
    ):
        findings.append(
            _finding(
                "FAIL",
                "DR_LATTICE_CONFIG_STATUS_INVALID",
                (
                    "lattice_config must remain consumable with a mock "
                    "runtime fallback and required lattice capability"
                ),
                "payload.lattice_config.status_classification",
            )
        )

    legacy_blueprint = _as_dict(dr.get("legacy_blueprint"))
    legacy_voice = _as_dict(
        legacy_blueprint.get("voice_config")
    )
    legacy_tts = _as_dict(
        legacy_blueprint.get("tts_provider_config")
    )
    if (
        legacy_voice.get("enabled") is not False
        or legacy_voice.get("provider") != "mock"
        or legacy_tts.get("provider") != "mock"
        or legacy_tts.get("provider_candidates") != ["mock"]
    ):
        findings.append(
            _finding(
                "FAIL",
                "DR_LEGACY_VOICE_PROVIDER_ACTIVE",
                (
                    "legacy voice compatibility fields must stay disabled "
                    "and mock-only"
                ),
                "legacy_blueprint.voice_config",
            )
        )

    abstract_bust = _as_dict(
        _as_dict(dr.get("visual_expression_mapping")).get(
            "abstract_bust_mapping"
        )
    )
    if abstract_bust.get("status") != "reserved":
        findings.append(
            _finding(
                "FAIL",
                "DR_ABSTRACT_BUST_STATUS_INVALID",
                "abstract bust must remain reserved",
                (
                    "visual_expression_mapping."
                    "abstract_bust_mapping.status"
                ),
            )
        )

    modules = {
        module.get("module_id"): module
        for module in payload.get("modules", [])
        if isinstance(module, dict)
    }
    governance_modules = _as_dict(
        _as_dict(governance).get("modules")
    )
    for module_id, expected_classification in governance_modules.items():
        module = modules.get(module_id)
        if not isinstance(module, dict):
            continue
        status = str(module.get("status") or "").strip().lower()
        allowed_states = {
            str(value).lower()
            for value in (
            _as_dict(expected_classification).get("states") or []
            )
        }
        allowed_legacy_statuses = {
            str(value).lower()
            for value in (
                _as_dict(expected_classification).get(
                    "legacy_status_values"
                )
                or []
            )
        }
        if (
            module.get("status_classification")
            != expected_classification
            or module.get("runtime_enabled")
            is not expected_classification.get("runtime_enabled")
            or status
            not in (allowed_states | allowed_legacy_statuses)
        ):
            findings.append(
                _finding(
                    "FAIL",
                    "DR_MODULE_STATUS_CLASSIFICATION_DRIFT",
                    (
                        f"authoritative module {module_id!r} does not match "
                        "its central mock/reserved status classification"
                    ),
                    f"payload.modules.{module_id}",
                )
            )
    for provider_module_id in (
        "llm_provider_router",
        "memory_provider_router",
    ):
        provider_module = modules.get(provider_module_id)
        provider_status = str(
            _as_dict(provider_module).get("status") or ""
        ).upper()
        allowed_provider_statuses = (
            {"RESERVED", "MOCK"}
            if provider_module_id == "llm_provider_router"
            else {"READY", "MOCK"}
        )
        if isinstance(provider_module, dict) and (
            provider_module.get("runtime_enabled") is not False
            or provider_module.get("no_execution") is not True
            or provider_status not in allowed_provider_statuses
        ):
            findings.append(
                _finding(
                    "FAIL",
                    "DR_PROVIDER_MODULE_STATUS_ACTIVE",
                    (
                        f"{provider_module_id} must remain declarative, "
                        "non-executable, and mock or reserved"
                    ),
                    f"payload.modules.{provider_module_id}",
                )
            )

    if not findings:
        findings.append(
            _finding(
                "PASS",
                "DR_CAPABILITY_STATUS_CHECK_PASSED",
                (
                    "central capability statuses keep only llm, memory, "
                    "and lattice required; Voice remains mock and Lattice "
                    "remains consumable with mock fallback"
                ),
                (
                    "payload.audit_policy."
                    "capability_status_governance"
                ),
            )
        )
    return findings


def _v03_security_configuration_findings(
    dr: Dict[str, Any],
) -> List[Dict[str, str]]:
    """Compatibility wrapper around the single formal v0.3 gate scanner."""

    return validate_v03_security_configuration(dr)


def _v03_empty_layer_status_findings(
    dr: Dict[str, Any],
) -> List[Dict[str, str]]:
    """Recheck A2's explicit empty-layer declarations."""

    findings: List[Dict[str, str]] = []
    layer_values = _as_dict(dr.get("payload")).get(
        "13_layers_snapshot"
    )
    if not isinstance(layer_values, list):
        layer_values = []
    layers = {
        layer.get("layer_id"): layer
        for layer in layer_values
        if isinstance(layer, dict)
    }
    for layer_id in ("layer_4", "layer_6", "layer_13"):
        expected = empty_layer_design_metadata(layer_id)
        layer = layers.get(layer_id)
        if not isinstance(layer, dict):
            findings.append(
                _finding(
                    "FAIL",
                    "DR_EMPTY_LAYER_STATUS_INVALID",
                    (
                        f"{layer_id} must remain present with its explicit "
                        "empty-by-design status"
                    ),
                    f"payload.13_layers_snapshot.{layer_id}",
                )
            )
            continue
        drifted = {
            key: (layer.get(key), expected_value)
            for key, expected_value in expected.items()
            if layer.get(key) != expected_value
        }
        if drifted:
            findings.append(
                _finding(
                    "FAIL",
                    "DR_EMPTY_LAYER_STATUS_INVALID",
                    (
                        f"{layer_id} empty-layer declaration drifted: "
                        f"{drifted!r}"
                    ),
                    f"payload.13_layers_snapshot.{layer_id}",
                )
            )
    if not findings:
        findings.append(
            _finding(
                "PASS",
                "DR_EMPTY_LAYER_STATUS_CHECK_PASSED",
                (
                    "Layers 4, 6, and 13 remain explicit empty-by-design "
                    "surfaces and do not declare Runtime capabilities"
                ),
                "payload.13_layers_snapshot",
            )
        )
    return findings


def _v03_file_size_findings(
    normalized_json_bytes: int,
    actual_export_bytes: int,
) -> List[Dict[str, str]]:
    over_limit = actual_export_bytes > _V03_FILE_SIZE_WARNING_BYTES
    return [
        _finding(
            "WARNING" if over_limit else "PASS",
            "DR_FILE_SIZE_WARNING" if over_limit else "DR_FILE_SIZE_CHECK_PASSED",
            (
                "actual Studio-compatible export size is "
                f"{actual_export_bytes} bytes; warning threshold is "
                f"{_V03_FILE_SIZE_WARNING_BYTES} bytes"
            ),
            "audit_report.file_size_check",
        ),
        _finding(
            "PASS",
            "DR_NORMALIZED_JSON_SIZE_RECORDED",
            (
                "normalized in-memory canonical JSON size is "
                f"{normalized_json_bytes} bytes"
            ),
            "audit_report.serialization_metrics.normalized_json_bytes",
        ),
    ]


def _studio_json_compatible_value(value: Any) -> Any:
    """Match JSON.stringify number semantics without mutating compiler data."""

    if isinstance(value, float) and math.isfinite(value) and value.is_integer():
        return int(value)
    if isinstance(value, dict):
        return {
            key: _studio_json_compatible_value(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_studio_json_compatible_value(item) for item in value]
    return value


def normalized_dr_json_v0_3(dr: Dict[str, Any]) -> bytes:
    """Return compact canonical UTF-8 JSON for in-memory size accounting."""

    return json.dumps(
        _studio_json_compatible_value(dr),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def serialize_dr_v0_3(dr: Dict[str, Any]) -> bytes:
    """Serialize Studio JSON.stringify-compatible UTF-8 export bytes."""

    return json.dumps(
        _studio_json_compatible_value(dr),
        ensure_ascii=False,
        indent=2,
    ).encode("utf-8")


def _attach_v03_audit_report(
    dr: Dict[str, Any],
    findings: List[Dict[str, str]],
    checked_at: str,
    named_check_findings: Dict[str, List[Dict[str, str]]],
    compatibility_metrics: Optional[Dict[str, int]] = None,
) -> None:
    metrics: Dict[str, Any] = {
        "normalized_json_bytes": 0,
        "actual_export_bytes": 0,
        "actual_export_serialization": (
            "studio_json_stringify_pretty_utf8"
        ),
    }
    for _ in range(32):
        named_check_findings["file_size_check"] = _v03_file_size_findings(
            int(metrics["normalized_json_bytes"]),
            int(metrics["actual_export_bytes"]),
        )
        audit_report = _build_v03_audit_report(
            findings,
            checked_at,
            named_check_findings,
            serialization_metrics=metrics,
            compatibility_metrics=compatibility_metrics,
        )
        dr["audit_report"] = audit_report
        dr["audit"] = deepcopy(audit_report)
        next_metrics = {
            **metrics,
            "normalized_json_bytes": len(normalized_dr_json_v0_3(dr)),
            "actual_export_bytes": len(serialize_dr_v0_3(dr)),
        }
        if next_metrics == metrics:
            return
        metrics = next_metrics
    raise RuntimeError("DR v0.3 audit file size did not converge to final serialized bytes")


def _v03_export_projection_findings(dr: Dict[str, Any]) -> List[Dict[str, str]]:
    """Reject drift in required v0.3 compatibility aliases and frozen fields."""
    findings: List[Dict[str, str]] = []
    payload = _as_dict(dr.get("payload"))
    graph_snapshot = _as_dict(payload.get("graph_snapshot"))

    required_aliases = {
        "layers": "13_layers_snapshot",
        "slots": "slots",
        "runtime_requirements": "runtime_requirements",
        "memory_config": "memory_config",
        "memory_policy": "memory_policy",
        "lattice_config": "lattice_config",
        "voice_config": "voice_config",
        "safety_policy": "safety_policy",
        "screen_capability_declaration": "screen_capability_declaration",
    }
    for root_key, payload_key in required_aliases.items():
        if dr.get(root_key) != payload.get(payload_key):
            findings.append(
                _finding(
                    "FAIL",
                    "DR_EXPORT_COMPATIBILITY_PROJECTION_DRIFT",
                    f"required compatibility alias {root_key!r} must equal payload.{payload_key}",
                    root_key,
                )
            )
    if _normalized_module_semantics(dr.get("modules")) != (
        _normalized_module_semantics(payload.get("modules"))
    ):
        findings.append(
            _finding(
                "FAIL",
                "DR_EXPORT_COMPATIBILITY_PROJECTION_DRIFT",
                (
                    "required compatibility alias 'modules' must be a "
                    "normalized semantic projection of payload.modules"
                ),
                "modules",
            )
        )
    memory_config = _as_dict(payload.get("memory_config"))
    if memory_config.get("storage_backend") != "local_runtime":
        findings.append(
            _finding(
                "FAIL",
                "DR_MEMORY_STORAGE_BACKEND_OVERBOUND",
                "memory_config.storage_backend must use the semantic local_runtime contract",
                "payload.memory_config.storage_backend",
            )
        )
    legacy_memory_config = _as_dict(_as_dict(dr.get("legacy_blueprint")).get("memory_config"))
    if legacy_memory_config and legacy_memory_config.get("store") != "local_runtime":
        findings.append(
            _finding(
                "FAIL",
                "DR_LEGACY_MEMORY_STORAGE_BACKEND_OVERBOUND",
                "legacy memory_config.store must project the semantic local_runtime contract",
                "legacy_blueprint.memory_config.store",
            )
        )

    memory_policy = _as_dict(payload.get("memory_policy"))
    if dr.get("memory_namespace") != memory_policy.get("namespace"):
        findings.append(
            _finding(
                "FAIL",
                "DR_EXPORT_COMPATIBILITY_PROJECTION_DRIFT",
                "required memory_namespace compatibility alias must equal payload.memory_policy.namespace",
                "memory_namespace",
            )
        )
    expected_memory_base = {
        "namespace": "default",
        "memory_types": list(_V03_FROZEN_MEMORY_TYPES),
        "preference_memory": {"type": "kv", "scope": "per_resident"},
        "retention_policy": "persistent",
        "read_write_policy": "local_runtime",
    }
    for key, expected in expected_memory_base.items():
        if memory_policy.get(key) != expected:
            findings.append(
                _finding(
                    "FAIL",
                    "DR_V03_MEMORY_CONTRACT_DRIFT",
                    f"frozen memory_policy.{key} must remain {expected!r}",
                    f"payload.memory_policy.{key}",
                )
            )
    extensions = _as_dict(memory_policy.get(_V03_MEMORY_POLICY_EXTENSIONS_KEY))
    if not extensions:
        findings.append(
            _finding(
                "FAIL",
                "DR_MEMORY_POLICY_EXTENSIONS_MISSING",
                "Stage 7.4 memory strategy must be nested under memory_policy_extensions",
                f"payload.memory_policy.{_V03_MEMORY_POLICY_EXTENSIONS_KEY}",
            )
        )
    for key in ("event_memory", "relationship_memory", "memory_access_control", "namespace_policy"):
        if key in memory_policy:
            findings.append(
                _finding(
                    "FAIL",
                    "DR_MEMORY_STRATEGY_ESCAPED_EXTENSION",
                    f"new memory strategy {key!r} must exist only inside memory_policy_extensions",
                    f"payload.memory_policy.{key}",
                )
            )

    top_safety = _as_dict(payload.get("safety_policy"))
    layer_3 = _as_dict(_as_dict(graph_snapshot.get("layer_outputs")).get("layer_3"))
    modules = {
        module.get("module_id"): module
        for module in payload.get("modules", [])
        if isinstance(module, dict)
    }
    output_sources = {output_key: module_id for module_id, output_key in LAYER3_SAFETY_POLICY_MODULES}
    output_sources.update({output_key: RISK_RESPONSE_MODULE_ID for output_key in LAYER3_RISK_RESPONSE_OUTPUT_KEYS})
    for output_key, module_id in output_sources.items():
        module = modules.get(module_id)
        module_output = _compiled_module_output(module, output_key) if isinstance(module, dict) else {}
        module_root_output = _as_dict(_as_dict(module.get("outputs")).get(output_key)) if isinstance(module, dict) else {}
        projected = _as_dict(top_safety.get(output_key))
        if not module_output or module_output != module_root_output or module_output != projected or projected != _as_dict(layer_3.get(output_key)):
            findings.append(
                _finding(
                    "FAIL",
                    "DR_SAFETY_PROJECTION_INCONSISTENT",
                    f"Layer 3 module output and safety projection differ for {output_key!r}",
                    f"payload.safety_policy.{output_key}",
                )
            )
            continue
        status = module_output.get("compile_validation_status")
        if status is not None and status not in {"valid", "invalid"}:
            findings.append(
                _finding(
                    "FAIL",
                    "DR_SAFETY_VALIDATION_STATUS_DRIFT",
                    f"compiled safety status must be final, got {status!r}",
                    f"payload.modules.{module_id}.outputs.{output_key}.compile_validation_status",
                )
            )

    if not any(finding.get("status") == "FAIL" for finding in findings):
        findings.append(
            _finding(
                "PASS",
                "DR_EXPORT_PROJECTIONS_CONSISTENT",
                "frozen compatibility aliases, local Runtime storage semantics, and Layer 3 safety projections are consistent",
                "payload",
            )
        )
    return findings


def _v03_frozen_root_field_findings(dr: Dict[str, Any]) -> List[Dict[str, str]]:
    """Require the frozen v0.3 root compatibility fields."""
    findings: List[Dict[str, str]] = []
    for field in ("layers", "modules", "slots"):
        if field not in dr:
            findings.append(
                _finding(
                    "FAIL",
                    "DR_V03_FROZEN_ROOT_FIELD_MISSING",
                    f"frozen DR v0.3 root field {field!r} is missing",
                    field,
                )
            )
    frozen_scalars = {
        "dr_version": DR_VERSION_V0_3,
        "dr_schema_version": DR_SCHEMA_VERSION_V0_3,
        "schema_version": SCHEMA_VERSION_V0_4,
        "protocol_version": PROTOCOL_VERSION_V0_4,
    }
    for field, expected in frozen_scalars.items():
        if dr.get(field) != expected:
            findings.append(
                _finding(
                    "FAIL",
                    "DR_V03_FROZEN_ROOT_FIELD_DRIFT",
                    (
                        f"frozen field {field!r} must remain "
                        f"{expected!r}, got {dr.get(field)!r}"
                    ),
                    field,
                )
            )

    payload = _as_dict(dr.get("payload"))
    manifest = _as_dict(dr.get("manifest"))
    expected_capabilities = list(STAGE_7_4_REQUIRED_SLOT_TYPES)
    if manifest.get("required_capabilities") != expected_capabilities:
        findings.append(
            _finding(
                "FAIL",
                "DR_V03_FROZEN_ROOT_FIELD_DRIFT",
                (
                    "manifest.required_capabilities must remain "
                    f"{expected_capabilities!r}"
                ),
                "manifest.required_capabilities",
            )
        )

    required_payload_fields = (
        "resident_identity",
        "memory_policy",
        "lattice_config",
        "voice_config",
        "runtime_requirements",
    )
    for field in required_payload_fields:
        if not isinstance(payload.get(field), dict) or not payload.get(field):
            findings.append(
                _finding(
                    "FAIL",
                    "DR_V03_FROZEN_ROOT_FIELD_MISSING",
                    f"frozen payload field {field!r} is missing",
                    f"payload.{field}",
                )
            )
    projection_expected = (
        _as_dict(payload.get("audit_policy")).get(
            "runtime_dialogue_projection_expected"
        )
        is True
    )
    if (
        projection_expected
        and "runtime_dialogue_projection" not in payload
    ):
        findings.append(
            _finding(
                "FAIL",
                "DR_V03_FROZEN_ROOT_FIELD_MISSING",
                (
                    "the current compile produced a runtime dialogue "
                    "projection and the frozen derived field is missing"
                ),
                "payload.runtime_dialogue_projection",
            )
        )
    elif "runtime_dialogue_projection" in payload and (
        not isinstance(payload.get("runtime_dialogue_projection"), dict)
        or not payload.get("runtime_dialogue_projection")
    ):
        findings.append(
            _finding(
                "FAIL",
                "DR_V03_FROZEN_ROOT_FIELD_DRIFT",
                (
                    "runtime_dialogue_projection must remain a non-empty "
                    "derived object when present; legacy-compatible absence "
                    "remains optional"
                ),
                "payload.runtime_dialogue_projection",
            )
        )
    if not isinstance(payload.get("modules"), list):
        findings.append(
            _finding(
                "FAIL",
                "DR_V03_FROZEN_ROOT_FIELD_MISSING",
                "authoritative payload.modules must be present",
                "payload.modules",
            )
        )
    if not isinstance(dr.get("visual_expression_mapping"), dict):
        findings.append(
            _finding(
                "FAIL",
                "DR_V03_FROZEN_ROOT_FIELD_MISSING",
                "frozen visual_expression_mapping projection is missing",
                "visual_expression_mapping",
            )
        )
    if not findings:
        findings.append(
            _finding(
                "PASS",
                "DR_V03_FROZEN_ROOT_FIELD_CHECK_PASSED",
                (
                    "frozen versions, required capabilities, authority "
                    "projection, and runtime projection fields are present"
                ),
                "payload",
            )
        )
    return findings


def _v3_compile_dr(canvas: Dict[str, Any], resident_name: Optional[str] = None) -> Dict[str, Any]:
    collection = collect_canvas(canvas)
    _normalize_visual_style_reference_sources(collection)
    raw_findings = validate_collection(collection)
    # Stage 6.11 is protocol-only: ignore provider-boundary findings that belong
    # to execution-layer wiring. The envelope must stay mock-only and declarative.
    findings = [
        finding
        for finding in raw_findings
        if finding.get("code") != "DR_PROVIDER_CONFIG"
        and not (
            finding.get("code") == "DR_SLOT_TYPE_UNMATCHED"
            and any(
                f"slot_type {slot_type!r}" in str(finding.get("message") or "")
                for slot_type in ("tts", "speech", "screen", "avatar", "ar", "tool")
            )
        )
    ]
    mapping_errors = projection_field_mapping_errors()
    if mapping_errors:
        findings.append(
            _finding(
                "FAIL",
                "DR_PROJECTION_FIELD_MAPPING_ERROR",
                "Runtime projection field mapping is invalid: "
                + "; ".join(mapping_errors),
                "compile_audit.projection_traceability.mappings",
            )
        )
    _synchronize_layer3_module_outputs(collection)
    _synchronize_stage_7_4_module_scope(collection)
    _synchronize_a4_module_status_classifications(collection)
    _synchronize_expression_state_module_output(collection, findings)
    _synchronize_particle_avatar_module_output(collection, findings)
    visual_expression_mapping_raw, visual_expression_diagnostics = (
        build_visual_expression_mapping(collection.get("modules", []))
    )
    visual_expression_mapping = VisualExpressionMappingV03.model_validate(
        visual_expression_mapping_raw
    ).model_dump(mode="json")
    for diagnostic in visual_expression_diagnostics:
        findings.append(
            _finding(
                "WARNING",
                diagnostic["code"],
                diagnostic["message"],
                diagnostic["path"],
            )
        )
    _synchronize_layer8_validation_results(collection, findings)
    _synchronize_layer8_behavior_module_outputs(collection)
    _synchronize_runtime_projection_source_outputs(
        collection, findings
    )
    _synchronize_self_awareness_fact_sources(collection)
    _validate_first_interaction_max_active_prompts(collection, findings)
    _synchronize_first_presence_module_output(collection, findings)
    blueprint = assemble_blueprint(collection, resident_name=resident_name)
    checked_at = _now_iso()
    compile_info = {"compiler": COMPILER_NAME, "compiler_version": COMPILER_VERSION, "compiled_at": checked_at, "source": "canvas", "layer_count": len(collection["layers"]), "module_count": len(collection["modules"]), "slot_count": len(collection["slots"]), "schema_version": DR_SCHEMA_VERSION_V0_3, "protocol_version": PROTOCOL_VERSION_V0_4}
    resident = blueprint.get("resident", {})
    if isinstance(resident, dict):
        # v0.3 root metadata is authoritative for this formal compatibility
        # alias. The frozen v0.1 compiler constant remains unchanged.
        resident["dr_version"] = DR_VERSION_V0_3
    resident_id = resident.get("resident_id") or _slugify(resident.get("name") or resident_name or "Digital Resident")
    resident_name_final = resident.get("name") or resident_name or "Digital Resident"
    basic_identity_module = next(
        (
            module
            for module in collection.get("modules", [])
            if isinstance(module, dict)
            and module.get("module_id") == "module_basic_identity"
        ),
        {},
    )
    basic_identity_fields = _module_field_values_from_fields(
        _module_fields_from_field_input(basic_identity_module)
    )
    configured_resident_id = _nonempty_str(
        basic_identity_fields.get("resident_id")
    )
    if configured_resident_id:
        resident_id = configured_resident_id
    dialogue_runtime_profile = (
        _synchronize_dialogue_runtime_profile_module_output(
            collection, resident_id
        )
    )
    if dialogue_runtime_profile is not None and not validate_dialogue_runtime_profile(
        dialogue_runtime_profile
    ):
        findings.append(
            _finding(
                "FAIL",
                "DR_DIALOGUE_RUNTIME_PROFILE_INVALID",
                "dialogue_runtime_profile must use a known type template, valid resident overrides, and both required authority references",
                "payload.modules.dialogue_runtime_profile",
            )
        )
    required_capabilities = list(STAGE_7_4_REQUIRED_SLOT_TYPES)
    runtime_requirements, provider_requirements = build_v03_runtime_contract(collection["slots"])
    payload = {"resident_identity": {"resident_id": resident_id, "name": resident_name_final, "resident_type": "digital_resident", "primary_language": "zh", "symbolic_origin": "Eterna Studio", "city_symbol": "Aftelle", "personality_summary": blueprint.get("disclosure") or "AI-generated digital resident; synthetic persona.", "domain_focus": ["memory", "lattice", "voice", "screen_guidance"]}, "resident_blueprint": {"resident_id": resident_id, "resident_name": resident_name_final, "description": resident.get("description"), "source_workflow_name": collection["workflow"].get("name"), "ui_language": _normalize_ui_language(collection["workflow"].get("metadata", {}).get("ui_language")) if isinstance(collection["workflow"].get("metadata"), dict) else None, "tags": collection["workflow"].get("metadata", {}).get("tags", []) if isinstance(collection["workflow"].get("metadata"), dict) else []}, "13_layers_snapshot": collection["layers"], "modules": collection["modules"], "nodes": collection["nodes"], "node_snapshot": collection["nodes"], "slots": collection["slots"], "edges": collection["edges"], "graph_snapshot": _build_lightweight_graph_snapshot(collection), "runtime_requirements": runtime_requirements, "provider_requirements": provider_requirements, "memory_policy": {}, "memory_config": {"schema_version": DR_SCHEMA_VERSION_V0_3, "resident_id": resident_id, "namespace": "default", "storage_backend": "sqlite", "memory_types": ["short_term_memory", "preference_memory", "event_memory", "relationship_memory", "interaction_log"], "interaction_log": {"enabled": True, "append_only": True}, "preference_memory": {"enabled": True, "mode": "kv"}, "mock_only": True}, "lattice_config": {"schema_version": DR_SCHEMA_VERSION_V0_3, "resident_id": resident_id, "emotion": "neutral", "energy": 0.5, "attention": "self", "motion": "idle_breathing", "voice_state": "idle", "particle_density": 0.5, "color_palette": ["#7aa2f7", "#5dd39e", "#f2a65a"], "focus_target": "none", "state_transition_policy": "mock_transition"}, "voice_config": {"schema_version": DR_SCHEMA_VERSION_V0_3, "tts_profile": {"provider": "mock", "voice_id": "mock_voice"}, "voice_profile": {"voice_id": "mock_voice", "speed": 1.0, "timbre": "neutral"}, "voice_state_schema": {"voice_state": ["idle", "speaking", "listening", "muted"]}, "voice_lattice_sync_policy": {"sync_policy": "mirror", "trace_keys": ["voice_state", "lattice_state.voice_state"]}, "speech_event_schema": {"placeholder": True, "event_type": "speech.input_event", "fields": ["text", "locale", "source", "timestamp"]}, "subtitle_policy": {"enabled": True, "mode": "mock"}}, "screen_capability_declaration": _v3_screen_capability(), "safety_policy": {"no_secret_in_dr": True, "no_direct_provider_binding": True, "mock_screen_only": True, "user_data_not_embedded": True, "not_executable": True, "notes": ["mock-only screen guidance", "no real screen read", "no auto click"]}, "audit_policy": {"mode": "declarative", "source": "compile_audit", "requires_review": False}, "runtime_plan": _v3_runtime_plan(), "fallback_routes": [{"capability": "llm", "route": "llm_mock", "mode": "mock", "notes": "fallback reasoning"}, {"capability": "memory", "route": "memory_mock", "mode": "mock", "notes": "fallback memory"}, {"capability": "tts", "route": "tts_mock", "mode": "mock", "notes": "fallback TTS"}, {"capability": "lattice", "route": "lattice_mock", "mode": "mock", "notes": "fallback lattice"}, {"capability": "screen_mock", "route": "screen_mock", "mode": "mock", "notes": "fallback screen guidance"}]}
    payload["voice_config"] = derive_voice_config_status(
        payload["voice_config"]
    )
    payload["lattice_config"] = derive_lattice_config_status(
        payload["lattice_config"]
    )
    payload["audit_policy"].update(
        {
            "content_revision": STAGE7_4_12_A4_CONTENT_REVISION,
            "schema_traceability_gate_revision": (
                STAGE7_4_12_FINAL_SCHEMA_TRACEABILITY_GATE_FIX_REVISION
            ),
            "identity_literal_export_gate_revision": (
                STAGE7_4_12_IDENTITY_LITERAL_EXPORT_GATE_FIX_REVISION
            ),
            "capability_status_governance": (
                build_capability_status_governance()
            ),
        }
    )
    # payload.modules is the sole module authority. The frozen memory surface
    # remains unchanged; Stage 7.4 policy is attached later as an extension.
    payload["memory_config"]["storage_backend"] = "local_runtime"
    payload["fallback_routes"] = [
        route
        for route in payload["fallback_routes"]
        if route.get("capability") in set(STAGE_7_4_REQUIRED_SLOT_TYPES)
    ]
    payload["memory_config"]["memory_types"] = list(_V03_FROZEN_MEMORY_TYPES)
    payload["memory_config"]["namespace"] = "default"
    payload["graph_snapshot"]["layer_outputs"] = _assemble_identity_core_outputs(
        collection,
        resident_id,
        resident_name_final,
        findings,
    )
    payload["graph_snapshot"]["layer_outputs"].update(_assemble_layer3_safety_outputs(collection))
    _merge_layer3_safety_into_safety_policy(payload)
    payload["graph_snapshot"]["layer_outputs"].update(_assemble_layer8_behavior_outputs(collection))
    payload["graph_snapshot"]["layer_outputs_status"] = (
        module_surface_classification(
            "payload.graph_snapshot.layer_outputs"
        )
    )
    _merge_layer8_behavior_into_payload(payload)
    payload.update(_assemble_first_greeting_config_extensions(collection))
    memory_policy_extensions = _assemble_layer5_memory_policy(collection, resident_id, findings)
    payload["memory_policy"] = _build_v03_memory_policy(resident_id, memory_policy_extensions)
    identity_sync = _v3_identity_sync_from_profile(payload)
    if identity_sync.get("resident_id"):
        resident_id = identity_sync["resident_id"]
    if identity_sync.get("name"):
        resident_name_final = identity_sync["name"]
    payload["resident_identity"]["resident_id"] = resident_id
    payload["resident_identity"]["name"] = resident_name_final
    if identity_sync.get("primary_language"):
        payload["resident_identity"]["primary_language"] = identity_sync["primary_language"]
    if identity_sync.get("city_symbol"):
        payload["resident_identity"]["city_symbol"] = identity_sync["city_symbol"]
    if identity_sync.get("personality_summary"):
        payload["resident_identity"]["personality_summary"] = identity_sync["personality_summary"]
    if identity_sync.get("domain_focus"):
        payload["resident_identity"]["domain_focus"] = identity_sync["domain_focus"]
    payload["resident_blueprint"]["resident_id"] = resident_id
    payload["resident_blueprint"]["resident_name"] = resident_name_final
    payload["resident_blueprint"]["source_workflow_name"] = STAGE_7_4_BASELINE_WORKFLOW_NAME
    if identity_sync.get("description"):
        payload["resident_blueprint"]["description"] = identity_sync["description"]
    if identity_sync.get("primary_language"):
        identity_ui_language = _normalize_ui_language(
            identity_sync["primary_language"]
        )
        if identity_ui_language is not None:
            payload["resident_blueprint"][
                "ui_language"
            ] = identity_ui_language
    if identity_sync.get("tags"):
        payload["resident_blueprint"]["tags"] = identity_sync["tags"]
    for config_key in ("memory_policy", "memory_config", "lattice_config"):
        if isinstance(payload.get(config_key), dict):
            payload[config_key]["resident_id"] = resident_id
    private_namespace = f"private_memory:{resident_id}"
    extensions = _as_dict(_as_dict(payload.get("memory_policy")).get(_V03_MEMORY_POLICY_EXTENSIONS_KEY))
    extensions["resident_id"] = resident_id
    extensions["namespace"] = private_namespace
    payload["memory_policy"][_V03_MEMORY_POLICY_EXTENSIONS_KEY] = extensions
    if isinstance(resident, dict):
        resident["resident_id"] = resident_id
        resident["name"] = resident_name_final
        if identity_sync.get("resident_description"):
            resident["description"] = identity_sync["resident_description"]
        if identity_sync.get("disclosure"):
            resident["disclosure"] = identity_sync["disclosure"]
    _sync_legacy_blueprint_identity(blueprint, resident_id, resident_name_final)
    _sync_legacy_blueprint_runtime_requirements(blueprint)
    blueprint["memory_namespace"] = "default"
    if isinstance(blueprint.get("memory_config"), dict):
        blueprint["memory_config"]["memory_types"] = list(_V03_FROZEN_MEMORY_TYPES)
        blueprint["memory_config"]["store"] = "local_runtime"
        blueprint["memory_config"].pop("namespace", None)
    supporting_source_paths = [
        path
        for path, present in (
            ("payload.resident_identity", bool(_as_dict(payload.get("resident_identity")))),
            ("payload.safety_policy", bool(_as_dict(payload.get("safety_policy")))),
            ("payload.memory_policy", bool(_as_dict(payload.get("memory_policy")))),
            (
                "payload.relationship.initial_relationship",
                bool(_as_dict(_as_dict(payload.get("relationship")).get("initial_relationship"))),
            ),
        )
        if present
    ]
    runtime_policy_values = _assemble_runtime_dialogue_policy_values(
        collection,
        memory_policy_extensions,
        findings,
    )
    runtime_dialogue_projection = build_runtime_dialogue_projection(
        _as_dict(payload.get("behavior_policy")),
        supporting_source_paths,
        dialogue_runtime_profile,
        runtime_policy_values,
    )
    if runtime_dialogue_projection is not None:
        payload["runtime_dialogue_projection"] = runtime_dialogue_projection
    payload["audit_policy"][
        "runtime_dialogue_projection_expected"
    ] = runtime_dialogue_projection is not None
    manifest = {"resident_id": resident_id, "resident_name": resident_name_final, "dr_schema_version": DR_SCHEMA_VERSION_V0_3, "revision": "1", "source_protocol_version": PROTOCOL_VERSION_V0_4, "compatible_runtime": RUNTIME_VERSION, "required_capabilities": required_capabilities, "checksum": f"mock-checksum:{resident_id}:{len(collection['layers'])}:{len(collection['modules'])}:{len(collection['slots'])}"}
    findings.extend(_identity_consistency_findings(manifest, payload, resident))
    findings.extend(_environment_mapping_findings(payload))
    findings.extend(_v03_version_findings(resident, manifest, payload, compile_info))
    dr = {
        "file_type": FILE_TYPE,
        "dr_version": DR_VERSION_V0_3,
        "dr_schema_version": DR_SCHEMA_VERSION_V0_3,
        "protocol_version": PROTOCOL_VERSION_V0_4,
        "schema_version": SCHEMA_VERSION_V0_4,
        "revision": "1",
        "created_at": checked_at,
        "updated_at": checked_at,
        "not_executable": True,
        "manifest": manifest,
        "payload": payload,
        "visual_expression_mapping": visual_expression_mapping,
        "compile_info": compile_info,
    }
    dr.update(_v03_compatibility_aliases(payload, resident, blueprint, resident_id))
    named_check_findings = {
        "stage_scope_check": _v03_stage_scope_findings(dr),
        "compatibility_check": _v03_export_projection_findings(dr),
        "frozen_root_field_check": _v03_frozen_root_field_findings(dr),
        "pending_validation_check": _v03_pending_validation_findings(dr),
        "duplicate_source_check": _v03_duplicate_source_findings(dr),
        "memory_support_level_check": _v03_memory_support_level_findings(dr),
        "capability_status_check": _v03_capability_status_findings(dr),
        "identity_literal_export_gate_check": (
            _identity_hardcode_findings(
                collection,
                payload,
                {
                    "visual_expression_mapping": (
                        visual_expression_mapping
                    )
                },
            )
        ),
        "empty_layer_status_check": (
            _v03_empty_layer_status_findings(dr)
        ),
    }
    _attach_v03_audit_report(
        dr,
        findings,
        checked_at,
        named_check_findings,
        compatibility_metrics=collection.get(
            "compatibility_metrics"
        ),
    )
    gate = validate_dr_document_v0_3(dr)
    named_check_findings["formal_schema_check"] = list(
        gate["schema_findings"]
    )
    named_check_findings["security_configuration_check"] = list(
        gate["security_findings"]
    )
    findings.extend(gate["runtime_contract_findings"])
    _attach_v03_audit_report(
        dr,
        findings,
        checked_at,
        named_check_findings,
        compatibility_metrics=collection.get(
            "compatibility_metrics"
        ),
    )
    return dr


def _v3_mock_load_dr(dr: Dict[str, Any]) -> Dict[str, Any]:
    dr = dr or {}
    manifest = _as_dict(dr.get("manifest"))
    payload = _as_dict(dr.get("payload"))
    resident = _as_dict(dr.get("resident"))
    payload_modules = (
        payload.get("modules")
        if "modules" in payload
        else dr.get("modules")
    )
    payload_slots = (
        payload.get("slots")
        if "slots" in payload
        else dr.get("slots")
    )
    payload_layers = (
        payload.get("13_layers_snapshot")
        if "13_layers_snapshot" in payload
        else dr.get("layers")
    )
    resident_id = manifest.get("resident_id") or resident.get("resident_id") or _as_dict(payload.get("resident_identity")).get("resident_id")
    visual_expression_mapping, compatibility_diagnostics = (
        normalize_visual_expression_mapping(dr.get("visual_expression_mapping"))
    )
    validation_document = deepcopy(dr)
    validation_document["visual_expression_mapping"] = (
        visual_expression_mapping
    )
    gate = validate_dr_document_v0_3(validation_document)
    visual_expression_mapping = VisualExpressionMappingV03.model_validate(
        visual_expression_mapping
    ).model_dump(mode="json")
    audit_valid = bool(_as_dict(dr.get("audit_report") or dr.get("audit")).get("valid"))
    ok = bool(
        gate["valid"]
        and audit_valid
        and resident_id
        and isinstance(payload_modules, list)
        and isinstance(payload_slots, list)
    )
    return {
        "loaded": bool(ok),
        "mock": True,
        "resident_id": resident_id,
        "dr_version": dr.get("dr_version"),
        "runtime_version": RUNTIME_VERSION,
        "layer_count": len(payload_layers or []),
        "module_count": len(payload_modules or []),
        "slot_count": len(payload_slots or []),
        "audit_valid": audit_valid,
        "visual_expression_mapping": visual_expression_mapping,
        "compatibility_diagnostics": [
            *compatibility_diagnostics,
            *[
                finding
                for finding in gate["findings"]
                if finding.get("status") == "FAIL"
            ],
        ],
    }


def _v3_compile_dr_result(canvas: Dict[str, Any], resident_name: Optional[str] = None) -> Dict[str, Any]:
    v03 = _v3_compile_dr(canvas, resident_name=resident_name)
    valid = bool(v03.get("audit_report", {}).get("valid"))
    findings = list(v03.get("audit_report", {}).get("findings", []))
    errors = [f for f in findings if f.get("status") == "FAIL"]
    warnings = [f for f in findings if f.get("status") == "WARNING"]
    filename = dr_filename(v03)
    pseudo_dag = [{"type": "meta", "shape": "linear", "mode": "serial", "node_count": len(v03.get("payload", {}).get("runtime_plan", {}).get("steps", []))}]
    pseudo_dag.extend({"type": "node", "id": step.get("step"), "kind": "intent_step", "binding": None, "parallelizable": bool(step.get("optional"))} for step in v03.get("payload", {}).get("runtime_plan", {}).get("steps", []))
    return {
        "valid": valid,
        "errors": errors,
        "warnings": warnings,
        "module_audit": {"checked": len(v03.get("payload", {}).get("modules", [])), "findings": errors, "ok": valid},
        "layer_audit": {"present_layers": [layer["layer_id"] for layer in v03.get("layers", []) if layer.get("present")], "missing_layers": [], "findings": warnings, "ok": valid},
        "compile_audit": {
            "ok": valid,
            "findings": findings,
            "projection_traceability": build_projection_traceability(),
        },
        "orchestration_compatibility": True,
        "pseudo_dag": pseudo_dag,
        "dr_version": v03.get("dr_version"),
        "compiled_dr": v03 if valid else None,
        "dr_payload": v03.get("payload"),
        "lattice_config": v03.get("payload", {}).get("lattice_config"),
        "lattice_state_schema": v03.get("lattice_state_schema"),
        "multi_resident_lattice_state": v03.get("multi_resident_lattice_state"),
        "memory_config": v03.get("memory_config"),
        "memory_namespace": v03.get("memory_namespace"),
        "screen_capability_declaration": v03.get("screen_capability_declaration"),
        "voice_config": v03.get("voice_config"),
        "safety_policy": v03.get("safety_policy"),
        "behavior_policy": v03.get("payload", {}).get("behavior_policy"),
        "filename": filename,
        "metadata": {
            "filename": filename,
            "schema_version": v03.get("dr_schema_version"),
            "v03_compile_info": v03.get("compile_info"),
            "v03_audit_report": v03.get("audit_report"),
            "v03_valid": valid,
        },
    }


def compile_dr_v0_3(canvas: Dict[str, Any], resident_name: Optional[str] = None) -> Dict[str, Any]:
    return _v3_compile_dr(canvas, resident_name=resident_name)


def mock_load_dr_v0_3(dr: Dict[str, Any]) -> Dict[str, Any]:
    return _v3_mock_load_dr(dr)


def compile_dr_result_v0_3(canvas: Dict[str, Any], resident_name: Optional[str] = None) -> Dict[str, Any]:
    return _v3_compile_dr_result(canvas, resident_name=resident_name)
