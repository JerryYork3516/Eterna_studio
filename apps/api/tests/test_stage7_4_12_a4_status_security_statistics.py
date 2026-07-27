"""Stage 7.4.12 A4 status, security, mirror, and audit-statistics contracts."""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.v0_4 import empty_layer_design_metadata
from app.registry.module_catalog import get_module_catalog
from app.services import dr_compiler
from app.services.capability_status_governance import (
    STAGE7_4_12_A4_CONTENT_REVISION,
    build_capability_status_governance,
    build_lattice_config_status,
    build_voice_config_status,
)
from app.services.dr_compiler import (
    compile_dr_result_v0_3,
    compile_dr_v0_3,
    mock_load_dr_v0_3,
    normalized_dr_json_v0_3,
    serialize_dr_v0_3,
)


client = TestClient(app)
_REQUIRED_CAPABILITIES = ["llm", "memory", "lattice"]
_A4_DIAGNOSTIC_CODES = (
    "DR_COMPATIBILITY_FIELD_MIRROR_DRIFT",
    "DR_COMPATIBILITY_LEGACY_FIELDS_PROMOTED",
    "DR_COMPATIBILITY_LEGACY_FIELDS_AMBIGUOUS",
    "DR_CURRENT_LEGACY_FIELD_SYNC_COMPLETE",
    "DR_EXPORT_NONAUTHORITATIVE_MODULE_COPY",
    "DR_MODULE_AUTHORITY_PROJECTION_DRIFT",
    "DR_GRAPH_SNAPSHOT_STATUS_INVALID",
    "DR_CAPABILITY_STATUS_GOVERNANCE_INVALID",
    "DR_CAPABILITY_REQUIRED_SET_DRIFT",
    "DR_VOICE_CONFIG_STATUS_INVALID",
    "DR_VOICE_CONFIG_PROVIDER_ACTIVE",
    "DR_LATTICE_CONFIG_STATUS_INVALID",
    "DR_LEGACY_VOICE_PROVIDER_ACTIVE",
    "DR_ABSTRACT_BUST_STATUS_INVALID",
    "DR_MODULE_STATUS_CLASSIFICATION_DRIFT",
    "DR_PROVIDER_MODULE_STATUS_ACTIVE",
    "DR_CAPABILITY_STATUS_CHECK_PASSED",
    "DR_COMPILED_CREDENTIAL_VALUE",
    "DR_SECURITY_CONFIGURATION_CHECK_PASSED",
    "DR_EMPTY_LAYER_STATUS_INVALID",
    "DR_EMPTY_LAYER_STATUS_CHECK_PASSED",
    "DR_NORMALIZED_JSON_SIZE_RECORDED",
)


def _workflow() -> dict[str, Any]:
    return {
        "name": "Stage 7.4.12 A4 status fixture",
        "nodes": [
            {"node_id": f"layer_{index}"}
            for index in range(1, 14)
        ],
    }


def _canvas() -> dict[str, Any]:
    return {"workflow": _workflow()}


@pytest.fixture(scope="module")
def baseline_dr() -> dict[str, Any]:
    dr = compile_dr_v0_3(_canvas())
    assert dr["audit_report"]["valid"] is True
    return dr


def _catalog_module_with_fields() -> tuple[dict[str, Any], dict[str, Any]]:
    for model in get_module_catalog():
        module = model.model_dump(mode="json")
        graph = module.get("module_graph")
        if not isinstance(graph, dict):
            continue
        for node in graph.get("nodes", []):
            params = node.get("params")
            if (
                isinstance(params, dict)
                and isinstance(params.get("fields"), list)
                and params["fields"]
            ):
                return module, node
    raise AssertionError("catalog has no current-field module")


def _compatibility_node_count(modules: list[dict[str, Any]]) -> int:
    return sum(
        1
        for module in modules
        for node in dr_compiler._module_graph_nodes(module)
        if node.get("node_type") in {"field_input", "text_input"}
        if isinstance(node.get("params"), dict)
        and any(
            key in node["params"]
            for key in (
                "fields",
                "legacy_fields",
                "legacy_data_fields",
            )
        )
    )


def test_compiled_status_registry_is_central_and_required_set_is_frozen(
    baseline_dr: dict[str, Any],
):
    payload = baseline_dr["payload"]
    registry = payload["audit_policy"][
        "capability_status_governance"
    ]

    assert registry == build_capability_status_governance()
    assert (
        payload["audit_policy"]["content_revision"]
        == STAGE7_4_12_A4_CONTENT_REVISION
    )
    assert baseline_dr["manifest"]["required_capabilities"] == (
        _REQUIRED_CAPABILITIES
    )
    assert payload["runtime_requirements"]["required_slot_types"] == (
        _REQUIRED_CAPABILITIES
    )
    non_required_subjects = {
        "ar",
        "tool",
        "tts",
        "voice_config",
        "screen",
        "speech",
        "avatar_runtime",
        "abstract_bust",
        "llm_provider",
        "memory_provider",
    }
    for subject_id in non_required_subjects:
        classification = registry["capabilities"][subject_id]
        assert classification["required_capability"] is False
        assert "active" not in classification["states"]


def test_voice_is_mock_and_lattice_is_consumable_without_visual_drift(
    baseline_dr: dict[str, Any],
):
    payload = baseline_dr["payload"]
    voice = payload["voice_config"]
    lattice = payload["lattice_config"]
    visual = baseline_dr["visual_expression_mapping"]

    assert voice["status_classification"] == build_voice_config_status()
    assert voice["tts_profile"]["provider"] == "mock"
    assert voice["status_classification"]["required_capability"] is False
    assert lattice["status_classification"] == (
        build_lattice_config_status()
    )
    assert lattice["status_classification"]["configuration_consumable"] is True
    assert lattice["status_classification"]["required_capability"] is True
    assert visual["allowed_states"] == [
        "neutral",
        "calm",
        "caring",
        "subdued",
        "joyful",
    ]
    mapping = visual["particle_core_mapping"]
    assert mapping["caring"]["brightness_multiplier"] == 1.06
    assert mapping["subdued"]["energy_multiplier"] == 0.78
    assert mapping["joyful"]["diffusion_multiplier"] == 1.14


def test_legacy_voice_shell_is_disabled_mock_compatibility_only(
    baseline_dr: dict[str, Any],
):
    legacy = baseline_dr["legacy_blueprint"]
    voice = legacy["voice_config"]
    tts = legacy["tts_provider_config"]

    assert legacy["compatibility_status"]["authoritative"] is False
    assert legacy["compatibility_status"]["may_override_authority"] is False
    assert voice["enabled"] is False
    assert voice["provider"] == "mock"
    assert voice["output_mode"] == "mock"
    assert voice["status_classification"] == build_voice_config_status()
    assert tts["provider"] == "mock"
    assert tts["provider_candidates"] == ["mock"]
    assert tts["status_classification"] == build_voice_config_status()


def test_authoritative_provider_modules_are_not_ready_or_executable(
    baseline_dr: dict[str, Any],
):
    modules = {
        module["module_id"]: module
        for module in baseline_dr["payload"]["modules"]
    }
    llm_provider = modules["llm_provider_router"]
    memory_provider = modules["memory_provider_router"]

    assert llm_provider["status"] == "RESERVED"
    assert memory_provider["status"] == "READY"
    for module in (llm_provider, memory_provider):
        assert module["runtime_enabled"] is False
        assert module["no_execution"] is True
        assert module["status_classification"]["runtime_enabled"] is False
    assert llm_provider["status"].lower() in (
        llm_provider["status_classification"]["states"]
    )
    assert memory_provider["status"] in memory_provider[
        "status_classification"
    ]["legacy_status_values"]
    assert memory_provider["status_classification"][
        "legacy_status_semantics"
    ] == "catalog_configuration_ready_only_not_runtime_enabled"


def test_provider_module_status_drift_is_rejected_by_audit(
    baseline_dr: dict[str, Any],
):
    drifted = deepcopy(baseline_dr)
    memory_provider = next(
        module
        for module in drifted["payload"]["modules"]
        if module["module_id"] == "memory_provider_router"
    )
    memory_provider["status"] = "ACTIVE"

    findings = dr_compiler._v03_capability_status_findings(drifted)

    assert any(
        finding["status"] == "FAIL"
        and finding["code"]
        in {
            "DR_MODULE_STATUS_CLASSIFICATION_DRIFT",
            "DR_PROVIDER_MODULE_STATUS_ACTIVE",
        }
        for finding in findings
    )


def test_graph_output_cache_requires_non_authoritative_status(
    baseline_dr: dict[str, Any],
):
    drifted = deepcopy(baseline_dr)
    drifted["payload"]["graph_snapshot"].pop(
        "layer_outputs_status"
    )

    findings = dr_compiler._v03_duplicate_source_findings(drifted)

    assert any(
        finding["status"] == "FAIL"
        and finding["code"] == "DR_GRAPH_SNAPSHOT_STATUS_INVALID"
        for finding in findings
    )


def test_empty_layers_keep_a2_explicit_non_capability_states(
    baseline_dr: dict[str, Any],
):
    layers = {
        layer["layer_id"]: layer
        for layer in baseline_dr["payload"]["13_layers_snapshot"]
    }
    for layer_id in ("layer_4", "layer_6", "layer_13"):
        expected = empty_layer_design_metadata(layer_id)
        assert layer_id in layers
        for key, expected_value in expected.items():
            assert layers[layer_id][key] == expected_value
        assert layers[layer_id]["runtime_enabled"] is False
        assert layers[layer_id]["declares_capability"] is False


def test_current_fields_win_and_legacy_mirrors_are_idempotent():
    module, node = _catalog_module_with_fields()
    params = node["params"]
    current_fields = deepcopy(params["fields"])
    first_field = current_fields[0]
    value_key = (
        "value" if "value" in first_field else "field_value"
    )
    first_field[value_key] = "current-authority-value"
    params["fields"] = current_fields
    params["legacy_fields"] = deepcopy(current_fields)
    params["legacy_data_fields"] = deepcopy(current_fields)
    params["legacy_fields"][0][value_key] = "legacy-must-not-win"
    params["legacy_data_fields"][0][value_key] = (
        "legacy-data-must-not-win"
    )

    findings: list[dict[str, str]] = []
    first_metrics = dr_compiler._sync_current_field_compatibility(
        [module], findings
    )
    first_snapshot = deepcopy(module)
    second_findings: list[dict[str, str]] = []
    second_metrics = dr_compiler._sync_current_field_compatibility(
        [module], second_findings
    )

    output_params = node["params"]
    assert output_params["fields"][0][value_key] == (
        "current-authority-value"
    )
    assert output_params["legacy_fields"] == output_params["fields"]
    assert output_params["legacy_data_fields"] == output_params["fields"]
    assert any(
        finding["code"] == "DR_COMPATIBILITY_FIELD_MIRROR_DRIFT"
        for finding in findings
    )
    assert first_metrics["inspected_nodes"] == (
        _compatibility_node_count([module])
    )
    assert first_metrics["synchronized_nodes"] == (
        first_metrics["inspected_nodes"]
    )
    assert second_metrics["repaired_nodes"] == 0
    assert module == first_snapshot
    assert not any(
        finding["code"] == "DR_COMPATIBILITY_FIELD_MIRROR_DRIFT"
        for finding in second_findings
    )


def test_legacy_only_fields_are_promoted_only_when_unambiguous():
    module, node = _catalog_module_with_fields()
    params = node["params"]
    legacy_fields = deepcopy(params.pop("fields"))
    legacy_fields[0][
        "value" if "value" in legacy_fields[0] else "field_value"
    ] = "legacy-authored-value"
    params["legacy_fields"] = deepcopy(legacy_fields)
    params["legacy_data_fields"] = deepcopy(legacy_fields)
    findings: list[dict[str, str]] = []

    metrics = dr_compiler._sync_current_field_compatibility(
        [module], findings
    )

    assert params["fields"] == legacy_fields
    assert params["legacy_fields"] == legacy_fields
    assert params["legacy_data_fields"] == legacy_fields
    assert metrics["promoted_nodes"] >= 1
    assert any(
        finding["code"] == "DR_COMPATIBILITY_LEGACY_FIELDS_PROMOTED"
        for finding in findings
    )


def test_disagreeing_legacy_only_fields_are_preserved_without_guessing():
    module, node = _catalog_module_with_fields()
    params = node["params"]
    original_fields = deepcopy(params.pop("fields"))
    params["legacy_fields"] = deepcopy(original_fields)
    params["legacy_data_fields"] = deepcopy(original_fields)
    value_key = (
        "value"
        if "value" in params["legacy_data_fields"][0]
        else "field_value"
    )
    params["legacy_data_fields"][0][value_key] = "conflicting-value"
    legacy_before = {
        "legacy_fields": deepcopy(params["legacy_fields"]),
        "legacy_data_fields": deepcopy(params["legacy_data_fields"]),
    }
    findings: list[dict[str, str]] = []

    metrics = dr_compiler._sync_current_field_compatibility(
        [module], findings
    )

    assert "fields" not in params
    assert params["legacy_fields"] == legacy_before["legacy_fields"]
    assert (
        params["legacy_data_fields"]
        == legacy_before["legacy_data_fields"]
    )
    assert metrics["preserved_ambiguous_nodes"] >= 1
    assert any(
        finding["code"] == "DR_COMPATIBILITY_LEGACY_FIELDS_AMBIGUOUS"
        for finding in findings
    )


def test_compiled_compatibility_count_matches_actual_structure(
    baseline_dr: dict[str, Any],
):
    metrics = baseline_dr["audit_report"]["compatibility_metrics"]
    actual = _compatibility_node_count(
        baseline_dr["payload"]["modules"]
    )

    assert metrics["inspected_nodes"] == actual
    assert metrics["synchronized_nodes"] == actual
    assert metrics["created_nodes"] >= 0
    assert metrics["repaired_nodes"] >= 0


def test_serialization_metrics_match_actual_in_memory_and_export_bytes(
    baseline_dr: dict[str, Any],
):
    metrics = baseline_dr["audit_report"]["serialization_metrics"]

    assert metrics["normalized_json_bytes"] == len(
        normalized_dr_json_v0_3(baseline_dr)
    )
    assert metrics["actual_export_bytes"] == len(
        serialize_dr_v0_3(baseline_dr)
    )
    assert metrics["actual_export_serialization"] == (
        "studio_json_stringify_pretty_utf8"
    )
    assert metrics["normalized_json_bytes"] < (
        metrics["actual_export_bytes"]
    )


@pytest.mark.parametrize(
    ("key", "value"),
    (
        ("api_key", "sk-test-actual-secret-value"),
        ("token", "actual-token-value"),
        ("bearer_credential", "Bearer actual-token-value"),
        ("base_url", "https://provider.example/v1"),
        ("endpoint", "https://provider.example/v1/chat"),
        ("endpointUrl", "https://provider.example/v1/chat"),
        ("api_token", "actual-api-token-value"),
        ("provider_secret", "actual-provider-secret"),
        ("password", "actual-password"),
        ("provider", "openai"),
        ("provider_profile", {"provider": "real"}),
    ),
)
def test_security_scan_rejects_actual_values(key: str, value: Any):
    findings = dr_compiler._v03_security_configuration_findings(
        {"payload": {key: value}}
    )

    assert any(
        finding["status"] == "FAIL"
        and finding["code"] == "DR_COMPILED_CREDENTIAL_VALUE"
        for finding in findings
    )


def test_security_scan_allows_empty_placeholders_and_mock_labels():
    findings = dr_compiler._v03_security_configuration_findings(
        {
            "payload": {
                "api_key": "",
                "token": None,
                "base_url": "",
                "credential": {},
                "provider_profile": "mock",
                "provider": "memory_mock",
                "endpoint": "",
            }
        }
    )

    assert findings == [
        {
            "status": "PASS",
            "code": "DR_SECURITY_CONFIGURATION_CHECK_PASSED",
            "message": (
                "compiled DR contains no actual API key, token, bearer "
                "credential, base URL, Provider secret, password, or real "
                "Provider Profile"
            ),
            "path": "payload",
        }
    ]


def test_compiled_credential_blocks_compile_and_export(
    monkeypatch: pytest.MonkeyPatch,
):
    original = dr_compiler._v03_compatibility_aliases

    def inject_credential(*args, **kwargs):
        aliases = original(*args, **kwargs)
        aliases["legacy_blueprint"]["credentials"] = {
            "token": "actual-token-value"
        }
        return aliases

    monkeypatch.setattr(
        dr_compiler,
        "_v03_compatibility_aliases",
        inject_credential,
    )
    result = compile_dr_result_v0_3(_canvas())
    response = client.post("/dr/export", json=_canvas())

    assert result["valid"] is False
    assert result["compiled_dr"] is None
    assert response.status_code == 422
    assert any(
        finding["code"] == "DR_COMPILED_CREDENTIAL_VALUE"
        for finding in result["errors"]
    )


def test_old_dr_without_a4_status_projections_still_loads(
    baseline_dr: dict[str, Any],
):
    legacy = deepcopy(baseline_dr)
    legacy["payload"]["audit_policy"].pop(
        "capability_status_governance", None
    )
    legacy["payload"]["audit_policy"].pop("content_revision", None)
    legacy["payload"]["voice_config"].pop(
        "status_classification", None
    )
    legacy["payload"]["lattice_config"].pop(
        "status_classification", None
    )
    legacy["voice_config"].pop("status_classification", None)
    legacy["lattice_config"].pop("status_classification", None)
    legacy["legacy_blueprint"].pop("compatibility_status", None)

    assert mock_load_dr_v0_3(legacy)["loaded"] is True


def test_api_export_bytes_use_the_reported_actual_size():
    response = client.post("/dr/export", json=_canvas())
    assert response.status_code == 200
    exported = json.loads(response.content)

    assert len(response.content) == exported["audit_report"][
        "serialization_metrics"
    ]["actual_export_bytes"]


def test_a4_diagnostics_are_complete_in_chinese_and_english():
    locale_root = Path(__file__).parents[2] / "web" / "locales"
    dictionaries = {
        language: json.loads(
            (locale_root / f"{language}.json").read_text(
                encoding="utf-8"
            )
        )
        for language in ("zh", "en")
    }

    for code in _A4_DIAGNOSTIC_CODES:
        for language, dictionary in dictionaries.items():
            for prefix in ("audit", "validation"):
                value = dictionary[f"{prefix}.{code}"]
                assert value.strip(), (language, prefix, code)
                assert "\ufffd" not in value


def test_version_capabilities_and_frozen_visual_values_remain_unchanged(
    baseline_dr: dict[str, Any],
):
    visual = baseline_dr["visual_expression_mapping"]

    assert baseline_dr["dr_version"] == "0.3"
    assert baseline_dr["dr_schema_version"] == "0.3.0"
    assert baseline_dr["schema_version"] == "0.4.0"
    assert baseline_dr["protocol_version"] == "0.4.0"
    assert baseline_dr["manifest"]["required_capabilities"] == (
        _REQUIRED_CAPABILITIES
    )
    assert visual["default_state"] == "neutral"
    assert visual["base_color_policy"]["priority"] == [
        "user_current_base_color",
        "resident_default_base_color",
        "particle_core_default_gray_white",
    ]
    assert visual["transition_policy"][
        "uses_accumulated_idle_time_as_progress"
    ] is False
