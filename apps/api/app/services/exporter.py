"""Legacy v0.2 export preview.

The mounted runtime path uses workflow_v0_3.export_preview_v0_3. This file
remains for historical compatibility only.

Two export kinds:
  - workflow_json: the workflow itself, serialized.
  - persona: a layer-ordered projection (generic; NOT hardwired to any single
    persona domain — it simply reads whatever layer_container nodes exist).

Warnings are surfaced from the shared validator so preview and validate agree.
"""

from __future__ import annotations

from typing import List

from ..models.enums import NodeType
from ..models.export import ExportPreview
from ..models.workflow import Workflow
from . import validator


def _collect_warnings(workflow: Workflow) -> List[str]:
    package, _layers, _nodes = validator.validate(workflow)
    return [f"[{c.level}] {c.rule}: {c.message}" for c in package.checks]


def export_preview(workflow: Workflow, export_kind: str) -> ExportPreview:
    warnings = _collect_warnings(workflow)

    if export_kind == "workflow_json":
        return ExportPreview(
            export_kind="workflow_json",
            content=workflow.model_dump(mode="json"),
            warnings=warnings,
        )

    # persona projection — ordered by layer_index.
    layers = [n for n in workflow.nodes if n.type == NodeType.layer_container]
    layers.sort(key=lambda n: int(n.data.get("layer_index", 0) or 0))

    persona_layers = [
        {
            "layer_index": n.data.get("layer_index"),
            "title_key": n.title_key,
            "title_fallback": n.title_fallback,
            "lock_level": n.lock_level.value,
            "status": n.data.get("status"),
            "version": n.data.get("version"),
            "data": n.data,
        }
        for n in layers
    ]

    content = {
        "schema_version": workflow.schema_version,
        "name": workflow.name,
        "template_type": workflow.template_type,
        "content_locale": workflow.content_locale,
        "layers": persona_layers,
    }
    return ExportPreview(
        export_kind="persona",
        content=content,
        warnings=warnings,
    )
