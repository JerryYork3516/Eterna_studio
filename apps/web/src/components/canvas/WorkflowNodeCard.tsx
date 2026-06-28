import { Handle, Position, type NodeProps } from "@xyflow/react";
import { useEffect, useState, type CSSProperties } from "react";
import { translate, type Language } from "@/i18n";
import { aiSlotClass, aiSlotLabel, inferAiSlot } from "@/lib/ai-slot";
import type { LLMConfigInput } from "@/lib/api";
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
const LLM_CONFIG_NODE_TYPES = new Set([
  "model_adapter",
  "llm_provider_router",
  "llm_adapter",
  "ai_slot_router",
  "local_model_adapter",
  "brain_config"
]);

function schemaLabel(field: NodeInputField, language: Language) {
  return translate(language, `input.${field.key}`, field.label);
}

function optionLabel(option: { value: string; label: string }, language: Language) {
  return translate(language, `input.option.${option.value}`, option.label);
}

function inputPlaceholder(field: NodeInputField, language: Language, fallback = "") {
  return translate(language, `input.placeholder.${field.key}`, field.placeholder ?? fallback);
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

// NodeInputRenderer is fully schema-driven from backend node-registry-v0.4.
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
                placeholder={inputPlaceholder(field, language)}
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
                <option value="">{translate(language, "node.option.none", "None")}</option>
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
                placeholder={inputPlaceholder(field, language, "{}")}
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
                placeholder={inputPlaceholder(field, language, translate(language, "node.placeholder.tags", "tag, tag"))}
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
                placeholder={inputPlaceholder(field, language, translate(language, "node.placeholder.keyValue", "{\"key\":\"value\"}"))}
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
              placeholder={inputPlaceholder(field, language)}
              onChange={(event) => onInput(field.key, field.type === "number" ? Number(event.target.value) : event.target.value)}
            />
          </label>
        );
      })}
    </div>
  );
}

function normalizeNodeStatus(rawStatus: string | undefined, hasAiSlot: boolean, llmStatus?: "READY" | "MOCK" | "ERROR" | "UNPLANNED") {
  if (llmStatus) {
    return llmStatus;
  }
  const status = String(rawStatus ?? "").toUpperCase();
  if (status === "READY") {
    return "READY";
  }
  if (status === "MOCK") {
    return "MOCK";
  }
  if (status === "ERROR") {
    return "ERROR";
  }
  return hasAiSlot ? "MOCK" : "UNPLANNED";
}

function isLLMConfigNode(node: WorkflowNode) {
  const type = String(node.type || "");
  return LLM_CONFIG_NODE_TYPES.has(type) || /llm|brain/i.test(type);
}

function resolveLLMNodeStatus({
  enabled,
  testStatus
}: {
  enabled: boolean | undefined;
  testStatus: "idle" | "testing" | "success" | "error";
}) {
  if (testStatus === "error") {
    return "ERROR";
  }
  if (enabled) {
    return testStatus === "success" ? "READY" : "UNPLANNED";
  }
  return "MOCK";
}

function BrainConfigSection({ language }: { language: Language }) {
  const llmConfig = useCanvasStore((state) => state.llmConfig);
  const llmTestStatus = useCanvasStore((state) => state.llmTestStatus);
  const llmTestMessage = useCanvasStore((state) => state.llmTestMessage);
  const loadLLMConfig = useCanvasStore((state) => state.loadLLMConfig);
  const saveLLMConfig = useCanvasStore((state) => state.saveLLMConfig);
  const testLLMConnection = useCanvasStore((state) => state.testLLMConnection);
  const [baseUrl, setBaseUrl] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [model, setModel] = useState("");
  const [enabled, setEnabled] = useState(false);
  const [fallbackToMock, setFallbackToMock] = useState(true);

  useEffect(() => {
    loadLLMConfig();
  }, [loadLLMConfig]);

  useEffect(() => {
    if (!llmConfig) {
      return;
    }
    setBaseUrl(llmConfig.base_url || "");
    setModel(llmConfig.model || "");
    setEnabled(Boolean(llmConfig.enabled));
    setFallbackToMock(Boolean(llmConfig.fallback_to_mock));
  }, [llmConfig]);

  const saveConfig = (patch: LLMConfigInput = {}) => {
    saveLLMConfig({
      base_url: baseUrl,
      api_key: apiKey || undefined,
      model,
      enabled,
      fallback_to_mock: fallbackToMock,
      ...patch
    });
    if (patch.api_key !== undefined) {
      setApiKey("");
    }
  };

  const testConfig = () => {
    testLLMConnection({
      base_url: baseUrl,
      api_key: apiKey || undefined,
      model,
      enabled,
      fallback_to_mock: fallbackToMock
    });
  };

  return (
    <section className="node-llm-config">
      <label className="node-inputs__row node-inputs__row--block">
        <span>{translate(language, "field.apiUrl", "API URL")}</span>
        <input
          className="nodrag"
          value={baseUrl}
          placeholder={translate(language, "llm.placeholder.apiUrl", "https://relay.example/v1")}
          onChange={(event) => setBaseUrl(event.target.value)}
          onBlur={() => saveConfig({ base_url: baseUrl })}
        />
      </label>
      <label className="node-inputs__row node-inputs__row--block">
        <span>{translate(language, "field.apiKey", "API Key")}</span>
        <input
          className="nodrag"
          type="password"
          value={apiKey}
          placeholder={
            llmConfig?.has_api_key
              ? translate(language, "field.apiKeySet", "Configured (leave blank to keep)")
              : translate(language, "field.apiKeyUnset", "Not configured")
          }
          onChange={(event) => setApiKey(event.target.value)}
          onBlur={() => {
            if (apiKey) {
              saveConfig({ api_key: apiKey });
            }
          }}
        />
      </label>
      <label className="node-inputs__row node-inputs__row--block">
        <span>{translate(language, "field.modelName", "Model")}</span>
        <input
          className="nodrag"
          value={model}
          placeholder={translate(language, "llm.placeholder.model", "gpt-4o-mini")}
          onChange={(event) => setModel(event.target.value)}
          onBlur={() => saveConfig({ model })}
        />
      </label>
      <label className="node-inputs__row node-inputs__row--toggle">
        <span>{translate(language, "field.enabled", "Enable real LLM")}</span>
        <input
          className="nodrag"
          type="checkbox"
          checked={enabled}
          onChange={(event) => {
            const checked = event.target.checked;
            setEnabled(checked);
            saveConfig({ enabled: checked });
          }}
        />
      </label>
      <label className="node-inputs__row node-inputs__row--toggle">
        <span>{translate(language, "field.fallbackToMock", "Fallback to mock")}</span>
        <input
          className="nodrag"
          type="checkbox"
          checked={fallbackToMock}
          onChange={(event) => {
            const checked = event.target.checked;
            setFallbackToMock(checked);
            saveConfig({ fallback_to_mock: checked });
          }}
        />
      </label>
      <div className="node-llm-config__status">
        <span>{translate(language, "field.testStatus", "Test status")}</span>
        <strong>{translate(language, `llm.testStatus.${llmTestStatus}`, llmTestStatus)}</strong>
      </div>
      {llmTestMessage ? <p className={`node-llm-config__message is-${llmTestStatus}`}>{llmTestMessage}</p> : null}
      <button type="button" className="node-llm-config__test nodrag" onClick={testConfig} disabled={llmTestStatus === "testing"}>
        {llmTestStatus === "testing" ? translate(language, "status.testingConnection", "Testing...") : translate(language, "button.testConnection", "Test Connection")}
      </button>
    </section>
  );
}

export function WorkflowNodeCard({ data, selected }: NodeProps) {
  const language = useCanvasStore((state) => state.language);
  const llmConfig = useCanvasStore((state) => state.llmConfig);
  const llmTestStatus = useCanvasStore((state) => state.llmTestStatus);
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
  const aiSlot = inferAiSlot(schemaNode);
  const showLLMConfig = isLLMConfigNode(schemaNode);
  const llmEnabled = llmConfig ? llmConfig.enabled : typeof nodeData.enabled === "boolean" ? nodeData.enabled : undefined;
  const llmStatus = showLLMConfig ? resolveLLMNodeStatus({ enabled: llmEnabled, testStatus: llmTestStatus }) : undefined;
  const normalizedStatus = normalizeNodeStatus(nodeDefinition?.status, aiSlot !== "none", llmStatus);
  const statusKey = normalizedStatus.toLowerCase();
  const stateLabel = translate(language, `node.status.${normalizedStatus}`, normalizedStatus);
  const lockLabel = translate(language, `lock.${schemaNode.lock_level}`, schemaNode.lock_level);
  const schemaNodeInputSchema = (schemaNode as unknown as { input_schema?: NodeInputField[] }).input_schema;
  const inputSchema: NodeInputField[] = schemaNodeInputSchema ?? nodeDefinition?.input_schema ?? [];
  const inputKeys = new Set(inputSchema.map((field) => field.key));
  const paramEntries = Object.entries(nodeData).filter(
    ([key]) => !key.startsWith("ui_") && !HIDDEN_PARAM_KEYS.has(key) && !inputKeys.has(key)
  );
  const isEnabled = typeof nodeData.enabled === "boolean" ? nodeData.enabled : true;

  return (
    <div
      className={`workflow-node lock-${schemaNode.lock_level} ${aiSlotClass(aiSlot)} ${aiSlot === "none" ? "is-ai-unplanned" : "has-ai-slot"} ${selected ? "is-selected" : ""}`}
      style={uiColor ? ({ "--node-accent": uiColor } as CSSProperties) : undefined}
    >
      {hasInput ? <Handle type="target" position={Position.Left} id="p_in" className="flow-handle flow-handle-left" /> : null}
      <header className="workflow-node__header">
        <div className="workflow-node__header-main">
          <div className="workflow-node__topline">
            <div className="workflow-node__type">{typeLabel}</div>
            <span className="workflow-node__badges-inline">
              <span className={`ai-slot-badge ${aiSlotClass(aiSlot)}`}>{aiSlotLabel(aiSlot)}</span>
              <span className={`workflow-node__state-badge is-${statusKey}`}>{stateLabel}</span>
            </span>
          </div>
          {onRename ? (
            <label className="workflow-node__name-field">
              <span>{translate(language, "node.header.name", "Name")}</span>
              <input
                className="nodrag"
                value={label}
                onChange={(event) => onRename(event.target.value)}
                aria-label={translate(language, "node.header.name", "Name")}
              />
            </label>
          ) : (
            <div className="workflow-node__title">{label}</div>
          )}
        </div>
        <label className="workflow-node__toggle nodrag">
          <span>{translate(language, "node.header.toggle", "Enabled")}</span>
          <input
            type="checkbox"
            checked={isEnabled}
            disabled={!onInput}
            onChange={(event) => onInput?.("enabled", event.target.checked)}
            aria-label={translate(language, "node.header.toggle", "Enabled")}
          />
        </label>
        {onColor ? (
          <label className="workflow-node__color-picker nodrag">
            <span>{translate(language, "node.header.color", "Color")}</span>
            <input
              type="color"
              value={uiColor || "#4f8cff"}
              onChange={(event) => onColor(event.target.value)}
              aria-label={translate(language, "node.header.color", "Color")}
            />
          </label>
        ) : null}
      </header>

      <details className="workflow-node__params nodrag nopan" onPointerDown={(event) => event.stopPropagation()}>
        <summary>{translate(language, "node.sections.core", "Core Params")}</summary>
        <div className="workflow-node__params-body">
          {onInput ? (
            <NodeInputRenderer fields={inputSchema} data={nodeData} language={language} onInput={onInput} />
          ) : (
            <div className="node-inputs__empty">{translate(language, "node.inputs.readonly", "Read-only node")}</div>
          )}
          {showLLMConfig ? <BrainConfigSection language={language} /> : null}
        </div>
      </details>

      <details className="workflow-node__params nodrag nopan" onPointerDown={(event) => event.stopPropagation()}>
        <summary>{translate(language, "node.sections.advanced", "Advanced Params")}</summary>
        <div className="workflow-node__params-body">
          {uiGroup ? <div className="workflow-node__group">{uiGroup}</div> : null}
          {uiTags.length ? (
            <div className="workflow-node__tags">
              {uiTags.slice(0, 3).map((tag) => (
                <span key={tag}>{tag}</span>
              ))}
            </div>
          ) : null}
          <dl>
            {paramEntries.length ? (
              paramEntries.map(([key, value]) => (
                <div key={key} className="workflow-node__param-pair">
                  <dt>{key}</dt>
                  <dd>{typeof value === "object" ? JSON.stringify(value) : String(value)}</dd>
                </div>
              ))
            ) : (
              <>
                <dt>{translate(language, "node.advanced.empty", "Extra")}</dt>
                <dd>{translate(language, "node.inputs.empty", "No schema inputs")}</dd>
              </>
            )}
          </dl>
        </div>
      </details>

      <details className="workflow-node__params nodrag nopan" onPointerDown={(event) => event.stopPropagation()}>
        <summary>{translate(language, "node.sections.runtime", "Runtime Info")}</summary>
        <div className="workflow-node__params-body">
          <dl>
            <dt>{translate(language, "field.nodeId", "Node ID")}</dt>
            <dd>{schemaNode.node_id}</dd>
            <dt>{translate(language, "field.status", "Status")}</dt>
            <dd>{stateLabel}</dd>
            <dt>{translate(language, "field.lockLevel", "Lock")}</dt>
            <dd>{lockLabel}</dd>
            <dt>{translate(language, "field.validation", "Validation")}</dt>
            <dd>{schemaNode.validation?.status ?? translate(language, "node.status.UNPLANNED", "UNPLANNED")}</dd>
          </dl>
        </div>
      </details>
      {hasOutput ? <Handle type="source" position={Position.Right} id="p_out" className="flow-handle flow-handle-right" /> : null}
    </div>
  );
}
