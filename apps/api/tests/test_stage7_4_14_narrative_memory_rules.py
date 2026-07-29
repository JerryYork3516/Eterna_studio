"""Stage 7.4.14 A1 Layer 5 narrative-memory rule contracts."""

from __future__ import annotations

import json
from pathlib import Path

from app.registry.module_catalog import (
    NARRATIVE_MEMORY_EXTENSION_COMPATIBILITY_FIX_REVISION,
    NARRATIVE_MEMORY_LIFECYCLE_STATES,
    NARRATIVE_MEMORY_TYPES,
    get_module_catalog,
)
from app.services.dr_compiler import compile_dr_result_v0_3


NARRATIVE_CHAIN = [
    "narrative_event_input",
    "narrative_memory_type_recognition",
    "narrative_memory_user_source_validation",
    "narrative_memory_future_value_evaluation",
    "narrative_memory_sensitive_information_check",
    "narrative_memory_user_consent_judgement",
    "event_memory_output",
    "narrative_memory_reference_output",
]
UPDATE_CHAIN = [
    "memory_update_request_input",
    "memory_update_operation_classifier",
    "memory_update_confirmation_check",
    "memory_update_conflict_check",
    "memory_update_policy_apply",
    "memory_update_audit_record",
    "memory_update_output",
]
ACCESS_CHAIN = [
    "memory_access_request_input",
    "memory_user_permission_check",
    "memory_type_classifier",
    "memory_sensitive_check",
    "memory_policy_match",
    "memory_access_decision",
    "memory_access_audit",
    "memory_access_output",
]


def _modules() -> list[dict]:
    return [module.model_dump(mode="json") for module in get_module_catalog()]


def _module(module_id: str) -> dict:
    return next(module for module in _modules() if module["module_id"] == module_id)


def _output(module_id: str) -> dict:
    module = _module(module_id)
    return module["outputs"][module["module_graph"]["output_key"]]


def _node(module_id: str, node_id: str) -> dict:
    return next(
        node
        for node in _module(module_id)["module_graph"]["nodes"]
        if node["node_id"] == node_id
    )


def _extension(module_id: str) -> dict:
    return _output(module_id)["narrative_memory_extension"]


def _compile() -> dict:
    result = compile_dr_result_v0_3(
        {
            "workflow": {
                "name": "stage_7_4_14_narrative_memory_rules",
                "nodes": [
                    {"node_id": f"layer_{index}"}
                    for index in range(1, 14)
                ],
            },
            "modules": _modules(),
        }
    )
    assert result["valid"] is True, result["errors"]
    return result["compiled_dr"]


def test_existing_layer5_modules_are_extended_once_with_exact_main_chains():
    modules = _modules()
    expected = {
        "event_memory": NARRATIVE_CHAIN,
        "memory_update": UPDATE_CHAIN,
        "memory_access_control": ACCESS_CHAIN,
    }
    for module_id, chain in expected.items():
        assert len([module for module in modules if module["module_id"] == module_id]) == 1
        module = _module(module_id)
        assert module["layer_id"] == "layer_5"
        assert module["config"]["content_revision"] == (
            NARRATIVE_MEMORY_EXTENSION_COMPATIBILITY_FIX_REVISION
        )
        assert module["module_graph"]["nodes"][0]["params"]["content_revision"] == (
            NARRATIVE_MEMORY_EXTENSION_COMPATIBILITY_FIX_REVISION
        )
        assert [node["node_id"] for node in module["module_graph"]["nodes"]] == chain
        assert [
            (edge["source"], edge["target"])
            for edge in module["module_graph"]["edges"]
        ] == list(zip(chain, chain[1:]))


def test_six_memory_types_and_five_lifecycle_states_are_stable():
    narrative = _extension("event_memory")
    update = _extension("memory_update")
    assert narrative["allowed_memory_types"] == list(NARRATIVE_MEMORY_TYPES)
    assert narrative["memory_lifecycle_states"] == list(
        NARRATIVE_MEMORY_LIFECYCLE_STATES
    )
    assert update["memory_lifecycle_states"] == list(
        NARRATIVE_MEMORY_LIFECYCLE_STATES
    )


def test_small_talk_model_inference_and_unconfirmed_emotion_are_not_candidates():
    narrative = _extension("event_memory")
    evidence = narrative["candidate_evidence_rules"]
    assert evidence["requirements"] == [
        "explicit_user_statement",
        "has_future_continuation_value",
        "traceable_to_real_user_turn",
        "not_denied_or_withdrawn_by_user",
        "complies_with_safety_and_memory_policy",
    ]
    assert {
        "ordinary_small_talk",
        "one_off_question_answer",
        "model_inference",
        "unconfirmed_emotion_judgement",
    } == set(evidence["excluded_inputs"])


def test_model_can_only_propose_and_runtime_owns_all_memory_decisions():
    model_expected = {
        "model_can_propose_candidate_only": True,
        "model_can_write_memory": False,
        "model_can_update_memory": False,
        "model_can_delete_memory": False,
    }
    runtime_expected = {
        "runtime_is_final_decision_owner": True,
    }
    for module_id in ("event_memory", "memory_update"):
        extension = _extension(module_id)
        assert extension["model_authority"] == model_expected
        assert extension["runtime_authority"] == runtime_expected


def test_candidate_contract_consent_and_forbidden_save_rules_are_closed():
    narrative = _extension("event_memory")
    assert narrative["candidate_evidence_rules"]["candidate_fields"] == [
        "memory_type",
        "candidate_summary",
        "source_turn_reference",
        "importance_reason",
        "sensitivity_level",
        "requires_user_consent",
    ]
    consent = narrative["consent_policy"]
    assert consent["explicit_remember_request_raises_candidate_priority"] is True
    assert consent["explicit_remember_request_bypasses_safety"] is False
    assert consent["sensitive_or_ambiguous_requires_explicit_user_consent"] is True
    assert consent["user_rejection_state"] == "rejected"
    assert consent["rejected_candidate_auto_reproposal"] is False
    assert {
        "password",
        "verification_code",
        "api_key",
        "payment_credential",
        "full_dialogue_transcript",
        "provider_request",
        "internal_reasoning",
        "provider_trace",
        "user_requested_not_to_save",
    } <= set(narrative["forbidden_content_rules"])


def test_dedup_supersede_delete_reject_and_clear_rules_are_complete():
    update = _extension("memory_update")
    assert update["deduplication_policy"] == {
        "same_event": "deduplicate_or_merge",
    }
    assert update["conflict_resolution_policy"] == {
        "latest_explicit_user_statement": "supersede_older_information",
        "superseded_is_not_current_fact": True,
    }
    assert update["allowed_transitions"] == [
        ["candidate", "active"],
        ["active", "superseded"],
        ["active", "deleted"],
        ["superseded", "deleted"],
        ["candidate", "rejected"],
    ]
    assert ["deleted", "active"] in update["forbidden_transitions"]
    assert ["rejected", "active"] in update["forbidden_transitions"]
    assert update["deletion_policy"]["single_item_delete"] is True
    assert update["deletion_policy"]["clear_all"] is True
    assert update["deletion_policy"]["restore_from_model_inference"] is False
    assert update["deletion_policy"]["restore_from_historical_transcript"] is False


def test_deleted_rejected_and_superseded_content_cannot_enter_context():
    access = _extension("memory_access_control")
    retrieval = access["retrieval_policy"]
    expression = access["expression_policy"]
    assert retrieval["allowed_lifecycle_states"] == ["active"]
    assert retrieval["excluded_lifecycle_states"] == [
        "candidate",
        "superseded",
        "deleted",
        "rejected",
    ]
    assert "retrieve_only_when_relevant_to_current_topic" in retrieval["rules"]
    assert "use_few_most_relevant_active_memories_per_turn" in retrieval["rules"]
    assert "never_claim_to_remember_forever" in expression["rules"]
    assert "never_reference_unsaved_deleted_or_rejected_content" in expression["rules"]
    assert "do_not_use_narrative_memory_to_upgrade_relationship_stage" in expression["rules"]


def test_references_point_only_to_real_layer3_layer8_and_layer11_modules():
    modules = {module["module_id"]: module for module in _modules()}
    references = [
        *_extension("event_memory")["references"],
        *_extension("memory_update")["references"],
        *_extension("memory_access_control")["references"],
    ]
    assert {ref["source_layer_id"] for ref in references} == {
        "layer_3",
        "layer_8",
        "layer_11",
    }
    for reference in references:
        source = modules[reference["source_module_id"]]
        assert source["layer_id"] == reference["source_layer_id"]
        assert any(
            node["node_id"] == reference["source_node_id"]
            for node in source["module_graph"]["nodes"]
        )


def test_rules_and_compiled_dr_contain_no_user_memory_records():
    for module_id in ("event_memory", "memory_update", "memory_access_control"):
        extension = _extension(module_id)
        assert extension["contains_user_memory_records"] is False
        serialized = json.dumps(extension, ensure_ascii=False)
        for forbidden in (
            "current_user_memory",
            "stored_memories",
            "memory_record_value",
            '"memory_records"',
        ):
            assert forbidden not in serialized
    dr = _compile()
    assert dr["dr_version"] == "0.3"
    assert dr["manifest"]["required_capabilities"] == ["llm", "memory", "lattice"]


def test_chinese_and_english_i18n_cover_new_nodes_types_and_states():
    root = Path(__file__).resolve().parents[3]
    zh = json.loads((root / "apps/web/locales/zh.json").read_text())
    en = json.loads((root / "apps/web/locales/en.json").read_text())
    node_suffixes = [
        "typeRecognition",
        "userSourceValidation",
        "futureValueEvaluation",
        "sensitiveInformationCheck",
        "userConsentJudgement",
        "referenceOutput",
    ]
    keys = [
        *(f"layer5.eventMemory.node.{suffix}.title" for suffix in node_suffixes),
        *(f"layer5.eventMemory.node.{suffix}.description" for suffix in node_suffixes),
        *(f"layer5.eventMemory.memoryType.{memory_type}" for memory_type in NARRATIVE_MEMORY_TYPES),
        *(f"layer5.eventMemory.lifecycle.{state}" for state in NARRATIVE_MEMORY_LIFECYCLE_STATES),
        *(
            f"layer5.memoryAccessControl.node.{suffix}.{part}"
            for suffix in (
                "topicRelevanceCheck",
                "lifecycleStateFilter",
                "relevantMemorySelection",
                "expressionBoundaryCheck",
            )
            for part in ("title", "description")
        ),
        *(
            f"layer5.memoryUpdate.node.{suffix}.{part}"
            for suffix in (
                "duplicateEventRecognition",
                "latestExplicitStatementValidation",
                "mergeOrSupersede",
                "lifecycleStateUpdate",
                "referenceOutput",
            )
            for part in ("title", "description")
        ),
        *(
            f"layer5.eventMemory.field.{suffix}"
            for suffix in (
                "memoryType",
                "candidateSummary",
                "sourceTurnReference",
                "importanceReason",
                "sensitivityLevel",
                "requiresUserConsent",
            )
        ),
    ]
    for key in keys:
        assert key in zh and zh[key].strip() and zh[key] != key
        assert key in en and en[key].strip() and en[key] != key
    assert zh["layer5.eventMemory.memoryType.shared_experience"] == "共同经历"
    assert en["layer5.eventMemory.memoryType.shared_experience"] == "Shared Experience"
