from __future__ import annotations

import json
import math
from copy import deepcopy
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Literal

from pydantic import BaseModel, ConfigDict


ABSTRACT_BUST_GENERATOR_VERSION = "abstract_bust_v0_1"
ABSTRACT_BUST_CONTRACT_ROOT = (
    Path(__file__).resolve().parents[4]
    / "packages"
    / "shared-schema"
    / "contracts"
    / ABSTRACT_BUST_GENERATOR_VERSION
)
ABSTRACT_BUST_SCHEMA_PATH = (
    ABSTRACT_BUST_CONTRACT_ROOT / "abstract_bust_blueprint_v0_1.schema.json"
)
ABSTRACT_BUST_DEFAULT_FIXTURE_PATH = (
    ABSTRACT_BUST_CONTRACT_ROOT / "fixtures" / "default.json"
)


class AbstractBustBlueprintValidationError(ValueError):
    def __init__(self, code: str, path: str, message: str):
        self.code = code
        self.path = path
        super().__init__(f"{code} at {path}: {message}")


class AbstractBustPresentation(str, Enum):
    neutral = "neutral"
    feminine = "feminine"
    masculine = "masculine"


class AbstractBustAgeTendency(str, Enum):
    youthful = "youthful"
    balanced = "balanced"
    mature = "mature"


class AbstractBustHairStyle(str, Enum):
    none = "none"
    short = "short"
    medium = "medium"
    long = "long"
    tied = "tied"


class AbstractBustModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class AbstractBustHead(AbstractBustModel):
    width: float
    height: float
    roundness: float


class AbstractBustEyes(AbstractBustModel):
    vertical_position: float
    spacing: float
    size: float
    tilt: float
    contour_strength: float


class AbstractBustNose(AbstractBustModel):
    vertical_position: float
    width: float
    length: float
    prominence: float


class AbstractBustMouth(AbstractBustModel):
    vertical_position: float
    width: float
    curvature: float
    contour_strength: float


class AbstractBustCheeks(AbstractBustModel):
    width: float
    vertical_position: float
    prominence: float


class AbstractBustJaw(AbstractBustModel):
    width: float
    taper: float
    length: float
    roundness: float


class AbstractBustFace(AbstractBustModel):
    eyes: AbstractBustEyes
    nose: AbstractBustNose
    mouth: AbstractBustMouth
    cheeks: AbstractBustCheeks
    jaw: AbstractBustJaw


class AbstractBustNeck(AbstractBustModel):
    width: float
    length: float


class AbstractBustShoulders(AbstractBustModel):
    width: float
    slope: float


class AbstractBustTorso(AbstractBustModel):
    width: float
    thickness: float
    length: float
    taper: float


class AbstractBustHair(AbstractBustModel):
    style: AbstractBustHairStyle
    volume: float
    length: float


class AbstractBustContour(AbstractBustModel):
    softening: float
    asymmetry: float


class AbstractBustBlueprint(AbstractBustModel):
    generator_version: Literal["abstract_bust_v0_1"]
    presentation: AbstractBustPresentation
    age_tendency: AbstractBustAgeTendency
    seed: int
    head: AbstractBustHead
    face: AbstractBustFace
    neck: AbstractBustNeck
    shoulders: AbstractBustShoulders
    torso: AbstractBustTorso
    hair: AbstractBustHair
    contour: AbstractBustContour


def _reject_json_constant(value: str) -> None:
    raise AbstractBustBlueprintValidationError(
        "non_finite_number", "$", f"{value} is not valid JSON"
    )


def _load_json(path: Path) -> Dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"), parse_constant=_reject_json_constant)
    if not isinstance(value, dict):
        raise AbstractBustBlueprintValidationError(
            "invalid_root_type", "$", "expected an object"
        )
    return value


_SCHEMA = _load_json(ABSTRACT_BUST_SCHEMA_PATH)
_DEFAULT_BLUEPRINT = _load_json(ABSTRACT_BUST_DEFAULT_FIXTURE_PATH)


def _resolve_schema(schema: Dict[str, Any]) -> Dict[str, Any]:
    reference = schema.get("$ref")
    if reference is None:
        return schema
    prefix = "#/$defs/"
    if not isinstance(reference, str) or not reference.startswith(prefix):
        raise RuntimeError(f"Unsupported AbstractBustBlueprint schema reference: {reference!r}")
    definition = _SCHEMA.get("$defs", {}).get(reference[len(prefix) :])
    if not isinstance(definition, dict):
        raise RuntimeError(f"Missing AbstractBustBlueprint schema definition: {reference}")
    return definition


def _validation_error(code: str, path: str, message: str) -> None:
    raise AbstractBustBlueprintValidationError(code, path, message)


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
        code = "unknown_generator_version" if path == "$.generator_version" else "invalid_const"
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
        missing_required = [
            field_name for field_name in required_fields if field_name not in value
        ]
        if missing_required:
            field_name = sorted(missing_required)[0]
            _validation_error(
                "missing_required_field",
                f"{path}.{field_name}",
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
            _validation_error("non_finite_number", path, "number must be finite")
        minimum = schema.get("minimum")
        maximum = schema.get("maximum")
        if isinstance(minimum, (int, float)):
            numeric_value = max(float(minimum), numeric_value)
        if isinstance(maximum, (int, float)):
            numeric_value = min(float(maximum), numeric_value)
        return numeric_value

    return value


def normalize_abstract_bust_blueprint(value: Any) -> Dict[str, Any]:
    if isinstance(value, (str, bytes, bytearray)):
        try:
            value = json.loads(value, parse_constant=_reject_json_constant)
        except AbstractBustBlueprintValidationError:
            raise
        except (TypeError, json.JSONDecodeError) as error:
            raise AbstractBustBlueprintValidationError(
                "invalid_json", "$", str(error)
            ) from error
    normalized = _normalize_value(value, _SCHEMA, _DEFAULT_BLUEPRINT, "$")
    return AbstractBustBlueprint.model_validate(normalized).model_dump(mode="json")


def parse_abstract_bust_blueprint(value: Any) -> AbstractBustBlueprint:
    return AbstractBustBlueprint.model_validate(normalize_abstract_bust_blueprint(value))


def load_default_abstract_bust_blueprint() -> AbstractBustBlueprint:
    return parse_abstract_bust_blueprint(deepcopy(_DEFAULT_BLUEPRINT))


def default_abstract_bust_blueprint_dict() -> Dict[str, Any]:
    return load_default_abstract_bust_blueprint().model_dump(mode="json")
