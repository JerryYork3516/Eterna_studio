"""Execution Engine — Stage 6 single runtime entry.

Execution boundary (do not violate):
  * Node / Module / Slot are protocol descriptors only — they never execute.
  * THIS module is the ONLY runtime entry. Protocol execute, resident step and
    the runtime loop must all pass through here.
  * UI never executes. Providers are mock-only and reached only via this engine
    (through resident_runtime / provider_adapters).

It does not reimplement runtime logic: workflow execution reuses the existing
v0.4 orchestrator + v0.3 execution adapter; the resident step delegates to the
resident_runtime loop.
"""

from __future__ import annotations

from typing import Any, Dict

from . import resident_runtime
from .v4_orchestrator import execute as orchestrate_execute

RUNTIME_VERSION = "resident_v1_mock"
SCHEMA_VERSION = "0.4.0"


def execute_workflow(workflow: Any, action: str = "mock_run") -> Dict[str, Any]:
    """Plan + forward a workflow through the existing control plane / adapter.

    Reuses v4_orchestrator.execute (which chains plan_execution + execute_plan).
    Returns a plain dict — never a Python object reference.
    """
    return orchestrate_execute(workflow, action).model_dump(mode="json")


def execute_resident_step(
    workflow: Any, input_text: str, resident_id: str = "resident_v1"
) -> Dict[str, Any]:
    """Run one Resident v1 step through the fixed mock runtime loop.

    The only entry the API uses for the resident runtime loop. Returns a plain
    dict envelope.
    """
    loop = resident_runtime.run_resident_loop(workflow, input_text, resident_id)
    return {
        "schema_version": SCHEMA_VERSION,
        "runtime_version": RUNTIME_VERSION,
        **loop,
    }
