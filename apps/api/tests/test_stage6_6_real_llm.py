"""Stage 6.6 real LLM v1 acceptance — config-driven reasoning + mock fallback.

Real network is NEVER hit: the OpenAI-compatible adapter is monkeypatched.

Run: cd apps/api && .venv/bin/python -m pytest tests/test_stage6_6_real_llm.py -q
"""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services import provider_adapters, resident_runtime
from app.services.dr_compiler import compile_dr_result
from app.services.runtime_llm_config import (
    get_runtime_llm_config,
    reset_runtime_llm_config,
    set_runtime_llm_config,
)

client = TestClient(app)


@pytest.fixture(autouse=True)
def _reset():
    provider_adapters.reset_memory()
    resident_runtime.reset_states()
    reset_runtime_llm_config()
    yield
    provider_adapters.reset_memory()
    resident_runtime.reset_states()
    reset_runtime_llm_config()


def _reasoning(body: dict) -> dict:
    return next(s for s in body["execution_trace"] if s["step"] == "reasoning")


def _real_ok(base_url, api_key, model, prompt, timeout=30.0):
    return {
        "status": "success", "mock": False, "engine": "llm_primary",
        "provider": "real", "model": model, "text": "REAL reply",
    }


def _real_err(base_url, api_key, model, prompt, timeout=30.0):
    return {"status": "error", "mock": False, "engine": "llm_primary", "model": model, "error": "llm http 401"}


# --- 1. no config -> mock ----------------------------------------------------
def test_no_config_uses_mock():
    body = client.post("/runtime/resident/step", json={"workflow": {}, "input_text": "hi", "resident_id": "r1"}).json()
    rs = _reasoning(body)
    assert rs["mock"] is True
    assert rs["fallback_mock"] is False
    assert rs["engine_id"] == "llm_mock"
    assert rs["text"] == "This is a mock LLM response."


# --- 2. configured + success -> real -----------------------------------------
def test_configured_uses_real_llm(monkeypatch):
    monkeypatch.setattr(provider_adapters, "call_openai_compat", _real_ok)
    set_runtime_llm_config(profile_id="default", provider="openai_compatible", base_url="https://relay/v1", api_key="sk-secret", model="gpt-x", enabled=True)
    body = client.post("/runtime/resident/step", json={"workflow": {}, "input_text": "hi", "resident_id": "r2"}).json()
    rs = _reasoning(body)
    assert rs["mock"] is False
    assert rs["fallback_mock"] is False
    assert rs["engine_id"] == "llm_primary"
    assert rs["model"] == "gpt-x"
    assert rs["profile_id"] == "default"
    assert rs["text"] == "REAL reply"


# --- 3. configured + failure -> fallback mock (no crash) ---------------------
def test_real_failure_falls_back_to_mock(monkeypatch):
    monkeypatch.setattr(provider_adapters, "call_openai_compat", _real_err)
    set_runtime_llm_config(profile_id="default", provider="openai_compatible", base_url="https://relay/v1", api_key="sk-secret", model="gpt-x", enabled=True)
    body = client.post("/runtime/resident/step", json={"workflow": {}, "input_text": "hi", "resident_id": "r3"}).json()
    rs = _reasoning(body)
    assert rs["mock"] is True
    assert rs["fallback_mock"] is True
    assert rs["engine_id"] == "llm_mock"
    assert rs["profile_id"] == "default"
    assert rs["error"] == "llm http 401"
    assert rs["text"] == "This is a mock LLM response."


def test_real_failure_no_fallback_keeps_error(monkeypatch):
    monkeypatch.setattr(provider_adapters, "call_openai_compat", _real_err)
    set_runtime_llm_config(profile_id="default", provider="openai_compatible", base_url="https://relay/v1", api_key="sk-secret", model="gpt-x", enabled=True, fallback_to_mock=False)
    body = client.post("/runtime/resident/step", json={"workflow": {}, "input_text": "hi", "resident_id": "r4"}).json()
    rs = _reasoning(body)
    assert rs["fallback_mock"] is False
    assert rs["profile_id"] == "default"
    assert rs["error"] == "llm http 401"
    # Loop must not crash; response is still a normal envelope.
    assert body["status"] == "completed"


# --- 4. trace fields present -------------------------------------------------
def test_reasoning_trace_fields(monkeypatch):
    monkeypatch.setattr(provider_adapters, "call_openai_compat", _real_ok)
    set_runtime_llm_config(profile_id="default", provider="openai_compatible", base_url="https://relay/v1", api_key="sk-secret", model="gpt-x", enabled=True)
    body = client.post("/runtime/resident/step", json={"workflow": {}, "input_text": "hi", "resident_id": "r5"}).json()
    rs = _reasoning(body)
    for key in ("profile_id", "provider", "model", "mock", "fallback_mock"):
        assert key in rs
    assert rs["provider"] == "openai_compatible"


# --- 5. api_key never leaks --------------------------------------------------
def test_api_key_never_leaks_in_response(monkeypatch):
    monkeypatch.setattr(provider_adapters, "call_openai_compat", _real_ok)
    set_runtime_llm_config(profile_id="default", provider="openai_compatible", base_url="https://relay/v1", api_key="sk-super-secret", model="gpt-x", enabled=True)
    body = client.post("/runtime/resident/step", json={"workflow": {}, "input_text": "hi", "resident_id": "r6"}).json()
    assert "sk-super-secret" not in json.dumps(body)
    assert "api_key" not in json.dumps(body)


# --- 6. config endpoints (masked; no key echo) -------------------------------
def test_config_save_and_get_are_masked():
    saved = client.post(
        "/runtime/config/llm",
        json={"profile_id": "default", "base_url": "https://relay/v1", "api_key": "sk-secret", "model": "gpt-x", "enabled": True},
    ).json()
    assert saved["saved"] is True
    assert saved["has_api_key"] is True
    assert saved["profile_id"] == "default"
    assert "api_key" not in saved
    assert "sk-secret" not in json.dumps(saved)

    got = client.get("/runtime/config/llm").json()
    assert got["has_api_key"] is True
    assert got["base_url"] == "https://relay/v1"
    assert got["profiles"]["default"]["has_api_key"] is True
    assert "api_key" not in got


def test_config_empty_api_key_keeps_existing():
    set_runtime_llm_config(profile_id="default", provider="openai_compatible", base_url="https://relay/v1", api_key="sk-secret", model="gpt-x", enabled=True)
    # Resubmit without api_key (UI never resends the stored key).
    client.post("/runtime/config/llm", json={"profile_id": "default", "model": "gpt-y", "api_key": ""})
    cfg = get_runtime_llm_config()
    assert cfg.api_key == "sk-secret"  # unchanged
    assert cfg.model == "gpt-y"


def test_test_connection_endpoint(monkeypatch):
    import app.routers.runtime_config as rc

    monkeypatch.setattr(rc, "call_openai_compat", _real_ok)
    r = client.post(
        "/runtime/config/llm/test",
        json={"profile_id": "default", "base_url": "https://relay/v1", "api_key": "sk-secret", "model": "gpt-x"},
    ).json()
    assert r["ok"] is True
    assert r["model"] == "gpt-x"
    assert r["provider"] == "openai_compatible"
    assert "sk-secret" not in json.dumps(r)


def test_test_connection_incomplete_config():
    r = client.post("/runtime/config/llm/test", json={"profile_id": "custom", "base_url": "", "model": ""}).json()
    assert r["ok"] is False


# --- 7. regressions: /step and /load-dr still work ---------------------------
def test_resident_step_regression():
    body = client.post("/runtime/resident/step", json={"workflow": {}, "input_text": "hi", "resident_id": "rr"}).json()
    assert body["mock"] is True
    steps = [s["step"] for s in body["execution_trace"]]
    for required in ("input", "memory.read", "reasoning", "action", "memory.write", "output"):
        assert required in steps


def test_load_dr_regression():
    dr = compile_dr_result({"workflow": {"name": "Aria", "nodes": [{"node_id": f"layer_{i}"} for i in range(1, 14)]}})["dr_payload"]
    resp = client.post("/runtime/resident/load-dr", json=dr)
    assert resp.status_code == 200
    body = resp.json()
    assert body["loaded"] is True
    assert "execution_trace" in body
