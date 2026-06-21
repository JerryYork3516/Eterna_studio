"""ValidationReview logic — Contract §3.1, §7.5.

Combines:
  - graph-level checks: invalid_edge, orphan_node, cycle_detected, mixed_empty
  - per-node structural checks: from services.completeness (single source)

Then distributes them into node / layer / package ValidationReviews.
error → status failed (blocks); warning → status warning (does not block).
"""

from __future__ import annotations

from typing import Dict, List

from ..models.enums import LockLevel, ModuleTier, NodeType, ReviewScope, ReviewStatus
from ..models.review import ValidationCheck, ValidationReview
from ..models.workflow import Workflow, WorkflowNode
from . import completeness
from .persona_builder import TIER_BY_INDEX
from .topo import topo_sort

# V8: the trunk-layer existence rule only applies to persona builder workflows;
# generic / blank workflows are NOT forced to have 13 layers.
PERSONA_TEMPLATE_TYPE = "persona_builder"


def _status_from_checks(checks: List[ValidationCheck]) -> ReviewStatus:
    if any(c.level == "error" for c in checks):
        return ReviewStatus.failed
    if any(c.level == "warning" for c in checks):
        return ReviewStatus.warning
    return ReviewStatus.passed


def trunk_layer_checks(workflow: Workflow) -> List[ValidationCheck]:
    """V8 trunk-layer existence rule (Contract §3.1.1).

    Only for template_type == "persona_builder". Judged by layer_index 1..13
    (NOT by title_key). Expected tier per index comes from §8 (TIER_BY_INDEX).

        tier=core   : missing -> missing_trunk_layer (error)
                      present & children_count==0 -> empty_core_layer (warning)
        tier=plugin : missing -> missing_trunk_layer (warning); empty -> ok
        tier=later  : missing/empty -> ok
    """
    checks: List[ValidationCheck] = []
    if workflow.template_type != PERSONA_TEMPLATE_TYPE:
        return checks

    present: dict = {}
    for node in workflow.nodes:
        if node.type == NodeType.layer_container:
            idx = node.data.get("layer_index")
            if idx is not None:
                present[int(idx)] = node

    for idx, tier in TIER_BY_INDEX.items():
        node = present.get(idx)
        if node is None:
            if tier == ModuleTier.core:
                checks.append(
                    ValidationCheck(
                        rule="missing_trunk_layer",
                        level="error",
                        target_id=None,
                        message=f"required core trunk layer (layer_index={idx}) is missing.",
                    )
                )
            elif tier == ModuleTier.plugin:
                checks.append(
                    ValidationCheck(
                        rule="missing_trunk_layer",
                        level="warning",
                        target_id=None,
                        message=f"plugin trunk layer (layer_index={idx}) is missing.",
                    )
                )
            # later: not reported.
        else:
            if tier == ModuleTier.core and int(node.data.get("children_count", 0) or 0) == 0:
                checks.append(
                    ValidationCheck(
                        rule="empty_core_layer",
                        level="warning",
                        target_id=node.node_id,
                        message=f"core trunk layer (layer_index={idx}) has no child nodes.",
                    )
                )
            # plugin empty -> ok; later -> ok.

    return checks


def graph_checks(workflow: Workflow) -> List[ValidationCheck]:
    """Checks that depend on the whole graph rather than a single node."""
    checks: List[ValidationCheck] = []
    node_by_id: Dict[str, WorkflowNode] = {n.node_id: n for n in workflow.nodes}

    # --- edges: endpoints + ports must exist (invalid_edge) ---
    referenced: set = set()
    for edge in workflow.edges:
        src = node_by_id.get(edge.source)
        tgt = node_by_id.get(edge.target)
        if src is None or tgt is None:
            missing = edge.source if src is None else edge.target
            checks.append(
                ValidationCheck(
                    rule="invalid_edge",
                    level="error",
                    target_id=edge.edge_id,
                    message=f"edge references unknown node '{missing}'.",
                )
            )
            continue
        referenced.add(edge.source)
        referenced.add(edge.target)
        if edge.source_port not in {p.port_id for p in src.ports.outputs}:
            checks.append(
                ValidationCheck(
                    rule="invalid_edge",
                    level="error",
                    target_id=edge.edge_id,
                    message=(
                        f"edge source_port '{edge.source_port}' is not an output "
                        f"of node '{edge.source}'."
                    ),
                )
            )
        if edge.target_port not in {p.port_id for p in tgt.ports.inputs}:
            checks.append(
                ValidationCheck(
                    rule="invalid_edge",
                    level="error",
                    target_id=edge.edge_id,
                    message=(
                        f"edge target_port '{edge.target_port}' is not an input "
                        f"of node '{edge.target}'."
                    ),
                )
            )

    # --- orphan_node: node touched by no edge (only meaningful for >1 node) ---
    if len(workflow.nodes) > 1:
        for node in workflow.nodes:
            if node.node_id not in referenced:
                checks.append(
                    ValidationCheck(
                        rule="orphan_node",
                        level="warning",
                        target_id=node.node_id,
                        message="node is not connected to any edge.",
                    )
                )

    # --- mixed_empty: mixed container must hold at least one child (warning) ---
    for node in workflow.nodes:
        if (
            node.type == NodeType.layer_container
            and node.lock_level == LockLevel.mixed
            and int(node.data.get("children_count", 0) or 0) == 0
        ):
            checks.append(
                ValidationCheck(
                    rule="mixed_empty",
                    level="warning",
                    target_id=node.node_id,
                    message="mixed layer_container must contain at least one child node.",
                )
            )

    # --- V8 trunk-layer existence (persona_builder only) ---
    checks.extend(trunk_layer_checks(workflow))

    # --- cycle_detected ---
    order, cycle_nodes = topo_sort(workflow)
    if order is None:
        checks.append(
            ValidationCheck(
                rule="cycle_detected",
                level="error",
                target_id=None,
                message=(
                    "workflow graph contains a cycle (must be a DAG); "
                    f"unresolved nodes: {sorted(cycle_nodes)}."
                ),
            )
        )

    return checks


def validate(workflow: Workflow):
    """Return (package, layers, nodes) ValidationReviews — Contract §7.5."""
    g_checks = graph_checks(workflow)

    # Per-node structural checks (shared completeness source).
    node_checks: Dict[str, List[ValidationCheck]] = {}
    for node in workflow.nodes:
        node_checks[node.node_id] = list(completeness.check_node(node))

    # Fold graph checks that target a specific node into that node's bucket
    # (so node/layer reviews surface them too). target_id may be an edge id or
    # None (cycle) — those stay package-only.
    node_id_set = {n.node_id for n in workflow.nodes}
    for chk in g_checks:
        if chk.target_id in node_id_set:
            node_checks[chk.target_id].append(chk)

    # node reviews (every node).
    node_reviews: List[ValidationReview] = []
    for node in workflow.nodes:
        cs = node_checks[node.node_id]
        node_reviews.append(
            ValidationReview(
                scope=ReviewScope.node,
                status=_status_from_checks(cs),
                checks=cs,
            )
        )

    # layer reviews (one per layer_container).
    layer_reviews: List[ValidationReview] = []
    for node in workflow.nodes:
        if node.type == NodeType.layer_container:
            cs = node_checks[node.node_id]
            layer_reviews.append(
                ValidationReview(
                    scope=ReviewScope.layer,
                    status=_status_from_checks(cs),
                    checks=cs,
                )
            )

    # package review — all checks (graph + every node).
    all_checks: List[ValidationCheck] = list(g_checks)
    for node in workflow.nodes:
        all_checks.extend(completeness.check_node(node))
    package = ValidationReview(
        scope=ReviewScope.package,
        status=_status_from_checks(all_checks),
        checks=all_checks,
    )

    return package, layer_reviews, node_reviews
