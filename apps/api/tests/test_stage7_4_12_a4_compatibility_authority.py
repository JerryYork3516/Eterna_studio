"""Stage 7.4.12 A4 module authority and compatibility-copy contracts."""

from __future__ import annotations

from copy import deepcopy
import json
from typing import Any

import pytest

from app.services import dr_compiler
from app.services.dr_compiler import (
    compile_dr_result_v0_3,
    mock_load_dr_v0_3,
)


_REQUIRED_CAPABILITIES = ["llm", "memory", "lattice"]
_FROZEN_PATHS = (
    ("layers",),
    ("modules",),
    ("slots",),
    ("dr_version",),
    ("dr_schema_version",),
    ("schema_version",),
    ("protocol_version",),
    ("manifest", "required_capabilities"),
    ("payload", "modules"),
    ("payload", "resident_identity"),
    ("payload", "memory_policy"),
    ("payload", "runtime_dialogue_projection"),
    ("visual_expression_mapping",),
    ("payload", "lattice_config"),
    ("payload", "voice_config"),
    ("payload", "runtime_requirements"),
)


def _workflow() -> dict[str, Any]:
    return {
        "name": "Stage 7.4.12 A4 compatibility authority fixture",
        "nodes": [
            {"node_id": f"layer_{index}"}
            for index in range(1, 14)
        ],
    }


def _compile() -> dict[str, Any]:
    return compile_dr_result_v0_3({"workflow": _workflow()})


def _valid_dr() -> dict[str, Any]:
    result = _compile()
    assert result["valid"] is True, result["errors"]
    assert result["compiled_dr"] is not None
    return result["compiled_dr"]


@pytest.fixture(scope="module")
def baseline_dr() -> dict[str, Any]:
    return _valid_dr()


def _normalized_module_semantics(modules: list[dict[str, Any]]) -> str:
    normalized = sorted(
        deepcopy(modules),
        key=lambda module: (
            str(module.get("layer_id") or ""),
            str(module.get("module_id") or ""),
        ),
    )
    return json.dumps(
        normalized,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _contains_full_module_copy(value: Any) -> bool:
    if isinstance(value, dict):
        if (
            value.get("module_id")
            and value.get("layer_id")
            and isinstance(value.get("module_graph"), dict)
        ):
            return True
        return any(
            _contains_full_module_copy(item)
            for item in value.values()
        )
    if isinstance(value, list):
        return any(_contains_full_module_copy(item) for item in value)
    return False


def _remove_path(value: dict[str, Any], path: tuple[str, ...]) -> None:
    parent: dict[str, Any] = value
    for key in path[:-1]:
        child = parent.get(key)
        assert isinstance(child, dict), ".".join(path)
        parent = child
    assert path[-1] in parent, ".".join(path)
    parent.pop(path[-1])


def test_payload_modules_are_authoritative_and_root_is_read_only_deep_copy(
    baseline_dr: dict[str, Any],
):
    dr = deepcopy(baseline_dr)
    payload_modules = dr["payload"]["modules"]
    root_modules = dr["modules"]

    assert _normalized_module_semantics(root_modules) == (
        _normalized_module_semantics(payload_modules)
    )
    assert root_modules == payload_modules
    assert root_modules is not payload_modules

    root_module = next(
        module
        for module in root_modules
        if isinstance(module.get("module_graph"), dict)
    )
    payload_module = next(
        module
        for module in payload_modules
        if module.get("module_id") == root_module.get("module_id")
    )
    assert root_module is not payload_module
    assert root_module["module_graph"] is not payload_module["module_graph"]

    reordered = deepcopy(dr)
    reordered["modules"] = list(reversed(reordered["modules"]))
    reordered_findings = dr_compiler._v03_export_projection_findings(
        reordered
    )
    assert not any(
        finding["status"] == "FAIL"
        and finding["code"] == "DR_EXPORT_COMPATIBILITY_PROJECTION_DRIFT"
        and finding["path"] == "modules"
        for finding in reordered_findings
    )

    original_payload_module_id = payload_module["module_id"]
    root_module["module_id"] = "root_compatibility_drift"
    assert payload_module["module_id"] == original_payload_module_id

    findings = dr_compiler._v03_export_projection_findings(dr)
    assert any(
        finding["status"] == "FAIL"
        and finding["code"] == "DR_EXPORT_COMPATIBILITY_PROJECTION_DRIFT"
        and finding["path"] == "modules"
        for finding in findings
    )


def test_standard_compile_has_no_full_module_copy_in_cache_or_legacy_shell(
    baseline_dr: dict[str, Any],
):
    dr = baseline_dr

    assert "modules" not in dr["payload"]["graph_snapshot"]
    assert "modules" not in dr["legacy_blueprint"]
    assert not _contains_full_module_copy(
        dr["payload"]["graph_snapshot"]
    )
    assert not _contains_full_module_copy(dr["legacy_blueprint"])


@pytest.mark.parametrize(
    "duplicate_target",
    ("graph_snapshot", "legacy_blueprint"),
)
def test_nested_full_module_copy_blocks_public_compile(
    monkeypatch: pytest.MonkeyPatch,
    duplicate_target: str,
):
    original = dr_compiler._v03_compatibility_aliases

    def inject_nested_module_copy(*args, **kwargs):
        aliases = original(*args, **kwargs)
        payload = args[0] if args else kwargs["payload"]
        module_copy = deepcopy(payload["modules"])
        if duplicate_target == "graph_snapshot":
            payload["graph_snapshot"]["display_cache"] = {
                "modules": module_copy,
            }
        else:
            aliases["legacy_blueprint"]["compatibility_cache"] = {
                "modules": module_copy,
            }
        return aliases

    monkeypatch.setattr(
        dr_compiler,
        "_v03_compatibility_aliases",
        inject_nested_module_copy,
    )
    result = _compile()
    audit = result["metadata"]["v03_audit_report"]

    assert result["valid"] is False
    assert result["compiled_dr"] is None
    assert audit["summary"]["duplicate_source_check_fail"] >= 1
    assert any(
        finding["status"] == "FAIL"
        and finding["code"] == "DR_EXPORT_NONAUTHORITATIVE_MODULE_COPY"
        for finding in result["errors"]
    )


@pytest.mark.parametrize(
    "missing_path",
    _FROZEN_PATHS,
    ids=lambda path: ".".join(path),
)
def test_frozen_root_check_covers_full_a4_contract(
    missing_path: tuple[str, ...],
    baseline_dr: dict[str, Any],
):
    dr = deepcopy(baseline_dr)
    _remove_path(dr, missing_path)

    findings = dr_compiler._v03_frozen_root_field_findings(dr)

    assert any(finding["status"] == "FAIL" for finding in findings), (
        missing_path,
        findings,
    )
    assert not any(
        finding["code"] == "DR_V03_FROZEN_ROOT_FIELD_CHECK_PASSED"
        for finding in findings
    )


def test_frozen_versions_capabilities_and_authority_values_are_unchanged(
    baseline_dr: dict[str, Any],
):
    dr = baseline_dr

    assert dr["dr_version"] == "0.3"
    assert dr["dr_schema_version"] == "0.3.0"
    assert dr["schema_version"] == "0.4.0"
    assert dr["protocol_version"] == "0.4.0"
    assert dr["manifest"]["required_capabilities"] == _REQUIRED_CAPABILITIES
    assert dr["modules"] == dr["payload"]["modules"]


def test_runtime_dialogue_projection_remains_optional_but_checked_when_present(
    baseline_dr: dict[str, Any],
):
    legacy_compatible = deepcopy(baseline_dr)
    legacy_compatible["payload"]["audit_policy"][
        "runtime_dialogue_projection_expected"
    ] = False
    legacy_compatible["payload"].pop("runtime_dialogue_projection")
    absent_findings = dr_compiler._v03_frozen_root_field_findings(
        legacy_compatible
    )
    assert not any(
        finding["status"] == "FAIL"
        and finding["path"] == "payload.runtime_dialogue_projection"
        for finding in absent_findings
    )

    invalid = deepcopy(baseline_dr)
    invalid["payload"]["runtime_dialogue_projection"] = {}
    invalid_findings = dr_compiler._v03_frozen_root_field_findings(invalid)
    assert any(
        finding["status"] == "FAIL"
        and finding["path"] == "payload.runtime_dialogue_projection"
        for finding in invalid_findings
    )


def test_loader_uses_root_modules_only_when_payload_key_is_missing(
    baseline_dr: dict[str, Any],
):
    dr = baseline_dr
    root_module_count = len(dr["modules"])
    assert root_module_count > 0

    authoritative_empty = deepcopy(dr)
    authoritative_empty["payload"]["modules"] = []
    empty_summary = mock_load_dr_v0_3(authoritative_empty)
    assert empty_summary["module_count"] == 0

    legacy_missing = deepcopy(dr)
    legacy_missing["payload"].pop("modules")
    legacy_summary = mock_load_dr_v0_3(legacy_missing)
    assert legacy_summary["module_count"] == root_module_count


def test_repeated_compile_keeps_authority_surfaces_stable():
    first = _compile()
    second = _compile()

    assert first["valid"] is second["valid"] is True
    first_dr = first["compiled_dr"]
    second_dr = second["compiled_dr"]
    assert first_dr is not None
    assert second_dr is not None

    assert first_dr["payload"]["modules"] == second_dr["payload"]["modules"]
    assert first_dr["modules"] == second_dr["modules"]
    assert (
        first_dr["payload"]["graph_snapshot"]
        == second_dr["payload"]["graph_snapshot"]
    )
    assert first_dr["legacy_blueprint"] == second_dr["legacy_blueprint"]
