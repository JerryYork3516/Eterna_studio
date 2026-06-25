"""v0.4 Execution Orchestrator (control plane -> v0.3 runtime bridge) acceptance.

Run: cd apps/api && .venv/bin/python -m pytest tests/test_execution_bridge_v0_4.py -q
"""

from __future__ import annotations

import json

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _demo_v0_3() -> dict:
    return client.post("/templates/persona-builder", json={"name": "Br", "ui_language": "en"}).json()["workflow"]


def _demo_v0_4() -> dict:
    wf3 = _demo_v0_3()
    return client.post("/protocol/workflow/migrate", json={"workflow": wf3}).json()["workflow"]


def _norm_run(run: dict) -> dict:
    # ignore run_id / timestamps / durations
    return {
        "status": run["status"],
        "order": run["order"],
        "nodes": [(r["node_id"], r["status"]) for r in run["node_results"]],
        "artifacts": [a["kind"] for a in run["artifacts"]],
    }


# --- Bridge runs through v0.3, output identical ----------------------------
def test_mock_run_via_bridge_matches_direct_v0_3():
    wf3 = _demo_v0_3()
    direct = client.post("/workflow/mock-run", json={"workflow": wf3}).json()["run"]
    wf4 = client.post("/protocol/workflow/migrate", json={"workflow": wf3}).json()["workflow"]
    resp = client.post("/protocol/execute", json={"workflow": wf4, "action": "mock_run"}).json()
    assert resp["executed"] is True
    assert resp["runtime"] == "v0.3"
    assert resp["plan"]["target_runtime"] == "v0.3"
    assert _norm_run(direct) == _norm_run(resp["result"]["run"])


def test_audit_via_bridge_matches_direct():
    wf3 = _demo_v0_3()
    wf4 = client.post("/protocol/workflow/migrate", json={"workflow": wf3}).json()["workflow"]
    bridged = client.post("/protocol/execute", json={"workflow": wf4, "action": "audit"}).json()["result"]["audit"]["status"]
    direct = client.post("/workflow/audit", json={"workflow": wf3}).json()["audit"]["status"]
    assert bridged == direct == "PASS"


def test_compile_via_bridge_returns_resident():
    wf4 = _demo_v0_4()
    resp = client.post("/protocol/execute", json={"workflow": wf4, "action": "compile"}).json()
    assert resp["executed"] is True
    assert "resident_instance" in resp["result"]
    assert resp["result"]["audit"]["status"] == "PASS"


# --- Plan-only does not forward to runtime --------------------------------
def test_plan_does_not_execute_but_translates():
    wf4 = _demo_v0_4()
    plan = client.post("/protocol/plan", json={"workflow": wf4, "action": "mock_run"}).json()
    assert plan["target_runtime"] == "v0.3"
    assert plan["blocked"] is False
    assert len(plan["resolved_bindings"]) == len(wf4["nodes"])
    assert plan["v0_3_workflow"]["schema_version"] == "0.3.0"
    # 13-layer trunk preserved through translation
    assert [l["id"] for l in plan["v0_3_workflow"]["layers"]] == [f"layer_{i}" for i in range(1, 14)]


# --- Fallback: v0.3 input can be downgraded-executed ----------------------
def test_v0_3_input_fallback_executes():
    wf3 = _demo_v0_3()
    resp = client.post("/protocol/execute", json={"workflow": wf3, "action": "mock_run"}).json()
    assert resp["executed"] is True
    assert resp["result"]["run"]["status"] == "success"


# --- Node -> Slot -> Engine resolution ------------------------------------
def test_node_slot_engine_resolution():
    wf4 = _demo_v0_4()
    # bind one node to the llm slot (which binds the llm_mock engine)
    wf4["nodes"][0]["slot_binding"] = "slot_llm"
    plan = client.post("/protocol/plan", json={"workflow": wf4, "action": "mock_run"}).json()
    bound = next(b for b in plan["resolved_bindings"] if b["slot_id"] == "slot_llm")
    assert bound["resolved"] is True
    assert bound["engine_id"] == "llm_mock"
    assert bound["engine_provider"] == "mock"


# --- Permission/risk gate blocks high/critical ----------------------------
def test_gate_blocks_critical_module_and_does_not_forward():
    wf4 = _demo_v0_4()
    # module_wallet is critical-risk; without human confirmation it must block.
    wf4["nodes"][0]["module_id"] = "module_wallet"
    plan = client.post("/protocol/plan", json={"workflow": wf4, "action": "mock_run"}).json()
    assert plan["blocked"] is True
    assert any(d["blocked_or_allowed"] == "blocked" for d in plan["permission_decisions"])
    resp = client.post("/protocol/execute", json={"workflow": wf4, "action": "mock_run"}).json()
    assert resp["executed"] is False          # never silently executed
    assert resp["result"] == {}


# --- v0.3 runtime / APIs untouched ----------------------------------------
def test_v0_3_runtime_and_apis_intact():
    wf3 = _demo_v0_3()
    assert client.post("/workflow/validate", json={"workflow": wf3}).json()["valid"] is True
    assert client.post("/workflow/audit", json={"workflow": wf3}).json()["audit"]["status"] == "PASS"
    rc = client.post("/resident/compile", json={"workflow": wf3}).json()
    assert rc["audit"]["status"] == "PASS"
    ri = rc["resident_instance"]
    assert client.post("/resident/audit", json={"resident_instance": ri}).json()["audit"]["status"] == "PASS"
    assert client.post("/resident/preview", json={"resident_instance": ri}).json()["preview"]["kind"] == "resident_preview"
    assert client.post("/workflow/mock-run", json={"workflow": wf3}).json()["run"]["status"] == "success"


def test_execute_response_is_exportable():
    wf4 = _demo_v0_4()
    resp = client.post("/protocol/execute", json={"workflow": wf4, "action": "mock_run"}).json()
    json.dumps(resp)  # fully JSON-serializable, no circular refs


# --- Strict boundary: adapter is the only path to the v0.3 runtime --------
def test_orchestrator_does_not_import_v0_3_runtime_directly():
    from pathlib import Path

    src = Path(__file__).resolve().parents[1].joinpath("app", "services", "v4_orchestrator.py").read_text()
    code = "\n".join(line for line in src.splitlines() if not line.lstrip().startswith("#"))
    # The control plane must reach the runtime only via the Execution Adapter.
    assert "mock_run_v0_3" not in code
    assert "audit_workflow" not in code
    assert "compile_resident_from_workflow" not in code
    assert "run_v0_3" not in code  # only adapter.execute_plan is used
    assert "execute_plan" in code


def test_adapter_execute_plan_refuses_blocked_plan():
    from app.services.v3_execution_adapter import ExecutionBlockedError, execute_plan
    from app.services.v4_orchestrator import plan_execution

    wf4 = _demo_v0_4()
    wf4["nodes"][0]["module_id"] = "module_wallet"  # critical risk -> blocked
    plan = plan_execution(wf4, "mock_run")
    assert plan.blocked is True
    try:
        execute_plan(plan)
        assert False, "blocked plan must not execute"
    except ExecutionBlockedError:
        pass
