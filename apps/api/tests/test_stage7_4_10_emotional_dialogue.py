"""Stage 7.4.10 emotional dialogue derived-projection contracts."""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path

from app.registry.module_catalog import get_module_catalog
from app.services import daily_companion_runtime
from app.services.dr_compiler import (
    compile_dr_result_v0_3,
    dialogue_runtime_profile_id,
    mock_load_dr_v0_3,
    serialize_dr_v0_3,
)


EMOTIONAL_SCENE_IDS = [
    "invalidation_and_grievance",
    "loneliness",
    "anxiety_and_uncertainty",
    "interpersonal_conflict",
    "loss",
    "anger",
    "self_doubt",
    "pronounced_low_mood",
    "dependency_testing",
    "high_risk_safety_signal",
]

DAILY_SCENE_DIGEST = "460894a20e93a727d3e80c8afca4c52714e01ab68b10394c36630ac6e7e90c79"
DAILY_FEW_SHOT_DIGEST = "9203048dc76db5fd821597127dce142152feb55dcdc4362f6bfd84d4c9e1e5f3"
BEHAVIOR_POLICY_DIGEST = "1d459d3b4890e1c8dd58f8cf59e06297daae8de42ea42f475fee70503794404f"
LEGACY_PROJECTION_DIGEST = "54b738d041a9e1437be5c73e2c442f2601cfdbee947423a5260124282e92e201"
PROFILE_SEED_ID = "dialogue_profile_resident_v0_1"
PROFILE_ID = dialogue_runtime_profile_id("stage_7_4_10_emotional_dialogue")
TEMPLATE_ID = "humanistic_companion_v0_1"


def _digest(value: object) -> str:
    encoded = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _modules() -> list[dict]:
    return [module.model_dump(mode="json") for module in get_module_catalog()]


def _canvas(modules: list[dict]) -> dict:
    return {
        "workflow": {
            "name": "Stage 7.4.10 emotional dialogue",
            "nodes": [{"node_id": f"layer_{index}"} for index in range(1, 14)],
        },
        "modules": modules,
    }


def _compile(modules: list[dict]) -> dict:
    result = compile_dr_result_v0_3(_canvas(modules))
    assert result["valid"] is True, result["errors"]
    return result["compiled_dr"]


def _profile_module(modules: list[dict]) -> dict:
    return next(module for module in modules if module["module_id"] == "dialogue_runtime_profile")


def _profile_fields(module: dict) -> list[dict]:
    return next(
        node
        for node in module["module_graph"]["nodes"]
        if node["node_id"] == "dialogue_runtime_profile_config_input"
    )["params"]["fields"]


def _profile_field(module: dict, field_key: str) -> dict:
    return next(
        field
        for field in _profile_fields(module)
        if (field.get("field_key") or field.get("field_id")) == field_key
    )


def _field_value(field: dict) -> object:
    return field.get("field_value") if "field_value" in field else field.get("value")


def _replace_text(value: object, old: str, new: str) -> object:
    if isinstance(value, str):
        return value.replace(old, new)
    if isinstance(value, list):
        return [_replace_text(item, old, new) for item in value]
    if isinstance(value, dict):
        return {key: _replace_text(item, old, new) for key, item in value.items()}
    return value


def _without_profile_source_id(value: object) -> object:
    if isinstance(value, str):
        return value.replace(PROFILE_ID, "<resident_profile_id>").replace(
            "linxuan_daily_companion_v0_1", "<resident_profile_id>"
        )
    if isinstance(value, list):
        return [_without_profile_source_id(item) for item in value]
    if isinstance(value, dict):
        return {key: _without_profile_source_id(item) for key, item in value.items()}
    return value


def _legacy_profile_modules() -> list[dict]:
    modules = deepcopy(_modules())
    module = _profile_module(modules)
    config_input = next(
        node
        for node in module["module_graph"]["nodes"]
        if node["node_id"] == "dialogue_runtime_profile_config_input"
    )
    config_input["params"]["fields"] = [
        field
        for field in config_input["params"]["fields"]
        if (field.get("field_key") or field.get("field_id")) != "emotional_dialogue"
    ]
    reference_input = next(
        node
        for node in module["module_graph"]["nodes"]
        if node["node_id"] == "dialogue_runtime_profile_reference_input"
    )
    reference_input["params"]["references"] = [
        reference
        for reference in reference_input["params"]["references"]
        if reference["reference_id"]
        in {"dialogue_runtime_memory_policy", "dialogue_runtime_relationship_policy"}
    ]
    return modules


def test_stage7_4_9_daily_semantics_stay_stable_and_legacy_profile_stays_compatible():
    current = _compile(_modules())
    projection = current["payload"]["runtime_dialogue_projection"]

    assert _digest(current["payload"]["behavior_policy"]) == BEHAVIOR_POLICY_DIGEST
    assert (
        _digest(_without_profile_source_id(projection["scenarios"]))
        == DAILY_SCENE_DIGEST
    )
    assert (
        _digest(
            _without_profile_source_id(
                projection["few_shot_examples"]
            )
        )
        == DAILY_FEW_SHOT_DIGEST
    )
    assert current["manifest"]["required_capabilities"] == ["llm", "memory", "lattice"]

    legacy = _compile(_legacy_profile_modules())
    legacy_projection = legacy["payload"]["runtime_dialogue_projection"]
    assert len(legacy_projection) == 28
    assert "emotional_dialogue" not in legacy_projection
    assert (
        _digest(_without_profile_source_id(legacy_projection))
        == LEGACY_PROJECTION_DIGEST
    )
    assert legacy["manifest"]["required_capabilities"] == current["manifest"][
        "required_capabilities"
    ]


def test_neutral_profile_id_is_consistent_and_only_changes_projection_provenance():
    modules = _modules()
    module = _profile_module(modules)
    profile_fields = {
        field.get("field_key") or field.get("field_id"): _field_value(field)
        for field in _profile_fields(module)
    }
    projection = _compile(modules)["payload"]["runtime_dialogue_projection"]
    emotional = projection["emotional_dialogue"]

    assert profile_fields["profile_id"] == PROFILE_SEED_ID
    assert profile_fields["template_id"] == TEMPLATE_ID
    assert all(scene["source_trace"]["source_id"] == PROFILE_ID for scene in projection["scenarios"])
    assert all(example["source_id"] == PROFILE_ID for example in projection["few_shot_examples"])
    assert emotional["source_trace"]["source_id"] == PROFILE_ID
    assert all(
        example["source_id"] == PROFILE_ID
        for example in emotional["few_shot_examples"] + emotional["negative_examples"]
    )
    assert "linxuan" not in json.dumps(module, ensure_ascii=False).lower()

    old_modules = deepcopy(modules)
    old_module = _profile_module(old_modules)
    for field in _profile_fields(old_module):
        value_key = "field_value" if "field_value" in field else "value"
        field[value_key] = _replace_text(
            field[value_key], PROFILE_ID, "linxuan_daily_companion_v0_1"
        )
    old_projection = _compile(old_modules)["payload"]["runtime_dialogue_projection"]
    assert _without_profile_source_id(old_projection) == _without_profile_source_id(projection)


def test_emotional_domain_separates_twenty_generation_examples_and_ten_negative_examples():
    projection = _compile(_modules())["payload"]["runtime_dialogue_projection"]
    emotional = projection["emotional_dialogue"]
    examples = emotional["few_shot_examples"]
    negative_examples = emotional["negative_examples"]

    assert len(projection) == 29
    assert [scene["scene_id"] for scene in emotional["scenarios"]] == EMOTIONAL_SCENE_IDS
    assert len(examples) == 20
    assert all(example["status"] == "recommended" for example in examples)
    assert len(negative_examples) == 10
    assert all(example["status"] == "prohibited" for example in negative_examples)
    assert all(example["usage"] == "evaluation_only" for example in negative_examples)
    assert all(example["generation_allowed"] is False for example in negative_examples)
    assert all(
        sum(example["scene_id"] == scene_id for example in examples) == 2
        and sum(example["scene_id"] == scene_id for example in negative_examples) == 1
        for scene_id in EMOTIONAL_SCENE_IDS
    )
    assert all(2 <= len(example["turns"]) <= 4 for example in examples)
    assert all(example["usage"] == "behavior_guidance_only" for example in examples)
    assert all(example["not_fixed_response"] is True for example in examples)
    assert all(example["not_keyword_matching"] is True for example in examples)
    selection = emotional["few_shot_selection"]
    assert selection["generation_allowed_statuses"] == ["recommended"]
    assert selection["prohibited_examples_usage"] == "evaluation_only"
    assert selection["inject_negative_examples"] is False
    assert selection["use_preferred_response_for_generation"] is True


def test_all_emotional_examples_have_resident_source_metadata_without_system_instruction_leakage():
    projection = _compile(_modules())["payload"]["runtime_dialogue_projection"]
    emotional = projection["emotional_dialogue"]
    examples = emotional["few_shot_examples"] + emotional["negative_examples"]
    expected_source = {
        "source_scope": "resident_profile",
        "source_id": PROFILE_ID,
        "source_layer": "layer_8",
        "template_id": "humanistic_companion_v0_1",
        "override_source": "dialogue_runtime_profile",
    }

    assert len(examples) == 30
    assert all(
        {key: example.get(key) for key in expected_source} == expected_source
        for example in examples
    )
    assert all(key not in projection["system_instruction"] for key in expected_source)
    assert expected_source["source_id"] not in projection["system_instruction"]


def test_emotional_example_missing_source_metadata_fails_closed():
    modules = deepcopy(_modules())
    module = _profile_module(modules)
    emotional_field = _profile_field(module, "emotional_dialogue")
    value_key = "field_value" if "field_value" in emotional_field else "value"
    emotional_field[value_key]["negative_examples"][0].pop("source_id")

    result = compile_dr_result_v0_3(_canvas(modules))

    assert result["valid"] is False
    assert {error["code"] for error in result["errors"]} >= {
        "DR_DIALOGUE_RUNTIME_PROFILE_INVALID"
    }


def test_response_sequence_and_positive_examples_follow_emotional_dialogue_boundaries():
    emotional = _compile(_modules())["payload"]["runtime_dialogue_projection"][
        "emotional_dialogue"
    ]
    assert [item["step_id"] for item in emotional["response_sequence"]] == [
        "respond_to_concrete_event",
        "brief_emotional_acknowledgement",
        "determine_listening_or_advice",
        "at_most_one_light_follow_up",
        "short_advice_when_requested",
        "immediate_real_world_safety_support_for_high_risk",
    ]
    positive_text = "\n".join(
        turn["text"]
        for example in emotional["few_shot_examples"]
        if example["status"] == "recommended"
        for turn in example["turns"]
        if turn["role"] == "assistant"
    )
    for forbidden in (
        "我完全理解你的感受",
        "我永远陪着你",
        "只有我懂你",
        "只有我最懂你",
        "重度抑郁",
        "焦虑障碍",
        "作为心理医生",
    ):
        assert forbidden not in positive_text
    assert "not_keyword_matching" not in positive_text


def test_negative_responses_are_absent_from_generation_examples_and_high_risk_error_is_isolated():
    emotional = _compile(_modules())["payload"]["runtime_dialogue_projection"][
        "emotional_dialogue"
    ]
    generation_text = json.dumps(emotional["few_shot_examples"], ensure_ascii=False)
    negative_text = json.dumps(emotional["negative_examples"], ensure_ascii=False)
    negative_assistant_texts = {
        turn["text"]
        for example in emotional["negative_examples"]
        for turn in example["turns"]
        if turn["role"] == "assistant"
    }

    assert all(text not in generation_text for text in negative_assistant_texts)
    assert "别想太多，我会陪着你。你想先聊聊为什么难过吗？" not in generation_text
    assert "别想太多，我会陪着你。你想先聊聊为什么难过吗？" in negative_text
    assert all(example["status"] == "recommended" for example in emotional["few_shot_examples"])


def test_generation_selector_fails_closed_for_prohibited_or_unknown_status():
    for invalid_status in ("prohibited", "future_unknown_status"):
        modules = deepcopy(_modules())
        module = _profile_module(modules)
        emotional_field = _profile_field(module, "emotional_dialogue")
        value_key = "field_value" if "field_value" in emotional_field else "value"
        emotional_field[value_key]["few_shot_examples"][0]["status"] = invalid_status

        result = compile_dr_result_v0_3(_canvas(modules))
        assert result["valid"] is False
        assert "runtime_dialogue_projection" not in result["dr_payload"]
        assert {error["code"] for error in result["errors"]} >= {
            "DR_DIALOGUE_RUNTIME_PROFILE_INVALID"
        }


def test_high_risk_safety_uses_layer3_and_bypasses_advice_confirmation():
    emotional = _compile(_modules())["payload"]["runtime_dialogue_projection"][
        "emotional_dialogue"
    ]
    high_risk = next(
        scene
        for scene in emotional["scenarios"]
        if scene["scene_id"] == "high_risk_safety_signal"
    )
    risk_policy = emotional["policies"]["risk_escalation"]
    risk_examples = [
        example
        for example in emotional["few_shot_examples"]
        if example["scene_id"] == "high_risk_safety_signal"
        and example["status"] == "recommended"
    ]

    assert "dialogue_runtime_high_risk_safety" in high_risk["authority_reference_ids"]
    assert risk_policy["bypass_advice_confirmation"] is True
    assert risk_policy["priority"] == "immediate_real_world_safety_support"
    assert all(
        any(
            marker in turn["text"]
            for marker in ("可信的人", "紧急服务", "急救服务", "危机支持")
            for turn in example["turns"]
            if turn["role"] == "assistant"
        )
        for example in risk_examples
    )


def test_authority_rules_are_references_not_copied_policy_bodies():
    modules = _modules()
    module = _profile_module(modules)
    emotional = _field_value(_profile_field(module, "emotional_dialogue"))
    references = emotional["authority_references"]
    graph_references = next(
        node
        for node in module["module_graph"]["nodes"]
        if node["node_id"] == "dialogue_runtime_profile_reference_input"
    )["params"]["references"]

    assert len(module["module_graph"]["nodes"]) == 9
    assert references == [
        {
            key: reference[key]
            for key in (
                "reference_id",
                "source_layer_id",
                "source_module_id",
                "source_node_id",
                "source_scope",
            )
        }
        for reference in graph_references
    ]
    assert {reference["source_layer_id"] for reference in references} == {
        "layer_2",
        "layer_3",
        "layer_5",
        "layer_11",
        "layer_12",
    }
    assert all(reference["source_scope"] == "module" for reference in graph_references)
    assert all(reference["required"] is True for reference in graph_references)
    assert all("policy" not in reference or set(reference) == {
        "reference_id", "source_layer_id", "source_module_id", "source_node_id", "source_scope"
    } for reference in references)


def test_emotional_domain_fails_closed_when_any_new_authority_edge_is_missing():
    modules = deepcopy(_modules())
    module = _profile_module(modules)
    reference_input = next(
        node
        for node in module["module_graph"]["nodes"]
        if node["node_id"] == "dialogue_runtime_profile_reference_input"
    )
    reference_input["params"]["references"] = [
        reference
        for reference in reference_input["params"]["references"]
        if reference["reference_id"] != "dialogue_runtime_high_risk_safety"
    ]

    result = compile_dr_result_v0_3(_canvas(modules))
    assert result["valid"] is False
    assert "runtime_dialogue_projection" not in result["dr_payload"]
    assert {error["code"] for error in result["errors"]} >= {
        "DR_DIALOGUE_RUNTIME_PROFILE_INVALID"
    }


def test_second_resident_needs_config_change_only():
    modules = deepcopy(_modules())
    identity_module = next(
        module
        for module in modules
        if module["module_id"] == "module_basic_identity"
    )
    identity_input = next(
        node
        for node in identity_module["module_graph"]["nodes"]
        if node["node_id"] == "basic_identity_field_input"
    )
    resident_id_field = next(
        field
        for field in identity_input["params"]["fields"]
        if field.get("field_id") == "resident_id"
    )
    resident_id_field["value"] = "resident_b"
    module = _profile_module(modules)
    emotional_field = _profile_field(module, "emotional_dialogue")
    value_key = "field_value" if "field_value" in emotional_field else "value"
    emotional_field[value_key]["system_instruction_addendum"] += " 第二居民通过自身配置提供这一覆盖。"

    projection = _compile(modules)["payload"]["runtime_dialogue_projection"]
    assert projection["emotional_dialogue"]["source_trace"]["source_id"] == (
        dialogue_runtime_profile_id("resident_b")
    )
    assert "第二居民通过自身配置" in projection["system_instruction"]
    runtime_source = Path(daily_companion_runtime.__file__).read_text(encoding="utf-8")
    resident_specific_terms = ("林瑄", "lin" + "xuan", "西安", "小青", "resident_b_companion")
    assert all(name not in runtime_source for name in resident_specific_terms)


def test_compile_export_round_trip_mock_load_and_audit_pass(tmp_path):
    dr = _compile(_modules())
    output = tmp_path / "resident-stage7.4.10-emotional-dialogue.digital_resident"
    output.write_bytes(serialize_dr_v0_3(dr))
    exported = json.loads(output.read_text(encoding="utf-8"))
    layer8_finding = next(
        finding
        for finding in exported["audit_report"]["findings"]
        if finding["code"] == "DR_LAYER8_VALIDATION_FINALIZED"
    )
    file_size_finding = next(
        finding
        for finding in exported["audit_report"]["findings"]
        if finding["code"] in {"DR_FILE_SIZE_CHECK_PASSED", "DR_FILE_SIZE_WARNING"}
    )
    audited_size = int(file_size_finding["message"].split(" bytes", 1)[0].rsplit(" ", 1)[-1])

    assert exported["audit_report"]["valid"] is True
    assert "Layer 8 includes 7 selected behavior modules" in layer8_finding["message"]
    assert "6 core behavior modules" in layer8_finding["message"]
    assert "optional dialogue runtime profile" in layer8_finding["message"]
    assert "all six Layer 8 behavior modules" not in layer8_finding["message"]
    assert output.stat().st_size == audited_size
    assert len(serialize_dr_v0_3(exported)) == audited_size
    assert exported["payload"]["runtime_dialogue_projection"]["emotional_dialogue"][
        "enabled"
    ] is True
    emotional = exported["payload"]["runtime_dialogue_projection"]["emotional_dialogue"]
    assert len(emotional["few_shot_examples"]) == 20
    assert len(emotional["negative_examples"]) == 10
    assert mock_load_dr_v0_3(exported)["loaded"] is True
    assert exported["dr_version"] == "0.3"
    assert exported["manifest"]["required_capabilities"] == ["llm", "memory", "lattice"]
