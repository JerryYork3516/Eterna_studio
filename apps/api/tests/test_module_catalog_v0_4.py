"""Module catalog v0.4 — catalog coverage and placeholder safety checks."""

from __future__ import annotations

from collections import Counter

from app.models.v0_4 import CANONICAL_LAYERS, ProtocolStatus
from app.registry.module_catalog import get_module_catalog, validate_module_catalog


# Baseline catalog plus Stage 6.9 voice / TTS and Stage 6.10 screen guidance surfaces.
EXPECTED_TOTAL = 143


def test_module_catalog_coverage_and_counts():
    catalog = get_module_catalog()
    assert len(catalog) == EXPECTED_TOTAL

    counts = Counter(module.status.value for module in catalog)
    assert counts[ProtocolStatus.core.value] == 4
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


def test_placeholder_modules_exist_and_safe():
    catalog = get_module_catalog()
    catalog_map = {module.module_id: module for module in catalog}

    expected_placeholders = {
        "basic_identity",
        "existence_boundary",
        "identity_anchor",
        "identity_llm_slot",
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
