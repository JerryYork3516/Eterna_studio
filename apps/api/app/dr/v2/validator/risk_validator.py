"""Risk / safety validation + the declarative security_manifest checks.

Pure declarative checks. No real security system is implemented or called: no
AES, no license server, no keychain, no secure enclave. The security_manifest is
validated as data only.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from ....registry.module_catalog import module_catalog_map
from ..dr_v0_2_schema import DigitalResidentV02Gate, RiskLevelDecl
from .dr_validation_result import DRValidationResult, finding

_UNSAFE_LEVELS = {RiskLevelDecl.high, RiskLevelDecl.critical}


def validate_risk(
    model: DigitalResidentV02Gate,
    result: DRValidationResult,
    *,
    baseline: Optional[Dict[str, Any]] = None,
) -> None:
    rp = model.risk_policy

    # high/critical must require audit; critical must require human confirm.
    if rp.risk_level in _UNSAFE_LEVELS and not rp.audit_required:
        result.add(
            finding("FAIL", "DR_RISK_UNSAFE_NO_AUDIT", f"risk_level {rp.risk_level.value} requires audit_required=true", "risk_policy.audit_required")
        )
    if rp.risk_level == RiskLevelDecl.critical and not rp.human_confirm_required:
        result.add(
            finding("FAIL", "DR_RISK_UNSAFE_NO_CONFIRM", "critical risk_level requires human_confirm_required=true", "risk_policy.human_confirm_required")
        )
    if not rp.disclosure_required:
        result.add(
            finding("FAIL", "DR_RISK_NO_DISCLOSURE", "disclosure_required must be true (synthetic persona disclosure is mandatory)", "risk_policy.disclosure_required")
        )

    # blocked_modules referencing unknown module ids.
    modules = module_catalog_map()
    for i, mid in enumerate(rp.blocked_modules):
        if mid not in modules:
            result.add(finding("WARNING", "DR_RISK_BLOCKED_UNKNOWN", f"blocked_modules {mid!r} is not a known module", f"risk_policy.blocked_modules[{i}]"))

    # a declared tool whose path is also forbidden.
    forbidden = set(rp.forbidden_tool_paths)
    for i, tool in enumerate(model.capabilities.tools):
        if tool.tool_id in forbidden or (tool.module_id and tool.module_id in forbidden):
            result.add(
                finding("FAIL", "DR_RISK_FORBIDDEN_TOOL_DECLARED", f"tool {tool.tool_id} is in forbidden_tool_paths", f"capabilities.tools[{i}]")
            )

    # system_locked tamper detection (only when a baseline is provided).
    if rp.system_locked and baseline is not None:
        base_risk = (baseline.get("risk_policy") or {}) if isinstance(baseline, dict) else {}
        current = rp.model_dump()
        for fieldname in rp.system_locked_fields:
            if fieldname in base_risk and base_risk[fieldname] != current.get(fieldname):
                result.add(
                    finding("FAIL", "DR_RISK_LOCKED_FIELD_MODIFIED", f"system_locked field {fieldname!r} was modified", f"risk_policy.{fieldname}")
                )


def validate_security_manifest(model: DigitalResidentV02Gate, result: DRValidationResult) -> None:
    """Declarative security checks. No crypto is performed."""
    sm = model.security_manifest
    if sm.signature_required is not True:
        result.add(finding("FAIL", "DR_SEC_SIGNATURE_REQUIRED", "signature_required must be true", "security_manifest.signature_required"))
    if sm.watermark_required is not True:
        result.add(finding("FAIL", "DR_SEC_WATERMARK_REQUIRED", "watermark_required must be true", "security_manifest.watermark_required"))
    if sm.secure_loader_required is not True:
        result.add(finding("FAIL", "DR_SEC_LOADER_REQUIRED", "secure_loader_required must be true", "security_manifest.secure_loader_required"))
