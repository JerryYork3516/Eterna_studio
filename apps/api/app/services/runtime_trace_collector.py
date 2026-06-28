"""Runtime Trace Collector — Stage 6.1 observability.

Execution boundary (do not violate):
  * Node / Module / Slot are protocol descriptors only — they never execute.
  * The Execution Engine (execution_engine.py) is the only runtime entry; this
    collector is reached only through resident_runtime.
  * Pure recording: it observes the mock runtime loop, it never drives it and
    never calls a provider. No real model, no network, no database.

A TraceCollector records one structured trace step per phase of a single
resident step so the whole loop (input -> memory -> reasoning -> action ->
output) can be replayed in order by a frontend Debug Panel.

Each recorded step is a plain dict shaped as::

    {
        "index": <int, 0-based order>,
        "step":  <str phase name, e.g. "reasoning">,   # backward-compatible
        "phase": <str, same as step>,
        "timestamp": <ISO-8601 UTC>,
        "input":  <Any structured input for this phase>,
        "output": <Any structured output for this phase>,
        ...<flat convenience keys merged from `data`>,
    }

The flat ``data`` keys (e.g. ``provider``, ``text``, ``count``) are preserved at
top level so existing consumers/tests keep working; the ``index`` / ``phase`` /
``timestamp`` / ``input`` / ``output`` fields are the structured additions the
Debug Panel renders.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class TraceCollector:
    """Collects ordered, structured trace steps for one resident step run."""

    def __init__(self, run_id: str, resident_id: str) -> None:
        self.run_id = run_id
        self.resident_id = resident_id
        self._steps: List[Dict[str, Any]] = []

    def record(
        self,
        step: str,
        *,
        data: Optional[Dict[str, Any]] = None,
        input: Any = None,
        output: Any = None,
    ) -> Dict[str, Any]:
        """Append one structured trace step and return it.

        ``data`` keys are merged at the top level for backward compatibility;
        ``input`` / ``output`` capture the structured payload for replay.
        """
        entry: Dict[str, Any] = {
            "index": len(self._steps),
            "step": step,
            "phase": step,
            "timestamp": _now_iso(),
            "input": input,
            "output": output,
        }
        if data:
            # Do not let convenience keys clobber the structural fields.
            for key, value in data.items():
                if key not in entry:
                    entry[key] = value
        self._steps.append(entry)
        return entry

    def steps(self) -> List[Dict[str, Any]]:
        """Return the trace as a plain list of dicts (ordered by index)."""
        return list(self._steps)

    def __len__(self) -> int:  # pragma: no cover - trivial
        return len(self._steps)
