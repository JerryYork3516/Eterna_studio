"""Stage 7.4 P0 DR compile/runtime boundary regression tests."""

from __future__ import annotations

from copy import deepcopy
import json

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.registry.module_catalog import get_module_catalog
from app.registry.provider_registry import resolve_provider_for_engine
from app.registry.slot_catalog import get_slot_catalog
from app.services import dr_compiler, provider_adapters, resident_runtime
from app.services.dr_compiler import compile_dr_result_v0_3
from app.services.runtime_llm_config import reset_runtime_llm_config


client = TestClient(app)

_REQUIRED_CAPABILITIES = ("llm", "memory", "lattice")
_OPTIONAL_CAPABILITIES = ("tts", "speech", "screen", "avatar", "ar", "tool")
_LAYER5_POLICY_OUTPUTS = (
    ("short_term_memory", "short_term_memory_context", "short_term_memory"),
    ("preference_memory", "preference_memory", "preference_memory"),
    ("event_memory", "event_memory", "event_memory"),
    ("relationship_memory", "relationship_memory", "relationship_memory"),
    ("memory_update", "memory_update_policy", "memory_update"),
    ("memory_access_control", "memory_access_policy_result", "memory_access_control"),
    ("memory_provider_router", "memory_provider_route_policy", "memory_provider_router"),
)


@pytest.fixture(autouse=True)
def _reset_runtime_state():
    provider_adapters.reset_memory()
    resident_runtime.reset_states()
    reset_runtime_llm_config()
    yield
    provider_adapters.reset_memory()
    resident_runtime.reset_states()
    reset_runtime_llm_config()


def _workflow() -> dict:
    return {
        "name": "Stage 7.4 P0 contract fixture",
        "nodes": [{"node_id": f"layer_{index}"} for index in range(1, 14)],
    }


def _catalog_modules() -> list[dict]:
    return [module.model_dump(mode="json") for module in get_module_catalog()]


def _catalog_slots() -> list[dict]:
    return [slot.model_dump(mode="json") for slot in get_slot_catalog()]


def _compile(*, modules: list[dict] | None = None, slots: list[dict] | None = None) -> dict:
    canvas = {"workflow": _workflow()}
    if modules is not None:
        canvas["modules"] = modules
    if slots is not None:
        canvas["slots"] = slots
    return compile_dr_result_v0_3(canvas)


def _valid_dr() -> dict:
    result = _compile()
    assert result["valid"] is True
    return result["compiled_dr"]


def _reference_canvas(
    *,
    source_node_id: str | None = None,
    required: bool = True,
    source_field_paths: list[str] | None = None,
) -> tuple[dict, str]:
    modules = _catalog_modules()
    source_module = next(module for module in modules if module["module_id"] == "self_awareness")
    target_module = next(module for module in modules if module["module_id"] == "goal_setting")
    source_output = next(
        node for node in source_module["module_graph"]["nodes"] if node["node_type"] == "reference_output"
    )
    target_input = next(
        node for node in target_module["module_graph"]["nodes"] if node["node_type"] == "reference_input"
    )
    local_source_node_id = source_output["node_id"]
    source_output.setdefault("params", {})["export_fields"] = [{"field_path": "profile.name"}]
    target_input.setdefault("params", {})["references"] = [
        {
            "source_layer_id": "layer_12",
            "source_module_id": "self_awareness",
            "source_node_id": source_node_id or local_source_node_id,
            "source_scope": "field" if source_field_paths is not None else "module",
            "source_field_paths": source_field_paths or [],
            "reference_type": "references",
            "required": required,
        }
    ]
    return {"workflow": _workflow(), "modules": modules}, local_source_node_id


def _target_reference(dr_payload: dict) -> dict:
    target = next(module for module in dr_payload["modules"] if module["module_id"] == "goal_setting")
    node = next(item for item in target["module_graph"]["nodes"] if item["node_type"] == "reference_input")
    return node["params"]["references"][0]


def _reasoning_prompt(body: dict) -> str:
    reasoning = next(step for step in body["execution_trace"] if step["step"] == "reasoning")
    return reasoning["input"]["prompt"]


def _memory_router_module(modules: list[dict]) -> dict:
    return next(module for module in modules if module["module_id"] == "memory_provider_router")


def _memory_router_output(module: dict) -> dict:
    output_node = next(
        node for node in module["module_graph"]["nodes"] if node["node_type"] == "module_output"
    )
    return output_node["outputs"]["memory_provider_route_policy"]


def _frozen_aftelle_loader_contract(dr: dict) -> tuple[str, str, str, str]:
    manifest = dr["manifest"]
    payload = dr["payload"]
    identity = payload["resident_identity"]
    assert dr["not_executable"] is True
    assert manifest["resident_id"] == identity["resident_id"]
    assert isinstance(dr["lattice_config"], dict)
    assert isinstance(dr["runtime_requirements"], dict)
    assert dr["safety_policy"]["no_secret_in_dr"] is True
    assert dr["safety_policy"]["no_direct_provider_binding"] is True
    assert dr["safety_policy"]["user_data_not_embedded"] is True
    assert dr["safety_policy"]["not_executable"] is True
    return dr["schema_version"], dr["revision"], manifest["resident_id"], identity["name"]


def test_required_reference_resolves_local_node_and_field_path():
    canvas, local_node_id = _reference_canvas(source_field_paths=["profile.name"])

    result = compile_dr_result_v0_3(canvas)

    assert result["valid"] is True
    assert _target_reference(result["compiled_dr"]["payload"])["source_node_id"] == local_node_id
    finding = next(
        item
        for item in result["compiled_dr"]["audit_report"]["findings"]
        if item["code"] == "DR_REFERENCE_VALIDATION_COMPLETE"
    )
    assert finding["status"] == "PASS"
    message = finding["message"]
    checked = message.split("checked=", 1)[1].split(",", 1)[0]
    resolved = message.split("resolved=", 1)[1]
    # The fixture's required reference plus Layer 10's seven static first-presence
    # module references must all resolve.
    assert "required=8" in message
    assert checked == resolved


def test_exact_legacy_reference_prefix_is_canonicalized_without_mutating_canvas():
    canvas, local_node_id = _reference_canvas()
    legacy_id = f"layer_12::self_awareness::{local_node_id}"
    _target_reference({"modules": canvas["modules"]})["source_node_id"] = legacy_id
    before = deepcopy(canvas)

    result = compile_dr_result_v0_3(canvas)

    assert result["valid"] is True
    assert canvas == before
    assert _target_reference(result["compiled_dr"]["payload"])["source_node_id"] == local_node_id


def test_required_reference_failure_blocks_compile_and_export_with_audit_evidence():
    canvas, _local_node_id = _reference_canvas(source_node_id="missing_local_node")

    result = compile_dr_result_v0_3(canvas)
    response = client.post("/dr/export", json=canvas)

    assert result["valid"] is False
    assert result["compiled_dr"] is None
    finding = next(item for item in result["errors"] if item["code"] == "DR_REFERENCE_SOURCE_NODE_MISSING")
    assert "module_id=goal_setting" in finding["message"]
    assert "node_id=self_state_reference_input" in finding["message"]
    assert "exact local node_id" in finding["message"]
    assert "params.references[0].source_node_id" in finding["path"]
    assert response.status_code == 422


def test_optional_reference_failure_is_warning_and_does_not_block_export():
    canvas, _local_node_id = _reference_canvas(source_node_id="missing_optional_node", required=False)

    result = compile_dr_result_v0_3(canvas)

    assert result["valid"] is True
    finding = next(item for item in result["warnings"] if item["code"] == "DR_REFERENCE_SOURCE_NODE_MISSING")
    assert finding["status"] == "WARNING"


def test_required_reference_unexported_field_path_is_rejected():
    canvas, _local_node_id = _reference_canvas(source_field_paths=["profile.unexported"])

    result = compile_dr_result_v0_3(canvas)

    assert result["valid"] is False
    assert any(item["code"] == "DR_REFERENCE_SOURCE_FIELD_PATH_UNRESOLVED" for item in result["errors"])


def test_required_capability_contract_is_registry_derived_and_does_not_overclaim():
    dr = _valid_dr()
    runtime = dr["payload"]["runtime_requirements"]
    providers = dr["payload"]["provider_requirements"]

    assert dr["manifest"]["required_capabilities"] == list(_REQUIRED_CAPABILITIES)
    assert runtime["required_slot_types"] == list(_REQUIRED_CAPABILITIES)
    assert runtime["required_engines"] == ["llm_mock", "memory_mock", "lattice_mock"]
    assert runtime["required_provider_types"] == ["llm", "memory"]
    assert not set(_OPTIONAL_CAPABILITIES).intersection(runtime["required_slot_types"])
    assert "voice" not in runtime["required_slot_types"]
    assert {key for key, value in providers.items() if value.get("required")} == set(_REQUIRED_CAPABILITIES)
    assert providers["lattice"]["mode"] == "mock_fallback"
    assert "fallback_provider_type" not in providers["lattice"]
    assert [
        route for route in dr["payload"]["fallback_routes"] if route["capability"] == "lattice"
    ] == [{"capability": "lattice", "route": "lattice_mock", "mode": "mock", "notes": "fallback lattice"}]
    assert "screen" not in runtime["required_provider_types"]
    for engine_id in runtime["required_engines"]:
        assert resolve_provider_for_engine(engine_id) is not None


def test_lattice_fallback_is_lattice_mock_across_runtime_slots_and_routes():
    dr = _valid_dr()
    payload = dr["payload"]

    assert "lattice_mock" in payload["runtime_requirements"]["required_engines"]
    assert "fallback_provider_type" not in payload["provider_requirements"]["lattice"]
    assert {
        slot["engine_binding"]
        for slot in payload["slots"]
        if slot.get("slot_type") == "lattice"
    } == {"lattice_mock"}
    assert [
        route["route"]
        for route in payload["fallback_routes"]
        if route.get("capability") == "lattice"
    ] == ["lattice_mock"]
    assert not any(
        route.get("capability") == "lattice" and route.get("route") == "screen"
        for route in payload["fallback_routes"]
    )


@pytest.mark.parametrize("missing_slot_type", _REQUIRED_CAPABILITIES)
def test_missing_required_slot_blocks_compile(missing_slot_type: str):
    slots = [slot for slot in _catalog_slots() if slot["slot_type"] != missing_slot_type]

    result = _compile(slots=slots)

    assert result["valid"] is False
    assert result["compiled_dr"] is None
    assert any(item["code"] == "DR_CAP_REQUIRED_SLOT_UNRESOLVED" for item in result["errors"])


def test_invalid_required_engine_binding_has_specific_audit_failure():
    slots = _catalog_slots()
    llm_slot = next(slot for slot in slots if slot["slot_id"] == "slot_llm")
    llm_slot["engine_binding"] = "missing_engine"

    result = _compile(slots=slots)

    assert result["valid"] is False
    assert any(item["code"] == "DR_CAP_REQUIRED_ENGINE_UNRESOLVED" for item in result["errors"])


def test_missing_optional_slots_and_policy_declarations_still_load():
    slots = [slot for slot in _catalog_slots() if slot["slot_type"] in set(_REQUIRED_CAPABILITIES)]
    result = _compile(slots=slots)
    assert result["valid"] is True
    dr = result["compiled_dr"]
    for capability in _OPTIONAL_CAPABILITIES:
        dr["payload"]["provider_requirements"].pop(capability, None)
    dr["payload"]["provider_requirements"]["future_optional"] = {"required": False}

    body = resident_runtime.load_digital_resident(dr, input_text="optional capabilities absent")

    assert body["loaded"] is True
    assert body["validation_result"]["valid"] is True


def test_runtime_revalidates_required_chain_instead_of_trusting_stale_audit():
    dr = _valid_dr()
    dr["payload"]["slots"] = [slot for slot in dr["payload"]["slots"] if slot["slot_type"] != "llm"]

    body = resident_runtime.load_digital_resident(dr)

    assert dr["audit_report"]["valid"] is True
    assert body["loaded"] is False
    assert any(item["code"] == "DR_CAP_REQUIRED_SLOT_UNRESOLVED" for item in body["validation_result"]["errors"])


def test_runtime_rejects_tampered_lattice_fallback_requirement():
    dr = _valid_dr()
    dr["payload"]["provider_requirements"]["lattice"]["fallback_provider_type"] = "avatar"

    body = resident_runtime.load_digital_resident(dr)

    assert body["loaded"] is False
    assert any(
        item["code"] == "DR_CAP_LATTICE_FALLBACK_PROVIDER_TYPE_FORBIDDEN"
        for item in body["validation_result"]["errors"]
    )


def test_runtime_consumes_compiled_policy_summaries_in_fixed_order_and_keeps_dr_read_only(monkeypatch):
    dr = _valid_dr()
    dr["payload"]["safety_policy"]["p0_test_marker"] = "SAFETY_POLICY_MARKER"
    dr["payload"]["behavior_policy"]["p0_test_marker"] = "BEHAVIOR_POLICY_MARKER"
    dr["payload"]["behavior_policy"]["future_optional_policy"] = {"unknown": True}
    dr["payload"]["resident_identity"]["p0_test_marker"] = "IDENTITY_POLICY_MARKER"
    dr["payload"]["memory_policy"]["p0_test_marker"] = "MEMORY_POLICY_MARKER"
    dr["payload"]["modules"][0]["module_graph"]["nodes"][0].setdefault("params", {})[
        "runtime_forbidden_marker"
    ] = "MODULE_GRAPH_MUST_NOT_EXECUTE"
    before = deepcopy(dr)
    original_route = resident_runtime.route_provider_for_engine

    def alternate_route(engine_id: str, payload: dict) -> dict:
        if engine_id == "llm_mock":
            return {
                "status": "success",
                "mock": True,
                "text": "alternate provider response",
                "provider_id": "provider_llm_alternate_mock",
                "provider_type": "llm",
                "engine_id": engine_id,
            }
        return original_route(engine_id, payload)

    monkeypatch.setattr(resident_runtime, "route_provider_for_engine", alternate_route)

    body = resident_runtime.load_digital_resident(dr, input_text="USER_INPUT_MARKER")
    prompt = _reasoning_prompt(body)

    assert body["loaded"] is True
    assert "alternate provider response" in body["output_text"]
    assert "SAFETY_POLICY_MARKER" in prompt
    assert "BEHAVIOR_POLICY_MARKER" in prompt
    assert "IDENTITY_POLICY_MARKER" in prompt
    assert "MODULE_GRAPH_MUST_NOT_EXECUTE" not in prompt
    ordered_markers = (
        "[1. Layer 3 safety constraints]",
        "[2. Dialogue boundary]",
        "[3. Resident identity]",
        "[4. Personality, language, and emotional behavior policy]",
        "[5. Retrieved memory context]",
        "[6. User input]",
    )
    assert [prompt.index(marker) for marker in ordered_markers] == sorted(
        prompt.index(marker) for marker in ordered_markers
    )
    assert prompt.rfind("USER_INPUT_MARKER") > prompt.index("SAFETY_POLICY_MARKER")
    resident_id = dr["manifest"]["resident_id"]
    state = resident_runtime.get_or_create_state(resident_id)
    assert state.resident_identity == before["payload"]["resident_identity"]
    assert state.behavior_policy == before["payload"]["behavior_policy"]
    assert state.safety_policy == before["payload"]["safety_policy"]
    assert state.memory_policy == before["payload"]["memory_policy"]
    assert state.memory_policy["p0_test_marker"] == "MEMORY_POLICY_MARKER"
    assert dr == before


def test_layer5_all_seven_module_outputs_project_to_authoritative_memory_policy():
    dr = _valid_dr()
    policy = dr["payload"]["memory_policy"]["memory_policy_extensions"]
    modules = {module["module_id"]: module for module in dr["payload"]["modules"]}

    for module_id, output_key, policy_key in _LAYER5_POLICY_OUTPUTS:
        output_node = next(
            node for node in modules[module_id]["module_graph"]["nodes"] if node["node_type"] == "module_output"
        )
        assert policy[policy_key] == output_node["outputs"][output_key]
    assert policy["short_term_memory"]["session_scoped_only"] is True
    assert policy["short_term_memory"]["retention"] == "session"
    assert policy["relationship_memory"]["change_policy"] == "gradual_only"
    assert policy["memory_update"]["no_dr_writeback"] is True


def test_frozen_v03_memory_contract_survives_when_extensions_are_ignored():
    dr = _valid_dr()
    memory_policy = dr["payload"]["memory_policy"]
    extensions = memory_policy["memory_policy_extensions"]
    legacy_view = deepcopy(dr)
    legacy_view["payload"]["memory_policy"].pop("memory_policy_extensions")
    legacy_view["memory_policy"].pop("memory_policy_extensions")

    assert memory_policy["retention_policy"] == "persistent"
    assert memory_policy["read_write_policy"] == "local_runtime"
    assert memory_policy["memory_types"] == [
        "short_term_memory",
        "profile_memory",
        "preference_memory",
        "interaction_log",
    ]
    assert memory_policy["preference_memory"] == {"type": "kv", "scope": "per_resident"}
    assert extensions["memory_types"] == [
        "short_term_memory",
        "preference_memory",
        "event_memory",
        "relationship_memory",
        "interaction_log",
    ]
    assert _frozen_aftelle_loader_contract(legacy_view) == _frozen_aftelle_loader_contract(dr)


def test_payload_modules_are_authoritative_and_required_aliases_match():
    dr = _valid_dr()

    assert isinstance(dr["payload"]["modules"], list)
    assert dr["modules"] == dr["payload"]["modules"]
    assert dr["modules"] is not dr["payload"]["modules"]
    assert "modules" not in dr["payload"]["graph_snapshot"]
    assert "modules" not in dr["legacy_blueprint"]
    assert "behavior_policy" not in dr
    for root_key, payload_key in (
        ("layers", "13_layers_snapshot"),
        ("modules", "modules"),
        ("slots", "slots"),
        ("runtime_requirements", "runtime_requirements"),
        ("memory_config", "memory_config"),
        ("memory_policy", "memory_policy"),
        ("lattice_config", "lattice_config"),
        ("voice_config", "voice_config"),
        ("safety_policy", "safety_policy"),
        ("screen_capability_declaration", "screen_capability_declaration"),
    ):
        assert dr[root_key] == dr["payload"][payload_key]


@pytest.mark.parametrize("missing_field", ["layers", "modules", "slots"])
def test_missing_frozen_root_field_blocks_compile_and_export(
    monkeypatch: pytest.MonkeyPatch, missing_field: str
):
    original = dr_compiler._v03_compatibility_aliases

    def omit_frozen_field(*args, **kwargs):
        aliases = original(*args, **kwargs)
        aliases.pop(missing_field)
        return aliases

    monkeypatch.setattr(dr_compiler, "_v03_compatibility_aliases", omit_frozen_field)
    result = _compile()
    response = client.post("/dr/export", json={"workflow": _workflow()})
    summary = result["metadata"]["v03_audit_report"]["summary"]

    assert result["valid"] is False
    assert result["compiled_dr"] is None
    assert response.status_code == 422
    assert summary["frozen_root_field_check_fail"] == 1
    assert summary["compatibility_check_fail"] >= 1
    assert summary["compatibility_check_pass"] == 0
    assert any(item["code"] == "DR_V03_FROZEN_ROOT_FIELD_MISSING" for item in result["errors"])
    assert any(item["code"] == "DR_EXPORT_COMPATIBILITY_PROJECTION_DRIFT" for item in result["errors"])


def test_top_level_modules_projection_drift_blocks_compile_and_export(monkeypatch: pytest.MonkeyPatch):
    original = dr_compiler._v03_compatibility_aliases

    def drift_modules(*args, **kwargs):
        aliases = original(*args, **kwargs)
        aliases["modules"] = aliases["modules"][:-1]
        return aliases

    monkeypatch.setattr(dr_compiler, "_v03_compatibility_aliases", drift_modules)
    result = _compile()
    response = client.post("/dr/export", json={"workflow": _workflow()})
    summary = result["metadata"]["v03_audit_report"]["summary"]

    assert result["valid"] is False
    assert result["compiled_dr"] is None
    assert response.status_code == 422
    assert summary["frozen_root_field_check_pass"] == 1
    assert summary["compatibility_check_fail"] >= 1
    assert any(item["code"] == "DR_EXPORT_COMPATIBILITY_PROJECTION_DRIFT" for item in result["errors"])


def test_required_compatibility_projection_drift_blocks_compile_and_export(monkeypatch: pytest.MonkeyPatch):
    original = dr_compiler._v03_compatibility_aliases

    def drift(*args, **kwargs):
        aliases = original(*args, **kwargs)
        aliases["memory_policy"]["retention_policy"] = "drifted"
        return aliases

    monkeypatch.setattr(dr_compiler, "_v03_compatibility_aliases", drift)
    result = _compile()
    response = client.post("/dr/export", json={"workflow": _workflow()})

    assert result["valid"] is False
    assert result["compiled_dr"] is None
    assert response.status_code == 422
    assert any(item["code"] == "DR_EXPORT_COMPATIBILITY_PROJECTION_DRIFT" for item in result["errors"])


def test_pending_module_safety_status_cannot_project_as_valid(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(dr_compiler, "_synchronize_layer3_module_outputs", lambda _collection: None)

    result = _compile()

    assert result["valid"] is False
    assert result["compiled_dr"] is None
    assert any(
        item["code"] in {"DR_SAFETY_PROJECTION_INCONSISTENT", "DR_SAFETY_VALIDATION_STATUS_DRIFT"}
        for item in result["errors"]
    )


def test_compiled_safety_modules_and_top_policy_share_final_validation_status():
    dr = _valid_dr()
    top_safety = dr["payload"]["safety_policy"]
    checked = 0

    for module in dr["payload"]["modules"]:
        for output_key, output in module.get("outputs", {}).items():
            if not isinstance(output, dict) or "compile_validation_status" not in output:
                continue
            checked += 1
            assert output["compile_validation_status"] in {"valid", "invalid"}
            assert top_safety[output_key] == output
    assert checked == 5


def test_memory_router_stale_output_is_rebuilt_from_current_node_config_without_mutating_canvas():
    modules = _catalog_modules()
    router = _memory_router_module(modules)
    stale = deepcopy(_memory_router_output(router))
    stale["request_contract"]["operations"] = ["read", "write", "view", "clear"]
    stale["request_contract"].pop("canonical_operations", None)
    stale["request_contract"].pop("accepted_operations", None)
    stale["request_contract"].pop("operation_aliases", None)
    stale_types = ["short_term_memory", "profile_memory", "preference_memory", "interaction_log"]
    stale["memory_type_policy"]["allowed_memory_types"] = stale_types
    stale["access_policy"] = {
        operation: deepcopy(stale_types) for operation in ("read", "write", "view", "clear")
    }
    stale["access_policy"].update(
        {
            "session_only": ["short_term_memory"],
            "forbidden_memory": ["api_key", "token", "credential", "base_url"],
        }
    )
    router["outputs"]["memory_provider_route_policy"] = deepcopy(stale)
    output_node = next(node for node in router["module_graph"]["nodes"] if node["node_type"] == "module_output")
    output_node["outputs"]["memory_provider_route_policy"] = deepcopy(stale)
    before = deepcopy(modules)

    result = _compile(modules=modules)

    assert result["valid"] is True
    assert modules == before
    dr = result["compiled_dr"]
    compiled_router = _memory_router_module(dr["payload"]["modules"])
    module_output = _memory_router_output(compiled_router)
    frozen_policy = dr["payload"]["memory_policy"]
    top_policy = frozen_policy["memory_policy_extensions"]
    expected_types = [
        "short_term_memory",
        "preference_memory",
        "event_memory",
        "relationship_memory",
        "interaction_log",
    ]
    expected_operations = ["read", "write", "update", "delete"]

    assert module_output == compiled_router["outputs"]["memory_provider_route_policy"]
    assert module_output == top_policy["memory_provider_router"]
    assert frozen_policy == dr["memory_policy"]
    assert top_policy["memory_types"] == expected_types
    assert frozen_policy["memory_types"] == [
        "short_term_memory",
        "profile_memory",
        "preference_memory",
        "interaction_log",
    ]
    assert dr["legacy_blueprint"]["memory_config"]["memory_types"] == frozen_policy["memory_types"]
    assert module_output["memory_type_policy"]["allowed_memory_types"] == expected_types
    assert "profile_memory" not in json.dumps(top_policy, ensure_ascii=False)
    assert dr["modules"] == dr["payload"]["modules"]
    assert "modules" not in dr["payload"]["graph_snapshot"]
    assert "modules" not in dr["legacy_blueprint"]
    assert module_output["request_contract"]["operations"] == expected_operations
    assert module_output["request_contract"]["canonical_operations"] == expected_operations
    assert module_output["request_contract"]["accepted_operations"] == [
        *expected_operations,
        "view",
        "clear",
    ]
    assert module_output["request_contract"]["operation_aliases"] == {"view": "read", "clear": "delete"}
    assert set(module_output["access_policy"]) == {
        *expected_operations,
        "session_only",
        "forbidden_memory",
    }
    assert any(
        item["code"] == "DR_MEMORY_ROUTER_PROJECTION_CONSISTENT"
        for item in dr["audit_report"]["findings"]
    )


def test_memory_router_node_config_mismatch_blocks_compile_and_export():
    modules = _catalog_modules()
    router = _memory_router_module(modules)
    classifier = next(
        node
        for node in router["module_graph"]["nodes"]
        if node["node_id"] == "memory_router_operation_classifier"
    )
    classifier["params"]["canonical_operations"] = ["read", "write", "view", "clear"]
    canvas = {"workflow": _workflow(), "modules": modules}

    result = compile_dr_result_v0_3(canvas)
    response = client.post("/dr/export", json=canvas)

    assert result["valid"] is False
    assert result["compiled_dr"] is None
    assert any(item["code"] == "DR_MEMORY_ROUTER_NODE_CONFIG_INCONSISTENT" for item in result["errors"])
    assert response.status_code == 422


def test_short_term_memory_stays_in_session_state_and_never_reaches_persistent_store():
    dr = _valid_dr()
    resident_runtime.create_runtime_state_from_dr(dr)
    resident_id = dr["manifest"]["resident_id"]
    payload = {
        "op": "write",
        "resident_id": resident_id,
        "namespace": "default",
        "memory_type": "short_term_memory",
        "entry": {"current_task": "P0 verification"},
    }

    write = resident_runtime.execute_memory_operation(payload)
    gated_read = resident_runtime.execute_memory_operation({**payload, "op": "read"})
    persistent_read = provider_adapters.route_provider_for_engine(
        "memory_mock",
        {"op": "read", "resident_id": resident_id, "namespace": "default", "memory_type": "short_term_memory"},
    )

    assert write["storage_backend"] == "session_state"
    assert gated_read["entries"] == [{"current_task": "P0 verification"}]
    assert persistent_read["count"] == 0


def test_preference_requires_explicit_expression_or_confirmation():
    dr = _valid_dr()
    resident_runtime.create_runtime_state_from_dr(dr)
    resident_id = dr["manifest"]["resident_id"]
    base = {
        "op": "write",
        "resident_id": resident_id,
        "namespace": "default",
        "memory_type": "preference_memory",
        "entry": {"preference_key": "color", "preference_value": "blue"},
    }

    denied = resident_runtime.execute_memory_operation(base)
    allowed = resident_runtime.execute_memory_operation(
        {**base, "entry": {**base["entry"], "confirmed": True}}
    )

    assert denied["status"] == "denied"
    assert denied["reason"] == "preference_requires_explicit_expression_or_confirmation"
    assert allowed["status"] == "success"
    assert allowed["count"] == 1


def test_policy_only_event_memory_degrades_safely_and_relationship_jump_is_denied():
    dr = _valid_dr()
    resident_runtime.create_runtime_state_from_dr(dr)
    resident_id = dr["manifest"]["resident_id"]

    event = resident_runtime.execute_memory_operation(
        {
            "op": "write",
            "resident_id": resident_id,
            "memory_type": "event_memory",
            "entry": {
                "brief_summary": "project milestone",
                "meaning": "important progress",
                "full_chat_log": "must not persist",
                "raw_sensitive_content": "must not persist",
            },
        }
    )
    relationship = resident_runtime.execute_memory_operation(
        {
            "op": "write",
            "resident_id": resident_id,
            "memory_type": "relationship_memory",
            "entry": {"from_level": 1, "to_level": 4},
        }
    )

    assert event["status"] == "denied"
    assert event["reason"] == "memory_policy_only_not_runtime_supported"
    assert event["count"] == 0
    assert relationship["status"] == "denied"
    assert relationship["reason"] == "relationship_single_interaction_level_jump_forbidden"


@pytest.mark.parametrize(
    ("request_overrides", "expected_reason"),
    (
        ({"entry": {"inferred": True}}, "inferred_facts_forbidden"),
        ({"entry": {"sensitive": True}}, "sensitive_data_requires_explicit_confirmation"),
        ({"entry": {"source": "resident_setting"}}, "setting_content_cannot_be_user_memory"),
        ({"requesting_resident_id": "another_resident"}, "cross_resident_private_memory_forbidden"),
    ),
)
def test_memory_restrictions_deny_before_provider_call(monkeypatch, request_overrides: dict, expected_reason: str):
    dr = _valid_dr()
    resident_runtime.create_runtime_state_from_dr(dr)
    resident_id = dr["manifest"]["resident_id"]
    calls: list[tuple[str, dict]] = []

    def provider_spy(engine_id: str, payload: dict) -> dict:
        calls.append((engine_id, payload))
        return {"status": "success", "count": 1}

    monkeypatch.setattr(resident_runtime, "route_provider_for_engine", provider_spy)
    request = {
        "op": "write",
        "resident_id": resident_id,
        "memory_type": "event_memory",
        "entry": {"brief_summary": "candidate"},
        **request_overrides,
    }

    result = resident_runtime.execute_memory_operation(request)

    assert result["status"] == "denied"
    assert result["reason"] == expected_reason
    assert calls == []


def test_compiled_memory_access_policy_can_deny_write_before_provider_call(monkeypatch):
    dr = _valid_dr()
    dr["payload"]["memory_policy"]["memory_policy_extensions"]["memory_provider_router"]["access_policy"]["write"] = []
    resident_runtime.create_runtime_state_from_dr(dr)
    resident_id = dr["manifest"]["resident_id"]
    calls: list[tuple[str, dict]] = []

    def provider_spy(engine_id: str, payload: dict) -> dict:
        calls.append((engine_id, payload))
        return {"status": "success", "count": 1}

    monkeypatch.setattr(resident_runtime, "route_provider_for_engine", provider_spy)

    result = resident_runtime.execute_memory_operation(
        {
            "op": "write",
            "resident_id": resident_id,
            "memory_type": "preference_memory",
            "entry": {"preference_key": "color", "preference_value": "blue", "confirmed": True},
        }
    )

    assert result["status"] == "denied"
    assert result["reason"] == "memory_type_not_allowed_for_write"
    assert calls == []


def test_allowed_memory_api_result_shape_stays_compatible():
    dr = _valid_dr()
    resident_runtime.create_runtime_state_from_dr(dr)
    resident_id = dr["manifest"]["resident_id"]
    payload = {
        "op": "view",
        "resident_id": resident_id,
        "namespace": "default",
        "memory_type": "interaction_log",
        "limit": 20,
    }

    direct = provider_adapters.route_provider_for_engine("memory_mock", payload)
    gated = resident_runtime.execute_memory_operation(payload)

    assert set(gated) == set(direct)
