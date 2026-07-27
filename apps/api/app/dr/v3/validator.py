"""Single formal validation gate for DR v0.3 documents.

The gate validates the full frozen envelope before applying the Runtime
capability contract and the no-credential export boundary. It never rewrites
the submitted document.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List

from pydantic import ValidationError

from ..v2.validator.capability_validator import (
    validate_v03_runtime_contract,
)
from .dr_v0_3_schema import DRDocumentV03


_OUTPUT_CREDENTIAL_KEYS = frozenset(
    {
        "api_key",
        "apikey",
        "api_token",
        "auth_token",
        "authorization",
        "token",
        "access_token",
        "refresh_token",
        "bearer",
        "bearer_credential",
        "bearer_token",
        "base_url",
        "endpoint",
        "endpoint_url",
        "api_endpoint",
        "credential",
        "credentials",
        "secret",
        "provider_secret",
        "password",
        "client_secret",
        "private_key",
        "provider",
        "provider_binding",
        "provider_config",
        "provider_profile",
        "provider_profile_id",
    }
)
_OUTPUT_CREDENTIAL_VALUE_PATTERNS = (
    re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]{8,}"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{12,}"),
    re.compile(r"\bAKIA[A-Z0-9]{16}\b"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b"),
)
_NON_BINDING_PROVIDER_LABEL_KEYS = frozenset(
    {"provider", "provider_binding", "provider_profile_id"}
)


def _finding(
    status: str, code: str, message: str, path: str
) -> Dict[str, str]:
    return {
        "status": status,
        "code": code,
        "message": message,
        "path": path,
    }


def _contains_actual_credential_value(value: Any) -> bool:
    if value is None or value is False:
        return False
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {
            "",
            "mock",
            "placeholder",
            "reserved",
            "policy_only",
            "compatibility_fallback",
            "disabled",
            "runtime_disabled",
            "not_configured",
            "none",
            "null",
        }:
            return False
        if normalized.endswith("_mock") or normalized.startswith("mock_"):
            return False
        return True
    if isinstance(value, dict):
        return any(
            _contains_actual_credential_value(item)
            for item in value.values()
        )
    if isinstance(value, list):
        return any(
            _contains_actual_credential_value(item) for item in value
        )
    return bool(value)


def _normalized_credential_key(value: Any) -> str:
    text = re.sub(
        r"(?<!^)(?=[A-Z])",
        "_",
        str(value or "").strip(),
    )
    return re.sub(r"[^a-zA-Z0-9]+", "_", text).strip("_").lower()


def compiled_credential_paths(
    value: Any, path: str = ""
) -> List[str]:
    """Return credential paths without returning any credential values."""

    paths: List[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            item_path = f"{path}.{key}" if path else str(key)
            normalized_key = _normalized_credential_key(key)
            if (
                normalized_key in _NON_BINDING_PROVIDER_LABEL_KEYS
                and isinstance(item, str)
                and item.strip().lower() == "default"
            ):
                # Frozen early-v0.3 compatibility shells used "default" as a
                # non-binding display label. It carries no endpoint, profile,
                # credential, or executable Provider selection.
                continue
            if (
                normalized_key in _OUTPUT_CREDENTIAL_KEYS
                and _contains_actual_credential_value(item)
            ):
                paths.append(item_path)
                continue
            paths.extend(compiled_credential_paths(item, item_path))
        return paths
    if isinstance(value, list):
        for index, item in enumerate(value):
            paths.extend(
                compiled_credential_paths(item, f"{path}[{index}]")
            )
        return paths
    if isinstance(value, str) and any(
        pattern.search(value)
        for pattern in _OUTPUT_CREDENTIAL_VALUE_PATTERNS
    ):
        paths.append(path or "$")
    return paths


def validate_v03_security_configuration(
    document: Dict[str, Any],
) -> List[Dict[str, str]]:
    """Reject actual credentials on every exported v0.3 surface."""

    export_surface = {
        key: value
        for key, value in document.items()
        if key not in {"audit", "audit_report"}
    }
    credential_paths = sorted(
        set(compiled_credential_paths(export_surface))
    )
    if credential_paths:
        return [
            _finding(
                "FAIL",
                "DR_COMPILED_CREDENTIAL_VALUE",
                (
                    "compiled DR contains a non-empty credential, endpoint, "
                    "or Provider Profile value; the value was not included "
                    "in this diagnostic"
                ),
                path,
            )
            for path in credential_paths
        ]
    return [
        _finding(
            "PASS",
            "DR_SECURITY_CONFIGURATION_CHECK_PASSED",
            (
                "compiled DR contains no actual API key, token, bearer "
                "credential, base URL, Provider secret, password, or real "
                "Provider Profile"
            ),
            "payload",
        )
    ]


def _schema_error_path(location: tuple[Any, ...]) -> str:
    path = ""
    for component in location:
        if isinstance(component, int):
            path += f"[{component}]"
        elif path:
            path += f".{component}"
        else:
            path = str(component)
    return path or "$"


def _schema_error_code(error_type: str) -> str:
    if error_type == "missing":
        return "DR_V03_SCHEMA_REQUIRED"
    if error_type == "literal_error":
        return "DR_V03_SCHEMA_ENUM"
    if error_type == "extra_forbidden":
        return "DR_V03_SCHEMA_EXTRA"
    if error_type.startswith(
        (
            "bool_",
            "dict_",
            "float_",
            "int_",
            "list_",
            "model_",
            "string_",
        )
    ):
        return "DR_V03_SCHEMA_TYPE"
    return "DR_V03_SCHEMA_VALUE"


def validate_v03_formal_schema(
    document: Any,
) -> List[Dict[str, str]]:
    """Run the strict DRDocumentV03 model without mutating the input."""

    try:
        DRDocumentV03.model_validate(document)
    except ValidationError as exc:
        findings: List[Dict[str, str]] = []
        for error in exc.errors(
            include_input=False,
            include_url=False,
        ):
            error_type = str(error.get("type") or "value_error")
            path = _schema_error_path(tuple(error.get("loc") or ()))
            findings.append(
                _finding(
                    "FAIL",
                    _schema_error_code(error_type),
                    (
                        "DR v0.3 formal schema rejected this field "
                        f"({error_type})"
                    ),
                    path,
                )
            )
        return findings
    return [
        _finding(
            "PASS",
            "DR_V03_FORMAL_SCHEMA_CHECK_PASSED",
            (
                "DRDocumentV03 accepted the full authoritative payload and "
                "its controlled v0.3 compatibility projections"
            ),
            "payload",
        )
    ]


def validate_dr_document_v0_3(
    document: Any,
) -> Dict[str, Any]:
    """Validate Schema -> Runtime contract -> credential boundary in order."""

    schema_findings = validate_v03_formal_schema(document)
    schema_valid = not any(
        finding["status"] == "FAIL"
        for finding in schema_findings
    )
    runtime_contract_findings = (
        validate_v03_runtime_contract(document)
        if isinstance(document, dict)
        else []
    )
    security_findings = (
        validate_v03_security_configuration(document)
        if isinstance(document, dict)
        else []
    )
    findings = [
        *schema_findings,
        *runtime_contract_findings,
        *security_findings,
    ]
    return {
        "valid": not any(
            finding["status"] == "FAIL" for finding in findings
        ),
        "schema_valid": schema_valid,
        "schema_findings": schema_findings,
        "runtime_contract_findings": runtime_contract_findings,
        "security_findings": security_findings,
        "findings": findings,
    }
