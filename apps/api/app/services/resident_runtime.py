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

from dataclasses import dataclass, field
from typing import Any, Dict, List

from .memory_snapshotter import take_snapshot
from .provider_adapters import route_provider
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


_STATES: Dict[str, ResidentRuntimeState] = {}

_state_manager = RuntimeStateManager()


def get_or_create_state(resident_id: str) -> ResidentRuntimeState:
    state = _STATES.get(resident_id)
    if state is None:
        state = ResidentRuntimeState(resident_id=resident_id)
        _STATES[resident_id] = state
    return state


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

    # 1. input
    state.last_input = input_text
    collector.record(
        "input",
        data={"input_text": input_text},
        input=input_text,
        output={"input_text": input_text},
    )

    # 2. memory.read
    read = route_provider("memory", {"op": "read", "resident_id": resident_id})
    collector.record(
        "memory.read",
        data={"count": read.get("count", 0)},
        input={"op": "read", "resident_id": resident_id},
        output={"count": read.get("count", 0), "entries": list(read.get("entries", []))},
    )

    # 3. reasoning (mock LLM only)
    memory_context = f"{read.get('count', 0)} prior memories"
    prompt = f"{input_text}\n[context: {memory_context}]"
    reasoning = route_provider("llm", {"prompt": prompt})
    reasoning_text = reasoning.get("text", "")
    state.last_reasoning = reasoning_text
    collector.record(
        "reasoning",
        data={"provider": reasoning.get("provider"), "text": reasoning_text},
        input={"prompt": prompt},
        output=reasoning,
    )

    # 4. action / tool routing (deterministic echo)
    action = route_provider("tool", {"tool": "echo", "args": {"text": input_text}})
    state.last_action = action
    echo_result = action.get("result", "")
    collector.record(
        "action",
        data={"tool": action.get("tool"), "result": echo_result},
        input={"tool": "echo", "args": {"text": input_text}},
        output=action,
    )

    # 5/6. compose output, update state
    output_text = f"[{resident_id}] {reasoning_text} | echo: {echo_result}"
    state.last_output = output_text
    state.turn_count += 1

    # memory.write (record this turn's input/output)
    entry = {"turn": state.turn_count, "input": input_text, "output": output_text}
    write = route_provider("memory", {"op": "write", "resident_id": resident_id, "entry": entry})
    collector.record(
        "memory.write",
        data={"count": write.get("count", 0)},
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
