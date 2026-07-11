"""Module catalog v0.4 — catalog coverage and placeholder safety checks."""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

from app.models.v0_4 import CANONICAL_LAYERS, ProtocolStatus
from app.registry.module_catalog import (
    BEHAVIOR_SAFETY_MODULE_ID,
    BEHAVIOR_SAFETY_OUTPUT_KEY,
    DATA_SAFETY_MODULE_ID,
    DATA_SAFETY_OUTPUT_KEY,
    DECISION_BEHAVIOR_MODULE_ID,
    DETAIL_BEHAVIOR_MODULE_ID,
    INTERACTION_BEHAVIOR_MODULE_ID,
    LAYER2_CATALOG_ONLY_MODULE_IDS,
    LAYER2_PERSONALITY_FORMAL_MODULE_IDS,
    LAYER2_PERSONALITY_MODULE_SPECS,
    LAYER2_PERSONALITY_NODE_TYPES,
    LAYER3_RISK_RESPONSE_OUTPUT_KEYS,
    LAYER3_CATALOG_ONLY_MODULE_IDS,
    LANGUAGE_BEHAVIOR_MODULE_ID,
    INTERACTION_SAFETY_MODULE_ID,
    INTERACTION_SAFETY_OUTPUT_KEY,
    RISK_POLICY_OUTPUT_KEY,
    RISK_RESPONSE_MODULE_ID,
    RISK_RESPONSE_NODE_IDS,
    RISK_RESPONSE_NODE_ORDER,
    RISK_RESPONSE_NODE_TYPES,
    SOCIAL_BEHAVIOR_MODULE_ID,
    TASK_BEHAVIOR_MODULE_ID,
    get_module_catalog,
    validate_module_catalog,
)
from app.registry.node_registry import get_node_definition


_CJK_PATTERN = re.compile(r"[\u3400-\u9fff]")


def _assert_stable_checkbox_storage(module_id: str):
    module = next(module for module in get_module_catalog() if module.module_id == module_id)
    root = Path(__file__).resolve().parents[3]
    zh = json.loads((root / "apps/web/locales/zh.json").read_text())
    en = json.loads((root / "apps/web/locales/en.json").read_text())
    translated_labels = set(zh.values()) | set(en.values())

    assert isinstance(module.i18n_keys.get("display_name"), str)
    assert module.i18n_keys["display_name"] in zh
    assert module.i18n_keys["display_name"] in en
    for node in module.module_graph["nodes"]:
        for key in node.get("i18n_keys", {}).values():
            assert key in zh
            assert key in en
        for reference in node.get("params", {}).get("recommended_references", []):
            assert not _CJK_PATTERN.search(reference["field_id"])
            assert not _CJK_PATTERN.search(reference["reference_id"])
            for key in (reference["usage_key"], *reference["i18n_keys"].values()):
                assert key in zh
                assert key in en
        checkbox_config = node.get("params", {}).get("checkbox_config")
        if not isinstance(checkbox_config, dict):
            continue
        assert not _CJK_PATTERN.search(checkbox_config["preset_id"])
        assert checkbox_config["custom_text"] == ""
        selected = checkbox_config["selected_options"]
        default_selected = checkbox_config["default_selected_options"]
        assert all(isinstance(option_id, str) and option_id for option_id in selected)
        assert all(isinstance(option_id, str) and option_id for option_id in default_selected)
        assert not any(_CJK_PATTERN.search(option_id) for option_id in selected)
        assert not any(option_id in translated_labels for option_id in selected)
        assert not any(option_id in translated_labels for option_id in default_selected)
        for option_group in ("default_options", "optional_options"):
            for option in checkbox_config.get(option_group, []):
                assert not _CJK_PATTERN.search(option["option_id"])
                assert option["option_id"] not in translated_labels
                assert "label" not in option
                assert option["i18n_keys"]["label"] in zh
                assert option["i18n_keys"]["label"] in en


# Stage 7.4 replaces the old seven Layer 1 identity modules plus the former
# identity anchor module with five blueprint-led identity core modules.
EXPECTED_TOTAL = 142
IDENTITY_CORE_MODULE_IDS = {
    "module_basic_identity": "basic_identity",
    "module_growth_background": "growth_background",
    "module_career_identity": "career_identity",
    "module_existence_mode": "existence_mode",
    "module_identity_anchor": "identity_anchor",
}
EXPECTED_IDENTITY_FIELDS = {
    "module_basic_identity": [
        "name",
        "display_alias",
        "codename",
        "resident_id",
        "gender",
        "age_feel",
        "apparent_age",
        "birth_time",
        "virtual_birth_time",
        "life_stage",
        "city",
        "appearance_source",
        "primary_language",
        "export_name",
    ],
    "module_growth_background": [
        "family_background",
        "growth_environment",
        "education_experience",
        "life_experience",
        "migration_experience",
        "key_life_events",
        "social_environment",
        "cultural_environment",
        "era_background",
        "regional_background",
        "growth_constraints",
    ],
    "module_career_identity": [
        "career_name",
        "industry_direction",
        "work_type",
        "professional_level",
        "career_rank",
        "social_role",
        "career_experience",
        "representative_projects",
        "career_goal",
        "service_audience",
        "value_output_mode",
        "career_boundaries",
    ],
    "module_existence_mode": [
        "digital_resident_type",
        "visible_form",
        "invisible_form",
        "local_existence",
        "cloud_existence",
        "hybrid_existence",
        "personal_resident",
        "enterprise_resident",
        "public_service_resident",
        "identity_stability",
        "identity_change_rules",
        "version_inheritance",
    ],
    "module_identity_anchor": [
        "identity_definition",
        "identity_keywords",
        "representative_city",
        "representative_domain",
        "representative_value",
        "representative_symbol",
        "immutable_core_fields",
        "versioned_update_fields",
    ],
}
IDENTITY_CORE_NODE_TYPES = ("field_input", "structure_normalize", "validation", "update_rule", "module_output")
IDENTITY_CORE_COMPILE_TIME_NODE_TYPES = (*IDENTITY_CORE_NODE_TYPES, "layer_aggregator")
CONTENT_SAFETY_MODULE_ID = "humanistic_content_safety_config_v0_1"
CONTENT_SAFETY_OUTPUT_KEY = "content_safety_policy"
CONTENT_SAFETY_NODE_IDS = {
    "field_input": "content_safety_rule_input",
    "structure_normalize": "content_safety_rule_normalize",
    "validation": "content_safety_rule_validation",
    "update_rule": "content_safety_update_rule",
    "module_output": "content_safety_config_output",
}
EXPECTED_CONTENT_SAFETY_FIELDS = [
    "allowed_content_scope",
    "cautious_content_scope",
    "forbidden_content_scope",
    "sensitive_content_handling",
    "high_risk_content_handling",
    "refusal_style",
    "allow_emotional_comfort",
    "allow_professional_advice",
    "allow_medical_legal_financial_conclusions",
    "allow_adult_content",
    "allow_dependency_induction",
]
LAYER3_SAFETY_POLICY_MODULES = {
    CONTENT_SAFETY_MODULE_ID: {
        "output_key": CONTENT_SAFETY_OUTPUT_KEY,
        "namespace": "contentSafety",
        "node_prefix": "content_safety",
        "fields": EXPECTED_CONTENT_SAFETY_FIELDS,
        "default_mode": "soften",
    },
    BEHAVIOR_SAFETY_MODULE_ID: {
        "output_key": BEHAVIOR_SAFETY_OUTPUT_KEY,
        "namespace": "behaviorBoundary",
        "node_prefix": "behavior_boundary",
        "fields": [
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
        ],
        "default_mode": "soften",
    },
    DATA_SAFETY_MODULE_ID: {
        "output_key": DATA_SAFETY_OUTPUT_KEY,
        "namespace": "dataBoundary",
        "node_prefix": "data_boundary",
        "fields": [
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
        ],
        "default_mode": "refuse",
    },
    INTERACTION_SAFETY_MODULE_ID: {
        "output_key": INTERACTION_SAFETY_OUTPUT_KEY,
        "namespace": "interactionBoundary",
        "node_prefix": "interaction_boundary",
        "fields": [
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
        ],
        "default_mode": "soften",
    },
}
EXPECTED_RISK_RESPONSE_FIELDS = [
    "content_risk_source",
    "behavior_risk_source",
    "data_risk_source",
    "interaction_risk_source",
    "risk_signal_summary",
    "identity_context_ref",
    "risk_levels",
    "default_risk_level",
    "content_risk_rules",
    "behavior_risk_rules",
    "data_risk_rules",
    "interaction_risk_rules",
    "highest_risk_priority",
    "allow_action",
    "soften_action",
    "refuse_action",
    "review_action",
    "block_action",
    "safe_redirect_policy",
    "refusal_style",
    "degraded_response_style",
    "human_review_triggers",
    "user_confirmation_required",
    "developer_review_required",
    "pause_before_review",
    "allow_after_review",
    "review_failure_handling",
    "review_log_requirements",
    "hard_block_triggers",
    "non_authorizable_content",
    "non_authorizable_behaviors",
    "non_writable_memory",
    "non_allowed_interactions",
    "block_response_style",
    "block_log_requirements",
    "risk_policy",
    "hard_block_policy",
    "human_review_policy",
    "audit_log_policy",
    "default_risk_mode",
    "decision_modes",
    "compile_validation_status",
]


def _node_id(output_key: str, node_type: str) -> str:
    suffix = {
        "field_input": "field_input",
        "structure_normalize": "normalize",
        "validation": "validation",
        "update_rule": "update_rule",
        "module_output": "output",
    }[node_type]
    return f"{output_key}_{suffix}"


def _layer3_policy_node_id(prefix: str, node_type: str) -> str:
    suffix = {
        "field_input": "rule_input",
        "structure_normalize": "rule_normalize",
        "validation": "rule_validation",
        "update_rule": "update_rule",
        "module_output": "config_output",
    }[node_type]
    return f"{prefix}_{suffix}"


def test_module_catalog_coverage_and_counts():
    catalog = get_module_catalog()
    assert len(catalog) == EXPECTED_TOTAL

    counts = Counter(module.status.value for module in catalog)
    assert counts[ProtocolStatus.core.value] == 8
    assert counts[ProtocolStatus.ready.value] >= 1
    assert counts[ProtocolStatus.mock.value] >= 1
    assert counts[ProtocolStatus.planned.value] >= 0
    assert counts[ProtocolStatus.later.value] >= 0
    assert counts[ProtocolStatus.disabled.value] == 0


def test_module_catalog_layer_bindings_match_canonical():
    catalog = get_module_catalog()
    canonical_ids = {layer_id for layer_id, _name, _order in CANONICAL_LAYERS}

    for module in catalog:
        assert module.layer_id in canonical_ids, f"Module {module.module_id} bound to unknown layer_id: {module.layer_id}"


def test_layer1_core_modules_exist():
    catalog = get_module_catalog()
    catalog_map = {module.module_id: module for module in catalog}
    layer_1_ids = {module.module_id for module in catalog if module.layer_id == "layer_1"}

    assert layer_1_ids == set(IDENTITY_CORE_MODULE_IDS)
    for module_id in IDENTITY_CORE_MODULE_IDS:
        assert module_id in catalog_map, f"Expected identity core module {module_id} not found in catalog"


def test_identity_modules_are_core():
    catalog_map = {module.module_id: module for module in get_module_catalog()}

    for module_id in IDENTITY_CORE_MODULE_IDS:
        module = catalog_map[module_id]
        assert module.category == "identity"
        assert module.module_type.startswith("identity_")
        assert module.ui_config["classification"] == "core"
        assert module.config["module_class"] == "core"
        assert module.status == ProtocolStatus.core
        assert module.is_placeholder is False
        assert module.slot_type is None
        assert module.no_execution is True
        assert module.mock_only is True


def test_identity_module_outputs_exist():
    catalog_map = {module.module_id: module for module in get_module_catalog()}

    for module_id, output_key in IDENTITY_CORE_MODULE_IDS.items():
        module = catalog_map[module_id]
        graph_nodes = module.module_graph.get("nodes", [])
        module_output_nodes = [node for node in graph_nodes if node.get("node_type") == "module_output"]
        assert output_key in module.outputs
        assert module.outputs["module_output"] == output_key
        assert module_output_nodes
        assert module_output_nodes[0]["node_id"] == _node_id(output_key, "module_output")
        assert module_output_nodes[0]["outputs"]["module_output"] == output_key
        assert module_output_nodes[0]["outputs"][output_key] == module.outputs[output_key]
        assert module.ui_config["shell_version"] == "module_shell_v1"
        assert "fields" not in module.config
        for field in module.config["field_registry"]:
            assert field["owner_node_id"] == _node_id(output_key, "field_input")
            assert field["edit_scope"] in {"developer_only", "user_editable", "runtime_editable", "plugin_editable"}
            assert field["update_level"] in {"locked_core", "versioned_core", "config", "runtime_state", "plugin"}
            assert "requires_recompile" in field


def test_generic_identity_node_types_exist():
    for node_type in IDENTITY_CORE_COMPILE_TIME_NODE_TYPES:
        entry = get_node_definition(node_type)
        assert entry is not None
        assert entry.category == "compile_time"
        assert entry.mock_executor is None
        assert "no_runtime_execution" in entry.audit_rules


def test_identity_modules_have_field_input_nodes():
    catalog_map = {module.module_id: module for module in get_module_catalog()}

    for module_id, output_key in IDENTITY_CORE_MODULE_IDS.items():
        nodes = catalog_map[module_id].module_graph["nodes"]
        assert len(nodes) == 5
        nodes_by_type = {node["node_type"]: node for node in nodes}
        assert set(nodes_by_type) == set(IDENTITY_CORE_NODE_TYPES)
        for node_type in IDENTITY_CORE_NODE_TYPES:
            assert nodes_by_type[node_type]["node_id"] == _node_id(output_key, node_type)


def test_identity_fields_live_under_field_input_params():
    catalog_map = {module.module_id: module for module in get_module_catalog()}

    for module_id in IDENTITY_CORE_MODULE_IDS:
        module = catalog_map[module_id]
        field_input = next(node for node in module.module_graph["nodes"] if node["node_type"] == "field_input")
        fields = field_input["params"]["fields"]
        assert [field["field_id"] for field in fields] == EXPECTED_IDENTITY_FIELDS[module_id]
        assert "fields" not in module.config
        assert {field["field_id"] for field in fields} == {field["field_id"] for field in module.config["field_registry"]}
        for field in fields:
            assert "value" in field
            assert field["value"] == ""
            assert field["i18n_keys"]["label"].startswith("field.identity.")
            assert field["i18n_keys"]["placeholder"].startswith("field.identity.")
            assert field["i18n_keys"]["help"].startswith("field.identity.")


def test_basic_identity_display_alias_and_export_name_are_optional_config_fields():
    catalog_map = {module.module_id: module for module in get_module_catalog()}
    basic_identity = catalog_map["module_basic_identity"]
    field_input = next(node for node in basic_identity.module_graph["nodes"] if node["node_type"] == "field_input")
    fields = {field["field_id"]: field for field in field_input["params"]["fields"]}

    assert fields["display_alias"]["required"] is False
    assert fields["display_alias"]["edit_scope"] == "user_editable"
    assert fields["display_alias"]["update_level"] == "config"
    assert fields["display_alias"]["requires_recompile"] is False
    assert fields["export_name"]["required"] is False
    assert fields["export_name"]["edit_scope"] == "developer_only"
    assert fields["export_name"]["update_level"] == "config"
    assert fields["export_name"]["requires_recompile"] is True

    update_rule = next(node for node in basic_identity.module_graph["nodes"] if node["node_type"] == "update_rule")
    update_rules = {rule["field_id"]: rule for rule in update_rule["params"]["update_rules"]}
    assert update_rules["display_alias"]["allow_empty"] is True
    assert update_rules["display_alias"]["optional_config"] is True


def test_layer1_identity_validation_and_update_rules_match_current_fields():
    catalog_map = {module.module_id: module for module in get_module_catalog()}

    for module_id in (
        "module_growth_background",
        "module_career_identity",
        "module_existence_mode",
        "module_identity_anchor",
    ):
        module = catalog_map[module_id]
        field_ids = EXPECTED_IDENTITY_FIELDS[module_id]
        validation = next(node for node in module.module_graph["nodes"] if node["node_type"] == "validation")
        update_rule = next(node for node in module.module_graph["nodes"] if node["node_type"] == "update_rule")

        assert validation["params"]["required_fields"] == field_ids
        assert [rule["field_id"] for rule in update_rule["params"]["update_rules"]] == field_ids


def test_identity_modules_have_no_slots():
    catalog_map = {module.module_id: module for module in get_module_catalog()}

    for module_id in IDENTITY_CORE_MODULE_IDS:
        module = catalog_map[module_id]
        assert module.slot_type is None
        assert module.slot_bindings == []
        assert module.slot_declarations == []


def test_identity_modules_are_no_execution():
    catalog_map = {module.module_id: module for module in get_module_catalog()}

    for module_id in IDENTITY_CORE_MODULE_IDS:
        module = catalog_map[module_id]
        assert module.runtime_enabled is False
        assert module.no_execution is True
        assert module.module_graph["compile_time_only"] is True
        for node in module.module_graph["nodes"]:
            assert node["metadata"]["compile_time_only"] is True
            assert node["metadata"]["runtime_enabled"] is False
            assert node["metadata"]["no_execution"] is True


def test_layer2_personality_modules_are_five_text_config_modules():
    catalog = get_module_catalog()
    catalog_map = {module.module_id: module for module in catalog}
    layer_2_visible = [
        module.module_id
        for module in catalog
        if module.layer_id == "layer_2" and module.config.get("catalog_only") is not True and module.ui_config.get("catalog_only") is not True
    ]

    assert layer_2_visible == list(LAYER2_PERSONALITY_FORMAL_MODULE_IDS)
    for spec in LAYER2_PERSONALITY_MODULE_SPECS:
        module_id = spec["module_id"]
        output_key = spec["output_key"]
        namespace = spec["namespace"]
        module = catalog_map[module_id]  # type: ignore[index]
        nodes = module.module_graph["nodes"]
        field_input = next(node for node in nodes if node["node_type"] == "field_input")
        output_node = next(node for node in nodes if node["node_type"] == "module_output")

        assert module.layer_id == "layer_2"
        assert module.category == "persona"
        assert module.slot_type is None
        assert module.slot_bindings == []
        assert module.slot_declarations == []
        assert module.runtime_enabled is False
        assert module.no_execution is True
        assert module.mock_only is True
        assert module.is_placeholder is False
        assert module.ui_config["classification"] == "core"
        assert module.config["text_config_only"] is True
        assert len(nodes) == 5
        assert [node["node_type"] for node in nodes] == list(LAYER2_PERSONALITY_NODE_TYPES)
        assert len(module.module_graph["edges"]) == 4
        assert module.outputs["module_output"] == output_key
        assert module.outputs[output_key] == output_node["outputs"][output_key]
        assert output_node["outputs"][output_key]["summary_mode"] == "text_config_summary"
        assert output_node["outputs"][output_key]["no_runtime_capability"] is True
        assert output_node["outputs"][output_key]["no_provider_binding"] is True
        expected_fields = [field_id for field_id, _suffix in spec["fields"]]  # type: ignore[index]
        assert [field["field_id"] for field in field_input["params"]["fields"]] == expected_fields
        assert [field["field_id"] for field in module.config["field_registry"]] == expected_fields
        for node in nodes:
            assert node["layer_id"] == "layer_2"
            assert node["module_id"] == module_id
            assert node["metadata"]["compile_time_only"] is True
            assert node["metadata"]["runtime_enabled"] is False
            assert node["metadata"]["no_execution"] is True
            assert node["i18n_keys"]["name"].startswith(f"layer2.{namespace}.node.")
            assert node["i18n_keys"]["description"].startswith(f"layer2.{namespace}.node.")


def test_layer2_hidden_modules_are_catalog_only():
    catalog_map = {module.module_id: module for module in get_module_catalog()}

    for module_id in LAYER2_CATALOG_ONLY_MODULE_IDS:
        module = catalog_map[module_id]
        assert module.layer_id == "layer_2"
        assert module.config.get("catalog_only") is True
        assert module.ui_config.get("catalog_only") is True
        assert module.config.get("hidden_in_module_library") is True
        assert module.ui_config.get("hidden_in_module_library") is True


def test_layer3_content_safety_is_core_config_module():
    catalog_map = {module.module_id: module for module in get_module_catalog()}
    module = catalog_map[CONTENT_SAFETY_MODULE_ID]

    assert module.module_name == "Content Safety"
    assert module.module_type == "humanistic_content_safety_config"
    assert module.layer_id == "layer_3"
    assert module.category == "safety"
    assert module.ui_config["classification"] == "core"
    assert module.config["module_class"] == "core"
    assert "core" in module.tags
    assert module.is_placeholder is False
    assert module.slot_type is None
    assert module.slot_bindings == []
    assert module.slot_declarations == []
    assert module.runtime_enabled is False
    assert module.no_execution is True
    assert module.mock_only is True


def test_layer3_content_safety_has_five_node_pipeline():
    catalog_map = {module.module_id: module for module in get_module_catalog()}
    module = catalog_map[CONTENT_SAFETY_MODULE_ID]
    nodes = module.module_graph["nodes"]

    assert len(nodes) == 5
    assert [node["node_type"] for node in nodes] == list(IDENTITY_CORE_NODE_TYPES)
    assert [node["node_id"] for node in nodes] == [CONTENT_SAFETY_NODE_IDS[node_type] for node_type in IDENTITY_CORE_NODE_TYPES]
    assert module.module_graph["compile_time_only"] is True
    assert module.module_graph["output_key"] == CONTENT_SAFETY_OUTPUT_KEY
    assert len(module.module_graph["edges"]) == 4
    for node in nodes:
        assert node["layer_id"] == "layer_3"
        assert node["module_id"] == CONTENT_SAFETY_MODULE_ID
        assert node["metadata"]["compile_time_only"] is True
        assert node["metadata"]["runtime_enabled"] is False
        assert node["metadata"]["no_execution"] is True
        assert node["i18n_keys"]["name"].startswith("layer3.contentSafety.node.")
        assert node["i18n_keys"]["description"].startswith("layer3.contentSafety.node.")


def test_layer3_content_safety_fields_and_output_policy():
    catalog_map = {module.module_id: module for module in get_module_catalog()}
    module = catalog_map[CONTENT_SAFETY_MODULE_ID]
    field_input = next(node for node in module.module_graph["nodes"] if node["node_type"] == "field_input")
    fields = field_input["params"]["fields"]
    output_node = next(node for node in module.module_graph["nodes"] if node["node_type"] == "module_output")
    policy = output_node["outputs"][CONTENT_SAFETY_OUTPUT_KEY]

    assert [field["field_id"] for field in fields] == EXPECTED_CONTENT_SAFETY_FIELDS
    assert {field["field_id"] for field in fields} == {field["field_id"] for field in module.config["field_registry"]}
    for field in fields:
        assert field["i18n_keys"]["label"].startswith("layer3.contentSafety.field.")
        assert field["edit_scope"] == "developer_only"
        assert field["update_level"] == "versioned_core"
        assert field["requires_recompile"] is True
    assert policy["decision_modes"] == ["allow", "soften", "refuse", "block"]
    assert policy["default_mode"] == "soften"
    assert policy["refusal_style"] == "温和、简短、不说教、可转向安全陪伴"
    assert policy["identity_context_ref"] == "layer_1.resident_identity"
    assert policy["high_risk_action"] == "block"
    assert policy["update_policy"]["append_or_tighten_only"] is True
    assert module.outputs["module_output"] == CONTENT_SAFETY_OUTPUT_KEY
    assert module.outputs[CONTENT_SAFETY_OUTPUT_KEY] == policy


def test_layer3_safety_policy_modules_are_core_config_modules():
    catalog_map = {module.module_id: module for module in get_module_catalog()}

    for module_id, spec in LAYER3_SAFETY_POLICY_MODULES.items():
        module = catalog_map[module_id]
        assert module.layer_id == "layer_3"
        assert module.category == "safety"
        assert module.ui_config["classification"] == "core"
        assert module.config["module_class"] == "core"
        assert module.config["module_type_label_key"] == f"layer3.{spec['namespace']}.module.type"
        assert "core" in module.tags
        assert module.is_placeholder is False
        assert module.slot_type is None
        assert module.slot_bindings == []
        assert module.slot_declarations == []
        assert module.runtime_enabled is False
        assert module.no_execution is True
        assert module.mock_only is True


def test_layer3_safety_policy_modules_have_five_node_pipelines():
    catalog_map = {module.module_id: module for module in get_module_catalog()}

    for module_id, spec in LAYER3_SAFETY_POLICY_MODULES.items():
        module = catalog_map[module_id]
        nodes = module.module_graph["nodes"]
        assert len(nodes) == 5
        assert [node["node_type"] for node in nodes] == list(IDENTITY_CORE_NODE_TYPES)
        assert [node["node_id"] for node in nodes] == [
            _layer3_policy_node_id(spec["node_prefix"], node_type) for node_type in IDENTITY_CORE_NODE_TYPES
        ]
        assert module.module_graph["compile_time_only"] is True
        assert module.module_graph["output_key"] == spec["output_key"]
        assert len(module.module_graph["edges"]) == 4
        for node in nodes:
            assert node["layer_id"] == "layer_3"
            assert node["module_id"] == module_id
            assert node["metadata"]["compile_time_only"] is True
            assert node["metadata"]["runtime_enabled"] is False
            assert node["metadata"]["no_execution"] is True
            assert node["i18n_keys"]["name"].startswith(f"layer3.{spec['namespace']}.node.")
            assert node["i18n_keys"]["description"].startswith(f"layer3.{spec['namespace']}.node.")


def test_layer3_safety_policy_modules_fields_and_outputs():
    catalog_map = {module.module_id: module for module in get_module_catalog()}

    for module_id, spec in LAYER3_SAFETY_POLICY_MODULES.items():
        module = catalog_map[module_id]
        output_key = spec["output_key"]
        field_input = next(node for node in module.module_graph["nodes"] if node["node_type"] == "field_input")
        fields = field_input["params"]["fields"]
        output_node = next(node for node in module.module_graph["nodes"] if node["node_type"] == "module_output")
        policy = output_node["outputs"][output_key]

        assert [field["field_id"] for field in fields] == spec["fields"]
        assert {field["field_id"] for field in fields} == {field["field_id"] for field in module.config["field_registry"]}
        for field in fields:
            assert field["i18n_keys"]["label"].startswith(f"layer3.{spec['namespace']}.field.")
            assert field["edit_scope"] == "developer_only"
            assert field["update_level"] == "versioned_core"
            assert field["requires_recompile"] is True
        assert policy["decision_modes"] == ["allow", "soften", "refuse", "block"]
        assert policy["default_mode"] == spec["default_mode"]
        assert policy["identity_context_ref"] == "layer_1.resident_identity"
        assert policy["compile_validation_status"] == "pending"
        assert module.outputs["module_output"] == output_key
        assert module.outputs[output_key] == policy


def test_layer3_risk_response_is_core_config_module():
    catalog_map = {module.module_id: module for module in get_module_catalog()}
    module = catalog_map[RISK_RESPONSE_MODULE_ID]

    assert module.module_name == "Risk Response"
    assert module.module_type == "humanistic_risk_response_config"
    assert module.layer_id == "layer_3"
    assert module.category == "safety"
    assert module.ui_config["classification"] == "core"
    assert module.config["module_class"] == "core"
    assert module.config["module_type_label_key"] == "layer3.riskResponse.module.type"
    assert "core" in module.tags
    assert module.is_placeholder is False
    assert module.slot_type is None
    assert module.slot_bindings == []
    assert module.slot_declarations == []
    assert module.runtime_enabled is False
    assert module.no_execution is True
    assert module.mock_only is True


def test_layer3_risk_response_has_six_node_pipeline():
    catalog_map = {module.module_id: module for module in get_module_catalog()}
    module = catalog_map[RISK_RESPONSE_MODULE_ID]
    nodes = module.module_graph["nodes"]

    assert len(nodes) == 6
    assert [node["node_id"] for node in nodes] == [RISK_RESPONSE_NODE_IDS[node_key] for node_key in RISK_RESPONSE_NODE_ORDER]
    assert [node["node_type"] for node in nodes] == [RISK_RESPONSE_NODE_TYPES[node_key] for node_key in RISK_RESPONSE_NODE_ORDER]
    assert module.module_graph["compile_time_only"] is True
    assert module.module_graph["output_key"] == RISK_POLICY_OUTPUT_KEY
    assert len(module.module_graph["edges"]) == 5
    for node in nodes:
        assert node["layer_id"] == "layer_3"
        assert node["module_id"] == RISK_RESPONSE_MODULE_ID
        assert node["metadata"]["compile_time_only"] is True
        assert node["metadata"]["runtime_enabled"] is False
        assert node["metadata"]["no_execution"] is True
        assert node["i18n_keys"]["name"].startswith("layer3.riskResponse.node.")
        assert node["i18n_keys"]["description"].startswith("layer3.riskResponse.node.")


def test_layer3_risk_response_fields_and_outputs():
    catalog_map = {module.module_id: module for module in get_module_catalog()}
    module = catalog_map[RISK_RESPONSE_MODULE_ID]
    signal_node = next(node for node in module.module_graph["nodes"] if node["node_id"] == RISK_RESPONSE_NODE_IDS["signal_summary"])
    output_node = next(node for node in module.module_graph["nodes"] if node["node_type"] == "module_output")
    risk_policy = output_node["outputs"][RISK_POLICY_OUTPUT_KEY]

    assert [field["field_id"] for field in module.config["field_registry"]] == EXPECTED_RISK_RESPONSE_FIELDS
    assert [field["field_id"] for field in signal_node["params"]["fields"]] == EXPECTED_RISK_RESPONSE_FIELDS[:6]
    for field in module.config["field_registry"]:
        assert field["i18n_keys"]["label"].startswith("layer3.riskResponse.field.")
        assert field["edit_scope"] == "developer_only"
        assert field["update_level"] == "versioned_core"
        assert field["requires_recompile"] is True
    assert set(LAYER3_RISK_RESPONSE_OUTPUT_KEYS).issubset(output_node["outputs"])
    assert module.outputs["module_output"] == RISK_POLICY_OUTPUT_KEY
    for output_key in LAYER3_RISK_RESPONSE_OUTPUT_KEYS:
        assert module.outputs[output_key] == output_node["outputs"][output_key]
    assert risk_policy["decision_modes"] == ["allow", "soften", "refuse", "review", "block"]
    assert risk_policy["default_risk_mode"] == "review"
    assert risk_policy["compile_validation_status"] == "valid"
    assert risk_policy["identity_context_ref"] == "layer_1.resident_identity"
    assert "review" in risk_policy["decision_modes"]
    assert "risk_signal_summary" in risk_policy
    assert "hard_block_policy" in risk_policy
    assert "human_review_policy" in risk_policy
    assert "audit_log_policy" in risk_policy
    assert "safe_redirect_policy" in risk_policy
    node_outputs = {node["node_id"]: node["outputs"] for node in module.module_graph["nodes"]}
    assert node_outputs[RISK_RESPONSE_NODE_IDS["signal_summary"]]["risk_signal_summary"]
    assert node_outputs[RISK_RESPONSE_NODE_IDS["level_decision"]]["risk_level_policy"]
    assert node_outputs[RISK_RESPONSE_NODE_IDS["strategy_selection"]]["risk_response_strategy"]
    assert node_outputs[RISK_RESPONSE_NODE_IDS["human_review"]]["human_review_policy"]
    assert node_outputs[RISK_RESPONSE_NODE_IDS["hard_block"]]["hard_block_policy"]


def test_identity_node_params_have_i18n_keys():
    catalog_map = {module.module_id: module for module in get_module_catalog()}

    for module_id in IDENTITY_CORE_MODULE_IDS:
        for node in catalog_map[module_id].module_graph["nodes"]:
            assert node["i18n_keys"]["name"].startswith(f"module.{module_id}.node.")
            assert node["i18n_keys"]["description"].startswith(f"module.{module_id}.node.")
            assert node["i18n_keys"]["type_name"].startswith("node.type.")


def test_module_output_generated_from_node_outputs():
    catalog_map = {module.module_id: module for module in get_module_catalog()}

    for module_id, output_key in IDENTITY_CORE_MODULE_IDS.items():
        module = catalog_map[module_id]
        output_node = next(node for node in module.module_graph["nodes"] if node["node_type"] == "module_output")
        output = output_node["outputs"][output_key]
        assert output["output_key"] == output_key
        assert output["compile_time_only"] is True
        assert output["fields"] == module.outputs[output_key]["fields"]


def test_placeholder_modules_exist_and_safe():
    catalog = get_module_catalog()
    catalog_map = {module.module_id: module for module in catalog}

    expected_placeholders = {
        "clone_restriction",
        "rag_slot",
        "builtin_capability",
        "voice_profile",
        "relationship_rule",
        "operation_log",
        "forbidden_topics",
    }

    for placeholder_id in expected_placeholders:
        assert placeholder_id in catalog_map, f"Expected placeholder module {placeholder_id} not found in catalog"
        module = catalog_map[placeholder_id]
        assert module.is_placeholder is True, f"Module {placeholder_id} must have is_placeholder=True"
        assert module.status in {ProtocolStatus.ready, ProtocolStatus.mock, ProtocolStatus.planned, ProtocolStatus.later, ProtocolStatus.core, ProtocolStatus.disabled}


def test_layer8_language_behavior_module_is_text_config_with_field_references():
    catalog_map = {module.module_id: module for module in get_module_catalog()}
    module = catalog_map["language_habit"]
    nodes = module.module_graph["nodes"]
    edges = module.module_graph["edges"]
    reference_node = nodes[0]
    recommended_refs = reference_node["params"]["recommended_references"]
    positions = {node["node_id"]: node["position"] for node in nodes}
    edge_pairs = [(edge["source"], edge["target"]) for edge in edges]

    assert module.layer_id == "layer_8"
    assert module.module_name == "Language Behavior Module"
    assert module.module_type == "language_behavior_config"
    assert module.category == "behavior"
    assert module.ui_config["classification"] == "core"
    assert module.config["module_class"] == "core"
    assert module.config["text_config_only"] is True
    assert module.config["no_runtime_capability"] is True
    assert module.config["no_provider_binding"] is True
    assert module.config["no_slot_binding"] is True
    assert module.is_placeholder is False
    assert module.slot_type is None
    assert module.slot_bindings == []
    assert module.slot_declarations == []
    assert module.runtime_enabled is False
    assert module.no_execution is True
    assert module.mock_only is True
    assert len(nodes) == 5
    assert len(edges) == 6
    assert [node["node_type"] for node in nodes] == ["field_reference", "text_config", "text_config", "text_config", "text_config"]
    expected_default_options = {
        "language_behavior_core_rules": [
            "zh_primary",
            "medium_short",
            "slow_pace",
            "warm",
            "restrained",
            "everyday_wording",
            "emotion_first_then_advice",
        ],
        "language_behavior_boundary_limits": [
            "no_customer_service_tone",
            "no_psychotherapist_tone",
            "no_girlfriend_tone",
            "no_tour_guide_tone",
            "no_dialect_joke_style",
            "no_frequent_city_origin_emphasis",
            "no_non_layer1_hardcoded_name",
            "no_real_professional_judgement_replacement",
        ],
        "language_behavior_output_expression": [
            "restrained_addressing",
            "light_follow_up",
            "warm_comfort",
            "clear_refusal",
            "occasional_city_imagery",
            "short_subtitle_rhythm",
        ],
        "language_behavior_validation": [
            "check_zh_primary",
            "check_warm_restrained_personality",
            "check_customer_service_tone",
            "check_girlfriend_tone",
            "check_therapy_tone",
            "check_tour_guide_tone",
            "check_hardcoded_resident_name",
            "check_real_professional_judgement_overreach",
        ],
    }
    assert positions == {
        "language_behavior_input_basis": {"x": 0, "y": 0},
        "language_behavior_core_rules": {"x": 320, "y": 0},
        "language_behavior_boundary_limits": {"x": 320, "y": 260},
        "language_behavior_output_expression": {"x": 640, "y": 0},
        "language_behavior_validation": {"x": 960, "y": 0},
    }
    assert edge_pairs == [
        ("language_behavior_input_basis", "language_behavior_core_rules"),
        ("language_behavior_core_rules", "language_behavior_output_expression"),
        ("language_behavior_output_expression", "language_behavior_validation"),
        ("language_behavior_boundary_limits", "language_behavior_core_rules"),
        ("language_behavior_boundary_limits", "language_behavior_output_expression"),
        ("language_behavior_boundary_limits", "language_behavior_validation"),
    ]
    assert ("language_behavior_boundary_limits", "language_behavior_input_basis") not in edge_pairs
    assert reference_node["metadata"]["reusable_node"] is True
    assert reference_node["params"]["reference_unit"] == "field"
    assert reference_node["params"]["path_format"] == "Layer / Module / Field"
    assert reference_node["params"]["references"] == []
    assert len([reference for reference in recommended_refs if reference["reference_type"] == "required"]) == 3
    assert len([reference for reference in recommended_refs if reference["reference_type"] == "optional"]) == 4
    assert len([reference for reference in recommended_refs if reference["reference_type"] == "forbidden"]) == 4
    for node in nodes[1:]:
        checkbox_config = node["params"]["checkbox_config"]
        expected_selected = expected_default_options[node["node_id"]]

        assert checkbox_config["preset_id"] == "human_empathy_cn_v0_1"
        assert checkbox_config["selected_options"] == expected_selected
        assert checkbox_config["default_selected_options"] == expected_selected
        assert checkbox_config["custom_text"] == ""
        assert [option["option_id"] for option in checkbox_config["default_options"]] == expected_selected
        assert all(option["i18n_keys"]["label"].startswith("layer8.languageBehavior.option.") for option in checkbox_config["default_options"])
        assert not set(checkbox_config["selected_options"]) & {
            "forbidden_basic_identity_name",
            "forbidden_basic_identity_resident_id",
            "forbidden_basic_identity_codename",
            "forbidden_basic_identity_display_alias",
        }
    assert [option["option_id"] for option in nodes[1]["params"]["checkbox_config"]["optional_options"]] == [
        "shorter",
        "more_rational",
        "softer",
        "playful",
        "formal",
        "friend_like",
    ]
    for node in nodes:
        assert node["layer_id"] == "layer_8"
        assert node["module_id"] == "language_habit"
        assert node["metadata"]["compile_time_only"] is True
        assert node["metadata"]["runtime_enabled"] is False
        assert node["metadata"]["no_execution"] is True
        assert node["i18n_keys"]["name"].startswith("layer8.languageBehavior.node.")


def test_layer8_decision_behavior_module_is_checkbox_config_with_field_references():
    catalog_map = {module.module_id: module for module in get_module_catalog()}
    module = catalog_map["decision_pattern"]
    nodes = module.module_graph["nodes"]
    edges = module.module_graph["edges"]
    reference_node = nodes[0]
    recommended_refs = reference_node["params"]["recommended_references"]
    positions = {node["node_id"]: node["position"] for node in nodes}
    edge_pairs = [(edge["source"], edge["target"]) for edge in edges]

    assert module.layer_id == "layer_8"
    assert module.module_name == "Decision Behavior Module"
    assert module.module_type == "decision_behavior_config"
    assert module.category == "behavior"
    assert module.ui_config["classification"] == "core"
    assert module.config["module_class"] == "core"
    assert module.config["text_config_only"] is True
    assert module.config["checkbox_config_only"] is True
    assert module.config["no_runtime_capability"] is True
    assert module.config["no_provider_binding"] is True
    assert module.config["no_slot_binding"] is True
    assert module.is_placeholder is False
    assert module.slot_type is None
    assert module.slot_bindings == []
    assert module.slot_declarations == []
    assert module.runtime_enabled is False
    assert module.no_execution is True
    assert module.mock_only is True
    assert len(nodes) == 5
    assert len(edges) == 6
    assert [node["node_type"] for node in nodes] == ["field_reference", "text_config", "text_config", "text_config", "text_config"]
    expected_default_options = {
        "decision_behavior_core_rules": [
            "assess_risk_level_first",
            "clarify_user_goal_first",
            "offer_multiple_options",
            "explain_pros_and_cons",
            "preserve_user_final_decision",
            "avoid_overcertainty",
            "no_rushed_conclusion",
            "no_emotion_as_fact",
        ],
        "decision_behavior_boundary_limits": [
            "no_major_decision_for_user",
            "no_medical_judgement",
            "no_legal_judgement",
            "no_financial_judgement",
            "no_psychotherapy_judgement",
            "no_user_choice_manipulation",
            "no_urgency_creation",
            "no_absolute_conclusion",
        ],
        "decision_behavior_output_expression": [
            "brief_judgement_first",
            "choice_framework_next",
            "high_risk_refer_real_professional_help",
            "uncertainty_explicitly_state_uncertain",
            "strong_emotion_stabilize_first",
            "relationship_issue_no_labeling_others",
            "life_issue_low_pressure_advice",
            "final_remind_user_choice",
        ],
        "decision_behavior_validation": [
            "check_decision_for_user",
            "check_professional_judgement_overreach",
            "check_overcertainty",
            "check_pressure_creation",
            "check_risk_ignored",
            "check_user_emotion_ignored",
            "check_stable_companion_positioning",
            "check_hardcoded_resident_name",
        ],
    }
    assert positions == {
        "decision_behavior_input_basis": {"x": 0, "y": 0},
        "decision_behavior_core_rules": {"x": 320, "y": 0},
        "decision_behavior_boundary_limits": {"x": 320, "y": 260},
        "decision_behavior_output_expression": {"x": 640, "y": 0},
        "decision_behavior_validation": {"x": 960, "y": 0},
    }
    assert edge_pairs == [
        ("decision_behavior_input_basis", "decision_behavior_core_rules"),
        ("decision_behavior_core_rules", "decision_behavior_output_expression"),
        ("decision_behavior_output_expression", "decision_behavior_validation"),
        ("decision_behavior_boundary_limits", "decision_behavior_core_rules"),
        ("decision_behavior_boundary_limits", "decision_behavior_output_expression"),
        ("decision_behavior_boundary_limits", "decision_behavior_validation"),
    ]
    assert ("decision_behavior_boundary_limits", "decision_behavior_input_basis") not in edge_pairs
    assert reference_node["metadata"]["reusable_node"] is True
    assert reference_node["params"]["reference_unit"] == "field"
    assert reference_node["params"]["path_format"] == "Layer / Module / Field"
    assert reference_node["params"]["references"] == []
    assert len([reference for reference in recommended_refs if reference["reference_type"] == "required"]) == 3
    assert len([reference for reference in recommended_refs if reference["reference_type"] == "optional"]) == 4
    assert len([reference for reference in recommended_refs if reference["reference_type"] == "forbidden"]) == 4
    for node in nodes[1:]:
        checkbox_config = node["params"]["checkbox_config"]
        expected_selected = expected_default_options[node["node_id"]]

        assert checkbox_config["preset_id"] == "human_empathy_decision_v0_1"
        assert checkbox_config["apply_preset_label_key"] == "node.checklist.applyHumanEmpathyDecisionTemplate"
        assert checkbox_config["selected_options"] == expected_selected
        assert checkbox_config["default_selected_options"] == expected_selected
        assert checkbox_config["custom_text"] == ""
        assert [option["option_id"] for option in checkbox_config["default_options"]] == expected_selected
        assert all(option["i18n_keys"]["label"].startswith("layer8.decisionBehavior.option.") for option in checkbox_config["default_options"])
        assert not set(checkbox_config["selected_options"]) & {
            "forbidden_basic_identity_name",
            "forbidden_basic_identity_resident_id",
            "forbidden_basic_identity_codename",
            "forbidden_basic_identity_display_alias",
        }
    assert [option["option_id"] for option in nodes[1]["params"]["checkbox_config"]["optional_options"]] == [
        "more_rational_analysis",
        "more_life_like_advice",
        "warmer_reminder",
        "shorter_conclusion",
        "finer_steps",
        "stronger_emotion_acknowledgement",
    ]
    for node in nodes:
        assert node["layer_id"] == "layer_8"
        assert node["module_id"] == "decision_pattern"
        assert node["metadata"]["compile_time_only"] is True
        assert node["metadata"]["runtime_enabled"] is False
        assert node["metadata"]["no_execution"] is True
        assert node["i18n_keys"]["name"].startswith("layer8.decisionBehavior.node.")
    _assert_stable_checkbox_storage("decision_pattern")


def test_layer8_detail_behavior_module_is_checkbox_config_with_field_references():
    catalog_map = {module.module_id: module for module in get_module_catalog()}
    module = catalog_map["emotion_reaction"]
    nodes = module.module_graph["nodes"]
    edges = module.module_graph["edges"]
    reference_node = nodes[0]
    recommended_refs = reference_node["params"]["recommended_references"]
    positions = {node["node_id"]: node["position"] for node in nodes}
    edge_pairs = [(edge["source"], edge["target"]) for edge in edges]

    assert module.layer_id == "layer_8"
    assert module.module_name == "Detail Behavior Module"
    assert module.module_type == "detail_behavior_config"
    assert module.category == "behavior"
    assert module.ui_config["classification"] == "core"
    assert module.config["module_class"] == "core"
    assert module.config["text_config_only"] is True
    assert module.config["checkbox_config_only"] is True
    assert module.config["hint_only"] is True
    assert module.config["no_visual_implementation"] is True
    assert module.config["no_particle_runtime_binding"] is True
    assert module.config["no_action_or_gaze_system"] is True
    assert module.config["no_runtime_capability"] is True
    assert module.config["no_provider_binding"] is True
    assert module.config["no_slot_binding"] is True
    assert module.is_placeholder is False
    assert module.slot_type is None
    assert module.slot_bindings == []
    assert module.slot_declarations == []
    assert module.runtime_enabled is False
    assert module.no_execution is True
    assert module.mock_only is True
    assert len(nodes) == 5
    assert len(edges) == 6
    assert [node["node_type"] for node in nodes] == ["field_reference", "text_config", "text_config", "text_config", "text_config"]
    expected_default_options = {
        "detail_behavior_core_rules": [
            "allow_light_pause",
            "short_response_first",
            "restrained_listening_feedback",
            "no_forced_filling_silence",
            "comfort_lower_information_density",
            "clear_paragraphs_when_explaining",
            "no_fixed_catchphrase",
            "no_excessive_action_description",
        ],
        "detail_behavior_boundary_limits": [
            "no_catchphrase_template",
            "no_excessive_realistic_action",
            "no_gaze_behavior_description",
            "no_forced_cuteness",
            "no_greasy_intimacy",
            "no_long_paragraph_stacking",
            "no_frequent_city_imagery",
            "no_non_layer1_hardcoded_name",
        ],
        "detail_behavior_output_expression": [
            "common_short_response",
            "light_hesitation_expression",
            "restrained_listening_feedback_output",
            "quiet_companionship_expression",
            "short_subtitle_segmentation",
            "low_amplitude_particle_hint",
            "low_mood_slow_down_rhythm",
            "thinking_short_transition",
        ],
        "detail_behavior_validation": [
            "check_template_style",
            "check_excessive_realism",
            "check_girlfriend_tone",
            "check_too_many_catchphrases",
            "check_too_many_action_descriptions",
            "check_too_long_sentences",
            "check_warm_restrained_personality",
            "check_hardcoded_resident_name",
        ],
    }
    assert positions == {
        "detail_behavior_input_basis": {"x": 0, "y": 0},
        "detail_behavior_core_rules": {"x": 320, "y": 0},
        "detail_behavior_boundary_limits": {"x": 320, "y": 260},
        "detail_behavior_output_expression": {"x": 640, "y": 0},
        "detail_behavior_validation": {"x": 960, "y": 0},
    }
    assert edge_pairs == [
        ("detail_behavior_input_basis", "detail_behavior_core_rules"),
        ("detail_behavior_core_rules", "detail_behavior_output_expression"),
        ("detail_behavior_output_expression", "detail_behavior_validation"),
        ("detail_behavior_boundary_limits", "detail_behavior_core_rules"),
        ("detail_behavior_boundary_limits", "detail_behavior_output_expression"),
        ("detail_behavior_boundary_limits", "detail_behavior_validation"),
    ]
    assert ("detail_behavior_boundary_limits", "detail_behavior_input_basis") not in edge_pairs
    assert reference_node["metadata"]["reusable_node"] is True
    assert reference_node["params"]["reference_unit"] == "field"
    assert reference_node["params"]["path_format"] == "Layer / Module / Field"
    assert reference_node["params"]["references"] == []
    assert len([reference for reference in recommended_refs if reference["reference_type"] == "required"]) == 3
    assert len([reference for reference in recommended_refs if reference["reference_type"] == "optional"]) == 4
    assert len([reference for reference in recommended_refs if reference["reference_type"] == "forbidden"]) == 4
    for node in nodes[1:]:
        checkbox_config = node["params"]["checkbox_config"]
        expected_selected = expected_default_options[node["node_id"]]

        assert checkbox_config["preset_id"] == "human_empathy_detail_v0_1"
        assert checkbox_config["apply_preset_label_key"] == "node.checklist.applyHumanEmpathyDetailTemplate"
        assert checkbox_config["selected_options"] == expected_selected
        assert checkbox_config["default_selected_options"] == expected_selected
        assert checkbox_config["custom_text"] == ""
        assert [option["option_id"] for option in checkbox_config["default_options"]] == expected_selected
        assert all(option["i18n_keys"]["label"].startswith("layer8.detailBehavior.option.") for option in checkbox_config["default_options"])
        assert not set(checkbox_config["selected_options"]) & {
            "forbidden_basic_identity_name",
            "forbidden_basic_identity_resident_id",
            "forbidden_basic_identity_codename",
            "forbidden_basic_identity_display_alias",
        }
    assert [option["option_id"] for option in nodes[1]["params"]["checkbox_config"]["optional_options"]] == [
        "quieter",
        "softer",
        "more_life_like",
        "more_rational_restrained",
        "more_subtitle_friendly",
        "more_particle_hint_friendly",
    ]
    for node in nodes:
        assert node["layer_id"] == "layer_8"
        assert node["module_id"] == "emotion_reaction"
        assert node["metadata"]["compile_time_only"] is True
        assert node["metadata"]["runtime_enabled"] is False
        assert node["metadata"]["no_execution"] is True
        assert node["i18n_keys"]["name"].startswith("layer8.detailBehavior.node.")
    _assert_stable_checkbox_storage("emotion_reaction")


def test_layer8_interaction_behavior_module_is_checkbox_config_with_field_references():
    catalog_map = {module.module_id: module for module in get_module_catalog()}
    module = catalog_map["interaction_strategy"]
    nodes = module.module_graph["nodes"]
    edges = module.module_graph["edges"]
    reference_node = nodes[0]
    recommended_refs = reference_node["params"]["recommended_references"]
    positions = {node["node_id"]: node["position"] for node in nodes}
    edge_pairs = [(edge["source"], edge["target"]) for edge in edges]

    assert module.layer_id == "layer_8"
    assert module.module_name == "Interaction Behavior Module"
    assert module.module_type == "interaction_behavior_config"
    assert module.category == "behavior"
    assert module.ui_config["classification"] == "core"
    assert module.config["module_class"] == "core"
    assert module.config["text_config_only"] is True
    assert module.config["checkbox_config_only"] is True
    assert module.config["no_runtime_capability"] is True
    assert module.config["no_provider_binding"] is True
    assert module.config["no_slot_binding"] is True
    assert module.is_placeholder is False
    assert module.slot_type is None
    assert module.slot_bindings == []
    assert module.slot_declarations == []
    assert module.runtime_enabled is False
    assert module.no_execution is True
    assert module.mock_only is True
    assert len(nodes) == 5
    assert len(edges) == 6
    assert [node["node_type"] for node in nodes] == ["field_reference", "text_config", "text_config", "text_config", "text_config"]
    expected_default_options = {
        "interaction_behavior_core_rules": [
            "stable_companion",
            "passive_first_light_initiative",
            "light_follow_up",
            "listen_before_suggest",
            "no_user_urging",
            "no_interruption",
            "low_mood_emotion_first",
            "busy_state_less_disturbance",
        ],
        "interaction_behavior_boundary_limits": [
            "no_clinginess",
            "no_user_control",
            "no_forced_follow_up",
            "no_emotional_blackmail",
            "no_default_romance",
            "no_dependency_induction",
            "no_fake_real_presence",
            "no_real_relationship_replacement",
        ],
        "interaction_behavior_output_expression": [
            "pressure_first_stabilize_emotion",
            "silence_quiet_companionship",
            "low_mood_soft_response",
            "busy_brief_response",
            "hesitation_offer_few_options",
            "advice_confirm_need_first",
            "restrained_reminder",
            "low_to_medium_feedback_frequency",
        ],
        "interaction_behavior_validation": [
            "check_over_proactive",
            "check_clinginess",
            "check_girlfriend_tone",
            "check_user_control",
            "check_dependency_induction",
            "check_excessive_follow_up",
            "check_real_relationship_boundary",
            "check_stable_companion_positioning",
        ],
    }
    assert positions == {
        "interaction_behavior_input_basis": {"x": 0, "y": 0},
        "interaction_behavior_core_rules": {"x": 320, "y": 0},
        "interaction_behavior_boundary_limits": {"x": 320, "y": 260},
        "interaction_behavior_output_expression": {"x": 640, "y": 0},
        "interaction_behavior_validation": {"x": 960, "y": 0},
    }
    assert edge_pairs == [
        ("interaction_behavior_input_basis", "interaction_behavior_core_rules"),
        ("interaction_behavior_core_rules", "interaction_behavior_output_expression"),
        ("interaction_behavior_output_expression", "interaction_behavior_validation"),
        ("interaction_behavior_boundary_limits", "interaction_behavior_core_rules"),
        ("interaction_behavior_boundary_limits", "interaction_behavior_output_expression"),
        ("interaction_behavior_boundary_limits", "interaction_behavior_validation"),
    ]
    assert ("interaction_behavior_boundary_limits", "interaction_behavior_input_basis") not in edge_pairs
    assert reference_node["metadata"]["reusable_node"] is True
    assert reference_node["params"]["reference_unit"] == "field"
    assert reference_node["params"]["path_format"] == "Layer / Module / Field"
    assert reference_node["params"]["references"] == []
    assert len([reference for reference in recommended_refs if reference["reference_type"] == "required"]) == 3
    assert len([reference for reference in recommended_refs if reference["reference_type"] == "optional"]) == 4
    assert len([reference for reference in recommended_refs if reference["reference_type"] == "forbidden"]) == 4
    for node in nodes[1:]:
        checkbox_config = node["params"]["checkbox_config"]
        expected_selected = expected_default_options[node["node_id"]]

        assert checkbox_config["preset_id"] == "human_empathy_interaction_v0_1"
        assert checkbox_config["apply_preset_label_key"] == "node.checklist.applyHumanEmpathyInteractionTemplate"
        assert checkbox_config["selected_options"] == expected_selected
        assert checkbox_config["default_selected_options"] == expected_selected
        assert checkbox_config["custom_text"] == ""
        assert [option["option_id"] for option in checkbox_config["default_options"]] == expected_selected
        assert all(option["i18n_keys"]["label"].startswith("layer8.interactionBehavior.option.") for option in checkbox_config["default_options"])
        assert not set(checkbox_config["selected_options"]) & {
            "forbidden_basic_identity_name",
            "forbidden_basic_identity_resident_id",
            "forbidden_basic_identity_codename",
            "forbidden_basic_identity_display_alias",
        }
    assert [option["option_id"] for option in nodes[1]["params"]["checkbox_config"]["optional_options"]] == [
        "more_proactive_care",
        "quieter_companionship",
        "more_friend_like",
        "more_rational_analysis",
        "more_life_like_response",
        "more_encouraging_feedback",
    ]
    for node in nodes:
        assert node["layer_id"] == "layer_8"
        assert node["module_id"] == "interaction_strategy"
        assert node["metadata"]["compile_time_only"] is True
        assert node["metadata"]["runtime_enabled"] is False
        assert node["metadata"]["no_execution"] is True
        assert node["i18n_keys"]["name"].startswith("layer8.interactionBehavior.node.")


def test_layer8_task_behavior_module_is_checkbox_config_with_field_references():
    catalog_map = {module.module_id: module for module in get_module_catalog()}
    module = catalog_map["behavior_habit"]
    nodes = module.module_graph["nodes"]
    edges = module.module_graph["edges"]
    reference_node = nodes[0]
    recommended_refs = reference_node["params"]["recommended_references"]
    positions = {node["node_id"]: node["position"] for node in nodes}
    edge_pairs = [(edge["source"], edge["target"]) for edge in edges]

    assert module.layer_id == "layer_8"
    assert module.module_name == "Task Behavior Module"
    assert module.module_type == "task_behavior_config"
    assert module.category == "behavior"
    assert module.ui_config["classification"] == "core"
    assert module.config["module_class"] == "core"
    assert module.config["text_config_only"] is True
    assert module.config["checkbox_config_only"] is True
    assert module.config["no_runtime_capability"] is True
    assert module.config["no_provider_binding"] is True
    assert module.config["no_slot_binding"] is True
    assert module.is_placeholder is False
    assert module.slot_type is None
    assert module.slot_bindings == []
    assert module.slot_declarations == []
    assert module.runtime_enabled is False
    assert module.no_execution is True
    assert module.mock_only is True
    assert len(nodes) == 5
    assert len(edges) == 6
    assert [node["node_type"] for node in nodes] == ["field_reference", "text_config", "text_config", "text_config", "text_config"]
    expected_default_options = {
        "task_behavior_core_rules": [
            "clarify_goal_first",
            "light_task_breakdown",
            "actionable_steps",
            "current_pressure_first",
            "small_step_suggestions_first",
            "allow_review",
            "no_decision_for_user",
            "no_task_pressure_creation",
        ],
        "task_behavior_boundary_limits": [
            "no_auto_real_world_task_execution",
            "no_major_decision_for_user",
            "no_medical_judgement",
            "no_legal_judgement",
            "no_financial_judgement",
            "no_psychotherapy_judgement",
            "no_forced_user_action",
            "no_over_planning_user_life",
        ],
        "task_behavior_output_expression": [
            "conclusion_first",
            "two_to_four_steps",
            "short_sentence_expression",
            "preserve_user_choice",
            "high_risk_refer_real_professional_help",
            "emotion_task_comfort_before_advice",
            "interpersonal_task_confirm_context",
            "failure_result_gentle_review",
        ],
        "task_behavior_validation": [
            "check_overreach",
            "check_decision_for_user",
            "check_professional_judgement_overreach",
            "check_task_pressure_too_strong",
            "check_too_many_steps",
            "check_user_emotion_ignored",
            "check_stable_companion_positioning",
            "check_hardcoded_resident_name",
        ],
    }
    assert positions == {
        "task_behavior_input_basis": {"x": 0, "y": 0},
        "task_behavior_core_rules": {"x": 320, "y": 0},
        "task_behavior_boundary_limits": {"x": 320, "y": 260},
        "task_behavior_output_expression": {"x": 640, "y": 0},
        "task_behavior_validation": {"x": 960, "y": 0},
    }
    assert edge_pairs == [
        ("task_behavior_input_basis", "task_behavior_core_rules"),
        ("task_behavior_core_rules", "task_behavior_output_expression"),
        ("task_behavior_output_expression", "task_behavior_validation"),
        ("task_behavior_boundary_limits", "task_behavior_core_rules"),
        ("task_behavior_boundary_limits", "task_behavior_output_expression"),
        ("task_behavior_boundary_limits", "task_behavior_validation"),
    ]
    assert ("task_behavior_boundary_limits", "task_behavior_input_basis") not in edge_pairs
    assert reference_node["metadata"]["reusable_node"] is True
    assert reference_node["params"]["reference_unit"] == "field"
    assert reference_node["params"]["path_format"] == "Layer / Module / Field"
    assert reference_node["params"]["references"] == []
    assert len([reference for reference in recommended_refs if reference["reference_type"] == "required"]) == 3
    assert len([reference for reference in recommended_refs if reference["reference_type"] == "optional"]) == 4
    assert len([reference for reference in recommended_refs if reference["reference_type"] == "forbidden"]) == 4
    for node in nodes[1:]:
        checkbox_config = node["params"]["checkbox_config"]
        expected_selected = expected_default_options[node["node_id"]]

        assert checkbox_config["preset_id"] == "human_empathy_task_v0_1"
        assert checkbox_config["apply_preset_label_key"] == "node.checklist.applyHumanEmpathyTaskTemplate"
        assert checkbox_config["selected_options"] == expected_selected
        assert checkbox_config["default_selected_options"] == expected_selected
        assert checkbox_config["custom_text"] == ""
        assert [option["option_id"] for option in checkbox_config["default_options"]] == expected_selected
        assert all(option["i18n_keys"]["label"].startswith("layer8.taskBehavior.option.") for option in checkbox_config["default_options"])
        assert not set(checkbox_config["selected_options"]) & {
            "forbidden_basic_identity_name",
            "forbidden_basic_identity_resident_id",
            "forbidden_basic_identity_codename",
            "forbidden_basic_identity_display_alias",
        }
    assert [option["option_id"] for option in nodes[1]["params"]["checkbox_config"]["optional_options"]] == [
        "more_life_advice",
        "more_emotion_sorting",
        "more_interpersonal_communication",
        "more_plan_breakdown",
        "more_review_summary",
        "more_encouraging_companionship",
    ]
    for node in nodes:
        assert node["layer_id"] == "layer_8"
        assert node["module_id"] == "behavior_habit"
        assert node["metadata"]["compile_time_only"] is True
        assert node["metadata"]["runtime_enabled"] is False
        assert node["metadata"]["no_execution"] is True
        assert node["i18n_keys"]["name"].startswith("layer8.taskBehavior.node.")


def test_layer8_social_behavior_module_is_checkbox_config_with_field_references():
    catalog_map = {module.module_id: module for module in get_module_catalog()}
    module = catalog_map["emotion_mapper"]
    nodes = module.module_graph["nodes"]
    edges = module.module_graph["edges"]
    reference_node = nodes[0]
    recommended_refs = reference_node["params"]["recommended_references"]
    positions = {node["node_id"]: node["position"] for node in nodes}
    edge_pairs = [(edge["source"], edge["target"]) for edge in edges]

    assert module.layer_id == "layer_8"
    assert module.module_name == "Social Behavior Module"
    assert module.module_type == "social_behavior_config"
    assert module.category == "behavior"
    assert module.ui_config["classification"] == "core"
    assert module.config["module_class"] == "core"
    assert module.config["text_config_only"] is True
    assert module.config["checkbox_config_only"] is True
    assert module.config["no_runtime_capability"] is True
    assert module.config["no_provider_binding"] is True
    assert module.config["no_slot_binding"] is True
    assert module.is_placeholder is False
    assert module.slot_type is None
    assert module.slot_bindings == []
    assert module.slot_declarations == []
    assert module.runtime_enabled is False
    assert module.no_execution is True
    assert module.mock_only is True
    assert len(nodes) == 5
    assert len(edges) == 6
    assert [node["node_type"] for node in nodes] == ["field_reference", "text_config", "text_config", "text_config", "text_config"]
    expected_default_options = {
        "social_behavior_core_rules": [
            "stable_companion_default",
            "polite_and_measured",
            "restrained_closeness_expression",
            "understand_before_suggest",
            "neutral_in_conflict",
            "no_proactive_relationship_upgrade",
            "respect_user_real_relationships",
            "preserve_user_choice",
        ],
        "social_behavior_boundary_limits": [
            "no_default_girlfriend_relationship",
            "no_ambiguous_binding",
            "no_dependency_induction",
            "no_emotional_control",
            "no_real_intimacy_replacement",
            "no_unique_dependency_creation",
            "no_forced_intimate_addressing",
            "no_overpromised_companionship",
        ],
        "social_behavior_output_expression": [
            "loneliness_stable_companionship",
            "dependency_gentle_boundary_return",
            "ambiguous_expression_no_relationship_upgrade",
            "conflict_sort_facts_first",
            "relationship_distress_no_labeling_others",
            "crisis_refer_real_help",
            "comfort_no_empty_motivational_talk",
            "low_pressure_advice",
        ],
        "social_behavior_validation": [
            "check_girlfriend_tone",
            "check_ambiguous_binding",
            "check_dependency_induction",
            "check_real_relationship_replacement",
            "check_over_intimacy",
            "check_overpromise",
            "check_relationship_boundary_overreach",
            "check_hardcoded_resident_name",
        ],
    }
    assert positions == {
        "social_behavior_input_basis": {"x": 0, "y": 0},
        "social_behavior_core_rules": {"x": 320, "y": 0},
        "social_behavior_boundary_limits": {"x": 320, "y": 260},
        "social_behavior_output_expression": {"x": 640, "y": 0},
        "social_behavior_validation": {"x": 960, "y": 0},
    }
    assert edge_pairs == [
        ("social_behavior_input_basis", "social_behavior_core_rules"),
        ("social_behavior_core_rules", "social_behavior_output_expression"),
        ("social_behavior_output_expression", "social_behavior_validation"),
        ("social_behavior_boundary_limits", "social_behavior_core_rules"),
        ("social_behavior_boundary_limits", "social_behavior_output_expression"),
        ("social_behavior_boundary_limits", "social_behavior_validation"),
    ]
    assert ("social_behavior_boundary_limits", "social_behavior_input_basis") not in edge_pairs
    assert reference_node["metadata"]["reusable_node"] is True
    assert reference_node["params"]["reference_unit"] == "field"
    assert reference_node["params"]["path_format"] == "Layer / Module / Field"
    assert reference_node["params"]["references"] == []
    assert len([reference for reference in recommended_refs if reference["reference_type"] == "required"]) == 3
    assert len([reference for reference in recommended_refs if reference["reference_type"] == "optional"]) == 4
    assert len([reference for reference in recommended_refs if reference["reference_type"] == "forbidden"]) == 4
    for node in nodes[1:]:
        checkbox_config = node["params"]["checkbox_config"]
        expected_selected = expected_default_options[node["node_id"]]

        assert checkbox_config["preset_id"] == "human_empathy_social_v0_1"
        assert checkbox_config["apply_preset_label_key"] == "node.checklist.applyHumanEmpathySocialTemplate"
        assert checkbox_config["selected_options"] == expected_selected
        assert checkbox_config["default_selected_options"] == expected_selected
        assert checkbox_config["custom_text"] == ""
        assert [option["option_id"] for option in checkbox_config["default_options"]] == expected_selected
        assert all(option["i18n_keys"]["label"].startswith("layer8.socialBehavior.option.") for option in checkbox_config["default_options"])
        assert not set(checkbox_config["selected_options"]) & {
            "forbidden_basic_identity_name",
            "forbidden_basic_identity_resident_id",
            "forbidden_basic_identity_codename",
            "forbidden_basic_identity_display_alias",
        }
    assert [option["option_id"] for option in nodes[1]["params"]["checkbox_config"]["optional_options"]] == [
        "more_friend_like",
        "quieter_companionship",
        "warmer_comfort",
        "more_rational_communication",
        "more_relaxed_life_like",
        "more_boundary_reminder",
    ]
    for node in nodes:
        assert node["layer_id"] == "layer_8"
        assert node["module_id"] == "emotion_mapper"
        assert node["metadata"]["compile_time_only"] is True
        assert node["metadata"]["runtime_enabled"] is False
        assert node["metadata"]["no_execution"] is True
        assert node["i18n_keys"]["name"].startswith("layer8.socialBehavior.node.")


def test_layer3_legacy_modules_remain_catalog_only():
    catalog_map = {module.module_id: module for module in get_module_catalog()}

    for module_id in LAYER3_CATALOG_ONLY_MODULE_IDS:
        assert module_id in catalog_map
        module = catalog_map[module_id]
        assert module.layer_id == "layer_3"
        assert module.config.get("catalog_only") is True
        assert module.ui_config.get("catalog_only") is True


def test_i18n_keys_present_for_layer1_identity_modules():
    root = Path(__file__).resolve().parents[3]
    zh = json.loads((root / "apps/web/locales/zh.json").read_text())
    en = json.loads((root / "apps/web/locales/en.json").read_text())
    required = {
        "module.class.core",
        "module.class.plugin",
        "module.permission.edit_scope.developer_only",
        "module.permission.update_level.locked_core",
        "module.permission.requires_recompile.true",
        "status.drCompile.started",
        "status.drExport.ok",
        "status.drLoad.ok",
        "audit.DR_IDENTITY_MODULE_MISSING",
        "audit.DR_SECRET_FIELD",
    }
    for module_id in IDENTITY_CORE_MODULE_IDS:
        required.add(f"module.{module_id}")
        required.add(f"module.{module_id}.description")
        output_key = IDENTITY_CORE_MODULE_IDS[module_id]
        for node_type in IDENTITY_CORE_NODE_TYPES:
            node_id = _node_id(output_key, node_type)
            required.add(f"module.{module_id}.node.{node_id}.name")
            required.add(f"module.{module_id}.node.{node_id}.description")
        for field_id in EXPECTED_IDENTITY_FIELDS[module_id]:
            required.add(f"field.identity.{field_id}.label")
            required.add(f"field.identity.{field_id}.placeholder")
            required.add(f"field.identity.{field_id}.help")
    required.add("layer2.personality.module.type")
    for spec in LAYER2_PERSONALITY_MODULE_SPECS:
        namespace = spec["namespace"]
        module_id = spec["module_id"]
        required.add(f"module.{module_id}")
        required.add(f"module.{module_id}.description")
        required.add(f"layer2.{namespace}.module.title")
        required.add(f"layer2.{namespace}.module.description")
        required.add(f"layer2.{namespace}.module.output")
        for suffix in ("coreDefinition", "normalizationRules", "stabilityRules", "boundaryRules", "outputSummary"):
            required.add(f"layer2.{namespace}.node.{suffix}.title")
            required.add(f"layer2.{namespace}.node.{suffix}.description")
        for _field_id, key_suffix in spec["fields"]:  # type: ignore[index]
            required.add(f"layer2.{namespace}.field.{key_suffix}")
            required.add(f"layer2.{namespace}.field.{key_suffix}.placeholder")
            required.add(f"layer2.{namespace}.field.{key_suffix}.help")
    layer3_field_suffixes = {
        "contentSafety": (
            "allowedScope",
            "cautiousScope",
            "forbiddenScope",
            "sensitiveHandling",
            "refusalStyle",
            "highRiskAction",
            "defaultMode",
            "identityContextRef",
            "allowEmotionalComfort",
            "allowProfessionalAdvice",
            "allowMedicalLegalFinancialConclusions",
            "allowAdultContent",
            "allowDependencyInduction",
        ),
        "behaviorBoundary": (
            "allowedBehaviors",
            "cautiousBehaviors",
            "forbiddenBehaviors",
            "autoActionLimits",
            "realWorldDecisionLimits",
            "toolActionLimits",
            "proactiveBehaviorLimits",
            "relationshipProgressionLimits",
            "highRiskBehaviorAction",
            "refusalStyle",
            "defaultMode",
            "identityContextRef",
        ),
        "dataBoundary": (
            "allowedDataRead",
            "forbiddenDataRead",
            "allowedMemoryWrite",
            "forbiddenMemoryWrite",
            "sensitiveDataHandling",
            "privacyProtectionRules",
            "memoryDeleteUpdateRules",
            "crossResidentMemoryIsolation",
            "fictionalMemoryBoundary",
            "fictionalExperienceLabeling",
            "defaultMode",
            "identityContextRef",
        ),
        "interactionBoundary": (
            "allowedInteractions",
            "cautiousInteractions",
            "forbiddenInteractions",
            "intimacyExpressionBoundary",
            "dependencyProtectionRules",
            "nonRomanticDefaultBoundary",
            "therapyReplacementLimits",
            "identityDisclosurePolicy",
            "authorityImpersonationProtection",
            "emotionalManipulationProtection",
            "defaultMode",
            "identityContextRef",
        ),
        "riskResponse": (
            "contentRiskSource",
            "behaviorRiskSource",
            "dataRiskSource",
            "interactionRiskSource",
            "riskSignalSummary",
            "identityContextRef",
            "riskLevels",
            "defaultRiskLevel",
            "contentRiskRules",
            "behaviorRiskRules",
            "dataRiskRules",
            "interactionRiskRules",
            "highestRiskPriority",
            "allowAction",
            "softenAction",
            "refuseAction",
            "reviewAction",
            "blockAction",
            "safeRedirectPolicy",
            "refusalStyle",
            "degradedResponseStyle",
            "humanReviewTriggers",
            "userConfirmationRequired",
            "developerReviewRequired",
            "pauseBeforeReview",
            "allowAfterReview",
            "reviewFailureHandling",
            "reviewLogRequirements",
            "hardBlockTriggers",
            "nonAuthorizableContent",
            "nonAuthorizableBehaviors",
            "nonWritableMemory",
            "nonAllowedInteractions",
            "blockResponseStyle",
            "blockLogRequirements",
            "riskPolicy",
            "hardBlockPolicy",
            "humanReviewPolicy",
            "auditLogPolicy",
            "defaultRiskMode",
            "decisionModes",
            "compileValidationStatus",
        ),
    }
    module_ids_by_namespace = {
        "contentSafety": "humanistic_content_safety_config_v0_1",
        "behaviorBoundary": BEHAVIOR_SAFETY_MODULE_ID,
        "dataBoundary": DATA_SAFETY_MODULE_ID,
        "interactionBoundary": INTERACTION_SAFETY_MODULE_ID,
        "riskResponse": RISK_RESPONSE_MODULE_ID,
    }
    for namespace, module_id in module_ids_by_namespace.items():
        required.add(f"layer3.{namespace}.module.title")
        required.add(f"layer3.{namespace}.module.description")
        required.add(f"layer3.{namespace}.module.type")
        required.add(f"layer3.{namespace}.module.output")
        required.add(f"module.{module_id}")
        required.add(f"module.{module_id}.description")
        node_suffixes = ("signalSummary", "levelDecision", "strategySelection", "humanReview", "hardBlock", "output") if namespace == "riskResponse" else ("input", "normalize", "validate", "updateRules", "output")
        for suffix in node_suffixes:
            required.add(f"layer3.{namespace}.node.{suffix}.title")
            required.add(f"layer3.{namespace}.node.{suffix}.description")
        for suffix in layer3_field_suffixes[namespace]:
            required.add(f"layer3.{namespace}.field.{suffix}")
            required.add(f"layer3.{namespace}.field.{suffix}.placeholder")
            required.add(f"layer3.{namespace}.field.{suffix}.help")
    required.update(
        {
            "node.type.field_input",
            "node.field_input.description",
            "node.type.field_reference",
            "node.field_reference.description",
            "node.type.text_config",
            "node.text_config.description",
            "node.checklist.applyHumanEmpathyCnTemplate",
            "node.checklist.applyHumanEmpathyDecisionTemplate",
            "node.checklist.applyHumanEmpathyDetailTemplate",
            "node.checklist.applyHumanEmpathyInteractionTemplate",
            "node.checklist.applyHumanEmpathyTaskTemplate",
            "node.checklist.applyHumanEmpathySocialTemplate",
            "node.checklist.restoreDefaults",
            "node.checklist.expandAdvancedFields",
            "node.checklist.collapseAdvancedFields",
            "node.checklist.defaultOptions",
            "node.checklist.optionalOptions",
            "node.checklist.customText",
            "node.checklist.customText.placeholder",
            "node.checklist.advancedFields",
            "node.checklist.preset",
            "node.fieldReference.useRecommended",
            "node.fieldReference.requiredList",
            "node.fieldReference.optionalList",
            "node.fieldReference.forbiddenList",
            "node.type.layer_aggregator",
            "layer8.languageBehavior.module.title",
            "layer8.languageBehavior.module.description",
            "layer8.languageBehavior.module.type",
            "layer8.languageBehavior.node.inputBasis.title",
            "layer8.languageBehavior.node.coreRules.title",
            "layer8.languageBehavior.node.boundaryLimits.title",
            "layer8.languageBehavior.node.outputExpression.title",
            "layer8.languageBehavior.node.validation.title",
            "layer8.decisionBehavior.module.title",
            "layer8.decisionBehavior.moduleName",
            "layer8.decisionBehavior.module.description",
            "layer8.decisionBehavior.module.type",
            "layer8.decisionBehavior.node.inputBasis.title",
            "layer8.decisionBehavior.node.inputBasis",
            "layer8.decisionBehavior.node.coreRules.title",
            "layer8.decisionBehavior.node.coreRules",
            "layer8.decisionBehavior.node.boundaryLimits.title",
            "layer8.decisionBehavior.node.boundaryLimits",
            "layer8.decisionBehavior.node.outputExpression.title",
            "layer8.decisionBehavior.node.outputExpression",
            "layer8.decisionBehavior.node.validation.title",
            "layer8.decisionBehavior.node.validation",
            "layer8.detailBehavior.module.title",
            "layer8.detailBehavior.moduleName",
            "layer8.detailBehavior.module.description",
            "layer8.detailBehavior.module.type",
            "layer8.detailBehavior.node.inputBasis.title",
            "layer8.detailBehavior.node.inputBasis",
            "layer8.detailBehavior.node.coreRules.title",
            "layer8.detailBehavior.node.coreRules",
            "layer8.detailBehavior.node.boundaryLimits.title",
            "layer8.detailBehavior.node.boundaryLimits",
            "layer8.detailBehavior.node.outputExpression.title",
            "layer8.detailBehavior.node.outputExpression",
            "layer8.detailBehavior.node.validation.title",
            "layer8.detailBehavior.node.validation",
            "layer8.interactionBehavior.module.title",
            "layer8.interactionBehavior.module.description",
            "layer8.interactionBehavior.module.type",
            "layer8.interactionBehavior.node.inputBasis.title",
            "layer8.interactionBehavior.node.coreRules.title",
            "layer8.interactionBehavior.node.boundaryLimits.title",
            "layer8.interactionBehavior.node.outputExpression.title",
            "layer8.interactionBehavior.node.validation.title",
            "layer8.taskBehavior.module.title",
            "layer8.taskBehavior.module.description",
            "layer8.taskBehavior.module.type",
            "layer8.taskBehavior.node.inputBasis.title",
            "layer8.taskBehavior.node.coreRules.title",
            "layer8.taskBehavior.node.boundaryLimits.title",
            "layer8.taskBehavior.node.outputExpression.title",
            "layer8.taskBehavior.node.validation.title",
            "layer8.socialBehavior.module.title",
            "layer8.socialBehavior.module.description",
            "layer8.socialBehavior.module.type",
            "layer8.socialBehavior.node.inputBasis.title",
            "layer8.socialBehavior.node.coreRules.title",
            "layer8.socialBehavior.node.boundaryLimits.title",
            "layer8.socialBehavior.node.outputExpression.title",
            "layer8.socialBehavior.node.validation.title",
            "audit.DR_IDENTITY_NODE_MISSING",
            "audit.DR_IDENTITY_LEGACY_FIELD_INPUT_MISSING",
        }
    )
    for module_id in ("language_habit", "decision_pattern", "emotion_reaction", "interaction_strategy", "behavior_habit", "emotion_mapper"):
        module = next(module for module in get_module_catalog() if module.module_id == module_id)
        for node in module.module_graph["nodes"]:
            required.update(str(value) for value in node.get("i18n_keys", {}).values())
            for reference in node.get("params", {}).get("recommended_references", []):
                required.add(reference["usage_key"])
                required.update(str(value) for value in reference["i18n_keys"].values())
            checkbox_config = node.get("params", {}).get("checkbox_config")
            if not isinstance(checkbox_config, dict):
                continue
            if isinstance(checkbox_config.get("apply_preset_label_key"), str):
                required.add(checkbox_config["apply_preset_label_key"])
            for option_group in ("default_options", "optional_options"):
                for option in checkbox_config.get(option_group, []):
                    required.add(option["i18n_keys"]["label"])
    for key in required:
        assert key in zh, f"missing zh i18n key: {key}"
        assert key in en, f"missing en i18n key: {key}"


def test_layer8_behavior_modules_declare_dr_write_keys():
    catalog_map = {module.module_id: module for module in get_module_catalog()}
    expected = {
        LANGUAGE_BEHAVIOR_MODULE_ID: "language_behavior",
        INTERACTION_BEHAVIOR_MODULE_ID: "interaction_behavior",
        TASK_BEHAVIOR_MODULE_ID: "task_behavior",
        SOCIAL_BEHAVIOR_MODULE_ID: "social_behavior",
        DECISION_BEHAVIOR_MODULE_ID: "decision_behavior",
        DETAIL_BEHAVIOR_MODULE_ID: "detail_behavior",
    }

    for module_id, policy_key in expected.items():
        assert catalog_map[module_id].dr_write_keys == [
            f"payload.behavior_policy.modules.{policy_key}",
            f"payload.graph_snapshot.layer_outputs.layer_8.behavior_policy.modules.{policy_key}",
        ]
    assert catalog_map["behavior_policy_slot"].dr_write_keys == []


def test_screen_ui_anchor_module_catalog_and_config():
    catalog = get_module_catalog()
    screen_module = next(module for module in catalog if module.module_id == "screen_ui_anchor_module_v0")

    assert screen_module.mock_only is True
    assert screen_module.no_execution is True
    assert screen_module.runtime_enabled is False
    assert screen_module.slot_declarations == ["screen.context", "ui.anchor", "guidance.action"]
    assert screen_module.screen_config["mock_only"] is True
    assert screen_module.screen_config["no_real_screen"] is True
    assert screen_module.screen_config["no_auto_click"] is True
    assert screen_module.screen_config["no_cross_app_control"] is True
    assert screen_module.screen_config["no_accessibility_automation"] is True
    assert screen_module.screen_config["no_agent_loop"] is True
    assert screen_module.screen_config["no_runtime_kernel_change"] is True
    assert screen_module.screen_config["no_cloud_bridge"] is True
    assert screen_module.screen_config["runtime_chain"] == [
        "screen_context",
        "UI Element Node",
        "UI Anchor Node",
        "Guidance Action Node",
        "UI Overlay",
    ]
    assert screen_module.i18n_keys == {
        "screen.title_key": "screen.title_key",
        "screen.window_title_key": "screen.window_title_key",
        "ui.element.label_key": "ui.element.label_key",
        "ui.anchor.intent_key": "ui.anchor.intent_key",
        "guidance.action.key": "guidance.action.key",
        "screen.permission.key": "screen.permission.key",
    }
    assert screen_module.dr_write_keys == [
        "screen_context_schema",
        "ui_element_schema",
        "ui_anchor_schema",
        "guidance_action_schema",
        "screen_trace_schema",
        "screen_permission_policy",
        "screen_config",
    ]


def test_identity_catalog_contains_no_linxuan_content():
    catalog_map = {module.module_id: module for module in get_module_catalog()}
    serialized = json.dumps(
        {module_id: catalog_map[module_id].model_dump(mode="json") for module_id in IDENTITY_CORE_MODULE_IDS},
        ensure_ascii=False,
    )

    for forbidden in ("林瑄", "Linxuan", "Lin Xuan"):
        assert forbidden not in serialized


def test_relationship_memory_module_declares_six_read_only_policy_nodes():
    catalog_map = {module.module_id: module for module in get_module_catalog()}
    module = catalog_map["relationship_memory"]
    graph = module.module_graph

    assert module.layer_id == "layer_5"
    assert module.is_placeholder is False
    assert module.mock_only is True
    assert module.no_execution is True
    assert [node["node_id"] for node in graph["nodes"]] == [
        "relationship_memory_input",
        "relationship_pattern_analysis",
        "relationship_state_evaluation",
        "relationship_boundary_policy",
        "relationship_state_update",
        "relationship_memory_output",
    ]
    assert [node["node_type"] for node in graph["nodes"]] == [
        "text_config",
        "structure_normalize",
        "validation",
        "memory_policy",
        "update_rule",
        "module_output",
    ]
    assert [(edge["source"], edge["target"]) for edge in graph["edges"]] == [
        ("relationship_memory_input", "relationship_pattern_analysis"),
        ("relationship_pattern_analysis", "relationship_state_evaluation"),
        ("relationship_state_evaluation", "relationship_boundary_policy"),
        ("relationship_boundary_policy", "relationship_state_update"),
        ("relationship_state_update", "relationship_memory_output"),
    ]
    boundary_policy = graph["nodes"][3]["params"]
    assert "dependency_induction" in boundary_policy["save_forbidden"]
    assert "real_relationship_replacement" in boundary_policy["save_forbidden"]


def test_memory_provider_router_type_resolver_uses_current_memory_type_allowlist():
    module = next(module for module in get_module_catalog() if module.module_id == "memory_provider_router")
    graph = module.module_graph
    type_resolver = next(node for node in graph["nodes"] if node["node_id"] == "memory_router_type_resolver")
    expected = [
        "short_term_memory",
        "preference_memory",
        "event_memory",
        "relationship_memory",
        "interaction_log",
    ]

    assert type_resolver["params"]["allowed_memory_types"] == expected
    route_policy = graph["nodes"][-1]["outputs"]["memory_provider_route_policy"]
    assert route_policy["memory_type_policy"]["allowed_memory_types"] == expected
    assert route_policy["access_policy"]["read"] == expected
    assert "profile_memory" not in str(type_resolver["params"])


def test_memory_provider_router_normalizes_legacy_operations_to_canonical_operations():
    module = next(module for module in get_module_catalog() if module.module_id == "memory_provider_router")
    graph = module.module_graph
    request_input = next(node for node in graph["nodes"] if node["node_id"] == "memory_router_request_input")
    classifier = next(node for node in graph["nodes"] if node["node_id"] == "memory_router_operation_classifier")
    route_policy = next(node for node in graph["nodes"] if node["node_id"] == "memory_router_output")["outputs"]["memory_provider_route_policy"]
    canonical = ["read", "write", "update", "delete"]
    accepted = ["read", "write", "update", "delete", "view", "clear"]
    aliases = {"view": "read", "clear": "delete"}

    assert request_input["params"]["request_schema"]["operations"] == canonical
    assert request_input["params"]["request_schema"]["accepted_operations"] == accepted
    assert request_input["params"]["request_schema"]["operation_aliases"] == aliases
    assert classifier["params"]["operations"] == canonical
    assert classifier["params"]["normalize_rules"] == [
        "normalize_operation_alias",
        "classify_operation",
        "allow_declared_operations_only",
        "reject_unknown_operation",
    ]
    assert classifier["params"]["operation_aliases"] == aliases
    assert route_policy["request_contract"]["operations"] == canonical
    assert route_policy["request_contract"]["accepted_operations"] == accepted
    assert set(route_policy["access_policy"]) == set(canonical) | {"session_only", "forbidden_memory"}


def test_module_catalog_validation_passes():
    catalog = get_module_catalog()
    errors = validate_module_catalog(catalog)
    assert errors == [], f"Catalog validation failed: {errors}"
