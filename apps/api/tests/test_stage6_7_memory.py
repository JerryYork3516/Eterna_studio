"""Stage 6.7 Memory Module v1 acceptance.

Memory read/write/view/clear with memory_type + namespace + storage backend, the
two-round recall loop (memory injected into the reasoning prompt), trace fields,
the /runtime/memory endpoints, and DR memory-field collection.

Run: cd apps/api && .venv/bin/python -m pytest tests/test_stage6_7_memory.py -q
"""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services import provider_adapters, resident_runtime
from app.services.dr_compiler import compile_dr_result
from app.services.memory_store import get_memory_store
from app.services.runtime_llm_config import reset_runtime_llm_config

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


def _route(payload):
    return provider_adapters.route_provider_for_engine("memory_mock", payload)


def _step(text, resident="rmem"):
    return client.post(
        "/runtime/resident/step", json={"workflow": {}, "input_text": text, "resident_id": resident}
    ).json()


def _trace(body, step):
    return next(s for s in body["execution_trace"] if s["step"] == step)


# --- provider capabilities: read / write / view / clear ----------------------
def test_memory_write_read_view_clear():
    w = _route({"op": "write", "resident_id": "r", "namespace": "default", "memory_type": "interaction_log", "entry": {"input": "我喜欢蓝色"}})
    assert w["count"] == 1
    assert w["memory_type"] == "interaction_log"
    assert w["namespace"] == "default"
    assert w["storage_backend"] in ("sqlite", "json", "mock")

    r = _route({"op": "read", "resident_id": "r", "namespace": "default", "memory_type": "interaction_log"})
    assert r["count"] == 1 and r["entries"][0]["input"] == "我喜欢蓝色"

    v = _route({"op": "view", "resident_id": "r", "namespace": "default"})
    assert v["items"][0]["content"]["input"] == "我喜欢蓝色"

    c = _route({"op": "clear", "resident_id": "r", "namespace": "default"})
    assert c["cleared"] == 1 and c["count"] == 0


def test_namespace_isolation_and_memory_types():
    _route({"op": "write", "resident_id": "r", "namespace": "ns1", "memory_type": "profile_memory", "entry": {"a": 1}})
    _route({"op": "write", "resident_id": "r", "namespace": "ns2", "memory_type": "interaction_log", "entry": {"b": 2}})
    assert _route({"op": "read", "resident_id": "r", "namespace": "ns1"})["count"] == 1
    assert _route({"op": "read", "resident_id": "r", "namespace": "ns2"})["count"] == 1
    # memory_type filter
    assert _route({"op": "read", "resident_id": "r", "namespace": "ns1", "memory_type": "interaction_log"})["count"] == 0


def test_unknown_op_returns_error():
    e = _route({"op": "frobnicate", "resident_id": "r"})
    assert e["status"] == "error"


# --- two-round recall: memory is injected into the reasoning prompt -----------
def test_two_round_recall_injects_memory_into_prompt():
    _step("我喜欢蓝色。")  # round 1
    body2 = _step("我喜欢什么颜色？")  # round 2
    read = _trace(body2, "memory.read")
    assert read["count"] >= 1  # round 1 was recalled
    # The recalled content is injected into the reasoning prompt (so a real LLM
    # can answer "蓝色"; with the mock engine the reply is fixed but the
    # mechanism is verifiable here).
    reasoning = _trace(body2, "reasoning")
    assert "我喜欢蓝色" in reasoning["input"]["prompt"]


def test_runtime_order_unchanged():
    body = _step("hi")
    steps = [s["step"] for s in body["execution_trace"]]
    # input -> memory.read -> reasoning -> action -> memory.write -> output
    assert steps.index("memory.read") < steps.index("reasoning") < steps.index("memory.write") < steps.index("output")


def test_trace_has_memory_fields():
    body = _step("hello")
    for step in ("memory.read", "memory.write"):
        s = _trace(body, step)
        for key in ("namespace", "memory_type", "storage_backend", "mock"):
            assert key in s, f"{step} missing {key}"


# --- /runtime/memory endpoints (viewer + clear) ------------------------------
def test_memory_view_and_clear_endpoints():
    _step("我喜欢蓝色。", resident="rapi")
    view = client.get(
        "/runtime/memory/view",
        params={"resident_id": "rapi", "namespace": "default", "memory_type": "interaction_log", "limit": 20},
    ).json()
    assert view["count"] >= 1
    assert view["memory_type"] == "interaction_log"
    assert view["limit"] == 20
    assert any("我喜欢蓝色" in json.dumps(item, ensure_ascii=False) for item in view["entries"])

    cleared = client.post(
        "/runtime/memory/clear",
        json={"resident_id": "rapi", "namespace": "default", "memory_type": "interaction_log"},
    ).json()
    assert cleared["cleared"] is True
    assert cleared["deleted_count"] >= 1
    after = client.get(
        "/runtime/memory/view",
        params={"resident_id": "rapi", "namespace": "default", "memory_type": "interaction_log", "limit": 20},
    ).json()
    assert after["count"] == 0


# --- DR collects memory fields -----------------------------------------------
def test_dr_collects_memory_config():
    nodes13 = [{"node_id": f"layer_{i}"} for i in range(1, 14)]
    dr = compile_dr_result({"workflow": {"name": "Aria", "nodes": nodes13}})["compiled_dr"]
    # compiled_dr is the v0.2 candidate; memory fields are collected on the v0.1
    # blueprint exposed via metadata.v01... — assert through a plain compile too.
    from app.services.dr_compiler import compile_dr

    bp = compile_dr({"workflow": {"name": "Aria", "nodes": nodes13}})
    assert "memory_config" in bp
    assert "memory_namespace" in bp
    assert "memory_policy" in bp
    assert "memory_storage_requirement" in bp
    assert bp["memory_storage_requirement"]["vector"] is False  # no vector memory
    assert bp["memory_storage_requirement"]["cloud"] is False  # no cloud memory


# --- 6.6 LLM untouched -------------------------------------------------------
def test_llm_path_still_mock_without_config():
    body = _step("hi", resident="rllm")
    rs = _trace(body, "reasoning")
    assert rs["mock"] is True and rs["engine_id"] == "llm_mock"
    assert rs["text"] == "This is a mock LLM response."
