from __future__ import annotations

import json
import subprocess
from copy import deepcopy
from pathlib import Path

import pytest

from app.services.abstract_bust_blueprint import (
    AbstractBustBlueprintValidationError,
)
from app.services.abstract_bust_blueprint_router import (
    normalize_abstract_bust_blueprint_by_version,
)
from app.services.abstract_bust_blueprint_v2 import (
    ABSTRACT_BUST_V2_GENERATOR_VERSION,
    AbstractBustAgeTendencyV2,
    AbstractBustBlueprintV2ValidationError,
    AbstractBustHairStyleV2,
    AbstractBustPresentationV2,
    apply_abstract_bust_preset_v2,
    default_abstract_bust_blueprint_v2_dict,
    load_abstract_bust_preset_fixture_v2,
    normalize_abstract_bust_blueprint_v2,
    parse_abstract_bust_blueprint_v2,
)


ROOT = Path(__file__).resolve().parents[3]
CONTRACT_ROOT = (
    ROOT
    / "packages"
    / "shared-schema"
    / "contracts"
    / "abstract_bust_v0_2"
)
FIXTURE_ROOT = CONTRACT_ROOT / "fixtures"
FIXTURE_NAMES = (
    "default.json",
    "neutral.json",
    "feminine.json",
    "masculine.json",
    "youthful.json",
    "balanced.json",
    "mature.json",
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


def _assert_error(value, code: str, path: str | None = None):
    with pytest.raises(AbstractBustBlueprintV2ValidationError) as captured:
        normalize_abstract_bust_blueprint_v2(value)
    assert captured.value.code == code
    if path is not None:
        assert captured.value.path == path


def test_v2_default_and_all_twelve_fixtures_parse_without_drift():
    assert default_abstract_bust_blueprint_v2_dict() == _fixture()
    for fixture_name in FIXTURE_NAMES:
        fixture = _fixture(fixture_name)
        assert normalize_abstract_bust_blueprint_v2(fixture) == fixture
        assert (
            parse_abstract_bust_blueprint_v2(fixture).model_dump(mode="json")
            == fixture
        )
        assert fixture["generator_version"] == ABSTRACT_BUST_V2_GENERATOR_VERSION
        assert fixture["particle_count"] == 12000


def test_v2_enums_are_derived_from_the_schema():
    schema = _read_json(
        CONTRACT_ROOT / "abstract_bust_blueprint_v0_2.schema.json"
    )
    assert {value.value for value in AbstractBustPresentationV2} == set(
        schema["properties"]["presentation"]["enum"]
    )
    assert {value.value for value in AbstractBustAgeTendencyV2} == set(
        schema["properties"]["age_tendency"]["enum"]
    )
    assert {value.value for value in AbstractBustHairStyleV2} == set(
        schema["$defs"]["hair"]["properties"]["style"]["enum"]
    )


def test_version_router_dispatches_v1_and_v2_without_migration():
    v1 = _read_json(
        ROOT
        / "packages"
        / "shared-schema"
        / "contracts"
        / "abstract_bust_v0_1"
        / "fixtures"
        / "default.json"
    )
    assert (
        normalize_abstract_bust_blueprint_by_version(v1)["generator_version"]
        == "abstract_bust_v0_1"
    )
    assert (
        normalize_abstract_bust_blueprint_by_version(_fixture())[
            "generator_version"
        ]
        == "abstract_bust_v0_2"
    )

    missing = _fixture()
    missing.pop("generator_version")
    with pytest.raises(AbstractBustBlueprintValidationError) as captured:
        normalize_abstract_bust_blueprint_by_version(missing)
    assert captured.value.code == "missing_required_field"

    unknown = _fixture()
    unknown["generator_version"] = "abstract_bust_v0_3"
    with pytest.raises(AbstractBustBlueprintValidationError) as captured:
        normalize_abstract_bust_blueprint_by_version(unknown)
    assert captured.value.code == "unknown_generator_version"


@pytest.mark.parametrize(
    ("mutate", "code", "path"),
    (
        (
            lambda value: value.update(
                {"generator_version": "abstract_bust_v9"}
            ),
            "unknown_generator_version",
            "$.generator_version",
        ),
        (
            lambda value: value.update({"presentation": "cinematic"}),
            "unknown_enum",
            "$.presentation",
        ),
        (
            lambda value: value["head"].update({"crown": 0.2}),
            "unknown_field",
            "$.head.crown",
        ),
        (
            lambda value: value["head"].update({"depth": "0.23"}),
            "invalid_type",
            "$.head.depth",
        ),
        (
            lambda value: value["face"].update({"eyes": []}),
            "invalid_type",
            "$.face.eyes",
        ),
    ),
)
def test_v2_rejects_unknown_contract_content(mutate, code: str, path: str):
    blueprint = _fixture()
    mutate(blueprint)
    _assert_error(blueprint, code, path)


@pytest.mark.parametrize("invalid_number", (float("nan"), float("inf"), float("-inf")))
def test_v2_rejects_non_finite_numbers(invalid_number: float):
    blueprint = _fixture()
    blueprint["head"]["depth"] = invalid_number
    _assert_error(blueprint, "non_finite_number", "$.head.depth")


@pytest.mark.parametrize(
    ("mutate", "path"),
    (
        (lambda value: value.pop("head"), "$.head"),
        (lambda value: value["head"].pop("depth"), "$.head.depth"),
        (
            lambda value: value["face"]["eyes"].pop("spacing"),
            "$.face.eyes.spacing",
        ),
    ),
)
def test_v2_rejects_missing_required_fields(mutate, path: str):
    blueprint = _fixture()
    mutate(blueprint)
    _assert_error(blueprint, "missing_required_field", path)


def test_particle_count_defaults_and_clamps_from_schema():
    schema = _read_json(
        CONTRACT_ROOT / "abstract_bust_blueprint_v0_2.schema.json"
    )
    particle_schema = schema["properties"]["particle_count"]

    missing = _fixture()
    missing.pop("particle_count")
    assert (
        normalize_abstract_bust_blueprint_v2(missing)["particle_count"]
        == particle_schema["default"]
    )

    below = _fixture()
    below["particle_count"] = 1
    assert (
        normalize_abstract_bust_blueprint_v2(below)["particle_count"]
        == particle_schema["minimum"]
    )

    above = _fixture()
    above["particle_count"] = 999999
    assert (
        normalize_abstract_bust_blueprint_v2(above)["particle_count"]
        == particle_schema["maximum"]
    )


@pytest.mark.parametrize(
    "invalid",
    (
        12000.5,
        "12000",
        True,
        float("nan"),
        float("inf"),
        float("-inf"),
    ),
)
def test_particle_count_rejects_non_integer_values(invalid):
    blueprint = _fixture()
    blueprint["particle_count"] = invalid
    _assert_error(blueprint, "invalid_type", "$.particle_count")


def test_v2_optional_defaults_and_finite_clamp_are_schema_driven():
    optional = _fixture()
    optional.pop("particle_count")
    optional.pop("age_tendency")
    optional.pop("face")
    optional.pop("contour")
    assert normalize_abstract_bust_blueprint_v2(optional) == _fixture()

    clamped = _fixture()
    clamped["seed"] = 0
    clamped["head"]["depth"] = -100
    clamped["shoulders"]["width"] = 100
    clamped["contour"]["asymmetry"] = -1
    normalized = normalize_abstract_bust_blueprint_v2(clamped)
    assert normalized["seed"] == 1
    assert normalized["head"]["depth"] == 0.18
    assert normalized["shoulders"]["width"] == 0.68
    assert normalized["contour"]["asymmetry"] == 0


@pytest.mark.parametrize(
    ("kind", "values"),
    (
        ("presentation", ("neutral", "feminine", "masculine")),
        ("age_tendency", ("youthful", "balanced", "mature")),
        ("hair", ("none", "short", "medium", "long", "tied")),
    ),
)
def test_v2_presets_preserve_seed_and_particle_count(kind: str, values):
    current = _fixture()
    current["seed"] = 17
    current["particle_count"] = 23001
    for value in values:
        fixture = load_abstract_bust_preset_fixture_v2(
            kind, value
        ).model_dump(mode="json")
        applied = apply_abstract_bust_preset_v2(
            current, kind, value
        ).model_dump(mode="json")
        assert applied["seed"] == current["seed"]
        assert applied["particle_count"] == current["particle_count"]
        expected = deepcopy(fixture)
        expected["seed"] = current["seed"]
        expected["particle_count"] = current["particle_count"]
        assert applied == expected

    restored = default_abstract_bust_blueprint_v2_dict()
    assert restored["seed"] == _fixture()["seed"]
    assert restored["particle_count"] == 12000


def test_v2_output_is_nested_and_has_no_legacy_flat_fields():
    normalized = normalize_abstract_bust_blueprint_v2(
        _fixture("hair_long.json")
    )
    assert list(normalized) == [
        "generator_version",
        "particle_count",
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
    ]
    serialized = json.dumps(normalized)
    assert all(
        forbidden not in serialized
        for forbidden in (
            "head_width",
            "head_depth",
            "shoulders_width",
            "hair_style",
            "AbstractBustTuning",
        )
    )


def test_frontend_and_backend_normalize_v2_fixtures_identically():
    runner = (
        ROOT
        / "apps"
        / "web"
        / "tests"
        / "helpers"
        / "abstract-bust-v2-parity-runner.mjs"
    )
    fixture_paths = [FIXTURE_ROOT / name for name in FIXTURE_NAMES]
    frontend = json.loads(
        subprocess.run(
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
        ).stdout
    )
    backend = {
        path.name: normalize_abstract_bust_blueprint_v2(_read_json(path))
        for path in fixture_paths
    }
    assert frontend == backend


def test_frontend_and_backend_share_v2_normalization_and_error_rules():
    runner = (
        ROOT
        / "apps"
        / "web"
        / "tests"
        / "helpers"
        / "abstract-bust-v2-parity-runner.mjs"
    )
    optional = _fixture()
    optional.pop("particle_count")
    optional.pop("age_tendency")
    optional.pop("face")
    optional.pop("contour")
    clamped = _fixture()
    clamped["particle_count"] = 1
    clamped["head"]["depth"] = 99
    cases = {
        "optional": optional,
        "clamped": clamped,
        "unknown_field": {
            **_fixture(),
            "private_shape": 1,
        },
        "invalid_particle_count": {
            **_fixture(),
            "particle_count": 12000.5,
        },
        "missing_depth": {
            **_fixture(),
            "head": {
                key: value
                for key, value in _fixture()["head"].items()
                if key != "depth"
            },
        },
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
                "value": normalize_abstract_bust_blueprint_v2(value),
            }
        except AbstractBustBlueprintV2ValidationError as error:
            backend[name] = {
                "ok": False,
                "code": error.code,
                "path": error.path,
            }
    assert frontend == backend


def test_v2_contract_has_no_generator_artifacts():
    names = [path.name.lower() for path in CONTRACT_ROOT.rglob("*")]
    assert not any(
        forbidden in name
        for name in names
        for forbidden in (
            "golden",
            "digest",
            "coordinate",
            "coordinates",
            "oracle",
        )
    )


def test_v2_implementation_has_no_private_fixed_particle_constant():
    sources = (
        ROOT
        / "packages"
        / "shared-schema"
        / "src"
        / "abstract-bust-blueprint-v2.ts",
        ROOT
        / "apps"
        / "api"
        / "app"
        / "services"
        / "abstract_bust_blueprint_v2.py",
    )
    for source in sources:
        text = source.read_text(encoding="utf-8")
        assert "12000" not in text
        assert "Float32Array(12000" not in text
