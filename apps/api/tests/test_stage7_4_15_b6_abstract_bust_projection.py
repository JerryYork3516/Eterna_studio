"""Stage 7.4.15-B6 AbstractBustBlueprint DR projection contract."""

from __future__ import annotations

import json
from copy import deepcopy

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.dr.v3.dr_v0_3_schema import (
    DRDocumentV03,
    STAGE7_4_REQUIRED_CAPABILITIES_V0_3,
)
from app.main import app
from app.registry.module_catalog import (
    PARTICLE_AVATAR_MODULE_ID,
    PARTICLE_AVATAR_NODE_IDS,
    get_module_catalog,
)
from app.services.abstract_bust_blueprint import (
    default_abstract_bust_blueprint_dict,
    normalize_abstract_bust_blueprint,
)
from app.services.dr_compiler import (
    compile_dr_result_v0_3,
    compile_dr_v0_3,
)


client = TestClient(app)
BLUEPRINT_KEY = "abstract_bust_blueprint"


def _modules() -> list[dict]:
    return [
        module.model_dump(mode="json")
        for module in get_module_catalog()
    ]


def _canvas(modules: list[dict]) -> dict:
    return {
        "workflow": {
            "name": "Stage 7.4.15-B6 Abstract bust projection",
            "nodes": [
                {"node_id": f"layer_{index}"}
                for index in range(1, 14)
            ],
        },
        "modules": modules,
    }


def _particle(modules: list[dict]) -> dict:
    return next(
        module
        for module in modules
        if module["module_id"] == PARTICLE_AVATAR_MODULE_ID
    )


def _config_node(module: dict) -> dict:
    return next(
        node
        for node in module["module_graph"]["nodes"]
        if node.get("node_id")
        == PARTICLE_AVATAR_NODE_IDS["config_input"]
    )


def _blueprint_fields(module: dict) -> list[dict]:
    return [
        field
        for field in _config_node(module)["params"]["fields"]
        if field.get("field_key") == BLUEPRINT_KEY
    ]


def _blueprint_field(module: dict) -> dict:
    fields = _blueprint_fields(module)
    assert len(fields) == 1
    return fields[0]


def _set_blueprint(modules: list[dict], value) -> None:
    field = _blueprint_field(_particle(modules))
    key = "value" if "value" in field else "field_value"
    field[key] = deepcopy(value)


def _compiled_particle(dr: dict) -> dict:
    return _particle(dr["payload"]["modules"])


def _result(modules: list[dict]) -> dict:
    return compile_dr_result_v0_3(_canvas(modules))


def _error_codes(result: dict) -> set[str]:
    return {error["code"] for error in result["errors"]}


def test_valid_blueprint_materializes_module_config_and_read_only_projection():
    result = _result(_modules())
    assert result["valid"] is True, result["errors"]
    dr = result["compiled_dr"]
    particle = _compiled_particle(dr)
    field_value = _blueprint_field(particle)["field_value"]
    module_value = particle["config"][BLUEPRINT_KEY]
    root_value = dr["payload"][BLUEPRINT_KEY]

    assert field_value == module_value == root_value
    assert root_value == default_abstract_bust_blueprint_dict()
    assert root_value is not module_value
    assert module_value is not field_value
    assert (
        _particle(dr["modules"])["config"][BLUEPRINT_KEY]
        == root_value
    )
    assert dr["visual_expression_mapping"]["abstract_bust_mapping"] == {
        "status": "reserved"
    }


def test_optional_defaults_and_numeric_bounds_come_from_b1_normalizer():
    modules = _modules()
    blueprint = default_abstract_bust_blueprint_dict()
    blueprint.pop("age_tendency")
    blueprint.pop("face")
    blueprint.pop("contour")
    blueprint["seed"] = 0
    blueprint["head"]["width"] = -100
    blueprint["shoulders"]["width"] = 100
    expected = normalize_abstract_bust_blueprint(blueprint)
    _set_blueprint(modules, blueprint)

    result = _result(modules)
    assert result["valid"] is True, result["errors"]
    dr = result["compiled_dr"]
    assert dr["payload"][BLUEPRINT_KEY] == expected
    assert (
        _compiled_particle(dr)["config"][BLUEPRINT_KEY]
        == expected
    )
    assert _blueprint_field(_compiled_particle(dr))["field_value"] == expected


@pytest.mark.parametrize(
    ("mutation", "expected_code"),
    (
        (
            lambda value: value.update(
                {"generator_version": "abstract_bust_v9"}
            ),
            "DR_ABSTRACT_BUST_GENERATOR_VERSION_UNKNOWN",
        ),
        (
            lambda value: value.update({"presentation": "unknown"}),
            "DR_ABSTRACT_BUST_BLUEPRINT_INVALID",
        ),
        (
            lambda value: value.update({"studio_private": True}),
            "DR_ABSTRACT_BUST_BLUEPRINT_UNKNOWN_FIELD",
        ),
        (
            lambda value: value["head"].update({"width": "wide"}),
            "DR_ABSTRACT_BUST_BLUEPRINT_TYPE_INVALID",
        ),
        (
            lambda value: value["head"].update({"width": float("nan")}),
            "DR_ABSTRACT_BUST_BLUEPRINT_NON_FINITE",
        ),
        (
            lambda value: value["head"].update({"width": float("inf")}),
            "DR_ABSTRACT_BUST_BLUEPRINT_NON_FINITE",
        ),
        (
            lambda value: value["face"]["eyes"].pop("spacing"),
            "DR_ABSTRACT_BUST_BLUEPRINT_INVALID",
        ),
    ),
)
def test_invalid_blueprint_blocks_compile_without_partial_projection(
    mutation,
    expected_code: str,
):
    modules = _modules()
    blueprint = default_abstract_bust_blueprint_dict()
    mutation(blueprint)
    _set_blueprint(modules, blueprint)

    result = _result(modules)
    assert result["valid"] is False
    assert result["compiled_dr"] is None
    assert expected_code in _error_codes(result)
    assert BLUEPRINT_KEY not in result["dr_payload"]
    stored = _blueprint_field(_particle(result["dr_payload"]["modules"]))
    assert (
        stored.get("value")
        if "value" in stored
        else stored.get("field_value")
    ) == blueprint
    assert all(
        "Traceback" not in error["message"]
        and json.dumps(blueprint, default=str) not in error["message"]
        for error in result["errors"]
    )


@pytest.mark.parametrize("raw_value", ([], "not-json"))
def test_invalid_root_or_json_uses_type_error(raw_value):
    modules = _modules()
    _set_blueprint(modules, raw_value)
    result = _result(modules)
    assert result["valid"] is False
    assert result["compiled_dr"] is None
    assert (
        "DR_ABSTRACT_BUST_BLUEPRINT_TYPE_INVALID"
        in _error_codes(result)
    )


def test_duplicate_particle_module_has_specific_failure():
    modules = _modules()
    modules.append(deepcopy(_particle(modules)))
    result = _result(modules)
    assert result["valid"] is False
    assert result["compiled_dr"] is None
    assert "DR_ABSTRACT_BUST_MODULE_DUPLICATE" in _error_codes(result)
    assert BLUEPRINT_KEY not in result["dr_payload"]


def test_duplicate_config_node_or_blueprint_field_blocks_projection():
    modules = _modules()
    particle = _particle(modules)
    particle["module_graph"]["nodes"].append(
        deepcopy(_config_node(particle))
    )
    result = _result(modules)
    assert result["valid"] is False
    assert "DR_ABSTRACT_BUST_BLUEPRINT_INVALID" in _error_codes(result)

    modules = _modules()
    fields = _config_node(_particle(modules))["params"]["fields"]
    fields.append(deepcopy(_blueprint_field(_particle(modules))))
    result = _result(modules)
    assert result["valid"] is False
    assert "DR_ABSTRACT_BUST_BLUEPRINT_INVALID" in _error_codes(result)


def test_missing_module_or_saved_blueprint_remains_legacy_compatible():
    without_particle = [
        module
        for module in _modules()
        if module["module_id"] != PARTICLE_AVATAR_MODULE_ID
    ]
    result = _result(without_particle)
    assert result["valid"] is True, result["errors"]
    assert BLUEPRINT_KEY not in result["compiled_dr"]["payload"]

    modules = _modules()
    fields = _config_node(_particle(modules))["params"]["fields"]
    fields[:] = [
        field
        for field in fields
        if field.get("field_key") != BLUEPRINT_KEY
    ]
    result = _result(modules)
    assert result["valid"] is True, result["errors"]
    assert BLUEPRINT_KEY not in result["compiled_dr"]["payload"]
    assert BLUEPRINT_KEY not in _compiled_particle(
        result["compiled_dr"]
    )["config"]


def test_saved_field_overwrites_stale_module_config_on_recompile():
    modules = _modules()
    particle = _particle(modules)
    expected = default_abstract_bust_blueprint_dict()
    expected["hair"]["style"] = "long"
    stale = default_abstract_bust_blueprint_dict()
    stale["hair"]["style"] = "none"
    _set_blueprint(modules, expected)
    particle.setdefault("config", {})[BLUEPRINT_KEY] = stale

    first = compile_dr_v0_3(_canvas(modules))
    second = compile_dr_v0_3(
        _canvas(deepcopy(first["payload"]["modules"]))
    )
    normalized = normalize_abstract_bust_blueprint(expected)
    assert first["payload"][BLUEPRINT_KEY] == normalized
    assert second["payload"][BLUEPRINT_KEY] == normalized
    assert (
        _compiled_particle(second)["config"][BLUEPRINT_KEY]
        == normalized
    )


def test_formal_schema_rejects_root_and_module_config_drift():
    dr = compile_dr_v0_3(_canvas(_modules()))
    tampered = deepcopy(dr)
    tampered["payload"][BLUEPRINT_KEY]["head"]["width"] += 0.01
    with pytest.raises(ValidationError, match="read-only projection"):
        DRDocumentV03.model_validate(tampered)


def test_projection_contains_only_b1_fields_and_no_studio_runtime_state():
    dr = compile_dr_v0_3(_canvas(_modules()))
    projection = dr["payload"][BLUEPRINT_KEY]
    assert set(projection) == {
        "generator_version",
        "presentation",
        "age_tendency",
        "seed",
        "head",
        "face",
        "neck",
        "shoulders",
        "torso",
        "hair",
        "contour",
    }
    serialized = json.dumps(projection, ensure_ascii=False)
    for forbidden in (
        "visualAssetBinding",
        "studioMetadata",
        "blueprint_digest",
        "positions",
        "regions",
        "anchors",
        "camera",
        "three",
        "webgl",
        "updated_at",
        "bound_at",
    ):
        assert forbidden not in serialized


def test_compile_export_gate_and_frozen_contract_remain_unchanged():
    modules = _modules()
    blueprint = default_abstract_bust_blueprint_dict()
    blueprint["presentation"] = "unsupported"
    _set_blueprint(modules, blueprint)
    canvas = _canvas(modules)

    compile_response = client.post("/dr/compile", json=canvas)
    export_response = client.post("/dr/export", json=canvas)
    assert compile_response.status_code == 200
    assert compile_response.json()["valid"] is False
    assert compile_response.json()["compiled_dr"] is None
    assert export_response.status_code == 422

    valid = compile_dr_v0_3(_canvas(_modules()))
    assert valid["dr_version"] == "0.3"
    assert valid["dr_schema_version"] == "0.3.0"
    assert valid["protocol_version"] == "0.4.0"
    assert valid["schema_version"] == "0.4.0"
    assert valid["manifest"]["required_capabilities"] == list(
        STAGE7_4_REQUIRED_CAPABILITIES_V0_3
    )
    assert valid["modules"] == valid["payload"]["modules"]
