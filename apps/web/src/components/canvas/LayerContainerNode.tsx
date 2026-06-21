import { Handle, Position, type NodeProps } from "@xyflow/react";
import { translate } from "@/i18n";
import type { WorkflowNode } from "@/lib/schema-types";
import { useCanvasStore } from "@/store/canvas-store";

type CanvasNodeData = {
  schemaNode: WorkflowNode;
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
  const { schemaNode } = data as CanvasNodeData;
  const label = translate(language, schemaNode.title_key, schemaNode.title_fallback);
  const lockLabel = translate(language, `lock.${schemaNode.lock_level}`, schemaNode.lock_level);
  const moduleTier = typeof schemaNode.data?.module_tier === "string" ? schemaNode.data.module_tier : null;
  const reviewStatus =
    schemaNode.validation?.status ??
    (schemaNode.data?.validation && typeof schemaNode.data.validation === "object"
      ? String((schemaNode.data.validation as { status?: unknown }).status ?? "-")
      : "-");

  return (
    <div className={`layer-node lock-${schemaNode.lock_level} ${moduleTier ? `tier-${moduleTier}` : ""} ${selected ? "is-selected" : ""}`}>
      <Handle type="target" position={Position.Top} id="p_in" className="flow-handle" />
      <div className="layer-node__header">
        <div>
          <div className="layer-node__eyebrow">{translate(language, "node.type.layer_container")}</div>
          <div className="layer-node__title">{label}</div>
        </div>
        <div className="layer-node__badges">
          {moduleTier ? <span className="tier-pill">{moduleTier}</span> : null}
          <span className="lock-pill">{lockLabel}</span>
        </div>
      </div>
      <div className="layer-node__description">{dataText(schemaNode.data, "description", schemaNode.title_fallback)}</div>
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
      <Handle type="source" position={Position.Bottom} id="p_out" className="flow-handle" />
    </div>
  );
}
