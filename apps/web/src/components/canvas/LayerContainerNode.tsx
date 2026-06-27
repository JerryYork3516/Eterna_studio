import { Handle, Position, type NodeProps } from "@xyflow/react";
import type { CSSProperties } from "react";
import { translate } from "@/i18n";
import type { WorkflowNode } from "@/lib/schema-types";
import { getNodeDefinition } from "@/registry/nodeRegistry";
import { useCanvasStore } from "@/store/canvas-store";

type CanvasNodeData = {
  schemaNode: WorkflowNode;
  viewLabel?: string;
  viewIndex?: number;
  groupLabel?: string;
  uiGroup?: string;
  uiTags?: string[];
  uiColor?: string;
};

function dataText(data: WorkflowNode["data"], key: string, fallback = "-") {
  const value = data?.[key];
  if (value === null || value === undefined || value === "") {
    return fallback;
  }
  return String(value);
}

export function LayerContainerNode({ data, selected }: NodeProps) {
  const language = useCanvasStore((state) => state.language);
  const { schemaNode, viewLabel, viewIndex, groupLabel, uiGroup, uiTags = [], uiColor } = data as CanvasNodeData;
  const label = viewLabel ?? translate(language, schemaNode.title_key, schemaNode.title_fallback);
  const typeLabel = getNodeDefinition(schemaNode.type)?.display_name ?? translate(language, `node.type.${schemaNode.type}`, schemaNode.type);
  const lockLabel = translate(language, `lock.${schemaNode.lock_level}`, schemaNode.lock_level);
  const moduleTier = typeof schemaNode.data?.module_tier === "string" ? schemaNode.data.module_tier : null;
  const reviewStatus =
    schemaNode.validation?.status ??
    (schemaNode.data?.validation && typeof schemaNode.data.validation === "object"
      ? String((schemaNode.data.validation as { status?: unknown }).status ?? "-")
      : "-");

  return (
    <div
      className={`layer-node lock-${schemaNode.lock_level} ${moduleTier ? `tier-${moduleTier}` : ""} ${selected ? "is-selected" : ""}`}
      style={uiColor ? ({ "--node-accent": uiColor } as CSSProperties) : undefined}
    >
      <Handle type="target" position={Position.Top} id="p_in" className="flow-handle layer-flow-handle-top" />
      {groupLabel ? <div className="layer-node__group">{groupLabel}</div> : null}
      <div className="layer-node__header">
        <div>
          <div className="layer-node__eyebrow">{typeLabel}</div>
          <div className="layer-node__title">
            {viewIndex ? <span>L{viewIndex}</span> : null}
            {translate(language, `layer.${schemaNode.layer_id}`, label)}
          </div>
        </div>
        <div className="layer-node__badges">
          {moduleTier ? <span className="tier-pill">{moduleTier}</span> : null}
          <span className="lock-pill">{lockLabel}</span>
        </div>
      </div>
      <details className="layer-node__params nodrag nopan" onPointerDown={(event) => event.stopPropagation()}>
        <summary>{translate(language, "node.params", "参数")}</summary>
        <div className="layer-node__description">{dataText(schemaNode.data, "description", schemaNode.title_fallback)}</div>
        {uiGroup || uiTags.length ? (
          <div className="layer-node__ui-meta">
            {uiGroup ? <span className="layer-node__ui-group">{uiGroup}</span> : null}
            {uiTags.slice(0, 3).map((tag) => (
              <span key={tag} className="layer-node__ui-tag">
                {tag}
              </span>
            ))}
          </div>
        ) : null}
        <div className="layer-node__grid">
          <span>{translate(language, "field.status")}</span>
          <strong>{dataText(schemaNode.data, "status")}</strong>
          <span>{translate(language, "field.version")}</span>
          <strong>{dataText(schemaNode.data, "version")}</strong>
          <span>{translate(language, "field.childrenCount")}</span>
          <strong>{dataText(schemaNode.data, "children_count", "0")}</strong>
          <span>{translate(language, "field.review")}</span>
          <strong>{reviewStatus}</strong>
        </div>
      </details>
      <Handle type="target" position={Position.Left} id="p_left_in" className="flow-handle flow-handle-left" />
      <Handle type="source" position={Position.Bottom} id="p_out" className="flow-handle layer-flow-handle-bottom" />
    </div>
  );
}
