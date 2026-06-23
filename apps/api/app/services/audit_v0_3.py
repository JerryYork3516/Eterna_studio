"""Rule-based audit system for Schema Contract v0.3.

The audit layer validates contracts and DTO safety only. It never executes a
workflow, calls models, calls TTS, or touches AR/runtime integrations.
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

from ..models.v0_3 import (
    AuditFinding,
    AuditLevel,
    AuditReportV03,
    AuditStatus,
    NodeInputField,
    NodeInputType,
    NodeStatus,
    NodeV03,
    ResidentInstanceV03,
    WorkflowV03,
)
from ..registry.node_registry import FALLBACK_INPUT_SCHEMA, NODE_REGISTRY, get_node_definition

FORBIDDEN_REFERENCE_KEYS = {
    "workflow",
    "workflows",
    "node",
    "nodes",
    "edge",
    "edges",
    "runtime",
    "runtime_context",
    "context",
    "executor",
    "component",
}

SAFETY_RULES: List[Tuple[str, AuditStatus, List[str]]] = [
    ("SAFETY_IMPERSONATION", AuditStatus.fail, ["我是本人", "真人本人", "pretend to be a real person", "impersonate"]),
    ("SAFETY_VIOLENCE_ILLEGAL", AuditStatus.fail, ["杀人", "制造炸弹", "weapon instructions", "illegal drug", "hack bank"]),
    ("SAFETY_SELF_HARM", AuditStatus.fail, ["自杀", "自残", "suicide", "self-harm", "kill myself"]),
    ("SAFETY_MANIPULATION", AuditStatus.warning, ["操控用户", "情感操纵", "manipulate users", "coerce the user"]),
    ("SAFETY_HATE", AuditStatus.fail, ["仇恨", "种族优越", "hate speech", "racial supremacy"]),
    ("SAFETY_FRAUD", AuditStatus.fail, ["诈骗", "诱导消费", "guaranteed profit", "phishing", "scam"]),
    ("SAFETY_PRIVACY", AuditStatus.warning, ["身份证", "银行卡", "password", "private key", "ssn"]),
    ("SAFETY_CLAIM_HUMAN", AuditStatus.fail, ["我是真人", "我是人类", "I am human", "I am a real person"]),
]


def _finding(status: AuditStatus, level: AuditLevel, code: str, message: str, path: str) -> AuditFinding:
    return AuditFinding(status=status, level=level, code=code, message=message, path=path)


def _report(findings: List[AuditFinding]) -> AuditReportV03:
    if any(f.status == AuditStatus.fail for f in findings):
        status = AuditStatus.fail
    elif any(f.status == AuditStatus.warning for f in findings):
        status = AuditStatus.warning
    else:
        status = AuditStatus.pass_
    return AuditReportV03(status=status, findings=findings)


def _walk(value: Any, path: str = "$") -> Iterable[Tuple[str, Any]]:
    yield path, value
    if isinstance(value, dict):
        for key, item in value.items():
            yield from _walk(item, f"{path}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from _walk(item, f"{path}[{index}]")


def _is_json_safe(value: Any) -> bool:
    try:
        json.dumps(value, ensure_ascii=False)
        return True
    except (TypeError, ValueError, OverflowError):
        return False


def _find_circular_reference(value: Any, path: str = "$", seen: Optional[Set[int]] = None) -> Optional[str]:
    if seen is None:
        seen = set()
    if not isinstance(value, (dict, list)):
        return None
    object_id = id(value)
    if object_id in seen:
        return path
    seen.add(object_id)
    if isinstance(value, dict):
        for key, item in value.items():
            found = _find_circular_reference(item, f"{path}.{key}", seen)
            if found:
                return found
    else:
        for index, item in enumerate(value):
            found = _find_circular_reference(item, f"{path}[{index}]", seen)
            if found:
                return found
    seen.remove(object_id)
    return None


def _looks_like_stringified_json(text: str) -> bool:
    stripped = text.strip()
    if not stripped or stripped[0] not in "[{":
        return False
    try:
        parsed = json.loads(stripped)
        return isinstance(parsed, (dict, list))
    except ValueError:
        return bool(re.search(r'["{]\s*(workflow|node|runtime|resident_instance|edges?)\s*["}]', stripped, re.I))


def _dto_safety_findings(value: Any, level: AuditLevel, path: str) -> List[AuditFinding]:
    findings: List[AuditFinding] = []
    if not _is_json_safe(value):
        findings.append(_finding(AuditStatus.fail, level, "JSON_UNSAFE", "Value is not JSON.stringify safe.", path))
    circular_path = _find_circular_reference(value, path)
    if circular_path:
        findings.append(
            _finding(AuditStatus.fail, level, "CIRCULAR_REFERENCE", "Circular reference is not allowed.", circular_path)
        )
    for item_path, item in _walk(value, path):
        if isinstance(item, str) and _looks_like_stringified_json(item):
            findings.append(
                _finding(
                    AuditStatus.fail,
                    level,
                    "STRINGIFIED_JSON",
                    "Nested stringified JSON is not allowed in DTO fields.",
                    item_path,
                )
            )
        if item_path.split(".")[-1] in FORBIDDEN_REFERENCE_KEYS:
            findings.append(
                _finding(
                    AuditStatus.fail,
                    level,
                    "RUNTIME_REFERENCE",
                    "Workflow, node, edge, runtime, or component references are not allowed in DTO fields.",
                    item_path,
                )
            )
    return findings


def _safety_findings(value: Any, level: AuditLevel, base_path: str) -> List[AuditFinding]:
    findings: List[AuditFinding] = []
    for path, item in _walk(value, base_path):
        if not isinstance(item, str):
            continue
        lowered = item.lower()
        for code, status, patterns in SAFETY_RULES:
            if any(pattern.lower() in lowered for pattern in patterns):
                findings.append(
                    _finding(
                        status,
                        level,
                        code,
                        "Rule-based safety scan found disallowed or risky content.",
                        path,
                    )
                )
    return findings


def _field_map(schema: List[NodeInputField]) -> Dict[str, NodeInputField]:
    return {field.key: field for field in schema}


def _input_type_matches(value: Any, field: NodeInputField) -> bool:
    if value is None:
        return not field.required
    if field.type in (NodeInputType.text, NodeInputType.textarea, NodeInputType.color, NodeInputType.file):
        return isinstance(value, str) or (field.multiple and isinstance(value, list))
    if field.type in (NodeInputType.number, NodeInputType.slider):
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if field.type == NodeInputType.boolean:
        return isinstance(value, bool)
    if field.type == NodeInputType.select:
        return isinstance(value, str)
    if field.type in (NodeInputType.multi_select, NodeInputType.tags):
        return isinstance(value, list) and all(isinstance(item, str) for item in value)
    if field.type in (NodeInputType.json, NodeInputType.key_value):
        return isinstance(value, dict)
    return True


def audit_node(node: NodeV03, index: int = 0) -> List[AuditFinding]:
    path = f"$.nodes[{index}]"
    findings: List[AuditFinding] = []
    registry_entry = get_node_definition(node.type)

    schema = node.input_schema
    if registry_entry and not schema:
        schema = registry_entry.input_schema
    if not schema:
        schema = FALLBACK_INPUT_SCHEMA
        findings.append(
            _finding(
                AuditStatus.warning,
                AuditLevel.node,
                "INPUT_SCHEMA_FALLBACK",
                "Node has no input_schema; fallback schema is used for audit.",
                f"{path}.input_schema",
            )
        )

    if not registry_entry:
        findings.append(
            _finding(
                AuditStatus.warning,
                AuditLevel.node,
                "NODE_TYPE_UNREGISTERED",
                "Node type is not present in the v0.3 node registry.",
                f"{path}.type",
            )
        )
    elif node.status != registry_entry.status:
        findings.append(
            _finding(
                AuditStatus.warning,
                AuditLevel.node,
                "NODE_STATUS_MISMATCH",
                "Node status differs from registry status.",
                f"{path}.status",
            )
        )

    if node.status not in (NodeStatus.ready, NodeStatus.mock, NodeStatus.disabled):
        findings.append(_finding(AuditStatus.fail, AuditLevel.node, "INVALID_STATUS", "Invalid node status.", f"{path}.status"))

    fields = _field_map(schema)
    for field in schema:
        if field.required and field.key not in node.inputs:
            findings.append(
                _finding(
                    AuditStatus.fail,
                    AuditLevel.node,
                    "MISSING_INPUT",
                    f"Required input '{field.key}' is missing.",
                    f"{path}.inputs.{field.key}",
                )
            )
    for key, value in node.inputs.items():
        field = fields.get(key)
        if field is None:
            findings.append(
                _finding(
                    AuditStatus.warning,
                    AuditLevel.node,
                    "INPUT_NOT_IN_SCHEMA",
                    f"Input '{key}' is not declared by input_schema.",
                    f"{path}.inputs.{key}",
                )
            )
            continue
        if not _input_type_matches(value, field):
            findings.append(
                _finding(
                    AuditStatus.fail,
                    AuditLevel.node,
                    "INPUT_TYPE_MISMATCH",
                    f"Input '{key}' does not match declared type '{field.type.value}'.",
                    f"{path}.inputs.{key}",
                )
            )

    if not isinstance(node.outputs, dict):
        findings.append(_finding(AuditStatus.fail, AuditLevel.node, "OUTPUT_NOT_DTO", "Node outputs must be a JSON object DTO.", f"{path}.outputs"))
    findings.extend(_dto_safety_findings(node.outputs, AuditLevel.node, f"{path}.outputs"))
    findings.extend(_dto_safety_findings(node.params, AuditLevel.node, f"{path}.params"))
    findings.extend(_dto_safety_findings(node.metadata, AuditLevel.node, f"{path}.metadata"))
    findings.extend(_safety_findings(node.model_dump(mode="json"), AuditLevel.node, path))
    return findings


def _edge_checks(workflow: WorkflowV03) -> List[AuditFinding]:
    findings: List[AuditFinding] = []
    node_by_id = {node.id: node for node in workflow.nodes}
    for index, edge in enumerate(workflow.edges):
        path = f"$.edges[{index}]"
        source = node_by_id.get(edge.source_node_id)
        target = node_by_id.get(edge.target_node_id)
        if source is None:
            findings.append(_finding(AuditStatus.fail, AuditLevel.module, "EDGE_SOURCE_MISSING", "Edge source node is missing.", f"{path}.source_node_id"))
            continue
        if target is None:
            findings.append(_finding(AuditStatus.fail, AuditLevel.module, "EDGE_TARGET_MISSING", "Edge target node is missing.", f"{path}.target_node_id"))
            continue

        source_outputs = {field.key for field in source.output_schema} | set(source.outputs.keys())
        target_inputs = {field.key for field in (target.input_schema or get_node_definition(target.type).input_schema if get_node_definition(target.type) else [])}
        if edge.source_output not in source_outputs:
            findings.append(_finding(AuditStatus.warning, AuditLevel.module, "EDGE_OUTPUT_UNDECLARED", "Edge source output is not declared by the source node.", f"{path}.source_output"))
        if edge.target_input not in target_inputs:
            findings.append(_finding(AuditStatus.warning, AuditLevel.module, "EDGE_INPUT_UNDECLARED", "Edge target input is not declared by the target node.", f"{path}.target_input"))
    return findings


def _graph_cycle_checks(workflow: WorkflowV03) -> List[AuditFinding]:
    outgoing: Dict[str, List[str]] = {node.id: [] for node in workflow.nodes}
    indegree: Dict[str, int] = {node.id: 0 for node in workflow.nodes}
    for edge in workflow.edges:
        if edge.source_node_id in outgoing and edge.target_node_id in indegree:
            outgoing[edge.source_node_id].append(edge.target_node_id)
            indegree[edge.target_node_id] += 1

    queue = [node_id for node_id, degree in indegree.items() if degree == 0]
    visited = 0
    while queue:
        node_id = queue.pop(0)
        visited += 1
        for target in outgoing[node_id]:
            indegree[target] -= 1
            if indegree[target] == 0:
                queue.append(target)

    if visited != len(indegree):
        return [
            _finding(
                AuditStatus.fail,
                AuditLevel.module,
                "CYCLE_DETECTED",
                "Workflow edges contain a cycle; contract graphs must be acyclic.",
                "$.edges",
            )
        ]
    return []


def audit_modules_and_layers(workflow: WorkflowV03) -> List[AuditFinding]:
    findings: List[AuditFinding] = []
    node_ids = {node.id for node in workflow.nodes}
    module_ids = {module.id for module in workflow.modules}
    connected_nodes = {edge.source_node_id for edge in workflow.edges} | {edge.target_node_id for edge in workflow.edges}

    findings.extend(_edge_checks(workflow))
    findings.extend(_graph_cycle_checks(workflow))

    if len(workflow.nodes) > 1:
        for index, node in enumerate(workflow.nodes):
            if node.id not in connected_nodes:
                findings.append(
                    _finding(AuditStatus.warning, AuditLevel.module, "NODE_DISCONNECTED", "Node is not connected to any edge.", f"$.nodes[{index}]")
                )

    for index, module in enumerate(workflow.modules):
        path = f"$.modules[{index}]"
        for node_id in module.node_ids:
            if node_id not in node_ids:
                findings.append(_finding(AuditStatus.fail, AuditLevel.module, "MODULE_NODE_MISSING", "Module references an unknown node.", f"{path}.node_ids"))
        for field in module.output_schema:
            if field.required and field.key not in module.outputs:
                findings.append(_finding(AuditStatus.warning, AuditLevel.module, "MODULE_OUTPUT_INCOMPLETE", "Module is missing a required output field.", f"{path}.outputs.{field.key}"))

    for index, layer in enumerate(workflow.layers):
        path = f"$.layers[{index}]"
        for module_id in layer.module_ids:
            if module_id not in module_ids:
                findings.append(_finding(AuditStatus.fail, AuditLevel.layer, "LAYER_MODULE_MISSING", "Layer references an unknown module.", f"{path}.module_ids"))
        for node_id in layer.node_ids:
            if node_id not in node_ids:
                findings.append(_finding(AuditStatus.fail, AuditLevel.layer, "LAYER_NODE_MISSING", "Layer references an unknown node.", f"{path}.node_ids"))
        for field in layer.output_schema:
            if field.required and field.key not in layer.outputs:
                findings.append(_finding(AuditStatus.warning, AuditLevel.layer, "LAYER_OUTPUT_INCOMPLETE", "Layer is missing a required output field.", f"{path}.outputs.{field.key}"))

    return findings


def audit_workflow(workflow: WorkflowV03) -> AuditReportV03:
    findings: List[AuditFinding] = []
    if workflow.schema_version != "0.3.0":
        findings.append(_finding(AuditStatus.fail, AuditLevel.module, "SCHEMA_VERSION_INVALID", "Workflow schema_version must be '0.3.0'.", "$.schema_version"))
    for index, node in enumerate(workflow.nodes):
        findings.extend(audit_node(node, index))
    findings.extend(audit_modules_and_layers(workflow))
    findings.extend(_dto_safety_findings(workflow.metadata.model_dump(mode="json"), AuditLevel.module, "$.metadata"))
    return _report(findings)


def audit_resident(resident: ResidentInstanceV03) -> AuditReportV03:
    value = resident.model_dump(mode="json")
    findings: List[AuditFinding] = []
    required_sections = ["identity", "personality", "dialogue", "voice_profile", "avatar", "metadata"]
    for section in required_sections:
        if section not in value or not isinstance(value[section], dict):
            findings.append(_finding(AuditStatus.fail, AuditLevel.resident, "RESIDENT_SECTION_MISSING", f"Resident section '{section}' is missing.", f"$.{section}"))

    if not resident.identity.name:
        findings.append(_finding(AuditStatus.warning, AuditLevel.resident, "RESIDENT_IDENTITY_INCOMPLETE", "Resident identity.name is empty.", "$.identity.name"))
    if not resident.personality.traits:
        findings.append(_finding(AuditStatus.warning, AuditLevel.resident, "RESIDENT_PERSONALITY_INCOMPLETE", "Resident personality.traits is empty.", "$.personality.traits"))
    if not resident.metadata.mock:
        findings.append(_finding(AuditStatus.warning, AuditLevel.resident, "RESIDENT_MOCK_MARKER", "Stage 4 resident_instance should be marked mock=true.", "$.metadata.mock"))
    if not resident.voice_profile.mock:
        findings.append(_finding(AuditStatus.warning, AuditLevel.resident, "VOICE_PROFILE_MOCK_MARKER", "voice_profile should be marked mock=true while TTS is not integrated.", "$.voice_profile.mock"))
    if not resident.avatar.mock:
        findings.append(_finding(AuditStatus.warning, AuditLevel.resident, "AVATAR_MOCK_MARKER", "avatar should be marked mock=true while AR/runtime is not integrated.", "$.avatar.mock"))

    findings.extend(_dto_safety_findings(value, AuditLevel.resident, "$"))
    findings.extend(_safety_findings(value, AuditLevel.resident, "$"))
    return _report(findings)
