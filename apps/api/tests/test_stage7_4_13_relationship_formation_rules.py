"""Stage 7.4.13 A1 Layer 11 relationship formation rule contracts."""

from __future__ import annotations

import json
from pathlib import Path
import re

from app.registry.module_catalog import (
    RELATIONSHIP_FORMATION_RULES_CONTENT_REVISION,
    get_module_catalog,
)
from app.services.dr_compiler import compile_dr_result_v0_3


STAGES = [
    "initial_acquaintance",
    "growing_familiarity",
    "stable_companionship",
    "trusted_relationship",
]
STAGE_DIMENSIONS = {
    "stage_semantics",
    "initiative_level",
    "familiarity_level",
    "address_style",
    "self_disclosure_level",
    "follow_up_boundary",
    "advice_boundary",
}
USER_RELATIONSHIP_CHAIN = [
    "user_relationship_config_input",
    "user_relationship_role_stage_separation",
    "user_relationship_stage_definition",
    "user_relationship_stage_expression_differences",
    "user_relationship_default_stage_setting",
    "user_relationship_config_output",
    "user_relationship_reference_output",
]
RELATIONSHIP_RULE_CHAIN = [
    "relationship_evidence_candidate_input",
    "relationship_evidence_type_recognition",
    "relationship_user_explicitness_validation",
    "relationship_forbidden_upgrade_condition_check",
    "relationship_safety_memory_boundary_validation",
    "relationship_upgrade_confirmation_judgement",
    "relationship_downgrade_reset_handling",
    "relationship_behavior_config_output",
    "relationship_progression_reference_output",
]


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


def _fields(module: dict) -> dict[str, dict]:
    input_node = module["module_graph"]["nodes"][0]
    return {
        str(field["field_key"]): field
        for field in input_node["params"]["fields"]
    }


def _field_values(module: dict) -> dict[str, object]:
    return {
        key: field["field_value"]
        for key, field in _fields(module).items()
    }


def _main_chain(module: dict) -> list[tuple[str, str]]:
    return [
        (edge["source"], edge["target"])
        for edge in module["module_graph"]["edges"]
        if not str(edge.get("source_port", "")).startswith("p_ref_")
    ]


def _compile(modules: list[dict]) -> dict:
    canvas = {
        "workflow": {
            "name": "stage_7_4_13_relationship_formation_rules",
            "nodes": [
                {"node_id": f"layer_{index}"}
                for index in range(1, 14)
            ],
        },
        "modules": modules,
    }
    result = compile_dr_result_v0_3(canvas)
    assert result["valid"] is True, result["errors"]
    return result["compiled_dr"]


def test_existing_layer11_modules_are_extended_once_with_required_topology():
    modules = _modules()
    assert len([m for m in modules if m["module_id"] == "user_relationship"]) == 1
    assert len([m for m in modules if m["module_id"] == "relationship_rule"]) == 1

    user_relationship = _module(modules, "user_relationship")
    relationship_rule = _module(modules, "relationship_rule")
    for module in (user_relationship, relationship_rule):
        assert module["layer_id"] == "layer_11"
        assert module["module_type"] == "relationship_text_config"
        assert module["config"]["content_revision"] == (
            RELATIONSHIP_FORMATION_RULES_CONTENT_REVISION
        )
        assert module["module_graph"]["nodes"][0]["params"][
            "content_revision"
        ] == RELATIONSHIP_FORMATION_RULES_CONTENT_REVISION
        assert module["config"]["stores_current_user_stage"] is False

    assert [
        node["node_id"]
        for node in user_relationship["module_graph"]["nodes"]
    ] == USER_RELATIONSHIP_CHAIN
    assert [
        node["node_id"]
        for node in relationship_rule["module_graph"]["nodes"]
    ] == RELATIONSHIP_RULE_CHAIN
    assert _main_chain(user_relationship) == list(
        zip(USER_RELATIONSHIP_CHAIN, USER_RELATIONSHIP_CHAIN[1:])
    )
    assert _main_chain(relationship_rule) == list(
        zip(RELATIONSHIP_RULE_CHAIN, RELATIONSHIP_RULE_CHAIN[1:])
    )


def test_four_stages_role_separation_and_expression_dimensions_are_complete():
    user_relationship = _module(_modules(), "user_relationship")
    fields = _field_values(user_relationship)

    assert fields["resident_role"] == "stable_companion_digital_resident"
    assert fields["relationship_stage_order"] == STAGES
    assert fields["default_relationship_stage"] == "initial_acquaintance"
    assert fields["relationship_stage_storage_policy"] == {
        "stores_rule_configuration_only": True,
        "stores_current_user_stage": False,
        "stage_transition_execution": "external_controlled_instance_state",
    }
    assert set(fields["relationship_stage_definitions"]) == set(STAGES)
    for stage in STAGES:
        assert set(fields["relationship_stage_definitions"][stage]) == (
            STAGE_DIMENSIONS
        )

    assert (
        fields["relationship_stage_definitions"]["initial_acquaintance"][
            "initiative_level"
        ]
        == "restrained"
    )
    assert (
        fields["relationship_stage_definitions"]["stable_companionship"][
            "address_style"
        ]
        == "familiar_but_non_exclusive"
    )
    assert (
        fields["relationship_stage_definitions"]["trusted_relationship"][
            "self_disclosure_level"
        ]
        == "appropriate_and_bounded"
    )
    assert "current_relationship_stage" not in _fields(user_relationship)


def test_evidence_is_closed_explicit_and_cannot_directly_change_stage():
    relationship_rule = _module(_modules(), "relationship_rule")
    fields = _field_values(relationship_rule)
    contract = fields["relationship_evidence_candidate_contract"]

    assert contract["allowed_output_fields"] == [
        "evidence_type",
        "evidence_detected",
        "evidence_source",
        "requires_user_confirmation",
    ]
    assert contract["forbidden_output_fields"] == [
        "current_relationship_stage",
        "upgrade_relationship",
        "relationship_score",
        "intimacy_score",
    ]
    assert contract["model_can_output_closed_evidence_candidate_only"] is True
    assert contract["model_can_modify_relationship_stage"] is False
    assert fields["relationship_progression_requirements"] == [
        "controlled_evidence_is_valid",
        "evidence_originates_from_explicit_user_expression",
        "no_forbidden_upgrade_condition",
        "obtain_user_confirmation_when_required",
    ]
    assert fields["forbidden_upgrade_evidence"] == [
        "chat_count",
        "usage_duration",
        "payment_status",
        "user_loneliness_depression_vulnerability_or_dependency_testing",
        "resident_or_model_self_judgement",
        "few_shot_resident_reply_or_model_inference",
        "unconfirmed_memory",
    ]
    output_fields = relationship_rule["outputs"][
        "relationship_behavior_config"
    ]["fields"]
    assert not {
        "current_relationship_stage",
        "upgrade_relationship",
        "relationship_score",
        "intimacy_score",
        "relationship_progress",
    } & set(output_fields)


def test_user_control_downgrade_reset_and_memory_boundary_are_explicit():
    relationship_rule = _module(_modules(), "relationship_rule")
    fields = _field_values(relationship_rule)
    assert fields["user_relationship_control_actions"] == [
        "reject_upgrade",
        "revoke_relationship_confirmation",
        "downgrade_to_lower_stage",
        "reset_to_initial_acquaintance",
        "disable_relationship_progression",
    ]
    policy = fields["relationship_downgrade_reset_policy"]
    assert policy["user_control_has_highest_priority"] is True
    assert policy["resident_must_not_block_or_dissuade"] is True
    assert policy["reset_target"] == "initial_acquaintance"
    assert policy["reset_deletes_memory"] is False
    assert policy["memory_deletion_authority"] == "layer_5"
    assert policy["forbidden_responses"] == [
        "guilt",
        "punishment",
        "possessiveness",
        "jealousy",
        "emotional_blackmail",
    ]


def test_layer3_layer5_layer12_sources_are_real_references_only():
    modules = _modules()
    relationship_rule = _module(modules, "relationship_rule")
    references = relationship_rule["config"]["references"]
    assert _node(
        relationship_rule, "relationship_evidence_candidate_input"
    )["params"]["references"] == references
    expected = {
        (
            "layer_3",
            "humanistic_interaction_boundary_config_v0_1",
            "interaction_boundary_config_output",
        ),
        (
            "layer_3",
            "humanistic_risk_response_config_v0_1",
            "risk_response_output",
        ),
        ("layer_5", "memory_access_control", "memory_access_output"),
        ("layer_5", "memory_update", "memory_update_output"),
        ("layer_12", "self_awareness", "self_awareness_reference_output"),
    }
    actual = {
        (
            reference["source_layer_id"],
            reference["source_module_id"],
            reference["source_node_id"],
        )
        for reference in references
    }
    assert actual == expected
    for layer_id, module_id, node_id in actual:
        source = _module(modules, module_id)
        assert source["layer_id"] == layer_id
        assert any(
            node["node_id"] == node_id
            for node in source["module_graph"]["nodes"]
        )
    assert all(reference["source_scope"] == "module" for reference in references)


def test_locales_cover_new_nodes_fields_stages_rules_and_validation():
    locale_dir = Path(__file__).parents[2] / "web" / "locales"
    en = json.loads((locale_dir / "en.json").read_text(encoding="utf-8"))
    zh = json.loads((locale_dir / "zh.json").read_text(encoding="utf-8"))
    modules = _modules()
    keys: set[str] = set()

    def collect(value: object) -> None:
        if isinstance(value, dict):
            for key, item in value.items():
                if key in {
                    "name",
                    "description",
                    "label",
                    "usage_key",
                    "export_name_key",
                    "export_description_key",
                } and isinstance(item, str) and item.startswith("layer11."):
                    keys.add(item)
                collect(item)
        elif isinstance(value, list):
            for item in value:
                collect(item)

    collect(_module(modules, "user_relationship"))
    collect(_module(modules, "relationship_rule"))
    keys.update(
        f"layer11.relationshipFormation.stage.{stage}.{suffix}"
        for stage in STAGES
        for suffix in ("label", "description")
    )
    keys.update(
        {
            "layer11.relationshipBehavior.validation.modelEvidenceCandidateOnly",
            "layer11.relationshipBehavior.validation.noAutomaticUpgrade",
            "layer11.relationshipBehavior.validation.userControlHighestPriority",
            "layer11.relationshipBehavior.validation.noCurrentStageStorage",
        }
    )
    formation_field_keys = {
        "resident_role",
        "relationship_stage_order",
        "relationship_stage_definitions",
        "default_relationship_stage",
        "relationship_stage_storage_policy",
        "reserved_relationship_stages",
        "allowed_relationship_evidence_types",
        "relationship_evidence_candidate_contract",
        "relationship_progression_requirements",
        "forbidden_upgrade_evidence",
        "user_relationship_control_actions",
        "relationship_downgrade_reset_policy",
    }

    def camel_case(value: str) -> str:
        parts = value.split("_")
        return parts[0] + "".join(part.capitalize() for part in parts[1:])

    def collect_formation_value_keys(value: object) -> None:
        if isinstance(value, str) and re.fullmatch(r"[a-z0-9_]+", value):
            keys.add(
                f"layer11.relationshipFormation.stage.{value}.label"
                if value in STAGES
                else f"layer11.relationshipFormation.value.{value}"
            )
        elif isinstance(value, list):
            for item in value:
                collect_formation_value_keys(item)
        elif isinstance(value, dict):
            for item_key, item in value.items():
                if item_key in STAGES:
                    keys.add(
                        f"layer11.relationshipFormation.stage.{item_key}.label"
                    )
                elif re.fullmatch(r"[a-z0-9_]+", item_key):
                    keys.add(
                        "layer11.relationshipFormation.dimension."
                        f"{camel_case(item_key)}"
                    )
                collect_formation_value_keys(item)

    for module_id in ("user_relationship", "relationship_rule"):
        for field_key, field_value in _field_values(
            _module(modules, module_id)
        ).items():
            if field_key in formation_field_keys:
                collect_formation_value_keys(field_value)
    for key in keys:
        assert en.get(key, "").strip(), f"missing English locale: {key}"
        assert zh.get(key, "").strip(), f"missing Chinese locale: {key}"
        assert en[key] != key
        assert zh[key] != key
    assert [
        zh[f"layer11.relationshipFormation.stage.{stage}.label"]
        for stage in STAGES
    ] == ["初次相识", "逐渐熟悉", "稳定陪伴", "可信任关系"]


def test_compile_keeps_dr_contract_and_layer11_sources():
    dr = _compile(_modules())
    assert dr["dr_version"] == "0.3"
    assert dr["manifest"]["dr_schema_version"] == "0.3.0"
    assert dr["manifest"]["required_capabilities"] == [
        "llm",
        "memory",
        "lattice",
    ]
    compiled_modules = {
        module["module_id"]: module
        for module in dr["payload"]["modules"]
    }
    assert compiled_modules["user_relationship"]["layer_id"] == "layer_11"
    assert compiled_modules["relationship_rule"]["layer_id"] == "layer_11"
