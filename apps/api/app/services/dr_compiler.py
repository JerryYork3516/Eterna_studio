"""DR Compiler v0.1 — Stage 6.2 Canvas -> .digital_resident compile chain.

Pipeline (single direction, no execution):
    collect (13 layers / modules / slots from canvas + catalog)
      -> validate (completeness / id uniqueness / slot matching / provider binding)
      -> assemble (resident blueprint)
      -> wrap (DR metadata: dr_version / schema_version / file_type)
      -> emit .digital_resident file payload

Execution boundary (do not violate):
  * This is a pure compiler. It NEVER executes anything, never calls a provider,
    never touches the Stage 6 Runtime Kernel (execution_engine / trace / memory /
    state). No real LLM / memory / tool.
  * The produced DR is the unified input protocol for Stage 7/8 and is read back
    by the runtime only through a mock loader (`mock_load_dr`) that parses — it
    does not run.

Schema contract: the DR v0.1 field set below is frozen. Only ADD fields in later
versions — never rename or remove. `DR_VERSION` gates the contract.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ..models.v0_4 import (
    CANONICAL_LAYERS,
    CANONICAL_LAYER_IDS,
    PROTOCOL_VERSION_V0_4,
    SCHEMA_VERSION_V0_4,
    SlotType,
)
from ..registry.engine_registry import get_engine_registry
from ..registry.module_catalog import get_module_catalog
from ..registry.slot_catalog import get_slot_catalog

DR_VERSION = "0.1"
FILE_TYPE = "digital_resident"
FILE_SUFFIX = ".digital_resident"
COMPILER_NAME = "DRCompiler"
COMPILER_VERSION = "0.1.0"
RUNTIME_VERSION = "resident_v1_mock"
MIN_KERNEL = "6.1"

# Allowed slot_types this stage (mock-only capability interfaces).
_ALLOWED_SLOT_TYPES = frozenset(t.value for t in SlotType)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _finding(status: str, code: str, message: str, path: str) -> Dict[str, str]:
    return {"status": status, "code": code, "message": message, "path": path}


def _as_dict(value: Any) -> Dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, dict):
        return value
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    return {}


def _slugify(text: str) -> str:
    cleaned = "".join(c if c.isalnum() else "_" for c in (text or "").strip().lower())
    while "__" in cleaned:
        cleaned = cleaned.replace("__", "_")
    return cleaned.strip("_") or "digital_resident"


# --- 1. collect ------------------------------------------------------------
def collect_canvas(canvas: Dict[str, Any]) -> Dict[str, Any]:
    """Collect the 13 layers, modules and slots from the canvas + catalog.

    The canvas (workflow + nodes + edges) defines which layers are present. The
    module / slot capability content comes from the catalog unless the canvas
    explicitly carries its own `modules` / `slots` arrays (which then win).
    """
    canvas = canvas or {}
    workflow = _as_dict(canvas.get("workflow")) or canvas
    nodes = canvas.get("nodes") or workflow.get("nodes") or []
    edges = canvas.get("edges") or workflow.get("edges") or []

    # Modules: prefer canvas-supplied, else the authoritative catalog.
    raw_modules = canvas.get("modules") or workflow.get("modules")
    if raw_modules:
        modules = [_as_dict(m) for m in raw_modules]
    else:
        modules = [m.model_dump(mode="json") for m in get_module_catalog()]

    # Slots: prefer canvas-supplied, else the catalog.
    raw_slots = canvas.get("slots") or workflow.get("slots")
    if raw_slots:
        slots = [_as_dict(s) for s in raw_slots]
    else:
        slots = [s.model_dump(mode="json") for s in get_slot_catalog()]

    # Which canonical layers are present ON THE CANVAS. Presence is derived from
    # the canvas graph (a node whose id is a layer_id, or a node referencing a
    # layer_id) — NOT from the catalog fallback, so the completeness check
    # reflects what the user actually has on the canvas.
    present_layer_ids: set[str] = set()
    for node in nodes:
        node = _as_dict(node)
        node_id = node.get("node_id") or node.get("id")
        if node_id in CANONICAL_LAYER_IDS:
            present_layer_ids.add(node_id)
        layer_ref = node.get("layer_id")
        if layer_ref in CANONICAL_LAYER_IDS:
            present_layer_ids.add(layer_ref)

    # Group module_ids per layer.
    modules_by_layer: Dict[str, List[str]] = {}
    for module in modules:
        modules_by_layer.setdefault(module.get("layer_id", ""), []).append(module.get("module_id", ""))

    layers: List[Dict[str, Any]] = []
    for layer_id, layer_name, layer_order in CANONICAL_LAYERS:
        layers.append(
            {
                "layer_id": layer_id,
                "layer_name": layer_name,
                "layer_order": layer_order,
                "module_ids": modules_by_layer.get(layer_id, []),
                "present": layer_id in present_layer_ids,
            }
        )

    return {
        "workflow": workflow,
        "nodes": [_as_dict(n) for n in nodes],
        "edges": [_as_dict(e) for e in edges],
        "layers": layers,
        "modules": modules,
        "slots": slots,
    }


# --- 2. validate -----------------------------------------------------------
def validate_collection(collection: Dict[str, Any]) -> List[Dict[str, str]]:
    """Run the four mandatory DR checks. Returns a list of findings.

    1. 13 layers completeness
    2. module_id uniqueness
    3. slot_type <-> module slot_type matching
    4. no illegal runtime provider binding (mock-only this stage)
    """
    findings: List[Dict[str, str]] = []
    layers = collection["layers"]
    modules = collection["modules"]
    slots = collection["slots"]

    # 1. 13 layers completeness ------------------------------------------------
    present_ids = {layer["layer_id"] for layer in layers if layer.get("present")}
    defined_ids = {layer["layer_id"] for layer in layers}
    missing_defined = CANONICAL_LAYER_IDS - defined_ids
    if missing_defined:
        findings.append(
            _finding("FAIL", "DR_LAYERS_INCOMPLETE", f"missing canonical layers: {sorted(missing_defined)}", "layers")
        )
    missing_on_canvas = CANONICAL_LAYER_IDS - present_ids
    if missing_on_canvas:
        findings.append(
            _finding(
                "WARNING",
                "DR_LAYER_NOT_ON_CANVAS",
                f"canonical layers not present on canvas: {sorted(missing_on_canvas)}",
                "layers",
            )
        )
    if len(layers) != len(CANONICAL_LAYERS):
        findings.append(
            _finding("FAIL", "DR_LAYER_COUNT", f"expected {len(CANONICAL_LAYERS)} layers, got {len(layers)}", "layers")
        )

    # 2. module_id uniqueness --------------------------------------------------
    seen: set[str] = set()
    for index, module in enumerate(modules):
        module_id = module.get("module_id")
        if not module_id:
            findings.append(_finding("FAIL", "DR_MODULE_ID_EMPTY", "module has empty module_id", f"modules[{index}]"))
            continue
        if module_id in seen:
            findings.append(
                _finding("FAIL", "DR_MODULE_ID_DUPLICATE", f"duplicate module_id: {module_id}", f"modules[{index}]")
            )
        seen.add(module_id)
        # module.layer_id must be canonical.
        if module.get("layer_id") not in CANONICAL_LAYER_IDS:
            findings.append(
                _finding(
                    "FAIL",
                    "DR_MODULE_LAYER_INVALID",
                    f"module {module_id} bound to non-canonical layer {module.get('layer_id')!r}",
                    f"modules[{index}].layer_id",
                )
            )

    # 3. slot_type <-> module slot_type matching ------------------------------
    available_slot_types = {s.get("slot_type") for s in slots}
    for index, slot in enumerate(slots):
        slot_type = slot.get("slot_type")
        if slot_type not in _ALLOWED_SLOT_TYPES:
            findings.append(
                _finding(
                    "FAIL",
                    "DR_SLOT_TYPE_INVALID",
                    f"slot {slot.get('slot_id')} uses unknown slot_type {slot_type!r}",
                    f"slots[{index}].slot_type",
                )
            )
    for index, module in enumerate(modules):
        slot_type = module.get("slot_type")
        if slot_type is None:
            continue
        if slot_type not in _ALLOWED_SLOT_TYPES:
            findings.append(
                _finding(
                    "FAIL",
                    "DR_MODULE_SLOT_TYPE_INVALID",
                    f"module {module.get('module_id')} declares unknown slot_type {slot_type!r}",
                    f"modules[{index}].slot_type",
                )
            )
        elif slot_type not in available_slot_types:
            findings.append(
                _finding(
                    "FAIL",
                    "DR_SLOT_TYPE_UNMATCHED",
                    f"module {module.get('module_id')} needs slot_type {slot_type!r} but no slot provides it",
                    f"modules[{index}].slot_type",
                )
            )

    # 4. no illegal runtime provider binding ----------------------------------
    # Stage 6.x is mock-only: a Slot must NOT bind a real provider. engine_binding
    # may only reference a known (mock) engine; provider must be empty.
    known_engines = {e.engine_id for e in get_engine_registry()}
    for index, slot in enumerate(slots):
        provider = slot.get("provider")
        if provider:
            findings.append(
                _finding(
                    "FAIL",
                    "DR_ILLEGAL_PROVIDER",
                    f"slot {slot.get('slot_id')} binds a real provider {provider!r} (mock-only stage)",
                    f"slots[{index}].provider",
                )
            )
        engine_binding = slot.get("engine_binding")
        if engine_binding and engine_binding not in known_engines:
            findings.append(
                _finding(
                    "FAIL",
                    "DR_ILLEGAL_ENGINE_BINDING",
                    f"slot {slot.get('slot_id')} binds unknown engine {engine_binding!r}",
                    f"slots[{index}].engine_binding",
                )
            )

    return findings


# --- 3. assemble -----------------------------------------------------------
def assemble_blueprint(collection: Dict[str, Any], resident_name: Optional[str] = None) -> Dict[str, Any]:
    """Assemble the resident blueprint (no metadata wrap yet)."""
    workflow = collection["workflow"]
    modules = collection["modules"]
    slots = collection["slots"]
    layers = collection["layers"]

    name = resident_name or workflow.get("name") or "Digital Resident"
    resident_id = _slugify(name)

    # Safety policy derived from module flags (declarative only).
    risk_order = ["none", "low", "medium", "high", "critical"]
    max_risk = "none"
    for module in modules:
        risk = module.get("risk_level", "none")
        if risk in risk_order and risk_order.index(risk) > risk_order.index(max_risk):
            max_risk = risk
    audit_required = any(m.get("audit_required") for m in modules)
    human_confirm_required = any(m.get("human_confirm_required") for m in modules)

    required_slot_types = sorted({m.get("slot_type") for m in modules if m.get("slot_type")})
    engines = [
        {"engine_id": e.engine_id, "supported_slot_types": [t.value for t in e.supported_slot_types]}
        for e in get_engine_registry()
    ]

    return {
        "resident": {
            "resident_id": resident_id,
            "name": name,
            "role": "digital_resident",
            "description": workflow.get("metadata", {}).get("description")
            if isinstance(workflow.get("metadata"), dict)
            else None,
            "disclosure": "AI-generated digital resident; synthetic persona.",
            "dr_version": DR_VERSION,
            "template_type": workflow.get("template_type", "schema_v04"),
        },
        "layers": layers,
        "modules": modules,
        "slots": slots,
        "runtime_requirements": {
            "runtime_version": RUNTIME_VERSION,
            "min_kernel": MIN_KERNEL,
            "execution_mode": "mock",
            "required_slot_types": required_slot_types,
            "engines": engines,
        },
        "memory_config": {
            "provider": "mock",
            "store": "in_process",
            "isolation": "per_resident",
            "persistence": False,
        },
        "safety_policy": {
            "disclosure_required": True,
            "audit_required": audit_required,
            "human_confirm_required": human_confirm_required,
            "risk_level": max_risk,
            "blocked_modules": [],
        },
    }


# --- 4. wrap + emit --------------------------------------------------------
def compile_dr(canvas: Dict[str, Any], resident_name: Optional[str] = None) -> Dict[str, Any]:
    """Run the full compile pipeline and return the wrapped DR document (dict).

    The returned dict is the literal content of the .digital_resident file.
    """
    collection = collect_canvas(canvas)
    findings = validate_collection(collection)
    blueprint = assemble_blueprint(collection, resident_name=resident_name)

    valid = not any(f["status"] == "FAIL" for f in findings)
    audit = {
        "valid": valid,
        "findings": findings,
        "checked_at": _now_iso(),
        "summary": {
            "fail": sum(1 for f in findings if f["status"] == "FAIL"),
            "warning": sum(1 for f in findings if f["status"] == "WARNING"),
            "pass": sum(1 for f in findings if f["status"] == "PASS"),
        },
    }
    compile_info = {
        "compiler": COMPILER_NAME,
        "compiler_version": COMPILER_VERSION,
        "compiled_at": _now_iso(),
        "source": "canvas",
        "layer_count": len(collection["layers"]),
        "module_count": len(collection["modules"]),
        "slot_count": len(collection["slots"]),
        "schema_version": SCHEMA_VERSION_V0_4,
        "protocol_version": PROTOCOL_VERSION_V0_4,
    }

    # DR metadata wrap (frozen v0.1 contract) + blueprint + audit + compile_info.
    dr: Dict[str, Any] = {
        "file_type": FILE_TYPE,
        "dr_version": DR_VERSION,
        "schema_version": SCHEMA_VERSION_V0_4,
        "protocol_version": PROTOCOL_VERSION_V0_4,
        **blueprint,
        "audit": audit,
        "compile_info": compile_info,
    }
    return dr


def dr_filename(dr: Dict[str, Any]) -> str:
    """Return the download filename: <resident_id>.digital_resident."""
    resident_id = _as_dict(dr.get("resident")).get("resident_id") or "digital_resident"
    return f"{resident_id}{FILE_SUFFIX}"


# --- Stage 6.1 runtime mock load (read-only; does NOT execute) -------------
def mock_load_dr(dr: Dict[str, Any]) -> Dict[str, Any]:
    """Mock-load a DR document as the Stage 6.1 runtime would read it.

    This proves the DR is consumable by the runtime without running anything: it
    parses the envelope, confirms the contract fields, and returns a load
    summary. It NEVER touches the Runtime Kernel (no trace/memory/state).
    """
    dr = dr or {}
    resident = _as_dict(dr.get("resident"))
    ok = (
        dr.get("file_type") == FILE_TYPE
        and dr.get("dr_version") == DR_VERSION
        and bool(resident.get("resident_id"))
        and isinstance(dr.get("layers"), list)
        and isinstance(dr.get("modules"), list)
        and isinstance(dr.get("slots"), list)
    )
    return {
        "loaded": bool(ok),
        "mock": True,
        "resident_id": resident.get("resident_id"),
        "dr_version": dr.get("dr_version"),
        "runtime_version": RUNTIME_VERSION,
        "layer_count": len(dr.get("layers") or []),
        "module_count": len(dr.get("modules") or []),
        "slot_count": len(dr.get("slots") or []),
        "audit_valid": bool(_as_dict(dr.get("audit")).get("valid")),
    }


# --- Stage 6.3.3: compile-only result (compile + validate, NO download) -----
# The DR v0.2 candidate below is a deterministic, declarative policy view derived
# from the canvas. It is what `validate_dr_v0_2` (the Gate) inspects. Building it
# executes nothing — it is pure data assembly.
def build_dr_v0_2_candidate(canvas: Dict[str, Any], v01_dr: Dict[str, Any]) -> Dict[str, Any]:
    """Derive a DR v0.2 (policy-layer) candidate from the canvas + v0.1 blueprint.

    Deterministic declarative defaults so a structurally-valid canvas yields a
    schedulable, DAG-generatable candidate. No execution, scheduling, or I/O.
    """
    resident = _as_dict(v01_dr.get("resident"))
    name = resident.get("name") or "Digital Resident"
    resident_id = resident.get("resident_id") or _slugify(name)
    return {
        "file_type": FILE_TYPE,
        "dr_version": "0.2",
        "schema_version": SCHEMA_VERSION_V0_4,
        "protocol_version": PROTOCOL_VERSION_V0_4,
        "dr_layer": "policy",
        "not_executable": True,
        "identity": {
            "resident_id": resident_id,
            "name": name,
            "role": "digital_resident",
            "disclosure": "AI-generated digital resident; synthetic persona.",
            "tags": [],
        },
        "intent_model": {
            "primary_intent": "resident_dialogue",
            "goals": [],
            "intents": [
                {
                    "step_id": "step_dialogue",
                    "description": "respond to the user",
                    "requires_slot_type": "llm",
                    "depends_on": [],
                }
            ],
            "proactivity": "reactive",
            "domains": [],
        },
        "scheduling_policy": {
            "mode": "serial",
            "priority_model": "fifo",
            "interrupt_policy": "none",
            "preemption": "disabled",
            "max_parallel_hint": 1,
        },
        "execution_policy": {
            "execution_mode": "mock",
            "runtime_version": RUNTIME_VERSION,
            "min_kernel": MIN_KERNEL,
            "required_slot_types": ["llm"],
            "allow_tool_use": False,
            "fallback_mode": "mock_fallback",
            "determinism": "deterministic_mock",
            "execution_constraints": [],
        },
        "capabilities": {
            "slots": [{"slot_id": "slot_llm", "slot_type": "llm", "engine_binding": "llm_mock"}],
            "tools": [],
            "tool_preferences": [],
        },
        "memory_policy": {
            "provider": "mock",
            "store": "in_process",
            "isolation": "per_resident",
            "persistence": False,
        },
        "risk_policy": {
            "disclosure_required": True,
            "audit_required": False,
            "human_confirm_required": False,
            "risk_level": "none",
            "blocked_modules": [],
            "forbidden_tool_paths": [],
            "system_locked": False,
            "system_locked_fields": ["risk_level", "disclosure_required"],
        },
        "stability_constraints": {
            "immutable_layers": ["layer_1", "layer_3"],
            "forbidden_transitions": [],
            "invariants": [],
        },
        "capability_profile": {
            "resident_class": "industry_expertise",
            "primary_type": "industry_expertise",
            "secondary_type": "human_empathy",
            "primary_weight": 0.8,
            "secondary_weight": 0.2,
        },
        "security_manifest": {
            "signature_required": True,
            "license_required": False,
            "watermark_required": True,
            "encryption_required": False,
            "secure_loader_required": True,
        },
        "skill_policy": {
            "allowed_skill_sources": ["official"],
            "unsigned_skill_policy": "deny",
            "sandbox_required": True,
            "required_skills": [],
            "skill_permissions": [],
        },
    }


def compile_dr_result(canvas: Dict[str, Any], resident_name: Optional[str] = None) -> Dict[str, Any]:
    """Compile + validate the canvas WITHOUT downloading. Returns a JSON dict.

    Pipeline: canvas -> compile_dr (v0.1 blueprint + audit) -> derive DR v0.2
    candidate -> validate_dr_v0_2(candidate). The downloadable `compiled_dr` is
    only populated when the result is valid (valid=false must NOT yield a
    downloadable .digital_resident).
    """
    # Local import keeps the policy-layer Gate decoupled from the compiler module.
    from ..dr.v2.validator import validate_dr_v0_2

    v01 = compile_dr(canvas, resident_name=resident_name)
    candidate = build_dr_v0_2_candidate(canvas, v01)
    gate = validate_dr_v0_2(candidate)

    v01_findings = _as_dict(v01.get("audit")).get("findings", []) or []
    v01_errors = [f for f in v01_findings if f.get("status") == "FAIL"]
    v01_warnings = [f for f in v01_findings if f.get("status") == "WARNING"]

    errors = v01_errors + list(gate.get("errors", []))
    warnings = v01_warnings + list(gate.get("warnings", []))
    valid = len(errors) == 0

    filename = dr_filename(v01)
    return {
        "valid": valid,
        "dr_version": gate.get("dr_version", "0.2"),
        "errors": errors,
        "warnings": warnings,
        "module_audit": gate.get("module_audit", {}),
        "layer_audit": gate.get("layer_audit", {}),
        "compile_audit": gate.get("compile_audit", {}),
        "orchestration_compatibility": gate.get("orchestration_compatibility", False),
        "pseudo_dag": gate.get("pseudo_dag", []),
        # The downloadable file content — the DR v0.2 candidate that PASSED
        # validate_dr_v0_2 (NOT the v0.1 wrapper). Only present when valid.
        "compiled_dr": candidate if valid else None,
        # The policy-layer candidate the Gate inspected (always returned, v0.2).
        "dr_payload": candidate,
        "filename": filename,
        "metadata": {
            "filename": filename,
            "schema_version": candidate.get("schema_version"),
            # v0.1 blueprint kept for reference / canvas-structure audit only.
            "v01_compile_info": v01.get("compile_info"),
            "v01_audit": v01.get("audit"),
            "v01_valid": bool(_as_dict(v01.get("audit")).get("valid")),
            "gate_valid": bool(gate.get("valid")),
        },
    }
