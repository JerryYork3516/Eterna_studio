"""Stage 6 runtime engine acceptance — Resident v1 mock loop + regressions.

Run: cd apps/api && .venv/bin/python -m pytest tests/test_stage6_runtime_engine.py -q
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services import provider_adapters, resident_runtime
from app.services.llm_mock_engine import run_mock_llm

client = TestClient(app)


@pytest.fixture(autouse=True)
def _reset_runtime():
    """Isolate process-local runtime/provider state per test."""
    provider_adapters.reset_memory()
    resident_runtime.reset_states()
    yield
    provider_adapters.reset_memory()
    resident_runtime.reset_states()


def _demo_v0_3() -> dict:
    return client.post("/templates/persona-builder", json={"name": "Br", "ui_language": "en"}).json()["workflow"]


def _demo_v0_4() -> dict:
    wf3 = _demo_v0_3()
    return client.post("/protocol/workflow/migrate", json={"workflow": wf3}).json()["workflow"]


def _step(input_text: str, resident_id: str = "resident_test") -> dict:
    resp = client.post(
        "/runtime/resident/step",
        json={"workflow": {}, "input_text": input_text, "resident_id": resident_id},
    )
    assert resp.status_code == 200  # 1
    return resp.json()


# --- Resident v1 step --------------------------------------------------------
def test_resident_step_returns_200_and_mock():
    body = _step("hello")
    assert body["mock"] is True  # 2
    assert body["runtime_version"] == "resident_v1_mock"
    assert body["schema_version"] == "0.4.0"


def test_output_text_present():
    body = _step("hello world")
    assert body["output_text"]  # 3 non-empty


def test_memory_snapshot_records_input_output():
    body = _step("remember me")
    entries = body["memory_snapshot"]["entries"]
    assert len(entries) == 1  # 4
    assert entries[0]["input"] == "remember me"
    assert entries[0]["output"] == body["output_text"]


def test_turn_count_increments_across_calls():
    first = _step("a", resident_id="r_counter")
    second = _step("b", resident_id="r_counter")
    assert first["turn_count"] == 1  # 5
    assert second["turn_count"] == 2
    assert second["memory_snapshot"]["count"] == 2


def test_execution_trace_has_all_loop_steps():
    body = _step("trace me")
    steps = [entry["step"] for entry in body["execution_trace"]]
    for required in ("input", "memory.read", "reasoning", "action", "memory.write", "output"):
        assert required in steps  # 6


def test_reasoning_uses_only_mock_provider():
    body = _step("no real model")
    reasoning = next(e for e in body["execution_trace"] if e["step"] == "reasoning")
    assert reasoning["provider"] == "mock"  # 7
    assert reasoning["text"] == run_mock_llm()["text"]


# --- Regressions: existing endpoints still work ------------------------------
def test_protocol_execute_still_passes():
    wf4 = _demo_v0_4()
    resp = client.post("/protocol/execute", json={"workflow": wf4, "action": "mock_run"})
    assert resp.status_code == 200  # 8
    assert resp.json()["executed"] is True


def test_resident_compile_still_passes():
    wf3 = _demo_v0_3()
    resp = client.post("/resident/compile", json={"workflow": wf3})
    assert resp.status_code == 200  # 9
    assert "resident_instance" in resp.json()


def test_workflow_mock_run_still_passes():
    wf3 = _demo_v0_3()
    resp = client.post("/workflow/mock-run", json={"workflow": wf3})
    assert resp.status_code == 200  # 10
    assert resp.json()["run"]["status"] in ("success", "warning", "error")
