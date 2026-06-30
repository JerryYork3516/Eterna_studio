"""Stage 5 task 1/3 acceptance — v0.4 core Schema / Node / Module / Slot.

Scope: protocol DTOs only (no engine, no permission gating, no real migration).
Run: cd apps/api && .venv/bin/python -m pytest tests/test_protocol_v0_4_core.py -q
"""

from __future__ import annotations

import json

from fastapi.testclient import TestClient

from app.main import app
from app.models.v0_4 import (
    CANONICAL_LAYERS,
    FallbackPolicy,
    GuidanceActionType,
    ModuleV04,
    NodeV04,
    PersonaV04,
    ProtocolStatus,
    ScreenElementState,
    ScreenElementType,
    ScreenUiAnchorModuleCatalogResponseV04,
    ScreenUiAnchorModuleV04,
    SlotType,
    SlotV04,
    WorkflowV04,
)
from app.registry.module_catalog import get_module_catalog, validate_module_catalog
from app.registry.slot_catalog import get_slot_catalog, validate_slot_catalog
from app.services.migration_v0_4 import validate_workflow_v0_4

client = TestClient(app)

WORKFLOW_CORE_FIELDS = {
    "schema_version", "protocol_version", "id", "type", "modules", "inputs",
    "outputs", "permissions", "risk_level", "audit_log", "extensions", "metadata",
}
PERSONA_CORE_FIELDS = WORKFLOW_CORE_FIELDS
NODE_PROTOCOL_FIELDS = {
    "node_id", "node_type", "input_schema", "output_schema",
    "execution_status", "slot_binding", "layer_id", "module_id",
}
MODULE_REQUIRED_FIELDS = {
    "module_id", "module_type", "module_name", "module_version", "layer_id",
    "inputs", "outputs", "config", "permissions", "risk_level", "status",
    "slot_type", "protocol_version",
}
MODULE_RESERVED_FIELDS = {
    "audit_required", "human_confirm_required", "runtime_enabled",
    "is_placeholder", "category", "tags", "color_status",
}
SLOT_FIELDS = {
    "slot_id", "slot_type", "input_schema", "output_schema", "provider",
    "execution_mode", "fallback_policy", "status", "engine_binding",
    "enabled", "protocol_version",
}
ALLOWED_SLOT_TYPES = {"llm", "tts", "memory", "avatar", "speech", "screen", "ar", "tool", "lattice"}
ALLOWED_STATUS = {"CORE", "READY", "MOCK", "PLANNED", "LATER", "DISABLED"}
ALLOWED_ON_ERROR = {"mock", "next_provider", "fail"}


# --- I. workflow / persona v0.4 core structure ----------------------------
def test_workflow_v0_4_core_fields_and_versions():
    wf = WorkflowV04(id="wf_1")
    data = wf.model_dump(mode="json")
    assert WORKFLOW_CORE_FIELDS <= set(data)
    assert data["schema_version"] == "0.4.0"
    assert data["protocol_version"] == "0.4.0"


def test_persona_v0_4_core_fields_and_versions():
    persona = PersonaV04(id="persona_1")
    data = persona.model_dump(mode="json")
    assert PERSONA_CORE_FIELDS <= set(data)
    assert data["schema_version"] == "0.4.0"
    assert data["protocol_version"] == "0.4.0"


def test_workflow_persona_exportable_and_loadable():
    wf = WorkflowV04(id="wf_x", name="Demo")
    blob = json.dumps(wf.model_dump(mode="json"))  # exportable
    assert WorkflowV04.model_validate(json.loads(blob)).id == "wf_x"  # loadable
    persona = PersonaV04(id="p_x")
    pblob = json.dumps(persona.model_dump(mode="json"))
    assert PersonaV04.model_validate(json.loads(pblob)).id == "p_x"


# --- II. Node Protocol ----------------------------------------------------
def test_node_protocol_locked_fields():
    node = NodeV04(node_id="n1", node_type="identity")
    fields = set(node.model_dump().keys())
    assert NODE_PROTOCOL_FIELDS <= fields
    # runtime_binding is no longer used for Node; provider is never on a Node.
    assert "runtime_binding" not in fields
    assert "provider" not in fields


def test_node_id_non_empty_and_unique_validation():
    wf3 = client.post("/templates/persona-builder", json={"name": "T", "ui_language": "en"}).json()["workflow"]
    wf4 = client.post("/protocol/workflow/migrate", json={"workflow": wf3}).json()["workflow"]
    # clean migrated workflow validates
    assert validate_workflow_v0_4(wf4).valid is True
    # empty + duplicate node_id are caught
    bad = json.loads(json.dumps(wf4))
    bad["nodes"][0]["node_id"] = ""
    bad["nodes"][1]["node_id"] = bad["nodes"][2]["node_id"]
    report = validate_workflow_v0_4(bad)
    codes = {f.code for f in report.findings}
    assert report.valid is False
    assert "NODE_ID_EMPTY" in codes
    assert "NODE_ID_DUPLICATE" in codes


# --- III. Module Protocol -------------------------------------------------
def test_module_protocol_fields_and_status_enum():
    module = ModuleV04(module_id="m1", module_type="identity", module_name="Identity", layer_id="layer_2")
    fields = set(module.model_dump().keys())
    assert MODULE_REQUIRED_FIELDS <= fields
    assert MODULE_RESERVED_FIELDS <= fields
    assert {s.value for s in ProtocolStatus} == ALLOWED_STATUS


def test_module_catalog_unique_and_bound_to_canonical_layer():
    modules = get_module_catalog()
    assert validate_module_catalog(modules) == []
    ids = [m.module_id for m in modules]
    assert all(ids) and len(set(ids)) == len(ids)
    canonical = {lid for lid, _n, _o in CANONICAL_LAYERS}
    assert all(m.layer_id in canonical for m in modules)
    # catalog API exists
    assert client.get("/schema/module-catalog-v0.4").status_code == 200


def test_future_capabilities_are_modules_only():
    ids = {m.module_id for m in get_module_catalog()}
    for future in ("module_agent", "module_wallet", "module_phone", "module_social", "module_ar", "module_emergency_contact"):
        assert future in ids
    assert "screen_ui_anchor_module_v0" in ids
    module = next(m for m in get_module_catalog() if m.module_id == "screen_ui_anchor_module_v0")
    assert module.module_graph == module.screen_config
    assert module.module_graph["runtime_chain"] == module.config["runtime_chain"]


def test_screen_ui_anchor_module_protocol_and_defaults():
    module = next(m for m in get_module_catalog() if m.module_id == "screen_ui_anchor_module_v0")
    assert module.mock_only is True
    assert module.runtime_enabled is False
    assert module.no_execution is True
    assert module.slot_declarations == ["screen.context", "ui.anchor", "guidance.action"]
    assert module.i18n_keys["screen.title_key"] == "screen.title_key"
    assert module.config["mock_only"] is True
    assert module.config["runtime_chain"] == [
        "screen_context",
        "UI Element Node",
        "UI Anchor Node",
        "Guidance Action Node",
        "UI Overlay",
    ]
    assert module.dr_write_keys == [
        "screen_context_schema",
        "ui_element_schema",
        "ui_anchor_schema",
        "guidance_action_schema",
        "screen_trace_schema",
        "screen_permission_policy",
        "screen_config",
    ]
    assert module.screen_config["no_real_screen"] is True
    assert module.screen_config["no_auto_click"] is True


# --- IV. Slot Protocol ----------------------------------------------------
def test_slot_protocol_fields_and_types():
    slot = SlotV04(slot_id="s1", slot_type=SlotType.llm)
    fields = set(slot.model_dump().keys())
    assert SLOT_FIELDS <= fields
    assert "runtime_binding" not in fields  # engine_binding replaces it
    assert {t.value for t in SlotType} == ALLOWED_SLOT_TYPES


def test_fallback_policy_minimal_structure():
    fp = FallbackPolicy().model_dump()
    assert set(fp) == {"on_error", "retry", "fallback_provider"}
    assert fp == {"on_error": "mock", "retry": 0, "fallback_provider": None}
    assert fp["on_error"] in ALLOWED_ON_ERROR


def test_slot_catalog_unique_and_allowed_types():
    slots = get_slot_catalog()
    assert validate_slot_catalog(slots) == []
    ids = [s.slot_id for s in slots]
    assert all(ids) and len(set(ids)) == len(ids)
    assert {s.slot_type.value for s in slots} <= ALLOWED_SLOT_TYPES
    assert client.get("/schema/slot-catalog-v0.4").status_code == 200
    response = client.get("/schema/screen-ui-anchor-module-v0")
    assert response.status_code == 200
    payload = response.json()
    assert payload["slot_declarations"] == ["screen.context", "ui.anchor", "guidance.action"]
    assert payload["screen_config"]["no_cloud_bridge"] is True


# --- V. existing v0.3 compile / audit / preview untouched -----------------
def test_v0_3_compile_audit_preview_intact():
    wf3 = client.post("/templates/persona-builder", json={"name": "Reg", "ui_language": "en"}).json()["workflow"]
    assert client.post("/workflow/validate", json={"workflow": wf3}).json()["valid"] is True
    assert client.post("/workflow/audit", json={"workflow": wf3}).json()["audit"]["status"] == "PASS"
    rc = client.post("/resident/compile", json={"workflow": wf3}).json()
    assert rc["audit"]["status"] == "PASS"
    ri = rc["resident_instance"]
    assert client.post("/resident/audit", json={"resident_instance": ri}).json()["audit"]["status"] == "PASS"
    assert client.post("/resident/preview", json={"resident_instance": ri}).json()["preview"]["kind"] == "resident_preview"
    assert client.post("/workflow/mock-run", json={"workflow": wf3}).json()["run"]["status"] == "success"


def test_13_layers_frozen():
    assert [lid for lid, _n, _o in CANONICAL_LAYERS] == [f"layer_{i}" for i in range(1, 14)]
    assert [o for _l, _n, o in CANONICAL_LAYERS] == list(range(1, 14))
    layers = client.get("/protocol/layers").json()
    assert [l["layer_id"] for l in layers] == [f"layer_{i}" for i in range(1, 14)]
    assert [l["layer_name"] for _i, l in enumerate(layers)] == [n for _l, n, _o in CANONICAL_LAYERS]
