"""Module catalog v0.4 — catalog coverage and placeholder safety checks."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from app.models.v0_4 import CANONICAL_LAYERS, ProtocolStatus
from app.registry.module_catalog import get_module_catalog, validate_module_catalog
from app.registry.node_registry import get_node_definition


# Stage 7.4 replaces the old seven Layer 1 identity modules plus the former
# identity anchor module with five blueprint-led identity core modules.
EXPECTED_TOTAL = 140
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


def _node_id(output_key: str, node_type: str) -> str:
    suffix = {
        "field_input": "field_input",
        "structure_normalize": "normalize",
        "validation": "validation",
        "update_rule": "update_rule",
        "module_output": "output",
    }[node_type]
    return f"{output_key}_{suffix}"


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
        "personality_traits",
        "content_safety",
        "clone_restriction",
        "event_memory",
        "rag_slot",
        "language_habit",
        "builtin_capability",
        "voice_profile",
        "relationship_rule",
        "operation_log",
    }

    for placeholder_id in expected_placeholders:
        assert placeholder_id in catalog_map, f"Expected placeholder module {placeholder_id} not found in catalog"
        module = catalog_map[placeholder_id]
        assert module.is_placeholder is True, f"Module {placeholder_id} must have is_placeholder=True"
        assert module.status in {ProtocolStatus.ready, ProtocolStatus.mock, ProtocolStatus.planned, ProtocolStatus.later, ProtocolStatus.core, ProtocolStatus.disabled}


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
    required.update(
        {
            "node.type.field_input",
            "node.field_input.description",
            "node.type.layer_aggregator",
            "audit.DR_IDENTITY_NODE_MISSING",
            "audit.DR_IDENTITY_LEGACY_FIELD_INPUT_MISSING",
        }
    )
    for key in required:
        assert key in zh, f"missing zh i18n key: {key}"
        assert key in en, f"missing en i18n key: {key}"


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


def test_module_catalog_validation_passes():
    catalog = get_module_catalog()
    errors = validate_module_catalog(catalog)
    assert errors == [], f"Catalog validation failed: {errors}"
