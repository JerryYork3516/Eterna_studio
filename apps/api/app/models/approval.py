"""ChangeApproval / ChangeDiff — Contract §3.2 (M4 minimal structure).

Human approval for core-layer modifications. Stored / echoed only in MVP.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

from ..schema_version import SCHEMA_VERSION
from ..util import gen_id, now
from .enums import ChangeApprovalStatus


class ChangeDiff(BaseModel):  # M4
    before: Dict[str, Any] = Field(default_factory=dict)
    after: Dict[str, Any] = Field(default_factory=dict)
    changed_fields: List[str] = Field(default_factory=list)


class ChangeApproval(BaseModel):
    schema_version: str = SCHEMA_VERSION
    approval_id: str = Field(default_factory=lambda: gen_id("ap"))
    target_kind: Literal["node", "layer"]
    target_id: str
    status: ChangeApprovalStatus = ChangeApprovalStatus.draft
    reason: Optional[str] = None
    diff: Optional[ChangeDiff] = None
    resulting_version: Optional[str] = None
    created_at: datetime = Field(default_factory=now)
