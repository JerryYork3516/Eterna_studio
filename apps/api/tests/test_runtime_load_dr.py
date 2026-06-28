"""Stage 6.4 Runtime Load DR acceptance — validated .digital_resident -> mock loop.

Run: cd apps/api && .venv/bin/python -m pytest tests/test_runtime_load_dr.py -q
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services import provider_adapters, resident_runtime
from app.services.dr_compiler import compile_dr

client = TestClient(app)

_EXAMPLE_PATH = Path(__file__).resolve().parents[1] / "app" / "dr" / "v2" / "dr_v0_2_example.json"


@pytest.fixture(autouse=True)
def _reset_runtime():
    provider_adapters.reset_memory()
    resident_runtime.reset_states()
    yield
    provider_adapters.reset_memory()
    resident_runtime.reset_states()


def _dr_v0_2() -> dict:
    return json.loads(_EXAMPLE_PATH.read_text())


def _steps(body: dict) -> list[str]:
    return [entry["step"] for entry in body["execution_trace"]]


def test_service_loads_valid_dr_and_creates_runtime_state():
    body = resident_runtime.load_digital_resident(_dr_v0_2(), input_text="hello loaded dr")

    assert body["loaded"] is True
    assert body["resident_id"] == "aria_demo"
    assert body["dr_version"] == "0.2"
    assert body["validation_result"]["valid"] is True
    assert body["runtime_state"]["resident_id"] == "aria_demo"
    assert body["runtime_state"]["identity"]["name"] == "Aria"
    assert body["runtime_state"]["capability_profile"]["resident_class"] == "industry_expertise"
    assert body["runtime_state"]["memory_policy"]["provider"] == "mock"
    assert body["runtime_state"]["provider_bindings"] == {"llm": "mock", "memory": "mock", "tool": "mock"}


def test_api_loads_valid_dr_and_returns_mock_response():
    resp = client.post(
        "/runtime/resident/load-dr",
        json={"dr": _dr_v0_2(), "input_text": "hello from upload"},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["loaded"] is True
    assert body["mock"] is True
    assert body["resident_id"] == "aria_demo"
    assert body["dr_version"] == "0.2"
    assert body["runtime_version"] == "resident_v1_mock"
    assert body["output_text"]


def test_api_accepts_raw_digital_resident_json_body():
    resp = client.post(
        "/runtime/resident/load-dr",
        content=json.dumps(_dr_v0_2()),
        headers={"Content-Type": "application/json"},
    )

    assert resp.status_code == 200
    assert resp.json()["loaded"] is True


def test_load_dr_trace_has_all_six_loop_steps():
    body = client.post("/runtime/resident/load-dr", json={"dr": _dr_v0_2()}).json()

    assert _steps(body) == ["input", "memory.read", "reasoning", "action", "memory.write", "output"]


def test_load_dr_memory_snapshot_records_input_and_output():
    body = client.post(
        "/runtime/resident/load-dr",
        json={"dr": _dr_v0_2(), "input_text": "remember loaded dr"},
    ).json()

    snapshot = body["memory_snapshot"]
    assert snapshot["count"] == 1
    assert snapshot["entries"][0]["input"] == "remember loaded dr"
    assert snapshot["entries"][0]["output"] == body["output_text"]


def test_invalid_dr_is_rejected_with_validation_errors():
    dr = copy.deepcopy(_dr_v0_2())
    dr["capabilities"]["slots"][0]["provider"] = "openai"

    body = client.post("/runtime/resident/load-dr", json={"dr": dr}).json()

    assert body["loaded"] is False
    assert body["status"] == "rejected"
    assert body["validation_result"]["valid"] is False
    assert body["validation_result"]["errors"]
    assert body["execution_trace"] == []
    assert body["memory_snapshot"]["count"] == 0
    assert body["output_text"] == ""


def test_v0_1_dr_is_rejected_with_validation_errors():
    v01 = compile_dr({"workflow": {"name": "Legacy", "nodes": [{"node_id": f"layer_{i}"} for i in range(1, 14)]}})

    body = client.post("/runtime/resident/load-dr", json={"dr": v01}).json()

    assert body["loaded"] is False
    assert body["dr_version"] == "0.1"
    assert body["validation_result"]["valid"] is False
    assert body["validation_result"]["errors"]


def test_existing_resident_step_still_works():
    resp = client.post("/runtime/resident/step", json={"workflow": {}, "input_text": "hi", "resident_id": "r_64_reg"})

    assert resp.status_code == 200
    body = resp.json()
    assert body["mock"] is True
    for required in ("input", "memory.read", "reasoning", "action", "memory.write", "output"):
        assert required in _steps(body)
