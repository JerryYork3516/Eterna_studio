"""Stage 7.4 export-layer P1 capability, memory, and audit contracts."""

from __future__ import annotations

from copy import deepcopy

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.registry.module_catalog import get_module_catalog
from app.services import dr_compiler, provider_adapters, resident_runtime
from app.services.dr_compiler import compile_dr_result_v0_3, mock_load_dr_v0_3


client = TestClient(app)

_REQUIRED_SLOT_TYPES = {"llm", "memory", "lattice"}
_RESERVED_SLOT_TYPES = {"tts", "speech", "screen", "avatar", "ar", "tool"}
_FORCED_RESERVED_MODULE_IDS = {"particle_avatar", "llm_provider_router"}
_MEMORY_SUPPORT_LEVELS = {
    "short_term_memory": "supported",
    "preference_memory": "supported_minimal_kv",
    "event_memory": "policy_only",
    "relationship_memory": "policy_only",
    "interaction_log": "display_cache_only",
}
_AUDIT_CHECKS = (
    "stage_scope_check",
    "compatibility_check",
    "frozen_root_field_check",
    "pending_validation_check",
    "duplicate_source_check",
    "memory_support_level_check",
    "file_size_check",
)


@pytest.fixture(autouse=True)
def _reset_runtime_state():
    provider_adapters.reset_memory()
    resident_runtime.reset_states()
    yield
    provider_adapters.reset_memory()
    resident_runtime.reset_states()


def _workflow(name: str = "Stage 7.4 P1 export contracts") -> dict:
    return {"name": name, "nodes": [{"node_id": f"layer_{index}"} for index in range(1, 14)]}


def _catalog_modules() -> list[dict]:
    return [module.model_dump(mode="json") for module in get_module_catalog()]


def _canvas(*, modules: list[dict] | None = None) -> dict:
    canvas = {"workflow": _workflow()}
    if modules is not None:
        canvas["modules"] = modules
    return canvas


def _compiled_dr(*, modules: list[dict] | None = None) -> dict:
    result = compile_dr_result_v0_3(_canvas(modules=modules))
    assert result["valid"] is True, result["errors"]
    return result["compiled_dr"]


def test_compiler_reserves_future_and_forced_placeholder_modules_without_mutating_canvas():
    modules = _catalog_modules()
    before = deepcopy(modules)
    source = {module["module_id"]: module for module in modules}

    dr = _compiled_dr(modules=modules)
    exported = {module["module_id"]: module for module in dr["payload"]["modules"]}
    reserved = [
        module
        for module in exported.values()
        if module.get("slot_type") in _RESERVED_SLOT_TYPES
        or module["module_id"] in _FORCED_RESERVED_MODULE_IDS
    ]

    assert reserved
    assert _FORCED_RESERVED_MODULE_IDS <= {module["module_id"] for module in reserved}
    assert modules == before
    for module in reserved:
        assert module["status"] == "RESERVED"
        assert module["is_placeholder"] is True
        assert module["no_execution"] is True
        assert module["runtime_enabled"] is False
        assert module["runtime_mapping"] == {}
        assert not module.get("module_graph", {}).get("runtime_flow")
        assert not module.get("module_graph", {}).get("slot_routes")

    for module_id, module in exported.items():
        if (
            module.get("slot_type") in _REQUIRED_SLOT_TYPES
            and module_id in source
            and module_id not in _FORCED_RESERVED_MODULE_IDS
        ):
            for field in ("status", "is_placeholder", "no_execution", "runtime_enabled"):
                assert module[field] == source[module_id][field]

    runtime_steps = dr["payload"]["runtime_plan"]["steps"]
    assert not any("voice." in str(step) or "tts." in str(step) for step in runtime_steps)
    assert {route["capability"] for route in dr["payload"]["fallback_routes"]} == _REQUIRED_SLOT_TYPES


def test_particle_avatar_compiles_saved_fields_into_declarative_mapping_output():
    modules = _catalog_modules()
    particle = next(
        module for module in modules if module["module_id"] == "particle_avatar"
    )
    input_node = next(
        node
        for node in particle["module_graph"]["nodes"]
        if node["node_id"] == "particle_visual_config_input"
    )
    fields = {
        field["field_key"]: field for field in input_node["params"]["fields"]
    }
    configured_values = {
        "user_current_base_color": "#123456",
        "resident_default_base_color": "#234567",
        "primary_color": "#345678",
        "secondary_color": "#456789",
        "highlight_color": "#56789a",
        "calm_brightness_multiplier": 1.2,
        "caring_color_temperature_offset": 8.0,
        "subdued_energy_multiplier": 0.2,
        "joyful_motion_speed_multiplier": "not-a-number",
        "transition_duration": 2.4,
        "minimum_hold_duration": 0.8,
        "transition_style": "unsupported_flash",
    }
    for field_key, value in configured_values.items():
        fields[field_key]["field_value"] = value
    before = deepcopy(modules)

    dr = _compiled_dr(modules=modules)

    assert modules == before
    compiled_particle = next(
        module
        for module in dr["payload"]["modules"]
        if module["module_id"] == "particle_avatar"
    )
    assert compiled_particle["status"] == "RESERVED"
    assert compiled_particle["no_execution"] is True
    output = compiled_particle["outputs"]["particle_mapping_config"]
    output_node = next(
        node
        for node in compiled_particle["module_graph"]["nodes"]
        if node["node_id"] == "particle_mapping_config_output"
    )
    assert output_node["outputs"]["particle_mapping_config"] == output

    base_color = output["base_color_config"]
    assert base_color["priority"] == [
        "user_current_base_color",
        "resident_default_base_color",
        "particle_core_default_gray_white",
    ]
    assert base_color["user_current_base_color"] == "#123456"
    assert base_color["resident_default_base_color"] == "#234567"
    assert base_color["primary_color"] == "#345678"
    assert base_color["secondary_color"] == "#456789"
    assert base_color["highlight_color"] == "#56789a"
    assert base_color["expression_may_replace_user_base_color"] is False

    mappings = output["expression_relative_mapping"]["state_mappings"]
    assert mappings["calm"]["brightness_multiplier"] == 1.2
    assert mappings["caring"]["color_temperature_offset"] == 0.15
    assert mappings["subdued"]["energy_multiplier"] == 0.7
    assert mappings["joyful"]["motion_speed_multiplier"] == 1.12
    assert set(mappings) == {"neutral", "calm", "caring", "subdued", "joyful"}
    assert all(
        set(mapping)
        == {
            "brightness_multiplier",
            "saturation_multiplier",
            "color_temperature_offset",
            "energy_multiplier",
            "motion_speed_multiplier",
            "diffusion_multiplier",
        }
        for mapping in mappings.values()
    )
    assert not any(
        key in mapping
        for mapping in mappings.values()
        for key in ("color", "fixed_color", "primary_color", "highlight_color")
    )

    transition = output["transition_rules"]
    assert transition["transition_duration"] == 2.4
    assert transition["minimum_hold_duration"] == 0.8
    assert transition["transition_style"] == "smooth"
    assert transition["transition_executor"] == "aftelle"
    assert transition["studio_stores_rules_only"] is True
    assert "final_color" not in output
    assert "final_particle_parameters" not in output

    compiled_input = next(
        node
        for node in compiled_particle["module_graph"]["nodes"]
        if node["node_id"] == "particle_visual_config_input"
    )
    compiled_fields = {
        field["field_key"]: field["field_value"]
        for field in compiled_input["params"]["fields"]
    }
    assert compiled_fields["caring_color_temperature_offset"] == 0.15
    assert compiled_fields["subdued_energy_multiplier"] == 0.7
    assert compiled_fields["joyful_motion_speed_multiplier"] == 1.12
    assert compiled_fields["transition_style"] == "smooth"


def test_stage_scope_audit_fails_if_ready_future_module_escapes_normalization(monkeypatch):
    monkeypatch.setattr(dr_compiler, "_synchronize_stage_7_4_module_scope", lambda collection: None)

    result = compile_dr_result_v0_3(_canvas(modules=_catalog_modules()))

    assert result["valid"] is False
    assert result["compiled_dr"] is None
    assert any(item["code"] == "DR_STAGE_SCOPE_RESERVED_MODULE_EXECUTABLE" for item in result["errors"])


@pytest.mark.parametrize("module_id", sorted(_FORCED_RESERVED_MODULE_IDS))
def test_stage_scope_audit_rejects_forced_placeholder_status_conflict(monkeypatch, module_id: str):
    original = dr_compiler._synchronize_stage_7_4_module_scope

    def drift(collection: dict) -> None:
        original(collection)
        module = next(item for item in collection["modules"] if item["module_id"] == module_id)
        module["status"] = "READY"
        module["no_execution"] = False

    monkeypatch.setattr(dr_compiler, "_synchronize_stage_7_4_module_scope", drift)
    result = compile_dr_result_v0_3(_canvas(modules=_catalog_modules()))

    assert result["valid"] is False
    assert result["compiled_dr"] is None
    assert any(
        item["code"] == "DR_STAGE_SCOPE_RESERVED_MODULE_EXECUTABLE"
        and module_id in item["message"]
        for item in result["errors"]
    )


def test_memory_support_levels_and_local_runtime_backend_preserve_frozen_v03_policy():
    dr = _compiled_dr()
    memory_policy = dr["payload"]["memory_policy"]
    extensions = memory_policy["memory_policy_extensions"]

    assert extensions["memory_support_levels"] == _MEMORY_SUPPORT_LEVELS
    assert dr["payload"]["memory_config"]["storage_backend"] == "local_runtime"
    assert dr["memory_config"] == dr["payload"]["memory_config"]
    assert dr["legacy_blueprint"]["memory_config"]["store"] == "local_runtime"
    assert memory_policy["retention_policy"] == "persistent"
    assert memory_policy["read_write_policy"] == "local_runtime"
    assert memory_policy["memory_types"] == [
        "short_term_memory",
        "profile_memory",
        "preference_memory",
        "interaction_log",
    ]
    assert memory_policy["preference_memory"] == {"type": "kv", "scope": "per_resident"}


def test_policy_only_memory_degrades_without_provider_and_interaction_log_uses_display_cache(monkeypatch):
    dr = _compiled_dr()
    resident_id = dr["manifest"]["resident_id"]
    state = resident_runtime.create_runtime_state_from_dr(dr)
    calls: list[tuple[str, dict]] = []

    def provider_spy(engine_id: str, payload: dict) -> dict:
        calls.append((engine_id, payload))
        return {"status": "success", "count": 1}

    monkeypatch.setattr(resident_runtime, "route_provider_for_engine", provider_spy)
    event = resident_runtime.execute_memory_operation(
        {
            "op": "write",
            "resident_id": resident_id,
            "memory_type": "event_memory",
            "entry": {"event_summary": "policy only"},
        }
    )
    relationship = resident_runtime.execute_memory_operation(
        {
            "op": "write",
            "resident_id": resident_id,
            "memory_type": "relationship_memory",
            "entry": {"from_level": 1, "to_level": 2},
        }
    )
    interaction = resident_runtime.execute_memory_operation(
        {
            "op": "write",
            "resident_id": resident_id,
            "memory_type": "interaction_log",
            "entry": {"input": "display cache"},
        },
        _runtime_authorized=True,
    )

    assert event["status"] == "denied"
    assert event["reason"] == "memory_policy_only_not_runtime_supported"
    assert relationship["status"] == "denied"
    assert relationship["reason"] == "memory_policy_only_not_runtime_supported"
    assert interaction["status"] == "success"
    assert interaction["storage_backend"] == "session_state"
    assert interaction["namespace"] == f"public_transcript:{state.session_id}"
    assert calls == []


def test_audit_report_executes_all_seven_checks_and_reports_real_counts():
    dr = _compiled_dr()
    audit = dr["audit_report"]
    summary = audit["summary"]

    assert summary["fail"] == sum(item["status"] == "FAIL" for item in audit["findings"])
    assert summary["warning"] == sum(item["status"] == "WARNING" for item in audit["findings"])
    assert summary["pass"] == sum(item["status"] == "PASS" for item in audit["findings"])
    for check_name in _AUDIT_CHECKS:
        counts = [summary[f"{check_name}_{status}"] for status in ("pass", "warning", "fail")]
        assert sum(counts) > 0
    assert summary["pending_validation_check_warning"] == 0
    assert summary["pending_validation_check_pass"] == 1
    assert summary["frozen_root_field_check_pass"] == 1
    assert summary["warning"] == summary["file_size_check_warning"]
    assert summary["memory_support_level_check_pass"] == 5


def test_layer8_validation_nodes_are_finalized_without_mutating_canvas():
    modules = _catalog_modules()
    before = deepcopy(modules)

    dr = _compiled_dr(modules=modules)
    behavior_modules = {
        module["module_id"]: module
        for module in dr["payload"]["modules"]
        if module["module_id"]
        in {
            "language_habit",
            "decision_pattern",
            "emotion_reaction",
            "interaction_strategy",
            "emotion_mapper",
            "behavior_habit",
        }
    }

    assert modules == before
    assert len(behavior_modules) == 6
    for module in behavior_modules.values():
        validation_node = next(
            node
            for node in module["module_graph"]["nodes"]
            if str(node.get("params", {}).get("config_mode", "")).endswith("_validation")
        )
        assert validation_node["params"]["validation_result"] == "pass"
    assert not any(
        finding["code"] == "DR_PENDING_VALIDATION_REPORTED"
        for finding in dr["audit_report"]["findings"]
    )


def test_missing_required_layer8_validation_rule_blocks_compile():
    modules = _catalog_modules()
    language = next(module for module in modules if module["module_id"] == "language_habit")
    validation_node = next(
        node
        for node in language["module_graph"]["nodes"]
        if str(node.get("params", {}).get("config_mode", "")).endswith("_validation")
    )
    selected = validation_node["params"]["checkbox_config"]["selected_options"]
    validation_node["params"]["checkbox_config"]["selected_options"] = selected[:-1]

    result = compile_dr_result_v0_3(_canvas(modules=modules))

    assert result["valid"] is False
    assert result["compiled_dr"] is None
    assert any(item["code"] == "DR_LAYER8_VALIDATION_INCOMPLETE" for item in result["errors"])


def test_file_size_warning_is_real_but_does_not_block_compile_or_export(monkeypatch):
    monkeypatch.setattr(dr_compiler, "_V03_FILE_SIZE_WARNING_BYTES", 1)
    canvas = _canvas(modules=_catalog_modules())

    result = compile_dr_result_v0_3(canvas)
    response = client.post("/dr/export", json=canvas)

    assert result["valid"] is True
    assert any(item["code"] == "DR_FILE_SIZE_WARNING" for item in result["warnings"])
    assert result["compiled_dr"]["audit_report"]["summary"]["file_size_check_warning"] == 1
    assert response.status_code == 200


def test_memory_support_level_drift_blocks_compile(monkeypatch):
    original = dr_compiler._assemble_layer5_memory_policy

    def drifted(collection: dict, resident_id: str, findings: list[dict]) -> dict:
        policy = original(collection, resident_id, findings)
        policy["memory_support_levels"]["event_memory"] = "supported"
        return policy

    monkeypatch.setattr(dr_compiler, "_assemble_layer5_memory_policy", drifted)
    result = compile_dr_result_v0_3(_canvas())

    assert result["valid"] is False
    assert any(item["code"] == "DR_MEMORY_SUPPORT_LEVEL_INACCURATE" for item in result["errors"])


def test_legacy_v03_without_root_modules_or_optional_memory_extensions_and_new_dr_both_load():
    current = _compiled_dr()
    legacy = deepcopy(current)
    legacy.pop("modules")
    legacy["payload"]["memory_policy"].pop("memory_policy_extensions", None)
    legacy["memory_policy"] = deepcopy(legacy["payload"]["memory_policy"])

    assert mock_load_dr_v0_3(legacy)["loaded"] is True
    assert mock_load_dr_v0_3(current)["loaded"] is True
    assert resident_runtime.create_runtime_state_from_dr(legacy).resident_id == legacy["manifest"]["resident_id"]
    legacy_event = resident_runtime.execute_memory_operation(
        {
            "op": "write",
            "resident_id": legacy["manifest"]["resident_id"],
            "memory_type": "event_memory",
            "entry": {"event_summary": "legacy behavior remains available"},
        }
    )
    assert legacy_event["status"] == "success"
    assert resident_runtime.create_runtime_state_from_dr(current).resident_id == current["manifest"]["resident_id"]
