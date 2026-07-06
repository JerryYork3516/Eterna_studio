"""Stage 6.11 DR v0.3 envelope regression tests.

These tests guard the new declarative envelope without touching runtime logic.
"""

from __future__ import annotations

import json

from fastapi.testclient import TestClient

from app.main import app
from app.services.dr_compiler import compile_dr_result_v0_3, compile_dr_v0_3, mock_load_dr_v0_3
from app.registry.module_catalog import get_module_catalog

client = TestClient(app)


def _canvas_13() -> dict:
    nodes = [{"node_id": f"layer_{i}"} for i in range(1, 14)]
    return {"workflow": {"name": "Aria Demo", "template_type": "schema_v04", "nodes": nodes, "edges": []}}


def test_compile_returns_v03_envelope():
    dr = compile_dr_v0_3(_canvas_13())
    assert dr["file_type"] == "digital_resident"
    assert dr["dr_version"] == "0.3"
    assert dr["dr_schema_version"] == "0.3.0"
    assert dr["protocol_version"] == "0.4.0"
    assert dr["not_executable"] is True
    for key in ("revision", "created_at", "updated_at", "manifest", "payload", "compile_info", "audit_report"):
        assert key in dr


def test_manifest_and_payload_contain_required_fields():
    dr = compile_dr_v0_3(_canvas_13())
    manifest = dr["manifest"]
    payload = dr["payload"]
    assert manifest["resident_id"]
    assert manifest["resident_name"]
    assert manifest["dr_schema_version"] == "0.3.0"
    assert manifest["source_protocol_version"] == "0.4.0"
    assert manifest["compatible_runtime"]
    assert isinstance(manifest["required_capabilities"], list)
    assert "checksum" in manifest
    for key in (
        "resident_identity",
        "resident_blueprint",
        "13_layers_snapshot",
        "modules",
        "slots",
        "runtime_requirements",
        "provider_requirements",
        "memory_policy",
        "memory_config",
        "lattice_config",
        "voice_config",
        "screen_capability_declaration",
        "safety_policy",
        "runtime_plan",
        "fallback_routes",
    ):
        assert key in payload


def test_runtime_plan_and_screen_declaration_are_mock_only():
    dr = compile_dr_v0_3(_canvas_13())
    runtime_plan = dr["payload"]["runtime_plan"]
    forbidden = set(runtime_plan["forbidden"])
    assert {"agent_loop", "cloud_task_queue", "bridge_executor", "auto_click", "screen_control", "autonomous_action"}.issubset(forbidden)
    screen_decl = dr["payload"]["screen_capability_declaration"]
    assert screen_decl["mock_only"] is True
    assert screen_decl["no_execution"] is True
    assert screen_decl["no_real_screen_read"] is True
    assert screen_decl["no_auto_click"] is True
    assert screen_decl["no_accessibility_automation"] is True
    assert screen_decl["no_cross_app_control"] is True


def test_provider_requirements_do_not_include_secrets():
    dr = compile_dr_v0_3(_canvas_13())
    providers = json.dumps(dr["payload"]["provider_requirements"], ensure_ascii=False)
    for forbidden in ("api_key", "base_url", "token", "credential", "secret"):
        assert forbidden not in providers


def test_identity_profile_assembled():
    dr = compile_dr_v0_3(_canvas_13())
    layer_outputs = dr["payload"]["graph_snapshot"]["layer_outputs"]
    identity_profile = layer_outputs["identity_profile"]

    assert identity_profile["resident_id"] == dr["manifest"]["resident_id"]
    assert identity_profile["name"] == dr["manifest"]["resident_name"]
    for key in ("basic_identity", "growth_background", "career_identity", "existence_mode", "identity_anchor"):
        assert key in identity_profile
    assert layer_outputs["layer_1"]["identity_profile"] == identity_profile


def test_identity_profile_assembled_from_module_outputs():
    dr = compile_dr_v0_3(_canvas_13())
    modules = {module["module_id"]: module for module in dr["payload"]["modules"]}
    identity_profile = dr["payload"]["graph_snapshot"]["layer_outputs"]["identity_profile"]

    expected_outputs = {
        "module_basic_identity": "basic_identity",
        "module_growth_background": "growth_background",
        "module_career_identity": "career_identity",
        "module_existence_mode": "existence_mode",
        "module_identity_anchor": "identity_anchor",
    }
    for module_id, output_key in expected_outputs.items():
        module_output = next(
            node for node in modules[module_id]["module_graph"]["nodes"] if node["node_type"] == "module_output"
        )
        assert identity_profile[output_key] == module_output["outputs"][output_key]


def test_identity_core_aggregator_outputs_exist():
    dr = compile_dr_v0_3(_canvas_13())
    aggregator = dr["payload"]["graph_snapshot"]["layer_outputs"]["layer_1"]["identity_core_aggregator"]

    for key in (
        "identity_profile",
        "locked_core_fields",
        "versioned_core_fields",
        "update_rules",
        "identity_summary",
        "module_audit",
        "layer_audit",
    ):
        assert key in aggregator
    assert aggregator["module_audit"]["ok"] is True
    assert aggregator["layer_audit"]["ok"] is True


def test_v03_contract_unchanged_for_aftelle():
    dr = compile_dr_v0_3(_canvas_13())

    assert dr["manifest"]["resident_id"]
    assert dr["payload"]["resident_identity"]["resident_id"] == dr["manifest"]["resident_id"]
    assert dr["payload"]["resident_identity"]["name"] == dr["manifest"]["resident_name"]
    assert dr["payload"]["lattice_config"]["schema_version"] == "0.3.0"
    assert dr["payload"]["voice_config"]["schema_version"] == "0.3.0"
    assert dr["payload"]["safety_policy"]["no_secret_in_dr"] is True
    assert dr["payload"]["safety_policy"]["no_direct_provider_binding"] is True
    assert dr["lattice_config"] == dr["payload"]["lattice_config"]
    assert dr["voice_config"] == dr["payload"]["voice_config"]
    assert dr["safety_policy"] == dr["payload"]["safety_policy"]


def test_identity_profile_optional_and_fallback_safe():
    dr = compile_dr_v0_3(_canvas_13())
    dr["payload"]["graph_snapshot"].pop("layer_outputs", None)

    loaded = mock_load_dr_v0_3(dr)
    assert loaded["loaded"] is True
    assert loaded["resident_id"] == dr["manifest"]["resident_id"]


def test_identity_compile_time_nodes_not_in_runtime_plan():
    dr = compile_dr_v0_3(_canvas_13())
    runtime_steps = json.dumps(dr["payload"]["runtime_plan"]["steps"], ensure_ascii=False)

    for node_type in ("field_input", "structure_normalize", "validation", "update_rule", "module_output", "layer_aggregator"):
        assert node_type not in runtime_steps


def test_legacy_module_output_fallback_warning():
    modules = [module.model_dump(mode="json") for module in get_module_catalog()]
    modules.append(
        {
            "module_id": "legacy_persona_output",
            "module_type": "legacy_persona",
            "module_name": "Legacy Persona Output",
            "module_version": "0.1.0",
            "layer_id": "layer_2",
            "module_graph": {"nodes": []},
            "outputs": {"legacy_persona": {"fields": {}}, "module_output": "legacy_persona"},
            "category": "persona",
            "status": "MOCK",
            "runtime_enabled": False,
            "no_execution": True,
        }
    )
    canvas = _canvas_13()
    canvas["modules"] = modules

    body = compile_dr_result_v0_3(canvas)
    assert body["valid"] is True
    assert any(
        finding["status"] == "WARNING" and finding["code"] == "DR_IDENTITY_LEGACY_FIELD_INPUT_MISSING"
        for finding in body["warnings"]
    )


def test_compile_result_and_export_use_v03_payload():
    body = compile_dr_result_v0_3(_canvas_13())
    assert body["valid"] is True
    assert body["dr_version"] == "0.3"
    assert body["compiled_dr"]["dr_version"] == "0.3"
    assert body["dr_payload"]["runtime_plan"]["steps"]

    resp = client.post("/dr/compile", json=_canvas_13())
    assert resp.status_code == 200
    compile_body = resp.json()
    assert compile_body["valid"] is True
    assert compile_body["dr_version"] == "0.3"
    assert compile_body["compiled_dr"]["dr_version"] == "0.3"
    assert compile_body["compiled_dr"]["dr_schema_version"] == "0.3.0"
    assert compile_body["compiled_dr"]["not_executable"] is True

    export_resp = client.post("/dr/export", json=_canvas_13())
    assert export_resp.status_code == 200
    assert export_resp.headers["content-type"] == "application/x-digital-resident"
    exported = json.loads(export_resp.text)
    assert exported["dr_version"] == "0.3"
    assert exported["dr_schema_version"] == "0.3.0"
    assert exported["not_executable"] is True

    load_resp = client.post("/dr/load", json={"dr": body["compiled_dr"]})
    assert load_resp.status_code == 200
    assert load_resp.json()["loaded"] is True


def test_invalid_canvas_blocks_export():
    canvas = _canvas_13()
    canvas["modules"] = [
        {"module_id": "dup", "module_type": "t", "layer_id": "layer_1"},
        {"module_id": "dup", "module_type": "t", "layer_id": "layer_2"},
    ]
    body = client.post("/dr/compile", json=canvas).json()
    assert body["valid"] is False
    assert body["compiled_dr"] is None
    assert client.post("/dr/export", json=canvas).status_code == 422


def test_mock_loader_reads_v03_dr():
    dr = compile_dr_v0_3(_canvas_13())
    loaded = mock_load_dr_v0_3(dr)
    assert loaded["loaded"] is True
    assert loaded["layer_count"] == 13
    assert loaded["audit_valid"] is True
