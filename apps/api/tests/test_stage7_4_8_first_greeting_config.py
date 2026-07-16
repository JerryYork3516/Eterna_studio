"""Stage 7.4.8 optional first-interaction and first-presence configuration contracts."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

from app.registry.module_catalog import get_module_catalog
from app.services.dr_compiler import compile_dr_result_v0_3, mock_load_dr_v0_3


ROOT = Path(__file__).resolve().parents[3]


def _catalog() -> dict[str, dict]:
    return {module.module_id: module.model_dump(mode="json") for module in get_module_catalog()}


def _workflow() -> dict:
    return {
        "name": "Stage 7.4.8 first presence config",
        "nodes": [{"node_id": f"layer_{index}"} for index in range(1, 14)],
    }


def _node(module: dict, node_id: str) -> dict:
    return next(node for node in module["module_graph"]["nodes"] if node["node_id"] == node_id)


def _field(module: dict, node_id: str, field_id: str) -> dict:
    fields = _node(module, node_id)["params"]["fields"]
    return next(field for field in fields if (field.get("field_id") or field.get("field_key")) == field_id)


def _remove_field(module: dict, node_id: str, field_id: str) -> None:
    node = _node(module, node_id)
    node["params"]["fields"] = [
        field
        for field in node["params"]["fields"]
        if (field.get("field_id") or field.get("field_key")) != field_id
    ]


def _compile_result(modules: list[dict]) -> dict:
    return compile_dr_result_v0_3({"workflow": _workflow(), "modules": modules})


def _compile(modules: list[dict]) -> dict:
    result = _compile_result(modules)
    assert result["valid"] is True, result["errors"]
    return result["compiled_dr"]


def _compiled_visual_output(dr: dict) -> dict:
    visual_style = next(
        module for module in dr["payload"]["modules"] if module["module_id"] == "visual_style"
    )
    return visual_style["outputs"]["first_presence_config"]


def _stage_expression_i18n_keys(value: object) -> set[str]:
    if isinstance(value, dict):
        return set().union(*(_stage_expression_i18n_keys(item) for item in value.values()), set())
    if isinstance(value, list):
        return set().union(*(_stage_expression_i18n_keys(item) for item in value), set())
    if isinstance(value, str) and value.startswith("stage7_4_8.expression."):
        return {value}
    return set()


def test_visual_style_reuses_the_existing_module_with_exact_seven_node_graph():
    catalog = _catalog()
    module = catalog["visual_style"]
    nodes = module["module_graph"]["nodes"]
    assert [(node["node_id"], node["node_type"]) for node in nodes] == [
        ("visual_style_first_greeting_config", "text_input"),
        ("visual_style_reference_input", "reference_input"),
        ("visual_style_config_normalize", "structure_normalize"),
        ("visual_style_first_greeting_validation", "validation"),
        ("visual_style_first_presence_validation", "validation"),
        ("visual_style_first_presence_output", "module_output"),
        ("visual_style_reference_output", "reference_output"),
    ]
    assert {
        (edge["source"], edge["target"])
        for edge in module["module_graph"]["edges"]
    } == {
        ("visual_style_first_greeting_config", "visual_style_config_normalize"),
        ("visual_style_config_normalize", "visual_style_first_greeting_validation"),
        ("visual_style_first_greeting_validation", "visual_style_first_presence_validation"),
        ("visual_style_first_presence_validation", "visual_style_first_presence_output"),
        ("visual_style_first_presence_output", "visual_style_reference_output"),
        ("visual_style_reference_input", "visual_style_first_greeting_validation"),
        ("visual_style_reference_input", "visual_style_first_presence_validation"),
        ("visual_style_reference_input", "visual_style_first_presence_output"),
    }
    assert module["runtime_enabled"] is False
    assert module["no_execution"] is True
    assert module["slot_bindings"] == []
    assert module["config"]["no_engine_binding"] is True
    assert module["config"]["no_provider_binding"] is True


def test_visual_style_fields_references_validation_and_exports_are_optional_and_resolved():
    catalog = _catalog()
    module = catalog["visual_style"]
    greeting = _field(module, "visual_style_first_greeting_config", "first_greeting")
    presence = _field(module, "visual_style_first_greeting_config", "first_presence")
    assert greeting["required"] is False
    assert greeting["field_value"]["content_status"] == "pending_authoring"
    assert greeting["field_value"]["variants"] == []
    assert [
        option["value"] for option in greeting["structured_options"]["content_status"]
    ] == ["pending_authoring", "authored"]
    assert presence["required"] is False
    assert presence["field_value"] == {
        "particle_state": "calm",
        "motion": "slow_breathing",
        "energy": "soft",
        "subtitle_mode": "minimal",
    }

    reference_input = _node(module, "visual_style_reference_input")
    references = reference_input["params"]["references"]
    assert [
        (reference["source_layer_id"], reference["source_module_id"], reference["source_node_id"])
        for reference in references
    ] == [
        ("layer_1", "module_basic_identity", "basic_identity_output"),
        ("layer_2", "personality_traits", "personality_traits_output_summary"),
        ("layer_3", "humanistic_interaction_boundary_config_v0_1", "interaction_boundary_config_output"),
        ("layer_5", "memory_access_control", "memory_access_output"),
        ("layer_7", "world_setting", "worldview_module_output"),
        ("layer_8", "interaction_strategy", "interaction_behavior_core_rules"),
        ("layer_11", "user_relationship", "user_relationship_config_output"),
    ]
    assert all(reference["required"] is True for reference in references)
    assert all(reference["source_scope"] == "module" for reference in references)
    assert not any(
        reference["source_module_id"] == "humanistic_behavior_boundary_config_v0_1"
        for reference in references
    )
    for reference in references:
        source = catalog[reference["source_module_id"]]
        assert source["layer_id"] == reference["source_layer_id"]
        assert reference["source_node_id"] in {
            node["node_id"] for node in source["module_graph"]["nodes"]
        }

    greeting_rules = _node(module, "visual_style_first_greeting_validation")["params"]["validation_rules"]
    assert "no_automatic_greeting_authoring" in greeting_rules
    assert "no_false_shared_history" in greeting_rules
    assert "no_default_romantic_or_intimate_relationship" in greeting_rules
    presence_rules = _node(module, "visual_style_first_presence_validation")["params"]["validation_rules"]
    assert "motion_hint_only_no_animation" in presence_rules
    assert "subtitle_mode_config_only_no_runtime_capability" in presence_rules
    assert "no_required_capability_addition" in presence_rules

    reference_output = _node(module, "visual_style_reference_output")
    assert [field["field_path"] for field in reference_output["params"]["export_fields"]] == [
        "expression.first_greeting",
        "expression.first_presence",
        "reference_source_summary",
        "validation_result",
        "optional_config_status",
    ]
    assert all(field["required"] is False for field in reference_output["params"]["export_fields"])


def test_config_values_survive_module_snapshot_compile_and_export():
    catalog = _catalog()
    first_interaction = _field(
        catalog["interaction_strategy"],
        "interaction_behavior_core_rules",
        "first_interaction",
    )
    assert first_interaction["value"]["enabled"] is True
    assert first_interaction["value"]["scenes"]["user_silence"]["max_active_prompts"] == 1
    first_interaction["value"]["initiative_level"] = "very_low"
    greeting = _field(catalog["visual_style"], "visual_style_first_greeting_config", "first_greeting")
    greeting["field_value"]["max_sentences"] = 1
    initial_relationship = _field(
        catalog["user_relationship"],
        "user_relationship_config_input",
        "initial_relationship",
    )
    initial_relationship["field_value"]["trust_building"] = "explicit_and_gradual"

    dr = _compile(list(catalog.values()))
    assert dr["payload"]["behavior"]["first_interaction"]["enabled"] is True
    assert dr["payload"]["behavior"]["first_interaction"]["initiative_level"] == "very_low"
    assert dr["payload"]["behavior"]["first_interaction"]["scenes"]["user_silence"] == {
        "enabled": True,
        "max_active_prompts": 1,
    }
    assert dr["payload"]["expression"]["first_greeting"]["max_sentences"] == 1
    assert dr["payload"]["expression"]["first_greeting"]["variants"] == greeting["field_value"]["variants"]
    assert dr["payload"]["expression"]["first_presence"]["particle_state"] == "calm"
    assert dr["payload"]["relationship"]["initial_relationship"]["trust_building"] == "explicit_and_gradual"
    assert dr["payload"]["relationship"]["initial_relationship"]["relationship_memory_creation"] == "disabled_until_explicit_user_authorization"

    output = _compiled_visual_output(dr)
    assert output["first_greeting"] == dr["payload"]["expression"]["first_greeting"]
    assert output["first_presence"] == dr["payload"]["expression"]["first_presence"]
    assert output["validation_result"] == {
        "status": "pass",
        "first_greeting": "pass",
        "first_presence": "pass",
        "risk_items": [],
    }
    assert len(output["reference_source_summary"]) == 7
    assert all(item["reference_id"] for item in output["reference_source_summary"])
    assert all(item["resolved"] is True for item in output["reference_source_summary"])
    assert output["optional_config_status"]["variants"] == "empty_allowed"
    assert dr["dr_schema_version"] == "0.3.0"
    assert dr["manifest"]["required_capabilities"] == ["llm", "memory", "lattice"]


@pytest.mark.parametrize("enabled", [True, False])
def test_first_interaction_enabled_preserves_explicit_saved_boolean(enabled: bool):
    catalog = _catalog()
    first_interaction = _field(
        catalog["interaction_strategy"],
        "interaction_behavior_core_rules",
        "first_interaction",
    )
    first_interaction["value"]["enabled"] = enabled
    scenes = deepcopy(first_interaction["value"]["scenes"])

    dr = _compile(list(catalog.values()))
    compiled = dr["payload"]["behavior"]["first_interaction"]
    assert compiled["enabled"] is enabled
    assert compiled["scenes"] == scenes


def test_current_linxuan_first_interaction_enabled_compiles_true():
    catalog = _catalog()
    identity = catalog["module_basic_identity"]
    _field(identity, "basic_identity_field_input", "name")["value"] = "林瑄"
    _field(identity, "basic_identity_field_input", "codename")["value"] = "linxuan_hum_cn_xian_01"
    _field(identity, "basic_identity_field_input", "resident_id")["value"] = (
        "dr_eterna_hum_cn_xian_linxuan_0001"
    )
    first_interaction = _field(
        catalog["interaction_strategy"],
        "interaction_behavior_core_rules",
        "first_interaction",
    )
    first_interaction["value"]["enabled"] = True

    dr = _compile(list(catalog.values()))
    assert dr["payload"]["behavior"]["first_interaction"]["enabled"] is True


def test_current_linxuan_authored_greeting_exports_only_the_three_retained_variants():
    catalog = _catalog()
    identity = catalog["module_basic_identity"]
    _field(identity, "basic_identity_field_input", "name")["value"] = "林瑄"
    _field(identity, "basic_identity_field_input", "codename")["value"] = (
        "linxuan_hum_cn_xian_01"
    )
    _field(identity, "basic_identity_field_input", "resident_id")["value"] = (
        "dr_eterna_hum_cn_xian_linxuan_0001"
    )
    retained_variants = [
        "你好，我叫林瑄。刚见面，先认识一下吧。",
        "你好，我是林瑄。第一次见面，请多关照。",
        "你好，我是林瑄。你叫什么名字？",
    ]
    greeting = _field(
        catalog["visual_style"], "visual_style_first_greeting_config", "first_greeting"
    )
    greeting["field_value"]["content_status"] = "authored"
    greeting["field_value"]["variants"] = retained_variants

    dr = _compile(list(catalog.values()))
    compiled = dr["payload"]["expression"]["first_greeting"]
    assert compiled["content_status"] == "authored"
    assert compiled["variants"] == retained_variants
    assert "你好，我是林瑄。今天开始，我们可以慢慢熟悉。" not in compiled["variants"]
    assert _compiled_visual_output(dr)["first_greeting"] == compiled


@pytest.mark.parametrize("value", [0, 1])
def test_first_interaction_prompt_limit_accepts_zero_or_one(value: int):
    catalog = _catalog()
    first_interaction = _field(
        catalog["interaction_strategy"],
        "interaction_behavior_core_rules",
        "first_interaction",
    )
    first_interaction["value"]["scenes"]["user_silence"]["max_active_prompts"] = value

    dr = _compile(list(catalog.values()))
    assert (
        dr["payload"]["behavior"]["first_interaction"]["scenes"]["user_silence"]["max_active_prompts"]
        == value
    )


@pytest.mark.parametrize("value", [-1, 2, "1", 0.5])
def test_first_interaction_prompt_limit_rejects_invalid_raw_compile_values(value: object):
    catalog = _catalog()
    first_interaction = _field(
        catalog["interaction_strategy"],
        "interaction_behavior_core_rules",
        "first_interaction",
    )
    first_interaction["value"]["scenes"]["user_silence"]["max_active_prompts"] = value

    result = _compile_result(list(catalog.values()))
    assert result["valid"] is False
    error = next(
        error
        for error in result["errors"]
        if error["code"] == "DR_FIRST_INTERACTION_MAX_ACTIVE_PROMPTS_INVALID"
    )
    assert error["path"] == "payload.behavior.first_interaction.scenes.user_silence.max_active_prompts"
    assert "must be an integer in range 0-1" in error["message"]
    assert result["compiled_dr"] is None
    assert (
        result["dr_payload"]["behavior"]["first_interaction"]["scenes"]["user_silence"]["max_active_prompts"]
        == value
    )


def test_empty_variants_and_missing_optional_expression_groups_compile():
    catalog = _catalog()
    visual_style = catalog["visual_style"]
    _remove_field(visual_style, "visual_style_first_greeting_config", "first_greeting")
    dr = _compile(list(catalog.values()))
    assert "first_greeting" not in dr["payload"]["expression"]
    assert dr["payload"]["expression"]["first_presence"]["particle_state"] == "calm"
    output = _compiled_visual_output(dr)
    assert output["validation_result"]["first_greeting"] == "missing_optional"
    assert output["optional_config_status"]["first_greeting"] == "missing_optional"

    catalog = _catalog()
    visual_style = catalog["visual_style"]
    _remove_field(visual_style, "visual_style_first_greeting_config", "first_greeting")
    _remove_field(visual_style, "visual_style_first_greeting_config", "first_presence")
    dr = _compile(list(catalog.values()))
    assert "expression" not in dr["payload"]
    output = _compiled_visual_output(dr)
    assert output["validation_result"]["status"] == "pass"
    assert "first_greeting" not in output
    assert "first_presence" not in output


@pytest.mark.parametrize(
    ("content_status", "variants", "valid"),
    [
        ("pending_authoring", [], True),
        ("authored", [], False),
        ("authored", ["你好。"], True),
        ("pending_authoring", ["你好。"], False),
        ("authored", [{"text": "你好。", "variant_id": "existing-metadata"}], True),
    ],
)
def test_first_greeting_content_status_matches_variants(
    content_status: str, variants: list[object], valid: bool
):
    catalog = _catalog()
    greeting = _field(
        catalog["visual_style"], "visual_style_first_greeting_config", "first_greeting"
    )
    greeting["field_value"]["content_status"] = content_status
    greeting["field_value"]["variants"] = variants

    result = _compile_result(list(catalog.values()))
    assert result["valid"] is valid
    if valid:
        compiled = result["compiled_dr"]["payload"]["expression"]["first_greeting"]
        assert compiled["content_status"] == content_status
        assert compiled["variants"] == variants
    else:
        error = next(
            error
            for error in result["errors"]
            if error["code"] == "DR_FIRST_PRESENCE_CONFIG_INVALID"
        )
        assert error["path"] == "payload.expression.first_greeting"
        assert "content_status_must_match_variants" in error["message"]


@pytest.mark.parametrize(
    "variant",
    ["", "   ", {}, {"text": ""}, {"text": "   "}, {"content": "你好。"}, 1, None],
)
def test_first_greeting_rejects_invalid_variant_items(variant: object):
    catalog = _catalog()
    greeting = _field(
        catalog["visual_style"], "visual_style_first_greeting_config", "first_greeting"
    )
    greeting["field_value"]["content_status"] = "authored"
    greeting["field_value"]["variants"] = [variant]

    result = _compile_result(list(catalog.values()))
    assert result["valid"] is False
    error = next(
        error
        for error in result["errors"]
        if error["code"] == "DR_FIRST_PRESENCE_CONFIG_INVALID"
    )
    assert error["path"] == "payload.expression.first_greeting"
    assert "greeting_variants_must_contain_valid_copy" in error["message"]


def test_reference_summary_inherits_static_ids_repairs_legacy_boundary_and_resolves():
    catalog = _catalog()
    visual_style = catalog["visual_style"]
    references = _node(visual_style, "visual_style_reference_input")["params"]["references"]
    expected_ids = [reference["reference_id"] for reference in references]
    for reference in references:
        if reference["reference_id"] != "first_presence_safety_boundary":
            reference["reference_id"] = None
    legacy_boundary_reference = next(
        reference
        for reference in references
        if reference["reference_id"] == "first_presence_safety_boundary"
    )
    legacy_boundary_reference["source_module_id"] = "humanistic_behavior_boundary_config_v0_1"
    legacy_boundary_reference["source_node_id"] = "reference_output"
    legacy_boundary_reference["source_scope"] = "node"
    legacy_boundary_reference["required"] = False
    legacy_config_reference = next(
        reference
        for reference in visual_style["config"]["reference_sources"]
        if reference["reference_id"] == "first_presence_safety_boundary"
    )
    legacy_config_reference["source_module_id"] = "humanistic_behavior_boundary_config_v0_1"
    legacy_config_reference["source_node_id"] = "reference_output"

    dr = _compile(list(catalog.values()))
    summary = _compiled_visual_output(dr)["reference_source_summary"]
    assert [item["reference_id"] for item in summary] == expected_ids
    assert all(item["reference_id"] for item in summary)
    assert all(item["resolved"] is True for item in summary)
    compiled_visual_style = next(
        module for module in dr["payload"]["modules"] if module["module_id"] == "visual_style"
    )
    compiled_config_reference = next(
        reference
        for reference in compiled_visual_style["config"]["reference_sources"]
        if reference["reference_id"] == "first_presence_safety_boundary"
    )
    assert compiled_config_reference["source_module_id"] == "humanistic_interaction_boundary_config_v0_1"
    assert compiled_config_reference["source_node_id"] == "interaction_boundary_config_output"
    assert compiled_config_reference["source_scope"] == "module"
    assert compiled_config_reference["required"] is True
    compiled_reference_input = _node(compiled_visual_style, "visual_style_reference_input")
    compiled_references = compiled_reference_input["params"]["references"]
    assert [reference["reference_id"] for reference in compiled_references] == expected_ids
    compiled_layer3_reference = next(
        reference
        for reference in compiled_references
        if reference["source_module_id"] == "humanistic_interaction_boundary_config_v0_1"
    )
    assert compiled_layer3_reference["source_node_id"] == "interaction_boundary_config_output"
    assert compiled_layer3_reference["source_scope"] == "module"
    assert compiled_layer3_reference["required"] is True
    assert [item["reference_id"] for item in summary] == [
        reference["reference_id"] for reference in compiled_references
    ]
    assert not any(
        item["source_module_id"] == "humanistic_behavior_boundary_config_v0_1"
        for item in summary
    )


def test_expression_payload_is_authoritative_over_stale_module_output_mirror():
    catalog = _catalog()
    visual_style = catalog["visual_style"]
    greeting = _field(visual_style, "visual_style_first_greeting_config", "first_greeting")
    greeting["field_value"]["content_status"] = "authored"
    greeting["field_value"]["variants"] = ["真实模块字段文案。"]
    visual_style["outputs"]["first_presence_config"]["first_greeting"] = {
        "content_status": "authored",
        "variants": ["过期镜像文案。"],
    }

    dr = _compile(list(catalog.values()))
    payload_greeting = dr["payload"]["expression"]["first_greeting"]
    output_greeting = _compiled_visual_output(dr)["first_greeting"]
    assert payload_greeting == greeting["field_value"]
    assert output_greeting == payload_greeting
    assert "过期镜像文案。" not in output_greeting["variants"]


def test_invalid_first_presence_configuration_is_rejected_at_compile_time():
    catalog = _catalog()
    greeting = _field(catalog["visual_style"], "visual_style_first_greeting_config", "first_greeting")
    greeting["field_value"]["variants"] = "not-an-array"
    result = _compile_result(list(catalog.values()))
    assert result["valid"] is False
    assert any(error["code"] == "DR_FIRST_PRESENCE_CONFIG_INVALID" for error in result["errors"])
    assert "variants_must_be_array" in result["errors"][0]["message"]


def test_legacy_module_snapshots_without_stage_7_4_8_fields_still_compile_and_load():
    catalog = _catalog()
    modules = deepcopy(list(catalog.values()))
    by_id = {module["module_id"]: module for module in modules}

    interaction = _node(by_id["interaction_strategy"], "interaction_behavior_core_rules")
    interaction["params"].pop("fields", None)

    visual_style = by_id["visual_style"]
    visual_style["module_graph"] = {}
    visual_style["outputs"] = {}
    visual_style["output_schema"] = []
    visual_style["config"] = {}

    relationship_input = _node(by_id["user_relationship"], "user_relationship_config_input")
    relationship_input["params"]["fields"] = [
        field
        for field in relationship_input["params"]["fields"]
        if field.get("field_key") != "initial_relationship"
    ]
    relationship_input["params"]["field_registry"] = [
        field
        for field in relationship_input["params"].get("field_registry", [])
        if field.get("field_key") != "initial_relationship"
    ]
    by_id["user_relationship"]["config"]["field_registry"] = [
        field
        for field in by_id["user_relationship"]["config"]["field_registry"]
        if field.get("field_key") != "initial_relationship"
    ]

    dr = _compile(modules)
    assert "behavior" not in dr["payload"]
    assert "expression" not in dr["payload"]
    assert "relationship" not in dr["payload"]
    assert mock_load_dr_v0_3(dr)["loaded"] is True


def test_visual_style_stage_i18n_keys_exist_in_both_locales():
    module = _catalog()["visual_style"]
    required_keys = _stage_expression_i18n_keys(module) | {
        "genericFields.optional",
        "genericFields.emptyArray",
        "reference.catalogSourceNode",
    }
    assert required_keys
    for locale_name in ("zh.json", "en.json"):
        locale = json.loads((ROOT / "apps" / "web" / "locales" / locale_name).read_text())
        missing = sorted(key for key in required_keys if not locale.get(key))
        assert missing == []
