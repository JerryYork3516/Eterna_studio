from __future__ import annotations

import hashlib
import json
import subprocess
from copy import deepcopy
from pathlib import Path

import pytest

from app.registry.module_catalog import (
    PARTICLE_AVATAR_MODULE_ID,
    get_module_catalog,
)
from app.services.abstract_bust_blueprint import (
    ABSTRACT_BUST_GENERATOR_VERSION,
    AbstractBustAgeTendency,
    AbstractBustBlueprintValidationError,
    AbstractBustHairStyle,
    AbstractBustPresentation,
    default_abstract_bust_blueprint_dict,
    normalize_abstract_bust_blueprint,
    parse_abstract_bust_blueprint,
)
from app.services.dr_compiler import compile_dr_v0_3


ROOT = Path(__file__).resolve().parents[3]
CONTRACT_ROOT = (
    ROOT
    / "packages"
    / "shared-schema"
    / "contracts"
    / "abstract_bust_v0_1"
)
FIXTURE_ROOT = CONTRACT_ROOT / "fixtures"
VALID_FIXTURE_NAMES = (
    "default.json",
    "neutral.json",
    "feminine.json",
    "masculine.json",
    "hair_none.json",
    "hair_short.json",
    "hair_medium.json",
    "hair_long.json",
    "hair_tied.json",
)


def _read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _fixture(name: str = "default.json"):
    return _read_json(FIXTURE_ROOT / name)


def _assert_error(value, code: str):
    with pytest.raises(AbstractBustBlueprintValidationError) as captured:
        normalize_abstract_bust_blueprint(value)
    assert captured.value.code == code


def test_upstream_snapshot_metadata_and_hashes_are_complete():
    snapshot = _read_json(CONTRACT_ROOT / "upstream_snapshot.json")
    assert snapshot["upstream_project"] == "Eterna_aftelle"
    assert (
        snapshot["upstream_commit"]
        == "c81b801b5ab3b53ed4733ac92add5ffaffd11395"
    )
    assert snapshot["generator_version"] == ABSTRACT_BUST_GENERATOR_VERSION
    assert set(snapshot["files"]) == {
        "abstract_bust_blueprint_v0_1.md",
        "abstract_bust_blueprint_v0_1.schema.json",
        *(f"fixtures/{name}" for name in VALID_FIXTURE_NAMES),
        "fixtures/golden_manifest.json",
    }
    for relative_path, metadata in snapshot["files"].items():
        content = (CONTRACT_ROOT / relative_path).read_bytes()
        assert hashlib.sha256(content).hexdigest() == metadata["sha256"]


def test_golden_manifest_declares_the_frozen_integrity_contract():
    manifest = _read_json(FIXTURE_ROOT / "golden_manifest.json")
    assert manifest["algorithm"] == "fnv1a64_float32_le_xyz_index_order"
    assert manifest["particle_count"] == 12000
    assert manifest["generator_version"] == ABSTRACT_BUST_GENERATOR_VERSION
    assert set(manifest["fixtures"]) == set(VALID_FIXTURE_NAMES)
    assert all(
        len(digest) == 16
        and digest == digest.lower()
        and all(character in "0123456789abcdef" for character in digest)
        for digest in manifest["fixtures"].values()
    )


def test_protocol_freezes_head_and_shoulders_width_as_half_dimensions():
    protocol = (
        CONTRACT_ROOT / "abstract_bust_blueprint_v0_1.md"
    ).read_text(encoding="utf-8")
    assert "标准头宽 | `2 × head.width = 0.5300`" in protocol
    assert "标准肩宽 | `2 × shoulders.width = 1.2000`" in protocol
    assert (
        "`head.width`、`head.height`、`neck.width`、`shoulders.width`、"
        "`torso.width` 和 `torso.thickness` 是中心线到外轮廓的半径/半尺寸"
        in protocol
    )


def test_default_fixture_parses_and_normalizes_without_drift():
    default = _fixture()
    assert normalize_abstract_bust_blueprint(default) == default
    assert default_abstract_bust_blueprint_dict() == default
    assert parse_abstract_bust_blueprint(default).model_dump(mode="json") == default


@pytest.mark.parametrize("fixture_name", VALID_FIXTURE_NAMES)
def test_all_nine_upstream_fixtures_parse(fixture_name: str):
    normalized = normalize_abstract_bust_blueprint(_fixture(fixture_name))
    assert normalized["generator_version"] == ABSTRACT_BUST_GENERATOR_VERSION
    assert set(normalized) == {
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


def test_enum_types_match_the_frozen_schema():
    schema = _read_json(
        CONTRACT_ROOT / "abstract_bust_blueprint_v0_1.schema.json"
    )
    assert {value.value for value in AbstractBustPresentation} == set(
        schema["properties"]["presentation"]["enum"]
    )
    assert {value.value for value in AbstractBustAgeTendency} == set(
        schema["properties"]["age_tendency"]["enum"]
    )
    assert {value.value for value in AbstractBustHairStyle} == set(
        schema["$defs"]["hair"]["properties"]["style"]["enum"]
    )


def test_unknown_generator_version_is_rejected():
    value = _fixture()
    value["generator_version"] = "abstract_bust_v9"
    _assert_error(value, "unknown_generator_version")


@pytest.mark.parametrize(
    ("path", "value"),
    (
        (("presentation",), "cinematic"),
        (("age_tendency",), "ancient"),
        (("hair", "style"), "braided"),
    ),
)
def test_unknown_enums_are_rejected(path: tuple[str, ...], value):
    blueprint = _fixture()
    target = blueprint
    for component in path[:-1]:
        target = target[component]
    target[path[-1]] = value
    _assert_error(blueprint, "unknown_enum")


@pytest.mark.parametrize(
    "mutate",
    (
        lambda value: value.update({"private_shape": 1}),
        lambda value: value["head"].update({"full_width": 0.53}),
        lambda value: value["face"]["eyes"].update({"iris_detail": 0.5}),
    ),
)
def test_unknown_fields_are_rejected_at_every_depth(mutate):
    blueprint = _fixture()
    mutate(blueprint)
    _assert_error(blueprint, "unknown_field")


@pytest.mark.parametrize(
    "mutate",
    (
        lambda value: value.update({"seed": 1.5}),
        lambda value: value.update({"seed": True}),
        lambda value: value["head"].update({"width": "0.265"}),
        lambda value: value["face"].update({"eyes": []}),
    ),
)
def test_wrong_field_types_are_rejected(mutate):
    blueprint = _fixture()
    mutate(blueprint)
    _assert_error(blueprint, "invalid_type")


@pytest.mark.parametrize("invalid_number", (float("nan"), float("inf"), float("-inf")))
def test_non_finite_numbers_are_rejected(invalid_number: float):
    blueprint = _fixture()
    blueprint["head"]["width"] = invalid_number
    _assert_error(blueprint, "non_finite_number")


@pytest.mark.parametrize(
    "mutate",
    (
        lambda value: value.pop("head"),
        lambda value: value["head"].pop("width"),
        lambda value: value["face"]["eyes"].pop("spacing"),
    ),
)
def test_missing_required_fields_are_rejected(mutate):
    blueprint = _fixture()
    mutate(blueprint)
    _assert_error(blueprint, "missing_required_field")


def test_only_protocol_optional_top_level_fields_receive_defaults():
    blueprint = _fixture()
    del blueprint["age_tendency"]
    del blueprint["face"]
    del blueprint["contour"]
    assert normalize_abstract_bust_blueprint(blueprint) == _fixture()


def test_finite_out_of_range_numbers_are_clamped_from_schema():
    schema = _read_json(
        CONTRACT_ROOT / "abstract_bust_blueprint_v0_1.schema.json"
    )
    blueprint = _fixture()
    blueprint["head"]["width"] = -100
    blueprint["shoulders"]["width"] = 100
    blueprint["face"]["mouth"]["vertical_position"] = 100
    blueprint["contour"]["asymmetry"] = -1
    normalized = normalize_abstract_bust_blueprint(blueprint)
    assert normalized["head"]["width"] == schema["$defs"]["head"]["properties"]["width"]["minimum"]
    assert normalized["shoulders"]["width"] == schema["$defs"]["shoulders"]["properties"]["width"]["maximum"]
    assert normalized["face"]["mouth"]["vertical_position"] == schema["$defs"]["mouth"]["properties"]["vertical_position"]["maximum"]
    assert normalized["contour"]["asymmetry"] == schema["$defs"]["contour"]["properties"]["asymmetry"]["minimum"]


@pytest.mark.parametrize(
    ("seed", "bound"),
    (
        (0, "minimum"),
        (999999999999, "maximum"),
    ),
)
def test_seed_is_clamped_from_schema(seed: int, bound: str):
    schema = _read_json(
        CONTRACT_ROOT / "abstract_bust_blueprint_v0_1.schema.json"
    )
    blueprint = _fixture()
    blueprint["seed"] = seed
    assert normalize_abstract_bust_blueprint(blueprint)["seed"] == (
        schema["properties"]["seed"][bound]
    )


def test_normalized_output_stays_nested_and_has_no_flat_bust_fields():
    normalized = normalize_abstract_bust_blueprint(_fixture("hair_long.json"))
    serialized_keys = set()

    def collect_keys(value):
        if isinstance(value, dict):
            for key, child in value.items():
                serialized_keys.add(key)
                collect_keys(child)
        elif isinstance(value, list):
            for child in value:
                collect_keys(child)

    collect_keys(normalized)
    assert {
        "head_width",
        "head_height",
        "shoulders_width",
        "hair_style",
        "AbstractBustTuning",
    }.isdisjoint(serialized_keys)
    assert isinstance(normalized["face"]["eyes"], dict)
    assert isinstance(normalized["face"]["jaw"], dict)


def test_frontend_and_backend_normalize_all_fixtures_identically():
    runner = (
        ROOT
        / "apps"
        / "web"
        / "tests"
        / "helpers"
        / "abstract-bust-parity-runner.mjs"
    )
    fixture_paths = [FIXTURE_ROOT / name for name in VALID_FIXTURE_NAMES]
    completed = subprocess.run(
        [
            "node",
            "--experimental-strip-types",
            str(runner),
            *(str(path) for path in fixture_paths),
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    frontend = json.loads(completed.stdout)
    backend = {
        path.name: normalize_abstract_bust_blueprint(_read_json(path))
        for path in fixture_paths
    }
    assert frontend == backend


def test_frontend_and_backend_share_optional_clamp_and_rejection_rules():
    runner = (
        ROOT
        / "apps"
        / "web"
        / "tests"
        / "helpers"
        / "abstract-bust-parity-runner.mjs"
    )
    optional = _fixture()
    optional.pop("age_tendency")
    optional.pop("face")
    optional.pop("contour")
    clamped = _fixture()
    clamped["seed"] = 0
    clamped["head"]["width"] = -100
    clamped["shoulders"]["width"] = 100
    unknown_version = _fixture()
    unknown_version["generator_version"] = "abstract_bust_v9"
    unknown_enum = _fixture()
    unknown_enum["hair"]["style"] = "braided"
    unknown_field = _fixture()
    unknown_field["face"]["eyes"]["iris_detail"] = 0.5
    invalid_type = _fixture()
    invalid_type["head"]["width"] = "0.265"
    missing_required = _fixture()
    missing_required["face"]["eyes"].pop("spacing")
    cases = {
        "optional": optional,
        "clamped": clamped,
        "unknown_version": unknown_version,
        "unknown_enum": unknown_enum,
        "unknown_field": unknown_field,
        "invalid_type": invalid_type,
        "missing_required": missing_required,
    }

    frontend = json.loads(
        subprocess.run(
            [
                "node",
                "--experimental-strip-types",
                str(runner),
                "--stdin",
            ],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
            input=json.dumps(cases),
        ).stdout
    )

    backend = {}
    for name, value in cases.items():
        try:
            backend[name] = {
                "ok": True,
                "value": normalize_abstract_bust_blueprint(value),
            }
        except AbstractBustBlueprintValidationError as error:
            backend[name] = {
                "ok": False,
                "code": error.code,
                "path": error.path,
            }
    assert frontend == backend


def test_layer10_blueprint_stays_in_authoritative_payload_modules_only():
    modules = [module.model_dump(mode="json") for module in get_module_catalog()]
    dr = compile_dr_v0_3(
        {
            "workflow": {
                "name": "Stage 7.4.15 B1 Abstract Bust contract",
                "nodes": [
                    {"node_id": f"layer_{index}"} for index in range(1, 14)
                ],
            },
            "modules": modules,
        }
    )
    particle = next(
        module
        for module in dr["payload"]["modules"]
        if module["module_id"] == PARTICLE_AVATAR_MODULE_ID
    )
    config_input = next(
        node
        for node in particle["module_graph"]["nodes"]
        if node.get("params", {}).get("mode") == "generic_fields"
    )
    fields = {
        field["field_key"]: field for field in config_input["params"]["fields"]
    }
    assert (
        fields["abstract_bust_blueprint"]["field_value"]
        == default_abstract_bust_blueprint_dict()
    )
    assert "abstract_bust_blueprint" not in dr["payload"]
    assert "abstract_bust_blueprint" not in particle["outputs"]["particle_mapping_config"]
    assert dr["visual_expression_mapping"]["abstract_bust_mapping"] == {
        "status": "reserved"
    }
