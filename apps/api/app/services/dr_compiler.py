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

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

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
    VoiceConfigV03,
    build_runtime_plan_steps,
)
from ..models.v0_4 import (
    CANONICAL_LAYERS,
    CANONICAL_LAYER_IDS,
    PROTOCOL_VERSION_V0_4,
    SCHEMA_VERSION_V0_4,
    SlotType,
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
    get_module_catalog,
    LANGUAGE_BEHAVIOR_MODULE_ID,
    LANGUAGE_BEHAVIOR_PRESET_ID,
    INTERACTION_BEHAVIOR_MODULE_ID,
    INTERACTION_BEHAVIOR_PRESET_ID,
    TASK_BEHAVIOR_MODULE_ID,
    TASK_BEHAVIOR_PRESET_ID,
    SOCIAL_BEHAVIOR_MODULE_ID,
    SOCIAL_BEHAVIOR_PRESET_ID,
    DECISION_BEHAVIOR_MODULE_ID,
    DECISION_BEHAVIOR_PRESET_ID,
    DETAIL_BEHAVIOR_MODULE_ID,
    DETAIL_BEHAVIOR_PRESET_ID,
)
from ..registry.slot_catalog import get_slot_catalog

DR_VERSION = "0.1"
FILE_TYPE = "digital_resident"
FILE_SUFFIX = ".digital_resident"
COMPILER_NAME = "DRCompiler"
COMPILER_VERSION = "0.1.0"
RUNTIME_VERSION = "resident_v1_mock"
MIN_KERNEL = "6.1"
STAGE_7_4_BASELINE_WORKFLOW_NAME = "Stage 7.4 Human Empathy DR Baseline"
STAGE_7_4_REQUIRED_SLOT_TYPES = ["llm", "memory", "lattice", "voice"]
_FORBIDDEN_STAGE_7_4_DOMAIN_FOCUS = {"ar", "tool", "screen_guidance", "provider", "cross_app_control"}

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
_LAYER8_EXCLUDED_BEHAVIOR_MODULE_IDS = ("behavior_policy_slot",)
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
    return _as_dict(params.get("checkbox_config") or params.get("checklist_config"))


def _behavior_reference_payload(reference: Dict[str, Any]) -> Dict[str, Any]:
    layer_id = _nonempty_str(reference.get("layer_id"))
    module_id = _nonempty_str(reference.get("module_id"))
    field_id = _nonempty_str(reference.get("field_id"))
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
    field_reference_nodes = _module_nodes_by_type(module, "field_reference")
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
        if isinstance(node_selected, list):
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
        if isinstance(node.get("node_id"), str) and node.get("node_id")
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


def _assemble_layer8_behavior_outputs(collection: Dict[str, Any]) -> Dict[str, Any]:
    modules = {module.get("module_id"): module for module in collection.get("modules", []) if isinstance(module, dict)}
    behavior_modules: Dict[str, Any] = {}
    for module_id, policy_key, preset_id in _LAYER8_BEHAVIOR_MODULES:
        module = modules.get(module_id)
        if isinstance(module, dict):
            behavior_modules[policy_key] = _behavior_module_policy(module, policy_key, preset_id)

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


def _build_v03_audit_report(findings: List[Dict[str, str]], checked_at: str) -> Dict[str, Any]:
    return {
        "schema_version": DR_SCHEMA_VERSION_V0_3,
        "valid": not any(finding.get("status") == "FAIL" for finding in findings),
        "findings": findings,
        "checked_at": checked_at,
        "summary": {
            "fail": sum(1 for finding in findings if finding.get("status") == "FAIL"),
            "warning": sum(1 for finding in findings if finding.get("status") == "WARNING"),
            "pass": sum(1 for finding in findings if finding.get("status") == "PASS"),
        },
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
    raw_modules = canvas.get("modules") or workflow.get("modules")
    if raw_modules:
        modules = [_as_dict(m) for m in raw_modules]
    else:
        modules = [m.model_dump(mode="json") for m in get_module_catalog()]
    modules = [module for module in modules if not _is_catalog_only_module(module)]

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
        layers.append(
            {
                "layer_id": layer_id,
                "layer_name": layer_name,
                "layer_order": layer_order,
                "module_ids": modules_by_layer.get(layer_id, []),
                "present": layer_id in present_layer_ids,
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
            "memory_types": ["short_term_memory", "profile_memory", "preference_memory", "interaction_log"],
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
        "module_audit": {"checked": len(v03.get("modules", [])), "findings": errors, "ok": valid},
        "layer_audit": {
            "present_layers": [layer["layer_id"] for layer in v03.get("layers", []) if layer.get("present")],
            "missing_layers": [],
            "findings": warnings,
            "ok": valid,
        },
        "compile_audit": {"ok": valid, "findings": findings},
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

def _v3_provider_requirements() -> Dict[str, Any]:
    return {
        "llm": {"required": True, "mode": "mock", "capabilities": ["reasoning"]},
        "memory": {"required": True, "mode": "local_runtime", "capabilities": ["read", "write", "view", "clear"]},
        "tts": {"required": True, "mode": "mock", "capabilities": ["speak", "preview"]},
        "avatar": {"required": False, "mode": "mock", "capabilities": ["render_state"]},
        "lattice": {"required": True, "mode": "mock", "capabilities": ["state_update", "state_read"]},
        "screen_mock": {"required": True, "mode": "mock", "capabilities": ["context", "anchor", "guidance"]},
        "screen": {"required": True, "mode": "mock", "capabilities": ["context", "anchor", "guidance"]},
    }


def _v3_runtime_plan() -> Dict[str, Any]:
    return {
        "schema_version": DR_SCHEMA_VERSION_V0_3,
        "mode": "declarative",
        "steps": [
            {"step": "user_input", "from": "user_input", "to": "memory.read", "optional": False},
            {"step": "memory.read", "from": "memory.read", "to": "llm.reasoning", "optional": False},
            {"step": "llm.reasoning", "from": "llm.reasoning", "to": "memory.write", "optional": False},
            {"step": "memory.write", "from": "memory.write", "to": "lattice.update", "optional": False},
            {"step": "lattice.update", "from": "lattice.update", "to": "voice.speak", "optional": True},
            {"step": "voice.speak", "from": "voice.speak", "to": "output", "optional": True},
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


def _v3_compile_dr(canvas: Dict[str, Any], resident_name: Optional[str] = None) -> Dict[str, Any]:
    collection = collect_canvas(canvas)
    raw_findings = validate_collection(collection)
    # Stage 6.11 is protocol-only: ignore provider-boundary findings that belong
    # to execution-layer wiring. The envelope must stay mock-only and declarative.
    findings = [f for f in raw_findings if f.get("code") != "DR_PROVIDER_CONFIG"]
    # Preserve legacy slot-type mismatch behavior for the v0.1 acceptance tests.
    if any(m.get("slot_type") == "tts" for m in collection.get("modules", [])) and not any(s.get("slot_type") == "tts" for s in collection.get("slots", [])):
        findings.append(_finding("FAIL", "DR_SLOT_TYPE_UNMATCHED", "module requires slot_type 'tts' but no slot provides it", "modules"))
    blueprint = assemble_blueprint(collection, resident_name=resident_name)
    valid = not any(f["status"] == "FAIL" for f in findings)
    checked_at = _now_iso()
    audit_report = _build_v03_audit_report(findings, checked_at)
    compile_info = {"compiler": COMPILER_NAME, "compiler_version": COMPILER_VERSION, "compiled_at": checked_at, "source": "canvas", "layer_count": len(collection["layers"]), "module_count": len(collection["modules"]), "slot_count": len(collection["slots"]), "schema_version": DR_SCHEMA_VERSION_V0_3, "protocol_version": PROTOCOL_VERSION_V0_4}
    resident = blueprint.get("resident", {})
    resident_id = resident.get("resident_id") or _slugify(resident.get("name") or resident_name or "Digital Resident")
    resident_name_final = resident.get("name") or resident_name or "Digital Resident"
    required_capabilities = list(STAGE_7_4_REQUIRED_SLOT_TYPES)
    required_slot_types = list(STAGE_7_4_REQUIRED_SLOT_TYPES)
    payload = {"resident_identity": {"resident_id": resident_id, "name": resident_name_final, "resident_type": "digital_resident", "primary_language": "zh", "symbolic_origin": "Eterna Studio", "city_symbol": "Aftelle", "personality_summary": blueprint.get("disclosure") or "AI-generated digital resident; synthetic persona.", "domain_focus": ["memory", "lattice", "voice", "screen_guidance"]}, "resident_blueprint": {"resident_id": resident_id, "resident_name": resident_name_final, "description": resident.get("description"), "source_workflow_name": collection["workflow"].get("name"), "ui_language": collection["workflow"].get("metadata", {}).get("ui_language") if isinstance(collection["workflow"].get("metadata"), dict) else None, "tags": collection["workflow"].get("metadata", {}).get("tags", []) if isinstance(collection["workflow"].get("metadata"), dict) else []}, "13_layers_snapshot": collection["layers"], "modules": collection["modules"], "nodes": collection["nodes"], "node_snapshot": collection["nodes"], "slots": collection["slots"], "edges": collection["edges"], "graph_snapshot": {"nodes": collection["nodes"], "edges": collection["edges"], "layers": collection["layers"], "modules": collection["modules"], "slots": collection["slots"]}, "runtime_requirements": {"required_slot_types": required_slot_types, "required_engines": ["llm_mock", "memory_mock", "tts_mock", "avatar_mock", "lattice_mock", "screen_mock"], "required_provider_types": ["llm", "memory", "tts", "avatar", "screen"], "runtime_api_version": SCHEMA_VERSION_V0_4, "execution_mode": "mock", "fallback_mode": "mock_fallback"}, "provider_requirements": _v3_provider_requirements(), "memory_policy": {"schema_version": DR_SCHEMA_VERSION_V0_3, "resident_id": resident_id, "namespace": "default", "memory_types": ["short_term_memory", "profile_memory", "preference_memory", "interaction_log"], "interaction_log": {"type": "append_only", "scope": "per_resident"}, "preference_memory": {"type": "kv", "scope": "per_resident"}, "retention_policy": "persistent", "read_write_policy": "local_runtime"}, "memory_config": {"schema_version": DR_SCHEMA_VERSION_V0_3, "resident_id": resident_id, "namespace": "default", "storage_backend": "sqlite", "memory_types": ["short_term_memory", "profile_memory", "preference_memory", "interaction_log"], "interaction_log": {"enabled": True, "append_only": True}, "preference_memory": {"enabled": True, "mode": "kv"}, "mock_only": True}, "lattice_config": {"schema_version": DR_SCHEMA_VERSION_V0_3, "resident_id": resident_id, "emotion": "neutral", "energy": 0.5, "attention": "self", "motion": "idle_breathing", "voice_state": "idle", "particle_density": 0.5, "color_palette": ["#7aa2f7", "#5dd39e", "#f2a65a"], "focus_target": "none", "state_transition_policy": "mock_transition"}, "voice_config": {"schema_version": DR_SCHEMA_VERSION_V0_3, "tts_profile": {"provider": "mock", "voice_id": "mock_voice"}, "voice_profile": {"voice_id": "mock_voice", "speed": 1.0, "timbre": "neutral"}, "voice_state_schema": {"voice_state": ["idle", "speaking", "listening", "muted"]}, "voice_lattice_sync_policy": {"sync_policy": "mirror", "trace_keys": ["voice_state", "lattice_state.voice_state"]}, "speech_event_schema": {"placeholder": True, "event_type": "speech.input_event", "fields": ["text", "locale", "source", "timestamp"]}, "subtitle_policy": {"enabled": True, "mode": "mock"}}, "screen_capability_declaration": _v3_screen_capability(), "safety_policy": {"no_secret_in_dr": True, "no_direct_provider_binding": True, "mock_screen_only": True, "user_data_not_embedded": True, "not_executable": True, "notes": ["mock-only screen guidance", "no real screen read", "no auto click"]}, "audit_policy": {"mode": "declarative", "source": "compile_audit", "requires_review": False}, "runtime_plan": _v3_runtime_plan(), "fallback_routes": [{"capability": "llm", "route": "llm_mock", "mode": "mock", "notes": "fallback reasoning"}, {"capability": "memory", "route": "memory_mock", "mode": "mock", "notes": "fallback memory"}, {"capability": "tts", "route": "tts_mock", "mode": "mock", "notes": "fallback TTS"}, {"capability": "lattice", "route": "lattice_mock", "mode": "mock", "notes": "fallback lattice"}, {"capability": "screen_mock", "route": "screen_mock", "mode": "mock", "notes": "fallback screen guidance"}]}
    payload["graph_snapshot"]["layer_outputs"] = _assemble_identity_core_outputs(
        collection,
        resident_id,
        resident_name_final,
        findings,
    )
    payload["graph_snapshot"]["layer_outputs"].update(_assemble_layer3_safety_outputs(collection))
    _merge_layer3_safety_into_safety_policy(payload)
    payload["graph_snapshot"]["layer_outputs"].update(_assemble_layer8_behavior_outputs(collection))
    _merge_layer8_behavior_into_payload(payload)
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
        payload["resident_blueprint"]["ui_language"] = identity_sync["primary_language"]
    if identity_sync.get("tags"):
        payload["resident_blueprint"]["tags"] = identity_sync["tags"]
    for config_key in ("memory_policy", "memory_config", "lattice_config"):
        if isinstance(payload.get(config_key), dict):
            payload[config_key]["resident_id"] = resident_id
    if isinstance(resident, dict):
        resident["resident_id"] = resident_id
        resident["name"] = resident_name_final
        if identity_sync.get("resident_description"):
            resident["description"] = identity_sync["resident_description"]
        if identity_sync.get("disclosure"):
            resident["disclosure"] = identity_sync["disclosure"]
    _sync_legacy_blueprint_identity(blueprint, resident_id, resident_name_final)
    _sync_legacy_blueprint_runtime_requirements(blueprint)
    manifest = {"resident_id": resident_id, "resident_name": resident_name_final, "dr_schema_version": DR_SCHEMA_VERSION_V0_3, "revision": "1", "source_protocol_version": PROTOCOL_VERSION_V0_4, "compatible_runtime": RUNTIME_VERSION, "required_capabilities": required_capabilities, "checksum": f"mock-checksum:{resident_id}:{len(collection['layers'])}:{len(collection['modules'])}:{len(collection['slots'])}"}
    findings.extend(_identity_consistency_findings(manifest, payload, resident))
    audit_report = _build_v03_audit_report(findings, checked_at)
    return {
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
        "compile_info": compile_info,
        "audit_report": audit_report,
        # Backward-compatible aliases kept so older read-only tests and loaders
        # can still inspect the legacy compile surface while v0.3 is the source
        # of truth.
        "resident": resident,
        "layers": collection["layers"],
        "modules": collection["modules"],
        "slots": collection["slots"],
        "runtime_requirements": payload.get("runtime_requirements"),
        "memory_config": payload.get("memory_config"),
        "memory_namespace": payload.get("memory_policy", {}).get("namespace", payload.get("memory_config", {}).get("namespace", "default")),
        "memory_policy": payload.get("memory_policy"),
        "lattice_config": payload.get("lattice_config"),
        "lattice_state_schema": {
            "resident_id": resident_id,
            "emotion": payload.get("lattice_config", {}).get("emotion", "neutral"),
            "energy": payload.get("lattice_config", {}).get("energy", 0.5),
            "attention": payload.get("lattice_config", {}).get("attention", "self"),
            "motion": payload.get("lattice_config", {}).get("motion", "idle_breathing"),
            "voice_state": payload.get("lattice_config", {}).get("voice_state", "idle"),
            "particle_density": payload.get("lattice_config", {}).get("particle_density", 0.5),
            "color_palette": payload.get("lattice_config", {}).get("color_palette", []),
            "focus_target": payload.get("lattice_config", {}).get("focus_target", "none"),
        },
        "voice_config": payload.get("voice_config"),
        "safety_policy": payload.get("safety_policy"),
        "behavior_policy": payload.get("behavior_policy"),
        "screen_capability_declaration": payload.get("screen_capability_declaration"),
        "multi_resident_lattice_state": {
            "resident_ids": [resident_id],
            "states": [],
        },
        "voice_state": payload.get("lattice_config", {}).get("voice_state"),
        "audit": audit_report,
        "legacy_blueprint": blueprint,
    }


def _v3_mock_load_dr(dr: Dict[str, Any]) -> Dict[str, Any]:
    dr = dr or {}
    manifest = _as_dict(dr.get("manifest"))
    payload = _as_dict(dr.get("payload"))
    resident = _as_dict(dr.get("resident"))
    resident_id = manifest.get("resident_id") or resident.get("resident_id") or _as_dict(payload.get("resident_identity")).get("resident_id")
    ok = bool(dr.get("file_type") == FILE_TYPE and dr.get("dr_version") == DR_VERSION_V0_3 and dr.get("not_executable") is True and resident_id and isinstance(payload.get("modules"), list) and isinstance(payload.get("slots"), list))
    return {"loaded": bool(ok), "mock": True, "resident_id": resident_id, "dr_version": dr.get("dr_version"), "runtime_version": RUNTIME_VERSION, "layer_count": len(payload.get("13_layers_snapshot") or dr.get("layers") or []), "module_count": len(payload.get("modules") or dr.get("modules") or []), "slot_count": len(payload.get("slots") or dr.get("slots") or []), "audit_valid": bool(_as_dict(dr.get("audit_report") or dr.get("audit")).get("valid"))}


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
        "module_audit": {"checked": len(v03.get("modules", [])), "findings": errors, "ok": valid},
        "layer_audit": {"present_layers": [layer["layer_id"] for layer in v03.get("layers", []) if layer.get("present")], "missing_layers": [], "findings": warnings, "ok": valid},
        "compile_audit": {"ok": valid, "findings": findings},
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
        "behavior_policy": v03.get("behavior_policy"),
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
