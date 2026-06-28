"""Orchestration compatibility — build a static **pseudo-DAG** and report whether
the DR is orchestration-compatible.

THIS GENERATES DATA, NOT BEHAVIOR. The pseudo-DAG is a list of plain records
(meta / node / edge). Building it only does registry lookups to decide whether a
binding *exists*; it never invokes a slot, engine, tool, or MCP, and produces no
runnable steps. capability_profile / security_manifest / skill_policy ride along
as declarations in the meta record only — they never become nodes/steps/edges.
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

from ....registry.engine_registry import engine_registry_map
from ..dr_v0_2_schema import DigitalResidentV02Gate, SchedulingMode
from .dr_validation_result import DRValidationResult, finding


# --- pseudo-DAG accessors (the list is the contract; these read it) ---------
def dag_meta(pseudo_dag: List[Dict[str, Any]]) -> Dict[str, Any]:
    for rec in pseudo_dag:
        if rec.get("type") == "meta":
            return rec
    return {}


def dag_nodes(pseudo_dag: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [r for r in pseudo_dag if r.get("type") == "node"]


def dag_edges(pseudo_dag: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [r for r in pseudo_dag if r.get("type") == "edge"]


def _has_cycle(node_ids: List[str], edges: List[Dict[str, Any]]) -> bool:
    """Static DFS cycle detection over from->to edges. No execution."""
    adj: Dict[str, List[str]] = {nid: [] for nid in node_ids}
    for e in edges:
        if e["from"] in adj:
            adj[e["from"]].append(e["to"])
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {nid: WHITE for nid in node_ids}

    def visit(n: str) -> bool:
        color[n] = GRAY
        for m in adj.get(n, []):
            if m not in color:
                continue
            if color[m] == GRAY:
                return True
            if color[m] == WHITE and visit(m):
                return True
        color[n] = BLACK
        return False

    return any(color[nid] == WHITE and visit(nid) for nid in node_ids)


def build_pseudo_dag(
    model: DigitalResidentV02Gate, result: DRValidationResult
) -> Tuple[List[Dict[str, Any]], bool]:
    """Return (pseudo_dag, orchestration_compatible)."""
    im = model.intent_model
    engines = engine_registry_map()
    compatible = True

    # 1. need at least one intent.
    intents = list(im.intents)
    if not im.primary_intent and not intents:
        result.add(finding("FAIL", "DR_ORCH_NO_INTENT", "no primary_intent and no intent steps", "intent_model"))
        return ([], False)
    if not intents:
        # derive a single implicit step from primary_intent.
        from ..dr_v0_2_schema import IntentStep

        intents = [IntentStep(step_id="intent_root", description=im.primary_intent)]

    slot_index = {s.slot_type: s for s in model.capabilities.slots}
    tool_index = {t.tool_id: t for t in model.capabilities.tools}

    # 2. nodes — slot/tool selection (resolution only, never invocation).
    nodes: List[Dict[str, Any]] = []
    for step in intents:
        path = f"intent_model.intents[{step.step_id}]"
        binding: Dict[str, Any] = {}
        if step.requires_slot_type:
            slot = slot_index.get(step.requires_slot_type)
            if slot is None:
                result.add(finding("FAIL", "DR_ORCH_STEP_NO_SLOT", f"step {step.step_id} needs slot_type {step.requires_slot_type!r} but none declared", path))
                compatible = False
            else:
                if slot.engine_binding and slot.engine_binding not in engines:
                    result.add(finding("FAIL", "DR_ORCH_STEP_NO_ENGINE", f"step {step.step_id} slot binds unknown engine {slot.engine_binding!r}", path))
                    compatible = False
                binding = {"slot_id": slot.slot_id, "slot_type": slot.slot_type, "engine_binding": slot.engine_binding}
        if step.requires_tool:
            tool = tool_index.get(step.requires_tool)
            if tool is None:
                result.add(finding("FAIL", "DR_ORCH_STEP_NO_TOOL", f"step {step.step_id} needs tool {step.requires_tool!r} but none declared", path))
                compatible = False
            else:
                binding = {**binding, "tool_id": tool.tool_id}
        nodes.append(
            {
                "type": "node",
                "id": step.step_id,
                "kind": "intent_step",
                "requires_slot_type": step.requires_slot_type,
                "binding": binding or None,
                "parallelizable": step.parallelizable,
            }
        )

    node_ids = [n["id"] for n in nodes]

    # 3. edges from depends_on.
    edges: List[Dict[str, Any]] = []
    for step in intents:
        for dep in step.depends_on:
            if dep not in node_ids:
                result.add(finding("FAIL", "DR_ORCH_BAD_DEPENDENCY", f"step {step.step_id} depends on unknown step {dep!r}", f"intent_model.intents[{step.step_id}]"))
                compatible = False
            else:
                edges.append({"type": "edge", "from": dep, "to": step.step_id, "kind": "depends_on"})

    if _has_cycle(node_ids, edges):
        result.add(finding("FAIL", "DR_ORCH_CYCLE", "intent dependency graph has a cycle", "intent_model.intents"))
        compatible = False

    # 4. shape per scheduling mode (static graph annotation only).
    mode = model.scheduling_policy.mode
    if mode == SchedulingMode.serial:
        shape = "linear"
        if not edges and len(node_ids) > 1:
            # chain in declared order
            edges = [
                {"type": "edge", "from": node_ids[i], "to": node_ids[i + 1], "kind": "sequence"}
                for i in range(len(node_ids) - 1)
            ]
    elif mode == SchedulingMode.semi_parallel:
        shape = "fan_out_fan_in"
    else:
        shape = "adaptive_conditional"
        for n in nodes:
            n["conditional"] = True

    # 5/6. meta record carries the three declarative sections (data only).
    meta = {
        "type": "meta",
        "shape": shape,
        "mode": mode.value,
        "node_count": len(nodes),
        "capability_profile": model.capability_profile.model_dump(mode="json"),
        "security_manifest": model.security_manifest.model_dump(mode="json"),
        "skill_policy": model.skill_policy.model_dump(mode="json"),
    }

    pseudo_dag: List[Dict[str, Any]] = [meta, *nodes, *edges]
    return (pseudo_dag, compatible)
