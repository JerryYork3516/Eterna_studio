"""ValidationReview / ValidationCheck — Contract §3.1.

Format / structure / completeness checks (system-automatic).
error blocks (package status=failed); warning does not block (status=warning).
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, Field

from ..schema_version import SCHEMA_VERSION
from ..util import now
from .enums import ReviewScope, ReviewStatus


class ValidationCheck(BaseModel):
    rule: str  # missing_field | invalid_edge | orphan_node | cycle_detected |
    #            layer_required_field | invalid_lock_level | mixed_empty ...
    level: Literal["error", "warning"]
    target_id: Optional[str] = None
    message: str


class ValidationReview(BaseModel):
    schema_version: str = SCHEMA_VERSION
    scope: ReviewScope
    status: ReviewStatus
    checks: List[ValidationCheck] = Field(default_factory=list)
    checked_at: datetime = Field(default_factory=now)
