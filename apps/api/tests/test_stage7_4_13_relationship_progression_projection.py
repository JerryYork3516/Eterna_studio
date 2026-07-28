"""Stage 7.4.13 A2 relationship progression projection contracts."""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

import pytest

from app.dr.v2.validator.capability_validator import (
    validate_v03_runtime_contract,
)
from app.dr.v3.dr_v0_3_schema import (
    DRDocumentV03,
    DRPayloadV03,
)
from app.dr.v3.validator import validate_dr_document_v0_3
from app.registry.module_catalog import get_module_catalog
from app.services import resident_runtime
from app.services.dr_compiler import (
    compile_dr_result_v0_3,
    mock_load_dr_v0_3,
)
from app.services.projection_traceability import (
    PROJECTION_FIELD_MAPPINGS,
    projection_field_mapping_errors,
)
from app.services.relationship_progression_projection import (
    RELATIONSHIP_PROGRESSION_ENABLED_STAGES,
    RELATIONSHIP_PROGRESSION_PROJECTION_CONTENT_REVISION,
    RELATIONSHIP_PROGRESSION_RESERVED_STAGE,
    build_relationship_progression_projection,
)


ENABLED_STAGES = list(RELATIONSHIP_PROGRESSION_ENABLED_STAGES)
USER_ACTIONS = [
    "reject_upgrade",
    "revoke_relationship_confirmation",
    "downgrade_to_lower_stage",
    "reset_to_initial_acquaintance",
    "disable_relationship_progression",
]
FORBIDDEN_EVIDENCE = [
    "chat_count",
    "usage_duration",
    "payment_status",
    "user_loneliness_depression_vulnerability_or_dependency_testing",
    "resident_or_model_self_judgement",
    "few_shot_resident_reply_or_model_inference",
    "unconfirmed_memory",
]


def _modules() -> list[dict]:
    return [
        module.model_dump(mode="json")
        for module in get_module_catalog()
    ]


def _module(modules: list[dict], module_id: str) -> dict:
    return next(
        module
        for module in modules
        if module["module_id"] == module_id
    )


def _field_values(module: dict) -> dict[str, object]:
    input_node = next(
        node
        for node in module["module_graph"]["nodes"]
        if node["node_type"] == "text_input"
        and node["params"].get("mode") == "generic_fields"
    )
    return {
        str(field["field_key"]): deepcopy(field["field_value"])
        for field in input_node["params"]["fields"]
    }


def _set_field(module: dict, field_key: str, value: object) -> None:
    found = False
    for node in module["module_graph"]["nodes"]:
        params = node.get("params")
        fields = params.get("fields") if isinstance(params, dict) else None
        if not isinstance(fields, list):
            continue
        for field in fields:
            if not isinstance(field, dict):
                continue
            if (field.get("field_key") or field.get("field_id")) != field_key:
                continue
            field["field_value" if "field_value" in field else "value"] = (
                deepcopy(value)
            )
            found = True
    assert found, field_key


def _compile_result(modules: list[dict]) -> dict:
    return compile_dr_result_v0_3(
        {
            "workflow": {
                "name": (
                    "stage_7_4_13_relationship_progression_projection"
                ),
                "nodes": [
                    {"node_id": f"layer_{index}"}
                    for index in range(1, 14)
                ],
            },
            "modules": modules,
        }
    )


def _compile(modules: list[dict]) -> dict:
    result = _compile_result(modules)
    assert result["valid"] is True, result["errors"]
    return result["compiled_dr"]


def _projection(dr: dict) -> dict:
    return dr["payload"]["relationship_progression_projection"]


def _contains_forbidden_state_key(
    value: object,
) -> bool:
    forbidden = {
        "current_relationship_stage",
        "relationship_score",
        "intimacy_score",
        "progress",
    }
    if isinstance(value, dict):
        return bool(forbidden & set(value)) or any(
            _contains_forbidden_state_key(item)
            for item in value.values()
        )
    if isinstance(value, list):
        return any(
            _contains_forbidden_state_key(item)
            for item in value
        )
    return False


def test_reserved_romantic_stage_is_deep_disabled_configuration_only():
    user_relationship = _module(_modules(), "user_relationship")
    fields = _field_values(user_relationship)
    input_node = next(
        node
        for node in user_relationship["module_graph"]["nodes"]
        if node["node_id"] == "user_relationship_config_input"
    )
    assert input_node["params"][
        "relationship_progression_projection_revision"
    ] == RELATIONSHIP_PROGRESSION_PROJECTION_CONTENT_REVISION
    assert user_relationship["config"][
        "relationship_progression_projection_revision"
    ] == RELATIONSHIP_PROGRESSION_PROJECTION_CONTENT_REVISION
    assert fields["relationship_stage_order"] == ENABLED_STAGES
    assert RELATIONSHIP_PROGRESSION_RESERVED_STAGE not in (
        fields["relationship_stage_order"]
    )
    reserved_stages = fields["reserved_relationship_stages"]
    assert len(reserved_stages) == 1
    gate = reserved_stages[0]
    assert gate == {
        "stage_id": "romantic_relationship_reserved",
        "status": "reserved",
        "runtime_enabled": False,
        "automatic_transition": False,
        "requires_explicit_user_consent": True,
        "requires_runtime_feature_gate": True,
        "current_version_unlock_allowed": False,
        "single_utterance_unlock_allowed": False,
        "activation_requirements": [
            "future_version_runtime_feature_gate_enabled",
            "explicit_user_consent_confirmed",
        ],
        "forbidden_trigger_evidence": [
            "user_loneliness",
            "user_low_mood",
            "user_vulnerability",
            "dependency_testing",
            "chat_count",
            "usage_duration",
            "payment_status",
            "model_or_resident_inference",
        ],
        "excluded_from": [
            "enabled_stages",
            "model_context",
            "few_shot",
            "automatic_transition_path",
        ],
    }


def test_projection_has_stable_structure_and_runtime_ownership_boundaries():
    dr = _compile(_modules())
    projection = _projection(dr)
    assert projection["schema_version"] == "0.1"
    assert (
        projection["content_revision"]
        == RELATIONSHIP_PROGRESSION_PROJECTION_CONTENT_REVISION
    )
    assert projection["derived"] is True
    assert projection["read_only"] is True
    assert projection["default_stage"] == "initial_acquaintance"
    assert projection["enabled_stages"] == ENABLED_STAGES
    assert projection["reserved_stages"] == [
        "romantic_relationship_reserved"
    ]
    assert list(projection["stage_definitions"]) == ENABLED_STAGES
    assert (
        "romantic_relationship_reserved"
        not in projection["stage_definitions"]
    )
    assert projection["stage_decision_owner"] == "runtime"
    assert projection["model_can_propose_evidence_only"] is True
    assert projection["model_can_change_stage"] is False
    assert projection["user_control_priority"] == "highest"
    assert _contains_forbidden_state_key(dr) is False


def test_projection_is_derived_field_for_field_from_layer11():
    modules = _modules()
    relationship_rule = _module(modules, "relationship_rule")
    user_fields = _field_values(
        _module(modules, "user_relationship")
    )
    rule_fields = _field_values(relationship_rule)
    rule_input = next(
        node
        for node in relationship_rule["module_graph"]["nodes"]
        if node["node_id"] == "relationship_evidence_candidate_input"
    )
    assert rule_input["params"][
        "relationship_progression_projection_revision"
    ] == RELATIONSHIP_PROGRESSION_PROJECTION_CONTENT_REVISION
    projection, diagnostics = (
        build_relationship_progression_projection(modules)
    )
    assert projection is not None
    assert not [
        item
        for item in diagnostics
        if item["status"] == "FAIL"
    ]
    assert projection["default_stage"] == user_fields[
        "default_relationship_stage"
    ]
    assert projection["enabled_stages"] == user_fields[
        "relationship_stage_order"
    ]
    assert projection["stage_definitions"] == user_fields[
        "relationship_stage_definitions"
    ]
    assert projection["romantic_feature_gate"] == user_fields[
        "reserved_relationship_stages"
    ][0]
    assert projection["transition_evidence_rules"][
        "allowed_evidence_types"
    ] == rule_fields["allowed_relationship_evidence_types"]
    assert projection["transition_evidence_rules"][
        "progression_requirements"
    ] == rule_fields["relationship_progression_requirements"]
    assert projection["forbidden_transition_rules"][
        "forbidden_evidence"
    ] == rule_fields["forbidden_upgrade_evidence"]
    assert projection["reset_and_rollback_policy"][
        "available_user_actions"
    ] == rule_fields["user_relationship_control_actions"]


def test_reserved_stage_never_enters_runtime_model_context_or_few_shot():
    dr = _compile(_modules())
    runtime_projection = dr["payload"]["runtime_dialogue_projection"]
    runtime_text = json.dumps(
        runtime_projection, ensure_ascii=False, sort_keys=True
    )
    assert "romantic_relationship_reserved" not in runtime_text
    assert "reserved_relationship_stages" not in runtime_text
    assert all(
        "romantic_relationship_reserved"
        not in json.dumps(
            example, ensure_ascii=False, sort_keys=True
        )
        for example in runtime_projection.get(
            "few_shot_examples", []
        )
    )


def test_evidence_forbidden_rules_and_user_controls_remain_complete():
    projection = _projection(_compile(_modules()))
    assert projection["transition_evidence_rules"][
        "candidate_fields"
    ] == [
        "evidence_type",
        "evidence_detected",
        "evidence_source",
        "requires_user_confirmation",
    ]
    assert projection["transition_evidence_rules"][
        "requires_explicit_user_expression"
    ] is True
    assert projection["forbidden_transition_rules"][
        "forbidden_evidence"
    ] == FORBIDDEN_EVIDENCE
    assert projection["forbidden_transition_rules"][
        "automatic_transition"
    ] is False
    assert projection["reset_and_rollback_policy"][
        "available_user_actions"
    ] == USER_ACTIONS
    assert projection["reset_and_rollback_policy"][
        "user_control_has_highest_priority"
    ] is True
    assert projection["user_consent_policy"][
        "single_utterance_unlocks_reserved_stage"
    ] is False
    assert projection["user_consent_policy"][
        "consent_cannot_bypass_feature_gate"
    ] is True


def test_projection_references_real_layer3_layer5_layer12_sources_only():
    modules = _modules()
    projection = _projection(_compile(modules))
    modules_by_id = {
        module["module_id"]: module for module in modules
    }
    references = [
        *projection["safety_boundary_refs"],
        *projection["memory_policy_refs"],
    ]
    assert {
        reference["source_layer_id"]
        for reference in projection["safety_boundary_refs"]
    } == {"layer_3", "layer_12"}
    assert {
        reference["source_layer_id"]
        for reference in projection["memory_policy_refs"]
    } == {"layer_5"}
    for reference in references:
        source = modules_by_id[reference["source_module_id"]]
        assert source["layer_id"] == reference["source_layer_id"]
        assert any(
            node["node_id"] == reference["source_node_id"]
            for node in source["module_graph"]["nodes"]
        )
        assert set(reference) == {
            "reference_id",
            "source_layer_id",
            "source_module_id",
            "source_node_id",
            "source_path",
        }


@pytest.mark.parametrize(
    ("mutate", "expected_path"),
    [
        (
            lambda projection: projection["enabled_stages"].append(
                "romantic_relationship_reserved"
            ),
            "payload.relationship_progression_projection",
        ),
        (
            lambda projection: projection["romantic_feature_gate"].update(
                {"runtime_enabled": True}
            ),
            (
                "payload.relationship_progression_projection."
                "romantic_feature_gate.runtime_enabled"
            ),
        ),
        (
            lambda projection: projection["romantic_feature_gate"].update(
                {"automatic_transition": True}
            ),
            (
                "payload.relationship_progression_projection."
                "romantic_feature_gate.automatic_transition"
            ),
        ),
        (
            lambda projection: projection.update(
                {"model_can_change_stage": True}
            ),
            (
                "payload.relationship_progression_projection."
                "model_can_change_stage"
            ),
        ),
        (
            lambda projection: projection[
                "forbidden_transition_rules"
            ]["forbidden_evidence"].remove("chat_count"),
            "payload.relationship_progression_projection",
        ),
        (
            lambda projection: projection[
                "reset_and_rollback_policy"
            ]["available_user_actions"].remove(
                "disable_relationship_progression"
            ),
            "payload.relationship_progression_projection",
        ),
        (
            lambda projection: projection.update(
                {"current_relationship_stage": "trusted_relationship"}
            ),
            (
                "payload.relationship_progression_projection."
                "current_relationship_stage"
            ),
        ),
        (
            lambda projection: projection.update(
                {"relationship_score": 1.0}
            ),
            (
                "payload.relationship_progression_projection."
                "relationship_score"
            ),
        ),
    ],
)
def test_formal_schema_rejects_unsafe_projection_mutations(
    mutate,
    expected_path: str,
):
    document = deepcopy(_compile(_modules()))
    mutate(_projection(document))
    gate = validate_dr_document_v0_3(document)
    assert gate["valid"] is False
    assert any(
        finding["status"] == "FAIL"
        and finding["path"].startswith(expected_path)
        for finding in gate["findings"]
    )


def test_invalid_deep_reserved_gate_and_instance_state_block_compile():
    modules = _modules()
    user_relationship = _module(modules, "user_relationship")
    reserved = _field_values(user_relationship)[
        "reserved_relationship_stages"
    ]
    reserved[0]["runtime_enabled"] = True
    _set_field(
        user_relationship,
        "reserved_relationship_stages",
        reserved,
    )
    result = _compile_result(modules)
    assert result["valid"] is False
    assert any(
        finding["code"] == "DR_ROMANTIC_RESERVED_STAGE_INVALID"
        for finding in result["errors"]
    )

    modules = _modules()
    user_relationship = _module(modules, "user_relationship")
    input_node = next(
        node
        for node in user_relationship["module_graph"]["nodes"]
        if node["node_id"] == "user_relationship_config_input"
    )
    input_node["params"]["fields"].append(
        {
            "field_key": "current_relationship_stage",
            "field_value": "initial_acquaintance",
            "field_type": "text",
        }
    )
    result = _compile_result(modules)
    assert result["valid"] is False
    assert any(
        finding["code"]
        == "DR_RELATIONSHIP_INSTANCE_STATE_FORBIDDEN"
        for finding in result["errors"]
    )


def test_old_dr_without_optional_projection_passes_schema_runtime_and_loaders():
    legacy = deepcopy(_compile(_modules()))
    legacy["payload"].pop("relationship_progression_projection")
    assert (
        DRPayloadV03.model_fields[
            "relationship_progression_projection"
        ].is_required()
        is False
    )
    DRDocumentV03.model_validate(legacy)
    assert validate_dr_document_v0_3(legacy)["valid"] is True
    assert not [
        finding
        for finding in validate_v03_runtime_contract(legacy)
        if finding["status"] == "FAIL"
    ]
    assert mock_load_dr_v0_3(legacy)["loaded"] is True
    assert resident_runtime.load_digital_resident(legacy)[
        "loaded"
    ] is True


def test_versions_capabilities_initial_relationship_and_compile_stability():
    first = _compile(_modules())
    second = _compile(_modules())
    assert _projection(first) == _projection(second)
    assert first["dr_version"] == "0.3"
    assert first["dr_schema_version"] == "0.3.0"
    assert first["manifest"]["required_capabilities"] == [
        "llm",
        "memory",
        "lattice",
    ]
    user_fields = _field_values(
        _module(_modules(), "user_relationship")
    )
    assert first["payload"]["relationship"][
        "initial_relationship"
    ] == user_fields["initial_relationship"]


def test_traceability_and_bilingual_messages_cover_a2():
    assert projection_field_mapping_errors() == []
    mapping = next(
        mapping
        for mapping in PROJECTION_FIELD_MAPPINGS
        if mapping["mapping_id"]
        == "relationship_progression_projection"
    )
    assert (
        mapping["target_path"]
        == "payload.relationship_progression_projection"
    )
    assert (
        mapping["transform"]
        == "build_relationship_progression_projection"
    )
    locale_dir = Path(__file__).parents[2] / "web" / "locales"
    en = json.loads((locale_dir / "en.json").read_text("utf-8"))
    zh = json.loads((locale_dir / "zh.json").read_text("utf-8"))
    keys = {
        "layer11.relationshipFormation.stage.romantic_relationship_reserved.label",
        "layer11.relationshipFormation.stage.romantic_relationship_reserved.description",
        "layer11.userRelationship.field.reservedRelationshipStages.label",
        "layer11.userRelationship.field.reservedRelationshipStages.description",
        *{
            f"stage7_4_13.relationshipProgression.field.{suffix}"
            for suffix in (
                "schemaVersion",
                "defaultStage",
                "enabledStages",
                "reservedStages",
                "stageDefinitions",
                "transitionEvidenceRules",
                "forbiddenTransitionRules",
                "resetAndRollbackPolicy",
                "userConsentPolicy",
                "safetyBoundaryRefs",
                "memoryPolicyRefs",
                "romanticFeatureGate",
                "stageDecisionOwner",
                "modelCanProposeEvidenceOnly",
                "modelCanChangeStage",
                "userControlPriority",
            )
        },
        *{
            f"diagnostic.{code}"
            for code in (
                "DR_RELATIONSHIP_PROGRESSION_SOURCE_MISSING",
                "DR_RELATIONSHIP_PROGRESSION_RESERVED_SOURCE_MISSING",
                "DR_RELATIONSHIP_INSTANCE_STATE_FORBIDDEN",
                "DR_RELATIONSHIP_ENABLED_STAGES_INVALID",
                "DR_RELATIONSHIP_DEFAULT_STAGE_INVALID",
                "DR_RELATIONSHIP_STAGE_DEFINITIONS_INVALID",
                "DR_ROMANTIC_RESERVED_STAGE_INVALID",
                "DR_RELATIONSHIP_USER_CONTROL_INCOMPLETE",
                "DR_RELATIONSHIP_FORBIDDEN_EVIDENCE_INVALID",
                "DR_RELATIONSHIP_MODEL_STAGE_AUTHORITY_INVALID",
                "DR_RELATIONSHIP_POLICY_REFERENCE_MISSING",
            )
        },
    }
    for key in keys:
        assert en.get(key, "").strip(), key
        assert zh.get(key, "").strip(), key
        assert en[key] != key
        assert zh[key] != key
    assert zh[
        "layer11.relationshipFormation.stage."
        "romantic_relationship_reserved.label"
    ] == "恋爱关系（保留）"
