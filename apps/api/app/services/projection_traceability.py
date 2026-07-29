"""Stable Stage 7.4.12 A3 runtime projection mapping metadata.

The registry describes the one-way compile contract only. It is returned in
Studio compile audit metadata and is not serialized into a digital resident.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict


STAGE7_4_12_A3_CONTENT_REVISION = (
    "stage7_4_12_a3_projection_traceability_mapping_v1"
)
STAGE7_4_12_FINAL_SCHEMA_TRACEABILITY_GATE_FIX_REVISION = (
    "stage7_4_12_final_schema_traceability_gate_fix_v1"
)
PROJECTION_SOURCE_PRIORITY = (
    "current_module_output",
    "normalized_current_node",
    "protocol_compatibility_fallback",
)

PROJECTION_FIELD_MAPPINGS: tuple[Dict[str, Any], ...] = (
    {
        "mapping_id": "resident_identity",
        "source_layer": "layer_1",
        "source_module": (
            "module_basic_identity",
            "module_growth_background",
            "module_career_identity",
            "module_existence_mode",
            "module_identity_anchor",
        ),
        "source_output": (
            "basic_identity",
            "growth_background",
            "career_identity",
            "existence_mode",
            "identity_anchor",
        ),
        "source_field": "identity_profile",
        "source_path": "payload.graph_snapshot.layer_outputs.identity_profile",
        "target_path": "payload.resident_identity",
        "transform": "_assemble_identity_core_outputs -> _v3_identity_sync_from_profile",
        "alias_rule": "city -> city_symbol; primary_language normalized",
        "missing_fallback": "required identity failure or protocol-safe summary",
        "consumer": "RuntimeCore / Aftelle",
        "projection_type": "derived_read_only",
    },
    {
        "mapping_id": "resident_identity_summary",
        "source_layer": "layer_1",
        "source_module": (
            "module_basic_identity",
            "module_growth_background",
            "module_career_identity",
            "module_existence_mode",
            "module_identity_anchor",
        ),
        "source_output": "identity_profile",
        "source_field": "identity_summary",
        "source_path": "payload.graph_snapshot.layer_outputs.identity_profile",
        "target_path": (
            "payload.resident_blueprint; resident.description; "
            "resident.disclosure"
        ),
        "transform": "_build_identity_top_summary",
        "alias_rule": "identity fields -> public description/disclosure summary",
        "missing_fallback": "generic digital-resident safety summary",
        "consumer": "Studio / Aftelle",
        "projection_type": "derived_read_only",
    },
    {
        "mapping_id": "memory_policy_extensions",
        "source_layer": "layer_5",
        "source_module": (
            "short_term_memory",
            "preference_memory",
            "event_memory",
            "relationship_memory",
            "memory_update",
            "memory_access_control",
            "memory_provider_router",
        ),
        "source_output": (
            "short_term_memory_context",
            "preference_memory",
            "event_memory",
            "relationship_memory",
            "memory_update_policy",
            "memory_access_policy_result",
            "memory_provider_route_policy",
        ),
        "source_field": "current module output",
        "source_path": "payload.modules[layer_5].outputs",
        "target_path": (
            "payload.memory_policy.memory_policy_extensions; memory_policy"
        ),
        "transform": "_assemble_layer5_memory_policy -> _build_v03_memory_policy",
        "alias_rule": "root memory_policy remains the v0.3 compatibility mirror",
        "missing_fallback": "frozen v0.3 memory envelope with diagnostic",
        "consumer": "RuntimeCore Memory",
        "projection_type": "derived_read_only",
    },
    {
        "mapping_id": "runtime_memory_usage_policy",
        "source_layer": "layer_5",
        "source_module": (
            "short_term_memory",
            "preference_memory",
            "event_memory",
            "relationship_memory",
            "memory_update",
            "memory_access_control",
            "memory_provider_router",
        ),
        "source_output": (
            "short_term_memory_context",
            "preference_memory",
            "event_memory",
            "relationship_memory",
            "memory_update_policy",
            "memory_access_policy_result",
            "memory_provider_route_policy",
        ),
        "source_field": (
            "access/write/sensitive/narrative/session_and_long_term_boundaries"
        ),
        "source_path": "payload.memory_policy.memory_policy_extensions",
        "target_path": (
            "payload.runtime_dialogue_projection.memory_usage_policy.derived_values"
        ),
        "transform": "_assemble_runtime_dialogue_policy_values",
        "alias_rule": "none",
        "missing_fallback": "public runtime memory policy plus warning",
        "consumer": "RuntimeCore LLM context",
        "projection_type": "derived_read_only",
    },
    {
        "mapping_id": "first_interaction",
        "source_layer": "layer_8",
        "source_module": "interaction_strategy",
        "source_output": "interaction_behavior_config",
        "source_field": "first_interaction",
        "source_path": (
            "payload.modules.interaction_strategy.current_fields.first_interaction"
        ),
        "target_path": "payload.behavior.first_interaction",
        "transform": "_assemble_first_greeting_config_extensions",
        "alias_rule": "none",
        "missing_fallback": "omit optional projection",
        "consumer": "RuntimeCore first interaction",
        "projection_type": "derived_read_only",
    },
    {
        "mapping_id": "runtime_behavior_policy",
        "source_layer": "layer_8",
        "source_module": (
            "language_habit",
            "decision_pattern",
            "interaction_strategy",
            "emotion_mapper",
            "behavior_habit",
            "emotion_reaction",
            "dialogue_runtime_profile",
        ),
        "source_output": (
            "language_behavior_config",
            "decision_behavior_config",
            "interaction_behavior_config",
            "social_behavior_config",
            "task_behavior_config",
            "dialogue_runtime_profile_config",
        ),
        "source_field": (
            "materialized behavior outputs; current emotion_reaction rule "
            "nodes; dialogue runtime profile output"
        ),
        "source_path": (
            "payload.modules[layer_8].outputs; "
            "payload.modules.emotion_reaction.module_graph.nodes"
        ),
        "target_path": (
            "payload.behavior_policy; payload.runtime_dialogue_projection"
        ),
        "transform": (
            "_assemble_layer8_behavior_outputs -> "
            "build_runtime_dialogue_projection"
        ),
        "alias_rule": (
            "daily_companion uses the public type template; emotional_dialogue "
            "is nested in dialogue_runtime_profile_config"
        ),
        "missing_fallback": "current-node normalization then public template",
        "consumer": "RuntimeCore LLM context",
        "projection_type": "derived_read_only",
        "source_structure": "multiple",
        "sources": (
            {
                "source_id": "materialized_layer8_behavior_outputs",
                "source_layer": "layer_8",
                "source_module": (
                    "language_habit",
                    "decision_pattern",
                    "interaction_strategy",
                    "emotion_mapper",
                    "behavior_habit",
                ),
                "source_node": "module_output",
                "source_output": (
                    "language_behavior_config",
                    "decision_behavior_config",
                    "interaction_behavior_config",
                    "social_behavior_config",
                    "task_behavior_config",
                ),
                "source_field": "current compiled module output",
                "source_path": "payload.modules[layer_8].outputs",
                "projection_path": "payload.behavior_policy.modules",
                "transform": "_assemble_layer8_behavior_outputs",
            },
            {
                "source_id": "detail_behavior_current_rule_nodes",
                "source_layer": "layer_8",
                "source_module": "emotion_reaction",
                "source_node": (
                    "expression_context_input",
                    "expression_allowed_state_recognition",
                    "expression_state_selection_rules",
                    "expression_personality_consistency_validation",
                    "expression_relationship_safety_validation",
                    "expression_intensity_calculation",
                    "expression_state_normalize_fallback_validation",
                    "expression_state_output",
                    "expression_state_reference_output",
                ),
                "source_output": None,
                "source_field": (
                    "module_id",
                    "module_type",
                    "tags",
                    "module_graph.nodes[*].node_id",
                    (
                        "module_graph.nodes.expression_context_input."
                        "params.references"
                    ),
                    (
                        "module_graph.nodes.expression_state_selection_rules."
                        "params.checkbox_config.preset_id"
                    ),
                    (
                        "module_graph.nodes.expression_state_selection_rules."
                        "params.checkbox_config.selected_options"
                    ),
                    (
                        "module_graph.nodes.expression_state_selection_rules."
                        "params.checkbox_config.custom_text"
                    ),
                    (
                        "module_graph.nodes."
                        "expression_state_normalize_fallback_validation."
                        "params.checkbox_config.selected_options"
                    ),
                    (
                        "module_graph.nodes."
                        "expression_state_normalize_fallback_validation."
                        "params.checkbox_config.custom_text"
                    ),
                ),
                "source_path": (
                    "payload.modules.emotion_reaction.module_graph.nodes"
                ),
                "projection_path": (
                    "payload.behavior_policy.modules.detail_behavior"
                ),
                "transform": "_behavior_module_policy",
            },
            {
                "source_id": "dialogue_runtime_profile_output",
                "source_layer": "layer_8",
                "source_module": "dialogue_runtime_profile",
                "source_node": "module_output",
                "source_output": "dialogue_runtime_profile_config",
                "source_field": "current compiled dialogue runtime rules",
                "source_path": (
                    "payload.modules.dialogue_runtime_profile.outputs."
                    "dialogue_runtime_profile_config"
                ),
                "projection_path": (
                    "payload.runtime_dialogue_projection"
                ),
                "transform": "build_runtime_dialogue_projection",
            },
        ),
    },
    {
        "mapping_id": "visual_expression_state_selection",
        "source_layer": "layer_8",
        "source_module": "emotion_reaction",
        "source_output": None,
        "source_field": (
            "module_graph.nodes.expression_state_selection_rules."
            "params.selection_rules"
        ),
        "source_path": (
            "payload.modules.emotion_reaction.module_graph.nodes."
            "expression_state_selection_rules.params.selection_rules"
        ),
        "target_path": (
            "visual_expression_mapping.state_selection_policy.selection_rules"
        ),
        "transform": "build_visual_expression_mapping",
        "alias_rule": "ordered verbatim rule projection",
        "missing_fallback": "empty selection rules with diagnostic",
        "consumer": "RuntimeCore state selection / Aftelle",
        "projection_type": "derived_read_only",
    },
    {
        "mapping_id": "first_visual_presence",
        "source_layer": "layer_10",
        "source_module": "visual_style",
        "source_output": "first_presence_config",
        "source_field": "first_greeting; first_presence",
        "source_path": "payload.modules.visual_style.outputs.first_presence_config",
        "target_path": (
            "payload.expression.first_greeting; payload.expression.first_presence"
        ),
        "transform": "_synchronize_first_presence_module_output",
        "alias_rule": "none",
        "missing_fallback": "omit optional projection",
        "consumer": "Aftelle first presence",
        "projection_type": "derived_read_only",
    },
    {
        "mapping_id": "particle_core_mapping",
        "source_layer": "layer_10",
        "source_module": "particle_avatar",
        "source_output": "particle_mapping_config",
        "source_field": "expression_relative_mapping.state_mappings",
        "source_path": (
            "payload.modules.particle_avatar.outputs.particle_mapping_config."
            "expression_relative_mapping.state_mappings"
        ),
        "target_path": "visual_expression_mapping.particle_core_mapping",
        "transform": "build_visual_expression_mapping",
        "alias_rule": "color_temperature_offset -> temperature_shift",
        "missing_fallback": "parameter identity default with clamp diagnostic",
        "consumer": "Aftelle ParticleCore",
        "projection_type": "derived_read_only",
    },
    {
        "mapping_id": "particle_transition_policy",
        "source_layer": "layer_10",
        "source_module": "particle_avatar",
        "source_output": "particle_mapping_config",
        "source_field": "transition_rules",
        "source_path": (
            "payload.modules.particle_avatar.outputs.particle_mapping_config."
            "transition_rules"
        ),
        "target_path": "visual_expression_mapping.transition_policy",
        "transform": "build_visual_expression_mapping",
        "alias_rule": (
            "same_state_retriggers_transition -> "
            "repeat_same_state_restarts_transition; "
            "new_state_continues_from_current_visual -> "
            "continue_from_current_visual_value"
        ),
        "missing_fallback": "protocol transition defaults with diagnostic",
        "consumer": "Aftelle transition executor",
        "projection_type": "derived_read_only",
    },
    {
        "mapping_id": "initial_relationship",
        "source_layer": "layer_11",
        "source_module": "user_relationship",
        "source_output": "user_relationship_config",
        "source_field": "fields.initial_relationship",
        "source_path": (
            "payload.modules.user_relationship.outputs."
            "user_relationship_config.fields.initial_relationship"
        ),
        "target_path": "payload.relationship.initial_relationship",
        "transform": "_assemble_first_greeting_config_extensions",
        "alias_rule": "none",
        "missing_fallback": "omit optional projection",
        "consumer": "RuntimeCore relationship initialization",
        "projection_type": "derived_read_only",
    },
    {
        "mapping_id": "runtime_relationship_policy",
        "source_layer": "layer_11",
        "source_module": (
            "user_relationship",
            "relationship_rule",
            "intimacy_level",
            "role_positioning",
        ),
        "source_output": (
            "user_relationship_config",
            "relationship_behavior_config",
            "relationship_stage_config",
            "trust_mechanism_config",
        ),
        "source_field": "fields",
        "source_path": "payload.modules[layer_11].outputs",
        "target_path": (
            "payload.runtime_dialogue_projection.relationship_policy.derived_values"
        ),
        "transform": "_assemble_runtime_dialogue_policy_values",
        "alias_rule": "relationship modules grouped without redefining initial_relationship",
        "missing_fallback": "public relationship policy plus warning",
        "consumer": "RuntimeCore LLM context",
        "projection_type": "derived_read_only",
    },
    {
        "mapping_id": "relationship_progression_projection",
        "source_layer": (
            "layer_3",
            "layer_5",
            "layer_11",
            "layer_12",
        ),
        "source_module": (
            "humanistic_interaction_boundary_config_v0_1",
            "humanistic_risk_response_config_v0_1",
            "memory_access_control",
            "memory_update",
            "user_relationship",
            "relationship_rule",
            "self_awareness",
        ),
        "source_output": (
            "interaction_safety_policy",
            "risk_policy",
            "memory_access_policy_result",
            "memory_update_policy",
            "user_relationship_config",
            "relationship_behavior_config",
            "self_awareness_config",
        ),
        "source_field": (
            "relationship stages; reserved stage gate; evidence rules; "
            "forbidden transition evidence; user controls; policy references"
        ),
        "source_path": (
            "payload.modules.user_relationship.module_graph.nodes."
            "user_relationship_config_input.params.fields; "
            "payload.modules.relationship_rule.module_graph.nodes."
            "relationship_evidence_candidate_input.params.fields"
        ),
        "target_path": (
            "payload.relationship_progression_projection"
        ),
        "transform": "build_relationship_progression_projection",
        "alias_rule": (
            "Layer 11 remains authoritative; Layer 3, 5, and 12 are "
            "reference identifiers only"
        ),
        "missing_fallback": "omit optional projection for legacy compatibility",
        "consumer": "RuntimeCore relationship-stage policy",
        "projection_type": "derived_read_only",
    },
    {
        "mapping_id": "narrative_memory_projection",
        "source_layer": "layer_5",
        "source_module": (
            "event_memory",
            "memory_update",
            "memory_access_control",
        ),
        "source_output": (
            "event_memory",
            "memory_update_policy",
            "memory_access_policy_result",
        ),
        "source_field": (
            "memory_types; lifecycle_states; candidate and consent rules; "
            "deduplication, conflict, supersession, deletion, retrieval, "
            "expression, model and runtime authority; boundary references"
        ),
        "source_path": (
            "payload.modules.event_memory.outputs.event_memory; "
            "payload.modules.memory_update.outputs.memory_update_policy; "
            "payload.modules.memory_access_control.outputs."
            "memory_access_policy_result"
        ),
        "target_path": "payload.narrative_memory_projection",
        "transform": "build_narrative_memory_projection",
        "alias_rule": (
            "Layer 5 remains authoritative; Layer 3, 8, and 11 are "
            "validated reference identifiers only"
        ),
        "missing_fallback": (
            "omit optional projection for legacy compatibility"
        ),
        "consumer": "RuntimeCore narrative-memory policy",
        "projection_type": "derived_read_only",
    },
    {
        "mapping_id": "runtime_self_and_capability_boundaries",
        "source_layer": "layer_12",
        "source_module": ("self_awareness", "growth_plan"),
        "source_output": (
            "self_awareness_config",
            "growth_identity_continuity_governance_config",
        ),
        "source_field": (
            "resolved_facts; capability_awareness; limitation_awareness; "
            "relationship_awareness; immutable_core; real_human_boundary; "
            "growth governance constraints"
        ),
        "source_path": "payload.modules[layer_12].outputs",
        "target_path": (
            "payload.runtime_dialogue_projection.self_disclosure_policy."
            "derived_values; payload.runtime_dialogue_projection.advice_policy."
            "derived_values"
        ),
        "transform": "_assemble_runtime_dialogue_policy_values",
        "alias_rule": (
            "identity/language/region/relationship facts use A2 resolved_facts"
        ),
        "missing_fallback": "existing safe boundary policy plus warning",
        "consumer": "RuntimeCore LLM context",
        "projection_type": "derived_read_only",
    },
    {
        "mapping_id": "runtime_requirements",
        "source_layer": "slots_registry",
        "source_module": "slot / engine / provider registry",
        "source_output": "runtime contract",
        "source_field": "slot_type; engine_id; provider_type",
        "source_path": "payload.slots; Studio registry",
        "target_path": "payload.runtime_requirements; runtime_requirements",
        "transform": "build_v03_runtime_contract",
        "alias_rule": "root runtime_requirements is the v0.3 compatibility mirror",
        "missing_fallback": "required runtime contract failure",
        "consumer": "RuntimeCore loader / router",
        "projection_type": "derived_read_only",
    },
)


def build_projection_traceability() -> Dict[str, Any]:
    """Return deterministic compile-only trace metadata."""

    return {
        "content_revision": STAGE7_4_12_A3_CONTENT_REVISION,
        "schema_traceability_gate_revision": (
            STAGE7_4_12_FINAL_SCHEMA_TRACEABILITY_GATE_FIX_REVISION
        ),
        "projection_type": "derived_read_only",
        "source_priority": list(PROJECTION_SOURCE_PRIORITY),
        "mappings": deepcopy(list(PROJECTION_FIELD_MAPPINGS)),
    }


def projection_field_mapping_errors() -> list[str]:
    """Return structural registry errors without raising raw exceptions."""

    required_keys = {
        "mapping_id",
        "source_layer",
        "source_module",
        "source_output",
        "source_field",
        "source_path",
        "target_path",
        "transform",
        "alias_rule",
        "missing_fallback",
        "consumer",
        "projection_type",
    }
    errors: list[str] = []
    mapping_ids: set[str] = set()
    source_required_keys = {
        "source_id",
        "source_layer",
        "source_module",
        "source_node",
        "source_output",
        "source_field",
        "source_path",
        "projection_path",
        "transform",
    }
    for index, mapping in enumerate(PROJECTION_FIELD_MAPPINGS):
        missing = sorted(required_keys - set(mapping))
        if missing:
            errors.append(
                f"mapping[{index}] missing keys: {', '.join(missing)}"
            )
        mapping_id = mapping.get("mapping_id")
        if not isinstance(mapping_id, str) or not mapping_id:
            errors.append(f"mapping[{index}] has no stable mapping_id")
        elif mapping_id in mapping_ids:
            errors.append(f"duplicate mapping_id: {mapping_id}")
        else:
            mapping_ids.add(mapping_id)
        if mapping.get("projection_type") != "derived_read_only":
            errors.append(
                f"mapping[{index}] projection_type must be derived_read_only"
            )
        if mapping.get("source_structure") == "multiple":
            sources = mapping.get("sources")
            if not isinstance(sources, (list, tuple)) or not sources:
                errors.append(
                    f"mapping[{index}] multiple source registry is empty"
                )
                continue
            source_ids: set[str] = set()
            for source_index, source in enumerate(sources):
                if not isinstance(source, dict):
                    errors.append(
                        f"mapping[{index}].sources[{source_index}] must be an object"
                    )
                    continue
                missing_source_keys = sorted(
                    source_required_keys - set(source)
                )
                if missing_source_keys:
                    errors.append(
                        f"mapping[{index}].sources[{source_index}] missing keys: "
                        + ", ".join(missing_source_keys)
                    )
                source_id = source.get("source_id")
                if not isinstance(source_id, str) or not source_id:
                    errors.append(
                        f"mapping[{index}].sources[{source_index}] has no stable source_id"
                    )
                elif source_id in source_ids:
                    errors.append(
                        f"mapping[{index}] duplicate source_id: {source_id}"
                    )
                else:
                    source_ids.add(source_id)
    if len(PROJECTION_FIELD_MAPPINGS) != 16:
        errors.append(
            "projection registry must contain exactly 16 mappings"
        )
    return errors
