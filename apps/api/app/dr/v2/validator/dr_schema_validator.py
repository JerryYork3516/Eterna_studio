"""Schema validation — required / type / enum / extra + metadata markers.

This is the only gate that short-circuits: without a typed model the downstream
validators have nothing to inspect.
"""

from __future__ import annotations

from typing import Optional

from pydantic import ValidationError

from ..dr_v0_2_schema import (
    DR_FILE_TYPE,
    DR_LAYER_ROLE,
    DR_VERSION_V0_2,
    DigitalResidentV02Gate,
)
from .dr_validation_result import DRValidationResult, finding

# Map a Pydantic v2 error "type" to a stable DR schema failure code.
_REQUIRED_TYPES = {"missing", "model_attributes_type"}
_ENUM_TYPES = {"enum", "literal_error"}
_EXTRA_TYPES = {"extra_forbidden"}


def _classify(err_type: str) -> str:
    if err_type in _REQUIRED_TYPES:
        return "DR_SCHEMA_REQUIRED"
    if err_type in _ENUM_TYPES:
        return "DR_SCHEMA_ENUM"
    if err_type in _EXTRA_TYPES:
        return "DR_SCHEMA_EXTRA"
    return "DR_SCHEMA_TYPE"


def validate_schema(dr: dict, result: DRValidationResult) -> Optional[DigitalResidentV02Gate]:
    """Construct the typed model; emit findings on failure. Returns model or None."""
    try:
        model = DigitalResidentV02Gate.model_validate(dr)
    except ValidationError as exc:
        for err in exc.errors():
            code = _classify(err.get("type", ""))
            path = ".".join(str(p) for p in err.get("loc", ())) or "(root)"
            result.add(finding("FAIL", code, err.get("msg", "invalid"), path))
        return None

    # Metadata markers — policy-layer invariants.
    if model.dr_layer != DR_LAYER_ROLE:
        result.add(
            finding("FAIL", "DR_META_LAYER_INVALID", f"dr_layer must be '{DR_LAYER_ROLE}'", "dr_layer")
        )
    if model.not_executable is not True:
        result.add(
            finding("FAIL", "DR_META_NOT_EXECUTABLE", "not_executable must be true", "not_executable")
        )
    if model.dr_version != DR_VERSION_V0_2:
        result.add(
            finding("FAIL", "DR_META_VERSION", f"dr_version must be '{DR_VERSION_V0_2}'", "dr_version")
        )
    if model.file_type != DR_FILE_TYPE:
        result.add(
            finding("WARNING", "DR_META_FILE_TYPE", f"file_type should be '{DR_FILE_TYPE}'", "file_type")
        )
    return model
