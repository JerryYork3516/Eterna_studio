"""Resident Runtime — Stage 6 minimal "running digital resident" (v1, mock).

Execution boundary (do not violate):
  * Node / Module / Slot are protocol descriptors only — they never execute.
  * The Execution Engine (execution_engine.py) is the only runtime entry; this
    loop is reached only through it.
  * Providers are mock-only and reached via provider_adapters.route_provider.

Holds in-process resident state and runs one fixed loop per step:
  input -> memory.read -> reasoning -> action -> memory.write -> output
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

from .provider_adapters import route_provider


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


_STATES: Dict[str, ResidentRuntimeState] = {}


def get_or_create_state(resident_id: str) -> ResidentRuntimeState:
    state = _STATES.get(resident_id)
    if state is None:
        state = ResidentRuntimeState(resident_id=resident_id)
        _STATES[resident_id] = state
    return state


def reset_states() -> None:
    """Test seam: clear all in-process resident states."""
    _STATES.clear()


def run_resident_loop(workflow: Any, input_text: str, resident_id: str) -> Dict[str, Any]:
    """Run one resident step. `workflow` is accepted for context only — this mock
    loop is provider-driven and does not execute the v0.3 workflow.

    Returns a plain dict (no Python object references).
    """
    state = get_or_create_state(resident_id)
    trace: List[Dict[str, Any]] = []

    # 1. input
    state.status = "thinking"
    state.last_input = input_text
    trace.append({"step": "input", "input_text": input_text})

    # 2. memory.read
    read = route_provider("memory", {"op": "read", "resident_id": resident_id})
    trace.append({"step": "memory.read", "count": read.get("count", 0)})

    # 3. reasoning (mock LLM only)
    memory_context = f"{read.get('count', 0)} prior memories"
    reasoning = route_provider("llm", {"prompt": f"{input_text}\n[context: {memory_context}]"})
    reasoning_text = reasoning.get("text", "")
    state.last_reasoning = reasoning_text
    trace.append({"step": "reasoning", "provider": reasoning.get("provider"), "text": reasoning_text})

    # 4. action / tool routing (deterministic echo)
    action = route_provider("tool", {"tool": "echo", "args": {"text": input_text}})
    state.last_action = action
    echo_result = action.get("result", "")
    trace.append({"step": "action", "tool": action.get("tool"), "result": echo_result})

    # 5/6. compose output, update state
    output_text = f"[{resident_id}] {reasoning_text} | echo: {echo_result}"
    state.last_output = output_text
    state.turn_count += 1

    # memory.write (record this turn's input/output)
    entry = {"turn": state.turn_count, "input": input_text, "output": output_text}
    write = route_provider("memory", {"op": "write", "resident_id": resident_id, "entry": entry})
    trace.append({"step": "memory.write", "count": write.get("count", 0)})

    # snapshot memory back onto the state for inspection
    snapshot = route_provider("memory", {"op": "list", "resident_id": resident_id})
    state.memory = list(snapshot.get("entries", []))

    # 7. output
    state.status = "completed"
    trace.append({"step": "output", "output_text": output_text})

    return {
        "resident_id": resident_id,
        "status": state.status,
        "output_text": output_text,
        "memory_snapshot": {
            "resident_id": resident_id,
            "entries": list(state.memory),
            "count": len(state.memory),
        },
        "execution_trace": trace,
        "turn_count": state.turn_count,
        "mock": True,
    }
