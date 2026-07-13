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
_STAGE_7_3_FROZEN_MODULE_IDS = {"particle_avatar"}
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


def test_compiler_reserves_future_modules_without_mutating_required_or_stage_7_3_modules():
    modules = _catalog_modules()
    before = deepcopy(modules)
    source = {module["module_id"]: module for module in modules}

    dr = _compiled_dr(modules=modules)
    exported = {module["module_id"]: module for module in dr["payload"]["modules"]}
    reserved = [
        module
        for module in exported.values()
        if module.get("slot_type") in _RESERVED_SLOT_TYPES
        and module["module_id"] not in _STAGE_7_3_FROZEN_MODULE_IDS
    ]

    assert reserved
    assert modules == before
    for module in reserved:
        assert module["status"] == "RESERVED"
        assert module["is_placeholder"] is True
        assert module["no_execution"] is True
        assert module["runtime_enabled"] is False
        assert module["runtime_mapping"] == {}
        assert not module.get("module_graph", {}).get("runtime_flow")
        assert not module.get("module_graph", {}).get("slot_routes")

    particle = exported["particle_avatar"]
    particle_source = source["particle_avatar"]
    for field in ("status", "is_placeholder", "no_execution", "runtime_enabled"):
        assert particle[field] == particle_source[field]

    for module_id, module in exported.items():
        if module.get("slot_type") in _REQUIRED_SLOT_TYPES and module_id in source:
            for field in ("status", "is_placeholder", "no_execution", "runtime_enabled"):
                assert module[field] == source[module_id][field]

    runtime_steps = dr["payload"]["runtime_plan"]["steps"]
    assert not any("voice." in str(step) or "tts." in str(step) for step in runtime_steps)
    assert {route["capability"] for route in dr["payload"]["fallback_routes"]} == _REQUIRED_SLOT_TYPES


def test_stage_scope_audit_fails_if_ready_future_module_escapes_normalization(monkeypatch):
    monkeypatch.setattr(dr_compiler, "_synchronize_stage_7_4_module_scope", lambda collection: None)

    result = compile_dr_result_v0_3(_canvas(modules=_catalog_modules()))

    assert result["valid"] is False
    assert result["compiled_dr"] is None
    assert any(item["code"] == "DR_STAGE_SCOPE_RESERVED_MODULE_EXECUTABLE" for item in result["errors"])


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


def test_audit_report_executes_all_six_checks_and_reports_real_counts():
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
    assert summary["warning"] == 0
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


def test_legacy_v03_without_optional_memory_extensions_and_new_dr_both_load():
    current = _compiled_dr()
    legacy = deepcopy(current)
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
