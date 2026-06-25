"""v0.3 → v0.4.0 migration + v0.4 protocol validation.

Migration preserves the 13-layer trunk (layers / nodes / edges) and fills new
v0.4 fields with defaults. Legacy v0.3 structural modules are preserved under
extensions.legacy_modules so nothing is lost. No execution, no real provider.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from ..models.v0_3 import ResidentInstanceV03, WorkflowV03
from ..models.v0_4 import (
    CANONICAL_LAYER_IDS,
    EdgeV04,
    LayerRefV04,
    MigrationResponseV04,
    NodeV04,
    PersonaIdentityV04,
    PersonaV04,
    ProtocolValidationFinding,
    SlotType,
    WorkflowV04,
    WorkflowValidationResponseV04,
)
from ..util import gen_id
from .workflow_v0_3 import normalize_workflow_v0_3

_LAYER_NUM = re.compile(r"layer[_-]?(\d+)", re.I)


def _layer_order(layer_id: str, fallback: int) -> int:
    match = _LAYER_NUM.search(layer_id or "")
    return int(match.group(1)) if match else fallback


def _node_layer_map(workflow: WorkflowV03) -> Dict[str, str]:
    mapping: Dict[str, str] = {}
    for layer in workflow.layers:
        for node_id in layer.node_ids:
            mapping.setdefault(node_id, layer.id)
    return mapping


def _node_module_map(workflow: WorkflowV03) -> Dict[str, str]:
    mapping: Dict[str, str] = {}
    for module in workflow.modules:
        for node_id in module.node_ids:
            mapping.setdefault(node_id, module.id)
    return mapping


def migrate_workflow_to_v0_4(value: Any) -> WorkflowV04:
    """Normalize any legacy/v0.3 payload to v0.3, then map to v0.4.0."""
    workflow = normalize_workflow_v0_3(value)
    node_layer = _node_layer_map(workflow)
    node_module = _node_module_map(workflow)

    layers = [
        LayerRefV04(
            layer_id=layer.id,
            layer_name=layer.name,
            layer_order=_layer_order(layer.id, index + 1),
            module_ids=list(layer.module_ids),
            node_ids=list(layer.node_ids),
        )
        for index, layer in enumerate(workflow.layers)
    ]

    nodes = [
        NodeV04(
            node_id=node.id,
            node_type=node.type,
            input_schema=node.input_schema,
            output_schema=node.output_schema,
            execution_status=node.status,
            slot_binding=None,
            layer_id=node_layer.get(node.id),
            module_id=node_module.get(node.id),
            inputs=dict(node.inputs),
            outputs=dict(node.outputs),
            metadata=dict(node.metadata),
        )
        for node in workflow.nodes
    ]

    edges = [
        EdgeV04(
            id=edge.id,
            source_node_id=edge.source_node_id,
            source_output=edge.source_output,
            target_node_id=edge.target_node_id,
            target_input=edge.target_input,
            metadata=dict(edge.metadata),
        )
        for edge in workflow.edges
    ]

    return WorkflowV04(
        id=workflow.id,
        type="workflow",
        name=workflow.name,
        layers=layers,
        nodes=nodes,
        edges=edges,
        modules=[],  # capability modules are registered via the module catalog
        inputs={},
        outputs={},
        permissions=[],
        audit_log=[{"action": "migrate", "from": "0.3.0", "to": "0.4.0"}],
        extensions={
            "migrated_from": "0.3.0",
            "legacy_modules": [module.model_dump(mode="json") for module in workflow.modules],
            # Full original v0.3 payload — guarantees no old field is dropped.
            "legacy": workflow.model_dump(mode="json"),
        },
        metadata=workflow.metadata.model_dump(mode="json"),
    )


def migrate_persona_to_v0_4(value: Any) -> PersonaV04:
    """Migrate a v0.3 ResidentInstance (or dict) to the v0.4 Persona envelope.

    No old field is dropped: the full v0.3 resident payload is preserved under
    extensions.legacy (and extensions.legacy_resident). New v0.4 fields are
    filled with defaults.
    """
    if isinstance(value, ResidentInstanceV03):
        resident = value
    else:
        resident = ResidentInstanceV03.model_validate(value if isinstance(value, dict) else {})
    payload = resident.model_dump(mode="json")
    return PersonaV04(
        id=gen_id("persona"),
        type="persona",
        identity=PersonaIdentityV04(
            name=resident.identity.name,
            role=resident.identity.role,
            description=resident.identity.description,
            disclosure=resident.identity.disclosure,
        ),
        modules=[],
        inputs={},
        outputs={},
        permissions=[],
        audit_log=[{"action": "migrate", "from": "0.3.0", "to": "0.4.0", "kind": "persona"}],
        extensions={"migrated_from": "0.3.0", "legacy_resident": payload, "legacy": payload},
        metadata=dict(payload.get("metadata") or {}),
    )


def migrate_response(value: Any) -> MigrationResponseV04:
    incoming_version = "0.3.0"
    if isinstance(value, dict):
        incoming_version = str(value.get("schema_version") or "0.3.0")
    return MigrationResponseV04(migrated_from=incoming_version, workflow=migrate_workflow_to_v0_4(value))


def _coerce_to_v0_4(value: Any) -> WorkflowV04:
    if isinstance(value, WorkflowV04):
        return value
    if isinstance(value, dict) and value.get("schema_version") == "0.4.0":
        return WorkflowV04.model_validate(value)
    return migrate_workflow_to_v0_4(value)


def validate_workflow_v0_4(value: Any) -> WorkflowValidationResponseV04:
    workflow = _coerce_to_v0_4(value)
    findings: List[ProtocolValidationFinding] = []

    # Node Protocol: node_id non-empty + unique.
    seen: set[str] = set()
    for index, node in enumerate(workflow.nodes):
        path = f"$.nodes[{index}].node_id"
        if not node.node_id:
            findings.append(ProtocolValidationFinding(status="FAIL", code="NODE_ID_EMPTY", message="node_id must be non-empty.", path=path))
            continue
        if node.node_id in seen:
            findings.append(ProtocolValidationFinding(status="FAIL", code="NODE_ID_DUPLICATE", message=f"Duplicate node_id '{node.node_id}'.", path=path))
        seen.add(node.node_id)
        if node.layer_id is not None and node.layer_id not in CANONICAL_LAYER_IDS:
            findings.append(ProtocolValidationFinding(status="WARNING", code="NODE_LAYER_UNKNOWN", message=f"Node layer_id '{node.layer_id}' is not a canonical layer.", path=f"$.nodes[{index}].layer_id"))

    # Module Protocol: module_id non-empty + unique + bound to a canonical layer.
    module_ids: set[str] = set()
    for index, module in enumerate(workflow.modules):
        path = f"$.modules[{index}]"
        if not module.module_id:
            findings.append(ProtocolValidationFinding(status="FAIL", code="MODULE_ID_EMPTY", message="module_id must be non-empty.", path=f"{path}.module_id"))
            continue
        if module.module_id in module_ids:
            findings.append(ProtocolValidationFinding(status="FAIL", code="MODULE_ID_DUPLICATE", message=f"Duplicate module_id '{module.module_id}'.", path=f"{path}.module_id"))
        module_ids.add(module.module_id)
        if module.layer_id not in CANONICAL_LAYER_IDS:
            findings.append(ProtocolValidationFinding(status="FAIL", code="MODULE_LAYER_INVALID", message=f"Module layer_id '{module.layer_id}' is not one of the 13 canonical layers.", path=f"{path}.layer_id"))
        if module.slot_type is not None and not isinstance(module.slot_type, SlotType):
            findings.append(ProtocolValidationFinding(status="FAIL", code="MODULE_SLOT_TYPE_INVALID", message="Module slot_type is not an allowed slot_type.", path=f"{path}.slot_type"))

    valid = not any(finding.status == "FAIL" for finding in findings)
    return WorkflowValidationResponseV04(valid=valid, findings=findings)
