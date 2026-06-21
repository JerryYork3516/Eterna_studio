"""ExportPreview — Contract §5."""

from __future__ import annotations

from typing import Any, Dict, List, Literal

from pydantic import BaseModel, Field

from ..schema_version import SCHEMA_VERSION


class ExportPreview(BaseModel):
    schema_version: str = SCHEMA_VERSION
    export_kind: Literal["workflow_json", "persona"]
    content: Dict[str, Any] = Field(default_factory=dict)
    warnings: List[str] = Field(default_factory=list)
