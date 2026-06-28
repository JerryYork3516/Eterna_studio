"""Runtime State Manager — Stage 6.1 observability.

Execution boundary (do not violate):
  * Node / Module / Slot are protocol descriptors only — they never execute.
  * The Execution Engine (execution_engine.py) is the only runtime entry; this
    manager is reached only through resident_runtime.
  * Pure bookkeeping: it tracks run lifecycle metadata only. It never calls a
    provider, never executes the loop. No network, no database.

Owns the lifecycle metadata of a single resident step run — ``run_id``,
``turn_count``, ``status`` — and keeps a process-local run history per resident
so completed runs can be listed and replayed.

A run moves: created -> running (start_run) -> completed (complete_run), or
-> error (fail_run).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

STATUS_RUNNING = "running"
STATUS_COMPLETED = "completed"
STATUS_ERROR = "error"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class RunState:
    """Lifecycle metadata for one resident step run."""

    run_id: str
    resident_id: str
    status: str = STATUS_RUNNING
    turn_count: int = 0
    started_at: str = field(default_factory=_now_iso)
    ended_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "resident_id": self.resident_id,
            "status": self.status,
            "turn_count": self.turn_count,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
        }


# Process-local run history, keyed by resident_id. No persistence.
_HISTORY: Dict[str, List[RunState]] = {}


class RuntimeStateManager:
    """Creates and transitions RunState objects and records run history."""

    def start_run(self, resident_id: str, turn_count: int) -> RunState:
        """Open a new run in ``running`` status and record it in history."""
        run = RunState(
            run_id=f"run_{uuid.uuid4().hex[:12]}",
            resident_id=resident_id,
            status=STATUS_RUNNING,
            turn_count=turn_count,
        )
        _HISTORY.setdefault(resident_id, []).append(run)
        return run

    def complete_run(self, run: RunState, turn_count: Optional[int] = None) -> RunState:
        """Mark a run completed and stamp ``ended_at``."""
        if turn_count is not None:
            run.turn_count = turn_count
        run.status = STATUS_COMPLETED
        run.ended_at = _now_iso()
        return run

    def fail_run(self, run: RunState) -> RunState:
        """Mark a run errored and stamp ``ended_at``."""
        run.status = STATUS_ERROR
        run.ended_at = _now_iso()
        return run

    def history(self, resident_id: str) -> List[Dict[str, Any]]:
        """Return the run history for a resident as a plain list of dicts."""
        return [run.to_dict() for run in _HISTORY.get(resident_id, [])]


def reset_history() -> None:
    """Test seam: clear the process-local run history."""
    _HISTORY.clear()
