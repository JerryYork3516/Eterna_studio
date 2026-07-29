"""Stage 7.4.12 A3 value-level projection and traceability contracts."""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

from app.registry.module_catalog import get_module_catalog
from app.services.dr_compiler import (
    _assemble_layer8_behavior_outputs,
    compile_dr_result_v0_3,
)
from app.services.projection_traceability import (
    PROJECTION_FIELD_MAPPINGS,
    STAGE7_4_12_A3_CONTENT_REVISION,
    STAGE7_4_12_FINAL_SCHEMA_TRACEABILITY_GATE_FIX_REVISION,
    projection_field_mapping_errors,
)


LAYER8_OUTPUTS = {
    "language_habit": ("language_behavior", "language_behavior_config"),
    "decision_pattern": ("decision_behavior", "decision_behavior_config"),
    "interaction_strategy": (
        "interaction_behavior",
        "interaction_behavior_config",
    ),
    "emotion_mapper": ("social_behavior", "social_behavior_config"),
    "behavior_habit": ("task_behavior", "task_behavior_config"),
}
DIAGNOSTIC_CODES = (
    "DR_PROJECTION_SOURCE_NODE_NORMALIZED",
    "DR_PROJECTION_SOURCE_MISSING",
    "DR_PROJECTION_COMPATIBILITY_FALLBACK",
    "DR_PROJECTION_FIELD_MAPPING_ERROR",
)


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


def _canvas(modules: list[dict], **extra: object) -> dict:
    return {
        "workflow": {
            "name": "stage_7_4_12_a3_projection_traceability",
            "nodes": [
                {"node_id": f"layer_{index}"}
                for index in range(1, 14)
            ],
        },
        "modules": modules,
        **extra,
    }


def _compile_result(modules: list[dict], **extra: object) -> dict:
    return compile_dr_result_v0_3(_canvas(modules, **extra))


def _compile(modules: list[dict], **extra: object) -> dict:
    result = _compile_result(modules, **extra)
    assert result["valid"] is True, result["errors"]
    return result["compiled_dr"]


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
            value_key = (
                "field_value"
                if "field_value" in field
                else "value"
            )
            field[value_key] = deepcopy(value)
            found = True
    assert found, f"field {field_key!r} was not found"


def _set_output_path(
    module: dict,
    output_key: str,
    path: tuple[str, ...],
    value: object,
) -> None:
    targets: list[dict] = []
    module_output = module.get("outputs", {}).get(output_key)
    if isinstance(module_output, dict):
        targets.append(module_output)
    for node in module["module_graph"]["nodes"]:
        node_output = node.get("outputs", {}).get(output_key)
        if isinstance(node_output, dict):
            targets.append(node_output)
    assert targets, f"output {output_key!r} was not found"
    for target in targets:
        cursor = target
        for key in path[:-1]:
            nested = cursor.get(key)
            if not isinstance(nested, dict):
                nested = {}
                cursor[key] = nested
            cursor = nested
        cursor[path[-1]] = deepcopy(value)


def _projection(dr: dict) -> dict:
    return dr["payload"]["runtime_dialogue_projection"]


def test_layer5_current_outputs_drive_all_runtime_memory_value_groups():
    modules = _modules()
    access = _module(modules, "memory_access_control")
    update = _module(modules, "memory_update")
    event = _module(modules, "event_memory")
    short_term = _module(modules, "short_term_memory")
    _set_output_path(
        access,
        "memory_access_policy_result",
        ("permission_policy", "missing_user_authorization"),
        "A3_ACCESS_SENTINEL",
    )
    _set_output_path(
        update,
        "memory_update_policy",
        ("write_boundary",),
        "A3_WRITE_SENTINEL",
    )
    _set_output_path(
        event,
        "event_memory",
        ("save_allowed",),
        [
            "brief_summary",
            "event_meaning",
            "timestamp",
            "A3_NARRATIVE_SENTINEL",
        ],
    )
    _set_output_path(
        short_term,
        "short_term_memory_context",
        ("expires_on",),
        "A3_SESSION_SENTINEL",
    )

    dr = _compile(modules)
    memory = _projection(dr)["memory_usage_policy"]["derived_values"]

    assert memory["memory_access_limits"]["permission_policy"][
        "missing_user_authorization"
    ] == "A3_ACCESS_SENTINEL"
    assert (
        memory["memory_write_limits"]["write_boundary"]
        == "A3_WRITE_SENTINEL"
    )
    assert memory["narrative_memory_usage_rules"]["event_memory"][
        "save_allowed"
    ][-1] == "A3_NARRATIVE_SENTINEL"
    assert memory["conversation_and_long_term_boundary"][
        "short_term_memory"
    ]["expires_on"] == "A3_SESSION_SENTINEL"


def test_layer11_current_nodes_drive_initial_and_runtime_relationship_values():
    modules = _modules()
    user_relationship = _module(modules, "user_relationship")
    relationship_rule = _module(modules, "relationship_rule")
    intimacy = _module(modules, "intimacy_level")
    role = _module(modules, "role_positioning")
    initial = {
        "default": "A3_RELATIONSHIP_MODE",
        "intimacy_level": "low",
        "trust_building": "gradual",
    }
    _set_field(user_relationship, "initial_relationship", initial)
    _set_field(
        user_relationship,
        "default_relationship_position",
        "A3_ROLE_SENTINEL",
    )
    _set_field(
        relationship_rule,
        "baseline_relationship_behavior",
        "A3_BOUNDARY_SENTINEL",
    )
    _set_field(intimacy, "default_stage", "A3_STAGE_SENTINEL")
    _set_field(
        role,
        "trust_building_rules",
        ["A3_TRUST_SENTINEL"],
    )
    for module, output_key, stale_field in (
        (
            user_relationship,
            "user_relationship_config",
            "default_relationship_position",
        ),
        (
            relationship_rule,
            "relationship_behavior_config",
            "baseline_relationship_behavior",
        ),
        (intimacy, "relationship_stage_config", "default_stage"),
        (role, "trust_mechanism_config", "trust_building_rules"),
    ):
        _set_output_path(
            module,
            output_key,
            ("fields", stale_field),
            "STALE_OUTPUT_MUST_NOT_WIN",
        )

    dr = _compile(modules)
    relationship = _projection(dr)["relationship_policy"][
        "derived_values"
    ]

    assert dr["payload"]["relationship"]["initial_relationship"] == initial
    assert (
        "initial_relationship"
        not in relationship["user_relationship"]
    )
    assert relationship["user_relationship"][
        "default_relationship_position"
    ] == "A3_ROLE_SENTINEL"
    assert relationship["relationship_boundaries"][
        "baseline_relationship_behavior"
    ] == "A3_BOUNDARY_SENTINEL"
    assert relationship["intimacy_limits"][
        "default_stage"
    ] == "A3_STAGE_SENTINEL"
    assert relationship["role_boundaries"][
        "trust_building_rules"
    ] == ["A3_TRUST_SENTINEL"]


def test_layer12_boundaries_use_current_output_and_a2_resolved_facts():
    modules = _modules()
    identity = _module(modules, "module_existence_mode")
    language = _module(modules, "module_basic_identity")
    environment = _module(modules, "environment_setting")
    relationship = _module(modules, "user_relationship")
    self_awareness = _module(modules, "self_awareness")
    growth = _module(modules, "growth_plan")
    _set_field(
        identity,
        "digital_resident_type",
        "A3_IDENTITY_FACT",
    )
    _set_field(language, "primary_language", "a3-language")
    _set_field(environment, "city_environment", "A3_REGION_FACT")
    _set_field(
        relationship,
        "default_relationship_position",
        "A3_RELATION_FACT",
    )
    _set_field(
        self_awareness,
        "identity_type",
        "STALE_SELF_AWARENESS_IDENTITY",
    )
    _set_field(
        self_awareness,
        "capability_scope",
        ["A3_CAPABILITY_SENTINEL"],
    )
    _set_field(
        self_awareness,
        "capability_limits",
        ["A3_PROFESSIONAL_BOUNDARY_SENTINEL"],
    )
    _set_output_path(
        growth,
        "growth_identity_continuity_governance_config",
        ("forbidden_change_reason",),
        "A3_GROWTH_SENTINEL",
    )

    dr = _compile(modules)
    projection = _projection(dr)
    disclosure = projection["self_disclosure_policy"][
        "derived_values"
    ]
    advice = projection["advice_policy"]["derived_values"]

    assert disclosure["resolved_facts"] == {
        "identity_type": "A3_IDENTITY_FACT",
        "resident_type": "A3_IDENTITY_FACT",
        "primary_language": "a3-language",
        "regional_identity_type": "A3_REGION_FACT",
        "default_relationship_role": "A3_RELATION_FACT",
    }
    assert (
        disclosure["relationship_awareness"]["default_role"]
        == "A3_RELATION_FACT"
    )
    assert disclosure["growth_limits"][
        "forbidden_change_reason"
    ] == "A3_GROWTH_SENTINEL"
    assert advice["capability_scope"] == [
        "A3_CAPABILITY_SENTINEL"
    ]
    assert advice["capability_limits"] == [
        "A3_PROFESSIONAL_BOUNDARY_SENTINEL"
    ]
    assert "STALE_SELF_AWARENESS_IDENTITY" not in json.dumps(
        projection, ensure_ascii=False
    )


def test_layer8_behavior_assembly_prefers_a2_module_outputs():
    modules = _modules()
    for index, (
        module_id,
        (_policy_key, output_key),
    ) in enumerate(LAYER8_OUTPUTS.items(), start=1):
        module = _module(modules, module_id)
        _set_output_path(
            module,
            output_key,
            ("selected_options",),
            [f"A3_MODULE_OUTPUT_{index}"],
        )

    assembled = _assemble_layer8_behavior_outputs(
        {"modules": modules}
    )
    behavior_modules = assembled["behavior_policy"]["modules"]

    for index, (
        _module_id,
        (policy_key, _output_key),
    ) in enumerate(LAYER8_OUTPUTS.items(), start=1):
        assert behavior_modules[policy_key][
            "selected_options"
        ] == [f"A3_MODULE_OUTPUT_{index}"]


def test_old_top_projections_never_reverse_fill_current_deep_sources():
    baseline = _compile(_modules())
    stale = {
        "runtime_dialogue_projection": {
            "memory_usage_policy": "STALE_TOP_PROJECTION"
        },
        "memory_policy": {"STALE_TOP_PROJECTION": True},
        "visual_expression_mapping": {
            "allowed_states": ["STALE_TOP_PROJECTION"]
        },
    }
    actual = _compile(_modules(), **stale)

    assert (
        _projection(actual)["memory_usage_policy"]["derived_values"]
        == _projection(baseline)["memory_usage_policy"][
            "derived_values"
        ]
    )
    assert (
        actual["visual_expression_mapping"]
        == baseline["visual_expression_mapping"]
    )
    assert "STALE_TOP_PROJECTION" not in json.dumps(
        {
            "runtime": _projection(actual),
            "memory": actual["payload"]["memory_policy"],
            "visual": actual["visual_expression_mapping"],
        },
        ensure_ascii=False,
    )


def test_missing_output_rebuilds_from_current_node_and_reports_diagnostic():
    modules = _modules()
    relationship = _module(modules, "relationship_rule")
    _set_field(
        relationship,
        "baseline_relationship_behavior",
        "A3_NODE_FALLBACK_SENTINEL",
    )
    output_key = "relationship_behavior_config"
    relationship["outputs"].pop(output_key, None)
    for node in relationship["module_graph"]["nodes"]:
        if isinstance(node.get("outputs"), dict):
            node["outputs"].pop(output_key, None)

    result = _compile_result(modules)

    assert result["valid"] is True, result["errors"]
    assert "DR_PROJECTION_SOURCE_NODE_NORMALIZED" in {
        warning["code"] for warning in result["warnings"]
    }
    assert (
        result["compiled_dr"]["payload"][
            "runtime_dialogue_projection"
        ]["relationship_policy"]["derived_values"][
            "relationship_boundaries"
        ]["baseline_relationship_behavior"]
        == "A3_NODE_FALLBACK_SENTINEL"
    )


def test_missing_deep_source_uses_safe_shape_and_localized_fallback_diagnostics():
    modules = [
        module
        for module in _modules()
        if module["module_id"]
        not in {"relationship_rule", "dialogue_runtime_profile"}
    ]

    result = _compile_result(modules)
    diagnostics = {
        item["code"]
        for item in [*result["errors"], *result["warnings"]]
    }
    projection = result["dr_payload"]["runtime_dialogue_projection"]

    assert result["valid"] is False
    assert {
        "DR_PROJECTION_SOURCE_MISSING",
        "DR_PROJECTION_COMPATIBILITY_FALLBACK",
    } <= diagnostics
    assert projection["relationship_policy"]["derived_values"][
        "relationship_boundaries"
    ] == {}

    locale_root = Path(__file__).parents[2] / "web" / "locales"
    en = json.loads(
        (locale_root / "en.json").read_text(encoding="utf-8")
    )
    zh = json.loads(
        (locale_root / "zh.json").read_text(encoding="utf-8")
    )
    for code in DIAGNOSTIC_CODES:
        for prefix in ("audit", "validation"):
            key = f"{prefix}.{code}"
            assert en[key].strip()
            assert zh[key].strip()
            assert en[key] != key
            assert zh[key] != key
            assert "\ufffd" not in en[key] + zh[key]


def test_compile_audit_contains_exact_stable_sixteen_mapping_registry():
    result = _compile_result(_modules())
    traceability = result["compile_audit"][
        "projection_traceability"
    ]

    assert result["valid"] is True, result["errors"]
    assert projection_field_mapping_errors() == []
    assert traceability == {
        "content_revision": STAGE7_4_12_A3_CONTENT_REVISION,
        "schema_traceability_gate_revision": (
            STAGE7_4_12_FINAL_SCHEMA_TRACEABILITY_GATE_FIX_REVISION
        ),
        "projection_type": "derived_read_only",
        "source_priority": [
            "current_module_output",
            "normalized_current_node",
            "protocol_compatibility_fallback",
        ],
        "mappings": list(PROJECTION_FIELD_MAPPINGS),
    }
    assert len(traceability["mappings"]) == 16
    assert len(
        {
            mapping["mapping_id"]
            for mapping in traceability["mappings"]
        }
    ) == 16
    for mapping in traceability["mappings"]:
        assert mapping["source_layer"]
        assert mapping["source_module"]
        assert "source_output" in mapping
        assert mapping["source_field"]
        assert mapping["source_path"]
        assert mapping["target_path"]
        assert mapping["transform"]
        assert mapping["alias_rule"]
        assert mapping["missing_fallback"]
        assert mapping["consumer"]
        assert mapping["projection_type"] == "derived_read_only"
    assert "projection_traceability" not in result["compiled_dr"]


def test_repeated_compile_and_compiled_module_migration_are_idempotent():
    modules = _modules()
    before = deepcopy(modules)
    first = _compile_result(modules)
    second = _compile_result(modules)
    migrated = _compile_result(
        deepcopy(first["compiled_dr"]["payload"]["modules"])
    )

    assert modules == before
    assert first["valid"] is second["valid"] is migrated["valid"] is True
    for key in (
        "runtime_dialogue_projection",
        "memory_policy",
    ):
        assert (
            first["compiled_dr"]["payload"][key]
            == second["compiled_dr"]["payload"][key]
            == migrated["compiled_dr"]["payload"][key]
        )
    assert (
        first["compiled_dr"]["visual_expression_mapping"]
        == second["compiled_dr"]["visual_expression_mapping"]
        == migrated["compiled_dr"]["visual_expression_mapping"]
    )
    assert (
        first["compile_audit"]["projection_traceability"]
        == second["compile_audit"]["projection_traceability"]
        == migrated["compile_audit"]["projection_traceability"]
    )
    for result in (first, second, migrated):
        compiled = result["compiled_dr"]
        modules = compiled["payload"]["modules"]
        assert len(
            [m for m in modules if m["module_id"] == "relationship_rule"]
        ) == 1
        for module in modules:
            node_ids = [
                node["node_id"]
                for node in module.get(
                    "module_graph", {}
                ).get("nodes", [])
                if isinstance(node, dict) and node.get("node_id")
            ]
            assert len(node_ids) == len(set(node_ids))


def test_versions_capabilities_and_frozen_compatibility_mirrors_do_not_change():
    result = _compile_result(_modules())
    dr = result["compiled_dr"]

    assert dr["dr_version"] == "0.3"
    assert dr["dr_schema_version"] == "0.3.0"
    assert dr["manifest"]["required_capabilities"] == [
        "llm",
        "memory",
        "lattice",
    ]
    assert dr["memory_policy"] == dr["payload"]["memory_policy"]
    assert dr["lattice_config"] == dr["payload"]["lattice_config"]
    assert dr["voice_config"] == dr["payload"]["voice_config"]
    assert (
        dr["runtime_requirements"]
        == dr["payload"]["runtime_requirements"]
    )
    mapping = dr["visual_expression_mapping"][
        "particle_core_mapping"
    ]
    assert mapping["caring"]["brightness_multiplier"] == 1.06
    assert mapping["subdued"]["energy_multiplier"] == 0.78
    assert mapping["joyful"]["diffusion_multiplier"] == 1.14
