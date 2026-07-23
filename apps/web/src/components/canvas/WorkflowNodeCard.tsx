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
import { firstInteractionEnabledValue, updateFirstInteractionEnabled } from "@/store/module-graph-merge";
import {
  isLayer11Module,
  isLayer11RoleCollection,
  layer11ModuleId,
  resolveLayer11DisplayText,
  resolveLayer11RoleDescription,
} from "./layer11-display";

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

const CoreParamModuleContext = createContext<string | undefined>(undefined);

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

function isFirstInteractionField(field: Record<string, unknown>) {
  return String(field.field_id || field.field_key || "") === "first_interaction";
}

function fieldsFromNodeData(data: Record<string, unknown>): Record<string, unknown>[] {
  const params = isRecord(data.params) ? data.params : {};
  const paramsFields = Array.isArray(params.fields) ? params.fields.filter(isRecord) : [];
  if (paramsFields.some(isFirstInteractionField)) {
    return paramsFields;
  }
  return Array.isArray(data.fields) ? data.fields.filter(isRecord) : paramsFields;
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

function localizedFieldText(
  field: Record<string, unknown>,
  key: "label" | "placeholder" | "help" | "default" | "validation_error",
  language: Language,
  fallback: string
) {
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

function layer12CoreParamPrefix(moduleId?: string) {
  if (moduleId === "self_awareness") return "layer12.engineeringSelfAwareness.param";
  if (moduleId === "goal_setting") return "layer12.selfStateMetacognition.param";
  if (moduleId === "reflection_summary") return "layer12.controlledSelfWill.param";
  if (moduleId === "self_evaluation") return "layer12.consistencyCorrection.param";
  if (moduleId === "growth_plan") return "layer12.growthContinuity.param";
  return "";
}

function layer8EmotionalExpressionPrefix(moduleId?: string) {
  return moduleId === "emotion_reaction" ? "layer8.emotionalExpression" : "";
}

function stage748ConfigPrefix(moduleId?: string) {
  if (moduleId === "interaction_strategy") return "stage7_4_8.firstInteraction";
  if (moduleId === "visual_style") return "stage7_4_8.expression";
  return "";
}

function stage749ConfigPrefix(moduleId?: string) {
  if (moduleId === "dialogue_runtime_profile") return "stage7_4_9.dialogueRuntime";
  return "";
}

function usesLocalizedStructuredIds(moduleId?: string) {
  return isLayer11Module(moduleId) || Boolean(layer8EmotionalExpressionPrefix(moduleId)) || Boolean(layer12CoreParamPrefix(moduleId)) || Boolean(stage748ConfigPrefix(moduleId)) || Boolean(stage749ConfigPrefix(moduleId));
}

function localizedCoreKey(language: Language, key: string, moduleId?: string) {
  if (isLayer11Module(moduleId)) {
    return resolveLayer11DisplayText({ value: key, valueType: "key", moduleId, language });
  }
  const layer8ExpressionPrefix = layer8EmotionalExpressionPrefix(moduleId);
  if (layer8ExpressionPrefix) {
    const localized = translateIfPresent(language, `${layer8ExpressionPrefix}.key.${key}`);
    if (localized) return localized;
  }
  const layer12Prefix = layer12CoreParamPrefix(moduleId);
  if (layer12Prefix) {
    const localized = translateIfPresent(language, `${layer12Prefix}.${key}`);
    if (localized) return localized;
  }
  const stage748Prefix = stage748ConfigPrefix(moduleId);
  if (stage748Prefix) {
    const localized = translateIfPresent(language, `${stage748Prefix}.key.${key}`);
    if (localized) return localized;
  }
  const stage749Prefix = stage749ConfigPrefix(moduleId);
  if (stage749Prefix) {
    const localized = translateIfPresent(language, `${stage749Prefix}.key.${key}`);
    if (localized) return localized;
  }
  return (
    translateIfPresent(language, `assembly.field.${stableI18nKeyPart(key)}`) ||
    translateIfPresent(language, `node.coreParams.key.${key}`) ||
    translateIfPresent(language, `field.identity.${key}.label`) ||
    key
  );
}

function localizedCoreValue(language: Language, value: string, moduleId?: string) {
  if (isLayer11Module(moduleId)) {
    return resolveLayer11DisplayText({ value, valueType: "value", moduleId, language });
  }
  const layer8ExpressionPrefix = layer8EmotionalExpressionPrefix(moduleId);
  if (layer8ExpressionPrefix) {
    const localized = translateIfPresent(language, `${layer8ExpressionPrefix}.value.${value}`);
    if (localized) return localized;
  }
  const layer12Prefix = layer12CoreParamPrefix(moduleId);
  if (layer12Prefix) {
    const localized = translateIfPresent(language, `${layer12Prefix}.${value}`);
    if (localized) return localized;
  }
  const stage748Prefix = stage748ConfigPrefix(moduleId);
  if (stage748Prefix) {
    const localized = translateIfPresent(language, `${stage748Prefix}.value.${value}`);
    if (localized) return localized;
  }
  const stage749Prefix = stage749ConfigPrefix(moduleId);
  if (stage749Prefix) {
    const localized = translateIfPresent(language, `${stage749Prefix}.value.${value}`);
    if (localized) return localized;
  }
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

const GENERIC_FIELD_TYPES: GenericFieldType[] = ["text", "long_text", "number", "boolean", "list", "object", "unknown"];
const GENERIC_FIELD_RESERVED_KEYS = new Set(["mode", "text", "fields", "tags"]);
const GENERIC_FIELD_NAME_KEY_MAP: Record<string, string> = {
  "姓名": "resident_name",
  "年龄设定": "age_profile",
  "年龄": "age_profile",
  "城市锚点": "city_anchor",
  "主语言": "primary_language",
  "居民类型": "resident_type",
  "性别感": "gender_presentation",
  "身份锚点": "identity_anchor",
  "事实源规则": "source_of_truth_rule",
  "身份稳定规则": "identity_stability_rule",
  "成长背景": "growth_background",
  "家庭背景": "family_background",
  "教育背景": "education_background",
  "生活经历": "life_experience",
  "关键人生事件": "key_life_events",
  "文化背景": "cultural_background",
  "职业身份": "career_identity",
  "职业": "occupation",
  "专业领域": "professional_domain",
  "服务对象": "service_target",
  "职业边界": "professional_boundary",
  "存在模式": "existence_mode",
  "可视形态": "visible_form",
  "不可见形态": "invisible_form",
  "运行形态": "runtime_form",
  "设备形态": "device_form",
  "归属边界": "ownership_boundary",
};
const GENERIC_FIELD_KEY_NAME_MAP: Record<string, string> = {
  resident_name: "姓名",
  age_profile: "年龄设定",
  primary_language: "主语言",
  resident_type: "居民类型",
  gender_presentation: "性别感",
  identity_anchor: "身份锚点",
  city_anchor: "城市锚点",
  source_of_truth_rule: "事实源规则",
  identity_stability_rule: "身份稳定规则",
  growth_background: "成长背景",
  family_background: "家庭背景",
  education_background: "教育背景",
  life_experience: "生活经历",
  key_life_events: "关键人生事件",
  cultural_background: "文化背景",
  career_identity: "职业身份",
  occupation: "职业",
  professional_domain: "专业领域",
  service_target: "服务对象",
  professional_boundary: "职业边界",
  existence_mode: "存在模式",
  visible_form: "可视形态",
  invisible_form: "不可见形态",
  runtime_form: "运行形态",
  device_form: "设备形态",
  ownership_boundary: "归属边界",
};

function safeGenericFieldKey(value: string) {
  const mapped = GENERIC_FIELD_NAME_KEY_MAP[value.trim()];
  const raw = mapped || value.normalize("NFKD").toLowerCase();
  let key = raw
    .replace(/['’]/g, "")
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "")
    .replace(/_+/g, "_");
  if (!key) {
    key = "field";
  }
  if (/^[0-9]/.test(key)) {
    key = `field_${key}`;
  }
  return key;
}

function uniqueGenericFieldKey(baseKey: string, fields: GenericField[], currentIndex: number) {
  const base = safeGenericFieldKey(baseKey);
  const used = new Set(fields.map((field, index) => (index === currentIndex ? "" : field.field_key)).filter(Boolean));
  if (!used.has(base)) {
    return base;
  }
  let suffix = 2;
  while (used.has(`${base}_${suffix}`)) {
    suffix += 1;
  }
  return `${base}_${suffix}`;
}

function genericFieldDrMapping(layerId: string, moduleId: string, fieldKey: string) {
  return layerId && moduleId && fieldKey ? `payload.layers.${layerId}.modules.${moduleId}.fields.${fieldKey}` : "";
}

function fieldValue(field: Record<string, unknown>, keys: string[]) {
  for (const key of keys) {
    if (key in field) {
      return field[key];
    }
  }
  return "";
}

function normalizeGenericField(field: Record<string, unknown>, index: number): GenericField {
  const fieldKeySource =
    stringValue(field.field_key) ||
    stringValue(field.field_id) ||
    stringValue(field.key) ||
    stringValue(field.id);
  const fallbackName = stringValue(field.name) || stringValue(field.title) || stringValue(field.label);
  const generatedKey = fieldKeySource || (fallbackName ? safeGenericFieldKey(fallbackName) : `field_${index + 1}`);
  const fieldKey = generatedKey || `field_${index + 1}`;
  const fieldName =
    stringValue(field.field_name) ||
    GENERIC_FIELD_KEY_NAME_MAP[fieldKey] ||
    fallbackName ||
    fieldKey;
  return {
    field_key: fieldKey,
    field_name: fieldName,
    field_value: fieldValue(field, ["field_value", "value", "text", "content"]),
    field_type: GENERIC_FIELD_TYPES.includes(field.field_type as GenericFieldType) ? (field.field_type as GenericFieldType) : "long_text",
    description: stringValue(field.description),
    dr_mapping: stringValue(field.dr_mapping),
    reference_enabled: field.reference_enabled === true,
    required: typeof field.required === "boolean" ? field.required : undefined,
    field_key_auto: field.field_key_auto === true,
    dr_mapping_auto: field.dr_mapping_auto === true,
    i18n_keys: isRecord(field.i18n_keys)
      ? Object.fromEntries(
          Object.entries(field.i18n_keys)
            .filter(([, value]) => typeof value === "string" && value)
            .map(([key, value]) => [key, String(value)])
        )
      : undefined,
    field_name_custom: field.field_name_custom === true,
    description_custom: field.description_custom === true,
    enum_options: Array.isArray(field.enum_options)
      ? field.enum_options
          .filter(isRecord)
          .map((option) => ({ value: stringValue(option.value), label_key: stringValue(option.label_key) }))
          .filter((option) => option.value)
      : undefined,
    structured_options: isRecord(field.structured_options)
      ? Object.fromEntries(
          Object.entries(field.structured_options)
            .filter(([, options]) => Array.isArray(options))
            .map(([key, options]) => [
              key,
              (options as unknown[])
                .filter(isRecord)
                .map((option) => ({ value: stringValue(option.value), label_key: stringValue(option.label_key) }))
                .filter((option) => option.value),
            ])
        )
      : undefined,
    minimum: typeof field.minimum === "number" ? field.minimum : undefined,
    maximum: typeof field.maximum === "number" ? field.maximum : undefined,
  };
}

function genericFieldsFromParams(value: unknown): GenericField[] {
  return Array.isArray(value)
    ? value
        .filter(isRecord)
        .map((field, index) => normalizeGenericField(field, index))
    : [];
}

function standardGenericFields(fields: GenericField[]) {
  return fields.map((field, index) => normalizeGenericField(field as unknown as Record<string, unknown>, index));
}

function textInputLegacyText(data: Record<string, unknown>, params: Record<string, unknown>) {
  const candidates = [params.text, data.source_text, data.text, data.value, data.content, data.prompt];
  const text = candidates.find((value) => typeof value === "string" && value.trim());
  return typeof text === "string" ? text : "";
}

function inferGenericFieldType(value: unknown): GenericFieldType {
  if (typeof value === "number") return "number";
  if (typeof value === "boolean") return "boolean";
  if (Array.isArray(value)) return "list";
  if (isRecord(value)) return "object";
  const text = typeof value === "string" ? value : prettyValue(value);
  return text.length > 80 || text.includes("\n") ? "long_text" : "text";
}

function genericFieldsFromLegacy(data: Record<string, unknown>, params: Record<string, unknown>): GenericField[] {
  const paramFields = Object.entries(params)
    .filter(([key, value]) => !GENERIC_FIELD_RESERVED_KEYS.has(key) && !HIDDEN_PARAM_KEYS.has(key) && !isEmptyDisplayValue(value))
    .map(([key, value]) => ({
      field_key: key,
      field_name: key,
      field_value: value,
      field_type: inferGenericFieldType(value),
      description: "",
      dr_mapping: "",
      reference_enabled: true,
      field_key_auto: false,
      dr_mapping_auto: true,
    }));
  if (paramFields.length) {
    return paramFields;
  }
  const text = textInputLegacyText(data, params);
  return text
    ? [
        {
          field_key: "field_1",
          field_name: "field_1",
          field_value: text,
          field_type: "long_text",
          description: "",
          dr_mapping: "",
          reference_enabled: true,
          field_key_auto: true,
          dr_mapping_auto: true,
        },
      ]
    : [];
}

function nextGenericFieldKey(fields: GenericField[]) {
  let index = fields.length + 1;
  const used = new Set(fields.map((field) => field.field_key));
  while (used.has(`field_${index}`)) {
    index += 1;
  }
  return `field_${index}`;
}

function genericFieldContext(data: Record<string, unknown>, moduleInstanceRegistry: ModuleInstanceRegistryStore) {
  const parentModule = stringValue(data.parent_module) || stringValue(data.module_instance_id);
  const registryEntry = moduleInstanceRegistry[parentModule];
  const parts = moduleInstanceParts(parentModule);
  return {
    layerId: registryEntry?.layerId || stringValue(data.parent_layer) || stringValue(data.layer_id) || parts.layerId,
    moduleId: registryEntry?.moduleId || stringValue(data.catalog_module_id) || stringValue(data.module_id) || parts.moduleId,
  };
}

function shouldAutoUpdateFieldKey(field: GenericField, fields: GenericField[], index: number) {
  if (!field.field_key) return true;
  if (field.field_key_auto) return true;
  if (field.field_key_auto === false) return false;
  const generatedFromCurrentName = uniqueGenericFieldKey(field.field_name || field.field_key, fields, index);
  return field.field_key === generatedFromCurrentName || /^field_\d+$/.test(field.field_key);
}

function shouldAutoUpdateDrMapping(field: GenericField, layerId: string, moduleId: string) {
  if (!field.dr_mapping) return true;
  if (field.dr_mapping_auto) return true;
  if (field.dr_mapping_auto === false) return false;
  return field.dr_mapping === genericFieldDrMapping(layerId, moduleId, field.field_key);
}

function genericFieldWarnings(fields: GenericField[], field: GenericField, language: Language) {
  const warnings: string[] = [];
  if (!field.field_key.trim()) {
    warnings.push(i18nText(language, "genericFields.validation.emptyKey"));
  }
  if (field.field_key.trim() && fields.filter((candidate) => candidate.field_key === field.field_key).length > 1) {
    warnings.push(i18nText(language, "genericFields.validation.duplicateKey"));
  }
  return warnings;
}

function genericFieldValueText(value: unknown) {
  if (value === null || value === undefined) return "";
  if (typeof value === "string") return value;
  if (typeof value === "number" || typeof value === "boolean") return String(value);
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}

function genericFieldListItems(value: unknown) {
  return Array.isArray(value) ? value : [];
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
  moduleId,
  onFieldFocus,
  onInput
}: {
  fields: Record<string, unknown>[];
  params: Record<string, unknown>;
  language: Language;
  moduleId?: string;
  onFieldFocus?: (key: string) => void;
  onInput?: (key: string, value: unknown) => void;
}) {
  if (!fields.length) {
    const configuredParams = displayObjectEntries(
      Object.fromEntries(
        Object.entries(params).filter(
          ([key, value]) =>
            !HIDDEN_PARAM_KEYS.has(key) &&
            !["mode", "field_registry", "config_mode", "checkbox_config"].includes(key) &&
            !isEmptyDisplayValue(value)
        )
      )
    );
    if (Object.keys(configuredParams).length) {
      return (
        <div className="node-inputs__configured">
          <CoreParamValue value={configuredParams} language={language} />
        </div>
      );
    }
    return <div className="node-inputs__empty">{translate(language, "node.compileTime.fields.empty", "No fields configured")}</div>;
  }

  const commitFields = (nextFields: Record<string, unknown>[]) => {
    if (!fields.some(isFirstInteractionField)) {
      onInput?.("fields", nextFields);
    }
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
              <StructuredValueEditor
                value={value}
                language={language}
                moduleId={moduleId}
                contextKey={compileTimeFieldKey(field, index)}
                onValueChange={(next) => commitFields(updateFieldValue(fields, index, next))}
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

function StructuredValueEditor({
  value,
  onValueChange,
  language,
  depth = 0,
  moduleId,
  contextKey,
  options,
}: {
  value: unknown;
  onValueChange: (value: unknown) => void;
  language: Language;
  depth?: number;
  moduleId?: string;
  contextKey?: string;
  options?: Record<string, StructuredOption[]>;
}) {
  if (Array.isArray(value)) {
    return (
      <div className="generic-fields-editor__structured-list">
        {!value.length ? <small className="generic-fields-editor__hint">{i18nText(language, "genericFields.emptyArray")}</small> : null}
        {value.map((item, index) => (
          <div key={`${index}-${typeof item === "string" ? item : "item"}`} className="generic-fields-editor__structured-row">
            <span className="generic-fields-editor__structured-index">{index + 1}</span>
            <StructuredValueEditor
              value={item}
              language={language}
              depth={depth + 1}
              moduleId={moduleId}
              contextKey={contextKey}
              options={options}
              onValueChange={(nextValue) => onValueChange(value.map((candidate, candidateIndex) => (candidateIndex === index ? nextValue : candidate)))}
            />
            <button
              className="generic-fields-editor__structured-action nodrag"
              type="button"
              onPointerDown={stopInputEventPropagation}
              onClick={() => onValueChange(value.filter((_, candidateIndex) => candidateIndex !== index))}
              aria-label={i18nText(language, "genericFields.removeField")}
            >
              −
            </button>
          </div>
        ))}
        <button
          className="generic-fields-editor__structured-action generic-fields-editor__structured-add nodrag"
          type="button"
          onPointerDown={stopInputEventPropagation}
          onClick={() => onValueChange([...value, ""])}
        >
          +
        </button>
      </div>
    );
  }
  if (isRecord(value)) {
    const entries = Object.entries(value);
    return (
      <div className={`generic-fields-editor__structured-object generic-fields-editor__structured-object--depth-${Math.min(depth, 2)}`}>
        {entries.map(([key, item]) => (
          <div key={key} className="generic-fields-editor__structured-object-row">
            <span title={usesLocalizedStructuredIds(moduleId) ? key : undefined}>
              {usesLocalizedStructuredIds(moduleId) ? localizedCoreKey(language, key, moduleId) : key}
            </span>
            <StructuredValueEditor value={item} language={language} depth={depth + 1} moduleId={moduleId} contextKey={key} options={options} onValueChange={(nextValue) => onValueChange({ ...value, [key]: nextValue })} />
          </div>
        ))}
      </div>
    );
  }
  if (typeof value === "boolean") {
    return (
      <input
        className="nodrag"
        type="checkbox"
        checked={value}
        onPointerDown={stopInputEventPropagation}
        onKeyDown={stopInputEventPropagation}
        onChange={(event) => onValueChange(event.target.checked)}
      />
    );
  }
  if (typeof value === "number") {
    return <NodeTextInput className="nodrag" type="number" value={String(value)} onValueChange={(next) => onValueChange(next.trim() === "" ? "" : Number(next))} />;
  }
  const text = typeof value === "string" ? value : "";
  const structuredOptions = contextKey ? options?.[contextKey] ?? [] : [];
  if (structuredOptions.length) {
    return (
      <select
        className="nodrag"
        value={text}
        onPointerDown={stopInputEventPropagation}
        onKeyDown={stopInputEventPropagation}
        onChange={(event) => onValueChange(event.target.value)}
      >
        {structuredOptions.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label_key ? translate(language, option.label_key, option.value) : option.value}
          </option>
        ))}
      </select>
    );
  }
  const localizedStructuredId =
    /^[A-Za-z][A-Za-z0-9_-]*$/.test(text) ||
    (moduleId === "dialogue_runtime_profile" && /^[A-Za-z][A-Za-z0-9_:-]*$/.test(text));
  if (text && usesLocalizedStructuredIds(moduleId) && localizedStructuredId) {
    return (
      <div className="layer11-id-editor" title={text}>
        <span>{localizedCoreValue(language, text, moduleId)}</span>
        <details className="layer11-id-editor__advanced">
          <summary>{translate(language, "layer11.common.internalId", "Internal ID")}</summary>
          <NodeTextInput className="nodrag layer11-id-editor__raw" value={text} onValueChange={onValueChange} aria-label={localizedCoreKey(language, contextKey || text, moduleId)} />
        </details>
      </div>
    );
  }
  if (text.includes("\n") || text.length > 80) {
    return <NodeTextarea className="nodrag" rows={2} value={text} onValueChange={onValueChange} />;
  }
  return <NodeTextInput className="nodrag" value={text} onValueChange={onValueChange} />;
}

function Layer11RoleCards({ value, moduleId, language }: { value: Record<string, unknown>; moduleId?: string; language: Language }) {
  return (
    <div className="layer11-role-cards">
      {Object.entries(value).map(([roleId, role]) => {
        const roleData = isRecord(role) ? role : {};
        const name = resolveLayer11DisplayText({ value: roleId, valueType: "value", moduleId, language });
        const description = resolveLayer11RoleDescription({ roleId, moduleId, language }) || stringValue(roleData.description);
        return (
          <article key={roleId} className="layer11-role-card" title={roleId}>
            <strong>{name}</strong>
            {description ? <small>{description}</small> : null}
          </article>
        );
      })}
    </div>
  );
}

function GenericTextInputRenderer({
  fields,
  data,
  language,
  onFieldFocus,
  onInput,
}: {
  fields: NodeInputField[];
  data: Record<string, unknown>;
  language: Language;
  onFieldFocus?: (key: string) => void;
  onInput?: (key: string, value: unknown) => void;
}) {
  const params = paramsFromNodeData(data);
  const mode = stringValue(params.mode) === "generic_fields" ? "generic_fields" : "text";
  const genericFields = genericFieldsFromParams(params.fields);
  const moduleInstanceRegistry = useCanvasStore((state) => state.moduleInstanceRegistry);
  const { layerId, moduleId } = genericFieldContext(data, moduleInstanceRegistry);
  const legacyText = textInputLegacyText(data, params);
  const [expandedFieldKeys, setExpandedFieldKeys] = useState<Set<string>>(() => new Set());
  const commitParams = (nextParams: Record<string, unknown>) => {
    onInput?.("params", nextParams);
    for (const [key, value] of Object.entries(nextParams)) {
      onInput?.(key, value);
    }
  };
  const commitFields = (nextFields: GenericField[]) => {
    const standardFields = standardGenericFields(nextFields);
    commitParams({
      ...params,
      mode: "generic_fields",
      text: stringValue(params.text) || legacyText,
      fields: standardFields,
    });
  };
  const rawFieldsSnapshot = JSON.stringify(params.fields ?? []);
  const normalizedFieldsSnapshot = JSON.stringify(genericFields);
  useEffect(() => {
    if (!onInput || mode !== "generic_fields" || !["layer_1", "layer_3"].includes(layerId) || rawFieldsSnapshot === normalizedFieldsSnapshot) {
      return;
    }
    commitFields(genericFields);
  }, [genericFields, layerId, mode, normalizedFieldsSnapshot, onInput, rawFieldsSnapshot]);
  const convertToFields = () => {
    const sourceFields = genericFields.length ? genericFields : genericFieldsFromLegacy(data, params);
    const nextFields = sourceFields.map((field, index) => {
      const fieldKey = field.field_key || uniqueGenericFieldKey(field.field_name || `field_${index + 1}`, sourceFields, index);
      return {
        ...field,
        field_key: fieldKey,
        field_name: field.field_name || fieldKey,
        dr_mapping: field.dr_mapping || genericFieldDrMapping(layerId, moduleId, fieldKey),
        reference_enabled: field.reference_enabled !== false,
        field_key_auto: field.field_key_auto ?? !field.field_key,
        dr_mapping_auto: field.dr_mapping_auto ?? !field.dr_mapping,
      };
    });
    commitParams({
      ...params,
      mode: "generic_fields",
      text: stringValue(params.text) || legacyText,
      fields: nextFields,
    });
  };
  const addField = () => {
    const key = nextGenericFieldKey(genericFields);
    commitFields([
      ...genericFields,
      {
        field_key: key,
        field_name: key,
        field_value: "",
        field_type: "long_text",
        description: "",
        dr_mapping: genericFieldDrMapping(layerId, moduleId, key),
        reference_enabled: true,
        field_key_auto: true,
        dr_mapping_auto: true,
      },
    ]);
  };
  const patchField = (index: number, patchValue: Partial<GenericField>) => {
    commitFields(genericFields.map((field, fieldIndex) => (fieldIndex === index ? { ...field, ...patchValue } : field)));
  };
  const patchFieldName = (index: number, value: string) => {
    const field = genericFields[index];
    if (!field) return;
    const shouldUpdateKey = shouldAutoUpdateFieldKey(field, genericFields, index);
    const nextKey = shouldUpdateKey ? uniqueGenericFieldKey(value, genericFields, index) : field.field_key;
    const shouldUpdateMapping = shouldAutoUpdateDrMapping(field, layerId, moduleId);
    patchField(index, {
      field_name: value,
      field_name_custom: true,
      field_key: nextKey,
      field_key_auto: shouldUpdateKey ? true : field.field_key_auto,
      dr_mapping: shouldUpdateMapping ? genericFieldDrMapping(layerId, moduleId, nextKey) : field.dr_mapping,
      dr_mapping_auto: shouldUpdateMapping ? true : field.dr_mapping_auto,
    });
  };
  const patchFieldKey = (index: number, value: string) => {
    const field = genericFields[index];
    if (!field) return;
    const nextKey = value.trim() ? safeGenericFieldKey(value) : "";
    const shouldUpdateMapping = shouldAutoUpdateDrMapping(field, layerId, moduleId);
    patchField(index, {
      field_key: nextKey,
      field_key_auto: false,
      dr_mapping: shouldUpdateMapping ? genericFieldDrMapping(layerId, moduleId, nextKey) : field.dr_mapping,
      dr_mapping_auto: shouldUpdateMapping ? true : field.dr_mapping_auto,
    });
  };
  const patchDrMapping = (index: number, value: string) => {
    patchField(index, {
      dr_mapping: value,
      dr_mapping_auto: false,
    });
  };
  const removeField = (index: number) => {
    if (typeof window !== "undefined" && !window.confirm(i18nText(language, "genericFields.confirmDelete"))) {
      return;
    }
    commitFields(genericFields.filter((_, fieldIndex) => fieldIndex !== index));
  };
  const toggleExpanded = (fieldIdentity: string) => {
    setExpandedFieldKeys((current) => {
      const next = new Set(current);
      if (next.has(fieldIdentity)) {
        next.delete(fieldIdentity);
      } else {
        next.add(fieldIdentity);
      }
      return next;
    });
  };
  const renderFieldValueControl = (field: GenericField, index: number, placeholder?: string) => {
    if (field.field_type === "boolean") {
      return (
        <div className="generic-fields-editor__toggle generic-fields-editor__value-toggle">
          <input
            className="nodrag"
            type="checkbox"
            checked={field.field_value === true}
            onPointerDown={stopInputEventPropagation}
            onKeyDown={stopInputEventPropagation}
            onChange={(event) => patchField(index, { field_value: event.target.checked })}
          />
        </div>
      );
    }
    if (field.field_type === "number") {
      return (
        <NodeTextInput
          className="nodrag"
          type="number"
          min={field.minimum}
          max={field.maximum}
          step={field.minimum === 0 && field.maximum === 1 ? 0.01 : undefined}
          value={genericFieldValueText(field.field_value)}
          onValueChange={(value) => {
            if (value.trim() === "") {
              patchField(index, { field_value: "" });
              return;
            }
            const parsed = Number(value);
            const minimum = field.minimum ?? Number.NEGATIVE_INFINITY;
            const maximum = field.maximum ?? Number.POSITIVE_INFINITY;
            patchField(index, { field_value: Math.min(maximum, Math.max(minimum, parsed)) });
          }}
        />
      );
    }
    if (field.field_type === "text") {
      if (field.enum_options?.length) {
        return (
          <select
            className="nodrag"
            value={stringValue(field.field_value)}
            onPointerDown={stopInputEventPropagation}
            onKeyDown={stopInputEventPropagation}
            onChange={(event) => patchField(index, { field_value: event.target.value })}
          >
            {field.enum_options.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label_key ? translate(language, option.label_key, option.value) : option.value}
              </option>
            ))}
          </select>
        );
      }
      return (
        <NodeTextInput
          className="nodrag"
          value={genericFieldValueText(field.field_value)}
          placeholder={placeholder}
          onValueChange={(value) => patchField(index, { field_value: value })}
        />
      );
    }
    if (field.field_type === "list") {
      return (
        <StructuredValueEditor
          value={genericFieldListItems(field.field_value)}
          language={language}
          moduleId={moduleId}
          contextKey={field.field_key}
          options={field.structured_options}
          onValueChange={(value) => patchField(index, { field_value: Array.isArray(value) ? value : [] })}
        />
      );
    }
    if (field.field_type === "object") {
      if (isRecord(field.field_value) && isLayer11RoleCollection(field.field_key, moduleId)) {
        return <Layer11RoleCards value={field.field_value} moduleId={moduleId} language={language} />;
      }
      return (
        <StructuredValueEditor
          value={isRecord(field.field_value) ? field.field_value : {}}
          language={language}
          moduleId={moduleId}
          contextKey={field.field_key}
          options={field.structured_options}
          onValueChange={(value) => patchField(index, { field_value: isRecord(value) ? value : {} })}
        />
      );
    }
    return (
      <NodeTextarea
        className="nodrag"
        rows={3}
        value={genericFieldValueText(field.field_value)}
        placeholder={placeholder}
        onValueChange={(value) => patchField(index, { field_value: value })}
      />
    );
  };

  if (mode !== "generic_fields") {
    return (
      <div className="generic-fields-editor">
        <div className="generic-fields-editor__mode">
          <span>{i18nText(language, "genericFields.mode.text")}</span>
          <button className="nodrag" type="button" onPointerDown={stopInputEventPropagation} onClick={convertToFields} disabled={!onInput}>
            {i18nText(language, "genericFields.convert")}
          </button>
        </div>
        {onInput ? (
          <NodeInputRenderer fields={fields} data={data} language={language} onFieldFocus={onFieldFocus} onInput={onInput} />
        ) : (
          <div className="node-inputs__empty">{translate(language, "node.inputs.readonly", "Read-only node")}</div>
        )}
      </div>
    );
  }

  return (
    <div className="generic-fields-editor">
      <div className="generic-fields-editor__mode">
        <span>{i18nText(language, "genericFields.summary")}</span>
        <button className="nodrag" type="button" onPointerDown={stopInputEventPropagation} onClick={addField} disabled={!onInput}>
          {i18nText(language, "genericFields.addField")}
        </button>
      </div>
      <div className="generic-fields-editor__summary">
        <span>{i18nText(language, "genericFields.fieldCount")}：{genericFields.length}</span>
        <span>{i18nText(language, "genericFields.referenceEnabledCount")}：{genericFields.filter((field) => field.reference_enabled !== false).length}</span>
      </div>
      <div className="generic-fields-editor__scroll nodrag nopan" onPointerDown={stopInputEventPropagation} onWheel={(event) => event.stopPropagation()}>
        {genericFields.length ? (
          genericFields.map((field, index) => {
            const warnings = genericFieldWarnings(genericFields, field, language);
            const fieldIdentity = `${index}:${field.field_key || field.field_name || "field"}`;
            const expanded = expandedFieldKeys.has(fieldIdentity);
            const localizedFieldName =
              !field.field_name_custom && field.i18n_keys?.label
                ? translate(language, field.i18n_keys.label, field.field_name || field.field_key)
                : field.field_name || field.field_key;
            const localizedDescription =
              !field.description_custom && field.i18n_keys?.description
                ? translate(language, field.i18n_keys.description, field.description ?? "")
                : field.description ?? "";
            const localizedPlaceholder = field.i18n_keys?.placeholder
              ? translate(language, field.i18n_keys.placeholder, "")
              : undefined;
            const localizedHelp = field.i18n_keys?.help
              ? translate(language, field.i18n_keys.help, "")
              : "";
            const localizedDefault = field.i18n_keys?.default
              ? translate(language, field.i18n_keys.default, "")
              : "";
            const localizedValidationError = field.i18n_keys?.validation_error
              ? translate(language, field.i18n_keys.validation_error, "")
              : "";
            const numberInvalid = field.field_type === "number" && (
              typeof field.field_value !== "number" ||
              !Number.isFinite(field.field_value) ||
              (typeof field.minimum === "number" && field.field_value < field.minimum) ||
              (typeof field.maximum === "number" && field.field_value > field.maximum)
            );
            const enumInvalid = Boolean(
              field.enum_options?.length &&
              !field.enum_options.some((option) => option.value === field.field_value)
            );
            return (
              <article key={`${index}-${field.field_key}`} className="generic-fields-editor__field-card">
              <div className="generic-fields-editor__field-head">
                <label>
                  <span>
                    {i18nText(language, "genericFields.fieldName")}
                    {field.required === false ? ` · ${i18nText(language, "genericFields.optional")}` : ""}
                  </span>
                  <NodeTextInput className="nodrag" value={localizedFieldName} onValueChange={(value) => patchFieldName(index, value)} />
                </label>
                <button className="generic-fields-editor__expand nodrag" type="button" onPointerDown={stopInputEventPropagation} onClick={() => toggleExpanded(fieldIdentity)} title={i18nText(language, expanded ? "genericFields.collapseField" : "genericFields.expandField")}>
                  {warnings.length && !expanded ? <span className="generic-fields-editor__warning-dot" aria-label={i18nText(language, "genericFields.warning")}>!</span> : null}
                  {expanded ? "−" : "+"}
                </button>
              </div>
              <label className="generic-fields-editor__block">
                <span>{i18nText(language, "genericFields.fieldValue")}</span>
                {renderFieldValueControl(field, index, localizedPlaceholder)}
                {localizedHelp ? <small className="generic-fields-editor__hint">{localizedHelp}</small> : null}
                {localizedDefault ? <small className="generic-fields-editor__hint">{localizedDefault}</small> : null}
                {(numberInvalid || enumInvalid) && localizedValidationError ? (
                  <small className="generic-fields-editor__warning" role="alert">{localizedValidationError}</small>
                ) : null}
              </label>
              <label className="generic-fields-editor__block">
                <span>{i18nText(language, "genericFields.description")}</span>
                <NodeTextarea
                  className="nodrag"
                  rows={2}
                  value={localizedDescription}
                  onValueChange={(value) => patchField(index, { description: value, description_custom: true })}
                />
              </label>
              {expanded ? (
                <section className="generic-fields-editor__advanced">
                  <h5>{i18nText(language, "genericFields.advancedSettings")}</h5>
                  <div className="generic-fields-editor__grid">
                    <label>
                      <span>{i18nText(language, "genericFields.fieldKey")}</span>
                      <NodeTextInput className="nodrag" value={field.field_key} onValueChange={(value) => patchFieldKey(index, value)} />
                      {field.field_key_auto || !field.field_key ? <small className="generic-fields-editor__hint">{i18nText(language, "genericFields.autoGenerated")}</small> : null}
                    </label>
                    <label>
                      <span>{i18nText(language, "genericFields.fieldType")}</span>
                      <select className="nodrag" value={field.field_type || "long_text"} onPointerDown={stopInputEventPropagation} onKeyDown={stopInputEventPropagation} onChange={(event) => patchField(index, { field_type: event.target.value as GenericFieldType })}>
                        {GENERIC_FIELD_TYPES.map((type) => (
                          <option key={type} value={type}>
                            {i18nText(language, `genericFields.type.${type}`)}
                          </option>
                        ))}
                      </select>
                    </label>
                    <label>
                      <span>{i18nText(language, "genericFields.drMapping")}</span>
                      <NodeTextInput className="nodrag" value={field.dr_mapping ?? ""} onValueChange={(value) => patchDrMapping(index, value)} />
                      {field.dr_mapping_auto || !field.dr_mapping ? <small className="generic-fields-editor__hint">{i18nText(language, "genericFields.autoGenerated")}</small> : null}
                    </label>
                    <label className="generic-fields-editor__toggle">
                      <input
                        className="nodrag"
                        type="checkbox"
                        checked={Boolean(field.reference_enabled)}
                        onPointerDown={stopInputEventPropagation}
                        onKeyDown={stopInputEventPropagation}
                        onChange={(event) => patchField(index, { reference_enabled: event.target.checked })}
                      />
                      <span>{i18nText(language, "genericFields.referenceEnabled")}</span>
                    </label>
                  </div>
                  {warnings.length ? (
                    <ul className="generic-fields-editor__warnings">
                      {warnings.map((warning) => (
                        <li key={warning}>{warning}</li>
                      ))}
                    </ul>
                  ) : null}
                  <button className="generic-fields-editor__remove nodrag" type="button" onPointerDown={stopInputEventPropagation} onClick={() => removeField(index)}>
                    {i18nText(language, "genericFields.removeField")}
                  </button>
                </section>
              ) : null}
              </article>
            );
          })
        ) : (
          <div className="node-inputs__empty">{translate(language, "common.empty", "Empty")}</div>
        )}
      </div>
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

type ReferenceValueType = "text" | "number" | "boolean" | "object" | "array" | "unknown";
type ReferenceScope = "module" | "node" | "field";
type StructuredOption = { value: string; label_key?: string };
type ReferenceAuthoritySourceType =
  | "core_fact"
  | "derived_config"
  | "authoritative_constraint"
  | "authoritative_permission"
  | "dynamic_state"
  | "normal_output";
type GenericFieldType = "text" | "long_text" | "number" | "boolean" | "list" | "object" | "unknown";
type ModuleGraphStore = ReturnType<typeof useCanvasStore.getState>["moduleGraphs"];
type ModuleInstanceRegistryStore = ReturnType<typeof useCanvasStore.getState>["moduleInstanceRegistry"];

type ReferenceExportField = {
  field_key: string;
  field_path: string;
  display_name?: string;
  description?: string;
  label_key?: string;
  description_key?: string;
  value_type?: ReferenceValueType;
  required?: boolean;
};

type GenericField = {
  field_key: string;
  field_name: string;
  field_value: unknown;
  field_type: GenericFieldType;
  description?: string;
  dr_mapping?: string;
  reference_enabled?: boolean;
  required?: boolean;
  field_key_auto?: boolean;
  dr_mapping_auto?: boolean;
  i18n_keys?: Record<string, string>;
  field_name_custom?: boolean;
  description_custom?: boolean;
  enum_options?: StructuredOption[];
  structured_options?: Record<string, StructuredOption[]>;
  minimum?: number;
  maximum?: number;
};

type ReferenceOutputSource = {
  layerId: string;
  moduleId: string;
  moduleInstanceId: string;
  nodeId: string;
  label: string;
  exportName: string;
  exportScope: ReferenceScope;
  exportScopes: ReferenceScope[];
  allowModuleLevelReference: boolean;
  exportFields: ReferenceExportField[];
  allowLayers: string[];
  forbiddenLayers: string[];
  authoritySourceType: ReferenceAuthoritySourceType;
  isCoreSource: boolean;
  overrideAllowed: boolean;
};

const REFERENCE_TYPES = ["references", "outputs_to", "constrains", "conflicts_with", "overrides_forbidden"] as const;
const REFERENCE_SCOPES: ReferenceScope[] = ["module", "node", "field"];
const REFERENCE_VALUE_TYPES: ReferenceValueType[] = ["text", "number", "boolean", "object", "array", "unknown"];
const REFERENCE_AUTHORITY_SOURCE_TYPES: ReferenceAuthoritySourceType[] = [
  "core_fact",
  "derived_config",
  "authoritative_constraint",
  "authoritative_permission",
  "dynamic_state",
  "normal_output",
];
const REFERENCE_DOWNSTREAM_REWRITE_DEFAULT_OFF_TYPES = new Set<ReferenceAuthoritySourceType>([
  "core_fact",
  "authoritative_constraint",
  "authoritative_permission",
]);

function referenceAuthoritySourceTypeForLayer(layerId?: string): ReferenceAuthoritySourceType {
  switch (layerId) {
    case "layer_1":
      return "core_fact";
    case "layer_2":
    case "layer_7":
    case "layer_8":
    case "layer_11":
      return "derived_config";
    case "layer_3":
    case "layer_12":
      return "authoritative_constraint";
    case "layer_4":
      return "authoritative_permission";
    case "layer_5":
      return "dynamic_state";
    default:
      return "normal_output";
  }
}

function referenceAuthoritySourceType(value: unknown, layerId?: string): ReferenceAuthoritySourceType {
  return REFERENCE_AUTHORITY_SOURCE_TYPES.includes(value as ReferenceAuthoritySourceType)
    ? (value as ReferenceAuthoritySourceType)
    : referenceAuthoritySourceTypeForLayer(layerId);
}

function moduleInstanceParts(instanceId: string) {
  const [layerId = "", moduleId = instanceId] = instanceId.split("::");
  return { layerId, moduleId };
}

function referenceExportFields(value: unknown): ReferenceExportField[] {
  return Array.isArray(value)
    ? value
        .filter(isRecord)
        .map((field) => ({
          field_key: stringValue(field.field_key) || stringValue(field.field_path),
          field_path: stringValue(field.field_path) || stringValue(field.field_key),
          display_name: stringValue(field.display_name),
          description: stringValue(field.description),
          label_key: stringValue(field.label_key),
          description_key: stringValue(field.description_key),
          value_type: REFERENCE_VALUE_TYPES.includes(field.value_type as ReferenceValueType) ? (field.value_type as ReferenceValueType) : "unknown",
          required: Boolean(field.required),
        }))
        .filter((field) => field.field_key || field.field_path)
    : [];
}

function referenceValueTypeFromGenericField(type: GenericFieldType): ReferenceValueType {
  if (type === "long_text") return "text";
  if (type === "list") return "array";
  return REFERENCE_VALUE_TYPES.includes(type as ReferenceValueType) ? (type as ReferenceValueType) : "unknown";
}

function referenceValueTypeFromValue(value: unknown): ReferenceValueType {
  if (Array.isArray(value)) return "array";
  if (value === null || value === undefined) return "unknown";
  if (typeof value === "string") return "text";
  if (typeof value === "number") return "number";
  if (typeof value === "boolean") return "boolean";
  if (typeof value === "object") return "object";
  return "unknown";
}

function automaticReferenceExportFields(nodes: WorkflowNode[]): ReferenceExportField[] {
  const candidates = new Map<string, ReferenceExportField>();
  const blockedFieldPaths = new Set<string>();
  for (const node of nodes) {
    const data = workflowNodeData(node);
    const params = paramsFromNodeData(data);
    if (workflowNodeType(node) === "text_input" && params.mode === "generic_fields") {
      for (const field of genericFieldsFromParams(params.fields)) {
        if (!field.field_key) continue;
        if (field.reference_enabled === false) {
          blockedFieldPaths.add(field.field_key);
          candidates.delete(field.field_key);
          continue;
        }
        candidates.set(field.field_key, {
          field_key: field.field_key,
          field_path: field.field_key,
          display_name: field.field_name || field.field_key,
          description: field.description || "",
          value_type: referenceValueTypeFromGenericField(field.field_type),
          required: false,
        });
      }
    }
  }
  for (const node of nodes) {
    const data = workflowNodeData(node);
    if (workflowNodeType(node) !== "module_output") continue;
    const outputs = isRecord(data.outputs) ? data.outputs : {};
    for (const output of Object.values(outputs)) {
      if (!isRecord(output) || !isRecord(output.fields)) continue;
      for (const [fieldKey, fieldValue] of Object.entries(output.fields)) {
        if (!fieldKey || blockedFieldPaths.has(fieldKey) || candidates.has(fieldKey)) continue;
        candidates.set(fieldKey, {
          field_key: fieldKey,
          field_path: fieldKey,
          display_name: fieldKey,
          description: "",
          value_type: referenceValueTypeFromValue(fieldValue),
          required: false,
        });
      }
    }
  }
  return [...candidates.values()];
}

function appendMissingReferenceExportFields(value: unknown, candidates: ReferenceExportField[]): Record<string, unknown>[] {
  const existing = Array.isArray(value) ? value.filter(isRecord).map((field) => ({ ...field })) : [];
  const existingPaths = new Set(
    existing
      .map((field) => stringValue(field.field_path) || stringValue(field.field_key))
      .filter(Boolean)
  );
  for (const candidate of candidates) {
    const path = candidate.field_path || candidate.field_key;
    if (!path || existingPaths.has(path)) continue;
    existing.push(candidate);
    existingPaths.add(path);
  }
  return existing;
}

function referenceStringArray(value: unknown): string[] {
  return Array.isArray(value) ? value.map((item) => stringValue(item)).filter(Boolean) : [];
}

function referenceScope(value: unknown, fallback: ReferenceScope = "field"): ReferenceScope {
  return REFERENCE_SCOPES.includes(value as ReferenceScope) ? (value as ReferenceScope) : fallback;
}

function referenceScopes(value: unknown): ReferenceScope[] {
  if (!Array.isArray(value)) {
    return [...REFERENCE_SCOPES];
  }
  const scopes = value.filter((scope): scope is ReferenceScope => REFERENCE_SCOPES.includes(scope as ReferenceScope));
  return scopes.length ? scopes : [...REFERENCE_SCOPES];
}

function referenceOutputScopes(params: Record<string, unknown>): ReferenceScope[] {
  if (Array.isArray(params.export_scopes)) {
    const scopes = params.export_scopes.filter((scope): scope is ReferenceScope => REFERENCE_SCOPES.includes(scope as ReferenceScope));
    if (scopes.length) {
      return scopes;
    }
  }
  if (REFERENCE_SCOPES.includes(params.export_scope as ReferenceScope)) {
    return [params.export_scope as ReferenceScope];
  }
  return [...REFERENCE_SCOPES];
}

function normalizeReferenceOutputParams(params: Record<string, unknown>, layerId?: string): Record<string, unknown> {
  const exportScopes = referenceOutputScopes(params);
  const authoritySourceType = referenceAuthoritySourceType(params.authority_source_type, layerId);
  const legacyExportScope = exportScopes.includes("module") ? "module" : exportScopes[0];
  return {
    ...params,
    export_scopes: exportScopes,
    export_scope: legacyExportScope,
    allow_module_level_reference: exportScopes.includes("module"),
    authority_source_type: authoritySourceType,
    is_core_source: authoritySourceType === "core_fact",
    override_allowed: typeof params.override_allowed === "boolean" ? params.override_allowed : false,
  };
}

function referenceFieldLabel(field: ReferenceExportField) {
  return field.display_name || field.field_path || field.field_key;
}

function referenceFieldDisplayName(field: ReferenceExportField, language: Language) {
  const key = field.field_key || field.field_path;
  return (
    field.display_name ||
    (field.label_key ? translateIfPresent(language, field.label_key) : "") ||
    translateIfPresent(language, `field.identity.${key}.label`) ||
    GENERIC_FIELD_KEY_NAME_MAP[key] ||
    field.field_path ||
    field.field_key
  );
}

function referenceLayerDisplayName(layerId: string, language: Language) {
  return translateIfPresent(language, `layer.${layerId}`) || layerId;
}

function referenceModuleDisplayName(moduleId: string, language: Language) {
  return translateIfPresent(language, `module.${moduleId}`) || moduleId;
}

function schemaNodeFromGraphNode(value: unknown): WorkflowNode | null {
  const record = isRecord(value) ? value : {};
  const data = isRecord(record.data) ? record.data : {};
  const schemaNode = isRecord(data.schemaNode) ? data.schemaNode : record;
  return isRecord(schemaNode) ? (schemaNode as unknown as WorkflowNode) : null;
}

function workflowNodesFromGraph(graph: { nodes?: unknown[] } | undefined): WorkflowNode[] {
  return Array.isArray(graph?.nodes) ? graph.nodes.map(schemaNodeFromGraphNode).filter((node): node is WorkflowNode => Boolean(node)) : [];
}

function referenceOutputSourcesFromNodes(
  nodes: WorkflowNode[],
  moduleInstanceId: string,
  moduleInstanceRegistry: ModuleInstanceRegistryStore
): ReferenceOutputSource[] {
  const parts = moduleInstanceParts(moduleInstanceId);
  const registryEntry = moduleInstanceRegistry[moduleInstanceId];
  const layerId = registryEntry?.layerId || parts.layerId;
  const moduleId = registryEntry?.moduleId || parts.moduleId;
  return nodes
    .filter((node) => workflowNodeType(node) === "reference_output")
    .map((node) => {
      const data = workflowNodeData(node);
      const params = normalizeReferenceOutputParams({ ...data, ...paramsFromNodeData(data) }, layerId);
      const label = translateIfPresent(useCanvasStore.getState().language, node.title_key) || node.title_fallback || node.node_id;
      const exportScopes = referenceOutputScopes(params);
      const authoritySourceType = referenceAuthoritySourceType(params.authority_source_type, layerId);
      return {
        layerId,
        moduleId,
        moduleInstanceId,
        nodeId: node.node_id,
        label,
        exportName:
          stringValue(params.export_name) ||
          (stringValue(params.export_name_key) ? translateIfPresent(useCanvasStore.getState().language, stringValue(params.export_name_key)) : "") ||
          label,
        exportScope: referenceScope(params.export_scope),
        exportScopes,
        allowModuleLevelReference: Boolean(params.allow_module_level_reference),
        exportFields: referenceExportFields(params.export_fields),
        allowLayers: referenceStringArray(params.allow_layers),
        forbiddenLayers: referenceStringArray(params.forbidden_layers),
        authoritySourceType,
        isCoreSource: authoritySourceType === "core_fact",
        overrideAllowed: Boolean(params.override_allowed),
      };
    });
}

function referenceOutputSources(
  moduleGraphs: ModuleGraphStore,
  moduleInstanceRegistry: ModuleInstanceRegistryStore,
  currentModuleInstanceId: string,
  currentNodes: WorkflowNode[]
) {
  const byKey = new Map<string, ReferenceOutputSource>();
  for (const [moduleInstanceId, graph] of Object.entries(moduleGraphs)) {
    for (const source of referenceOutputSourcesFromNodes(workflowNodesFromGraph(graph), moduleInstanceId, moduleInstanceRegistry)) {
      byKey.set(`${source.moduleInstanceId}:${source.nodeId}`, source);
    }
  }
  if (currentModuleInstanceId) {
    for (const source of referenceOutputSourcesFromNodes(currentNodes, currentModuleInstanceId, moduleInstanceRegistry)) {
      byKey.set(`${source.moduleInstanceId}:${source.nodeId}`, source);
    }
  }
  return [...byKey.values()];
}

function ReferenceOutputRenderer({
  data,
  language,
  onInput,
}: {
  data: Record<string, unknown>;
  language: Language;
  onInput?: (key: string, value: unknown) => void;
}) {
  const rawParams = paramsFromNodeData(data);
  const moduleInstanceRegistry = useCanvasStore((state) => state.moduleInstanceRegistry);
  const moduleNames = useCanvasStore((state) => state.moduleNames);
  const currentNodes = useModuleWorkflowNodes();
  const currentModuleInstanceId = stringValue(data.parent_module);
  const currentModule = moduleInstanceRegistry[currentModuleInstanceId];
  const currentLayerId = currentModule?.layerId || moduleInstanceParts(currentModuleInstanceId).layerId;
  const currentModuleId = currentModule?.moduleId || moduleInstanceParts(currentModuleInstanceId).moduleId;
  const autoExportFields = useMemo(() => automaticReferenceExportFields(currentNodes), [currentNodes]);
  const mergedExportFields = appendMissingReferenceExportFields(rawParams.export_fields, autoExportFields);
  const params = normalizeReferenceOutputParams({ ...rawParams, export_fields: mergedExportFields }, currentLayerId);
  const fields = referenceExportFields(params.export_fields);
  const currentModuleName =
    moduleNames[currentModuleInstanceId] ||
    moduleNames[currentModuleId] ||
    referenceModuleDisplayName(currentModuleId, language) ||
    currentModuleInstanceId ||
    i18nText(language, "common.unknown");
  const activeScopes = referenceOutputScopes(params);
  const autoExportName =
    stringValue(params.export_name) ||
    (stringValue(params.export_name_key) ? translateIfPresent(language, stringValue(params.export_name_key)) : "") ||
    currentModuleName;
  const fieldSummary = fields.map((field) => referenceFieldDisplayName(field, language)).filter(Boolean).join(", ");
  const autoExportDescription =
    stringValue(params.export_description) ||
    (stringValue(params.export_description_key)
      ? translateIfPresent(language, stringValue(params.export_description_key))
      : "") ||
    (fieldSummary
      ? `${i18nText(language, "reference.autoOutputContent")}: ${fieldSummary}`
      : i18nText(language, "reference.autoOutputContentEmpty"));
  const authoritySourceType = referenceAuthoritySourceType(params.authority_source_type, currentLayerId);
  const commitParams = (nextParams: Record<string, unknown>) => {
    onInput?.("params", nextParams);
    for (const [key, value] of Object.entries(nextParams)) {
      onInput?.(key, value);
    }
  };
  const patch = (patchValue: Record<string, unknown>) => commitParams({ ...params, ...patchValue });
  const patchField = (index: number, patchValue: Partial<ReferenceExportField>) => {
    patch({ export_fields: fields.map((field, fieldIndex) => (fieldIndex === index ? { ...field, ...patchValue } : field)) });
  };
  const addField = () => {
    patch({
      export_fields: [
        ...fields,
        {
          field_key: "",
          field_path: "",
          display_name: "",
          description: "",
          value_type: "unknown",
          required: false,
        },
      ],
    });
  };
  const removeField = (index: number) => {
    patch({ export_fields: fields.filter((_, fieldIndex) => fieldIndex !== index) });
  };
  const toggleExportScope = (scope: ReferenceScope, checked: boolean) => {
    const nextScopes = checked ? [...new Set([...activeScopes, scope])] : activeScopes.filter((item) => item !== scope);
    const safeScopes = nextScopes.length ? nextScopes : [...REFERENCE_SCOPES];
    const legacyExportScope = safeScopes.includes("module") ? "module" : safeScopes[0];
    patch({
      export_scopes: safeScopes,
      export_scope: legacyExportScope,
      allow_module_level_reference: safeScopes.includes("module"),
    });
  };
  const rawParamsFingerprint = JSON.stringify(rawParams);
  const normalizedParamsFingerprint = JSON.stringify(params);
  useEffect(() => {
    if (!onInput || rawParamsFingerprint === normalizedParamsFingerprint) {
      return;
    }
    commitParams(params);
  }, [onInput, rawParamsFingerprint, normalizedParamsFingerprint]);
  const changeAuthoritySourceType = (value: ReferenceAuthoritySourceType) => {
    patch({
      authority_source_type: value,
      is_core_source: value === "core_fact",
      override_allowed: REFERENCE_DOWNSTREAM_REWRITE_DEFAULT_OFF_TYPES.has(value) ? false : Boolean(params.override_allowed),
    });
  };

  return (
    <div className="reference-node-editor reference-node-editor--output">
      <label className="node-inputs__row node-inputs__row--block">
        <span>{i18nText(language, "reference.exportName")}</span>
        <NodeTextInput className="nodrag" value={autoExportName} onValueChange={(value) => patch({ export_name: value })} />
      </label>
      <label className="node-inputs__row node-inputs__row--block">
        <span>{i18nText(language, "reference.exportDescription")}</span>
        <NodeTextarea className="nodrag" rows={2} value={autoExportDescription} onValueChange={(value) => patch({ export_description: value })} />
      </label>
      <div className="reference-node-editor__scope-group">
        <span>{i18nText(language, "reference.exportScope")}</span>
        <div className="reference-node-editor__toggles">
          {REFERENCE_SCOPES.map((scope) => (
            <label key={scope}>
              <input
                className="nodrag"
                type="checkbox"
                checked={activeScopes.includes(scope)}
                onPointerDown={stopInputEventPropagation}
                onKeyDown={stopInputEventPropagation}
                onChange={(event) => toggleExportScope(scope, event.target.checked)}
              />
              <span>{i18nText(language, `reference.scope.${scope}`)}</span>
            </label>
          ))}
        </div>
      </div>
      <div className="reference-node-editor__grid">
        <label className="reference-node-editor__field-required">
          <input
            className="nodrag"
            type="checkbox"
            checked={Boolean(params.allow_module_level_reference ?? activeScopes.includes("module"))}
            onPointerDown={stopInputEventPropagation}
            onKeyDown={stopInputEventPropagation}
            onChange={(event) =>
              {
                const nextScopes = event.target.checked ? [...new Set([...activeScopes, "module"])] : activeScopes.filter((scope) => scope !== "module");
                const safeScopes = nextScopes.length ? nextScopes : ["node", "field"];
                patch({
                  allow_module_level_reference: event.target.checked,
                  export_scopes: safeScopes,
                  export_scope: safeScopes.includes("module") ? "module" : safeScopes[0],
                });
              }
            }
          />
          <span>{i18nText(language, "reference.allowModuleLevelReference")}</span>
        </label>
      </div>
      <div className="reference-node-editor__scope-group">
        <span>{i18nText(language, "reference.authoritySourceType")}</span>
        <div className="reference-node-editor__toggles">
          {REFERENCE_AUTHORITY_SOURCE_TYPES.map((sourceType) => (
            <label key={sourceType}>
              <input
                className="nodrag"
                type="radio"
                name={`reference-authority-${currentModuleInstanceId || "node"}`}
                checked={authoritySourceType === sourceType}
                onPointerDown={stopInputEventPropagation}
                onKeyDown={stopInputEventPropagation}
                onChange={() => changeAuthoritySourceType(sourceType)}
              />
              <span>{i18nText(language, `reference.authority.${sourceType}`)}</span>
            </label>
          ))}
        </div>
      </div>
      <div className="reference-node-editor__grid">
        <label className="node-inputs__row node-inputs__row--block">
          <span>{i18nText(language, "reference.allowLayers")}</span>
          <NodeTextInput className="nodrag" value={referenceStringArray(params.allow_layers).join(", ")} onValueChange={(value) => patch({ allow_layers: value.split(",").map((item) => item.trim()).filter(Boolean) })} />
        </label>
        <label className="node-inputs__row node-inputs__row--block">
          <span>{i18nText(language, "reference.forbiddenLayers")}</span>
          <NodeTextInput className="nodrag" value={referenceStringArray(params.forbidden_layers).join(", ")} onValueChange={(value) => patch({ forbidden_layers: value.split(",").map((item) => item.trim()).filter(Boolean) })} />
        </label>
      </div>
      <details className="reference-node-editor__advanced">
        <summary>{i18nText(language, "genericFields.advancedSettings")}</summary>
        <div className="reference-node-editor__toggles">
          <label>
            <input className="nodrag" type="checkbox" checked={Boolean(params.override_allowed)} onPointerDown={stopInputEventPropagation} onKeyDown={stopInputEventPropagation} onChange={(event) => patch({ override_allowed: event.target.checked })} />
            <span>{i18nText(language, "reference.overrideAllowed")}</span>
          </label>
        </div>
      </details>
      <section className="reference-node-editor__section">
        <div className="reference-node-editor__section-header">
          <h5>{i18nText(language, "reference.exportFields")}</h5>
          <button className="nodrag" type="button" onPointerDown={stopInputEventPropagation} onClick={addField} disabled={!onInput}>
            +
          </button>
        </div>
        {fields.length ? (
          fields.map((field, index) => (
            <article key={`${index}-${field.field_key || field.field_path}`} className="reference-node-editor__field-card">
              <label>
                <span>{i18nText(language, "reference.fieldKey")}</span>
                <NodeTextInput className="nodrag" value={field.field_key} onValueChange={(value) => patchField(index, { field_key: value, field_path: field.field_path || value })} />
              </label>
              <label>
                <span>{i18nText(language, "reference.fieldPath")}</span>
                <NodeTextInput className="nodrag" value={field.field_path} onValueChange={(value) => patchField(index, { field_path: value })} />
              </label>
              <label>
                <span>{i18nText(language, "reference.displayName")}</span>
                <NodeTextInput className="nodrag" value={field.display_name ?? ""} placeholder={referenceFieldDisplayName(field, language)} onValueChange={(value) => patchField(index, { display_name: value })} />
              </label>
              <label>
                <span>{i18nText(language, "reference.valueType")}</span>
                <select className="nodrag" value={field.value_type ?? "unknown"} onPointerDown={stopInputEventPropagation} onKeyDown={stopInputEventPropagation} onChange={(event) => patchField(index, { value_type: event.target.value as ReferenceValueType })}>
                  {REFERENCE_VALUE_TYPES.map((type) => (
                    <option key={type} value={type}>
                      {type}
                    </option>
                  ))}
                </select>
              </label>
              <label className="reference-node-editor__usage">
                <span>{i18nText(language, "reference.description")}</span>
                <NodeTextarea
                  className="nodrag"
                  rows={2}
                  value={field.description ?? ""}
                  placeholder={field.description_key ? translateIfPresent(language, field.description_key) : ""}
                  onValueChange={(value) => patchField(index, { description: value })}
                />
              </label>
              <label className="reference-node-editor__field-required">
                <input className="nodrag" type="checkbox" checked={Boolean(field.required)} onPointerDown={stopInputEventPropagation} onKeyDown={stopInputEventPropagation} onChange={(event) => patchField(index, { required: event.target.checked })} />
                <span>{i18nText(language, "reference.required")}</span>
              </label>
              <button className="reference-node-editor__remove nodrag" type="button" onPointerDown={stopInputEventPropagation} onClick={() => removeField(index)}>
                {i18nText(language, "reference.removeField")}
              </button>
            </article>
          ))
        ) : (
          <div className="node-inputs__empty">{translate(language, "common.empty", "Empty")}</div>
        )}
      </section>
    </div>
  );
}

function ReferenceInputRenderer({
  currentNode,
  data,
  language,
  onInput,
}: {
  currentNode: WorkflowNode;
  data: Record<string, unknown>;
  language: Language;
  onInput?: (key: string, value: unknown) => void;
}) {
  const moduleGraphs = useCanvasStore((state) => state.moduleGraphs);
  const moduleInstanceRegistry = useCanvasStore((state) => state.moduleInstanceRegistry);
  const currentNodes = useModuleWorkflowNodes();
  const currentModuleInstanceId = stringValue(data.parent_module);
  const currentLayerId = moduleInstanceRegistry[currentModuleInstanceId]?.layerId || moduleInstanceParts(currentModuleInstanceId).layerId;
  const sources = useMemo(
    () => referenceOutputSources(moduleGraphs, moduleInstanceRegistry, currentModuleInstanceId, currentNodes),
    [currentModuleInstanceId, currentNodes, moduleGraphs, moduleInstanceRegistry]
  );
  const moduleOptions = useMemo(
    () =>
      Object.values(moduleInstanceRegistry)
        .map((instance) => ({
          layerId: instance.layerId,
          moduleId: instance.moduleId,
          moduleInstanceId: instance.instanceId,
        }))
        .filter((instance) => instance.layerId && instance.moduleId),
    [moduleInstanceRegistry]
  );
  const params = paramsFromNodeData(data);
  const references = Array.isArray(params.references) ? params.references.filter(isRecord) : [];
  const layerOptions = [
    ...new Set(
      [
        ...sources.map((source) => source.layerId),
        ...moduleOptions.map((module) => module.layerId),
        ...references.map((reference) => stringValue(reference.source_layer_id)),
      ].filter(Boolean)
    ),
  ].sort();
  const commitReferences = (nextReferences: Record<string, unknown>[]) => {
    const nextParams = { ...params, references: nextReferences };
    onInput?.("params", nextParams);
    onInput?.("references", nextReferences);
  };
  const addReference = () => {
    const source = sources[0];
    const moduleOption = moduleOptions[0];
    commitReferences([
      ...references,
      {
        source_layer_id: source?.layerId ?? moduleOption?.layerId ?? "",
        source_module_id: source?.moduleId ?? moduleOption?.moduleId ?? "",
        source_node_id: source?.nodeId ?? "",
        source_scope: "module",
        source_field_paths: [],
        reference_type: "references",
        usage_reason: "",
        required: true,
      },
    ]);
  };
  const patchReference = (index: number, patchValue: Record<string, unknown>) => {
    commitReferences(references.map((reference, referenceIndex) => (referenceIndex === index ? { ...reference, ...patchValue } : reference)));
  };
  const removeReference = (index: number) => {
    commitReferences(references.filter((_, referenceIndex) => referenceIndex !== index));
  };
  const warningsForReference = (reference: Record<string, unknown>, source: ReferenceOutputSource | undefined, selectedFields: string[]) => {
    const warnings: string[] = [];
    if (!stringValue(reference.source_module_id)) {
      return warnings;
    }
    if (!source) {
      if (!(stringValue(reference.reference_id) && stringValue(reference.source_node_id))) {
        warnings.push(i18nText(language, "reference.validation.noReferenceOutput"));
      }
      return warnings;
    }
    const sourceScope = referenceScope(reference.source_scope, selectedFields.length ? "field" : "module");
    if (!source.exportScopes.includes(sourceScope) || (sourceScope === "module" && !source.allowModuleLevelReference)) {
      warnings.push(i18nText(language, "reference.validation.scopeUnavailable"));
    }
    const fieldPaths = new Set(source.exportFields.map((field) => field.field_path || field.field_key));
    if (sourceScope === "field" && (!selectedFields.length || selectedFields.some((fieldPath) => !fieldPaths.has(fieldPath)))) {
      warnings.push(i18nText(language, "reference.validation.fieldMissing"));
    }
    if (currentLayerId && source.forbiddenLayers.includes(currentLayerId)) {
      warnings.push(i18nText(language, "reference.validation.forbiddenLayer"));
    }
    if (currentLayerId && source.allowLayers.length && !source.allowLayers.includes(currentLayerId)) {
      warnings.push(i18nText(language, "reference.validation.notAllowedLayer"));
    }
    if (source.isCoreSource && !source.overrideAllowed) {
      warnings.push(i18nText(language, "reference.validation.coreSource"));
    }
    return warnings;
  };

  return (
    <div className="reference-node-editor reference-node-editor--input">
      <div className="reference-node-editor__actions">
        <button className="nodrag" type="button" onPointerDown={stopInputEventPropagation} onClick={addReference} disabled={!onInput || (!sources.length && !moduleOptions.length)}>
          {i18nText(language, "reference.addReference")}
        </button>
      </div>
      {!sources.length && !references.length ? <div className="reference-node-editor__warning">{i18nText(language, "reference.validation.noReferenceOutput")}</div> : null}
      {references.length ? (
        references.map((reference, index) => {
          const selectedLayerId = stringValue(reference.source_layer_id);
          const selectedModuleId = stringValue(reference.source_module_id);
          const moduleChoiceMap = new Map<string, { layerId: string; moduleId: string; moduleInstanceId?: string }>();
          for (const moduleOption of moduleOptions.filter((moduleOption) => !selectedLayerId || moduleOption.layerId === selectedLayerId)) {
            moduleChoiceMap.set(`${moduleOption.layerId}:${moduleOption.moduleId}`, moduleOption);
          }
          for (const source of sources.filter((source) => !selectedLayerId || source.layerId === selectedLayerId)) {
            moduleChoiceMap.set(`${source.layerId}:${source.moduleId}`, source);
          }
          if (selectedLayerId && selectedModuleId && !moduleChoiceMap.has(`${selectedLayerId}:${selectedModuleId}`)) {
            moduleChoiceMap.set(`${selectedLayerId}:${selectedModuleId}`, {
              layerId: selectedLayerId,
              moduleId: selectedModuleId,
            });
          }
          const moduleChoices = [...moduleChoiceMap.values()];
          const outputChoices = sources.filter((source) => (!selectedLayerId || source.layerId === selectedLayerId) && (!selectedModuleId || source.moduleId === selectedModuleId));
          const selectedNodeId = stringValue(reference.source_node_id);
          const selectedSource = outputChoices.find((source) => source.nodeId === selectedNodeId) ?? outputChoices[0];
          const catalogSourceNode = Boolean(
            stringValue(reference.reference_id) &&
            selectedNodeId &&
            !outputChoices.some((source) => source.nodeId === selectedNodeId)
          );
          const fieldChoices = selectedSource?.exportFields ?? [];
          const rawSelectedFields = referenceStringArray(reference.source_field_paths);
          const selectedScope = referenceScope(reference.source_scope, rawSelectedFields.length ? "field" : "module");
          const selectedFields = rawSelectedFields.filter((fieldPath) => fieldChoices.some((field) => (field.field_path || field.field_key) === fieldPath));
          const warnings = warningsForReference(reference, selectedSource, rawSelectedFields);
          return (
            <article key={`${index}-${selectedLayerId}-${selectedModuleId}-${selectedNodeId}`} className="reference-node-editor__reference-card">
              <label>
                <span>{i18nText(language, "reference.sourceLayer")}</span>
                <select
                  className="nodrag"
                  value={selectedLayerId}
                  onPointerDown={stopInputEventPropagation}
                  onKeyDown={stopInputEventPropagation}
                  onChange={(event) => {
                    const nextLayer = event.target.value;
                    const nextModule = moduleOptions.find((moduleOption) => moduleOption.layerId === nextLayer);
                    const nextSource = sources.find((source) => source.layerId === nextLayer && (!nextModule || source.moduleId === nextModule.moduleId));
                    patchReference(index, {
                      source_layer_id: nextLayer,
                      source_module_id: nextModule?.moduleId ?? nextSource?.moduleId ?? "",
                      source_node_id: nextSource?.nodeId ?? "",
                      source_field_paths: [],
                    });
                  }}
                >
                  <option value="">{i18nText(language, "common.notGenerated")}</option>
                  {layerOptions.map((layerId) => (
                    <option key={layerId} value={layerId}>
                      {referenceLayerDisplayName(layerId, language)}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                <span>{i18nText(language, "reference.sourceModule")}</span>
                <select
                  className="nodrag"
                  value={selectedModuleId}
                  onPointerDown={stopInputEventPropagation}
                  onKeyDown={stopInputEventPropagation}
                  onChange={(event) => {
                    const nextModule = event.target.value;
                    const nextSource = sources.find((source) => source.layerId === selectedLayerId && source.moduleId === nextModule);
                    patchReference(index, {
                      source_module_id: nextModule,
                      source_node_id: nextSource?.nodeId ?? "",
                      source_field_paths: [],
                    });
                  }}
                >
                  <option value="">{i18nText(language, "common.notGenerated")}</option>
                  {moduleChoices.map((source) => (
                    <option key={`${source.layerId}:${source.moduleId}`} value={source.moduleId}>
                      {referenceModuleDisplayName(source.moduleId, language)}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                <span>{i18nText(language, "reference.sourceScope")}</span>
                <select
                  className="nodrag"
                  value={selectedScope}
                  onPointerDown={stopInputEventPropagation}
                  onKeyDown={stopInputEventPropagation}
                  onChange={(event) => {
                    const nextScope = event.target.value as ReferenceScope;
                    patchReference(index, {
                      source_scope: nextScope,
                      source_node_id: nextScope === "module" ? "" : selectedSource?.nodeId ?? selectedNodeId,
                      source_field_paths: nextScope === "field" ? rawSelectedFields : [],
                    });
                  }}
                >
                  {REFERENCE_SCOPES.map((scope) => (
                    <option key={scope} value={scope}>
                      {i18nText(language, `reference.scope.${scope}`)}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                <span>{i18nText(language, "reference.sourceNode")}</span>
                <select
                  className="nodrag"
                  value={selectedNodeId}
                  disabled={selectedScope === "module"}
                  onPointerDown={stopInputEventPropagation}
                  onKeyDown={stopInputEventPropagation}
                  onChange={(event) => patchReference(index, { source_node_id: event.target.value, source_field_paths: [] })}
                >
                  <option value="">{i18nText(language, "common.notGenerated")}</option>
                  {catalogSourceNode ? (
                    <option value={selectedNodeId} title={selectedNodeId}>
                      {i18nText(language, "reference.catalogSourceNode")}
                    </option>
                  ) : null}
                  {outputChoices.map((source) => (
                    <option key={source.nodeId} value={source.nodeId}>
                      {source.exportName || source.label}
                    </option>
                  ))}
                </select>
              </label>
              {selectedScope === "field" ? (
              <label>
                <span>{i18nText(language, "reference.sourceFields")}</span>
                <select
                  className="nodrag"
                  multiple
                  value={selectedFields}
                  onPointerDown={stopInputEventPropagation}
                  onKeyDown={stopInputEventPropagation}
                  onChange={(event) =>
                    patchReference(index, {
                      source_field_paths: [...event.currentTarget.selectedOptions].map((option) => option.value),
                    })
                  }
                >
                  {fieldChoices.map((field) => {
                    const value = field.field_path || field.field_key;
                    return (
                      <option key={value} value={value}>
                        {referenceFieldDisplayName(field, language)}
                      </option>
                    );
                  })}
                </select>
              </label>
              ) : null}
              <label>
                <span>{i18nText(language, "reference.referenceType")}</span>
                <select className="nodrag" value={stringValue(reference.reference_type) || "references"} onPointerDown={stopInputEventPropagation} onKeyDown={stopInputEventPropagation} onChange={(event) => patchReference(index, { reference_type: event.target.value })}>
                  {REFERENCE_TYPES.map((type) => (
                    <option key={type} value={type}>
                      {i18nText(language, `reference.type.${type}`)}
                    </option>
                  ))}
                </select>
              </label>
              <label className="reference-node-editor__usage">
                <span>{i18nText(language, "reference.usageReason")}</span>
                <NodeTextarea className="nodrag" rows={2} value={stringValue(reference.usage_reason)} onValueChange={(value) => patchReference(index, { usage_reason: value })} />
                {stringValue(reference.usage_key) ? (
                  <small className="generic-fields-editor__hint">
                    {translate(language, stringValue(reference.usage_key), stringValue(reference.usage_key))}
                  </small>
                ) : null}
              </label>
              <label className="reference-node-editor__field-required">
                <input className="nodrag" type="checkbox" checked={Boolean(reference.required)} onPointerDown={stopInputEventPropagation} onKeyDown={stopInputEventPropagation} onChange={(event) => patchReference(index, { required: event.target.checked })} />
                <span>{i18nText(language, "reference.required")}</span>
              </label>
              {warnings.length ? (
                <ul className="reference-node-editor__warnings">
                  {warnings.map((warning) => (
                    <li key={warning}>{warning}</li>
                  ))}
                </ul>
              ) : null}
              <button className="reference-node-editor__remove nodrag" type="button" onPointerDown={stopInputEventPropagation} onClick={() => removeReference(index)}>
                {i18nText(language, "reference.removeReference")}
              </button>
            </article>
          );
        })
      ) : (
        <div className="node-inputs__empty">{translate(language, "common.empty", "Empty")}</div>
      )}
    </div>
  );
}

function ChecklistTextConfigRenderer({
  fields,
  params,
  language,
  moduleId,
  onFieldFocus,
  onInput,
}: {
  fields: Record<string, unknown>[];
  params: Record<string, unknown>;
  language: Language;
  moduleId?: string;
  onFieldFocus?: (key: string) => void;
  onInput?: (key: string, value: unknown) => void;
}) {
  const [advancedOpen, setAdvancedOpen] = useState(false);
  const config = textConfigChecklistFromParams(params);
  if (!config) {
    return <CompileTimeFieldInputRenderer fields={fields} params={params} language={language} moduleId={moduleId} onFieldFocus={onFieldFocus} onInput={onInput} />;
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
        <strong>{localizedCoreValue(language, config.presetId, moduleId)}</strong>
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
              <CompileTimeFieldInputRenderer fields={fields} params={params} language={language} moduleId={moduleId} onFieldFocus={onFieldFocus} onInput={onInput} />
            </div>
          ) : null}
        </section>
      ) : null}
    </div>
  );
}

function CoreParamValue({
  value,
  language,
  depth = 0,
  moduleId,
  contextKey,
}: {
  value: unknown;
  language: Language;
  depth?: number;
  moduleId?: string;
  contextKey?: string;
}) {
  const inheritedModuleId = useContext(CoreParamModuleContext);
  const displayModuleId = moduleId ?? inheritedModuleId;
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
    return <span title={usesLocalizedStructuredIds(displayModuleId) ? value : undefined}>{localizedCoreValue(language, value, displayModuleId)}</span>;
  }
  if (Array.isArray(value)) {
    return (
      <ul className="core-params__list">
        {value.length ? (
          value.map((item, index) => (
            <li key={`${index}-${String(typeof item === "object" ? index : item)}`}>
              <CoreParamValue value={item} language={language} depth={depth + 1} moduleId={displayModuleId} contextKey={contextKey} />
            </li>
          ))
        ) : (
          <li>
            <CoreParamValue value={[]} language={language} depth={depth + 1} moduleId={displayModuleId} contextKey={contextKey} />
          </li>
        )}
      </ul>
    );
  }
  if (isRecord(value)) {
    if (contextKey && isLayer11RoleCollection(contextKey, displayModuleId)) {
      return <Layer11RoleCards value={value} moduleId={displayModuleId} language={language} />;
    }
    const entries = Object.entries(value).filter(([, item]) => !isEmptyDisplayValue(item));
    if (!entries.length) {
      return <CoreParamValue value={null} language={language} moduleId={displayModuleId} contextKey={contextKey} />;
    }
    if (depth >= 2) {
      return (
        <details className="core-params__nested">
          <summary>{translate(language, "node.coreParams.expand", "Expand")}</summary>
          <CoreParamValue value={value} language={language} depth={0} moduleId={displayModuleId} contextKey={contextKey} />
        </details>
      );
    }
    return (
      <dl className="core-params__object">
        {entries.map(([key, item]) => (
          <div key={key} className="core-params__object-row">
            <dt>{localizedCoreKey(language, key, displayModuleId)}</dt>
            <dd>
              <CoreParamValue value={item} language={language} depth={depth + 1} moduleId={displayModuleId} contextKey={key} />
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
  moduleId,
  valueContextKey,
  tone = "default"
}: {
  titleKey: string;
  titleFallback: string;
  value: unknown;
  language: Language;
  moduleId?: string;
  valueContextKey?: string;
  tone?: "default" | "warning";
}) {
  return (
    <section className={`core-params__section is-${tone}`}>
      <h5>{translate(language, titleKey, titleFallback)}</h5>
      <CoreParamValue value={value} language={language} moduleId={moduleId} contextKey={valueContextKey} />
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
  const moduleId = useContext(CoreParamModuleContext);
  if (!rules.length) {
    return <CoreParamValue value={[]} language={language} />;
  }
  return (
    <div className="core-params__rule-list">
      {rules.map((rule, index) => {
        const name = updateRuleDisplayName(rule) || `${translate(language, "common.field", "Field")} ${index + 1}`;
        const displayName = localizedCoreValue(language, name, moduleId);
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
    const allowedMemoryTypes = valueByCandidateKeys([data, params], ["allowed_memory_types"]);
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
        {!isEmptyDisplayValue(allowedMemoryTypes) ? (
          <CoreParamSection titleKey="node.normalization.allowedMemoryTypes" titleFallback="Allowed memory types" value={allowedMemoryTypes} language={language} />
        ) : null}
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
  const moduleId = layer11ModuleId(data);
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
          .replace("{output}", outputKey ? localizedCoreValue(language, outputKey, moduleId) : translate(language, "common.unknown", "Unknown"))
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
  if (String(effectiveType) === "reference_input" || String(effectiveType) === "reference_output") {
    collapsedSections.add("core");
  }
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
  const showReferenceOutputForm = String(effectiveType) === "reference_output";
  const showReferenceInputForm = String(effectiveType) === "reference_input";
  const showReferenceInputGenericFields =
    showReferenceInputForm &&
    stringValue(compileTimeParams.mode) === "generic_fields" &&
    compileTimeFields.length > 0;
  const showGenericTextInputForm = String(effectiveType) === "text_input";
  const showCoreParamsPanel = isCatalogPreconfigured && ["layer_aggregator", "structure_normalize", "validation", "update_rule"].includes(String(effectiveType));
  const showModuleOutputSummary = isCatalogPreconfigured && String(effectiveType) === "module_output";
  const siblingOutput = moduleOutputValue(findSiblingModuleOutputNode(schemaNode, moduleWorkflowNodes));
  const schemaLayerId = typeof schemaNode.layer_id === "string" ? schemaNode.layer_id : typeof nodeData.layer_id === "string" ? nodeData.layer_id : moduleInstanceParts(String(nodeData.parent_module || "")).layerId;
  const schemaModuleId =
    typeof schemaNode.module_id === "string"
      ? schemaNode.module_id
      : typeof nodeData.catalog_module_id === "string"
        ? nodeData.catalog_module_id
        : moduleInstanceParts(String(nodeData.parent_module || "")).moduleId;
  const catalogNodeId = String(nodeData.catalog_node_id || schemaNode.node_id).split("::").pop() ?? "";
  const paramsFields = Array.isArray(compileTimeParams.fields)
    ? compileTimeParams.fields.filter(isRecord)
    : [];
  const firstInteractionFieldIndex = paramsFields.findIndex(isFirstInteractionField);
  const firstInteractionField = firstInteractionFieldIndex >= 0 ? paramsFields[firstInteractionFieldIndex] : null;
  const firstInteractionValue = isRecord(firstInteractionField?.value) ? firstInteractionField.value : {};
  const usesFirstInteractionEnabled =
    schemaModuleId === "interaction_strategy" &&
    catalogNodeId === "interaction_behavior_core_rules" &&
    firstInteractionFieldIndex >= 0;
  const isEnabled = usesFirstInteractionEnabled
    ? firstInteractionEnabledValue(firstInteractionValue)
    : typeof nodeData.enabled === "boolean"
      ? nodeData.enabled
      : true;
  const commitEnabled = (enabled: boolean) => {
    if (usesFirstInteractionEnabled) {
      const nextValue = updateFirstInteractionEnabled(firstInteractionValue, enabled);
      const nextFields = updateFieldValue(paramsFields, firstInteractionFieldIndex, nextValue);
      onInput?.("params", { ...compileTimeParams, fields: nextFields });
      return;
    }
    onInput?.("enabled", enabled);
  };
  const normalizedReferenceOutputParams = showReferenceOutputForm ? normalizeReferenceOutputParams(compileTimeParams, schemaLayerId) : compileTimeParams;
  const normalizedReferenceOutputScopes = referenceOutputScopes(normalizedReferenceOutputParams);
  const summaryAuthoritySourceType = referenceAuthoritySourceType(normalizedReferenceOutputParams.authority_source_type, schemaLayerId);
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
      className={`workflow-node module-${schemaModuleId || "unknown"} node-kind-${effectiveType} lock-${schemaNode.lock_level} ${aiSlotClass(aiSlot)} ${aiSlot === "none" ? "is-ai-unplanned" : "has-ai-slot"} ${selected ? "is-selected" : ""}`}
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
            onChange={(event) => commitEnabled(event.target.checked)}
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

      {showReferenceOutputForm ? (
        <div className="workflow-node__output reference-node-summary nodrag nopan" onPointerDown={(event) => event.stopPropagation()}>
          <div className="workflow-node__output-head">
            <span className="workflow-node__output-label">{i18nText(language, "nodes.referenceOutput.title")}</span>
          </div>
          <dl>
            <div>
              <dt>{i18nText(language, "reference.exportScope")}</dt>
              <dd>{normalizedReferenceOutputScopes.map((scope) => i18nText(language, `reference.scope.${scope}`)).join(", ")}</dd>
            </div>
            <div>
              <dt>{i18nText(language, "reference.allowModuleLevelReference")}</dt>
              <dd>
                {translate(
                  language,
                  Boolean(normalizedReferenceOutputParams.allow_module_level_reference) ? "common.yes" : "common.no",
                  Boolean(normalizedReferenceOutputParams.allow_module_level_reference) ? "Yes" : "No"
                )}
              </dd>
            </div>
            <div>
              <dt>{i18nText(language, "reference.exportFields")}</dt>
              <dd>{referenceExportFields(normalizedReferenceOutputParams.export_fields).length}</dd>
            </div>
            <div>
              <dt>{i18nText(language, "reference.authoritySourceType")}</dt>
              <dd>{i18nText(language, `reference.authority.${summaryAuthoritySourceType}`)}</dd>
            </div>
            <div>
              <dt>{i18nText(language, "reference.overrideAllowed")}</dt>
              <dd>{translate(language, normalizedReferenceOutputParams.override_allowed ? "common.yes" : "common.no", normalizedReferenceOutputParams.override_allowed ? "Yes" : "No")}</dd>
            </div>
          </dl>
        </div>
      ) : null}

      {showReferenceInputForm ? (
        <div className="workflow-node__output reference-node-summary nodrag nopan" onPointerDown={(event) => event.stopPropagation()}>
          <div className="workflow-node__output-head">
            <span className="workflow-node__output-label">{i18nText(language, "nodes.referenceInput.title")}</span>
          </div>
          <dl>
            <div>
              <dt>{i18nText(language, "reference.addReference")}</dt>
              <dd>{Array.isArray(compileTimeParams.references) ? compileTimeParams.references.length : 0}</dd>
            </div>
            <div>
              <dt>{i18nText(language, "reference.referenceType")}</dt>
              <dd>
                {Array.isArray(compileTimeParams.references)
                  ? [...new Set(compileTimeParams.references.filter(isRecord).map((reference) => stringValue(reference.reference_type) || "references"))]
                      .map((type) => i18nText(language, `reference.type.${type}`))
                      .join(", ")
                  : i18nText(language, "reference.type.references")}
              </dd>
            </div>
          </dl>
        </div>
      ) : null}

      <details className="workflow-node__params nodrag nopan" onPointerDown={(event) => event.stopPropagation()} open={!sections.core && !isCatalogPreconfigured}>
        <summary>{sectionTitle(language, "node.coreParams.title", "Core Params")}</summary>
        <div className="workflow-node__params-body">
          <CoreParamModuleContext.Provider value={schemaModuleId || layer11ModuleId(nodeData)}>
          {showGenericTextInputForm ? (
            <GenericTextInputRenderer fields={inputSchema} data={nodeData} language={language} onFieldFocus={onFieldFocus} onInput={onInput} />
          ) : showReferenceOutputForm ? (
            <ReferenceOutputRenderer data={nodeData} language={language} onInput={onInput} />
          ) : showReferenceInputForm ? (
            <>
              {showReferenceInputGenericFields ? (
                <GenericTextInputRenderer fields={inputSchema} data={nodeData} language={language} onFieldFocus={onFieldFocus} onInput={onInput} />
              ) : null}
              <ReferenceInputRenderer currentNode={schemaNode} data={nodeData} language={language} onInput={onInput} />
            </>
          ) : showFieldReferenceForm ? (
            <FieldReferenceRenderer data={nodeData} language={language} onInput={onInput} />
          ) : showChecklistTextConfig ? (
            <ChecklistTextConfigRenderer fields={compileTimeFields} params={compileTimeParams} language={language} moduleId={schemaModuleId} onFieldFocus={onFieldFocus} onInput={onInput} />
          ) : showCompileTimeFieldForm ? (
            <CompileTimeFieldInputRenderer fields={compileTimeFields} params={compileTimeParams} language={language} moduleId={schemaModuleId} onFieldFocus={onFieldFocus} onInput={onInput} />
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
          </CoreParamModuleContext.Provider>
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
