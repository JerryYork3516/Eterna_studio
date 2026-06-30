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


def test_audit_valid_true_for_full_canvas():
    dr = compile_dr(_canvas_13())
    assert dr["audit"]["valid"] is True  # 4
    assert not [f for f in dr["audit"]["findings"] if f["status"] == "FAIL"]


def test_filename_suffix_is_digital_resident():
    dr = compile_dr(_canvas_13())
    name = dr_filename(dr)
    assert name.endswith(FILE_SUFFIX)  # 5
    assert not name.endswith(".json")


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
    assert "api_key" not in json.dumps(body, ensure_ascii=False)


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
