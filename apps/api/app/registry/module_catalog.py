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
    SlotType,
)


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
) -> ModuleV04:
    return ModuleV04(
        module_id=module_id,
        module_type=module_type,
        module_name=module_name,
        module_version="0.1.0",
        layer_id=layer_id,
        inputs={},
        outputs={},
        config={},
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
    )


MODULE_CATALOG: List[ModuleV04] = [
    # L1 Identity Core
    _module("basic_identity", "identity_core", "Basic Identity", "layer_1", status=ProtocolStatus.ready, category="identity", is_placeholder=True, color_status="green"),
    _module("existence_boundary", "identity_core", "Existence Boundary", "layer_1", status=ProtocolStatus.ready, category="identity", is_placeholder=True, color_status="green"),
    _module("identity_anchor", "identity_core", "Identity Anchor", "layer_1", status=ProtocolStatus.ready, category="identity", is_placeholder=True, color_status="green"),
    _module("identity_llm_slot", "identity_slot", "Identity LLM Slot", "layer_1", status=ProtocolStatus.ready, slot_type=SlotType.llm, category="identity", is_placeholder=True, color_status="green"),
    _module("background_setting", "identity_profile", "Background Setting", "layer_1", status=ProtocolStatus.mock, category="identity", color_status="amber"),
    _module("worldview_position", "identity_profile", "Worldview Position", "layer_1", status=ProtocolStatus.mock, category="identity", color_status="amber"),
    _module("identity_consistency_lock", "identity_guard", "Identity Consistency Lock", "layer_1", status=ProtocolStatus.mock, category="identity", color_status="amber"),

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
    _module("voice_profile", "multimodal", "Voice Profile", "layer_10", status=ProtocolStatus.ready, slot_type=SlotType.tts, category="multimodal", is_placeholder=True, color_status="green"),
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
    # The 13-layer trunk keeps four CORE anchor modules — the non-placeholder
    # backbone of identity / personality / safety / legal. These were part of
    # the v0.4 protocol baseline and are data-only additions (no protocol change).
    _module("module_identity_core", "identity", "Identity Core", "layer_1", status=ProtocolStatus.core, category="persona", is_placeholder=False, color_status="green"),
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
