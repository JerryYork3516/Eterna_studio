"""Stage 7.4.13 relationship fact-source and runtime-state compatibility."""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

from app.registry.module_catalog import (
    RELATIONSHIP_SINGLE_SOURCE_RUNTIME_STATE_FIX_REVISION,
    get_module_catalog,
)
from app.services.dr_compiler import compile_dr_result_v0_3


STAGES = [
    "initial_acquaintance",
    "growing_familiarity",
    "stable_companionship",
    "trusted_relationship",
]
LEGACY_STAGES = [
    "initial_contact",
    "basic_familiarity",
    "established_rapport",
    "deep_rapport",
]


def _modules() -> list[dict]:
    return [module.model_dump(mode="json") for module in get_module_catalog()]


def _module(modules: list[dict], module_id: str) -> dict:
    return next(module for module in modules if module["module_id"] == module_id)


def _input_node(module: dict) -> dict:
    return next(
        node
        for node in module["module_graph"]["nodes"]
        if node["node_type"] == "text_input"
        and node["params"].get("mode") == "generic_fields"
    )


def _fields(module: dict) -> dict[str, object]:
    return {
        str(field["field_key"]): deepcopy(field["field_value"])
        for field in _input_node(module)["params"]["fields"]
    }


def _compile(modules: list[dict]) -> dict:
    result = compile_dr_result_v0_3(
        {
            "workflow": {
                "name": "stage_7_4_13_relationship_single_source",
                "nodes": [
                    {"node_id": f"layer_{index}"}
                    for index in range(1, 14)
                ],
            },
            "modules": modules,
        }
    )
    assert result["valid"] is True, result["errors"]
    return result["compiled_dr"]


def _contains_key(value: object, forbidden: set[str]) -> bool:
    if isinstance(value, dict):
        return bool(set(value) & forbidden) or any(
            _contains_key(item, forbidden) for item in value.values()
        )
    if isinstance(value, list):
        return any(_contains_key(item, forbidden) for item in value)
    return False


def test_intimacy_level_references_only_user_relationship_standard_stages():
    module = _module(_modules(), "intimacy_level")
    fields = _fields(module)
    assert fields["relationship_stage_source"] == {
        "source_layer_id": "layer_11",
        "source_module_id": "user_relationship",
        "source_field_path": "relationship_stage_definitions",
        "authority": "reference_only",
    }
    assert fields["default_stage"] == "initial_acquaintance"
    assert fields["stage_order"] == STAGES
    assert list(fields["stage_definitions"]) == STAGES
    serialized = json.dumps(module, ensure_ascii=False)
    assert not any(stage in serialized for stage in LEGACY_STAGES)
    assert not _contains_key(
        module,
        {"relationship_score", "intimacy_score"},
    )
    output = module["outputs"]["relationship_stage_config"]
    assert output["validation_status"] == "pass"
    assert output["risk_items"] == []
    assert output["correction_suggestions"] == []
    assert (
        output["content_revision"]
        == RELATIONSHIP_SINGLE_SOURCE_RUNTIME_STATE_FIX_REVISION
    )


def test_goal_setting_stores_runtime_ownership_rule_not_user_stage():
    module = _module(_modules(), "goal_setting")
    fields = _fields(module)
    assert "current_relationship_state" not in fields
    assert fields["relationship_runtime_state_policy"] == {
        "state_owner": "runtime_user_instance",
        "dr_stores_specific_user_relationship_stage": False,
        "rules": [
            "current_relationship_stage_is_managed_by_runtime_user_instance_state",
            "dr_does_not_store_specific_user_relationship_stage",
        ],
    }
    serialized = json.dumps(module, ensure_ascii=False)
    assert '"current_relationship_state"' not in serialized
    assert '"状态": "稳定陪伴"' not in serialized
    assert (
        _input_node(module)["params"]["content_revision"]
        == RELATIONSHIP_SINGLE_SOURCE_RUNTIME_STATE_FIX_REVISION
    )


def test_compiled_relationship_policies_have_one_stage_system_and_no_instance_state():
    dr = _compile(_modules())
    payload = dr["payload"]
    relationship_policy = payload["runtime_dialogue_projection"][
        "relationship_policy"
    ]
    serialized = json.dumps(
        {
            "modules": payload["modules"],
            "relationship_policy": relationship_policy,
            "relationship_projection": payload[
                "relationship_progression_projection"
            ],
        },
        ensure_ascii=False,
    )
    assert not any(stage in serialized for stage in LEGACY_STAGES)
    assert not _contains_key(
        {
            "modules": payload["modules"],
            "relationship_policy": relationship_policy,
            "relationship_projection": payload[
                "relationship_progression_projection"
            ],
        },
        {
            "current_relationship_state",
            "current_relationship_stage",
            "relationship_score",
            "intimacy_score",
        },
    )
    intimacy_limits = relationship_policy["derived_values"]["intimacy_limits"]
    assert intimacy_limits["stage_order"] == STAGES
    assert list(intimacy_limits["stage_definitions"]) == STAGES
    projection = payload["relationship_progression_projection"]
    assert projection["default_stage"] == "initial_acquaintance"
    assert projection["enabled_stages"] == STAGES
    assert projection["reserved_stages"] == [
        "romantic_relationship_reserved"
    ]
    romantic = projection["romantic_feature_gate"]
    assert romantic["status"] == "reserved"
    assert romantic["runtime_enabled"] is False
    assert romantic["automatic_transition"] is False
    assert "disable_relationship_progression" in projection[
        "reset_and_rollback_policy"
    ]["available_user_actions"]
    assert payload["modules"] == dr["modules"]
    assert dr["dr_version"] == "0.3"
    assert dr["manifest"]["required_capabilities"] == [
        "llm",
        "memory",
        "lattice",
    ]


def test_legacy_compiler_copy_is_migrated_without_duplicate_stages_or_custom_loss():
    modules = _modules()
    intimacy = _module(modules, "intimacy_level")
    intimacy_input = _input_node(intimacy)
    intimacy_input["params"]["fields"] = [
        {
            "field_key": "default_stage",
            "field_value": "initial_contact",
            "field_type": "text",
        },
        {
            "field_key": "stage_order",
            "field_value": LEGACY_STAGES,
            "field_type": "list",
        },
        {
            "field_key": "custom_intimacy_note",
            "field_value": "preserve me",
            "field_type": "text",
        },
    ]
    goal = _module(modules, "goal_setting")
    goal_input = _input_node(goal)
    goal_input["params"]["fields"] = [
        field
        for field in goal_input["params"]["fields"]
        if field["field_key"] != "relationship_runtime_state_policy"
    ]
    goal_input["params"]["fields"].append(
        {
            "field_key": "current_relationship_state",
            "field_value": {"状态": "稳定陪伴"},
            "field_type": "object",
        }
    )

    first = _compile(modules)
    second = _compile(modules)
    assert first["payload"]["modules"] == second["payload"]["modules"]
    assert (
        first["payload"]["runtime_dialogue_projection"]
        == second["payload"]["runtime_dialogue_projection"]
    )
    compiled_modules = first["payload"]["modules"]
    compiled_intimacy = _module(compiled_modules, "intimacy_level")
    compiled_goal = _module(compiled_modules, "goal_setting")
    intimacy_fields = _fields(compiled_intimacy)
    goal_fields = _fields(compiled_goal)
    assert intimacy_fields["stage_order"] == STAGES
    assert intimacy_fields["custom_intimacy_note"] == "preserve me"
    assert "current_relationship_state" not in goal_fields
    assert goal_fields["relationship_runtime_state_policy"][
        "state_owner"
    ] == "runtime_user_instance"
    for module in (compiled_intimacy, compiled_goal):
        params = _input_node(module)["params"]
        assert params["legacy_fields"] == params["fields"]
        assert params["legacy_data_fields"] == params["fields"]
    goal_output = compiled_goal["outputs"][
        "self_state_metacognition_config"
    ]
    assert "current_relationship_state" not in goal_output
    assert "current_relationship_state" not in goal_output["fields"]


def test_bilingual_field_descriptions_use_runtime_ownership_semantics():
    locale_dir = Path(__file__).parents[2] / "web" / "locales"
    en = json.loads((locale_dir / "en.json").read_text("utf-8"))
    zh = json.loads((locale_dir / "zh.json").read_text("utf-8"))
    keys = {
        "layer11.relationshipStage.field.relationshipStageSource.label",
        "layer11.relationshipStage.field.relationshipStageSource.description",
        "layer12.selfStateMetacognition.field.relationshipRuntimeStatePolicy.label",
        "layer12.selfStateMetacognition.field.relationshipRuntimeStatePolicy.description",
        *{
            f"layer11.relationshipStage.stage.{stage}.{suffix}"
            for stage in STAGES
            for suffix in ("name", "description")
        },
    }
    assert all(zh.get(key) and en.get(key) for key in keys)
    assert all(zh[key] != key and en[key] != key for key in keys)


def test_legacy_intimacy_reference_output_pointer_uses_current_module_output():
    modules = _modules()
    legacy_node_id = (
        "layer_11::intimacy_level_reference_output_1783861767696_2"
    )
    for target_module_id in ("growth_plan", "role_positioning"):
        target = _module(modules, target_module_id)
        reference_input = next(
            (
                node
                for node in target["module_graph"]["nodes"]
                if node["node_type"] == "reference_input"
            ),
            None,
        )
        if reference_input is None:
            reference_input = {
                "node_id": f"{target_module_id}_legacy_reference_input",
                "node_type": "reference_input",
                "module_id": target_module_id,
                "layer_id": target["layer_id"],
                "params": {"references": []},
                "position": {"x": 0, "y": 0},
                "outputs": {},
            }
            target["module_graph"]["nodes"].append(reference_input)
        reference_input["params"].setdefault("references", []).append(
            {
                "reference_id": (
                    f"{target_module_id}_legacy_intimacy_reference"
                ),
                "source_layer_id": "layer_11",
                "source_module_id": "intimacy_level",
                "source_node_id": legacy_node_id,
                "source_scope": "module",
                "source_field_paths": [],
                "reference_type": "references",
                "required": True,
            }
        )

    dr = _compile(modules)
    for target_module_id in ("growth_plan", "role_positioning"):
        target = _module(dr["payload"]["modules"], target_module_id)
        references = [
            reference
            for node in target["module_graph"]["nodes"]
            if node["node_type"] == "reference_input"
            for reference in node["params"].get("references", [])
            if reference.get("source_module_id") == "intimacy_level"
        ]
        assert references
        assert all(
            reference["source_node_id"]
            == "relationship_stage_config_output"
            for reference in references
        )
