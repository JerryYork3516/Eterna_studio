"""DR v0.2 validation result container + finding helper.

Pure data structures. No validation logic here. The finding shape mirrors the
rest of the codebase: {status, code, message, path} with status in
FAIL / WARNING / PASS.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

DR_VERSION_V0_2 = "0.2"


def finding(status: str, code: str, message: str, path: str) -> Dict[str, str]:
    """Build a single finding record (same shape as dr_compiler/_finding)."""
    return {"status": status, "code": code, "message": message, "path": path}


@dataclass
class DRValidationResult:
    """Aggregates findings + audit sub-results into the unified 9-key contract.

    `valid` is derived purely from the presence of FAIL findings, so the result
    is deterministic (no timestamps).
    """

    dr_version: str = DR_VERSION_V0_2
    errors: List[Dict[str, Any]] = field(default_factory=list)
    warnings: List[Dict[str, Any]] = field(default_factory=list)
    module_audit: Dict[str, Any] = field(default_factory=dict)
    layer_audit: Dict[str, Any] = field(default_factory=dict)
    compile_audit: Dict[str, Any] = field(default_factory=dict)
    orchestration_compatibility: bool = False
    pseudo_dag: List[Dict[str, Any]] = field(default_factory=list)

    def add(self, f: Dict[str, Any]) -> None:
        """Route a finding: FAIL -> errors, WARNING -> warnings, PASS -> ignored."""
        status = f.get("status")
        if status == "FAIL":
            self.errors.append(f)
        elif status == "WARNING":
            self.warnings.append(f)

    def add_all(self, findings: List[Dict[str, Any]]) -> None:
        for f in findings:
            self.add(f)

    @property
    def valid(self) -> bool:
        return len(self.errors) == 0

    def to_dict(self) -> Dict[str, Any]:
        """Return exactly the unified 9-key result contract."""
        return {
            "valid": self.valid,
            "dr_version": self.dr_version,
            "errors": self.errors,
            "warnings": self.warnings,
            "module_audit": self.module_audit,
            "layer_audit": self.layer_audit,
            "compile_audit": self.compile_audit,
            "orchestration_compatibility": self.orchestration_compatibility,
            "pseudo_dag": self.pseudo_dag,
        }
