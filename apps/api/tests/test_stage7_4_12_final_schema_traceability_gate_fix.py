"""Stage 7.4.12 final P1 schema-gate and traceability regression tests."""

from __future__ import annotations

from copy import deepcopy

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.dr.v3.dr_v0_3_schema import DRDocumentV03
from app.dr.v3.validator import validate_dr_document_v0_3
from app.main import app
from app.registry.module_catalog import (
    DETAIL_BEHAVIOR_MODULE_ID,
    DETAIL_BEHAVIOR_OUTPUT_KEY,
    DETAIL_BEHAVIOR_PRESET_ID,
)
from app.services import dr_compiler, resident_runtime
from app.services.dr_compiler import (
    _behavior_module_policy,
    compile_dr_result_v0_3,
    compile_dr_v0_3,
    mock_load_dr_v0_3,
)
from app.services.projection_traceability import (
    PROJECTION_FIELD_MAPPINGS,
    STAGE7_4_12_FINAL_SCHEMA_TRACEABILITY_GATE_FIX_REVISION,
)


client = TestClient(app)
_REQUIRED_CAPABILITIES = ["llm", "memory", "lattice"]
_ALLOWED_STATES = [
    "neutral",
    "calm",
    "caring",
    "subdued",
    "joyful",
]


def _canvas() -> dict:
    return {
        "workflow": {
            "name": "Stage 7.4.12 final schema gate fixture",
            "template_type": "schema_v04",
            "nodes": [
                {"node_id": f"layer_{index}"}
                for index in range(1, 14)
            ],
            "edges": [],
        }
    }


@pytest.fixture(scope="module")
def baseline_dr() -> dict:
    dr = compile_dr_v0_3(_canvas())
    assert dr["audit_report"]["valid"] is True
    return dr


def _runtime_behavior_mapping() -> dict:
    return next(
        mapping
        for mapping in PROJECTION_FIELD_MAPPINGS
        if mapping["mapping_id"] == "runtime_behavior_policy"
    )


def test_detail_behavior_value_and_expression_output_contract_are_unchanged(
    baseline_dr: dict,
):
    modules = {
        module["module_id"]: module
        for module in baseline_dr["payload"]["modules"]
    }
    emotion_reaction = modules[DETAIL_BEHAVIOR_MODULE_ID]
    detail_behavior = baseline_dr["payload"]["behavior_policy"][
        "modules"
    ]["detail_behavior"]

    assert detail_behavior == _behavior_module_policy(
        emotion_reaction,
        "detail_behavior",
        DETAIL_BEHAVIOR_PRESET_ID,
    )
    assert emotion_reaction["outputs"][DETAIL_BEHAVIOR_OUTPUT_KEY] == {
        "expression_state": "neutral",
        "expression_intensity": 0.0,
    }
    assert {
        "expression_state",
        "expression_intensity",
    }.isdisjoint(detail_behavior)


def test_detail_behavior_traceability_matches_current_node_inputs():
    mapping = _runtime_behavior_mapping()
    sources = {
        source["source_id"]: source for source in mapping["sources"]
    }
    detail = sources["detail_behavior_current_rule_nodes"]

    assert mapping["source_structure"] == "multiple"
    assert detail["source_layer"] == "layer_8"
    assert detail["source_module"] == "emotion_reaction"
    assert detail["source_output"] is None
    assert detail["projection_path"] == (
        "payload.behavior_policy.modules.detail_behavior"
    )
    assert detail["transform"] == "_behavior_module_policy"
    assert detail["source_node"] == (
        "expression_context_input",
        "expression_allowed_state_recognition",
        "expression_state_selection_rules",
        "expression_personality_consistency_validation",
        "expression_relationship_safety_validation",
        "expression_intensity_calculation",
        "expression_state_normalize_fallback_validation",
        "expression_state_output",
        "expression_state_reference_output",
    )
    assert (
        "module_graph.nodes.expression_context_input.params.references"
        in detail["source_field"]
    )
    assert (
        "module_graph.nodes.expression_state_selection_rules."
        "params.checkbox_config.selected_options"
        in detail["source_field"]
    )
    assert (
        "module_graph.nodes."
        "expression_state_normalize_fallback_validation."
        "params.checkbox_config.selected_options"
        in detail["source_field"]
    )
    assert DETAIL_BEHAVIOR_OUTPUT_KEY not in mapping["source_output"]
    assert all(
        source["source_output"] != DETAIL_BEHAVIOR_OUTPUT_KEY
        for source in mapping["sources"]
    )


@pytest.mark.parametrize(
    "locale", ("zh-CN", "en", "zh", "en-US")
)
def test_controlled_ui_languages_pass_formal_schema(
    baseline_dr: dict, locale: str
):
    document = deepcopy(baseline_dr)
    document["payload"]["resident_blueprint"][
        "ui_language"
    ] = locale

    DRDocumentV03.model_validate(document)


def test_current_full_envelope_passes_single_formal_gate(
    baseline_dr: dict,
):
    validated = DRDocumentV03.model_validate(baseline_dr)
    gate = validate_dr_document_v0_3(baseline_dr)

    assert validated.payload.behavior is not None
    assert validated.payload.behavior_policy is not None
    assert validated.payload.expression is not None
    assert validated.payload.relationship is not None
    assert validated.payload.runtime_dialogue_projection is not None
    assert validated.visual_expression_mapping is not None
    assert validated.modules == validated.payload.modules
    assert gate["schema_valid"] is True
    assert gate["valid"] is True
    assert mock_load_dr_v0_3(baseline_dr)["loaded"] is True


def test_formal_gate_rejects_unknown_root_and_wrong_field_type(
    baseline_dr: dict,
):
    unknown = deepcopy(baseline_dr)
    unknown["unknown_business_projection"] = {}
    wrong_type = deepcopy(baseline_dr)
    wrong_type["payload"]["modules"] = "not-a-module-list"

    for document, expected_code in (
        (unknown, "DR_V03_SCHEMA_EXTRA"),
        (wrong_type, "DR_V03_SCHEMA_TYPE"),
    ):
        with pytest.raises(ValidationError):
            DRDocumentV03.model_validate(document)
        findings = validate_dr_document_v0_3(document)["findings"]
        assert expected_code in {
            finding["code"]
            for finding in findings
            if finding["status"] == "FAIL"
        }
        assert all("Traceback" not in finding["message"] for finding in findings)


@pytest.mark.parametrize(
    ("path", "value"),
    (
        (("dr_version",), "0.4"),
        (("dr_schema_version",), "0.4.0"),
        (("protocol_version",), "0.5.0"),
        (("schema_version",), "0.5.0"),
        (("not_executable",), False),
        (
            ("manifest", "required_capabilities"),
            ["llm", "memory", "lattice", "tts"],
        ),
    ),
)
def test_frozen_versions_and_required_capabilities_are_rejected_on_drift(
    baseline_dr: dict, path: tuple[str, ...], value: object
):
    document = deepcopy(baseline_dr)
    cursor = document
    for key in path[:-1]:
        cursor = cursor[key]
    cursor[path[-1]] = value

    with pytest.raises(ValidationError):
        DRDocumentV03.model_validate(document)


def test_illegal_module_envelope_is_rejected(baseline_dr: dict):
    document = deepcopy(baseline_dr)
    document["payload"]["modules"][0].pop("module_id")
    document["modules"][0].pop("module_id")

    findings = validate_dr_document_v0_3(document)["schema_findings"]

    assert any(
        finding["status"] == "FAIL"
        and finding["code"] == "DR_V03_SCHEMA_REQUIRED"
        and finding["path"].endswith("module_id")
        for finding in findings
    )


def test_root_module_projection_cannot_override_payload_authority(
    baseline_dr: dict,
):
    document = deepcopy(baseline_dr)
    document["modules"][0]["module_name"] = "ROOT_OVERRIDE"

    with pytest.raises(ValidationError):
        DRDocumentV03.model_validate(document)


def test_root_resident_projection_cannot_override_payload_identity(
    baseline_dr: dict,
):
    document = deepcopy(baseline_dr)
    document["resident"]["resident_id"] = "ROOT_OVERRIDE"
    document["resident"]["name"] = "ROOT_OVERRIDE"

    with pytest.raises(ValidationError):
        DRDocumentV03.model_validate(document)
    assert validate_dr_document_v0_3(document)["valid"] is False
    assert mock_load_dr_v0_3(document)["loaded"] is False


def test_real_provider_credentials_are_rejected_by_formal_gate(
    baseline_dr: dict,
):
    document = deepcopy(baseline_dr)
    for modules in (
        document["payload"]["modules"],
        document["modules"],
    ):
        modules[0]["config"]["provider_profile"] = {
            "provider": "openai",
            "endpoint": "https://provider.example/v1",
        }

    gate = validate_dr_document_v0_3(document)

    assert gate["schema_valid"] is True
    assert gate["valid"] is False
    assert any(
        finding["code"] == "DR_COMPILED_CREDENTIAL_VALUE"
        for finding in gate["security_findings"]
    )


def test_schema_runs_before_runtime_contract(
    baseline_dr: dict, monkeypatch: pytest.MonkeyPatch
):
    from app.dr.v3 import validator

    calls: list[str] = []
    original_schema = validator.DRDocumentV03.model_validate
    original_runtime = validator.validate_v03_runtime_contract

    def schema(document):
        calls.append("schema")
        return original_schema(document)

    def runtime(document):
        calls.append("runtime")
        return original_runtime(document)

    monkeypatch.setattr(
        validator.DRDocumentV03, "model_validate", schema
    )
    monkeypatch.setattr(
        validator, "validate_v03_runtime_contract", runtime
    )

    assert validator.validate_dr_document_v0_3(baseline_dr)[
        "valid"
    ] is True
    assert calls[:2] == ["schema", "runtime"]


def test_compile_calls_the_central_formal_schema_gate_once(
    monkeypatch: pytest.MonkeyPatch,
):
    from app.dr.v3 import validator

    calls = 0
    original_schema = validator.DRDocumentV03.model_validate

    def schema(document):
        nonlocal calls
        calls += 1
        return original_schema(document)

    monkeypatch.setattr(
        validator.DRDocumentV03, "model_validate", schema
    )

    result = compile_dr_result_v0_3(_canvas())

    assert result["valid"] is True
    assert calls == 1


def test_schema_failure_blocks_compile_result_and_export(
    monkeypatch: pytest.MonkeyPatch,
):
    failure = {
        "status": "FAIL",
        "code": "DR_V03_SCHEMA_TYPE",
        "message": "forced formal schema failure",
        "path": "payload.modules",
    }

    def reject(_document):
        return {
            "valid": False,
            "schema_valid": False,
            "schema_findings": [failure],
            "runtime_contract_findings": [],
            "security_findings": [],
            "findings": [failure],
        }

    monkeypatch.setattr(
        dr_compiler, "validate_dr_document_v0_3", reject
    )
    result = compile_dr_result_v0_3(_canvas())
    response = client.post("/dr/export", json=_canvas())

    assert result["valid"] is False
    assert result["compiled_dr"] is None
    assert failure in result["errors"]
    assert response.status_code == 422


def test_old_optional_projection_absence_remains_loadable(
    baseline_dr: dict,
):
    legacy = deepcopy(baseline_dr)
    legacy.pop("visual_expression_mapping")
    legacy["payload"].pop("behavior")
    legacy["payload"].pop("expression")
    legacy["payload"].pop("relationship")
    legacy["payload"].pop("runtime_dialogue_projection")
    legacy["payload"]["audit_policy"].pop(
        "schema_traceability_gate_revision", None
    )

    assert DRDocumentV03.model_validate(legacy)
    assert validate_dr_document_v0_3(legacy)["valid"] is True
    assert mock_load_dr_v0_3(legacy)["loaded"] is True


def test_old_non_binding_default_provider_labels_remain_compatible(
    baseline_dr: dict,
):
    legacy = deepcopy(baseline_dr)
    legacy["legacy_blueprint"]["voice_config"].update(
        {"enabled": True, "provider": "default", "output_mode": "tts"}
    )
    legacy["legacy_blueprint"]["tts_provider_config"].update(
        {
            "provider": "default",
            "provider_candidates": [
                "default",
                "elevenlabs",
                "volcano",
            ],
            "mode": "mock",
        }
    )

    assert validate_dr_document_v0_3(legacy)["valid"] is True
    assert mock_load_dr_v0_3(legacy)["loaded"] is True


def test_runtime_loader_rejects_schema_invalid_v03_without_execution(
    baseline_dr: dict,
):
    document = deepcopy(baseline_dr)
    document["unknown_business_projection"] = {}

    result = resident_runtime.load_digital_resident(document)

    assert result["loaded"] is False
    assert result["execution_trace"] == []
    assert any(
        error["code"] == "DR_V03_SCHEMA_EXTRA"
        for error in result["validation_result"]["errors"]
    )


def test_revision_frozen_visual_values_and_repeat_compile_are_stable():
    first = compile_dr_result_v0_3(_canvas())
    second = compile_dr_result_v0_3(_canvas())

    assert first["valid"] is second["valid"] is True
    for result in (first, second):
        dr = result["compiled_dr"]
        assert dr["payload"]["audit_policy"][
            "schema_traceability_gate_revision"
        ] == STAGE7_4_12_FINAL_SCHEMA_TRACEABILITY_GATE_FIX_REVISION
        assert dr["dr_version"] == "0.3"
        assert dr["dr_schema_version"] == "0.3.0"
        assert dr["manifest"][
            "required_capabilities"
        ] == _REQUIRED_CAPABILITIES
        assert dr["visual_expression_mapping"][
            "allowed_states"
        ] == _ALLOWED_STATES
        particle = dr["visual_expression_mapping"][
            "particle_core_mapping"
        ]
        assert particle["caring"]["brightness_multiplier"] == 1.06
        assert particle["subdued"]["energy_multiplier"] == 0.78
        assert particle["joyful"]["diffusion_multiplier"] == 1.14
    assert first["compiled_dr"]["payload"][
        "behavior_policy"
    ] == second["compiled_dr"]["payload"]["behavior_policy"]
    assert first["compiled_dr"][
        "visual_expression_mapping"
    ] == second["compiled_dr"]["visual_expression_mapping"]
    assert first["compile_audit"][
        "projection_traceability"
    ] == second["compile_audit"]["projection_traceability"]
