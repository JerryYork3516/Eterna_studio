"""Execution Adapter Layer — the ONLY entry that calls the v0.3 runtime.

This module is the single, narrow surface through which the v0.4 control plane
reaches the v0.3 execution core. It shields v0.3 details: callers pass a
WorkflowV03 and an action, and receive a plain dict result. No v0.4 code calls
the v0.3 execution functions directly — everything routes through here.

It executes nothing new: it merely forwards to the unchanged v0.3 services
(audit / mock-run / resident compile). No real AI/provider is ever invoked.
"""

from __future__ import annotations

from typing import Any, Dict

from ..models.v0_3 import WorkflowV03
from ..models.v0_4 import V4ExecutionPlan
from ..services.audit_v0_3 import audit_resident, audit_workflow
from ..services.workflow_v0_3 import compile_resident_from_workflow, mock_run_v0_3

SUPPORTED_ACTIONS = ("validate", "audit", "mock_run", "compile")


class ExecutionBlockedError(RuntimeError):
    """Raised when a V4ExecutionPlan was blocked by the permission/risk gate."""


def execute_plan(plan: V4ExecutionPlan) -> Dict[str, Any]:
    """Strict boundary entry: accept a V4ExecutionPlan and run it on v0.3.

    This is the only path the control plane uses to reach the runtime. The
    orchestrator never imports the v0.3 runtime nor reconstructs the workflow
    itself — it hands the plan here. A blocked plan is never executed.
    """
    if plan.blocked:
        raise ExecutionBlockedError("execution plan was blocked by the permission/risk gate")
    workflow = WorkflowV03.model_validate(plan.v0_3_workflow)
    return run_v0_3(workflow, plan.action)


def run_v0_3(workflow: WorkflowV03, action: str) -> Dict[str, Any]:
    """Forward a translated v0.3 workflow to the v0.3 runtime. Read-only bridge.

    Internal to the adapter; the control plane reaches this only via execute_plan.
    """
    if action == "validate":
        report = audit_workflow(workflow)
        return {"valid": report.status.value != "FAIL", "audit": report.model_dump(mode="json")}
    if action == "audit":
        return {"audit": audit_workflow(workflow).model_dump(mode="json")}
    if action == "mock_run":
        return {"run": mock_run_v0_3(workflow).model_dump(mode="json")}
    if action == "compile":
        resident = compile_resident_from_workflow(workflow)
        return {
            "resident_instance": resident.model_dump(mode="json"),
            "audit": audit_resident(resident).model_dump(mode="json"),
        }
    raise ValueError(f"unsupported execution action: {action!r}")
