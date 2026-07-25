"""Stage 7.4.11 A3 top-level visual expression projection contracts."""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

from app.dr.v3.dr_v0_3_schema import (
    DRDocumentV03,
    VisualExpressionMappingV03,
)
from app.registry.module_catalog import (
    PARTICLE_MAPPING_SOURCE_PRIORITY_FIX_REVISION,
    get_module_catalog,
)
from app.services.dr_compiler import compile_dr_result_v0_3, mock_load_dr_v0_3
from app.services.visual_expression_projection import (
    VISUAL_EXPRESSION_PROJECTION_CONTENT_REVISION,
    build_visual_expression_mapping,
)


_STATES = ["neutral", "calm", "caring", "subdued", "joyful"]
_RELATIVE_KEYS = {
    "brightness_multiplier",
    "saturation_multiplier",
    "temperature_shift",
    "energy_multiplier",
    "motion_speed_multiplier",
    "diffusion_multiplier",
}
_RANGES = {
    "brightness_multiplier": (0.7, 1.25),
    "saturation_multiplier": (0.65, 1.2),
    "temperature_shift": (-0.15, 0.15),
    "energy_multiplier": (0.7, 1.25),
    "motion_speed_multiplier": (0.75, 1.2),
    "diffusion_multiplier": (0.75, 1.25),
}
_PARAMETER_RANGES = {
    "expression_intensity": {"minimum": 0.0, "maximum": 1.0},
    "brightness_multiplier": {"minimum": 0.7, "maximum": 1.25},
    "saturation_multiplier": {"minimum": 0.65, "maximum": 1.2},
    "temperature_shift": {"minimum": -0.15, "maximum": 0.15},
    "energy_multiplier": {"minimum": 0.7, "maximum": 1.25},
    "motion_speed_multiplier": {"minimum": 0.75, "maximum": 1.2},
    "diffusion_multiplier": {"minimum": 0.75, "maximum": 1.25},
}


def _workflow() -> dict:
    return {
        "name": "Stage 7.4.11 visual expression projection",
        "nodes": [{"node_id": f"layer_{index}"} for index in range(1, 14)],
    }


def _modules() -> list[dict]:
    return [module.model_dump(mode="json") for module in get_module_catalog()]


def _compile(modules: list[dict] | None = None) -> dict:
    canvas = {"workflow": _workflow()}
    if modules is not None:
        canvas["modules"] = modules
    result = compile_dr_result_v0_3(canvas)
    assert result["valid"] is True, result["errors"]
    return result


def _particle_fields(modules: list[dict]) -> dict[str, dict]:
    module = next(
        item for item in modules if item["module_id"] == "particle_avatar"
    )
    input_node = next(
        node
        for node in module["module_graph"]["nodes"]
        if node["node_id"] == "particle_visual_config_input"
    )
    return {
        field["field_key"]: field for field in input_node["params"]["fields"]
    }


def _locales() -> tuple[dict, dict]:
    root = Path(__file__).resolve().parents[3]
    zh = json.loads((root / "apps/web/locales/zh.json").read_text())
    en = json.loads((root / "apps/web/locales/en.json").read_text())
    return zh, en


def test_a1_a2_compile_to_stable_top_level_visual_expression_mapping():
    first = _compile()
    second = _compile()
    dr = first["compiled_dr"]
    projection = dr["visual_expression_mapping"]

    assert projection == second["compiled_dr"]["visual_expression_mapping"]
    assert "visual_expression_mapping" not in dr["payload"]
    assert "visual_state" not in dr
    assert "expression_state" not in dr
    assert "runtime_visual_state" not in dr
    assert projection["protocol_version"] == "1.0"
    assert projection["content_revision"] == (
        VISUAL_EXPRESSION_PROJECTION_CONTENT_REVISION
    )
    assert projection["allowed_states"] == _STATES
    assert projection["default_state"] == "neutral"
    assert projection["intensity_range"] == {"minimum": 0.0, "maximum": 1.0}
    assert projection["parameter_ranges"] == _PARAMETER_RANGES
    assert list(projection["parameter_ranges"]) == list(_PARAMETER_RANGES)
    assert projection["state_selection_policy"] == {
        "selection_source": "runtime_core",
        "state_field": "expression_state",
        "intensity_field": "expression_intensity",
        "allowed_states": _STATES,
        "default_state": "neutral",
        "missing_state_fallback": "neutral",
        "invalid_state_fallback": "neutral",
        "single_state_per_turn": True,
        "resident_expression_only": True,
        "user_emotion_diagnosis": False,
        "renderer_parameters_allowed": False,
        "lifecycle_state_separated": True,
    }
    assert (
        projection["state_selection_policy"]["allowed_states"]
        == projection["allowed_states"]
    )
    assert projection["fallback_policy"] == {
        "invalid_state": "neutral",
        "missing_state": "neutral",
        "clamp_intensity": True,
        "clamp_mapping_values": True,
    }

    assert projection["base_color_policy"] == {
        "priority": [
            "user_current_base_color",
            "resident_default_base_color",
            "particle_core_default_gray_white",
        ],
        "resident_default_base_color": "#7aa2f7",
        "particle_core_fallback": "default_gray_white",
    }
    mapping = projection["particle_core_mapping"]
    assert list(mapping) == _STATES
    for state in _STATES:
        assert set(mapping[state]) == _RELATIVE_KEYS
        assert all(isinstance(value, (int, float)) for value in mapping[state].values())
        for field_key, (minimum, maximum) in _RANGES.items():
            assert minimum <= mapping[state][field_key] <= maximum
    assert mapping["neutral"] == {
        "brightness_multiplier": 1.0,
        "saturation_multiplier": 1.0,
        "temperature_shift": 0.0,
        "energy_multiplier": 1.0,
        "motion_speed_multiplier": 1.0,
        "diffusion_multiplier": 1.0,
    }
    mapping_json = json.dumps(mapping, ensure_ascii=False).lower()
    for forbidden in (
        "fixed_color",
        "primary_color",
        "secondary_color",
        "highlight_color",
        "yellow",
        "blue",
        "gold",
        "黄色",
        "蓝色",
        "金色",
    ):
        assert forbidden not in mapping_json

    assert projection["transition_policy"] == {
        "transition_duration": 0.6,
        "minimum_hold_duration": 0.35,
        "transition_style": "smooth",
        "repeat_same_state_restarts_transition": False,
        "continue_from_current_visual_value": True,
    }
    lifecycle = projection["lifecycle_priority"]
    assert lifecycle["override_states"] == ["error", "loading", "exit"]
    assert lifecycle["composable_states"] == ["idle", "thinking", "speaking"]
    assert set(lifecycle["override_states"]).isdisjoint(_STATES)
    assert set(lifecycle["composable_states"]).isdisjoint(_STATES)
    assert projection["abstract_bust_mapping"] == {"status": "reserved"}

    runtime_view = {"visual_expression_mapping": deepcopy(projection)}
    assert runtime_view["visual_expression_mapping"] == projection
    assert "modules" not in runtime_view
    assert dr["dr_version"] == "0.3"
    assert dr["dr_schema_version"] == "0.3.0"
    assert dr["manifest"]["required_capabilities"] == ["llm", "memory", "lattice"]
    assert dr["payload"]["lattice_config"]["emotion"] == "neutral"
    assert dr["lattice_config"] == dr["payload"]["lattice_config"]
    VisualExpressionMappingV03.model_validate(projection)


def test_aftelle_projection_completion_preserves_frozen_mapping_and_contract():
    first = _compile()["compiled_dr"]
    second = _compile()["compiled_dr"]
    projection = first["visual_expression_mapping"]
    mapping = projection["particle_core_mapping"]
    policy = projection["state_selection_policy"]

    assert projection == second["visual_expression_mapping"]
    assert projection["content_revision"] == (
        "stage7_4_11_aftelle_projection_completion_v1"
    )
    assert projection["parameter_ranges"] == _PARAMETER_RANGES
    assert policy["selection_source"] == "runtime_core"
    assert policy["state_field"] == "expression_state"
    assert policy["intensity_field"] == "expression_intensity"
    assert policy["allowed_states"] == projection["allowed_states"] == _STATES
    assert policy["default_state"] == "neutral"
    assert policy["missing_state_fallback"] == "neutral"
    assert policy["invalid_state_fallback"] == "neutral"
    assert policy["single_state_per_turn"] is True
    assert policy["resident_expression_only"] is True
    assert policy["user_emotion_diagnosis"] is False
    assert policy["renderer_parameters_allowed"] is False
    assert policy["lifecycle_state_separated"] is True
    assert mapping["caring"]["brightness_multiplier"] == 1.06
    assert mapping["subdued"]["energy_multiplier"] == 0.78
    assert mapping["joyful"]["diffusion_multiplier"] == 1.14
    assert first["dr_version"] == "0.3"
    assert first["dr_schema_version"] == "0.3.0"
    assert first["manifest"]["required_capabilities"] == [
        "llm",
        "memory",
        "lattice",
    ]


def test_legacy_projection_without_a6_fields_remains_loadable():
    current = _compile()["compiled_dr"]
    legacy = deepcopy(current)
    legacy_projection = legacy["visual_expression_mapping"]
    legacy_projection["content_revision"] = (
        "stage7_4_11_visual_expression_projection_v1"
    )
    legacy_projection.pop("parameter_ranges")
    legacy_projection.pop("state_selection_policy")

    parsed_legacy = VisualExpressionMappingV03.model_validate(
        legacy_projection
    )
    assert parsed_legacy.parameter_ranges is None
    assert parsed_legacy.state_selection_policy is None

    loaded = mock_load_dr_v0_3(legacy)
    assert loaded["loaded"] is True
    assert loaded["visual_expression_mapping"]["parameter_ranges"] == (
        _PARAMETER_RANGES
    )
    assert loaded["visual_expression_mapping"]["state_selection_policy"][
        "allowed_states"
    ] == _STATES
    assert "parameter_ranges" not in legacy_projection
    assert "state_selection_policy" not in legacy_projection


def test_particle_mapping_current_node_synchronizes_output_and_top_projection():
    modules = _modules()
    particle = next(
        module for module in modules if module["module_id"] == "particle_avatar"
    )
    input_node = next(
        node
        for node in particle["module_graph"]["nodes"]
        if node["node_id"] == "particle_visual_config_input"
    )
    mapping_node = next(
        node
        for node in particle["module_graph"]["nodes"]
        if node["node_id"] == "particle_expression_state_relative_mapping"
    )
    output_node = next(
        node
        for node in particle["module_graph"]["nodes"]
        if node["node_id"] == "particle_mapping_config_output"
    )
    expected_internal = deepcopy(mapping_node["params"]["state_mappings"])
    identity_internal = {
        "brightness_multiplier": 1.0,
        "saturation_multiplier": 1.0,
        "color_temperature_offset": 0.0,
        "energy_multiplier": 1.0,
        "motion_speed_multiplier": 1.0,
        "diffusion_multiplier": 1.0,
    }

    # Reproduce the regression: stale config-input fields, normalized config,
    # output mirrors, and legacy copies all contain neutral identities.
    for field in input_node["params"]["fields"]:
        field_key = field["field_key"]
        for state in _STATES[1:]:
            prefix = f"{state}_"
            if field_key.startswith(prefix):
                field["field_value"] = identity_internal[field_key[len(prefix) :]]
    input_node["params"]["legacy_fields"] = deepcopy(
        input_node["params"]["fields"]
    )
    particle["config"]["expression_relative_mapping"] = {
        "state_mappings": {
            state: deepcopy(identity_internal) for state in _STATES
        }
    }
    stale_output = deepcopy(particle["outputs"]["particle_mapping_config"])
    stale_output["expression_relative_mapping"]["state_mappings"] = {
        state: deepcopy(identity_internal) for state in _STATES
    }
    particle["outputs"]["particle_mapping_config"] = deepcopy(stale_output)
    output_node["outputs"]["particle_mapping_config"] = deepcopy(stale_output)

    # A field saved on the current mapping node is higher priority even than
    # the node's older structured mirror.
    mapping_node["params"]["state_mappings"]["caring"][
        "brightness_multiplier"
    ] = 1.0
    mapping_node["params"]["fields"] = [
        {
            "field_key": "caring_brightness_multiplier",
            "field_value": 1.06,
        }
    ]
    direct_projection, _ = build_visual_expression_mapping([particle])
    assert (
        direct_projection["particle_core_mapping"]["caring"][
            "brightness_multiplier"
        ]
        == 1.06
    )
    assert (
        direct_projection["particle_core_mapping"]["subdued"][
            "energy_multiplier"
        ]
        == 0.78
    )
    assert (
        direct_projection["particle_core_mapping"]["joyful"][
            "diffusion_multiplier"
        ]
        == 1.14
    )

    first = _compile(modules)
    second = _compile(modules)
    dr = first["compiled_dr"]
    compiled_particle = next(
        module
        for module in dr["payload"]["modules"]
        if module["module_id"] == "particle_avatar"
    )
    compiled_mapping_node = next(
        node
        for node in compiled_particle["module_graph"]["nodes"]
        if node["node_id"] == "particle_expression_state_relative_mapping"
    )
    compiled_output = compiled_particle["outputs"]["particle_mapping_config"]
    compiled_output_node = next(
        node
        for node in compiled_particle["module_graph"]["nodes"]
        if node["node_id"] == "particle_mapping_config_output"
    )
    output_mapping = compiled_output["expression_relative_mapping"][
        "state_mappings"
    ]
    normalized_config_mapping = compiled_particle["config"][
        "expression_relative_mapping"
    ]["state_mappings"]
    top_mapping = dr["visual_expression_mapping"]["particle_core_mapping"]
    expected_internal["caring"]["brightness_multiplier"] = 1.06

    assert compiled_mapping_node["params"]["state_mappings"] == expected_internal
    assert normalized_config_mapping == expected_internal
    assert output_mapping == expected_internal
    assert (
        compiled_output_node["outputs"]["particle_mapping_config"][
            "expression_relative_mapping"
        ]["state_mappings"]
        == expected_internal
    )
    assert top_mapping == {
        state: {
            (
                "temperature_shift"
                if parameter == "color_temperature_offset"
                else parameter
            ): value
            for parameter, value in values.items()
        }
        for state, values in expected_internal.items()
    }
    neutral = top_mapping["neutral"]
    assert all(top_mapping[state] != neutral for state in _STATES[1:])
    assert top_mapping["caring"]["brightness_multiplier"] == 1.06
    assert top_mapping["subdued"]["energy_multiplier"] == 0.78
    assert top_mapping["joyful"]["diffusion_multiplier"] == 1.14
    assert (
        compiled_particle["config"]["source_priority_revision"]
        == PARTICLE_MAPPING_SOURCE_PRIORITY_FIX_REVISION
    )
    assert (
        compiled_mapping_node["params"]["source_priority_revision"]
        == PARTICLE_MAPPING_SOURCE_PRIORITY_FIX_REVISION
    )
    assert (
        dr["visual_expression_mapping"]
        == second["compiled_dr"]["visual_expression_mapping"]
    )
    module_ids = [module["module_id"] for module in dr["payload"]["modules"]]
    node_ids = [
        node["node_id"] for node in compiled_particle["module_graph"]["nodes"]
    ]
    assert len(module_ids) == len(set(module_ids))
    assert len(node_ids) == len(set(node_ids))


def test_particle_mapping_uses_normalized_config_then_safe_default_only_when_missing():
    modules = _modules()
    particle = next(
        module for module in modules if module["module_id"] == "particle_avatar"
    )
    input_node = next(
        node
        for node in particle["module_graph"]["nodes"]
        if node["node_id"] == "particle_visual_config_input"
    )
    mapping_node = next(
        node
        for node in particle["module_graph"]["nodes"]
        if node["node_id"] == "particle_expression_state_relative_mapping"
    )
    output_node = next(
        node
        for node in particle["module_graph"]["nodes"]
        if node["node_id"] == "particle_mapping_config_output"
    )

    del mapping_node["params"]["state_mappings"]["caring"][
        "brightness_multiplier"
    ]
    del mapping_node["params"]["state_mappings"]["calm"][
        "brightness_multiplier"
    ]
    input_node["params"]["fields"] = [
        field
        for field in input_node["params"]["fields"]
        if field["field_key"]
        not in {
            "caring_brightness_multiplier",
            "calm_brightness_multiplier",
        }
    ]
    particle["config"]["expression_relative_mapping"] = {
        "state_mappings": {
            "caring": {"brightness_multiplier": 1.08},
        }
    }
    for output in (
        particle["outputs"]["particle_mapping_config"],
        output_node["outputs"]["particle_mapping_config"],
    ):
        del output["expression_relative_mapping"]["state_mappings"]["calm"][
            "brightness_multiplier"
        ]
        output["expression_relative_mapping"]["state_mappings"]["caring"][
            "brightness_multiplier"
        ] = 1.0
    particle["config"].pop("validation_compatibility_revision", None)
    particle["module_graph"].pop("validation_compatibility_revision", None)
    for node in particle["module_graph"]["nodes"]:
        node.get("params", {}).pop(
            "validation_compatibility_revision", None
        )

    result = _compile(modules)
    mapping = result["compiled_dr"]["visual_expression_mapping"][
        "particle_core_mapping"
    ]

    assert mapping["caring"]["brightness_multiplier"] == 1.08
    assert mapping["calm"]["brightness_multiplier"] == 1.0


def test_projection_reads_saved_a2_fields_without_calculating_final_color():
    modules = _modules()
    fields = _particle_fields(modules)
    configured = {
        "resident_default_base_color": "#123456",
        "calm_brightness_multiplier": 1.2,
        "caring_color_temperature_offset": 0.12,
        "subdued_energy_multiplier": 0.74,
        "transition_duration": 1.8,
        "minimum_hold_duration": 0.75,
    }
    for field_key, value in configured.items():
        fields[field_key]["field_value"] = value
    before = deepcopy(modules)

    result = _compile(modules)
    projection = result["compiled_dr"]["visual_expression_mapping"]

    assert modules == before
    assert (
        projection["base_color_policy"]["resident_default_base_color"]
        == "#123456"
    )
    assert (
        projection["particle_core_mapping"]["calm"]["brightness_multiplier"]
        == 1.2
    )
    assert (
        projection["particle_core_mapping"]["caring"]["temperature_shift"]
        == 0.12
    )
    assert (
        projection["particle_core_mapping"]["subdued"]["energy_multiplier"]
        == 0.74
    )
    assert projection["transition_policy"]["transition_duration"] == 1.8
    assert projection["transition_policy"]["minimum_hold_duration"] == 0.75
    assert "final_color" not in projection
    assert "final_particle_parameters" not in projection
    assert "interpolated_color" not in projection


def test_legacy_out_of_range_values_are_clamped_and_localized_diagnostic_exists():
    modules = _modules()
    particle_module = next(
        item for item in modules if item["module_id"] == "particle_avatar"
    )
    particle_module["config"].pop("validation_compatibility_revision", None)
    particle_module["module_graph"].pop(
        "validation_compatibility_revision", None
    )
    for node in particle_module["module_graph"]["nodes"]:
        node.get("params", {}).pop("validation_compatibility_revision", None)
    fields = _particle_fields(modules)
    fields["calm_brightness_multiplier"]["field_value"] = 9.0
    fields["caring_saturation_multiplier"]["field_value"] = -2.0
    fields["subdued_color_temperature_offset"]["field_value"] = 4.0
    fields["joyful_energy_multiplier"]["field_value"] = "invalid"
    fields["calm_motion_speed_multiplier"]["field_value"] = 8.0
    fields["subdued_diffusion_multiplier"]["field_value"] = 0.1

    result = _compile(modules)
    projection = result["compiled_dr"]["visual_expression_mapping"]
    mapping = projection["particle_core_mapping"]

    assert mapping["calm"]["brightness_multiplier"] == 1.25
    assert mapping["caring"]["saturation_multiplier"] == 0.65
    assert mapping["subdued"]["temperature_shift"] == 0.15
    assert mapping["joyful"]["energy_multiplier"] == 1.0
    assert mapping["calm"]["motion_speed_multiplier"] == 1.2
    assert mapping["subdued"]["diffusion_multiplier"] == 0.75
    assert list(mapping) == _STATES
    warning_codes = {warning["code"] for warning in result["warnings"]}
    assert "DR_VISUAL_EXPRESSION_MAPPING_CLAMPED" in warning_codes

    zh, en = _locales()
    for prefix in ("audit", "validation"):
        key = f"{prefix}.DR_VISUAL_EXPRESSION_MAPPING_CLAMPED"
        assert zh[key]
        assert en[key]
        assert zh[key] != en[key]
        assert "\ufffd" not in zh[key]
        assert "\ufffd" not in en[key]
    assert zh["layer10.particleAvatar.validation.brightnessMultiplier"]
    assert en["layer10.particleAvatar.validation.brightnessMultiplier"]


def test_visual_expression_projection_is_optional_for_legacy_dr_loading():
    dr = _compile()["compiled_dr"]
    legacy = deepcopy(dr)
    legacy.pop("visual_expression_mapping")

    loaded = mock_load_dr_v0_3(legacy)

    assert loaded["loaded"] is True
    assert loaded["dr_version"] == "0.3"
    assert DRDocumentV03.model_fields["visual_expression_mapping"].is_required() is False


def test_missing_a1_a2_use_deterministic_safe_defaults_with_bilingual_diagnostic():
    first, first_diagnostics = build_visual_expression_mapping([])
    second, second_diagnostics = build_visual_expression_mapping([])

    assert first == second
    assert first_diagnostics == second_diagnostics
    assert first["allowed_states"] == _STATES
    assert first["default_state"] == "neutral"
    assert first["intensity_range"] == {"minimum": 0.0, "maximum": 1.0}
    assert first["base_color_policy"]["resident_default_base_color"] is None
    assert first["transition_policy"]["transition_duration"] == 0.0
    assert first["transition_policy"]["minimum_hold_duration"] == 0.0
    assert first["abstract_bust_mapping"] == {"status": "reserved"}
    assert {
        diagnostic["code"] for diagnostic in first_diagnostics
    } == {"DR_VISUAL_EXPRESSION_MAPPING_DEFAULTED"}
    VisualExpressionMappingV03.model_validate(first)

    zh, en = _locales()
    for prefix in ("audit", "validation"):
        key = f"{prefix}.DR_VISUAL_EXPRESSION_MAPPING_DEFAULTED"
        assert zh[key]
        assert en[key]
        assert zh[key] != en[key]
