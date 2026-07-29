"""Stage 7.4.14 A3 generic-memory compatibility and export Gate."""

from __future__ import annotations

from copy import deepcopy

from app.registry.module_catalog import (
    NARRATIVE_MEMORY_EXTENSION_COMPATIBILITY_FIX_REVISION,
    get_module_catalog,
)
from app.services.dr_compiler import compile_dr_result_v0_3


def _modules() -> list[dict]:
    return [
        module.model_dump(mode="json")
        for module in get_module_catalog()
    ]


def _output(module_id: str) -> dict:
    module = next(
        module
        for module in _modules()
        if module["module_id"] == module_id
    )
    return module["outputs"][module["module_graph"]["output_key"]]


def _compile(modules: list[dict] | None = None) -> dict:
    return compile_dr_result_v0_3(
        {
            "workflow": {
                "name": "stage_7_4_14_a3_compatibility",
                "nodes": [
                    {"node_id": f"layer_{index}"}
                    for index in range(1, 14)
                ],
            },
            "modules": modules or _modules(),
        }
    )


def test_frozen_generic_access_contract_and_topology_are_restored() -> None:
    module = next(
        module
        for module in _modules()
        if module["module_id"] == "memory_access_control"
    )
    assert [node["node_id"] for node in module["module_graph"]["nodes"]] == [
        "memory_access_request_input",
        "memory_user_permission_check",
        "memory_type_classifier",
        "memory_sensitive_check",
        "memory_policy_match",
        "memory_access_decision",
        "memory_access_audit",
        "memory_access_output",
    ]
    output = _output("memory_access_control")
    assert {
        "permission_policy",
        "request_contract",
        "policy_actions",
        "audit_policy",
        "decision",
        "reason",
        "memory_categories",
    } <= set(output)
    assert output["permission_policy"] == {
        "user_explicit_remember": "allow",
        "missing_user_authorization": "confirm",
        "sensitive_information": "deny",
    }
    assert output["content_revision"] == (
        NARRATIVE_MEMORY_EXTENSION_COMPATIBILITY_FIX_REVISION
    )


def test_frozen_generic_update_contract_and_topology_are_restored() -> None:
    module = next(
        module
        for module in _modules()
        if module["module_id"] == "memory_update"
    )
    assert [node["node_id"] for node in module["module_graph"]["nodes"]] == [
        "memory_update_request_input",
        "memory_update_operation_classifier",
        "memory_update_confirmation_check",
        "memory_update_conflict_check",
        "memory_update_policy_apply",
        "memory_update_audit_record",
        "memory_update_output",
    ]
    output = _output("memory_update")
    assert {
        "confirmation_policy",
        "decision_values",
        "audit_policy",
        "write_boundary",
        "allowed_operations",
    } <= set(output)
    assert output["allowed_operations"] == [
        "create",
        "update",
        "delete",
        "confirm",
        "archive",
    ]
    assert output["write_boundary"] == "local_memory_store_only"
    assert (
        output["confirmation_policy"][
            "explicit_user_remember_request"
        ]
        == "allow_without_second_confirmation"
    )


def test_narrative_rules_live_only_under_extension() -> None:
    forbidden_flat_keys = {
        "candidate_requirements",
        "candidate_exclusions",
        "candidate_output_contract",
        "narrative_save_forbidden",
        "allowed_lifecycle_states",
        "excluded_lifecycle_states",
        "retrieval_rules",
        "expression_rules",
    }
    for module_id in (
        "event_memory",
        "memory_update",
        "memory_access_control",
    ):
        output = _output(module_id)
        assert "narrative_memory_extension" in output
        assert forbidden_flat_keys.isdisjoint(output)
        extension = output["narrative_memory_extension"]
        assert extension["content_revision"] == (
            NARRATIVE_MEMORY_EXTENSION_COMPATIBILITY_FIX_REVISION
        )
        assert extension["contains_user_memory_records"] is False


def test_sensitive_semantics_are_consistent_and_alias_is_compatibility_only() -> None:
    extension = _output("event_memory")[
        "narrative_memory_extension"
    ]
    sensitivity = extension["sensitivity_policy"]
    assert sensitivity["permanently_forbidden_categories"] == [
        "password",
        "verification_code",
        "api_key",
        "payment_credential",
        "precise_identity_credential",
        "authentication_information",
    ]
    assert (
        sensitivity[
            "other_sensitive_or_ambiguous_requires_explicit_user_consent"
        ]
        is True
    )
    assert sensitivity["safety_policy_validation_still_required"] is True
    assert sensitivity["legacy_sensitive_event_alias"] == {
        "status": "compatibility_alias",
        "interpretation": (
            "sensitive_or_ambiguous_requires_explicit_"
            "user_consent_and_safety_validation"
        ),
        "not_a_blanket_allow": True,
        "not_a_blanket_deny": True,
    }
    event = _output("event_memory")
    assert "sensitive_event" not in event["save_forbidden"]


def test_runtime_projection_keeps_generic_and_narrative_policies_separate() -> None:
    result = _compile()
    assert result["valid"] is True, result["errors"]
    policy = result["compiled_dr"]["payload"][
        "runtime_dialogue_projection"
    ]["memory_usage_policy"]
    derived = policy["derived_values"]
    assert derived["memory_access_limits"]["permission_policy"][
        "missing_user_authorization"
    ] == "confirm"
    assert derived["memory_access_limits"]["permission_policy"][
        "sensitive_information"
    ] == "deny"
    assert derived["memory_write_limits"]["confirmation_policy"][
        "explicit_user_remember_request"
    ] == "allow_without_second_confirmation"
    assert (
        derived["memory_write_limits"]["write_boundary"]
        == "local_memory_store_only"
    )
    generic_event = derived["narrative_memory_usage_rules"][
        "event_memory"
    ]
    assert generic_event["save_allowed"]
    assert "allowed_memory_types" not in generic_event
    narrative = result["compiled_dr"]["payload"][
        "narrative_memory_projection"
    ]
    assert narrative["allowed_memory_types"]
    assert narrative["retrieval_policy"]["allowed_lifecycle_states"] == [
        "active"
    ]


def test_instance_gate_runs_on_every_compile_with_pass_or_fail_result() -> None:
    clean = _compile()
    assert clean["valid"] is True, clean["errors"]
    gate_findings = clean["compiled_dr"]["audit_report"]["findings"]
    assert any(
        finding["status"] == "PASS"
        and finding["code"]
        == "NARRATIVE_MEMORY_INSTANCE_GATE_CHECK_PASSED"
        for finding in gate_findings
    )

    modules = deepcopy(_modules())
    event = next(
        module
        for module in modules
        if module["module_id"] == "event_memory"
    )
    event["module_graph"]["nodes"][0]["params"][
        "current_narrative_memories"
    ] = [{"candidate_summary": "concrete user event"}]
    blocked = _compile(modules)
    assert blocked["valid"] is False
    assert blocked["compiled_dr"] is None
    assert any(
        finding["status"] == "FAIL"
        and finding["code"]
        == "DR_NARRATIVE_MEMORY_INSTANCE_DATA_FORBIDDEN"
        for finding in blocked["errors"]
    )
    assert not any(
        finding["code"]
        == "NARRATIVE_MEMORY_INSTANCE_GATE_CHECK_PASSED"
        for finding in blocked["errors"]
    )


def test_repeat_compile_is_stable_and_version_contract_is_frozen() -> None:
    first = _compile()
    second = _compile()
    assert first["valid"] is second["valid"] is True
    first_dr = first["compiled_dr"]
    second_dr = second["compiled_dr"]
    assert (
        first_dr["payload"]["narrative_memory_projection"]
        == second_dr["payload"]["narrative_memory_projection"]
    )
    assert first_dr["dr_version"] == "0.3"
    assert first_dr["dr_schema_version"] == "0.3.0"
    assert first_dr["manifest"]["required_capabilities"] == [
        "llm",
        "memory",
        "lattice",
    ]
