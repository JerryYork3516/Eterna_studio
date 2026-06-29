import { Handle, Position, type NodeProps } from "@xyflow/react";
import { useEffect, useState, type CSSProperties } from "react";
import { translate, type Language } from "@/i18n";
import { aiSlotClass, aiSlotLabel, inferAiSlot } from "@/lib/ai-slot";
import type { LLMProfileInput } from "@/lib/api";
import type { WorkflowNode } from "@/lib/schema-types";
import { getNodeDefinition, type NodeInputField } from "@/registry/nodeRegistry";
import { useCanvasStore } from "@/store/canvas-store";

type CanvasNodeData = {
  schemaNode: WorkflowNode;
  onRename?: (name: string) => void;
  onColor?: (color: string) => void;
  onInput?: (key: string, value: unknown) => void;
};

const HIDDEN_PARAM_KEYS = new Set([
  "parent_module",
  "parent_layer",
  "slot_binding",
  "node_role",
  "layer_id",
  "module_id",
  "context_requirements",
  "runtime_mapping",
  "dr_mapping",
  "input_schema",
  "output_schema",
  "i18n_keys",
  "collapsed_sections",
  "ui_color",
  "memory_entries",
  "memory_view_result",
  "memory_clear_result"
]);
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

function sectionTitle(language: Language, key: string, fallback: string) {
  return translate(language, key, fallback);
}

function prettyValue(value: unknown) {
  if (value === null || value === undefined) {
    return "";
  }
  if (typeof value === "string") {
    return value;
  }
  if (typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }
  return JSON.stringify(value);
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

export function BrainConfigSection({
  language,
  nodeData,
  onInput
}: {
  language: Language;
  nodeData: Record<string, unknown>;
  onInput?: (key: string, value: unknown) => void;
}) {
  const llmProfiles = useCanvasStore((state) => state.llmProfiles);
  const llmTestStatus = useCanvasStore((state) => state.llmTestStatus);
  const llmTestMessage = useCanvasStore((state) => state.llmTestMessage);
  const loadLLMConfig = useCanvasStore((state) => state.loadLLMConfig);
  const profileIds = llmProfiles?.profile_ids?.length ? llmProfiles.profile_ids : ["default", "deepseek", "mimo", "custom"];
  const [profileId, setProfileId] = useState(typeof nodeData.llm_profile_id === "string" && nodeData.llm_profile_id ? nodeData.llm_profile_id : "default");
  const [systemPrompt, setSystemPrompt] = useState(typeof nodeData.system_prompt === "string" ? nodeData.system_prompt : "");
  const [temperature, setTemperature] = useState(typeof nodeData.temperature === "number" ? String(nodeData.temperature) : "0.7");
  const [maxTokens, setMaxTokens] = useState(typeof nodeData.max_tokens === "number" ? String(nodeData.max_tokens) : "1024");
  const [modelOverride, setModelOverride] = useState(typeof nodeData.model_override === "string" ? nodeData.model_override : "");

  useEffect(() => {
    loadLLMConfig();
  }, [loadLLMConfig]);

  useEffect(() => {
    setProfileId(typeof nodeData.llm_profile_id === "string" && nodeData.llm_profile_id ? nodeData.llm_profile_id : "default");
    setSystemPrompt(typeof nodeData.system_prompt === "string" ? nodeData.system_prompt : "");
    setTemperature(typeof nodeData.temperature === "number" ? String(nodeData.temperature) : "0.7");
    setMaxTokens(typeof nodeData.max_tokens === "number" ? String(nodeData.max_tokens) : "1024");
    setModelOverride(typeof nodeData.model_override === "string" ? nodeData.model_override : "");
  }, [nodeData]);

  const commit = (patch: Record<string, unknown>) => {
    for (const [key, value] of Object.entries(patch)) {
      onInput?.(key, value);
    }
  };

  return (
    <section className="node-llm-config">
      <label className="node-inputs__row node-inputs__row--block">
        <span>{translate(language, "field.profile", "Profile")}</span>
        <select
          className="nodrag"
          value={profileId}
          onChange={(event) => {
            const next = event.target.value;
            setProfileId(next);
            commit({ llm_profile_id: next });
          }}
        >
          {profileIds.map((id) => (
            <option key={id} value={id}>
              {id}
            </option>
          ))}
        </select>
      </label>
      <label className="node-inputs__row node-inputs__row--block">
        <span>{translate(language, "field.systemPrompt", "System Prompt")}</span>
        <textarea
          className="nodrag"
          value={systemPrompt}
          rows={3}
          onChange={(event) => {
            const next = event.target.value;
            setSystemPrompt(next);
            commit({ system_prompt: next });
          }}
        />
      </label>
      <label className="node-inputs__row node-inputs__row--block">
        <span>{translate(language, "field.temperature", "Temperature")}</span>
        <input
          className="nodrag"
          type="number"
          min={0}
          max={2}
          step={0.1}
          value={temperature}
          onChange={(event) => {
            const next = event.target.value;
            setTemperature(next);
            commit({ temperature: Number(next) });
          }}
        />
      </label>
      <label className="node-inputs__row node-inputs__row--block">
        <span>{translate(language, "field.maxTokens", "Max Tokens")}</span>
        <input
          className="nodrag"
          type="number"
          min={1}
          step={1}
          value={maxTokens}
          onChange={(event) => {
            const next = event.target.value;
            setMaxTokens(next);
            commit({ max_tokens: Number(next) });
          }}
        />
      </label>
      <label className="node-inputs__row node-inputs__row--block">
        <span>{translate(language, "field.modelOverride", "Model Override")}</span>
        <input
          className="nodrag"
          value={modelOverride}
          onChange={(event) => {
            const next = event.target.value;
            setModelOverride(next);
            commit({ model_override: next });
          }}
        />
      </label>
      <div className="node-llm-config__status">
        <span>{translate(language, "field.testStatus", "Test status")}</span>
        <strong>{translate(language, `llm.testStatus.${llmTestStatus}`, llmTestStatus)}</strong>
      </div>
      {llmTestMessage ? <p className={`node-llm-config__message is-${llmTestStatus}`}>{llmTestMessage}</p> : null}
      <p className="node-llm-config__hint">{translate(language, "llm.nodeHint", "Credentials are managed in Runtime LLM Profiles.")}</p>
    </section>
  );
}

// Stage 6.7 — Memory Viewer / Clear section embedded in the Node card.
// All config (resident_id / namespace / memory_type) is read from the node's own
// fields; the section only views/clears via the backend (never the store).
function MemorySection({
  mode,
  nodeData,
  language,
  onInput
}: {
  mode: "viewer" | "clear";
  nodeData: Record<string, unknown>;
  language: Language;
  onInput?: (key: string, value: unknown) => void;
}) {
  const runtimeResult = useCanvasStore((state) => state.runtimeResult);
  const memoryClearResult = useCanvasStore((state) => state.memoryClearResult);
  const memoryStatus = useCanvasStore((state) => state.memoryStatus);
  const viewMemory = useCanvasStore((state) => state.viewMemory);
  const clearMemory = useCanvasStore((state) => state.clearMemory);
  const residentId = typeof runtimeResult?.resident_id === "string" ? runtimeResult.resident_id : "";
  const namespace = typeof nodeData.namespace === "string" && nodeData.namespace ? nodeData.namespace : "default";
  const memoryType = typeof nodeData.memory_type === "string" && nodeData.memory_type ? nodeData.memory_type : "interaction_log";
  const localEntries = Array.isArray(nodeData.memory_entries) ? nodeData.memory_entries : [];
  const memoryViewResult = (nodeData.memory_view_result as Record<string, unknown> | undefined) ?? null;
  const entries = localEntries;
  const clearResult = memoryClearResult && memoryClearResult.resident_id === residentId ? memoryClearResult : null;
  const t = (key: string, fallback: string) => translate(language, key, fallback);
  const actionError = memoryStatus === "error" ? t("memory.error", "记忆操作失败") : "";

  const handleView = async () => {
    const latest = await viewMemory(residentId, namespace, memoryType, 20);
    if (!latest) {
      return;
    }
    const nextEntries = latest.entries ?? latest.items ?? [];
    onInput?.("memory_entries", nextEntries);
    onInput?.("memory_view_result", latest);
  };

  const handleClear = async () => {
    const result = await clearMemory(residentId, namespace, memoryType);
    if (!result) {
      return;
    }
    onInput?.("memory_entries", []);
    onInput?.("memory_clear_result", result);
  };

  return (
    <div className="node-memory nodrag" onPointerDown={(event) => event.stopPropagation()}>
      <div className="node-memory__actions">
        <button type="button" onClick={() => void handleView()}>
          {t("memory.action.view", "查看记忆")}
        </button>
        {mode === "clear" ? (
          <button type="button" className="node-memory__danger" onClick={() => void handleClear()}>
            {t("memory.action.clear", "清空记忆")}
          </button>
        ) : null}
      </div>
      <div className="node-memory__meta-row">
        <span>{t("input.resident_id", "Resident ID")}: {residentId}</span>
        <span>{t("input.namespace", "Namespace")}: {namespace}</span>
        <span>{t("input.memory_type", "Memory Type")}: {translate(language, `memory.type.${memoryType}`, memoryType)}</span>
      </div>
      {actionError ? <p className="node-memory__error">{actionError}</p> : null}
      {clearResult ? (
        <p className="node-memory__meta">
          {t("memory.cleared", "已清空")}: {String(clearResult.cleared)} · {t("memory.deletedCount", "删除条数")}: {clearResult.deleted_count}
        </p>
      ) : null}
      <div className="node-memory__list">
        {memoryStatus === "loading" ? <p className="node-memory__hint">{t("memory.loading", "加载中…")}</p> : null}
        {entries && entries.length ? (
          <>
            <p className="node-memory__meta">
              {t("memory.count", "记录数")}: {entries.length} · {String((memoryViewResult?.storage_backend ?? localEntries?.[0]?.storage_backend) ?? t("common.empty", "空"))}
            </p>
            <ul>
              {entries.slice(0, 20).map((item, index) => (
                <li key={`${item.created_at ?? "entry"}-${index}`}>
                  <strong>{translate(language, `memory.type.${item.memory_type}`, item.memory_type ?? memoryType)}</strong>{" "}
                  {JSON.stringify(item.content ?? item)}
                </li>
              ))}
            </ul>
          </>
        ) : memoryStatus === "success" ? (
          <p className="node-memory__hint">{t("memory.empty", "暂无记忆")}</p>
        ) : null}
      </div>
    </div>
  );
}

export function WorkflowNodeCard({ data, selected }: NodeProps) {
  const language = useCanvasStore((state) => state.language);
  const llmProfiles = useCanvasStore((state) => state.llmProfiles);
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
  const nodeColor = typeof schemaNode.ui_color === "string" && schemaNode.ui_color ? schemaNode.ui_color : uiColor;
  const aiSlot = inferAiSlot(schemaNode);
  const showLLMConfig = isLLMConfigNode(schemaNode);
  const memoryMode: "viewer" | "clear" | null =
    String(effectiveType) === "memory_viewer" ? "viewer" : String(effectiveType) === "memory_clear" ? "clear" : null;
  const llmEnabled = llmProfiles ? llmProfiles.profiles?.[llmProfiles.default_profile_id ?? "default"]?.enabled : typeof nodeData.enabled === "boolean" ? nodeData.enabled : undefined;
  const llmStatus = showLLMConfig ? resolveLLMNodeStatus({ enabled: llmEnabled, testStatus: llmTestStatus }) : undefined;
  const normalizedStatus = normalizeNodeStatus(nodeDefinition?.status, aiSlot !== "none", llmStatus);
  const statusKey = normalizedStatus.toLowerCase();
  const stateLabel = translate(language, `node.status.${normalizedStatus}`, normalizedStatus);
  const lockLabel = translate(language, `lock.${schemaNode.lock_level}`, schemaNode.lock_level);
  // Runtime output written back by a module-canvas run (output node only).
  const isOutputNode = String(effectiveType) === "output";
  const outputText = isOutputNode && typeof nodeData.output_text === "string" ? nodeData.output_text : "";
  const lastStatus = typeof nodeData.last_status === "string" ? nodeData.last_status : "";
  const schemaNodeInputSchema = (schemaNode as unknown as { input_schema?: NodeInputField[] }).input_schema;
  const inputSchema: NodeInputField[] = schemaNodeInputSchema ?? nodeDefinition?.input_schema ?? [];
  const outputSchema = (schemaNode as unknown as { output_schema?: unknown[] }).output_schema ?? [];
  const slotBinding = typeof schemaNode.slot_binding === "string" ? schemaNode.slot_binding : typeof nodeData.slot_binding === "string" ? nodeData.slot_binding : "";
  const contextRequirements = Array.isArray(schemaNode.context_requirements)
    ? schemaNode.context_requirements.map(String).filter(Boolean)
    : Array.isArray(nodeData.context_requirements)
      ? nodeData.context_requirements.map(String).filter(Boolean)
      : [];
  const collapsedSections = new Set(
    Array.isArray(schemaNode.collapsed_sections)
      ? schemaNode.collapsed_sections.map(String)
      : Array.isArray(nodeData.collapsed_sections)
        ? nodeData.collapsed_sections.map(String)
        : ["core", "advanced", "input_schema", "output_schema", "slot_binding", "runtime"]
  );
  const inputKeys = new Set(inputSchema.map((field) => field.key));
  const paramEntries = Object.entries(nodeData).filter(
    ([key]) => !key.startsWith("ui_") && !HIDDEN_PARAM_KEYS.has(key) && !inputKeys.has(key)
  );
  const isEnabled = typeof nodeData.enabled === "boolean" ? nodeData.enabled : true;
  const sections = {
    core: collapsedSections.has("core"),
    advanced: collapsedSections.has("advanced"),
    input_schema: collapsedSections.has("input_schema"),
    output_schema: collapsedSections.has("output_schema"),
    slot_binding: collapsedSections.has("slot_binding"),
    runtime: collapsedSections.has("runtime")
  };

  return (
    <div
      className={`workflow-node lock-${schemaNode.lock_level} ${aiSlotClass(aiSlot)} ${aiSlot === "none" ? "is-ai-unplanned" : "has-ai-slot"} ${selected ? "is-selected" : ""}`}
      style={nodeColor ? ({ "--node-accent": nodeColor, backgroundColor: nodeColor } as CSSProperties) : undefined}
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

      {isOutputNode ? (
        <div className="workflow-node__output nodrag nopan" onPointerDown={(event) => event.stopPropagation()}>
          <div className="workflow-node__output-head">
            <span className="workflow-node__output-label">{translate(language, "node.output.text", "Output")}</span>
            {lastStatus ? <span className="workflow-node__output-status">{lastStatus}</span> : null}
          </div>
          {outputText ? (
            <p className="workflow-node__output-text">{outputText}</p>
          ) : (
            <p className="workflow-node__output-empty">{translate(language, "node.output.empty", "No output yet")}</p>
          )}
        </div>
      ) : null}

      <details className="workflow-node__params nodrag nopan" onPointerDown={(event) => event.stopPropagation()} open={!sections.core}>
        <summary>{sectionTitle(language, "node.sections.core", "Core Params")}</summary>
        <div className="workflow-node__params-body">
          {onInput ? (
            <NodeInputRenderer fields={inputSchema} data={nodeData} language={language} onInput={onInput} />
          ) : (
            <div className="node-inputs__empty">{translate(language, "node.inputs.readonly", "Read-only node")}</div>
          )}
          {showLLMConfig ? <BrainConfigSection language={language} nodeData={nodeData} onInput={onInput} /> : null}
          {memoryMode ? <MemorySection mode={memoryMode} nodeData={nodeData} language={language} onInput={onInput} /> : null}
        </div>
      </details>

      <details className="workflow-node__params nodrag nopan" onPointerDown={(event) => event.stopPropagation()} open={!sections.advanced}>
        <summary>{sectionTitle(language, "node.sections.advanced", "Advanced Params")}</summary>
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
                  <dd>{prettyValue(value)}</dd>
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

      <details className="workflow-node__params nodrag nopan" onPointerDown={(event) => event.stopPropagation()} open={!sections.runtime}>
        <summary>{sectionTitle(language, "node.sections.runtime", "Runtime Info")}</summary>
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
            <dt>{translate(language, "node.sections.slotBinding", "Slot Binding")}</dt>
            <dd>{slotBinding || translate(language, "node.slotBinding.none", "None")}</dd>
            <dt>{translate(language, "node.sections.inputSchema", "Input Schema")}</dt>
            <dd>{inputSchema.length ? inputSchema.map((field) => field.key).join(", ") : translate(language, "node.inputs.empty", "No schema inputs")}</dd>
            <dt>{translate(language, "node.sections.outputSchema", "Output Schema")}</dt>
            <dd>{outputSchema.length ? outputSchema.length.toString() : translate(language, "node.inputs.empty", "No schema inputs")}</dd>
            <dt>{translate(language, "node.sections.context", "Context")}</dt>
            <dd>{contextRequirements.length ? contextRequirements.join(", ") : translate(language, "node.context.empty", "None")}</dd>
          </dl>
        </div>
      </details>
      {hasOutput ? <Handle type="source" position={Position.Right} id="p_out" className="flow-handle flow-handle-right" /> : null}
    </div>
  );
}
