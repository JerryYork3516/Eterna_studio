"""DR v0.2 Validation Gate acceptance — schema + scheduling + capability + risk
+ upgraded 6.3 three-layer audit + pseudo-DAG, plus runtime regression.

Run: cd apps/api && .venv/bin/python -m pytest tests/test_dr_v0_2_validation_gate.py -q
"""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

from fastapi.testclient import TestClient

from app.dr.v2.validator import validate_dr_v0_2
from app.main import app

client = TestClient(app)

_EXAMPLE_PATH = Path(__file__).resolve().parents[1] / "app" / "dr" / "v2" / "dr_v0_2_example.json"


def _example() -> dict:
    return json.loads(_EXAMPLE_PATH.read_text())


def _codes(result: dict) -> list:
    return [f["code"] for f in result["errors"]]


def _warn_codes(result: dict) -> list:
    return [f["code"] for f in result["warnings"]]


# --- Valid DR + result contract ---------------------------------------------
def test_valid_example_passes():
    r = validate_dr_v0_2(_example())
    assert r["valid"] is True
    assert r["errors"] == []
    assert r["orchestration_compatibility"] is True
    assert r["pseudo_dag"]
    assert r["module_audit"]["ok"] and r["layer_audit"]["ok"] and r["compile_audit"]["ok"]


def test_result_shape_contract():
    r = validate_dr_v0_2(_example())
    assert set(r.keys()) == {
        "valid", "dr_version", "errors", "warnings",
        "module_audit", "layer_audit", "compile_audit",
        "orchestration_compatibility", "pseudo_dag",
    }
    assert r["dr_version"] == "0.2"


# --- Metadata markers -------------------------------------------------------
def test_metadata_layer_marker_enforced():
    dr = _example()
    dr["dr_layer"] = "runtime"
    assert "DR_META_LAYER_INVALID" in _codes(validate_dr_v0_2(dr))


def test_metadata_not_executable_enforced():
    dr = _example()
    dr["not_executable"] = False
    assert "DR_META_NOT_EXECUTABLE" in _codes(validate_dr_v0_2(dr))


# --- Schema -----------------------------------------------------------------
def test_missing_required_section():
    dr = _example()
    del dr["risk_policy"]
    r = validate_dr_v0_2(dr)
    assert "DR_SCHEMA_REQUIRED" in _codes(r)
    assert r["valid"] is False
    # downstream audits report not-ok without crashing
    assert r["compile_audit"]["ok"] is False


def test_bad_enum():
    dr = _example()
    dr["scheduling_policy"]["mode"] = "parallel"
    assert "DR_SCHEMA_ENUM" in _codes(validate_dr_v0_2(dr))


def test_extra_field_rejected():
    dr = _example()
    dr["surprise_field"] = 1
    assert "DR_SCHEMA_EXTRA" in _codes(validate_dr_v0_2(dr))


def test_illegal_provider_on_slot_caught_by_schema():
    dr = _example()
    dr["capabilities"]["slots"][0]["provider"] = "openai"  # SlotRef forbids extras
    assert "DR_SCHEMA_EXTRA" in _codes(validate_dr_v0_2(dr))


# --- Scheduling consistency -------------------------------------------------
def test_serial_preemption_conflict():
    dr = _example()
    dr["scheduling_policy"]["preemption"] = "priority_based"
    assert "DR_SCHED_SERIAL_PREEMPTION" in _codes(validate_dr_v0_2(dr))


def test_adaptive_requires_ranking_priority():
    dr = _example()
    dr["scheduling_policy"]["mode"] = "adaptive"
    dr["scheduling_policy"]["priority_model"] = "fifo"
    assert "DR_SCHED_ADAPTIVE_PRIORITY" in _codes(validate_dr_v0_2(dr))


def test_preemption_requires_priority():
    dr = _example()
    dr["scheduling_policy"]["mode"] = "semi_parallel"
    dr["scheduling_policy"]["preemption"] = "priority_based"
    dr["scheduling_policy"]["priority_model"] = "fifo"
    assert "DR_SCHED_PREEMPTION_NO_PRIORITY" in _codes(validate_dr_v0_2(dr))


# --- Capability / slot -------------------------------------------------------
def test_unknown_slot():
    dr = _example()
    dr["capabilities"]["slots"] = [{"slot_id": "slot_email", "slot_type": "tool"}]
    dr["execution_policy"]["required_slot_types"] = []
    dr["intent_model"]["intents"] = [{"step_id": "s1", "requires_slot_type": "tool"}]
    assert "DR_CAP_SLOT_UNKNOWN" in _codes(validate_dr_v0_2(dr))


def test_engine_slot_unsupported():
    dr = _example()
    dr["capabilities"]["slots"] = [
        {"slot_id": "slot_tts", "slot_type": "tts", "engine_binding": "llm_mock"},
        {"slot_id": "slot_memory", "slot_type": "memory"},
    ]
    assert "DR_CAP_ENGINE_SLOT_UNSUPPORTED" in _codes(validate_dr_v0_2(dr))


def test_required_slot_unmet():
    dr = _example()
    dr["execution_policy"]["required_slot_types"] = ["avatar"]
    assert "DR_CAP_REQUIRED_SLOT_UNMET" in _codes(validate_dr_v0_2(dr))


# --- Risk / security ---------------------------------------------------------
def test_risk_unsafe_no_confirm():
    dr = _example()
    dr["risk_policy"]["risk_level"] = "critical"
    dr["risk_policy"]["audit_required"] = True
    assert "DR_RISK_UNSAFE_NO_CONFIRM" in _codes(validate_dr_v0_2(dr))


def test_disclosure_required():
    dr = _example()
    dr["risk_policy"]["disclosure_required"] = False
    assert "DR_RISK_NO_DISCLOSURE" in _codes(validate_dr_v0_2(dr))


def test_system_locked_tamper_with_baseline():
    baseline = _example()
    baseline["risk_policy"]["risk_level"] = "low"
    dr = _example()
    dr["risk_policy"]["system_locked"] = True
    dr["risk_policy"]["risk_level"] = "high"
    dr["risk_policy"]["audit_required"] = True  # avoid unrelated unsafe finding
    assert "DR_RISK_LOCKED_FIELD_MODIFIED" in _codes(validate_dr_v0_2(dr, baseline=baseline))


def test_security_manifest_required_flags():
    for field, code in (
        ("signature_required", "DR_SEC_SIGNATURE_REQUIRED"),
        ("watermark_required", "DR_SEC_WATERMARK_REQUIRED"),
        ("secure_loader_required", "DR_SEC_LOADER_REQUIRED"),
    ):
        dr = _example()
        dr["security_manifest"][field] = False
        assert code in _codes(validate_dr_v0_2(dr)), field


# --- capability_profile ------------------------------------------------------
def test_capability_profile_reserved_class():
    dr = _example()
    dr["capability_profile"]["resident_class"] = "civilization_synthesis"
    assert "DR_CAPROF_CLASS_NOT_ENABLED" in _codes(validate_dr_v0_2(dr))


def test_capability_profile_weight_range_and_sum():
    dr = _example()
    dr["capability_profile"]["primary_weight"] = 0.6
    dr["capability_profile"]["secondary_weight"] = 0.4
    codes = _codes(validate_dr_v0_2(dr))
    assert "DR_CAPROF_PRIMARY_WEIGHT_RANGE" in codes
    assert "DR_CAPROF_SECONDARY_WEIGHT_RANGE" in codes

    dr2 = _example()
    dr2["capability_profile"]["primary_weight"] = 0.8
    dr2["capability_profile"]["secondary_weight"] = 0.3
    assert "DR_CAPROF_WEIGHT_SUM" in _codes(validate_dr_v0_2(dr2))


# --- skill_policy ------------------------------------------------------------
def test_skill_policy_rules():
    dr = _example()
    dr["skill_policy"]["unsigned_skill_policy"] = "allow"
    assert "DR_SKILL_UNSIGNED_POLICY" in _codes(validate_dr_v0_2(dr))

    dr2 = _example()
    dr2["skill_policy"]["sandbox_required"] = False
    assert "DR_SKILL_SANDBOX_REQUIRED" in _codes(validate_dr_v0_2(dr2))

    dr3 = _example()
    dr3["skill_policy"]["allowed_skill_sources"] = ["community"]
    assert "DR_SKILL_SOURCE_INVALID" in _codes(validate_dr_v0_2(dr3))


# --- pseudo-DAG / orchestration ---------------------------------------------
def test_pseudo_dag_serial_shape_and_nodes():
    r = validate_dr_v0_2(_example())
    nodes = [rec for rec in r["pseudo_dag"] if rec["type"] == "node"]
    edges = [rec for rec in r["pseudo_dag"] if rec["type"] == "edge"]
    meta = next(rec for rec in r["pseudo_dag"] if rec["type"] == "meta")
    assert len(nodes) == 3  # == declared intents
    assert {(e["from"], e["to"]) for e in edges} == {("step_greet", "step_recall"), ("step_recall", "step_reply")}
    assert meta["shape"] == "linear"


def test_orchestration_incompatible_unbound_slot():
    dr = _example()
    dr["intent_model"]["intents"].append({"step_id": "step_ar", "requires_slot_type": "ar", "depends_on": ["step_reply"]})
    r = validate_dr_v0_2(dr)
    assert r["orchestration_compatibility"] is False
    assert "DR_ORCH_STEP_NO_SLOT" in _codes(r)
    assert "DR_CAUDIT_ORCH_FAIL" in _codes(r)


def test_no_intent_incompatible():
    dr = _example()
    dr["intent_model"]["primary_intent"] = ""
    dr["intent_model"]["intents"] = []
    r = validate_dr_v0_2(dr)
    assert r["orchestration_compatibility"] is False
    assert "DR_ORCH_NO_INTENT" in _codes(r)


def test_cycle_detection():
    dr = _example()
    dr["intent_model"]["intents"] = [
        {"step_id": "a", "requires_slot_type": "llm", "depends_on": ["b"]},
        {"step_id": "b", "requires_slot_type": "llm", "depends_on": ["a"]},
    ]
    assert "DR_ORCH_CYCLE" in _codes(validate_dr_v0_2(dr))


def test_three_sections_in_meta_only_not_steps():
    r = validate_dr_v0_2(_example())
    meta = next(rec for rec in r["pseudo_dag"] if rec["type"] == "meta")
    assert "capability_profile" in meta and "security_manifest" in meta and "skill_policy" in meta
    nodes = [rec for rec in r["pseudo_dag"] if rec["type"] == "node"]
    # declarations never produce extra nodes/steps
    assert len(nodes) == len(_example()["intent_model"]["intents"])


# --- upgraded 6.3 audits -----------------------------------------------------
def test_module_scheduling_incompatibility():
    dr = _example()
    # human-gated module as a tool + preemption -> module audit incompat
    dr["execution_policy"]["allow_tool_use"] = True
    dr["capabilities"]["tools"] = [{"tool_id": "module_agent", "module_id": "module_agent"}]
    dr["scheduling_policy"]["mode"] = "semi_parallel"
    dr["scheduling_policy"]["priority_model"] = "weighted"
    dr["scheduling_policy"]["preemption"] = "priority_based"
    r = validate_dr_v0_2(dr)
    assert "DR_MAUDIT_SCHED_INCOMPAT" in _codes(r)


def test_layer_dependency_broken():
    dr = _example()
    # reference tools layer (9) without safety layer (3)
    dr["stability_constraints"]["immutable_layers"] = ["layer_1", "layer_9"]
    assert "DR_LAUDIT_DEP_BROKEN" in _codes(validate_dr_v0_2(dr))


def test_safety_forbidden_tool_path():
    dr = _example()
    dr["execution_policy"]["allow_tool_use"] = True
    dr["capabilities"]["tools"] = [{"tool_id": "web_search_slot", "module_id": "web_search_slot"}]
    dr["intent_model"]["intents"].append({"step_id": "step_tool", "requires_tool": "web_search_slot", "depends_on": ["step_reply"]})
    dr["risk_policy"]["forbidden_tool_paths"] = ["web_search_slot"]
    r = validate_dr_v0_2(dr)
    assert "DR_CAUDIT_SAFETY_FORBIDDEN_TOOL" in _codes(r)


# --- purity / determinism ---------------------------------------------------
def test_validation_is_pure_and_deterministic():
    dr = _example()
    snapshot = copy.deepcopy(dr)
    r1 = validate_dr_v0_2(dr)
    r2 = validate_dr_v0_2(dr)
    assert r1 == r2          # deterministic
    assert dr == snapshot    # input not mutated


def test_gate_does_not_import_execution_engine():
    # In a fresh process, importing + running the Gate must NOT pull in the
    # runtime kernel (proves the policy layer is decoupled from execution).
    import subprocess

    api_root = Path(__file__).resolve().parents[1]
    code = (
        "import sys, json; "
        "from app.dr.v2.validator import validate_dr_v0_2; "
        "validate_dr_v0_2(json.load(open('app/dr/v2/dr_v0_2_example.json'))); "
        "assert 'app.services.execution_engine' not in sys.modules; "
        "print('PURE_OK')"
    )
    out = subprocess.run([sys.executable, "-c", code], cwd=str(api_root), capture_output=True, text=True)
    assert "PURE_OK" in out.stdout, out.stderr


# --- runtime regression ------------------------------------------------------
def test_runtime_resident_step_untouched():
    resp = client.post("/runtime/resident/step", json={"workflow": {}, "input_text": "hi", "resident_id": "r_drgate"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["mock"] is True
    steps = [e["step"] for e in body["execution_trace"]]
    for required in ("input", "memory.read", "reasoning", "action", "memory.write", "output"):
        assert required in steps
