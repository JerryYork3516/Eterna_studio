"""Topological sort + cycle detection — Contract §0, §4.

Workflow is a DAG. Mock Run uses topological ordering. A detected cycle is a
package-blocking error (cycle_detected).
"""

from __future__ import annotations

from typing import Dict, List, Optional, Set, Tuple

from ..models.workflow import Workflow


def topo_sort(workflow: Workflow) -> Tuple[Optional[List[str]], Set[str]]:
    """Kahn's algorithm.

    Returns (order, cycle_nodes):
      - order = topologically sorted node_ids, or None if a cycle exists.
      - cycle_nodes = node_ids that remain unresolved when a cycle is present
        (empty when acyclic).
    Edges referencing unknown nodes are ignored here; the validator reports them
    separately as invalid_edge.
    """
    node_ids = [n.node_id for n in workflow.nodes]
    node_set = set(node_ids)

    indegree: Dict[str, int] = {nid: 0 for nid in node_ids}
    adjacency: Dict[str, List[str]] = {nid: [] for nid in node_ids}

    for edge in workflow.edges:
        if edge.source not in node_set or edge.target not in node_set:
            continue
        adjacency[edge.source].append(edge.target)
        indegree[edge.target] += 1

    # Seed with indegree-0 nodes, preserving original declaration order.
    queue = [nid for nid in node_ids if indegree[nid] == 0]
    order: List[str] = []

    while queue:
        current = queue.pop(0)
        order.append(current)
        for nxt in adjacency[current]:
            indegree[nxt] -= 1
            if indegree[nxt] == 0:
                queue.append(nxt)

    if len(order) != len(node_ids):
        cycle_nodes = {nid for nid in node_ids if nid not in set(order)}
        return None, cycle_nodes

    return order, set()
