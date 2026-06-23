import { Handle, Position, type NodeProps } from "@xyflow/react";
import { type CSSProperties } from "react";
import { translate, type Language } from "@/i18n";
import type { WorkflowNode } from "@/lib/schema-types";
import { getNodeDefinition, type NodeInputField } from "@/registry/nodeRegistry";
import { useCanvasStore } from "@/store/canvas-store";

type CanvasNodeData = {
  schemaNode: WorkflowNode;
  onRename?: (name: string) => void;
  onColor?: (color: string) => void;
  onInput?: (key: string, value: unknown) => void;
};

const HIDDEN_PARAM_KEYS = new Set(["parent_module", "parent_layer"]);

function schemaLabel(field: NodeInputField, language: Language) {
  return translate(language, `input.${field.key}`, field.label);
}

function optionLabel(option: { value: string; label: string }, language: Language) {
  return translate(language, `input.option.${option.value}`, option.label);
}

function parseJsonInput(value: string) {
  if (!value.trim()) {
    return null;
  }
  try {
    return JSON.parse(value) as unknown;
  } catch {
    return value;
  }
}

// NodeInputRenderer is fully schema-driven from backend node-registry-v0.3.
function NodeInputRenderer({
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
  if (!fields.length) {
    return <div className="node-inputs__empty">{translate(language, "node.inputs.empty", "No schema inputs")}</div>;
  }

  return (
    <div className="node-inputs">
      {fields.map((field) => {
        const label = schemaLabel(field, language);
        const raw = data[field.key];
        if (field.type === "textarea") {
          return (
            <label key={field.key} className="node-inputs__row node-inputs__row--block">
              <span>{label}</span>
              <textarea
                className="nodrag"
                rows={2}
                value={typeof raw === "string" ? raw : ""}
                placeholder={field.placeholder ?? undefined}
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
                    {optionLabel(option, language)}
                  </option>
                ))}
              </select>
            </label>
          );
        }
        if (field.type === "multi_select") {
          const selected = Array.isArray(raw) ? raw.map(String) : [];
          return (
            <label key={field.key} className="node-inputs__row node-inputs__row--block">
              <span>{label}</span>
              <select
                className="nodrag"
                multiple
                value={selected}
                onChange={(event) =>
                  onInput(
                    field.key,
                    [...event.currentTarget.selectedOptions].map((option) => option.value)
                  )
                }
              >
                {(field.options ?? []).map((option) => (
                  <option key={option.value} value={option.value}>
                    {optionLabel(option, language)}
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
                  min={field.min ?? undefined}
                  max={field.max ?? undefined}
                  step={field.step ?? undefined}
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
        if (field.type === "color") {
          return (
            <label key={field.key} className="node-inputs__row">
              <span>{label}</span>
              <input className="nodrag" type="color" value={typeof raw === "string" ? raw : "#4f8cff"} onChange={(event) => onInput(field.key, event.target.value)} />
            </label>
          );
        }
        if (field.type === "json") {
          return (
            <label key={field.key} className="node-inputs__row node-inputs__row--block">
              <span>{label}</span>
              <textarea
                className="nodrag"
                rows={3}
                value={typeof raw === "string" ? raw : raw === undefined || raw === null ? "" : JSON.stringify(raw, null, 2)}
                placeholder={field.placeholder ?? "{}"}
                onChange={(event) => onInput(field.key, parseJsonInput(event.target.value))}
              />
            </label>
          );
        }
        if (field.type === "tags") {
          const text = Array.isArray(raw) ? raw.join(", ") : typeof raw === "string" ? raw : "";
          return (
            <label key={field.key} className="node-inputs__row node-inputs__row--block">
              <span>{label}</span>
              <input
                className="nodrag"
                type="text"
                value={text}
                placeholder={field.placeholder ?? "tag, tag"}
                onChange={(event) =>
                  onInput(
                    field.key,
                    event.target.value
                      .split(",")
                      .map((item) => item.trim())
                      .filter(Boolean)
                  )
                }
              />
            </label>
          );
        }
        if (field.type === "key_value") {
          const text = raw && typeof raw === "object" && !Array.isArray(raw) ? JSON.stringify(raw, null, 2) : "";
          return (
            <label key={field.key} className="node-inputs__row node-inputs__row--block">
              <span>{label}</span>
              <textarea
                className="nodrag"
                rows={3}
                value={text}
                placeholder={field.placeholder ?? '{"key":"value"}'}
                onChange={(event) => onInput(field.key, parseJsonInput(event.target.value))}
              />
            </label>
          );
        }
        if (field.type === "file") {
          return (
            <label key={field.key} className="node-inputs__row node-inputs__row--block">
              <span>{label}</span>
              <input
                className="nodrag"
                type="file"
                accept={field.accept?.join(",")}
                multiple={field.multiple}
                onChange={(event) =>
                  onInput(
                    field.key,
                    [...(event.target.files ?? [])].map((file) => ({ name: file.name, size: file.size, type: file.type }))
                  )
                }
              />
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
              min={field.min ?? undefined}
              max={field.max ?? undefined}
              step={field.step ?? undefined}
              value={raw === null || raw === undefined ? "" : String(raw)}
              placeholder={field.placeholder ?? undefined}
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
  const effectiveType = schemaNode.type;
  const nodeDefinition = getNodeDefinition(effectiveType);
  const typeLabel = translate(language, `node.type.${effectiveType}`, nodeDefinition?.display_name ?? effectiveType);
  const hasInput = (schemaNode.ports?.inputs?.length ?? 0) > 0;
  const hasOutput = (schemaNode.ports?.outputs?.length ?? 0) > 0;
  const uiTags = Array.isArray(nodeData.ui_tags) ? (nodeData.ui_tags as unknown[]).map(String).filter(Boolean) : [];
  const uiGroup = typeof nodeData.ui_group === "string" ? nodeData.ui_group : "";
  const uiColor = typeof nodeData.ui_color === "string" ? nodeData.ui_color : "";
  const status = nodeDefinition?.status;
  const statusKey = status?.toLowerCase() ?? "";
  const stateLabel = status ? translate(language, `node.status.${status}`, status) : "";
  const lockLabel = translate(language, `lock.${schemaNode.lock_level}`, schemaNode.lock_level);
  const schemaNodeInputSchema = (schemaNode as unknown as { input_schema?: NodeInputField[] }).input_schema;
  const inputSchema: NodeInputField[] = schemaNodeInputSchema ?? nodeDefinition?.input_schema ?? [];
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
        {status ? <span className={`workflow-node__state-badge is-${statusKey}`}>{stateLabel}</span> : null}
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
              <NodeInputRenderer fields={inputSchema} data={nodeData} language={language} onInput={onInput} />
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
