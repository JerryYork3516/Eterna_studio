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
from app.services.dr_compiler import compile_dr, compile_dr_result_v0_3

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


def test_service_loads_legacy_v0_2_dr_and_creates_runtime_state():
    body = resident_runtime.load_digital_resident(_dr_v0_2(), input_text="hello loaded dr")

    assert body["loaded"] is True
    assert body["resident_id"] == "aria_demo"
    assert body["dr_version"] == "0.2"
    assert body["validation_result"]["valid"] is True
    assert body["runtime_state"]["resident_id"] == "aria_demo"
    assert body["runtime_state"]["identity"]["name"] == "Aria"
    assert body["runtime_state"]["capability_profile"]["resident_class"] == "industry_expertise"
    assert body["runtime_state"]["memory_policy"]["provider"] == "mock"
    assert body["runtime_state"]["provider_bindings"] == {
        "llm": "llm_mock:provider_llm_mock",
        "memory": "memory_mock:provider_memory_mock",
        "tool": "tool_mock:provider_tool_mock",
    }


def test_api_loads_legacy_v0_2_dr_and_returns_mock_response():
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


def test_api_accepts_raw_legacy_v0_2_json_body():
    resp = client.post(
        "/runtime/resident/load-dr",
        content=json.dumps(_dr_v0_2()),
        headers={"Content-Type": "application/json"},
    )

    assert resp.status_code == 200
    assert resp.json()["loaded"] is True


def test_load_dr_trace_has_all_six_loop_steps_legacy_v0_2():
    body = client.post("/runtime/resident/load-dr", json={"dr": _dr_v0_2()}).json()

    assert _steps(body) == ["input", "memory.read", "reasoning", "action", "memory.write", "output"]
    for step_name in ("memory.read", "reasoning", "action", "memory.write"):
        step = next(entry for entry in body["execution_trace"] if entry["step"] == step_name)
        assert step["mock"] is True
        assert step["provider_type"]
        assert step["provider_id"].startswith("provider_")
        assert step["engine_id"].endswith("_mock")


def test_load_dr_memory_snapshot_records_input_and_output_legacy_v0_2():
    body = client.post(
        "/runtime/resident/load-dr",
        json={"dr": _dr_v0_2(), "input_text": "remember loaded dr"},
    ).json()

    snapshot = body["memory_snapshot"]
    assert snapshot["count"] == 1
    assert snapshot["entries"][0]["input"] == "remember loaded dr"
    assert snapshot["entries"][0]["output"] == body["output_text"]


def test_invalid_legacy_v0_2_dr_is_rejected_with_validation_errors():
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


def test_legacy_v0_1_dr_is_rejected_with_validation_errors_legacy():
    legacy = compile_dr({"workflow": {"name": "Legacy", "nodes": [{"node_id": f"layer_{i}"} for i in range(1, 14)]}})
    # Compatibility note: the legacy helper still returns the Stage 6.11 public
    # envelope, so the runtime sees the v0.2-style validation failure path.
    body = client.post("/runtime/resident/load-dr", json={"dr": legacy}).json()

    assert body["loaded"] is False
    assert body["dr_version"] == "0.2"
    assert body["validation_result"]["valid"] is False
    assert body["validation_result"]["errors"]


def test_v03_envelope_loads_through_runtime_boundary_formal_path():
    v03 = compile_dr_result_v0_3({"workflow": {"name": "Aria", "nodes": [{"node_id": f"layer_{i}"} for i in range(1, 14)]}})["compiled_dr"]
    assert v03["dr_version"] == "0.3"
    body = client.post("/runtime/resident/load-dr", json={"dr": v03}).json()
    assert body["loaded"] is True
    assert body["dr_version"] == "0.3"
    assert body["resident_id"] == v03["manifest"]["resident_id"]


def test_existing_resident_step_still_works_formal_runtime():
    resp = client.post("/runtime/resident/step", json={"workflow": {}, "input_text": "hi", "resident_id": "r_64_reg"})

    assert resp.status_code == 200
    body = resp.json()
    assert body["mock"] is True
    for required in ("input", "memory.read", "reasoning", "action", "memory.write", "output"):
        assert required in _steps(body)
