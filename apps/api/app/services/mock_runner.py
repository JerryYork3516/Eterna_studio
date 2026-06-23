"""Legacy v0.2 mock runner.

The mounted runtime path uses workflow_v0_3.mock_run_v0_3. This file remains for
historical compatibility only and must not be used as the main runtime.

No real LLM calls. Executes nodes in topological order, producing mock outputs.
Incomplete nodes run as `warning` (never crash). A detected cycle makes the
whole run `error` (the validator emits the cycle_detected check).
"""

from __future__ import annotations

from ..models.enums import NodeType, RunStatus
from ..models.run import Artifact, NodeRunResult, RunLog, RunResult
from ..models.workflow import Workflow
from ..util import gen_id, now
from . import completeness
from .topo import topo_sort

# Fixed mock duration so runs are deterministic / reproducible.
_MOCK_DURATION_MS = 5


def _mock_output(node) -> dict:
    """A small, type-aware placeholder output (no real execution)."""
    return {
        "mock": True,
        "node_type": node.type.value,
        "title": node.title_fallback,
        "echo": node.data,
    }


def mock_run(workflow: Workflow) -> RunResult:
    started = now()
    order, _cycle_nodes = topo_sort(workflow)

    # Cycle → overall error; do not attempt execution.
    if order is None:
        return RunResult(
            workflow_id=workflow.workflow_id,
            status=RunStatus.error,
            order=[],
            node_results=[],
            artifacts=[],
            started_at=started,
            finished_at=now(),
        )

    node_by_id = {n.node_id: n for n in workflow.nodes}
    node_results = []
    artifacts = []
    any_warning = False

    for node_id in order:
        node = node_by_id[node_id]
        complete = completeness.is_node_complete(node)
        status = RunStatus.success if complete else RunStatus.warning
        if not complete:
            any_warning = True

        logs = [
            RunLog(
                level="info" if complete else "warn",
                message=(
                    f"executed '{node.title_fallback}' ({node.type.value})"
                    if complete
                    else f"node '{node.title_fallback}' is incomplete; ran with warning"
                ),
            )
        ]

        node_results.append(
            NodeRunResult(
                node_id=node_id,
                status=status,
                output=_mock_output(node),
                logs=logs,
                duration_ms=_MOCK_DURATION_MS,
            )
        )

        # export / output nodes emit an artifact preview.
        if node.type in (NodeType.export, NodeType.output):
            artifacts.append(
                Artifact(
                    artifact_id=gen_id("ar"),
                    node_id=node_id,
                    kind=str(node.data.get("format", node.type.value)),
                    name=node.title_fallback,
                    preview={"mock": True, "from_node": node_id},
                )
            )

    overall = RunStatus.warning if any_warning else RunStatus.success
    return RunResult(
        workflow_id=workflow.workflow_id,
        status=overall,
        order=order,
        node_results=node_results,
        artifacts=artifacts,
        started_at=started,
        finished_at=now(),
    )
