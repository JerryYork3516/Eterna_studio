"""Rule-based node registry for Schema Contract v0.3.

Registry entries describe the API/UI contract for node types. They are not
runtime implementations. Optional mock_executor values are string identifiers
only, so registry JSON stays serializable and reference-free.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from ..models.v0_3 import (
    NodeInputField,
    NodeInputOption,
    NodeInputType,
    NodeRegistryEntry,
    NodeStatus,
    OutputSchemaField,
)

DEFAULT_AUDIT_RULES = [
    "schema_compliance",
    "inputs_match_schema",
    "outputs_are_dto",
    "no_circular_reference",
    "no_stringified_json",
    "status_allowed",
    "safety_rule_scan",
]


def input_field(
    key: str,
    field_type: NodeInputType,
    label: str,
    *,
    required: bool = False,
    default=None,
    options: Optional[List[NodeInputOption]] = None,
    min: Optional[float] = None,
    max: Optional[float] = None,
    step: Optional[float] = None,
    accept: Optional[List[str]] = None,
    multiple: bool = False,
) -> NodeInputField:
    return NodeInputField(
        key=key,
        type=field_type,
        label=label,
        required=required,
        default=default,
        options=options or [],
        min=min,
        max=max,
        step=step,
        accept=accept,
        multiple=multiple,
    )


def output_field(key: str, field_type: str, description: str = "", required: bool = False) -> OutputSchemaField:
    return OutputSchemaField(key=key, type=field_type, description=description, required=required)


def select_options(*values: str) -> List[NodeInputOption]:
    return [NodeInputOption(value=value, label=value.replace("_", " ").title()) for value in values]


def registry_entry(
    node_type: str,
    category: str,
    display_name: str,
    description: str,
    *,
    input_schema: Optional[List[NodeInputField]] = None,
    output_schema: Optional[List[OutputSchemaField]] = None,
    status: NodeStatus = NodeStatus.mock,
    mock_executor: Optional[str] = None,
    audit_rules: Optional[List[str]] = None,
) -> NodeRegistryEntry:
    return NodeRegistryEntry(
        type=node_type,
        category=category,
        display_name=display_name,
        description=description,
        input_schema=input_schema or [],
        output_schema=output_schema or [],
        status=status,
        mock_executor=mock_executor,
        audit_rules=audit_rules or DEFAULT_AUDIT_RULES,
    )


FALLBACK_INPUT_SCHEMA = [
    input_field(
        "source_text",
        NodeInputType.textarea,
        "Source text",
        required=False,
    )
]

NODE_REGISTRY: Dict[str, NodeRegistryEntry] = {
    "layer_container": registry_entry(
        "layer_container",
        "container",
        "Layer Container",
        "v0.3 layer DTO boundary node.",
        input_schema=[
            input_field("layer_index", NodeInputType.number, "Layer index", required=True, min=1, step=1),
            input_field("module_tier", NodeInputType.select, "Module tier", options=select_options("core", "plugin", "later")),
        ],
        output_schema=[output_field("layer", "object", "Layer DTO.", True)],
        status=NodeStatus.ready,
        mock_executor="layer_container_mock",
    ),
    "input": registry_entry(
        "input",
        "source",
        "Input",
        "Legacy-compatible generic input node, normalized to v0.3 DTO.",
        input_schema=[input_field("source_text", NodeInputType.textarea, "Source text")],
        output_schema=[output_field("input", "object", "Generic input DTO.", True)],
        status=NodeStatus.ready,
        mock_executor="input_mock",
    ),
    "transform": registry_entry(
        "transform",
        "processing",
        "Transform",
        "DTO transform placeholder.",
        input_schema=[input_field("params", NodeInputType.key_value, "Params")],
        output_schema=[output_field("transform", "object", "Transform DTO.", True)],
        status=NodeStatus.ready,
        mock_executor="transform_mock",
    ),
    "model": registry_entry(
        "model",
        "model",
        "Model",
        "Mock model descriptor. No model runtime is called.",
        input_schema=[input_field("model", NodeInputType.text, "Model", default="mock-model")],
        output_schema=[output_field("model", "object", "Model DTO.", True)],
        status=NodeStatus.mock,
        mock_executor="model_mock",
    ),
    "agent": registry_entry(
        "agent",
        "control",
        "Agent",
        "Mock agent descriptor.",
        input_schema=[input_field("instructions", NodeInputType.textarea, "Instructions")],
        output_schema=[output_field("agent", "object", "Agent DTO.", True)],
        status=NodeStatus.mock,
        mock_executor="agent_mock",
    ),
    "review": registry_entry(
        "review",
        "control",
        "Review",
        "Rule-based review placeholder.",
        input_schema=[input_field("rules", NodeInputType.tags, "Rules")],
        output_schema=[output_field("review", "object", "Review DTO.", True)],
        status=NodeStatus.ready,
        mock_executor="review_mock",
    ),
    "text_input": registry_entry(
        "text_input",
        "source",
        "Text Input",
        "User-provided source text.",
        input_schema=[
            input_field("source_text", NodeInputType.textarea, "Source text", required=True),
            input_field("tags", NodeInputType.tags, "Tags"),
        ],
        output_schema=[output_field("text_input", "object", "Normalized text input DTO.", True)],
        status=NodeStatus.ready,
        mock_executor="text_input_mock",
    ),
    "identity": registry_entry(
        "identity",
        "persona",
        "Identity",
        "Resident identity fields.",
        input_schema=[
            input_field("name", NodeInputType.text, "Name", required=True),
            input_field("role", NodeInputType.text, "Role", default="digital_resident"),
        ],
        output_schema=[output_field("identity", "object", "Resident identity DTO.", True)],
        status=NodeStatus.ready,
        mock_executor="identity_mock",
    ),
    "personality": registry_entry(
        "personality",
        "persona",
        "Personality",
        "Resident personality traits and boundaries.",
        input_schema=[
            input_field("traits", NodeInputType.tags, "Traits", required=True),
            input_field("warmth", NodeInputType.slider, "Warmth", default=0.7, min=0, max=1, step=0.1),
            input_field("boundaries", NodeInputType.tags, "Boundaries"),
        ],
        output_schema=[output_field("personality", "object", "Resident personality DTO.", True)],
        status=NodeStatus.ready,
        mock_executor="personality_mock",
    ),
    "dialogue": registry_entry(
        "dialogue",
        "persona",
        "Dialogue Style",
        "Dialogue tone and sample phrasing.",
        input_schema=[
            input_field("tone", NodeInputType.select, "Tone", options=select_options("warm", "calm", "formal")),
            input_field("sample", NodeInputType.textarea, "Sample dialogue"),
        ],
        output_schema=[output_field("dialogue", "object", "Dialogue DTO.", True)],
        status=NodeStatus.mock,
        mock_executor="dialogue_mock",
    ),
    "voice_profile": registry_entry(
        "voice_profile",
        "media",
        "Voice Profile",
        "Mock voice profile settings. No TTS runtime is called.",
        input_schema=[
            input_field("voice_id", NodeInputType.select, "Voice", options=select_options("neutral", "female", "male")),
            input_field("speed", NodeInputType.slider, "Speed", default=1, min=0.5, max=1.5, step=0.1),
        ],
        output_schema=[output_field("voice_profile", "object", "Voice profile DTO.", True)],
        status=NodeStatus.mock,
        mock_executor="voice_profile_mock",
    ),
    "particle_avatar": registry_entry(
        "particle_avatar",
        "media",
        "Particle Avatar",
        "Mock avatar visual parameters. No AR runtime is called.",
        input_schema=[
            input_field("preset", NodeInputType.select, "Preset", options=select_options("nebula", "aurora", "minimal")),
            input_field("color", NodeInputType.color, "Color", default="#7aa2f7"),
            input_field("density", NodeInputType.slider, "Density", default=0.6, min=0, max=1, step=0.1),
        ],
        output_schema=[output_field("avatar", "object", "Avatar DTO.", True)],
        status=NodeStatus.mock,
        mock_executor="particle_avatar_mock",
    ),
    "memory": registry_entry(
        "memory",
        "memory",
        "Memory",
        "Mock memory settings.",
        input_schema=[
            input_field("capacity", NodeInputType.number, "Capacity", default=128, min=0, step=1),
            input_field("strategy", NodeInputType.select, "Strategy", options=select_options("rolling", "pinned")),
        ],
        output_schema=[output_field("memory", "object", "Memory DTO.", True)],
        status=NodeStatus.mock,
        mock_executor="memory_mock",
    ),
    "knowledge": registry_entry(
        "knowledge",
        "memory",
        "Knowledge",
        "Mock knowledge source descriptor.",
        input_schema=[
            input_field("source", NodeInputType.text, "Source"),
            input_field("documents", NodeInputType.file, "Documents", accept=[".txt", ".md", ".json"], multiple=True),
        ],
        output_schema=[output_field("knowledge", "object", "Knowledge DTO.", True)],
        status=NodeStatus.mock,
        mock_executor="knowledge_mock",
    ),
    "model_adapter": registry_entry(
        "model_adapter",
        "model",
        "Model Adapter",
        "Mock model adapter descriptor. No model call is made.",
        input_schema=[
            input_field("provider", NodeInputType.select, "Provider", options=select_options("mock")),
            input_field("model", NodeInputType.text, "Model", default="mock-model"),
            input_field("params", NodeInputType.key_value, "Params"),
        ],
        output_schema=[output_field("model_adapter", "object", "Model adapter DTO.", True)],
        status=NodeStatus.mock,
        mock_executor="model_adapter_mock",
    ),
    "llm_adapter": registry_entry(
        "llm_adapter",
        "model",
        "LLM Adapter",
        "Disabled real LLM adapter placeholder.",
        input_schema=[
            input_field("provider", NodeInputType.select, "Provider", options=select_options("mock")),
            input_field("model", NodeInputType.text, "Model", default="mock-llm"),
        ],
        output_schema=[output_field("llm_adapter", "object", "LLM adapter DTO.", True)],
        status=NodeStatus.mock,
        mock_executor="llm_adapter_mock",
    ),
    "tts_adapter": registry_entry(
        "tts_adapter",
        "media",
        "TTS Adapter",
        "Disabled real TTS placeholder.",
        input_schema=[input_field("voice", NodeInputType.text, "Voice", default="mock_voice")],
        output_schema=[output_field("tts_adapter", "object", "TTS adapter DTO.", True)],
        status=NodeStatus.mock,
        mock_executor="tts_adapter_mock",
    ),
    "tools": registry_entry(
        "tools",
        "tools",
        "Tools",
        "Disabled tool integration placeholder.",
        input_schema=[input_field("enabled", NodeInputType.boolean, "Enabled", default=False)],
        output_schema=[output_field("tools", "object", "Tools DTO.", True)],
        status=NodeStatus.disabled,
        mock_executor=None,
    ),
    "compile_resident": registry_entry(
        "compile_resident",
        "sink",
        "Compile Resident",
        "Combines resident DTO fields into a resident_instance contract.",
        input_schema=[input_field("metadata", NodeInputType.json, "Metadata")],
        output_schema=[output_field("resident_instance", "object", "Resident instance DTO.", True)],
        status=NodeStatus.mock,
        mock_executor="compile_resident_mock",
    ),
    "output": registry_entry(
        "output",
        "sink",
        "Output",
        "Final DTO output node.",
        input_schema=[],
        output_schema=[output_field("output", "object", "Final output DTO.", True)],
        status=NodeStatus.ready,
        mock_executor="output_mock",
    ),
    "export": registry_entry(
        "export",
        "sink",
        "Export",
        "Final export DTO node.",
        input_schema=[input_field("format", NodeInputType.select, "Format", options=select_options("workflow_json", "persona"))],
        output_schema=[output_field("export", "object", "Export DTO.", True)],
        status=NodeStatus.ready,
        mock_executor="export_mock",
    ),
    "module": registry_entry(
        "module",
        "module",
        "Module",
        "Legacy-compatible module placeholder.",
        input_schema=[input_field("module_id", NodeInputType.text, "Module id")],
        output_schema=[output_field("module", "object", "Module DTO.", True)],
        status=NodeStatus.ready,
        mock_executor="module_mock",
    ),
    "text": registry_entry(
        "text",
        "core",
        "Text",
        "Legacy-compatible text placeholder.",
        input_schema=[input_field("text", NodeInputType.textarea, "Text")],
        output_schema=[output_field("text", "object", "Text DTO.", True)],
        status=NodeStatus.ready,
        mock_executor="text_mock",
    ),
    "reasoning": registry_entry(
        "reasoning",
        "core",
        "Reasoning",
        "Mock reasoning descriptor. No LLM runtime is called.",
        input_schema=[input_field("prompt", NodeInputType.textarea, "Prompt")],
        output_schema=[output_field("reasoning", "object", "Reasoning DTO.", True)],
        status=NodeStatus.mock,
        mock_executor="reasoning_mock",
    ),
    "api_connector": registry_entry(
        "api_connector",
        "integration",
        "API Connector",
        "Mock API connector descriptor. No network call is made.",
        input_schema=[
            input_field("endpoint", NodeInputType.text, "Endpoint"),
            input_field("method", NodeInputType.select, "Method", options=select_options("GET", "POST")),
        ],
        output_schema=[output_field("api_connector", "object", "API connector DTO.", True)],
        status=NodeStatus.mock,
        mock_executor="api_connector_mock",
    ),
    "model_loader": registry_entry(
        "model_loader",
        "model",
        "Model Loader",
        "Mock model loader descriptor.",
        input_schema=[input_field("model", NodeInputType.text, "Model")],
        output_schema=[output_field("model_loader", "object", "Model loader DTO.", True)],
        status=NodeStatus.mock,
        mock_executor="model_loader_mock",
    ),
    "local_model": registry_entry(
        "local_model",
        "model",
        "Local Model",
        "Mock local model descriptor. No model file is loaded.",
        input_schema=[input_field("path", NodeInputType.text, "Path")],
        output_schema=[output_field("local_model", "object", "Local model DTO.", True)],
        status=NodeStatus.mock,
        mock_executor="local_model_mock",
    ),
    "ar_particle": registry_entry(
        "ar_particle",
        "media",
        "AR Particle",
        "Mock AR particle descriptor. No AR runtime is called.",
        input_schema=[input_field("preset", NodeInputType.select, "Preset", options=select_options("aurora", "nebula"))],
        output_schema=[output_field("ar_particle", "object", "AR particle DTO.", True)],
        status=NodeStatus.mock,
        mock_executor="ar_particle_mock",
    ),
    "particle_physics": registry_entry(
        "particle_physics",
        "media",
        "Particle Physics",
        "Mock particle physics descriptor.",
        input_schema=[
            input_field("gravity", NodeInputType.slider, "Gravity", default=0.2, min=0, max=1, step=0.1),
            input_field("turbulence", NodeInputType.slider, "Turbulence", default=0.5, min=0, max=1, step=0.1),
        ],
        output_schema=[output_field("particle_physics", "object", "Particle physics DTO.", True)],
        status=NodeStatus.mock,
        mock_executor="particle_physics_mock",
    ),
    "avatar_preview": registry_entry(
        "avatar_preview",
        "media",
        "Avatar Preview",
        "Mock avatar preview DTO.",
        input_schema=[input_field("enabled", NodeInputType.boolean, "Enabled", default=True)],
        output_schema=[output_field("avatar_preview", "object", "Avatar preview DTO.", True)],
        status=NodeStatus.mock,
        mock_executor="avatar_preview_mock",
    ),
    "runtime_mock": registry_entry(
        "runtime_mock",
        "runtime",
        "Runtime Mock",
        "Disabled runtime placeholder.",
        input_schema=[input_field("enabled", NodeInputType.boolean, "Enabled", default=False)],
        output_schema=[output_field("runtime_mock", "object", "Runtime mock DTO.", True)],
        status=NodeStatus.disabled,
        mock_executor=None,
    ),
    "export_package": registry_entry(
        "export_package",
        "sink",
        "Export Package",
        "Mock export package DTO.",
        input_schema=[input_field("format", NodeInputType.select, "Format", options=select_options("zip", "json"))],
        output_schema=[output_field("export_package", "object", "Export package DTO.", True)],
        status=NodeStatus.mock,
        mock_executor="export_package_mock",
    ),
}


def get_node_definition(node_type: str) -> Optional[NodeRegistryEntry]:
    return NODE_REGISTRY.get(node_type)
