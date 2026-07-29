"""Compile-only Layer 5 narrative-memory projection.

Layer 5 remains authoritative. This module derives a read-only Runtime-facing
policy view, validates real cross-layer references, and rejects per-user
narrative-memory records from DR compile/export data.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, Iterable, Optional


NARRATIVE_MEMORY_PROJECTION_SCHEMA_VERSION = "0.1"
NARRATIVE_MEMORY_PROJECTION_CONTENT_REVISION = (
    "stage7_4_14_narrative_memory_projection_v0_1"
)
NARRATIVE_MEMORY_ALLOWED_TYPES = (
    "shared_experience",
    "confirmed_plan",
    "important_progress",
    "confirmed_emotional_event",
    "mutual_commitment",
    "user_marked_important",
)
NARRATIVE_MEMORY_LIFECYCLE_STATES = (
    "candidate",
    "active",
    "superseded",
    "deleted",
    "rejected",
)
NARRATIVE_MEMORY_SOURCE_MODULES = (
    "event_memory",
    "memory_update",
    "memory_access_control",
)
NARRATIVE_MEMORY_SOURCE_PATHS = (
    "payload.modules.event_memory.outputs.event_memory",
    "payload.modules.memory_update.outputs.memory_update_policy",
    (
        "payload.modules.memory_access_control.outputs."
        "memory_access_policy_result"
    ),
)
NARRATIVE_MEMORY_FORBIDDEN_INSTANCE_FIELDS = frozenset(
    {
        "current_narrative_memories",
        "stored_memory_items",
        "narrative_memory_records",
        "user_memory_records",
        "memory_records",
        "conversation_transcript",
        "event_content",
        "event_summary",
        "candidate_summary",
        "plan_content",
        "confirmed_plan_content",
        "current_user_plan",
        "confirmed_user_plan",
        "emotional_event_content",
        "confirmed_emotional_event_content",
        "user_emotional_experience",
        "memory_record_value",
    }
)
NARRATIVE_MEMORY_FORBIDDEN_RECORD_SUFFIXES = (
    "_memory_items",
    "_memory_records",
    "_narrative_memories",
)
NARRATIVE_MEMORY_SCHEMA_ONLY_PATH_PARTS = frozenset(
    {
        "output_schema",
        "candidate_output_contract",
        "accepted_fields",
        "request_fields",
        "fields_schema",
        "field_aliases",
        "i18n_keys",
    }
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


def _module_output(
    module: Dict[str, Any], output_key: str
) -> Dict[str, Any]:
    outputs = _as_dict(module.get("outputs"))
    return deepcopy(_as_dict(outputs.get(output_key)))


def _narrative_extension(
    output: Dict[str, Any],
    source_kind: str,
) -> Dict[str, Any]:
    """Read the nested A3 source, with a narrow A1/A2 compatibility view."""

    nested = output.get("narrative_memory_extension")
    if isinstance(nested, dict):
        return deepcopy(nested)

    if source_kind == "event":
        return {
            "allowed_memory_types": deepcopy(
                output.get("memory_types") or []
            ),
            "memory_lifecycle_states": deepcopy(
                output.get("lifecycle_states") or []
            ),
            "candidate_evidence_rules": {
                "requirements": deepcopy(
                    output.get("candidate_requirements") or []
                ),
                "excluded_inputs": deepcopy(
                    output.get("candidate_exclusions") or []
                ),
                "candidate_fields": deepcopy(
                    output.get("candidate_output_contract") or []
                ),
            },
            "forbidden_content_rules": deepcopy(
                output.get("narrative_save_forbidden") or []
            ),
            "consent_policy": deepcopy(
                _as_dict(output.get("consent_policy"))
            ),
            "model_authority": deepcopy(
                _as_dict(output.get("permission_boundary"))
            ),
            "runtime_authority": deepcopy(
                _as_dict(output.get("permission_boundary"))
            ),
            "references": deepcopy(output.get("references") or []),
        }
    if source_kind == "update":
        conflict = _as_dict(output.get("conflict_policy"))
        return {
            "memory_lifecycle_states": deepcopy(
                output.get("lifecycle_states") or []
            ),
            "allowed_transitions": deepcopy(
                output.get("allowed_transitions") or []
            ),
            "forbidden_transitions": deepcopy(
                output.get("forbidden_transitions") or []
            ),
            "deduplication_policy": {
                "same_event": conflict.get("same_event"),
            },
            "conflict_resolution_policy": {
                "latest_explicit_user_statement": conflict.get(
                    "latest_explicit_user_statement"
                ),
                "superseded_is_not_current_fact": conflict.get(
                    "superseded_is_not_current_fact"
                ),
            },
            "deletion_policy": deepcopy(
                _as_dict(output.get("delete_policy"))
            ),
            "rejected_policy": deepcopy(
                _as_dict(output.get("rejected_policy"))
            ),
            "model_authority": deepcopy(
                _as_dict(output.get("permission_boundary"))
            ),
            "runtime_authority": deepcopy(
                _as_dict(output.get("permission_boundary"))
            ),
            "references": deepcopy(output.get("references") or []),
        }
    return {
        "retrieval_policy": {
            "allowed_lifecycle_states": deepcopy(
                output.get("allowed_lifecycle_states") or []
            ),
            "excluded_lifecycle_states": deepcopy(
                output.get("excluded_lifecycle_states") or []
            ),
            "rules": deepcopy(output.get("retrieval_rules") or []),
        },
        "expression_policy": {
            "rules": deepcopy(
                output.get("expression_rules") or []
            ),
            "relationship_stage_transition_allowed": False,
        },
        "user_control": deepcopy(
            _as_dict(output.get("user_control"))
        ),
        "references": deepcopy(output.get("references") or []),
    }


def _meaningful_instance_value(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, dict)):
        return bool(value)
    return True


def _field_instance_findings(
    value: Any,
    path: str,
    findings: list[Dict[str, str]],
) -> None:
    if isinstance(value, dict):
        field_key = str(
            value.get("field_key")
            or value.get("field_id")
            or ""
        )
        if (
            field_key in NARRATIVE_MEMORY_FORBIDDEN_INSTANCE_FIELDS
            and _meaningful_instance_value(
                value.get("field_value")
                if "field_value" in value
                else value.get("value")
            )
        ):
            findings.append(
                {
                    "status": "FAIL",
                    "code": "DR_NARRATIVE_MEMORY_INSTANCE_DATA_FORBIDDEN",
                    "message": (
                        "DR narrative-memory rules must not contain a "
                        f"per-user value for field {field_key!r}"
                    ),
                    "path": path,
                }
            )
        for key, item in value.items():
            key_text = str(key)
            item_path = f"{path}.{key_text}" if path else key_text
            path_parts = set(item_path.split("."))
            schema_only = bool(
                path_parts & NARRATIVE_MEMORY_SCHEMA_ONLY_PATH_PARTS
            )
            forbidden_container = (
                key_text in NARRATIVE_MEMORY_FORBIDDEN_INSTANCE_FIELDS
                or key_text.endswith(
                    NARRATIVE_MEMORY_FORBIDDEN_RECORD_SUFFIXES
                )
            )
            if (
                forbidden_container
                and not schema_only
                and _meaningful_instance_value(item)
            ):
                findings.append(
                    {
                        "status": "FAIL",
                        "code": (
                            "DR_NARRATIVE_MEMORY_INSTANCE_DATA_FORBIDDEN"
                        ),
                        "message": (
                            "DR narrative-memory rules must not embed "
                            f"per-user data in {key_text!r}"
                        ),
                        "path": item_path,
                    }
                )
                continue
            _field_instance_findings(item, item_path, findings)
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _field_instance_findings(
                item, f"{path}[{index}]", findings
            )


def narrative_memory_instance_findings(
    modules: Iterable[Dict[str, Any]],
) -> list[Dict[str, str]]:
    """Reject concrete per-user narrative-memory data in Layer 5 rules."""

    findings: list[Dict[str, str]] = []
    for module in modules:
        if (
            not isinstance(module, dict)
            or module.get("module_id")
            not in NARRATIVE_MEMORY_SOURCE_MODULES
        ):
            continue
        _field_instance_findings(
            module,
            f"payload.modules.{module.get('module_id')}",
            findings,
        )
    deduped: Dict[tuple[str, str], Dict[str, str]] = {}
    for finding in findings:
        deduped[(finding["code"], finding["path"])] = finding
    return list(deduped.values())


def _reference_projection(
    reference: Dict[str, Any],
) -> Dict[str, str]:
    source_layer_id = str(reference.get("source_layer_id") or "")
    source_module_id = str(reference.get("source_module_id") or "")
    source_node_id = str(reference.get("source_node_id") or "")
    usage = str(reference.get("usage") or "")
    return {
        "source_layer_id": source_layer_id,
        "source_module_id": source_module_id,
        "source_node_id": source_node_id,
        "source_path": (
            f"payload.modules.{source_module_id}.module_graph.nodes."
            f"{source_node_id}"
        ),
        "usage": usage,
    }


def _validated_references(
    module_list: list[Dict[str, Any]],
    outputs: Iterable[Dict[str, Any]],
) -> tuple[list[Dict[str, str]], list[Dict[str, str]]]:
    modules_by_id = {
        str(module.get("module_id") or ""): module
        for module in module_list
    }
    references: list[Dict[str, str]] = []
    diagnostics: list[Dict[str, str]] = []
    seen: set[tuple[str, str, str]] = set()
    for output in outputs:
        declared = output.get("references")
        if not isinstance(declared, list):
            continue
        for reference in declared:
            if not isinstance(reference, dict):
                continue
            projected = _reference_projection(reference)
            identity = (
                projected["source_layer_id"],
                projected["source_module_id"],
                projected["source_node_id"],
            )
            if identity in seen:
                continue
            seen.add(identity)
            source_module = modules_by_id.get(
                projected["source_module_id"]
            )
            source_nodes = (
                _as_dict(source_module.get("module_graph")).get("nodes")
                if isinstance(source_module, dict)
                else []
            )
            node_exists = any(
                isinstance(node, dict)
                and str(node.get("node_id") or "")
                == projected["source_node_id"]
                for node in (
                    source_nodes if isinstance(source_nodes, list) else []
                )
            )
            layer_matches = (
                isinstance(source_module, dict)
                and source_module.get("layer_id")
                == projected["source_layer_id"]
            )
            if not source_module or not node_exists or not layer_matches:
                diagnostics.append(
                    {
                        "status": "FAIL",
                        "code": (
                            "DR_NARRATIVE_MEMORY_REFERENCE_INVALID"
                        ),
                        "message": (
                            "Narrative-memory projection reference must "
                            "target a real module and node"
                        ),
                        "path": (
                            "payload.modules."
                            f"{projected['source_module_id']}."
                            f"{projected['source_node_id']}"
                        ),
                    }
                )
                continue
            references.append(projected)
    return references, diagnostics


def build_narrative_memory_projection(
    modules: Iterable[Dict[str, Any]],
) -> tuple[Optional[Dict[str, Any]], list[Dict[str, str]]]:
    """Build the optional projection from current Layer 5 rule outputs."""

    module_list = [
        module for module in modules if isinstance(module, dict)
    ]
    event_module = _module_by_id(module_list, "event_memory")
    update_module = _module_by_id(module_list, "memory_update")
    access_module = _module_by_id(
        module_list, "memory_access_control"
    )
    if not event_module or not update_module or not access_module:
        return None, [
            {
                "status": "WARNING",
                "code": "DR_NARRATIVE_MEMORY_SOURCE_MISSING",
                "message": (
                    "Layer 5 narrative-memory rule sources are missing; "
                    "the optional projection was omitted"
                ),
                "path": "payload.narrative_memory_projection",
            }
        ]

    event = _module_output(event_module, "event_memory")
    update = _module_output(update_module, "memory_update_policy")
    access = _module_output(
        access_module, "memory_access_policy_result"
    )
    event_extension = _narrative_extension(event, "event")
    update_extension = _narrative_extension(update, "update")
    access_extension = _narrative_extension(access, "access")
    diagnostics = narrative_memory_instance_findings(module_list)

    allowed_types = event_extension.get("allowed_memory_types")
    if allowed_types != list(NARRATIVE_MEMORY_ALLOWED_TYPES):
        diagnostics.append(
            {
                "status": "FAIL",
                "code": "DR_NARRATIVE_MEMORY_TYPES_INVALID",
                "message": (
                    "Narrative-memory types must contain exactly the six "
                    "Stage 7.4.14 types in stable order"
                ),
                "path": (
                    "payload.modules.event_memory.outputs."
                    "event_memory.narrative_memory_extension."
                    "allowed_memory_types"
                ),
            }
        )
        allowed_types = list(NARRATIVE_MEMORY_ALLOWED_TYPES)

    lifecycle_states = event_extension.get(
        "memory_lifecycle_states"
    )
    if (
        lifecycle_states
        != list(NARRATIVE_MEMORY_LIFECYCLE_STATES)
        or update_extension.get("memory_lifecycle_states")
        != list(NARRATIVE_MEMORY_LIFECYCLE_STATES)
    ):
        diagnostics.append(
            {
                "status": "FAIL",
                "code": "DR_NARRATIVE_MEMORY_LIFECYCLE_INVALID",
                "message": (
                    "Narrative-memory lifecycle states must contain exactly "
                    "candidate, active, superseded, deleted, and rejected"
                ),
                "path": (
                    "payload.modules.event_memory.outputs."
                    "event_memory.narrative_memory_extension."
                    "memory_lifecycle_states"
                ),
            }
        )
        lifecycle_states = list(
            NARRATIVE_MEMORY_LIFECYCLE_STATES
        )

    references, reference_diagnostics = _validated_references(
        module_list,
        (event_extension, update_extension, access_extension),
    )
    diagnostics.extend(reference_diagnostics)
    safety_refs = [
        reference
        for reference in references
        if reference["source_layer_id"] == "layer_3"
    ]
    dialogue_refs = [
        reference
        for reference in references
        if reference["source_layer_id"] == "layer_8"
    ]
    relationship_refs = [
        reference
        for reference in references
        if reference["source_layer_id"] == "layer_11"
    ]
    if not safety_refs or not dialogue_refs or not relationship_refs:
        diagnostics.append(
            {
                "status": "FAIL",
                "code": "DR_NARRATIVE_MEMORY_BOUNDARY_REFERENCE_MISSING",
                "message": (
                    "Narrative-memory projection requires real Layer 3, "
                    "Layer 8, and Layer 11 boundary references"
                ),
                "path": "payload.narrative_memory_projection",
            }
        )
        return None, diagnostics

    model_authority = _as_dict(
        event_extension.get("model_authority")
    )
    runtime_authority = _as_dict(
        event_extension.get("runtime_authority")
    )
    consent = _as_dict(event_extension.get("consent_policy"))
    sensitivity = _as_dict(
        event_extension.get("sensitivity_policy")
    )
    candidate_evidence = _as_dict(
        event_extension.get("candidate_evidence_rules")
    )
    deduplication = _as_dict(
        update_extension.get("deduplication_policy")
    )
    conflict = _as_dict(
        update_extension.get("conflict_resolution_policy")
    )
    supersession = _as_dict(
        update_extension.get("supersession_policy")
    )
    delete_policy = _as_dict(
        update_extension.get("deletion_policy")
    )
    rejected_policy = _as_dict(
        update_extension.get("rejected_policy")
    )
    retrieval = _as_dict(
        access_extension.get("retrieval_policy")
    )
    expression = _as_dict(
        access_extension.get("expression_policy")
    )
    user_control = _as_dict(
        access_extension.get("user_control")
    )

    projection = {
        "schema_version": NARRATIVE_MEMORY_PROJECTION_SCHEMA_VERSION,
        "content_revision": (
            NARRATIVE_MEMORY_PROJECTION_CONTENT_REVISION
        ),
        "derived": True,
        "read_only": True,
        "source_paths": list(NARRATIVE_MEMORY_SOURCE_PATHS),
        "enabled": True,
        "allowed_memory_types": deepcopy(allowed_types),
        "memory_lifecycle_states": deepcopy(lifecycle_states),
        "candidate_evidence_rules": {
            "requirements": deepcopy(
                candidate_evidence.get("requirements") or []
            ),
            "excluded_inputs": deepcopy(
                candidate_evidence.get("excluded_inputs") or []
            ),
            "candidate_fields": deepcopy(
                candidate_evidence.get("candidate_fields") or []
            ),
            "explicit_user_statement_required": True,
            "source_turn_traceability_required": True,
        },
        "forbidden_content_rules": deepcopy(
            event_extension.get("forbidden_content_rules") or []
        ),
        "consent_policy": {
            **deepcopy(consent),
            "user_forget_request_target_state": "deleted",
        },
        "sensitivity_policy": {
            "sensitive_or_ambiguous_requires_explicit_user_consent": bool(
                consent.get(
                    (
                        "sensitive_or_ambiguous_requires_"
                        "explicit_user_consent"
                    )
                )
            ),
            "permanently_forbidden_categories": deepcopy(
                sensitivity.get("permanently_forbidden_categories")
                or []
            ),
            "safety_boundary_enforced": bool(
                sensitivity.get(
                    "safety_policy_validation_still_required",
                    True,
                )
            ),
            "legacy_sensitive_event_alias": deepcopy(
                sensitivity.get("legacy_sensitive_event_alias") or {}
            ),
        },
        "deduplication_policy": {
            "same_event_action": deduplication.get("same_event"),
            "duplicate_events_are_merged": (
                deduplication.get("same_event")
                == "deduplicate_or_merge"
            ),
        },
        "conflict_resolution_policy": {
            "latest_explicit_user_statement": conflict.get(
                "latest_explicit_user_statement"
            ),
            "user_latest_explicit_statement_has_priority": True,
        },
        "supersession_policy": {
            "older_conflicting_memory_state": (
                supersession.get(
                    "older_conflicting_memory_state"
                )
                or "superseded"
            ),
            "superseded_memory_is_current_fact": False,
            "superseded_memory_retrievable": False,
        },
        "deletion_policy": {
            **deepcopy(delete_policy),
            "deleted_memory_retrievable": False,
            "deleted_memory_enters_model_context": False,
        },
        "retrieval_policy": {
            "allowed_lifecycle_states": deepcopy(
                retrieval.get("allowed_lifecycle_states") or []
            ),
            "excluded_lifecycle_states": deepcopy(
                retrieval.get("excluded_lifecycle_states") or []
            ),
            "rules": deepcopy(retrieval.get("rules") or []),
            "deleted_memory_retrievable": False,
            "rejected_memory_retrievable": False,
            "deleted_or_rejected_enters_model_context": False,
        },
        "expression_policy": {
            "rules": deepcopy(expression.get("rules") or []),
            "relationship_stage_transition_allowed": False,
            "never_claim_permanent_memory": True,
        },
        "model_authority": {
            "model_can_propose_candidate_only": bool(
                model_authority.get(
                    "model_can_propose_candidate_only"
                )
            ),
            "model_can_write_memory": bool(
                model_authority.get("model_can_write_memory")
            ),
            "model_can_update_memory": bool(
                model_authority.get("model_can_update_memory")
            ),
            "model_can_delete_memory": bool(
                model_authority.get("model_can_delete_memory")
            ),
        },
        "runtime_authority": {
            "runtime_is_final_decision_owner": bool(
                runtime_authority.get(
                    "runtime_is_final_decision_owner"
                )
            ),
        },
        "relationship_boundary_refs": relationship_refs,
        "safety_boundary_refs": safety_refs,
        "dialogue_boundary_refs": dialogue_refs,
        "deleted_memory_retrievable": False,
        "rejected_candidate_reproposal_allowed": bool(
            rejected_policy.get("automatic_reproposal")
        ),
        "relationship_stage_transition_allowed": False,
        "full_dialogue_storage_allowed": False,
        "single_item_delete_supported": bool(
            delete_policy.get("single_item_delete")
            or user_control.get("single_item_delete")
        ),
        "clear_all_supported": bool(
            delete_policy.get("clear_all")
            or user_control.get("clear_all")
        ),
        "contains_user_memory_records": False,
    }
    return projection, diagnostics
