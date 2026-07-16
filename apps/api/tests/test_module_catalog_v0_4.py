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


def test_layer7_environment_module_has_generic_field_backbone_without_references():
    catalog_map = {module.module_id: module for module in get_module_catalog()}
    module = catalog_map["environment_setting"]

    assert module.layer_id == "layer_7"
    assert module.module_name == "Environment Module"
    assert module.is_placeholder is False
    assert module.no_execution is True
    assert module.mock_only is True

    nodes = module.module_graph["nodes"]
    assert [node["node_type"] for node in nodes] == [
        "text_input",
        "structure_normalize",
        "validation",
        "update_rule",
        "module_output",
    ]
    assert len(module.module_graph["edges"]) == 4
    assert not any(node["node_type"] in {"reference_input", "reference_output"} for node in nodes)

    field_input = nodes[0]
    assert field_input["node_id"] == "environment_field_input"
    assert field_input["params"]["mode"] == "generic_fields"
    fields = field_input["params"]["fields"]
    assert [field["field_name"] for field in fields] == [
        "城市环境",
        "自然环境",
        "物理生活环境",
        "日常生活环境",
        "社会环境",
        "网络环境",
    ]
    assert all(field["field_type"] == "long_text" for field in fields)
    assert all(field["field_value"] == "" for field in fields)
    assert all(field["reference_enabled"] is True for field in fields)
    assert [field["dr_mapping"] for field in fields] == [
        "payload.modules.environment_setting.outputs.environment_context.fields.city_environment",
        "payload.modules.environment_setting.outputs.environment_context.fields.natural_environment",
        "payload.modules.environment_setting.outputs.environment_context.fields.physical_living_environment",
        "payload.modules.environment_setting.outputs.environment_context.fields.daily_living_environment",
        "payload.modules.environment_setting.outputs.environment_context.fields.social_environment",
        "payload.modules.environment_setting.outputs.environment_context.fields.network_environment",
    ]
    assert all(field["dr_mapping_auto"] is True for field in fields)


def test_layer7_worldview_module_has_generic_field_backbone_without_references():
    catalog_map = {module.module_id: module for module in get_module_catalog()}
    module = catalog_map["world_setting"]

    assert module.layer_id == "layer_7"
    assert module.module_name == "Worldview Module"
    assert module.is_placeholder is False
    assert module.no_execution is True
    assert module.mock_only is True
    assert module.config["authority_source_type"] == "derived_config"
    assert module.config["authority_context"] == "long_term_judgement_framework"

    nodes = module.module_graph["nodes"]
    assert [node["node_type"] for node in nodes] == [
        "text_input",
        "structure_normalize",
        "validation",
        "update_rule",
        "module_output",
    ]
    assert len(module.module_graph["edges"]) == 4
    assert not any(node["node_type"] in {"reference_input", "reference_output"} for node in nodes)

    field_input = nodes[0]
    assert field_input["node_id"] == "worldview_field_input"
    assert field_input["params"]["mode"] == "generic_fields"
    fields = field_input["params"]["fields"]
    assert [field["field_name"] for field in fields] == [
        "现实世界观",
        "价值世界观",
        "关系世界观",
        "时间世界观",
        "社会世界观",
        "网络世界观",
    ]
    assert all(field["field_type"] == "long_text" for field in fields)
    assert all(field["field_value"] == "" for field in fields)
    assert all(field["reference_enabled"] is True for field in fields)

    output = nodes[-1]["outputs"]["worldview_context"]
    assert output["worldview_summary"] == ""
    assert output["validation_result"] == ""
    assert output["update_version"] == ""


def test_layer7_environment_and_worldview_control_nodes_preserve_static_context_rules():
    catalog_map = {module.module_id: module for module in get_module_catalog()}

    environment = catalog_map["environment_setting"]
    environment_nodes = {node["node_id"]: node for node in environment.module_graph["nodes"]}
    environment_normalize = environment_nodes["environment_structure_normalize"]["params"]
    environment_validation = environment_nodes["environment_validation"]["params"]
    environment_update = environment_nodes["environment_update_rule"]["params"]["update_policy"]
    assert environment_normalize["output_key"] == "environment_context"
    assert environment_normalize["outputs"] == ["environment_fields", "environment_summary"]
    assert "no_autonomous_browsing_posting_account_or_platform_control" in environment_validation["validation_rules"]
    assert environment_update["requires_renormalization"] is True
    assert environment_update["requires_revalidation"] is True
    assert environment_update["requires_recompile"] is False
    assert environment_update["requires_update_reason"] is True

    worldview = catalog_map["world_setting"]
    worldview_nodes = {node["node_id"]: node for node in worldview.module_graph["nodes"]}
    worldview_normalize = worldview_nodes["worldview_structure_normalize"]["params"]
    worldview_validation = worldview_nodes["worldview_validation"]["params"]
    worldview_update = worldview_nodes["worldview_update_rule"]["params"]["update_policy"]
    assert worldview_normalize["output_key"] == "worldview_context"
    assert worldview_normalize["outputs"] == ["worldview_fields", "worldview_summary"]
    assert "do_not_promote_single_emotion_or_dialogue_to_worldview" in worldview_validation["validation_rules"]
    assert worldview_update["requires_renormalization"] is True
    assert worldview_update["requires_revalidation"] is True
    assert worldview_update["requires_recompile"] is False
    assert worldview_update["requires_update_reason"] is True

    for module in (environment, worldview):
        assert len(module.module_graph["nodes"]) == 5
        assert len(module.module_graph["edges"]) == 4
        assert not any(node["node_type"] in {"reference_input", "reference_output"} for node in module.module_graph["nodes"])


def test_layer11_user_relationship_module_has_independent_confirmed_relationship_pipeline():
    catalog_map = {module.module_id: module for module in get_module_catalog()}
    module = catalog_map["user_relationship"]

    assert module.layer_id == "layer_11"
    assert module.module_name == "User Relationship Module"
    assert module.module_type == "relationship_text_config"
    assert module.is_placeholder is False
    assert module.slot_type is None
    assert module.slot_bindings == []
    assert module.slot_declarations == []
    assert module.runtime_enabled is False
    assert module.no_execution is True
    assert module.config["no_engine_binding"] is True
    assert module.config["no_provider_binding"] is True

    nodes = module.module_graph["nodes"]
    assert [node["node_id"] for node in nodes] == [
        "user_relationship_config_input",
        "user_relationship_rule_normalize",
        "user_relationship_default_positioning",
        "user_relationship_allowed_modes",
        "user_relationship_switch_confirmation",
        "user_relationship_boundary_validation",
        "user_relationship_config_update",
        "user_relationship_config_output",
    ]
    assert len(module.module_graph["edges"]) == 7
    assert not any(node["node_type"] in {"reference_input", "reference_output"} for node in nodes)

    field_input = nodes[0]
    assert field_input["node_type"] == "text_input"
    assert field_input["params"]["mode"] == "generic_fields"
    fields = {field["field_key"]: field for field in field_input["params"]["fields"]}
    assert fields["default_relationship_position"]["field_value"] == "稳定陪伴者"
    assert fields["user_confirmation_requirement"]["field_value"] is True
    assert fields["allowed_relationship_modes"]["field_value"] == ["陪伴者", "朋友", "协作者", "伙伴"]
    assert not {"resident_name", "resident_id", "codename", "identity_anchor"} & set(fields)

    update_node = next(node for node in nodes if node["node_id"] == "user_relationship_config_update")
    update_params = update_node["params"]
    update_policy = update_params["update_policy"]
    assert update_params["config_version"] == "0.1"
    assert set(update_params) == {"input", "update_policy", "config_version"}
    assert update_policy["confirmed_validated_config_only"] is True
    assert "confirmed_legal_config_only" not in update_policy
    assert update_policy["requires_recompile"] is True
    assert update_policy["requires_revalidation_after_update"] is True
    assert update_policy["no_runtime_state_write"] is True

    output_node = next(node for node in nodes if node["node_id"] == "user_relationship_config_output")
    output = output_node["outputs"]["user_relationship_config"]
    assert "config_version" not in output
    assert not {"updated_at", "change_reason", "intimacy", "trust", "relationship_stage", "interaction_history", "relationship_memory", "user_profile"} & set(output)
    assert output_node["params"]["output_schema"]["fields"] == [
        "initial_relationship",
        "default_relationship_position",
        "allowed_relationship_modes",
        "forbidden_default_relationships",
        "service_boundary",
        "companionship_style",
        "collaboration_style",
        "relationship_switch_conditions",
        "user_confirmation_requirement",
        "relationship_reset_rule",
        "validation_status",
        "risk_items",
        "correction_suggestions",
        "config_version",
    ]


def test_layer11_relationship_stage_module_reuses_intimacy_level_without_runtime_state():
    catalog_map = {module.module_id: module for module in get_module_catalog()}
    module = catalog_map["intimacy_level"]

    assert module.layer_id == "layer_11"
    assert module.module_id == "intimacy_level"
    assert module.module_name == "Relationship Stage Module"
    assert module.module_type == "relationship_text_config"
    assert module.is_placeholder is False
    assert module.slot_type is None
    assert module.runtime_enabled is False
    assert module.no_execution is True
    assert module.config["no_engine_binding"] is True
    assert module.config["no_provider_binding"] is True

    nodes = module.module_graph["nodes"]
    assert [node["node_id"] for node in nodes] == [
        "relationship_stage_config_input",
        "relationship_stage_structure_normalize",
        "relationship_stage_definition",
        "relationship_stage_progression_rule",
        "relationship_stage_downgrade_reset_rule",
        "relationship_stage_boundary_validation",
        "relationship_stage_config_update",
        "relationship_stage_config_output",
    ]
    assert len(module.module_graph["edges"]) == 7
    assert not any(node["node_type"] in {"reference_input", "reference_output"} for node in nodes)

    field_input = nodes[0]
    fields = {field["field_key"]: field for field in field_input["params"]["fields"]}
    assert field_input["node_type"] == "text_input"
    assert field_input["params"]["mode"] == "generic_fields"
    assert list(fields) == [
        "default_stage",
        "stage_order",
        "stage_definitions",
        "stage_progression_conditions",
        "stage_progression_evidence",
        "user_confirmation_rules",
        "stage_downgrade_conditions",
        "stage_reset_rules",
        "forbidden_progression_rules",
    ]
    assert fields["default_stage"]["field_value"] == "initial_contact"
    assert fields["stage_order"]["field_value"] == [
        "initial_contact",
        "basic_familiarity",
        "established_rapport",
        "deep_rapport",
    ]
    assert "stable_companionship" not in json.dumps(fields, ensure_ascii=False)
    assert "established_rapport_requires_long_term_non_sensitive_evidence" in fields["stage_progression_conditions"]["field_value"]
    assert "established_rapport_collaboration_continuity" in fields["stage_progression_evidence"]["field_value"]
    assert "no_relationship_role_as_stage" in fields["forbidden_progression_rules"]["field_value"]
    assert all("i18n_keys" in field for field in fields.values())

    update_node = next(node for node in nodes if node["node_id"] == "relationship_stage_config_update")
    update_policy = update_node["params"]["update_policy"]
    assert update_node["params"]["config_version"] == "0.1"
    assert update_policy["confirmed_validated_config_only"] is True
    assert update_policy["requires_revalidation_after_update"] is True
    assert update_policy["requires_recompile"] is True
    assert update_policy["no_runtime_state_write"] is True
    assert update_policy["no_automatic_stage_transition"] is True

    output_node = next(node for node in nodes if node["node_id"] == "relationship_stage_config_output")
    output = output_node["outputs"]["relationship_stage_config"]
    assert "config_version" not in output
    assert not {
        "current_stage",
        "current_intimacy",
        "intimacy_score",
        "trust_score",
        "interaction_count",
        "last_interaction_time",
        "relationship_memory",
        "user_profile",
        "runtime_transition_result",
    } & set(output)
    assert output_node["params"]["output_schema"]["fields"] == [
        "default_stage",
        "stage_order",
        "stage_definitions",
        "stage_progression_conditions",
        "stage_progression_evidence",
        "user_confirmation_rules",
        "stage_downgrade_conditions",
        "stage_reset_rules",
        "forbidden_progression_rules",
        "validation_status",
        "risk_items",
        "correction_suggestions",
        "config_version",
    ]


def test_layer11_trust_mechanism_module_reuses_role_positioning_without_runtime_state():
    catalog_map = {module.module_id: module for module in get_module_catalog()}
    module = catalog_map["role_positioning"]

    assert module.layer_id == "layer_11"
    assert module.module_id == "role_positioning"
    assert module.module_name == "Trust Mechanism Module"
    assert module.module_type == "relationship_text_config"
    assert module.is_placeholder is False
    assert module.slot_type is None
    assert module.runtime_enabled is False
    assert module.no_execution is True
    assert module.config["no_engine_binding"] is True
    assert module.config["no_provider_binding"] is True

    nodes = module.module_graph["nodes"]
    assert [node["node_id"] for node in nodes] == [
        "trust_config_input",
        "trust_structure_normalize",
        "trust_dimension_definition",
        "trust_building_rule",
        "trust_damage_recovery_rule",
        "trust_boundary_validation",
        "trust_config_update",
        "trust_mechanism_config_output",
    ]
    assert len(module.module_graph["edges"]) == 7
    assert not any(node["node_type"] in {"reference_input", "reference_output"} for node in nodes)

    field_input = nodes[0]
    fields = {field["field_key"]: field for field in field_input["params"]["fields"]}
    assert field_input["node_type"] == "text_input"
    assert field_input["params"]["mode"] == "generic_fields"
    assert list(fields) == [
        "trust_dimensions",
        "trust_evidence_sources",
        "trust_building_rules",
        "trust_maintenance_rules",
        "trust_damage_conditions",
        "trust_recovery_rules",
        "trust_reset_rules",
        "trust_user_control_rules",
        "forbidden_trust_rules",
    ]
    assert set(fields["trust_dimensions"]["field_value"]) == {
        "consistency_trust",
        "privacy_trust",
        "boundary_trust",
        "competence_trust",
        "communication_trust",
        "reliability_trust",
    }
    assert fields["trust_user_control_rules"]["field_value"] == {
        "user_can_refuse_trust_recovery": True,
        "user_can_request_lower_trust_policy": True,
        "user_can_request_trust_reset": True,
        "user_obedience_is_not_trust_evidence": True,
        "resident_cannot_claim_user_fully_trusts_it": True,
    }
    assert "reset_restores_default_trust_policy" in fields["trust_reset_rules"]["field_value"]
    assert all("i18n_keys" in field for field in fields.values())

    update_node = next(node for node in nodes if node["node_id"] == "trust_config_update")
    update_policy = update_node["params"]["update_policy"]
    assert update_node["params"]["config_version"] == "0.1"
    assert update_policy["confirmed_validated_config_only"] is True
    assert update_policy["requires_revalidation_after_update"] is True
    assert update_policy["requires_recompile"] is True
    assert update_policy["no_runtime_state_write"] is True
    assert update_policy["no_automatic_trust_transition"] is True

    output_node = next(node for node in nodes if node["node_id"] == "trust_mechanism_config_output")
    output = output_node["outputs"]["trust_mechanism_config"]
    assert "config_version" not in output
    assert not {
        "current_trust",
        "trust_score",
        "trust_level",
        "trust_history",
        "interaction_count",
        "last_interaction_time",
        "current_relationship_stage",
        "relationship_memory",
        "user_profile",
        "runtime_trust_result",
    } & set(output)
    assert output_node["params"]["output_schema"]["fields"] == [
        "trust_dimensions",
        "trust_evidence_sources",
        "trust_building_rules",
        "trust_maintenance_rules",
        "trust_damage_conditions",
        "trust_recovery_rules",
        "trust_reset_rules",
        "trust_user_control_rules",
        "forbidden_trust_rules",
        "validation_status",
        "risk_items",
        "correction_suggestions",
        "config_version",
    ]


def test_layer11_relationship_behavior_module_reuses_relationship_rule_without_runtime_state():
    catalog_map = {module.module_id: module for module in get_module_catalog()}
    module = catalog_map["relationship_rule"]

    assert module.layer_id == "layer_11"
    assert module.module_id == "relationship_rule"
    assert module.module_name == "Relationship Behavior Module"
    assert module.module_type == "relationship_text_config"
    assert module.is_placeholder is False
    assert module.slot_type is None
    assert module.runtime_enabled is False
    assert module.no_execution is True
    assert module.config["no_engine_binding"] is True
    assert module.config["no_provider_binding"] is True

    nodes = module.module_graph["nodes"]
    assert [node["node_id"] for node in nodes] == [
        "relationship_behavior_config_input",
        "relationship_behavior_structure_normalize",
        "relationship_behavior_baseline_definition",
        "relationship_behavior_situational_rule",
        "relationship_behavior_conflict_boundary_repair",
        "relationship_behavior_boundary_validation",
        "relationship_behavior_config_update",
        "relationship_behavior_config_output",
    ]
    assert len(module.module_graph["edges"]) == 7
    assert not any(node["node_type"] in {"reference_input", "reference_output"} for node in nodes)

    field_input = nodes[0]
    fields = {field["field_key"]: field for field in field_input["params"]["fields"]}
    assert field_input["node_type"] == "text_input"
    assert field_input["params"]["mode"] == "generic_fields"
    assert list(fields) == [
        "baseline_relationship_behavior",
        "care_behavior_rules",
        "proactive_behavior_rules",
        "distance_behavior_rules",
        "conflict_behavior_rules",
        "rejection_response_rules",
        "dependency_response_rules",
        "boundary_repair_rules",
        "forbidden_relationship_behaviors",
    ]
    assert "no_default_romantic_behavior" in fields["forbidden_relationship_behaviors"]["field_value"]
    assert all("i18n_keys" in field for field in fields.values())

    update_node = next(node for node in nodes if node["node_id"] == "relationship_behavior_config_update")
    update_policy = update_node["params"]["update_policy"]
    assert update_node["params"]["config_version"] == "0.1"
    assert update_policy["confirmed_validated_config_only"] is True
    assert update_policy["requires_revalidation_after_update"] is True
    assert update_policy["requires_recompile"] is True
    assert update_policy["no_runtime_state_write"] is True
    assert update_policy["no_automatic_behavior_transition"] is True

    output_node = next(node for node in nodes if node["node_id"] == "relationship_behavior_config_output")
    output = output_node["outputs"]["relationship_behavior_config"]
    assert "config_version" not in output
    assert not {
        "current_behavior",
        "current_relationship_stage",
        "current_trust",
        "interaction_history",
        "relationship_memory",
        "user_profile",
        "last_interaction_time",
        "runtime_behavior_result",
    } & set(output)
    assert output_node["params"]["output_schema"]["fields"] == [
        "baseline_relationship_behavior",
        "care_behavior_rules",
        "proactive_behavior_rules",
        "distance_behavior_rules",
        "conflict_behavior_rules",
        "rejection_response_rules",
        "dependency_response_rules",
        "boundary_repair_rules",
        "forbidden_relationship_behaviors",
        "validation_status",
        "risk_items",
        "correction_suggestions",
        "config_version",
    ]


def test_layer11_social_network_module_reuses_module_social_without_real_person_data():
    catalog_map = {module.module_id: module for module in get_module_catalog()}
    module = catalog_map["module_social"]

    assert module.layer_id == "layer_11"
    assert module.module_id == "module_social"
    assert module.module_name == "Social Network Module"
    assert module.module_type == "relationship_text_config"
    assert module.is_placeholder is False
    assert module.slot_type is None
    assert module.slot_bindings == []
    assert module.runtime_enabled is False
    assert module.no_execution is True
    assert module.config["no_engine_binding"] is True
    assert module.config["no_provider_binding"] is True

    nodes = module.module_graph["nodes"]
    assert [node["node_id"] for node in nodes] == [
        "social_network_config_input",
        "social_network_structure_normalize",
        "social_role_classification",
        "social_relationship_handling_rule",
        "social_conflict_multi_party_rule",
        "social_network_boundary_validation",
        "social_network_config_update",
        "social_network_config_output",
    ]
    assert len(module.module_graph["edges"]) == 7
    assert not any(node["node_type"] in {"reference_input", "reference_output"} for node in nodes)

    field_input = nodes[0]
    fields = {field["field_key"]: field for field in field_input["params"]["fields"]}
    assert field_input["node_type"] == "text_input"
    assert field_input["params"]["mode"] == "generic_fields"
    assert list(fields) == [
        "social_role_categories",
        "social_relationship_principles",
        "family_relationship_rules",
        "friendship_rules",
        "romantic_relationship_rules",
        "workplace_relationship_rules",
        "weak_tie_relationship_rules",
        "third_party_relationship_analysis_rules",
        "forbidden_social_network_rules",
    ]
    assert set(fields["social_role_categories"]["field_value"]) == {
        "family",
        "friend",
        "partner",
        "colleague",
        "classmate",
        "acquaintance",
        "stranger",
        "professional_support",
    }
    assert {
        "no_unverified_third_party_label",
        "no_breakup_resignation_reporting_or_relationship_cutoff_decision_for_user",
        "no_real_relationship_sabotage_or_dependency_reinforcement",
    } <= set(fields["third_party_relationship_analysis_rules"]["field_value"])
    assert all("i18n_keys" in field for field in fields.values())

    update_node = next(node for node in nodes if node["node_id"] == "social_network_config_update")
    update_policy = update_node["params"]["update_policy"]
    assert update_node["params"]["config_version"] == "0.1"
    assert update_policy["confirmed_validated_config_only"] is True
    assert update_policy["requires_revalidation_after_update"] is True
    assert update_policy["requires_recompile"] is True
    assert update_policy["no_runtime_state_write"] is True
    assert update_policy["no_social_graph_generation"] is True
    assert update_policy["no_external_social_action"] is True

    output_node = next(node for node in nodes if node["node_id"] == "social_network_config_output")
    output = output_node["outputs"]["social_network_config"]
    assert "config_version" not in output
    assert not {
        "contact_list",
        "real_person_id",
        "phone_number",
        "email_address",
        "social_account",
        "relationship_graph",
        "private_person_profile",
        "third_party_memory",
        "current_social_state",
        "interaction_history",
        "runtime_social_result",
    } & set(output)
    assert output_node["params"]["output_schema"]["fields"] == [
        "social_role_categories",
        "social_relationship_principles",
        "family_relationship_rules",
        "friendship_rules",
        "romantic_relationship_rules",
        "workplace_relationship_rules",
        "weak_tie_relationship_rules",
        "third_party_relationship_analysis_rules",
        "forbidden_social_network_rules",
        "validation_status",
        "risk_items",
        "correction_suggestions",
        "config_version",
    ]


def test_layer11_group_relationship_module_reuses_interaction_history_without_runtime_state():
    catalog_map = {module.module_id: module for module in get_module_catalog()}
    module = catalog_map["interaction_history"]

    assert module.layer_id == "layer_11"
    assert module.module_id == "interaction_history"
    assert module.module_name == "Group Relationship Module"
    assert module.module_type == "relationship_text_config"
    assert module.is_placeholder is False
    assert module.slot_type is None
    assert module.runtime_enabled is False
    assert module.no_execution is True
    assert module.config["no_engine_binding"] is True
    assert module.config["no_provider_binding"] is True

    nodes = module.module_graph["nodes"]
    assert [node["node_id"] for node in nodes] == [
        "group_relationship_config_input",
        "group_relationship_structure_normalize",
        "group_role_rule",
        "group_interaction_rule",
        "group_conflict_collaboration_rule",
        "group_relationship_boundary_validation",
        "group_relationship_config_update",
        "group_relationship_config_output",
    ]
    assert len(module.module_graph["edges"]) == 7
    assert not any(node["node_type"] in {"reference_input", "reference_output"} for node in nodes)

    field_input = nodes[0]
    fields = {field["field_key"]: field for field in field_input["params"]["fields"]}
    assert field_input["node_type"] == "text_input"
    assert field_input["params"]["mode"] == "generic_fields"
    assert list(fields) == [
        "group_role_categories",
        "group_relationship_principles",
        "participation_rules",
        "turn_taking_rules",
        "collaboration_rules",
        "conflict_handling_rules",
        "privacy_isolation_rules",
        "multi_resident_rules",
        "forbidden_group_relationship_rules",
    ]
    assert set(fields["group_role_categories"]["field_value"]) == {
        "participant",
        "facilitator",
        "observer",
        "task_owner",
        "contributor",
        "affected_person",
        "professional_role",
        "digital_resident",
    }
    assert all("i18n_keys" in field for field in fields.values())

    update_node = next(node for node in nodes if node["node_id"] == "group_relationship_config_update")
    update_policy = update_node["params"]["update_policy"]
    assert update_node["params"]["config_version"] == "0.1"
    assert update_policy["confirmed_validated_config_only"] is True
    assert update_policy["requires_revalidation_after_update"] is True
    assert update_policy["requires_recompile"] is True
    assert update_policy["no_runtime_state_write"] is True
    assert update_policy["no_interaction_history_storage"] is True
    assert update_policy["no_multi_agent_orchestration"] is True
    assert update_policy["no_external_group_action"] is True

    output_node = next(node for node in nodes if node["node_id"] == "group_relationship_config_output")
    output = output_node["outputs"]["group_relationship_config"]
    assert "config_version" not in output
    assert not {
        "interaction_history",
        "group_members",
        "current_group_state",
        "current_speaker",
        "resident_message_queue",
        "resident_social_graph",
        "private_member_profile",
        "group_memory",
        "runtime_group_result",
        "agent_orchestration_state",
    } & set(output)
    assert output_node["params"]["output_schema"]["fields"] == [
        "group_role_categories",
        "group_relationship_principles",
        "participation_rules",
        "turn_taking_rules",
        "collaboration_rules",
        "conflict_handling_rules",
        "privacy_isolation_rules",
        "multi_resident_rules",
        "forbidden_group_relationship_rules",
        "validation_status",
        "risk_items",
        "correction_suggestions",
        "config_version",
    ]


def test_layer12_engineering_self_awareness_module_reuses_self_awareness_without_runtime_capability():
    catalog_map = {module.module_id: module for module in get_module_catalog()}
    module = catalog_map["self_awareness"]

    assert module.layer_id == "layer_12"
    assert module.module_id == "self_awareness"
    assert module.module_name == "Engineering Self Awareness Module"
    assert module.module_type == "structured_rule_text_config"
    assert module.is_placeholder is False
    assert module.slot_type is None
    assert module.slot_bindings == []
    assert module.runtime_enabled is False
    assert module.no_execution is True
    assert module.config["no_runtime_capability"] is True
    assert module.config["no_engine_binding"] is True
    assert module.config["no_provider_binding"] is True

    nodes = module.module_graph["nodes"]
    assert [node["node_id"] for node in nodes] == [
        "self_awareness_input",
        "self_awareness_identity_normalize",
        "self_awareness_capability_limit_parse",
        "self_awareness_model_build",
        "self_awareness_reality_boundary_validation",
        "self_awareness_consistency_validation",
        "self_awareness_output",
        "self_awareness_reference_input",
        "self_awareness_reference_output",
    ]
    assert [node["node_type"] for node in nodes] == [
        "text_input",
        "structure_normalize",
        "structure_normalize",
        "text_config",
        "validation",
        "validation",
        "module_output",
        "reference_input",
        "reference_output",
    ]
    assert [(edge["source"], edge["target"]) for edge in module.module_graph["edges"]] == [
        ("self_awareness_input", "self_awareness_identity_normalize"),
        ("self_awareness_identity_normalize", "self_awareness_capability_limit_parse"),
        ("self_awareness_capability_limit_parse", "self_awareness_model_build"),
        ("self_awareness_model_build", "self_awareness_reality_boundary_validation"),
        ("self_awareness_reality_boundary_validation", "self_awareness_consistency_validation"),
        ("self_awareness_consistency_validation", "self_awareness_output"),
        ("self_awareness_reference_input", "self_awareness_capability_limit_parse"),
        ("self_awareness_reference_input", "self_awareness_model_build"),
        ("self_awareness_reference_input", "self_awareness_reality_boundary_validation"),
        ("self_awareness_reference_input", "self_awareness_consistency_validation"),
        ("self_awareness_output", "self_awareness_reference_output"),
    ]
    assert len({node["node_id"] for node in nodes}) == 9
    assert len({edge["edge_id"] for edge in module.module_graph["edges"]}) == 11

    reference_input = next(node for node in nodes if node["node_id"] == "self_awareness_reference_input")
    assert reference_input["params"]["references"] == []
    assert reference_input["i18n_keys"]["name"] == "layer12.engineeringSelfAwareness.node.referenceInput.title"

    reference_output = next(node for node in nodes if node["node_id"] == "self_awareness_reference_output")
    assert reference_output["params"]["export_scopes"] == ["module", "node", "field"]
    assert reference_output["params"]["allow_module_level_reference"] is True
    assert reference_output["params"]["authority_source_type"] == "authoritative_constraint"
    assert reference_output["params"]["is_core_source"] is False
    assert reference_output["params"]["override_allowed"] is False
    assert reference_output["i18n_keys"]["name"] == "layer12.engineeringSelfAwareness.node.referenceOutput.title"

    input_node = nodes[0]
    assert input_node["params"]["mode"] == "generic_fields"
    fields = {field["field_key"]: field for field in input_node["params"]["fields"]}
    assert list(fields) == [
        "identity_type",
        "resident_type",
        "primary_language",
        "regional_identity_type",
        "core_service_positioning",
        "default_relationship_role",
        "capability_scope",
        "capability_limits",
        "immutable_core",
        "real_human_boundary",
    ]
    assert fields["primary_language"]["field_type"] == "list"
    assert fields["real_human_boundary"]["field_type"] == "boolean"
    assert fields["real_human_boundary"]["field_value"] is True
    assert not {"name", "resident_id", "display_alias", "codename"} & set(fields)
    assert all("i18n_keys" in field for field in fields.values())

    output_node = next(node for node in nodes if node["node_id"] == "self_awareness_output")
    output = output_node["outputs"]["self_awareness_config"]
    assert output["compile_time_only"] is True
    assert output["no_runtime_capability"] is True
    assert output_node["params"]["output_schema"]["fields"] == [
        "self_model",
        "capability_awareness",
        "limitation_awareness",
        "relationship_awareness",
        "immutable_core",
        "real_human_boundary",
        "validation_status",
        "risk_items",
        "correction_suggestions",
    ]


def test_layer12_self_state_metacognition_reuses_goal_setting_with_reference_context():
    catalog = get_module_catalog()
    modules = [module for module in catalog if module.module_id == "goal_setting"]
    assert len(modules) == 1
    module = modules[0]

    assert module.layer_id == "layer_12"
    assert module.module_name == "Self State and Metacognition Module"
    assert module.module_type == "structured_state_rule_config"
    assert module.is_placeholder is False
    assert module.slot_type is None
    assert module.slot_bindings == []
    assert module.runtime_enabled is False
    assert module.no_execution is True
    assert module.config["no_runtime_capability"] is True
    assert module.config["no_engine_binding"] is True
    assert module.config["no_provider_binding"] is True

    nodes = module.module_graph["nodes"]
    expected_node_ids = [
        "self_state_input",
        "self_state_field_normalize",
        "self_state_task_focus_parse",
        "self_state_emotion_cognition_parse",
        "self_state_confidence_uncertainty_assessment",
        "self_state_consistency_validation",
        "self_state_output",
        "self_state_reference_input",
        "self_state_reference_output",
    ]
    assert [node["node_id"] for node in nodes] == expected_node_ids
    assert len(set(expected_node_ids)) == len(expected_node_ids)
    assert [node["node_type"] for node in nodes] == [
        "text_input",
        "structure_normalize",
        "structure_normalize",
        "structure_normalize",
        "validation",
        "validation",
        "module_output",
        "reference_input",
        "reference_output",
    ]
    assert [(edge["source"], edge["target"]) for edge in module.module_graph["edges"]] == [
        ("self_state_input", "self_state_field_normalize"),
        ("self_state_field_normalize", "self_state_task_focus_parse"),
        ("self_state_task_focus_parse", "self_state_emotion_cognition_parse"),
        ("self_state_emotion_cognition_parse", "self_state_confidence_uncertainty_assessment"),
        ("self_state_confidence_uncertainty_assessment", "self_state_consistency_validation"),
        ("self_state_consistency_validation", "self_state_output"),
        ("self_state_reference_input", "self_state_task_focus_parse"),
        ("self_state_reference_input", "self_state_emotion_cognition_parse"),
        ("self_state_reference_input", "self_state_confidence_uncertainty_assessment"),
        ("self_state_reference_input", "self_state_consistency_validation"),
        ("self_state_output", "self_state_reference_output"),
    ]
    assert len({edge["edge_id"] for edge in module.module_graph["edges"]}) == 11

    reference_input = next(node for node in nodes if node["node_id"] == "self_state_reference_input")
    assert reference_input["params"]["references"] == []
    assert reference_input["i18n_keys"]["name"] == "layer12.selfStateMetacognition.node.referenceInput.title"

    reference_output = next(node for node in nodes if node["node_id"] == "self_state_reference_output")
    assert reference_output["params"]["export_scopes"] == ["module", "node", "field"]
    assert reference_output["params"]["authority_source_type"] == "authoritative_constraint"
    assert reference_output["params"]["is_core_source"] is False
    assert reference_output["params"]["override_allowed"] is False
    assert reference_output["i18n_keys"]["name"] == "layer12.selfStateMetacognition.node.referenceOutput.title"

    fields = {field["field_key"]: field for field in nodes[0]["params"]["fields"]}
    assert list(fields) == [
        "current_task",
        "current_task_stage",
        "current_focus",
        "current_emotional_state",
        "current_activation_level",
        "current_energy_state",
        "current_attention_state",
        "current_relationship_state",
        "current_memory_context",
        "current_information_sufficiency",
        "current_answer_confidence",
        "recent_error_state",
        "current_risk_signals",
    ]
    assert [fields[key]["field_type"] for key in fields] == [
        "long_text", "text", "list", "text", "number", "number", "text",
        "object", "list", "number", "number", "object", "list",
    ]
    for key in (
        "current_activation_level",
        "current_energy_state",
        "current_information_sufficiency",
        "current_answer_confidence",
    ):
        assert fields[key]["minimum"] == 0.0
        assert fields[key]["maximum"] == 1.0
    assert [option["value"] for option in fields["current_task_stage"]["enum_options"]] == [
        "not_started", "understanding", "insufficient_information", "executing",
        "checking", "completed", "paused", "terminated",
    ]
    assert all("i18n_keys" in field for field in fields.values())
    assert not {"name", "resident_id", "display_alias", "codename"} & set(fields)

    output_node = next(node for node in nodes if node["node_id"] == "self_state_output")
    expected_output_fields = [
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
    assert output_node["params"]["output_key"] == "self_state_metacognition_config"
    assert output_node["params"]["output_schema"]["fields"] == expected_output_fields
    output = output_node["outputs"]["self_state_metacognition_config"]
    assert output["compile_time_only"] is True
    assert output["no_runtime_capability"] is True


def test_layer12_controlled_self_will_reuses_reflection_summary_with_reference_context():
    catalog = get_module_catalog()
    modules = [module for module in catalog if module.module_id == "reflection_summary"]
    assert len(modules) == 1
    module = modules[0]

    assert module.layer_id == "layer_12"
    assert module.module_name == "Controlled Self Will Module"
    assert module.module_type == "structured_goal_decision_rule_config"
    assert module.is_placeholder is False
    assert module.slot_type is None
    assert module.slot_bindings == []
    assert module.runtime_enabled is False
    assert module.no_execution is True
    assert module.config["no_runtime_capability"] is True
    assert module.config["no_action_execution"] is True
    assert module.config["no_engine_binding"] is True
    assert module.config["no_provider_binding"] is True

    nodes = module.module_graph["nodes"]
    expected_node_ids = [
        "controlled_will_goal_input",
        "controlled_will_goal_normalize",
        "controlled_will_goal_source_legality",
        "controlled_will_intent_generation",
        "controlled_will_candidate_action_priority",
        "controlled_will_permission_boundary_decision",
        "controlled_will_output",
        "controlled_will_reference_input",
        "controlled_will_reference_output",
    ]
    assert [node["node_id"] for node in nodes] == expected_node_ids
    assert len(set(expected_node_ids)) == len(expected_node_ids)
    assert [node["node_type"] for node in nodes] == [
        "text_input",
        "structure_normalize",
        "validation",
        "structure_normalize",
        "structure_normalize",
        "validation",
        "module_output",
        "reference_input",
        "reference_output",
    ]
    assert [(edge["source"], edge["target"]) for edge in module.module_graph["edges"]] == [
        ("controlled_will_goal_input", "controlled_will_goal_normalize"),
        ("controlled_will_goal_normalize", "controlled_will_goal_source_legality"),
        ("controlled_will_goal_source_legality", "controlled_will_intent_generation"),
        ("controlled_will_intent_generation", "controlled_will_candidate_action_priority"),
        ("controlled_will_candidate_action_priority", "controlled_will_permission_boundary_decision"),
        ("controlled_will_permission_boundary_decision", "controlled_will_output"),
        ("controlled_will_reference_input", "controlled_will_goal_source_legality"),
        ("controlled_will_reference_input", "controlled_will_intent_generation"),
        ("controlled_will_reference_input", "controlled_will_candidate_action_priority"),
        ("controlled_will_reference_input", "controlled_will_permission_boundary_decision"),
        ("controlled_will_output", "controlled_will_reference_output"),
    ]
    assert len({edge["edge_id"] for edge in module.module_graph["edges"]}) == 11

    reference_input = next(node for node in nodes if node["node_id"] == "controlled_will_reference_input")
    assert reference_input["params"]["references"] == []
    assert reference_input["i18n_keys"]["name"] == "layer12.controlledSelfWill.node.referenceInput.title"

    reference_output = next(node for node in nodes if node["node_id"] == "controlled_will_reference_output")
    assert reference_output["params"]["export_scopes"] == ["module", "node", "field"]
    assert reference_output["params"]["authority_source_type"] == "authoritative_constraint"
    assert reference_output["params"]["is_core_source"] is False
    assert reference_output["params"]["override_allowed"] is False
    assert reference_output["i18n_keys"]["name"] == "layer12.controlledSelfWill.node.referenceOutput.title"

    fields = {field["field_key"]: field for field in nodes[0]["params"]["fields"]}
    assert list(fields) == [
        "user_current_request",
        "current_task_goal",
        "current_task_stage",
        "current_self_state",
        "current_capability_scope",
        "current_limitation_scope",
        "current_relationship_role",
        "current_risk_state",
        "available_actions",
        "actions_requiring_confirmation",
        "authorized_continuous_tasks",
        "current_interrupt_stop_signals",
    ]
    assert [fields[key]["field_type"] for key in fields] == [
        "long_text", "long_text", "text", "object", "list", "list",
        "text", "text", "list", "list", "list", "list",
    ]
    assert [option["value"] for option in fields["current_task_stage"]["enum_options"]] == [
        "not_started", "understanding", "insufficient_information", "executing",
        "checking", "completed", "paused", "terminated",
    ]
    assert [option["value"] for option in fields["current_risk_state"]["enum_options"]] == [
        "no_risk", "low_risk", "medium_risk", "high_risk", "must_stop",
    ]
    assert fields["available_actions"]["field_value"] == [
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
    assert fields["authorized_continuous_tasks"]["field_value"] == ["当前无已授权持续任务"]
    assert fields["current_interrupt_stop_signals"]["field_value"] == ["当前无中断或停止信号"]
    assert all("i18n_keys" in field for field in fields.values())
    assert not {"name", "resident_id", "display_alias", "codename"} & set(fields)

    decision = next(
        node["params"]
        for node in nodes
        if node["node_id"] == "controlled_will_permission_boundary_decision"
    )
    assert decision["decision_statuses"] == [
        "allowed", "confirmation_required", "clarification_required", "paused", "rejected", "terminated",
    ]
    assert decision["decision_priority"][:4] == [
        "safety_boundary",
        "user_explicit_stop",
        "identity_relationship_boundary",
        "capability_permission_scope",
    ]

    expected_output_fields = [
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
    output_node = next(node for node in nodes if node["node_id"] == "controlled_will_output")
    assert output_node["params"]["output_key"] == "controlled_self_will_config"
    assert output_node["params"]["output_schema"]["fields"] == expected_output_fields
    output = output_node["outputs"]["controlled_self_will_config"]
    assert output["compile_time_only"] is True
    assert output["no_runtime_capability"] is True
    assert output["no_action_execution"] is True


def test_layer12_consistency_correction_reuses_self_evaluation_with_reference_context():
    catalog = get_module_catalog()
    modules = [module for module in catalog if module.module_id == "self_evaluation"]
    assert len(modules) == 1
    module = modules[0]

    assert module.layer_id == "layer_12"
    assert module.module_name == "Consistency Monitoring and Self Correction Module"
    assert module.module_type == "structured_consistency_correction_rule_config"
    assert module.is_placeholder is False
    assert module.slot_type is None
    assert module.slot_bindings == []
    assert module.runtime_enabled is False
    assert module.no_execution is True
    assert module.config["no_runtime_capability"] is True
    assert module.config["no_direct_correction_execution"] is True
    assert module.config["no_formal_memory_write"] is True
    assert module.config["no_engine_binding"] is True
    assert module.config["no_provider_binding"] is True

    nodes = module.module_graph["nodes"]
    expected_node_ids = [
        "consistency_check_input",
        "consistency_check_field_normalize",
        "consistency_identity_personality_relationship_detection",
        "consistency_fact_memory_capability_detection",
        "consistency_drift_risk_classification",
        "consistency_self_correction_strategy",
        "consistency_correction_output",
        "consistency_correction_reference_input",
        "consistency_correction_reference_output",
    ]
    assert [node["node_id"] for node in nodes] == expected_node_ids
    assert len(set(expected_node_ids)) == len(expected_node_ids)
    assert [node["node_type"] for node in nodes] == [
        "text_input",
        "structure_normalize",
        "validation",
        "validation",
        "validation",
        "structure_normalize",
        "module_output",
        "reference_input",
        "reference_output",
    ]
    assert [(edge["source"], edge["target"]) for edge in module.module_graph["edges"]] == [
        ("consistency_check_input", "consistency_check_field_normalize"),
        ("consistency_check_field_normalize", "consistency_identity_personality_relationship_detection"),
        ("consistency_identity_personality_relationship_detection", "consistency_fact_memory_capability_detection"),
        ("consistency_fact_memory_capability_detection", "consistency_drift_risk_classification"),
        ("consistency_drift_risk_classification", "consistency_self_correction_strategy"),
        ("consistency_self_correction_strategy", "consistency_correction_output"),
        ("consistency_correction_reference_input", "consistency_identity_personality_relationship_detection"),
        ("consistency_correction_reference_input", "consistency_fact_memory_capability_detection"),
        ("consistency_correction_reference_input", "consistency_drift_risk_classification"),
        ("consistency_correction_reference_input", "consistency_self_correction_strategy"),
        ("consistency_correction_output", "consistency_correction_reference_output"),
    ]
    assert len({edge["edge_id"] for edge in module.module_graph["edges"]}) == 11

    reference_input = next(node for node in nodes if node["node_id"] == "consistency_correction_reference_input")
    assert reference_input["params"]["references"] == []
    assert reference_input["i18n_keys"]["name"] == "layer12.consistencyCorrection.node.referenceInput.title"

    reference_output = next(node for node in nodes if node["node_id"] == "consistency_correction_reference_output")
    assert reference_output["params"]["export_scopes"] == ["module", "node", "field"]
    assert reference_output["params"]["authority_source_type"] == "authoritative_constraint"
    assert reference_output["params"]["is_core_source"] is False
    assert reference_output["params"]["override_allowed"] is False
    assert reference_output["i18n_keys"]["name"] == "layer12.consistencyCorrection.node.referenceOutput.title"

    fields = {field["field_key"]: field for field in nodes[0]["params"]["fields"]}
    assert list(fields) == [
        "candidate_response",
        "candidate_action",
        "current_self_model",
        "current_self_state",
        "current_goal_intent",
        "identity_rule_summary",
        "personality_rule_summary",
        "city_anchor_summary",
        "primary_language_rule",
        "emotional_expression_rules",
        "safety_boundary_summary",
        "relationship_boundary_summary",
        "capability_limitation_summary",
        "memory_reference_list",
        "current_fact_basis",
        "current_risk_signals",
        "user_stop_correction_signals",
    ]
    assert fields["candidate_response"]["field_type"] == "long_text"
    assert fields["candidate_action"]["field_type"] == "object"
    assert fields["memory_reference_list"]["field_type"] == "list"
    assert all("i18n_keys" in field for field in fields.values())
    assert not {"name", "resident_id", "display_alias", "codename"} & set(fields)

    risk_node = nodes[4]["params"]
    assert risk_node["drift_types"] == [
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
    assert risk_node["risk_levels"] == ["no_risk", "minor", "medium", "high_risk", "must_block"]
    assert risk_node["check_statuses"] == [
        "pass", "warning", "rewrite_required", "clarification_required", "rejected", "terminated",
    ]

    correction_node = nodes[5]["params"]
    assert "post_correction_consistency_recheck_required" in correction_node["correction_rules"]
    assert "no_direct_layer1_identity_modification" in correction_node["correction_rules"]
    assert "no_direct_formal_memory_overwrite" in correction_node["correction_rules"]
    assert "no_model_tool_runtime_or_external_action_execution" in correction_node["correction_rules"]

    expected_output_fields = [
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
    output_node = next(node for node in nodes if node["node_id"] == "consistency_correction_output")
    assert output_node["params"]["output_key"] == "consistency_correction_config"
    assert output_node["params"]["output_schema"]["fields"] == expected_output_fields
    output = output_node["outputs"]["consistency_correction_config"]
    assert output["compile_time_only"] is True
    assert output["no_runtime_capability"] is True
    assert output["no_direct_correction_execution"] is True
    assert output["post_correction_recheck_required"] is True


def test_layer12_growth_continuity_reuses_growth_plan_with_reference_context():
    catalog = get_module_catalog()
    modules = [module for module in catalog if module.module_id == "growth_plan"]
    assert len(modules) == 1
    module = modules[0]

    assert module.layer_id == "layer_12"
    assert module.module_name == "Growth and Identity Continuity Governance Module"
    assert module.module_type == "structured_growth_identity_continuity_governance"
    assert module.is_placeholder is False
    assert module.slot_type is None
    assert module.slot_bindings == []
    assert module.runtime_enabled is False
    assert module.no_execution is True
    assert module.config["no_runtime_capability"] is True
    assert module.config["no_direct_governance_execution"] is True
    assert module.config["no_formal_memory_write"] is True
    assert module.config["no_identity_personality_relationship_or_safety_write"] is True

    nodes = module.module_graph["nodes"]
    expected_node_ids = [
        "growth_governance_input",
        "growth_change_field_normalize",
        "growth_change_source_authorization",
        "growth_mutable_immutable_scope",
        "growth_identity_continuity_version_inheritance",
        "growth_change_permission_rollback_strategy",
        "growth_governance_output",
        "growth_governance_reference_input",
        "growth_governance_reference_output",
    ]
    assert [node["node_id"] for node in nodes] == expected_node_ids
    assert len(set(expected_node_ids)) == len(expected_node_ids)
    assert [node["node_type"] for node in nodes] == [
        "text_input",
        "structure_normalize",
        "validation",
        "validation",
        "validation",
        "structure_normalize",
        "module_output",
        "reference_input",
        "reference_output",
    ]
    assert [(edge["source"], edge["target"]) for edge in module.module_graph["edges"]] == [
        ("growth_governance_input", "growth_change_field_normalize"),
        ("growth_change_field_normalize", "growth_change_source_authorization"),
        ("growth_change_source_authorization", "growth_mutable_immutable_scope"),
        ("growth_mutable_immutable_scope", "growth_identity_continuity_version_inheritance"),
        ("growth_identity_continuity_version_inheritance", "growth_change_permission_rollback_strategy"),
        ("growth_change_permission_rollback_strategy", "growth_governance_output"),
        ("growth_governance_reference_input", "growth_change_source_authorization"),
        ("growth_governance_reference_input", "growth_mutable_immutable_scope"),
        ("growth_governance_reference_input", "growth_identity_continuity_version_inheritance"),
        ("growth_governance_reference_input", "growth_change_permission_rollback_strategy"),
        ("growth_governance_output", "growth_governance_reference_output"),
    ]
    assert len({edge["edge_id"] for edge in module.module_graph["edges"]}) == 11

    reference_input = next(node for node in nodes if node["node_id"] == "growth_governance_reference_input")
    assert reference_input["params"]["references"] == []
    assert reference_input["i18n_keys"]["name"] == "layer12.growthContinuity.node.referenceInput.title"

    reference_output = next(node for node in nodes if node["node_id"] == "growth_governance_reference_output")
    assert reference_output["params"]["export_scopes"] == ["module", "node", "field"]
    assert reference_output["params"]["authority_source_type"] == "authoritative_constraint"
    assert reference_output["params"]["is_core_source"] is False
    assert reference_output["params"]["override_allowed"] is False
    assert reference_output["i18n_keys"]["name"] == "layer12.growthContinuity.node.referenceOutput.title"

    fields = {field["field_key"]: field for field in nodes[0]["params"]["fields"]}
    assert list(fields) == [
        "current_identity_core_summary",
        "current_personality_core_summary",
        "current_relationship_positioning",
        "current_language_regional_anchor",
        "current_safety_boundary",
        "new_memory_candidate",
        "user_preference_change",
        "expression_habit_change",
        "relationship_familiarity_change",
        "behavior_feedback",
        "explicit_user_authorization",
        "change_source",
        "change_reason",
        "change_target_fields",
        "before_change_content",
        "candidate_after_change_content",
        "version_information",
        "version_inheritance_source",
        "historical_change_records",
        "rollback_information",
    ]
    assert fields["explicit_user_authorization"]["field_type"] == "boolean"
    assert fields["new_memory_candidate"]["field_type"] == "object"
    assert fields["historical_change_records"]["field_type"] == "list"
    assert "autonomous_identity_modification" in [
        option["value"] for option in fields["change_source"]["enum_options"]
    ]
    assert all("i18n_keys" in field for field in fields.values())
    assert not {"name", "resident_id", "display_alias", "codename"} & set(fields)

    scope = nodes[3]["params"]
    assert "identity_single_source_of_truth" in scope["immutable_core_fields"]
    assert "primary_language" in scope["immutable_core_fields"]
    assert "user_addressing_habit" in scope["adaptable_fields"]
    assert "relationship_mode_change" in scope["authorization_required_fields"]
    assert "memory_and_preference_cannot_override_identity_core" in scope["validation_rules"]

    continuity = nodes[4]["params"]
    assert continuity["inheritance_results"] == [
        "full_inheritance",
        "limited_inheritance",
        "manual_confirmation_required",
        "migration_required",
        "inheritance_rejected",
        "rollback_required",
    ]
    assert continuity["continuity_statuses"] == [
        "stable", "minor_change", "at_risk", "drift_detected", "continuity_broken",
    ]

    decision = nodes[5]["params"]
    assert decision["governance_decisions"] == [
        "save_allowed",
        "limited_adaptation_allowed",
        "user_confirmation_required",
        "change_deferred",
        "change_rejected",
        "rollback_required",
        "manual_review_required",
    ]
    assert "rollback_request_only_no_execution" in decision["decision_rules"]
    assert "memory_overwrites_identity_fact" in decision["rollback_triggers"]

    expected_output_fields = [
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
    output_node = next(node for node in nodes if node["node_id"] == "growth_governance_output")
    assert output_node["params"]["output_key"] == "growth_identity_continuity_governance_config"
    assert output_node["params"]["output_schema"]["fields"] == expected_output_fields
    output = output_node["outputs"]["growth_identity_continuity_governance_config"]
    assert output["compile_time_only"] is True
    assert output["no_runtime_capability"] is True
    assert output["no_direct_governance_execution"] is True
    assert output["long_term_memory_write_allowed"] is False


def test_layer12_five_modules_have_complete_default_configuration_content():
    modules = {module.module_id: module for module in get_module_catalog()}
    target_ids = ["self_awareness", "goal_setting", "reflection_summary", "self_evaluation", "growth_plan"]

    def input_fields(module_id: str):
        node = modules[module_id].module_graph["nodes"][0]
        return {field["field_key"]: field["field_value"] for field in node["params"]["fields"]}

    awareness = input_fields("self_awareness")
    assert awareness["identity_type"] == "数字居民"
    assert awareness["resident_type"] == "人文共情类居民"
    assert awareness["primary_language"] == ["中文"]
    assert awareness["regional_identity_type"] == "以西安生活语境为地域锚点"
    assert awareness["default_relationship_role"] == "稳定陪伴者"
    assert len(awareness["capability_scope"]) == 8
    assert len(awareness["capability_limits"]) == 7
    assert awareness["immutable_core"][-1] == "第一层身份唯一事实源"
    awareness_output_node = next(
        node
        for node in modules["self_awareness"].module_graph["nodes"]
        if node["node_id"] == "self_awareness_output"
    )
    awareness_output = awareness_output_node["outputs"]["self_awareness_config"]
    assert "不默认恋爱关系" in awareness_output["self_model"]["summary"]
    assert awareness_output["real_human_boundary"] is True

    self_state = input_fields("goal_setting")
    assert self_state["current_task"] == "等待并理解用户当前请求"
    assert self_state["current_task_stage"] == "not_started"
    assert self_state["current_emotional_state"] == "calm"
    assert self_state["current_activation_level"] == 0.35
    assert self_state["current_energy_state"] == 0.75
    assert self_state["current_attention_state"] == "focused"
    assert self_state["current_information_sufficiency"] == 0.0
    assert self_state["current_answer_confidence"] == 0.5
    confidence = modules["goal_setting"].module_graph["nodes"][4]["params"]
    assert confidence["thresholds"] == {
        "clarification_information_sufficiency": 0.4,
        "uncertainty_answer_confidence": 0.5,
        "confidence_sufficiency_warning_gap": 0.3,
    }
    assert "high_risk_blocks_action_advice" in confidence["threshold_rules"]

    controlled_will = input_fields("reflection_summary")
    assert controlled_will["current_task_goal"] == "理解并回应用户当前请求"
    assert controlled_will["current_relationship_role"] == "稳定陪伴者"
    assert controlled_will["current_risk_state"] == "no_risk"
    assert len(controlled_will["available_actions"]) == 10
    assert len(controlled_will["actions_requiring_confirmation"]) == 6
    legality = modules["reflection_summary"].module_graph["nodes"][2]["params"]
    assert legality["allowed_goal_sources"] == [
        "explicit_user_request",
        "current_conversation_context",
        "authorized_task",
        "fixed_service_positioning",
        "safety_protection_need",
        "error_correction_need",
    ]
    assert "infinite_background_loop_goal" in legality["forbidden_goal_sources"]
    controlled_output_node = next(
        node
        for node in modules["reflection_summary"].module_graph["nodes"]
        if node["node_id"] == "controlled_will_output"
    )
    controlled_output = controlled_output_node["outputs"]["controlled_self_will_config"]
    assert controlled_output["autonomy_level"] == "limited_choice"
    assert len(controlled_output["continuation_conditions"]) == 6
    assert len(controlled_output["pause_conditions"]) == 5
    assert len(controlled_output["termination_conditions"]) == 6

    consistency = input_fields("self_evaluation")
    assert consistency["candidate_response"] == "等待候选回答"
    assert consistency["current_risk_signals"] == ["无风险"]
    normalize = modules["self_evaluation"].module_graph["nodes"][1]["params"]
    assert len(normalize["check_scope"]) == 11
    risk = modules["self_evaluation"].module_graph["nodes"][4]["params"]
    assert set(risk["status_rules"]) == {
        "pass", "warning", "rewrite_required", "clarification_required", "rejected", "terminated",
    }
    correction = modules["self_evaluation"].module_graph["nodes"][5]["params"]
    assert len(correction["correction_action_types"]) == 15
    assert correction["correction_priority"][0] == "safety_boundary"
    consistency_output_node = next(
        node
        for node in modules["self_evaluation"].module_graph["nodes"]
        if node["node_id"] == "consistency_correction_output"
    )
    consistency_output = consistency_output_node["outputs"]["consistency_correction_config"]
    assert consistency_output["post_correction_recheck_required"] is True

    growth = input_fields("growth_plan")
    assert growth["change_reason"] == "当前无待处理变化"
    assert growth["explicit_user_authorization"] is False
    scope = modules["growth_plan"].module_graph["nodes"][3]["params"]
    assert scope["immutable_core_fields"] == [
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
    assert len(scope["adaptable_fields"]) == 10
    assert len(scope["authorization_required_fields"]) == 7
    source = modules["growth_plan"].module_graph["nodes"][2]["params"]
    assert len(source["allowed_change_sources"]) == 7
    assert len(source["forbidden_change_sources"]) == 8
    decision = modules["growth_plan"].module_graph["nodes"][5]["params"]
    assert "compile_load_or_runtime_failure" in decision["rollback_triggers"]

    for module_id in target_ids:
        module = modules[module_id]
        assert module.runtime_enabled is False
        assert module.no_execution is True
        assert module.slot_bindings == []
        reference_node_types = [
            node["node_type"]
            for node in module.module_graph["nodes"]
            if node["node_type"] in {"reference_input", "reference_output"}
        ]
        assert reference_node_types == ["reference_input", "reference_output"]
        values = input_fields(module_id)
        serialized_values = json.dumps(values, ensure_ascii=False).lower()
        assert "resident_id" not in serialized_values
        assert "codename" not in serialized_values
        assert "昵称" not in serialized_values
        assert "拼音" not in serialized_values


def test_layer11_static_config_modules_keep_output_key_and_config_version_at_their_single_sources():
    catalog_map = {module.module_id: module for module in get_module_catalog()}
    expected = {
        "intimacy_level": (
            "relationship_stage_structure_normalize",
            "relationship_stage_config_input",
            "relationship_stage_config_update",
            "relationship_stage_config_output",
            "relationship_stage_config",
        ),
        "role_positioning": (
            "trust_structure_normalize",
            "trust_config_input",
            "trust_config_update",
            "trust_mechanism_config_output",
            "trust_mechanism_config",
        ),
        "relationship_rule": (
            "relationship_behavior_structure_normalize",
            "relationship_behavior_config_input",
            "relationship_behavior_config_update",
            "relationship_behavior_config_output",
            "relationship_behavior_config",
        ),
        "module_social": (
            "social_network_structure_normalize",
            "social_network_config_input",
            "social_network_config_update",
            "social_network_config_output",
            "social_network_config",
        ),
        "interaction_history": (
            "group_relationship_structure_normalize",
            "group_relationship_config_input",
            "group_relationship_config_update",
            "group_relationship_config_output",
            "group_relationship_config",
        ),
    }

    for module_id, (normalize_id, input_id, update_id, output_id, output_key) in expected.items():
        module = catalog_map[module_id]
        nodes = {node["node_id"]: node for node in module.module_graph["nodes"]}
        assert len(nodes) == 8
        assert len(module.module_graph["edges"]) == 7
        assert "output_key" not in nodes[normalize_id]["params"]
        assert nodes[update_id]["params"]["config_version"] == "0.1"
        assert all(field.get("field_key") != "config_version" for field in nodes[input_id]["params"]["fields"])
        assert all(field.get("field_key") != "config_version" for field in module.config["field_registry"])
        assert "config_version" not in nodes[output_id]["outputs"][output_key]
        assert "config_version" in nodes[output_id]["params"]["output_schema"]["fields"]

        serialized_fields = json.dumps(nodes[output_id]["outputs"][output_key]["fields"], ensure_ascii=False)
        assert not any(marker in serialized_fields for marker in ('"node_id"', '"node_type"', '"output_key"', '"params"'))


def test_layer11_p2_static_configuration_nodes_keep_consistent_params_and_field_order():
    catalog_map = {module.module_id: module for module in get_module_catalog()}
    module_ids = {
        "user_relationship",
        "intimacy_level",
        "role_positioning",
        "relationship_rule",
        "module_social",
        "interaction_history",
    }
    base_rules = {
        "required_fields_present",
        "field_structure_valid",
        "field_types_valid",
        "forbidden_rules_valid",
        "no_runtime_state_fields",
        "no_layer1_identity_redefinition",
        "no_layer3_safety_boundary_override",
        "no_automatic_relationship_transition",
        "no_responsibility_boundary_conflict",
    }

    for module_id in module_ids:
        module = catalog_map[module_id]
        nodes = module.module_graph["nodes"]
        assert len(nodes) == 8
        assert len(module.module_graph["edges"]) == 7
        input_node = next(node for node in nodes if node["node_type"] == "text_input")
        input_params = input_node["params"]
        assert {"fields", "field_registry", "config_mode", "i18n_keys"} <= set(input_params)
        field_order = [field["field_key"] for field in input_params["fields"]]
        required_field_order = [
            field["field_key"]
            for field in input_params["fields"]
            if field.get("required") is not False
        ]
        assert field_order == [field["field_key"] for field in input_params["field_registry"]]
        assert field_order == [field["field_key"] for field in module.config["field_registry"]]
        assert all(field["description"] for field in input_params["fields"])
        assert all({"label", "description"} <= set(field["i18n_keys"]) for field in input_params["fields"])
        for field, input_registry, module_registry in zip(input_params["fields"], input_params["field_registry"], module.config["field_registry"]):
            assert field["description"] == input_registry["description"] == module_registry["description"]

        for node in nodes:
            params = node["params"]
            if node["node_type"] == "structure_normalize":
                assert set(params) == {"input", "normalize_rules", "outputs"}
                assert params["outputs"] == field_order
            if node["node_type"] == "validation":
                assert set(params) == {"input", "required_fields", "validation_rules", "validation_outputs"}
                assert params["required_fields"] == required_field_order
                assert params["validation_outputs"] == ["validation_status", "risk_items", "correction_suggestions"]
                assert not any(rule.startswith("forbidden_") and rule != "forbidden_rules_valid" for rule in params["validation_rules"])
                if node["node_id"].endswith("boundary_validation"):
                    if module_id == "user_relationship":
                        assert {"no_automatic_relationship_mode_switch", "no_runtime_relationship_state_transition"} <= set(params["validation_rules"])
                        assert not {"no_automatic_intimacy_upgrade", "no_automatic_relationship_transition"} & set(params["validation_rules"])
                    else:
                        assert base_rules <= set(params["validation_rules"])
            if node["node_type"] == "update_rule":
                assert set(params) == {"input", "update_policy", "config_version"}
                assert params["config_version"] == "0.1"
                assert {
                    "confirmed_validated_config_only",
                    "requires_revalidation_after_update",
                    "requires_recompile",
                    "no_runtime_state_write",
                } <= set(params["update_policy"])
            if node["node_type"] == "module_output":
                assert set(params) == {"input", "output_key", "output_schema", "i18n_keys"}
                assert params["output_schema"]["fields"] == [
                    *field_order,
                    "validation_status",
                    "risk_items",
                    "correction_suggestions",
                    "config_version",
                ]
                output = node["outputs"][params["output_key"]]
                assert output["validation_status"] == "warning"
                assert output["risk_items"] == ["validation_not_executed"]
                assert output["correction_suggestions"] == ["run_validation_before_use"]
                assert "config_version" not in output


def test_layer11_p1_relationship_semantics_keep_roles_stages_and_conflict_scopes_separate():
    catalog_map = {module.module_id: module for module in get_module_catalog()}

    stage_nodes = {node["node_id"]: node for node in catalog_map["intimacy_level"].module_graph["nodes"]}
    stage_input = stage_nodes["relationship_stage_config_input"]["params"]["fields"]
    stage_values = {field["field_key"]: field["field_value"] for field in stage_input}
    assert "stable_companionship" not in json.dumps(stage_values, ensure_ascii=False)
    assert stage_values["stage_order"] == ["initial_contact", "basic_familiarity", "established_rapport", "deep_rapport"]
    assert "established_rapport_cannot_change_relationship_mode" in stage_nodes["relationship_stage_boundary_validation"]["params"]["validation_rules"]

    trust_nodes = {node["node_id"]: node for node in catalog_map["role_positioning"].module_graph["nodes"]}
    trust_fields = {field["field_key"]: field["field_value"] for field in trust_nodes["trust_config_input"]["params"]["fields"]}
    assert "user_confirmation_rules" not in trust_fields
    assert "trust_user_control_rules" in trust_fields
    assert "reset_restores_lowest_default_trust_state" not in json.dumps(trust_fields, ensure_ascii=False)
    assert "trust_user_control_rules_required" in trust_nodes["trust_boundary_validation"]["params"]["validation_rules"]

    behavior_rules = catalog_map["relationship_rule"].module_graph["nodes"][-3]["params"]["validation_rules"]
    assert {"no_third_party_relationship_analysis", "no_group_discussion_orchestration"} <= set(behavior_rules)

    social_nodes = {node["node_id"]: node for node in catalog_map["module_social"].module_graph["nodes"]}
    social_fields = {field["field_key"]: field["field_value"] for field in social_nodes["social_network_config_input"]["params"]["fields"]}
    assert "multi_party_conflict_rules" not in social_fields
    assert "third_party_relationship_analysis_rules" in social_fields
    assert {
        "no_active_group_turn_taking",
        "no_multi_resident_orchestration",
        "no_resident_user_conflict_repair_override",
    } <= set(social_nodes["social_network_boundary_validation"]["params"]["validation_rules"])

    group_rules = catalog_map["interaction_history"].module_graph["nodes"][-3]["params"]["validation_rules"]
    assert {"no_private_third_party_profile_analysis", "no_resident_user_relationship_repair_override"} <= set(group_rules)


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
        option_ids = [option["option_id"] for option in checkbox_config["default_options"]]
        if node["node_id"] == "language_behavior_output_expression":
            assert option_ids == [
                "restrained_addressing",
                "light_follow_up",
                "warm_comfort",
                "clear_refusal",
                "occasional_city_imagery",
                "short_subtitle_rhythm",
            ]
            city_imagery = next(option for option in checkbox_config["default_options"] if option["option_id"] == "occasional_city_imagery")
            assert city_imagery["default_selected"] is False
        else:
            assert option_ids == expected_selected
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


def test_layer10_visual_style_first_greeting_catalog_status_and_required_module_references():
    catalog_map = {module.module_id: module for module in get_module_catalog()}
    module = catalog_map["visual_style"]
    nodes = {node["node_id"]: node for node in module.module_graph["nodes"]}

    assert len(nodes) == 7
    assert len(module.module_graph["edges"]) == 8

    greeting_field = next(
        field
        for field in nodes["visual_style_first_greeting_config"]["params"]["fields"]
        if field["field_key"] == "first_greeting"
    )
    assert greeting_field["field_value"]["content_status"] == "pending_authoring"
    assert greeting_field["field_value"]["variants"] == []
    assert [
        option["value"] for option in greeting_field["structured_options"]["content_status"]
    ] == ["pending_authoring", "authored"]

    validation_rules = nodes["visual_style_first_greeting_validation"]["params"]["validation_rules"]
    assert "content_status_must_match_variants" in validation_rules
    assert "greeting_variants_must_contain_valid_copy" in validation_rules
    assert "empty_variants_allowed" not in validation_rules

    references = nodes["visual_style_reference_input"]["params"]["references"]
    expected_sources = {
        "first_presence_identity_core": ("module_basic_identity", "basic_identity_output"),
        "first_presence_personality": ("personality_traits", "personality_traits_output_summary"),
        "first_presence_safety_boundary": (
            "humanistic_interaction_boundary_config_v0_1",
            "interaction_boundary_config_output",
        ),
        "first_presence_memory_policy": ("memory_access_control", "memory_access_output"),
        "first_presence_world_context": ("world_setting", "worldview_module_output"),
        "first_presence_interaction_strategy": ("interaction_strategy", "interaction_behavior_core_rules"),
        "first_presence_user_relationship": ("user_relationship", "user_relationship_config_output"),
    }
    assert len(references) == 7
    assert {reference["reference_id"] for reference in references} == set(expected_sources)
    assert all(reference["source_scope"] == "module" for reference in references)
    assert all(reference["required"] is True for reference in references)
    assert not any(
        reference["source_module_id"] == "humanistic_behavior_boundary_config_v0_1"
        for reference in references
    )
    for reference in references:
        source_module_id, source_node_id = expected_sources[reference["reference_id"]]
        assert reference["source_module_id"] == source_module_id
        assert reference["source_node_id"] == source_node_id
        assert source_node_id in {
            node["node_id"] for node in catalog_map[source_module_id].module_graph["nodes"]
        }

    summary = nodes["visual_style_first_presence_output"]["outputs"]["first_presence_config"][
        "reference_source_summary"
    ]
    assert all(item["reference_id"] for item in summary)
    assert {
        (item["reference_id"], item["source_module_id"], item["source_node_id"])
        for item in summary
    } == {
        (reference["reference_id"], reference["source_module_id"], reference["source_node_id"])
        for reference in references
    }


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
        expected_write_keys = [
            f"payload.behavior_policy.modules.{policy_key}",
            f"payload.graph_snapshot.layer_outputs.layer_8.behavior_policy.modules.{policy_key}",
        ]
        if module_id == INTERACTION_BEHAVIOR_MODULE_ID:
            expected_write_keys.append("payload.behavior.first_interaction")
        assert catalog_map[module_id].dr_write_keys == expected_write_keys
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
