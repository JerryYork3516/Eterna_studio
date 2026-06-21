"""Node completeness — Contract §3.1, §9 (single decision point).

This is the SINGLE judgment function shared by `validator` and `mock_runner`
so that validate and mock-run always reach the same conclusion.

`check_node` returns per-node structural checks (errors block, warnings do not).
`is_node_complete` is the boolean derived from those checks (no error AND no
content-level warning), used by mock_runner to pick success vs. warning.
"""

from __future__ import annotations

from typing import List

from ..models.enums import LockLevel, NodeType
from ..models.review import ValidationCheck
from ..models.workflow import WorkflowNode

# Structural required fields for layer_container data (§2.4).
LAYER_REQUIRED_FIELDS = ("layer_index", "status", "version")
VALID_LAYER_STATUS = {"empty", "in_progress", "complete"}


def check_node(node: WorkflowNode) -> List[ValidationCheck]:
    """Per-node structural / completeness checks. Order-independent."""
    checks: List[ValidationCheck] = []

    # invalid_lock_level — `mixed` only on layer_container (M2, error).
    if node.lock_level == LockLevel.mixed and node.type != NodeType.layer_container:
        checks.append(
            ValidationCheck(
                rule="invalid_lock_level",
                level="error",
                target_id=node.node_id,
                message=(
                    f"lock_level 'mixed' is only allowed on layer_container, "
                    f"got type '{node.type.value}'."
                ),
            )
        )

    if node.type == NodeType.layer_container:
        for field in LAYER_REQUIRED_FIELDS:
            if node.data.get(field) in (None, ""):
                checks.append(
                    ValidationCheck(
                        rule="layer_required_field",
                        level="error",
                        target_id=node.node_id,
                        message=f"layer_container is missing required field '{field}'.",
                    )
                )
        status = node.data.get("status")
        if status is not None and status not in VALID_LAYER_STATUS:
            checks.append(
                ValidationCheck(
                    rule="layer_required_field",
                    level="error",
                    target_id=node.node_id,
                    message=(
                        f"layer_container status '{status}' is invalid; "
                        f"expected one of {sorted(VALID_LAYER_STATUS)}."
                    ),
                )
            )

    elif node.type == NodeType.model:
        # Content not yet filled in — warning only, never blocks (MVP).
        if not node.data.get("model"):
            checks.append(
                ValidationCheck(
                    rule="missing_field",
                    level="warning",
                    target_id=node.node_id,
                    message="model node has no 'model' configured.",
                )
            )

    elif node.type == NodeType.export:
        if not node.data.get("format"):
            checks.append(
                ValidationCheck(
                    rule="missing_field",
                    level="warning",
                    target_id=node.node_id,
                    message="export node has no 'format' configured.",
                )
            )

    elif node.type == NodeType.review:
        if not node.data.get("scope"):
            checks.append(
                ValidationCheck(
                    rule="missing_field",
                    level="warning",
                    target_id=node.node_id,
                    message="review node has no 'scope' configured.",
                )
            )

    return checks


def is_node_complete(node: WorkflowNode) -> bool:
    """True when the node has no structural error and no content warning.

    Used by mock_runner: an incomplete node runs as `warning` (never crashes).
    """
    return len(check_node(node)) == 0
