"""V4ToV3Translator — translate a v0.4 workflow into a v0.3 workflow.

Translation only: it builds a v0.3-compatible data structure and never executes
anything. The 13-layer trunk semantics are preserved.

Mapping:
  NodeV4   -> NodeV3        (node_id->id, node_type->type, execution_status->status;
                             slot_binding/module_id/layer_id retained in metadata)
  ModuleV4 -> legacy module (capability modules recorded as metadata, not executed)
  SlotV4   -> runtime binding mapping (slot_id/engine recorded in node metadata)
  EngineV4 -> mock-compatible adapter (resolved descriptor only; never called here)

If the v0.4 workflow was migrated from v0.3 it carries the exact original under
extensions.legacy; that lossless payload is preferred so the round-trip is
byte-faithful and the v0.3 mock-run output is identical.
"""

from __future__ import annotations

from typing import Any, Dict, List

from ..models.v0_3 import WorkflowV03
from ..models.v0_4 import WorkflowV04
from ..registry.node_registry import get_node_definition
from .workflow_v0_3 import normalize_workflow_v0_3


def _node_v4_to_v3_dict(node: Dict[str, Any]) -> Dict[str, Any]:
    node_type = str(node.get("node_type") or node.get("type") or "unknown")
    definition = get_node_definition(node_type)
    metadata = dict(node.get("metadata") or {})
    # SlotV4 -> runtime binding mapping: retain binding info as metadata (not executed).
    metadata.update(
        {
            "v4_origin": True,
            "slot_binding": node.get("slot_binding"),
            "module_id": node.get("module_id"),
            "layer_id": node.get("layer_id"),
        }
    )
    return {
        "id": str(node.get("node_id") or node.get("id") or ""),
        "type": node_type,
        "label": metadata.get("label") or node.get("label") or node_type,
        "category": definition.category if definition else str(node.get("category") or "unknown"),
        "status": node.get("execution_status") or node.get("status") or "MOCK",
        "input_schema": node.get("input_schema") or [],
        "inputs": node.get("inputs") or {},
        "output_schema": node.get("output_schema") or [],
        "outputs": node.get("outputs") or {},
        "params": {},
        "ui": {},
        "metadata": metadata,
    }


def _from_trunk(wf4: Dict[str, Any]) -> Dict[str, Any]:
    nodes = [_node_v4_to_v3_dict(n) for n in (wf4.get("nodes") or [])]
    edges = [
        {
            "id": str(e.get("id") or ""),
            "source_node_id": e.get("source_node_id", ""),
            "source_output": e.get("source_output", "output"),
            "target_node_id": e.get("target_node_id", ""),
            "target_input": e.get("target_input", "input"),
            "metadata": dict(e.get("metadata") or {}),
        }
        for e in (wf4.get("edges") or [])
    ]
    layers = [
        {
            "id": l.get("layer_id", ""),
            "name": l.get("layer_name", ""),
            "module_ids": list(l.get("module_ids") or []),
            "node_ids": list(l.get("node_ids") or []),
            "output_schema": [],
            "outputs": {},
            "metadata": {},
        }
        for l in (wf4.get("layers") or [])
    ]
    # ModuleV4 -> legacy structural modules recovered from the migration record;
    # capability modules in wf4["modules"] are recorded but never made executable.
    legacy_modules = (wf4.get("extensions") or {}).get("legacy_modules")
    modules: List[Dict[str, Any]] = legacy_modules if isinstance(legacy_modules, list) else []
    return {
        "schema_version": "0.3.0",
        "id": str(wf4.get("id") or "wf_v4"),
        "name": str(wf4.get("name") or "Untitled Workflow"),
        "layers": layers,
        "modules": modules,
        "nodes": nodes,
        "edges": edges,
        "metadata": dict(wf4.get("metadata") or {}),
    }


def translate_v0_4_to_v0_3(value: Any) -> WorkflowV03:
    """Translate a v0.4 workflow (model/dict) into a validated WorkflowV03."""
    wf4 = value.model_dump(mode="json") if isinstance(value, WorkflowV04) else dict(value or {})

    # Prefer the lossless original captured at migration time.
    legacy = (wf4.get("extensions") or {}).get("legacy")
    if isinstance(legacy, dict) and legacy.get("schema_version") == "0.3.0":
        return normalize_workflow_v0_3(legacy)

    return normalize_workflow_v0_3(_from_trunk(wf4))
