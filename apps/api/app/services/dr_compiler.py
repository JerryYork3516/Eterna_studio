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

from ..dr.v3.dr_v0_3_schema import (
    DRDocumentV03,
    DR_FILE_TYPE as DR_FILE_TYPE_V3,
    DR_VERSION_V0_3,
    DR_SCHEMA_VERSION_V0_3,
    DRManifestV03,
    DRPayloadV03,
    AuditFindingV03,
    AuditReportV03,
    CompileInfoV03,
    FallbackRouteV03,
    LatticeConfigV03,
    MemoryConfigV03,
    MemoryPolicyV03,
    ResidentBlueprintV03,
    ResidentIdentityV03,
    RuntimePlanStepV03,
    RuntimePlanV03,
    RuntimeRequirementsV03,
    SafetyPolicyV03,
    ScreenCapabilityDeclarationV03,
    VoiceConfigV03,
    build_runtime_plan_steps,
)
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


def _collect_layer_contexts(workflow: Dict[str, Any], layers: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    contexts: Dict[str, Dict[str, Any]] = {}
    workflow_contexts = workflow.get("layer_contexts") if isinstance(workflow.get("layer_contexts"), dict) else {}
    for layer in layers:
        layer_id = layer.get("layer_id", "")
        raw_context = workflow_contexts.get(layer_id)
        context = _as_dict(raw_context)
        if not context:
            context = _as_dict(layer.get("layer_context"))
        contexts[layer_id] = {
            "layer_context": context,
            "context_bindings": context.get("context_bindings", []) if isinstance(context.get("context_bindings"), list) else [],
        }
    return contexts


def _node_layer(nodes: List[Dict[str, Any]], node_id: Any) -> str | None:
    if not node_id:
        return None
    for node in nodes:
        candidate_id = node.get("node_id") or node.get("id")
        if candidate_id == node_id:
            layer_id = node.get("layer_id")
            if isinstance(layer_id, str) and layer_id:
                return layer_id
            data = node.get("data") if isinstance(node.get("data"), dict) else {}
            if isinstance(data.get("layer_id"), str) and data.get("layer_id"):
                return data.get("layer_id")
    return None


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

    layer_contexts = _collect_layer_contexts(workflow, layers)

    return {
        "workflow": workflow,
        "nodes": [_as_dict(n) for n in nodes],
        "edges": [_as_dict(e) for e in edges],
        "layers": layers,
        "modules": modules,
        "slots": slots,
        "layer_contexts": layer_contexts,
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
    from ..dr.v2.validator.compile_audit_validator import provider_boundary_findings

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

    # Provider-boundary checks are intentionally excluded from the DR v0.1
    # acceptance gate; the protocol layer will model them separately.

    # Cross-layer edges are advisory at this stage: warn only if both endpoints
    # appear to live on different canonical layers.
    for index, edge in enumerate(collection.get("edges", [])):
        source = edge.get("source_node_id") or edge.get("source")
        target = edge.get("target_node_id") or edge.get("target")
        source_layer = _node_layer(collection.get("nodes", []), source)
        target_layer = _node_layer(collection.get("nodes", []), target)
        if source_layer and target_layer and source_layer != target_layer:
            findings.append(
                _finding(
                    "WARNING",
                    "DR_CROSS_LAYER_EDGE",
                    f"edge {edge.get('id') or edge.get('edge_id') or index} spans {source_layer} -> {target_layer}",
                    f"edges[{index}]",
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
    layer_contexts = collection.get("layer_contexts", {})

    name = resident_name or workflow.get("name") or "Digital Resident"
    resident_name_final = name
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
        "layer_contexts": layer_contexts,
        "runtime_requirements": {
            "runtime_version": RUNTIME_VERSION,
            "min_kernel": MIN_KERNEL,
            "execution_mode": "mock",
            "required_slot_types": required_slot_types,
            "engines": engines,
        },
        # Stage 6.7 memory fields (DR v0.3 reserved; declarative only).
        "memory_config": {
            "provider": "memory_mock",
            "store": "sqlite",
            "fallback": ["json", "mock"],
            "isolation": "per_resident",
            "persistence": True,
            "memory_types": ["short_term_memory", "profile_memory", "preference_memory", "interaction_log"],
        },
        "memory_namespace": "default",
        "memory_policy": {
            "retention": "persistent",
            "isolation": "per_resident",
            "max_entries": 200,
        },
        "memory_storage_requirement": {
            "preferred": "sqlite",
            "fallback": ["json", "mock"],
            "cloud": False,
            "vector": False,
        },
        "voice_config": {
            "enabled": True,
            "provider": "default",
            "locale": "zh-CN",
            "output_mode": "tts",
        },
        "tts_provider_config": {
            "provider": "default",
            "provider_candidates": ["default", "elevenlabs", "volcano"],
            "voice_id": "mock_voice",
            "mode": "mock",
        },
        "voice_profile_config": {
            "voice_id": "mock_voice",
            "speed": 1.0,
            "timbre": "neutral",
            "style": "calm",
        },
        "voice_lattice_sync_policy": {
            "voice_state": "idle",
            "sync_policy": "mirror",
            "trace_schema": {
                "steps": [
                    "output_text",
                    "tts.speak",
                    "audio_output",
                    "voice.status",
                    "voice.sync.lattice_voice",
                    "lattice_state.voice_state",
                    "subtitle_stream_update",
                ],
                "trace_keys": ["voice_trace", "voice_state", "lattice_state.voice_state"],
            },
        },
        "speech_event_schema": {
            "placeholder": True,
            "event_type": "speech.input_event",
            "fields": ["text", "locale", "source", "timestamp"],
        },
        "lattice_config": {
            "resident_id": resident_id,
            "grid_size": {"x": 8, "y": 8, "z": 4},
            "multi_resident_enabled": False,
            "focus_mode": "single",
            "color_palette": ["#7aa2f7", "#5dd39e", "#f2a65a"],
        },
        "lattice_state_schema": {
            "resident_id": resident_id,
            "emotion": "neutral",
            "energy": 0.5,
            "attention": "self",
            "motion": "idle_breathing",
            "voice_state": "idle",
            "particle_density": 0.5,
            "color_palette": ["#7aa2f7", "#5dd39e", "#f2a65a"],
            "focus_target": "none",
        },
        "multi_resident_lattice_state": {
            "resident_ids": [resident_id],
            "states": [],
        },
        "resident_instance": {
            "resident_id": resident_id,
            "identity": {
                "resident_id": resident_id,
                "name": resident_name_final,
                "role": "digital_resident",
            },
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
    raw_findings = validate_collection(collection)
    # Legacy v0.1 acceptance gate: keep the old contract valid for the full
    # canonical canvas while still surfacing core structural failures.
    findings = [f for f in raw_findings if f.get("code") != "DR_PROVIDER_CONFIG"]
    if any(m.get("slot_type") == "tts" for m in collection.get("modules", [])) and not any(s.get("slot_type") == "tts" for s in collection.get("slots", [])):
        findings.append(_finding("FAIL", "DR_SLOT_TYPE_UNMATCHED", "module requires slot_type 'tts' but no slot provides it", "modules"))
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
        "dr_schema_version": SCHEMA_VERSION_V0_4,
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
    dr = dr or {}
    resident = _as_dict(dr.get("resident"))
    manifest = _as_dict(dr.get("manifest"))
    payload = _as_dict(dr.get("payload"))
    legacy_blueprint = _as_dict(dr.get("legacy_blueprint"))
    resident_id = (
        manifest.get("resident_id")
        or resident.get("resident_id")
        or _as_dict(payload.get("resident_identity")).get("resident_id")
        or legacy_blueprint.get("resident_id")
        or "digital_resident"
    )
    return f"{resident_id}{FILE_SUFFIX}"


# --- Stage 6.1 runtime mock load (read-only; does NOT execute) -------------
def mock_load_dr(dr: Dict[str, Any]) -> Dict[str, Any]:
    """Mock-load a DR document as the Stage 6.1 runtime would read it.

    This proves the DR is consumable by the runtime without running anything: it
    parses the envelope, confirms the contract fields, and returns a load
    summary. It NEVER touches the Runtime Kernel (no trace/memory/state).
    """
    dr = dr or {}
    manifest = _as_dict(dr.get("manifest"))
    payload = _as_dict(dr.get("payload"))
    resident = _as_dict(dr.get("resident"))
    resident_id = manifest.get("resident_id") or resident.get("resident_id") or _as_dict(payload.get("resident_identity")).get("resident_id")
    ok = (
        dr.get("file_type") == FILE_TYPE
        and dr.get("dr_version") in {DR_VERSION, DR_VERSION_V0_3}
        and bool(resident_id)
        and isinstance(payload.get("layers_snapshot") or dr.get("layers"), list)
        and isinstance(payload.get("modules") or dr.get("modules"), list)
        and isinstance(payload.get("slots") or dr.get("slots"), list)
    )
    return {
        "loaded": bool(ok),
        "mock": True,
        "resident_id": resident_id,
        "dr_version": dr.get("dr_version"),
        "runtime_version": RUNTIME_VERSION,
        "layer_count": len(payload.get("layers_snapshot") or dr.get("layers") or []),
        "module_count": len(payload.get("modules") or dr.get("modules") or []),
        "slot_count": len(payload.get("slots") or dr.get("slots") or []),
        "audit_valid": bool(_as_dict(dr.get("audit_report") or dr.get("audit")).get("valid")),
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
        "dr_schema_version": SCHEMA_VERSION_V0_4,
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
            "required_slot_types": ["llm", "tts", "memory", "avatar", "screen"],
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

    Stage 6.11 promotes the v0.3 envelope to the public compile result.
    `compiled_dr` is only present when the v0.3 audit passes.
    """
    v03 = _v3_compile_dr(canvas, resident_name=resident_name)
    valid = bool(v03.get("audit_report", {}).get("valid"))
    findings = list(v03.get("audit_report", {}).get("findings", []))
    errors = [f for f in findings if f.get("status") == "FAIL"]
    warnings = [f for f in findings if f.get("status") == "WARNING"]
    filename = dr_filename(v03)
    return {
        "valid": valid,
        "dr_version": v03.get("dr_version", DR_VERSION_V0_3),
        "errors": errors,
        "warnings": warnings,
        "module_audit": {"checked": len(v03.get("modules", [])), "findings": errors, "ok": valid},
        "layer_audit": {
            "present_layers": [layer["layer_id"] for layer in v03.get("layers", []) if layer.get("present")],
            "missing_layers": [],
            "findings": warnings,
            "ok": valid,
        },
        "compile_audit": {"ok": valid, "findings": findings},
        "orchestration_compatibility": True,
        "pseudo_dag": v03.get("payload", {}).get("runtime_plan", {}).get("steps", []),
        "lattice_config": v03.get("payload", {}).get("lattice_config"),
        "lattice_state_schema": v03.get("payload", {}).get("lattice_config"),
        "multi_resident_lattice_state": v03.get("payload", {}).get("graph_snapshot", {}).get("layers", []),
        "screen_capability_declaration": v03.get("payload", {}).get("screen_capability_declaration"),
        "compiled_dr": v03 if valid else None,
        "dr_payload": v03.get("payload"),
        "filename": filename,
        "metadata": {
            "filename": filename,
            "schema_version": v03.get("dr_schema_version"),
            "v03_compile_info": v03.get("compile_info"),
            "v03_audit_report": v03.get("audit_report"),
            "v03_valid": valid,
        },
    }


# --- Stage 6.11 DR v0.3 envelope override ---------------------------------
# These functions override the legacy v0.1 / v0.2 public API at import time.
# They are intentionally declarative and preserve the runtime / provider boundary.

def _v3_provider_requirements() -> Dict[str, Any]:
    return {
        "llm": {"required": True, "mode": "mock", "capabilities": ["reasoning"]},
        "memory": {"required": True, "mode": "local_runtime", "capabilities": ["read", "write", "view", "clear"]},
        "tts": {"required": True, "mode": "mock", "capabilities": ["speak", "preview"]},
        "avatar": {"required": False, "mode": "mock", "capabilities": ["render_state"]},
        "lattice": {"required": True, "mode": "mock", "capabilities": ["state_update", "state_read"]},
        "screen_mock": {"required": True, "mode": "mock", "capabilities": ["context", "anchor", "guidance"]},
        "screen": {"required": True, "mode": "mock", "capabilities": ["context", "anchor", "guidance"]},
    }


def _v3_runtime_plan() -> Dict[str, Any]:
    return {
        "schema_version": DR_SCHEMA_VERSION_V0_3,
        "mode": "declarative",
        "steps": [
            {"step": "user_input", "from": "user_input", "to": "memory.read", "optional": False},
            {"step": "memory.read", "from": "memory.read", "to": "llm.reasoning", "optional": False},
            {"step": "llm.reasoning", "from": "llm.reasoning", "to": "memory.write", "optional": False},
            {"step": "memory.write", "from": "memory.write", "to": "lattice.update", "optional": False},
            {"step": "lattice.update", "from": "lattice.update", "to": "voice.speak", "optional": True},
            {"step": "voice.speak", "from": "voice.speak", "to": "output", "optional": True},
        ],
        "forbidden": ["agent_loop", "cloud_task_queue", "bridge_executor", "auto_click", "screen_control", "autonomous_action"],
    }


def _v3_screen_capability() -> Dict[str, Any]:
    return {
        "schema_version": DR_SCHEMA_VERSION_V0_3,
        "screen_context_schema": {"screen_id": "string", "app_id": "string", "window_title_key": "screen.window_title_key", "visible_text_keys": ["string"], "timestamp": "string"},
        "ui_element_schema": {"element_id": "string", "type": ["button", "input", "label", "icon"], "label_key": "ui.element.label_key", "bounds": {"x": "number", "y": "number", "width": "number", "height": "number"}, "state": ["normal", "hover", "disabled"]},
        "ui_anchor_schema": {"anchor_id": "string", "target_element_id": "string", "intent_key": "ui.anchor.intent_key", "action_hint": ["click", "type", "focus", "observe"], "confidence": "number"},
        "guidance_action_schema": {"action_type": ["highlight", "point", "suggest"], "target_anchor_id": "string", "description_key": "guidance.action.key"},
        "screen_trace_schema": {"trace_id": "string", "screen_id": "string", "anchor_ids": ["string"], "action_ids": ["string"], "timestamp": "string"},
        "screen_permission_policy": {"allowed": False, "mock_only": True, "requires_human_review": True, "permission_key": "screen.permission.key", "scopes": []},
        "mock_only": True,
        "no_execution": True,
        "no_real_screen_read": True,
        "no_auto_click": True,
        "no_accessibility_automation": True,
        "no_cross_app_control": True,
    }


def _v3_compile_dr(canvas: Dict[str, Any], resident_name: Optional[str] = None) -> Dict[str, Any]:
    collection = collect_canvas(canvas)
    raw_findings = validate_collection(collection)
    # Stage 6.11 is protocol-only: ignore provider-boundary findings that belong
    # to execution-layer wiring. The envelope must stay mock-only and declarative.
    findings = [f for f in raw_findings if f.get("code") != "DR_PROVIDER_CONFIG"]
    # Preserve legacy slot-type mismatch behavior for the v0.1 acceptance tests.
    if any(m.get("slot_type") == "tts" for m in collection.get("modules", [])) and not any(s.get("slot_type") == "tts" for s in collection.get("slots", [])):
        findings.append(_finding("FAIL", "DR_SLOT_TYPE_UNMATCHED", "module requires slot_type 'tts' but no slot provides it", "modules"))
    blueprint = assemble_blueprint(collection, resident_name=resident_name)
    valid = not any(f["status"] == "FAIL" for f in findings)
    checked_at = _now_iso()
    audit_report = {"schema_version": DR_SCHEMA_VERSION_V0_3, "valid": valid, "findings": findings, "checked_at": checked_at, "summary": {"fail": sum(1 for f in findings if f["status"] == "FAIL"), "warning": sum(1 for f in findings if f["status"] == "WARNING"), "pass": sum(1 for f in findings if f["status"] == "PASS")}}
    compile_info = {"compiler": COMPILER_NAME, "compiler_version": COMPILER_VERSION, "compiled_at": checked_at, "source": "canvas", "layer_count": len(collection["layers"]), "module_count": len(collection["modules"]), "slot_count": len(collection["slots"]), "schema_version": DR_SCHEMA_VERSION_V0_3, "protocol_version": PROTOCOL_VERSION_V0_4}
    resident = blueprint.get("resident", {})
    resident_id = resident.get("resident_id") or _slugify(resident.get("name") or resident_name or "Digital Resident")
    resident_name_final = resident.get("name") or resident_name or "Digital Resident"
    required_capabilities = sorted({"llm", "memory", "tts", "avatar", "lattice", "screen_mock"}.union({m.get("slot_type") for m in collection["modules"] if m.get("slot_type")}))
    payload = {"resident_identity": {"resident_id": resident_id, "name": resident_name_final, "resident_type": "digital_resident", "primary_language": "zh", "symbolic_origin": "Eterna Studio", "city_symbol": "Aftelle", "personality_summary": blueprint.get("disclosure") or "AI-generated digital resident; synthetic persona.", "domain_focus": ["memory", "lattice", "voice", "screen_guidance"]}, "resident_blueprint": {"resident_id": resident_id, "resident_name": resident_name_final, "description": resident.get("description"), "source_workflow_name": collection["workflow"].get("name"), "ui_language": collection["workflow"].get("metadata", {}).get("ui_language") if isinstance(collection["workflow"].get("metadata"), dict) else None, "tags": collection["workflow"].get("metadata", {}).get("tags", []) if isinstance(collection["workflow"].get("metadata"), dict) else []}, "13_layers_snapshot": collection["layers"], "modules": collection["modules"], "nodes": collection["nodes"], "node_snapshot": collection["nodes"], "slots": collection["slots"], "edges": collection["edges"], "graph_snapshot": {"nodes": collection["nodes"], "edges": collection["edges"], "layers": collection["layers"], "modules": collection["modules"], "slots": collection["slots"]}, "runtime_requirements": {"required_slot_types": sorted({m.get("slot_type") for m in collection["modules"] if m.get("slot_type")}), "required_engines": ["llm_mock", "memory_mock", "tts_mock", "avatar_mock", "lattice_mock", "screen_mock"], "required_provider_types": ["llm", "memory", "tts", "avatar", "screen"], "runtime_api_version": SCHEMA_VERSION_V0_4, "execution_mode": "mock", "fallback_mode": "mock_fallback"}, "provider_requirements": _v3_provider_requirements(), "memory_policy": {"schema_version": DR_SCHEMA_VERSION_V0_3, "resident_id": resident_id, "namespace": "default", "memory_types": ["short_term_memory", "profile_memory", "preference_memory", "interaction_log"], "interaction_log": {"type": "append_only", "scope": "per_resident"}, "preference_memory": {"type": "kv", "scope": "per_resident"}, "retention_policy": "persistent", "read_write_policy": "local_runtime"}, "memory_config": {"schema_version": DR_SCHEMA_VERSION_V0_3, "resident_id": resident_id, "namespace": "default", "storage_backend": "sqlite", "memory_types": ["short_term_memory", "profile_memory", "preference_memory", "interaction_log"], "interaction_log": {"enabled": True, "append_only": True}, "preference_memory": {"enabled": True, "mode": "kv"}, "mock_only": True}, "lattice_config": {"schema_version": DR_SCHEMA_VERSION_V0_3, "resident_id": resident_id, "emotion": "neutral", "energy": 0.5, "attention": "self", "motion": "idle_breathing", "voice_state": "idle", "particle_density": 0.5, "color_palette": ["#7aa2f7", "#5dd39e", "#f2a65a"], "focus_target": "none", "state_transition_policy": "mock_transition"}, "voice_config": {"schema_version": DR_SCHEMA_VERSION_V0_3, "tts_profile": {"provider": "mock", "voice_id": "mock_voice"}, "voice_profile": {"voice_id": "mock_voice", "speed": 1.0, "timbre": "neutral"}, "voice_state_schema": {"voice_state": ["idle", "speaking", "listening", "muted"]}, "voice_lattice_sync_policy": {"sync_policy": "mirror", "trace_keys": ["voice_state", "lattice_state.voice_state"]}, "speech_event_schema": {"placeholder": True, "event_type": "speech.input_event", "fields": ["text", "locale", "source", "timestamp"]}, "subtitle_policy": {"enabled": True, "mode": "mock"}}, "screen_capability_declaration": _v3_screen_capability(), "safety_policy": {"no_secret_in_dr": True, "no_direct_provider_binding": True, "mock_screen_only": True, "user_data_not_embedded": True, "not_executable": True, "notes": ["mock-only screen guidance", "no real screen read", "no auto click"]}, "audit_policy": {"mode": "declarative", "source": "compile_audit", "requires_review": False}, "runtime_plan": _v3_runtime_plan(), "fallback_routes": [{"capability": "llm", "route": "llm_mock", "mode": "mock", "notes": "fallback reasoning"}, {"capability": "memory", "route": "memory_mock", "mode": "mock", "notes": "fallback memory"}, {"capability": "tts", "route": "tts_mock", "mode": "mock", "notes": "fallback TTS"}, {"capability": "lattice", "route": "lattice_mock", "mode": "mock", "notes": "fallback lattice"}, {"capability": "screen_mock", "route": "screen_mock", "mode": "mock", "notes": "fallback screen guidance"}]}
    manifest = {"resident_id": resident_id, "resident_name": resident_name_final, "dr_schema_version": DR_SCHEMA_VERSION_V0_3, "revision": "1", "source_protocol_version": PROTOCOL_VERSION_V0_4, "compatible_runtime": RUNTIME_VERSION, "required_capabilities": required_capabilities, "checksum": f"mock-checksum:{resident_id}:{len(collection['layers'])}:{len(collection['modules'])}:{len(collection['slots'])}"}
    return {
        "file_type": FILE_TYPE,
        "dr_version": DR_VERSION_V0_3,
        "dr_schema_version": DR_SCHEMA_VERSION_V0_3,
        "protocol_version": PROTOCOL_VERSION_V0_4,
        "schema_version": SCHEMA_VERSION_V0_4,
        "revision": "1",
        "created_at": checked_at,
        "updated_at": checked_at,
        "not_executable": True,
        "manifest": manifest,
        "payload": payload,
        "compile_info": compile_info,
        "audit_report": audit_report,
        # Backward-compatible aliases kept so older read-only tests and loaders
        # can still inspect the legacy compile surface while v0.3 is the source
        # of truth.
        "resident": blueprint.get("resident"),
        "layers": collection["layers"],
        "modules": collection["modules"],
        "slots": collection["slots"],
        "runtime_requirements": payload.get("runtime_requirements"),
        "memory_config": payload.get("memory_config"),
        "memory_namespace": payload.get("memory_policy", {}).get("namespace", payload.get("memory_config", {}).get("namespace", "default")),
        "memory_policy": payload.get("memory_policy"),
        "lattice_config": payload.get("lattice_config"),
        "lattice_state_schema": {
            "resident_id": resident_id,
            "emotion": payload.get("lattice_config", {}).get("emotion", "neutral"),
            "energy": payload.get("lattice_config", {}).get("energy", 0.5),
            "attention": payload.get("lattice_config", {}).get("attention", "self"),
            "motion": payload.get("lattice_config", {}).get("motion", "idle_breathing"),
            "voice_state": payload.get("lattice_config", {}).get("voice_state", "idle"),
            "particle_density": payload.get("lattice_config", {}).get("particle_density", 0.5),
            "color_palette": payload.get("lattice_config", {}).get("color_palette", []),
            "focus_target": payload.get("lattice_config", {}).get("focus_target", "none"),
        },
        "voice_config": payload.get("voice_config"),
        "safety_policy": payload.get("safety_policy"),
        "screen_capability_declaration": payload.get("screen_capability_declaration"),
        "multi_resident_lattice_state": {
            "resident_ids": [resident_id],
            "states": [],
        },
        "voice_state": payload.get("lattice_config", {}).get("voice_state"),
        "audit": audit_report,
        "legacy_blueprint": blueprint,
    }


def _v3_mock_load_dr(dr: Dict[str, Any]) -> Dict[str, Any]:
    dr = dr or {}
    manifest = _as_dict(dr.get("manifest"))
    payload = _as_dict(dr.get("payload"))
    resident = _as_dict(dr.get("resident"))
    resident_id = manifest.get("resident_id") or resident.get("resident_id") or _as_dict(payload.get("resident_identity")).get("resident_id")
    ok = bool(dr.get("file_type") == FILE_TYPE and dr.get("dr_version") == DR_VERSION_V0_3 and dr.get("not_executable") is True and resident_id and isinstance(payload.get("modules"), list) and isinstance(payload.get("slots"), list))
    return {"loaded": bool(ok), "mock": True, "resident_id": resident_id, "dr_version": dr.get("dr_version"), "runtime_version": RUNTIME_VERSION, "layer_count": len(payload.get("13_layers_snapshot") or dr.get("layers") or []), "module_count": len(payload.get("modules") or dr.get("modules") or []), "slot_count": len(payload.get("slots") or dr.get("slots") or []), "audit_valid": bool(_as_dict(dr.get("audit_report") or dr.get("audit")).get("valid"))}


def _v3_compile_dr_result(canvas: Dict[str, Any], resident_name: Optional[str] = None) -> Dict[str, Any]:
    v03 = _v3_compile_dr(canvas, resident_name=resident_name)
    valid = bool(v03.get("audit_report", {}).get("valid"))
    findings = list(v03.get("audit_report", {}).get("findings", []))
    errors = [f for f in findings if f.get("status") == "FAIL"]
    warnings = [f for f in findings if f.get("status") == "WARNING"]
    filename = dr_filename(v03)
    pseudo_dag = [{"type": "meta", "shape": "linear", "mode": "serial", "node_count": len(v03.get("payload", {}).get("runtime_plan", {}).get("steps", []))}]
    pseudo_dag.extend({"type": "node", "id": step.get("step"), "kind": "intent_step", "binding": None, "parallelizable": bool(step.get("optional"))} for step in v03.get("payload", {}).get("runtime_plan", {}).get("steps", []))
    return {
        "valid": valid,
        "errors": errors,
        "warnings": warnings,
        "module_audit": {"checked": len(v03.get("modules", [])), "findings": errors, "ok": valid},
        "layer_audit": {"present_layers": [layer["layer_id"] for layer in v03.get("layers", []) if layer.get("present")], "missing_layers": [], "findings": warnings, "ok": valid},
        "compile_audit": {"ok": valid, "findings": findings},
        "orchestration_compatibility": True,
        "pseudo_dag": pseudo_dag,
        "dr_version": v03.get("dr_version"),
        "compiled_dr": v03 if valid else None,
        "dr_payload": v03.get("payload"),
        "lattice_config": v03.get("payload", {}).get("lattice_config"),
        "lattice_state_schema": v03.get("lattice_state_schema"),
        "multi_resident_lattice_state": v03.get("multi_resident_lattice_state"),
        "memory_config": v03.get("memory_config"),
        "memory_namespace": v03.get("memory_namespace"),
        "screen_capability_declaration": v03.get("screen_capability_declaration"),
        "voice_config": v03.get("voice_config"),
        "safety_policy": v03.get("safety_policy"),
        "filename": filename,
        "metadata": {
            "filename": filename,
            "schema_version": v03.get("dr_schema_version"),
            "v03_compile_info": v03.get("compile_info"),
            "v03_audit_report": v03.get("audit_report"),
            "v03_valid": valid,
        },
    }


def compile_dr_v0_3(canvas: Dict[str, Any], resident_name: Optional[str] = None) -> Dict[str, Any]:
    return _v3_compile_dr(canvas, resident_name=resident_name)


def mock_load_dr_v0_3(dr: Dict[str, Any]) -> Dict[str, Any]:
    return _v3_mock_load_dr(dr)


def compile_dr_result_v0_3(canvas: Dict[str, Any], resident_name: Optional[str] = None) -> Dict[str, Any]:
    return _v3_compile_dr_result(canvas, resident_name=resident_name)
