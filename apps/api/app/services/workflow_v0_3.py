"""v0.3 workflow adapter, template, mock runtime, and resident compiler.

Legacy v0.2-shaped payloads may enter here only to be normalized into
WorkflowV03. After normalization, all validation, audit, mock run, export, and
resident compilation logic operates on v0.3 DTOs.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Set, Tuple

from pydantic import ValidationError

from ..models.enums import RunStatus
from ..models.export import ExportPreview
from ..models.run import Artifact, NodeRunResult, RunLog, RunResult
from ..models.v0_3 import (
    EdgeV03,
    LayerV03,
    ModuleV03,
    NodeStatus,
    NodeUiState,
    NodeV03,
    ResidentInstanceV03,
    WorkflowMetadataV03,
    WorkflowV03,
)
from ..registry.node_registry import FALLBACK_INPUT_SCHEMA, get_node_definition
from ..util import gen_id, now
from .audit_v0_3 import audit_workflow


def _as_dict(value: Any) -> Dict[str, Any]:
    if isinstance(value, dict):
        return value
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    raise ValueError("workflow must be an object")


def _registry_status(node_type: str) -> NodeStatus:
    definition = get_node_definition(node_type)
    return definition.status if definition else NodeStatus.mock


def _schema_for(node_type: str):
    definition = get_node_definition(node_type)
    if definition:
        return definition.input_schema, definition.output_schema
    return FALLBACK_INPUT_SCHEMA, []


def _safe_status(value: Any, node_type: str) -> NodeStatus:
    if value in {"READY", "MOCK", "DISABLED"}:
        return NodeStatus(value)
    return _registry_status(node_type)


def _safe_node_type(value: Any) -> str:
    if hasattr(value, "value"):
        return str(value.value)
    return str(value or "unknown")


def _safe_category(value: Any, node_type: str) -> str:
    definition = get_node_definition(node_type)
    if definition:
        return definition.category
    if hasattr(value, "value"):
        return str(value.value)
    return str(value or "unknown")


def _normalize_v0_3_dict(raw: Dict[str, Any]) -> WorkflowV03:
    normalized = dict(raw)
    normalized["schema_version"] = "0.3.0"
    for index, node in enumerate(normalized.get("nodes", []) or []):
        if not isinstance(node, dict):
            continue
        node_type = _safe_node_type(node.get("type"))
        input_schema, output_schema = _schema_for(node_type)
        node.setdefault("input_schema", [field.model_dump(mode="json") for field in input_schema])
        node.setdefault("output_schema", [field.model_dump(mode="json") for field in output_schema])
        node.setdefault("inputs", {})
        node.setdefault("outputs", {})
        node.setdefault("params", {})
        node.setdefault("metadata", {})
        node.setdefault("ui", {})
        node.setdefault("category", _safe_category(node.get("category"), node_type))
        node.setdefault("label", node_type)
        node.setdefault("status", _registry_status(node_type).value)
        node.setdefault("id", f"node_{index + 1}")
    normalized.setdefault("layers", [])
    normalized.setdefault("modules", [])
    normalized.setdefault("edges", [])
    normalized.setdefault("metadata", {"mock": True})
    return WorkflowV03.model_validate(normalized)


def _legacy_node_to_v0_3(raw_node: Dict[str, Any], index: int) -> NodeV03:
    node_type = _safe_node_type(raw_node.get("type"))
    input_schema, output_schema = _schema_for(node_type)
    data = raw_node.get("data") if isinstance(raw_node.get("data"), dict) else {}
    position = raw_node.get("position") if isinstance(raw_node.get("position"), dict) else {}
    status = _safe_status(data.get("contract_status") or data.get("node_status") or data.get("status"), node_type)
    return NodeV03(
        id=str(raw_node.get("node_id") or raw_node.get("id") or f"node_{index + 1}"),
        type=node_type,
        label=str(raw_node.get("title_fallback") or raw_node.get("label") or node_type),
        category=_safe_category(raw_node.get("category"), node_type),
        status=status,
        input_schema=input_schema,
        inputs=dict(data),
        output_schema=output_schema,
        outputs={},
        params={},
        ui=NodeUiState(
            position={
                "x": float(position.get("x", 0) or 0),
                "y": float(position.get("y", 0) or 0),
            }
        ),
        metadata={
            "legacy_id": str(raw_node.get("node_id") or raw_node.get("id") or f"node_{index + 1}"),
            "legacy_title_key": raw_node.get("title_key"),
            "adapter": "v0.2_to_v0.3",
        },
    )


def _legacy_edge_to_v0_3(raw_edge: Dict[str, Any], index: int) -> EdgeV03:
    return EdgeV03(
        id=str(raw_edge.get("edge_id") or raw_edge.get("id") or f"edge_{index + 1}"),
        source_node_id=str(raw_edge.get("source") or raw_edge.get("source_node_id") or ""),
        source_output=str(raw_edge.get("source_port") or raw_edge.get("source_output") or "output"),
        target_node_id=str(raw_edge.get("target") or raw_edge.get("target_node_id") or ""),
        target_input=str(raw_edge.get("target_port") or raw_edge.get("target_input") or "input"),
        metadata={"adapter": "v0.2_to_v0.3"},
    )


def _legacy_layers_and_modules(nodes: List[NodeV03]) -> Tuple[List[LayerV03], List[ModuleV03]]:
    layers: List[LayerV03] = []
    modules: List[ModuleV03] = []
    assigned: Set[str] = set()

    for node in nodes:
        if node.type != "layer_container":
            continue
        layer_id = f"layer_{node.id}"
        module_id = f"module_{node.id}"
        layers.append(LayerV03(id=layer_id, name=node.label, module_ids=[module_id], node_ids=[node.id]))
        modules.append(ModuleV03(id=module_id, name=node.label, layer_id=layer_id, node_ids=[node.id]))
        assigned.add(node.id)

    unassigned = [node.id for node in nodes if node.id not in assigned]
    if unassigned:
        modules.append(ModuleV03(id="module_adapter_unassigned", name="Adapter Unassigned", node_ids=unassigned))
        if not layers:
            layers.append(
                LayerV03(
                    id="layer_adapter_default",
                    name="Adapter Default",
                    module_ids=["module_adapter_unassigned"],
                    node_ids=unassigned,
                )
            )

    return layers, modules


def normalize_workflow_v0_3(value: Any) -> WorkflowV03:
    raw = _as_dict(value)
    try:
        if raw.get("schema_version") == "0.3.0" and "id" in raw:
            return _normalize_v0_3_dict(raw)
    except ValidationError:
        raise

    nodes = [_legacy_node_to_v0_3(node, index) for index, node in enumerate(raw.get("nodes", []) or []) if isinstance(node, dict)]
    edges = [_legacy_edge_to_v0_3(edge, index) for index, edge in enumerate(raw.get("edges", []) or []) if isinstance(edge, dict)]
    layers, modules = _legacy_layers_and_modules(nodes)
    metadata = raw.get("metadata") if isinstance(raw.get("metadata"), dict) else {}
    return WorkflowV03(
        id=str(raw.get("workflow_id") or raw.get("id") or gen_id("wf")),
        name=str(raw.get("name") or "Untitled Workflow"),
        schema_version="0.3.0",
        layers=layers,
        modules=modules,
        nodes=nodes,
        edges=edges,
        metadata=WorkflowMetadataV03(
            description=metadata.get("description"),
            author=metadata.get("author"),
            tags=metadata.get("tags") if isinstance(metadata.get("tags"), list) else [],
            ui_language=metadata.get("ui_language") if metadata.get("ui_language") in {"zh", "en"} else None,
            mock=True,
        ),
    )


def build_persona_builder_v0_3(name: Optional[str] = None, ui_language: str = "zh") -> WorkflowV03:
    layers: List[LayerV03] = []
    modules: List[ModuleV03] = []
    nodes: List[NodeV03] = []
    edges: List[EdgeV03] = []

    layer_names = [
        "Source Input",
        "Identity Core",
        "Legal Permission",
        "Safety Boundary",
        "World Context",
        "Personality",
        "Memory",
        "Knowledge",
        "Relationship",
        "Behavior",
        "Capability Tools",
        "Multimodal",
        "Audit Export Deploy",
    ]
    previous_node_id: Optional[str] = None
    for index, label in enumerate(layer_names, start=1):
        node_type = "layer_container"
        input_schema, output_schema = _schema_for(node_type)
        node_id = f"layer_node_{index}"
        layer_id = f"layer_{index}"
        module_id = f"module_{index}"
        nodes.append(
            NodeV03(
                id=node_id,
                type=node_type,
                label=label,
                category="container",
                status=NodeStatus.ready,
                input_schema=input_schema,
                output_schema=output_schema,
                inputs={"layer_index": index, "module_tier": "core" if index in {1, 2, 3, 4, 6, 7, 8, 10, 13} else "plugin"},
                outputs={"layer": {"id": layer_id, "name": label}},
                ui=NodeUiState(position={"x": 0, "y": float((index - 1) * 160)}),
                metadata={"template": "persona_builder"},
            )
        )
        layers.append(LayerV03(id=layer_id, name=label, module_ids=[module_id], node_ids=[node_id]))
        modules.append(ModuleV03(id=module_id, name=label, layer_id=layer_id, node_ids=[node_id]))
        if previous_node_id:
            edges.append(
                EdgeV03(
                    id=gen_id("ed"),
                    source_node_id=previous_node_id,
                    source_output="layer",
                    target_node_id=node_id,
                    target_input="layer_index",
                )
            )
        previous_node_id = node_id

    for node_type, label, x_offset in [
        ("text_input", "Text Input", 360),
        ("identity", "Identity", 520),
        ("personality", "Personality", 680),
        ("dialogue", "Dialogue", 840),
        ("voice_profile", "Voice Profile", 1000),
        ("particle_avatar", "Particle Avatar", 1160),
        ("compile_resident", "Compile Resident", 1320),
    ]:
        input_schema, output_schema = _schema_for(node_type)
        node_id = f"node_{node_type}"
        default_inputs: Dict[str, Any] = {}
        if node_type == "text_input":
            default_inputs = {"source_text": "Synthetic resident seed text."}
        elif node_type == "identity":
            default_inputs = {"name": "Unnamed Resident", "role": "digital_resident"}
        elif node_type == "personality":
            default_inputs = {"traits": ["calm", "supportive"], "boundaries": ["synthetic persona"]}
        nodes.append(
            NodeV03(
                id=node_id,
                type=node_type,
                label=label,
                category=_safe_category(None, node_type),
                status=_registry_status(node_type),
                input_schema=input_schema,
                output_schema=output_schema,
                inputs=default_inputs,
                outputs={},
                ui=NodeUiState(position={"x": float(x_offset), "y": 0}),
                metadata={"template": "persona_builder"},
            )
        )
        modules.append(ModuleV03(id=f"module_{node_type}", name=label, layer_id="layer_13", node_ids=[node_id]))
        layers[-1].module_ids.append(f"module_{node_type}")
        layers[-1].node_ids.append(node_id)

    resident_chain = [
        ("node_text_input", "text_input", "node_identity", "name"),
        ("node_identity", "identity", "node_personality", "traits"),
        ("node_personality", "personality", "node_dialogue", "tone"),
        ("node_dialogue", "dialogue", "node_voice_profile", "voice_id"),
        ("node_voice_profile", "voice_profile", "node_particle_avatar", "preset"),
        ("node_particle_avatar", "avatar", "node_compile_resident", "metadata"),
    ]
    for source_node_id, source_output, target_node_id, target_input in resident_chain:
        edges.append(
            EdgeV03(
                id=gen_id("ed"),
                source_node_id=source_node_id,
                source_output=source_output,
                target_node_id=target_node_id,
                target_input=target_input,
            )
        )

    return WorkflowV03(
        id=gen_id("wf"),
        name=name or "Persona Builder",
        schema_version="0.3.0",
        layers=layers,
        modules=modules,
        nodes=nodes,
        edges=edges,
        metadata=WorkflowMetadataV03(
            description="13-layer persona builder trunk using v0.3 schema.",
            ui_language=ui_language if ui_language in {"zh", "en"} else "zh",
            mock=True,
        ),
    )


def _first_record(workflow: WorkflowV03, node_type: str, output_key: str) -> Dict[str, Any]:
    for node in workflow.nodes:
        if node.type != node_type:
            continue
        output = node.outputs.get(output_key)
        if isinstance(output, dict):
            return output
        return node.inputs
    return {}


def _string(value: Any, fallback: str) -> str:
    return value if isinstance(value, str) and value else fallback


def _string_list(value: Any, fallback: List[str]) -> List[str]:
    if isinstance(value, list):
        cleaned = [item for item in value if isinstance(item, str) and item]
        if cleaned:
            return cleaned
    if isinstance(value, str) and value:
        return [value]
    return fallback


def compile_resident_from_workflow(workflow: WorkflowV03) -> ResidentInstanceV03:
    identity = _first_record(workflow, "identity", "identity")
    personality = _first_record(workflow, "personality", "personality")
    dialogue = _first_record(workflow, "dialogue", "dialogue")
    voice = _first_record(workflow, "voice_profile", "voice_profile")
    avatar = _first_record(workflow, "particle_avatar", "avatar")

    resident = ResidentInstanceV03()
    resident.identity.name = _string(identity.get("name"), "Unnamed Resident")
    resident.identity.role = _string(identity.get("role"), "digital_resident")
    resident.personality.traits = _string_list(personality.get("traits"), ["calm", "supportive"])
    resident.personality.speaking_style = _string(personality.get("speaking_style"), "calm and supportive")
    resident.personality.boundaries = _string_list(personality.get("boundaries"), ["synthetic persona", "no real-human impersonation"])
    resident.dialogue.tone = _string(dialogue.get("tone"), "warm")
    resident.dialogue.formality = _string(dialogue.get("formality"), "casual")
    resident.dialogue.sample = _string(dialogue.get("sample"), "Hello, I am a synthetic resident.")
    resident.voice_profile.voice_id = _string(voice.get("voice_id"), "mock_voice")
    resident.avatar.preset = _string(avatar.get("preset"), "mock_avatar")
    resident.avatar.color = _string(avatar.get("color"), "#7aa2f7")
    resident.metadata.tags = list(workflow.metadata.tags)
    resident.metadata.mock = True
    return resident


def _topo_sort_v0_3(workflow: WorkflowV03) -> Tuple[Optional[List[str]], Set[str]]:
    outgoing: Dict[str, List[str]] = {node.id: [] for node in workflow.nodes}
    indegree: Dict[str, int] = {node.id: 0 for node in workflow.nodes}
    for edge in workflow.edges:
        if edge.source_node_id in outgoing and edge.target_node_id in indegree:
            outgoing[edge.source_node_id].append(edge.target_node_id)
            indegree[edge.target_node_id] += 1
    queue = [node_id for node_id, degree in indegree.items() if degree == 0]
    order: List[str] = []
    while queue:
        node_id = queue.pop(0)
        order.append(node_id)
        for target in outgoing[node_id]:
            indegree[target] -= 1
            if indegree[target] == 0:
                queue.append(target)
    if len(order) != len(indegree):
        return None, {node_id for node_id, degree in indegree.items() if degree > 0}
    return order, set()


def mock_run_v0_3(workflow: WorkflowV03) -> RunResult:
    started = now()
    order, _cycle_nodes = _topo_sort_v0_3(workflow)
    if order is None:
        return RunResult(workflow_id=workflow.id, status=RunStatus.error, order=[], started_at=started, finished_at=now())

    node_by_id = {node.id: node for node in workflow.nodes}
    audit = audit_workflow(workflow)
    any_warning = audit.status != "PASS"
    node_results: List[NodeRunResult] = []
    artifacts: List[Artifact] = []
    for node_id in order:
        node = node_by_id[node_id]
        output = {
            "mock": True,
            "node_id": node.id,
            "type": node.type,
            "outputs": node.outputs,
        }
        node_results.append(
            NodeRunResult(
                node_id=node.id,
                status=RunStatus.warning if node.status == NodeStatus.disabled else RunStatus.success,
                output=output,
                logs=[RunLog(level="info", message=f"v0.3 mock executed {node.type}")],
                duration_ms=5,
            )
        )
        if node.type in {"output", "export", "compile_resident"}:
            artifacts.append(
                Artifact(
                    artifact_id=gen_id("ar"),
                    node_id=node.id,
                    kind=node.type,
                    name=node.label,
                    preview={"mock": True, "from_node_id": node.id},
                )
            )
    return RunResult(
        workflow_id=workflow.id,
        status=RunStatus.warning if any_warning else RunStatus.success,
        order=order,
        node_results=node_results,
        artifacts=artifacts,
        started_at=started,
        finished_at=now(),
    )


def export_preview_v0_3(workflow: WorkflowV03, export_kind: str) -> ExportPreview:
    if export_kind == "resident":
        content = compile_resident_from_workflow(workflow).model_dump(mode="json")
    else:
        content = workflow.model_dump(mode="json")
    audit = audit_workflow(workflow)
    warnings = [f"[{finding.status.value}] {finding.code}: {finding.message}" for finding in audit.findings]
    return ExportPreview(export_kind="workflow_json" if export_kind == "workflow_json" else "persona", content=content, warnings=warnings)
