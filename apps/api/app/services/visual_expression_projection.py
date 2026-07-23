"""Compile A1/A2 module configuration into a read-only visual projection."""

from __future__ import annotations

import math
from copy import deepcopy
from typing import Any, Dict, List, Sequence

from ..registry.module_catalog import (
    DETAIL_BEHAVIOR_MODULE_ID,
    EXPRESSION_STATE_VALUES,
    PARTICLE_AVATAR_MODULE_ID,
    PARTICLE_AVATAR_OUTPUT_KEY,
    PARTICLE_RELATIVE_PARAMETER_RANGES,
)

VISUAL_EXPRESSION_PROJECTION_CONTENT_REVISION = (
    "stage7_4_11_visual_expression_projection_v1"
)
VISUAL_EXPRESSION_PROJECTION_PROTOCOL_VERSION = "1.0"
VISUAL_EXPRESSION_ALLOWED_STATES = tuple(EXPRESSION_STATE_VALUES)
VISUAL_EXPRESSION_DEFAULT_STATE = "neutral"
VISUAL_EXPRESSION_INTENSITY_RANGE = {"minimum": 0.0, "maximum": 1.0}
VISUAL_EXPRESSION_BASE_COLOR_PRIORITY = (
    "user_current_base_color",
    "resident_default_base_color",
    "particle_core_default_gray_white",
)
VISUAL_EXPRESSION_PARTICLE_CORE_FALLBACK = "default_gray_white"
VISUAL_EXPRESSION_LIFECYCLE_OVERRIDE_STATES = ("error", "loading", "exit")
VISUAL_EXPRESSION_LIFECYCLE_COMPOSABLE_STATES = (
    "idle",
    "thinking",
    "speaking",
)
VISUAL_EXPRESSION_TRANSITION_DEFAULTS = {
    "transition_duration": 0.0,
    "minimum_hold_duration": 0.0,
    "transition_style": "smooth",
    "repeat_same_state_restarts_transition": False,
    "continue_from_current_visual_value": True,
}
VISUAL_EXPRESSION_PARAMETER_SPECS = {
    "brightness_multiplier": {
        "source_key": "brightness_multiplier",
        "identity": 1.0,
        "minimum": PARTICLE_RELATIVE_PARAMETER_RANGES["brightness_multiplier"][0],
        "maximum": PARTICLE_RELATIVE_PARAMETER_RANGES["brightness_multiplier"][1],
    },
    "saturation_multiplier": {
        "source_key": "saturation_multiplier",
        "identity": 1.0,
        "minimum": PARTICLE_RELATIVE_PARAMETER_RANGES["saturation_multiplier"][0],
        "maximum": PARTICLE_RELATIVE_PARAMETER_RANGES["saturation_multiplier"][1],
    },
    "temperature_shift": {
        "source_key": "color_temperature_offset",
        "identity": 0.0,
        "minimum": PARTICLE_RELATIVE_PARAMETER_RANGES["color_temperature_offset"][0],
        "maximum": PARTICLE_RELATIVE_PARAMETER_RANGES["color_temperature_offset"][1],
    },
    "energy_multiplier": {
        "source_key": "energy_multiplier",
        "identity": 1.0,
        "minimum": PARTICLE_RELATIVE_PARAMETER_RANGES["energy_multiplier"][0],
        "maximum": PARTICLE_RELATIVE_PARAMETER_RANGES["energy_multiplier"][1],
    },
    "motion_speed_multiplier": {
        "source_key": "motion_speed_multiplier",
        "identity": 1.0,
        "minimum": PARTICLE_RELATIVE_PARAMETER_RANGES["motion_speed_multiplier"][0],
        "maximum": PARTICLE_RELATIVE_PARAMETER_RANGES["motion_speed_multiplier"][1],
    },
    "diffusion_multiplier": {
        "source_key": "diffusion_multiplier",
        "identity": 1.0,
        "minimum": PARTICLE_RELATIVE_PARAMETER_RANGES["diffusion_multiplier"][0],
        "maximum": PARTICLE_RELATIVE_PARAMETER_RANGES["diffusion_multiplier"][1],
    },
}


def _as_dict(value: Any) -> Dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _find_module(modules: Sequence[Dict[str, Any]], module_id: str) -> Dict[str, Any]:
    return next(
        (
            module
            for module in modules
            if isinstance(module, dict) and module.get("module_id") == module_id
        ),
        {},
    )


def _module_output(module: Dict[str, Any], output_key: str) -> Dict[str, Any]:
    graph = _as_dict(module.get("module_graph"))
    nodes = graph.get("nodes") if isinstance(graph.get("nodes"), list) else []
    for node in nodes:
        if not isinstance(node, dict) or node.get("node_type") != "module_output":
            continue
        outputs = _as_dict(node.get("outputs"))
        if isinstance(outputs.get(output_key), dict):
            return deepcopy(outputs[output_key])
    outputs = _as_dict(module.get("outputs"))
    return deepcopy(_as_dict(outputs.get(output_key)))


def _number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if math.isfinite(parsed) else None


def _stable_state_list(value: Any) -> bool:
    return (
        isinstance(value, list)
        and len(value) == len(VISUAL_EXPRESSION_ALLOWED_STATES)
        and all(isinstance(item, str) for item in value)
        and set(value) == set(VISUAL_EXPRESSION_ALLOWED_STATES)
    )


def _stable_lifecycle_list(value: Any, expected: Sequence[str]) -> bool:
    return isinstance(value, list) and value == list(expected)


def build_visual_expression_mapping(
    modules: Sequence[Dict[str, Any]],
) -> tuple[Dict[str, Any], List[Dict[str, str]]]:
    """Build a deterministic projection without calculating final visual values."""

    defaulted_paths: set[str] = set()
    clamped_paths: set[str] = set()
    a1 = _find_module(modules, DETAIL_BEHAVIOR_MODULE_ID)
    a2 = _find_module(modules, PARTICLE_AVATAR_MODULE_ID)

    a1_config = _as_dict(a1.get("config"))
    output_contract = _as_dict(a1_config.get("output_contract"))
    state_contract = _as_dict(output_contract.get("expression_state"))
    intensity_contract = _as_dict(output_contract.get("expression_intensity"))

    raw_allowed_states = state_contract.get("allowed")
    if _stable_state_list(raw_allowed_states):
        allowed_states = list(VISUAL_EXPRESSION_ALLOWED_STATES)
    else:
        allowed_states = list(VISUAL_EXPRESSION_ALLOWED_STATES)
        defaulted_paths.add("visual_expression_mapping.allowed_states")

    raw_default_state = state_contract.get("default")
    default_state = (
        raw_default_state
        if raw_default_state == VISUAL_EXPRESSION_DEFAULT_STATE
        else VISUAL_EXPRESSION_DEFAULT_STATE
    )
    if raw_default_state != VISUAL_EXPRESSION_DEFAULT_STATE:
        defaulted_paths.add("visual_expression_mapping.default_state")

    raw_invalid_fallback = state_contract.get("invalid_fallback")
    if raw_invalid_fallback != VISUAL_EXPRESSION_DEFAULT_STATE:
        defaulted_paths.add("visual_expression_mapping.fallback_policy.invalid_state")

    intensity_minimum = _number(intensity_contract.get("minimum"))
    intensity_maximum = _number(intensity_contract.get("maximum"))
    if (
        intensity_minimum != VISUAL_EXPRESSION_INTENSITY_RANGE["minimum"]
        or intensity_maximum != VISUAL_EXPRESSION_INTENSITY_RANGE["maximum"]
    ):
        intensity_range = deepcopy(VISUAL_EXPRESSION_INTENSITY_RANGE)
        defaulted_paths.add("visual_expression_mapping.intensity_range")
    else:
        intensity_range = {
            "minimum": intensity_minimum,
            "maximum": intensity_maximum,
        }

    a2_output = _module_output(a2, PARTICLE_AVATAR_OUTPUT_KEY)
    base_color_config = _as_dict(a2_output.get("base_color_config"))
    raw_priority = base_color_config.get("priority")
    if (
        isinstance(raw_priority, list)
        and tuple(raw_priority) == VISUAL_EXPRESSION_BASE_COLOR_PRIORITY
    ):
        base_color_priority = list(raw_priority)
    else:
        base_color_priority = list(VISUAL_EXPRESSION_BASE_COLOR_PRIORITY)
        defaulted_paths.add("visual_expression_mapping.base_color_policy.priority")
    resident_default_base_color = base_color_config.get(
        "resident_default_base_color"
    )
    if not isinstance(resident_default_base_color, str):
        resident_default_base_color = None
        defaulted_paths.add(
            "visual_expression_mapping.base_color_policy.resident_default_base_color"
        )

    range_config = _as_dict(a2_output.get("parameter_ranges"))
    source_ranges: Dict[str, tuple[float, float]] = {}
    for spec in VISUAL_EXPRESSION_PARAMETER_SPECS.values():
        source_key = str(spec["source_key"])
        expected_minimum = float(spec["minimum"])
        expected_maximum = float(spec["maximum"])
        configured_range = _as_dict(range_config.get(source_key))
        configured_minimum = _number(configured_range.get("minimum"))
        configured_maximum = _number(configured_range.get("maximum"))
        if (
            configured_minimum == expected_minimum
            and configured_maximum == expected_maximum
        ):
            source_ranges[source_key] = (
                configured_minimum,
                configured_maximum,
            )
        else:
            source_ranges[source_key] = (expected_minimum, expected_maximum)
            defaulted_paths.add(
                f"visual_expression_mapping.particle_core_mapping.range.{source_key}"
            )

    relative_mapping = _as_dict(a2_output.get("expression_relative_mapping"))
    raw_state_mappings = _as_dict(relative_mapping.get("state_mappings"))
    particle_core_mapping: Dict[str, Dict[str, float]] = {}
    for state in VISUAL_EXPRESSION_ALLOWED_STATES:
        raw_state_mapping = _as_dict(raw_state_mappings.get(state))
        projected_state: Dict[str, float] = {}
        for output_key, spec in VISUAL_EXPRESSION_PARAMETER_SPECS.items():
            source_key = str(spec["source_key"])
            identity = float(spec["identity"])
            minimum, maximum = source_ranges[source_key]
            path = f"visual_expression_mapping.particle_core_mapping.{state}.{output_key}"
            parsed = _number(raw_state_mapping.get(source_key))
            if state == VISUAL_EXPRESSION_DEFAULT_STATE:
                if parsed != identity:
                    defaulted_paths.add(path)
                projected_state[output_key] = identity
                continue
            if parsed is None:
                projected_state[output_key] = identity
                defaulted_paths.add(path)
                continue
            bounded = min(maximum, max(minimum, parsed))
            projected_state[output_key] = bounded
            if bounded != parsed:
                clamped_paths.add(path)
        particle_core_mapping[state] = projected_state

    transition_rules = _as_dict(a2_output.get("transition_rules"))

    def transition_number(field_key: str) -> float:
        path = f"visual_expression_mapping.transition_policy.{field_key}"
        fallback = float(VISUAL_EXPRESSION_TRANSITION_DEFAULTS[field_key])
        parsed = _number(transition_rules.get(field_key))
        if parsed is None:
            defaulted_paths.add(path)
            return fallback
        bounded = min(10.0, max(0.0, parsed))
        if bounded != parsed:
            clamped_paths.add(path)
        return bounded

    transition_style = transition_rules.get("transition_style")
    if transition_style != "smooth":
        transition_style = "smooth"
        defaulted_paths.add(
            "visual_expression_mapping.transition_policy.transition_style"
        )
    repeat_same_state = transition_rules.get("same_state_retriggers_transition")
    if not isinstance(repeat_same_state, bool):
        repeat_same_state = False
        defaulted_paths.add(
            "visual_expression_mapping.transition_policy.repeat_same_state_restarts_transition"
        )
    continue_from_current = transition_rules.get(
        "new_state_continues_from_current_visual"
    )
    if not isinstance(continue_from_current, bool):
        continue_from_current = True
        defaulted_paths.add(
            "visual_expression_mapping.transition_policy.continue_from_current_visual_value"
        )

    lifecycle = _as_dict(a2_output.get("lifecycle_priority"))
    raw_override_states = lifecycle.get("override_states")
    raw_composable_states = lifecycle.get("composable_states")
    if _stable_lifecycle_list(
        raw_override_states, VISUAL_EXPRESSION_LIFECYCLE_OVERRIDE_STATES
    ):
        override_states = list(raw_override_states)
    else:
        override_states = list(VISUAL_EXPRESSION_LIFECYCLE_OVERRIDE_STATES)
        defaulted_paths.add(
            "visual_expression_mapping.lifecycle_priority.override_states"
        )
    if _stable_lifecycle_list(
        raw_composable_states, VISUAL_EXPRESSION_LIFECYCLE_COMPOSABLE_STATES
    ):
        composable_states = list(raw_composable_states)
    else:
        composable_states = list(VISUAL_EXPRESSION_LIFECYCLE_COMPOSABLE_STATES)
        defaulted_paths.add(
            "visual_expression_mapping.lifecycle_priority.composable_states"
        )

    projection = {
        "protocol_version": VISUAL_EXPRESSION_PROJECTION_PROTOCOL_VERSION,
        "content_revision": VISUAL_EXPRESSION_PROJECTION_CONTENT_REVISION,
        "allowed_states": allowed_states,
        "default_state": default_state,
        "intensity_range": intensity_range,
        "base_color_policy": {
            "priority": base_color_priority,
            "resident_default_base_color": resident_default_base_color,
            "particle_core_fallback": VISUAL_EXPRESSION_PARTICLE_CORE_FALLBACK,
        },
        "particle_core_mapping": particle_core_mapping,
        "transition_policy": {
            "transition_duration": transition_number("transition_duration"),
            "minimum_hold_duration": transition_number("minimum_hold_duration"),
            "transition_style": transition_style,
            "repeat_same_state_restarts_transition": repeat_same_state,
            "continue_from_current_visual_value": continue_from_current,
        },
        "lifecycle_priority": {
            "override_states": override_states,
            "composable_states": composable_states,
        },
        "fallback_policy": {
            "invalid_state": VISUAL_EXPRESSION_DEFAULT_STATE,
            "missing_state": VISUAL_EXPRESSION_DEFAULT_STATE,
            "clamp_intensity": True,
            "clamp_mapping_values": True,
        },
        "abstract_bust_mapping": {"status": "reserved"},
    }
    diagnostics: List[Dict[str, str]] = []
    if clamped_paths:
        diagnostics.append(
            {
                "code": "DR_VISUAL_EXPRESSION_MAPPING_CLAMPED",
                "message": (
                    "Visual expression mapping values were clamped to protocol ranges: "
                    + ", ".join(sorted(clamped_paths))
                ),
                "path": "visual_expression_mapping.particle_core_mapping",
            }
        )
    if defaulted_paths:
        diagnostics.append(
            {
                "code": "DR_VISUAL_EXPRESSION_MAPPING_DEFAULTED",
                "message": (
                    "Visual expression mapping used protocol-safe defaults for: "
                    + ", ".join(sorted(defaulted_paths))
                ),
                "path": "visual_expression_mapping",
            }
        )
    return projection, diagnostics
