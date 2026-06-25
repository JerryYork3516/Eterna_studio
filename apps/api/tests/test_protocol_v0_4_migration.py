"""Stage 5 task 3/3 acceptance — Migration / runtime compatibility / final.

Run: cd apps/api && .venv/bin/python -m pytest tests/test_protocol_v0_4_migration.py -q
"""

from __future__ import annotations

import json

from fastapi.testclient import TestClient

from app.main import app
from app.models.v0_4 import CANONICAL_LAYERS, PersonaV04, WorkflowV04

client = TestClient(app)

V04_FILLED_FIELDS = {"modules", "permissions", "risk_level", "audit_log", "extensions", "metadata"}


def _demo_workflow_v0_3() -> dict:
    return client.post("/templates/persona-builder", json={"name": "Demo", "ui_language": "en"}).json()["workflow"]


# --- I. Migration: schema/protocol version + filled defaults --------------
def test_migration_versions_and_defaults():
    wf3 = _demo_workflow_v0_3()
    assert wf3["schema_version"] == "0.3.0"
    wf4 = client.post("/protocol/workflow/migrate", json={"workflow": wf3}).json()["workflow"]
    assert wf4["schema_version"] == "0.4.0"
    assert wf4["protocol_version"] == "0.4.0"
    for field in V04_FILLED_FIELDS:
        assert field in wf4, f"missing filled field {field}"


def test_migration_no_field_loss_via_extensions_legacy():
    wf3 = _demo_workflow_v0_3()
    wf4 = client.post("/protocol/workflow/migrate", json={"workflow": wf3}).json()["workflow"]
    # The full original v0.3 payload is preserved; nothing is dropped.
    legacy = wf4["extensions"]["legacy"]
    assert legacy["schema_version"] == "0.3.0"
    assert {n["id"] for n in legacy["nodes"]} == {n["id"] for n in wf3["nodes"]}
    assert len(legacy["nodes"]) == len(wf3["nodes"])


def test_migration_keeps_13_layers_semantics():
    wf3 = _demo_workflow_v0_3()
    wf4 = client.post("/protocol/workflow/migrate", json={"workflow": wf3}).json()["workflow"]
    canonical_ids = [lid for lid, _n, _o in CANONICAL_LAYERS]
    assert [l["layer_id"] for l in wf4["layers"]] == canonical_ids
    assert [l["layer_name"] for l in wf4["layers"]] == [n for _l, n, _o in CANONICAL_LAYERS]
    assert [l["layer_order"] for l in wf4["layers"]] == [o for _l, _n, o in CANONICAL_LAYERS]


# --- II. Export / load / validate round-trip ------------------------------
def test_migrated_workflow_loadable_and_exportable():
    wf3 = _demo_workflow_v0_3()
    wf4 = client.post("/protocol/workflow/migrate", json={"workflow": wf3}).json()["workflow"]
    blob = json.dumps(wf4)  # exportable
    loaded = WorkflowV04.model_validate(json.loads(blob))  # loadable
    assert loaded.schema_version == "0.4.0"


def test_v0_3_input_migrates_then_validates_and_v0_4_validates_directly():
    wf3 = _demo_workflow_v0_3()
    wf4 = client.post("/protocol/workflow/migrate", json={"workflow": wf3}).json()["workflow"]
    # v0.4 input validates directly
    assert client.post("/protocol/workflow/validate-v0.4", json={"workflow": wf4}).json()["valid"] is True
    # node_id empty/duplicate still caught
    bad = json.loads(json.dumps(wf4))
    bad["nodes"][0]["node_id"] = ""
    codes = {f["code"] for f in client.post("/protocol/workflow/validate-v0.4", json={"workflow": bad}).json()["findings"]}
    assert "NODE_ID_EMPTY" in codes


# --- III. Persona migration -----------------------------------------------
def test_persona_migration_no_field_loss_and_loadable():
    wf3 = _demo_workflow_v0_3()
    ri = client.post("/resident/compile", json={"workflow": wf3}).json()["resident_instance"]
    persona = client.post("/protocol/persona/migrate", json={"resident_instance": ri}).json()
    assert persona["schema_version"] == "0.4.0"
    assert persona["protocol_version"] == "0.4.0"
    assert persona["type"] == "persona"
    assert persona["extensions"]["legacy"]["identity"]["name"] == ri["identity"]["name"]
    PersonaV04.model_validate(json.loads(json.dumps(persona)))  # loadable


# --- IV. Existing runtime not broken --------------------------------------
def test_existing_compile_audit_preview_intact():
    wf3 = _demo_workflow_v0_3()
    assert client.post("/workflow/validate", json={"workflow": wf3}).json()["valid"] is True
    assert client.post("/workflow/audit", json={"workflow": wf3}).json()["audit"]["status"] == "PASS"
    rc = client.post("/resident/compile", json={"workflow": wf3}).json()
    assert rc["audit"]["status"] == "PASS"
    ri = rc["resident_instance"]
    assert client.post("/resident/audit", json={"resident_instance": ri}).json()["audit"]["status"] == "PASS"
    assert client.post("/resident/preview", json={"resident_instance": ri}).json()["preview"]["kind"] == "resident_preview"


def test_mock_run_not_broken():
    wf3 = _demo_workflow_v0_3()
    assert client.post("/workflow/mock-run", json={"workflow": wf3}).json()["run"]["status"] == "success"


# --- V. Catalogs + protocol-version reachable -----------------------------
def test_protocol_version_and_catalogs_reachable():
    pv = client.get("/schema/protocol-version").json()
    assert pv == {"schema_version": "0.4.0", "protocol_version": "0.4.0"}
    assert client.get("/schema/module-catalog-v0.4").status_code == 200
    assert client.get("/schema/slot-catalog-v0.4").status_code == 200
    assert client.get("/schema/engine-registry-v0.4").status_code == 200
