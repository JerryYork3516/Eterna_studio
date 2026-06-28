"""Upgraded 6.3 three-layer audit: Module / Layer / Compile (+ 4 compile gates).

Pure declarative auditing. It consumes the already-built pseudo-DAG and the
static registries; it never executes, schedules, or calls anything.

Each audit returns a sub-result dict and also routes its findings into the shared
DRValidationResult. To avoid double-counting, the Scheduling Validity Gate reuses
the consistency findings already added by `validate_scheduling` for its `ok`
status but does NOT re-add them to the result.
"""

from __future__ import annotations

from typing import Any, Dict, List

from ....models.v0_4 import CANONICAL_LAYER_IDS
from ....registry.engine_registry import engine_registry_map
from ....registry.module_catalog import module_catalog_map
from ..dr_v0_2_schema import (
    DigitalResidentV02Gate,
    InterruptPolicy as IPolicy,
    PreemptionPolicy as PPolicy,
    RiskLevelDecl,
    SchedulingMode,
)
from .dr_validation_result import DRValidationResult, finding
from .orchestration_compatibility import dag_edges, dag_nodes
from .scheduling_policy_validator import scheduling_consistency_findings

_TOOLS_LAYER = "layer_9"
_SAFETY_LAYER = "layer_3"
_PROVIDER_CONFIG_KEYS = {
    "api_key",
    "apikey",
    "key",
    "token",
    "access_token",
    "bearer",
    "secret",
    "url",
    "base_url",
    "endpoint",
    "provider_id",
    "provider_config",
    "credentials",
}
_REAL_PROVIDER_NAMES = {
    "openai",
    "anthropic",
    "claude",
    "gemini",
    "deepseek",
    "qwen",
    "elevenlabs",
    "volcano",
    "groq",
    "together",
}


def provider_boundary_findings(value: Any, path: str, code: str) -> List[Dict[str, Any]]:
    """Find forbidden provider runtime config in declarative DR data."""
    findings: List[Dict[str, Any]] = []

    def walk(node: Any, current_path: str) -> None:
        if isinstance(node, dict):
            for key, child in node.items():
                key_l = str(key).lower()
                child_path = f"{current_path}.{key}" if current_path else str(key)
                if key_l in _PROVIDER_CONFIG_KEYS:
                    findings.append(
                        finding("FAIL", code, f"provider runtime config field {key!r} is forbidden", child_path)
                    )
                if key_l == "provider":
                    allowed_mock_memory = child_path.endswith("memory_policy.provider") and child == "mock"
                    if child not in (None, "", "mock") and not allowed_mock_memory:
                        findings.append(
                            finding("FAIL", code, f"direct provider binding {child!r} is forbidden", child_path)
                        )
                walk(child, child_path)
            return
        if isinstance(node, list):
            for index, child in enumerate(node):
                walk(child, f"{current_path}[{index}]")
            return
        if isinstance(node, str):
            lowered = node.lower().strip()
            if lowered in _REAL_PROVIDER_NAMES or lowered.startswith("sk-") or lowered.startswith(("http://", "https://")):
                findings.append(
                    finding("FAIL", code, f"real provider/config value {node!r} is forbidden", current_path)
                )

    walk(value, path)
    return findings


def _resolved_tool_modules(model: DigitalResidentV02Gate):
    """Yield (index, tool, module_or_None) for each declared tool."""
    modules = module_catalog_map()
    for i, tool in enumerate(model.capabilities.tools):
        ref_id = tool.module_id or tool.tool_id
        yield i, tool, modules.get(ref_id)


# --- ① Module Audit --------------------------------------------------------
def module_audit(model: DigitalResidentV02Gate, result: DRValidationResult) -> Dict[str, Any]:
    findings: List[Dict[str, Any]] = []
    sp = model.scheduling_policy
    declared_slot_types = {s.slot_type for s in model.capabilities.slots}
    checked = 0

    for i, tool, module in _resolved_tool_modules(model):
        checked += 1
        path = f"capabilities.tools[{i}]"
        if module is None:
            findings.append(finding("FAIL", "DR_MAUDIT_MODULE_UNKNOWN", f"tool {tool.tool_id} does not resolve to a catalog module", path))
            continue
        # slot compatibility: a module slot_type must be served by a declared slot.
        if module.slot_type is not None and module.slot_type.value not in declared_slot_types:
            findings.append(finding("FAIL", "DR_MAUDIT_SLOT_INCOMPAT", f"module {module.module_id} needs slot_type {module.slot_type.value!r} but no slot declares it", path))
        # module -> scheduling_policy compatibility (new): a human-gated module
        # cannot be preempted / immediately interrupted.
        if module.human_confirm_required and (
            sp.preemption == PPolicy.priority_based or sp.interrupt_policy == IPolicy.immediate
        ):
            findings.append(finding("FAIL", "DR_MAUDIT_SCHED_INCOMPAT", f"human-gated module {module.module_id} is incompatible with preemption/immediate-interrupt", path))
        # declared execution constraints support (new).
        if "no_external_io" in model.execution_policy.execution_constraints and module.risk_level.value != "none":
            findings.append(finding("WARNING", "DR_MAUDIT_CONSTRAINT_UNSUPPORTED", f"module {module.module_id} (risk={module.risk_level.value}) may violate 'no_external_io'", path))

    findings.extend(
        provider_boundary_findings(model.model_dump(mode="json"), "dr", "DR_MAUDIT_PROVIDER_CONFIG")
    )
    result.add_all(findings)
    return {"checked": checked, "findings": findings, "ok": not any(f["status"] == "FAIL" for f in findings)}


# --- ② Layer Audit ---------------------------------------------------------
def layer_audit(
    model: DigitalResidentV02Gate, result: DRValidationResult, pseudo_dag: List[Dict[str, Any]]
) -> Dict[str, Any]:
    findings: List[Dict[str, Any]] = []
    referenced: set = set()

    for _i, _tool, module in _resolved_tool_modules(model):
        if module is not None:
            referenced.add(module.layer_id)
    for lid in model.stability_constraints.immutable_layers:
        referenced.add(lid)

    # illegal layer placement (referenced layer must be canonical).
    for lid in sorted(referenced):
        if lid not in CANONICAL_LAYER_IDS:
            findings.append(finding("FAIL", "DR_LAUDIT_LAYER_INVALID", f"referenced layer {lid!r} is not a canonical layer", "layers"))

    # layer dependency: tools layer present requires the safety layer present.
    if _TOOLS_LAYER in referenced and _SAFETY_LAYER not in referenced:
        findings.append(finding("FAIL", "DR_LAUDIT_DEP_BROKEN", "tools layer (layer_9) requires safety layer (layer_3) to be present", "stability_constraints.immutable_layers"))

    # priority conflict: a layer both immutable and named in a forbidden_transition.
    immutable = set(model.stability_constraints.immutable_layers)
    for t in model.stability_constraints.forbidden_transitions:
        head = t.split("->")[0].strip()
        if head in immutable:
            findings.append(finding("WARNING", "DR_LAUDIT_PRIORITY_CONFLICT", f"layer {head} is immutable yet appears in forbidden_transition {t!r}", "stability_constraints.forbidden_transitions"))

    # execution-order feasibility (new): a step that depends on an unbindable
    # prerequisite cannot be ordered.
    unbound = {n["id"] for n in dag_nodes(pseudo_dag) if n.get("requires_slot_type") and not n.get("binding")}
    for e in dag_edges(pseudo_dag):
        if e["from"] in unbound:
            findings.append(finding("FAIL", "DR_LAUDIT_ORDER_INFEASIBLE", f"step {e['to']} depends on unbindable prerequisite {e['from']}", "intent_model.intents"))

    findings.extend(provider_boundary_findings(pseudo_dag, "pseudo_dag", "DR_LAUDIT_PROVIDER_CONFIG"))
    result.add_all(findings)
    present = sorted(lid for lid in referenced if lid in CANONICAL_LAYER_IDS)
    missing = sorted(CANONICAL_LAYER_IDS - referenced)
    return {
        "present_layers": present,
        "missing_layers": missing,
        "findings": findings,
        "ok": not any(f["status"] == "FAIL" for f in findings),
    }


# --- ③ Compile Audit (4 gates) ---------------------------------------------
def _gate(findings: List[Dict[str, Any]]) -> Dict[str, Any]:
    return {"ok": not any(f["status"] == "FAIL" for f in findings), "findings": findings}


def compile_audit(
    model: DigitalResidentV02Gate,
    result: DRValidationResult,
    pseudo_dag: List[Dict[str, Any]],
    orch_ok: bool,
) -> Dict[str, Any]:
    sp = model.scheduling_policy
    engines = engine_registry_map()
    modules = module_catalog_map()

    # A. Scheduling Validity Gate. Reuse consistency findings for ok (already
    #    added to result by validate_scheduling — do NOT re-add). Add only new codes.
    consistency = scheduling_consistency_findings(model)
    gate_a_new: List[Dict[str, Any]] = []
    if sp.interrupt_policy == IPolicy.immediate and sp.preemption == PPolicy.disabled and sp.mode == SchedulingMode.adaptive:
        gate_a_new.append(finding("FAIL", "DR_CAUDIT_SCHED_IMPOSSIBLE", "adaptive + immediate interrupt + disabled preemption is not executable", "scheduling_policy"))
    result.add_all(gate_a_new)
    scheduling_gate = _gate(consistency + gate_a_new)

    # B. Orchestration Compatibility Gate. Consume File 10 output; do not rebuild.
    gate_b: List[Dict[str, Any]] = []
    if not orch_ok or not pseudo_dag:
        gate_b.append(finding("FAIL", "DR_CAUDIT_ORCH_FAIL", "DR cannot produce a valid orchestration pseudo-DAG", "intent_model"))
    result.add_all(gate_b)
    orchestration_gate = _gate(gate_b)

    # C. Execution Feasibility Gate. slot->engine exists, tool resolvable, path unbroken.
    gate_c: List[Dict[str, Any]] = []
    nodes = dag_nodes(pseudo_dag)
    edges = dag_edges(pseudo_dag)
    for n in nodes:
        binding = n.get("binding") or {}
        eng = binding.get("engine_binding")
        if eng and eng not in engines:
            gate_c.append(finding("FAIL", "DR_CAUDIT_FEAS_NO_ENGINE", f"step {n['id']} binds unknown engine {eng!r}", "intent_model.intents"))
        if eng and eng in engines:
            from ....registry.provider_registry import resolve_provider_for_engine

            if resolve_provider_for_engine(eng) is None:
                gate_c.append(finding("FAIL", "DR_CAUDIT_FEAS_NO_PROVIDER", f"engine {eng!r} has no registered mock provider", "intent_model.intents"))
        tool_id = binding.get("tool_id")
        if tool_id and tool_id not in modules:
            gate_c.append(finding("FAIL", "DR_CAUDIT_FEAS_NO_TOOL", f"step {n['id']} binds unresolved tool {tool_id!r}", "intent_model.intents"))
    gate_c.extend(provider_boundary_findings(model.model_dump(mode="json"), "dr", "DR_CAUDIT_PROVIDER_CONFIG"))
    # path break: a non-root node unreachable from any root.
    if nodes:
        incoming = {n["id"]: 0 for n in nodes}
        adj: Dict[str, List[str]] = {n["id"]: [] for n in nodes}
        for e in edges:
            if e["to"] in incoming:
                incoming[e["to"]] += 1
            if e["from"] in adj:
                adj[e["from"]].append(e["to"])
        roots = [nid for nid, deg in incoming.items() if deg == 0]
        reachable: set = set()
        stack = list(roots)
        while stack:
            cur = stack.pop()
            if cur in reachable:
                continue
            reachable.add(cur)
            stack.extend(adj.get(cur, []))
        for nid in incoming:
            if nid not in reachable:
                gate_c.append(finding("FAIL", "DR_CAUDIT_FEAS_PATH_BREAK", f"step {nid} is unreachable from any root (path break)", "intent_model.intents"))
    result.add_all(gate_c)
    feasibility_gate = _gate(gate_c)

    # D. Safety Execution Gate.
    gate_d: List[Dict[str, Any]] = []
    forbidden = set(model.risk_policy.forbidden_tool_paths)
    blocked = set(model.risk_policy.blocked_modules)
    risk_unsafe = model.risk_policy.risk_level in {RiskLevelDecl.high, RiskLevelDecl.critical}
    for n in nodes:
        binding = n.get("binding") or {}
        tool_id = binding.get("tool_id")
        if tool_id:
            if tool_id in forbidden:
                gate_d.append(finding("FAIL", "DR_CAUDIT_SAFETY_FORBIDDEN_TOOL", f"step {n['id']} binds forbidden tool {tool_id!r}", "risk_policy.forbidden_tool_paths"))
            if tool_id in blocked:
                gate_d.append(finding("FAIL", "DR_CAUDIT_SAFETY_BLOCKED_IN_PATH", f"blocked module {tool_id!r} appears in execution path", "risk_policy.blocked_modules"))
            if risk_unsafe and not model.risk_policy.human_confirm_required:
                gate_d.append(finding("FAIL", "DR_CAUDIT_SAFETY_UNCONFIRMED", f"unsafe risk_level with tool step {n['id']} requires human_confirm_required", "risk_policy.human_confirm_required"))
    result.add_all(gate_d)
    safety_gate = _gate(gate_d)

    return {
        "scheduling_gate": scheduling_gate,
        "orchestration_gate": orchestration_gate,
        "feasibility_gate": feasibility_gate,
        "safety_gate": safety_gate,
        "ok": all(g["ok"] for g in (scheduling_gate, orchestration_gate, feasibility_gate, safety_gate)),
    }
