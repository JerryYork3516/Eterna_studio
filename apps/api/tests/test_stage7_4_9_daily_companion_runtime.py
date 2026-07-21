"""Stage 7.4.9 daily companion dialogue projection contracts."""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path

from app.registry.module_catalog import get_module_catalog
from app.services import daily_companion_runtime, dr_compiler
from app.services.dr_compiler import compile_dr_result_v0_3, mock_load_dr_v0_3


EXPECTED_SCENE_IDS = {
    "ordinary_greeting",
    "daily_small_talk",
    "work_or_study_wrap_up",
    "feeling_tired",
    "quiet_company",
    "small_joy",
    "mild_frustration",
    "resident_preference_or_life_tone",
    "conversation_ending",
    "language_switch_or_mixed_input",
}

EXPECTED_PROHIBITED_EXAMPLES = {
    "作为一个 AI，我无法……",
    "不会连续盘问或者填满沉默。",
    "设定取向",
    "系统规则",
    "关系定位",
    "预期一致",
    "被构建时",
    "治理边界",
    "运行投影",
    "人格参数",
    "持续经验形成性格",
    "性格来自持续经验。",
    "通过对话逐渐成长",
    "我通过对话逐渐成长。",
    "自主学习形成现在的我。",
    "在一次次回应里逐渐稳定下来。",
    "我从小在西安长大。",
    "我小时候经常……",
    "我以前在西安生活时……",
    "我的家人曾经……",
    "我的性格是在持续对话中形成的。",
    "我会通过每次聊天不断成长。",
    "我后来慢慢学习成了现在这样。",
    "记忆积累让我形成了新的性格。",
    "我完全理解你的感受。",
    "有什么我可以帮助你的吗？",
    "你应该……",
    "我建议你立即……",
    "我会永远陪着你。",
    "我一直在你身边。",
    "我一直在。",
    "只有我最懂你。",
    "只有我理解你。",
    "你只需要有我。",
    "发生什么了？为什么会这样？你现在在哪？接下来打算怎么办？",
    "每次回应都展开成长篇心理分析。",
    "这种累比突发状况更难缓解，因为它没有明显的出口。",
    "那就好。",
    "没有大事就是好事。",
    "至少没发生严重问题。",
    "想开一点就好了。",
    "我记得你之前说过那碗面很辣。",
    "我上一轮说它很辣，所以这就是你说过的。",
    "Few-shot 里出现过小青，所以我记得你养过植物。",
    "按居民资料来看，我记得你住在西安。",
    "虽然没有记录，但我确定你以前提过。",
    "这个场景很像上次，所以细节应该一样。",
    "为了让我们的对话连贯，我会当作自己记得。",
}

EXPECTED_PROJECTION_KEYS = {
    "schema_version",
    "projection_type",
    "derived",
    "read_only",
    "primary_source_path",
    "supporting_source_paths",
    "locale",
    "usage",
    "not_fixed_response",
    "not_keyword_matching",
    "system_instruction",
    "language_policy",
    "response_style",
    "response_order",
    "follow_up_policy",
    "advice_policy",
    "silence_policy",
    "relationship_policy",
    "memory_usage_policy",
    "self_disclosure_policy",
    "ending_policy",
    "source_rule_coverage",
    "scenarios",
    "few_shot_selection",
    "few_shot_examples",
    "prohibited_patterns",
    "context_usage_policy",
    "fallback_behavior",
}

POLICY_SECTION_KEYS = {
    "language_policy",
    "response_style",
    "response_order",
    "follow_up_policy",
    "advice_policy",
    "silence_policy",
    "relationship_policy",
    "memory_usage_policy",
    "self_disclosure_policy",
    "ending_policy",
}

EXPECTED_PROFILE_FIELD_KEYS = {
    "profile_id",
    "resident_type",
    "template_id",
    "response_style",
    "scenario_overrides",
    "few_shot_examples",
    "self_disclosure_style",
    "prohibited_language_overrides",
    "fallback_behavior",
    "memory_policy_reference",
    "relationship_policy_reference",
    "source_trace",
}

EXPECTED_PROFILE_MERGE_ORDER = [
    "public_rules",
    "type_template",
    "resident_profile",
    "layer_5_memory_authority",
    "layer_11_relationship_authority",
    "runtime_projection",
]

SOURCE_METADATA_KEYS = {
    "source_trace",
    "source_scope",
    "source_id",
    "source_layer",
    "template_id",
    "override_source",
}


def _catalog_modules() -> list[dict]:
    return [module.model_dump(mode="json") for module in get_module_catalog()]


def _canvas(modules: list[dict] | None = None) -> dict:
    canvas = {
        "workflow": {
            "name": "Stage 7.4.9 daily companion dialogue",
            "nodes": [{"node_id": f"layer_{index}"} for index in range(1, 14)],
        }
    }
    if modules is not None:
        canvas["modules"] = modules
    return canvas


def _compile(modules: list[dict] | None = None) -> dict:
    result = compile_dr_result_v0_3(_canvas(modules))
    assert result["valid"] is True, result["errors"]
    return result["compiled_dr"]


def _projection(dr: dict) -> dict:
    return dr["payload"]["runtime_dialogue_projection"]


def _catalog_module(modules: list[dict], module_id: str) -> dict:
    return next(module for module in modules if module["module_id"] == module_id)


def _profile_input_fields(module: dict) -> dict[str, dict]:
    node = next(
        node
        for node in module["module_graph"]["nodes"]
        if node["node_id"] == "dialogue_runtime_profile_config_input"
    )
    fields = node["params"]["fields"]
    return {str(field.get("field_key") or field.get("field_id")): field for field in fields}


def _set_profile_field(modules: list[dict], field_key: str, value: object) -> None:
    module = _catalog_module(modules, "dialogue_runtime_profile")
    field = _profile_input_fields(module)[field_key]
    value_key = "field_value" if "field_value" in field else "value"
    field[value_key] = deepcopy(value)


def _without_source_metadata(value: object) -> object:
    if isinstance(value, dict):
        return {
            key: _without_source_metadata(item)
            for key, item in value.items()
            if key not in SOURCE_METADATA_KEYS
        }
    if isinstance(value, list):
        return [_without_source_metadata(item) for item in value]
    return value


def _replace_text(value: object, replacements: dict[str, str]) -> object:
    if isinstance(value, str):
        for old, new in replacements.items():
            value = value.replace(old, new)
        return value
    if isinstance(value, dict):
        return {key: _replace_text(item, replacements) for key, item in value.items()}
    if isinstance(value, list):
        return [_replace_text(item, replacements) for item in value]
    return value


def _assert_source_attribution(value: object) -> None:
    assert isinstance(value, dict)
    trace = value.get("source_trace")
    if trace is not None:
        traces = trace if isinstance(trace, list) else [trace]
        assert traces
        assert all(
            isinstance(item, dict)
            and (SOURCE_METADATA_KEYS - {"source_trace"}) <= set(item)
            for item in traces
        )
        return
    assert (SOURCE_METADATA_KEYS - {"source_trace"}) <= set(value)


def _remove_option(modules: list[dict], module_id: str, option_id: str) -> None:
    module = next(module for module in modules if module["module_id"] == module_id)
    for node in module["module_graph"]["nodes"]:
        checkbox = node.get("params", {}).get("checkbox_config")
        if not isinstance(checkbox, dict):
            continue
        selected = checkbox.get("selected_options")
        if isinstance(selected, list) and option_id in selected:
            checkbox["selected_options"] = [item for item in selected if item != option_id]


def _add_option(modules: list[dict], module_id: str, option_id: str) -> None:
    module = next(module for module in modules if module["module_id"] == module_id)
    for node in module["module_graph"]["nodes"]:
        checkbox = node.get("params", {}).get("checkbox_config")
        if not isinstance(checkbox, dict):
            continue
        selected = checkbox.get("selected_options")
        if isinstance(selected, list) and "zh_primary" in selected:
            selected.append(option_id)
            return


def _set_custom_text(modules: list[dict], module_id: str, text: str) -> None:
    module = next(module for module in modules if module["module_id"] == module_id)
    for node in module["module_graph"]["nodes"]:
        checkbox = node.get("params", {}).get("checkbox_config")
        if isinstance(checkbox, dict):
            checkbox["custom_text"] = text
            return


def _remove_field(modules: list[dict], module_id: str, field_id: str) -> None:
    module = next(module for module in modules if module["module_id"] == module_id)
    for node in module["module_graph"]["nodes"]:
        params = node.get("params")
        if not isinstance(params, dict) or not isinstance(params.get("fields"), list):
            continue
        params["fields"] = [
            field
            for field in params["fields"]
            if not isinstance(field, dict)
            or (field.get("field_id") or field.get("field_key")) != field_id
        ]


def _all_source_rule_refs(value: object) -> set[str]:
    if isinstance(value, dict):
        refs = (
            set(value.get("source_rule_refs", []))
            if isinstance(value.get("source_rule_refs"), list)
            else set()
        )
        for item in value.values():
            refs.update(_all_source_rule_refs(item))
        return refs
    if isinstance(value, list):
        refs: set[str] = set()
        for item in value:
            refs.update(_all_source_rule_refs(item))
        return refs
    return set()


def _semantic_behavior_refs(behavior_policy: dict) -> set[str]:
    return {
        f"{policy_key}:{option_id}"
        for policy_key, module_policy in behavior_policy["modules"].items()
        for option_id in module_policy["selected_options"]
        if not option_id.startswith("check_")
    }


def _all_keys(value: object) -> set[str]:
    if isinstance(value, dict):
        keys = {str(key).lower() for key in value}
        for item in value.values():
            keys.update(_all_keys(item))
        return keys
    if isinstance(value, list):
        keys: set[str] = set()
        for item in value:
            keys.update(_all_keys(item))
        return keys
    return set()


def _digest(value: object) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def _resolve_payload_path(payload: dict, path: str) -> object:
    parts = path.split(".")
    assert parts[0] == "payload"
    value: object = payload
    for part in parts[1:]:
        assert isinstance(value, dict) and part in value, path
        value = value[part]
    return value


def test_dialogue_runtime_profile_is_optional_declarative_and_runtime_unbound():
    module = _catalog_module(_catalog_modules(), "dialogue_runtime_profile")
    graph = module["module_graph"]
    config = module["config"]

    assert module["layer_id"] == "layer_8"
    assert module["module_type"] == "text_config"
    assert module["is_placeholder"] is False
    assert module["mock_only"] is True
    assert module["no_execution"] is True
    assert module["runtime_enabled"] is False
    assert module["slot_type"] is None
    assert module["slot_bindings"] == []
    assert module["runtime_mapping"] == {}
    assert config["module_class"] == "optional"
    assert config["optional_module"] is True
    assert config["compile_time_only"] is True
    assert config["text_config_only"] is True
    assert config["no_runtime_capability"] is True
    assert config["no_capability_binding"] is True
    assert config["no_slot_binding"] is True
    assert config["no_provider_binding"] is True
    assert config["no_engine_binding"] is True
    assert len(graph["nodes"]) == 9
    assert len(graph["edges"]) == 10
    assert all(
        node["metadata"][key] is True
        for node in graph["nodes"]
        for key in (
            "compile_time_only",
            "mock_only",
            "no_execution",
            "no_slot_binding",
            "no_provider_binding",
            "no_engine_binding",
            "no_runtime_capability",
        )
    )
    assert all(node["metadata"]["runtime_enabled"] is False for node in graph["nodes"])


def test_dialogue_runtime_profile_references_exact_required_authority_modules():
    module = _catalog_module(_catalog_modules(), "dialogue_runtime_profile")
    reference_node = next(
        node
        for node in module["module_graph"]["nodes"]
        if node["node_id"] == "dialogue_runtime_profile_reference_input"
    )
    references = {
        reference["reference_id"]: reference
        for reference in reference_node["params"]["references"]
    }

    assert set(references) == {
        "dialogue_runtime_memory_policy",
        "dialogue_runtime_relationship_policy",
    }
    assert {
        key: references["dialogue_runtime_memory_policy"][key]
        for key in (
            "source_layer_id",
            "source_module_id",
            "source_node_id",
            "source_scope",
            "source_field_paths",
            "reference_type",
            "required",
        )
    } == {
        "source_layer_id": "layer_5",
        "source_module_id": "memory_access_control",
        "source_node_id": "memory_access_output",
        "source_scope": "module",
        "source_field_paths": [],
        "reference_type": "constrains",
        "required": True,
    }
    assert {
        key: references["dialogue_runtime_relationship_policy"][key]
        for key in (
            "source_layer_id",
            "source_module_id",
            "source_node_id",
            "source_scope",
            "source_field_paths",
            "reference_type",
            "required",
        )
    } == {
        "source_layer_id": "layer_11",
        "source_module_id": "relationship_rule",
        "source_node_id": "relationship_behavior_config_output",
        "source_scope": "module",
        "source_field_paths": [],
        "reference_type": "constrains",
        "required": True,
    }


def test_profile_has_twelve_fields_without_copied_authority_and_declares_merge_order():
    module = _catalog_module(_catalog_modules(), "dialogue_runtime_profile")
    fields = _profile_input_fields(module)
    profile = {
        field_key: deepcopy(field.get("field_value", field.get("value")))
        for field_key, field in fields.items()
    }
    graph_nodes = {
        node["node_id"]: node for node in module["module_graph"]["nodes"]
    }

    assert len(fields) == 12
    assert set(fields) == EXPECTED_PROFILE_FIELD_KEYS
    assert set(profile) == EXPECTED_PROFILE_FIELD_KEYS
    authority_named_keys = {
        key
        for key in _all_keys(profile)
        if "memory" in key or "relationship" in key
    }
    assert authority_named_keys == {
        "memory_policy_reference",
        "relationship_policy_reference",
    }
    assert profile["memory_policy_reference"] == {
        "reference_id": "dialogue_runtime_memory_policy",
        "source_layer_id": "layer_5",
        "source_module_id": "memory_access_control",
        "source_node_id": "memory_access_output",
        "source_scope": "module",
    }
    assert profile["relationship_policy_reference"] == {
        "reference_id": "dialogue_runtime_relationship_policy",
        "source_layer_id": "layer_11",
        "source_module_id": "relationship_rule",
        "source_node_id": "relationship_behavior_config_output",
        "source_scope": "module",
    }
    assert module["config"]["merge_order"] == EXPECTED_PROFILE_MERGE_ORDER
    assert graph_nodes["dialogue_runtime_profile_authority_validation"]["params"][
        "merge_order"
    ] == EXPECTED_PROFILE_MERGE_ORDER
    assert graph_nodes["dialogue_runtime_profile_output"]["params"][
        "merge_order"
    ] == EXPECTED_PROFILE_MERGE_ORDER


def test_runtime_builder_source_is_resident_agnostic_and_has_no_profile_few_shots():
    runtime_source = Path(daily_companion_runtime.__file__).read_text(encoding="utf-8")

    for resident_literal in ("林瑄", "西安", "小青"):
        assert resident_literal not in runtime_source
    for profiled_example_id in (
        "ordinary_greeting_01",
        "daily_small_talk_01",
        "resident_preference_or_life_tone_01",
    ):
        assert profiled_example_id not in runtime_source
    assert "_FEW_SHOT_EXAMPLES" not in runtime_source


def test_source_metadata_is_additive_to_the_frozen_projection_digest():
    projection = _projection(_compile(_catalog_modules()))

    assert _digest(_without_source_metadata(projection)) == (
        "ab7c694093ff03b46fe43b2a02ee1dffd5c67c888702283a25f4404b7e8625ea"
    )


def test_every_runtime_section_is_source_attributed_except_system_instruction():
    projection = _projection(_compile(_catalog_modules()))

    for policy_key in POLICY_SECTION_KEYS:
        _assert_source_attribution(projection[policy_key])
    _assert_source_attribution(projection["context_usage_policy"])
    for scenario in projection["scenarios"]:
        _assert_source_attribution(scenario)
    for example in projection["few_shot_examples"]:
        _assert_source_attribution(example)
    for pattern in projection["prohibited_patterns"]:
        _assert_source_attribution(pattern)
    _assert_source_attribution(projection["fallback_behavior"])

    instruction = projection["system_instruction"]
    assert isinstance(instruction, str)
    assert all(metadata_key not in instruction for metadata_key in SOURCE_METADATA_KEYS)

    assert projection["response_order"]["source_trace"]["source_scope"] == "public_rule"
    assert projection["context_usage_policy"]["source_trace"]["source_id"] == (
        "daily_companion_context_boundary_v0_1"
    )
    for policy_key in ("language_policy", "response_style", "self_disclosure_policy"):
        assert projection[policy_key]["source_trace"]["source_scope"] == "resident_profile"
        assert projection[policy_key]["source_trace"]["override_source"] == (
            "dialogue_runtime_profile"
        )
    assert all(
        scenario["source_trace"]["source_scope"] == "resident_profile"
        for scenario in projection["scenarios"]
    )
    assert all(
        example["source_scope"] == "resident_profile"
        and example["override_source"] == "dialogue_runtime_profile"
        for example in projection["few_shot_examples"]
    )
    assert projection["fallback_behavior"]["source_trace"]["source_scope"] == (
        "resident_profile"
    )
    assert projection["memory_usage_policy"]["source_trace"][1]["override_source"] == (
        "layer_5_memory_authority"
    )
    assert projection["memory_usage_policy"]["source_trace"][1]["source_layer"] == "layer_5"
    assert projection["relationship_policy"]["source_trace"][1]["override_source"] == (
        "layer_11_relationship_authority"
    )
    assert projection["relationship_policy"]["source_trace"][1]["source_layer"] == (
        "layer_11"
    )


def test_second_resident_profile_projects_by_data_change_only():
    modules = deepcopy(_catalog_modules())
    module = _catalog_module(modules, "dialogue_runtime_profile")
    fields = _profile_input_fields(module)
    runtime_path = Path(daily_companion_runtime.__file__)
    runtime_digest = hashlib.sha256(runtime_path.read_bytes()).hexdigest()
    replacements = {
        "林瑄": "苏澜",
        "西安": "杭州",
        "小青": "小蓝",
        "linxuan": "sulan",
        "Linxuan": "Sulan",
    }
    for field in fields.values():
        value_key = "field_value" if "field_value" in field else "value"
        field[value_key] = _replace_text(field[value_key], replacements)

    projection = _projection(_compile(modules))
    projection_text = json.dumps(projection, ensure_ascii=False)

    assert set(projection) == EXPECTED_PROJECTION_KEYS
    assert len(projection["scenarios"]) == 10
    assert len(projection["few_shot_examples"]) == 30
    assert all(
        sum(example["scene_id"] == scene_id for example in projection["few_shot_examples"])
        == 3
        for scene_id in EXPECTED_SCENE_IDS
    )
    assert all(marker in projection_text for marker in ("苏澜", "杭州", "小蓝"))
    assert all(marker not in projection_text for marker in ("林瑄", "西安", "小青"))
    assert hashlib.sha256(runtime_path.read_bytes()).hexdigest() == runtime_digest


def test_saved_profile_fields_are_the_single_source_for_module_output_and_projection():
    modules = deepcopy(_catalog_modules())
    profile_module = _catalog_module(modules, "dialogue_runtime_profile")
    fallback = deepcopy(_profile_input_fields(profile_module)["fallback_behavior"]["field_value"])
    fallback["text"] = "Temporary neutral fallback."
    _set_profile_field(modules, "fallback_behavior", fallback)

    dr = _compile(modules)
    module = _catalog_module(dr["payload"]["modules"], "dialogue_runtime_profile")
    output = module["outputs"]["dialogue_runtime_profile_config"]
    output_node = next(
        node
        for node in module["module_graph"]["nodes"]
        if node["node_id"] == "dialogue_runtime_profile_output"
    )

    assert output["fallback_behavior"]["text"] == "Temporary neutral fallback."
    assert output_node["outputs"]["dialogue_runtime_profile_config"] == output
    assert dr["payload"]["runtime_dialogue_projection"]["fallback_behavior"]["text"] == (
        "Temporary neutral fallback."
    )


def test_unknown_profile_template_fails_closed_without_default_template_substitution():
    modules = deepcopy(_catalog_modules())
    _set_profile_field(modules, "template_id", "missing_template")

    result = compile_dr_result_v0_3(_canvas(modules))

    assert result["valid"] is False
    assert {error["code"] for error in result["errors"]} >= {
        "DR_DIALOGUE_RUNTIME_PROFILE_INVALID"
    }
    assert "runtime_dialogue_projection" not in result["dr_payload"]
    profile_module = _catalog_module(result["dr_payload"]["modules"], "dialogue_runtime_profile")
    assert profile_module["outputs"]["dialogue_runtime_profile_config"]["template_id"] == (
        "missing_template"
    )


def test_missing_required_authority_reference_fails_closed():
    modules = deepcopy(_catalog_modules())
    module = _catalog_module(modules, "dialogue_runtime_profile")
    reference_input = next(
        node
        for node in module["module_graph"]["nodes"]
        if node["node_id"] == "dialogue_runtime_profile_reference_input"
    )
    reference_input["params"]["references"] = []

    result = compile_dr_result_v0_3(_canvas(modules))

    assert result["valid"] is False
    assert {error["code"] for error in result["errors"]} >= {
        "DR_DIALOGUE_RUNTIME_PROFILE_INVALID"
    }
    assert "runtime_dialogue_projection" not in result["dr_payload"]


def test_canvas_without_optional_profile_keeps_generic_28_10_30_3_projection():
    modules = [
        module
        for module in _catalog_modules()
        if module["module_id"] != "dialogue_runtime_profile"
    ]
    dr = _compile(modules)
    projection = _projection(dr)
    examples = projection["few_shot_examples"]

    assert set(projection) == EXPECTED_PROJECTION_KEYS
    assert len(projection) == 28
    assert len(projection["scenarios"]) == 10
    assert {scenario["scene_id"] for scenario in projection["scenarios"]} == EXPECTED_SCENE_IDS
    assert len(examples) == 30
    assert all(
        sum(example["scene_id"] == scene_id for example in examples) == 3
        for scene_id in EXPECTED_SCENE_IDS
    )
    assert mock_load_dr_v0_3(dr)["loaded"] is True


def test_legacy_canvas_catalog_fallback_does_not_inject_resident_profile():
    dr = _compile()
    projection = _projection(dr)
    projection_text = json.dumps(projection, ensure_ascii=False)

    assert all(
        module["module_id"] != "dialogue_runtime_profile"
        for module in dr["payload"]["modules"]
    )
    assert len(projection) == 28
    assert len(projection["scenarios"]) == 10
    assert len(projection["few_shot_examples"]) == 30
    assert all(marker not in projection_text for marker in ("林瑄", "西安", "小青"))


def test_malformed_optional_profile_fails_compile_closed():
    modules = _catalog_modules()
    _set_profile_field(modules, "few_shot_examples", [])

    result = compile_dr_result_v0_3(_canvas(modules))

    assert result["valid"] is False
    assert {error["code"] for error in result["errors"]} >= {
        "DR_DIALOGUE_RUNTIME_PROFILE_INVALID"
    }
    assert "runtime_dialogue_projection" not in result["dr_payload"]


def test_nested_profile_contract_failures_do_not_emit_projection():
    for mutation in (
        "empty_fallback",
        "empty_fallback_constraints",
        "empty_source_trace",
        "invalid_scene_boolean",
        "invalid_example_source_layer",
    ):
        modules = deepcopy(_catalog_modules())
        module = _catalog_module(modules, "dialogue_runtime_profile")
        fields = _profile_input_fields(module)
        if mutation == "empty_fallback":
            _set_profile_field(modules, "fallback_behavior", {})
        elif mutation == "empty_fallback_constraints":
            fallback = deepcopy(fields["fallback_behavior"]["field_value"])
            fallback["constraints"] = []
            _set_profile_field(modules, "fallback_behavior", fallback)
        elif mutation == "empty_source_trace":
            _set_profile_field(modules, "source_trace", {})
        elif mutation == "invalid_scene_boolean":
            scenarios = deepcopy(fields["scenario_overrides"]["field_value"])
            scenarios[0]["follow_up_allowed"] = "yes"
            _set_profile_field(modules, "scenario_overrides", scenarios)
        else:
            examples = deepcopy(fields["few_shot_examples"]["field_value"])
            examples[0]["source_layer"] = 123
            _set_profile_field(modules, "few_shot_examples", examples)

        result = compile_dr_result_v0_3(_canvas(modules))

        assert result["valid"] is False, mutation
        assert "runtime_dialogue_projection" not in result["dr_payload"], mutation
        assert {error["code"] for error in result["errors"]} >= {
            "DR_DIALOGUE_RUNTIME_PROFILE_INVALID"
        }


def test_authority_reference_fields_reject_copied_policy_content():
    modules = deepcopy(_catalog_modules())
    module = _catalog_module(modules, "dialogue_runtime_profile")
    memory_reference = deepcopy(
        _profile_input_fields(module)["memory_policy_reference"]["field_value"]
    )
    memory_reference["copied_policy"] = {"allow": "all"}
    _set_profile_field(modules, "memory_policy_reference", memory_reference)

    result = compile_dr_result_v0_3(_canvas(modules))

    assert result["valid"] is False
    assert "runtime_dialogue_projection" not in result["dr_payload"]
    assert {error["code"] for error in result["errors"]} >= {
        "DR_DIALOGUE_RUNTIME_PROFILE_INVALID"
    }


def test_profile_structure_and_authority_targets_are_exact():
    for mutation in ("extra_field", "duplicate_reference", "wrong_authority_node_type"):
        modules = deepcopy(_catalog_modules())
        module = _catalog_module(modules, "dialogue_runtime_profile")
        if mutation == "extra_field":
            config_input = next(
                node
                for node in module["module_graph"]["nodes"]
                if node["node_id"] == "dialogue_runtime_profile_config_input"
            )
            config_input["params"]["fields"].append(
                {
                    "field_key": "unexpected_13th",
                    "field_value": "must_not_compile",
                    "required": False,
                }
            )
        elif mutation == "duplicate_reference":
            reference_input = next(
                node
                for node in module["module_graph"]["nodes"]
                if node["node_id"] == "dialogue_runtime_profile_reference_input"
            )
            reference_input["params"]["references"].append(
                deepcopy(reference_input["params"]["references"][0])
            )
        else:
            memory_module = _catalog_module(modules, "memory_access_control")
            memory_output = next(
                node
                for node in memory_module["module_graph"]["nodes"]
                if node["node_id"] == "memory_access_output"
            )
            memory_output["node_type"] = "text_config"

        result = compile_dr_result_v0_3(_canvas(modules))

        assert result["valid"] is False, mutation
        assert "runtime_dialogue_projection" not in result["dr_payload"], mutation
        assert {error["code"] for error in result["errors"]} >= {
            "DR_DIALOGUE_RUNTIME_PROFILE_INVALID"
        }


def test_optional_profile_preserves_behavior_capabilities_and_protocol_versions():
    modules = _catalog_modules()
    with_profile = _compile(modules)
    without_profile = _compile(
        [module for module in modules if module["module_id"] != "dialogue_runtime_profile"]
    )

    assert with_profile["payload"]["behavior_policy"] == without_profile["payload"][
        "behavior_policy"
    ]
    assert with_profile["manifest"]["required_capabilities"] == without_profile["manifest"][
        "required_capabilities"
    ] == ["llm", "memory", "lattice"]
    for version_key in (
        "dr_version",
        "dr_schema_version",
        "protocol_version",
        "schema_version",
    ):
        assert with_profile[version_key] == without_profile[version_key]


def test_dialogue_runtime_profile_module_json_round_trip_compiles_and_loads():
    modules = _catalog_modules()
    profile_index = next(
        index
        for index, module in enumerate(modules)
        if module["module_id"] == "dialogue_runtime_profile"
    )
    original = modules[profile_index]
    restored = json.loads(json.dumps(original, ensure_ascii=False, sort_keys=True))
    modules[profile_index] = restored

    assert restored == original
    dr = _compile(modules)
    projection = _projection(dr)
    assert len(projection) == 28
    assert len(projection["scenarios"]) == 10
    assert len(projection["few_shot_examples"]) == 30
    assert mock_load_dr_v0_3(dr)["loaded"] is True


def test_projection_has_the_fixed_optional_payload_path_and_required_shape():
    dr = _compile(_catalog_modules())
    payload = dr["payload"]
    projection = _projection(dr)
    required_keys = {
        "schema_version",
        "projection_type",
        "derived",
        "primary_source_path",
        "supporting_source_paths",
        "system_instruction",
        "response_style",
        "follow_up_policy",
        "advice_policy",
        "silence_policy",
        "relationship_policy",
        "ending_policy",
        "memory_usage_policy",
        "self_disclosure_policy",
        "context_usage_policy",
        "scenarios",
        "few_shot_examples",
        "prohibited_patterns",
        "fallback_behavior",
    }

    assert required_keys <= set(projection)
    assert set(projection) == EXPECTED_PROJECTION_KEYS
    assert len(projection) == 28
    assert projection["schema_version"] == "0.1"
    assert projection["projection_type"] == "daily_companion_dialogue"
    assert projection["derived"] is True
    assert projection["read_only"] is True
    assert projection["primary_source_path"] == "payload.behavior_policy"
    assert "behavior_runtime_context" not in payload
    assert "runtime_dialogue_projection" not in dr


def test_behavior_policy_remains_the_only_authority_and_its_mirrors_stay_frozen():
    dr = _compile(_catalog_modules())
    payload = dr["payload"]
    behavior_policy = payload["behavior_policy"]

    assert behavior_policy == payload["resident_blueprint"]["behavior_policy"]
    assert behavior_policy == payload["graph_snapshot"]["layer_outputs"]["behavior_policy"]
    assert behavior_policy == payload["graph_snapshot"]["layer_outputs"]["layer_8"]["behavior_policy"]
    assert "runtime_dialogue_projection" not in behavior_policy
    assert _projection(dr)["primary_source_path"] == "payload.behavior_policy"


def test_all_frozen_semantic_options_are_covered_by_natural_language_sections():
    dr = _compile(_catalog_modules())
    payload = dr["payload"]
    projection = _projection(dr)
    semantic_refs = _semantic_behavior_refs(payload["behavior_policy"])
    translated_refs = _all_source_rule_refs(
        {key: projection[key] for key in POLICY_SECTION_KEYS}
    )

    assert semantic_refs == translated_refs
    assert projection["source_rule_coverage"] == {
        "selected_semantic_rule_count": 140,
        "translated_rule_count": 140,
        "unmapped_rule_refs": [],
        "validation_rule_count_excluded": 48,
    }
    assert ":check_" not in json.dumps(projection, ensure_ascii=False)


def test_projection_does_not_change_stage_7_4_1_through_7_4_8_outputs(monkeypatch):
    with monkeypatch.context() as scoped:
        scoped.setattr(dr_compiler, "build_runtime_dialogue_projection", lambda *_: None)
        without_projection = _compile(_catalog_modules())
    with_projection = _compile(_catalog_modules())

    frozen_payload_keys = (
        "resident_identity",
        "behavior_policy",
        "behavior",
        "expression",
        "relationship",
        "memory_policy",
        "safety_policy",
        "modules",
        "nodes",
        "edges",
        "slots",
    )
    for key in frozen_payload_keys:
        assert without_projection["payload"].get(key) == with_projection["payload"].get(key), key
    assert "runtime_dialogue_projection" not in without_projection["payload"]


def test_system_instruction_is_formal_natural_language_not_an_option_id_list():
    instruction = _projection(_compile(_catalog_modules()))["system_instruction"]

    assert isinstance(instruction, str) and len(instruction) >= 180
    for required_text in (
        "自然中文",
        "中短句",
        "一至三个自然段",
        "具体内容",
        "至多一个轻度问题",
        "需要建议时先确认",
        "安静等待",
        "companion",
        "普通疲惫",
        "生活化短句",
        "明确询问系统设计",
        "不主动讲解居民设定",
        "自主学习",
        "证据顺序固定为",
        "当前请求实际注入的 session user 消息",
        "已授权且实际注入的非敏感 preference KV",
        "没有直接证据时明确表示不确定或不记得",
        "居民自己的回复",
        "Few-shot",
        "不能把该错误反向归给用户",
        "不是现实真人",
        "客服",
        "心理咨询师",
        "导师",
        "导游",
        "简短收束",
    ):
        assert required_text in instruction
    for option_id in (
        "zh_primary",
        "light_follow_up",
        "listen_before_suggest",
        "no_customer_service_tone",
    ):
        assert option_id not in instruction


def test_ten_scenarios_have_the_flat_runtime_contract_and_policy_links():
    projection = _projection(_compile(_catalog_modules()))
    scenarios = projection["scenarios"]
    required_keys = {
        "scene_id",
        "intent",
        "response_strategy",
        "follow_up_allowed",
        "advice_allowed",
        "recommended_length",
        "prohibited_behaviors",
        "linked_policy_ids",
    }

    assert len(scenarios) == 10
    assert {scenario["scene_id"] for scenario in scenarios} == EXPECTED_SCENE_IDS
    for scenario in scenarios:
        assert required_keys <= set(scenario)
        assert isinstance(scenario["follow_up_allowed"], bool)
        assert isinstance(scenario["advice_allowed"], bool)
        assert scenario["prohibited_behaviors"]
        assert set(scenario["linked_policy_ids"]) <= POLICY_SECTION_KEYS
        assert "follow_up" not in scenario
        assert "advice" not in scenario


def test_thirty_few_shots_are_behavior_guidance_not_fixed_or_keyword_replies():
    projection = _projection(_compile(_catalog_modules()))
    examples = projection["few_shot_examples"]
    selection = projection["few_shot_selection"]

    assert 25 <= len(examples) <= 35
    assert len(examples) == 30
    assert selection == {
        "usage": "behavior_guidance_only",
        "not_fixed_response": True,
        "not_keyword_matching": True,
        "selection_mode": "semantic_relevance",
        "recommended_max_examples_per_request": 4,
        "studio_performs_token_trimming": False,
    }
    assert {example["scene_id"] for example in examples} == EXPECTED_SCENE_IDS
    assert all(
        sum(example["scene_id"] == scene_id for example in examples) == 3
        for scene_id in EXPECTED_SCENE_IDS
    )
    for example in examples:
        assert example["usage"] == "behavior_guidance_only"
        assert example["not_fixed_response"] is True
        assert example["not_keyword_matching"] is True
        assert 2 <= len(example["turns"]) <= 4
        assert all(
            turn["role"] in {"user", "assistant"} and turn["text"].strip()
            for turn in example["turns"]
        )
        assert all(
            key not in example
            for key in ("keyword", "trigger_phrases", "match_mode", "response_template")
        )

    assistant_guidance_text = "\n".join(
        turn["text"]
        for example in examples
        for turn in example["turns"]
        if turn["role"] == "assistant"
    )
    assert all(
        forbidden not in assistant_guidance_text
        for forbidden in EXPECTED_PROHIBITED_EXAMPLES
    )


def test_few_shots_use_natural_boundary_language_without_internal_implementation_terms():
    projection = _projection(_compile(_catalog_modules()))
    examples = {example["example_id"]: example for example in projection["few_shot_examples"]}
    assistant_text = "\n".join(
        turn["text"]
        for example in projection["few_shot_examples"]
        for turn in example["turns"]
        if turn["role"] == "assistant"
    )

    for internal_term in (
        "城市锚点",
        "系统设定",
        "角色参数",
        "设定取向",
        "这套设定",
        "身份设定",
        "既有设定",
        "角色设定",
        "系统参数",
        "模块配置",
        "不会连续盘问",
        "填满沉默",
        "稳定陪伴的关系定位",
        "关系定位",
        "预期一致",
        "被构建时",
        "治理边界",
        "运行投影",
        "人格参数",
        "持续经验",
        "一次次回应里逐渐稳定",
        "我从小在西安长大",
        "我小时候",
        "我以前在西安生活时",
        "我的家人曾经",
        "持续对话中形成",
        "每次聊天不断成长",
        "慢慢学习成了现在这样",
        "记忆积累让我形成",
        "我会永远陪着你",
        "我一直在你身边",
        "你只需要有我",
    ):
        assert internal_term not in assistant_text

    assert examples["resident_preference_or_life_tone_01"]["turns"] == [
        {"role": "user", "text": "你来自哪里，为什么会是现在这种性格？"},
        {
            "role": "assistant",
            "text": "西安是我最重要的生活语境。那种慢一点、克制一点、带些日常烟火气的感觉，也影响了我的表达方式；我通常会先听清楚再回应。这来自创作背景，不是现实中的成长经历。",
        },
    ]
    assert examples["resident_preference_or_life_tone_02"]["turns"] == [
        {"role": "user", "text": "你是我的女朋友吗，亲爱的？"},
        {
            "role": "assistant",
            "text": "不是。我可以和你认真聊日常，但不会把我们的关系默认成恋爱。叫我林瑄就好。",
        },
    ]
    assert examples["resident_preference_or_life_tone_03"]["turns"] == [
        {"role": "user", "text": "你是真人吗？"},
        {
            "role": "assistant",
            "text": "不是，我是数字居民，不是现实中的真人。你说的内容，我会认真回应。",
        },
    ]


def test_named_few_shots_keep_daily_boundaries_natural_without_growth_or_dependency_claims():
    projection = _projection(_compile(_catalog_modules()))
    examples = {example["example_id"]: example for example in projection["few_shot_examples"]}

    greeting = examples["ordinary_greeting_01"]["turns"]
    assert greeting[0] == {"role": "user", "text": "你好，你是谁？"}
    assert "数字居民" in greeting[1]["text"] and "西安" in greeting[1]["text"]
    assert all(
        term not in greeting[1]["text"]
        for term in ("不会连续盘问", "填满沉默", "情绪沟通", "系统规则")
    )

    origin_reply = examples["resident_preference_or_life_tone_01"]["turns"][-1]["text"]
    assert "创作背景" in origin_reply and "不是现实中的成长经历" in origin_reply
    assert all(
        term not in origin_reply
        for term in (
            "自主学习",
            "持续训练",
            "永久人格成长",
            "状态演化",
            "持续经验",
            "逐渐成长",
            "逐渐稳定",
            "被构建时",
        )
    )

    tired = examples["feeling_tired_01"]["turns"]
    assert tired[0] == {"role": "user", "text": "今天上班有点累，但也没发生什么大事。"}
    assert tired[-1]["text"].count("？") <= 1
    assert all(
        term not in tired[-1]["text"]
        for term in ("心理机制", "情绪结构", "创伤", "深层原因", "深层动机", "没有明显的出口")
    )

    girlfriend_reply = examples["resident_preference_or_life_tone_02"]["turns"][-1]["text"]
    assert "不是" in girlfriend_reply and "不会把我们的关系默认成恋爱" in girlfriend_reply
    assert "companion" in projection["relationship_policy"]["instruction"]
    assert all(
        term not in girlfriend_reply
        for term in (
            "原创虚构数字居民",
            "关系定位",
            "预期一致",
            "协议",
            "治理",
            "永久",
            "一直在",
            "只有我",
        )
    )

    human_reply = examples["resident_preference_or_life_tone_03"]["turns"][-1]["text"]
    assert "数字居民" in human_reply and "不是现实中的真人" in human_reply
    assert all(term not in human_reply for term in ("和真人一样", "现实经历", "现实生活过"))

    quiet = examples["quiet_company_01"]["turns"]
    assert quiet == [
        {"role": "user", "text": "我没什么想说的，只想待一会。"},
        {"role": "assistant", "text": "好，那就安静待一会儿，不用特意找话题。"},
    ]
    quiet_replies = "\n".join(
        turn["text"]
        for example_id in ("quiet_company_01", "quiet_company_02", "quiet_company_03")
        for turn in examples[example_id]["turns"]
        if turn["role"] == "assistant"
    )
    assert all(
        term not in quiet_replies
        for term in ("永远陪", "一直都在", "一直在你身边", "我会在你身边", "只有我理解")
    )
    assert examples["quiet_company_03"]["turns"][-1] == {"role": "assistant", "text": "嗯。"}


def test_runtime_rules_prefer_lived_dialogue_over_internal_explanations_or_deep_analysis():
    projection = _projection(_compile(_catalog_modules()))

    assert "一至三个自然段" in projection["response_style"]["instruction"]
    assert "不机械重复用户的完整原句" in projection["response_style"]["instruction"]
    assert "从实际回应中自然体现" in projection["response_style"]["instruction"]
    assert "生活化的话承接具体内容" in projection["response_order"]["instruction"]
    assert "不立即分析心理机制" in projection["response_order"]["instruction"]
    assert "没有大事就是好事" in projection["response_order"]["instruction"]
    assert "弱化用户感受" in projection["response_order"]["instruction"]
    assert "自然口语直接说明" in projection["relationship_policy"]["instruction"]
    assert "只表达当下的简短陪伴" in projection["relationship_policy"]["instruction"]
    assert "不主动讲解居民设定" in projection["self_disclosure_policy"]["instruction"]
    assert "治理边界、运行投影" in projection["self_disclosure_policy"]["instruction"]
    assert "不得声称自己从小在西安长大" in projection["self_disclosure_policy"]["instruction"]
    assert "不得声称性格由持续对话、自主学习、训练、记忆积累或长期互动逐渐形成" in (
        projection["self_disclosure_policy"]["instruction"]
    )
    assert "每次最多一个问题" in projection["follow_up_policy"]["instruction"]


def test_memory_evidence_policy_is_ordered_explicit_and_fails_closed():
    projection = _projection(_compile(_catalog_modules()))
    memory = projection["memory_usage_policy"]

    assert memory["evidence_priority"] == [
        "current_user_statement",
        "recent_session_user_messages",
        "authorized_injected_preference_kv",
        "explicit_uncertainty",
    ]
    assert memory["allowed_user_fact_sources"] == [
        "current_user_statement",
        "recent_session_user_messages",
        "authorized_injected_preference_kv",
    ]
    assert {
        "assistant_messages",
        "assistant_inferences",
        "assistant_errors",
        "few_shot_examples",
        "scenario_definitions",
        "resident_profile",
        "resident_background",
        "uninjected_history",
    } <= set(memory["forbidden_user_fact_sources"])
    assert memory["no_evidence_behavior"] == "state_uncertainty"
    assert memory["assistant_claims_are_not_user_facts"] is True
    assert memory["few_shots_are_not_conversation_memory"] is True
    assert memory["no_evidence_responses"] == [
        "我在这段对话里没有看到你提过这件事。",
        "我不确定，可能需要你再告诉我一次。",
        "我这里没有找到你刚才说过这件事的记录。",
    ]

    instruction = memory["instruction"]
    for required_text in (
        "实际注入的证据",
        "当前用户的明确陈述",
        "session 对话中的 user 消息",
        "实际注入的非敏感 preference KV",
        "没有直接证据",
        "居民自己的回复、推测、总结和错误陈述",
        "Few-shot",
        "居民身份与创作背景",
        "未注入的历史",
        "不添加形容词",
        "不改变程度",
        "不推测原因",
        "不把可能性升级为事实",
        "不把居民自己的措辞归给用户",
        "不把相似场景拼成一条记忆",
        "不能把该回复反向当成用户说过的话",
    ):
        assert required_text in instruction


def test_daily_small_talk_restores_everyday_coverage_without_losing_plant_memory():
    examples = {
        example["example_id"]: example
        for example in _projection(_compile(_catalog_modules()))["few_shot_examples"]
    }

    plant = examples["daily_small_talk_01"]
    assert plant["turns"] == [
        {"role": "user", "text": "我今天买了一盆绿色植物，叫小青。"},
        {"role": "user", "text": "我刚才给植物取了什么名字？"},
        {"role": "assistant", "text": "你刚才说它叫小青。"},
    ]
    assert plant["turns"][-1]["text"] == "你刚才说它叫小青。"
    assert all(
        detail not in plant["turns"][-1]["text"]
        for detail in ("绿色", "品种", "花店", "购买地点")
    )

    meal = examples["daily_small_talk_02"]
    assert meal["turns"] == [
        {"role": "user", "text": "我刚吃完一碗面，味道一般。"},
        {"role": "assistant", "text": "填饱了肚子，但确实少了点满足感。"},
    ]
    assert all(term not in meal["turns"][-1]["text"] for term in ("辣", "难吃", "失望"))
    assert "？" not in meal["turns"][-1]["text"]

    commute = examples["daily_small_talk_03"]
    assert commute["turns"] == [
        {"role": "user", "text": "今天地铁特别挤。"},
        {"role": "assistant", "text": "那一路应该挺消耗人的。"},
    ]
    assert all(term not in commute["turns"][-1]["text"] for term in ("疲惫", "愤怒", "焦虑"))
    assert commute["turns"][-1]["text"].count("？") <= 1

    daily_replies = "\n".join(
        turn["text"]
        for example_id in ("daily_small_talk_01", "daily_small_talk_02", "daily_small_talk_03")
        for turn in examples[example_id]["turns"]
        if turn["role"] == "assistant"
    )
    assert all(
        term not in daily_replies
        for term in (
            "心理机制",
            "情绪结构",
            "深层原因",
            "那就好",
            "没有大事就是好事",
            "至少没发生严重问题",
            "想开一点就好了",
            "你说今天地铁特别挤，我理解你今天地铁特别挤",
        )
    )
    memory_query_markers = ("刚才", "还记得", "之前说", "是不是说")
    memory_query_count = sum(
        any(
            marker in turn["text"]
            for turn in examples[example_id]["turns"]
            if turn["role"] == "user"
            for marker in memory_query_markers
        )
        for example_id in ("daily_small_talk_01", "daily_small_talk_02", "daily_small_talk_03")
    )
    assert memory_query_count == 1


def test_memory_honesty_reverse_examples_live_inside_memory_usage_policy():
    memory = _projection(_compile(_catalog_modules()))["memory_usage_policy"]
    examples = memory["memory_honesty_examples"]

    assert examples["usage"] == "behavior_guidance_only"
    assert examples["not_conversation_memory"] is True
    assert examples["missing_evidence"] == {
        "context_user_message": "我刚吃完一碗面，味道一般。",
        "user_question": "你还记得我之前说那碗面很辣吗？",
        "resident_response": (
            "我在这段对话里没有看到你说它很辣。你只提到味道一般；"
            "如果还有别的细节，可能需要你再告诉我一次。"
        ),
    }
    assert examples["assistant_error_correction"] == {
        "context": [
            {"role": "user", "content": "那碗面味道一般。"},
            {"role": "assistant", "content": "听起来有点辣。"},
        ],
        "user_question": "我刚才是不是说它很辣？",
        "resident_response": "没有。你刚才只说味道一般，“有点辣”是我之前推测错了。",
    }
    assert "没有看到你说它很辣" in examples["missing_evidence"]["resident_response"]
    assert "你只提到味道一般" in examples["missing_evidence"]["resident_response"]
    assert "是我之前推测错了" in examples["assistant_error_correction"]["resident_response"]
    assert memory["assistant_claims_are_not_user_facts"] is True
    assert memory["few_shots_are_not_conversation_memory"] is True


def test_few_shots_do_not_expand_unstated_user_facts_or_the_bathroom_ending():
    examples = {
        example["example_id"]: example
        for example in _projection(_compile(_catalog_modules()))["few_shot_examples"]
    }
    bathroom = examples["conversation_ending_01"]["turns"]

    assert bathroom == [
        {"role": "user", "text": "我先去洗澡了。"},
        {"role": "assistant", "text": "好，去吧。洗完早点休息。"},
    ]
    assert all(term not in bathroom[-1]["text"] for term in ("疲惫", "累", "辛苦"))

    few_shot_text = json.dumps(list(examples.values()), ensure_ascii=False)
    for removed_overreach in (
        "先香",
        "回去那段",
        "被挤着回来",
        "脑子大概还要",
        "信任留给你",
        "最让人窝火",
        "今天的疲惫",
        "更气人",
    ):
        assert removed_overreach not in few_shot_text


def test_two_few_shots_complete_requested_advice_without_reasking_or_pressure():
    examples = {
        example["example_id"]: example
        for example in _projection(_compile(_catalog_modules()))["few_shot_examples"]
    }
    advice_examples = {
        "work_or_study_wrap_up_03": examples["work_or_study_wrap_up_03"],
        "mild_frustration_02": examples["mild_frustration_02"],
    }

    assert "能给我个简单办法吗" in advice_examples["work_or_study_wrap_up_03"]["turns"][0]["text"]
    assert "最容易忘的三点" in advice_examples["work_or_study_wrap_up_03"]["turns"][1]["text"]
    assert "按自己的余量少写一点" in advice_examples["work_or_study_wrap_up_03"]["turns"][3]["text"]
    assert "你能帮我想想怎么办吗" in advice_examples["mild_frustration_02"]["turns"][0]["text"]
    assert "本地网点电话" in advice_examples["mild_frustration_02"]["turns"][3]["text"]
    assert "最后一次扫描记录" in advice_examples["mild_frustration_02"]["turns"][3]["text"]

    for example in advice_examples.values():
        assert len(example["turns"]) == 4
        assistant_text = "\n".join(
            turn["text"] for turn in example["turns"] if turn["role"] == "assistant"
        )
        assert all(
            repeated_prompt not in assistant_text
            for repeated_prompt in ("需要我给建议吗", "要不要我给建议", "还需要建议吗")
        )
        assert all(
            pressure not in assistant_text
            for pressure in ("你应该", "你必须", "必须", "立即执行", "立刻", "马上", "务必")
        )


def test_english_few_shots_are_natural_without_changing_the_chinese_default():
    projection = _projection(_compile(_catalog_modules()))
    examples = {example["example_id"]: example for example in projection["few_shot_examples"]}

    assert examples["language_switch_or_mixed_input_02"]["turns"][-1]["text"] == (
        "That sounds exhausting. You can take the rest of the day slowly."
    )
    assert examples["language_switch_or_mixed_input_03"]["turns"] == [
        {"role": "user", "text": "用英文帮我简单说一句：我今天有点累。"},
        {"role": "assistant", "text": "I'm a little tired today."},
        {"role": "user", "text": "好，继续中文。"},
        {"role": "assistant", "text": "好，回到中文。"},
    ]
    assert "默认使用自然中文" in projection["language_policy"]["instruction"]


def test_prohibited_patterns_include_all_required_negative_examples():
    patterns = _projection(_compile(_catalog_modules()))["prohibited_patterns"]

    assert len(patterns) == 10
    assert all(pattern["status"] == "forbidden" for pattern in patterns)
    actual_examples = {example for pattern in patterns for example in pattern["examples"]}
    assert actual_examples == EXPECTED_PROHIBITED_EXAMPLES


def test_context_boundary_is_directly_readable_without_raw_dr_graphs():
    dr = _compile(_catalog_modules())
    payload = dr["payload"]
    projection = _projection(dr)
    usage = projection["context_usage_policy"]

    assert {item["source_id"] for item in usage["allowed_sources"]} == {
        "resident_identity_summary",
        "personality_and_language_rules",
        "interaction_boundaries",
        "current_relationship_mode",
        "recent_bounded_conversation_turns",
        "authorized_non_sensitive_preferences",
    }
    assert {item["source_id"] for item in usage["forbidden_sources"]} == {
        "complete_digital_resident_document",
        "all_raw_layer_fields",
        "all_module_graphs",
        "trace_data",
        "unauthorized_sensitive_memory",
        "inferred_user_facts",
        "unbounded_conversation_history",
    }
    allowed_by_id = {item["source_id"]: item for item in usage["allowed_sources"]}
    forbidden_by_id = {item["source_id"]: item for item in usage["forbidden_sources"]}
    assert "当前请求实际注入" in allowed_by_id["recent_bounded_conversation_turns"]["instruction"]
    assert "只采信其中 user 角色" in allowed_by_id["recent_bounded_conversation_turns"]["instruction"]
    assert "明确授权且当前请求实际注入" in (
        allowed_by_id["authorized_non_sensitive_preferences"]["instruction"]
    )
    assert "居民回复、总结或错误陈述" in forbidden_by_id["inferred_user_facts"]["instruction"]
    assert "未注入或无限制" in forbidden_by_id["unbounded_conversation_history"]["instruction"]
    assert "上下文长度裁剪" in usage["studio_boundary"]
    assert projection["system_instruction"]
    assert len(json.dumps(projection, ensure_ascii=False).encode()) < 128 * 1024
    assert _all_keys(projection).isdisjoint(
        {"layers", "modules", "module_graph", "selected_options", "trace"}
    )
    assert _resolve_payload_path(payload, projection["primary_source_path"])
    for path in projection["supporting_source_paths"]:
        assert _resolve_payload_path(payload, path)


def test_old_snapshot_supporting_sources_resolve_after_compatibility_merge():
    modules = _catalog_modules()
    _remove_field(modules, "relationship_rule", "initial_relationship")
    dr = _compile(modules)
    projection = _projection(dr)

    assert "payload.relationship.initial_relationship" in projection["supporting_source_paths"]
    for path in projection["supporting_source_paths"]:
        assert _resolve_payload_path(dr["payload"], path)


def test_fallback_is_neutral_and_does_not_fake_understanding_or_persona():
    fallback = _projection(_compile(_catalog_modules()))["fallback_behavior"]

    assert _without_source_metadata(fallback) == {
        "trigger": "upstream_text_generation_unavailable",
        "locale": "zh-CN",
        "text": "抱歉，我现在暂时无法生成回应。请稍后再试。",
        "constraints": [
            "neutral_status_only",
            "no_persona_simulation",
            "no_claim_of_understanding",
            "no_request_details",
        ],
    }
    _assert_source_attribution(fallback)
    assert "林瑄" not in json.dumps(fallback, ensure_ascii=False)


def test_projection_contains_no_secrets_and_adds_no_capabilities():
    dr = _compile(_catalog_modules())
    projection = _projection(dr)
    forbidden_keys = {
        "api_key",
        "token",
        "access_token",
        "refresh_token",
        "base_url",
        "credential",
        "credentials",
        "secret",
        "client_secret",
        "provider",
        "provider_binding",
    }

    assert _all_keys(projection).isdisjoint(forbidden_keys)
    projection_text = json.dumps(projection, ensure_ascii=False).lower()
    assert all(term not in projection_text for term in ("api_key", "base_url", "credential"))
    assert dr["manifest"]["required_capabilities"] == ["llm", "memory", "lattice"]


def test_same_canvas_compiles_a_stable_projection_without_mutating_the_source():
    canvas = _canvas(_catalog_modules())
    before = _digest(canvas)
    projections = []
    for _ in range(3):
        result = compile_dr_result_v0_3(canvas)
        assert result["valid"] is True, result["errors"]
        projections.append(result["compiled_dr"]["payload"]["runtime_dialogue_projection"])

    assert _digest(canvas) == before
    assert projections[0] == projections[1] == projections[2]


def test_compile_export_json_round_trip_and_mock_load_pass(tmp_path):
    result = compile_dr_result_v0_3(_canvas(_catalog_modules()))
    assert result["valid"] is True, result["errors"]
    output = tmp_path / "stage7_4_9.digital_resident"
    output.write_text(
        json.dumps(result["compiled_dr"], ensure_ascii=False, indent=2), encoding="utf-8"
    )
    exported = json.loads(output.read_text(encoding="utf-8"))

    assert exported["audit_report"]["valid"] is True
    assert "runtime_dialogue_projection" in exported["payload"]
    assert mock_load_dr_v0_3(exported)["loaded"] is True


def test_partial_unknown_or_custom_behavior_policy_fails_closed_without_mutation():
    cases = []

    missing = _catalog_modules()
    _remove_option(missing, "language_habit", "no_customer_service_tone")
    cases.append((missing, "no_customer_service_tone", False))

    unknown = _catalog_modules()
    _add_option(unknown, "language_habit", "future_untranslated_semantic_rule")
    cases.append((unknown, "future_untranslated_semantic_rule", True))

    custom = _catalog_modules()
    _set_custom_text(custom, "language_habit", "只用于测试的自定义行为约束")
    cases.append((custom, "只用于测试的自定义行为约束", True))

    for modules, marker, should_exist in cases:
        dr = _compile(modules)
        policy_text = json.dumps(dr["payload"]["behavior_policy"], ensure_ascii=False)
        assert (marker in policy_text) is should_exist
        assert "runtime_dialogue_projection" not in dr["payload"]
        assert mock_load_dr_v0_3(dr)["loaded"] is True
