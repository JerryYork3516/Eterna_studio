"""TemplateDefinition — Contract §5."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel

from ..schema_version import SCHEMA_VERSION


class TemplateDefinition(BaseModel):
    schema_version: str = SCHEMA_VERSION
    template_type: str
    name: str
    description: Optional[str] = None
    builder: str
