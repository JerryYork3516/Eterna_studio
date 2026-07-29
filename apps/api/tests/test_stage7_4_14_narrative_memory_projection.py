"""Stage 7.4.14 A2 narrative-memory projection and export gate."""

from __future__ import annotations

from copy import deepcopy

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.dr.v3.dr_v0_3_schema import DRDocumentV03
from app.dr.v3.validator import validate_dr_document_v0_3
from app.main import app
from app.registry.module_catalog import get_module_catalog
from app.services.dr_compiler import (
    _canonical_reference_source_node_id,
    _v3_mock_load_dr,
    compile_dr_result_v0_3,
)
from app.services.narrative_memory_projection import (
    NARRATIVE_MEMORY_ALLOWED_TYPES,
    NARRATIVE_MEMORY_LIFECYCLE_STATES,
    NARRATIVE_MEMORY_PROJECTION_CONTENT_REVISION,
    NARRATIVE_MEMORY_SOURCE_PATHS,
    build_narrative_memory_projection,
)
from app.services.projection_traceability import (
    PROJECTION_FIELD_MAPPINGS,
    projection_field_mapping_errors,
)


SOURCE_MODULE_IDS = (
    "event_memory",
    "memory_update",
    "memory_access_control",
)
client = TestClient(app)


def _modules() -> list[dict]:
    return [
        module.model_dump(mode="json")
        for module in get_module_catalog()
    ]


def _canvas(modules: list[dict]) -> dict:
    return {
        "workflow": {
            "name": "stage_7_4_14_narrative_memory_projection",
            "nodes": [
                {"node_id": f"layer_{index}"}
                for index in range(1, 14)
            ],
        },
        "modules": modules,
    }


def _compile_result(modules: list[dict]) -> dict:
    return compile_dr_result_v0_3(_canvas(modules))


@pytest.fixture(scope="module")
def compiled_result() -> dict:
    result = _compile_result(_modules())
    assert result["valid"] is True, result["errors"]
    return result


@pytest.fixture(scope="module")
def compiled_dr(compiled_result: dict) -> dict:
    return compiled_result["compiled_dr"]


@pytest.fixture(scope="module")
def projection(compiled_dr: dict) -> dict:
    return compiled_dr["payload"]["narrative_memory_projection"]


def _module_output(modules: list[dict], module_id: str) -> dict:
    module = next(
        module
        for module in modules
        if module["module_id"] == module_id
    )
    return module["outputs"][module["module_graph"]["output_key"]]


@pytest.mark.parametrize(
    ("module_id", "legacy_node_id", "expected_node_id"),
    [
        (
            "event_memory",
            "layer_5::event_memory_reference_output_1783773423862_2",
            "narrative_memory_reference_output",
        ),
        (
            "memory_update",
            "layer_5::memory_update_reference_output_1783773617996_2",
            "memory_update_output",
        ),
        (
            "memory_update",
            (
                "layer_5::memory_update::"
                "narrative_memory_update_reference_output"
            ),
            "memory_update_output",
        ),
        (
            "memory_access_control",
            (
                "layer_5::memory_access_control_reference_output_"
                "1783771957851_2"
            ),
            "memory_access_output",
        ),
    ],
)
def test_compiler_canonicalizes_legacy_layer5_reference_output_ids(
    module_id: str,
    legacy_node_id: str,
    expected_node_id: str,
) -> None:
    module = next(
        module
        for module in _modules()
        if module["module_id"] == module_id
    )
    reference = {
        "source_layer_id": "layer_5",
        "source_module_id": module_id,
        "source_node_id": legacy_node_id,
        "source_scope": "module",
        "source_field_paths": [],
    }
    assert (
        _canonical_reference_source_node_id(reference, module)
        == expected_node_id
    )


def test_projection_is_complete_read_only_and_derived_from_layer5(
    projection: dict,
) -> None:
    assert projection["schema_version"] == "0.1"
    assert (
        projection["content_revision"]
        == NARRATIVE_MEMORY_PROJECTION_CONTENT_REVISION
    )
    assert projection["derived"] is True
    assert projection["read_only"] is True
    assert projection["enabled"] is True
    assert projection["source_paths"] == list(
        NARRATIVE_MEMORY_SOURCE_PATHS
    )
    assert {
        "candidate_evidence_rules",
        "forbidden_content_rules",
        "consent_policy",
        "sensitivity_policy",
        "deduplication_policy",
        "conflict_resolution_policy",
        "supersession_policy",
        "deletion_policy",
        "retrieval_policy",
        "expression_policy",
        "model_authority",
        "runtime_authority",
        "relationship_boundary_refs",
        "safety_boundary_refs",
        "dialogue_boundary_refs",
    } <= set(projection)


def test_types_lifecycle_and_candidate_contract_match_layer5(
    projection: dict,
) -> None:
    modules = _modules()
    event = _module_output(modules, "event_memory")
    update = _module_output(modules, "memory_update")
    event_extension = event["narrative_memory_extension"]
    update_extension = update["narrative_memory_extension"]
    assert projection["allowed_memory_types"] == list(
        NARRATIVE_MEMORY_ALLOWED_TYPES
    )
    assert (
        projection["allowed_memory_types"]
        == event_extension["allowed_memory_types"]
    )
    assert projection["memory_lifecycle_states"] == list(
        NARRATIVE_MEMORY_LIFECYCLE_STATES
    )
    assert (
        projection["memory_lifecycle_states"]
        == event_extension["memory_lifecycle_states"]
        == update_extension["memory_lifecycle_states"]
    )
    assert (
        projection["candidate_evidence_rules"]["requirements"]
        == event_extension["candidate_evidence_rules"][
            "requirements"
        ]
    )
    assert (
        projection["candidate_evidence_rules"]["excluded_inputs"]
        == event_extension["candidate_evidence_rules"][
            "excluded_inputs"
        ]
    )
    assert (
        projection["candidate_evidence_rules"]["candidate_fields"]
        == event_extension["candidate_evidence_rules"][
            "candidate_fields"
        ]
    )


def test_model_and_runtime_authority_are_closed(
    projection: dict,
) -> None:
    assert projection["model_authority"] == {
        "model_can_propose_candidate_only": True,
        "model_can_write_memory": False,
        "model_can_update_memory": False,
        "model_can_delete_memory": False,
    }
    assert projection["runtime_authority"] == {
        "runtime_is_final_decision_owner": True,
    }
    assert projection["full_dialogue_storage_allowed"] is False
    assert (
        projection["relationship_stage_transition_allowed"] is False
    )


def test_user_control_conflict_supersession_and_retrieval_are_safe(
    projection: dict,
) -> None:
    assert (
        projection["consent_policy"][
            "explicit_remember_request_raises_candidate_priority"
        ]
        is True
    )
    assert (
        projection["consent_policy"][
            "explicit_remember_request_bypasses_safety"
        ]
        is False
    )
    assert (
        projection["consent_policy"][
            "sensitive_or_ambiguous_requires_explicit_user_consent"
        ]
        is True
    )
    assert projection["consent_policy"]["user_rejection_state"] == (
        "rejected"
    )
    assert (
        projection["consent_policy"][
            "user_forget_request_target_state"
        ]
        == "deleted"
    )
    assert projection["single_item_delete_supported"] is True
    assert projection["clear_all_supported"] is True
    assert (
        projection["deduplication_policy"][
            "duplicate_events_are_merged"
        ]
        is True
    )
    assert (
        projection["conflict_resolution_policy"][
            "user_latest_explicit_statement_has_priority"
        ]
        is True
    )
    assert (
        projection["supersession_policy"][
            "older_conflicting_memory_state"
        ]
        == "superseded"
    )
    assert projection["deleted_memory_retrievable"] is False
    assert (
        projection["rejected_candidate_reproposal_allowed"] is False
    )
    assert projection["retrieval_policy"][
        "allowed_lifecycle_states"
    ] == ["active"]
    assert projection["retrieval_policy"][
        "excluded_lifecycle_states"
    ] == ["candidate", "superseded", "deleted", "rejected"]
    assert (
        projection["retrieval_policy"][
            "deleted_or_rejected_enters_model_context"
        ]
        is False
    )


def test_forbidden_content_rules_cover_sensitive_and_concrete_content(
    projection: dict,
) -> None:
    assert {
        "password",
        "verification_code",
        "api_key",
        "payment_credential",
        "precise_identity_credential",
        "authentication_information",
        "inferred_health_relationship_or_emotion_conclusion",
        "full_dialogue_transcript",
        "provider_request",
        "internal_reasoning",
        "provider_trace",
        "user_requested_not_to_save",
        "generated_from_count_duration_or_relationship_stage_only",
    } <= set(projection["forbidden_content_rules"])
    assert projection["contains_user_memory_records"] is False


def test_layer3_layer8_and_layer11_references_are_real(
    projection: dict,
) -> None:
    modules = {
        module["module_id"]: module for module in _modules()
    }
    expected_layers = {
        "safety_boundary_refs": "layer_3",
        "dialogue_boundary_refs": "layer_8",
        "relationship_boundary_refs": "layer_11",
    }
    for projection_key, layer_id in expected_layers.items():
        assert projection[projection_key]
        for reference in projection[projection_key]:
            assert reference["source_layer_id"] == layer_id
            source = modules[reference["source_module_id"]]
            assert source["layer_id"] == layer_id
            assert any(
                node["node_id"] == reference["source_node_id"]
                for node in source["module_graph"]["nodes"]
            )
            assert reference["source_path"] == (
                "payload.modules."
                f"{reference['source_module_id']}."
                "module_graph.nodes."
                f"{reference['source_node_id']}"
            )


@pytest.mark.parametrize(
    ("field_name", "field_value"),
    [
        (
            "current_narrative_memories",
            [{"candidate_summary": "具体用户事件"}],
        ),
        ("stored_memory_items", [{"memory_id": "user-memory-1"}]),
        ("conversation_transcript", "用户与居民的完整对话"),
        ("confirmed_plan_content", "用户下周一的具体计划"),
        ("user_emotional_experience", "用户昨晚的具体情绪经历"),
    ],
)
def test_compile_gate_blocks_concrete_user_memory_instances(
    field_name: str,
    field_value: object,
) -> None:
    modules = _modules()
    event = next(
        module
        for module in modules
        if module["module_id"] == "event_memory"
    )
    event["module_graph"]["nodes"][0]["params"][field_name] = (
        field_value
    )
    result = _compile_result(modules)
    assert result["valid"] is False
    assert result["compiled_dr"] is None
    findings = [
        finding
        for finding in result["errors"]
        if finding["code"]
        == "DR_NARRATIVE_MEMORY_INSTANCE_DATA_FORBIDDEN"
    ]
    assert findings
    assert any(field_name in finding["path"] for finding in findings)


def test_export_gate_returns_structured_diagnostic() -> None:
    modules = _modules()
    event = next(
        module
        for module in modules
        if module["module_id"] == "event_memory"
    )
    event["module_graph"]["nodes"][0]["params"][
        "stored_memory_items"
    ] = [{"candidate_summary": "具体用户事件"}]
    response = client.post("/dr/export", json=_canvas(modules))
    assert response.status_code == 422
    detail = response.json()["detail"]
    assert detail["error"] == (
        "DR v0.3 did not pass validation; export is not allowed"
    )
    assert any(
        finding["code"]
        == "DR_NARRATIVE_MEMORY_INSTANCE_DATA_FORBIDDEN"
        and finding["status"] == "FAIL"
        and "stored_memory_items" in finding["path"]
        for finding in detail["errors"]
    )


def test_gate_does_not_block_empty_schema_or_field_descriptions() -> None:
    modules = _modules()
    event = next(
        module
        for module in modules
        if module["module_id"] == "event_memory"
    )
    event["module_graph"]["nodes"][0]["params"]["output_schema"] = {
        "conversation_transcript": "",
        "current_narrative_memories": [],
        "candidate_summary": "string",
    }
    event["module_graph"]["nodes"][0]["params"]["i18n_keys"][
        "fields"
    ]["conversation_transcript"] = (
        "layer5.eventMemory.field.conversationTranscript"
    )
    result = _compile_result(modules)
    assert result["valid"] is True, result["errors"]


def test_formal_schema_is_strict_and_old_dr_without_projection_loads(
    compiled_dr: dict,
) -> None:
    validated = DRDocumentV03.model_validate(compiled_dr)
    assert validated.payload.narrative_memory_projection is not None
    gate = validate_dr_document_v0_3(compiled_dr)
    assert gate["valid"] is True, gate["findings"]

    extra_field_dr = deepcopy(compiled_dr)
    extra_field_dr["payload"]["narrative_memory_projection"][
        "specific_user_memory"
    ] = {"event": "must not pass"}
    with pytest.raises(ValidationError):
        DRDocumentV03.model_validate(extra_field_dr)

    legacy_dr = deepcopy(compiled_dr)
    legacy_dr["payload"].pop("narrative_memory_projection")
    legacy_validated = DRDocumentV03.model_validate(legacy_dr)
    assert legacy_validated.payload.narrative_memory_projection is None
    assert _v3_mock_load_dr(legacy_dr)["loaded"] is True


def test_missing_layer5_source_omits_optional_projection() -> None:
    modules = [
        module
        for module in _modules()
        if module["module_id"] != "event_memory"
    ]
    missing_projection, diagnostics = (
        build_narrative_memory_projection(modules)
    )
    assert missing_projection is None
    assert any(
        diagnostic["status"] == "WARNING"
        and diagnostic["code"]
        == "DR_NARRATIVE_MEMORY_SOURCE_MISSING"
        for diagnostic in diagnostics
    )


def test_projection_registration_and_repeat_compile_are_stable(
    compiled_result: dict,
) -> None:
    mappings = {
        mapping["mapping_id"]: mapping
        for mapping in PROJECTION_FIELD_MAPPINGS
    }
    assert projection_field_mapping_errors() == []
    assert mappings["narrative_memory_projection"][
        "source_layer"
    ] == "layer_5"
    assert mappings["narrative_memory_projection"][
        "target_path"
    ] == "payload.narrative_memory_projection"
    assert mappings["narrative_memory_projection"][
        "projection_type"
    ] == "derived_read_only"

    repeated = _compile_result(_modules())
    assert repeated["valid"] is True, repeated["errors"]
    assert (
        repeated["compiled_dr"]["payload"][
            "narrative_memory_projection"
        ]
        == compiled_result["compiled_dr"]["payload"][
            "narrative_memory_projection"
        ]
    )


def test_versions_capabilities_and_existing_memory_policy_are_unchanged(
    compiled_dr: dict,
) -> None:
    assert compiled_dr["dr_version"] == "0.3"
    assert compiled_dr["dr_schema_version"] == "0.3.0"
    assert compiled_dr["protocol_version"] == "0.4.0"
    assert compiled_dr["manifest"]["required_capabilities"] == [
        "llm",
        "memory",
        "lattice",
    ]
    assert compiled_dr["payload"]["memory_policy"]["memory_types"] == [
        "short_term_memory",
        "profile_memory",
        "preference_memory",
        "interaction_log",
    ]
    assert (
        "memory_policy_extensions"
        in compiled_dr["payload"]["memory_policy"]
    )
    assert "current_narrative_memories" not in compiled_dr["payload"]
    assert "stored_memory_items" not in compiled_dr["payload"]
    assert "conversation_transcript" not in compiled_dr["payload"]
