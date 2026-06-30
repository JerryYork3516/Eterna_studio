"""Stage 6.8 Lattice State Module v1 acceptance.

Covers the minimal closed loop: lattice_state emission from runtime, stage-aware
state transitions, and DR compile reservations for lattice fields.

Run: cd apps/api && .venv/bin/python -m pytest tests/test_stage6_8_lattice.py -q
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services import provider_adapters, resident_runtime
from app.services.dr_compiler import compile_dr_result_v0_3

client = TestClient(app)


@pytest.fixture(autouse=True)
def _reset():
    provider_adapters.reset_memory()
    resident_runtime.reset_states()
    yield
    provider_adapters.reset_memory()
    resident_runtime.reset_states()


def _step(input_text: str, resident_id: str = "rlattice") -> dict:
    return client.post(
        "/runtime/resident/step",
        json={"workflow": {}, "input_text": input_text, "resident_id": resident_id},
    ).json()


# --- runtime lattice_state ---------------------------------------------------
def test_runtime_emits_lattice_state_formal_runtime():
    body = _step("hello world")
    assert body["mock"] is True
    assert body["resident_id"] == "rlattice"
    lattice_state = body["lattice_state"]
    assert lattice_state["resident_id"] == "rlattice"
    assert lattice_state["emotion"] == "calm"
    assert lattice_state["motion"] == "idle_breathing"
    assert lattice_state["voice_state"] == "idle"
    assert lattice_state["attention"] == "self"
    assert lattice_state["focus_target"] == "self"
    assert lattice_state["particle_density"] > 0
    assert isinstance(lattice_state["color_palette"], list)


def test_stage_transitions_change_lattice_state_formal_runtime():
    thinking = _step("please think about this")
    speaking = _step("please speak now")
    calm = _step("just continue")
    focused = _step("focus on the user")

    assert thinking["lattice_state"]["motion"] == "thinking_pulse"
    assert speaking["lattice_state"]["voice_state"] == "speaking"
    assert calm["lattice_state"]["motion"] == "idle_breathing"
    assert focused["lattice_state"]["attention"] == "user"
    assert focused["lattice_state"]["focus_target"] == "user"


# --- DR reservations ---------------------------------------------------------
def test_dr_compile_reserves_lattice_fields_v03():
    nodes13 = [{"node_id": f"layer_{i}"} for i in range(1, 14)]
    result = compile_dr_result_v0_3({"workflow": {"name": "Aria", "nodes": nodes13}})

    assert result["valid"] in (True, False)
    assert result["lattice_config"]["resident_id"] == "aria"
    assert result["lattice_state_schema"]["resident_id"] == "aria"
    assert result["multi_resident_lattice_state"]["resident_ids"] == ["aria"]
    assert result["metadata"]["v03_valid"] in (True, False)
    assert result["metadata"]["v03_compile_info"]["schema_version"] == "0.3.0"
    assert result["lattice_state_schema"]["voice_state"] == "idle"


# --- load-dr / preview path still returns lattice_state ----------------------
def test_load_dr_response_contains_lattice_state_v03():
    nodes13 = [{"node_id": f"layer_{i}"} for i in range(1, 14)]
    dr = compile_dr_result_v0_3({"workflow": {"name": "Aria", "nodes": nodes13}})["compiled_dr"]
    resp = client.post("/runtime/resident/load-dr", json={"dr": dr})
    assert resp.status_code == 200
    body = resp.json()
    assert "lattice_state" in body
    assert body["lattice_state"]["resident_id"] == body["resident_id"]
    assert body["lattice_state"]["motion"] in {"idle_breathing", "thinking_pulse", "speaking_motion", "focused_stillness"}
