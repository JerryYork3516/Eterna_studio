"""Compile A1/A2 module configuration into a read-only visual projection."""

from __future__ import annotations

import math
import re
from copy import deepcopy
from typing import Any, Dict, List, Sequence

from ..registry.module_catalog import (
    DETAIL_BEHAVIOR_MODULE_ID,
    EXPRESSION_STATE_NODE_IDS,
    EXPRESSION_STATE_VALUES,
    PARTICLE_AVATAR_MODULE_ID,
    PARTICLE_AVATAR_NODE_IDS,
    PARTICLE_AVATAR_OUTPUT_KEY,
    PARTICLE_RELATIVE_PARAMETER_RANGES,
)

VISUAL_EXPRESSION_PROJECTION_CONTENT_REVISION = (
    "stage7_4_11_selection_transition_projection_completion_v1"
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
    "uses_accumulated_idle_time_as_progress": False,
    "minimum_hold_prevents_flicker": True,
    "transition_executor": "aftelle",
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
VISUAL_EXPRESSION_SAFE_PARAMETER_DEFAULTS = {
    output_key: float(spec["identity"])
    for output_key, spec in VISUAL_EXPRESSION_PARAMETER_SPECS.items()
}
_HEX_COLOR_PATTERN = re.compile(r"^#[0-9a-fA-F]{6}$")


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


def _node_id(node: Dict[str, Any]) -> str:
    value = node.get("node_id") or node.get("id")
    return value if isinstance(value, str) else ""


def _expression_selection_rules(module: Dict[str, Any]) -> List[str]:
    graph = _as_dict(module.get("module_graph"))
    nodes = graph.get("nodes") if isinstance(graph.get("nodes"), list) else []
    selection_node = next(
        (
            node
            for node in nodes
            if isinstance(node, dict)
            and _node_id(node)
            == EXPRESSION_STATE_NODE_IDS["state_selection_rules"]
        ),
        {},
    )
    selection_rules = _as_dict(selection_node.get("params")).get(
        "selection_rules"
    )
    if not isinstance(selection_rules, list) or not all(
        isinstance(rule, str) for rule in selection_rules
    ):
        return []
    return deepcopy(selection_rules)


def _node_field_value(
    node: Dict[str, Any], field_key: str
) -> tuple[bool, Any]:
    params = _as_dict(node.get("params"))
    for fields in (params.get("fields"), node.get("fields")):
        if not isinstance(fields, list):
            continue
        for field in fields:
            if not isinstance(field, dict):
                continue
            candidate_key = field.get("field_key") or field.get("field_id")
            if candidate_key != field_key:
                continue
            value_key = (
                "value"
                if "value" in field and "field_value" not in field
                else "field_value"
            )
            return True, deepcopy(field.get(value_key))
    return False, None


def _state_mapping_value(
    mapping: Any, state: str, source_key: str
) -> tuple[bool, Any]:
    state_mapping = _as_dict(_as_dict(mapping).get(state))
    candidate_keys = [source_key]
    if source_key == "color_temperature_offset":
        candidate_keys.append("temperature_shift")
    for candidate_key in candidate_keys:
        if candidate_key in state_mapping:
            return True, deepcopy(state_mapping[candidate_key])
    return False, None


def _input_relative_fields_are_neutral_identities(
    input_node: Dict[str, Any],
) -> bool:
    for state in VISUAL_EXPRESSION_ALLOWED_STATES:
        if state == VISUAL_EXPRESSION_DEFAULT_STATE:
            continue
        for output_key, spec in VISUAL_EXPRESSION_PARAMETER_SPECS.items():
            source_key = str(spec["source_key"])
            found, raw_value = _node_field_value(
                input_node, f"{state}_{source_key}"
            )
            if not found or _number(raw_value) != float(spec["identity"]):
                return False
    return True


def particle_relative_mapping_source_value(
    module: Dict[str, Any], state: str, source_key: str
) -> tuple[bool, Any]:
    """Read one relative parameter using the Stage 7.4.11 source priority."""

    graph = _as_dict(module.get("module_graph"))
    nodes = graph.get("nodes") if isinstance(graph.get("nodes"), list) else []
    mapping_node = next(
        (
            node
            for node in nodes
            if isinstance(node, dict)
            and _node_id(node)
            == PARTICLE_AVATAR_NODE_IDS["expression_relative_mapping"]
        ),
        {},
    )
    field_key = f"{state}_{source_key}"

    # The current expression-relative-mapping node is authoritative.
    found, value = _node_field_value(mapping_node, field_key)
    if found:
        return True, value
    mapping_params = _as_dict(mapping_node.get("params"))
    mapping_found, mapping_value = _state_mapping_value(
        mapping_params.get("state_mappings"), state, source_key
    )

    # The current normalized module configuration is the next source.
    config_input = next(
        (
            node
            for node in nodes
            if isinstance(node, dict)
            and _node_id(node) == PARTICLE_AVATAR_NODE_IDS["config_input"]
        ),
        {},
    )
    if (
        mapping_found
        and _input_relative_fields_are_neutral_identities(config_input)
    ):
        return True, mapping_value
    found, value = _node_field_value(config_input, field_key)
    if found:
        return True, value
    if mapping_found:
        return True, mapping_value
    module_config = _as_dict(module.get("config"))
    normalized_mapping = _as_dict(
        module_config.get("expression_relative_mapping")
    )
    found, value = _state_mapping_value(
        normalized_mapping.get("state_mappings"), state, source_key
    )
    if found:
        return True, value

    # Output mirrors are compatibility fallbacks, never higher-priority inputs.
    module_outputs = _as_dict(module.get("outputs"))
    mirror = _as_dict(module_outputs.get(PARTICLE_AVATAR_OUTPUT_KEY))
    mirror_mapping = _as_dict(mirror.get("expression_relative_mapping"))
    found, value = _state_mapping_value(
        mirror_mapping.get("state_mappings"), state, source_key
    )
    if found:
        return True, value
    for node in nodes:
        if not isinstance(node, dict) or node.get("node_type") != "module_output":
            continue
        node_outputs = _as_dict(node.get("outputs"))
        mirror = _as_dict(node_outputs.get(PARTICLE_AVATAR_OUTPUT_KEY))
        mirror_mapping = _as_dict(mirror.get("expression_relative_mapping"))
        found, value = _state_mapping_value(
            mirror_mapping.get("state_mappings"), state, source_key
        )
        if found:
            return True, value
    return False, None


def _number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if math.isfinite(parsed) else None


def normalize_expression_state(value: Any) -> tuple[str, bool]:
    """Normalize a saved expression state without admitting lifecycle states."""

    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in VISUAL_EXPRESSION_ALLOWED_STATES:
            return normalized, normalized != value
    return VISUAL_EXPRESSION_DEFAULT_STATE, True


def normalize_expression_intensity(value: Any) -> tuple[float, bool, bool]:
    """Return value, whether it changed, and whether a finite value was clamped."""

    parsed = _number(value)
    if parsed is None:
        return 0.0, True, False
    bounded = min(1.0, max(0.0, parsed))
    return bounded, bounded != parsed, bounded != parsed


def valid_visual_base_color(value: Any) -> bool:
    return isinstance(value, str) and bool(_HEX_COLOR_PATTERN.fullmatch(value))


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
    selection_rules = _expression_selection_rules(a1)

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
    if not valid_visual_base_color(resident_default_base_color):
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

    parameter_ranges = {
        "expression_intensity": deepcopy(intensity_range),
    }
    for output_key, spec in VISUAL_EXPRESSION_PARAMETER_SPECS.items():
        source_key = str(spec["source_key"])
        minimum, maximum = source_ranges[source_key]
        parameter_ranges[output_key] = {
            "minimum": minimum,
            "maximum": maximum,
        }

    particle_core_mapping: Dict[str, Dict[str, float]] = {}
    for state in VISUAL_EXPRESSION_ALLOWED_STATES:
        projected_state: Dict[str, float] = {}
        for output_key, spec in VISUAL_EXPRESSION_PARAMETER_SPECS.items():
            source_key = str(spec["source_key"])
            identity = float(spec["identity"])
            minimum, maximum = source_ranges[source_key]
            path = f"visual_expression_mapping.particle_core_mapping.{state}.{output_key}"
            found, raw_value = particle_relative_mapping_source_value(
                a2, state, source_key
            )
            parsed = _number(raw_value) if found else None
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
        "parameter_ranges": parameter_ranges,
        "state_selection_policy": {
            "selection_source": "runtime_core",
            "state_field": "expression_state",
            "intensity_field": "expression_intensity",
            "selection_rules": selection_rules,
            "allowed_states": list(allowed_states),
            "default_state": default_state,
            "missing_state_fallback": default_state,
            "invalid_state_fallback": default_state,
            "single_state_per_turn": True,
            "resident_expression_only": True,
            "user_emotion_diagnosis": False,
            "renderer_parameters_allowed": False,
            "lifecycle_state_separated": True,
        },
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
            "uses_accumulated_idle_time_as_progress": (
                VISUAL_EXPRESSION_TRANSITION_DEFAULTS[
                    "uses_accumulated_idle_time_as_progress"
                ]
            ),
            "minimum_hold_prevents_flicker": (
                VISUAL_EXPRESSION_TRANSITION_DEFAULTS[
                    "minimum_hold_prevents_flicker"
                ]
            ),
            "transition_executor": VISUAL_EXPRESSION_TRANSITION_DEFAULTS[
                "transition_executor"
            ],
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


def normalize_visual_expression_mapping(
    value: Any,
) -> tuple[Dict[str, Any], List[Dict[str, str]]]:
    """Normalize an optional/legacy top-level projection without mutating its DR."""

    safe_projection, _ = build_visual_expression_mapping([])
    raw = _as_dict(value)
    diagnostics: List[Dict[str, str]] = []
    diagnostic_keys: set[tuple[str, str]] = set()

    def add_diagnostic(code: str, message: str, path: str) -> None:
        key = (code, path)
        if key in diagnostic_keys:
            return
        diagnostic_keys.add(key)
        diagnostics.append({"code": code, "message": message, "path": path})

    if not raw:
        add_diagnostic(
            "DR_VISUAL_EXPRESSION_LEGACY_MAPPING_MISSING",
            "Legacy resident has no visual expression mapping; compatibility defaults were loaded.",
            "visual_expression_mapping",
        )
        return safe_projection, diagnostics

    normalized = deepcopy(safe_projection)
    base_color_policy = _as_dict(raw.get("base_color_policy"))
    resident_color = base_color_policy.get("resident_default_base_color")
    if valid_visual_base_color(resident_color):
        normalized["base_color_policy"]["resident_default_base_color"] = resident_color
    elif resident_color not in (None, ""):
        add_diagnostic(
            "DR_VISUAL_EXPRESSION_BASE_COLOR_INVALID",
            "Resident default base color is invalid; particle core fallback will be used.",
            "visual_expression_mapping.base_color_policy.resident_default_base_color",
        )

    raw_mapping = _as_dict(
        raw.get("particle_core_mapping") or raw.get("state_mappings")
    )
    if not raw_mapping:
        add_diagnostic(
            "DR_PARTICLE_MAPPING_DEFAULTED",
            "Particle mapping is missing; safe relative defaults were used.",
            "visual_expression_mapping.particle_core_mapping",
        )
    normalized_mapping: Dict[str, Dict[str, float]] = {}
    for state in VISUAL_EXPRESSION_ALLOWED_STATES:
        raw_state_value = raw_mapping.get(state)
        if raw_state_value is None:
            raw_state_value = next(
                (
                    candidate
                    for raw_state_name, candidate in raw_mapping.items()
                    if isinstance(raw_state_name, str)
                    and raw_state_name.strip().lower() == state
                ),
                None,
            )
        raw_state = _as_dict(raw_state_value)
        state_mapping: Dict[str, float] = {}
        if not raw_state:
            add_diagnostic(
                "DR_PARTICLE_MAPPING_DEFAULTED",
                "Particle mapping is incomplete; safe relative defaults were used.",
                f"visual_expression_mapping.particle_core_mapping.{state}",
            )
        for output_key, spec in VISUAL_EXPRESSION_PARAMETER_SPECS.items():
            source_key = str(spec["source_key"])
            raw_value = raw_state.get(output_key)
            if raw_value is None and source_key != output_key:
                raw_value = raw_state.get(source_key)
            identity = float(spec["identity"])
            minimum = float(spec["minimum"])
            maximum = float(spec["maximum"])
            path = (
                "visual_expression_mapping.particle_core_mapping."
                f"{state}.{output_key}"
            )
            parsed = _number(raw_value)
            if state == VISUAL_EXPRESSION_DEFAULT_STATE:
                state_mapping[output_key] = identity
                if parsed is not None and parsed != identity:
                    add_diagnostic(
                        "DR_PARTICLE_MAPPING_DEFAULTED",
                        "Neutral particle mapping was restored to identity values.",
                        path,
                    )
                continue
            if parsed is None:
                state_mapping[output_key] = identity
                add_diagnostic(
                    "DR_PARTICLE_MAPPING_DEFAULTED",
                    "Particle mapping value is missing or non-numeric; a safe default was used.",
                    path,
                )
                continue
            bounded = min(maximum, max(minimum, parsed))
            state_mapping[output_key] = bounded
            if bounded != parsed:
                code = (
                    "DR_PARTICLE_BRIGHTNESS_MULTIPLIER_OUT_OF_RANGE"
                    if output_key == "brightness_multiplier"
                    else "DR_PARTICLE_RELATIVE_VALUE_OUT_OF_RANGE"
                )
                add_diagnostic(
                    code,
                    "Particle relative value was clamped to its allowed range.",
                    path,
                )
        normalized_mapping[state] = state_mapping
    normalized["particle_core_mapping"] = normalized_mapping

    raw_transition = _as_dict(raw.get("transition_policy"))
    for field_key in ("transition_duration", "minimum_hold_duration"):
        parsed = _number(raw_transition.get(field_key))
        path = f"visual_expression_mapping.transition_policy.{field_key}"
        if parsed is None:
            normalized["transition_policy"][field_key] = float(
                VISUAL_EXPRESSION_TRANSITION_DEFAULTS[field_key]
            )
            add_diagnostic(
                "DR_TRANSITION_TIME_INVALID_FALLBACK",
                "Transition time is missing or non-numeric; a safe default was used.",
                path,
            )
            continue
        bounded = min(10.0, max(0.0, parsed))
        normalized["transition_policy"][field_key] = bounded
        if bounded != parsed:
            add_diagnostic(
                "DR_TRANSITION_TIME_INVALID_FALLBACK",
                "Transition time was limited to a safe non-negative range.",
                path,
            )

    if raw_transition.get("transition_style") != "smooth":
        add_diagnostic(
            "DR_TRANSITION_STYLE_INVALID_FALLBACK",
            "Transition style is invalid; smooth transition was used.",
            "visual_expression_mapping.transition_policy.transition_style",
        )
    normalized["transition_policy"]["transition_style"] = "smooth"
    normalized["transition_policy"]["repeat_same_state_restarts_transition"] = False
    normalized["transition_policy"]["continue_from_current_visual_value"] = True
    return normalized, diagnostics
