"""Persona Builder — 13-layer default structure (Contract §8, §8.1, M1).

Generates a generic 13-layer trunk workflow. The persona builder is just ONE
template; the system itself stays domain-agnostic. The 13-layer order and the
default lock levels are fixed by the contract and MUST NOT be reordered.
"""

from __future__ import annotations

import json
import os
from typing import List, Optional

from ..models.enums import LockLevel, ModuleTier, NodeCategory, NodeType
from ..models.workflow import (
    Port,
    Ports,
    Position,
    Viewport,
    Workflow,
    WorkflowEdge,
    WorkflowMetadata,
    WorkflowNode,
)
from ..util import gen_id

_LOCALES_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "locales")

# (layer_index, title_key, default lock_level, module_tier) — Contract §8 (V7).
# Order is fixed; v0.2 only adds the tier column, never reorders.
LAYERS = [
    (1, "layer.source_input", LockLevel.editable, ModuleTier.core),
    (2, "layer.identity_core", LockLevel.locked, ModuleTier.core),
    (3, "layer.legal_permission", LockLevel.locked, ModuleTier.core),
    (4, "layer.safety_boundary", LockLevel.locked, ModuleTier.core),
    (5, "layer.world_context", LockLevel.review_required, ModuleTier.later),
    (6, "layer.personality", LockLevel.review_required, ModuleTier.core),
    (7, "layer.memory", LockLevel.review_required, ModuleTier.core),
    (8, "layer.knowledge", LockLevel.editable, ModuleTier.core),
    (9, "layer.relationship", LockLevel.review_required, ModuleTier.later),
    (10, "layer.behavior", LockLevel.review_required, ModuleTier.core),
    (11, "layer.capability_tools", LockLevel.editable, ModuleTier.plugin),
    (12, "layer.multimodal", LockLevel.review_required, ModuleTier.plugin),
    (13, "layer.audit_export_deploy", LockLevel.mixed, ModuleTier.core),  # M1
]

# layer_index -> expected ModuleTier (Contract §8). Single source for the V8
# trunk-layer existence rule in services.validator.
TIER_BY_INDEX = {idx: tier for idx, _key, _lock, tier in LAYERS}

# Layer-13 children (Contract §8.1): (title_key, NodeType, NodeCategory, lock_level, data)
LAYER13_CHILDREN = [
    ("node.audit_log", NodeType.output, NodeCategory.sink, LockLevel.system_locked, {"append_only": True}),
    ("node.version_snapshot", NodeType.output, NodeCategory.sink, LockLevel.system_locked, {"append_only": True}),
    ("node.export_workflow", NodeType.export, NodeCategory.sink, LockLevel.editable, {"format": "workflow_json"}),
    ("node.export_persona", NodeType.export, NodeCategory.sink, LockLevel.editable, {"format": "persona"}),
    ("node.deploy_target", NodeType.output, NodeCategory.sink, LockLevel.review_required, {}),
]


def _load_locale(ui_language: str) -> dict:
    lang = ui_language if ui_language in ("zh", "en") else "en"
    path = os.path.join(_LOCALES_DIR, f"{lang}.json")
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {}


def _std_ports() -> Ports:
    return Ports(
        inputs=[Port(port_id="p_in", name="input", direction="in")],
        outputs=[Port(port_id="p_out", name="output", direction="out")],
    )


def build(name: Optional[str] = None, ui_language: str = "zh") -> Workflow:
    """Build the 13-layer persona-builder workflow (Contract §7.4)."""
    locale = _load_locale(ui_language)
    nodes: List[WorkflowNode] = []
    edges: List[WorkflowEdge] = []

    layer_node_ids: List[str] = []

    for idx, title_key, lock_level, module_tier in LAYERS:
        node_id = f"nd_layer{idx}"
        children_count = len(LAYER13_CHILDREN) if idx == 13 else 0
        nodes.append(
            WorkflowNode(
                node_id=node_id,
                type=NodeType.layer_container,
                category=NodeCategory.container,
                title_key=title_key,
                title_fallback=locale.get(title_key, title_key),
                position=Position(x=0, y=(idx - 1) * 160),
                lock_level=lock_level,
                locale=None,
                data={
                    "layer_index": idx,
                    "status": "empty",
                    "version": "1.0.0",
                    "children_count": children_count,
                    "module_tier": module_tier.value,  # V7: 主干层后端写死
                },
                ports=_std_ports(),
            )
        )
        layer_node_ids.append(node_id)

    # Linear trunk: layer1 -> layer2 -> ... -> layer13.
    for i in range(len(layer_node_ids) - 1):
        edges.append(
            WorkflowEdge(
                edge_id=gen_id("ed"),
                source=layer_node_ids[i],
                source_port="p_out",
                target=layer_node_ids[i + 1],
                target_port="p_in",
            )
        )

    # Layer-13 children (§8.1): hang off layer13 so the mixed container is
    # non-empty and the children are not orphans.
    for child_i, (title_key, ntype, ncat, lock_level, data) in enumerate(LAYER13_CHILDREN):
        child_id = f"nd_l13_{title_key.split('.')[-1]}"
        # V7: 子模块节点 module_tier 默认 null，由前端/用户设定。
        child_data = {"module_tier": None, **data}
        nodes.append(
            WorkflowNode(
                node_id=child_id,
                type=ntype,
                category=ncat,
                title_key=title_key,
                title_fallback=locale.get(title_key, title_key),
                position=Position(x=320, y=12 * 160 + child_i * 120),
                lock_level=lock_level,
                locale=None,
                data=child_data,
                ports=Ports(
                    inputs=[Port(port_id="p_in", name="input", direction="in")],
                    outputs=[],
                ),
            )
        )
        edges.append(
            WorkflowEdge(
                edge_id=gen_id("ed"),
                source="nd_layer13",
                source_port="p_out",
                target=child_id,
                target_port="p_in",
            )
        )

    return Workflow(
        workflow_id=gen_id("wf"),
        name=name or "Persona Builder",
        version="1.0.0",
        template_type="persona_builder",
        content_locale=None,
        nodes=nodes,
        edges=edges,
        viewport=Viewport(x=0, y=0, zoom=1),
        metadata=WorkflowMetadata(
            description="13-layer persona builder trunk (Contract §8).",
            ui_language=ui_language if ui_language in ("zh", "en") else "en",
        ),
    )
