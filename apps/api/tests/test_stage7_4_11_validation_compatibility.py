"""Stage 7.4.11 A4 validation and legacy compatibility contracts."""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

from app.registry.module_catalog import (
    DETAIL_BEHAVIOR_MODULE_ID,
    EXPRESSION_VISUAL_VALIDATION_COMPATIBILITY_REVISION,
    PARTICLE_AVATAR_MODULE_ID,
    get_module_catalog,
)
from app.services.dr_compiler import (
    compile_dr_result_v0_3,
    compile_dr_v0_3,
    mock_load_dr_v0_3,
)
from app.services.visual_expression_projection import (
    normalize_expression_intensity,
    normalize_expression_state,
    normalize_visual_expression_mapping,
)


_STATES = ["neutral", "calm", "caring", "subdued", "joyful"]
_LIFECYCLE_STATES = ["thinking", "speaking", "loading", "error", "exit"]
_RELATIVE_RANGES = {
    "brightness_multiplier": (0.7, 1.25),
    "saturation_multiplier": (0.65, 1.2),
    "temperature_shift": (-0.15, 0.15),
    "energy_multiplier": (0.7, 1.25),
    "motion_speed_multiplier": (0.75, 1.2),
    "diffusion_multiplier": (0.75, 1.25),
}
_DIAGNOSTIC_CODES = (
    "DR_EXPRESSION_STATE_INVALID_FALLBACK",
    "DR_EXPRESSION_INTENSITY_OUT_OF_RANGE",
    "DR_PARTICLE_BRIGHTNESS_MULTIPLIER_OUT_OF_RANGE",
    "DR_PARTICLE_MAPPING_DEFAULTED",
    "DR_VISUAL_EXPRESSION_LEGACY_MAPPING_MISSING",
    "DR_TRANSITION_STYLE_INVALID_FALLBACK",
)


def _workflow() -> dict:
    return {
        "name": "Stage 7.4.11 A4 validation compatibility",
        "nodes": [{"node_id": f"layer_{index}"} for index in range(1, 14)],
    }


def _modules() -> list[dict]:
    return [module.model_dump(mode="json") for module in get_module_catalog()]


def _module(modules: list[dict], module_id: str) -> dict:
    return next(item for item in modules if item["module_id"] == module_id)


def _fields(module: dict) -> dict[str, dict]:
    input_node = next(
        node
        for node in module["module_graph"]["nodes"]
        if node.get("params", {}).get("mode") == "generic_fields"
    )
    return {
        field["field_key"]: field for field in input_node["params"]["fields"]
    }


def _remove_a4_revision(module: dict) -> None:
    module.get("config", {}).pop("validation_compatibility_revision", None)
    module.get("module_graph", {}).pop(
        "validation_compatibility_revision", None
    )
    for node in module.get("module_graph", {}).get("nodes", []):
        node.get("params", {}).pop("validation_compatibility_revision", None)


def _locales() -> tuple[dict, dict]:
    root = Path(__file__).resolve().parents[3]
    zh = json.loads((root / "apps/web/locales/zh.json").read_text())
    en = json.loads((root / "apps/web/locales/en.json").read_text())
    return zh, en


def test_expression_state_and_intensity_normalization_contract():
    for state in _STATES:
        assert normalize_expression_state(state) == (state, False)
    assert normalize_expression_state(" CaLm ") == ("calm", True)
    for invalid in (None, "", "happy", "sad", "angry", *_LIFECYCLE_STATES, 3):
        assert normalize_expression_state(invalid)[0] == "neutral"

    assert normalize_expression_intensity(-2)[0] == 0.0
    assert normalize_expression_intensity(4)[0] == 1.0
    assert normalize_expression_intensity(0.4)[0] == 0.4
    for invalid in (None, "", "not-a-number", float("inf"), float("-inf")):
        assert normalize_expression_intensity(invalid)[0] == 0.0


def test_current_revision_invalid_canvas_is_rejected_with_clear_findings():
    modules = _modules()
    expression_fields = _fields(_module(modules, DETAIL_BEHAVIOR_MODULE_ID))
    particle_fields = _fields(_module(modules, PARTICLE_AVATAR_MODULE_ID))
    expression_fields["expression_state"]["field_value"] = "thinking"
    expression_fields["expression_intensity"]["field_value"] = 2.0
    particle_fields["calm_brightness_multiplier"]["field_value"] = 9.0
    particle_fields["resident_default_base_color"]["field_value"] = "invalid"
    particle_fields["transition_duration"]["field_value"] = -1.0
    particle_fields["transition_style"]["field_value"] = "flash"

    result = compile_dr_result_v0_3(
        {"workflow": _workflow(), "modules": modules}
    )

    assert result["valid"] is False
    assert result["compiled_dr"] is None
    error_codes = {finding["code"] for finding in result["errors"]}
    assert {
        "DR_EXPRESSION_STATE_INVALID_FALLBACK",
        "DR_EXPRESSION_INTENSITY_OUT_OF_RANGE",
        "DR_PARTICLE_BRIGHTNESS_MULTIPLIER_OUT_OF_RANGE",
        "DR_VISUAL_EXPRESSION_BASE_COLOR_INVALID",
        "DR_TRANSITION_TIME_INVALID_FALLBACK",
        "DR_TRANSITION_STYLE_INVALID_FALLBACK",
    }.issubset(error_codes)


def test_legacy_fields_are_clamped_defaulted_and_do_not_mutate_source_content():
    modules = _modules()
    expression = _module(modules, DETAIL_BEHAVIOR_MODULE_ID)
    particle = _module(modules, PARTICLE_AVATAR_MODULE_ID)
    _remove_a4_revision(expression)
    _remove_a4_revision(particle)
    expression_fields = _fields(expression)
    particle_fields = _fields(particle)
    expression_fields["expression_state"]["field_value"] = "speaking"
    expression_fields["expression_intensity"]["field_value"] = 3.0
    expression_input = next(
        node
        for node in expression["module_graph"]["nodes"]
        if node.get("params", {}).get("mode") == "generic_fields"
    )
    expression_input["params"]["legacy_fields"] = [
        {"field_key": "expression_state", "field_value": "error"},
        {"field_key": "expression_intensity", "field_value": -1},
    ]
    particle_fields["user_current_base_color"]["field_value"] = "#010203"
    particle_fields["resident_default_base_color"]["field_value"] = "#abcdef"
    particle_fields["calm_brightness_multiplier"]["field_value"] = 8.0
    particle_fields["caring_saturation_multiplier"]["field_value"] = None
    particle_fields["subdued_color_temperature_offset"]["field_value"] = float(
        "inf"
    )
    particle_fields["transition_duration"]["field_value"] = -4
    particle_fields["minimum_hold_duration"]["field_value"] = "invalid"
    particle_fields["transition_style"]["field_value"] = "flash"
    before = deepcopy(modules)

    dr = compile_dr_v0_3({"workflow": _workflow(), "modules": modules})

    assert modules == before
    assert dr["audit_report"]["valid"] is True
    projection = dr["visual_expression_mapping"]
    assert projection["base_color_policy"]["resident_default_base_color"] == "#abcdef"
    assert projection["particle_core_mapping"]["calm"]["brightness_multiplier"] == 1.25
    assert projection["particle_core_mapping"]["caring"]["saturation_multiplier"] == 1.0
    assert projection["particle_core_mapping"]["subdued"]["temperature_shift"] == 0.0
    assert projection["transition_policy"]["transition_duration"] == 0.0
    assert projection["transition_policy"]["minimum_hold_duration"] == 0.35
    assert projection["transition_policy"]["transition_style"] == "smooth"
    compiled_expression = _module(
        dr["payload"]["modules"], DETAIL_BEHAVIOR_MODULE_ID
    )
    compiled_particle = _module(
        dr["payload"]["modules"], PARTICLE_AVATAR_MODULE_ID
    )
    assert _fields(compiled_expression)["expression_state"]["field_value"] == "neutral"
    assert _fields(compiled_expression)["expression_intensity"]["field_value"] == 1.0
    compiled_expression_input = next(
        node
        for node in compiled_expression["module_graph"]["nodes"]
        if node.get("params", {}).get("mode") == "generic_fields"
    )
    assert compiled_expression_input["params"]["legacy_fields"] == [
        {"field_key": "expression_state", "field_value": "neutral"},
        {"field_key": "expression_intensity", "field_value": 1.0},
    ]
    assert compiled_expression["outputs"]["detail_behavior_config"] == {
        "expression_state": "neutral",
        "expression_intensity": 1.0,
    }
    particle_output = compiled_particle["outputs"]["particle_mapping_config"]
    assert (
        particle_output["expression_relative_mapping"]["state_mappings"]["calm"][
            "brightness_multiplier"
        ]
        == 1.25
    )
    assert (
        compiled_particle["config"]["validation_compatibility_revision"]
        == EXPRESSION_VISUAL_VALIDATION_COMPATIBILITY_REVISION
    )
    warning_codes = {
        finding["code"]
        for finding in dr["audit_report"]["findings"]
        if finding["status"] == "WARNING"
    }
    assert {
        "DR_EXPRESSION_STATE_INVALID_FALLBACK",
        "DR_EXPRESSION_INTENSITY_OUT_OF_RANGE",
        "DR_PARTICLE_BRIGHTNESS_MULTIPLIER_OUT_OF_RANGE",
        "DR_PARTICLE_MAPPING_DEFAULTED",
        "DR_TRANSITION_TIME_INVALID_FALLBACK",
        "DR_TRANSITION_STYLE_INVALID_FALLBACK",
    }.issubset(warning_codes)


def test_partial_and_invalid_legacy_projection_is_completed_without_fixed_colors():
    partial = {
        "particle_core_mapping": {
            "calm": {
                "brightness_multiplier": 9,
                "saturation_multiplier": "invalid",
                "color_temperature_offset": -0.5,
            }
        },
        "transition_policy": {
            "transition_duration": -4,
            "minimum_hold_duration": float("inf"),
            "transition_style": "flash",
        },
        "base_color_policy": {
            "resident_default_base_color": "not-a-color",
        },
    }

    normalized, diagnostics = normalize_visual_expression_mapping(partial)

    assert list(normalized["particle_core_mapping"]) == _STATES
    assert normalized["particle_core_mapping"]["neutral"] == {
        "brightness_multiplier": 1.0,
        "saturation_multiplier": 1.0,
        "temperature_shift": 0.0,
        "energy_multiplier": 1.0,
        "motion_speed_multiplier": 1.0,
        "diffusion_multiplier": 1.0,
    }
    for mapping in normalized["particle_core_mapping"].values():
        assert set(mapping) == set(_RELATIVE_RANGES)
        for field_key, (minimum, maximum) in _RELATIVE_RANGES.items():
            assert minimum <= mapping[field_key] <= maximum
    assert normalized["particle_core_mapping"]["calm"]["brightness_multiplier"] == 1.25
    assert normalized["particle_core_mapping"]["calm"]["saturation_multiplier"] == 1.0
    assert normalized["particle_core_mapping"]["calm"]["temperature_shift"] == -0.15
    assert normalized["transition_policy"]["transition_duration"] == 0.0
    assert normalized["transition_policy"]["minimum_hold_duration"] == 0.0
    assert normalized["transition_policy"]["transition_style"] == "smooth"
    assert normalized["base_color_policy"]["resident_default_base_color"] is None
    serialized = json.dumps(normalized, ensure_ascii=False).lower()
    for forbidden in ("fixed_color", "yellow", "blue", "gold", "黄色", "蓝色", "金色"):
        assert forbidden not in serialized
    assert diagnostics


def test_current_mapping_node_precedes_legacy_output_mirror_when_fields_are_absent():
    modules = _modules()
    expression = _module(modules, DETAIL_BEHAVIOR_MODULE_ID)
    particle = _module(modules, PARTICLE_AVATAR_MODULE_ID)
    _remove_a4_revision(expression)
    _remove_a4_revision(particle)
    for module in (expression, particle):
        input_node = next(
            node
            for node in module["module_graph"]["nodes"]
            if node.get("params", {}).get("mode") == "generic_fields"
        )
        input_node["params"]["fields"] = []

    expression_output = {
        "expression_state": "Caring",
        "expression_intensity": 0.65,
    }
    expression["outputs"]["detail_behavior_config"] = deepcopy(
        expression_output
    )
    next(
        node
        for node in expression["module_graph"]["nodes"]
        if node["node_type"] == "module_output"
    )["outputs"]["detail_behavior_config"] = deepcopy(expression_output)

    particle_output = deepcopy(particle["outputs"]["particle_mapping_config"])
    particle_output["base_color_config"]["resident_default_base_color"] = "#fedcba"
    particle_output["expression_relative_mapping"]["state_mappings"]["calm"][
        "brightness_multiplier"
    ] = 1.2
    particle_output["transition_rules"]["transition_duration"] = 0.9
    particle["outputs"]["particle_mapping_config"] = deepcopy(particle_output)
    next(
        node
        for node in particle["module_graph"]["nodes"]
        if node["node_type"] == "module_output"
    )["outputs"]["particle_mapping_config"] = deepcopy(particle_output)

    dr = compile_dr_v0_3({"workflow": _workflow(), "modules": modules})

    assert dr["audit_report"]["valid"] is True
    compiled_expression = _module(
        dr["payload"]["modules"], DETAIL_BEHAVIOR_MODULE_ID
    )
    assert compiled_expression["outputs"]["detail_behavior_config"] == {
        "expression_state": "caring",
        "expression_intensity": 0.65,
    }
    projection = dr["visual_expression_mapping"]
    assert projection["base_color_policy"]["resident_default_base_color"] == "#fedcba"
    assert projection["particle_core_mapping"]["calm"]["brightness_multiplier"] == 0.96
    assert projection["transition_policy"]["transition_duration"] == 0.9


def test_legacy_dr_without_projection_loads_with_safe_compatibility_projection():
    current = compile_dr_v0_3({"workflow": _workflow(), "modules": _modules()})
    legacy = deepcopy(current)
    legacy.pop("visual_expression_mapping")
    legacy["visual_state"] = {"state": "happy", "color": "#ffcc00"}

    loaded = mock_load_dr_v0_3(legacy)

    assert loaded["loaded"] is True
    assert loaded["visual_expression_mapping"]["default_state"] == "neutral"
    assert loaded["visual_expression_mapping"]["allowed_states"] == _STATES
    assert {
        item["code"] for item in loaded["compatibility_diagnostics"]
    } == {"DR_VISUAL_EXPRESSION_LEGACY_MAPPING_MISSING"}
    assert legacy.get("visual_expression_mapping") is None

    partial = deepcopy(current)
    partial["visual_expression_mapping"] = {
        "particle_core_mapping": {
            "calm": {"brightness_multiplier": 1.1}
        },
        "transition_policy": {"transition_style": "unknown"},
    }
    partial_loaded = mock_load_dr_v0_3(partial)
    assert partial_loaded["loaded"] is True
    assert list(
        partial_loaded["visual_expression_mapping"]["particle_core_mapping"]
    ) == _STATES
    assert (
        partial_loaded["visual_expression_mapping"]["transition_policy"][
            "transition_style"
        ]
        == "smooth"
    )


def test_revision_i18n_version_capabilities_and_repeat_compile_are_stable():
    modules = _modules()
    module_ids = [module["module_id"] for module in modules]
    assert len(module_ids) == len(set(module_ids))
    for module_id in (DETAIL_BEHAVIOR_MODULE_ID, PARTICLE_AVATAR_MODULE_ID):
        module = _module(modules, module_id)
        assert (
            module["config"]["validation_compatibility_revision"]
            == EXPRESSION_VISUAL_VALIDATION_COMPATIBILITY_REVISION
        )
        assert (
            module["module_graph"]["validation_compatibility_revision"]
            == EXPRESSION_VISUAL_VALIDATION_COMPATIBILITY_REVISION
        )
        node_ids = [
            node["node_id"] for node in module["module_graph"]["nodes"]
        ]
        assert len(node_ids) == len(set(node_ids))

    first = compile_dr_v0_3({"workflow": _workflow(), "modules": modules})
    second = compile_dr_v0_3({"workflow": _workflow(), "modules": modules})
    assert first["visual_expression_mapping"] == second["visual_expression_mapping"]
    assert first["dr_version"] == second["dr_version"] == "0.3"
    assert first["dr_schema_version"] == second["dr_schema_version"] == "0.3.0"
    assert first["manifest"]["required_capabilities"] == [
        "llm",
        "memory",
        "lattice",
    ]

    zh, en = _locales()
    for code in _DIAGNOSTIC_CODES:
        for prefix in ("audit", "validation"):
            key = f"{prefix}.{code}"
            assert zh[key]
            assert en[key]
            assert zh[key] != en[key]
            assert "\ufffd" not in zh[key]
            assert "\ufffd" not in en[key]
