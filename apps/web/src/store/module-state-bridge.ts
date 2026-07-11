/**
 * P1-FIX：Module State Bridge
 * 
 * 在 Zustand store 和 React useState 之间建立双向同步
 * 作为从 localStorage-first 向 store-first 过渡的中间层
 */

import { useCanvasStore, type ModuleGraph, type ModuleGraphsState } from "./canvas-store";
import { loadCanvasStateFromLocalStorage, loadModuleGraphState, saveModuleGraphState } from "@/lib/canvas-persistence";
import type { WorkflowNode, WorkflowEdge } from "@/lib/schema-types";
import type { ModuleInstance } from "@/lib/canvas-persistence";
import { translate } from "@/i18n";
import { preserveStoredModuleEdges, preserveStoredModuleNodePosition } from "./module-graph-merge";

const MODULE_INSTANCE_SEPARATOR = "::";
const CATALOG_GRAPH_REPLACE_MODULE_IDS = new Set([
  "memory_provider_router",
  "memory_access_control",
  "short_term_memory",
  "preference_memory",
  "event_memory",
  "memory_update",
]);
const GENERIC_FIELD_MIGRATION_NODE_TYPES = new Set(["field_input", "text_input"]);
const LAYER3_GENERIC_FIELD_MIGRATION_MODULE_IDS = new Set([
  "humanistic_content_safety_config_v0_1",
  "humanistic_behavior_boundary_config_v0_1",
  "humanistic_data_boundary_config_v0_1",
  "humanistic_interaction_boundary_config_v0_1",
  "humanistic_risk_response_config_v0_1",
]);
const RISK_RESPONSE_LAYER_ID = "layer_3";
const RISK_RESPONSE_MODULE_ID = "humanistic_risk_response_config_v0_1";
const RISK_RESPONSE_MODULE_INSTANCE_ID = `${RISK_RESPONSE_LAYER_ID}${MODULE_INSTANCE_SEPARATOR}${RISK_RESPONSE_MODULE_ID}`;
const MEMORY_PROVIDER_ROUTER_LAYER_ID = "layer_5";
const MEMORY_PROVIDER_ROUTER_MODULE_ID = "memory_provider_router";
const MEMORY_ROUTER_TYPE_RESOLVER_NODE_ID = "memory_router_type_resolver";
const MEMORY_ROUTER_REQUEST_INPUT_NODE_ID = "memory_router_request_input";
const MEMORY_ROUTER_OPERATION_CLASSIFIER_NODE_ID = "memory_router_operation_classifier";
const LEGACY_MEMORY_ROUTER_ALLOWED_MEMORY_TYPES = ["short_term_memory", "profile_memory", "preference_memory", "interaction_log"];
const MEMORY_ROUTER_ALLOWED_MEMORY_TYPES = ["short_term_memory", "preference_memory", "event_memory", "relationship_memory", "interaction_log"];
const LEGACY_MEMORY_ROUTER_OPERATIONS = ["read", "write", "view", "clear"];
const MEMORY_ROUTER_CANONICAL_OPERATIONS = ["read", "write", "update", "delete"];
const MEMORY_ROUTER_ACCEPTED_OPERATIONS = [...MEMORY_ROUTER_CANONICAL_OPERATIONS, "view", "clear"];
const MEMORY_ROUTER_OPERATION_ALIASES = { view: "read", clear: "delete" };
const LEGACY_MEMORY_ROUTER_NORMALIZE_RULES = ["classify_operation", "allow_read_write_view_clear", "reject_unknown_operation"];
const MEMORY_ROUTER_NORMALIZE_RULES = ["normalize_operation_alias", "classify_operation", "allow_declared_operations_only", "reject_unknown_operation"];
const GENERIC_FIELD_RESERVED_PARAM_KEYS = new Set([
  "mode",
  "text",
  "fields",
  "tags",
  "legacy_fields",
  "legacy_data_fields",
]);
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

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value && typeof value === "object" && !Array.isArray(value));
}

function cloneJson<T>(value: T): T {
  return JSON.parse(JSON.stringify(value)) as T;
}

function stableJson(value: unknown) {
  return JSON.stringify(value ?? null);
}

function hasExactStringList(value: unknown, expected: string[]) {
  return Array.isArray(value) && value.length === expected.length && value.every((item, index) => item === expected[index]);
}

function stringValue(value: unknown): string {
  return typeof value === "string" && value.trim() ? value.trim() : "";
}

function zhText(key: string) {
  if (!key) return "";
  const marker = `__missing__${key}`;
  const value = translate("zh", key, marker);
  return value === marker ? "" : value;
}

function prettyValue(value: unknown) {
  if (value === null || value === undefined) return "";
  if (typeof value === "string") return value;
  if (typeof value === "number" || typeof value === "boolean") return String(value);
  return JSON.stringify(value);
}

function isEmptyDisplayValue(value: unknown): boolean {
  if (value === null || value === undefined) return true;
  if (typeof value === "string") return value.trim() === "";
  if (Array.isArray(value)) return value.length === 0;
  if (isRecord(value)) return Object.keys(value).length === 0;
  return false;
}

function positionValue(value: unknown): { x: number; y: number } | null {
  if (!isRecord(value)) {
    return null;
  }
  return typeof value.x === "number" && typeof value.y === "number" ? { x: value.x, y: value.y } : null;
}

function schemaNodeRecord(value: unknown): Record<string, unknown> | null {
  if (!isRecord(value)) {
    return null;
  }
  const data = isRecord(value.data) ? value.data : {};
  if (isRecord(data.schemaNode)) {
    return data.schemaNode;
  }
  return value;
}

function schemaDataRecord(schemaNode: Record<string, unknown>): Record<string, unknown> {
  if (!isRecord(schemaNode.data)) {
    schemaNode.data = {};
  }
  return schemaNode.data as Record<string, unknown>;
}

function fieldsFromData(data: Record<string, unknown>): Record<string, unknown>[] {
  if (Array.isArray(data.fields)) {
    return data.fields.filter(isRecord);
  }
  const params = isRecord(data.params) ? data.params : {};
  return Array.isArray(params.fields) ? params.fields.filter(isRecord) : [];
}

function mergeCatalogFields(seedFields: Record<string, unknown>[], existingFields: Record<string, unknown>[]) {
  const existingById = new Map(existingFields.map((field) => [String(field.field_id || ""), field]));
  return seedFields.map((seedField) => {
    const fieldId = String(seedField.field_id || "");
    const existingField = existingById.get(fieldId);
    return {
      ...cloneJson(seedField),
      value: existingField && "value" in existingField ? existingField.value : seedField.value,
    };
  });
}

function safeGenericFieldKey(value: string) {
  const mapped = GENERIC_FIELD_NAME_KEY_MAP[value.trim()];
  const raw = mapped || value.normalize("NFKD").toLowerCase();
  let key = raw
    .replace(/['’]/g, "")
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "")
    .replace(/_+/g, "_");
  if (!key) key = "field";
  if (/^[0-9]/.test(key)) key = `field_${key}`;
  return key;
}

function inferGenericFieldType(value: unknown): "text" | "long_text" | "number" | "boolean" | "list" | "object" | "unknown" {
  if (typeof value === "number") return "number";
  if (typeof value === "boolean") return "boolean";
  if (Array.isArray(value)) return "list";
  if (isRecord(value)) return "object";
  const text = typeof value === "string" ? value : prettyValue(value);
  return text.length > 80 || text.includes("\n") ? "long_text" : "text";
}

function uniqueGenericFieldKey(baseKey: string, usedKeys: Set<string>) {
  const base = safeGenericFieldKey(baseKey);
  if (!usedKeys.has(base)) {
    usedKeys.add(base);
    return base;
  }
  let suffix = 2;
  while (usedKeys.has(`${base}_${suffix}`)) {
    suffix += 1;
  }
  const key = `${base}_${suffix}`;
  usedKeys.add(key);
  return key;
}

function genericFieldDrMapping(layerId: string, moduleId: string, fieldKey: string) {
  return layerId && moduleId && fieldKey ? `payload.layers.${layerId}.modules.${moduleId}.fields.${fieldKey}` : "";
}

function legacyTextValue(data: Record<string, unknown>, params: Record<string, unknown>) {
  const candidate = [params.text, data.source_text, data.text, data.value, data.content, data.prompt].find(
    (value) => typeof value === "string" && value.trim()
  );
  return typeof candidate === "string" ? candidate : "";
}

function fieldI18nKey(field: Record<string, unknown>, keyName: "label" | "description" | "help" | "placeholder" | "field") {
  const i18n = isRecord(field.i18n_keys) ? field.i18n_keys : {};
  return stringValue(i18n[keyName]) || stringValue(field[`${keyName}_key`]);
}

function legacyFieldId(field: Record<string, unknown>) {
  return stringValue(field.field_id) || stringValue(field.field_key) || stringValue(field.key) || stringValue(field.id);
}

function legacyFieldDisplayName(field: Record<string, unknown>, fallback: string) {
  const fieldId = legacyFieldId(field);
  return (
    zhText(fieldI18nKey(field, "label")) ||
    zhText(fieldI18nKey(field, "field")) ||
    zhText(fieldId ? `field.identity.${fieldId}.label` : "") ||
    stringValue(field.field_name) ||
    stringValue(field.label) ||
    stringValue(field.name) ||
    fallback
  );
}

function legacyFieldDescription(field: Record<string, unknown>) {
  const fieldId = legacyFieldId(field);
  return (
    zhText(fieldI18nKey(field, "description")) ||
    zhText(fieldI18nKey(field, "help")) ||
    zhText(fieldId ? `field.identity.${fieldId}.help` : "") ||
    stringValue(field.description) ||
    stringValue(field.help)
  );
}

function legacyFieldLookup(fields: Record<string, unknown>[]) {
  const lookup = new Map<string, Record<string, unknown>>();
  fields.forEach((field) => {
    [
      legacyFieldId(field),
      stringValue(field.field_key),
      stringValue(field.key),
      stringValue(field.id),
      stringValue(field.field_name),
      stringValue(field.label),
      stringValue(field.name),
    ]
      .filter(Boolean)
      .forEach((key) => lookup.set(key, field));
  });
  return lookup;
}

function fieldValue(field: Record<string, unknown>, keys: string[]) {
  for (const key of keys) {
    if (key in field) {
      return field[key];
    }
  }
  return "";
}

function genericFieldValueByKey(fields: Record<string, unknown>[]) {
  const values = new Map<string, unknown>();
  fields.forEach((field, index) => {
    const key = String(field.field_key || field.field_id || field.key || field.id || `field_${index + 1}`);
    if (!key) {
      return;
    }
    values.set(key, "field_value" in field ? field.field_value : field.value);
  });
  return values;
}

function syncPrimaryLanguageFieldValue(fields: Record<string, unknown>[], value: unknown) {
  return fields.map((field, index) => {
    const fieldId = String(field.field_id || field.field_key || field.key || field.id || `field_${index + 1}`);
    if (fieldId !== "primary_language") {
      return field;
    }
    return {
      ...field,
      ...("field_value" in field || field.field_key ? { field_value: value } : {}),
      ...("value" in field || field.field_id ? { value } : {}),
    };
  });
}

function syncPrimaryLanguageCompatibilityFields(params: Record<string, unknown>) {
  const genericFields = Array.isArray(params.fields) ? params.fields.filter(isRecord) : [];
  const genericValues = genericFieldValueByKey(genericFields);
  if (!genericValues.has("primary_language")) {
    return params;
  }
  const primaryLanguage = genericValues.get("primary_language");
  const nextParams = { ...params };
  if (Array.isArray(nextParams.legacy_fields)) {
    nextParams.legacy_fields = syncPrimaryLanguageFieldValue(nextParams.legacy_fields.filter(isRecord), primaryLanguage);
  }
  if (Array.isArray(nextParams.legacy_data_fields)) {
    nextParams.legacy_data_fields = syncPrimaryLanguageFieldValue(nextParams.legacy_data_fields.filter(isRecord), primaryLanguage);
  }
  return nextParams;
}

function normalizeGenericField(
  field: Record<string, unknown>,
  index: number,
  legacyField?: Record<string, unknown>
) {
  const fieldKeySource =
    stringValue(field.field_key) ||
    stringValue(field.field_id) ||
    stringValue(field.key) ||
    stringValue(field.id) ||
    (legacyField ? legacyFieldId(legacyField) : "");
  const fallbackName = stringValue(field.name) || stringValue(field.title) || stringValue(field.label);
  const fieldKey = fieldKeySource || (fallbackName ? safeGenericFieldKey(fallbackName) : `field_${index + 1}`);
  const existingName = stringValue(field.field_name);
  const legacyName = legacyField ? legacyFieldDisplayName(legacyField, fieldKey) : "";
  const shouldUseMappedName = !existingName || existingName === fieldKey || existingName === stringValue(field.field_id);
  const description = stringValue(field.description) || (legacyField ? legacyFieldDescription(legacyField) : "");
  return {
    field_key: fieldKey,
    field_name: shouldUseMappedName ? legacyName || GENERIC_FIELD_KEY_NAME_MAP[fieldKey] || fallbackName || fieldKey : existingName,
    field_value: fieldValue(field, ["field_value", "value", "text", "content"]),
    field_type: ["text", "long_text", "number", "boolean", "list", "object", "unknown"].includes(String(field.field_type)) ? field.field_type : "long_text",
    description,
    dr_mapping: stringValue(field.dr_mapping),
    reference_enabled: field.reference_enabled === true,
    field_key_auto: field.field_key_auto === true,
    dr_mapping_auto: field.dr_mapping_auto === true,
  };
}

function refineGenericFieldsFromLegacy(genericFields: Record<string, unknown>[], legacyFields: Record<string, unknown>[]) {
  const lookup = legacyFieldLookup(legacyFields);
  return genericFields.map((field, index) => {
    const fieldKey = stringValue(field.field_key) || stringValue(field.field_id);
    const legacyField =
      lookup.get(fieldKey) ||
      lookup.get(stringValue(field.field_name)) ||
      legacyFields[index];
    return normalizeGenericField(field, index, legacyField);
  });
}

function genericFieldsFromLegacyNode(
  data: Record<string, unknown>,
  params: Record<string, unknown>,
  layerId: string,
  moduleId: string
) {
  const usedKeys = new Set<string>();
  const sourceFields = fieldsFromData(data);
  if (sourceFields.length) {
    return sourceFields.map((field, index) => {
      const existingKey = stringValue(field.field_key) || legacyFieldId(field);
      const rawName = legacyFieldDisplayName(field, existingKey || `field_${index + 1}`);
      const fieldKey = existingKey ? uniqueGenericFieldKey(existingKey, usedKeys) : uniqueGenericFieldKey(rawName, usedKeys);
      const value = "value" in field ? field.value : field.field_value;
      return {
        field_key: fieldKey,
        field_name: rawName || fieldKey,
        field_value: value,
        field_type: inferGenericFieldType(value),
        description: legacyFieldDescription(field),
        dr_mapping: stringValue(field.dr_mapping) || genericFieldDrMapping(layerId, moduleId, fieldKey),
        reference_enabled: false,
        field_key_auto: !existingKey,
        dr_mapping_auto: !stringValue(field.dr_mapping),
      };
    });
  }

  const paramFields = Object.entries(params)
    .filter(([key, value]) => !GENERIC_FIELD_RESERVED_PARAM_KEYS.has(key) && !isEmptyDisplayValue(value))
    .map(([key, value]) => {
      const fieldKey = uniqueGenericFieldKey(key, usedKeys);
      const label = zhText(`field.identity.${key}.label`);
      return {
        field_key: fieldKey,
        field_name: label || key,
        field_value: value,
        field_type: inferGenericFieldType(value),
        description: zhText(`field.identity.${key}.help`),
        dr_mapping: genericFieldDrMapping(layerId, moduleId, fieldKey),
        reference_enabled: false,
        field_key_auto: false,
        dr_mapping_auto: true,
      };
    });
  if (paramFields.length) {
    return paramFields;
  }

  const text = legacyTextValue(data, params);
  if (!text) {
    return [];
  }
  const fieldKey = uniqueGenericFieldKey("field_1", usedKeys);
  return [
    {
      field_key: fieldKey,
      field_name: fieldKey,
      field_value: text,
      field_type: "long_text",
      description: "",
      dr_mapping: genericFieldDrMapping(layerId, moduleId, fieldKey),
      reference_enabled: false,
      field_key_auto: true,
      dr_mapping_auto: true,
    },
  ];
}

function mergeCatalogFieldSeed(
  graph: ModuleGraph,
  initialNodes?: WorkflowNode[],
  initialEdges?: WorkflowEdge[]
): ModuleGraph | null {
  if (!initialNodes?.length || !graph.nodes?.length) {
    return null;
  }

  const seedFieldNode = initialNodes
    .map(schemaNodeRecord)
    .find((node) => {
      const data = node ? (isRecord(node.data) ? node.data : {}) : {};
      return node && String(data.node_type || node.type) === "field_input";
    });
  if (!seedFieldNode) {
    return null;
  }

  const seedData = schemaDataRecord(seedFieldNode);
  const seedFields = fieldsFromData(seedData);
  if (!seedFields.length) {
    return null;
  }

  let changed = false;
  const nextNodes = graph.nodes.map((node) => {
    const nextNode = cloneJson(node) as WorkflowNode;
    const schemaNode = schemaNodeRecord(nextNode);
    if (!schemaNode) {
      return nextNode;
    }
    const data = schemaDataRecord(schemaNode);
    if (data.catalog_preconfigured !== true || String(data.node_type || schemaNode.type) !== "field_input") {
      return nextNode;
    }

    const existingFields = fieldsFromData(data);
    const existingIds = existingFields.map((field) => String(field.field_id || ""));
    const seedIds = seedFields.map((field) => String(field.field_id || ""));
    if (existingIds.join("\u0000") === seedIds.join("\u0000")) {
      return nextNode;
    }

    const params = isRecord(data.params) ? { ...data.params } : {};
    const mergedFields = mergeCatalogFields(seedFields, existingFields);
    params.fields = mergedFields;
    data.params = params;
    data.fields = mergedFields;
    changed = true;
    return nextNode;
  });

  if (!changed) {
    return null;
  }

  return {
    ...graph,
    nodes: nextNodes,
    edges: preserveStoredModuleEdges(graph.edges, initialEdges),
  };
}

function catalogModuleIdFromSeed(initialNodes?: WorkflowNode[]): string {
  for (const node of initialNodes ?? []) {
    const schemaNode = schemaNodeRecord(node);
    const data = schemaNode && isRecord(schemaNode.data) ? schemaNode.data : {};
    const moduleId = String(data.catalog_module_id || schemaNode?.module_id || data.module_id || "");
    if (moduleId) {
      return moduleId;
    }
  }
  return "";
}

function catalogNodeIdFromGraphNode(node: unknown): string {
  const schemaNode = schemaNodeRecord(node);
  const data = schemaNode && isRecord(schemaNode.data) ? schemaNode.data : {};
  return String(data.catalog_node_id || schemaNode?.node_id || "");
}

function graphNodeId(node: unknown): string {
  const schemaNode = schemaNodeRecord(node);
  if (schemaNode) {
    return String(schemaNode.node_id || schemaNode.id || "");
  }
  return isRecord(node) ? String(node.node_id || node.id || "") : "";
}

function catalogNodeIdsFromGraph(nodes: unknown[] | undefined): string[] {
  return (nodes ?? []).map(catalogNodeIdFromGraphNode).filter(Boolean);
}

function nodeIdToCatalogNodeId(nodes: unknown[] | undefined) {
  const idMap = new Map<string, string>();
  for (const node of nodes ?? []) {
    const nodeId = graphNodeId(node);
    const catalogNodeId = catalogNodeIdFromGraphNode(node);
    if (nodeId && catalogNodeId) {
      idMap.set(nodeId, catalogNodeId);
    }
  }
  return idMap;
}

function catalogNodeIdFromEndpoint(endpoint: string, idMap: Map<string, string>) {
  return idMap.get(endpoint) || endpoint.split(MODULE_INSTANCE_SEPARATOR).pop() || endpoint;
}

function edgeEndpoint(edge: unknown, key: "source" | "target"): string {
  if (!isRecord(edge)) {
    return "";
  }
  if (typeof edge[key] === "string") {
    return edge[key];
  }
  const nodeKey = `${key}_node_id`;
  return typeof edge[nodeKey] === "string" ? edge[nodeKey] : "";
}

function edgePairsByCatalogNodeId(nodes: unknown[] | undefined, edges: unknown[] | undefined): string[] {
  const idMap = nodeIdToCatalogNodeId(nodes);
  return (edges ?? [])
    .map((edge) => {
      const source = edgeEndpoint(edge, "source");
      const target = edgeEndpoint(edge, "target");
      if (!source || !target) {
        return "";
      }
      return `${catalogNodeIdFromEndpoint(source, idMap)}->${catalogNodeIdFromEndpoint(target, idMap)}`;
    })
    .filter(Boolean);
}

function shouldReplaceWithCatalogGraph(
  graph: ModuleGraph,
  initialNodes?: WorkflowNode[],
  initialEdges?: WorkflowEdge[]
) {
  if (graph.nodes?.length || graph.edges?.length) {
    return false;
  }
  const catalogModuleId = catalogModuleIdFromSeed(initialNodes);
  if (!CATALOG_GRAPH_REPLACE_MODULE_IDS.has(catalogModuleId) || !initialNodes?.length) {
    return false;
  }

  const seedNodeIds = catalogNodeIdsFromGraph(initialNodes);
  const graphNodeIds = catalogNodeIdsFromGraph(graph.nodes);
  const seedEdges = edgePairsByCatalogNodeId(initialNodes, initialEdges);
  const graphEdges = edgePairsByCatalogNodeId(graph.nodes, graph.edges);
  return stableJson(graphNodeIds) !== stableJson(seedNodeIds) || stableJson(graphEdges) !== stableJson(seedEdges);
}

function seedPositionsByCatalogNodeId(initialNodes?: WorkflowNode[]) {
  const positions = new Map<string, { x: number; y: number }>();
  for (const node of initialNodes ?? []) {
    const schemaNode = schemaNodeRecord(node);
    const data = schemaNode && isRecord(schemaNode.data) ? schemaNode.data : {};
    const catalogNodeId = String(data.catalog_node_id || schemaNode?.node_id || "");
    const position = positionValue(schemaNode?.position);
    if (catalogNodeId && position) {
      positions.set(catalogNodeId, position);
    }
  }
  return positions;
}

function seedParamsByCatalogNodeId(initialNodes?: WorkflowNode[]) {
  const paramsByNodeId = new Map<string, Record<string, unknown>>();
  for (const node of initialNodes ?? []) {
    const schemaNode = schemaNodeRecord(node);
    const data = schemaNode && isRecord(schemaNode.data) ? schemaNode.data : {};
    const catalogNodeId = String(data.catalog_node_id || schemaNode?.node_id || "");
    const params = isRecord(data.params) ? data.params : {};
    if (catalogNodeId && Object.keys(params).length) {
      paramsByNodeId.set(catalogNodeId, params);
    }
  }
  return paramsByNodeId;
}

function setGraphNodePosition(node: WorkflowNode, position: { x: number; y: number }) {
  const nextNode = node as WorkflowNode & Record<string, unknown>;
  nextNode.position = position;
  const schemaNode = schemaNodeRecord(nextNode);
  if (schemaNode) {
    schemaNode.position = position;
  }
}

function mergeCatalogLayoutSeed(
  graph: ModuleGraph,
  initialNodes?: WorkflowNode[],
  initialEdges?: WorkflowEdge[]
): ModuleGraph | null {
  const catalogModuleId = catalogModuleIdFromSeed(initialNodes);
  if (
    !["language_habit", "decision_pattern", "emotion_reaction", "interaction_strategy", "behavior_habit", "emotion_mapper"].includes(catalogModuleId) ||
    !initialNodes?.length ||
    !graph.nodes?.length
  ) {
    return null;
  }
  const positions = seedPositionsByCatalogNodeId(initialNodes);
  const seedParamsByNodeId = seedParamsByCatalogNodeId(initialNodes);
  if (!positions.size && !seedParamsByNodeId.size && !initialEdges?.length) {
    return null;
  }

  let changed = false;
  const nextNodes = graph.nodes.map((node) => {
    const nextNode = cloneJson(node) as WorkflowNode;
    const catalogNodeId = catalogNodeIdFromGraphNode(nextNode);
    const seedPosition = positions.get(catalogNodeId);
    if (seedPosition) {
      const currentPosition = positionValue((nextNode as Record<string, unknown>).position);
      const nextPosition = preserveStoredModuleNodePosition(currentPosition, seedPosition);
      if (!currentPosition && nextPosition) {
        setGraphNodePosition(nextNode, nextPosition);
        changed = true;
      }
    }
    const seedParams = seedParamsByNodeId.get(catalogNodeId);
    const seedCheckboxConfig = seedParams && isRecord(seedParams.checkbox_config) ? seedParams.checkbox_config : null;
    if (seedCheckboxConfig) {
      const schemaNode = schemaNodeRecord(nextNode);
      if (schemaNode) {
        const data = schemaDataRecord(schemaNode);
        const params = isRecord(data.params) ? { ...data.params } : {};
        if (!isRecord(params.checkbox_config)) {
          params.checkbox_config = cloneJson(seedCheckboxConfig);
          data.params = params;
          changed = true;
        }
      }
    }
    return nextNode;
  });

  const nextEdges = preserveStoredModuleEdges(graph.edges, initialEdges);
  if (!changed) {
    return null;
  }
  return {
    ...graph,
    nodes: nextNodes,
    edges: nextEdges,
  };
}

function mergeCatalogSeed(
  graph: ModuleGraph,
  initialNodes?: WorkflowNode[],
  initialEdges?: WorkflowEdge[]
): ModuleGraph | null {
  const fieldMerged = mergeCatalogFieldSeed(graph, initialNodes, initialEdges);
  const layoutMerged = mergeCatalogLayoutSeed(fieldMerged ?? graph, initialNodes, initialEdges);
  return layoutMerged ?? fieldMerged;
}

function layerModuleIdentity(moduleNodeId: string, registry: Record<string, ModuleInstance>) {
  const registryEntry = registry[moduleNodeId];
  if (registryEntry) {
    return registryEntry;
  }
  const [layerId = "", moduleId = moduleNodeId] = moduleNodeId.split(MODULE_INSTANCE_SEPARATOR);
  return { instanceId: moduleNodeId, layerId, moduleId };
}

function shouldMigrateGenericFieldsGraph(identity: ModuleInstance) {
  if (identity.layerId === "layer_1") {
    return true;
  }
  return identity.layerId === "layer_3" && LAYER3_GENERIC_FIELD_MIGRATION_MODULE_IDS.has(identity.moduleId);
}

function shouldMigrateGenericFieldNode(
  identity: ModuleInstance,
  nodeType: string,
  data: Record<string, unknown>,
  params: Record<string, unknown>
) {
  if (GENERIC_FIELD_MIGRATION_NODE_TYPES.has(nodeType)) {
    return true;
  }
  if (identity.layerId !== "layer_3" || identity.moduleId !== "humanistic_risk_response_config_v0_1") {
    return false;
  }
  return nodeType !== "module_output" && (Array.isArray(params.fields) || Array.isArray(data.fields));
}

function migrateGenericFieldsGraph(
  graph: ModuleGraph,
  registry: Record<string, ModuleInstance>
): ModuleGraph | null {
  const identity = layerModuleIdentity(graph.moduleNodeId, registry);
  if (!shouldMigrateGenericFieldsGraph(identity)) {
    return null;
  }

  let changed = false;
  const nextNodes = graph.nodes.map((node) => {
    const nextNode = cloneJson(node) as WorkflowNode;
    const schemaNode = schemaNodeRecord(nextNode);
    if (!schemaNode) {
      return nextNode;
    }
    const data = schemaDataRecord(schemaNode);
    const nodeType = String(data.node_type || schemaNode.type || "");
    const params = isRecord(data.params) ? { ...data.params } : {};
    if (!shouldMigrateGenericFieldNode(identity, nodeType, data, params)) {
      return nextNode;
    }
    const alreadyGeneric = params.mode === "generic_fields" && Array.isArray(params.fields);
    const legacyFields = fieldsFromData(data);
    const genericFields = alreadyGeneric
      ? refineGenericFieldsFromLegacy(cloneJson((params.fields as unknown[]).filter(isRecord)), legacyFields)
      : genericFieldsFromLegacyNode(data, params, identity.layerId, identity.moduleId);
    const needsLegacyDataBackup = Array.isArray(data.fields) && !Array.isArray(params.legacy_data_fields);
    const syncedParams = syncPrimaryLanguageCompatibilityFields({ ...params, fields: genericFields });
    if (
      nodeType === "text_input" &&
      alreadyGeneric &&
      stableJson(genericFields) === stableJson(params.fields) &&
      stableJson(syncedParams) === stableJson(params) &&
      !needsLegacyDataBackup
    ) {
      return nextNode;
    }
    if (nodeType !== "text_input") {
      data.legacy_node_type = data.legacy_node_type || nodeType;
      data.node_type = "text_input";
      schemaNode.type = "text_input";
      schemaNode.title_key = "node.type.text_input";
      schemaNode.title_fallback = "Text Input";
    }
    params.mode = "generic_fields";
    params.text = stringValue(params.text) || legacyTextValue(data, params);
    if (Array.isArray(params.fields) && !Array.isArray(params.legacy_fields)) {
      params.legacy_fields = cloneJson(params.fields);
    }
    if (needsLegacyDataBackup) {
      params.legacy_data_fields = cloneJson(data.fields);
    }
    params.fields = genericFields;
    data.params = syncPrimaryLanguageCompatibilityFields(params);
    changed = true;
    return nextNode;
  });

  return changed ? { ...graph, nodes: nextNodes } : null;
}

function isRiskResponseIdentity(identity: ModuleInstance) {
  return identity.moduleId === RISK_RESPONSE_MODULE_ID;
}

function graphNodeType(schemaNode: Record<string, unknown>, data: Record<string, unknown>) {
  return String(data.node_type || schemaNode.type || "");
}

function replaceReferenceNodeIdPrefix(nodeId: string) {
  return nodeId.startsWith("layer_2::") ? nodeId.replace(/^layer_2::/, "layer_3::") : nodeId;
}

function updateReferencePointers(value: unknown, nodeIdMap: Map<string, string>): unknown {
  if (Array.isArray(value)) {
    return value.map((item) => updateReferencePointers(item, nodeIdMap));
  }
  if (!isRecord(value)) {
    return value;
  }
  const next: Record<string, unknown> = {};
  for (const [key, item] of Object.entries(value)) {
    if ((key === "source_node_id" || key === "source" || key === "target") && typeof item === "string") {
      next[key] = nodeIdMap.get(item) ?? item;
      continue;
    }
    if (key === "source_layer_id" && value.source_module_id === RISK_RESPONSE_MODULE_ID) {
      next[key] = RISK_RESPONSE_LAYER_ID;
      continue;
    }
    next[key] = updateReferencePointers(item, nodeIdMap);
  }
  return next;
}

function migrateRiskResponseReferenceGraph(
  graph: ModuleGraph,
  registry: Record<string, ModuleInstance>
): { graph: ModuleGraph; nodeIdMap: Map<string, string>; oldGraphId?: string } | null {
  const identity = layerModuleIdentity(graph.moduleNodeId, registry);
  if (!isRiskResponseIdentity(identity)) {
    return null;
  }

  let changed = graph.moduleNodeId !== RISK_RESPONSE_MODULE_INSTANCE_ID || identity.layerId !== RISK_RESPONSE_LAYER_ID;
  const nodeIdMap = new Map<string, string>();
  const nextNodes = graph.nodes.map((node) => {
    const nextNode = cloneJson(node) as WorkflowNode;
    const schemaNode = schemaNodeRecord(nextNode);
    if (!schemaNode) {
      return nextNode;
    }
    const data = schemaDataRecord(schemaNode);
    const nodeType = graphNodeType(schemaNode, data);
    data.parent_module = RISK_RESPONSE_MODULE_INSTANCE_ID;
    data.module_instance_id = RISK_RESPONSE_MODULE_INSTANCE_ID;
    data.catalog_module_id = RISK_RESPONSE_MODULE_ID;
    schemaNode.layer_id = RISK_RESPONSE_LAYER_ID;
    schemaNode.module_id = RISK_RESPONSE_MODULE_ID;
    if (nodeType !== "reference_input" && nodeType !== "reference_output") {
      return nextNode;
    }

    const oldNodeId = String(schemaNode.node_id || (nextNode as unknown as Record<string, unknown>).id || "");
    const nextNodeId = replaceReferenceNodeIdPrefix(oldNodeId);
    if (oldNodeId && nextNodeId !== oldNodeId) {
      nodeIdMap.set(oldNodeId, nextNodeId);
      schemaNode.node_id = nextNodeId;
      const nextNodeRecord = nextNode as unknown as Record<string, unknown>;
      if (typeof nextNodeRecord.id === "string") {
        nextNodeRecord.id = nextNodeId;
      }
      changed = true;
    }

    data.parent_module = RISK_RESPONSE_MODULE_INSTANCE_ID;
    data.module_instance_id = RISK_RESPONSE_MODULE_INSTANCE_ID;
    data.catalog_module_id = RISK_RESPONSE_MODULE_ID;
    data.layer_id = RISK_RESPONSE_LAYER_ID;
    data.module_id = RISK_RESPONSE_MODULE_ID;
    if (nodeType === "reference_output") {
      const params = isRecord(data.params) ? { ...data.params } : {};
      data.params = {
        ...params,
        authority_source_type: "authoritative_constraint",
        is_core_source: false,
        override_allowed: false,
      };
      data.authority_source_type = "authoritative_constraint";
      data.is_core_source = false;
      data.override_allowed = false;
      changed = true;
    }
    return nextNode;
  });

  const nextEdges = graph.edges.map((edge) => {
    const nextEdge = cloneJson(edge) as WorkflowEdge;
    let edgeChanged = false;
    for (const key of ["source", "target", "source_node_id", "target_node_id"]) {
      const record = nextEdge as unknown as Record<string, unknown>;
      const current = typeof record[key] === "string" ? record[key] : "";
      const nextValue = nodeIdMap.get(current);
      if (nextValue) {
        record[key] = nextValue;
        edgeChanged = true;
      }
    }
    changed = changed || edgeChanged;
    return nextEdge;
  });

  if (!changed && nodeIdMap.size === 0) {
    return null;
  }
  return {
    graph: {
      ...graph,
      moduleNodeId: RISK_RESPONSE_MODULE_INSTANCE_ID,
      nodes: nextNodes,
      edges: nextEdges,
    },
    nodeIdMap,
    oldGraphId: graph.moduleNodeId !== RISK_RESPONSE_MODULE_INSTANCE_ID ? graph.moduleNodeId : undefined,
  };
}

function migrateMemoryProviderRouterTypeResolverGraph(
  graph: ModuleGraph,
  registry: Record<string, ModuleInstance>
): ModuleGraph | null {
  const identity = layerModuleIdentity(graph.moduleNodeId, registry);
  if (identity.layerId !== MEMORY_PROVIDER_ROUTER_LAYER_ID || identity.moduleId !== MEMORY_PROVIDER_ROUTER_MODULE_ID) {
    return null;
  }

  let changed = false;
  const nextNodes = graph.nodes.map((node) => {
    const nextNode = cloneJson(node) as WorkflowNode;
    const schemaNode = schemaNodeRecord(nextNode);
    if (!schemaNode) {
      return nextNode;
    }
    const data = schemaDataRecord(schemaNode);
    const catalogNodeId = String(data.catalog_node_id || schemaNode.node_id || "").split(MODULE_INSTANCE_SEPARATOR).pop() ?? "";
    if (catalogNodeId !== MEMORY_ROUTER_TYPE_RESOLVER_NODE_ID) {
      return nextNode;
    }

    const params = isRecord(data.params) ? { ...data.params } : {};
    const paramsNeedsMigration = hasExactStringList(params.allowed_memory_types, LEGACY_MEMORY_ROUTER_ALLOWED_MEMORY_TYPES);
    const dataNeedsMigration = hasExactStringList(data.allowed_memory_types, LEGACY_MEMORY_ROUTER_ALLOWED_MEMORY_TYPES);
    if (!paramsNeedsMigration && !dataNeedsMigration) {
      return nextNode;
    }
    if (paramsNeedsMigration) {
      params.allowed_memory_types = [...MEMORY_ROUTER_ALLOWED_MEMORY_TYPES];
      data.params = params;
    }
    if (dataNeedsMigration) {
      data.allowed_memory_types = [...MEMORY_ROUTER_ALLOWED_MEMORY_TYPES];
    }
    changed = true;
    return nextNode;
  });

  return changed ? { ...graph, nodes: nextNodes } : null;
}

function normalizeMemoryRouterOperationParams(params: Record<string, unknown>, catalogNodeId: string) {
  if (catalogNodeId === MEMORY_ROUTER_REQUEST_INPUT_NODE_ID) {
    const requestSchema = isRecord(params.request_schema) ? { ...params.request_schema } : null;
    if (!requestSchema || !hasExactStringList(requestSchema.operations, LEGACY_MEMORY_ROUTER_OPERATIONS)) {
      return params;
    }
    requestSchema.operations = [...MEMORY_ROUTER_CANONICAL_OPERATIONS];
    if (!Array.isArray(requestSchema.canonical_operations)) {
      requestSchema.canonical_operations = [...MEMORY_ROUTER_CANONICAL_OPERATIONS];
    }
    if (!Array.isArray(requestSchema.accepted_operations)) {
      requestSchema.accepted_operations = [...MEMORY_ROUTER_ACCEPTED_OPERATIONS];
    }
    if (!isRecord(requestSchema.operation_aliases)) {
      requestSchema.operation_aliases = { ...MEMORY_ROUTER_OPERATION_ALIASES };
    }
    return { ...params, request_schema: requestSchema };
  }
  if (catalogNodeId === MEMORY_ROUTER_OPERATION_CLASSIFIER_NODE_ID) {
    const oldOperations = hasExactStringList(params.operations, LEGACY_MEMORY_ROUTER_OPERATIONS);
    const oldRules = hasExactStringList(params.normalize_rules, LEGACY_MEMORY_ROUTER_NORMALIZE_RULES);
    if (!oldOperations && !oldRules) {
      return params;
    }
    const nextParams = { ...params };
    if (oldOperations) {
      nextParams.operations = [...MEMORY_ROUTER_CANONICAL_OPERATIONS];
    }
    if (oldRules) {
      nextParams.normalize_rules = [...MEMORY_ROUTER_NORMALIZE_RULES];
    }
    if (!Array.isArray(nextParams.canonical_operations)) {
      nextParams.canonical_operations = [...MEMORY_ROUTER_CANONICAL_OPERATIONS];
    }
    if (!isRecord(nextParams.operation_aliases)) {
      nextParams.operation_aliases = { ...MEMORY_ROUTER_OPERATION_ALIASES };
    }
    return nextParams;
  }
  return params;
}

function migrateMemoryProviderRouterOperationsGraph(
  graph: ModuleGraph,
  registry: Record<string, ModuleInstance>
): ModuleGraph | null {
  const identity = layerModuleIdentity(graph.moduleNodeId, registry);
  if (identity.layerId !== MEMORY_PROVIDER_ROUTER_LAYER_ID || identity.moduleId !== MEMORY_PROVIDER_ROUTER_MODULE_ID) {
    return null;
  }

  let changed = false;
  const nextNodes = graph.nodes.map((node) => {
    const nextNode = cloneJson(node) as WorkflowNode;
    const schemaNode = schemaNodeRecord(nextNode);
    if (!schemaNode) {
      return nextNode;
    }
    const data = schemaDataRecord(schemaNode);
    const catalogNodeId = String(data.catalog_node_id || schemaNode.node_id || "").split(MODULE_INSTANCE_SEPARATOR).pop() ?? "";
    const params = isRecord(data.params) ? { ...data.params } : {};
    const nextParams = normalizeMemoryRouterOperationParams(params, catalogNodeId);
    if (stableJson(nextParams) === stableJson(params)) {
      return nextNode;
    }
    data.params = nextParams;
    changed = true;
    return nextNode;
  });

  return changed ? { ...graph, nodes: nextNodes } : null;
}

function migrateReferencePointersAcrossGraphs(nodeIdMap: Map<string, string>) {
  if (!nodeIdMap.size) {
    return;
  }
  const store = useCanvasStore.getState();
  for (const graph of Object.values(store.moduleGraphs)) {
    let changed = false;
    const nextNodes = graph.nodes.map((node) => {
      const nextNode = updateReferencePointers(cloneJson(node), nodeIdMap) as WorkflowNode;
      if (stableJson(nextNode) !== stableJson(node)) {
        changed = true;
      }
      return nextNode;
    });
    const nextEdges = graph.edges.map((edge) => {
      const nextEdge = updateReferencePointers(cloneJson(edge), nodeIdMap) as WorkflowEdge;
      if (stableJson(nextEdge) !== stableJson(edge)) {
        changed = true;
      }
      return nextEdge;
    });
    if (changed) {
      store.updateModuleGraph(graph.moduleNodeId, nextNodes, nextEdges, graph.viewport);
      saveModuleGraphState(graph.moduleNodeId, nextNodes, nextEdges);
    }
  }
}

function applyGenericFieldsMigration(graph: ModuleGraph): ModuleGraph {
  const store = useCanvasStore.getState();
  const riskMigration = migrateRiskResponseReferenceGraph(graph, store.moduleInstanceRegistry);
  if (riskMigration) {
    store.updateModuleGraph(riskMigration.graph.moduleNodeId, riskMigration.graph.nodes, riskMigration.graph.edges, riskMigration.graph.viewport);
    saveModuleGraphState(riskMigration.graph.moduleNodeId, riskMigration.graph.nodes, riskMigration.graph.edges);
    if (riskMigration.oldGraphId) {
      store.removeModuleGraph(riskMigration.oldGraphId);
      if (typeof window !== "undefined") {
        window.localStorage.removeItem(`module_graph_${riskMigration.oldGraphId}`);
      }
    }
    migrateReferencePointersAcrossGraphs(riskMigration.nodeIdMap);
    console.log("[P1-BRIDGE] migrated risk response reference node ids", {
      moduleNodeId: riskMigration.graph.moduleNodeId,
      movedIds: riskMigration.nodeIdMap.size,
    });
  }
  const graphAfterRiskMigration = riskMigration?.graph ?? graph;
  const memoryRouterMigration = migrateMemoryProviderRouterTypeResolverGraph(graphAfterRiskMigration, store.moduleInstanceRegistry);
  if (memoryRouterMigration) {
    store.updateModuleGraph(memoryRouterMigration.moduleNodeId, memoryRouterMigration.nodes, memoryRouterMigration.edges, memoryRouterMigration.viewport);
    saveModuleGraphState(memoryRouterMigration.moduleNodeId, memoryRouterMigration.nodes, memoryRouterMigration.edges);
    console.log("[P1-BRIDGE] migrated memory provider router allowed memory types", {
      moduleNodeId: memoryRouterMigration.moduleNodeId,
    });
  }
  const graphAfterMemoryRouterMigration = memoryRouterMigration ?? graphAfterRiskMigration;
  const memoryRouterOperationsMigration = migrateMemoryProviderRouterOperationsGraph(graphAfterMemoryRouterMigration, store.moduleInstanceRegistry);
  if (memoryRouterOperationsMigration) {
    store.updateModuleGraph(
      memoryRouterOperationsMigration.moduleNodeId,
      memoryRouterOperationsMigration.nodes,
      memoryRouterOperationsMigration.edges,
      memoryRouterOperationsMigration.viewport
    );
    saveModuleGraphState(memoryRouterOperationsMigration.moduleNodeId, memoryRouterOperationsMigration.nodes, memoryRouterOperationsMigration.edges);
    console.log("[P1-BRIDGE] migrated memory provider router operations", {
      moduleNodeId: memoryRouterOperationsMigration.moduleNodeId,
    });
  }
  const graphAfterMemoryRouterOperationsMigration = memoryRouterOperationsMigration ?? graphAfterMemoryRouterMigration;
  const migratedGraph = migrateGenericFieldsGraph(graphAfterMemoryRouterOperationsMigration, store.moduleInstanceRegistry);
  if (migratedGraph) {
    store.updateModuleGraph(migratedGraph.moduleNodeId, migratedGraph.nodes, migratedGraph.edges, migratedGraph.viewport);
    saveModuleGraphState(migratedGraph.moduleNodeId, migratedGraph.nodes, migratedGraph.edges);
    console.log("[P1-BRIDGE] migrated field/text input nodes to generic_fields", {
      moduleNodeId: migratedGraph.moduleNodeId,
    });
    return migratedGraph;
  }
  return graphAfterMemoryRouterOperationsMigration;
}

function migrateExistingGenericFieldsGraphs() {
  const store = useCanvasStore.getState();
  for (const graph of Object.values(store.moduleGraphs)) {
    applyGenericFieldsMigration(graph);
  }
}

/**
 * 初始化 module state 水合
 * 
 * 优先级：store > localStorage > 默认值
 * 
 * 这个函数应该在 CanvasShell 首次挂载时调用（在所有 UI 渲染之前）
 */
export function initializeModuleState() {
  console.log("[P1-BRIDGE] initializeModuleState: starting hydration");
  
  const store = useCanvasStore.getState();
  
  // 1. 尝试从 localStorage 恢复（作为后备方案）
  const stored = loadCanvasStateFromLocalStorage();
  
  // 2. 构建完整的 module state（store 优先）
  const moduleState = {
    moduleTabs: store.moduleTabs.length > 0 
      ? store.moduleTabs 
      : stored?.moduleTabs ?? [],
    activeModuleTabId: store.activeModuleTabId,
    moduleNames: Object.keys(store.moduleNames).length > 0
      ? store.moduleNames
      : stored?.moduleNames ?? {},
    uiNodeNames: Object.keys(store.uiNodeNames).length > 0
      ? store.uiNodeNames
      : stored?.uiNodeNames ?? {},
    uiTags: Object.keys(store.uiTags).length > 0
      ? store.uiTags
      : stored?.uiTags ?? {},
    uiGroups: Object.keys(store.uiGroups).length > 0
      ? store.uiGroups
      : stored?.uiGroups ?? {},
    uiColors: Object.keys(store.uiColors).length > 0
      ? store.uiColors
      : stored?.uiColors ?? {},
    moduleUiColors: Object.keys(store.moduleUiColors).length > 0
      ? store.moduleUiColors
      : stored?.moduleUiColors ?? {},
    layerModules: Object.keys(store.layerModules).length > 0
      ? store.layerModules
      : stored?.layerModules ?? {},
    moduleInstanceRegistry: Object.keys(store.moduleInstanceRegistry).length > 0
      ? store.moduleInstanceRegistry
      : stored?.moduleInstanceRegistry ?? {},
  };
  
  // 3. 同步回 store
  store.setModuleTabs(moduleState.moduleTabs);
  store.setModuleNames(moduleState.moduleNames);
  store.setUiNodeNames(moduleState.uiNodeNames);
  store.setUiTags(moduleState.uiTags);
  store.setUiGroups(moduleState.uiGroups);
  store.setUiColors(moduleState.uiColors);
  store.setModuleUiColors(moduleState.moduleUiColors);
  store.setLayerModules(moduleState.layerModules);
  store.setModuleInstanceRegistry(moduleState.moduleInstanceRegistry);
  migrateExistingGenericFieldsGraphs();
  
  console.log("[P1-BRIDGE] initializeModuleState: hydration completed", {
    tabCount: moduleState.moduleTabs.length,
    instanceCount: Object.keys(moduleState.moduleInstanceRegistry).length,
  });
}

/**
 * 为某个 module tab 初始化或恢复其 graph
 * 
 * 优先级：
 * 1. store 中已存在的 graph
 * 2. localStorage 中保存的 graph（从旧的 `module_graph_${moduleId}` key）
 * 3. 创建空 graph
 */
export function ensureModuleGraphExists(moduleNodeId: string, initialNodes?: WorkflowNode[], initialEdges?: WorkflowEdge[]) {
  console.log("[P1-BRIDGE] ensureModuleGraphExists:", { moduleNodeId });
  
  const store = useCanvasStore.getState();
  const hasInitialGraph = Boolean(initialNodes?.length || initialEdges?.length);
  
  // 1. 检查 store 中是否已存在
  const existingGraph = store.moduleGraphs[moduleNodeId];
  if (existingGraph) {
    if (shouldReplaceWithCatalogGraph(existingGraph, initialNodes, initialEdges)) {
      const graph: ModuleGraph = {
        moduleNodeId,
        nodes: initialNodes ?? [],
        edges: initialEdges ?? [],
        viewport: existingGraph.viewport,
      };
      store.updateModuleGraph(moduleNodeId, graph.nodes, graph.edges, graph.viewport);
      saveModuleGraphState(moduleNodeId, graph.nodes, graph.edges);
      console.log("[P1-BRIDGE] ensureModuleGraphExists: replaced stale catalog graph with current seed");
      return applyGenericFieldsMigration(graph);
    }
    const hasExistingGraph = Boolean(existingGraph.nodes?.length || existingGraph.edges?.length);
    if (!hasExistingGraph && hasInitialGraph) {
      const graph: ModuleGraph = {
        moduleNodeId,
        nodes: initialNodes ?? [],
        edges: initialEdges ?? [],
        viewport: existingGraph.viewport,
      };
      store.updateModuleGraph(moduleNodeId, graph.nodes, graph.edges, graph.viewport);
      console.log("[P1-BRIDGE] ensureModuleGraphExists: replaced empty graph with catalog seed");
      return applyGenericFieldsMigration(graph);
    }
    const mergedGraph = mergeCatalogSeed(existingGraph, initialNodes, initialEdges);
    if (mergedGraph) {
      store.updateModuleGraph(moduleNodeId, mergedGraph.nodes, mergedGraph.edges, mergedGraph.viewport);
      console.log("[P1-BRIDGE] ensureModuleGraphExists: merged catalog field seed into existing graph");
      return applyGenericFieldsMigration(mergedGraph);
    }
    console.log("[P1-BRIDGE] ensureModuleGraphExists: graph already in store");
    return applyGenericFieldsMigration(existingGraph);
  }
  
  // 2. 尝试从 localStorage 恢复（旧的单个 graph 存储）
  const legacyGraph = loadModuleGraphState(moduleNodeId);
  if (legacyGraph?.nodes?.length || legacyGraph?.edges?.length) {
    console.log("[P1-BRIDGE] ensureModuleGraphExists: graph found in legacy localStorage");
    const graph: ModuleGraph = {
      moduleNodeId,
      nodes: legacyGraph.nodes as WorkflowNode[],
      edges: legacyGraph.edges as WorkflowEdge[],
    };
    if (shouldReplaceWithCatalogGraph(graph, initialNodes, initialEdges)) {
      const seedGraph: ModuleGraph = {
        moduleNodeId,
        nodes: initialNodes ?? [],
        edges: initialEdges ?? [],
      };
      store.updateModuleGraph(moduleNodeId, seedGraph.nodes, seedGraph.edges, seedGraph.viewport);
      saveModuleGraphState(moduleNodeId, seedGraph.nodes, seedGraph.edges);
      console.log("[P1-BRIDGE] ensureModuleGraphExists: replaced stale legacy graph with current catalog seed");
      return applyGenericFieldsMigration(seedGraph);
    }
    const mergedGraph = mergeCatalogSeed(graph, initialNodes, initialEdges) ?? graph;
    store.updateModuleGraph(moduleNodeId, mergedGraph.nodes, mergedGraph.edges, mergedGraph.viewport);
    if (mergedGraph !== graph) {
      console.log("[P1-BRIDGE] ensureModuleGraphExists: merged catalog field seed into legacy graph");
    }
    return applyGenericFieldsMigration(mergedGraph);
  }
  
  // 3. 创建新的空 graph
  const newGraph: ModuleGraph = {
    moduleNodeId,
    nodes: initialNodes ?? [],
    edges: initialEdges ?? [],
  };
  store.updateModuleGraph(moduleNodeId, newGraph.nodes, newGraph.edges);
  console.log(hasInitialGraph ? "[P1-BRIDGE] ensureModuleGraphExists: created graph from catalog seed" : "[P1-BRIDGE] ensureModuleGraphExists: created new empty graph");
  
  return applyGenericFieldsMigration(newGraph);
}

/**
 * 清理孤立的 graph（对应的 module 不在 moduleTabs 中）
 */
export function cleanupOrphanedGraphs() {
  console.log("[P1-BRIDGE] cleanupOrphanedGraphs: starting");
  // Do not delete graphs merely because their tab is not currently open.
  // Module graph ids include the layer-scoped instance id; when a module is
  // displayed under its catalog layer, older instance ids can still hold the
  // user's filled node data and must remain available for recovery.
  console.log("[P1-BRIDGE] cleanupOrphanedGraphs: skipped to preserve recoverable module graphs");
}

/**
 * 为所有 tabs 确保都有对应的 graph
 */
export function ensureAllTabsHaveGraphs() {
  console.log("[P1-BRIDGE] ensureAllTabsHaveGraphs: starting");
  
  const store = useCanvasStore.getState();
  const tabs = store.moduleTabs;
  const graphs = store.moduleGraphs;
  
  let created = 0;
  
  for (const tabId of tabs) {
    if (!graphs[tabId]) {
      ensureModuleGraphExists(tabId);
      created++;
    }
  }
  
  console.log("[P1-BRIDGE] ensureAllTabsHaveGraphs: completed", { 
    totalTabs: tabs.length, 
    createdGraphs: created,
  });
}

/**
 * 处理 tab 打开事件
 */
export function handleTabOpened(moduleId: string, initialNodes?: WorkflowNode[], initialEdges?: WorkflowEdge[]) {
  console.log("[P1-BRIDGE] handleTabOpened:", { moduleId });
  
  const store = useCanvasStore.getState();
  
  // 1. 确保 tab 在 moduleTabs 中
  if (!store.moduleTabs.includes(moduleId)) {
    store.openModuleTab(moduleId);
  }
  
  // 2. 确保 graph 存在
  ensureModuleGraphExists(moduleId, initialNodes, initialEdges);
  
  // 3. 设置为 active
  store.setActiveModuleTabId(moduleId);
}

/**
 * 处理 tab 关闭事件
 */
export function handleTabClosed(moduleId: string) {
  console.log("[P1-BRIDGE] handleTabClosed:", { moduleId });
  
  const store = useCanvasStore.getState();
  
  // 1. 从 moduleTabs 移除
  store.closeModuleTab(moduleId);
  
  // 2. 可选：清理对应的 graph（取决于是否希望保留以便重新打开）
  // 如果希望关闭后再打开时恢复数据，不删除 graph
  // store.removeModuleGraph(moduleId);
}

/**
 * 从 CanvasShell useState 迁移到 store 的临时适配器
 * 
 * 用法：
 * const stateAdapter = createStateAdapter(localModuleTabs, localModuleNames, ...);
 * // 使用 stateAdapter 中的值作为 React state 的初始值
 * // 同时将这些值同步到 store
 */
export function createStateAdapter(
  localModuleTabs: string[],
  localModuleNames: Record<string, string>,
  localUiNodeNames: Record<string, string>,
  localUiTags: Record<string, string[]>,
  localUiGroups: Record<string, string>,
  localUiColors: Record<string, string>,
  localModuleUiColors: Record<string, string>,
  localLayerModules: Record<string, string[]>,
  localModuleInstanceRegistry: Record<string, ModuleInstance>
) {
  const store = useCanvasStore.getState();
  
  // 同步 useState 的值到 store
  if (localModuleTabs.length > 0) {
    store.setModuleTabs(localModuleTabs);
  }
  if (Object.keys(localModuleNames).length > 0) {
    store.setModuleNames(localModuleNames);
  }
  if (Object.keys(localUiNodeNames).length > 0) {
    store.setUiNodeNames(localUiNodeNames);
  }
  if (Object.keys(localUiTags).length > 0) {
    store.setUiTags(localUiTags);
  }
  if (Object.keys(localUiGroups).length > 0) {
    store.setUiGroups(localUiGroups);
  }
  if (Object.keys(localUiColors).length > 0) {
    store.setUiColors(localUiColors);
  }
  if (Object.keys(localModuleUiColors).length > 0) {
    store.setModuleUiColors(localModuleUiColors);
  }
  if (Object.keys(localLayerModules).length > 0) {
    store.setLayerModules(localLayerModules);
  }
  if (Object.keys(localModuleInstanceRegistry).length > 0) {
    store.setModuleInstanceRegistry(localModuleInstanceRegistry);
  }
  
  return {
    moduleTabs: localModuleTabs,
    moduleNames: localModuleNames,
    uiNodeNames: localUiNodeNames,
    uiTags: localUiTags,
    uiGroups: localUiGroups,
    uiColors: localUiColors,
    moduleUiColors: localModuleUiColors,
    layerModules: localLayerModules,
    moduleInstanceRegistry: localModuleInstanceRegistry,
  };
}
