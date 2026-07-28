"""Compile-only Layer 11 relationship progression projection.

The Layer 11 module fields remain authoritative. This module only creates a
read-only Runtime-facing view and never executes a stage transition.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, Iterable, Optional


RELATIONSHIP_PROGRESSION_SCHEMA_VERSION = "0.1"
RELATIONSHIP_PROGRESSION_PROJECTION_CONTENT_REVISION = (
    "stage7_4_13_relationship_progression_projection_v0_1"
)
RELATIONSHIP_PROGRESSION_ENABLED_STAGES = (
    "initial_acquaintance",
    "growing_familiarity",
    "stable_companionship",
    "trusted_relationship",
)
RELATIONSHIP_PROGRESSION_DEFAULT_STAGE = "initial_acquaintance"
RELATIONSHIP_PROGRESSION_RESERVED_STAGE = (
    "romantic_relationship_reserved"
)
RELATIONSHIP_PROGRESSION_FORBIDDEN_STATE_FIELDS = frozenset(
    {
        "current_relationship_stage",
        "relationship_score",
        "intimacy_score",
        "progress",
    }
)
RELATIONSHIP_PROGRESSION_REQUIRED_USER_ACTIONS = (
    "reject_upgrade",
    "revoke_relationship_confirmation",
    "downgrade_to_lower_stage",
    "reset_to_initial_acquaintance",
    "disable_relationship_progression",
)
RELATIONSHIP_PROGRESSION_REQUIRED_FORBIDDEN_EVIDENCE = (
    "chat_count",
    "usage_duration",
    "payment_status",
    "user_loneliness_depression_vulnerability_or_dependency_testing",
    "resident_or_model_self_judgement",
    "few_shot_resident_reply_or_model_inference",
    "unconfirmed_memory",
)
RELATIONSHIP_PROGRESSION_RESERVED_FORBIDDEN_TRIGGERS = (
    "user_loneliness",
    "user_low_mood",
    "user_vulnerability",
    "dependency_testing",
    "chat_count",
    "usage_duration",
    "payment_status",
    "model_or_resident_inference",
)
RELATIONSHIP_PROGRESSION_SOURCE_PATHS = (
    "payload.modules.user_relationship.module_graph.nodes."
    "user_relationship_config_input.params.fields",
    "payload.modules.relationship_rule.module_graph.nodes."
    "relationship_evidence_candidate_input.params.fields",
)


def _as_dict(value: Any) -> Dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _module_by_id(
    modules: Iterable[Dict[str, Any]], module_id: str
) -> Dict[str, Any]:
    return next(
        (
            module
            for module in modules
            if isinstance(module, dict)
            and module.get("module_id") == module_id
        ),
        {},
    )


def _module_field_values(module: Dict[str, Any]) -> Dict[str, Any]:
    graph = _as_dict(module.get("module_graph"))
    nodes = graph.get("nodes") if isinstance(graph.get("nodes"), list) else []
    for node in nodes:
        if not isinstance(node, dict):
            continue
        params = _as_dict(node.get("params"))
        if (
            node.get("node_type") != "text_input"
            or params.get("mode") != "generic_fields"
        ):
            continue
        fields = params.get("fields")
        if not isinstance(fields, list):
            continue
        values: Dict[str, Any] = {}
        for field in fields:
            if not isinstance(field, dict):
                continue
            field_key = str(
                field.get("field_key")
                or field.get("field_id")
                or ""
            )
            if not field_key:
                continue
            values[field_key] = deepcopy(
                field.get("field_value")
                if "field_value" in field
                else field.get("value")
            )
        if values:
            return values
    return {}


def _relationship_references(
    relationship_rule: Dict[str, Any],
) -> list[Dict[str, Any]]:
    config = _as_dict(relationship_rule.get("config"))
    references = config.get("references")
    if not isinstance(references, list):
        return []
    return [
        deepcopy(reference)
        for reference in references
        if isinstance(reference, dict)
    ]


def _reference_projection(reference: Dict[str, Any]) -> Dict[str, Any]:
    source_module_id = str(reference.get("source_module_id") or "")
    source_node_id = str(reference.get("source_node_id") or "")
    return {
        "reference_id": str(reference.get("reference_id") or ""),
        "source_layer_id": str(reference.get("source_layer_id") or ""),
        "source_module_id": source_module_id,
        "source_node_id": source_node_id,
        "source_path": (
            f"payload.modules.{source_module_id}.module_graph.nodes."
            f"{source_node_id}"
        ),
    }


def _reserved_stage_is_safe(value: Any) -> bool:
    if not isinstance(value, dict):
        return False
    return (
        value.get("stage_id")
        == RELATIONSHIP_PROGRESSION_RESERVED_STAGE
        and value.get("status") == "reserved"
        and value.get("runtime_enabled") is False
        and value.get("automatic_transition") is False
        and value.get("requires_explicit_user_consent") is True
        and value.get("requires_runtime_feature_gate") is True
        and value.get("current_version_unlock_allowed") is False
        and value.get("single_utterance_unlock_allowed") is False
        and value.get("activation_requirements")
        == [
            "future_version_runtime_feature_gate_enabled",
            "explicit_user_consent_confirmed",
        ]
        and set(value.get("excluded_from") or [])
        == {
            "enabled_stages",
            "model_context",
            "few_shot",
            "automatic_transition_path",
        }
        and value.get("forbidden_trigger_evidence")
        == list(
            RELATIONSHIP_PROGRESSION_RESERVED_FORBIDDEN_TRIGGERS
        )
    )


def relationship_progression_source_forbidden_fields(
    modules: Iterable[Dict[str, Any]],
) -> list[Dict[str, str]]:
    """Return forbidden per-user state fields declared by Layer 11 sources."""

    findings: list[Dict[str, str]] = []
    for module in modules:
        if (
            not isinstance(module, dict)
            or module.get("module_id")
            not in {"user_relationship", "relationship_rule"}
        ):
            continue
        graph = _as_dict(module.get("module_graph"))
        nodes = (
            graph.get("nodes")
            if isinstance(graph.get("nodes"), list)
            else []
        )
        for node_index, node in enumerate(nodes):
            params = _as_dict(node.get("params")) if isinstance(node, dict) else {}
            fields = params.get("fields")
            if not isinstance(fields, list):
                continue
            for field_index, field in enumerate(fields):
                if not isinstance(field, dict):
                    continue
                field_key = str(
                    field.get("field_key")
                    or field.get("field_id")
                    or ""
                )
                if (
                    field_key
                    in RELATIONSHIP_PROGRESSION_FORBIDDEN_STATE_FIELDS
                ):
                    findings.append(
                        {
                            "status": "FAIL",
                            "code": (
                                "DR_RELATIONSHIP_INSTANCE_STATE_FORBIDDEN"
                            ),
                            "message": (
                                "Layer 11 relationship rules must not store "
                                f"per-user state field {field_key!r}"
                            ),
                            "path": (
                                f"payload.modules.{module.get('module_id')}."
                                f"module_graph.nodes[{node_index}].params."
                                f"fields[{field_index}]"
                            ),
                        }
                    )
    return findings


def build_relationship_progression_projection(
    modules: Iterable[Dict[str, Any]],
) -> tuple[Optional[Dict[str, Any]], list[Dict[str, str]]]:
    """Build the optional projection from current Layer 11 module fields."""

    module_list = [
        module for module in modules if isinstance(module, dict)
    ]
    user_relationship = _module_by_id(
        module_list, "user_relationship"
    )
    relationship_rule = _module_by_id(module_list, "relationship_rule")
    if not user_relationship or not relationship_rule:
        return None, [
            {
                "status": "WARNING",
                "code": "DR_RELATIONSHIP_PROGRESSION_SOURCE_MISSING",
                "message": (
                    "Layer 11 relationship progression sources are missing; "
                    "the optional projection was omitted"
                ),
                "path": "payload.relationship_progression_projection",
            }
        ]

    relationship_values = _module_field_values(user_relationship)
    rule_values = _module_field_values(relationship_rule)
    reserved_stages = relationship_values.get(
        "reserved_relationship_stages"
    )
    if (
        not isinstance(reserved_stages, list)
        or len(reserved_stages) != 1
        or not isinstance(reserved_stages[0], dict)
    ):
        return None, [
            {
                "status": "WARNING",
                "code": (
                    "DR_RELATIONSHIP_PROGRESSION_RESERVED_SOURCE_MISSING"
                ),
                "message": (
                    "The reserved relationship stage source is missing; "
                    "the optional projection was omitted for compatibility"
                ),
                "path": (
                    "payload.modules.user_relationship.fields."
                    "reserved_relationship_stages"
                ),
            }
        ]

    diagnostics = relationship_progression_source_forbidden_fields(
        module_list
    )
    enabled_stages = relationship_values.get(
        "relationship_stage_order"
    )
    default_stage = relationship_values.get(
        "default_relationship_stage"
    )
    stage_definitions = relationship_values.get(
        "relationship_stage_definitions"
    )
    reserved_stage = deepcopy(reserved_stages[0])
    if enabled_stages != list(
        RELATIONSHIP_PROGRESSION_ENABLED_STAGES
    ):
        diagnostics.append(
            {
                "status": "FAIL",
                "code": "DR_RELATIONSHIP_ENABLED_STAGES_INVALID",
                "message": (
                    "enabled relationship stages must contain exactly the "
                    "four Stage 7.4.13 enabled stages in stable order"
                ),
                "path": (
                    "payload.modules.user_relationship.fields."
                    "relationship_stage_order"
                ),
            }
        )
        enabled_stages = list(
            RELATIONSHIP_PROGRESSION_ENABLED_STAGES
        )
    if default_stage != RELATIONSHIP_PROGRESSION_DEFAULT_STAGE:
        diagnostics.append(
            {
                "status": "FAIL",
                "code": "DR_RELATIONSHIP_DEFAULT_STAGE_INVALID",
                "message": (
                    "default relationship stage must remain "
                    "initial_acquaintance"
                ),
                "path": (
                    "payload.modules.user_relationship.fields."
                    "default_relationship_stage"
                ),
            }
        )
        default_stage = RELATIONSHIP_PROGRESSION_DEFAULT_STAGE
    if (
        not isinstance(stage_definitions, dict)
        or list(stage_definitions) != list(
            RELATIONSHIP_PROGRESSION_ENABLED_STAGES
        )
    ):
        diagnostics.append(
            {
                "status": "FAIL",
                "code": "DR_RELATIONSHIP_STAGE_DEFINITIONS_INVALID",
                "message": (
                    "stage definitions must map exactly the four enabled "
                    "relationship stages in stable order"
                ),
                "path": (
                    "payload.modules.user_relationship.fields."
                    "relationship_stage_definitions"
                ),
            }
        )
        stage_definitions = {
            stage: {}
            for stage in RELATIONSHIP_PROGRESSION_ENABLED_STAGES
        }
    if not _reserved_stage_is_safe(reserved_stage):
        diagnostics.append(
            {
                "status": "FAIL",
                "code": "DR_ROMANTIC_RESERVED_STAGE_INVALID",
                "message": (
                    "romantic_relationship_reserved must remain disabled, "
                    "non-automatic, gated, and unavailable in this version"
                ),
                "path": (
                    "payload.modules.user_relationship.fields."
                    "reserved_relationship_stages[0]"
                ),
            }
        )
        reserved_stage = {
            **reserved_stage,
            "stage_id": RELATIONSHIP_PROGRESSION_RESERVED_STAGE,
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
            "forbidden_trigger_evidence": list(
                RELATIONSHIP_PROGRESSION_RESERVED_FORBIDDEN_TRIGGERS
            ),
            "excluded_from": [
                "enabled_stages",
                "model_context",
                "few_shot",
                "automatic_transition_path",
            ],
        }

    references = _relationship_references(relationship_rule)
    safety_boundary_refs = [
        _reference_projection(reference)
        for reference in references
        if reference.get("source_layer_id") in {"layer_3", "layer_12"}
    ]
    memory_policy_refs = [
        _reference_projection(reference)
        for reference in references
        if reference.get("source_layer_id") == "layer_5"
    ]
    evidence_contract = _as_dict(
        rule_values.get("relationship_evidence_candidate_contract")
    )
    reset_policy = _as_dict(
        rule_values.get("relationship_downgrade_reset_policy")
    )
    user_actions = rule_values.get(
        "user_relationship_control_actions"
    )
    forbidden_evidence = rule_values.get("forbidden_upgrade_evidence")
    if user_actions != list(
        RELATIONSHIP_PROGRESSION_REQUIRED_USER_ACTIONS
    ):
        diagnostics.append(
            {
                "status": "FAIL",
                "code": "DR_RELATIONSHIP_USER_CONTROL_INCOMPLETE",
                "message": (
                    "relationship progression must preserve reject, revoke, "
                    "downgrade, reset, and disable controls"
                ),
                "path": (
                    "payload.modules.relationship_rule.fields."
                    "user_relationship_control_actions"
                ),
            }
        )
        user_actions = list(
            RELATIONSHIP_PROGRESSION_REQUIRED_USER_ACTIONS
        )
    if forbidden_evidence != list(
        RELATIONSHIP_PROGRESSION_REQUIRED_FORBIDDEN_EVIDENCE
    ):
        diagnostics.append(
            {
                "status": "FAIL",
                "code": "DR_RELATIONSHIP_FORBIDDEN_EVIDENCE_INVALID",
                "message": (
                    "count, duration, payment, vulnerability, inference, and "
                    "unconfirmed memory must remain forbidden transition "
                    "evidence"
                ),
                "path": (
                    "payload.modules.relationship_rule.fields."
                    "forbidden_upgrade_evidence"
                ),
            }
        )
        forbidden_evidence = list(
            RELATIONSHIP_PROGRESSION_REQUIRED_FORBIDDEN_EVIDENCE
        )
    if (
        evidence_contract.get("model_can_modify_relationship_stage")
        is not False
        or evidence_contract.get(
            "model_can_output_closed_evidence_candidate_only"
        )
        is not True
    ):
        diagnostics.append(
            {
                "status": "FAIL",
                "code": "DR_RELATIONSHIP_MODEL_STAGE_AUTHORITY_INVALID",
                "message": (
                    "the model may propose a closed evidence candidate only "
                    "and must never modify relationship stage"
                ),
                "path": (
                    "payload.modules.relationship_rule.fields."
                    "relationship_evidence_candidate_contract"
                ),
            }
        )
    if {
        reference.get("source_layer_id")
        for reference in safety_boundary_refs
    } != {"layer_3", "layer_12"} or {
        reference.get("source_layer_id")
        for reference in memory_policy_refs
    } != {"layer_5"}:
        diagnostics.append(
            {
                "status": "FAIL",
                "code": "DR_RELATIONSHIP_POLICY_REFERENCE_MISSING",
                "message": (
                    "relationship progression requires real Layer 3, Layer "
                    "5, and Layer 12 policy references"
                ),
                "path": (
                    "payload.modules.relationship_rule.config.references"
                ),
            }
        )
        return None, diagnostics
    projection = {
        "schema_version": RELATIONSHIP_PROGRESSION_SCHEMA_VERSION,
        "content_revision": (
            RELATIONSHIP_PROGRESSION_PROJECTION_CONTENT_REVISION
        ),
        "derived": True,
        "read_only": True,
        "source_paths": list(RELATIONSHIP_PROGRESSION_SOURCE_PATHS),
        "default_stage": default_stage,
        "enabled_stages": deepcopy(enabled_stages),
        "reserved_stages": [
            RELATIONSHIP_PROGRESSION_RESERVED_STAGE
        ],
        "stage_definitions": deepcopy(stage_definitions),
        "transition_evidence_rules": {
            "allowed_evidence_types": deepcopy(
                rule_values.get(
                    "allowed_relationship_evidence_types"
                )
                or []
            ),
            "progression_requirements": deepcopy(
                rule_values.get("relationship_progression_requirements")
                or []
            ),
            "candidate_fields": deepcopy(
                evidence_contract.get("allowed_output_fields") or []
            ),
            "requires_explicit_user_expression": True,
        },
        "forbidden_transition_rules": {
            "forbidden_evidence": deepcopy(
                forbidden_evidence or []
            ),
            "automatic_transition": False,
            "vulnerability_cannot_trigger": True,
            "model_or_resident_inference_cannot_trigger": True,
        },
        "reset_and_rollback_policy": {
            "available_user_actions": deepcopy(user_actions or []),
            "user_control_has_highest_priority": bool(
                reset_policy.get("user_control_has_highest_priority")
            ),
            "resident_must_not_block_or_dissuade": bool(
                reset_policy.get(
                    "resident_must_not_block_or_dissuade"
                )
            ),
            "reset_target": reset_policy.get("reset_target"),
            "reset_deletes_memory": reset_policy.get(
                "reset_deletes_memory"
            ),
            "memory_deletion_authority": reset_policy.get(
                "memory_deletion_authority"
            ),
            "forbidden_responses": deepcopy(
                reset_policy.get("forbidden_responses") or []
            ),
        },
        "user_consent_policy": {
            "requires_explicit_user_consent": True,
            "user_control_priority": "highest",
            "confirmation_required_when_requested": True,
            "single_utterance_unlocks_reserved_stage": False,
            "consent_cannot_bypass_feature_gate": True,
            "user_can_disable_progression": (
                "disable_relationship_progression"
                in (user_actions or [])
            ),
        },
        "safety_boundary_refs": safety_boundary_refs,
        "memory_policy_refs": memory_policy_refs,
        "romantic_feature_gate": reserved_stage,
        "stage_decision_owner": "runtime",
        "model_can_propose_evidence_only": True,
        "model_can_change_stage": False,
        "user_control_priority": "highest",
    }
    return projection, diagnostics
