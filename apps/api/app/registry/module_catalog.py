"""Built-in Module catalog for Protocol v0.4.

Modules are capability containers bound to an existing 13-layer layer_id. They
do not execute and never write into resident_instance. Future capabilities and
planned placeholders are registered here only — no real logic this stage.
"""

from __future__ import annotations

from typing import Dict, List

from ..models.v0_4 import (
    CANONICAL_LAYER_IDS,
    ModuleV04,
    ProtocolStatus,
    RiskLevel,
    ScreenUiAnchorModuleV04,
    SlotType,
)

IDENTITY_CORE_NODE_TYPES = ("field_input", "structure_normalize", "validation", "update_rule", "module_output")


def _module(
    module_id: str,
    module_type: str,
    module_name: str,
    layer_id: str,
    *,
    status: ProtocolStatus = ProtocolStatus.mock,
    slot_type: SlotType | None = None,
    risk_level: RiskLevel = RiskLevel.none,
    category: str = "",
    is_placeholder: bool = True,
    audit_required: bool = False,
    human_confirm_required: bool = False,
    color_status: str = "gray",
    tags: list[str] | None = None,
    module_graph: Dict[str, object] | None = None,
    input_schema: list[object] | None = None,
    output_schema: list[object] | None = None,
    slot_bindings: list[dict[str, object]] | None = None,
    context_bindings: list[dict[str, object]] | None = None,
    runtime_mapping: Dict[str, object] | None = None,
    dr_mapping: Dict[str, object] | None = None,
    ui_config: Dict[str, object] | None = None,
    i18n_keys: Dict[str, str] | None = None,
    inputs: Dict[str, object] | None = None,
    outputs: Dict[str, object] | None = None,
    config: Dict[str, object] | None = None,
    mock_only: bool = False,
    no_execution: bool = False,
    slot_declarations: list[str] | None = None,
    screen_config: Dict[str, object] | None = None,
    dr_write_keys: list[str] | None = None,
) -> ModuleV04:
    return ModuleV04(
        module_id=module_id,
        module_type=module_type,
        module_name=module_name,
        module_version="0.1.0",
        layer_id=layer_id,
        module_graph=module_graph or {},
        input_schema=input_schema or [],
        output_schema=output_schema or [],
        slot_bindings=slot_bindings or [],
        context_bindings=context_bindings or [],
        runtime_mapping=runtime_mapping or {},
        dr_mapping=dr_mapping or {},
        ui_config=ui_config or {},
        i18n_keys=i18n_keys or {},
        inputs=inputs or {},
        outputs=outputs or {},
        config=config or {},
        permissions=[],
        risk_level=risk_level,
        status=status,
        slot_type=slot_type,
        audit_required=audit_required,
        human_confirm_required=human_confirm_required,
        runtime_enabled=False,
        is_placeholder=is_placeholder,
        category=category,
        tags=tags or [],
        color_status=color_status,
        mock_only=mock_only,
        no_execution=no_execution,
        slot_declarations=slot_declarations or [],
        screen_config=screen_config or {},
        dr_write_keys=dr_write_keys or [],
    )


SCREEN_UI_ANCHOR_MODULE = ScreenUiAnchorModuleV04()

IDENTITY_CORE_MODULE_SPECS: List[Dict[str, object]] = [
    {
        "module_id": "module_basic_identity",
        "module_type": "identity_basic",
        "module_name": "Basic Identity",
        "output": "basic_identity",
        "fields": [
            ("resident_id", "locked_core", "developer_only", True),
            ("codename", "locked_core", "developer_only", True),
            ("name", "locked_core", "developer_only", True),
            ("primary_language", "versioned_core", "user_editable", True),
        ],
    },
    {
        "module_id": "module_growth_background",
        "module_type": "identity_growth_background",
        "module_name": "Growth Background",
        "output": "growth_background",
        "fields": [
            ("origin_region", "versioned_core", "user_editable", True),
            ("cultural_context", "versioned_core", "user_editable", True),
            ("growth_notes", "versioned_core", "user_editable", True),
        ],
    },
    {
        "module_id": "module_career_identity",
        "module_type": "identity_career",
        "module_name": "Career Identity",
        "output": "career_identity",
        "fields": [
            ("career_domain", "versioned_core", "user_editable", True),
            ("role_identity", "versioned_core", "user_editable", True),
            ("expertise_summary", "versioned_core", "user_editable", True),
        ],
    },
    {
        "module_id": "module_existence_mode",
        "module_type": "identity_existence_mode",
        "module_name": "Existence Mode",
        "output": "existence_mode",
        "fields": [
            ("existence_mode", "locked_core", "developer_only", True),
            ("local_only", "config", "developer_only", True),
            ("cloud_enabled", "config", "developer_only", True),
        ],
    },
    {
        "module_id": "module_identity_anchor",
        "module_type": "identity_anchor",
        "module_name": "Identity Anchor",
        "output": "identity_anchor",
        "fields": [
            ("identity_anchor", "locked_core", "developer_only", True),
            ("locked_core_fields", "locked_core", "developer_only", True),
            ("versioned_core_fields", "versioned_core", "developer_only", True),
        ],
    },
]


def _identity_field_default(field_id: str) -> object:
    if field_id in {"locked_core_fields", "versioned_core_fields"}:
        return []
    if field_id in {"local_only", "cloud_enabled"}:
        return False
    return ""


def _identity_node_id(output_key: str, node_type: str) -> str:
    suffix = {
        "field_input": "field_input",
        "structure_normalize": "normalize",
        "validation": "validation",
        "update_rule": "update_rule",
        "module_output": "output",
    }[node_type]
    return f"{output_key}_{suffix}"


def _identity_core_module(spec: Dict[str, object]) -> ModuleV04:
    module_id = str(spec["module_id"])
    output_key = str(spec["output"])
    fields = [
        {
            "field_id": field_id,
            "value": _identity_field_default(str(field_id)),
            "required": True,
            "edit_scope": edit_scope,
            "update_level": update_level,
            "requires_recompile": requires_recompile,
            "i18n_keys": {
                "label": f"field.identity.{field_id}.label",
                "placeholder": f"field.identity.{field_id}.placeholder",
                "help": f"field.identity.{field_id}.help",
            },
        }
        for field_id, update_level, edit_scope, requires_recompile in spec["fields"]  # type: ignore[misc]
    ]
    field_input_node_id = _identity_node_id(output_key, "field_input")
    normalize_node_id = _identity_node_id(output_key, "structure_normalize")
    validation_node_id = _identity_node_id(output_key, "validation")
    update_rule_node_id = _identity_node_id(output_key, "update_rule")
    field_registry = [
        {
            **{key: value for key, value in field.items() if key != "value"},
            "owner_node_id": field_input_node_id,
        }
        for field in fields
    ]
    update_rules = [
        {
            "field_id": field["field_id"],
            "edit_scope": field["edit_scope"],
            "update_level": field["update_level"],
            "requires_recompile": field["requires_recompile"],
        }
        for field in fields
    ]
    module_output = {
        "output_key": output_key,
        "fields": {str(field["field_id"]): field["value"] for field in fields},
        "source_node": field_input_node_id,
        "validation_node": validation_node_id,
        "update_rule_node": update_rule_node_id,
        "compile_time_only": True,
    }
    validation_rules = ["required_fields_present", "field_i18n_keys_present"]
    if module_id == "module_identity_anchor":
        validation_rules.append("identity_consistency_validation")
    update_rule_names = ["field_update_policy"]
    if module_id == "module_identity_anchor":
        update_rule_names.append("identity_lock_rule")
    node_params = {
        "field_input": {"fields": fields},
        "structure_normalize": {
            "input": field_input_node_id,
            "normalize_rules": ["preserve_field_ids", "preserve_empty_defaults"],
        },
        "validation": {
            "input": normalize_node_id,
            "required_fields": [str(field["field_id"]) for field in fields if field.get("required")],
            "validation_rules": validation_rules,
        },
        "update_rule": {
            "input": validation_node_id,
            "update_rules": update_rules,
            "rule_names": update_rule_names,
        },
        "module_output": {
            "input": update_rule_node_id,
            "output_key": output_key,
            "output_schema": {"type": "object", "required": True},
        },
    }
    nodes = []
    for node_type in IDENTITY_CORE_NODE_TYPES:
        node_id = _identity_node_id(output_key, node_type)
        nodes.append(
            {
                "node_id": node_id,
                "node_type": node_type,
                "module_id": module_id,
                "layer_id": "layer_1",
                "params": node_params[node_type],
                "i18n_keys": {
                    "name": f"module.{module_id}.node.{node_id}.name",
                    "description": f"module.{module_id}.node.{node_id}.description",
                    "type_name": f"node.type.{node_type}",
                },
                "outputs": {output_key: module_output, "module_output": output_key} if node_type == "module_output" else {},
                "metadata": {"compile_time_only": True, "runtime_enabled": False, "no_execution": True},
            }
        )
    return _module(
        module_id,
        str(spec["module_type"]),
        str(spec["module_name"]),
        "layer_1",
        status=ProtocolStatus.core,
        category="identity",
        is_placeholder=False,
        audit_required=True,
        color_status="green",
        tags=["identity", "stage7_4", "core"],
        module_graph={
            "shell_version": "module_shell_v1",
            "nodes": nodes,
            "output_key": output_key,
            "compile_time_only": True,
        },
        output_schema=[{"key": output_key, "type": "object", "required": True, "description": f"module.{module_id}.output"}],
        ui_config={"shell_version": "module_shell_v1", "classification": "core"},
        i18n_keys={
            "display_name": f"module.{module_id}",
            "description": f"module.{module_id}.description",
            "output": f"module.{module_id}.output",
        },
        outputs={output_key: module_output, "module_output": output_key},
        config={
            "shell_version": "module_shell_v1",
            "module_class": "core",
            "field_registry": field_registry,
            "edit_scope": "developer_only",
            "update_level": "versioned_core",
            "requires_recompile": True,
            "compile_time_only": True,
        },
        mock_only=True,
        no_execution=True,
        dr_write_keys=[f"payload.graph_snapshot.layer_outputs.layer_1.{output_key}"],
    )


MODULE_CATALOG: List[ModuleV04] = [
    # L1 Identity Core
    *[_identity_core_module(spec) for spec in IDENTITY_CORE_MODULE_SPECS],

    # L2 Personality
    _module("personality_traits", "personality", "Personality Traits", "layer_2", status=ProtocolStatus.ready, category="persona", is_placeholder=True, color_status="green"),
    _module("expression_style", "personality", "Expression Style", "layer_2", status=ProtocolStatus.ready, category="persona", is_placeholder=True, color_status="green"),
    _module("emotion_pattern", "personality", "Emotion Pattern", "layer_2", status=ProtocolStatus.ready, category="persona", is_placeholder=True, color_status="green"),
    _module("personality_llm_slot", "personality_slot", "Personality LLM Slot", "layer_2", status=ProtocolStatus.ready, slot_type=SlotType.llm, category="persona", is_placeholder=True, color_status="green"),
    _module("dialogue_language_style", "language_style", "Dialogue Language Style", "layer_2", status=ProtocolStatus.ready, category="persona", is_placeholder=True, color_status="green"),
    _module("values_profile", "value_model", "Values Profile", "layer_2", status=ProtocolStatus.mock, category="persona", color_status="amber"),
    _module("behavior_style_mapper", "style_mapper", "Behavior Style Mapper", "layer_2", status=ProtocolStatus.mock, category="persona", color_status="amber"),

    # L3 Safety Boundary
    _module("content_safety", "safety", "Content Safety", "layer_3", status=ProtocolStatus.ready, category="safety", is_placeholder=True, risk_level=RiskLevel.high, audit_required=True, color_status="green"),
    _module("behavior_boundary", "safety", "Behavior Boundary", "layer_3", status=ProtocolStatus.ready, category="safety", is_placeholder=True, risk_level=RiskLevel.high, audit_required=True, color_status="green"),
    _module("privacy_protection", "safety", "Privacy Protection", "layer_3", status=ProtocolStatus.ready, category="safety", is_placeholder=True, risk_level=RiskLevel.high, audit_required=True, color_status="green"),
    _module("ethics_constraint", "safety", "Ethics Constraint", "layer_3", status=ProtocolStatus.ready, category="safety", is_placeholder=True, risk_level=RiskLevel.high, audit_required=True, color_status="green"),
    _module("risk_control", "safety", "Risk Control", "layer_3", status=ProtocolStatus.ready, category="safety", is_placeholder=True, risk_level=RiskLevel.high, audit_required=True, color_status="green"),
    _module("safety_audit_slot", "safety_slot", "Safety Audit Slot", "layer_3", status=ProtocolStatus.ready, slot_type=SlotType.tool, category="safety", is_placeholder=True, risk_level=RiskLevel.high, audit_required=True, color_status="green"),
    _module("policy_guard_slot", "safety_slot", "Policy Guard Slot", "layer_3", status=ProtocolStatus.ready, slot_type=SlotType.tool, category="safety", is_placeholder=True, risk_level=RiskLevel.high, audit_required=True, color_status="green"),
    _module("forbidden_topics", "safety", "Forbidden Topics", "layer_3", status=ProtocolStatus.ready, category="safety", is_placeholder=True, risk_level=RiskLevel.high, audit_required=True, color_status="green"),
    _module("safety_boundary_profile", "safety_profile", "Safety Boundary Profile", "layer_3", status=ProtocolStatus.mock, category="safety", risk_level=RiskLevel.medium, color_status="amber"),

    # L4 Legal Permission
    _module("clone_restriction", "permission", "Clone Restriction", "layer_4", status=ProtocolStatus.ready, category="governance", is_placeholder=True, risk_level=RiskLevel.medium, audit_required=True, color_status="green"),
    _module("compliance_requirement", "permission", "Compliance Requirement", "layer_4", status=ProtocolStatus.ready, category="governance", is_placeholder=True, risk_level=RiskLevel.medium, audit_required=True, color_status="green"),
    _module("ownership_record", "permission_record", "Ownership Record", "layer_4", status=ProtocolStatus.mock, category="governance", risk_level=RiskLevel.medium, color_status="amber"),
    _module("permission_scope", "permission_record", "Permission Scope", "layer_4", status=ProtocolStatus.mock, category="governance", risk_level=RiskLevel.medium, color_status="amber"),
    _module("commercial_usage_right", "permission_record", "Commercial Usage Right", "layer_4", status=ProtocolStatus.mock, category="governance", risk_level=RiskLevel.medium, color_status="amber"),
    _module("consent_record_slot", "permission_slot", "Consent Record Slot", "layer_4", status=ProtocolStatus.mock, slot_type=SlotType.tool, category="governance", risk_level=RiskLevel.medium, color_status="amber"),
    _module("license_policy_slot", "permission_slot", "License Policy Slot", "layer_4", status=ProtocolStatus.mock, slot_type=SlotType.tool, category="governance", risk_level=RiskLevel.medium, color_status="amber"),
    _module("emergency_contact", "permission_future", "Emergency Contact", "layer_4", status=ProtocolStatus.later, category="governance", risk_level=RiskLevel.high, audit_required=True, human_confirm_required=True, color_status="gray"),

    # L5 Memory
    _module("event_memory", "memory", "Event Memory", "layer_5", status=ProtocolStatus.ready, category="memory", slot_type=SlotType.memory, is_placeholder=True, color_status="green"),
    _module("relationship_memory", "memory", "Relationship Memory", "layer_5", status=ProtocolStatus.ready, category="memory", slot_type=SlotType.memory, is_placeholder=True, color_status="green"),
    _module("memory_access_control", "memory", "Memory Access Control", "layer_5", status=ProtocolStatus.ready, category="memory", is_placeholder=True, color_status="green"),
    _module("short_term_memory_slot", "memory_slot", "Short Term Memory Slot", "layer_5", status=ProtocolStatus.ready, slot_type=SlotType.memory, category="memory", is_placeholder=True, color_status="green"),
    _module("long_term_memory_slot", "memory_slot", "Long Term Memory Slot", "layer_5", status=ProtocolStatus.ready, slot_type=SlotType.memory, category="memory", is_placeholder=True, color_status="green"),
    _module("vector_db_slot", "memory_slot", "Vector DB Slot", "layer_5", status=ProtocolStatus.ready, slot_type=SlotType.memory, category="memory", is_placeholder=True, color_status="green"),
    _module("memory_recall_slot", "memory_slot", "Memory Recall Slot", "layer_5", status=ProtocolStatus.ready, slot_type=SlotType.memory, category="memory", is_placeholder=True, color_status="green"),
    _module("memory_provider_router", "memory_router", "Memory Provider Router", "layer_5", status=ProtocolStatus.ready, slot_type=SlotType.memory, category="memory", is_placeholder=True, color_status="green"),
    _module("preference_memory", "memory", "Preference Memory", "layer_5", status=ProtocolStatus.mock, category="memory", slot_type=SlotType.memory, color_status="amber"),
    _module("self_memory", "memory", "Self Memory", "layer_5", status=ProtocolStatus.mock, category="memory", slot_type=SlotType.memory, color_status="amber"),
    _module("knowledge_memory", "memory", "Knowledge Memory", "layer_5", status=ProtocolStatus.mock, category="memory", slot_type=SlotType.memory, color_status="amber"),
    _module("memory_update_slot", "memory_slot", "Memory Update Slot", "layer_5", status=ProtocolStatus.mock, slot_type=SlotType.memory, category="memory", color_status="amber"),

    # L6 Knowledge
    _module("rag_slot", "knowledge_slot", "RAG Slot", "layer_6", status=ProtocolStatus.ready, slot_type=SlotType.llm, category="knowledge", is_placeholder=True, color_status="green"),
    _module("general_knowledge", "knowledge", "General Knowledge", "layer_6", status=ProtocolStatus.mock, category="knowledge", color_status="amber"),
    _module("professional_knowledge", "knowledge", "Professional Knowledge", "layer_6", status=ProtocolStatus.mock, category="knowledge", color_status="amber"),
    _module("private_knowledge", "knowledge", "Private Knowledge", "layer_6", status=ProtocolStatus.mock, category="knowledge", color_status="amber"),
    _module("knowledge_update", "knowledge", "Knowledge Update", "layer_6", status=ProtocolStatus.mock, category="knowledge", color_status="amber"),
    _module("knowledge_base_slot", "knowledge_slot", "Knowledge Base Slot", "layer_6", status=ProtocolStatus.mock, slot_type=SlotType.llm, category="knowledge", color_status="amber"),
    _module("realtime_information_source", "knowledge_source", "Realtime Information Source", "layer_6", status=ProtocolStatus.later, category="knowledge", color_status="gray"),
    _module("web_search_slot", "knowledge_slot", "Web Search Slot", "layer_6", status=ProtocolStatus.later, slot_type=SlotType.tool, category="knowledge", color_status="gray"),

    # L7 World / Context
    _module("world_setting", "world", "World Setting", "layer_7", status=ProtocolStatus.mock, category="context", color_status="amber"),
    _module("timeline_context", "world", "Timeline Context", "layer_7", status=ProtocolStatus.mock, category="context", color_status="amber"),
    _module("environment_setting", "world", "Environment Setting", "layer_7", status=ProtocolStatus.mock, category="context", color_status="amber"),
    _module("social_rules", "world", "Social Rules", "layer_7", status=ProtocolStatus.mock, category="context", color_status="amber"),
    _module("realtime_environment", "world", "Realtime Environment", "layer_7", status=ProtocolStatus.later, category="context", color_status="gray"),
    _module("spatial_context_slot", "world_slot", "Spatial Context Slot", "layer_7", status=ProtocolStatus.later, slot_type=SlotType.tool, category="context", color_status="gray"),
    _module("real_world_sensor_slot", "world_slot", "Real World Sensor Slot", "layer_7", status=ProtocolStatus.later, slot_type=SlotType.tool, category="context", color_status="gray"),

    # L8 Behavior
    _module("language_habit", "behavior", "Language Habit", "layer_8", status=ProtocolStatus.ready, category="behavior", is_placeholder=True, color_status="green"),
    _module("decision_pattern", "behavior", "Decision Pattern", "layer_8", status=ProtocolStatus.ready, category="behavior", is_placeholder=True, color_status="green"),
    _module("emotion_reaction", "behavior", "Emotion Reaction", "layer_8", status=ProtocolStatus.ready, category="behavior", is_placeholder=True, color_status="green"),
    _module("interaction_strategy", "behavior", "Interaction Strategy", "layer_8", status=ProtocolStatus.ready, category="behavior", is_placeholder=True, color_status="green"),
    _module("emotion_mapper", "behavior", "Emotion Mapper", "layer_8", status=ProtocolStatus.ready, category="behavior", is_placeholder=True, color_status="green"),
    _module("behavior_habit", "behavior", "Behavior Habit", "layer_8", status=ProtocolStatus.mock, category="behavior", color_status="amber"),
    _module("behavior_policy_slot", "behavior_slot", "Behavior Policy Slot", "layer_8", status=ProtocolStatus.mock, slot_type=SlotType.tool, category="behavior", color_status="amber"),

    # L9 Capability / Tools
    _module("builtin_capability", "capability", "Builtin Capability", "layer_9", status=ProtocolStatus.ready, category="capability", is_placeholder=True, color_status="green"),
    _module("permission_management", "capability", "Permission Management", "layer_9", status=ProtocolStatus.ready, category="capability", is_placeholder=True, color_status="green"),
    _module("api_connector_slot", "capability_slot", "API Connector Slot", "layer_9", status=ProtocolStatus.ready, slot_type=SlotType.tool, category="capability", is_placeholder=True, color_status="green"),
    _module("llm_provider_router", "capability_router", "LLM Provider Router", "layer_9", status=ProtocolStatus.ready, slot_type=SlotType.llm, category="capability", is_placeholder=True, color_status="green"),
    _module("model_adapter", "capability_adapter", "Model Adapter", "layer_9", status=ProtocolStatus.ready, slot_type=SlotType.llm, category="capability", is_placeholder=True, color_status="green"),
    _module("api_adapter", "capability_adapter", "API Adapter", "layer_9", status=ProtocolStatus.ready, slot_type=SlotType.tool, category="capability", is_placeholder=True, color_status="green"),
    _module("tool_router_slot", "capability_slot", "Tool Router Slot", "layer_9", status=ProtocolStatus.ready, slot_type=SlotType.tool, category="capability", is_placeholder=True, color_status="green"),
    _module("ai_slot_router", "capability_slot", "AI Slot Router", "layer_9", status=ProtocolStatus.ready, slot_type=SlotType.llm, category="capability", is_placeholder=True, color_status="green"),
    _module("tool_calling", "capability", "Tool Calling", "layer_9", status=ProtocolStatus.mock, slot_type=SlotType.tool, category="capability", color_status="amber"),
    _module("automation_task", "capability", "Automation Task", "layer_9", status=ProtocolStatus.later, slot_type=SlotType.tool, category="capability", color_status="gray"),
    _module("extension_capability", "capability", "Extension Capability", "layer_9", status=ProtocolStatus.later, slot_type=SlotType.tool, category="capability", color_status="gray"),
    _module("local_model_slot", "capability_slot", "Local Model Slot", "layer_9", status=ProtocolStatus.later, slot_type=SlotType.llm, category="capability", color_status="gray"),
    _module("local_model_adapter", "capability_adapter", "Local Model Adapter", "layer_9", status=ProtocolStatus.later, slot_type=SlotType.llm, category="capability", color_status="gray"),

    # L10 Multimodal
    _module(
        "voice_tts_module_v1",
        "voice_tts_module",
        "Voice / TTS Module v1",
        "layer_10",
        status=ProtocolStatus.ready,
        slot_type=SlotType.tts,
        category="multimodal",
        is_placeholder=False,
        color_status="green",
        tags=["voice", "tts", "lattice"],
        module_graph={
            "node_roles": [
                "voice_config",
                "tts_provider",
                "voice_profile",
                "audio_output",
                "speaking_status",
                "voice_lattice_sync",
                "speech_input_event_placeholder",
            ],
            "slot_routes": ["tts.speak", "tts.preview", "voice.status", "speech.input_event"],
        },
        slot_bindings=[
            {"slot_id": "slot_tts", "slot_type": SlotType.tts.value, "slot_name": "tts.speak", "node_role": "tts_provider"},
            {"slot_id": "slot_tts", "slot_type": SlotType.tts.value, "slot_name": "tts.preview", "node_role": "audio_output"},
            {"slot_id": "slot_lattice_update", "slot_type": SlotType.lattice.value, "slot_name": "voice.status", "node_role": "speaking_status"},
            {"slot_id": "slot_lattice_update", "slot_type": SlotType.lattice.value, "slot_name": "voice.sync.lattice_voice", "node_role": "voice_lattice_sync"},
            {"slot_id": "slot_speech", "slot_type": SlotType.speech.value, "slot_name": "speech.input_event", "node_role": "speech_input_event_placeholder"},
        ],
        runtime_mapping={
            "flow": [
                "output_text",
                "tts.speak",
                "audio_output",
                "voice.status=speaking",
                "voice.sync.lattice_voice",
                "lattice_state.voice_state=speaking",
                "subtitle_stream_update",
                "voice_state=idle",
            ]
        },
        dr_mapping={
            "voice_config": "voice_config",
            "tts_provider_config": "tts_provider_config",
            "voice_profile_config": "voice_profile_config",
            "voice_lattice_sync_policy": "voice_lattice_sync_policy",
            "speech_event_schema": "speech_event_schema",
        },
        ui_config={"strict_layers": True, "execution_entry": "slot_only"},
        i18n_keys={
            "display_name": "module.voice_tts_module_v1",
            "description": "module.voice_tts_module_v1.description",
        },
        inputs={"output_text": "string"},
        outputs={"voice_state": "idle"},
        config={
            "voice_config": True,
            "tts_provider_config": True,
            "voice_profile_config": True,
            "voice_lattice_sync_policy": True,
            "speech_event_schema": True,
        },
    ),
    _module("voice_profile", "multimodal", "Voice Profile", "layer_10", status=ProtocolStatus.ready, slot_type=SlotType.tts, category="multimodal", is_placeholder=True, color_status="green"),
    _module("voice_profile_keyed", "multimodal", "Voice Profile Keyed", "layer_10", status=ProtocolStatus.mock, slot_type=SlotType.tts, category="multimodal", color_status="amber"),
    _module("tts_provider_router", "multimodal_router", "TTS Provider Router", "layer_10", status=ProtocolStatus.ready, slot_type=SlotType.tts, category="multimodal", is_placeholder=True, color_status="green"),
    _module("elevenlabs_slot", "multimodal_slot", "ElevenLabs Slot", "layer_10", status=ProtocolStatus.ready, slot_type=SlotType.tts, category="multimodal", is_placeholder=True, color_status="green"),
    _module("volcano_tts_slot", "multimodal_slot", "Volcano TTS Slot", "layer_10", status=ProtocolStatus.ready, slot_type=SlotType.tts, category="multimodal", is_placeholder=True, color_status="green"),
    _module("particle_avatar", "multimodal", "Particle Avatar", "layer_10", status=ProtocolStatus.ready, slot_type=SlotType.avatar, category="multimodal", is_placeholder=True, color_status="green"),
    _module("ar_avatar_slot", "multimodal_slot", "AR Avatar Slot", "layer_10", status=ProtocolStatus.ready, slot_type=SlotType.ar, category="multimodal", is_placeholder=True, color_status="green"),
    _module("appearance_profile", "multimodal", "Appearance Profile", "layer_10", status=ProtocolStatus.mock, category="multimodal", color_status="amber"),
    _module("motion_profile", "multimodal", "Motion Profile", "layer_10", status=ProtocolStatus.mock, category="multimodal", color_status="amber"),
    _module("visual_style", "multimodal", "Visual Style", "layer_10", status=ProtocolStatus.mock, category="multimodal", color_status="amber"),
    _module("avatar_runtime", "multimodal", "Avatar Runtime", "layer_10", status=ProtocolStatus.mock, slot_type=SlotType.avatar, category="multimodal", color_status="amber"),
    _module("video_expression", "multimodal", "Video Expression", "layer_10", status=ProtocolStatus.later, category="multimodal", color_status="gray"),
    _module("lora_visual_slot", "multimodal_slot", "LoRA Visual Slot", "layer_10", status=ProtocolStatus.later, slot_type=SlotType.ar, category="multimodal", color_status="gray"),
    _module("realtime_human_video_slot", "multimodal_slot", "Realtime Human Video Slot", "layer_10", status=ProtocolStatus.later, slot_type=SlotType.ar, category="multimodal", color_status="gray"),
    _module("ar_runtime_bridge", "multimodal_bridge", "AR Runtime Bridge", "layer_10", status=ProtocolStatus.later, slot_type=SlotType.ar, category="multimodal", color_status="gray"),

    # L11 Relationship
    _module("relationship_rule", "relationship", "Relationship Rule", "layer_11", status=ProtocolStatus.ready, category="relationship", is_placeholder=True, color_status="green"),
    _module("user_relationship", "relationship", "User Relationship", "layer_11", status=ProtocolStatus.mock, category="relationship", color_status="amber"),
    _module("intimacy_level", "relationship", "Intimacy Level", "layer_11", status=ProtocolStatus.mock, category="relationship", color_status="amber"),
    _module("interaction_history", "relationship", "Interaction History", "layer_11", status=ProtocolStatus.mock, category="relationship", color_status="amber"),
    _module("role_positioning", "relationship", "Role Positioning", "layer_11", status=ProtocolStatus.mock, category="relationship", color_status="amber"),
    _module("relationship_memory_slot", "relationship_slot", "Relationship Memory Slot", "layer_11", status=ProtocolStatus.mock, slot_type=SlotType.memory, category="relationship", color_status="amber"),
    _module("user_profile_slot", "relationship_slot", "User Profile Slot", "layer_11", status=ProtocolStatus.mock, slot_type=SlotType.memory, category="relationship", color_status="amber"),

    # L12 Meta / Self-Reflection
    _module("self_awareness", "meta", "Self Awareness", "layer_12", status=ProtocolStatus.mock, category="meta", color_status="amber"),
    _module("goal_setting", "meta", "Goal Setting", "layer_12", status=ProtocolStatus.mock, category="meta", color_status="amber"),
    _module("reflection_summary", "meta", "Reflection Summary", "layer_12", status=ProtocolStatus.mock, category="meta", color_status="amber"),
    _module("self_evaluation", "meta", "Self Evaluation", "layer_12", status=ProtocolStatus.mock, category="meta", color_status="amber"),
    _module("growth_plan", "meta", "Growth Plan", "layer_12", status=ProtocolStatus.later, category="meta", color_status="gray"),
    _module("self_reflection_slot", "meta_slot", "Self Reflection Slot", "layer_12", status=ProtocolStatus.later, slot_type=SlotType.llm, category="meta", color_status="gray"),
    _module("growth_loop_slot", "meta_slot", "Growth Loop Slot", "layer_12", status=ProtocolStatus.later, slot_type=SlotType.llm, category="meta", color_status="gray"),

    # L13 Export / Deployment
    _module("operation_log", "export", "Operation Log", "layer_13", status=ProtocolStatus.ready, category="export", is_placeholder=True, color_status="green"),
    _module("version_management", "export", "Version Management", "layer_13", status=ProtocolStatus.ready, category="export", is_placeholder=True, color_status="green"),
    _module("data_source_record", "export", "Data Source Record", "layer_13", status=ProtocolStatus.ready, category="export", is_placeholder=True, color_status="green"),
    _module("audit_record", "export", "Audit Record", "layer_13", status=ProtocolStatus.ready, category="export", is_placeholder=True, color_status="green"),
    _module("export_record", "export", "Export Record", "layer_13", status=ProtocolStatus.ready, category="export", is_placeholder=True, color_status="green"),
    _module("node_audit_slot", "export_slot", "Node Audit Slot", "layer_13", status=ProtocolStatus.ready, slot_type=SlotType.tool, category="export", is_placeholder=True, color_status="green"),
    _module("layer_audit_slot", "export_slot", "Layer Audit Slot", "layer_13", status=ProtocolStatus.ready, slot_type=SlotType.tool, category="export", is_placeholder=True, color_status="green"),
    _module("resident_audit_slot", "export_slot", "Resident Audit Slot", "layer_13", status=ProtocolStatus.ready, slot_type=SlotType.tool, category="export", is_placeholder=True, color_status="green"),
    _module("persona_package_compiler", "export", "Persona Package Compiler", "layer_13", status=ProtocolStatus.ready, category="export", is_placeholder=True, color_status="green"),
    _module("runtime_engine", "export", "Runtime Engine", "layer_13", status=ProtocolStatus.ready, category="export", is_placeholder=True, color_status="green"),
    _module("runtime_binding_slot", "export_slot", "Runtime Binding Slot", "layer_13", status=ProtocolStatus.ready, slot_type=SlotType.tool, category="export", is_placeholder=True, color_status="green"),
    _module("preview_module", "export", "Preview Module", "layer_13", status=ProtocolStatus.ready, category="export", is_placeholder=True, color_status="green"),
    _module("log_module", "export", "Log Module", "layer_13", status=ProtocolStatus.ready, category="export", is_placeholder=True, color_status="green"),
    _module("version_diff_slot", "export_slot", "Version Diff Slot", "layer_13", status=ProtocolStatus.mock, slot_type=SlotType.tool, category="export", color_status="amber"),
    _module("config_module", "export", "Config Module", "layer_13", status=ProtocolStatus.mock, category="export", color_status="amber"),
    _module("debug_module", "export", "Debug Module", "layer_13", status=ProtocolStatus.mock, category="export", color_status="amber"),
    _module("deployment_platform", "export", "Deployment Platform", "layer_13", status=ProtocolStatus.later, category="export", color_status="gray"),
    _module("api_interface", "export", "API Interface", "layer_13", status=ProtocolStatus.later, category="export", color_status="gray"),
    _module("distribution_channel", "export", "Distribution Channel", "layer_13", status=ProtocolStatus.later, category="export", color_status="gray"),
    _module("mac_app_binding_slot", "export_slot", "Mac App Binding Slot", "layer_13", status=ProtocolStatus.later, slot_type=SlotType.tool, category="export", color_status="gray"),
    _module("ar_runtime_binding_slot", "export_slot", "AR Runtime Binding Slot", "layer_13", status=ProtocolStatus.later, slot_type=SlotType.ar, category="export", color_status="gray"),
    # --- Protocol skeleton anchors (Stage 5 baseline) -----------------------
    # Layer 1 is represented by the five Stage 7.4 identity core modules above.
    _module("module_personality", "personality", "Personality", "layer_2", status=ProtocolStatus.core, category="persona", is_placeholder=False, color_status="green"),
    _module("module_safety_boundary", "safety", "Safety Boundary", "layer_3", status=ProtocolStatus.core, risk_level=RiskLevel.high, category="governance", is_placeholder=False, audit_required=True, color_status="green"),
    _module("module_legal_permission", "permission", "Legal Permission", "layer_4", status=ProtocolStatus.core, risk_level=RiskLevel.medium, category="governance", is_placeholder=False, audit_required=True, color_status="green"),
    # --- Future capabilities (modules only; never standalone executables) ----
    # High-risk future capabilities are represented purely as catalog modules so
    # the permission/risk gate governs them (is_placeholder=False -> they flow
    # through the risk gate and produce permission decisions, instead of being
    # silently dropped as placeholders). They are never wired to a real provider.
    _module("module_agent", "agent", "Agent", "layer_9", status=ProtocolStatus.planned, slot_type=SlotType.tool, risk_level=RiskLevel.high, category="capability", is_placeholder=False, audit_required=True, human_confirm_required=True),
    _module("module_wallet", "wallet", "Wallet", "layer_9", status=ProtocolStatus.later, slot_type=SlotType.tool, risk_level=RiskLevel.critical, category="capability", is_placeholder=False, audit_required=True, human_confirm_required=True),
    _module("module_phone", "phone", "Phone", "layer_9", status=ProtocolStatus.later, slot_type=SlotType.tool, risk_level=RiskLevel.high, category="capability", is_placeholder=False, audit_required=True, human_confirm_required=True),
    _module("module_social", "social", "Social", "layer_11", status=ProtocolStatus.planned, slot_type=SlotType.tool, risk_level=RiskLevel.medium, category="relationship", is_placeholder=False, audit_required=True),
    _module("module_ar", "ar", "AR Presence", "layer_10", status=ProtocolStatus.planned, slot_type=SlotType.ar, risk_level=RiskLevel.medium, category="multimodal", is_placeholder=False),
    _module("module_emergency_contact", "emergency_contact", "Emergency Contact", "layer_4", status=ProtocolStatus.later, risk_level=RiskLevel.high, category="governance", is_placeholder=False, audit_required=True, human_confirm_required=True),
    _module("module_lattice_update", "lattice_update", "Lattice Update", "layer_10", status=ProtocolStatus.mock, slot_type=SlotType.lattice, category="multimodal", is_placeholder=False, color_status="amber"),
    _module("module_lattice_read", "lattice_read", "Lattice Read", "layer_10", status=ProtocolStatus.mock, slot_type=SlotType.lattice, category="multimodal", is_placeholder=False, color_status="amber"),
    _module("module_lattice_preview", "lattice_preview", "Lattice Preview", "layer_10", status=ProtocolStatus.mock, slot_type=SlotType.lattice, category="multimodal", is_placeholder=False, color_status="amber"),
    _module(
        SCREEN_UI_ANCHOR_MODULE.module_id,
        SCREEN_UI_ANCHOR_MODULE.module_type,
        SCREEN_UI_ANCHOR_MODULE.module_name,
        SCREEN_UI_ANCHOR_MODULE.layer_id,
        status=ProtocolStatus.mock,
        category="context",
        is_placeholder=False,
        color_status="amber",
        module_graph=SCREEN_UI_ANCHOR_MODULE.screen_config,
        input_schema=[],
        output_schema=[],
        slot_bindings=[{"slot_name": slot_name} for slot_name in SCREEN_UI_ANCHOR_MODULE.slot_declarations],
        context_bindings=[{"context": "screen.context"}, {"context": "ui.anchor"}, {"context": "guidance.action"}],
        runtime_mapping={"flow": SCREEN_UI_ANCHOR_MODULE.screen_config["runtime_chain"]},
        dr_mapping={
            "screen_context_schema": "screen_context_schema",
            "ui_element_schema": "ui_element_schema",
            "ui_anchor_schema": "ui_anchor_schema",
            "guidance_action_schema": "guidance_action_schema",
            "screen_trace_schema": "screen_trace_schema",
            "screen_permission_policy": "screen_permission_policy",
        },
        ui_config={"strict_layers": True, "execution_entry": "schema_only"},
        i18n_keys=SCREEN_UI_ANCHOR_MODULE.i18n_keys,
        inputs={},
        outputs={},
        config=SCREEN_UI_ANCHOR_MODULE.screen_config,
        mock_only=SCREEN_UI_ANCHOR_MODULE.mock_only,
        no_execution=SCREEN_UI_ANCHOR_MODULE.no_execution,
        slot_declarations=SCREEN_UI_ANCHOR_MODULE.slot_declarations,
        screen_config=SCREEN_UI_ANCHOR_MODULE.screen_config,
        dr_write_keys=SCREEN_UI_ANCHOR_MODULE.dr_write_keys,
    ),
]


def validate_module_catalog(modules: List[ModuleV04]) -> List[str]:
    """Return a list of error strings; empty list means the catalog is valid."""
    errors: List[str] = []
    seen: set[str] = set()
    for module in modules:
        if not module.module_id:
            errors.append("module_id is empty")
            continue
        if module.module_id in seen:
            errors.append(f"duplicate module_id: {module.module_id}")
        seen.add(module.module_id)
        if module.layer_id not in CANONICAL_LAYER_IDS:
            errors.append(f"module {module.module_id} bound to unknown layer_id: {module.layer_id}")
        if module.protocol_version != "0.4.0":
            errors.append(f"module {module.module_id} has invalid protocol_version: {module.protocol_version}")
        if module.status.value not in {"CORE", "READY", "MOCK", "PLANNED", "LATER", "DISABLED"}:
            errors.append(f"module {module.module_id} has invalid status: {module.status}")
    return errors


def get_module_catalog() -> List[ModuleV04]:
    return list(MODULE_CATALOG)


def module_catalog_map() -> Dict[str, ModuleV04]:
    return {module.module_id: module for module in MODULE_CATALOG}
