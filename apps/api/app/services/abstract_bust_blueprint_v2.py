from __future__ import annotations

import json
import math
from copy import deepcopy
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Literal

from pydantic import BaseModel, ConfigDict


ABSTRACT_BUST_V2_GENERATOR_VERSION = "abstract_bust_v0_2"
ABSTRACT_BUST_V2_CONTRACT_ROOT = (
    Path(__file__).resolve().parents[4]
    / "packages"
    / "shared-schema"
    / "contracts"
    / ABSTRACT_BUST_V2_GENERATOR_VERSION
)
ABSTRACT_BUST_V2_SCHEMA_PATH = (
    ABSTRACT_BUST_V2_CONTRACT_ROOT / "abstract_bust_blueprint_v0_2.schema.json"
)
ABSTRACT_BUST_V2_DEFAULT_FIXTURE_PATH = (
    ABSTRACT_BUST_V2_CONTRACT_ROOT / "fixtures" / "default.json"
)


class AbstractBustBlueprintV2ValidationError(ValueError):
    def __init__(self, code: str, path: str, message: str):
        self.code = code
        self.path = path
        super().__init__(f"{code} at {path}: {message}")


def _reject_json_constant(value: str) -> None:
    raise AbstractBustBlueprintV2ValidationError(
        "non_finite_number", "$", f"{value} is not valid JSON"
    )


def _load_json(path: Path) -> Dict[str, Any]:
    value = json.loads(
        path.read_text(encoding="utf-8"),
        parse_constant=_reject_json_constant,
    )
    if not isinstance(value, dict):
        raise AbstractBustBlueprintV2ValidationError(
            "invalid_root_type", "$", "expected an object"
        )
    return value


_SCHEMA = _load_json(ABSTRACT_BUST_V2_SCHEMA_PATH)
_DEFAULT_BLUEPRINT = _load_json(ABSTRACT_BUST_V2_DEFAULT_FIXTURE_PATH)


def _schema_enum(path: tuple[str, ...]) -> list[str]:
    value: Any = _SCHEMA
    for component in path:
        value = value[component]
    if not isinstance(value, list) or not all(
        isinstance(candidate, str) for candidate in value
    ):
        raise RuntimeError(f"Invalid v0.2 enum schema at {'.'.join(path)}")
    return value


AbstractBustPresentationV2 = Enum(
    "AbstractBustPresentationV2",
    {
        value: value
        for value in _schema_enum(("properties", "presentation", "enum"))
    },
    type=str,
)
AbstractBustAgeTendencyV2 = Enum(
    "AbstractBustAgeTendencyV2",
    {
        value: value
        for value in _schema_enum(("properties", "age_tendency", "enum"))
    },
    type=str,
)
AbstractBustHairStyleV2 = Enum(
    "AbstractBustHairStyleV2",
    {
        value: value
        for value in _schema_enum(
            ("$defs", "hair", "properties", "style", "enum")
        )
    },
    type=str,
)


class AbstractBustModelV2(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class AbstractBustHeadV2(AbstractBustModelV2):
    width: float
    height: float
    depth: float
    roundness: float


class AbstractBustEyesV2(AbstractBustModelV2):
    vertical_position: float
    spacing: float
    size: float
    tilt: float
    contour_strength: float


class AbstractBustNoseV2(AbstractBustModelV2):
    vertical_position: float
    width: float
    length: float
    prominence: float


class AbstractBustMouthV2(AbstractBustModelV2):
    vertical_position: float
    width: float
    curvature: float
    contour_strength: float


class AbstractBustCheeksV2(AbstractBustModelV2):
    width: float
    vertical_position: float
    prominence: float


class AbstractBustJawV2(AbstractBustModelV2):
    width: float
    taper: float
    length: float
    roundness: float


class AbstractBustFaceV2(AbstractBustModelV2):
    eyes: AbstractBustEyesV2
    nose: AbstractBustNoseV2
    mouth: AbstractBustMouthV2
    cheeks: AbstractBustCheeksV2
    jaw: AbstractBustJawV2


class AbstractBustNeckV2(AbstractBustModelV2):
    width: float
    length: float


class AbstractBustShouldersV2(AbstractBustModelV2):
    width: float
    slope: float


class AbstractBustTorsoV2(AbstractBustModelV2):
    width: float
    thickness: float
    length: float
    taper: float


class AbstractBustHairV2(AbstractBustModelV2):
    style: AbstractBustHairStyleV2
    volume: float
    length: float


class AbstractBustContourV2(AbstractBustModelV2):
    softening: float
    asymmetry: float


class AbstractBustBlueprintV2(AbstractBustModelV2):
    generator_version: Literal["abstract_bust_v0_2"]
    particle_count: int
    presentation: AbstractBustPresentationV2
    age_tendency: AbstractBustAgeTendencyV2
    seed: int
    head: AbstractBustHeadV2
    face: AbstractBustFaceV2
    neck: AbstractBustNeckV2
    shoulders: AbstractBustShouldersV2
    torso: AbstractBustTorsoV2
    hair: AbstractBustHairV2
    contour: AbstractBustContourV2


def _resolve_schema(schema: Dict[str, Any]) -> Dict[str, Any]:
    reference = schema.get("$ref")
    if reference is None:
        return schema
    prefix = "#/$defs/"
    if not isinstance(reference, str) or not reference.startswith(prefix):
        raise RuntimeError(
            f"Unsupported AbstractBustBlueprintV2 schema reference: {reference!r}"
        )
    definition = _SCHEMA.get("$defs", {}).get(reference[len(prefix) :])
    if not isinstance(definition, dict):
        raise RuntimeError(
            f"Missing AbstractBustBlueprintV2 schema definition: {reference}"
        )
    return definition


def _validation_error(code: str, path: str, message: str) -> None:
    raise AbstractBustBlueprintV2ValidationError(code, path, message)


def _normalize_value(
    value: Any,
    schema: Dict[str, Any],
    default_value: Any,
    path: str,
) -> Any:
    schema = _resolve_schema(schema)

    if "const" in schema and (
        type(value) is not type(schema["const"]) or value != schema["const"]
    ):
        code = (
            "unknown_generator_version"
            if path == "$.generator_version"
            else "invalid_const"
        )
        _validation_error(code, path, f"expected {schema['const']!r}")

    enum_values = schema.get("enum")
    if isinstance(enum_values, list) and not any(
        type(value) is type(candidate) and value == candidate
        for candidate in enum_values
    ):
        _validation_error("unknown_enum", path, f"unsupported value {value!r}")

    schema_type = schema.get("type")
    if schema_type == "object":
        if not isinstance(value, dict):
            _validation_error("invalid_type", path, "expected object")
        properties = schema.get("properties")
        if not isinstance(properties, dict):
            raise RuntimeError(f"Object schema has no properties at {path}")
        unknown_fields = sorted(set(value) - set(properties))
        if unknown_fields:
            _validation_error(
                "unknown_field",
                f"{path}.{unknown_fields[0]}",
                "additional properties are forbidden",
            )
        required = schema.get("required")
        required_fields = set(required) if isinstance(required, list) else set()
        missing_required = sorted(
            field_name
            for field_name in required_fields
            if field_name not in value
        )
        if missing_required:
            _validation_error(
                "missing_required_field",
                f"{path}.{missing_required[0]}",
                "required field is missing",
            )

        defaults = default_value if isinstance(default_value, dict) else {}
        normalized: Dict[str, Any] = {}
        for field_name, field_schema in properties.items():
            if not isinstance(field_schema, dict):
                raise RuntimeError(f"Invalid schema for {path}.{field_name}")
            if field_name in value:
                normalized[field_name] = _normalize_value(
                    value[field_name],
                    field_schema,
                    defaults.get(field_name),
                    f"{path}.{field_name}",
                )
                continue
            if field_name in required_fields:
                continue
            if field_name in defaults:
                optional_default = deepcopy(defaults[field_name])
            elif "default" in field_schema:
                optional_default = deepcopy(field_schema["default"])
            else:
                continue
            normalized[field_name] = _normalize_value(
                optional_default,
                field_schema,
                optional_default,
                f"{path}.{field_name}",
            )
        return normalized

    if schema_type == "integer":
        if type(value) is not int:
            _validation_error("invalid_type", path, "expected integer")
        minimum = schema.get("minimum")
        maximum = schema.get("maximum")
        if isinstance(minimum, int):
            value = max(minimum, value)
        if isinstance(maximum, int):
            value = min(maximum, value)
        return value

    if schema_type == "number":
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            _validation_error("invalid_type", path, "expected number")
        numeric_value = float(value)
        if not math.isfinite(numeric_value):
            _validation_error(
                "non_finite_number", path, "number must be finite"
            )
        minimum = schema.get("minimum")
        maximum = schema.get("maximum")
        if isinstance(minimum, (int, float)):
            numeric_value = max(float(minimum), numeric_value)
        if isinstance(maximum, (int, float)):
            numeric_value = min(float(maximum), numeric_value)
        return numeric_value

    return value


def _strict_model_from_normalized(
    normalized: Dict[str, Any],
) -> AbstractBustBlueprintV2:
    strict_model_input = deepcopy(normalized)
    strict_model_input["presentation"] = AbstractBustPresentationV2(
        strict_model_input["presentation"]
    )
    strict_model_input["age_tendency"] = AbstractBustAgeTendencyV2(
        strict_model_input["age_tendency"]
    )
    strict_model_input["hair"]["style"] = AbstractBustHairStyleV2(
        strict_model_input["hair"]["style"]
    )
    return AbstractBustBlueprintV2.model_validate(strict_model_input)


def normalize_abstract_bust_blueprint_v2(value: Any) -> Dict[str, Any]:
    if isinstance(value, (str, bytes, bytearray)):
        try:
            value = json.loads(value, parse_constant=_reject_json_constant)
        except AbstractBustBlueprintV2ValidationError:
            raise
        except (TypeError, json.JSONDecodeError) as error:
            raise AbstractBustBlueprintV2ValidationError(
                "invalid_json", "$", str(error)
            ) from error
    normalized = _normalize_value(value, _SCHEMA, _DEFAULT_BLUEPRINT, "$")
    return _strict_model_from_normalized(normalized).model_dump(mode="json")


def parse_abstract_bust_blueprint_v2(value: Any) -> AbstractBustBlueprintV2:
    return _strict_model_from_normalized(
        normalize_abstract_bust_blueprint_v2(value)
    )


def load_default_abstract_bust_blueprint_v2() -> AbstractBustBlueprintV2:
    return parse_abstract_bust_blueprint_v2(deepcopy(_DEFAULT_BLUEPRINT))


def default_abstract_bust_blueprint_v2_dict() -> Dict[str, Any]:
    return load_default_abstract_bust_blueprint_v2().model_dump(mode="json")


_PRESET_FILENAMES = {
    "presentation": {
        "neutral": "neutral.json",
        "feminine": "feminine.json",
        "masculine": "masculine.json",
    },
    "age_tendency": {
        "youthful": "youthful.json",
        "balanced": "balanced.json",
        "mature": "mature.json",
    },
    "hair": {
        "none": "hair_none.json",
        "short": "hair_short.json",
        "medium": "hair_medium.json",
        "long": "hair_long.json",
        "tied": "hair_tied.json",
    },
}


def load_abstract_bust_preset_fixture_v2(
    kind: str,
    value: str,
) -> AbstractBustBlueprintV2:
    filename = _PRESET_FILENAMES.get(kind, {}).get(value)
    if filename is None:
        _validation_error(
            "unknown_enum",
            f"$.{kind}",
            f"unsupported value {value!r}",
        )
    return parse_abstract_bust_blueprint_v2(
        _load_json(ABSTRACT_BUST_V2_CONTRACT_ROOT / "fixtures" / filename)
    )


def apply_abstract_bust_preset_v2(
    current: Any,
    kind: str,
    value: str,
) -> AbstractBustBlueprintV2:
    normalized_current = normalize_abstract_bust_blueprint_v2(current)
    preset = load_abstract_bust_preset_fixture_v2(kind, value).model_dump(
        mode="json"
    )
    preset["seed"] = normalized_current["seed"]
    preset["particle_count"] = normalized_current["particle_count"]
    return parse_abstract_bust_blueprint_v2(preset)
