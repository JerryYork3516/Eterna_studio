import { Handle, Position, type NodeProps } from "@xyflow/react";
import { type CSSProperties } from "react";
import { translate, type Language } from "@/i18n";
import type { WorkflowNode } from "@/lib/schema-types";
import { getNodeDefinition } from "@/registry/nodeRegistry";
import { getNodeInputSchema, type NodeInputField } from "@/registry/nodeInputs";
import { useCanvasStore } from "@/store/canvas-store";

type CanvasNodeData = {
  schemaNode: WorkflowNode;
  onRename?: (name: string) => void;
  onColor?: (color: string) => void;
  onInput?: (key: string, value: unknown) => void;
};

const HIDDEN_PARAM_KEYS = new Set(["mock_type", "parent_module", "parent_layer"]);

// Node Input Renderer: renders a node's inputs from its (front-end) input schema.
function NodeInputs({
  fields,
  data,
  language,
  onInput
}: {
  fields: NodeInputField[];
  data: Record<string, unknown>;
  language: Language;
  onInput: (key: string, value: unknown) => void;
}) {
  return (
    <div className="node-inputs">
      {fields.map((field) => {
        const label = translate(language, field.labelKey, field.labelFallback);
        const raw = data[field.key];
        if (field.type === "textarea") {
          return (
            <label key={field.key} className="node-inputs__row node-inputs__row--block">
              <span>{label}</span>
              <textarea
                className="nodrag"
                rows={2}
                value={typeof raw === "string" ? raw : ""}
                placeholder={field.placeholder}
                onChange={(event) => onInput(field.key, event.target.value)}
              />
            </label>
          );
        }
        if (field.type === "select") {
          return (
            <label key={field.key} className="node-inputs__row">
              <span>{label}</span>
              <select className="nodrag" value={typeof raw === "string" ? raw : ""} onChange={(event) => onInput(field.key, event.target.value)}>
                <option value="">--</option>
                {(field.options ?? []).map((option) => (
                  <option key={option.value} value={option.value}>
                    {translate(language, `input.option.${option.value}`, option.labelFallback)}
                  </option>
                ))}
              </select>
            </label>
          );
        }
        if (field.type === "slider") {
          const numeric = typeof raw === "number" ? raw : Number(raw) || field.min || 0;
          return (
            <label key={field.key} className="node-inputs__row">
              <span>{label}</span>
              <span className="node-inputs__slider">
                <input
                  className="nodrag"
                  type="range"
                  min={field.min}
                  max={field.max}
                  step={field.step}
                  value={numeric}
                  onChange={(event) => onInput(field.key, Number(event.target.value))}
                />
                <em>{numeric}</em>
              </span>
            </label>
          );
        }
        if (field.type === "boolean") {
          return (
            <label key={field.key} className="node-inputs__row node-inputs__row--toggle">
              <span>{label}</span>
              <input className="nodrag" type="checkbox" checked={Boolean(raw)} onChange={(event) => onInput(field.key, event.target.checked)} />
            </label>
          );
        }
        // text / number
        return (
          <label key={field.key} className="node-inputs__row">
            <span>{label}</span>
            <input
              className="nodrag"
              type={field.type === "number" ? "number" : "text"}
              min={field.min}
              max={field.max}
              step={field.step}
              value={raw === null || raw === undefined ? "" : String(raw)}
              placeholder={field.placeholder}
              onChange={(event) => onInput(field.key, field.type === "number" ? Number(event.target.value) : event.target.value)}
            />
          </label>
        );
      })}
    </div>
  );
}

export function WorkflowNodeCard({ data, selected }: NodeProps) {
  const language = useCanvasStore((state) => state.language);
  const { schemaNode, onRename, onColor, onInput } = data as CanvasNodeData;
  const nodeData = (schemaNode.data ?? {}) as Record<string, unknown>;
  const customName = typeof nodeData.ui_name === "string" ? nodeData.ui_name : "";
  const baseLabel = translate(language, schemaNode.title_key, schemaNode.title_fallback);
  const label = customName || baseLabel;
  const mockType = typeof nodeData.mock_type === "string" ? (nodeData.mock_type as string) : null;
  const effectiveType = mockType ?? schemaNode.type;
  const nodeDefinition = getNodeDefinition(effectiveType);
  const typeLabel = translate(language, `node.type.${effectiveType}`, nodeDefinition?.label ?? effectiveType);
  const hasInput = (schemaNode.ports?.inputs?.length ?? 0) > 0;
  const hasOutput = (schemaNode.ports?.outputs?.length ?? 0) > 0;
  const uiTags = Array.isArray(nodeData.ui_tags) ? (nodeData.ui_tags as unknown[]).map(String).filter(Boolean) : [];
  const uiGroup = typeof nodeData.ui_group === "string" ? nodeData.ui_group : "";
  const uiColor = typeof nodeData.ui_color === "string" ? nodeData.ui_color : "";
  const uiState = typeof nodeData.ui_state === "string" ? nodeData.ui_state.toLowerCase() : "ready";
  const dataState = uiState === "mock" ? "MOCK" : uiState === "disabled" ? "DISABLED" : "READY";
  const status = nodeDefinition?.status ?? dataState;
  const statusKey = status.toLowerCase();
  const stateLabel = translate(language, `node.status.${status}`, status);
  const lockLabel = translate(language, `lock.${schemaNode.lock_level}`, schemaNode.lock_level);
  const inputSchema = getNodeInputSchema(effectiveType);
  const inputKeys = new Set(inputSchema.map((field) => field.key));
  const paramEntries = Object.entries(nodeData).filter(
    ([key]) => !key.startsWith("ui_") && !HIDDEN_PARAM_KEYS.has(key) && !inputKeys.has(key)
  );

  return (
    <div
      className={`workflow-node lock-${schemaNode.lock_level} ${selected ? "is-selected" : ""}`}
      style={uiColor ? ({ "--node-accent": uiColor } as CSSProperties) : undefined}
    >
      {hasInput ? <Handle type="target" position={Position.Left} id="p_in" className="flow-handle flow-handle-left" /> : null}
      <div className="workflow-node__topline">
        <div className="workflow-node__type">{typeLabel}</div>
        <span className={`workflow-node__state-badge is-${statusKey}`}>{stateLabel}</span>
      </div>
      <div className="workflow-node__title">{label}</div>
      {uiGroup ? <div className="workflow-node__group">{uiGroup}</div> : null}
      {uiTags.length ? (
        <div className="workflow-node__tags">
          {uiTags.slice(0, 3).map((tag) => (
            <span key={tag}>{tag}</span>
          ))}
        </div>
      ) : null}

      {/* Fold panel: Inputs / Style / Params. Collapsed by default. */}
      <details className="workflow-node__params nodrag nopan" onPointerDown={(event) => event.stopPropagation()}>
        <summary>{translate(language, "node.params", "参数")}</summary>
        <div className="workflow-node__params-body">
          {onInput ? (
            <section className="node-fold__section">
              <h5>{translate(language, "node.section.inputs", "输入")}</h5>
              <NodeInputs fields={inputSchema} data={nodeData} language={language} onInput={onInput} />
            </section>
          ) : null}

          {onRename || onColor ? (
            <section className="node-fold__section">
              <h5>{translate(language, "node.section.style", "样式")}</h5>
              <div className="workflow-node__param-edit">
                {onRename ? (
                  <label>
                    <span>{translate(language, "field.name", "名称")}</span>
                    <input
                      className="nodrag"
                      defaultValue={label}
                      key={label}
                      onBlur={(event) => onRename(event.target.value)}
                      onKeyDown={(event) => {
                        if (event.key === "Enter") {
                          (event.target as HTMLInputElement).blur();
                        }
                      }}
                    />
                  </label>
                ) : null}
                {onColor ? (
                  <label>
                    <span>{translate(language, "field.color", "颜色")}</span>
                    <input type="color" className="nodrag" value={uiColor || "#4f8cff"} onChange={(event) => onColor(event.target.value)} />
                  </label>
                ) : null}
              </div>
            </section>
          ) : null}

          <section className="node-fold__section">
            <h5>{translate(language, "node.section.params", "参数")}</h5>
            <dl>
              <dt>{translate(language, "field.type", "类型")}</dt>
              <dd>{typeLabel}</dd>
              <dt>{translate(language, "field.status", "状态")}</dt>
              <dd>{stateLabel}</dd>
              <dt>{translate(language, "field.lockLevel", "锁定")}</dt>
              <dd>{lockLabel}</dd>
              {paramEntries.map(([key, value]) => (
                <div key={key} className="workflow-node__param-pair">
                  <dt>{key}</dt>
                  <dd>{typeof value === "object" ? JSON.stringify(value) : String(value)}</dd>
                </div>
              ))}
            </dl>
          </section>
        </div>
      </details>

      <div className="workflow-node__meta">{lockLabel}</div>
      {hasOutput ? <Handle type="source" position={Position.Right} id="p_out" className="flow-handle flow-handle-right" /> : null}
    </div>
  );
}
