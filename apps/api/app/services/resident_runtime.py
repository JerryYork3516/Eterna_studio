"""Resident Runtime — Stage 6 minimal "running digital resident" (v1, mock).

Execution boundary (do not violate):
  * Node / Module / Slot are protocol descriptors only — they never execute.
  * The Execution Engine (execution_engine.py) is the only runtime entry; this
    loop is reached only through it.
  * Providers are mock-only and reached via provider_adapters.route_provider.

Holds in-process resident state and runs one fixed loop per step:
  input -> memory.read -> reasoning -> action -> memory.write -> output

Stage 6.1 adds observability around this loop without changing it: a
TraceCollector records one structured step per phase, a RuntimeStateManager
tracks run_id / turn_count / status (running -> completed), and the
memory_snapshotter emits a memory snapshot at the end of each run.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from ..models.v0_4 import LatticeEmotion, LatticeMotion, LatticeStateV04, LatticeVoiceState

from ..dr.v2.validator import validate_dr_v0_2

from .memory_snapshotter import take_snapshot
from .provider_adapters import route_provider_for_engine
from .runtime_llm_config import get_runtime_llm_profile
from .runtime_state_manager import RuntimeStateManager, reset_history
from .runtime_trace_collector import TraceCollector


@dataclass
class ResidentRuntimeState:
    """Minimal running state of a digital resident (process-local, mock)."""

    resident_id: str
    memory: List[Dict[str, Any]] = field(default_factory=list)
    status: str = "idle"
    last_input: str = ""
    last_reasoning: str = ""
    last_action: Dict[str, Any] = field(default_factory=dict)
    last_output: str = ""
    turn_count: int = 0
    dr_version: str = ""
    identity: Dict[str, Any] = field(default_factory=dict)
    capability_profile: Dict[str, Any] = field(default_factory=dict)
    memory_policy: Dict[str, Any] = field(default_factory=dict)
    runtime_status: str = "idle"
    provider_bindings: Dict[str, str] = field(
        default_factory=lambda: {
            "llm": "llm_mock:provider_llm_mock",
            "memory": "memory_mock:provider_memory_mock",
            "tool": "tool_mock:provider_tool_mock",
        }
    )


_STATES: Dict[str, ResidentRuntimeState] = {}

_state_manager = RuntimeStateManager()


def get_or_create_state(resident_id: str) -> ResidentRuntimeState:
    state = _STATES.get(resident_id)
    if state is None:
        state = ResidentRuntimeState(resident_id=resident_id)
        _STATES[resident_id] = state
    return state


def create_runtime_state_from_dr(dr: Dict[str, Any]) -> ResidentRuntimeState:
    """Create or refresh the process-local runtime state from a valid DR v0.2.

    This only binds the existing deterministic mock providers. It does not create
    real provider clients, schedulers, secure loaders, or orchestration runners.
    """
    identity = dict(dr.get("identity") or {})
    resident_id = identity.get("resident_id") or "resident_v1"
    state = get_or_create_state(resident_id)
    state.dr_version = str(dr.get("dr_version") or "")
    state.identity = identity
    state.capability_profile = dict(dr.get("capability_profile") or {})
    state.memory_policy = dict(dr.get("memory_policy") or {})
    state.status = "idle"
    state.runtime_status = "idle"
    state.provider_bindings = {
        "llm": "llm_mock:provider_llm_mock",
        "memory": "memory_mock:provider_memory_mock",
        "tool": "tool_mock:provider_tool_mock",
    }
    return state


def _empty_memory_snapshot(resident_id: Optional[str]) -> Dict[str, Any]:
    return {"resident_id": resident_id, "entries": [], "count": 0}


def _empty_validation_result(
    *,
    dr_version: Optional[str] = None,
    errors: Optional[List[Dict[str, Any]]] = None,
    warnings: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    return {
        "valid": False,
        "dr_version": dr_version,
        "errors": errors or [],
        "warnings": warnings or [],
        "module_audit": {},
        "layer_audit": {},
        "compile_audit": {},
        "orchestration_compatibility": False,
        "pseudo_dag": [],
    }


def _rejected_load(
    *, resident_id: Optional[str],
    dr_version: Optional[str],
    errors: Optional[List[Dict[str, Any]]] = None,
    warnings: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    rid = resident_id or "resident_v1"
    validation_result = _empty_validation_result(dr_version=dr_version, errors=errors, warnings=warnings)
    return {
        "loaded": False,
        "resident_id": rid,
        "dr_version": dr_version,
        "status": "rejected",
        "validation_result": validation_result,
        "runtime_state": None,
        "output_text": "",
        "memory_snapshot": _empty_memory_snapshot(rid),
        "execution_trace": [],
        "trace": [],
        "turn_count": 0,
        "run_history": [],
        "mock": True,
    }


def reset_states() -> None:
    _STATES.clear()
    reset_history()


def _profile_trace_info(profile_id: str, provider: str, model: str, mock: bool, fallback_mock: bool) -> Dict[str, Any]:
    return {
        "profile_id": profile_id,
        "provider": provider,
        "model": model,
        "mock": mock,
        "fallback_mock": fallback_mock,
    }


def _stage_from_input(input_text: str) -> str:
    lowered = (input_text or "").lower()
    if "think" in lowered or "思考" in input_text:
        return "thinking"
    if "speak" in lowered or "说" in input_text or "talk" in lowered:
        return "speaking"
    if "focus" in lowered or "专注" in input_text:
        return "focused"
    return "calm"


def _build_lattice_state(
    *,
    resident_id: str,
    stage: str,
    input_text: str,
    output_text: str = "",
) -> Dict[str, Any]:
    emotion = {
        "thinking": LatticeEmotion.thinking.value,
        "speaking": LatticeEmotion.speaking.value,
        "focused": LatticeEmotion.focused.value,
        "calm": LatticeEmotion.calm.value,
    }.get(stage, LatticeEmotion.neutral.value)
    motion = {
        "thinking": LatticeMotion.thinking_pulse.value,
        "speaking": LatticeMotion.speaking_motion.value,
        "focused": LatticeMotion.focused_stillness.value,
        "calm": LatticeMotion.idle_breathing.value,
    }.get(stage, LatticeMotion.idle_breathing.value)
    voice_state = LatticeVoiceState.speaking.value if stage == "speaking" else LatticeVoiceState.idle.value
    attention = "user" if stage == "focused" else "self"
    focus_target = "user" if stage == "focused" else "self"
    particle_density = {"thinking": 0.72, "speaking": 0.64, "focused": 0.58, "calm": 0.42}.get(stage, 0.5)
    energy = {"thinking": 0.66, "speaking": 0.62, "focused": 0.74, "calm": 0.48}.get(stage, 0.5)
    color_palette = ["#7aa2f7", "#5dd39e", "#f2a65a"] if stage != "speaking" else ["#f87171", "#f2a65a", "#facc15"]
    state = LatticeStateV04(
        resident_id=resident_id,
        emotion=emotion,
        energy=energy,
        attention=attention,
        motion=motion,
        voice_state=voice_state,
        particle_density=particle_density,
        color_palette=color_palette,
        focus_target=focus_target,
        stage=stage,
    )
    payload = state.model_dump(mode="json")
    payload["resident_id"] = resident_id
    payload["multi_resident_lattice_state"] = {
        "resident_ids": [resident_id],
        "lattice_states": [],
        "coordination_mode": "reserved",
        "metadata": {"enabled": False},
    }
    payload["stage"] = stage
    payload["output_preview"] = output_text[:80]
    payload["input_preview"] = input_text[:80]
    return payload


def run_resident_loop(workflow: Any, input_text: str, resident_id: str = "resident_v1") -> Dict[str, Any]:
    """Run one resident step through the fixed mock runtime loop.

    The only entry the API uses for the resident runtime loop. Returns a plain
    dict envelope.
    """
    state = get_or_create_state(resident_id)

    run = _state_manager.start_run(resident_id, turn_count=state.turn_count + 1)
    collector = TraceCollector(run_id=run.run_id, resident_id=resident_id)
    state.status = run.status
    state.runtime_status = run.status

    state.last_input = input_text
    stage = _stage_from_input(input_text)
    collector.record(
        "input",
        data={"input_text": input_text, "stage": stage},
        input=input_text,
        output={"input_text": input_text, "stage": stage},
    )

    memory_namespace = "default"
    memory_type = "interaction_log"
    read = route_provider_for_engine(
        "memory_mock",
        {"op": "read", "resident_id": resident_id, "namespace": memory_namespace, "memory_type": memory_type},
    )
    read_entries = list(read.get("entries", []))
    collector.record(
        "memory.read",
        data={
            "count": read.get("count", 0),
            "provider_type": read.get("provider_type"),
            "provider_id": read.get("provider_id"),
            "engine_id": read.get("engine_id"),
            "namespace": read.get("namespace"),
            "memory_type": read.get("memory_type"),
            "storage_backend": read.get("storage_backend"),
            "mock": True,
        },
        input={"op": "read", "resident_id": resident_id, "namespace": memory_namespace, "memory_type": memory_type},
        output={"count": read.get("count", 0), "entries": read_entries},
    )

    memory_lines: List[str] = []
    for item in read_entries:
        if isinstance(item, dict):
            past_input = item.get("input")
            past_reply = item.get("reply") or item.get("output")
            if past_input:
                memory_lines.append(f"用户: {past_input}")
            if past_reply:
                memory_lines.append(f"居民: {past_reply}")
    memory_context = "\n".join(memory_lines) if memory_lines else "（无历史记忆）"
    prompt = f"已知历史记忆：\n{memory_context}\n\n当前用户输入：{input_text}"

    profile = get_runtime_llm_profile()
    _llm_cfg = profile
    fallback_mock = False
    reasoning_error: Optional[str] = None
    if _llm_cfg.is_valid():
        reasoning = route_provider_for_engine("llm_primary", {"prompt": prompt, "llm_profile_id": _llm_cfg.profile_id})
        if reasoning.get("status") == "error":
            reasoning_error = reasoning.get("error")
            if _llm_cfg.fallback_to_mock:
                reasoning = route_provider_for_engine("llm_mock", {"prompt": prompt})
                fallback_mock = True
    else:
        reasoning = route_provider_for_engine("llm_mock", {"prompt": prompt})

    reasoning_text = reasoning.get("text", "")
    state.last_reasoning = reasoning_text
    trace_profile = _profile_trace_info(
        profile_id=_llm_cfg.profile_id,
        provider=reasoning.get("provider") or _llm_cfg.provider,
        model=reasoning.get("model") or _llm_cfg.model,
        mock=bool(reasoning.get("mock", True)),
        fallback_mock=fallback_mock,
    )
    trace_profile["engine_id"] = reasoning.get("engine_id")
    if reasoning_error is not None:
        trace_profile["error"] = reasoning_error
    trace_profile["text"] = reasoning_text
    collector.record(
        "reasoning",
        data=trace_profile,
        input={"prompt": prompt},
        output=trace_profile,
    )

    action = route_provider_for_engine("tool_mock", {"tool": "echo", "args": {"text": input_text}})
    state.last_action = action
    echo_result = action.get("result", "")
    collector.record(
        "action",
        data={
            "tool": action.get("tool"),
            "result": echo_result,
            "provider_type": action.get("provider_type"),
            "provider_id": action.get("provider_id"),
            "engine_id": action.get("engine_id"),
            "mock": True,
        },
        input={"tool": "echo", "args": {"text": input_text}},
        output=action,
    )

    output_text = f"[{resident_id}] {reasoning_text} | echo: {echo_result}"
    state.last_output = output_text
    state.turn_count += 1

    entry = {"turn": state.turn_count, "input": input_text, "output": output_text, "reply": reasoning_text}
    write = route_provider_for_engine(
        "memory_mock",
        {"op": "write", "resident_id": resident_id, "namespace": memory_namespace, "memory_type": memory_type, "entry": entry},
    )
    collector.record(
        "memory.write",
        data={
            "count": write.get("count", 0),
            "provider_type": write.get("provider_type"),
            "provider_id": write.get("provider_id"),
            "engine_id": write.get("engine_id"),
            "namespace": write.get("namespace"),
            "memory_type": write.get("memory_type"),
            "storage_backend": write.get("storage_backend"),
            "mock": True,
        },
        input={"op": "write", "resident_id": resident_id, "namespace": memory_namespace, "memory_type": memory_type, "entry": entry},
        output={"count": write.get("count", 0)},
    )

    snapshot = take_snapshot(resident_id, run_id=run.run_id)
    state.memory = list(snapshot.get("entries", []))

    collector.record(
        "output",
        data={"output_text": output_text},
        input={"reasoning": reasoning_text, "action": echo_result},
        output={"output_text": output_text},
    )
    _state_manager.complete_run(run, turn_count=state.turn_count)
    state.status = run.status
    state.runtime_status = run.status

    trace = collector.steps()
    lattice_state = _build_lattice_state(
        resident_id=resident_id,
        stage=stage,
        input_text=input_text,
        output_text=output_text,
    )
    return {
        "resident_id": resident_id,
        "run_id": run.run_id,
        "status": state.status,
        "output_text": output_text,
        "memory_snapshot": snapshot,
        "execution_trace": trace,
        "trace": trace,
        "turn_count": state.turn_count,
        "run_history": _state_manager.history(resident_id),
        "lattice_state": lattice_state,
        "mock": True,
    }


def load_digital_resident(file_or_dict: Any, input_text: str = "load digital resident") -> Dict[str, Any]:
    """Load a validated DR v0.2 through the Stage 6 runtime boundary."""
    if not isinstance(file_or_dict, dict):
        return _rejected_load(resident_id=None, dr_version=None, errors=[{"code": "INVALID_INPUT", "message": "DR payload must be an object", "path": "dr"}])

    validation = validate_dr_v0_2(file_or_dict)
    resident_id = (file_or_dict.get("resident_instance") or {}).get("resident_id") if isinstance(file_or_dict.get("resident_instance"), dict) else None
    if not validation.get("valid"):
        errors = list(validation.get("errors", []))
        warnings = list(validation.get("warnings", []))
        return _rejected_load(
            resident_id=resident_id,
            dr_version=validation.get("dr_version"),
            errors=errors,
            warnings=warnings,
        )

    resident_id = resident_id or "resident_v1"
    create_runtime_state_from_dr(file_or_dict)
    step = run_resident_loop(file_or_dict, input_text=input_text, resident_id=resident_id)
    step.update(
        {
            "loaded": True,
            "dr_version": validation.get("dr_version"),
            "validation_result": validation,
            "runtime_state": {
                "resident_id": resident_id,
                "identity": get_or_create_state(resident_id).identity,
                "capability_profile": get_or_create_state(resident_id).capability_profile,
                "memory_policy": get_or_create_state(resident_id).memory_policy,
                "provider_bindings": get_or_create_state(resident_id).provider_bindings,
                "status": get_or_create_state(resident_id).status,
            },
        }
    )
    return step


def load_digital_resident_from_bytes(raw: bytes, input_text: Optional[str] = None) -> Dict[str, Any]:
    try:
        parsed = json.loads(raw.decode("utf-8"))
    except Exception:
        return _rejected_load(
            resident_id=None,
            dr_version=None,
            errors=[{"code": "INVALID_JSON", "message": "DR payload is not valid JSON", "path": "dr"}],
        )
    return load_digital_resident(parsed, input_text=input_text or "load digital resident")
