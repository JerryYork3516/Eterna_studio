"""Module catalog v0.4 — catalog coverage and placeholder safety checks."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from app.models.v0_4 import CANONICAL_LAYERS, ProtocolStatus
from app.registry.module_catalog import get_module_catalog, validate_module_catalog


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
        module_output_nodes = [node for node in graph_nodes if node.get("node_id") == "module_output"]
        assert output_key in module.outputs
        assert module.outputs["module_output"] == output_key
        assert module_output_nodes
        assert module_output_nodes[0]["outputs"]["module_output"] == output_key
        assert module.ui_config["shell_version"] == "module_shell_v1"
        for field in module.config["fields"]:
            assert field["edit_scope"] in {"developer_only", "user_editable", "runtime_editable", "plugin_editable"}
            assert field["update_level"] in {"locked_core", "versioned_core", "config", "runtime_state", "plugin"}
            assert "requires_recompile" in field


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
        for node_id in ("field_input", "structure_normalize", "module_output"):
            required.add(f"module.{module_id}.node.{node_id}.name")
            required.add(f"module.{module_id}.node.{node_id}.description")
    required.update(
        {
            "module.module_identity_anchor.node.identity_consistency_validation.name",
            "module.module_identity_anchor.node.identity_lock_rule.name",
            "field.identity.resident_id.label",
            "field.identity.identity_anchor.help",
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


def test_module_catalog_validation_passes():
    catalog = get_module_catalog()
    errors = validate_module_catalog(catalog)
    assert errors == [], f"Catalog validation failed: {errors}"
