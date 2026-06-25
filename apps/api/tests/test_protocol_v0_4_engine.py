"""Stage 5 task 2/3 acceptance — Engine / LLM Mock / Permission-Audit / Schema API.

Run: cd apps/api && .venv/bin/python -m pytest tests/test_protocol_v0_4_engine.py -q
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app
from app.models.v0_4 import EngineV04, RiskLevel
from app.registry.engine_registry import (
    get_engine_registry,
    validate_engine_registry,
    validate_protocol_chain,
)
from app.registry.module_catalog import get_module_catalog
from app.registry.slot_catalog import get_slot_catalog
from app.services.llm_mock_engine import mock_call, run_mock_llm
from app.services.permissions_v0_4 import (
    evaluate_permission,
    gate_action,
    runtime_check_order,
)

client = TestClient(app)

ENGINE_FIELDS = {
    "engine_id", "engine_type", "engine_name", "supported_slot_types",
    "providers", "status", "protocol_version",
}
AUDIT_FIELDS = {
    "action_id", "module_id", "actor", "input", "output", "decision_reason",
    "risk_level", "permission_result", "blocked_or_allowed", "timestamp",
    "human_confirmed_by",
}
EXPECTED_MOCK_RESULT = {
    "status": "success",
    "mock": True,
    "text": "This is a mock LLM response.",
    "engine": "llm_mock",
    "provider": "mock",
}


# --- I. Engine Registry ----------------------------------------------------
def test_engine_registry_fields_and_limits():
    engines = get_engine_registry()
    assert engines, "engine registry must not be empty"
    for e in engines:
        assert ENGINE_FIELDS <= set(e.model_dump().keys())
        assert e.engine_type.value == "llm"            # only llm engine_type
        assert e.providers == ["mock"]                  # only mock provider
        assert e.protocol_version == "0.4.0"
    assert validate_engine_registry(engines) == []


def test_engine_registry_api():
    body = client.get("/schema/engine-registry-v0.4").json()
    assert body["protocol_version"] == "0.4.0"
    assert all(e["engine_type"] == "llm" and e["providers"] == ["mock"] for e in body["engines"])


def test_engine_slot_module_chain():
    # LLM Slot -> LLM Engine -> Mock Provider Adapter
    slots = get_slot_catalog()
    llm_slot = next(s for s in slots if s.slot_id == "slot_llm")
    assert llm_slot.engine_binding == "llm_mock"
    assert validate_protocol_chain(get_engine_registry(), slots, get_module_catalog()) == []


def test_no_non_llm_engine_registered():
    for e in get_engine_registry():
        assert e.engine_type.value not in {"tts", "image", "video"}


# --- II. LLM Mock Engine ---------------------------------------------------
def test_llm_mock_engine_stable_result():
    r1 = run_mock_llm(prompt="hello")
    r2 = run_mock_llm(prompt="something else entirely")
    assert r1 == EXPECTED_MOCK_RESULT
    assert r1 == r2  # deterministic / stable


def test_llm_mock_engine_via_api_and_unknown_rejected():
    r = client.post("/protocol/engine/mock-call", json={"engine_id": "llm_mock", "payload": {"prompt": "x"}}).json()
    assert r == EXPECTED_MOCK_RESULT
    bad = mock_call("real_openai", {})
    assert bad["status"] == "error"


def test_engine_modules_have_no_real_network_calls():
    # No real provider / API key / network import in the engine code paths.
    forbidden_import = re.compile(r"^\s*(import|from)\s+(httpx|requests|aiohttp|urllib|socket|openai|anthropic)\b", re.M)
    forbidden_key = re.compile(r"(api_key|apikey|os\.environ|getenv|bearer|secret)", re.I)
    for rel in ("services/llm_mock_engine.py", "registry/engine_registry.py"):
        src = Path(__file__).resolve().parents[1].joinpath("app", rel).read_text()
        # strip comments/docstrings-ish: only fail on code lines, not the doc note
        code = "\n".join(line for line in src.splitlines() if not line.lstrip().startswith("#"))
        assert not forbidden_import.search(code), f"network import in {rel}"
        assert not forbidden_key.search(code), f"api-key access in {rel}"


# --- III. Permission & risk levels ----------------------------------------
def test_risk_level_enum_values():
    assert {r.value for r in RiskLevel} >= {"low", "medium", "high", "critical"}


def test_permission_rules():
    low = evaluate_permission(RiskLevel.low)
    assert low.blocked_or_allowed.value == "allowed" and low.audit_required is False

    med = evaluate_permission(RiskLevel.medium)
    assert med.blocked_or_allowed.value == "allowed" and med.audit_required is True

    high_no = evaluate_permission(RiskLevel.high)
    high_ok = evaluate_permission(RiskLevel.high, permission_granted=True)
    assert high_no.blocked_or_allowed.value == "blocked"
    assert high_ok.blocked_or_allowed.value == "allowed"

    crit_no = evaluate_permission(RiskLevel.critical)
    crit_ok = evaluate_permission(RiskLevel.critical, human_confirmed=True)
    assert crit_no.blocked_or_allowed.value == "blocked"            # never silent
    assert crit_no.permission_result.value == "requires_human_confirm"
    assert crit_ok.blocked_or_allowed.value == "allowed"


# --- IV. Audit log ---------------------------------------------------------
def test_audit_log_fields_and_high_critical_logged():
    for rl in (RiskLevel.high, RiskLevel.critical):
        decision, entry = gate_action(rl, module_id="module_wallet", permission_granted=True, human_confirmed=True)
        assert entry is not None, f"{rl} must produce an audit entry"
        assert AUDIT_FIELDS == set(entry.model_dump().keys())
        json.dumps(entry.model_dump(mode="json"))  # exportable / traceable


def test_low_risk_not_logged():
    _decision, entry = gate_action(RiskLevel.low)
    assert entry is None


# --- V. Runtime check priority (NOT layer order) --------------------------
def test_runtime_check_priority_order():
    order = runtime_check_order()
    assert [p["phase"] for p in order] == [1, 2, 3, 4]
    assert order[0]["name"] == "legal_permission_audit"   # legal/permission/audit first
    assert order[-1]["name"] == "ui_output"               # ui/output last (no decision power)
    body = client.get("/protocol/runtime-priority").json()
    assert [p["phase"] for p in body["runtime_check_priority"]] == [1, 2, 3, 4]


# --- VI. Schema API present + existing API not removed ---------------------
def test_required_schema_apis_present():
    for p in (
        "/schema/protocol-version",
        "/schema/node-registry-v0.4",
        "/schema/module-catalog-v0.4",
        "/schema/slot-catalog-v0.4",
        "/schema/engine-registry-v0.4",
    ):
        assert client.get(p).status_code == 200


def test_existing_v0_3_apis_not_removed():
    paths = {getattr(r, "path", None) for r in app.routes}
    for p in (
        "/workflow/validate",
        "/workflow/audit",
        "/resident/compile",
        "/resident/audit",
        "/resident/preview",
    ):
        assert p in paths


def test_engine_response_model_shape():
    # EngineV04 is exportable/loadable
    e = EngineV04(engine_id="x", engine_name="X", supported_slot_types=[])
    assert EngineV04.model_validate(json.loads(json.dumps(e.model_dump(mode="json")))).engine_id == "x"
