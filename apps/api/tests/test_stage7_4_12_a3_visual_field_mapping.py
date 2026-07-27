"""Focused contracts for the Stage 7.4.12 A3 visual field mapping."""

from __future__ import annotations

from app.registry.module_catalog import get_module_catalog
from app.services.visual_expression_projection import (
    VISUAL_EXPRESSION_FIELD_MAPPING,
    VISUAL_EXPRESSION_PARAMETER_SPECS,
    VISUAL_EXPRESSION_PROJECTION_CONTENT_REVISION,
    build_visual_expression_mapping,
)


_STATES = ["neutral", "calm", "caring", "subdued", "joyful"]
_PARTICLE_FIELDS = (
    ("brightness_multiplier", "brightness_multiplier"),
    ("saturation_multiplier", "saturation_multiplier"),
    ("color_temperature_offset", "temperature_shift"),
    ("energy_multiplier", "energy_multiplier"),
    ("motion_speed_multiplier", "motion_speed_multiplier"),
    ("diffusion_multiplier", "diffusion_multiplier"),
)
_TRANSITION_FIELDS = (
    ("transition_duration", "transition_duration"),
    ("minimum_hold_duration", "minimum_hold_duration"),
    ("transition_style", "transition_style"),
    (
        "same_state_retriggers_transition",
        "repeat_same_state_restarts_transition",
    ),
    (
        "new_state_continues_from_current_visual",
        "continue_from_current_visual_value",
    ),
    (
        "uses_accumulated_idle_time_as_progress",
        "uses_accumulated_idle_time_as_progress",
    ),
    (
        "minimum_hold_prevents_flicker",
        "minimum_hold_prevents_flicker",
    ),
    ("transition_executor", "transition_executor"),
)


def _modules() -> list[dict]:
    return [module.model_dump(mode="json") for module in get_module_catalog()]


def _module(modules: list[dict], module_id: str) -> dict:
    return next(module for module in modules if module["module_id"] == module_id)


def _node(module: dict, node_id: str) -> dict:
    return next(
        node
        for node in module["module_graph"]["nodes"]
        if node["node_id"] == node_id
    )


def test_visual_field_mapping_is_ordered_complete_and_importable():
    assert list(VISUAL_EXPRESSION_FIELD_MAPPING) == [
        "selection_rules",
        "particle_core_mapping",
        "transition_policy",
    ]
    assert VISUAL_EXPRESSION_FIELD_MAPPING["selection_rules"] == {
        "source_layer": "layer_8",
        "source_module": "emotion_reaction",
        "source_node": "expression_state_selection_rules",
        "source_field": "selection_rules",
        "target_path": (
            "visual_expression_mapping.state_selection_policy.selection_rules"
        ),
    }
    assert VISUAL_EXPRESSION_FIELD_MAPPING["particle_core_mapping"] == (
        _PARTICLE_FIELDS
    )
    assert VISUAL_EXPRESSION_FIELD_MAPPING["transition_policy"] == (
        _TRANSITION_FIELDS
    )
    assert tuple(VISUAL_EXPRESSION_PARAMETER_SPECS) == tuple(
        target_key for _source_key, target_key in _PARTICLE_FIELDS
    )
    assert tuple(
        (
            spec["source_key"],
            target_key,
        )
        for target_key, spec in VISUAL_EXPRESSION_PARAMETER_SPECS.items()
    ) == _PARTICLE_FIELDS


def test_visual_projection_uses_mapping_without_changing_frozen_values_or_shape():
    modules = _modules()
    expression = _module(modules, "emotion_reaction")
    particle = _module(modules, "particle_avatar")
    selection_node = _node(expression, "expression_state_selection_rules")
    mapping_node = _node(
        particle, "particle_expression_state_relative_mapping"
    )
    transition_node = _node(particle, "particle_state_transition_rules")

    projection, diagnostics = build_visual_expression_mapping(modules)

    assert diagnostics == []
    assert projection["content_revision"] == (
        VISUAL_EXPRESSION_PROJECTION_CONTENT_REVISION
    )
    assert projection["allowed_states"] == _STATES
    assert list(projection["particle_core_mapping"]) == _STATES
    assert (
        projection["state_selection_policy"]["selection_rules"]
        == selection_node["params"]["selection_rules"]
    )
    assert len(projection["state_selection_policy"]["selection_rules"]) == 4

    source_mappings = mapping_node["params"]["state_mappings"]
    target_mappings = projection["particle_core_mapping"]
    for state in _STATES:
        assert tuple(target_mappings[state]) == tuple(
            target_key for _source_key, target_key in _PARTICLE_FIELDS
        )
        assert "color_temperature_offset" not in target_mappings[state]
        for source_key, target_key in _PARTICLE_FIELDS:
            assert target_mappings[state][target_key] == (
                source_mappings[state][source_key]
            )

    assert tuple(projection["transition_policy"]) == tuple(
        target_key for _source_key, target_key in _TRANSITION_FIELDS
    )
    for source_key, target_key in _TRANSITION_FIELDS:
        assert projection["transition_policy"][target_key] == (
            transition_node["params"][source_key]
        )

    assert target_mappings["caring"]["brightness_multiplier"] == 1.06
    assert target_mappings["subdued"]["energy_multiplier"] == 0.78
    assert target_mappings["joyful"]["diffusion_multiplier"] == 1.14
    assert set(projection) == {
        "protocol_version",
        "content_revision",
        "allowed_states",
        "default_state",
        "intensity_range",
        "parameter_ranges",
        "state_selection_policy",
        "base_color_policy",
        "particle_core_mapping",
        "transition_policy",
        "lifecycle_priority",
        "fallback_policy",
        "abstract_bust_mapping",
    }
