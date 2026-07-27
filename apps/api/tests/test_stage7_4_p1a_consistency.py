"""Stage 7.4 P1-A reference and export consistency contracts."""

from __future__ import annotations

from copy import deepcopy
import json

from fastapi.testclient import TestClient

from app.services import dr_compiler as dr_compiler_module
from app.main import app
from app.registry.module_catalog import get_module_catalog
from app.services.dr_compiler import (
    compile_dr_result_v0_3,
    compile_dr_v0_3,
    mock_load_dr_v0_3,
)


client = TestClient(app)
OLD_BOUNDARY_MODULE_IDS = {"professional_boundary", "dialogue_boundary"}
ENVIRONMENT_FIELD_IDS = (
    "city_environment",
    "natural_environment",
    "physical_living_environment",
    "daily_living_environment",
    "social_environment",
    "network_environment",
)
ENVIRONMENT_MAPPING_PREFIX = "payload.modules.environment_setting.outputs.environment_context.fields."


def _modules() -> list[dict]:
    return [module.model_dump(mode="json") for module in get_module_catalog()]


def _canvas(modules: list[dict] | None = None) -> dict:
    canvas = {
        "workflow": {"name": "P1-A Resident", "template_type": "schema_v04", "nodes": [], "edges": []},
        "nodes": [{"node_id": f"layer_{index}"} for index in range(1, 14)],
        "edges": [],
    }
    if modules is not None:
        canvas["modules"] = modules
    return canvas


def _module(modules: list[dict], module_id: str) -> dict:
    return next(module for module in modules if module["module_id"] == module_id)


def _field_node(module: dict) -> dict:
    return next(
        node
        for node in module["module_graph"]["nodes"]
        if isinstance(node.get("params"), dict) and isinstance(node["params"].get("fields"), list)
    )


def _field(module: dict, field_id: str) -> dict:
    return next(
        field
        for field in _field_node(module)["params"]["fields"]
        if (field.get("field_id") or field.get("field_key")) == field_id
    )


def _compiled_module(dr: dict, module_id: str) -> dict:
    return _module(dr["payload"]["modules"], module_id)


def _registries(dr: dict) -> list[tuple[dict, list[dict]]]:
    result = []
    for module in dr["payload"]["modules"]:
        registry = (module.get("config") or {}).get("reference_registry")
        if isinstance(registry, list):
            result.append((module, registry))
    return result


def _declared_fields(module: dict) -> set[str]:
    result: set[str] = set()
    for field in (module.get("config") or {}).get("field_registry") or []:
        if isinstance(field, dict) and (field.get("field_id") or field.get("field_key")):
            result.add(str(field.get("field_id") or field.get("field_key")))
    for node in (module.get("module_graph") or {}).get("nodes") or []:
        if node.get("node_type") == "field_reference":
            continue
        params = node.get("params") or {}
        for field in params.get("fields") or []:
            if isinstance(field, dict) and (field.get("field_id") or field.get("field_key")):
                result.add(str(field.get("field_id") or field.get("field_key")))
        output_schema = params.get("output_schema")
        if isinstance(output_schema, dict):
            result.update(str(field_id) for field_id in output_schema if field_id)
        elif isinstance(output_schema, list):
            for field in output_schema:
                if isinstance(field, dict) and (field.get("field_id") or field.get("field_key") or field.get("key")):
                    result.add(str(field.get("field_id") or field.get("field_key") or field.get("key")))
    return result


def _basic_identity_canvas() -> tuple[dict, dict]:
    modules = _modules()
    basic = _module(modules, "module_basic_identity")
    values = {
        "name": "林瑄",
        "display_alias": "小瑄",
        "codename": "linxuan_hum_cn_xian_01",
        "export_name": "linxuan",
        "resident_id": "dr_eterna_hum_cn_xian_linxuan_0001",
    }
    for field_id, value in values.items():
        field = _field(basic, field_id)
        if "field_value" in field:
            field["field_value"] = value
        else:
            field["value"] = value
    return _canvas(modules), values


def _identity_warning_canvas(*, generic: bool = False) -> tuple[dict, str]:
    canvas, _values = _basic_identity_canvas()
    personality = _module(canvas["modules"], "personality_traits")
    target = _field(personality, "personality_base")
    text = "林瑄会在表达中保持温和和克制。"
    if "field_value" in target:
        target["field_value"] = text
    else:
        target["value"] = text
    if generic:
        canvas["workflow"]["metadata"] = {"is_generic_template": True}
    return canvas, text


def _environment_canvas() -> tuple[dict, dict[str, str]]:
    modules = _modules()
    environment = _module(modules, "environment_setting")
    values = {field_id: f"环境值::{field_id}" for field_id in ENVIRONMENT_FIELD_IDS}
    for field_id, value in values.items():
        _field(environment, field_id)["field_value"] = value
    return _canvas(modules), values


def _strip_dynamic(value):
    if isinstance(value, dict):
        return {
            key: _strip_dynamic(item)
            for key, item in value.items()
            if key not in {"created_at", "updated_at", "compiled_at", "checked_at"}
        }
    if isinstance(value, list):
        return [_strip_dynamic(item) for item in value]
    return value


# P1-A-01 -------------------------------------------------------------------


def test_reference_registry_uses_current_module_ids():
    dr = compile_dr_v0_3(_canvas())
    assert dr["audit_report"]["valid"] is True
    assert not {
        reference["module_id"]
        for _module_value, registry in _registries(dr)
        for reference in registry
    }.intersection(OLD_BOUNDARY_MODULE_IDS)


def test_old_boundary_module_ids_are_not_exported():
    exported = json.loads(client.post("/dr/export", json=_canvas()).text)
    for _module_value, registry in _registries(exported):
        assert all(reference.get("module_id") not in OLD_BOUNDARY_MODULE_IDS for reference in registry)
        assert all(reference.get("path", "").split("/")[1] not in OLD_BOUNDARY_MODULE_IDS for reference in registry)


def test_legacy_boundary_alias_resolves_without_source_mutation():
    modules = _modules()
    language = _module(modules, "language_habit")
    registry = language["config"]["reference_registry"]
    reference = next(item for item in registry if item["field_id"] == "forbidden_interactions")
    reference.update(
        {
            "reference_id": "required_dialogue_boundary_forbidden_tone",
            "layer_id": "layer_3",
            "module_id": "dialogue_boundary",
            "field_id": "forbidden_tone",
            "path": "layer_3/dialogue_boundary/forbidden_tone",
        }
    )
    decision = _module(modules, "decision_pattern")
    risk_reference = next(
        item for item in decision["config"]["reference_registry"] if item["field_id"] == "risk_policy"
    )
    risk_reference.update(
        {
            "reference_id": "required_dialogue_boundary_risk_response_boundary",
            "layer_id": "layer_3",
            "module_id": "dialogue_boundary",
            "field_id": "risk_response_boundary",
            "path": "layer_3/dialogue_boundary/risk_response_boundary",
        }
    )
    professional_reference = next(
        item for item in decision["config"]["reference_registry"] if item["field_id"] == "real_world_decision_limits"
    )
    professional_reference.update(
        {
            "reference_id": "required_professional_boundary_no_professional_judgement_replacement",
            "layer_id": "layer_3",
            "module_id": "professional_boundary",
            "field_id": "no_professional_judgement_replacement",
            "path": "layer_3/professional_boundary/no_professional_judgement_replacement",
        }
    )
    social = _module(modules, "emotion_mapper")
    relationship_reference = next(
        item for item in social["config"]["reference_registry"] if item["field_id"] == "non_romantic_default_boundary"
    )
    relationship_reference.update(
        {
            "reference_id": "required_dialogue_boundary_relationship_boundary",
            "layer_id": "layer_3",
            "module_id": "dialogue_boundary",
            "field_id": "relationship_boundary",
            "path": "layer_3/dialogue_boundary/relationship_boundary",
        }
    )
    canvas = _canvas(modules)
    before = deepcopy(canvas)
    dr = compile_dr_v0_3(canvas)
    compiled = _compiled_module(dr, "language_habit")["config"]["reference_registry"]
    resolved = next(item for item in compiled if item["field_id"] == "forbidden_interactions")
    assert resolved["module_id"] == "humanistic_interaction_boundary_config_v0_1"
    assert resolved["reference_id"] == "required_humanistic_interaction_boundary_forbidden_interactions"
    compiled_decision = _compiled_module(dr, "decision_pattern")["config"]["reference_registry"]
    resolved_risk = next(item for item in compiled_decision if item["field_id"] == "risk_policy")
    assert resolved_risk["module_id"] == "humanistic_risk_response_config_v0_1"
    assert resolved_risk["reference_id"] == "required_humanistic_risk_response_risk_policy"
    resolved_professional = next(
        item for item in compiled_decision if item["field_id"] == "real_world_decision_limits"
    )
    assert resolved_professional["module_id"] == "humanistic_behavior_boundary_config_v0_1"
    assert resolved_professional["reference_id"] == "required_humanistic_behavior_boundary_real_world_decision_limits"
    compiled_social = _compiled_module(dr, "emotion_mapper")["config"]["reference_registry"]
    resolved_relationship = next(
        item for item in compiled_social if item["field_id"] == "non_romantic_default_boundary"
    )
    assert resolved_relationship["module_id"] == "humanistic_interaction_boundary_config_v0_1"
    assert resolved_relationship["reference_id"] == "required_humanistic_interaction_boundary_non_romantic_default_boundary"
    assert canvas == before


def test_required_registry_reference_points_to_existing_field():
    dr = compile_dr_v0_3(_canvas())
    modules = {module["module_id"]: module for module in dr["payload"]["modules"]}
    for _owner, registry in _registries(dr):
        for reference in registry:
            if reference.get("reference_type") != "required":
                continue
            target = modules[reference["module_id"]]
            assert target["layer_id"] == reference["layer_id"]
            assert reference["field_id"] in _declared_fields(target)


def test_default_registry_references_all_resolve_without_optional_warnings():
    result = compile_dr_result_v0_3(_canvas())
    assert result["valid"] is True
    assert not any(
        item["code"] == "DR_OPTIONAL_REGISTRY_REFERENCE_OMITTED"
        for item in result["warnings"]
    )

    modules = {module["module_id"]: module for module in result["compiled_dr"]["payload"]["modules"]}
    for _owner, registry in _registries(result["compiled_dr"]):
        for reference in registry:
            target = modules[reference["module_id"]]
            assert target["layer_id"] == reference["layer_id"]
            assert reference["field_id"] in _declared_fields(target)


def test_optional_missing_registry_reference_warns_only():
    modules = _modules()
    language = _module(modules, "language_habit")
    language["config"]["reference_registry"].append(
        {
            "reference_id": "optional_missing",
            "reference_type": "optional",
            "layer_id": "layer_7",
            "module_id": "world_setting",
            "field_id": "missing_optional_field",
            "path": "layer_7/world_setting/missing_optional_field",
        }
    )
    result = compile_dr_result_v0_3(_canvas(modules))
    assert result["valid"] is True
    assert any(item["code"] == "DR_OPTIONAL_REGISTRY_REFERENCE_OMITTED" for item in result["warnings"])
    registry = _compiled_module(result["compiled_dr"], "language_habit")["config"]["reference_registry"]
    assert all(item["reference_id"] != "optional_missing" for item in registry)


def test_required_missing_registry_reference_blocks_export():
    modules = _modules()
    language = _module(modules, "language_habit")
    language["config"]["reference_registry"].append(
        {
            "reference_id": "required_missing",
            "reference_type": "required",
            "layer_id": "layer_7",
            "module_id": "world_setting",
            "field_id": "missing_required_field",
            "path": "layer_7/world_setting/missing_required_field",
        }
    )
    canvas = _canvas(modules)
    result = compile_dr_result_v0_3(canvas)
    assert result["valid"] is False
    assert any(item["code"] == "DR_REQUIRED_REGISTRY_REFERENCE_UNRESOLVED" for item in result["errors"])
    assert client.post("/dr/export", json=canvas).status_code == 422


def test_field_reference_recommended_values_share_registry_facts():
    dr = compile_dr_v0_3(_canvas())
    for module, registry in _registries(dr):
        node = next(node for node in module["module_graph"]["nodes"] if node["node_type"] == "field_reference")
        assert node["params"]["recommended_references"] == registry


# P1-A-02 -------------------------------------------------------------------


def _stale_legacy_canvas() -> tuple[dict, dict]:
    modules = _modules()
    basic = _module(modules, "module_basic_identity")
    params = _field_node(basic)["params"]
    _field(basic, "primary_language")["value"] = "ch-ZH"
    _field(basic, "display_alias")["value"] = "CURRENT_ALIAS"
    params["legacy_fields"] = [
        {"field_id": "primary_language", "value": "en", "required": True},
        {"field_id": "display_alias", "value": "STALE_ALIAS", "required": False},
    ]
    params["legacy_data_fields"] = [
        {"field_id": "primary_language", "value": "ch-ZH", "required": True},
        {"field_id": "display_alias", "value": "STALE_DATA_ALIAS", "required": False},
    ]
    return _canvas(modules), params


def _compiled_basic_params(dr: dict) -> dict:
    return _field_node(_compiled_module(dr, "module_basic_identity"))["params"]


def test_current_fields_are_source_of_truth():
    canvas, _params = _stale_legacy_canvas()
    compiled = _compiled_basic_params(compile_dr_v0_3(canvas))
    fields = {field["field_id"]: field["value"] for field in compiled["fields"]}
    assert fields["display_alias"] == "CURRENT_ALIAS"


def test_legacy_fields_generated_from_current_fields():
    canvas, _params = _stale_legacy_canvas()
    compiled = _compiled_basic_params(compile_dr_v0_3(canvas))
    assert compiled["legacy_fields"] == compiled["fields"]
    assert compiled["legacy_fields"] is not compiled["fields"]


def test_legacy_data_fields_generated_from_current_fields():
    canvas, _params = _stale_legacy_canvas()
    compiled = _compiled_basic_params(compile_dr_v0_3(canvas))
    assert compiled["legacy_data_fields"] == compiled["fields"]
    assert compiled["legacy_data_fields"] is not compiled["fields"]


def test_legacy_values_never_override_current():
    canvas, _params = _stale_legacy_canvas()
    compiled = _compiled_basic_params(compile_dr_v0_3(canvas))
    aliases = {
        field["field_id"]: field["value"]
        for field in compiled["legacy_fields"]
    }
    assert aliases["display_alias"] == "CURRENT_ALIAS"
    assert "STALE" not in json.dumps(compiled, ensure_ascii=False)


def test_language_code_ch_zh_normalizes_to_zh_cn():
    canvas, _params = _stale_legacy_canvas()
    dr = compile_dr_v0_3(canvas)
    compiled = _compiled_basic_params(dr)
    for key in ("fields", "legacy_fields", "legacy_data_fields"):
        language = next(field for field in compiled[key] if field["field_id"] == "primary_language")
        assert language["value"] == "zh-CN"
    assert '"ch-ZH"' not in json.dumps(dr, ensure_ascii=False)


def test_compile_does_not_mutate_canvas_fields():
    canvas, _params = _stale_legacy_canvas()
    before = deepcopy(canvas)
    compile_dr_v0_3(canvas)
    assert canvas == before


def test_repeated_compile_does_not_accumulate_legacy_data():
    canvas, _params = _stale_legacy_canvas()
    before = deepcopy(canvas)
    compiled = [_strip_dynamic(compile_dr_v0_3(canvas)) for _ in range(3)]
    assert compiled[0] == compiled[1] == compiled[2]
    params = _compiled_basic_params(compiled[0])
    assert len(params["legacy_fields"]) == len(params["fields"])
    assert len(params["legacy_data_fields"]) == len(params["fields"])
    assert canvas == before


def test_missing_current_required_field_fails_without_legacy_fallback():
    modules = _modules()
    basic = _module(modules, "module_basic_identity")
    params = _field_node(basic)["params"]
    params["fields"] = [field for field in params["fields"] if field["field_id"] != "name"]
    params["legacy_fields"] = [{"field_id": "name", "value": "LEGACY_NAME", "required": True}]
    result = compile_dr_result_v0_3(_canvas(modules))
    assert result["valid"] is False
    assert any(item["code"] == "DR_CURRENT_REQUIRED_FIELD_MISSING" for item in result["errors"])


def test_missing_current_optional_field_warns_and_is_omitted():
    modules = _modules()
    basic = _module(modules, "module_basic_identity")
    params = _field_node(basic)["params"]
    params["fields"] = [field for field in params["fields"] if field["field_id"] != "display_alias"]
    params["legacy_fields"] = [{"field_id": "display_alias", "value": "LEGACY_ALIAS", "required": False}]
    result = compile_dr_result_v0_3(_canvas(modules))
    assert result["valid"] is True
    assert any(item["code"] == "DR_CURRENT_OPTIONAL_FIELD_MISSING" for item in result["warnings"])
    compiled = _compiled_basic_params(result["compiled_dr"])
    assert all(field["field_id"] != "display_alias" for field in compiled["legacy_fields"])


# P1-A-03 -------------------------------------------------------------------


def test_all_six_environment_fields_are_exported():
    canvas, values = _environment_canvas()
    environment = _compiled_module(compile_dr_v0_3(canvas), "environment_setting")
    assert environment["outputs"]["environment_context"]["fields"] == values


def test_all_environment_dr_mappings_resolve():
    canvas, values = _environment_canvas()
    dr = compile_dr_v0_3(canvas)
    environment = _compiled_module(dr, "environment_setting")
    output_fields = environment["outputs"]["environment_context"]["fields"]
    for field in _field_node(environment)["params"]["fields"]:
        field_id = field["field_key"]
        assert field["dr_mapping"] == ENVIRONMENT_MAPPING_PREFIX + field_id
        assert output_fields[field_id] == values[field_id]
    passes = [item for item in dr["audit_report"]["findings"] if item["code"] == "DR_ENVIRONMENT_MAPPING_RESOLVED"]
    assert len(passes) == 6


def test_legacy_environment_mapping_is_normalized_before_mirroring():
    canvas, _values = _environment_canvas()
    environment = _module(canvas["modules"], "environment_setting")
    params = _field_node(environment)["params"]
    for field in params["fields"]:
        field["dr_mapping"] = f"payload.layers.layer_7.modules.environment_setting.fields.{field['field_key']}"
    params["legacy_fields"] = deepcopy(params["fields"])
    params["legacy_data_fields"] = deepcopy(params["fields"])
    before = deepcopy(canvas)
    compiled = _field_node(_compiled_module(compile_dr_v0_3(canvas), "environment_setting"))["params"]
    for key in ("fields", "legacy_fields", "legacy_data_fields"):
        assert all(field["dr_mapping"] == ENVIRONMENT_MAPPING_PREFIX + field["field_key"] for field in compiled[key])
    assert canvas == before


def test_environment_mapping_points_to_authoritative_output():
    canvas, _values = _environment_canvas()
    dr = compile_dr_v0_3(canvas)
    mappings = [field["dr_mapping"] for field in _field_node(_compiled_module(dr, "environment_setting"))["params"]["fields"]]
    assert all(mapping.startswith(ENVIRONMENT_MAPPING_PREFIX) for mapping in mappings)
    assert all("graph_snapshot" not in mapping and "13_layers_snapshot" not in mapping for mapping in mappings)


def test_environment_values_are_not_modified():
    canvas, values = _environment_canvas()
    before = deepcopy(canvas)
    dr = compile_dr_v0_3(canvas)
    compiled = _compiled_module(dr, "environment_setting")["outputs"]["environment_context"]["fields"]
    assert compiled == values
    assert canvas == before


def test_no_duplicate_environment_projection_is_added():
    canvas, _values = _environment_canvas()
    payload = compile_dr_v0_3(canvas)["payload"]
    assert "layers" not in payload
    assert "environment_context" not in payload
    assert "layer_7" not in payload["graph_snapshot"]["layer_outputs"]


# P1-A-04 -------------------------------------------------------------------


def test_root_dr_version_is_source_of_truth():
    dr = compile_dr_v0_3(_canvas())
    assert (dr["dr_version"], dr["dr_schema_version"], dr["protocol_version"]) == ("0.3", "0.3.0", "0.4.0")


def test_internal_version_does_not_override_root():
    dr = compile_dr_v0_3(_canvas())
    dr["resident"]["dr_version"] = "0.1"
    loaded = mock_load_dr_v0_3(dr)
    assert dr["dr_version"] == "0.3"
    assert loaded["dr_version"] == "0.3"


def test_internal_metadata_matches_root_when_required():
    dr = compile_dr_v0_3(_canvas())
    assert dr["resident"]["dr_version"] == dr["dr_version"]
    assert dr["legacy_blueprint"]["resident"]["dr_version"] == dr["dr_version"]
    assert dr["manifest"]["dr_schema_version"] == dr["dr_schema_version"]
    assert dr["compile_info"]["schema_version"] == dr["dr_schema_version"]
    assert dr["compile_info"]["protocol_version"] == dr["protocol_version"]


def test_old_internal_version_remains_readable():
    dr = compile_dr_v0_3(_canvas())
    dr["resident"]["dr_version"] = "0.1"
    dr["legacy_blueprint"]["resident"]["dr_version"] = "0.1"
    assert mock_load_dr_v0_3(dr)["loaded"] is True


def test_protocol_and_dr_versions_are_not_conflated():
    dr = compile_dr_v0_3(_canvas())
    assert dr["protocol_version"] == "0.4.0"
    assert dr["dr_version"] == "0.3"
    assert dr["compile_info"]["compiler_version"] == "0.1.0"
    assert {module["module_version"] for module in dr["payload"]["modules"]} == {"0.1.0"}
    assert dr["payload"]["behavior_policy"]["schema_version"] == "0.1"


# P1-A-05 -------------------------------------------------------------------


def test_identity_source_allows_resident_name():
    canvas, _values = _basic_identity_canvas()
    result = compile_dr_result_v0_3(canvas)
    assert result["valid"] is True
    assert not any(
        item["code"] == "DR_IDENTITY_LITERAL_OUTSIDE_ALLOWED_SCOPE"
        for item in result["errors"]
    )
    assert result["dr_payload"]["audit_policy"][
        "identity_literal_export_gate_revision"
    ] == "stage7_4_12_identity_literal_export_gate_fix_v1"


def test_resident_identity_summary_allows_resident_name():
    canvas, values = _basic_identity_canvas()
    dr = compile_dr_v0_3(canvas)
    assert dr["payload"]["resident_identity"]["name"] == values["name"]
    assert not any(
        item["code"] == "DR_IDENTITY_LITERAL_OUTSIDE_ALLOWED_SCOPE"
        for item in dr["audit_report"]["findings"]
    )


def test_resident_identity_fallback_name_is_used_for_scanning():
    modules = _modules()
    personality = _module(modules, "personality_traits")
    _field(personality, "personality_base")["field_value"] = "林瑄会保持温和。"
    result = compile_dr_result_v0_3(_canvas(modules), resident_name="林瑄")
    assert result["valid"] is False
    assert any(
        item["code"] == "DR_IDENTITY_LITERAL_OUTSIDE_ALLOWED_SCOPE"
        for item in result["errors"]
    )


def test_technical_resident_id_reference_is_allowed():
    canvas, values = _basic_identity_canvas()
    personality = _module(canvas["modules"], "personality_traits")
    _field_node(personality)["params"]["fields"].append(
        {"field_key": "resident_id", "field_value": values["resident_id"], "required": False}
    )
    result = compile_dr_result_v0_3(canvas)
    assert result["valid"] is True
    assert not any(
        item["code"] == "DR_IDENTITY_LITERAL_OUTSIDE_ALLOWED_SCOPE"
        for item in result["errors"]
    )


def test_reference_key_does_not_hide_natural_language_name():
    canvas, _values = _basic_identity_canvas()
    personality = _module(canvas["modules"], "personality_traits")
    _field_node(personality)["params"]["fields"].append(
        {"field_key": "character_reference", "field_value": "林瑄会在表达中保持温和。", "required": False}
    )
    result = compile_dr_result_v0_3(canvas)
    assert any(
        item["code"] == "DR_IDENTITY_LITERAL_OUTSIDE_ALLOWED_SCOPE"
        and "field_id=character_reference" in item["message"]
        for item in result["errors"]
    )


def test_short_technical_codename_does_not_match_unrelated_catalog_enums():
    canvas, _values = _basic_identity_canvas()
    _field(_module(canvas["modules"], "module_basic_identity"), "codename")["value"] = "core"
    result = compile_dr_result_v0_3(canvas)
    assert not any(
        item["code"] == "DR_IDENTITY_LITERAL_OUTSIDE_ALLOWED_SCOPE"
        for item in result["errors"]
    )


def test_short_ascii_identity_is_not_inferred_from_prose_but_is_blocked_in_config_id():
    canvas, _values = _basic_identity_canvas()
    _field(_module(canvas["modules"], "module_basic_identity"), "name")["value"] = "May"
    personality = _module(canvas["modules"], "personality_traits")
    _field(personality, "personality_base")["field_value"] = (
        "The resident may respond after a short pause."
    )
    assert compile_dr_result_v0_3(canvas)["valid"] is True

    personality["config"]["profile_id"] = "may_profile"
    blocked = compile_dr_result_v0_3(canvas)
    assert blocked["valid"] is False
    assert any(
        item["code"] == "DR_IDENTITY_LITERAL_OUTSIDE_ALLOWED_SCOPE"
        and "field_id=config.profile_id" in item["message"]
        for item in blocked["errors"]
    )


def test_generic_value_text_is_not_forced_into_identifier_matching():
    canvas, _values = _basic_identity_canvas()
    _field(_module(canvas["modules"], "module_basic_identity"), "name")[
        "value"
    ] = "May"
    personality = _module(canvas["modules"], "personality_traits")
    _field_node(personality)["params"]["display_copy"] = {
        "value": "May I help with that?"
    }

    assert compile_dr_result_v0_3(canvas)["valid"] is True


def test_ascii_resident_name_does_not_match_protocol_keys_or_enums():
    for resident_name in ("Memory", "Calm"):
        canvas, _values = _basic_identity_canvas()
        identity = _module(
            canvas["modules"],
            "module_basic_identity",
        )
        _field(identity, "name")["value"] = resident_name
        _field(identity, "codename")["value"] = ""
        _field(identity, "export_name")["value"] = ""
        _field(identity, "resident_id")["value"] = "dr_test_0001"

        result = compile_dr_result_v0_3(canvas)

        assert result["valid"] is True
        assert not any(
            item["code"]
            == "DR_IDENTITY_LITERAL_OUTSIDE_ALLOWED_SCOPE"
            for item in result["errors"]
        )


def test_single_character_nickname_is_reported_inside_natural_text():
    canvas, _values = _basic_identity_canvas()
    _field(_module(canvas["modules"], "module_basic_identity"), "display_alias")["value"] = "瑄"
    personality = _module(canvas["modules"], "personality_traits")
    _field(personality, "personality_base")["field_value"] = "小瑄会在表达中保持温和。"
    result = compile_dr_result_v0_3(canvas)
    assert any(
        item["code"] == "DR_IDENTITY_LITERAL_OUTSIDE_ALLOWED_SCOPE"
        and "identity_fields=display_alias" in item["message"]
        for item in result["errors"]
    )


def test_ascii_codename_is_reported_next_to_chinese_text():
    canvas, _values = _basic_identity_canvas()
    personality = _module(canvas["modules"], "personality_traits")
    _field(personality, "personality_base")["field_value"] = "请让linxuan_hum_cn_xian_01保持温和。"
    result = compile_dr_result_v0_3(canvas)
    assert any(
        item["code"] == "DR_IDENTITY_LITERAL_OUTSIDE_ALLOWED_SCOPE"
        and "codename" in item["message"]
        for item in result["errors"]
    )


def test_non_identity_natural_language_name_is_reported():
    canvas, _text = _identity_warning_canvas()
    result = compile_dr_result_v0_3(canvas)
    finding = next(
        item
        for item in result["errors"]
        if item["code"] == "DR_IDENTITY_LITERAL_OUTSIDE_ALLOWED_SCOPE"
    )
    assert result["valid"] is False
    assert all(token in finding["message"] for token in ("layer_id=layer_2", "module_id=personality_traits", "node_id=", "field_id=personality_base", "text_type=non_identity_module_text"))
    response = client.post("/dr/export", json=canvas)
    assert response.status_code == 422
    assert any(
        item["code"] == "DR_IDENTITY_LITERAL_OUTSIDE_ALLOWED_SCOPE"
        for item in response.json()["detail"]["errors"]
    )


def test_non_identity_module_description_name_is_reported():
    canvas, _values = _basic_identity_canvas()
    _module(canvas["modules"], "personality_traits")["description"] = "林瑄的非基础身份模块说明。"
    result = compile_dr_result_v0_3(canvas)
    finding = next(
        item
        for item in result["errors"]
        if item["code"] == "DR_IDENTITY_LITERAL_OUTSIDE_ALLOWED_SCOPE"
        and "field_id=description" in item["message"]
    )
    assert "node_id=module" in finding["message"]
    assert "text_type=non_identity_module_text" in finding["message"]


def test_name_scanner_covers_required_text_regions():
    canvas, _values = _basic_identity_canvas()
    personality = _module(canvas["modules"], "personality_traits")
    node = _field_node(personality)
    node["params"].update(
        {
            "memory_seeds": ["林瑄记得这段种子内容。"],
            "dialogue_rules": ["林瑄在此对话规则中被直接命名。"],
            "visual_hints": ["画面提示直接写林瑄。"],
            "behavior_policy": {"text": "行为策略对象直接写林瑄。"},
        }
    )
    personality["input_schema"] = [{"key": "template_copy", "default": "模板默认值包含林瑄。"}]
    personality["config"]["template_defaults"] = ["模板容器默认值也包含林瑄。"]
    language = _module(canvas["modules"], "language_habit")
    behavior_node = next(
        item
        for item in language["module_graph"]["nodes"]
        if isinstance((item.get("params") or {}).get("checkbox_config"), dict)
    )
    behavior_node["params"]["checkbox_config"]["custom_text"] = "行为策略直接写林瑄。"

    result = compile_dr_result_v0_3(canvas)
    text_types = {
        marker
        for item in result["errors"]
        if item["code"] == "DR_IDENTITY_LITERAL_OUTSIDE_ALLOWED_SCOPE"
        for marker in ("memory_seed", "dialogue_rule", "visual_hint", "template_default", "behavior_policy")
        if f"text_type={marker}" in item["message"]
    }
    assert text_types == {"memory_seed", "dialogue_rule", "visual_hint", "template_default", "behavior_policy"}


def test_identity_gate_scans_config_ids_and_nested_few_shots():
    canvas, values = _basic_identity_canvas()
    _field(
        _module(canvas["modules"], "module_basic_identity"),
        "export_name",
    )["value"] = ""
    personality = _module(canvas["modules"], "personality_traits")
    personality["config"]["profile_id"] = "linxuan_profile"
    personality["config"]["profiles"] = {
        f"{values['codename']}_profile": {"enabled": True}
    }
    field_node = _field_node(personality)
    field_node["params"]["selected_options"] = [values["codename"]]
    field_node["params"]["few_shot_examples"] = [
        {"assistant": "林瑄会先听完，再温和回应。"}
    ]

    result = compile_dr_result_v0_3(canvas)
    assert result["valid"] is False
    findings = [
        item
        for item in result["errors"]
        if item["code"] == "DR_IDENTITY_LITERAL_OUTSIDE_ALLOWED_SCOPE"
    ]
    assert any(
        "field_id=config.profile_id" in item["message"]
        and "identity_fields=pinyin" in item["message"]
        for item in findings
    )
    assert any(".__key__" in item["message"] for item in findings)
    assert any("selected_options" in item["message"] for item in findings)
    assert any("few_shot_examples" in item["message"] for item in findings)
    assert (
        result["metadata"]["v03_audit_report"]["summary"][
            "identity_literal_export_gate_check_fail"
        ]
        >= 2
    )


def test_identity_gate_scans_raw_reference_strings():
    canvas, values = _basic_identity_canvas()
    personality = _module(canvas["modules"], "personality_traits")
    _field_node(personality)["params"]["references"] = [
        f"{values['codename']}_profile"
    ]

    result = compile_dr_result_v0_3(canvas)

    assert result["valid"] is False
    assert any(
        item["code"] == "DR_IDENTITY_LITERAL_OUTSIDE_ALLOWED_SCOPE"
        and "references[0]" in item["message"]
        for item in result["errors"]
    )


def test_exact_resident_id_in_reference_value_is_allowed():
    canvas, values = _basic_identity_canvas()
    personality = _module(canvas["modules"], "personality_traits")
    _field_node(personality)["params"]["references"] = [
        {
            "key": "resident_id",
            "value": values["resident_id"],
        }
    ]

    result = compile_dr_result_v0_3(canvas)

    assert result["valid"] is True
    assert not any(
        item["code"] == "DR_IDENTITY_LITERAL_OUTSIDE_ALLOWED_SCOPE"
        for item in result["errors"]
    )


def test_identity_gate_scans_projection_only_identity_literals(monkeypatch):
    canvas, _values = _basic_identity_canvas()
    original_builder = (
        dr_compiler_module.build_runtime_dialogue_projection
    )

    def projection_with_illegal_literal(*args, **kwargs):
        projection = original_builder(*args, **kwargs)
        assert projection is not None
        projection["few_shot_examples"] = [
            {
                "user": "你好",
                "assistant": "林瑄会先听完，再温和回应。",
            }
        ]
        return projection

    monkeypatch.setattr(
        dr_compiler_module,
        "build_runtime_dialogue_projection",
        projection_with_illegal_literal,
    )
    result = compile_dr_result_v0_3(canvas)

    assert result["valid"] is False
    assert any(
        item["code"] == "DR_IDENTITY_LITERAL_OUTSIDE_ALLOWED_SCOPE"
        and item["path"].startswith(
            "payload.runtime_dialogue_projection."
        )
        for item in result["errors"]
    )


def test_identity_gate_scans_root_visual_projection_only_literals(
    monkeypatch,
):
    canvas, _values = _basic_identity_canvas()
    original_builder = (
        dr_compiler_module.build_visual_expression_mapping
    )

    def visual_projection_with_illegal_literal(*args, **kwargs):
        projection, diagnostics = original_builder(*args, **kwargs)
        projection["state_selection_policy"][
            "selection_rules"
        ][0] = "林瑄会直接选择本轮表达状态。"
        return projection, diagnostics

    monkeypatch.setattr(
        dr_compiler_module,
        "build_visual_expression_mapping",
        visual_projection_with_illegal_literal,
    )
    result = compile_dr_result_v0_3(canvas)

    assert result["valid"] is False
    assert any(
        item["code"] == "DR_IDENTITY_LITERAL_OUTSIDE_ALLOWED_SCOPE"
        and item["path"].startswith(
            "visual_expression_mapping."
        )
        for item in result["errors"]
    )


def test_fixed_resident_id_is_allowed_only_as_an_exact_resident_scoped_reference():
    canvas, values = _basic_identity_canvas()
    personality = _module(canvas["modules"], "personality_traits")
    _field_node(personality)["params"]["fields"].extend(
        [
            {
                "field_key": "resident_id",
                "field_value": values["resident_id"],
                "required": False,
            },
            {
                "field_key": "profile_id",
                "field_value": f"profile_{values['resident_id']}",
                "required": False,
            },
        ]
    )

    result = compile_dr_result_v0_3(canvas)
    findings = [
        item
        for item in result["errors"]
        if item["code"] == "DR_IDENTITY_LITERAL_OUTSIDE_ALLOWED_SCOPE"
    ]
    assert result["valid"] is False
    assert not any("field_id=resident_id," in item["message"] for item in findings)
    assert any("field_id=profile_id" in item["message"] for item in findings)


def test_identity_gate_scans_node_outputs_without_duplicate_mirror_findings():
    canvas, _values = _basic_identity_canvas()
    personality = _module(canvas["modules"], "personality_traits")
    field_node = _field_node(personality)
    identity_text = "林瑄会在表达中保持温和和克制。"
    _field(personality, "personality_base")["field_value"] = identity_text
    field_node["outputs"] = {"rule": identity_text}
    personality.setdefault("outputs", {})["identity_echo"] = identity_text

    result = compile_dr_result_v0_3(canvas)
    findings = [
        item
        for item in result["errors"]
        if item["code"] == "DR_IDENTITY_LITERAL_OUTSIDE_ALLOWED_SCOPE"
    ]
    assert result["valid"] is False
    assert len(findings) == 1
    assert "field_id=personality_base" in findings[0]["message"]

    clean_canvas, _clean_values = _basic_identity_canvas()
    clean_personality = _module(clean_canvas["modules"], "personality_traits")
    _field_node(clean_personality)["outputs"] = {
        "rule": "林瑄只存在于节点输出。"
    }
    output_only = compile_dr_result_v0_3(clean_canvas)
    assert any(
        item["code"] == "DR_IDENTITY_LITERAL_OUTSIDE_ALLOWED_SCOPE"
        and "field_id=outputs.rule" in item["message"]
        for item in output_only["errors"]
    )


def test_template_default_name_is_reported_once():
    canvas, _values = _basic_identity_canvas()
    personality = _module(canvas["modules"], "personality_traits")
    personality["input_schema"] = [{"key": "template_copy", "default": "模板默认值包含林瑄。"}]
    result = compile_dr_result_v0_3(canvas)
    findings = [
        item
        for item in result["errors"]
        if item["code"] == "DR_IDENTITY_LITERAL_OUTSIDE_ALLOWED_SCOPE"
        and "text_type=template_default" in item["message"]
    ]
    assert len(findings) == 1


def test_validator_does_not_rewrite_resident_text():
    canvas, text = _identity_warning_canvas()
    before = deepcopy(canvas)
    dr = compile_dr_v0_3(canvas)
    compiled_field = _field(_compiled_module(dr, "personality_traits"), "personality_base")
    value = compiled_field.get("field_value") if "field_value" in compiled_field else compiled_field.get("value")
    assert value == text
    assert canvas == before


def test_generic_template_cannot_embed_resident_name():
    canvas, _text = _identity_warning_canvas(generic=True)
    result = compile_dr_result_v0_3(canvas)
    assert result["valid"] is False
    assert any(
        item["code"] == "DR_IDENTITY_LITERAL_OUTSIDE_ALLOWED_SCOPE"
        for item in result["errors"]
    )
    assert client.post("/dr/export", json=canvas).status_code == 422
