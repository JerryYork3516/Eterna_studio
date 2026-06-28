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

from ..dr.v2.validator import validate_dr_v0_2

from .memory_snapshotter import take_snapshot
from .provider_adapters import route_provider_for_engine
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
    *,
    resident_id: Optional[str],
    dr_version: Optional[str],
    validation_result: Dict[str, Any],
) -> Dict[str, Any]:
    return {
        "loaded": False,
        "mock": True,
        "resident_id": resident_id,
        "dr_version": dr_version,
        "validation_result": validation_result,
        "status": "rejected",
        "memory_snapshot": _empty_memory_snapshot(resident_id),
        "execution_trace": [],
        "trace": [],
        "output_text": "",
        "turn_count": 0,
    }


def _normalize_dr_payload(file_or_dict: Any) -> Dict[str, Any]:
    if isinstance(file_or_dict, dict) and isinstance(file_or_dict.get("dr"), dict):
        return dict(file_or_dict["dr"])
    if isinstance(file_or_dict, dict):
        return dict(file_or_dict)
    if isinstance(file_or_dict, (bytes, bytearray)):
        text = bytes(file_or_dict).decode("utf-8")
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return _normalize_dr_payload(parsed)
    if isinstance(file_or_dict, str):
        parsed = json.loads(file_or_dict)
        if isinstance(parsed, dict):
            return _normalize_dr_payload(parsed)
    if hasattr(file_or_dict, "read"):
        raw = file_or_dict.read()
        if isinstance(raw, str):
            raw = raw.encode("utf-8")
        return _normalize_dr_payload(raw)
    raise ValueError("DR payload must be a JSON object or bytes containing a JSON object")


def load_digital_resident(file_or_dict: Any, input_text: str = "load digital resident") -> Dict[str, Any]:
    """Load a .digital_resident v0.2 into the mock runtime and run one step."""
    try:
        dr = _normalize_dr_payload(file_or_dict)
    except (TypeError, ValueError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        validation_result = _empty_validation_result(
            errors=[
                {
                    "status": "FAIL",
                    "code": "DR_LOAD_PARSE_ERROR",
                    "message": str(exc),
                    "path": "(root)",
                }
            ]
        )
        return _rejected_load(resident_id=None, dr_version=None, validation_result=validation_result)

    identity = dr.get("identity") if isinstance(dr.get("identity"), dict) else {}
    resident_id = identity.get("resident_id")
    dr_version = dr.get("dr_version")
    validation_result = validate_dr_v0_2(dr)
    if not validation_result.get("valid"):
        return _rejected_load(
            resident_id=resident_id,
            dr_version=dr_version,
            validation_result=validation_result,
        )

    state = create_runtime_state_from_dr(dr)
    loop = run_resident_loop({"digital_resident": dr}, input_text, state.resident_id)
    return {
        "loaded": True,
        "dr_version": state.dr_version,
        "validation_result": validation_result,
        "runtime_state": {
            "resident_id": state.resident_id,
            "dr_version": state.dr_version,
            "identity": state.identity,
            "capability_profile": state.capability_profile,
            "memory_policy": state.memory_policy,
            "runtime_status": state.runtime_status,
            "turn_count": state.turn_count,
            "provider_bindings": state.provider_bindings,
        },
        **loop,
    }


def load_digital_resident_from_bytes(raw: bytes, input_text: Optional[str] = None) -> Dict[str, Any]:
    """Parse bytes from a .digital_resident JSON file or JSON API body."""
    selected_input = input_text or "load digital resident"
    try:
        parsed = json.loads(raw.decode("utf-8"))
        if isinstance(parsed, dict) and isinstance(parsed.get("input_text"), str) and input_text is None:
            selected_input = parsed["input_text"]
        return load_digital_resident(parsed, input_text=selected_input)
    except (TypeError, ValueError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        validation_result = _empty_validation_result(
            errors=[
                {
                    "status": "FAIL",
                    "code": "DR_LOAD_PARSE_ERROR",
                    "message": str(exc),
                    "path": "(root)",
                }
            ]
        )
        return _rejected_load(resident_id=None, dr_version=None, validation_result=validation_result)


def reset_states() -> None:
    """Test seam: clear all in-process resident states and run history."""
    _STATES.clear()
    reset_history()


def run_resident_loop(workflow: Any, input_text: str, resident_id: str) -> Dict[str, Any]:
    """Run one resident step. `workflow` is accepted for context only — this mock
    loop is provider-driven and does not execute the v0.3 workflow.

    Returns a plain dict (no Python object references).
    """
    state = get_or_create_state(resident_id)

    # Open the run lifecycle: status running, fresh run_id. turn_count is the
    # turn this run will produce (current count + 1).
    run = _state_manager.start_run(resident_id, turn_count=state.turn_count + 1)
    collector = TraceCollector(run_id=run.run_id, resident_id=resident_id)
    state.status = run.status  # "running"
    state.runtime_status = run.status  # "running"

    # 1. input
    state.last_input = input_text
    collector.record(
        "input",
        data={"input_text": input_text},
        input=input_text,
        output={"input_text": input_text},
    )

    # 2. memory.read
    read = route_provider_for_engine("memory_mock", {"op": "read", "resident_id": resident_id})
    collector.record(
        "memory.read",
        data={
            "count": read.get("count", 0),
            "provider_type": read.get("provider_type"),
            "provider_id": read.get("provider_id"),
            "engine_id": read.get("engine_id"),
            "mock": True,
        },
        input={"op": "read", "resident_id": resident_id},
        output={"count": read.get("count", 0), "entries": list(read.get("entries", []))},
    )

    # 3. reasoning (mock LLM only)
    memory_context = f"{read.get('count', 0)} prior memories"
    prompt = f"{input_text}\n[context: {memory_context}]"
    reasoning = route_provider_for_engine("llm_mock", {"prompt": prompt})
    reasoning_text = reasoning.get("text", "")
    state.last_reasoning = reasoning_text
    collector.record(
        "reasoning",
        data={
            "provider": reasoning.get("provider"),
            "provider_type": reasoning.get("provider_type"),
            "provider_id": reasoning.get("provider_id"),
            "engine_id": reasoning.get("engine_id"),
            "mock": True,
            "text": reasoning_text,
        },
        input={"prompt": prompt},
        output=reasoning,
    )

    # 4. action / tool routing (deterministic echo)
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

    # 5/6. compose output, update state
    output_text = f"[{resident_id}] {reasoning_text} | echo: {echo_result}"
    state.last_output = output_text
    state.turn_count += 1

    # memory.write (record this turn's input/output)
    entry = {"turn": state.turn_count, "input": input_text, "output": output_text}
    write = route_provider_for_engine("memory_mock", {"op": "write", "resident_id": resident_id, "entry": entry})
    collector.record(
        "memory.write",
        data={
            "count": write.get("count", 0),
            "provider_type": write.get("provider_type"),
            "provider_id": write.get("provider_id"),
            "engine_id": write.get("engine_id"),
            "mock": True,
        },
        input={"op": "write", "resident_id": resident_id, "entry": entry},
        output={"count": write.get("count", 0)},
    )

    # End-of-run memory snapshot (deep-copied, point-in-time).
    snapshot = take_snapshot(resident_id, run_id=run.run_id)
    state.memory = list(snapshot.get("entries", []))

    # 7. output — close the run lifecycle: status completed.
    collector.record(
        "output",
        data={"output_text": output_text},
        input={"reasoning": reasoning_text, "action": echo_result},
        output={"output_text": output_text},
    )
    _state_manager.complete_run(run, turn_count=state.turn_count)
    state.status = run.status  # "completed"
    state.runtime_status = run.status  # "completed"

    return {
        "resident_id": resident_id,
        "run_id": run.run_id,
        "status": state.status,
        "output_text": output_text,
        "memory_snapshot": snapshot,
        "execution_trace": collector.steps(),
        "trace": collector.steps(),
        "turn_count": state.turn_count,
        "run_history": _state_manager.history(resident_id),
        "mock": True,
    }
