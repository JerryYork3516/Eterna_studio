"""Memory Snapshotter — Stage 6.1 observability.

Execution boundary (do not violate):
  * Node / Module / Slot are protocol descriptors only — they never execute.
  * The Execution Engine (execution_engine.py) is the only runtime entry; this
    snapshotter is reached only through resident_runtime.
  * It reads the mock Memory provider through provider_adapters.route_provider
    (the same surface the loop uses) — never a real database.

Captures an immutable, point-in-time snapshot of a resident's memory so each
run can emit "memory after this turn", and two runs can be diffed to show
memory growth in a Debug Panel.
"""

from __future__ import annotations

import copy
from datetime import datetime, timezone
from typing import Any, Dict

from .provider_adapters import route_provider


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def take_snapshot(resident_id: str, run_id: str = "") -> Dict[str, Any]:
    """Return a deep-copied snapshot of the resident's mock memory.

    The entries are deep-copied so the snapshot is stable even if later turns
    mutate the underlying store. Shape::

        {
            "resident_id": ...,
            "run_id": ...,
            "captured_at": <ISO-8601 UTC>,
            "entries": [...],
            "count": <int>,
        }
    """
    listing = route_provider("memory", {"op": "list", "resident_id": resident_id})
    entries = copy.deepcopy(list(listing.get("entries", [])))
    return {
        "resident_id": resident_id,
        "run_id": run_id,
        "captured_at": _now_iso(),
        "entries": entries,
        "count": len(entries),
    }
