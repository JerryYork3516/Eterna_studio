"""V4ExecutionOrchestrator — the v0.4 control plane over the v0.3 runtime.

Flow (strict):

    v0.4 workflow
      -> V4ExecutionOrchestrator   (parse, resolve Node->Slot->Engine, gate)
      -> V4ToV3Translator          (v0.4 -> v0.3 workflow)
      -> Execution Adapter         (single entry to v0.3 runtime)
      -> v0.3 runtime              (mock-run / audit / compile)

The orchestrator never executes workflow logic and never calls a provider. It
plans and routes only; v0.3 stays the sole execution core. A v0.4 workflow can
always be downgraded (fallback) to run on v0.3 through this bridge.
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

from ..models.v0_4 import (
    AuditLogEntryV04,
    PermissionDecisionV04,
    V4ExecutionPlan,
    V4ExecutionResponse,
    V4ResolvedBinding,
    WorkflowV04,
)
from ..registry.engine_registry import engine_registry_map
from ..registry.module_catalog import module_catalog_map
from ..registry.slot_catalog import slot_catalog_map
from .migration_v0_4 import migrate_workflow_to_v0_4
from .permissions_v0_4 import gate_action
from .v3_execution_adapter import SUPPORTED_ACTIONS, run_v0_3
from .v4_translator import translate_v0_4_to_v0_3


def _coerce_to_v0_4(value: Any) -> WorkflowV04:
    if isinstance(value, WorkflowV04):
        return value
    if isinstance(value, dict) and value.get("schema_version") == "0.4.0":
        return WorkflowV04.model_validate(value)
    # v0.3 / legacy input -> migrate up so the control plane has a v0.4 view.
    return migrate_workflow_to_v0_4(value)


def _resolve_bindings(workflow: WorkflowV04) -> List[V4ResolvedBinding]:
    slots = slot_catalog_map()
    engines = engine_registry_map()
    bindings: List[V4ResolvedBinding] = []
    for node in workflow.nodes:
        binding = V4ResolvedBinding(node_id=node.node_id, node_type=node.node_type, module_id=node.module_id)
        if not node.slot_binding:
            binding.note = "no slot bound; node runs as plain v0.3 mock node"
            bindings.append(binding)
            continue
        slot = slots.get(node.slot_binding)
        if slot is None:
            binding.note = f"slot_binding '{node.slot_binding}' not found in slot catalog"
            bindings.append(binding)
            continue
        binding.slot_id = slot.slot_id
        binding.slot_type = slot.slot_type
        binding.execution_mode = slot.execution_mode
        if slot.engine_binding:
            engine = engines.get(slot.engine_binding)
            if engine is not None:
                binding.engine_id = engine.engine_id
                binding.engine_provider = engine.providers[0] if engine.providers else None
                binding.resolved = True
                binding.note = "resolved Node->Slot->Engine (mock provider)"
            else:
                binding.note = f"engine_binding '{slot.engine_binding}' not found in engine registry"
        else:
            binding.note = "slot has no engine_binding"
        bindings.append(binding)
    return bindings


def _gate(workflow: WorkflowV04) -> Tuple[List[PermissionDecisionV04], List[AuditLogEntryV04], bool]:
    catalog = module_catalog_map()
    decisions: List[PermissionDecisionV04] = []
    audit_log: List[AuditLogEntryV04] = []
    blocked = False
    for node in workflow.nodes:
        module = catalog.get(node.module_id) if node.module_id else None
        if module is None:
            continue
        decision, entry = gate_action(module.risk_level, module_id=module.module_id)
        decisions.append(decision)
        if entry is not None:
            audit_log.append(entry)
        if decision.blocked_or_allowed.value == "blocked":
            blocked = True
    return decisions, audit_log, blocked


def plan_execution(value: Any, action: str = "mock_run") -> V4ExecutionPlan:
    if action not in SUPPORTED_ACTIONS:
        raise ValueError(f"unsupported execution action: {action!r}")
    workflow = _coerce_to_v0_4(value)
    bindings = _resolve_bindings(workflow)
    decisions, audit_log, blocked = _gate(workflow)
    wf3 = translate_v0_4_to_v0_3(workflow)
    notes = [
        "control plane only; v0.3 is the sole execution core",
        "execution is forwarded through the Execution Adapter",
    ]
    if blocked:
        notes.append("blocked by permission/risk gate; not forwarded to runtime")
    return V4ExecutionPlan(
        workflow_id=workflow.id,
        action=action,
        resolved_bindings=bindings,
        permission_decisions=decisions,
        audit_log=audit_log,
        blocked=blocked,
        v0_3_workflow=wf3.model_dump(mode="json"),
        notes=notes,
    )


def execute(value: Any, action: str = "mock_run") -> V4ExecutionResponse:
    plan = plan_execution(value, action)
    if plan.blocked:
        return V4ExecutionResponse(executed=False, plan=plan, result={})
    # Forward to v0.3 runtime via the single Execution Adapter.
    from ..models.v0_3 import WorkflowV03

    wf3 = WorkflowV03.model_validate(plan.v0_3_workflow)
    result = run_v0_3(wf3, action)
    return V4ExecutionResponse(executed=True, plan=plan, result=result)
