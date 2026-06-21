import { Handle, Position, type NodeProps } from "@xyflow/react";
import { translate } from "@/i18n";
import type { WorkflowNode } from "@/lib/schema-types";
import { getNodeDefinition } from "@/registry/nodeRegistry";
import { useCanvasStore } from "@/store/canvas-store";

type CanvasNodeData = {
  schemaNode: WorkflowNode;
};

export function WorkflowNodeCard({ data, selected }: NodeProps) {
  const language = useCanvasStore((state) => state.language);
  const { schemaNode } = data as CanvasNodeData;
  const label = translate(language, schemaNode.title_key, schemaNode.title_fallback);
  const nodeDefinition = getNodeDefinition(schemaNode.type);
  const typeLabel = nodeDefinition?.label ?? translate(language, `node.type.${schemaNode.type}`, schemaNode.type);
  const hasInput = (schemaNode.ports?.inputs?.length ?? 0) > 0;
  const hasOutput = (schemaNode.ports?.outputs?.length ?? 0) > 0;

  return (
    <div className={`workflow-node lock-${schemaNode.lock_level} ${selected ? "is-selected" : ""}`}>
      {hasInput ? <Handle type="target" position={Position.Top} id="p_in" className="flow-handle" /> : null}
      <div className="workflow-node__type">{typeLabel}</div>
      <div className="workflow-node__title">{label}</div>
      <div className="workflow-node__meta">{translate(language, `lock.${schemaNode.lock_level}`, schemaNode.lock_level)}</div>
      {hasOutput ? <Handle type="source" position={Position.Bottom} id="p_out" className="flow-handle" /> : null}
    </div>
  );
}
