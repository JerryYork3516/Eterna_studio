"""Permission / risk gating, audit-log builder, and runtime check priority (v0.4).

Risk rules (fixed):
  low      -> auto execute (no audit required)
  medium   -> allowed, MUST record an audit log entry
  high     -> MUST pass a permission check before execution; audited
  critical -> MUST be human-confirmed or rejected; NEVER silently executed; audited

These gates are protocol logic only. No capability is actually executed here and
no real provider is called.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from ..models.v0_4 import (
    AuditLogEntryV04,
    Decision,
    PermissionDecisionV04,
    PermissionResult,
    RiskLevel,
)
from ..util import gen_id, now

# Runtime check priority — NOT the 13-layer order. The 13-layer protocol order
# is frozen elsewhere and is unrelated to this execution-time gate ordering.
RUNTIME_CHECK_PRIORITY = [
    {"phase": 1, "name": "legal_permission_audit", "checks": ["legal", "permission", "audit"]},
    {"phase": 2, "name": "identity_persona_memory", "checks": ["identity", "persona", "memory"]},
    {"phase": 3, "name": "capability_agent_tool", "checks": ["capability", "agent", "tool"]},
    {"phase": 4, "name": "ui_output", "checks": ["ui", "output"]},
]


def runtime_check_order() -> list[dict]:
    """Fixed runtime gate order. Legal/permission/audit always precede capability
    execution; UI/Output only displays results and holds no final decision power."""
    return [dict(phase) for phase in RUNTIME_CHECK_PRIORITY]


def should_audit(risk_level: RiskLevel) -> bool:
    return risk_level in {RiskLevel.medium, RiskLevel.high, RiskLevel.critical}


def evaluate_permission(
    risk_level: RiskLevel,
    *,
    permission_granted: bool = False,
    human_confirmed: bool = False,
) -> PermissionDecisionV04:
    audit_required = should_audit(risk_level)

    if risk_level == RiskLevel.low:
        result, decision, reason = PermissionResult.allowed, Decision.allowed, "low risk: auto execute"
    elif risk_level == RiskLevel.medium:
        result, decision, reason = PermissionResult.allowed, Decision.allowed, "medium risk: allowed, audit recorded"
    elif risk_level == RiskLevel.high:
        if permission_granted:
            result, decision, reason = PermissionResult.allowed, Decision.allowed, "high risk: permission granted"
        else:
            result, decision, reason = PermissionResult.denied, Decision.blocked, "high risk: permission not granted"
    elif risk_level == RiskLevel.critical:
        if human_confirmed:
            result, decision, reason = PermissionResult.allowed, Decision.allowed, "critical risk: human confirmed"
        else:
            result, decision, reason = (
                PermissionResult.requires_human_confirm,
                Decision.blocked,
                "critical risk: human confirmation required; never silently executed",
            )
    else:  # RiskLevel.none
        result, decision, reason = PermissionResult.allowed, Decision.allowed, "no declared risk"

    return PermissionDecisionV04(
        risk_level=risk_level,
        permission_result=result,
        blocked_or_allowed=decision,
        audit_required=audit_required,
        decision_reason=reason,
    )


def build_audit_entry(
    decision: PermissionDecisionV04,
    *,
    module_id: Optional[str] = None,
    actor: str = "system",
    input: Optional[Dict[str, Any]] = None,
    output: Optional[Dict[str, Any]] = None,
    human_confirmed_by: Optional[str] = None,
) -> AuditLogEntryV04:
    """Build a factual audit-log entry for a gated action."""
    return AuditLogEntryV04(
        action_id=gen_id("act"),
        module_id=module_id,
        actor=actor,
        input=input or {},
        output=output or {},
        decision_reason=decision.decision_reason,
        risk_level=decision.risk_level,
        permission_result=decision.permission_result,
        blocked_or_allowed=decision.blocked_or_allowed,
        timestamp=now().isoformat(),
        human_confirmed_by=human_confirmed_by,
    )


def gate_action(
    risk_level: RiskLevel,
    *,
    module_id: Optional[str] = None,
    actor: str = "system",
    permission_granted: bool = False,
    human_confirmed: bool = False,
    human_confirmed_by: Optional[str] = None,
    input: Optional[Dict[str, Any]] = None,
    output: Optional[Dict[str, Any]] = None,
) -> tuple[PermissionDecisionV04, Optional[AuditLogEntryV04]]:
    """Evaluate a gated action and, when required, return its audit-log entry.

    high/critical (and medium) actions always produce an audit entry.
    """
    decision = evaluate_permission(
        risk_level,
        permission_granted=permission_granted,
        human_confirmed=human_confirmed,
    )
    entry = None
    if decision.audit_required:
        entry = build_audit_entry(
            decision,
            module_id=module_id,
            actor=actor,
            input=input,
            output=output,
            human_confirmed_by=human_confirmed_by,
        )
    return decision, entry
