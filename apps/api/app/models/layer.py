"""LayerContainerData — Contract §2.4 (M5: lock_level removed).

The layer's lock level is NOT stored here; the single authority is
WorkflowNode.lock_level. When that is `mixed`, real edit permission is
decided per child node.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel

from .approval import ChangeApproval
from .review import ValidationReview


class LayerContainerData(BaseModel):
    layer_index: int  # 1..13
    description: Optional[str] = None
    status: str = "empty"  # "empty" | "in_progress" | "complete"
    version: str = "1.0.0"
    children_count: int = 0
    validation: Optional[ValidationReview] = None
    change_approval: Optional[ChangeApproval] = None
