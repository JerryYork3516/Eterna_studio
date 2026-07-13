"""Stage 6.2 DR Compiler v0.1 acceptance — Canvas -> .digital_resident.

Run: cd apps/api && .venv/bin/python -m pytest tests/test_stage6_2_dr_compiler.py -q
"""

from __future__ import annotations

import json

from fastapi.testclient import TestClient

from app.main import app
from app.services.dr_compiler import (
    DR_VERSION,
    FILE_SUFFIX,
    FILE_TYPE,
    compile_dr,
    compile_dr_v0_3,
    dr_filename,
    mock_load_dr,
)
from app.registry.module_catalog import get_module_catalog

client = TestClient(app)

DR_STRUCT_FIELDS = (
    "resident",
    "layers",
    "modules",
    "slots",
    "runtime_requirements",
    "memory_config",
    "safety_policy",
    "audit",
    "compile_info",
)


def _canvas_13() -> dict:
    nodes = [{"node_id": f"layer_{i}"} for i in range(1, 14)]
    return {"workflow": {"name": "Aria Demo", "template_type": "schema_v04", "nodes": nodes, "edges": []}}


# --- compiler service --------------------------------------------------------
def test_dr_has_all_struct_fields_and_metadata():
    dr = compile_dr(_canvas_13())
    assert dr["file_type"] == FILE_TYPE  # 1
    assert dr["dr_version"] == DR_VERSION
    assert dr["schema_version"] == "0.4.0"
    for field in DR_STRUCT_FIELDS:
        assert field in dr  # 2


def test_blueprint_has_13_layers_and_modules_slots():
    dr = compile_dr(_canvas_13())
    assert len(dr["layers"]) == 13  # 3
    assert len(dr["modules"]) > 0
    assert len(dr["slots"]) > 0


def test_explicit_empty_workflow_modules_do_not_fall_back_to_the_catalog():
    canvas = _canvas_13()
    canvas["workflow"]["modules"] = []

    dr = compile_dr(canvas)

    assert dr["modules"] == []


def test_audit_valid_true_for_full_canvas():
    dr = compile_dr(_canvas_13())
    assert dr["audit"]["valid"] is True  # 4
    assert not [f for f in dr["audit"]["findings"] if f["status"] == "FAIL"]


def test_filename_suffix_is_digital_resident():
    dr = compile_dr(_canvas_13())
    name = dr_filename(dr)
    assert name.endswith(FILE_SUFFIX)  # 5
    assert not name.endswith(".json")


def test_v03_filename_prefers_basic_identity_export_name_and_codename_slug():
    modules = [module.model_dump(mode="json") for module in get_module_catalog()]
    basic_identity = next(module for module in modules if module["module_id"] == "module_basic_identity")
    field_input = next(node for node in basic_identity["module_graph"]["nodes"] if node["node_type"] == "field_input")
    for field in field_input["params"]["fields"]:
        if field["field_id"] == "name":
            field["value"] = "林瑄"
        if field["field_id"] == "codename":
            field["value"] = "linxuan_hum_cn_xian_01"
        if field["field_id"] == "resident_id":
            field["value"] = "dr_eterna_hum_cn_xian_linxuan_0001"
        if field["field_id"] == "export_name":
            field["value"] = "linxuan"

    fields_by_id = {field["field_id"]: field["value"] for field in field_input["params"]["fields"]}
    module_output = next(node for node in basic_identity["module_graph"]["nodes"] if node["node_type"] == "module_output")
    module_output["outputs"]["basic_identity"]["fields"] = fields_by_id
    basic_identity["outputs"]["basic_identity"]["fields"] = fields_by_id

    canvas = _canvas_13()
    canvas["modules"] = modules
    dr = compile_dr_v0_3(canvas)
    assert dr_filename(dr) == "linxuan.digital_resident"

    fields_by_id["export_name"] = ""
    module_output["outputs"]["basic_identity"]["fields"] = fields_by_id
    basic_identity["outputs"]["basic_identity"]["fields"] = fields_by_id
    dr_without_export_name = compile_dr_v0_3(canvas)
    assert dr_filename(dr_without_export_name) == "linxuan.digital_resident"


# --- validation checks -------------------------------------------------------
def test_duplicate_module_id_fails():
    canvas = _canvas_13()
    canvas["modules"] = [
        {"module_id": "dup", "module_type": "t", "layer_id": "layer_1"},
        {"module_id": "dup", "module_type": "t", "layer_id": "layer_2"},
    ]
    dr = compile_dr(canvas)
    codes = [f["code"] for f in dr["audit"]["findings"] if f["status"] == "FAIL"]
    assert "DR_MODULE_ID_DUPLICATE" in codes
    assert dr["audit"]["valid"] is False


def test_illegal_provider_binding_fails():
    canvas = _canvas_13()
    canvas["slots"] = [{"slot_id": "s_llm", "slot_type": "llm", "provider": "openai"}]
    canvas["modules"] = []  # avoid unrelated slot-match noise
    dr = compile_dr(canvas)
    codes = [f["code"] for f in dr["audit"]["findings"] if f["status"] == "FAIL"]
    assert "DR_ILLEGAL_PROVIDER" in codes
    assert dr["audit"]["valid"] is False


def test_slot_type_unmatched_fails():
    canvas = _canvas_13()
    canvas["modules"] = [{"module_id": "m1", "module_type": "voice", "layer_id": "layer_1", "slot_type": "tts"}]
    canvas["slots"] = [{"slot_id": "s_llm", "slot_type": "llm"}]
    dr = compile_dr(canvas)
    codes = [f["code"] for f in dr["audit"]["findings"] if f["status"] == "FAIL"]
    assert "DR_SLOT_TYPE_UNMATCHED" in codes


def test_missing_canvas_layer_warns_but_stays_valid():
    dr = compile_dr({"workflow": {"name": "Few", "nodes": [{"node_id": "layer_1"}]}})
    findings = dr["audit"]["findings"]
    assert any(f["code"] == "DR_LAYER_NOT_ON_CANVAS" and f["status"] == "WARNING" for f in findings)
    assert dr["audit"]["valid"] is True  # warning alone does not invalidate


# --- API: Stage 6.3.3 compile (JSON, no download) vs export (download) -------
def test_compile_endpoint_returns_json_not_file():
    resp = client.post("/dr/compile", json=_canvas_13())
    assert resp.status_code == 200
    assert "application/json" in resp.headers["content-type"]  # JSON, not a file
    assert "content-disposition" not in {k.lower() for k in resp.headers}
    body = resp.json()
    for key in (
        "valid", "errors", "warnings", "module_audit", "layer_audit", "compile_audit",
        "orchestration_compatibility", "pseudo_dag", "dr_version", "compiled_dr", "filename", "metadata",
    ):
        assert key in body
    assert body["valid"] is True
    assert body["dr_version"] == "0.3"
    assert body["compiled_dr"] is not None
    assert body["compiled_dr"]["dr_version"] == "0.3"
    assert body["compiled_dr"]["dr_schema_version"] == "0.3.0"
    assert body["dr_payload"]["runtime_plan"]["steps"]
    assert body["filename"].endswith(FILE_SUFFIX)


def test_compile_audit_blocks_secret():
    modules = [module.model_dump(mode="json") for module in get_module_catalog()]
    modules[0]["config"]["api_key"] = "sk-test-secret"
    modules[0]["config"]["access_token"] = "access-token"
    modules[0]["config"]["base_url_hint"] = "local runtime hint"
    modules[0]["config"]["token_policy"] = "reference-only"
    modules[0]["config"]["credential_ref"] = "runtime-profile"
    modules[0]["config"]["api_key_ref"] = "runtime-profile"
    modules[0]["config"]["provider_requirement"] = {"mode": "mock"}
    modules[0]["config"]["provider_type"] = "mock"
    canvas = _canvas_13()
    canvas["modules"] = modules

    body = client.post("/dr/compile", json=canvas).json()
    codes = {finding["code"] for finding in body["errors"]}
    paths = {finding["path"] for finding in body["errors"]}
    assert body["valid"] is False
    assert body["compiled_dr"] is None
    assert "DR_SECRET_FIELD" in codes
    assert any(path.endswith(".api_key") for path in paths)
    assert any(path.endswith(".access_token") for path in paths)
    assert not any(path.endswith(".base_url_hint") for path in paths)
    assert not any(path.endswith(".token_policy") for path in paths)
    assert not any(path.endswith(".credential_ref") for path in paths)
    assert not any(path.endswith(".api_key_ref") for path in paths)
    assert not any(path.endswith(".provider_requirement") for path in paths)
    assert not any(path.endswith(".provider_type") for path in paths)


def test_compile_frontend_export_load_preview_intact():
    compile_body = client.post("/dr/compile", json=_canvas_13()).json()

    assert compile_body["valid"] is True
    assert compile_body["compiled_dr"] is not None
    downloadable_compiled_dr = compile_body["compiled_dr"]
    assert downloadable_compiled_dr["dr_version"] == "0.3"

    load_resp = client.post("/dr/load", json={"dr": downloadable_compiled_dr})
    assert load_resp.status_code == 200
    assert load_resp.json()["loaded"] is True


def test_compile_v03_endpoint_returns_json_not_file():
    resp = client.post("/dr/compile", json=_canvas_13())
    assert resp.status_code == 200
    assert "application/json" in resp.headers["content-type"]
    body = resp.json()
    assert body["valid"] is True
    assert body["dr_version"] == "0.3"
    assert body["compiled_dr"]["dr_version"] == "0.3"
    assert body["dr_payload"]["runtime_plan"]["steps"]


V0_3_ROOT_FIELDS = (
    "file_type",
    "dr_version",
    "dr_schema_version",
    "protocol_version",
    "revision",
    "created_at",
    "updated_at",
    "not_executable",
    "manifest",
    "payload",
    "compile_info",
    "audit_report",
)


def test_compiled_dr_is_v0_3_envelope():
    body = client.post("/dr/compile", json=_canvas_13()).json()
    compiled = body["compiled_dr"]
    for field in V0_3_ROOT_FIELDS:
        assert field in compiled
    assert compiled["dr_version"] == "0.3"
    assert compiled["dr_schema_version"] == "0.3.0"
    assert compiled["not_executable"] is True
    assert "audit" in compiled  # legacy compatibility only


def test_compile_invalid_canvas_blocks_export():
    canvas = _canvas_13()
    canvas["modules"] = [
        {"module_id": "dup", "module_type": "t", "layer_id": "layer_1"},
        {"module_id": "dup", "module_type": "t", "layer_id": "layer_2"},
    ]
    body = client.post("/dr/compile", json=canvas).json()
    assert body["valid"] is False
    assert body["compiled_dr"] is None  # invalid => nothing downloadable
    assert any(f["code"] == "DR_MODULE_ID_DUPLICATE" for f in body["errors"])


def test_export_endpoint_returns_file_when_valid():
    resp = client.post("/dr/export", json=_canvas_13())
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/x-digital-resident"
    assert resp.headers["content-disposition"].endswith(f'{FILE_SUFFIX}"')
    assert resp.headers["x-dr-filename"].endswith(FILE_SUFFIX)
    assert resp.headers["x-dr-version"] == "0.3"
    body = json.loads(resp.text)
    assert body["file_type"] == FILE_TYPE
    assert body["dr_version"] == "0.3"
    assert body["dr_schema_version"] == "0.3.0"
    assert body["not_executable"] is True
    assert body["manifest"]["resident_id"]
    assert body["payload"]["runtime_plan"]["steps"]
    # Policy deny-lists may name ``api_key``; the exported DR must not contain
    # an actual secret-bearing field.
    assert '"api_key":' not in json.dumps(body, ensure_ascii=False)


def test_export_v03_endpoint_returns_file_when_valid():
    resp = client.post("/dr/export", json=_canvas_13())
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/x-digital-resident"
    assert resp.headers["x-dr-version"] == "0.3"
    body = json.loads(resp.text)
    assert body["file_type"] == FILE_TYPE
    assert body["dr_version"] == "0.3"
    assert body["dr_schema_version"] == "0.3.0"
    assert body["not_executable"] is True
    assert body["manifest"]["resident_id"]
    assert body["payload"]["runtime_plan"]["steps"]


def test_valid_export_never_emits_v0_1_payload():
    """A valid compile must not export a v0.1 payload (regression guard)."""
    body = client.post("/dr/compile", json=_canvas_13()).json()
    assert body["valid"] is True
    assert body["compiled_dr"]["dr_version"] != "0.1"
    assert body["compiled_dr"]["dr_version"] == "0.3"


def test_export_rejected_when_invalid():
    canvas = _canvas_13()
    canvas["slots"] = [{"slot_id": "s_llm", "slot_type": "llm", "provider": "openai"}]
    canvas["modules"] = []
    resp = client.post("/dr/export", json=canvas)
    assert resp.status_code == 422


# --- runtime v6.1 mock load --------------------------------------------------
def test_runtime_can_mock_load_dr():
    dr = compile_dr(_canvas_13())
    loaded = mock_load_dr(dr)
    assert loaded["loaded"] is True  # 5: runtime can read the DR
    assert loaded["layer_count"] == 13
    assert loaded["audit_valid"] is True


def test_dr_load_endpoint():
    dr = compile_dr_v0_3(_canvas_13())
    resp = client.post("/dr/load", json={"dr": dr})
    assert resp.status_code == 200
    assert resp.json()["loaded"] is True


# --- regression: runtime kernel untouched ------------------------------------
def test_runtime_resident_step_still_works():
    resp = client.post("/runtime/resident/step", json={"workflow": {}, "input_text": "hi", "resident_id": "r_dr_reg"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["mock"] is True
    steps = [e["step"] for e in body["execution_trace"]]
    for required in ("input", "memory.read", "reasoning", "action", "memory.write", "output"):
        assert required in steps
