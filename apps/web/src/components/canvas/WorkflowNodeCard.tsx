import { Handle, Position, type NodeProps } from "@xyflow/react";
import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type CSSProperties,
  type InputHTMLAttributes,
  type ReactNode,
  type TextareaHTMLAttributes
} from "react";
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
  onFieldFocus?: (key: string) => void;
};

type FlowNodeLike = {
  data?: unknown;
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
  "catalog_preconfigured",
  "catalog_module_id",
  "catalog_node_id",
  "module_instance_id",
  "node_type",
  "params",
  "fields",
  "outputs",
  "metadata",
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

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value && typeof value === "object" && !Array.isArray(value));
}

const ModuleWorkflowNodesContext = createContext<WorkflowNode[]>([]);

export function WorkflowNodeCardModuleNodesProvider({ nodes, children }: { nodes: FlowNodeLike[]; children: ReactNode }) {
  const schemaNodes = useMemo(
    () =>
      nodes
        .map((node) => {
          const data = isRecord(node.data) ? node.data : {};
          return isRecord(data.schemaNode) ? (data.schemaNode as WorkflowNode) : null;
        })
        .filter((node): node is WorkflowNode => Boolean(node)),
    [nodes]
  );

  return <ModuleWorkflowNodesContext.Provider value={schemaNodes}>{children}</ModuleWorkflowNodesContext.Provider>;
}

function useModuleWorkflowNodes() {
  return useContext(ModuleWorkflowNodesContext);
}

function fieldsFromNodeData(data: Record<string, unknown>): Record<string, unknown>[] {
  if (Array.isArray(data.fields)) {
    return data.fields.filter(isRecord);
  }
  const params = isRecord(data.params) ? data.params : {};
  return Array.isArray(params.fields) ? params.fields.filter(isRecord) : [];
}

function paramsFromNodeData(data: Record<string, unknown>) {
  return isRecord(data.params) ? data.params : {};
}

function workflowNodeData(node: WorkflowNode): Record<string, unknown> {
  return isRecord(node.data) ? node.data : {};
}

function workflowNodeType(node: WorkflowNode): string {
  const data = workflowNodeData(node);
  return String(data.node_type || node.type || "");
}

function stringValue(value: unknown): string {
  return typeof value === "string" && value.trim() ? value.trim() : "";
}

function compactValue(value: unknown): unknown {
  if (Array.isArray(value)) {
    return value.map(compactValue).filter((item) => !isEmptyDisplayValue(item));
  }
  if (isRecord(value)) {
    return Object.fromEntries(
      Object.entries(value)
        .map(([key, item]) => [key, compactValue(item)] as const)
        .filter(([, item]) => !isEmptyDisplayValue(item))
    );
  }
  return value;
}

function isEmptyDisplayValue(value: unknown): boolean {
  if (value === null || value === undefined) {
    return true;
  }
  if (typeof value === "string") {
    return value.trim() === "";
  }
  if (Array.isArray(value)) {
    return value.length === 0;
  }
  if (isRecord(value)) {
    return Object.keys(value).length === 0;
  }
  return false;
}

function moduleIdentity(data: Record<string, unknown>, node?: WorkflowNode) {
  return {
    instanceId: stringValue(data.module_instance_id) || stringValue(data.parent_module),
    catalogModuleId: stringValue(data.catalog_module_id) || stringValue(node?.module_id) || stringValue(data.module_id),
  };
}

function findSiblingModuleOutputNode(current: WorkflowNode, moduleNodes: WorkflowNode[]): WorkflowNode | null {
  const currentData = workflowNodeData(current);
  const currentIdentity = moduleIdentity(currentData, current);
  return (
    moduleNodes.find((candidate) => {
      if (candidate.node_id === current.node_id || workflowNodeType(candidate) !== "module_output") {
        return false;
      }
      const candidateData = workflowNodeData(candidate);
      const candidateIdentity = moduleIdentity(candidateData, candidate);
      if (currentIdentity.instanceId && candidateIdentity.instanceId && currentIdentity.instanceId !== candidateIdentity.instanceId) {
        return false;
      }
      if (currentIdentity.catalogModuleId && candidateIdentity.catalogModuleId && currentIdentity.catalogModuleId !== candidateIdentity.catalogModuleId) {
        return false;
      }
      return true;
    }) ?? null
  );
}

function moduleOutputValue(outputNode: WorkflowNode | null): { outputKey: string; output: Record<string, unknown> } {
  if (!outputNode) {
    return { outputKey: "", output: {} };
  }
  const data = workflowNodeData(outputNode);
  const params = paramsFromNodeData(data);
  const outputs = isRecord(data.outputs) ? data.outputs : {};
  const outputKey = stringValue(params.output_key) || stringValue(outputs.module_output);
  const output = outputKey && isRecord(outputs[outputKey]) ? outputs[outputKey] : {};
  return { outputKey, output };
}

const NORMALIZATION_RESULT_KEYS = [
  "normalized_result",
  "normalized",
  "normalization_result",
  "output",
  "outputs",
  "policy",
  "resident_identity",
  "content_safety_policy",
  "behavior_safety_policy",
  "data_safety_policy",
  "interaction_safety_policy",
  "risk_policy",
  "risk_signal_summary",
  "risk_level_policy",
  "risk_response_strategy",
  "human_review_policy",
  "hard_block_policy",
  "audit_log_policy",
  "safe_redirect_policy",
];

const POLICY_OUTPUT_KEYS = [
  "content_safety_policy",
  "behavior_safety_policy",
  "data_safety_policy",
  "interaction_safety_policy",
  "risk_policy",
];

function firstRecordByKeys(sources: Record<string, unknown>[], keys: string[]): Record<string, unknown> {
  for (const source of sources) {
    for (const key of keys) {
      if (isRecord(source[key])) {
        return source[key];
      }
    }
  }
  return {};
}

function normalizedResultValue(data: Record<string, unknown>, siblingOutput: { outputKey: string; output: Record<string, unknown> }) {
  const params = paramsFromNodeData(data);
  const direct = firstRecordByKeys([data, params], NORMALIZATION_RESULT_KEYS);
  if (!isEmptyDisplayValue(direct)) {
    return displayObjectEntries(direct, new Set(["compile_time_only"]));
  }
  for (const key of POLICY_OUTPUT_KEYS) {
    if (isRecord(siblingOutput.output[key])) {
      return displayObjectEntries(siblingOutput.output[key], new Set(["compile_time_only"]));
    }
  }
  if (isRecord(siblingOutput.output.fields)) {
    return displayObjectEntries(siblingOutput.output.fields);
  }
  return displayObjectEntries(siblingOutput.output, new Set(["compile_time_only"]));
}

function valueByCandidateKeys(sources: Record<string, unknown>[], keys: string[]): unknown {
  for (const source of sources) {
    for (const key of keys) {
      if (!isEmptyDisplayValue(source[key])) {
        return source[key];
      }
    }
  }
  return undefined;
}

function displayObjectEntries(value: Record<string, unknown>, omittedKeys: Set<string> = new Set()) {
  return Object.fromEntries(
    Object.entries(value)
      .filter(([key]) => !omittedKeys.has(key))
      .map(([key, item]) => [key, compactValue(item)] as const)
      .filter(([, item]) => !isEmptyDisplayValue(item))
  );
}

function localizedFieldText(field: Record<string, unknown>, key: "label" | "placeholder" | "help", language: Language, fallback: string) {
  const i18n = isRecord(field.i18n_keys) ? field.i18n_keys : {};
  const i18nKey = typeof i18n[key] === "string" ? i18n[key] : "";
  return i18nKey ? translate(language, i18nKey, fallback) : fallback;
}

function translateIfPresent(language: Language, key: string): string {
  const marker = `__missing_${key}__`;
  const translated = translate(language, key, marker);
  return translated === marker ? "" : translated;
}

function stableI18nKeyPart(value: string) {
  return value
    .trim()
    .replace(/([a-z0-9])([A-Z])/g, "$1_$2")
    .replace(/[^a-zA-Z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "")
    .toLowerCase();
}

function localizedCoreKey(language: Language, key: string) {
  return (
    translateIfPresent(language, `assembly.field.${stableI18nKeyPart(key)}`) ||
    translateIfPresent(language, `node.coreParams.key.${key}`) ||
    translateIfPresent(language, `field.identity.${key}.label`) ||
    key
  );
}

function localizedCoreValue(language: Language, value: string) {
  const normalized = stableI18nKeyPart(value);
  return (
    translateIfPresent(language, `validation.${value}`) ||
    translateIfPresent(language, `validation.${normalized}`) ||
    translateIfPresent(language, `assembly.status.${normalized}`) ||
    translateIfPresent(language, `node.coreParams.value.${value}`) ||
    translateIfPresent(language, `node.coreParams.key.${value}`) ||
    translateIfPresent(language, `field.identity.${value}.label`) ||
    value
  );
}

type FieldReferenceType = "required" | "optional" | "forbidden";

type FieldReferenceOption = {
  value: string;
  label_key?: string;
  layer_id?: string;
  module_id?: string;
};

type FieldReferenceEntry = {
  reference_id?: string;
  reference_type?: string;
  layer_id?: string;
  module_id?: string;
  field_id?: string;
  path?: string;
  usage?: string;
  usage_key?: string;
  i18n_keys?: Record<string, unknown>;
};

type TextConfigChecklistOption = {
  option_id: string;
  default_selected?: boolean;
  i18n_keys?: Record<string, unknown>;
  label_key?: string;
  description_key?: string;
  help_key?: string;
  tooltip_key?: string;
  error_key?: string;
};

type TextConfigChecklist = {
  raw: Record<string, unknown>;
  presetId: string;
  applyPresetLabelKey: string;
  selectedOptions: string[];
  defaultSelectedOptions: string[];
  defaultOptions: TextConfigChecklistOption[];
  optionalOptions: TextConfigChecklistOption[];
  customText: string;
};

function asFieldReferenceEntries(value: unknown): FieldReferenceEntry[] {
  return Array.isArray(value) ? value.filter(isRecord).map((item) => item as FieldReferenceEntry) : [];
}

function asFieldReferenceOptions(value: unknown): FieldReferenceOption[] {
  return Array.isArray(value)
    ? value
        .filter(isRecord)
        .map((item) => ({
          value: String(item.value || ""),
          label_key: typeof item.label_key === "string" ? item.label_key : undefined,
          layer_id: typeof item.layer_id === "string" ? item.layer_id : undefined,
          module_id: typeof item.module_id === "string" ? item.module_id : undefined,
        }))
        .filter((item) => item.value)
    : [];
}

function referenceType(value: unknown): FieldReferenceType {
  return value === "required" || value === "forbidden" ? value : "optional";
}

function referenceI18nLabel(reference: FieldReferenceEntry, key: "layer" | "module" | "field", language: Language) {
  const i18n = isRecord(reference.i18n_keys) ? reference.i18n_keys : {};
  const i18nKey = typeof i18n[key] === "string" ? i18n[key] : "";
  const rawValue = key === "layer" ? reference.layer_id : key === "module" ? reference.module_id : reference.field_id;
  return i18nKey ? translate(language, i18nKey, rawValue || i18nKey) : rawValue || translate(language, "common.notGenerated", "common.notGenerated");
}

function referenceOptionLabel(option: FieldReferenceOption, language: Language) {
  return option.label_key ? translate(language, option.label_key, option.value) : option.value;
}

function referenceDisplayPath(reference: FieldReferenceEntry, language: Language) {
  return [referenceI18nLabel(reference, "layer", language), referenceI18nLabel(reference, "module", language), referenceI18nLabel(reference, "field", language)].join(" / ");
}

function updateReferencePath(reference: FieldReferenceEntry) {
  return {
    ...reference,
    path: [reference.layer_id, reference.module_id, reference.field_id].filter(Boolean).join("/"),
  };
}

function i18nText(language: Language, key: string) {
  return translate(language, key, key);
}

function statusText(language: Language, value: unknown, fallbackKey = "node.status.UNPLANNED") {
  const raw = typeof value === "string" && value.trim() ? value.trim() : "";
  if (!raw) {
    return translate(language, fallbackKey, "UNPLANNED");
  }
  const normalized = raw.toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_+|_+$/g, "");
  const marker = `__missing__${normalized}`;
  const assemblyLabel = translate(language, `assembly.status.${normalized}`, marker);
  if (assemblyLabel !== marker) {
    return assemblyLabel;
  }
  return translate(language, `node.status.${raw}`, raw);
}

function stringArray(value: unknown): string[] {
  return Array.isArray(value) ? value.map((item) => (typeof item === "string" ? item.trim() : "")).filter(Boolean) : [];
}

function asChecklistOptions(value: unknown): TextConfigChecklistOption[] {
  return Array.isArray(value)
    ? value
        .filter(isRecord)
        .map((item) => ({
          option_id: String(item.option_id || ""),
          default_selected: typeof item.default_selected === "boolean" ? item.default_selected : undefined,
          i18n_keys: isRecord(item.i18n_keys) ? item.i18n_keys : undefined,
          label_key: typeof item.label_key === "string" ? item.label_key : undefined,
          description_key: typeof item.description_key === "string" ? item.description_key : undefined,
          help_key: typeof item.help_key === "string" ? item.help_key : undefined,
          tooltip_key: typeof item.tooltip_key === "string" ? item.tooltip_key : undefined,
          error_key: typeof item.error_key === "string" ? item.error_key : undefined,
        }))
        .filter((item) => item.option_id)
    : [];
}

function textConfigChecklistFromParams(params: Record<string, unknown>): TextConfigChecklist | null {
  const raw = isRecord(params.checkbox_config)
    ? params.checkbox_config
    : isRecord(params.checklist_config)
      ? params.checklist_config
      : null;
  if (!raw) {
    return null;
  }
  const defaultOptions = asChecklistOptions(raw.default_options);
  const optionalOptions = asChecklistOptions(raw.optional_options);
  const fallbackOptions = defaultOptions.length || optionalOptions.length ? [] : asChecklistOptions(raw.options);
  const effectiveDefaultOptions = defaultOptions.length ? defaultOptions : fallbackOptions.filter((option) => option.default_selected !== false);
  const defaultSelectedOptions = stringArray(raw.default_selected_options);
  const fallbackSelected = defaultSelectedOptions.length
    ? defaultSelectedOptions
    : effectiveDefaultOptions.filter((option) => option.default_selected !== false).map((option) => option.option_id);
  return {
    raw,
    presetId: typeof raw.preset_id === "string" && raw.preset_id.trim() ? raw.preset_id.trim() : "human_empathy_cn_v0_1",
    applyPresetLabelKey:
      typeof raw.apply_preset_label_key === "string" && raw.apply_preset_label_key.trim()
        ? raw.apply_preset_label_key.trim()
        : "node.checklist.applyHumanEmpathyCnTemplate",
    selectedOptions: Array.isArray(raw.selected_options) ? stringArray(raw.selected_options) : fallbackSelected,
    defaultSelectedOptions: fallbackSelected,
    defaultOptions: defaultOptions.length ? defaultOptions : effectiveDefaultOptions,
    optionalOptions,
    customText: typeof raw.custom_text === "string" ? raw.custom_text : "",
  };
}

function checklistOptionLabel(option: TextConfigChecklistOption, language: Language) {
  const i18n = isRecord(option.i18n_keys) ? option.i18n_keys : {};
  const key = typeof i18n.label === "string" ? i18n.label : option.label_key || "";
  return key ? translate(language, key, option.option_id) : option.option_id;
}

function checklistOptionText(option: TextConfigChecklistOption, language: Language, keyName: "description" | "help" | "tooltip" | "error") {
  const i18n = isRecord(option.i18n_keys) ? option.i18n_keys : {};
  const directKey = typeof i18n[keyName] === "string" ? i18n[keyName] : "";
  const fallbackKey =
    keyName === "description"
      ? option.description_key
      : keyName === "help"
        ? option.help_key
        : keyName === "tooltip"
          ? option.tooltip_key
          : option.error_key;
  const key = directKey || fallbackKey || "";
  return key ? translateIfPresent(language, key) : "";
}

function updateFieldValue(fields: Record<string, unknown>[], index: number, value: unknown) {
  return fields.map((field, fieldIndex) => (fieldIndex === index ? { ...field, value } : field));
}

function compileTimeFieldKey(field: Record<string, unknown>, index: number) {
  return String(field.field_id || field.key || field.name || field.id || `field_${index + 1}`);
}

function stopInputEventPropagation(event: { stopPropagation: () => void }) {
  event.stopPropagation();
}

type NodeTextInputProps = Omit<InputHTMLAttributes<HTMLInputElement>, "value" | "onChange"> & {
  value: string;
  onValueChange: (value: string) => void;
};

function NodeTextInput({ value, onValueChange, className, onCompositionStart, onCompositionEnd, onBlur, ...props }: NodeTextInputProps) {
  const [draft, setDraft] = useState(value);
  const [isComposing, setIsComposing] = useState(false);
  const composingRef = useRef(false);

  useEffect(() => {
    if (!isComposing) {
      setDraft(value);
    }
  }, [isComposing, value]);

  return (
    <input
      {...props}
      className={className ?? "nodrag"}
      value={draft}
      onPointerDown={stopInputEventPropagation}
      onKeyDown={stopInputEventPropagation}
      onCompositionStart={(event) => {
        composingRef.current = true;
        setIsComposing(true);
        onCompositionStart?.(event);
      }}
      onCompositionEnd={(event) => {
        composingRef.current = false;
        setIsComposing(false);
        setDraft(event.currentTarget.value);
        onValueChange(event.currentTarget.value);
        onCompositionEnd?.(event);
      }}
      onChange={(event) => {
        const next = event.target.value;
        setDraft(next);
        if (!composingRef.current) {
          onValueChange(next);
        }
      }}
      onBlur={(event) => {
        const next = event.currentTarget.value;
        setDraft(next);
        onValueChange(next);
        onBlur?.(event);
      }}
    />
  );
}

type NodeTextareaProps = Omit<TextareaHTMLAttributes<HTMLTextAreaElement>, "value" | "onChange"> & {
  value: string;
  onValueChange: (value: string) => void;
};

function NodeTextarea({ value, onValueChange, className, onCompositionStart, onCompositionEnd, onBlur, ...props }: NodeTextareaProps) {
  const [draft, setDraft] = useState(value);
  const [isComposing, setIsComposing] = useState(false);
  const composingRef = useRef(false);

  useEffect(() => {
    if (!isComposing) {
      setDraft(value);
    }
  }, [isComposing, value]);

  return (
    <textarea
      {...props}
      className={className ?? "nodrag"}
      value={draft}
      onPointerDown={stopInputEventPropagation}
      onKeyDown={stopInputEventPropagation}
      onCompositionStart={(event) => {
        composingRef.current = true;
        setIsComposing(true);
        onCompositionStart?.(event);
      }}
      onCompositionEnd={(event) => {
        composingRef.current = false;
        setIsComposing(false);
        setDraft(event.currentTarget.value);
        onValueChange(event.currentTarget.value);
        onCompositionEnd?.(event);
      }}
      onChange={(event) => {
        const next = event.target.value;
        setDraft(next);
        if (!composingRef.current) {
          onValueChange(next);
        }
      }}
      onBlur={(event) => {
        const next = event.currentTarget.value;
        setDraft(next);
        onValueChange(next);
        onBlur?.(event);
      }}
    />
  );
}

// NodeInputRenderer is fully schema-driven from backend node-registry-v0.4.
function NodeInputRenderer({
  fields,
  data,
  language,
  onFieldFocus,
  onInput
}: {
  fields: NodeInputField[];
  data: Record<string, unknown>;
  language: Language;
  onFieldFocus?: (key: string) => void;
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
            <label key={field.key} className="node-inputs__row node-inputs__row--block" onFocusCapture={() => onFieldFocus?.(field.key)}>
              <span>{label}</span>
              <NodeTextarea
                className="nodrag"
                rows={2}
                value={typeof raw === "string" ? raw : ""}
                placeholder={inputPlaceholder(field, language)}
                onValueChange={(value) => onInput(field.key, value)}
              />
            </label>
          );
        }
        if (field.type === "select") {
          return (
            <label key={field.key} className="node-inputs__row" onFocusCapture={() => onFieldFocus?.(field.key)}>
              <span>{label}</span>
              <select className="nodrag" value={typeof raw === "string" ? raw : ""} onPointerDown={stopInputEventPropagation} onKeyDown={stopInputEventPropagation} onChange={(event) => onInput(field.key, event.target.value)}>
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
            <label key={field.key} className="node-inputs__row node-inputs__row--block" onFocusCapture={() => onFieldFocus?.(field.key)}>
              <span>{label}</span>
              <select
                className="nodrag"
                multiple
                value={selected}
                onPointerDown={stopInputEventPropagation}
                onKeyDown={stopInputEventPropagation}
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
            <label key={field.key} className="node-inputs__row" onFocusCapture={() => onFieldFocus?.(field.key)}>
              <span>{label}</span>
              <span className="node-inputs__slider">
                <input
                  className="nodrag"
                  type="range"
                  min={field.min ?? undefined}
                  max={field.max ?? undefined}
                  step={field.step ?? undefined}
                  value={numeric}
                  onPointerDown={stopInputEventPropagation}
                  onKeyDown={stopInputEventPropagation}
                  onChange={(event) => onInput(field.key, Number(event.target.value))}
                />
                <em>{numeric}</em>
              </span>
            </label>
          );
        }
        if (field.type === "boolean") {
          return (
            <label key={field.key} className="node-inputs__row node-inputs__row--toggle" onFocusCapture={() => onFieldFocus?.(field.key)}>
              <span>{label}</span>
              <input className="nodrag" type="checkbox" checked={Boolean(raw)} onPointerDown={stopInputEventPropagation} onKeyDown={stopInputEventPropagation} onChange={(event) => onInput(field.key, event.target.checked)} />
            </label>
          );
        }
        if (field.type === "color") {
          return (
            <label key={field.key} className="node-inputs__row" onFocusCapture={() => onFieldFocus?.(field.key)}>
              <span>{label}</span>
              <input className="nodrag" type="color" value={typeof raw === "string" ? raw : "#4f8cff"} onPointerDown={stopInputEventPropagation} onKeyDown={stopInputEventPropagation} onChange={(event) => onInput(field.key, event.target.value)} />
            </label>
          );
        }
        if (field.type === "json") {
          return (
            <label key={field.key} className="node-inputs__row node-inputs__row--block" onFocusCapture={() => onFieldFocus?.(field.key)}>
              <span>{label}</span>
              <NodeTextarea
                className="nodrag"
                rows={3}
                value={typeof raw === "string" ? raw : raw === undefined || raw === null ? "" : JSON.stringify(raw, null, 2)}
                placeholder={inputPlaceholder(field, language, "{}")}
                onValueChange={(value) => onInput(field.key, parseJsonInput(value))}
              />
            </label>
          );
        }
        if (field.type === "tags") {
          const text = Array.isArray(raw) ? raw.join(", ") : typeof raw === "string" ? raw : "";
          return (
            <label key={field.key} className="node-inputs__row node-inputs__row--block" onFocusCapture={() => onFieldFocus?.(field.key)}>
              <span>{label}</span>
              <NodeTextInput
                className="nodrag"
                type="text"
                value={text}
                placeholder={inputPlaceholder(field, language, translate(language, "node.placeholder.tags", "tag, tag"))}
                onValueChange={(value) =>
                  onInput(
                    field.key,
                    value
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
            <label key={field.key} className="node-inputs__row node-inputs__row--block" onFocusCapture={() => onFieldFocus?.(field.key)}>
              <span>{label}</span>
              <NodeTextarea
                className="nodrag"
                rows={3}
                value={text}
                placeholder={inputPlaceholder(field, language, translate(language, "node.placeholder.keyValue", "{\"key\":\"value\"}"))}
                onValueChange={(value) => onInput(field.key, parseJsonInput(value))}
              />
            </label>
          );
        }
        if (field.type === "file") {
          return (
            <label key={field.key} className="node-inputs__row node-inputs__row--block" onFocusCapture={() => onFieldFocus?.(field.key)}>
              <span>{label}</span>
              <input
                className="nodrag"
                type="file"
                accept={field.accept?.join(",")}
                multiple={field.multiple}
                onPointerDown={stopInputEventPropagation}
                onKeyDown={stopInputEventPropagation}
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
          <label key={field.key} className="node-inputs__row" onFocusCapture={() => onFieldFocus?.(field.key)}>
            <span>{label}</span>
            <NodeTextInput
              className="nodrag"
              type={field.type === "number" ? "number" : "text"}
              min={field.min ?? undefined}
              max={field.max ?? undefined}
              step={field.step ?? undefined}
              value={raw === null || raw === undefined ? "" : String(raw)}
              placeholder={inputPlaceholder(field, language)}
              onValueChange={(value) => onInput(field.key, field.type === "number" ? Number(value) : value)}
            />
          </label>
        );
      })}
    </div>
  );
}

function CompileTimeFieldInputRenderer({
  fields,
  params,
  language,
  onFieldFocus,
  onInput
}: {
  fields: Record<string, unknown>[];
  params: Record<string, unknown>;
  language: Language;
  onFieldFocus?: (key: string) => void;
  onInput?: (key: string, value: unknown) => void;
}) {
  if (!fields.length) {
    return <div className="node-inputs__empty">{translate(language, "node.compileTime.fields.empty", "No fields configured")}</div>;
  }

  const commitFields = (nextFields: Record<string, unknown>[]) => {
    onInput?.("fields", nextFields);
    onInput?.("params", { ...params, fields: nextFields });
  };

  return (
    <div className="node-inputs">
      {fields.map((field, index) => {
        const label = localizedFieldText(field, "label", language, translate(language, "field.identity.unknown", "Field"));
        const placeholder = localizedFieldText(field, "placeholder", language, "");
        const help = localizedFieldText(field, "help", language, "");
        const value = field.value;
        if (typeof value === "boolean") {
          return (
            <label key={`${label}-${index}`} className="node-inputs__row node-inputs__row--toggle" onFocusCapture={() => onFieldFocus?.(compileTimeFieldKey(field, index))}>
              <span>{label}</span>
              <input
                className="nodrag"
                type="checkbox"
                checked={value}
                onPointerDown={stopInputEventPropagation}
                onKeyDown={stopInputEventPropagation}
                onChange={(event) => commitFields(updateFieldValue(fields, index, event.target.checked))}
              />
              {help ? <em>{help}</em> : null}
            </label>
          );
        }
        if (Array.isArray(value) || isRecord(value)) {
          return (
            <label key={`${label}-${index}`} className="node-inputs__row node-inputs__row--block" onFocusCapture={() => onFieldFocus?.(compileTimeFieldKey(field, index))}>
              <span>{label}</span>
              <NodeTextarea
                className="nodrag"
                rows={2}
                value={prettyValue(value)}
                placeholder={placeholder || "[]"}
                onValueChange={(next) => commitFields(updateFieldValue(fields, index, parseJsonInput(next)))}
              />
              {help ? <em>{help}</em> : null}
            </label>
          );
        }
        return (
          <label key={`${label}-${index}`} className="node-inputs__row node-inputs__row--block" onFocusCapture={() => onFieldFocus?.(compileTimeFieldKey(field, index))}>
            <span>{label}</span>
            <NodeTextInput
              className="nodrag"
              type="text"
              value={value === null || value === undefined ? "" : String(value)}
              placeholder={placeholder}
              onValueChange={(next) => commitFields(updateFieldValue(fields, index, next))}
            />
            {help ? <em>{help}</em> : null}
          </label>
        );
      })}
    </div>
  );
}

function FieldReferenceRenderer({
  data,
  language,
  onInput
}: {
  data: Record<string, unknown>;
  language: Language;
  onInput?: (key: string, value: unknown) => void;
}) {
  const params = paramsFromNodeData(data);
  const outputs = isRecord(data.outputs) ? data.outputs : {};
  const references = asFieldReferenceEntries(params.references);
  const recommended = asFieldReferenceEntries(params.recommended_references);
  const options = isRecord(params.reference_options) ? params.reference_options : {};
  const layerOptions = asFieldReferenceOptions(options.layers);
  const moduleOptions = asFieldReferenceOptions(options.modules);
  const fieldOptions = asFieldReferenceOptions(options.fields);
  const activeByType = {
    required: references.filter((reference) => referenceType(reference.reference_type) === "required"),
    optional: references.filter((reference) => referenceType(reference.reference_type) === "optional"),
    forbidden: references.filter((reference) => referenceType(reference.reference_type) === "forbidden"),
  };
  const recommendedByType = {
    required: recommended.filter((reference) => referenceType(reference.reference_type) === "required"),
    optional: recommended.filter((reference) => referenceType(reference.reference_type) === "optional"),
    forbidden: recommended.filter((reference) => referenceType(reference.reference_type) === "forbidden"),
  };

  const commitReferences = (nextReferences: FieldReferenceEntry[]) => {
    const nextParams = { ...params, references: nextReferences };
    onInput?.("params", nextParams);
    onInput?.("references", nextReferences);
    onInput?.("outputs", { ...outputs, field_references: nextReferences });
  };
  const useRecommendedReferences = () => {
    commitReferences(recommended.filter((reference) => referenceType(reference.reference_type) !== "forbidden").map(updateReferencePath));
  };
  const addReference = () => {
    const layerId = layerOptions[0]?.value || "";
    const moduleId = moduleOptions.find((option) => option.layer_id === layerId)?.value || "";
    const fieldId = fieldOptions.find((option) => option.module_id === moduleId)?.value || "";
    commitReferences([
      ...references,
      updateReferencePath({
        reference_id: `custom_${Date.now()}`,
        reference_type: "optional",
        layer_id: layerId,
        module_id: moduleId,
        field_id: fieldId,
        usage: "",
        i18n_keys: {},
      }),
    ]);
  };
  const patchReference = (target: FieldReferenceEntry, patch: Partial<FieldReferenceEntry>) => {
    const targetId = target.reference_id || target.path || `${target.layer_id}/${target.module_id}/${target.field_id}`;
    commitReferences(
      references.map((reference) => {
        const referenceId = reference.reference_id || reference.path || `${reference.layer_id}/${reference.module_id}/${reference.field_id}`;
        return referenceId === targetId ? updateReferencePath({ ...reference, ...patch }) : reference;
      })
    );
  };
  const removeReference = (target: FieldReferenceEntry) => {
    const targetId = target.reference_id || target.path || `${target.layer_id}/${target.module_id}/${target.field_id}`;
    commitReferences(references.filter((reference) => (reference.reference_id || reference.path || `${reference.layer_id}/${reference.module_id}/${reference.field_id}`) !== targetId));
  };
  const renderReferenceCard = (reference: FieldReferenceEntry, editable: boolean) => {
    const selectedLayer = reference.layer_id || "";
    const moduleChoices = moduleOptions.filter((option) => !selectedLayer || option.layer_id === selectedLayer);
    const selectedModule = reference.module_id || "";
    const fieldChoices = fieldOptions.filter((option) => !selectedModule || option.module_id === selectedModule);
    const usageKey = typeof reference.usage_key === "string" ? reference.usage_key : "";
    const usagePlaceholder = usageKey ? translate(language, usageKey, usageKey) : "";
    if (!editable) {
      return (
        <article key={reference.reference_id || reference.path || referenceDisplayPath(reference, language)} className="field-reference__card">
          <strong>{referenceDisplayPath(reference, language)}</strong>
          <span>{usagePlaceholder || i18nText(language, "common.notGenerated")}</span>
        </article>
      );
    }
    return (
      <article key={reference.reference_id || reference.path || referenceDisplayPath(reference, language)} className="field-reference__card is-editable">
        <label>
          <span>{i18nText(language, "node.fieldReference.referenceType")}</span>
          <select
            className="nodrag"
            value={referenceType(reference.reference_type)}
            onPointerDown={stopInputEventPropagation}
            onKeyDown={stopInputEventPropagation}
            onChange={(event) => patchReference(reference, { reference_type: event.target.value })}
          >
            {(["required", "optional", "forbidden"] as FieldReferenceType[]).map((type) => (
              <option key={type} value={type}>
                {i18nText(language, `node.fieldReference.type.${type}`)}
              </option>
            ))}
          </select>
        </label>
        <label>
          <span>{i18nText(language, "node.fieldReference.sourceLayer")}</span>
          <select
            className="nodrag"
            value={selectedLayer}
            onPointerDown={stopInputEventPropagation}
            onKeyDown={stopInputEventPropagation}
            onChange={(event) => {
              const nextLayer = event.target.value;
              const nextModule = moduleOptions.find((option) => option.layer_id === nextLayer)?.value || "";
              const nextField = fieldOptions.find((option) => option.module_id === nextModule)?.value || "";
              patchReference(reference, { layer_id: nextLayer, module_id: nextModule, field_id: nextField });
            }}
          >
            <option value="">{i18nText(language, "common.notGenerated")}</option>
            {layerOptions.map((option) => (
              <option key={option.value} value={option.value}>
                {referenceOptionLabel(option, language)}
              </option>
            ))}
          </select>
        </label>
        <label>
          <span>{i18nText(language, "node.fieldReference.sourceModule")}</span>
          <select
            className="nodrag"
            value={selectedModule}
            onPointerDown={stopInputEventPropagation}
            onKeyDown={stopInputEventPropagation}
            onChange={(event) => {
              const nextModule = event.target.value;
              const nextField = fieldOptions.find((option) => option.module_id === nextModule)?.value || "";
              patchReference(reference, { module_id: nextModule, field_id: nextField });
            }}
          >
            <option value="">{i18nText(language, "common.notGenerated")}</option>
            {moduleChoices.map((option) => (
              <option key={option.value} value={option.value}>
                {referenceOptionLabel(option, language)}
              </option>
            ))}
          </select>
        </label>
        <label>
          <span>{i18nText(language, "node.fieldReference.sourceField")}</span>
          <select
            className="nodrag"
            value={reference.field_id || ""}
            onPointerDown={stopInputEventPropagation}
            onKeyDown={stopInputEventPropagation}
            onChange={(event) => patchReference(reference, { field_id: event.target.value })}
          >
            <option value="">{i18nText(language, "common.notGenerated")}</option>
            {fieldChoices.map((option) => (
              <option key={option.value} value={option.value}>
                {referenceOptionLabel(option, language)}
              </option>
            ))}
          </select>
        </label>
        <label className="field-reference__usage">
          <span>{i18nText(language, "node.fieldReference.usage")}</span>
          <NodeTextarea
            className="nodrag"
            rows={2}
            value={typeof reference.usage === "string" ? reference.usage : ""}
            placeholder={usagePlaceholder}
            onValueChange={(value) => patchReference(reference, { usage: value })}
          />
        </label>
        <button className="field-reference__remove nodrag" type="button" onPointerDown={stopInputEventPropagation} onClick={() => removeReference(reference)}>
          {i18nText(language, "node.fieldReference.removeReference")}
        </button>
      </article>
    );
  };
  const renderReferenceSection = (type: FieldReferenceType) => {
    const active = activeByType[type];
    const fallback = recommendedByType[type];
    const items = active.length ? active : fallback;
    const editable = active.length > 0 && type !== "forbidden";
    return (
      <section className={`field-reference__section is-${type}`}>
        <h5>{i18nText(language, `node.fieldReference.${type}List`)}</h5>
        {items.length ? (
          <div className="field-reference__cards">{items.map((reference) => renderReferenceCard(reference, editable))}</div>
        ) : (
          <div className="node-inputs__empty">{i18nText(language, "common.empty")}</div>
        )}
      </section>
    );
  };

  return (
    <div className="field-reference">
      <div className="field-reference__actions">
        <button className="nodrag" type="button" onPointerDown={stopInputEventPropagation} onClick={useRecommendedReferences} disabled={!onInput || recommended.length === 0}>
          {i18nText(language, "node.fieldReference.useRecommended")}
        </button>
        <button className="nodrag" type="button" onPointerDown={stopInputEventPropagation} onClick={addReference} disabled={!onInput}>
          {i18nText(language, "node.fieldReference.addReference")}
        </button>
      </div>
      <div className="field-reference__path-format">
        <span>{i18nText(language, "node.fieldReference.pathFormat")}</span>
        <strong>{String(params.path_format || "Layer / Module / Field")}</strong>
      </div>
      {renderReferenceSection("required")}
      {renderReferenceSection("optional")}
      {renderReferenceSection("forbidden")}
    </div>
  );
}

function ChecklistTextConfigRenderer({
  fields,
  params,
  language,
  onFieldFocus,
  onInput,
}: {
  fields: Record<string, unknown>[];
  params: Record<string, unknown>;
  language: Language;
  onFieldFocus?: (key: string) => void;
  onInput?: (key: string, value: unknown) => void;
}) {
  const [advancedOpen, setAdvancedOpen] = useState(false);
  const config = textConfigChecklistFromParams(params);
  if (!config) {
    return <CompileTimeFieldInputRenderer fields={fields} params={params} language={language} onFieldFocus={onFieldFocus} onInput={onInput} />;
  }

  const selected = new Set(config.selectedOptions);
  const commitConfig = (nextConfig: Record<string, unknown>) => {
    onInput?.("params", { ...params, checkbox_config: nextConfig });
  };
  const commitSelectedOptions = (nextSelectedOptions: string[]) => {
    commitConfig({ ...config.raw, preset_id: config.presetId, selected_options: nextSelectedOptions, custom_text: config.customText });
  };
  const toggleOption = (optionId: string, checked: boolean) => {
    const nextSelected = new Set(config.selectedOptions);
    if (checked) {
      nextSelected.add(optionId);
    } else {
      nextSelected.delete(optionId);
    }
    commitSelectedOptions([...nextSelected]);
  };
  const applyTemplate = () => {
    commitConfig({
      ...config.raw,
      preset_id: config.presetId,
      selected_options: config.defaultSelectedOptions,
      custom_text: "",
    });
  };
  const restoreDefaults = () => {
    commitSelectedOptions(config.defaultSelectedOptions);
  };
  const commitCustomText = (customText: string) => {
    commitConfig({ ...config.raw, preset_id: config.presetId, selected_options: config.selectedOptions, custom_text: customText });
  };
  const renderOptionGroup = (titleKey: string, options: TextConfigChecklistOption[]) => {
    if (!options.length) {
      return null;
    }
    return (
      <section className="text-config-checklist__group">
        <h5>{i18nText(language, titleKey)}</h5>
        <div className="text-config-checklist__options">
          {options.map((option) => {
            const description = checklistOptionText(option, language, "description");
            const help = checklistOptionText(option, language, "help");
            const tooltip = checklistOptionText(option, language, "tooltip");
            const error = checklistOptionText(option, language, "error");
            return (
              <label key={option.option_id} className="text-config-checklist__option" title={tooltip || undefined}>
                <input
                  className="nodrag"
                  type="checkbox"
                  checked={selected.has(option.option_id)}
                  disabled={!onInput}
                  onPointerDown={stopInputEventPropagation}
                  onKeyDown={stopInputEventPropagation}
                  onChange={(event) => toggleOption(option.option_id, event.target.checked)}
                />
                <span>
                  <span>{checklistOptionLabel(option, language)}</span>
                  {description ? <small>{description}</small> : null}
                  {help ? <small>{help}</small> : null}
                  {error ? <small className="text-config-checklist__option-error">{error}</small> : null}
                </span>
              </label>
            );
          })}
        </div>
      </section>
    );
  };

  return (
    <div className="text-config-checklist">
      <div className="text-config-checklist__actions">
        <button className="nodrag" type="button" onPointerDown={stopInputEventPropagation} onClick={applyTemplate} disabled={!onInput}>
          {i18nText(language, config.applyPresetLabelKey)}
        </button>
        <button className="nodrag" type="button" onPointerDown={stopInputEventPropagation} onClick={restoreDefaults} disabled={!onInput}>
          {i18nText(language, "node.checklist.restoreDefaults")}
        </button>
        <button className="nodrag" type="button" onPointerDown={stopInputEventPropagation} onClick={() => setAdvancedOpen((open) => !open)}>
          {i18nText(language, advancedOpen ? "node.checklist.collapseAdvancedFields" : "node.checklist.expandAdvancedFields")}
        </button>
      </div>
      <div className="text-config-checklist__preset">
        <span>{i18nText(language, "node.checklist.preset")}</span>
        <strong>{config.presetId}</strong>
      </div>
      {renderOptionGroup("node.checklist.defaultOptions", config.defaultOptions)}
      {renderOptionGroup("node.checklist.optionalOptions", config.optionalOptions)}
      {advancedOpen ? (
        <section className="text-config-checklist__advanced">
          <label className="text-config-checklist__custom">
            <span>{i18nText(language, "node.checklist.customText")}</span>
            <NodeTextarea
              className="nodrag"
              rows={3}
              value={config.customText}
              placeholder={i18nText(language, "node.checklist.customText.placeholder")}
              onFocus={() => onFieldFocus?.("custom_text")}
              onValueChange={commitCustomText}
            />
          </label>
          {fields.length ? (
            <div className="text-config-checklist__legacy-fields">
              <h5>{i18nText(language, "node.checklist.advancedFields")}</h5>
              <CompileTimeFieldInputRenderer fields={fields} params={params} language={language} onFieldFocus={onFieldFocus} onInput={onInput} />
            </div>
          ) : null}
        </section>
      ) : null}
    </div>
  );
}

function CoreParamValue({ value, language, depth = 0 }: { value: unknown; language: Language; depth?: number }) {
  if (isEmptyDisplayValue(value)) {
    return <span className="core-params__empty">{translate(language, Array.isArray(value) ? "common.empty" : "common.notGenerated", Array.isArray(value) ? "Empty" : "Not generated")}</span>;
  }
  if (typeof value === "boolean") {
    return <span>{translate(language, value ? "common.yes" : "common.no", value ? "Yes" : "No")}</span>;
  }
  if (typeof value === "number") {
    return <span>{String(value)}</span>;
  }
  if (typeof value === "string") {
    return <span>{localizedCoreValue(language, value)}</span>;
  }
  if (Array.isArray(value)) {
    return (
      <ul className="core-params__list">
        {value.length ? (
          value.map((item, index) => (
            <li key={`${index}-${String(typeof item === "object" ? index : item)}`}>
              <CoreParamValue value={item} language={language} depth={depth + 1} />
            </li>
          ))
        ) : (
          <li>
            <CoreParamValue value={[]} language={language} depth={depth + 1} />
          </li>
        )}
      </ul>
    );
  }
  if (isRecord(value)) {
    const entries = Object.entries(value).filter(([, item]) => !isEmptyDisplayValue(item));
    if (!entries.length) {
      return <CoreParamValue value={null} language={language} />;
    }
    if (depth >= 2) {
      return (
        <details className="core-params__nested">
          <summary>{translate(language, "node.coreParams.expand", "Expand")}</summary>
          <CoreParamValue value={value} language={language} depth={0} />
        </details>
      );
    }
    return (
      <dl className="core-params__object">
        {entries.map(([key, item]) => (
          <div key={key} className="core-params__object-row">
            <dt>{localizedCoreKey(language, key)}</dt>
            <dd>
              <CoreParamValue value={item} language={language} depth={depth + 1} />
            </dd>
          </div>
        ))}
      </dl>
    );
  }
  return <span>{String(value)}</span>;
}

function CoreParamSection({
  titleKey,
  titleFallback,
  value,
  language,
  tone = "default"
}: {
  titleKey: string;
  titleFallback: string;
  value: unknown;
  language: Language;
  tone?: "default" | "warning";
}) {
  return (
    <section className={`core-params__section is-${tone}`}>
      <h5>{translate(language, titleKey, titleFallback)}</h5>
      <CoreParamValue value={value} language={language} />
    </section>
  );
}

function uniqueStrings(values: unknown[]): string[] {
  return [...new Set(values.map((value) => (typeof value === "string" ? value.trim() : "")).filter(Boolean))];
}

function pickOutputValues(output: Record<string, unknown>, keys: string[]) {
  const picked = Object.fromEntries(keys.filter((key) => key in output).map((key) => [key, output[key]]));
  return displayObjectEntries(picked);
}

function validationFailureReasons(validation: unknown): unknown[] {
  const data = isRecord(validation) ? validation : {};
  const direct = Array.isArray(data.failure_reasons) ? data.failure_reasons : Array.isArray(data.errors) ? data.errors : [];
  const findings = Array.isArray(data.findings) ? data.findings : [];
  const reasonItems = direct.length ? direct : findings;
  return reasonItems
    .map((item) => {
      if (typeof item === "string") {
        return item;
      }
      if (isRecord(item)) {
        return item.message || item.reason || item.code || item.status || "";
      }
      return "";
    })
    .filter((item) => typeof item === "string" && item.trim());
}

function validationPassed(params: Record<string, unknown>, output: Record<string, unknown>, validation: unknown): boolean {
  const validationData = isRecord(validation) ? validation : {};
  const explicitStatus = stringValue(validationData.status).toLowerCase();
  if (["fail", "failed", "invalid", "error"].includes(explicitStatus)) {
    return false;
  }
  if (["pass", "passed", "valid", "ok", "success"].includes(explicitStatus)) {
    return true;
  }
  const compileStatus = stringValue(output.compile_validation_status).toLowerCase();
  if (compileStatus === "invalid") {
    return false;
  }
  if (compileStatus === "valid") {
    return true;
  }
  const required = Array.isArray(params.required_fields) ? params.required_fields : [];
  const rules = Array.isArray(params.validation_rules) ? params.validation_rules : [];
  return required.length > 0 || rules.length > 0;
}

function updateRuleDisplayName(rule: Record<string, unknown>): string {
  return stringValue(rule.field_id) || stringValue(rule.rule_id) || stringValue(rule.name) || stringValue(rule.id);
}

function updateRuleUserEditable(rule: Record<string, unknown>): boolean {
  const editScope = stringValue(rule.edit_scope);
  return editScope === "user_editable" || editScope === "runtime_editable" || editScope === "plugin_editable";
}

function UpdateRuleCards({ rules, language }: { rules: Record<string, unknown>[]; language: Language }) {
  if (!rules.length) {
    return <CoreParamValue value={[]} language={language} />;
  }
  return (
    <div className="core-params__rule-list">
      {rules.map((rule, index) => {
        const name = updateRuleDisplayName(rule) || `${translate(language, "common.field", "Field")} ${index + 1}`;
        const displayName = localizedCoreValue(language, name);
        return (
          <article key={`${name}-${index}`} className="core-params__rule-card">
            <h6>{displayName}</h6>
            <dl>
              <div>
                <dt>{translate(language, "common.field", "Field")}</dt>
                <dd>
                  <CoreParamValue value={name} language={language} />
                </dd>
              </div>
              <div>
                <dt>{translate(language, "node.updateRules.updateLevel", "Update level")}</dt>
                <dd>
                  <CoreParamValue value={rule.update_level} language={language} />
                </dd>
              </div>
              <div>
                <dt>{translate(language, "node.updateRules.editScope", "Edit scope")}</dt>
                <dd>
                  <CoreParamValue value={rule.edit_scope} language={language} />
                </dd>
              </div>
              <div>
                <dt>{translate(language, "node.updateRules.requiresRecompile", "Requires recompile")}</dt>
                <dd>
                  <CoreParamValue value={rule.requires_recompile} language={language} />
                </dd>
              </div>
              <div>
                <dt>{translate(language, "node.updateRules.userEditable", "User editable")}</dt>
                <dd>
                  <CoreParamValue value={updateRuleUserEditable(rule)} language={language} />
                </dd>
              </div>
            </dl>
          </article>
        );
      })}
    </div>
  );
}

function CoreParamsPanel({
  type,
  data,
  language,
  siblingOutput,
  validation
}: {
  type: string;
  data: Record<string, unknown>;
  language: Language;
  siblingOutput: { outputKey: string; output: Record<string, unknown> };
  validation: unknown;
}) {
  const params = paramsFromNodeData(data);
  if (type === "layer_aggregator") {
    const inputPolicies = valueByCandidateKeys([data, params], ["input_policy_keys", "inputs"]);
    const signalSummary = firstRecordByKeys([data, params, siblingOutput.output], ["risk_signal_summary"]);
    const derivedOutputs = valueByCandidateKeys([data, params], ["outputs"]);
    return (
      <div className="core-params-panel">
        <CoreParamSection titleKey="node.riskResponse.inputPolicies" titleFallback="Input policies" value={inputPolicies} language={language} />
        <CoreParamSection titleKey="node.riskResponse.signalSummary" titleFallback="Risk signal summary" value={signalSummary} language={language} />
        <CoreParamSection titleKey="node.riskResponse.derivedOutputs" titleFallback="Derived outputs" value={derivedOutputs} language={language} />
      </div>
    );
  }
  if (type === "structure_normalize") {
    const rules = Array.isArray(valueByCandidateKeys([data, params], ["normalize_rules", "rules"])) ? (valueByCandidateKeys([data, params], ["normalize_rules", "rules"]) as unknown[]) : [];
    const normalizedOutput = normalizedResultValue(data, siblingOutput);
    const outputKeys = Array.isArray(params.outputs)
      ? uniqueStrings(params.outputs)
      : uniqueStrings(Object.keys(normalizedOutput));
    const expandedOutputKeys = uniqueStrings([...outputKeys, "decision_modes", "default_mode", "identity_context_ref"]);
    const normalizedFields = expandedOutputKeys.length ? pickOutputValues(normalizedOutput, expandedOutputKeys) : normalizedOutput;
    return (
      <div className="core-params-panel">
        <CoreParamSection titleKey="node.normalization.outputKey" titleFallback="Output key" value={siblingOutput.outputKey} language={language} />
        <CoreParamSection titleKey="node.normalization.defaultMode" titleFallback="Default mode" value={normalizedOutput.default_mode} language={language} />
        <CoreParamSection titleKey="node.normalization.decisionModes" titleFallback="Decision modes" value={normalizedOutput.decision_modes} language={language} />
        <CoreParamSection titleKey="node.normalization.resultTitle" titleFallback="Normalization result" value={normalizedFields} language={language} />
        <CoreParamSection titleKey="node.normalization.fields" titleFallback="Normalized fields" value={outputKeys} language={language} />
        <CoreParamSection titleKey="node.normalization.rules" titleFallback="Normalization rules" value={rules} language={language} />
      </div>
    );
  }
  if (type === "validation") {
    const validationData = isRecord(valueByCandidateKeys([data, params], ["validation_result", "validation", "result"]))
      ? (valueByCandidateKeys([data, params], ["validation_result", "validation", "result"]) as Record<string, unknown>)
      : {};
    const riskLevelPolicy = firstRecordByKeys([data, params, siblingOutput.output], ["risk_level_policy"]);
    const requiredValue = valueByCandidateKeys([validationData, data, params], ["required_fields", "scope", "validation_scope"]);
    const rulesValue = valueByCandidateKeys([validationData, data, params], ["validation_rules", "rules"]);
    const required = Array.isArray(requiredValue) ? requiredValue : [];
    const rules = Array.isArray(rulesValue) ? rulesValue : [];
    const readonlyRefs = isRecord(params.readonly_refs) ? params.readonly_refs : {};
    const passed = validationPassed(params, siblingOutput.output, validationData);
    const reasons = validationFailureReasons(validationData);
    return (
      <div className="core-params-panel">
        {!isEmptyDisplayValue(riskLevelPolicy) ? (
          <CoreParamSection titleKey="node.riskResponse.levelPolicy" titleFallback="Risk level policy" value={riskLevelPolicy} language={language} />
        ) : null}
        <CoreParamSection
          titleKey="node.validation.resultTitle"
          titleFallback="Validation result"
          value={translate(language, passed ? "node.validation.pass" : "node.validation.fail", passed ? "Pass" : "Fail")}
          language={language}
        />
        <CoreParamSection
          titleKey="node.validation.scopeTitle"
          titleFallback="Validation scope"
          value={displayObjectEntries({ required_fields: required, readonly_refs: readonlyRefs, input: params.input })}
          language={language}
        />
        <CoreParamSection titleKey="node.validation.rulesTitle" titleFallback="Validation rules" value={rules} language={language} />
        <CoreParamSection
          titleKey="node.validation.failureReasons"
          titleFallback="Failure reasons"
          value={reasons.length ? reasons : translate(language, "node.validation.none", "None")}
          language={language}
          tone={!passed && reasons.length ? "warning" : "default"}
        />
      </div>
    );
  }
  if (type === "update_rule") {
    const updatePolicy = isRecord(valueByCandidateKeys([data, params], ["update_policy"])) ? (valueByCandidateKeys([data, params], ["update_policy"]) as Record<string, unknown>) : {};
    const derivedPolicy = firstRecordByKeys(
      [data, params, siblingOutput.output],
      ["risk_response_strategy", "human_review_policy", "hard_block_policy", "audit_log_policy", "safe_redirect_policy"]
    );
    const rulesValue = valueByCandidateKeys([data, params], ["update_rules", "rules"]);
    const updateRules = (Array.isArray(rulesValue) ? rulesValue : []).filter(isRecord);
    const updatableFields = uniqueStrings(
      [
        ...(Array.isArray(valueByCandidateKeys([data, params], ["updatable_fields"])) ? (valueByCandidateKeys([data, params], ["updatable_fields"]) as unknown[]) : []),
        ...updateRules.filter((rule) => rule.locked !== true && rule.update_level !== "locked_core").map(updateRuleDisplayName),
      ]
    );
    const lockedFields = uniqueStrings(
      [
        ...(Array.isArray(valueByCandidateKeys([data, params], ["locked_fields"])) ? (valueByCandidateKeys([data, params], ["locked_fields"]) as unknown[]) : []),
        ...updateRules.filter((rule) => rule.locked === true || rule.update_level === "locked_core").map(updateRuleDisplayName),
      ]
    );
    const coreLockedFields = uniqueStrings(updateRules.filter((rule) => rule.update_level === "locked_core").map(updateRuleDisplayName));
    const requiresRevalidation =
      Boolean(valueByCandidateKeys([updatePolicy, data, params], ["requires_revalidation", "requires_revalidation_after_update"])) ||
      updateRules.some((rule) => Boolean(rule.requires_recompile) || String(rule.rule_id || "").includes("revalidation"));
    const requiresReason =
      Boolean(updatePolicy.requires_update_reason) ||
      Boolean(updatePolicy.requires_update_reason_time_impact_scope) ||
      updateRules.some((rule) => String(rule.rule_id || "").includes("reason"));
    return (
      <div className="core-params-panel">
        {updateRules.length ? (
          <section className="core-params__section">
            <h5>{translate(language, "node.updateRules.title", "Update rules")}</h5>
            <UpdateRuleCards rules={updateRules} language={language} />
          </section>
        ) : (
          <CoreParamSection titleKey="node.riskResponse.derivedPolicy" titleFallback="Derived policy" value={derivedPolicy} language={language} />
        )}
        <CoreParamSection titleKey="node.updateRules.updatableFields" titleFallback="Updatable fields" value={updatableFields} language={language} />
        <CoreParamSection titleKey="node.updateRules.lockedFields" titleFallback="Locked fields" value={lockedFields} language={language} />
        <CoreParamSection titleKey="node.updateRules.coreLockedFields" titleFallback="Core locked fields" value={coreLockedFields} language={language} />
        <CoreParamSection titleKey="node.updateRules.constraints" titleFallback="Constraints" value={updatePolicy} language={language} />
        <CoreParamSection
          titleKey="node.updateRules.requiresRecompile"
          titleFallback="Requires recompile"
          value={updateRules.some((rule) => Boolean(rule.requires_recompile))}
          language={language}
        />
        <CoreParamSection titleKey="node.updateRules.requiresRevalidation" titleFallback="Requires revalidation" value={requiresRevalidation} language={language} />
        <CoreParamSection titleKey="node.updateRules.requiresAuditReason" titleFallback="Requires audit reason" value={requiresReason} language={language} />
      </div>
    );
  }
  return <div className="node-inputs__empty">{translate(language, "node.inputs.empty", "No schema inputs")}</div>;
}

function CompileTimeNodeSummary({
  type,
  data,
  language
}: {
  type: string;
  data: Record<string, unknown>;
  language: Language;
}) {
  const params = paramsFromNodeData(data);
  const outputs = isRecord(data.outputs) ? data.outputs : {};
  if (type === "module_output") {
    const outputKey = typeof params.output_key === "string" ? params.output_key : "";
    const output = outputKey && isRecord(outputs[outputKey]) ? (outputs[outputKey] as Record<string, unknown>) : {};
    const outputFields = isRecord(output.fields) && Object.keys(output.fields).length
      ? Object.keys(output.fields).length
      : Object.keys(displayObjectEntries(output, new Set(["compile_time_only", "output_key"]))).length;
    return (
      <p className="node-inputs__empty">
        {translate(language, "node.compileTime.summary.moduleOutput", "Output: {output}; fields: {count}")
          .replace("{output}", outputKey || translate(language, "common.unknown", "Unknown"))
          .replace("{count}", String(outputFields))}
      </p>
    );
  }
  return <div className="node-inputs__empty">{translate(language, "node.inputs.empty", "No schema inputs")}</div>;
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
          onPointerDown={stopInputEventPropagation}
          onKeyDown={stopInputEventPropagation}
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
        <NodeTextarea
          className="nodrag"
          value={systemPrompt}
          rows={3}
          onValueChange={(next) => {
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
          onPointerDown={stopInputEventPropagation}
          onKeyDown={stopInputEventPropagation}
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
          onPointerDown={stopInputEventPropagation}
          onKeyDown={stopInputEventPropagation}
          onChange={(event) => {
            const next = event.target.value;
            setMaxTokens(next);
            commit({ max_tokens: Number(next) });
          }}
        />
      </label>
      <label className="node-inputs__row node-inputs__row--block">
        <span>{translate(language, "field.modelOverride", "Model Override")}</span>
        <NodeTextInput
          className="nodrag"
          value={modelOverride}
          onValueChange={(next) => {
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
// v0.3 formal path keeps resident_id on the node; v0.1/v0.2 remain legacy only.
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
  const runtimeResidentId = typeof runtimeResult?.resident_id === "string" ? runtimeResult.resident_id.trim() : "";
  const configuredResidentId = typeof nodeData.resident_id === "string" ? nodeData.resident_id.trim() : "";
  const effectiveResidentId = configuredResidentId && configuredResidentId !== "resident_v1" ? configuredResidentId : runtimeResidentId || configuredResidentId || "resident_v1";
  const namespace = typeof nodeData.namespace === "string" && nodeData.namespace ? nodeData.namespace : "default";
  const memoryType = typeof nodeData.memory_type === "string" && nodeData.memory_type ? nodeData.memory_type : "interaction_log";
  const localEntries = Array.isArray(nodeData.memory_entries) ? nodeData.memory_entries : [];
  const memoryViewResult = (nodeData.memory_view_result as Record<string, unknown> | undefined) ?? null;
  const entries = localEntries;
  const clearResult = memoryClearResult && memoryClearResult.resident_id === effectiveResidentId ? memoryClearResult : null;
  const t = (key: string, fallback: string) => translate(language, key, fallback);
  const actionError = memoryStatus === "error" ? t("memory.error", "记忆操作失败") : "";

  useEffect(() => {
    if (!onInput) {
      return;
    }
    if (!runtimeResidentId || effectiveResidentId !== runtimeResidentId || configuredResidentId && configuredResidentId !== "resident_v1") {
      return;
    }
    onInput("resident_id", effectiveResidentId);
  }, [configuredResidentId, effectiveResidentId, onInput, runtimeResidentId]);

  const handleView = async () => {
    const latest = await viewMemory(effectiveResidentId, namespace, memoryType, 20);
    if (!latest) {
      return;
    }
    const nextEntries = latest.entries ?? latest.items ?? [];
    onInput?.("memory_entries", nextEntries);
    onInput?.("memory_view_result", latest);
  };

  const handleClear = async () => {
    const result = await clearMemory(effectiveResidentId, namespace, memoryType);
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
        <span>{t("input.resident_id", "Resident ID")}: {effectiveResidentId}</span>
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
  const moduleWorkflowNodes = useModuleWorkflowNodes();
  const { schemaNode, onRename, onColor, onInput, onFieldFocus } = data as CanvasNodeData;
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
  const aiSlotText = aiSlot === "none" ? translate(language, "module.slot.unplanned", aiSlotLabel(aiSlot)) : aiSlotLabel(aiSlot);
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
  const isCatalogPreconfigured = nodeData.catalog_preconfigured === true;
  const compileTimeFields = fieldsFromNodeData(nodeData);
  const compileTimeParams = paramsFromNodeData(nodeData);
  const showCompileTimeFieldForm = isCatalogPreconfigured && ["field_input", "text_config"].includes(String(effectiveType));
  const showChecklistTextConfig = showCompileTimeFieldForm && String(effectiveType) === "text_config" && Boolean(textConfigChecklistFromParams(compileTimeParams));
  const showFieldReferenceForm = isCatalogPreconfigured && String(effectiveType) === "field_reference";
  const showCoreParamsPanel = isCatalogPreconfigured && ["layer_aggregator", "structure_normalize", "validation", "update_rule"].includes(String(effectiveType));
  const showModuleOutputSummary = isCatalogPreconfigured && String(effectiveType) === "module_output";
  const siblingOutput = moduleOutputValue(findSiblingModuleOutputNode(schemaNode, moduleWorkflowNodes));
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
              <span className={`ai-slot-badge ${aiSlotClass(aiSlot)}`}>{aiSlotText}</span>
              <span className={`workflow-node__state-badge is-${statusKey}`}>{stateLabel}</span>
            </span>
          </div>
          {onRename ? (
            <label className="workflow-node__name-field">
              <span>{translate(language, "node.header.name", "Name")}</span>
              <NodeTextInput
                className="nodrag"
                value={label}
                onValueChange={(value) => onRename(value)}
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
            onPointerDown={stopInputEventPropagation}
            onKeyDown={stopInputEventPropagation}
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
              onPointerDown={stopInputEventPropagation}
              onKeyDown={stopInputEventPropagation}
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

      <details className="workflow-node__params nodrag nopan" onPointerDown={(event) => event.stopPropagation()} open={!sections.core && !isCatalogPreconfigured}>
        <summary>{sectionTitle(language, "node.coreParams.title", "Core Params")}</summary>
        <div className="workflow-node__params-body">
          {showFieldReferenceForm ? (
            <FieldReferenceRenderer data={nodeData} language={language} onInput={onInput} />
          ) : showChecklistTextConfig ? (
            <ChecklistTextConfigRenderer fields={compileTimeFields} params={compileTimeParams} language={language} onFieldFocus={onFieldFocus} onInput={onInput} />
          ) : showCompileTimeFieldForm ? (
            <CompileTimeFieldInputRenderer fields={compileTimeFields} params={compileTimeParams} language={language} onFieldFocus={onFieldFocus} onInput={onInput} />
          ) : showCoreParamsPanel ? (
            <CoreParamsPanel
              type={String(effectiveType)}
              data={nodeData}
              language={language}
              siblingOutput={siblingOutput}
              validation={schemaNode.validation ?? null}
            />
          ) : showModuleOutputSummary ? (
            <CompileTimeNodeSummary type={String(effectiveType)} data={nodeData} language={language} />
          ) : onInput ? (
            <NodeInputRenderer fields={inputSchema} data={nodeData} language={language} onFieldFocus={onFieldFocus} onInput={onInput} />
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
            <dt>{translate(language, "field.status")}</dt>
            <dd>{stateLabel}</dd>
            <dt>{translate(language, "field.lockLevel", "Lock")}</dt>
            <dd>{lockLabel}</dd>
            <dt>{translate(language, "field.validation", "Validation")}</dt>
            <dd>{statusText(language, schemaNode.validation?.status)}</dd>
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
