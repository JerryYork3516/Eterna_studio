"""DR v0.2 Validation Gate — validators + aggregate entry.

`validate_dr_v0_2(dr)` orchestrates the four declarative validators and the
upgraded 6.3 three-layer audit, then returns the unified 9-key result. It is a
pure function: no execution, no scheduling, no I/O, deterministic output.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from .capability_validator import (
    validate_capabilities,
    validate_capability_profile,
    validate_skill_policy,
)
from .compile_audit_validator import compile_audit, layer_audit, module_audit
from .dr_schema_validator import validate_schema
from .dr_validation_result import DRValidationResult, finding
from .orchestration_compatibility import build_pseudo_dag
from .risk_validator import validate_risk, validate_security_manifest
from .scheduling_policy_validator import validate_scheduling

__all__ = ["validate_dr_v0_2", "DRValidationResult", "finding"]


def validate_dr_v0_2(dr: Dict[str, Any], *, baseline: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Validate a DR v0.2 document. Returns the unified 9-key result dict."""
    result = DRValidationResult()

    # 1. Schema gate — the only short-circuit (no typed model => nothing to audit).
    model = validate_schema(dr, result)
    if model is None:
        result.module_audit = {"checked": 0, "findings": [], "ok": False}
        result.layer_audit = {"present_layers": [], "missing_layers": [], "findings": [], "ok": False}
        result.compile_audit = {
            "scheduling_gate": {"ok": False, "findings": []},
            "orchestration_gate": {"ok": False, "findings": []},
            "feasibility_gate": {"ok": False, "findings": []},
            "safety_gate": {"ok": False, "findings": []},
            "ok": False,
        }
        result.orchestration_compatibility = False
        result.pseudo_dag = []
        return result.to_dict()

    # 2. Independent declarative validators (collect all findings, no short-circuit).
    validate_scheduling(model, result)
    validate_capabilities(model, result)
    validate_capability_profile(model, result)
    validate_skill_policy(model, result)
    validate_risk(model, result, baseline=baseline)
    validate_security_manifest(model, result)

    # 3. Pseudo-DAG (needed before compile_audit gates B/C/D).
    pseudo_dag, orch_ok = build_pseudo_dag(model, result)
    result.pseudo_dag = pseudo_dag
    result.orchestration_compatibility = orch_ok

    # 4. Upgraded 6.3 three-layer audit.
    result.module_audit = module_audit(model, result)
    result.layer_audit = layer_audit(model, result, pseudo_dag)
    result.compile_audit = compile_audit(model, result, pseudo_dag, orch_ok)

    return result.to_dict()
