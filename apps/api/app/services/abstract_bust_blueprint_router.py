from __future__ import annotations

import json
from typing import Any, Dict, Union

from app.services.abstract_bust_blueprint import (
    AbstractBustBlueprint,
    AbstractBustBlueprintValidationError,
    normalize_abstract_bust_blueprint,
    parse_abstract_bust_blueprint,
)
from app.services.abstract_bust_blueprint_v2 import (
    AbstractBustBlueprintV2,
    normalize_abstract_bust_blueprint_v2,
    parse_abstract_bust_blueprint_v2,
)


AnyAbstractBustBlueprint = Union[
    AbstractBustBlueprint,
    AbstractBustBlueprintV2,
]


def _reject_json_constant(value: str) -> None:
    raise AbstractBustBlueprintValidationError(
        "non_finite_number", "$", f"{value} is not valid JSON"
    )


def _parse_routing_input(value: Any) -> Dict[str, Any]:
    if isinstance(value, (str, bytes, bytearray)):
        try:
            value = json.loads(value, parse_constant=_reject_json_constant)
        except AbstractBustBlueprintValidationError:
            raise
        except (TypeError, json.JSONDecodeError) as error:
            raise AbstractBustBlueprintValidationError(
                "invalid_json", "$", str(error)
            ) from error
    if not isinstance(value, dict):
        raise AbstractBustBlueprintValidationError(
            "invalid_root_type", "$", "expected an object"
        )
    return value


def normalize_abstract_bust_blueprint_by_version(value: Any) -> Dict[str, Any]:
    parsed = _parse_routing_input(value)
    if "generator_version" not in parsed:
        raise AbstractBustBlueprintValidationError(
            "missing_required_field",
            "$.generator_version",
            "required field is missing",
        )
    version = parsed["generator_version"]
    if version == "abstract_bust_v0_1":
        return normalize_abstract_bust_blueprint(parsed)
    if version == "abstract_bust_v0_2":
        return normalize_abstract_bust_blueprint_v2(parsed)
    raise AbstractBustBlueprintValidationError(
        "unknown_generator_version",
        "$.generator_version",
        f"unsupported value {version!r}",
    )


def parse_abstract_bust_blueprint_by_version(
    value: Any,
) -> AnyAbstractBustBlueprint:
    parsed = _parse_routing_input(value)
    normalized = normalize_abstract_bust_blueprint_by_version(parsed)
    if normalized["generator_version"] == "abstract_bust_v0_1":
        return parse_abstract_bust_blueprint(normalized)
    return parse_abstract_bust_blueprint_v2(normalized)
