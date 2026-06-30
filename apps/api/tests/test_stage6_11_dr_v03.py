"""Stage 6.11 DR v0.3 envelope regression tests.

These tests guard the new declarative envelope without touching runtime logic.
"""

from __future__ import annotations

import json

from fastapi.testclient import TestClient

from app.main import app
from app.services.dr_compiler import compile_dr_result_v0_3, compile_dr_v0_3, mock_load_dr_v0_3

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


def test_compile_result_and_export_use_v03_payload():
    body = compile_dr_result_v0_3(_canvas_13())
    assert body["valid"] is True
    assert body["dr_version"] == "0.3"
    assert body["compiled_dr"]["dr_version"] == "0.3"
    assert body["dr_payload"]["runtime_plan"]["steps"]

    resp = client.post("/dr/compile-v0.3", json=_canvas_13())
    assert resp.status_code == 200
    compile_body = resp.json()
    assert compile_body["valid"] is True
    assert compile_body["dr_version"] == "0.3"
    assert compile_body["compiled_dr"]["dr_version"] == "0.3"
    assert compile_body["compiled_dr"]["dr_schema_version"] == "0.3.0"
    assert compile_body["compiled_dr"]["not_executable"] is True

    export_resp = client.post("/dr/export-v0.3", json=_canvas_13())
    assert export_resp.status_code == 200
    assert export_resp.headers["content-type"] == "application/x-digital-resident"
    exported = json.loads(export_resp.text)
    assert exported["dr_version"] == "0.3"
    assert exported["dr_schema_version"] == "0.3.0"
    assert exported["not_executable"] is True

    load_resp = client.post("/dr/load-v0.3", json={"dr": body["compiled_dr"]})
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
