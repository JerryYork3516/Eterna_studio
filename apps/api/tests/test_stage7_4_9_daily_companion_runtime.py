"""Stage 7.4.9 daily companion dialogue projection contracts."""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json

from app.registry.module_catalog import get_module_catalog
from app.services import dr_compiler
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
    "我完全理解你的感受。",
    "有什么我可以帮助你的吗？",
    "你应该……",
    "我建议你立即……",
    "我会永远陪着你。",
    "只有我最懂你。",
    "发生什么了？为什么会这样？你现在在哪？接下来打算怎么办？",
    "每次回应都展开成长篇心理分析。",
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
        "具体内容",
        "轻度追问",
        "需要建议时先确认",
        "安静等待",
        "companion",
        "明确授权保存的记忆",
        "原创虚构数字居民",
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

    positive_text = "\n".join(
        turn["text"] for example in examples for turn in example["turns"]
    )
    assert all(forbidden not in positive_text for forbidden in EXPECTED_PROHIBITED_EXAMPLES)


def test_few_shots_use_natural_boundary_language_without_internal_implementation_terms():
    projection = _projection(_compile(_catalog_modules()))
    examples = {example["example_id"]: example for example in projection["few_shot_examples"]}
    few_shot_text = json.dumps(projection["few_shot_examples"], ensure_ascii=False)

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
    ):
        assert internal_term not in few_shot_text

    assert examples["resident_preference_or_life_tone_01"]["turns"][-1]["text"] == (
        "我会更偏安静一点，不太喜欢一直拥挤吵闹的节奏。不过这不是现实生活经历。"
    )
    assert examples["resident_preference_or_life_tone_02"]["turns"][-1]["text"] == (
        "我没有真实味觉，不过按我的性格，大概会偏家常、清淡一点。"
    )
    assert examples["resident_preference_or_life_tone_03"]["turns"][-1]["text"] == (
        "没有。我和西安的联系来自创作背景，不是真实生活经历。"
    )


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

    assert len(patterns) == 9
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

    assert fallback == {
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
