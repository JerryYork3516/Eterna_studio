import { useCallback, useEffect, useMemo, useRef, useState, type CSSProperties, type DragEvent as ReactDragEvent, type MouseEvent as ReactMouseEvent, type ReactNode } from "react";
import { createPortal } from "react-dom";
import {
  addEdge,
  applyEdgeChanges,
  applyNodeChanges,
  Background,
  Controls,
  Handle,
  MiniMap,
  Position,
  ReactFlow,
  useEdgesState,
  useNodesState,
  type Connection,
  type Edge,
  type EdgeChange,
  type Node,
  type NodeChange,
  type NodeMouseHandler,
  type NodeProps,
  type ReactFlowInstance
} from "@xyflow/react";
import { translate, type Language } from "@/i18n";
import { aiSlotClass, aiSlotLabel, inferAiSlot } from "@/lib/ai-slot";
import { api } from "@/lib/api";
import type { DRLoadResult, LLMProfileInput } from "@/lib/api";
import type { ModuleCatalogEntryV04, ModuleCatalogResponseV04, NodeType, ResidentInstanceV03, Workflow, WorkflowEdge, WorkflowNode } from "@/lib/schema-types";
import { safeClone, safeSerialize } from "@/lib/safe-serialize";
import { downloadWorkflow } from "@/lib/workflow";
import { ModuleLibrary, readModuleDragId } from "@/components/ModuleLibrary";
import { StudioAssistantPanel } from "@/components/assistant/StudioAssistantPanel";
import { getNodeDefinition, getNodeRegistryEntries, getNodeStatus, setBackendNodeRegistry, type NodeDefinition, type NodeInputField } from "@/registry/nodeRegistry";
import { useCanvasStore } from "@/store/canvas-store";
import { filterDanglingModuleGraphEdges } from "@/store/module-graph-merge";
import { LayerContainerNode } from "@/components/canvas/LayerContainerNode";
import { WorkflowNodeCard, WorkflowNodeCardModuleNodesProvider } from "@/components/canvas/WorkflowNodeCard";
import { ResidentNeuralGraphPanel } from "@/components/neural-graph/ResidentNeuralGraphPanel";
import type { StudioAssistantPatch, StudioAssistantRequest } from "@/lib/studioAssistantApi";
import {
  type CanvasState,
  type ModuleInstance as PersistenceModuleInstance,
  createEmptyCanvasState,
  deserializeCanvasState,
  downloadCanvasState,
  loadCanvasStateFromLocalStorage,
  readCanvasStateFromFile,
  saveCanvasStateToLocalStorage,
  validateCanvasState,
  loadModuleGraphState,
  saveModuleGraphState
} from "@/lib/canvas-persistence";
import {
  initializeModuleState,
  ensureModuleGraphExists,
  cleanupOrphanedGraphs,
  ensureAllTabsHaveGraphs,
  handleTabOpened,
  handleTabClosed
} from "@/store/module-state-bridge";

type MockNodeType =
  | "text_input"
  | "identity"
  | "personality"
  | "dialogue"
  | "voice_profile"
  | "particle_avatar"
  | "model_adapter"
  | "memory"
  | "knowledge"
  | "tools"
  | "output"
  | "compile_resident"
  | "api_connector"
  | "model_loader"
  | "local_model"
  | "llm_adapter"
  | "tts_adapter"
  | "ar_particle"
  | "particle_physics"
  | "avatar_preview"
  | "runtime_mock"
  | "export_package";
type ModuleNodeType = NodeType | MockNodeType;

const NODE_DND_MIME = "application/eterna-node";
const MODULE_INSTANCE_SEPARATOR = "::";

function backendNodeCategory(type: NodeType): string {
  const definition = getNodeDefinition(String(type));
  if (definition?.category) {
    return definition.category;
  }
  switch (type) {
    case "input":
      return "source";
    case "output":
    case "export":
      return "sink";
    case "model":
    case "agent":
      return "ai";
    case "review":
      return "control";
    default:
      return "processing";
  }
}

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

function referenceNodeDefaultParams(type: ModuleNodeType, layerId?: string): Record<string, unknown> {
  if (type === "reference_output") {
    const authoritySourceType = referenceAuthoritySourceTypeForLayer(layerId);
    return {
      export_name: "",
      export_description: "",
      export_scope: "module",
      export_scopes: ["module", "node", "field"],
      allow_module_level_reference: true,
      export_fields: [],
      allow_layers: [],
      forbidden_layers: [],
      authority_source_type: authoritySourceType,
      is_core_source: authoritySourceType === "core_fact",
      override_allowed: false
    };
  }
  if (type === "reference_input") {
    return {
      references: []
    };
  }
  return {};
}

function referenceNodeDefaultColor(type: ModuleNodeType) {
  if (type === "reference_output") {
    return "#22d3ee";
  }
  if (type === "reference_input") {
    return "#8b5cf6";
  }
  return "";
}

function setNodeDragData(event: ReactDragEvent, type: ModuleNodeType) {
  event.dataTransfer.setData(NODE_DND_MIME, type);
  event.dataTransfer.setData("text/plain", type);
  event.dataTransfer.effectAllowed = "copy";
}

function readNodeDragType(event: ReactDragEvent): ModuleNodeType | null {
  const value = event.dataTransfer.getData(NODE_DND_MIME) || event.dataTransfer.getData("text/plain");
  return value ? (value as ModuleNodeType) : null;
}
const TRUNK_LAYER_HEIGHT = 216;
const FOLDER_GROUP_X = 80;
// Main-canvas folder preview: width is sized to fit FOLDER_PREVIEW_MODULE_LIMIT cards
// (each 180px + 10px gap) plus rail/section padding. Changing the limit must keep the
// width in sync so the rail does not clip cards.
const FOLDER_PREVIEW_MODULE_LIMIT = 6;
const FOLDER_GROUP_WIDTH = 1180;
const FOLDER_GROUP_HEIGHT = 216;
const FOLDER_TO_TRUNK_GAP = 120;
const TRUNK_LAYER_WIDTH = 346;
const TRUNK_LAYER_X = FOLDER_GROUP_X + FOLDER_GROUP_WIDTH + FOLDER_TO_TRUNK_GAP / 2;
const LAYER_ASSEMBLY_PANEL_GAP = 84;
const TRUNK_LAYER_Y_OFFSET = 110;
const LAYER_STACK_GAP = 80;
const LAYER_NODE_ROW_HEIGHT = 72;
const LAYER_STACK_PADDING = 120;

type LayerStackFrame = { x: number; y: number; width: number; height: number };

type CatalogLayerInput = { layer_id: string; layer_order: number; layer_name: string };

function catalogLayerOrder(layer: CatalogLayerInput) {
  return Number(layer.layer_order);
}

function displayText(value: unknown) {
  return typeof value === "string" && value.trim() ? value.trim() : "";
}

function uniqueDisplayValues(values: string[]) {
  return [...new Set(values.filter(Boolean))];
}

function mixedOrSingle(values: string[], emptyValue: string) {
  const unique = uniqueDisplayValues(values);
  if (!unique.length) {
    return emptyValue;
  }
  return unique.length === 1 ? unique[0] : "mixed";
}

function isHiddenCatalogModule(module: ModuleCatalogEntryV04) {
  return module.ui_config?.hidden_in_module_library === true || module.config?.hidden_in_module_library === true || module.ui_config?.catalog_only === true || module.config?.catalog_only === true;
}

function modulesForLayer(layer: CatalogLayerInput, moduleCatalog: ModuleCatalogResponseV04) {
  return moduleCatalog.modules.filter((module) => module.layer_id === layer.layer_id && !isHiddenCatalogModule(module));
}

function getLayerDisplayMeta(layer: CatalogLayerInput, t: (key: string, fallback?: string) => string) {
  const order = catalogLayerOrder(layer);
  const groupLabel =
    order <= 4
      ? t("ui.layerGroup.identityConstraints", "GROUP A: IDENTITY & CONSTRAINTS")
      : order <= 7
        ? t("ui.layerGroup.cognitionSystem", "GROUP B: COGNITION SYSTEM")
        : order <= 10
          ? t("ui.layerGroup.actionExecution", "GROUP C: ACTION & EXECUTION")
          : order <= 12
            ? t("ui.layerGroup.socialMeta", "GROUP D: SOCIAL & META")
            : t("ui.layerGroup.output", "GROUP E: OUTPUT");
  const moduleTier = order === 5 || order === 9 ? "later" : order === 11 || order === 12 ? "plugin" : "core";
  const lockLevel: WorkflowNode["lock_level"] =
    order === 1 || order === 8 || order === 11
      ? "editable"
      : order >= 2 && order <= 4
        ? "locked"
        : order === 13
          ? "mixed"
          : "review_required";
  const review =
    lockLevel === "editable"
      ? t("ui.lock.editable")
      : lockLevel === "locked"
        ? t("ui.lock.locked")
        : lockLevel === "mixed"
          ? t("ui.lock.mixed")
          : t("ui.lock.reviewRequired");

  return {
    groupLabel,
    module_tier: moduleTier,
    lock_level: lockLevel,
    review
  };
}

function getLayerCatalogDisplayFields(layer: CatalogLayerInput, moduleCatalog: ModuleCatalogResponseV04, t: (key: string, fallback?: string) => string) {
  const modules = modulesForLayer(layer, moduleCatalog);
  const statuses = modules.map((module) => displayText(module.status));
  const versions = modules.map((module) => displayText(module.module_version));
  const displayMeta = getLayerDisplayMeta(layer, t);

  return {
    groupLabel: displayMeta.groupLabel,
    status: mixedOrSingle(statuses, t("ui.layer.empty", "empty")),
    version: mixedOrSingle(versions, displayText(moduleCatalog.protocol_version)),
    children_count: modules.length,
    review: displayMeta.review,
    module_tier: displayMeta.module_tier,
    lock_level: displayMeta.lock_level
  } satisfies {
    groupLabel: string;
    status: string;
    version: string;
    children_count: number;
    review: string;
    module_tier: string;
    lock_level: WorkflowNode["lock_level"];
  };
}

function catalogLayerToWorkflowNode(layer: CatalogLayerInput, moduleCatalog: ModuleCatalogResponseV04): WorkflowNode {
  const layerOrder = catalogLayerOrder(layer);
  const catalogLayerName = layerDisplayName(useCanvasStore.getState().language, layer, layer.layer_name);
  return {
    node_id: layer.layer_id,
    type: "layer_container",
    category: "container",
    title_key: `layer.${layer.layer_id}`,
    title_fallback: catalogLayerName,
    position: { x: TRUNK_LAYER_X, y: TRUNK_LAYER_Y_OFFSET + (layerOrder - 1) * (FOLDER_GROUP_HEIGHT + LAYER_STACK_GAP) },
    lock_level: "editable",
    locale: null,
    data: { layer_order: layerOrder, layer_name: catalogLayerName },
    ports: {
      inputs: [{ port_id: "p_left_in", name: "in", direction: "in" }],
      outputs: [{ port_id: "p_out", name: "out", direction: "out" }]
    },
    validation: null
  } as WorkflowNode;
}

// CLEAN V4: the canvas graph is derived purely from the v0.4 module-catalog
// layers (13 frozen). No v0.3 workflow / createPersonaBuilder is used as a UI
// data source. Vertical TRUNK layout preserved; visualization only.
function buildSchemaWorkflow(moduleCatalog: ModuleCatalogResponseV04 | null): Workflow | null {
  if (!moduleCatalog) {
    return null;
  }
  const ordered = moduleCatalog.layers.slice().sort((a, b) => catalogLayerOrder(a) - catalogLayerOrder(b));
  if (!ordered.length) {
    return null;
  }
  const nodes = ordered.map((layer) => catalogLayerToWorkflowNode(layer, moduleCatalog));
  return {
    schema_version: "0.4.0",
    name: "Schema Canvas",
    version: "1.0.0",
    template_type: "schema_v04",
    nodes,
    edges: [],
    metadata: {}
  } as unknown as Workflow;
}
const MOCK_MODE = false;
const MODULE_COLOR_SWATCHES = [
  "#7aa2f7",
  "#5dd39e",
  "#a78bfa",
  "#f2a65a",
  "#f87171",
  "#22d3ee",
  "#facc15",
  "#94a3b8",
  "#e879f9",
  "#38bdf8"
];
const MODULE_COLOR_LABEL_KEYS = [
  "module.color.blue",
  "module.color.green",
  "module.color.purple",
  "module.color.orange",
  "module.color.red",
  "module.color.cyan",
  "module.color.yellow",
  "module.color.gray",
  "module.color.pink",
  "module.color.sky"
];
type BottomTab = "logs" | "artifacts" | "preview";
type DrawerId = "layers" | "residentPreview" | "residentNeuralGraph" | "settings" | "assistant" | "debugTrace" | BottomTab;
type ModuleAssistantPanelState = {
  title: string;
  meta: string;
  request: StudioAssistantRequest;
  canApplyPatch: boolean;
  onApplyPatch: (patch: StudioAssistantPatch) => void;
};
type WorkspaceMode = "inline" | "right" | "split" | "window";
type RunWorkflowStatus = "idle" | "running" | "success" | "error";
type AlignAction = "left" | "right" | "top" | "bottom" | "center-x" | "center-y";
type DistributeAction = "horizontal" | "vertical";
type CanvasContextMenuItem = {
  label: string;
  onSelect?: () => void;
  disabled?: boolean;
  danger?: boolean;
  children?: CanvasContextMenuItem[];
};
type CanvasContextMenuState = {
  x: number;
  y: number;
  items: CanvasContextMenuItem[];
};
type FlowHistorySnapshot = {
  nodes: Node[];
  edges: Edge[];
};
type FlowHistoryState = {
  past: FlowHistorySnapshot[];
  future: FlowHistorySnapshot[];
  restoring: boolean;
};
type MainCanvasSnapshot = {
  layerModules: Record<string, string[]>;
  moduleInstanceRegistry: Record<string, ModuleInstance>;
  moduleTabs: string[];
  activeModuleTabId: string | null;
  focusedModuleId: string | null;
  moduleNames: Record<string, string>;
  uiNodeNames: Record<string, string>;
  uiTags: Record<string, string[]>;
  uiGroups: Record<string, string>;
  uiColors: Record<string, string>;
  moduleUiColors: Record<string, string>;
  selectedLayerModuleKeys: string[];
  expandedLayerIds: string[];
  activeLayerId: string | null;
  activeWorkspaceId: string | null;
  workspaceTabs: string[];
  floatingLayerIds: string[];
  floatingNodeIds: string[];
  draggedNodeIds: string[];
};
type MainHistoryState = {
  past: MainCanvasSnapshot[];
  future: MainCanvasSnapshot[];
  restoring: boolean;
};

const CANVAS_HISTORY_LIMIT = 60;
type NodeLibraryCategory = {
  id: string;
  labelKey: string;
  labelFallback: string;
  nodes: ModuleNodeType[];
};
type ContextMenuEvent = ReactMouseEvent | MouseEvent;
type SaveStatus = "saved" | "dirty" | "error";
type ResidentInstance = ResidentInstanceV03;

type ResidentPreviewTab = "dialogue" | "voice" | "avatar";

type ModuleInstance = {
  instanceId: string;
  moduleId: string;
  layerId: string;
};

type FolderGroupNodeData = {
  layer: CatalogLayerInput;
  moduleCatalog: ModuleCatalogResponseV04;
  subnodes: WorkflowNode[];
  modules: ModuleCatalogEntryV04[];
  focusedModuleId: string | null;
  selectedModuleKeys: string[];
  moduleNames: Record<string, string>;
  moduleColors: Record<string, string>;
  uiColor?: string;
  onSelectNode: (node: WorkflowNode) => void;
  onPreviewNode: (node: WorkflowNode) => void;
  onFocusNode: (node: WorkflowNode) => void;
  onDropModule: (moduleId: string) => void;
  onSelectDroppedModule: (moduleId: string, multi: boolean) => void;
  onOpenDroppedModule: (moduleId: string) => void;
  onRemoveModule: (moduleId: string) => void;
  onColorModule: (moduleId: string, color: string) => void;
  onOpenModuleFocus: () => void;
  onContainerContextMenu: (event: ReactMouseEvent) => void;
  onDroppedModuleContextMenu: (event: ReactMouseEvent, moduleId: string) => void;
  onModuleContextMenu: (event: ReactMouseEvent, node: WorkflowNode) => void;
};

function moduleCatalogId(module: ModuleCatalogEntryV04) {
  return module.module_id;
}

function moduleCatalogName(module: ModuleCatalogEntryV04, t: (key: string, fallback?: string) => string) {
  return t(module.i18n_keys?.display_name || `module.${module.module_id}`, module.module_name);
}

function moduleCatalogSlot(module: ModuleCatalogEntryV04) {
  if (module.slot_type) {
    return module.slot_type;
  }
  return moduleCatalogClass(module) === "core" ? "core" : "unplanned";
}

function moduleCatalogClass(module: ModuleCatalogEntryV04) {
  const classification = module.ui_config?.classification;
  const moduleClass = module.config?.module_class;
  if (typeof classification === "string" && classification) {
    return classification;
  }
  if (typeof moduleClass === "string" && moduleClass) {
    return moduleClass;
  }
  return module.category || "plugin";
}

function i18nCandidate(language: Language, keys: string[], fallback: string) {
  for (const key of keys) {
    const marker = `__missing__${key}`;
    const translated = translate(language, key, marker);
    if (translated !== marker) {
      return translated;
    }
  }
  return fallback;
}

function stableI18nKeyPart(value: string) {
  return value
    .trim()
    .replace(/([a-z0-9])([A-Z])/g, "$1_$2")
    .replace(/[^a-zA-Z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "")
    .toLowerCase();
}

function assemblyStatusLabel(language: Language, value: unknown, fallback?: string) {
  const raw = typeof value === "string" && value.trim() ? value.trim() : fallback || "";
  if (!raw) {
    return translate(language, "common.notGenerated", "Not generated");
  }
  const normalized = stableI18nKeyPart(raw);
  return i18nCandidate(language, [`assembly.status.${normalized}`, `module.status.${raw}`, `lock.${raw}`], fallback || raw);
}

function assemblyFieldLabel(language: Language, value: string, fallback?: string) {
  const raw = value.trim();
  if (!raw) {
    return fallback || translate(language, "common.field", "Field");
  }
  const normalized = stableI18nKeyPart(raw);
  return i18nCandidate(
    language,
    [`assembly.field.${normalized}`, `node.coreParams.key.${raw}`, `field.identity.${raw}.label`, `field.${raw}`],
    fallback || raw
  );
}

function assemblyPrimitiveLabel(language: Language, value: unknown) {
  if (typeof value === "boolean") {
    return translate(language, value ? "common.yes" : "common.no", value ? "Yes" : "No");
  }
  if (typeof value === "number") {
    return String(value);
  }
  return String(value ?? "");
}

function assemblyModuleIdLabel(language: Language, moduleId: string, moduleCatalog: ModuleCatalogResponseV04 | null) {
  const catalogModule = moduleCatalog?.modules.find((candidate) => candidate.module_id === moduleId);
  if (catalogModule) {
    return i18nCandidate(language, [catalogModule.i18n_keys?.display_name || "", `module.${catalogModule.module_id}`], catalogModule.module_name);
  }
  return i18nCandidate(language, [`module.${moduleId}`], moduleId);
}

function assemblyModuleLabel(language: Language, module: Record<string, unknown>, moduleCatalog: ModuleCatalogResponseV04 | null) {
  const moduleId = String(module.module_id ?? module.id ?? "");
  const catalogLabel = moduleId ? assemblyModuleIdLabel(language, moduleId, moduleCatalog) : "";
  if (catalogLabel && catalogLabel !== moduleId) {
    return catalogLabel;
  }
  const fallback = String((module.module_name ?? module.name ?? module.title ?? moduleId) || translate(language, "assembly.field.module", "Module"));
  return i18nCandidate(language, [`module.${moduleId}`], fallback);
}

function layerDisplayName(language: Language, layer: CatalogLayerInput, fallback = "") {
  return i18nCandidate(language, [`layer.${layer.layer_id}`, `layer.${layer.layer_order}.name`], fallback || layer.layer_name || layer.layer_id);
}

function validationFindingMessage(language: Language, finding: unknown) {
  if (!isRecord(finding)) {
    return String(finding ?? "");
  }
  const code = typeof finding.code === "string" ? finding.code : "";
  const message = typeof finding.message === "string" ? finding.message : "";
  if (!code) {
    return message;
  }
  return i18nCandidate(language, [`validation.${code}`, `validation.${stableI18nKeyPart(code)}`, `audit.${code}`], message || code);
}

function moduleDisplayLayerId(module: ModuleCatalogEntryV04, storedLayerId: string) {
  return module.layer_id === "general" ? storedLayerId : module.layer_id;
}

function moduleIdsForDisplayLayer(layerModules: Record<string, string[]>, layerId: string, moduleCatalogById: Map<string, ModuleCatalogEntryV04>) {
  const ids: string[] = [];
  for (const [storedLayerId, moduleIds] of Object.entries(layerModules)) {
    for (const moduleId of moduleIds) {
      if (ids.includes(moduleId)) {
        continue;
      }
      const module = moduleCatalogById.get(moduleId);
      if (!module || isHiddenCatalogModule(module)) {
        continue;
      }
      if (moduleDisplayLayerId(module, storedLayerId) === layerId) {
        ids.push(moduleId);
      }
    }
  }
  return ids;
}

function storedLayerIdForModule(layerModules: Record<string, string[]>, moduleId: string, fallbackLayerId: string) {
  return Object.entries(layerModules).find(([, moduleIds]) => moduleIds.includes(moduleId))?.[0] ?? fallbackLayerId;
}

function moduleIdFromInstanceId(instanceId: string) {
  return instanceId.split(MODULE_INSTANCE_SEPARATOR).slice(1).join(MODULE_INSTANCE_SEPARATOR);
}

function layerIdFromInstanceId(instanceId: string) {
  return instanceId.split(MODULE_INSTANCE_SEPARATOR)[0] ?? "";
}

function hasMeaningfulValue(value: unknown): boolean {
  if (value === null || value === undefined || value === "") {
    return false;
  }
  if (Array.isArray(value)) {
    return value.some(hasMeaningfulValue);
  }
  if (typeof value === "object") {
    return Object.values(value as Record<string, unknown>).some(hasMeaningfulValue);
  }
  return true;
}

function moduleGraphNodeData(node: unknown): Record<string, unknown> {
  const schemaNode = schemaNodeFromModuleGraphNode(node);
  if (schemaNode && isRecord(schemaNode.data)) {
    return schemaNode.data;
  }
  if (isRecord(node) && isRecord(node.data)) {
    return node.data;
  }
  return {};
}

function moduleGraphNodeType(node: unknown): string {
  const schemaNode = schemaNodeFromModuleGraphNode(node);
  const data = schemaNode && isRecord(schemaNode.data) ? schemaNode.data : moduleGraphNodeData(node);
  return String(data.node_type || schemaNode?.type || (isRecord(node) ? node.type : "") || "");
}

function referenceOutputConfigScore(graph: { nodes?: unknown[]; edges?: unknown[] } | null | undefined, module?: ModuleCatalogEntryV04 | null) {
  const nodes = Array.isArray(graph?.nodes) ? graph.nodes : [];
  let score = 0;
  for (const node of nodes) {
    if (moduleGraphNodeType(node) !== "reference_output") {
      continue;
    }
    const data = moduleGraphNodeData(node);
    const params = normalizeReferenceOutputParams(cloneRecord(data.params), module?.layer_id);
    const signature = {
      export_scopes: params.export_scopes,
      export_scope: params.export_scope,
      allow_module_level_reference: params.allow_module_level_reference,
      authority_source_type: params.authority_source_type,
      is_core_source: params.is_core_source,
      override_allowed: params.override_allowed,
    };
    score += 1000 + stableJson(signature).length;
  }
  return score;
}

function moduleGraphUserContentScore(graph: { nodes?: unknown[]; edges?: unknown[] } | null | undefined) {
  const nodes = Array.isArray(graph?.nodes) ? graph.nodes : [];
  let score = 0;
  for (const node of nodes) {
    const data = moduleGraphNodeData(node);
    const params = isRecord(data.params) ? data.params : {};
    for (const fieldList of [params.fields, data.fields]) {
      if (!Array.isArray(fieldList)) {
        continue;
      }
      for (const field of fieldList) {
        if (isRecord(field) && hasMeaningfulValue("field_value" in field ? field.field_value : field.value)) {
          score += 1;
        }
      }
    }
  }
  return score;
}

function fieldInputFieldsFromCatalogModule(module: ModuleCatalogEntryV04) {
  const inputNode = moduleGraphNodes(module).find((node) => catalogNodeType(node) === "field_input");
  const params = isRecord(inputNode?.params) ? inputNode.params : {};
  return Array.isArray(params.fields) ? params.fields.filter(isRecord) : [];
}

function fieldValuesById(fields: Record<string, unknown>[]) {
  return new Map(
    fields.map((field) => [
      String(field.field_id || field.field_key || field.key || field.id || ""),
      "field_value" in field ? field.field_value : field.value,
    ])
  );
}

function stableJson(value: unknown) {
  return JSON.stringify(value ?? null);
}

function drCompileValueHasValue(value: unknown) {
  return !(value === null || value === undefined || value === "" || (Array.isArray(value) && value.length === 0) || (isRecord(value) && Object.keys(value).length === 0));
}

function sanitizeDrCompileValue(value: unknown): unknown {
  if (Array.isArray(value)) {
    return value.map(sanitizeDrCompileValue);
  }
  if (!isRecord(value)) {
    return value;
  }
  return Object.fromEntries(
    Object.entries(value)
      .filter(([key, item]) => {
        const keyLower = key.toLowerCase();
        return !drCompileValueHasValue(item) || !DR_COMPILE_FORBIDDEN_KEYS.has(keyLower) || DR_COMPILE_SECRET_REF_KEYS.has(keyLower);
      })
      .map(([key, item]) => [key, sanitizeDrCompileValue(item)])
  );
}

function sanitizeWorkflowForDrCompile(workflow: Workflow): Workflow {
  return sanitizeDrCompileValue(workflow) as Workflow;
}

const IDENTITY_CORE_MODULE_IDS = new Set([
  "module_basic_identity",
  "module_growth_background",
  "module_career_identity",
  "module_existence_mode",
  "module_identity_anchor",
]);
const IDENTITY_REQUIRED_COMPILE_TYPES = ["field_input", "structure_normalize", "validation", "update_rule", "module_output"] as const;

function isIdentityCoreModule(module: ModuleCatalogEntryV04 | null | undefined) {
  return Boolean(module && module.layer_id === "layer_1" && IDENTITY_CORE_MODULE_IDS.has(module.module_id));
}

function moduleGraphCompileNodeType(node: unknown): string {
  const data = moduleGraphNodeData(node);
  const nodeType = moduleGraphNodeType(node);
  const params = isRecord(data.params) ? data.params : {};
  if (nodeType === "text_input" && (data.legacy_node_type === "field_input" || params.mode === "generic_fields")) {
    return "field_input";
  }
  return nodeType;
}

function moduleGraphHasIdentityCompileChain(
  graph: { nodes?: unknown[]; edges?: unknown[] } | null | undefined,
  module: ModuleCatalogEntryV04 | null | undefined
) {
  if (!isIdentityCoreModule(module)) {
    return false;
  }
  const nodeTypes = new Set((Array.isArray(graph?.nodes) ? graph.nodes : []).map(moduleGraphCompileNodeType));
  return IDENTITY_REQUIRED_COMPILE_TYPES.every((nodeType) => nodeTypes.has(nodeType));
}

function moduleGraphStructureScore(
  graph: { nodes?: unknown[]; edges?: unknown[] } | null | undefined,
  module: ModuleCatalogEntryV04 | null | undefined
) {
  if (!module) {
    return 0;
  }
  const catalogTypes = new Set(moduleGraphNodes(module).map(catalogNodeType));
  const candidateTypes = new Set((Array.isArray(graph?.nodes) ? graph.nodes : []).map(moduleGraphCompileNodeType));
  let matches = 0;
  for (const nodeType of catalogTypes) {
    if (candidateTypes.has(nodeType)) {
      matches += 1;
    }
  }
  return matches * 100_000;
}

function referenceInputConfigScore(graph: { nodes?: unknown[]; edges?: unknown[] } | null | undefined) {
  let score = 0;
  for (const node of Array.isArray(graph?.nodes) ? graph.nodes : []) {
    if (moduleGraphNodeType(node) !== "reference_input") {
      continue;
    }
    const data = moduleGraphNodeData(node);
    const params = isRecord(data.params) ? data.params : {};
    const references = Array.isArray(params.references) ? params.references : [];
    score += references.length * 2_000 + stableJson(references).length;
  }
  return score;
}

function moduleGraphChangedFieldScore(
  graph: { nodes?: unknown[]; edges?: unknown[] } | null | undefined,
  module: ModuleCatalogEntryV04 | null | undefined
) {
  if (!module) {
    return moduleGraphUserContentScore(graph);
  }
  const defaults = fieldValuesById(fieldInputFieldsFromCatalogModule(module));
  const nodes = Array.isArray(graph?.nodes) ? graph.nodes : [];
  let changedScore = 0;
  for (const node of nodes) {
    const data = moduleGraphNodeData(node);
    const params = isRecord(data.params) ? data.params : {};
    for (const fieldList of [params.fields, data.fields]) {
      if (!Array.isArray(fieldList)) {
        continue;
      }
      for (const field of fieldList) {
        if (!isRecord(field)) {
          continue;
        }
        const fieldId = String(field.field_id || field.field_key || field.key || field.id || "");
        const value = "field_value" in field ? field.field_value : field.value;
        if (!hasMeaningfulValue(value)) {
          continue;
        }
        if (!defaults.has(fieldId) || stableJson(defaults.get(fieldId)) !== stableJson(value)) {
          changedScore += stableJson(value).length + 1;
        }
      }
    }
  }
  return changedScore + referenceOutputConfigScore(graph, module) + referenceInputConfigScore(graph) + moduleGraphStructureScore(graph, module);
}

function localStorageModuleGraphCandidatesForModule(moduleId: string) {
  if (typeof window === "undefined") {
    return [];
  }
  const candidates: Array<{ id: string; graph?: { nodes?: unknown[]; edges?: unknown[] } | null; backupKey?: string; isBackup?: boolean }> = [];
  for (let index = 0; index < window.localStorage.length; index += 1) {
    const key = window.localStorage.key(index);
    if (key?.startsWith("module_graph_backup_")) {
      const rawId = key.slice("module_graph_backup_".length).replace(/_\d+$/, "");
      if (moduleIdFromInstanceId(rawId) === moduleId) {
        try {
          const parsed = JSON.parse(window.localStorage.getItem(key) ?? "{}") as { nodes?: unknown[]; edges?: unknown[] };
          candidates.push({ id: rawId, graph: parsed, backupKey: key, isBackup: true });
        } catch {
          // Ignore malformed recovery candidates.
        }
      }
      continue;
    }
    if (!key?.startsWith("module_graph_")) {
      continue;
    }
    const id = key.slice("module_graph_".length);
    if (moduleIdFromInstanceId(id) === moduleId) {
      candidates.push({ id, graph: loadModuleGraphState(id), isBackup: false });
    }
  }
  return candidates;
}

function bestModuleGraphId(
  moduleId: string,
  preferredInstanceId: string,
  storeGraphs: Record<string, { nodes?: unknown[]; edges?: unknown[] } | undefined>,
  module?: ModuleCatalogEntryV04 | null
) {
  // A module graph is scoped by layer + module. Never let an identically named
  // legacy graph, backup, or catalog candidate replace this instance at compile time.
  const candidates: Array<{ id: string; graph?: { nodes?: unknown[]; edges?: unknown[] } | null; backupKey?: string; isBackup?: boolean }> = [
    { id: preferredInstanceId, graph: storeGraphs[preferredInstanceId] ?? loadModuleGraphState(preferredInstanceId), isBackup: false }
  ];
  let candidatePool = candidates.some((candidate) => !candidate.isBackup && moduleGraphChangedFieldScore(candidate.graph, module) > 0)
    ? candidates.filter((candidate) => !candidate.isBackup)
    : candidates;
  if (isIdentityCoreModule(module)) {
    const completeCandidates = candidatePool.filter((candidate) => moduleGraphHasIdentityCompileChain(candidate.graph, module));
    if (completeCandidates.length) {
      candidatePool = completeCandidates;
    }
  }
  let bestId = preferredInstanceId;
  let bestScore = -1;
  let bestBackupGraph: { nodes?: unknown[]; edges?: unknown[] } | null | undefined = null;
  for (const candidate of candidatePool) {
    const score = moduleGraphChangedFieldScore(candidate.graph, module);
    if (score > bestScore || (score === bestScore && candidate.id === preferredInstanceId)) {
      bestId = candidate.id;
      bestScore = score;
      bestBackupGraph = candidate.backupKey ? candidate.graph : null;
    }
  }
  if (bestBackupGraph) {
    saveModuleGraphState(bestId, bestBackupGraph.nodes ?? [], bestBackupGraph.edges ?? []);
  }
  return bestId;
}

type PendingModuleAdd = {
  requestId: number;
  moduleId: string;
  nodeType: ModuleNodeType;
};

const nodeTypes = {
  layerContainer: LayerContainerNode,
  workflowNode: WorkflowNodeCard,
  folderGroup: FolderGroupNode,
  layerAssemblyPanel: LayerAssemblyPanelNode
};

const CURVED_EDGE_DEFAULT_OPTIONS = {
  type: "bezier" as const,
  animated: false,
  style: {
    strokeWidth: 2
  }
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value && typeof value === "object" && !Array.isArray(value));
}

const IDENTITY_COMPILE_NODE_ORDER = ["field_input", "structure_normalize", "validation", "update_rule", "module_output"];
const DR_COMPILE_FORBIDDEN_KEYS = new Set([
  "api_key",
  "token",
  "access_token",
  "refresh_token",
  "base_url",
  "credential",
  "credentials",
  "secret",
  "client_secret",
  "provider",
  "provider_binding",
]);
const DR_COMPILE_SECRET_REF_KEYS = new Set(["key_ref", "secret_ref", "credential_ref", "api_key_ref"]);
const REFERENCE_OUTPUT_SCOPES = ["module", "node", "field"] as const;
type ReferenceOutputScope = (typeof REFERENCE_OUTPUT_SCOPES)[number];
const REFERENCE_AUTHORITY_SOURCE_TYPES = [
  "core_fact",
  "derived_config",
  "authoritative_constraint",
  "authoritative_permission",
  "dynamic_state",
  "normal_output",
] as const;
type ReferenceAuthoritySourceType = (typeof REFERENCE_AUTHORITY_SOURCE_TYPES)[number];
const REFERENCE_INPUT_SCOPES = ["module", "node", "field"] as const;
type ReferenceInputScope = (typeof REFERENCE_INPUT_SCOPES)[number];
const REFERENCE_INPUT_TYPES = ["references", "outputs_to", "constrains", "conflicts_with", "overrides_forbidden"] as const;
type ReferenceInputType = (typeof REFERENCE_INPUT_TYPES)[number];
const REFERENCE_INPUT_POINTER_KEYS = new Set([
  "source_layer_id",
  "source_module_id",
  "source_node_id",
  "source_scope",
  "source_field_paths",
  "reference_type",
  "required",
]);
const REFERENCE_INPUT_FORBIDDEN_KEYS = new Set([
  "source_module",
  "source_node",
  "source_content",
  "module_snapshot",
  "node_snapshot",
  "source_module_snapshot",
  "embedded_module",
  "resolved_content",
]);

type ReferenceInputNormalizationStats = {
  beforeCount: number;
  afterCount: number;
  duplicateCount: number;
  strippedCount: number;
  invalidCount: number;
  cycleCount: number;
  invalidSamples: string[];
};

function cloneRecord(value: unknown): Record<string, unknown> {
  return isRecord(value) ? safeClone(value) : {};
}

function referenceAuthoritySourceType(value: unknown, layerId?: string): ReferenceAuthoritySourceType {
  return REFERENCE_AUTHORITY_SOURCE_TYPES.includes(value as ReferenceAuthoritySourceType)
    ? (value as ReferenceAuthoritySourceType)
    : referenceAuthoritySourceTypeForLayer(layerId);
}

function referenceOutputScopes(params: Record<string, unknown>): ReferenceOutputScope[] {
  if (Array.isArray(params.export_scopes)) {
    const scopes = params.export_scopes.filter((scope): scope is ReferenceOutputScope => REFERENCE_OUTPUT_SCOPES.includes(scope as ReferenceOutputScope));
    if (scopes.length) {
      return scopes;
    }
  }
  if (REFERENCE_OUTPUT_SCOPES.includes(params.export_scope as ReferenceOutputScope)) {
    return [params.export_scope as ReferenceOutputScope];
  }
  return [...REFERENCE_OUTPUT_SCOPES];
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

function referenceInputString(value: unknown): string {
  return typeof value === "string" ? value : "";
}

function referenceInputStringArray(value: unknown): string[] {
  return Array.isArray(value) ? value.filter((item): item is string => typeof item === "string" && item.trim().length > 0) : [];
}

function referenceInputScope(value: unknown, fieldPaths: string[]): ReferenceInputScope {
  if (REFERENCE_INPUT_SCOPES.includes(value as ReferenceInputScope)) {
    return value as ReferenceInputScope;
  }
  return fieldPaths.length > 0 ? "field" : "module";
}

function referenceInputType(value: unknown): ReferenceInputType {
  return REFERENCE_INPUT_TYPES.includes(value as ReferenceInputType) ? (value as ReferenceInputType) : "references";
}

function referenceInputHasEmbeddedContent(item: Record<string, unknown>): boolean {
  return Object.keys(item).some((key) => !REFERENCE_INPUT_POINTER_KEYS.has(key) || REFERENCE_INPUT_FORBIDDEN_KEYS.has(key));
}

function normalizeReferenceInputItem(item: unknown): Record<string, unknown> | null {
  if (!isRecord(item)) {
    return null;
  }
  const sourceFieldPaths = referenceInputStringArray(item.source_field_paths);
  return {
    source_layer_id: referenceInputString(item.source_layer_id),
    source_module_id: referenceInputString(item.source_module_id),
    source_node_id: referenceInputString(item.source_node_id),
    source_scope: referenceInputScope(item.source_scope, sourceFieldPaths),
    source_field_paths: sourceFieldPaths,
    reference_type: referenceInputType(item.reference_type),
    required: Boolean(item.required),
  };
}

function normalizeReferenceInputReferences(
  references: unknown,
  stats?: ReferenceInputNormalizationStats,
  seen = new Set<string>()
): Record<string, unknown>[] {
  const rawReferences = Array.isArray(references) ? references : [];
  const normalizedReferences: Record<string, unknown>[] = [];
  if (stats) {
    stats.beforeCount += rawReferences.length;
  }
  for (const rawReference of rawReferences) {
    if (isRecord(rawReference) && referenceInputHasEmbeddedContent(rawReference) && stats) {
      stats.strippedCount += 1;
    }
    const normalized = normalizeReferenceInputItem(rawReference);
    if (!normalized) {
      if (stats) {
        stats.strippedCount += 1;
      }
      continue;
    }
    const signature = stableJson(normalized);
    if (seen.has(signature)) {
      if (stats) {
        stats.duplicateCount += 1;
      }
      continue;
    }
    seen.add(signature);
    normalizedReferences.push(normalized);
  }
  if (stats) {
    stats.afterCount += normalizedReferences.length;
  }
  return normalizedReferences;
}

function normalizeReferenceInputParams(
  params: Record<string, unknown>,
  stats?: ReferenceInputNormalizationStats,
  seen?: Set<string>
): Record<string, unknown> {
  if (!Array.isArray(params.references)) {
    return params;
  }
  return {
    ...params,
    references: normalizeReferenceInputReferences(params.references, stats, seen),
  };
}

function emptyReferenceInputStats(): ReferenceInputNormalizationStats {
  return {
    beforeCount: 0,
    afterCount: 0,
    duplicateCount: 0,
    strippedCount: 0,
    invalidCount: 0,
    cycleCount: 0,
    invalidSamples: [],
  };
}

function addReferenceInvalidSample(stats: ReferenceInputNormalizationStats, message: string) {
  if (stats.invalidSamples.length < 8) {
    stats.invalidSamples.push(message);
  }
}

function moduleGraphNodeIds(module: Record<string, unknown>): Set<string> {
  const graph = isRecord(module.module_graph) ? module.module_graph : {};
  const nodes = Array.isArray(graph.nodes) ? graph.nodes.filter(isRecord) : [];
  const layerId = String(module.layer_id || "");
  const moduleId = String(module.module_id || "");
  const ids = new Set<string>();
  for (const node of nodes) {
    const nodeId = String(node.node_id || "");
    if (nodeId) {
      ids.add(nodeId);
      if (layerId && moduleId) {
        ids.add(`${layerId}${MODULE_INSTANCE_SEPARATOR}${moduleId}${MODULE_INSTANCE_SEPARATOR}${nodeId}`);
      }
    }
    const data = isRecord(node.data) ? node.data : {};
    const catalogNodeId = String(data.catalog_node_id || "");
    if (catalogNodeId) {
      ids.add(catalogNodeId);
      if (layerId && moduleId) {
        ids.add(`${layerId}${MODULE_INSTANCE_SEPARATOR}${moduleId}${MODULE_INSTANCE_SEPARATOR}${catalogNodeId}`);
      }
    }
  }
  return ids;
}

function referenceInputItemsFromModule(module: Record<string, unknown>): Record<string, unknown>[] {
  const graph = isRecord(module.module_graph) ? module.module_graph : {};
  const nodes = Array.isArray(graph.nodes) ? graph.nodes.filter(isRecord) : [];
  const references: Record<string, unknown>[] = [];
  for (const node of nodes) {
    if (String(node.node_type || "") !== "reference_input") {
      continue;
    }
    const params = isRecord(node.params) ? node.params : {};
    if (Array.isArray(params.references)) {
      references.push(...params.references.filter(isRecord));
    }
  }
  return references;
}

function referenceOutputFieldPaths(module: Record<string, unknown>, sourceNodeId: string): Set<string> | null {
  const graph = isRecord(module.module_graph) ? module.module_graph : {};
  const nodes = Array.isArray(graph.nodes) ? graph.nodes.filter(isRecord) : [];
  const layerId = String(module.layer_id || "");
  const moduleId = String(module.module_id || "");
  for (const node of nodes) {
    if (String(node.node_type || "") !== "reference_output") continue;
    const data = isRecord(node.data) ? node.data : {};
    const nodeId = String(node.node_id || "");
    const catalogNodeId = String(data.catalog_node_id || "");
    const aliases = new Set([nodeId, catalogNodeId].filter(Boolean));
    if (layerId && moduleId) {
      if (nodeId) aliases.add(`${layerId}${MODULE_INSTANCE_SEPARATOR}${moduleId}${MODULE_INSTANCE_SEPARATOR}${nodeId}`);
      if (catalogNodeId) aliases.add(`${layerId}${MODULE_INSTANCE_SEPARATOR}${moduleId}${MODULE_INSTANCE_SEPARATOR}${catalogNodeId}`);
    }
    if (!aliases.has(sourceNodeId)) continue;
    const params = isRecord(node.params) ? node.params : isRecord(data.params) ? data.params : {};
    const fields = Array.isArray(params.export_fields) ? params.export_fields.filter(isRecord) : [];
    return new Set(fields.map((field) => String(field.field_path || field.field_key || "")).filter(Boolean));
  }
  return null;
}

function detectReferenceCycles(edges: Array<{ source: string; target: string }>): number {
  const adjacency = new Map<string, string[]>();
  for (const edge of edges) {
    if (!edge.source || !edge.target) {
      continue;
    }
    adjacency.set(edge.source, [...(adjacency.get(edge.source) ?? []), edge.target]);
  }
  const visiting = new Set<string>();
  const visited = new Set<string>();
  let cycles = 0;

  const visit = (moduleId: string) => {
    if (visiting.has(moduleId)) {
      cycles += 1;
      return;
    }
    if (visited.has(moduleId)) {
      return;
    }
    visiting.add(moduleId);
    for (const target of adjacency.get(moduleId) ?? []) {
      visit(target);
    }
    visiting.delete(moduleId);
    visited.add(moduleId);
  };

  for (const moduleId of adjacency.keys()) {
    visit(moduleId);
  }
  return cycles;
}

function validateReferenceInputs(workflow: Workflow, stats: ReferenceInputNormalizationStats) {
  const modules = Array.isArray(workflow.modules) ? workflow.modules.filter(isRecord) : [];
  const layerIds = new Set(modules.map((module) => String(module.layer_id || "")).filter(Boolean));
  const moduleById = new Map<string, Record<string, unknown>>();
  const nodeIdsByModule = new Map<string, Set<string>>();
  for (const module of modules) {
    const moduleId = String(module.module_id || "");
    if (!moduleId) {
      continue;
    }
    moduleById.set(moduleId, module);
    nodeIdsByModule.set(moduleId, moduleGraphNodeIds(module));
  }
  const referenceEdges: Array<{ source: string; target: string }> = [];

  for (const module of modules) {
    const targetModuleId = String(module.module_id || "");
    for (const reference of referenceInputItemsFromModule(module)) {
      let invalidReference = false;
      const invalidate = (message: string) => {
        invalidReference = true;
        addReferenceInvalidSample(stats, message);
      };
      const sourceLayerId = String(reference.source_layer_id || "");
      const sourceModuleId = String(reference.source_module_id || "");
      const sourceNodeId = String(reference.source_node_id || "");
      const sourceScope = String(reference.source_scope || "");
      const sourceFieldPaths = referenceInputStringArray(reference.source_field_paths);
      if (!sourceLayerId || !layerIds.has(sourceLayerId)) {
        invalidate(`${targetModuleId}: missing source_layer_id ${sourceLayerId || "(empty)"}`);
      }
      const sourceModule = moduleById.get(sourceModuleId);
      if (!sourceModule) {
        invalidate(`${targetModuleId}: missing source_module_id ${sourceModuleId || "(empty)"}`);
      } else if (sourceLayerId && String(sourceModule.layer_id || "") !== sourceLayerId) {
        invalidate(`${targetModuleId}: source_module_id ${sourceModuleId} is not in ${sourceLayerId}`);
      }
      if (sourceNodeId) {
        const sourceNodeIds = nodeIdsByModule.get(sourceModuleId);
        if (!sourceNodeIds?.has(sourceNodeId)) {
          invalidate(`${targetModuleId}: missing source_node_id ${sourceNodeId}`);
        }
      } else if (sourceScope === "node" || sourceScope === "field") {
        invalidate(`${targetModuleId}: ${sourceScope} reference missing source_node_id`);
      }
      if (sourceScope === "field" && sourceFieldPaths.length === 0) {
        invalidate(`${targetModuleId}: field reference missing source_field_paths`);
      } else if (sourceScope === "field" && sourceModule && sourceNodeId) {
        const availableFieldPaths = referenceOutputFieldPaths(sourceModule, sourceNodeId);
        if (!availableFieldPaths) {
          invalidate(`${targetModuleId}: field reference source_node_id ${sourceNodeId} is not a reference_output`);
        } else {
          const missingFieldPaths = sourceFieldPaths.filter((fieldPath) => !availableFieldPaths.has(fieldPath));
          if (missingFieldPaths.length) {
            invalidate(`${targetModuleId}: missing source_field_paths ${missingFieldPaths.join(", ")}`);
          }
        }
      }
      if (invalidReference) {
        stats.invalidCount += 1;
      }
      if (sourceModuleId && targetModuleId) {
        referenceEdges.push({ source: sourceModuleId, target: targetModuleId });
      }
    }
  }

  stats.cycleCount = detectReferenceCycles(referenceEdges);
}

function normalizeWorkflowReferenceInputs(workflow: Workflow): { workflow: Workflow; stats: ReferenceInputNormalizationStats } {
  const stats = emptyReferenceInputStats();
  const nextWorkflow = typeof structuredClone === "function"
    ? structuredClone(workflow)
    : JSON.parse(JSON.stringify(workflow)) as Workflow;
  if (Array.isArray(nextWorkflow.modules)) {
    nextWorkflow.modules = nextWorkflow.modules.map((module) => {
      if (!isRecord(module)) {
        return module;
      }
      const graph = isRecord(module.module_graph) ? module.module_graph : null;
      const nodes = Array.isArray(graph?.nodes) ? graph.nodes : null;
      if (!graph || !nodes) {
        return module;
      }
      const seen = new Set<string>();
      return {
        ...module,
        module_graph: {
          ...graph,
          nodes: nodes.map((node) => {
            if (!isRecord(node) || String(node.node_type || "") !== "reference_input") {
              return node;
            }
            return {
              ...node,
              params: normalizeReferenceInputParams(cloneRecord(node.params), stats, seen),
            };
          }),
        },
      };
    }) as Workflow["modules"];
  }
  validateReferenceInputs(nextWorkflow, stats);
  return { workflow: nextWorkflow, stats };
}

function cloneArray(value: unknown): unknown[] {
  return Array.isArray(value) ? safeClone(value) : [];
}

function readableNodeName(value: string) {
  return value
    .split("_")
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function moduleGraphNodes(module: ModuleCatalogEntryV04): Record<string, unknown>[] {
  const graph = isRecord(module.module_graph) ? module.module_graph : {};
  const nodes = graph.nodes;
  return Array.isArray(nodes) ? nodes.filter(isRecord) : [];
}

function moduleGraphOutputKey(module: ModuleCatalogEntryV04): string {
  const graph = isRecord(module.module_graph) ? module.module_graph : {};
  const outputs = isRecord(module.outputs) ? module.outputs : {};
  return String(graph.output_key || outputs.module_output || "");
}

function catalogNodeType(node: Record<string, unknown>) {
  return String(node.node_type || node.type || "transform");
}

function moduleRecordHasFieldInput(module: Record<string, unknown>) {
  const graph = isRecord(module.module_graph) ? module.module_graph : {};
  const nodes = Array.isArray(graph.nodes) ? graph.nodes.filter(isRecord) : [];
  return nodes.some((node) => catalogNodeType(node) === "field_input");
}

function withoutLegacyModuleOutputFallback(module: Record<string, unknown>) {
  if (moduleRecordHasFieldInput(module)) {
    return module;
  }
  const outputs = isRecord(module.outputs) ? { ...module.outputs } : {};
  if (!outputs.module_output) {
    return module;
  }
  delete outputs.module_output;
  return {
    ...module,
    outputs,
  };
}

function catalogNodeId(node: Record<string, unknown>, index: number) {
  return String(node.node_id || node.id || `${catalogNodeType(node)}_${index + 1}`);
}

function flowNodeId(instanceId: string, catalogId: string) {
  return `${instanceId}${MODULE_INSTANCE_SEPARATOR}${catalogId}`;
}

function buildCatalogModuleSeed(module: ModuleCatalogEntryV04, instanceId: string): { nodes: WorkflowNode[]; edges: WorkflowEdge[] } {
  const catalogNodes = moduleGraphNodes(module);
  const idByCatalogId = new Map<string, string>();
  const nodes = catalogNodes.map((node, index) => {
    const originalNodeId = catalogNodeId(node, index);
    const nodeType = catalogNodeType(node);
    const nodeId = flowNodeId(instanceId, originalNodeId);
    idByCatalogId.set(originalNodeId, nodeId);
    const params = cloneRecord(node.params);
    const fields = cloneArray(params.fields);
    const outputs = cloneRecord(node.outputs);
    const metadata = cloneRecord(node.metadata);
    const i18nKeys = cloneRecord(node.i18n_keys);
    const catalogPosition = isRecord(node.position) ? node.position : {};
    const positionX = typeof catalogPosition.x === "number" ? catalogPosition.x : 120 + index * 360;
    const positionY = typeof catalogPosition.y === "number" ? catalogPosition.y : 100;
    return ensurePorts({
      node_id: nodeId,
      type: nodeType,
      category: "compile_time",
      title_key: String(i18nKeys.name || `node.type.${nodeType}`),
      title_fallback: readableNodeName(originalNodeId),
      position: { x: positionX, y: positionY },
      lock_level: "editable",
      locale: null,
      data: {
        parent_module: instanceId,
        catalog_preconfigured: true,
        module_instance_id: instanceId,
        catalog_module_id: module.module_id,
        catalog_node_id: originalNodeId,
        node_type: nodeType,
        params,
        fields,
        outputs,
        metadata,
        i18n_keys: i18nKeys,
      },
      input_schema: [],
      output_schema: [],
      ports: {
        inputs: index === 0 ? [] : [{ port_id: "p_in", name: "in", direction: "in" }],
        outputs: index === catalogNodes.length - 1 ? [] : [{ port_id: "p_out", name: "out", direction: "out" }],
      },
      validation: null,
      layer_id: module.layer_id,
      module_id: module.module_id,
      i18n_keys: Object.fromEntries(Object.entries(i18nKeys).map(([key, value]) => [key, String(value)])),
      collapsed_sections: nodeType === "reference_input" || nodeType === "reference_output" ? ["core", "advanced", "runtime"] : ["advanced", "runtime"],
    } as WorkflowNode);
  });

  const graph = isRecord(module.module_graph) ? module.module_graph : {};
  const catalogEdges = Array.isArray(graph.edges) ? graph.edges.filter(isRecord) : [];
  const edges =
    catalogEdges.length > 0
      ? catalogEdges.map((edge, index) => {
          const sourceRaw = String(edge.source || edge.source_node_id || "");
          const targetRaw = String(edge.target || edge.target_node_id || "");
          const source = idByCatalogId.get(sourceRaw) || sourceRaw;
          const target = idByCatalogId.get(targetRaw) || targetRaw;
          const edgeId = String(edge.edge_id || edge.id || `${source}_to_${target}_${index + 1}`);
          return {
            edge_id: edgeId,
            id: edgeId,
            source,
            source_port: String(edge.source_port || edge.source_output || "p_out"),
            sourceHandle: String(edge.source_port || edge.source_output || "p_out"),
            target,
            target_port: String(edge.target_port || edge.target_input || "p_in"),
            targetHandle: String(edge.target_port || edge.target_input || "p_in"),
            type: "smoothstep",
          } as WorkflowEdge & Edge;
        })
      : IDENTITY_COMPILE_NODE_ORDER.slice(0, -1).flatMap((nodeType, index) => {
          const sourceNode = nodes.find((candidate) => candidate.data?.node_type === nodeType);
          const targetNode = nodes.find((candidate) => candidate.data?.node_type === IDENTITY_COMPILE_NODE_ORDER[index + 1]);
          if (!sourceNode || !targetNode) {
            return [];
          }
          const edgeId = `${sourceNode.node_id}_to_${targetNode.node_id}`;
          return [
            {
              edge_id: edgeId,
              id: edgeId,
              source: sourceNode.node_id,
              source_port: "p_out",
              sourceHandle: "p_out",
              target: targetNode.node_id,
              target_port: "p_in",
              targetHandle: "p_in",
              type: "smoothstep",
            } as WorkflowEdge & Edge,
          ];
        });

  return { nodes, edges };
}

function schemaNodeFromModuleGraphNode(value: unknown): WorkflowNode | null {
  if (!isRecord(value)) {
    return null;
  }
  const data = isRecord(value.data) ? value.data : {};
  if (isRecord(data.schemaNode)) {
    return data.schemaNode as unknown as WorkflowNode;
  }
  if (typeof value.node_id === "string" && typeof value.type === "string") {
    return value as unknown as WorkflowNode;
  }
  return null;
}

function fieldInputFields(schemaNode: WorkflowNode): Record<string, unknown>[] {
  const data = isRecord(schemaNode.data) ? schemaNode.data : {};
  if (Array.isArray(data.fields)) {
    return safeClone(data.fields.filter(isRecord));
  }
  const params = isRecord(data.params) ? data.params : {};
  return Array.isArray(params.fields) ? safeClone(params.fields.filter(isRecord)) : [];
}

function fieldsFromNodeData(data: Record<string, unknown>): Record<string, unknown>[] {
  if (Array.isArray(data.fields)) {
    return data.fields.filter(isRecord);
  }
  const params = isRecord(data.params) ? data.params : {};
  return Array.isArray(params.fields) ? params.fields.filter(isRecord) : [];
}

function paramsFromNodeData(data: Record<string, unknown>): Record<string, unknown> {
  return isRecord(data.params) ? data.params : {};
}

function compileTimeFieldKey(field: Record<string, unknown>, index: number) {
  return String(field.field_id || field.key || field.name || field.id || `field_${index + 1}`);
}

function compileTimeFieldMatches(field: Record<string, unknown>, index: number, key: string) {
  const candidates = [
    compileTimeFieldKey(field, index),
    field.field_id,
    field.key,
    field.name,
    field.id,
  ].map((value) => String(value || ""));
  return candidates.includes(key);
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

const LEGACY_MEMORY_ROUTER_ALLOWED_MEMORY_TYPES = ["short_term_memory", "profile_memory", "preference_memory", "interaction_log"];
const MEMORY_ROUTER_ALLOWED_MEMORY_TYPES = ["short_term_memory", "preference_memory", "event_memory", "relationship_memory", "interaction_log"];
const LEGACY_MEMORY_ROUTER_OPERATIONS = ["read", "write", "view", "clear"];
const MEMORY_ROUTER_CANONICAL_OPERATIONS = ["read", "write", "update", "delete"];
const MEMORY_ROUTER_ACCEPTED_OPERATIONS = [...MEMORY_ROUTER_CANONICAL_OPERATIONS, "view", "clear"];
const MEMORY_ROUTER_OPERATION_ALIASES = { view: "read", clear: "delete" };
const LEGACY_MEMORY_ROUTER_NORMALIZE_RULES = ["classify_operation", "allow_read_write_view_clear", "reject_unknown_operation"];
const MEMORY_ROUTER_NORMALIZE_RULES = ["normalize_operation_alias", "classify_operation", "allow_declared_operations_only", "reject_unknown_operation"];

function hasExactMemoryTypeList(value: unknown, expected: string[]) {
  return Array.isArray(value) && value.length === expected.length && value.every((item, index) => item === expected[index]);
}

function normalizeMemoryRouterTypeResolverParams(
  params: Record<string, unknown>,
  nodeId: string,
  moduleId: string
) {
  if (moduleId !== "memory_provider_router" || nodeId !== "memory_router_type_resolver") {
    return params;
  }
  if (!hasExactMemoryTypeList(params.allowed_memory_types, LEGACY_MEMORY_ROUTER_ALLOWED_MEMORY_TYPES)) {
    return params;
  }
  return {
    ...params,
    allowed_memory_types: [...MEMORY_ROUTER_ALLOWED_MEMORY_TYPES],
  };
}

function normalizeMemoryRouterOperationParams(
  params: Record<string, unknown>,
  nodeId: string,
  moduleId: string
) {
  if (moduleId !== "memory_provider_router") {
    return params;
  }
  if (nodeId === "memory_router_request_input") {
    const requestSchema = isRecord(params.request_schema) ? { ...params.request_schema } : null;
    if (!requestSchema || !hasExactMemoryTypeList(requestSchema.operations, LEGACY_MEMORY_ROUTER_OPERATIONS)) {
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
  if (nodeId !== "memory_router_operation_classifier") {
    return params;
  }
  const oldOperations = hasExactMemoryTypeList(params.operations, LEGACY_MEMORY_ROUTER_OPERATIONS);
  const oldRules = hasExactMemoryTypeList(params.normalize_rules, LEGACY_MEMORY_ROUTER_NORMALIZE_RULES);
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

function legacyFieldInputFieldsForCompile(data: Record<string, unknown>, params: Record<string, unknown>) {
  const genericFields = Array.isArray(params.fields) ? params.fields.filter(isRecord) : [];
  const genericValues = genericFieldValueByKey(genericFields);
  const legacyFields = Array.isArray(params.legacy_data_fields)
    ? params.legacy_data_fields.filter(isRecord)
    : Array.isArray(data.fields)
      ? data.fields.filter(isRecord)
      : [];

  if (legacyFields.length) {
    return safeClone(legacyFields).map((field, index) => {
      const fieldId = String(field.field_id || field.field_key || field.key || field.id || `field_${index + 1}`);
      if (!genericValues.has(fieldId)) {
        return field;
      }
      return {
        ...field,
        value: genericValues.get(fieldId),
      };
    });
  }

  return genericFields.map((field, index) => {
    const fieldId = String(field.field_key || field.field_id || field.key || field.id || `field_${index + 1}`);
    return {
      field_id: fieldId,
      value: "field_value" in field ? field.field_value : field.value,
      required: false,
      edit_scope: "user_editable",
      update_level: "versioned_core",
      requires_recompile: true,
      i18n_keys: {
        label: `field.identity.${fieldId}.label`,
        placeholder: `field.identity.${fieldId}.placeholder`,
        help: `field.identity.${fieldId}.help`,
      },
    };
  });
}

function updateFieldValue(fields: Record<string, unknown>[], index: number, value: unknown) {
  return fields.map((field, fieldIndex) => (fieldIndex === index ? { ...field, value } : field));
}

function compileNodeRecord(schemaNode: WorkflowNode, module: ModuleCatalogEntryV04): Record<string, unknown> {
  const data = isRecord(schemaNode.data) ? schemaNode.data : {};
  const nodeType = String(data.node_type || schemaNode.type);
  let params = cloneRecord(data.params);
  params = syncPrimaryLanguageCompatibilityFields(params);
  const catalogNodeId = String(data.catalog_node_id || schemaNode.node_id);
  params = normalizeMemoryRouterTypeResolverParams(params, catalogNodeId, module.module_id);
  params = normalizeMemoryRouterOperationParams(params, catalogNodeId, module.module_id);
  const legacyNodeType = typeof data.legacy_node_type === "string" ? data.legacy_node_type : "";
  const compileNodeType = nodeType === "text_input" && legacyNodeType ? legacyNodeType : nodeType;
  const compileLayerId =
    (typeof schemaNode.layer_id === "string" && schemaNode.layer_id) ||
    (typeof data.layer_id === "string" && data.layer_id) ||
    layerIdFromInstanceId(String(data.parent_module || "")) ||
    module.layer_id;
  if (nodeType === "text_input" && legacyNodeType && Array.isArray(params.fields)) {
    params.fields = legacyFieldInputFieldsForCompile(data, params);
  } else if (compileNodeType === "field_input" || compileNodeType === "text_config") {
    params.fields = fieldInputFields(schemaNode);
  }
  if (compileNodeType === "reference_output") {
    params = normalizeReferenceOutputParams(params, compileLayerId);
  }
  if (compileNodeType === "reference_input") {
    params = normalizeReferenceInputParams(params);
  }
  return {
    node_id: catalogNodeId,
    node_type: compileNodeType,
    module_id: module.module_id,
    layer_id: compileLayerId,
    params,
    i18n_keys: cloneRecord(data.i18n_keys || schemaNode.i18n_keys),
    outputs: cloneRecord(data.outputs),
    metadata: cloneRecord(data.metadata),
  };
}

function compileEdgesFromModuleGraph(
  module: ModuleCatalogEntryV04,
  nodes: unknown[],
  edges: unknown[]
): Record<string, unknown>[] {
  const idMap = new Map<string, string>();
  const nodeIds = new Set<string>();
  for (const graphNode of nodes) {
    const schemaNode = schemaNodeFromModuleGraphNode(graphNode);
    if (!schemaNode) {
      continue;
    }
    const data = isRecord(schemaNode.data) ? schemaNode.data : {};
    idMap.set(schemaNode.node_id, String(data.catalog_node_id || schemaNode.node_id));
    nodeIds.add(schemaNode.node_id);
    if (isRecord(graphNode) && typeof graphNode.id === "string") {
      nodeIds.add(graphNode.id);
    }
  }
  const integrity = filterDanglingModuleGraphEdges(nodeIds, edges);
  if (integrity.pruned.length && process.env.NODE_ENV !== "production") {
    for (const edge of integrity.pruned) {
      console.warn("[MODULE_GRAPH_EDGE_PRUNED]", {
        layer_id: module.layer_id,
        module_id: module.module_id,
        source: edge.source,
        target: edge.target,
      });
    }
  }
  return integrity.edges.filter(isRecord).map((edge, index) => {
    const source = String(edge.source || "");
    const target = String(edge.target || "");
    return {
      edge_id: String(edge.edge_id || edge.id || `module_edge_${index + 1}`),
      source: idMap.get(source) || source,
      source_port: String(edge.source_port || edge.sourceHandle || "p_out"),
      target: idMap.get(target) || target,
      target_port: String(edge.target_port || edge.targetHandle || "p_in"),
    };
  });
}

const LAYER1_IDENTITY_RULE_SYNC_MODULE_IDS = new Set([
  "module_growth_background",
  "module_career_identity",
  "module_existence_mode",
  "module_identity_anchor",
]);

function compileFieldId(field: Record<string, unknown>, index: number) {
  return String(field.field_id || field.field_key || field.key || field.id || `field_${index + 1}`);
}

function compileNodeFields(node: Record<string, unknown> | undefined) {
  const params = isRecord(node?.params) ? node.params : {};
  return Array.isArray(params.fields) ? params.fields.filter(isRecord) : [];
}

function currentModuleFieldRecords(compiledNodes: Record<string, unknown>[]) {
  const fieldInput = compiledNodes.find((node) => node.node_type === "field_input");
  const genericTextInput = compiledNodes.find((node) => {
    const params = isRecord(node.params) ? node.params : {};
    return node.node_type === "text_input" && params.mode === "generic_fields";
  });
  return compileNodeFields(fieldInput || genericTextInput);
}

function syncLayer1ValidationAndUpdateRules(module: ModuleCatalogEntryV04, compiledNodes: Record<string, unknown>[]) {
  if (module.layer_id !== "layer_1" || !LAYER1_IDENTITY_RULE_SYNC_MODULE_IDS.has(module.module_id)) {
    return compiledNodes;
  }
  const fields = currentModuleFieldRecords(compiledNodes);
  const fieldIds = fields.map(compileFieldId).filter(Boolean);
  if (!fieldIds.length) {
    return compiledNodes;
  }
  return compiledNodes.map((node) => {
    if (node.node_type !== "validation" && node.node_type !== "update_rule") {
      return node;
    }
    const params = isRecord(node.params) ? { ...node.params } : {};
    if (node.node_type === "validation") {
      params.required_fields = fields
        .filter((field) => field.required !== false)
        .map(compileFieldId)
        .filter(Boolean);
      return { ...node, params };
    }
    const existingRules = Array.isArray(params.update_rules) ? params.update_rules.filter(isRecord) : [];
    const rulesByFieldId = new Map(existingRules.map((rule) => [String(rule.field_id || ""), rule]));
    params.update_rules = fields.map((field, index) => {
      const fieldId = compileFieldId(field, index);
      const existing = rulesByFieldId.get(fieldId) || existingRules[index] || {};
      return {
        ...existing,
        field_id: fieldId,
        edit_scope: existing.edit_scope ?? field.edit_scope,
        update_level: existing.update_level ?? field.update_level,
        requires_recompile: typeof existing.requires_recompile === "boolean" ? existing.requires_recompile : Boolean(field.requires_recompile),
      };
    });
    return { ...node, params };
  });
}

function moduleWithCompiledGraph(module: ModuleCatalogEntryV04, graphNodes: unknown[], graphEdges: unknown[]): Record<string, unknown> {
  const compiledNodes = syncLayer1ValidationAndUpdateRules(module, graphNodes
    .map((node) => {
      const schemaNode = schemaNodeFromModuleGraphNode(node);
      return schemaNode ? compileNodeRecord(schemaNode, module) : null;
    })
    .filter(isRecord));
  const outputKey = moduleGraphOutputKey(module);
  const fields = currentModuleFieldRecords(compiledNodes);
  const fieldValues = Object.fromEntries(fields.map((field, index) => [compileFieldId(field, index), "value" in field ? field.value : field.field_value]).filter(([key]) => key));
  const hasFieldInput = fields.length > 0;
  let outputValue: Record<string, unknown> | null = null;
  for (const node of compiledNodes) {
    if (node.node_type !== "module_output" || !outputKey) {
      continue;
    }
    const outputs = isRecord(node.outputs) ? { ...node.outputs } : {};
    const existing = isRecord(outputs[outputKey]) ? outputs[outputKey] : {};
    outputValue = {
      ...existing,
      output_key: outputKey,
      compile_time_only: true,
    };
    if (fields.length > 0) {
      outputValue.fields = fieldValues;
    }
    outputs[outputKey] = outputValue;
    outputs.module_output = outputKey;
    node.outputs = outputs;
  }
  const outputs = cloneRecord(module.outputs);
  if (outputKey && outputValue) {
    outputs[outputKey] = outputValue;
    if (hasFieldInput) {
      outputs.module_output = outputKey;
    } else {
      delete outputs.module_output;
    }
  }
  return withoutLegacyModuleOutputFallback({
    ...safeClone(module),
    outputs,
    module_graph: {
      ...cloneRecord(module.module_graph),
      nodes: compiledNodes,
      edges: compileEdgesFromModuleGraph(module, graphNodes, graphEdges),
    },
  });
}

function extractResidentInstance(value: unknown): ResidentInstance | null {
  if (!isRecord(value)) {
    return null;
  }
  const direct = value.resident_instance;
  if (isRecord(direct)) {
    return direct as ResidentInstance;
  }
  return null;
}

function clampPreviewNumber(value: unknown, fallback: number) {
  return typeof value === "number" && Number.isFinite(value) ? value : fallback;
}

function dataString(node: WorkflowNode, key: string, fallback = "") {
  const value = node.data?.[key];
  return value === null || value === undefined || value === "" ? fallback : String(value);
}

function dataNumber(node: WorkflowNode, key: string) {
  const value = node.data?.[key];
  const numberValue = typeof value === "number" ? value : Number(value);
  return Number.isFinite(numberValue) ? numberValue : null;
}

function getLayerOrder(node: WorkflowNode) {
  return dataNumber(node, "layer_order");
}

function computeLayerHeight(_layer: CatalogLayerInput, moduleCount: number) {
  const contentCount = moduleCount;
  const contentHeight = contentCount * LAYER_NODE_ROW_HEIGHT + LAYER_STACK_PADDING;
  return Math.max(FOLDER_GROUP_HEIGHT, contentHeight);
}

function computeLayerStackFrame(layer: CatalogLayerInput, moduleCount: number, y: number): LayerStackFrame {
  return {
    x: FOLDER_GROUP_X,
    y,
    width: FOLDER_GROUP_WIDTH,
    height: computeLayerHeight(layer, moduleCount)
  };
}

const LayerStackLayoutEngine = {
  computeHeight: computeLayerHeight,
  computeFrame: computeLayerStackFrame,
  computeFrames(layers: CatalogLayerInput[], moduleCounts: Map<string, number>) {
    let y = 0;
    let previousBottom = -Infinity;
    const frames = new Map<string, LayerStackFrame>();
    for (const layer of layers) {
      const moduleCount = moduleCounts.get(layer.layer_id) ?? 0;
      const height = this.computeHeight(layer, moduleCount);
      const minY = previousBottom === -Infinity ? y : previousBottom + LAYER_STACK_GAP;
      if (y < minY) {
        y = minY;
      }
      const frame = this.computeFrame(layer, moduleCount, y);
      frames.set(layer.layer_id, frame);
      previousBottom = y + height;
      y = previousBottom + LAYER_STACK_GAP;
    }
    return frames;
  },
  computeTrunkPosition(frame: LayerStackFrame) {
    return {
      x: TRUNK_LAYER_X,
      y: frame.y + Math.max(0, (frame.height - TRUNK_LAYER_HEIGHT) / 2)
    };
  }
};

function computeLayerStackFrames(layers: CatalogLayerInput[], moduleCounts: Map<string, number>) {
  return LayerStackLayoutEngine.computeFrames(layers, moduleCounts);
}

// Main-canvas layout must be stable regardless of how many modules are attached to a
// layer. Passing this empty map makes every layer fall back to FOLDER_GROUP_HEIGHT, so
// container x/y positions are fixed by canonical layer order alone. children_count is
// shown via getLayerCatalogDisplayFields, independent of this layout.
const LAYOUT_MODULE_COUNTS: Map<string, number> = new Map();

function nodeLayerKey(node: WorkflowNode, layers: WorkflowNode[]) {
  const explicit =
    dataStringValue(node, "layer_id") ??
    dataStringValue(node, "layerId") ??
    dataStringValue(node, "parent_layer") ??
    dataStringValue(node, "parentLayer");
  if (explicit) {
    return explicit;
  }
  const layerIndex = inferNodeLayerIndex(node, layers);
  return layerIndex === null ? null : `layer_${layerIndex}`;
}

function buildFolderFlowNode({
  layer,
  moduleCatalog,
  frame,
  subnodes,
  attachedModules,
  attachedModuleIds,
  attachedModuleColors,
  focusedModuleId,
  selectedLayerModuleKeys,
  moduleNames,
  uiColors,
  onSelectNode,
  onPreviewNode,
  onFocusNode,
  onDropModule,
  onSelectDroppedModule,
  onOpenDroppedModule,
  onRemoveModule,
  onColorModule,
  onOpenModuleFocus,
  onContainerContextMenu,
  onDroppedModuleContextMenu,
  onModuleContextMenu
}: {
  layer: CatalogLayerInput;
  moduleCatalog: ModuleCatalogResponseV04;
  frame: LayerStackFrame;
  subnodes: WorkflowNode[];
  attachedModules: ModuleCatalogEntryV04[];
  attachedModuleIds: string[];
  attachedModuleColors: Record<string, string>;
  focusedModuleId: string | null;
  selectedLayerModuleKeys: Set<string>;
  moduleNames: Record<string, string>;
  uiColors: Record<string, string>;
  onSelectNode: (node: WorkflowNode) => void;
  onPreviewNode: (node: WorkflowNode) => void;
  onFocusNode: (node: WorkflowNode) => void;
  onDropModule: (moduleId: string) => void;
  onSelectDroppedModule: (moduleId: string, multi: boolean) => void;
  onOpenDroppedModule: (moduleId: string) => void;
  onRemoveModule: (moduleId: string) => void;
  onColorModule: (moduleId: string, color: string) => void;
  onOpenModuleFocus: () => void;
  onContainerContextMenu: (event: ReactMouseEvent) => void;
  onDroppedModuleContextMenu: (event: ReactMouseEvent, moduleId: string) => void;
  onModuleContextMenu: (event: ReactMouseEvent, node: WorkflowNode) => void;
}) {
  const layerId = layer.layer_id;
  return {
    id: `ui-folder-${layerId}`,
    type: "folderGroup",
    position: { x: frame.x, y: frame.y },
    style: { width: frame.width, height: frame.height },
    draggable: false,
    selectable: true,
    data: {
      layer,
      moduleCatalog,
      subnodes,
      modules: attachedModules,
      focusedModuleId,
      selectedModuleKeys: attachedModuleIds.filter((id) => selectedLayerModuleKeys.has(`${layerId}:${id}`)),
      moduleNames,
      moduleColors: attachedModuleColors,
      uiColor: uiColors[`ui-folder-${layerId}`] ?? uiColors[layerId] ?? "",
      onSelectNode,
      onPreviewNode,
      onFocusNode,
      onDropModule,
      onSelectDroppedModule,
      onOpenDroppedModule,
      onRemoveModule,
      onColorModule,
      onOpenModuleFocus,
      onContainerContextMenu,
      onDroppedModuleContextMenu,
      onModuleContextMenu
    } satisfies FolderGroupNodeData
  } satisfies Node;
}

function buildLayerContainerFlowNode({
  layer,
  moduleCatalog,
  frame,
  uiTags,
  uiGroups,
  uiColors,
  onColor,
  onOpenAssembly,
  t
}: {
  layer: CatalogLayerInput;
  moduleCatalog: ModuleCatalogResponseV04;
  frame: LayerStackFrame;
  uiTags: Record<string, string[]>;
  uiGroups: Record<string, string>;
  uiColors: Record<string, string>;
  onColor?: (layerId: string, color: string) => void;
  onOpenAssembly?: (layer: CatalogLayerInput) => void;
  t: (key: string, fallback?: string) => string;
}) {
  const layerId = layer.layer_id;
  const catalogLayerName = translate(useCanvasStore.getState().language, `layer.${layer.layer_id}`, layer.layer_name);
  const displayFields = getLayerCatalogDisplayFields(layer, moduleCatalog, t);
  const schemaNode = {
    node_id: layer.layer_id,
    type: "layer_container",
    category: "container",
    title_key: `layer.${layer.layer_id}`,
    title_fallback: catalogLayerName,
    position: LayerStackLayoutEngine.computeTrunkPosition(frame),
    lock_level: displayFields.lock_level,
    locale: null,
    data: {
      layer_order: layer.layer_order,
      layer_name: catalogLayerName,
      status: displayFields.status,
      version: displayFields.version,
      children_count: displayFields.children_count,
      module_tier: displayFields.module_tier,
      ui_color: uiColors[layerId] ?? "",
      validation: { status: displayFields.review }
    },
    ports: {
      inputs: [{ port_id: "p_left_in", name: "in", direction: "in" }],
      outputs: [{ port_id: "p_out", name: "out", direction: "out" }]
    },
    validation: { status: displayFields.review }
  } as WorkflowNode;
  return {
    id: layerId,
    type: "layerContainer",
    position: LayerStackLayoutEngine.computeTrunkPosition(frame),
    style: { width: TRUNK_LAYER_WIDTH, height: TRUNK_LAYER_HEIGHT },
    draggable: true,
    selectable: true,
    data: {
      schemaNode,
      layer_id: layerId,
      viewLabel: catalogLayerName,
      viewIndex: layer.layer_order,
      groupLabel: displayFields.groupLabel,
      uiTags: uiTags[layerId] ?? [],
      uiGroup: uiGroups[layerId] ?? "",
      uiColor: uiColors[layerId] ?? "",
      onColor: onColor ? (color: string) => onColor(layerId, color) : undefined,
      onOpenAssembly: onOpenAssembly ? () => onOpenAssembly(layer) : undefined,
      t
    }
  } satisfies Node;
}

function renderLayer(input: Parameters<typeof buildLayerContainerFlowNode>[0]) {
  return buildLayerContainerFlowNode(input);
}

function renderSlotHint(content: ReactNode) {
  return content;
}

function renderEngineBadge(content: ReactNode) {
  return content;
}

function buildFolderToLayerEdge(layer: CatalogLayerInput) {
  return {
    id: `edge-ui-folder-${layer.layer_id}`,
    source: `ui-folder-${layer.layer_id}`,
    target: layer.layer_id,
    sourceHandle: "p_out",
    targetHandle: "p_left_in",
    type: "bezier",
    selectable: false,
    deletable: false,
    focusable: false,
    animated: false,
    style: { stroke: "rgba(110, 231, 183, 0.95)", strokeWidth: 2.2 }
  } satisfies Edge;
}

function buildLayerSpineEdge(layer: CatalogLayerInput, nextLayer: CatalogLayerInput) {
  return {
    id: `edge-layer-spine-${layer.layer_id}-${nextLayer.layer_id}`,
    source: layer.layer_id,
    target: nextLayer.layer_id,
    sourceHandle: "p_out",
    targetHandle: "p_in",
    type: "bezier",
    selectable: false,
    deletable: false,
    focusable: false,
    animated: false,
    style: { stroke: "rgba(148, 163, 184, 0.74)", strokeWidth: 2.1 }
  } satisfies Edge;
}

function checkCanvasStructureConsistency(layers: CatalogLayerInput[], nodes: WorkflowNode[], frames: Map<string, LayerStackFrame>, moduleCatalog: ModuleCatalogResponseV04) {
  const warnings: string[] = [];
  
  // NODE F: CRITICAL 13-layer check (should never fail if earlier validation passed)
  if (layers.length !== 13) {
    const critical = `[NODE-F-CRITICAL] canvas rendering 13-layer check FAILED: ${layers.length} layers`;
    console.error(critical);
    warnings.push(critical);
  }

  const ordered = layers.slice().sort((a, b) => catalogLayerOrder(a) - catalogLayerOrder(b));
  ordered.forEach((layer, index) => {
    const expectedOrder = index + 1;
    if (layer.layer_order !== expectedOrder) {
      warnings.push(`layer order mismatch at ${layer.layer_id}: expected ${expectedOrder}, received ${layer.layer_order}`);
    }
  });

  const layerIds = new Set(layers.map((layer) => layer.layer_id));
  const layerNodes = layers.map((layer) => catalogLayerToWorkflowNode(layer, moduleCatalog));
  for (const node of nodes) {
    if (node.type === "layer_container") {
      continue;
    }
    const parentLayer = nodeLayerKey(node, layerNodes);
    if (parentLayer && !layerIds.has(parentLayer)) {
      warnings.push(`node ${node.node_id} references missing layer ${parentLayer}`);
    }
  }

  for (let index = 1; index < ordered.length; index += 1) {
    const previous = frames.get(ordered[index - 1].layer_id);
    const current = frames.get(ordered[index].layer_id);
    if (!previous || !current) {
      warnings.push(`missing layout frame for ${!previous ? ordered[index - 1].layer_id : ordered[index].layer_id}`);
      continue;
    }
    if (current.y < previous.y + previous.height) {
      warnings.push(`layout overlap: ${ordered[index - 1].layer_id} -> ${ordered[index].layer_id}`);
    }
  }

  return warnings;
}

function getNodeTypeLabel(type: string, t: (key: string, fallback?: string) => string) {
  // Prefer the i18n entry (zh/en) over the registry's English label so node
  // names localize correctly; fall back to the registry label, then the type.
  return t(`node.type.${type}`, getNodeDefinition(type)?.label ?? type);
}

function getNodeStatusLabel(type: string, t: (key: string, fallback?: string) => string) {
  const status = getNodeStatus(type);
  return status ? t(`node.status.${status}`, status) : null;
}

function buildNodeLibraryCategories(entries: NodeDefinition[]): NodeLibraryCategory[] {
  const groups = new Map<string, NodeLibraryCategory>();
  for (const entry of entries) {
    const id = entry.category || "other";
    if (!groups.has(id)) {
      groups.set(id, {
        id,
        labelKey: `lib.category.${id}`,
        labelFallback: id.replace(/_/g, " "),
        nodes: []
      });
    }
    groups.get(id)?.nodes.push(entry.type as ModuleNodeType);
  }
  return [...groups.values()].map((group) => ({
    ...group,
    nodes: group.nodes.sort((a, b) => getNodeTypeLabel(a, (_key, fallback) => fallback ?? a).localeCompare(getNodeTypeLabel(b, (_key, fallback) => fallback ?? b)))
  }));
}

function shouldUseNativeContextMenu(target: EventTarget | null) {
  return target instanceof HTMLElement && Boolean(target.closest("input, textarea, select, [contenteditable='true']"));
}

function shouldSkipCanvasContextCapture(target: EventTarget | null) {
  return (
    target instanceof HTMLElement &&
    Boolean(target.closest("input, textarea, select, button, a, [contenteditable='true'], [role='button'], .react-flow__controls, .react-flow__minimap"))
  );
}

function shouldLetReactFlowElementContextMenuHandle(target: EventTarget | null) {
  return target instanceof HTMLElement && Boolean(target.closest(".react-flow__node, .react-flow__edge"));
}

function makeContextMenu(event: ContextMenuEvent, items: CanvasContextMenuItem[]): CanvasContextMenuState | null {
  if (shouldUseNativeContextMenu(event.target)) {
    return null;
  }
  event.preventDefault();
  event.stopPropagation();
  const menuWidth = 220;
  const menuHeight = Math.min(360, 38 * items.length + 14);
  return {
    x: Math.min(event.clientX, window.innerWidth - menuWidth - 8),
    y: Math.min(event.clientY, window.innerHeight - menuHeight - 8),
    items
  };
}

function cloneCanvasValue<T>(value: T): T {
  if (typeof structuredClone === "function") {
    try {
      return structuredClone(value);
    } catch {
      // Fall through to JSON for ReactFlow plain node/edge snapshots.
    }
  }
  return JSON.parse(JSON.stringify(value)) as T;
}

function cloneFlowHistorySnapshot(nodes: Node[], edges: Edge[]): FlowHistorySnapshot {
  return {
    nodes: cloneCanvasValue(nodes),
    edges: cloneCanvasValue(edges)
  };
}

function isUndoRedoShortcut(event: KeyboardEvent) {
  const key = event.key.toLowerCase();
  const modifier = event.metaKey || event.ctrlKey;
  if (!modifier) {
    return null;
  }
  if (key === "z" && event.shiftKey) {
    return "redo" as const;
  }
  if (key === "z") {
    return "undo" as const;
  }
  if (key === "y") {
    return "redo" as const;
  }
  return null;
}

function inferNodeLayerIndex(node: WorkflowNode, layers: WorkflowNode[]) {
  const directLayer = getLayerOrder(node);
  if (directLayer !== null) {
    return directLayer;
  }

  const idMatch = node.node_id.match(/(?:^|_)l(\d{1,2})(?:_|$)/i);
  if (idMatch) {
    return Number(idMatch[1]);
  }

  const nodeY = node.position?.y;
  if (typeof nodeY !== "number") {
    return null;
  }

  let inferred: number | null = null;
  for (const layer of layers) {
    const layerIndex = getLayerOrder(layer);
    const layerY = layer.position?.y;
    if (layerIndex === null || typeof layerY !== "number") {
      continue;
    }
    if (nodeY >= layerY) {
      inferred = layerIndex;
    }
  }
  return inferred;
}

function dataStringValue(node: WorkflowNode, key: string) {
  const value = node.data?.[key];
  return typeof value === "string" && value ? value : null;
}

function resolveUiLayerId(schemaNode: WorkflowNode, layers: WorkflowNode[], allNodes: WorkflowNode[]) {
  const explicitLayerId =
    dataStringValue(schemaNode, "layer_id") ?? dataStringValue(schemaNode, "layerId") ?? dataStringValue(schemaNode, "parent_layer") ?? dataStringValue(schemaNode, "parentLayer");
  if (explicitLayerId) {
    return explicitLayerId;
  }

  if (schemaNode.type === "layer_container") {
    return schemaNode.node_id;
  }

  const inferredLayerIndex = inferNodeLayerIndex(schemaNode, layers);
  const inferredLayer = layers.find((layer) => getLayerOrder(layer) === inferredLayerIndex);
  if (inferredLayer) {
    return inferredLayer.node_id;
  }

  const nonLayerIndex = allNodes.filter((node) => node.type !== "layer_container").findIndex((node) => node.node_id === schemaNode.node_id);
  if (nonLayerIndex >= 0 && layers.length) {
    return layers[Math.min(nonLayerIndex, layers.length - 1)]?.node_id ?? null;
  }

  return null;
}

function makeFlowNode(schemaNode: WorkflowNode, offset?: { x: number; y: number }, uiLayerId?: string | null): Node {
  const position = schemaNode.position ?? { x: 0, y: 0 };
  return {
    id: schemaNode.node_id,
    type: schemaNode.type === "layer_container" ? "layerContainer" : "workflowNode",
    position: offset ? { x: position.x - offset.x, y: position.y - offset.y } : position,
    data: { schemaNode, layer_id: uiLayerId ?? schemaNode.data?.layer_id }
  };
}

function FolderGroupNode({ data }: { data: FolderGroupNodeData }) {
  const language = useCanvasStore((state) => state.language);
  const {
    layer,
    moduleCatalog,
    modules,
    focusedModuleId,
    selectedModuleKeys,
    moduleColors,
    uiColor,
    onDropModule,
    onSelectDroppedModule,
    onOpenDroppedModule,
    onOpenModuleFocus,
    onContainerContextMenu,
    onDroppedModuleContextMenu
  } = data;
  const label = layerDisplayName(language, layer, moduleCatalog.layers.find((l) => l.layer_id === layer.layer_id)?.layer_name ?? "");
  const parameterCount = Object.keys(layer).length;
  const visibleModules = modules.slice(0, FOLDER_PREVIEW_MODULE_LIMIT);
  const visibleSubnodes: WorkflowNode[] = data.subnodes.slice(0, FOLDER_PREVIEW_MODULE_LIMIT);
  const selectedModuleSet = new Set(selectedModuleKeys);

  return (
    <section
      className="folder-group-node tier-core"
      style={uiColor ? ({ "--node-accent": uiColor } as CSSProperties) : undefined}
      onDragOver={(event) => {
        if (readModuleDragId(event)) {
          event.preventDefault();
          event.dataTransfer.dropEffect = "copy";
        }
      }}
      onDrop={(event) => {
        const moduleId = readModuleDragId(event);
        if (!moduleId) {
          return;
        }
        event.preventDefault();
        event.stopPropagation();
        onDropModule(moduleId);
      }}
      onContextMenu={onContainerContextMenu}
    >
      <Handle type="source" position={Position.Right} id="p_out" className="flow-handle flow-handle-right" />
      <div className="folder-group-node__header">
        <div className="folder-group-title">
          <button
            type="button"
            className="folder-icon folder-focus-button nodrag"
            title={translate(language, "module.viewAll")}
            onClick={(event) => {
              event.stopPropagation();
              onOpenModuleFocus();
            }}
          >
            ::
          </button>
          <div>
            <p>{translate(language, "workspace.breadcrumb", "Workflow / Layer / Folder")}</p>
            <h3>
              L{layer.layer_order} {label}
              <span className="module-count-badge">{modules.length} {translate(language, "module.count")}</span>
            </h3>
          </div>
        </div>
        <details className="folder-group-params nodrag nopan" onPointerDown={(event) => event.stopPropagation()}>
          <summary>{translate(language, "node.params")}</summary>
          <div className="folder-group-meta compact">
            <span>{assemblyFieldLabel(language, "status", translate(language, "field.status"))}: {assemblyStatusLabel(language, "schema")}</span>
            <span>{assemblyFieldLabel(language, "tier")}: {assemblyStatusLabel(language, "core")}</span>
            <span>{translate(language, "field.data")}: {parameterCount}</span>
          </div>
        </details>
      </div>
      <div className="folder-group-node__body">
        <div className={`submodule-rail ${focusedModuleId ? "has-focused-module" : ""}`}>
          {visibleModules.length ? (
            visibleModules.map((mod) => {
              const modId = moduleCatalogId(mod);
              const slot = moduleCatalogSlot(mod);
              const slotLabel = translate(language, `module.slot.${slot}`, slot.toUpperCase());
              const status = String(mod.status);
              const category = String(mod.category || "general");
              const displayClass = moduleCatalogClass(mod);
              return (
                <button
                  key={modId}
                  type="button"
                  className={`submodule-card module-drop-card nodrag nopan cat-${displayClass} status-${status.toLowerCase()} ${selectedModuleSet.has(modId) ? "is-selected" : ""}`}
                  style={moduleColors[modId] ? ({ "--mod-accent": moduleColors[modId] } as CSSProperties) : undefined}
                  onClick={(event) => {
                    event.stopPropagation();
                    onSelectDroppedModule(modId, event.ctrlKey || event.metaKey);
                  }}
                  onDoubleClick={(event) => {
                    event.preventDefault();
                    event.stopPropagation();
                    console.log("[module-open] dropped module double-click", { moduleId: modId, layerId: layer.layer_id });
                    onOpenDroppedModule(modId);
                  }}
                  onContextMenu={(event) => {
                    event.preventDefault();
                    event.stopPropagation();
                    onDroppedModuleContextMenu(event, modId);
                  }}
                  title={`${moduleCatalogName(mod, (key, fallback) => translate(language, key, fallback))} · ${slotLabel} · ${translate(language, `module.status.${status}`, status)}`}
                >
                  <span className="submodule-name">{moduleCatalogName(mod, (key, fallback) => translate(language, key, fallback))}</span>
                  <span className="submodule-badge-row">
                    <span className="submodule-group">{mod.layer_id}</span>
                    <span className={`ai-slot-badge ai-slot-${category === "avatar" ? "ar" : category === "llm" || category === "memory" || category === "tts" || category === "runtime" ? category : "none"}`}>
                      {slotLabel}
                    </span>
                    <span className="submodule-tier">{translate(language, `module.status.${status}`, status)}</span>
                  </span>
                </button>
              );
            })
          ) : visibleSubnodes.length ? (
            visibleSubnodes.map((node) => {
              const moduleTier = dataString(node, "module_tier", "core");
              const uiTags: string[] = Array.isArray(node.data?.ui_tags) ? node.data.ui_tags.map(String).filter(Boolean) : [];
              const uiGroup = typeof node.data?.ui_group === "string" ? node.data.ui_group : "";
              const isFocused = focusedModuleId === node.node_id;
              const aiSlot = inferAiSlot(node);
              return (
                <button
                  key={node.node_id}
                  className={`submodule-card tier-${moduleTier} ${aiSlotClass(aiSlot)} ${aiSlot === "none" ? "is-ai-unplanned" : "has-ai-slot"} ${isFocused ? "is-focused" : ""}`}
                  style={typeof node.data?.ui_color === "string" ? ({ "--node-accent": node.data.ui_color } as CSSProperties) : undefined}
                  onClick={() => data.onSelectNode(node)}
                  onDoubleClick={() => {
                    data.onFocusNode(node);
                    data.onPreviewNode(node);
                  }}
                  onContextMenu={(event) => {
                    event.preventDefault();
                    event.stopPropagation();
                    data.onModuleContextMenu(event, node);
                  }}
                  onTouchEnd={(event) => {
                    event.preventDefault();
                    data.onSelectNode(node);
                  }}
                >
                  <span className="submodule-name">{data.moduleNames[node.node_id] ?? translate(language, node.title_key, node.title_fallback)}</span>
                  {uiGroup ? <span className="submodule-group">{uiGroup}</span> : null}
                  {uiTags.length ? (
                    <span className="submodule-tags">
                      {uiTags.slice(0, 2).map((tag: string) => (
                        <em key={tag}>{tag}</em>
                      ))}
                    </span>
                  ) : null}
                  <span className="submodule-badge-row">
                    <span className={`ai-slot-badge ${aiSlotClass(aiSlot)}`}>{aiSlotLabel(aiSlot)}</span>
                    <span className="submodule-tier">{moduleTier}</span>
                  </span>
                </button>
              );
            })
          ) : (
            <div className="submodule-drop-hint">{translate(language, "module.dropHere", "拖拽模块到这里")}</div>
          )}
        </div>
      </div>
    </section>
  );
}

type LayerAssemblyPanelNodeData = {
  layer: CatalogLayerInput;
  moduleCatalog: ModuleCatalogResponseV04 | null;
  edges: EdgeLike[];
  t: (key: string, fallback?: string) => string;
  moduleNames: Record<string, string>;
  onOpen: (layer: CatalogLayerInput, mode: WorkspaceMode) => void;
  onSelectNode: (node: WorkflowNode) => void;
  onPreviewNode: (node: WorkflowNode) => void;
};

function LayerAssemblyPanelNode({ data }: NodeProps) {
  const panel = data as LayerAssemblyPanelNodeData;
  return (
    <div className="layer-assembly-flow-node nodrag nopan">
      <LayerWorkspacePanel
        layer={panel.layer}
        moduleCatalog={panel.moduleCatalog}
        edges={panel.edges}
        t={panel.t}
        mode="inline"
        moduleNames={panel.moduleNames}
        onOpen={panel.onOpen}
        onSelectNode={panel.onSelectNode}
        onPreviewNode={panel.onPreviewNode}
      />
    </div>
  );
}

export function CanvasShell() {
  const mainFlowRef = useRef<ReactFlowInstance | null>(null);
  const libraryDefaultsAppliedRef = useRef(false);
  const consistencyWarningSignatureRef = useRef("");

  // uiState: shell navigation, drawers, panels, tabs, and visual editing state.
  const [bottomTab, setBottomTab] = useState<BottomTab>("logs");
  const [activeDrawer, setActiveDrawer] = useState<DrawerId | null>(null);
  const [assistantPanelOpen, setAssistantPanelOpen] = useState(false);
  const [residentPreviewPanelOpen, setResidentPreviewPanelOpen] = useState(false);
  const [residentNeuralGraphPanelOpen, setResidentNeuralGraphPanelOpen] = useState(false);
  const [moduleAssistantPanel, setModuleAssistantPanel] = useState<ModuleAssistantPanelState | null>(null);
  const [selectedTemplateType, setSelectedTemplateType] = useState("persona_builder");
  const [loadingTemplateType, setLoadingTemplateType] = useState<string | null>(null);
  const [nodeLibraryCollapsed, setNodeLibraryCollapsed] = useState(true);
  const [activeLayerId, setActiveLayerId] = useState<string | null>(null);
  const [expandedLayerIds, setExpandedLayerIds] = useState<Set<string>>(() => new Set());
  const [workspaceTabs, setWorkspaceTabs] = useState<string[]>([]);
  const [activeWorkspaceId, setActiveWorkspaceId] = useState<string | null>(null);
  const [workspaceMode, setWorkspaceMode] = useState<WorkspaceMode>("inline");
  const [collapsedLayerIds, setCollapsedLayerIds] = useState<Set<string>>(() => new Set());
  const [floatingLayerIds, setFloatingLayerIds] = useState<string[]>([]);
  const [floatingNodeIds, setFloatingNodeIds] = useState<string[]>([]);

  // layoutState: ReactFlow positions and canvas layout-only overrides.
  const [draggedNodeIds, setDraggedNodeIds] = useState<Set<string>>(() => new Set());

  // localStorage keys for module canvas state persistence
  const moduleCanvasStateKey = useRef("moduleCanvasState_v04").current;
  const layerModuleStateKey = useRef("layerModuleState_v04").current;
  
  // Helper: load module canvas state from localStorage
  const loadModuleCanvasState = useCallback(() => {
    if (typeof window === "undefined") {
      return null;
    }

    try {
      const stored = window.localStorage.getItem(moduleCanvasStateKey);
      if (stored) {
        const parsed = JSON.parse(stored);
        return {
          moduleTabs: parsed.moduleTabs ?? [],
          moduleNames: parsed.moduleNames ?? {},
          uiNodeNames: parsed.uiNodeNames ?? {},
          uiTags: parsed.uiTags ?? {},
          uiGroups: parsed.uiGroups ?? {},
          uiColors: parsed.uiColors ?? {},
          moduleUiColors: parsed.moduleUiColors ?? {},
        };
      }
    } catch (e) {
      console.error(t("error.localStorageLoad", "Failed to load module canvas state from localStorage:"), e);
    }
    return null;
  }, [moduleCanvasStateKey]);
  
  // Helper: save module canvas state to localStorage
  const saveModuleCanvasState = useCallback(
    (state: {
      moduleTabs: string[];
      moduleNames: Record<string, string>;
      uiNodeNames: Record<string, string>;
      uiTags: Record<string, string[]>;
      uiGroups: Record<string, string>;
      uiColors: Record<string, string>;
      moduleUiColors?: Record<string, string>;
    }) => {
      if (typeof window === "undefined") {
        return;
      }

      try {
        window.localStorage.setItem(moduleCanvasStateKey, JSON.stringify(state));
      } catch (e) {
        console.error("Failed to save module canvas state to localStorage:", e);
      }
    },
    [moduleCanvasStateKey]
  );

  // Helper: load layer module state from localStorage
  const loadLayerModuleState = useCallback(() => {
    if (typeof window === "undefined") {
      return null;
    }

    try {
      const stored = window.localStorage.getItem(layerModuleStateKey);
      if (stored) {
        const parsed = JSON.parse(stored);
        return {
          layerModules: parsed.layerModules ?? {},
          moduleInstanceRegistry: parsed.moduleInstanceRegistry ?? {},
        };
      }
    } catch (e) {
      console.error("Failed to load layer module state from localStorage:", e);
    }
    return null;
  }, [layerModuleStateKey]);

  // Helper: save layer module state to localStorage
  const saveLayerModuleState = useCallback(
    (layerModules: Record<string, string[]>, moduleInstanceRegistry: Record<string, ModuleInstance>) => {
      if (typeof window === "undefined") {
        return;
      }

      try {
        window.localStorage.setItem(
          layerModuleStateKey,
          JSON.stringify({ layerModules, moduleInstanceRegistry })
        );
      } catch (e) {
        console.error("Failed to save layer module state to localStorage:", e);
      }
    },
    [layerModuleStateKey]
  );

  // uiState: module tabs, naming, labels, groups, colors, and transient module UI.
  const [moduleTabs, setModuleTabs] = useState<string[]>(() => {
    const loaded = loadModuleCanvasState()?.moduleTabs ?? [];
    console.log("[hydrate-init] moduleTabs restored:", { count: loaded.length });
    return loaded;
  });
  const [activeModuleTabId, setActiveModuleTabId] = useState<string | null>(null);
  const [pendingModuleAdd, setPendingModuleAdd] = useState<PendingModuleAdd | null>(null);
  const [focusedModuleId, setFocusedModuleId] = useState<string | null>(null);
  const [moduleNames, setModuleNames] = useState<Record<string, string>>(() => loadModuleCanvasState()?.moduleNames ?? {});
  const [uiNodeNames, setUiNodeNames] = useState<Record<string, string>>(() => loadModuleCanvasState()?.uiNodeNames ?? {});
  const [uiTags, setUiTags] = useState<Record<string, string[]>>(() => loadModuleCanvasState()?.uiTags ?? {});
  const [uiGroups, setUiGroups] = useState<Record<string, string>>(() => loadModuleCanvasState()?.uiGroups ?? {});
  const [uiColors, setUiColors] = useState<Record<string, string>>(() => loadModuleCanvasState()?.uiColors ?? {});
  const [uiInputs, setUiInputs] = useState<Record<string, Record<string, unknown>>>({});
  // Stage 5: capability modules attached to each left folder workspace (Module != Node,
  // not part of workflow execution). Keyed by layer node_id -> module ids.
  const [layerModules, setLayerModules] = useState<Record<string, string[]>>(() => {
    const loaded = loadLayerModuleState()?.layerModules ?? {};
    console.log("[hydrate-init] layerModules restored:", { layerCount: Object.keys(loaded).length });
    return loaded;
  });
  const [moduleInstanceRegistry, setModuleInstanceRegistry] = useState<Record<string, ModuleInstance>>(() => {
    const loaded = loadLayerModuleState()?.moduleInstanceRegistry ?? {};
    console.log("[hydrate-init] moduleInstanceRegistry restored:", { instanceCount: Object.keys(loaded).length });
    return loaded;
  });
  const [focusLayerId, setFocusLayerId] = useState<string | null>(null);
  const [moduleUiColors, setModuleUiColors] = useState<Record<string, string>>(() => loadModuleCanvasState()?.moduleUiColors ?? {});
  const [selectedLayerModuleKeys, setSelectedLayerModuleKeys] = useState<Set<string>>(() => new Set());

  // schemaState: backend catalog and registry snapshots used for rendering.
  const [moduleCatalog, setModuleCatalog] = useState<ModuleCatalogResponseV04 | null>(null);
  const [catalogRevision, setCatalogRevision] = useState(0);
  const moduleCatalogById = useMemo(() => new Map((moduleCatalog?.modules ?? []).map((module) => [module.module_id, module])), [moduleCatalog, catalogRevision]);
  const modulesByCatalogLayerId = useMemo(() => {
    const grouped = new Map<string, ModuleCatalogEntryV04[]>();
    for (const module of moduleCatalog?.modules ?? []) {
      if (isHiddenCatalogModule(module)) {
        continue;
      }
      grouped.set(module.layer_id, [...(grouped.get(module.layer_id) ?? []), module]);
    }
    return grouped;
  }, [moduleCatalog, catalogRevision]);
  const ensureModuleInstance = useCallback((moduleId: string, layerId: string): ModuleInstance => {
    const instanceId = `${layerId}${MODULE_INSTANCE_SEPARATOR}${moduleId}`;
    const instance = { instanceId, moduleId, layerId } satisfies ModuleInstance;
    setModuleInstanceRegistry((current) => {
      if (current[instanceId]) {
        console.log("[NODE-C-DEDUP] ensureModuleInstance already exists, no duplicate created:", { instanceId });
        return current;
      }
      console.log("[NODE-C-DEDUP] ensureModuleInstance creating new:", { instanceId, moduleId, layerId });
      return { ...current, [instanceId]: instance };
    });
    return instance;
  }, []);
  const findModuleInstance = useCallback(
    (moduleId: string, layerId: string): ModuleInstance | null => {
      const preferredId = `${layerId}${MODULE_INSTANCE_SEPARATOR}${moduleId}`;
      const storeGraphs = useCanvasStore.getState().moduleGraphs;
      const module = moduleCatalogById.get(moduleId);
      const registryCandidates = Object.values(moduleInstanceRegistry).filter((instance) => instance.moduleId === moduleId);
      const bestGraphId = bestModuleGraphId(moduleId, preferredId, storeGraphs, module);
      const graphInstance =
        bestGraphId && moduleIdFromInstanceId(bestGraphId) === moduleId
          ? {
              instanceId: bestGraphId,
              moduleId,
              layerId: layerIdFromInstanceId(bestGraphId) || layerId
            }
          : null;
      return graphInstance ?? moduleInstanceRegistry[preferredId] ?? registryCandidates[0] ?? null;
    },
    [moduleCatalogById, moduleInstanceRegistry]
  );
  const addModuleToLayer = useCallback(
    (layerNodeId: string, moduleId: string) => {
      console.log("[NODE-C-DEDUP] addModuleToLayer called:", { layerNodeId, moduleId });
      const module = moduleCatalogById.get(moduleId);
      if (!module) {
        console.warn("[NODE-C-DEDUP] moduleId not found in catalog:", moduleId);
        return;
      }
      if (isHiddenCatalogModule(module)) {
        return;
      }
      const targetLayerId = moduleDisplayLayerId(module, layerNodeId);
      
      // Pre-check: verify moduleId is not already in this layer
      const existingStoredLayerId = storedLayerIdForModule(layerModules, moduleId, "");
      if (existingStoredLayerId) {
        console.warn("[NODE-C-DEDUP] DUPLICATE PREVENTED: moduleId already attached:", { storedLayerId: existingStoredLayerId, moduleId });
        return;
      }
      pushMainHistoryRef.current();
      
      // 1. Ensure instance is created and registered (dedup at instance level)
      ensureModuleInstance(moduleId, targetLayerId);
      
      // 2. Add to layer modules list (with dedup check)
      setLayerModules((current) => {
        const existing = current[targetLayerId] ?? [];
        if (existing.includes(moduleId)) {
          console.warn("[NODE-C-DEDUP] DUPLICATE in setLayerModules (race condition prevented):", { layerNodeId: targetLayerId, moduleId });
          return current;
        }
        const updated = { ...current, [targetLayerId]: [...existing, moduleId] };
        console.log("[NODE-C-DEDUP] module successfully added to layer:", { layerNodeId: targetLayerId, moduleId, totalInLayer: updated[targetLayerId].length });
        return updated;
      });
      
      // 3. Mark dirty for autosave
      setSaveStatus("dirty");
    },
    [ensureModuleInstance, moduleCatalogById, layerModules]
  );

  const removeModuleFromLayer = useCallback((layerNodeId: string, moduleId: string) => {
    pushMainHistoryRef.current();
    setLayerModules((current) => {
      const module = moduleCatalogById.get(moduleId);
      if (module?.layer_id === "general") {
        return { ...current, [layerNodeId]: (current[layerNodeId] ?? []).filter((id) => id !== moduleId) };
      }
      return Object.fromEntries(Object.entries(current).map(([id, moduleIds]) => [id, moduleIds.filter((currentModuleId) => currentModuleId !== moduleId)]));
    });
    setSelectedLayerModuleKeys((current) => {
      const next = new Set(current);
      next.delete(`${layerNodeId}:${moduleId}`);
      return next;
    });
    setSaveStatus("dirty");
  }, [moduleCatalogById]);
  const removeAllModulesFromLayer = useCallback((layerNodeId: string) => {
    pushMainHistoryRef.current();
    setLayerModules((current) => ({ ...current, [layerNodeId]: [] }));
    setSelectedLayerModuleKeys((current) => {
      const next = new Set(current);
      for (const key of current) {
        if (key.startsWith(`${layerNodeId}:`)) {
          next.delete(key);
        }
      }
      return next;
    });
    setSaveStatus("dirty");
  }, []);
  const setModuleColor = useCallback((layerNodeId: string, moduleId: string, color: string) => {
    pushMainHistoryRef.current();
    setModuleUiColors((current) => ({ ...current, [`${layerNodeId}:${moduleId}`]: color }));
    setSaveStatus("dirty");
  }, []);
  const [selectedFlowNodeIds, setSelectedFlowNodeIds] = useState<Set<string>>(() => new Set());
  const [mainContextMenu, setMainContextMenu] = useState<CanvasContextMenuState | null>(null);
  const [showGrid, setShowGrid] = useState(true);
  const [showMiniMap, setShowMiniMap] = useState(true);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [collapsedCategories, setCollapsedCategories] = useState<Set<string>>(() => new Set());
  const [libraryBodyCollapsed, setLibraryBodyCollapsed] = useState(true);
  const [saveStatus, setSaveStatus] = useState<SaveStatus>("saved");
  const [requiresDrRecompile, setRequiresDrRecompile] = useState(false);
  const mainHistoryRef = useRef<MainHistoryState>({ past: [], future: [], restoring: false });
  const pushMainHistoryRef = useRef<() => void>(() => undefined);
  const mainSnapshotRef = useRef<MainCanvasSnapshot | null>(null);
  const [mainHistoryVersion, setMainHistoryVersion] = useState(0);

  // executionState: display-only execution/result references; execution remains backend-owned.
  const [residentPreviewOutput, setResidentPreviewOutput] = useState<unknown>(null);
  const [registryRevision, setRegistryRevision] = useState(0);
  const nodeLibraryCategories = useMemo(() => buildNodeLibraryCategories(getNodeRegistryEntries()), [registryRevision]);
  const libraryNodeTypes = useMemo(() => nodeLibraryCategories.flatMap((category) => category.nodes), [nodeLibraryCategories]);
  const toggleCategory = useCallback((id: string) => {
    setCollapsedCategories((current) => {
      const next = new Set(current);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  }, []);
  const {
    logs,
    artifacts,
    language,
    validation,
    exportPreview,
    runtimeResult,
    memoryView,
    memoryClearResult,
    moduleGraphs,
    apiReady,
    setSelectedNode,
    setLanguage,
    setValidation,
    setExportPreview,
    setApiReady,
    appendLog,
    clearRunOutput,
    applyRuntimeResult,
    compileDR,
    exportDR,
    exportAuditDR,
    canExportDR,
    loadDRFile,
    loadCompiledDRToPreview,
    loadedDRResult,
    previewLoadStatus,
    previewLoadError
  } = useCanvasStore();

  const t = useCallback((key: string, fallback?: string) => translate(language, key, fallback), [language]);

  useEffect(() => {
    mainSnapshotRef.current = {
      layerModules: cloneCanvasValue(layerModules),
      moduleInstanceRegistry: cloneCanvasValue(moduleInstanceRegistry),
      moduleTabs: [...moduleTabs],
      activeModuleTabId,
      focusedModuleId,
      moduleNames: cloneCanvasValue(moduleNames),
      uiNodeNames: cloneCanvasValue(uiNodeNames),
      uiTags: cloneCanvasValue(uiTags),
      uiGroups: cloneCanvasValue(uiGroups),
      uiColors: cloneCanvasValue(uiColors),
      moduleUiColors: cloneCanvasValue(moduleUiColors),
      selectedLayerModuleKeys: [...selectedLayerModuleKeys],
      expandedLayerIds: [...expandedLayerIds],
      activeLayerId,
      activeWorkspaceId,
      workspaceTabs: [...workspaceTabs],
      floatingLayerIds: [...floatingLayerIds],
      floatingNodeIds: [...floatingNodeIds],
      draggedNodeIds: [...draggedNodeIds]
    };
  }, [
    activeLayerId,
    activeModuleTabId,
    activeWorkspaceId,
    draggedNodeIds,
    expandedLayerIds,
    floatingLayerIds,
    floatingNodeIds,
    focusedModuleId,
    layerModules,
    moduleInstanceRegistry,
    moduleNames,
    moduleTabs,
    moduleUiColors,
    selectedLayerModuleKeys,
    uiColors,
    uiGroups,
    uiNodeNames,
    uiTags,
    workspaceTabs
  ]);

  const pushMainHistory = useCallback(() => {
    const snapshot = mainSnapshotRef.current;
    if (!snapshot || mainHistoryRef.current.restoring) {
      return;
    }
    mainHistoryRef.current.past = [...mainHistoryRef.current.past.slice(-(CANVAS_HISTORY_LIMIT - 1)), cloneCanvasValue(snapshot)];
    mainHistoryRef.current.future = [];
    setMainHistoryVersion((version) => version + 1);
  }, []);

  useEffect(() => {
    pushMainHistoryRef.current = pushMainHistory;
  }, [pushMainHistory]);

  const restoreMainSnapshot = useCallback((snapshot: MainCanvasSnapshot) => {
    mainHistoryRef.current.restoring = true;
    setLayerModules(cloneCanvasValue(snapshot.layerModules));
    setModuleInstanceRegistry(cloneCanvasValue(snapshot.moduleInstanceRegistry));
    setModuleTabs([...snapshot.moduleTabs]);
    setActiveModuleTabId(snapshot.activeModuleTabId);
    setFocusedModuleId(snapshot.focusedModuleId);
    setModuleNames(cloneCanvasValue(snapshot.moduleNames));
    setUiNodeNames(cloneCanvasValue(snapshot.uiNodeNames));
    setUiTags(cloneCanvasValue(snapshot.uiTags));
    setUiGroups(cloneCanvasValue(snapshot.uiGroups));
    setUiColors(cloneCanvasValue(snapshot.uiColors));
    setModuleUiColors(cloneCanvasValue(snapshot.moduleUiColors));
    setSelectedLayerModuleKeys(new Set(snapshot.selectedLayerModuleKeys));
    setExpandedLayerIds(new Set(snapshot.expandedLayerIds));
    setActiveLayerId(snapshot.activeLayerId);
    setActiveWorkspaceId(snapshot.activeWorkspaceId);
    setWorkspaceTabs([...snapshot.workspaceTabs]);
    setFloatingLayerIds([...snapshot.floatingLayerIds]);
    setFloatingNodeIds([...snapshot.floatingNodeIds]);
    setDraggedNodeIds(new Set(snapshot.draggedNodeIds));
    setSaveStatus("dirty");
    window.queueMicrotask(() => {
      mainHistoryRef.current.restoring = false;
    });
  }, []);

  const undoMainCanvas = useCallback(() => {
    const current = mainSnapshotRef.current;
    const previous = mainHistoryRef.current.past.pop();
    if (!current || !previous) {
      appendLog(t("status.noUndo", "Nothing to undo"), "warn");
      return;
    }
    mainHistoryRef.current.future = [...mainHistoryRef.current.future.slice(-(CANVAS_HISTORY_LIMIT - 1)), cloneCanvasValue(current)];
    restoreMainSnapshot(previous);
    setMainHistoryVersion((version) => version + 1);
  }, [appendLog, restoreMainSnapshot, t]);

  const redoMainCanvas = useCallback(() => {
    const current = mainSnapshotRef.current;
    const next = mainHistoryRef.current.future.pop();
    if (!current || !next) {
      appendLog(t("status.noRedo", "Nothing to redo"), "warn");
      return;
    }
    mainHistoryRef.current.past = [...mainHistoryRef.current.past.slice(-(CANVAS_HISTORY_LIMIT - 1)), cloneCanvasValue(current)];
    restoreMainSnapshot(next);
    setMainHistoryVersion((version) => version + 1);
  }, [appendLog, restoreMainSnapshot, t]);

  // P1-BRIDGE：在挂载时初始化 store 状态（从 localStorage 恢复）
  useEffect(() => {
    console.log("[P1-BRIDGE] Initializing module state on mount");
    initializeModuleState();
    cleanupOrphanedGraphs();
    ensureAllTabsHaveGraphs();
  }, []); // run once on mount

  // NODE B HYDRATION: Verify moduleInstanceRegistry and layerModules were restored on mount
  useEffect(() => {
    const instanceCount = Object.keys(moduleInstanceRegistry).length;
    const layerCount = Object.keys(layerModules).length;
    if (instanceCount > 0 || layerCount > 0) {
      const msg = `[NODE-B-HYDRATION] moduleInstances restored on mount: ${instanceCount} instances across ${layerCount} layers`;
      console.log(msg);
      appendLog(msg);
    } else {
      console.log("[NODE-B-HYDRATION] no moduleInstances to restore on this mount");
    }
  }, []); // run once on mount

  useEffect(() => {
    let active = true;

    api
      .fetchNodeRegistry()
      .then((registry) => {
        if (!active) {
          return;
        }
        setBackendNodeRegistry(registry);
        setRegistryRevision((revision) => revision + 1);
        appendLog(`${translate(language, "status.nodeRegistryLoaded", "Node registry loaded")}: ${Object.keys(registry).length}`);
      })
      .catch((error) => {
        if (active) {
          appendLog(`${translate(language, "error.nodeRegistry", "Node registry failed")}: ${(error as Error).message}`, "error");
        }
      });

    api
      .fetchModuleCatalog()
      .then((modules) => {
        if (!active) {
          return;
        }
        
        // NODE F: CANONICAL_LAYERS validation - 13-layer strict check
        console.log("[NODE-F-VALIDATE] moduleCatalog received, validating 13-layer structure");
        
        const layerCount = modules.layers.length;
        if (layerCount !== 13) {
          const error = `[NODE-F-VALIDATE] CRITICAL: backend layer count = ${layerCount}, expected 13`;
          console.error(error);
          appendLog(error, "error");
          setApiReady(false);
          return;
        }
        
        // Verify layer order is strictly 1-13
        const sorted = [...modules.layers].sort((a, b) => (a.layer_order ?? 0) - (b.layer_order ?? 0));
        for (let i = 0; i < sorted.length; i += 1) {
          if (sorted[i].layer_order !== i + 1) {
            const error = `[NODE-F-VALIDATE] CRITICAL: layer_order mismatch at index ${i}: expected ${i + 1}, got ${sorted[i].layer_order}`;
            console.error(error);
            appendLog(error, "error");
            setApiReady(false);
            return;
          }
        }
        
        console.log("[NODE-F-VALIDATE] moduleCatalog passed 13-layer validation ✓");
        setModuleCatalog(modules);
        setCatalogRevision((revision) => revision + 1);
        appendLog(`${t("status.moduleCatalogLoaded", "Module catalog loaded and validated")}: ${modules.modules.length} ${t("common.modules", "modules")}; 13 ${t("common.layers", "layers")}`);
      })
      .catch((error) => {
        if (active) {
          appendLog(`${t("error.moduleCatalog", "Module catalog failed")}: ${(error as Error).message}`, "error");
        }
      });

    api
      .fetchSlotCatalog()
      .then((slots) => {
        if (active) {
          appendLog(`${t("status.slotCatalogLoaded", "Slot catalog loaded")}: ${slots.slots.length}`);
        }
      })
      .catch((error) => {
        if (active) {
          appendLog(`${t("error.slotCatalog", "Slot catalog failed")}: ${(error as Error).message}`, "error");
        }
      });

    api
      .fetchEngineRegistry()
      .then((engines) => {
        if (active) {
          appendLog(`${t("status.engineRegistryLoaded", "Engine registry loaded")}: ${engines.engines.length}`);
        }
      })
      .catch((error) => {
        if (active) {
          appendLog(`${t("error.engineRegistry", "Engine registry failed")}: ${(error as Error).message}`, "error");
        }
      });

    useCanvasStore
      .getState()
      .loadLLMConfig()
      .then(() => {
        if (!active) {
          return;
        }
        const profiles = useCanvasStore.getState().llmProfiles;
        appendLog(`${t("status.llmProfilesLoaded", "LLM profiles loaded")}: ${Object.keys(profiles?.profiles ?? {}).length}`);
      })
      .catch((error) => {
        if (active) {
          appendLog(`${t("error.llmProfiles", "LLM profiles failed")}: ${(error as Error).message}`, "error");
        }
      });

    return () => {
      active = false;
    };
  }, [appendLog, language]);

  // Debounced autosave of module canvas state to localStorage
  // P1-BRIDGE：同时同步到 store
  useEffect(() => {
    const timer = setTimeout(() => {
      console.log("[P1-SYNC] autosave: syncing state to both localStorage and store");
      const store = useCanvasStore.getState();
      
      // 同步到 localStorage
      saveModuleCanvasState({
        moduleTabs,
        moduleNames,
        uiNodeNames,
        uiTags,
        uiGroups,
        uiColors,
        moduleUiColors,
      });
      
      // P1-BRIDGE：同步到 store
      store.setModuleTabs(moduleTabs);
      store.setModuleNames(moduleNames);
      store.setUiNodeNames(uiNodeNames);
      store.setUiTags(uiTags);
      store.setUiGroups(uiGroups);
      store.setUiColors(uiColors);
    }, 500);
    return () => clearTimeout(timer);
  }, [moduleTabs, moduleNames, uiNodeNames, uiTags, uiGroups, uiColors, moduleUiColors, saveModuleCanvasState]);

  // Autosave of layer module state to localStorage (persists module instances)
  // P1-BRIDGE：同时同步到 store
  useEffect(() => {
    const timer = setTimeout(() => {
      console.log("[P1-SYNC] autosave layer modules: syncing to both localStorage and store", {
        layerCount: Object.keys(layerModules).length,
        instanceCount: Object.keys(moduleInstanceRegistry).length
      });
      const store = useCanvasStore.getState();
      
      // 同步到 localStorage
      saveLayerModuleState(layerModules, moduleInstanceRegistry);
      
      // P1-BRIDGE：同步到 store
      store.setLayerModules(layerModules);
      store.setModuleInstanceRegistry(moduleInstanceRegistry);
    }, 500);
    return () => clearTimeout(timer);
  }, [layerModules, moduleInstanceRegistry, saveLayerModuleState]);

  // 双层保存系统：聚合所有状态并保存到 localStorage
  // P1-BRIDGE：同时同步到 store
  useEffect(() => {
    const timer = setTimeout(() => {
      console.log("[P1-SYNC] full canvas state autosave triggered");
      const store = useCanvasStore.getState();
      
      const fullCanvasState = deserializeCanvasState({
        moduleTabs,
        moduleNames,
        uiNodeNames,
        uiTags,
        uiGroups,
        uiColors,
        moduleUiColors,
        layerModules,
        moduleInstanceRegistry,
      });
      
      // 保存到 localStorage
      saveCanvasStateToLocalStorage(fullCanvasState);
      
      // P1-BRIDGE：同步所有状态到 store（确保 store 是最新的）
      store.setModuleTabs(moduleTabs);
      store.setModuleNames(moduleNames);
      store.setUiNodeNames(uiNodeNames);
      store.setUiTags(uiTags);
      store.setUiGroups(uiGroups);
      store.setUiColors(uiColors);
      store.setModuleUiColors(moduleUiColors);
      store.setLayerModules(layerModules);
      store.setModuleInstanceRegistry(moduleInstanceRegistry);
    }, 1000);
    return () => clearTimeout(timer);
  }, [
    moduleTabs,
    moduleNames,
    uiNodeNames,
    uiTags,
    uiGroups,
    uiColors,
    moduleUiColors,
    layerModules,
    moduleInstanceRegistry,
  ]);

  // 导出 Canvas 状态为 JSON 文件
  const handleExportCanvasState = useCallback(() => {
    const canvasState = deserializeCanvasState({
      moduleTabs,
      moduleNames,
      uiNodeNames,
      uiTags,
      uiGroups,
      uiColors,
      moduleUiColors,
      layerModules,
      moduleInstanceRegistry,
    });
    downloadCanvasState(canvasState);
    appendLog(t("export.success", "Canvas 状态已导出"), "info");
  }, [
    moduleTabs,
    moduleNames,
    uiNodeNames,
    uiTags,
    uiGroups,
    uiColors,
    moduleUiColors,
    layerModules,
    moduleInstanceRegistry,
    appendLog,
    t,
  ]);

  // 导入 Canvas 状态
  const fileInputRef = useRef<HTMLInputElement>(null);
  const drLoadInputRef = useRef<HTMLInputElement>(null);
  const handleImportCanvasState = useCallback(
    async (event: React.ChangeEvent<HTMLInputElement>) => {
      const file = event.target.files?.[0];
      if (!file) {
        return;
      }

      try {
        const result = await readCanvasStateFromFile(file);
        if (!result.success || !result.state) {
          appendLog(`${t("error.importFailed", "Import failed")}: ${result.error || t("common.unknownError", "unknown error")}`, "error");
          return;
        }

        const state = result.state;
        
        // 恢复所有状态
        setModuleTabs(state.moduleTabs);
        setModuleNames(state.moduleNames);
        setUiNodeNames(state.uiNodeNames);
        setUiTags(state.uiTags);
        setUiGroups(state.uiGroups);
        setUiColors(state.uiColors);
        setModuleUiColors(state.moduleUiColors);
        setLayerModules(state.layerModules);
        setModuleInstanceRegistry(state.moduleInstanceRegistry);
        
        // P1-BRIDGE：同时同步到 store
        console.log("[P1-SYNC] Syncing imported canvas state to store");
        const store = useCanvasStore.getState();
        store.setModuleTabs(state.moduleTabs);
        store.setModuleNames(state.moduleNames);
        store.setUiNodeNames(state.uiNodeNames);
        store.setUiTags(state.uiTags);
        store.setUiGroups(state.uiGroups);
        store.setUiColors(state.uiColors);
        store.setModuleUiColors(state.moduleUiColors);
        store.setLayerModules(state.layerModules);
        store.setModuleInstanceRegistry(state.moduleInstanceRegistry);
        
        appendLog(t("import.success", "Canvas 状态已导入"), "info");
      } catch (error) {
        appendLog(`${t("error.importException", "Import exception")}: ${error instanceof Error ? error.message : t("common.unknownError", "unknown error")}`, "error");
      } finally {
        // 重置文件输入，以便可以再次选择同一文件
        if (fileInputRef.current) {
          fileInputRef.current.value = "";
        }
      }
    },
    [appendLog, t, setModuleTabs, setModuleNames, setUiNodeNames, setUiTags, setUiGroups, setUiColors, setModuleUiColors, setLayerModules, setModuleInstanceRegistry]
  );

  const handleImportCanvasStateClick = useCallback(() => {
    fileInputRef.current?.click();
  }, []);

  const handleLoadDRFile = useCallback(
    async (event: React.ChangeEvent<HTMLInputElement>) => {
      const file = event.target.files?.[0];
      if (!file) {
        return;
      }
      setBottomTab("logs");
      setActiveDrawer("logs");
      await loadDRFile(file);
      event.target.value = "";
    },
    [loadDRFile, setActiveDrawer, setBottomTab]
  );

  const handleLoadDRClick = useCallback(() => {
    drLoadInputRef.current?.click();
  }, []);

  const handleLoadCompiledDRToPreview = useCallback(async () => {
    await loadCompiledDRToPreview();
  }, [loadCompiledDRToPreview]);

  const handleUndo = useCallback(() => {
    undoMainCanvas();
  }, [undoMainCanvas]);

  const handleRedo = useCallback(() => {
    redoMainCanvas();
  }, [redoMainCanvas]);
  const canUndoMain = mainHistoryVersion >= 0 && mainHistoryRef.current.past.length > 0;
  const canRedoMain = mainHistoryVersion >= 0 && mainHistoryRef.current.future.length > 0;

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (activeModuleTabId || shouldUseNativeContextMenu(event.target)) {
        return;
      }
      const action = isUndoRedoShortcut(event);
      if (!action) {
        return;
      }
      event.preventDefault();
      if (action === "undo") {
        undoMainCanvas();
      } else {
        redoMainCanvas();
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [activeModuleTabId, redoMainCanvas, undoMainCanvas]);
  // User-facing template list. `persona_builder` is the only one currently wired
  // to a canvas (it reuses the v0.4 module-catalog source); the rest are legacy
  // placeholders. `schema_v04` is the internal data source and is never exposed
  // as a user template name.
  const templateOptions = useMemo(
    () => ["blank", "persona_builder", "agent", "knowledge_pipeline", "review_pipeline"],
    []
  );

  useEffect(() => {
    if (libraryDefaultsAppliedRef.current || !nodeLibraryCategories.length) {
      return;
    }
    setCollapsedCategories(new Set(nodeLibraryCategories.map((category) => category.id)));
    setLibraryBodyCollapsed(true);
    libraryDefaultsAppliedRef.current = true;
  }, [nodeLibraryCategories]);

  const catalogLayers = useMemo(
    () =>
      (moduleCatalog?.layers ?? [])
        .slice()
        .sort((a, b) => catalogLayerOrder(a) - catalogLayerOrder(b)),
    [moduleCatalog]
  );
  const catalogLayerNodes = useMemo(
    () =>
      moduleCatalog ? catalogLayers.map((layer) => catalogLayerToWorkflowNode(layer, moduleCatalog)) : [],
    [catalogLayers, moduleCatalog]
  );
  const workflow = useMemo(() => buildSchemaWorkflow(moduleCatalog), [moduleCatalog]);
  const nodes = catalogLayerNodes;
  const edges = useMemo(() => [], []);

  useEffect(() => {
    // Only reset module UI state when schema actually changes, not on every catalog update
    setSelectedLayerModuleKeys(new Set());
    setModuleUiColors({});
    // Do NOT reset layerModules here as it causes loss of user-added modules on page refresh
  }, [moduleCatalog?.schema_version]);

	  const layerById = useMemo(
	    () => new Map(catalogLayers.map((layer) => [layer.layer_id, layer])),
	    [catalogLayers]
	  );
  const selectedNodeId = useCanvasStore((state) => state.selectedNodeId);
  const selectedNode = useMemo(() => nodes.find((node) => node.node_id === selectedNodeId) ?? null, [nodes, selectedNodeId]);
  const resolveModuleNode = useCallback(
    (id: string) => {
      const existing = nodes.find((node) => node.node_id === id);
      if (existing) {
        return existing;
      }
      const [layerNodeId, moduleId] = id.split(MODULE_INSTANCE_SEPARATOR);
      const mod = moduleId ? moduleCatalogById.get(moduleId) : null;
      const layer = layerNodeId ? layerById.get(layerNodeId) : null;
      if (!mod || !layer) {
        return null;
      }
      return {
        node_id: id,
        type: "module",
        category: "container",
        title_key: "",
          title_fallback: moduleCatalogName(mod, (key, fallback) => translate(language, key, fallback)),
        position: { x: 0, y: 0 },
        lock_level: "editable",
	        data: {
	          ui_only: true,
	          parent_layer: layerNodeId,
	          layer_order: layer.layer_order,
	          module_catalog_id: moduleCatalogId(mod),
	          module_tier: "core",
	          status: mod.status
        },
        ports: { inputs: [], outputs: [] }
      } satisfies WorkflowNode;
    },
    [layerById, moduleCatalogById, nodes]
  );
  const moduleTabItems = useMemo(
    () =>
      moduleTabs.map((id) => {
        const node = resolveModuleNode(id);
        return { id, label: node ? translate(language, node.title_key, node.title_fallback) : id };
      }),
    [language, moduleTabs, resolveModuleNode]
  );
  const activeModuleNode = useMemo(
    () => (activeModuleTabId ? resolveModuleNode(activeModuleTabId) : null),
    [activeModuleTabId, resolveModuleNode]
  );
  const activeModuleSubnodes = useMemo(
    () =>
      activeModuleTabId
        ? nodes.filter(
            (node) =>
              node.node_id !== activeModuleTabId &&
              (node.data?.parent_module === activeModuleTabId || node.data?.parent_layer === activeModuleTabId)
          )
        : [],
    [activeModuleTabId, nodes]
  );

  const selectedLayer = activeWorkspaceId ? layerById.get(activeWorkspaceId) ?? null : null;
  const activeLayer = activeLayerId ? layerById.get(activeLayerId) ?? null : selectedLayer;

	  useEffect(() => {
	    const internal = workflow?.template_type;
	    if (!internal) {
	      return;
	    }
	    // `schema_v04` is the internal canvas data source — surface it to users as
	    // `persona_builder`. Never let the internal id (or any non-listed id) leak into
	    // the user-facing selector, which would otherwise fall back to the first option.
	    const mapped = internal === "schema_v04" ? "persona_builder" : internal;
	    setSelectedTemplateType(templateOptions.includes(mapped) ? mapped : "persona_builder");
  }, [workflow?.template_type, templateOptions]);

  useEffect(() => {
    let active = true;

    api
      .health()
      .then(() => {
        if (!active) {
          return;
        }
        setApiReady(true);
        appendLog(t("status.apiReady"));
      })
      .catch(() => {
        if (active) {
          setApiReady(false);
        }
      });

	    return () => {
	      active = false;
	    };
	  }, [appendLog, setApiReady, t]);

  useEffect(() => {
    if (activeLayerId && !layerById.has(activeLayerId)) {
      setActiveLayerId(null);
    }
    setExpandedLayerIds((ids) => {
      const next = new Set([...ids].filter((id) => layerById.has(id)));
      if (next.size === ids.size && [...next].every((id) => ids.has(id))) {
        return ids;
      }
      return next;
    });
    if (activeWorkspaceId && !layerById.has(activeWorkspaceId)) {
      setActiveWorkspaceId(null);
    }
    setWorkspaceTabs((tabs) => tabs.filter((id) => layerById.has(id)));
    setFloatingLayerIds((ids) => ids.filter((id) => layerById.has(id)));
    setFloatingNodeIds((ids) => ids.filter((id) => nodes.some((node) => node.node_id === id)));
  }, [activeLayerId, activeWorkspaceId, layerById, nodes]);

	  useEffect(() => {
    if (!moduleCatalog) {
      return;
    }
	    const frames = computeLayerStackFrames(catalogLayers, LAYOUT_MODULE_COUNTS);
	    const warnings = checkCanvasStructureConsistency(catalogLayers, nodes, frames, moduleCatalog);
	    const signature = warnings.join("|");
    if (!signature || signature === consistencyWarningSignatureRef.current) {
      return;
    }
    consistencyWarningSignatureRef.current = signature;
    warnings.forEach((warning) => appendLog(`[canvas-structure] ${warning}`, "warn"));
	  }, [appendLog, catalogLayers, layerModules, moduleCatalog, nodes]);

  const handleChildModuleSelect = useCallback(
    (node: WorkflowNode) => {
      setSelectedNode(node.node_id);
      appendLog(`${t("status.moduleSelected", "Module selected")}: ${t(node.title_key, node.title_fallback)}`);
    },
    [appendLog, setSelectedNode, t]
  );

  const handleChildModulePreview = useCallback(
    (node: WorkflowNode) => {
      console.log("[P1-SYNC] handleChildModulePreview called:", { moduleId: node.node_id });
      // P1-BRIDGE：使用 bridge 来处理 tab 打开，确保 graph 也被创建
      handleTabOpened(node.node_id);
      setModuleTabs((tabs) => (tabs.includes(node.node_id) ? tabs : [...tabs, node.node_id]));
      setActiveModuleTabId(node.node_id);
      setActiveDrawer(null);
      appendLog(`${t("status.moduleCanvasOpened", "Module canvas opened")}: ${t(node.title_key, node.title_fallback)}`);
    },
    [appendLog, t]
  );

  const selectLayerModule = useCallback((layerNodeId: string, moduleId: string, multi: boolean) => {
    const key = `${layerNodeId}:${moduleId}`;
    setSelectedLayerModuleKeys((current) => {
      if (!multi) {
        return new Set([key]);
      }
      const next = new Set(current);
      if (next.has(key)) {
        next.delete(key);
      } else {
        next.add(key);
      }
      return next;
    });
    setSelectedNode(layerNodeId);
  }, [setSelectedNode]);

  const openCatalogModuleCanvas = useCallback(
    (layerNodeId: string, moduleId: string) => {
      console.log("[P1-SYNC] openCatalogModuleCanvas: using bridge to open tab");
      let mod = moduleCatalogById.get(moduleId);

      if (!mod && moduleCatalog) {
        mod = moduleCatalog.modules.find((m) => m.module_id === moduleId);
      }

      if (!mod) {
        console.warn("[module-open] module not found", {
          moduleId,
          layerNodeId,
          catalogLoaded: Boolean(moduleCatalog),
          availableModules: moduleCatalog?.modules.map((m) => m.module_id) ?? []
        });
        appendLog(`模块未找到: ${moduleId}`, "error");
        return;
      }
      const targetLayerId = moduleDisplayLayerId(mod, layerNodeId);
      const moduleInstance = findModuleInstance(moduleId, targetLayerId) ?? ensureModuleInstance(moduleId, targetLayerId);
      const moduleNodeId = moduleInstance.instanceId;

      console.log("[module-open] open module canvas", { moduleId, layerId: layerNodeId, tabId: moduleNodeId });
      const seed = buildCatalogModuleSeed(mod, moduleNodeId);
      // P1-BRIDGE：使用 bridge 来确保 graph 也被创建
      handleTabOpened(moduleNodeId, seed.nodes, seed.edges);
      setModuleTabs((tabs) => (tabs.includes(moduleNodeId) ? tabs : [...tabs, moduleNodeId]));
      setActiveModuleTabId(moduleNodeId);
      setActiveDrawer(null);
      appendLog(`${t("status.moduleCanvasOpened", "Module canvas opened")}: ${moduleCatalogName(mod, (key, fallback) => translate(language, key, fallback))}`);
    },
    [appendLog, ensureModuleInstance, findModuleInstance, moduleCatalogById, moduleCatalog, t]
  );

  useEffect(() => {
    if (!moduleCatalog) {
      return;
    }
    for (const instance of Object.values(moduleInstanceRegistry)) {
      const mod = moduleCatalogById.get(instance.moduleId) ?? moduleCatalog.modules.find((module) => module.module_id === instance.moduleId);
      if (!mod) {
        continue;
      }
      const seed = buildCatalogModuleSeed(mod, instance.instanceId);
      ensureModuleGraphExists(instance.instanceId, seed.nodes, seed.edges);
    }
  }, [moduleCatalog, moduleCatalogById, moduleInstanceRegistry]);

  const renameUiNode = useCallback(
    (nodeId: string, currentName: string) => {
      const nextName = window.prompt(t("common.renameNode", "Rename node"), currentName);
      if (!nextName?.trim()) {
        return;
      }
      pushMainHistory();
      setUiNodeNames((current) => ({ ...current, [nodeId]: nextName.trim() }));
      appendLog(`${t("status.nodeRenamed", "Node renamed")}: ${nextName.trim()}`);
    },
    [appendLog, pushMainHistory, t]
  );

  const renameUiModule = useCallback(
    (nodeId: string, currentName: string) => {
      const nextName = window.prompt(t("common.renameModule", "Rename module"), currentName);
      if (!nextName?.trim()) {
        return;
      }
      pushMainHistory();
      setModuleNames((current) => ({ ...current, [nodeId]: nextName.trim() }));
      appendLog(`${t("status.moduleRenamed", "Module renamed")}: ${nextName.trim()}`);
    },
    [appendLog, pushMainHistory, t]
  );

  const editUiTagsForIds = useCallback((nodeIds: string[], title = t("common.nodeTags", "Node tags")) => {
    const firstId = nodeIds[0];
    if (!firstId) {
      return;
    }
    const currentText = (uiTags[firstId] ?? []).join(", ");
    const nextTags = window.prompt(title, currentText);
    if (nextTags === null) {
      return;
    }
    const tags = nextTags
      .split(",")
      .map((tag) => tag.trim())
      .filter(Boolean);
    pushMainHistory();
    setUiTags((current) => {
      const next = { ...current };
      for (const id of nodeIds) {
        next[id] = tags;
      }
      return next;
    });
    setSaveStatus("dirty");
  }, [pushMainHistory, uiTags]);

  const editUiGroupForIds = useCallback((nodeIds: string[], title = t("common.nodeGroup", "Node group")) => {
    const firstId = nodeIds[0];
    if (!firstId) {
      return;
    }
    const nextGroup = window.prompt(title, uiGroups[firstId] ?? "");
    if (nextGroup === null) {
      return;
    }
    pushMainHistory();
    setUiGroups((current) => {
      const next = { ...current };
      for (const id of nodeIds) {
        next[id] = nextGroup.trim();
      }
      return next;
    });
    setSaveStatus("dirty");
  }, [pushMainHistory, uiGroups]);

  const renameVisualGroup = useCallback((nodeId: string) => {
    const currentGroup = uiGroups[nodeId] ?? "";
    const nextGroup = window.prompt(t("common.renameGroup", "Rename group"), currentGroup);
    if (nextGroup === null) {
      return;
    }
    pushMainHistory();
    setUiGroups((current) => {
      const next = { ...current };
      if (!currentGroup) {
        next[nodeId] = nextGroup.trim();
        return next;
      }
      for (const [id, group] of Object.entries(current)) {
        if (group === currentGroup) {
          next[id] = nextGroup.trim();
        }
      }
      return next;
    });
  }, [pushMainHistory, t, uiGroups]);

  const dissolveVisualGroup = useCallback((nodeId: string) => {
    const currentGroup = uiGroups[nodeId] ?? "";
    if (!currentGroup) {
      return;
    }
    pushMainHistory();
    setUiGroups((current) => {
      const next = { ...current };
      for (const [id, group] of Object.entries(current)) {
        if (group === currentGroup) {
          next[id] = "";
        }
      }
      return next;
    });
  }, [pushMainHistory, uiGroups]);

  const handleModuleContextMenu = useCallback(
    (event: ReactMouseEvent, node: WorkflowNode) => {
      const label = moduleNames[node.node_id] ?? translate(language, node.title_key, node.title_fallback);
      const group = uiGroups[node.node_id] ?? "";
      const menu = makeContextMenu(event, [
        {
          label: t("common.focusView", "Focus view"),
          onSelect: () => {
            setFocusedModuleId(node.node_id);
            handleChildModulePreview(node);
          }
        },
        { label: t("common.renameModule", "Rename module"), onSelect: () => renameUiModule(node.node_id, label) },
        { label: t("common.color", "Color"), onSelect: () => {
          const nextColor = window.prompt(t("field.color", "Color"), uiColors[node.node_id] ?? "#4f8cff");
          if (nextColor) {
            pushMainHistory();
            setUiColors((current) => ({ ...current, [node.node_id]: nextColor.trim() }));
            setSaveStatus("dirty");
          }
        } },
        { label: t("common.addEditTags", "Add / edit tags"), onSelect: () => editUiTagsForIds([node.node_id], t("common.moduleTags", "Module tags")) },
        { label: t("common.createGroup", "Create group"), onSelect: () => editUiGroupForIds([node.node_id], t("common.moduleGroup", "Module group")) },
        { label: t("common.renameGroup", "Rename group"), onSelect: () => renameVisualGroup(node.node_id), disabled: !group },
        { label: t("common.dissolveGroup", "Dissolve group"), onSelect: () => dissolveVisualGroup(node.node_id), disabled: !group }
      ]);
      if (menu) {
        setMainContextMenu(menu);
      }
    },
    [
      dissolveVisualGroup,
      editUiGroupForIds,
      editUiTagsForIds,
      handleChildModulePreview,
      language,
      moduleNames,
      pushMainHistory,
      renameUiModule,
      renameVisualGroup,
      t,
      uiColors,
      uiGroups
    ]
  );

  const closeModuleTab = useCallback(
    (id: string) => {
      console.log("[NODE-D] closeModuleTab called:", { id });
      console.log("[P1-SYNC] Syncing tab close to store");
      const index = moduleTabs.indexOf(id);
      const next = moduleTabs.filter((tabId) => tabId !== id);
      setModuleTabs(next);
      setActiveModuleTabId((current) => (current === id ? next[Math.max(0, index - 1)] ?? null : current));
      // P1-BRIDGE：同时调用 store 的 closeModuleTab
      handleTabClosed(id);
      appendLog(`${t("status.moduleCanvasClosed", "Module canvas closed")}: ${id}`);
      // Trigger immediate autosave for moduleTabs
      console.log("[NODE-D] closeModuleTab autosave triggered");
      setSaveStatus("dirty");
    },
    [appendLog, moduleTabs, t]
  );

  const reorderModuleTab = useCallback((fromId: string, toId: string) => {
    console.log("[NODE-D] reorderModuleTab called:", { fromId, toId });
    setModuleTabs((tabs) => {
      const from = tabs.indexOf(fromId);
      const to = tabs.indexOf(toId);
      if (from === -1 || to === -1 || from === to) {
        return tabs;
      }
      const next = [...tabs];
      const [moved] = next.splice(from, 1);
      next.splice(to, 0, moved);
      console.log("[NODE-D] moduleTab reordered successfully");
      return next;
    });
    // Trigger immediate autosave for moduleTabs
    setSaveStatus("dirty");
  }, []);

  const pinModuleTab = useCallback((id: string) => {
    console.log("[NODE-D] pinModuleTab called:", { id });
    setModuleTabs((tabs) => {
      const nextTabs = !tabs.includes(id) || tabs[0] === id ? tabs : [id, ...tabs.filter((tabId) => tabId !== id)];
      console.log("[NODE-D] moduleTab pinned:", { id, wasAlreadyFirst: tabs[0] === id });
      return nextTabs;
    });
    // Trigger immediate autosave for moduleTabs
    setSaveStatus("dirty");
  }, []);

  const buildModuleAddMenu = useCallback(
    (layerNodeId: string): CanvasContextMenuItem[] => {
      const sortedLayers = (moduleCatalog?.layers ?? []).slice().sort((a, b) => catalogLayerOrder(a) - catalogLayerOrder(b));
      const layerGroups: CanvasContextMenuItem[] = [];
      for (const layer of sortedLayers) {
        const mods = modulesByCatalogLayerId.get(layer.layer_id) ?? [];
        if (!mods.length) {
          continue;
        }
        const layerName = i18nCandidate(language, [`layers.${layer.layer_id}`, `layer.${layer.layer_id}`], layer.layer_name);
        layerGroups.push({
          label: `L${layer.layer_order} ${layerName}`,
          children: mods.map((mod) => {
            const status = String(mod.status);
            const statusText = translate(language, `module.status.${status}`, status);
            return {
              label: `${moduleCatalogName(mod, (key, fallback) => translate(language, key, fallback))} · ${statusText}`,
              onSelect: () => addModuleToLayer(layerNodeId, moduleCatalogId(mod))
            };
          })
        });
      }
      if (!layerGroups.length) {
        return [{ label: t("module.empty", "暂无模块"), disabled: true }];
      }
      return layerGroups;
    },
    [addModuleToLayer, moduleCatalog, modulesByCatalogLayerId, language, t]
  );

  const openFolderContextMenu = useCallback(
    (event: ReactMouseEvent, layer: CatalogLayerInput) => {
      const menu = makeContextMenu(event, [
        {
          label: t("canvas.contextMenu.addModule", t("module.add", "添加模块")),
          children: buildModuleAddMenu(layer.layer_id)
        },
        { label: t("canvas.contextMenu.viewAllModules", t("module.viewAll")), onSelect: () => setFocusLayerId(layer.layer_id) },
        { label: t("canvas.contextMenu.removeAllModules", t("module.removeAll", "移除全部模块")), onSelect: () => removeAllModulesFromLayer(layer.layer_id), danger: true }
      ]);
      if (menu) {
        setMainContextMenu(menu);
      }
    },
    [buildModuleAddMenu, removeAllModulesFromLayer, t]
  );

  const openDroppedModuleContextMenu = useCallback(
    (event: ReactMouseEvent, layer: CatalogLayerInput, moduleId: string) => {
      const mod = moduleCatalogById.get(moduleId);
      const selectedInLayer = [...selectedLayerModuleKeys]
        .filter((key) => key.startsWith(`${layer.layer_id}:`))
        .map((key) => key.slice(layer.layer_id.length + 1))
        .filter((id) => moduleCatalogById.has(id));
      const targetModuleIds = selectedInLayer.includes(moduleId) ? selectedInLayer : [moduleId];
      const colorItems = MODULE_COLOR_SWATCHES.map((color, index) => ({
        label: `${index + 1}. ${t(MODULE_COLOR_LABEL_KEYS[index] ?? "module.color.custom", color)}`,
        onSelect: () => targetModuleIds.forEach((id) => setModuleColor(layer.layer_id, id, color))
      }));
      const menu = makeContextMenu(event, [
        { label: targetModuleIds.length > 1 ? `${targetModuleIds.length} ${t("module.count")}` : mod ? moduleCatalogName(mod, (key, fallback) => translate(language, key, fallback)) : moduleId, disabled: true },
        {
          label: t("module.open", "打开模组"),
          onSelect: () => openCatalogModuleCanvas(layer.layer_id, moduleId)
        },
        {
          label: t("module.colorMenu", "修改颜色"),
          children: colorItems
        },
        { label: t("module.viewAll"), onSelect: () => setFocusLayerId(layer.layer_id) },
        {
          label: t("module.remove", "移除"),
          onSelect: () => targetModuleIds.forEach((id) => removeModuleFromLayer(layer.layer_id, id)),
          danger: true
        }
      ]);
      if (menu) {
        setMainContextMenu(menu);
      }
    },
    [moduleCatalogById, openCatalogModuleCanvas, removeModuleFromLayer, selectedLayerModuleKeys, setModuleColor, t]
  );

  const openLayerWorkspace = useCallback(
    (layer: CatalogLayerInput, mode: WorkspaceMode) => {
      const catalogLayerName = moduleCatalog ? layerDisplayName(language, layer, moduleCatalog.layers.find((l) => l.layer_id === layer.layer_id)?.layer_name ?? "") : "";
      setSelectedNode(layer.layer_id);
      setActiveLayerId(layer.layer_id);
      setWorkspaceMode(mode);
      setExpandedLayerIds((ids) => {
        if (ids.has(layer.layer_id)) {
          return ids;
        }
        const next = new Set(ids);
        next.add(layer.layer_id);
        return next;
      });
      if (mode !== "inline") {
        setActiveWorkspaceId(layer.layer_id);
        setWorkspaceTabs((tabs) => (tabs.includes(layer.layer_id) ? tabs : [...tabs, layer.layer_id]));
      }
      if (mode === "window") {
        setFloatingLayerIds((ids) => (ids.includes(layer.layer_id) ? ids : [...ids, layer.layer_id]));
      }
      appendLog(`${t("status.layerOpened", "Layer opened")}: L${layer.layer_order} ${catalogLayerName}`);
    },
    [appendLog, language, moduleCatalog, setSelectedNode, t]
  );

  const flowNodes = useMemo<Node[]>(() => {
    if (!moduleCatalog) {
      return [];
    }
    const catalogLayersForRender = moduleCatalog.layers.slice().sort((a, b) => catalogLayerOrder(a) - catalogLayerOrder(b));
    // Layout positions/heights are derived ONLY from the canonical layer order, never
    // from how many modules are attached. The folder container is CSS-clamped to a
    // fixed height with a fixed 6-card rail, so adding/removing modules must not move
    // any LayerContainer / FolderGroup node. layerModules still drives card rendering
    // below (attachedModuleIds), just not the frame geometry.
    const stackFrames = computeLayerStackFrames(catalogLayersForRender, LAYOUT_MODULE_COUNTS);
    const folderNodes = catalogLayersForRender.map((layer) => {
      const layerId = layer.layer_id;
      const subnodes: WorkflowNode[] = [];
      const attachedModuleIds = moduleIdsForDisplayLayer(layerModules, layerId, moduleCatalogById);

      const attachedModules = attachedModuleIds
        .map((id) => {
          const mod = moduleCatalogById.get(id);
          if (!mod && moduleCatalog) {
            // 备用查询：直接从 moduleCatalog.modules 数组查询
            return moduleCatalog.modules.find((m) => m.module_id === id);
          }
          return mod;
        })
        .filter((module): module is ModuleCatalogEntryV04 => Boolean(module));
      const attachedModuleColors = Object.fromEntries(
        attachedModuleIds.map((id) => {
          const storedLayerId = storedLayerIdForModule(layerModules, id, layerId);
          return [id, moduleUiColors[`${layerId}:${id}`] ?? moduleUiColors[`${storedLayerId}:${id}`] ?? ""];
        })
      );
      const frame = stackFrames.get(layerId);
      if (!frame) {
        throw new Error(`Missing v0.4 module-catalog layer frame: ${layerId}`);
      }
      return buildFolderFlowNode({
        layer,
        moduleCatalog,
        frame,
        subnodes,
        attachedModules,
        attachedModuleIds,
        attachedModuleColors,
        focusedModuleId,
        selectedLayerModuleKeys,
        moduleNames,
        uiColors,
        onSelectNode: handleChildModuleSelect,
        onPreviewNode: handleChildModulePreview,
        onFocusNode: (node: WorkflowNode) => setFocusedModuleId(node.node_id),
        onDropModule: (moduleId: string) => addModuleToLayer(layerId, moduleId),
        onSelectDroppedModule: (moduleId: string, multi: boolean) => selectLayerModule(layerId, moduleId, multi),
        onOpenDroppedModule: (moduleId: string) => openCatalogModuleCanvas(layerId, moduleId),
        onRemoveModule: (moduleId: string) => removeModuleFromLayer(layerId, moduleId),
        onColorModule: (moduleId: string, color: string) => setModuleColor(layerId, moduleId, color),
        onOpenModuleFocus: () => setFocusLayerId(layerId),
        onContainerContextMenu: (event: ReactMouseEvent) => openFolderContextMenu(event, layer),
        onDroppedModuleContextMenu: (event: ReactMouseEvent, moduleId: string) => openDroppedModuleContextMenu(event, layer, moduleId),
        onModuleContextMenu: handleModuleContextMenu
      });
    });

    const layerSchemaNodes = catalogLayersForRender.map((layer) => {
      const frame = stackFrames.get(layer.layer_id);
      if (!frame) {
        throw new Error(`Missing v0.4 module-catalog layer frame: ${layer.layer_id}`);
      }
      return renderLayer({
        layer,
        moduleCatalog,
        frame,
        uiTags,
        uiGroups,
        uiColors,
        onColor: (layerId: string, color: string) => {
          setUiColors((current) => ({ ...current, [layerId]: color }));
          setSaveStatus("dirty");
        },
        onOpenAssembly: (targetLayer) => {
          const catalogLayerName = layerDisplayName(language, targetLayer, moduleCatalog.layers.find((item) => item.layer_id === targetLayer.layer_id)?.layer_name ?? "");
          setSelectedNode(targetLayer.layer_id);
          setActiveLayerId(targetLayer.layer_id);
          setWorkspaceMode("inline");
          setExpandedLayerIds((ids) => {
            const next = new Set(ids);
            if (ids.has(targetLayer.layer_id)) {
              next.delete(targetLayer.layer_id);
              return next;
            }
            next.add(targetLayer.layer_id);
            return next;
          });
          setActiveWorkspaceId(null);
          setActiveModuleTabId(null);
          appendLog(`${t("status.layerOpened", "Layer opened")}: L${targetLayer.layer_order} ${catalogLayerName}`);
        },
        t
      });
    });

    const layerAssemblyNodes = catalogLayersForRender.flatMap((layer) => {
      if (!expandedLayerIds.has(layer.layer_id)) {
        return [];
      }
      const frame = stackFrames.get(layer.layer_id);
      if (!frame) {
        throw new Error(`Missing v0.4 module-catalog layer frame: ${layer.layer_id}`);
      }
      const trunkPosition = LayerStackLayoutEngine.computeTrunkPosition(frame);
      return [
        {
          id: `ui-assembly-${layer.layer_id}`,
          type: "layerAssemblyPanel",
          position: { x: trunkPosition.x + TRUNK_LAYER_WIDTH + LAYER_ASSEMBLY_PANEL_GAP, y: trunkPosition.y },
          draggable: false,
          selectable: false,
          data: {
            layer,
            moduleCatalog,
            edges,
            t,
            moduleNames,
            onOpen: openLayerWorkspace,
            onSelectNode: handleChildModuleSelect,
            onPreviewNode: handleChildModulePreview
          } satisfies LayerAssemblyPanelNodeData
        } satisfies Node
      ];
    });

    return [...folderNodes, ...layerSchemaNodes, ...layerAssemblyNodes];
  }, [
    addModuleToLayer,
    appendLog,
    edges,
    expandedLayerIds,
    focusedModuleId,
    handleChildModulePreview,
    handleChildModuleSelect,
    handleModuleContextMenu,
    language,
    layerModules,
    moduleCatalog,
    moduleCatalogById,
    moduleNames,
    moduleUiColors,
	    openCatalogModuleCanvas,
    openDroppedModuleContextMenu,
    openFolderContextMenu,
    openLayerWorkspace,
    selectLayerModule,
    selectedLayerModuleKeys,
    setModuleColor,
    setSelectedNode,
    t,
    uiGroups,
    uiColors,
    uiTags
  ]);

  const flowEdges = useMemo<Edge[]>(() => {
    const catalogLayersForRender = (moduleCatalog?.layers ?? []).slice().sort((a, b) => catalogLayerOrder(a) - catalogLayerOrder(b));
    const folderToLayerEdges = catalogLayersForRender.map((layer) => buildFolderToLayerEdge(layer));
    const layerSpineEdges = catalogLayersForRender.slice(0, -1).map((layer, index) => buildLayerSpineEdge(layer, catalogLayersForRender[index + 1]));
    return [...folderToLayerEdges, ...layerSpineEdges];
  }, [moduleCatalog]);

  const workflowWithModuleGraphs = useCallback(
    (baseWorkflow: Workflow): Workflow => {
      if (!moduleCatalog) {
        return baseWorkflow;
      }
      const storeGraphs = useCanvasStore.getState().moduleGraphs;
      const overrides = new Map<string, Record<string, unknown>>();
      for (const catalogModule of moduleCatalog.modules) {
        const registryInstance = Object.values(moduleInstanceRegistry).find((instance) => instance.moduleId === catalogModule.module_id);
        const preferredInstanceId = registryInstance?.instanceId ?? `${catalogModule.layer_id}${MODULE_INSTANCE_SEPARATOR}${catalogModule.module_id}`;
        const graphId = bestModuleGraphId(catalogModule.module_id, preferredInstanceId, storeGraphs, catalogModule);
        const graph = storeGraphs[graphId] ?? loadModuleGraphState(graphId);
        const graphNodes = graph?.nodes ?? [];
        if (!graphNodes.length) {
          continue;
        }
        overrides.set(catalogModule.module_id, moduleWithCompiledGraph(catalogModule, graphNodes, graph?.edges ?? []));
      }
      const modules: Workflow["modules"] = moduleCatalog.modules.map((module) => {
        const compiled = overrides.get(module.module_id);
        const baseModule = compiled ?? withoutLegacyModuleOutputFallback(safeClone(module) as Record<string, unknown>);
        return {
          ...baseModule,
          module_id: module.module_id,
          module_name: module.module_name,
          layer_id: module.layer_id,
        };
      });
      return {
        ...baseWorkflow,
        modules,
      };
    },
    [moduleCatalog, moduleCatalogById, moduleInstanceRegistry]
  );

  const requireWorkflow = useCallback(() => {
    if (!workflow) {
      appendLog(t("error.noWorkflow"), "warn");
      return null;
    }
    return workflowWithModuleGraphs(workflow);
  }, [appendLog, t, workflow, workflowWithModuleGraphs]);

  const handleSave = useCallback(() => {
    const currentWorkflow = requireWorkflow();
    if (!currentWorkflow) {
      setSaveStatus("error");
      return;
    }
    downloadWorkflow(currentWorkflow);
    setSaveStatus("saved");
    setRequiresDrRecompile(true);
    appendLog(t("status.saved"));
  }, [appendLog, requireWorkflow, t]);

  const handleValidate = useCallback(async () => {
    const currentWorkflow = requireWorkflow();
    if (!currentWorkflow) {
      return;
    }

    try {
      const result = await api.validateWorkflow(currentWorkflow);
      setValidation(result);
      appendLog(`${t("status.validated")}: ${result.audit.status}`);
      setBottomTab("logs");
      setActiveDrawer("logs");
    } catch (error) {
      appendLog(`${t("error.api")}: ${(error as Error).message}`, "error");
    }
  }, [appendLog, requireWorkflow, setValidation, t]);

  // Stage 6 Runtime Kernel: the "运行 / Run" button dispatches one resident step
  // to the backend Execution Engine (POST /runtime/resident/step) — the sole
  // runtime entry. The v0.3 workflow adapter is no longer the execution path and
  // its backend-only warning fallback is gone. The UI never executes a workflow
  // or calls a provider directly; it only hydrates the response into the panels.
  const RESIDENT_ID = "resident_v1";
  const handleMockRun = useCallback(async () => {
    const currentWorkflow = requireWorkflow();
    if (!currentWorkflow) {
      return;
    }
    // input: from the current node selection, else the canvas/workflow name.
    const nodeLabel = selectedNode?.title_fallback || selectedNode?.node_id || "";
    const inputText =
      nodeLabel || currentWorkflow.name || currentWorkflow.template_type || "manual run";

    appendLog(`${t("status.runtimeDispatch", "Runtime dispatch")} → /runtime/resident/step (input: ${inputText})`);
    setBottomTab("logs");
    setActiveDrawer("logs");
    try {
      const response = await api.executeResidentStep(currentWorkflow, inputText, RESIDENT_ID);
      // Minimal hydration layer maps trace -> logs, memory -> artifacts, etc.
      applyRuntimeResult(response);
    } catch (error) {
      appendLog(`${t("error.api")}: ${(error as Error).message}`, "error");
    }
  }, [appendLog, applyRuntimeResult, requireWorkflow, selectedNode, setActiveDrawer, setBottomTab, t]);

  // Stage 6.3.3 step 1 — Compile DR: validate the canvas (no download). The
  // result (valid/errors/warnings/audits/pseudo_dag) is saved to the store.
  const handleCompileDR = useCallback(async () => {
    const currentWorkflow = requireWorkflow();
    if (!currentWorkflow) {
      return;
    }
    const normalizedReferences = normalizeWorkflowReferenceInputs(currentWorkflow);
    const referenceStats = normalizedReferences.stats;
    setBottomTab("logs");
    setActiveDrawer("logs");
    appendLog(
      `[reference-input] pure pointer normalize: ${referenceStats.beforeCount} -> ${referenceStats.afterCount}; invalid=${referenceStats.invalidCount}; duplicates=${referenceStats.duplicateCount}; stripped=${referenceStats.strippedCount}; cycles=${referenceStats.cycleCount}`,
      referenceStats.invalidCount > 0 || referenceStats.cycleCount > 0 ? "warn" : "info"
    );
    for (const sample of referenceStats.invalidSamples) {
      appendLog(`[reference-input] ${sample}`, "warn");
    }
    await compileDR(sanitizeWorkflowForDrCompile(normalizedReferences.workflow));
    if (useCanvasStore.getState().canExportDR) {
      setRequiresDrRecompile(false);
    }
  }, [appendLog, compileDR, requireWorkflow, setActiveDrawer, setBottomTab]);

  // Stage 6.3.3 step 2 — Export .digital_resident: download the already-validated
  // compiled DR. Disabled in the UI unless a valid DR was compiled first.
  const handleExportDR = useCallback(async () => {
    setBottomTab("logs");
    setActiveDrawer("logs");
    if (requiresDrRecompile) {
      appendLog(t("status.drExport.needsRecompile", "Saved canvas changes need a new DR compile before export."), "warn");
      return;
    }
    await exportDR();
  }, [appendLog, exportDR, requiresDrRecompile, setActiveDrawer, setBottomTab, t]);

  const handleExportAuditDR = useCallback(async () => {
    setBottomTab("logs");
    setActiveDrawer("logs");
    if (requiresDrRecompile) {
      appendLog(t("status.drAuditExport.needsRecompile", "Saved canvas changes need a new DR compile before audit export."), "warn");
      return;
    }
    await exportAuditDR();
  }, [appendLog, exportAuditDR, requiresDrRecompile, setActiveDrawer, setBottomTab, t]);

  const handleExportPreview = useCallback(async () => {
    const currentWorkflow = requireWorkflow();
    if (!currentWorkflow) {
      return;
    }

    try {
      const result = await api.exportPreview(currentWorkflow, "workflow_json");
      setExportPreview(result.preview);
      appendLog(`${t("status.exportPreview")}: ${result.preview.export_kind}`);
      setBottomTab("preview");
      setActiveDrawer("preview");
    } catch (error) {
      appendLog(`${t("error.api")}: ${(error as Error).message}`, "error");
    }
  }, [appendLog, requireWorkflow, setExportPreview, t]);

  const handleTemplateClick = useCallback(
    async (templateType: string) => {
      if (loadingTemplateType) {
        return;
      }
      clearRunOutput();

      if (templateType === "persona_builder") {
        setLoadingTemplateType(templateType);
        appendLog(`${t("status.templateLoading", "Loading template")}: ${t(`template.${templateType}`, templateType)}`);
        try {
          // CLEAN V4: persona_builder reuses the v0.4 module-catalog schema as its
          // canvas data source (the internal `schema_v04` source). No
          // createPersonaBuilder / v0.3 workflow source.
          const catalog = await api.fetchModuleCatalog();
          setModuleCatalog(catalog);
          setCatalogRevision((revision) => revision + 1);
          setSaveStatus("saved");
          setActiveLayerId(null);
          setExpandedLayerIds(new Set());
          setActiveWorkspaceId(null);
          setWorkspaceTabs([]);
          setFloatingLayerIds([]);
          setFloatingNodeIds([]);
          setResidentPreviewOutput(null);
          setDraggedNodeIds(new Set());
          setModuleTabs([]);
          setActiveModuleTabId(null);
          setNodeLibraryCollapsed(true);
          setLibraryBodyCollapsed(true);
          setActiveDrawer("layers");
          setApiReady(true);
          appendLog(t("status.personaLoaded"));
        } catch (error) {
          setApiReady(false);
          setBottomTab("logs");
          setActiveDrawer("logs");
          appendLog(`${t("error.api")}: ${(error as Error).message}`, "error");
        } finally {
          setLoadingTemplateType(null);
        }
        return;
      }

      appendLog(
        `${t("status.templateUnavailable", language === "zh" ? "暂未开放" : "Not available yet")}: ${t(`template.${templateType}`, templateType)}`,
        "warn"
      );
    },
    [appendLog, clearRunOutput, language, loadingTemplateType, setApiReady, t]
  );

  const toggleLayerCollapsed = useCallback(
    (layer: CatalogLayerInput) => {
      setCollapsedLayerIds((current) => {
        const next = new Set(current);
        if (next.has(layer.layer_id)) {
          next.delete(layer.layer_id);
          appendLog(`${t("status.layerExpanded", "Layer expanded")}: L${layer.layer_order}`);
        } else {
          next.add(layer.layer_id);
          appendLog(`${t("status.layerCollapsed", "Layer collapsed")}: L${layer.layer_order}`);
        }
        return next;
      });
    },
    [appendLog, t]
  );

  const closeWorkspaceTab = useCallback(
    (nodeId: string) => {
      setWorkspaceTabs((tabs) => tabs.filter((id) => id !== nodeId));
      setFloatingLayerIds((ids) => ids.filter((id) => id !== nodeId));
      if (activeWorkspaceId === nodeId) {
        setActiveWorkspaceId(null);
      }
      appendLog(`${t("status.workspaceClosed", "Workspace closed")}: ${nodeId}`);
    },
    [activeWorkspaceId, appendLog, t]
  );

  const handleNodeClick: NodeMouseHandler = useCallback(
    (_event, node) => {
      if (node.id.startsWith("ui-folder-")) {
        const layerId = node.id.slice("ui-folder-".length);
        const layer = layerById.get(layerId);
        if (layer) {
          setSelectedNode(layer.layer_id);
          setActiveLayerId(layer.layer_id);
        }
        return;
      }
      setSelectedNode(node.id);
      const layer = layerById.get(node.id);
      if (layer) {
        setActiveLayerId(layer.layer_id);
        setExpandedLayerIds((ids) => {
          if (ids.has(layer.layer_id)) {
            return ids;
          }
          const next = new Set(ids);
          next.add(layer.layer_id);
          return next;
        });
      }
    },
    [layerById, setSelectedNode]
  );

  const handleNodeDoubleClick: NodeMouseHandler = useCallback(
    (_event, node) => {
      if (node.id.startsWith("ui-folder-")) {
        return;
      }
      const [layerNodeId, moduleId] = node.id.split(MODULE_INSTANCE_SEPARATOR);
      if (layerNodeId && moduleId) {
        openCatalogModuleCanvas(layerNodeId, moduleId);
        return;
      }
      const schemaNode = (node.data as { schemaNode?: WorkflowNode } | undefined)?.schemaNode;
      if (schemaNode?.type === "module") {
        handleChildModulePreview(schemaNode);
        return;
      }
      setSelectedNode(node.id);
    },
    [handleChildModulePreview, openCatalogModuleCanvas, setSelectedNode]
  );

  const handlePaneClick = useCallback(() => {
    setSelectedNode(null);
    setMainContextMenu(null);
  }, [setSelectedNode]);

  const handleNodesChange = useCallback(
    (changes: NodeChange[]) => {
      changes.forEach((change) => {
        if (change.type === "select" && change.selected) {
          if (change.id.startsWith("ui-folder-")) {
            return;
          }
          setSelectedNode(change.id);
        }
        if (change.type === "select") {
          setSelectedFlowNodeIds((current) => {
            const next = new Set(current);
            if (change.selected) {
              next.add(change.id);
            } else {
              next.delete(change.id);
            }
            return next;
          });
        }
      });
    },
    [setSelectedNode]
  );

  const handleEdgesChange = useCallback(() => undefined, []);

  const handleConnect = useCallback(
    (_connection: Connection) => {
      appendLog(t("status.schemaOnly", "Schema-only canvas: workflow graph editing is disabled."), "warn");
    },
    [appendLog, t]
  );

  const handleNodesDelete = useCallback(
    (_deleted: Node[]) => {
      appendLog(t("status.schemaOnly", "Schema-only canvas: workflow graph editing is disabled."), "warn");
    },
    [appendLog, t]
  );

  const addMainNodeAt = useCallback(
    (_type: ModuleNodeType, _position: { x: number; y: number }) => {
      appendLog(t("status.schemaOnly", "Schema-only canvas: workflow graph editing is disabled."), "warn");
    },
    [appendLog, t]
  );

  const handleAddNode = useCallback(
    (type: ModuleNodeType) => {
      if (activeModuleTabId) {
        setPendingModuleAdd({
          requestId: Date.now() + Math.random(),
          moduleId: activeModuleTabId,
          nodeType: type
        });
        appendLog(`${t("status.nodeAdded", "Node added")}: ${type}`);
        return;
      }

      addMainNodeAt(type, { x: 160, y: -160 });
    },
    [activeModuleTabId, addMainNodeAt, appendLog, t]
  );

  const handleMainCanvasDrop = useCallback(
    (event: ReactDragEvent) => {
      event.preventDefault();
      if (readModuleDragId(event)) {
        appendLog(t("status.moduleDropLeftOnly", "Drag modules into the left module container"), "warn");
        return;
      }
      const type = readNodeDragType(event);
      if (!type) {
        return;
      }
      const instance = mainFlowRef.current;
      const position = instance?.screenToFlowPosition
        ? instance.screenToFlowPosition({ x: event.clientX, y: event.clientY })
        : { x: 160, y: -160 };
      addMainNodeAt(type, position);
    },
    [addMainNodeAt, appendLog, t]
  );

  const deleteMainNodeById = useCallback(
    (nodeId: string) => {
      const schemaNode = nodes.find((node) => node.node_id === nodeId);
      if (!schemaNode) {
        return;
      }
      if (schemaNode.type === "layer_container") {
        appendLog(t("status.layerDeleteBlocked", "Layer containers cannot be deleted"), "warn");
        return;
      }
      appendLog(t("status.schemaOnly", "Schema-only canvas: workflow graph editing is disabled."), "warn");
    },
    [appendLog, nodes, t]
  );

  const copyMainNodeById = useCallback(
    (nodeId: string) => {
      const schemaNode = nodes.find((node) => node.node_id === nodeId);
      if (!schemaNode || schemaNode.type === "layer_container") {
        appendLog(t("status.copyUnavailable", "Copy is unavailable for this node"), "warn");
        return;
      }
      appendLog(t("status.schemaOnly", "Schema-only canvas: workflow graph editing is disabled."), "warn");
    },
    [appendLog, nodes, t]
  );

  const pasteMainNode = useCallback(() => {
    appendLog(t("status.schemaOnly", "Schema-only canvas: workflow graph editing is disabled."), "warn");
  }, [appendLog, t]);

  const resetMainArrangement = useCallback(() => {
    pushMainHistory();
    setDraggedNodeIds(new Set());
    appendLog(t("status.canvasArranged", "Canvas arranged"));
  }, [appendLog, pushMainHistory, t]);

  const resetMainNodeUiById = useCallback(
    (nodeId: string) => {
      pushMainHistory();
      setUiColors((current) => ({ ...current, [nodeId]: "" }));
      setUiNodeNames((current) => ({ ...current, [nodeId]: "" }));
      setUiTags((current) => ({ ...current, [nodeId]: [] }));
      setUiGroups((current) => ({ ...current, [nodeId]: "" }));
      setSaveStatus("dirty");
      appendLog(`${t("status.nodeReset", "Node reset")}: ${nodeId}`);
    },
    [appendLog, pushMainHistory, t]
  );

  const handleMainNodeContextMenu: NodeMouseHandler = useCallback(
    (event, node) => {
      const schemaNode = (node.data as { schemaNode?: WorkflowNode } | undefined)?.schemaNode;
      if (!schemaNode) {
        return;
      }
      setSelectedNode(node.id);
	      const label = uiNodeNames[node.id] ?? translate(language, schemaNode.title_key, schemaNode.title_fallback);
	      const group = uiGroups[node.id] ?? "";
	      const isLayer = schemaNode.type === "layer_container";
      const menu = makeContextMenu(event, [
        { label: t("toolbar.undo", "撤销"), onSelect: handleUndo, disabled: !canUndoMain },
        { label: t("toolbar.redo", "重做"), onSelect: handleRedo, disabled: !canRedoMain },
        { label: t("menu.autoArrangeNodes", "自动整理节点"), onSelect: resetMainArrangement },
        ...(isLayer
          ? [
              { label: t("module.add", "添加模块"), children: buildModuleAddMenu(node.id) },
              { label: t("module.viewAll"), onSelect: () => setFocusLayerId(node.id) }
            ]
          : []),
        { label: t("common.rename", "重命名"), onSelect: () => renameUiNode(node.id, label) },
        { label: t("common.color", "颜色"), onSelect: () => {
          const nextColor = window.prompt(t("field.color", "Color"), uiColors[node.id] ?? "#4f8cff");
          if (nextColor) {
            pushMainHistory();
            setUiColors((current) => ({ ...current, [node.id]: nextColor.trim() }));
            setSaveStatus("dirty");
          }
        } },
        { label: t("common.reset", "Reset"), onSelect: () => resetMainNodeUiById(node.id) },
        { label: t("common.delete", "删除节点"), onSelect: () => deleteMainNodeById(node.id), disabled: isLayer, danger: true },
        { label: t("common.copy", "复制节点"), onSelect: () => copyMainNodeById(node.id), disabled: isLayer },
        { label: t("common.tags", "添加 / 编辑标签"), onSelect: () => editUiTagsForIds([node.id], t("common.tags", "Tags")) },
        { label: t("common.group", "创建分组"), onSelect: () => editUiGroupForIds([node.id], t("common.group", "Group")) },
        { label: t("common.rename", "重命名分组"), onSelect: () => renameVisualGroup(node.id), disabled: !group },
        { label: t("common.delete", "解散分组"), onSelect: () => dissolveVisualGroup(node.id), disabled: !group }
      ]);
      if (menu) {
        setMainContextMenu(menu);
      }
    },
    [
      buildModuleAddMenu,
      canRedoMain,
      canUndoMain,
      copyMainNodeById,
      deleteMainNodeById,
      dissolveVisualGroup,
      editUiGroupForIds,
      editUiTagsForIds,
      handleRedo,
      handleUndo,
      language,
      pushMainHistory,
      renameUiNode,
      renameVisualGroup,
      resetMainNodeUiById,
      resetMainArrangement,
      setSelectedNode,
      t,
      uiColors,
      uiGroups,
      uiNodeNames
    ]
  );

  const handleMainEdgeContextMenu = useCallback(
    (event: ContextMenuEvent, _edge: Edge) => {
      const menu = makeContextMenu(event, [
        {
          label: t("common.deleteEdge", "Delete edge"),
          onSelect: () => appendLog(t("status.schemaOnly", "Schema-only canvas: workflow graph editing is disabled."), "warn"),
          danger: true
        }
      ]);
      if (menu) {
        setMainContextMenu(menu);
      }
    },
    [appendLog, t]
  );

  const selectedMainIds = useMemo(() => {
    const ids = selectedFlowNodeIds.size ? [...selectedFlowNodeIds] : selectedNodeId ? [selectedNodeId] : [];
    return ids.filter((id) => !id.startsWith("ui-folder-"));
  }, [selectedFlowNodeIds, selectedNodeId]);

  const selectedCanvasIds = useMemo(() => {
    const ids = selectedFlowNodeIds.size ? [...selectedFlowNodeIds] : selectedNodeId ? [selectedNodeId] : [];
    return ids.filter(Boolean);
  }, [selectedFlowNodeIds, selectedNodeId]);

  const applyMainLayout = useCallback(
    (_nextFlowNodes: Node[]) => {
      appendLog(t("status.schemaOnly", "Schema-only canvas: workflow graph layout edits are disabled."), "warn");
    },
    [appendLog, t]
  );

  const applyMainAlignment = useCallback(
    (action: AlignAction) => {
      if (selectedCanvasIds.length < 2) {
        appendLog(t("status.selectMultipleFirst", "Select multiple nodes first"), "warn");
        return;
      }
      applyMainLayout(alignFlowNodes(flowNodes, new Set(selectedCanvasIds), action));
    },
    [appendLog, applyMainLayout, flowNodes, selectedCanvasIds, t]
  );

  const applyMainDistribution = useCallback(
    (action: DistributeAction) => {
      if (selectedCanvasIds.length < 3) {
        appendLog(t("status.selectThreeFirst", "Select at least three nodes first"), "warn");
        return;
      }
      applyMainLayout(distributeFlowNodes(flowNodes, new Set(selectedCanvasIds), action));
    },
    [appendLog, applyMainLayout, flowNodes, selectedCanvasIds, t]
  );

  const deleteSelectedMain = useCallback(() => {
    appendLog(t("status.schemaOnly", "Schema-only canvas: workflow graph editing is disabled."), "warn");
  }, [appendLog, t]);

  const editSelectedMainColor = useCallback(() => {
    if (!selectedCanvasIds.length) {
      appendLog(t("status.selectNodeFirst", "Select a node first"), "warn");
      return;
    }
    const firstId = selectedCanvasIds[0];
    const nextColor = window.prompt(t("field.color", "Color"), uiColors[firstId] ?? "#4f8cff");
    if (!nextColor) {
      return;
    }
    pushMainHistory();
    setUiColors((current) => {
      const next = { ...current };
      for (const id of selectedCanvasIds) {
        next[id] = nextColor.trim();
      }
      return next;
    });
    setSaveStatus("dirty");
  }, [appendLog, pushMainHistory, selectedCanvasIds, t, uiColors]);

  const editSelectedMainTags = useCallback(() => {
    if (!selectedMainIds.length) {
      appendLog(t("status.selectNodeFirst", "Select a node first"), "warn");
      return;
    }
    const firstId = selectedMainIds[0];
    const currentText = (uiTags[firstId] ?? []).join(", ");
    const nextTags = window.prompt("Tags", currentText);
    if (nextTags === null) {
      return;
    }
    const tags = nextTags
      .split(",")
      .map((tag) => tag.trim())
      .filter(Boolean);
    pushMainHistory();
    setUiTags((current) => {
      const next = { ...current };
      for (const id of selectedMainIds) {
        next[id] = tags;
      }
      return next;
    });
    setSaveStatus("dirty");
  }, [appendLog, pushMainHistory, selectedMainIds, t, uiTags]);

  const editSelectedMainGroup = useCallback(() => {
    if (!selectedMainIds.length) {
      appendLog(t("status.selectNodeFirst", "Select a node first"), "warn");
      return;
    }
    const firstId = selectedMainIds[0];
    const nextGroup = window.prompt("Visual group", uiGroups[firstId] ?? "");
    if (nextGroup === null) {
      return;
    }
    pushMainHistory();
    setUiGroups((current) => {
      const next = { ...current };
      for (const id of selectedMainIds) {
        next[id] = nextGroup.trim();
      }
      return next;
    });
    setSaveStatus("dirty");
  }, [appendLog, pushMainHistory, selectedMainIds, t, uiGroups]);

  // All canvas/toolbar actions are now reached via the blank-canvas right-click
  // menu (the on-screen top toolbar and bottom-left quick-actions were removed).
  const handleMainPaneContextMenu = useCallback(
    (event: ContextMenuEvent) => {
      const instance = mainFlowRef.current;
      const dropPos = instance?.screenToFlowPosition
        ? instance.screenToFlowPosition({ x: event.clientX, y: event.clientY })
        : { x: 160, y: -160 };
      const hasSelection = selectedCanvasIds.length > 0;
      const items: CanvasContextMenuItem[] = [
        { label: t("toolbar.undo", "撤销"), onSelect: handleUndo, disabled: !canUndoMain },
        { label: t("toolbar.redo", "重做"), onSelect: handleRedo, disabled: !canRedoMain },
        { label: t("menu.autoArrangeNodes", "自动整理节点"), onSelect: resetMainArrangement },
        {
          label: t("menu.addNode", "添加节点"),
          children: libraryNodeTypes.map((type) => ({
            label: getNodeTypeLabel(type, t),
            onSelect: () => addMainNodeAt(type, dropPos)
          }))
        },
        {
          label: t("menu.alignDistribute", "对齐 / 分布"),
          disabled: !hasSelection,
          children: [
            { label: t("align.left", "左对齐"), onSelect: () => applyMainAlignment("left") },
            { label: t("align.right", "右对齐"), onSelect: () => applyMainAlignment("right") },
            { label: t("align.top", "上对齐"), onSelect: () => applyMainAlignment("top") },
            { label: t("align.bottom", "下对齐"), onSelect: () => applyMainAlignment("bottom") },
            { label: t("align.distributeX", "水平分布"), onSelect: () => applyMainDistribution("horizontal") },
            { label: t("align.distributeY", "垂直分布"), onSelect: () => applyMainDistribution("vertical") }
          ]
        },
	        { label: t("menu.paste", "粘贴节点"), onSelect: pasteMainNode, disabled: true },
        {
          label: t("menu.viewActions", "视图"),
          children: [
            { label: t("menu.fitView", "适配视图"), onSelect: () => mainFlowRef.current?.fitView() },
            { label: t("menu.centerCanvas", "居中画布"), onSelect: () => mainFlowRef.current?.fitView({ padding: 0.34 }) },
            { label: t("menu.arrange", "整理节点"), onSelect: resetMainArrangement },
            { label: showGrid ? t("menu.hideGrid", "隐藏网格") : t("menu.showGrid", "显示网格"), onSelect: () => setShowGrid((value) => !value) },
            { label: showMiniMap ? t("menu.hideMiniMap", "隐藏小地图") : t("menu.showMiniMap", "显示小地图"), onSelect: () => setShowMiniMap((value) => !value) }
          ]
        },
        { label: t("toolbar.run", "运行"), onSelect: handleMockRun },
        { label: t("toolbar.save", "保存"), onSelect: handleSave },
        { label: t("toolbar.export", "导出"), onSelect: handleExportPreview },
        { label: t("toolbar.delete", "删除"), onSelect: deleteSelectedMain, disabled: !hasSelection, danger: true }
      ];
      const menu = makeContextMenu(event, items);
      if (menu) {
        setMainContextMenu(menu);
      }
    },
    [
      addMainNodeAt,
      applyMainAlignment,
      applyMainDistribution,
      canRedoMain,
      canUndoMain,
	      deleteSelectedMain,
      editSelectedMainColor,
      editSelectedMainGroup,
      editSelectedMainTags,
      handleExportPreview,
      handleMockRun,
      handleRedo,
      handleSave,
      handleUndo,
      pasteMainNode,
	      resetMainArrangement,
      selectedCanvasIds.length,
      showGrid,
      showMiniMap,
      t,
	    ]
	  );

  const handleMainFlowContextMenuCapture = useCallback(
    (event: ReactMouseEvent<HTMLDivElement>) => {
      if (shouldSkipCanvasContextCapture(event.target) || shouldLetReactFlowElementContextMenuHandle(event.target)) {
        return;
      }
      handleMainPaneContextMenu(event);
    },
    [handleMainPaneContextMenu]
  );

  const selectedLayerModuleKey = useMemo(() => [...selectedLayerModuleKeys][0] ?? "", [selectedLayerModuleKeys]);
  const selectedLayerModule = useMemo(() => {
    if (!selectedLayerModuleKey) {
      return null;
    }
    const separatorIndex = selectedLayerModuleKey.indexOf(":");
    if (separatorIndex < 0) {
      return null;
    }
    const layerId = selectedLayerModuleKey.slice(0, separatorIndex);
    const moduleId = selectedLayerModuleKey.slice(separatorIndex + 1);
    return {
      layerId,
      moduleId,
      module: moduleCatalogById.get(moduleId) ?? null,
    };
  }, [moduleCatalogById, selectedLayerModuleKey]);

  const mainAssistantRequest = useMemo<StudioAssistantRequest>(() => {
    const layerId =
      selectedLayerModule?.layerId ??
      activeLayer?.layer_id ??
      (selectedNodeId && layerById.has(selectedNodeId) ? selectedNodeId : undefined);
    const neighborModules = layerId
      ? moduleIdsForDisplayLayer(layerModules, layerId, moduleCatalogById)
          .map((moduleId) => moduleCatalogById.get(moduleId))
          .filter((module): module is ModuleCatalogEntryV04 => Boolean(module))
      : [];
    return {
      canvas_id: workflow?.template_type ?? "schema_v04",
      layer_id: layerId,
      module_id: selectedLayerModule?.moduleId,
      node_id: selectedNode?.node_id ?? selectedNodeId ?? undefined,
      field_key: undefined,
      selected_text: "",
      mode: "explain",
      context: {
        resident_identity: {
          source_layer: "layer_1",
        },
        current_layer: layerId ? layerById.get(layerId) ?? null : null,
        current_module: selectedLayerModule?.module ?? null,
        current_node: selectedNode,
        field_references: [],
        neighbor_modules: neighborModules,
      },
    };
  }, [
    activeLayer,
    layerById,
    layerModules,
    moduleCatalogById,
    selectedLayerModule,
    selectedNode,
    selectedNodeId,
    workflow?.template_type,
  ]);

  const handleMainAssistantPatch = useCallback(
    (_patch: StudioAssistantPatch) => {
      appendLog(t("assistant.status.noEditableField", "Open a module field before applying assistant suggestions."), "warn");
    },
    [appendLog, t]
  );

  const handleModuleAssistantPanelChange = useCallback((panel: ModuleAssistantPanelState | null) => {
    setModuleAssistantPanel(panel);
  }, []);

  const splitLayer = workspaceMode === "split" ? selectedLayer : null;
  const residentInstance = extractResidentInstance(residentPreviewOutput);
  const assistantPanel = activeModuleNode && moduleAssistantPanel
    ? moduleAssistantPanel
    : {
        title: t("assistant.panel.title", "Assistant"),
        meta: t("assistant.panel.meta", "Studio canvas"),
        request: mainAssistantRequest,
        canApplyPatch: false,
        onApplyPatch: handleMainAssistantPatch,
      };
  const rightPanelExpanded = assistantPanelOpen || residentPreviewPanelOpen || residentNeuralGraphPanelOpen;
  const templateIsLoading = Boolean(loadingTemplateType);
  const toggleDrawer = useCallback(
    (drawer: DrawerId) => {
      setActiveDrawer((current) => (current === drawer ? null : drawer));
      if (drawer === "logs" || drawer === "artifacts" || drawer === "preview") {
        setBottomTab(drawer);
      }
    },
    []
  );

  return (
    <main className="canvas-shell">
      <header className="top-toolbar">
        <div className="brand">
          <div className="brand-copy">
            <strong>{t("app.title")}</strong>
            <span>{t("app.subtitle")}</span>
          </div>
          <div className="template-select">
            <span>{t("panel.templates")}</span>
            <select
              value={selectedTemplateType}
              onChange={(event) => {
                setSelectedTemplateType(event.target.value);
                handleTemplateClick(event.target.value);
              }}
            >
              {templateOptions.map((templateType) => (
                <option key={templateType} value={templateType}>
                  {t(`template.${templateType}`, templateType)}
                </option>
              ))}
            </select>
            <button
              type="button"
              className="template-load-button"
              disabled={templateIsLoading}
              onClick={() => handleTemplateClick(selectedTemplateType)}
            >
              {templateIsLoading ? t("common.loading", "加载中") : t("toolbar.load")}
            </button>
          </div>
        </div>
        <div className="toolbar-actions">
	          <div className="run-bar" aria-label={t("toolbar.actionsLabel")}>
	            <button onClick={handleSave}>{t("toolbar.save")}</button>
	            <details className="toolbar-menu">
	              <summary>{t("toolbar.run")}</summary>
	              <div className="toolbar-menu__items" aria-label={t("toolbar.runActionsLabel")}>
	                <button onClick={handleValidate}>{t("toolbar.validate")}</button>
	                <button onClick={handleMockRun}>{t("toolbar.mockRun")}</button>
	                <button onClick={handleExportPreview}>{t("toolbar.exportPreview")}</button>
	              </div>
	            </details>
	            <details className="toolbar-menu">
	              <summary>{t("toolbar.file")}</summary>
	              <div className="toolbar-menu__items" aria-label={t("toolbar.fileActionsLabel")}>
	                <button className="compile-dr-button" onClick={handleCompileDR}>{t("toolbar.compileFile")}</button>
	                <button
	                  className="export-dr-button"
	                  onClick={handleExportDR}
	                  disabled={!canExportDR}
	                  title={canExportDR ? undefined : t("toolbar.exportFileBlocked")}
	                >
	                  {t("toolbar.exportFile")}
	                </button>
	                <button
	                  className="export-dr-audit-button"
	                  onClick={handleExportAuditDR}
	                  disabled={!canExportDR}
	                  title={canExportDR ? undefined : t("toolbar.exportAuditFileBlocked")}
	                >
	                  {t("toolbar.exportAuditFile")}
	                </button>
	                <button className="load-dr-button" onClick={handleLoadDRClick}>{t("toolbar.loadFile")}</button>
	              </div>
	            </details>
	            <details className="toolbar-menu">
	              <summary>{t("toolbar.project")}</summary>
	              <div className="toolbar-menu__items" aria-label={t("toolbar.projectActionsLabel")}>
	                <button onClick={handleExportCanvasState}>{t("canvas.export")}</button>
	                <button onClick={handleImportCanvasStateClick}>{t("canvas.import")}</button>
	              </div>
	            </details>
	            <input
	              ref={drLoadInputRef}
	              type="file"
	              accept=".digital_resident,application/json,.json"
	              onChange={handleLoadDRFile}
	              style={{ display: "none" }}
	            />
            <button type="button" className="toolbar-settings-button" onClick={() => setSettingsOpen((value) => !value)}>
              {t("toolbar.settings", "Settings")}
            </button>
            <input
              ref={fileInputRef}
              type="file"
              accept=".json"
              onChange={handleImportCanvasState}
              style={{ display: "none" }}
            />
          </div>
          <label className="language-select">
            <span>{t("toolbar.language")}</span>
            <select value={language} onChange={(event) => setLanguage(event.target.value as Language)}>
              <option value="zh">中文</option>
              <option value="en">English</option>
            </select>
          </label>
          <span className={`api-pill ${apiReady ? "is-ready" : ""}`}>
            {apiReady ? t("toolbar.apiReady") : t("toolbar.apiUnknown")}
          </span>
	        </div>
      </header>

      <section className={`workspace-grid ${nodeLibraryCollapsed ? "is-library-collapsed" : ""} ${rightPanelExpanded ? "has-right-panel-open" : ""} ${residentNeuralGraphPanelOpen ? "has-neural-graph-panel-open" : ""}`}>
        <aside className={`panel left-panel ${nodeLibraryCollapsed ? "is-collapsed" : ""}`}>
          <div className="sidebar-rail" aria-label={t("canvas.sidebar.library", "Library")}>
            <button
              type="button"
              className={`sidebar-rail__button sidebar-rail__button--library ${nodeLibraryCollapsed ? "" : "is-active"}`}
              title={t("canvas.sidebar.library", "Library")}
              aria-label={t("canvas.sidebar.library", "Library")}
              aria-pressed={!nodeLibraryCollapsed}
              onClick={() => {
                setNodeLibraryCollapsed((collapsed) => {
                  if (collapsed) {
                    setLibraryBodyCollapsed(true);
                  }
                  return !collapsed;
                });
              }}
            >
              <svg className="sidebar-rail__svg" viewBox="0 0 24 24" aria-hidden="true">
                <path d="M6 5h12a2 2 0 0 1 2 2v12H8a2 2 0 0 1-2-2z" />
                <path d="M4 7h12a2 2 0 0 1 2 2v10" />
                <path d="M9 10h6M9 14h7" />
              </svg>
            </button>
          </div>
          {!nodeLibraryCollapsed ? (
            <div className="left-panel__content">
              <section className="panel-section">
                <div className="section-title">
                <button
                  type="button"
                  className="library-master-toggle"
                  onClick={() => setLibraryBodyCollapsed((value) => !value)}
                  aria-expanded={!libraryBodyCollapsed}
                >
                  <span className="node-library-category__chevron">{libraryBodyCollapsed ? "▸" : "▾"}</span>
                  <h2>{t("panel.nodeLibrary")}</h2>
                </button>
                <span>{libraryNodeTypes.length}</span>
              </div>
              {libraryBodyCollapsed ? null : (
              <div className="node-library">
                {nodeLibraryCategories.map((category) => {
                  const categoryCollapsed = collapsedCategories.has(category.id);
                  return (
                    <section key={category.id} className={`node-library-category ${categoryCollapsed ? "is-collapsed" : ""}`}>
                      <button
                        type="button"
                        className="node-library-category__header"
                        onClick={() => toggleCategory(category.id)}
                        aria-expanded={!categoryCollapsed}
                      >
                        <span className="node-library-category__chevron">{categoryCollapsed ? "▸" : "▾"}</span>
                        <strong>{t(category.labelKey, category.labelFallback)}</strong>
                        <span className="node-library-category__count">{category.nodes.length}</span>
                      </button>
                      {!categoryCollapsed ? (
                        category.nodes.length ? (
                          <div className="node-library-category__items">
                            {category.nodes.map((type) => {
                              const status = getNodeStatus(type);
                              return (
                                <div
                                  key={type}
                                  role="button"
                                  tabIndex={0}
                                  draggable
                                  className={`library-item node-kind-${type} ${status ? `status-${status.toLowerCase()}` : ""}`}
                                  title={getNodeTypeLabel(type, t)}
                                  onDragStart={(event) => setNodeDragData(event, type)}
                                  onClick={() => handleAddNode(type)}
                                  onKeyDown={(event) => {
                                    if (event.key === "Enter" || event.key === " ") {
                                      event.preventDefault();
                                      handleAddNode(type);
                                    }
                                  }}
                                >
                                  <span>{getNodeTypeLabel(type, t)}</span>
                                  {status ? (
                                    <small className={`node-status-badge status-${status.toLowerCase()}`}>{getNodeStatusLabel(type, t)}</small>
                                  ) : (
                                    <small>{type}</small>
                                  )}
                                </div>
                              );
                            })}
                          </div>
                        ) : (
                          <div className="node-library-category__empty">{t("lib.category.reserved", "Reserved")}</div>
                        )
                      ) : null}
                    </section>
                  );
                })}
              </div>
              )}
              </section>
              <ModuleLibrary
                t={t}
                collapsed={false}
                layers={moduleCatalog?.layers ?? []}
                modules={moduleCatalog?.modules ?? []}
                onExpand={() => setNodeLibraryCollapsed(false)}
              />
            </div>
          ) : null}
        </aside>

        <section className="canvas-panel" aria-label={t("panel.canvas")}>
          {workflow ? (
            <>
              <WorkspaceTabs
                layers={layerById}
                moduleCatalog={moduleCatalog}
                tabs={workspaceTabs}
                activeId={activeWorkspaceId}
                mode={workspaceMode}
                moduleTabs={moduleTabItems}
                activeModuleId={activeModuleTabId}
                t={t}
                onSelect={(id) => {
                  setActiveWorkspaceId(id);
                  setActiveLayerId(id);
                  setSelectedNode(id);
                  setActiveModuleTabId(null);
                }}
                onClose={closeWorkspaceTab}
                onReturnToMain={() => setActiveModuleTabId(null)}
                onSelectModule={setActiveModuleTabId}
                onCloseModule={closeModuleTab}
                onReorderModule={reorderModuleTab}
                onPinModule={pinModuleTab}
              />
              <div className={`canvas-stage ${splitLayer ? "is-split" : ""}`}>
                <div
                  className="flow-stage"
                  onDragOver={(event) => {
                    event.preventDefault();
                    event.dataTransfer.dropEffect = "copy";
                  }}
                  onDrop={handleMainCanvasDrop}
                  onContextMenuCapture={handleMainFlowContextMenuCapture}
                >
                  <div className="canvas-hint-pill">
                    <span>
                      {selectedCanvasIds.length ? `${selectedCanvasIds.length} ${t("toolbar.selected", "selected")}` : t("toolbar.rightClickHint", "右键画布打开操作菜单")}
                    </span>
                    <span className={`save-status is-${saveStatus}`}>{t(`save.${saveStatus}`, saveStatus)}</span>
                  </div>
                  <ReactFlow
                    nodes={flowNodes}
                    edges={flowEdges}
                    nodeTypes={nodeTypes}
                    onInit={(instance) => {
                      mainFlowRef.current = instance;
                    }}
                    minZoom={0.2}
                    maxZoom={1.6}
                    onNodesChange={handleNodesChange}
                    onEdgesChange={handleEdgesChange}
                    onConnect={handleConnect}
                    onNodesDelete={handleNodesDelete}
                    onNodeClick={handleNodeClick}
                    onNodeContextMenu={handleMainNodeContextMenu}
                    onEdgeContextMenu={handleMainEdgeContextMenu}
	                    onPaneContextMenu={handleMainPaneContextMenu}
	                    onNodeDoubleClick={handleNodeDoubleClick}
	                    onPaneClick={handlePaneClick}
	                    selectionOnDrag
                    selectionKeyCode="Alt"
                    selectNodesOnDrag={false}
                    deleteKeyCode={["Backspace", "Delete"]}
                  >
                    {showGrid ? <Background color="#3a3a3a" gap={24} /> : null}
                    <Controls />
                    {showMiniMap ? (
                      <>
                        <MiniMap pannable zoomable className="canvas-debug-panel__minimap" />
                        <button
                          type="button"
                          className="canvas-debug-panel__collapse nodrag nopan"
                          aria-label={t("debugPanel.collapse")}
                          title={t("debugPanel.collapse")}
                          onClick={() => setShowMiniMap(false)}
                        >
                          {t("debugPanel.collapseGlyph")}
                        </button>
                      </>
                    ) : (
                      <button
                        type="button"
                        className="canvas-debug-panel__expand nodrag nopan"
                        aria-label={t("debugPanel.expand")}
                        title={t("debugPanel.expand")}
                        onClick={() => setShowMiniMap(true)}
                      >
                        {t("debugPanel.expandLabel")}
                      </button>
                    )}
                  </ReactFlow>
                  {mainContextMenu ? <CanvasContextMenu menu={mainContextMenu} onClose={() => setMainContextMenu(null)} /> : null}
                </div>
                {splitLayer ? (
              <LayerWorkspacePanel
                layer={splitLayer}
                moduleCatalog={moduleCatalog}
                edges={edges}
                    t={t}
                    mode="split"
                    moduleNames={moduleNames}
                    onOpen={openLayerWorkspace}
                    onSelectNode={handleChildModuleSelect}
                    onPreviewNode={handleChildModulePreview}
                  />
                ) : null}
                {activeModuleNode ? (
                  <ModuleCanvasPanel
                    key={activeModuleNode.node_id}
                    moduleNode={activeModuleNode}
                    workflow={workflow}
                    initialSubnodes={activeModuleSubnodes}
                    pendingAdd={pendingModuleAdd?.moduleId === activeModuleNode.node_id ? pendingModuleAdd : null}
                    libraryNodeTypes={libraryNodeTypes}
                    language={language}
                    t={t}
                    onRenameModule={(id, name) => setModuleNames((current) => ({ ...current, [id]: name }))}
                    onExecutionResult={setResidentPreviewOutput}
                    onAssistantPanelChange={handleModuleAssistantPanelChange}
                    onClose={() => closeModuleTab(activeModuleNode.node_id)}
                  />
                ) : null}
              </div>
              {floatingLayerIds.map((id, index) => {
                const layer = layerById.get(id);
                if (!layer) {
                  return null;
                }
                return (
                  <FloatingWorkspace
                    key={id}
                    index={index}
                    layer={layer}
                    moduleCatalog={moduleCatalog}
                    edges={edges}
                    t={t}
                    moduleNames={moduleNames}
                    onClose={() => {
                      setFloatingLayerIds((ids) => ids.filter((layerId) => layerId !== id));
                      appendLog(`${t("status.workspaceClosed", "Workspace closed")}: ${id}`);
                    }}
                    onSelectNode={handleChildModuleSelect}
                    onPreviewNode={handleChildModulePreview}
                  />
                );
              })}
              {floatingNodeIds.map((id, index) => {
                const node = nodes.find((candidate) => candidate.node_id === id);
                if (!node) {
                  return null;
                }
                return (
                  <FloatingNodeCanvas
                    key={id}
                    index={index + floatingLayerIds.length}
                    node={node}
                    nodes={nodes}
                    edges={edges}
                    t={t}
                    onClose={() => {
                      setFloatingNodeIds((ids) => ids.filter((nodeId) => nodeId !== id));
                      appendLog(`${t("status.workspaceClosed", "Workspace closed")}: ${id}`);
                    }}
                  />
                );
              })}
            </>
	          ) : (
	            <div className="empty-canvas">
	              <h2>{t("panel.noWorkflow")}</h2>
	              <button disabled={templateIsLoading} onClick={() => handleTemplateClick("persona_builder")}>
	                {templateIsLoading ? t("toolbar.loading", "加载中") : t("toolbar.load")}
	              </button>
	            </div>
	          )}
        </section>

        <RightStudioPanel
          assistantOpen={assistantPanelOpen}
          residentPreviewOpen={residentPreviewPanelOpen}
          residentNeuralGraphOpen={residentNeuralGraphPanelOpen}
          activeFloatingDrawer={activeDrawer}
          assistantTitle={assistantPanel.title}
          assistantMeta={assistantPanel.meta}
          assistantRequest={assistantPanel.request}
          assistantCanApplyPatch={assistantPanel.canApplyPatch}
          onAssistantPatch={assistantPanel.onApplyPatch}
          moduleCatalog={moduleCatalog}
          moduleGraphs={moduleGraphs}
          layerModules={layerModules}
          moduleInstanceRegistry={moduleInstanceRegistry}
          uiColors={uiColors}
          moduleUiColors={moduleUiColors}
          resident={residentInstance}
          canLoadCompiledDR={canExportDR}
          loadedDRResult={loadedDRResult}
          previewLoadStatus={previewLoadStatus}
          previewLoadError={previewLoadError}
          t={t}
          onToggleAssistant={() => {
            setAssistantPanelOpen((value) => !value);
            setResidentPreviewPanelOpen(false);
            setResidentNeuralGraphPanelOpen(false);
          }}
          onToggleResidentPreview={() => {
            setResidentPreviewPanelOpen((value) => !value);
            setAssistantPanelOpen(false);
            setResidentNeuralGraphPanelOpen(false);
          }}
          onToggleResidentNeuralGraph={() => {
            setResidentNeuralGraphPanelOpen((value) => !value);
            setAssistantPanelOpen(false);
            setResidentPreviewPanelOpen(false);
          }}
          onToggleFloatingDrawer={toggleDrawer}
          onCloseAssistant={() => setAssistantPanelOpen(false)}
          onCloseResidentPreview={() => setResidentPreviewPanelOpen(false)}
          onCloseResidentNeuralGraph={() => setResidentNeuralGraphPanelOpen(false)}
          onLoadCompiledDR={handleLoadCompiledDRToPreview}
        />
      </section>

      {focusLayerId ? (() => {
        const focusModuleIds = moduleIdsForDisplayLayer(layerModules, focusLayerId, moduleCatalogById);
        return (
        <ModuleFocusPanel
          layerLabel={moduleCatalog ? translate(language, `layer.${focusLayerId}`, moduleCatalog.layers.find((l) => l.layer_id === focusLayerId)?.layer_name ?? "") : ""}
          moduleIds={focusModuleIds}
          moduleCatalogById={moduleCatalogById}
          moduleColors={Object.fromEntries(
            focusModuleIds.map((id) => {
              const storedLayerId = storedLayerIdForModule(layerModules, id, focusLayerId);
              return [id, moduleUiColors[`${focusLayerId}:${id}`] ?? moduleUiColors[`${storedLayerId}:${id}`] ?? ""];
            })
          )}
          selectedModuleIds={new Set(
            focusModuleIds.filter((id) => {
              const storedLayerId = storedLayerIdForModule(layerModules, id, focusLayerId);
              return selectedLayerModuleKeys.has(`${focusLayerId}:${id}`) || selectedLayerModuleKeys.has(`${storedLayerId}:${id}`);
            })
          )}
          t={t}
          onOpen={(moduleId) => {
            // Opening the module canvas should reveal it: close the focus overlay,
            // which otherwise sits on top of the module canvas.
            openCatalogModuleCanvas(focusLayerId, moduleId);
            setFocusLayerId(null);
          }}
          onSelect={(moduleId, multi) => selectLayerModule(focusLayerId, moduleId, multi)}
          onContextMenu={(event, moduleId) => {
            const layer = catalogLayers.find((l) => l.layer_id === focusLayerId);
            if (layer) {
              openDroppedModuleContextMenu(event, layer, moduleId);
            }
          }}
          onContainerContextMenu={(event) => {
            const layer = catalogLayers.find((l) => l.layer_id === focusLayerId);
            if (layer) {
              openFolderContextMenu(event, layer);
            }
          }}
          onClose={() => setFocusLayerId(null)}
        />
        );
      })() : null}

      {activeDrawer === "layers" ? (
        <FloatingSidePanel
          title={t("panel.layerNavigator", "Layer Navigator")}
          meta={`${catalogLayers.length}/13`}
          rightPanelExpanded={rightPanelExpanded}
          onClose={() => setActiveDrawer(null)}
        >
          <LayerNavigator
            layers={catalogLayers}
            moduleCatalog={moduleCatalog}
            activeLayerId={activeLayer?.layer_id ?? null}
            collapsedLayerIds={collapsedLayerIds}
            t={t}
            onOpen={openLayerWorkspace}
            onToggle={toggleLayerCollapsed}
          />
        </FloatingSidePanel>
      ) : null}

      {activeDrawer === "debugTrace" ? (
        <FloatingSidePanel
          title={t("panel.debugTrace", "Debug / Trace")}
          meta={t("debugTrace.openLabel", "Debug")}
          rightPanelExpanded={rightPanelExpanded}
          onClose={() => setActiveDrawer(null)}
        >
          <CanvasDebugTracePanel
            open
            embedded
            t={t}
            logs={logs}
            trace={loadedDRResult?.execution_trace ?? (runtimeResult as { execution_trace?: unknown } | null)?.execution_trace ?? null}
            validation={loadedDRResult?.validation_result ?? validation}
            jsonPreview={{
              runtime_result: runtimeResult,
              loaded_file: loadedDRResult,
              export_preview: exportPreview,
              memory_view: memoryView,
              memory_clear_result: memoryClearResult
            }}
            memoryView={memoryView ?? null}
            memoryClearResult={memoryClearResult ?? null}
            onToggle={() => setActiveDrawer(null)}
          />
        </FloatingSidePanel>
      ) : null}

      {settingsOpen ? (
        <RuntimeLLMProfilesPanel
          t={t}
          onClose={() => setSettingsOpen(false)}
        />
      ) : null}

      {activeDrawer === "logs" ? (
        <FloatingSidePanel
          title={t("panel.logs")}
          rightPanelExpanded={rightPanelExpanded}
          onClose={() => setActiveDrawer(null)}
        >
          <LogsPanel logs={logs} validation={validation} emptyText={t("panel.noLogs")} t={t} />
        </FloatingSidePanel>
      ) : null}

      {activeDrawer === "artifacts" ? (
        <FloatingSidePanel
          title={t("panel.artifacts")}
          rightPanelExpanded={rightPanelExpanded}
          onClose={() => setActiveDrawer(null)}
        >
          <JsonPanel value={artifacts.length ? artifacts : null} emptyText={t("panel.noArtifacts")} />
        </FloatingSidePanel>
      ) : null}

      {activeDrawer === "preview" ? (
        <FloatingSidePanel
          title={t("panel.exportPreview")}
          rightPanelExpanded={rightPanelExpanded}
          onClose={() => setActiveDrawer(null)}
        >
          <JsonPanel value={exportPreview} emptyText={t("panel.noPreview")} />
        </FloatingSidePanel>
      ) : null}
    </main>
  );
}

function ModuleFocusPanel({
  layerLabel,
  moduleIds,
  moduleCatalogById,
  moduleColors,
  selectedModuleIds,
  t,
  onOpen,
  onSelect,
  onContextMenu,
  onContainerContextMenu,
  onClose
}: {
  layerLabel: string;
  moduleIds: string[];
  moduleCatalogById: Map<string, ModuleCatalogEntryV04>;
  moduleColors: Record<string, string>;
  selectedModuleIds: Set<string>;
  t: (key: string, fallback?: string) => string;
  onOpen: (moduleId: string) => void;
  onSelect: (moduleId: string, multi: boolean) => void;
  onContextMenu: (event: ReactMouseEvent, moduleId: string) => void;
  onContainerContextMenu: (event: ReactMouseEvent) => void;
  onClose: () => void;
}) {
  const mods = moduleIds
    .map((id) => moduleCatalogById.get(id))
    .filter((module): module is ModuleCatalogEntryV04 => Boolean(module));
  return (
    <div className="module-focus-backdrop" onClick={onClose}>
      <section
        className="module-focus"
        onClick={(event) => event.stopPropagation()}
        onContextMenu={(event) => {
          event.preventDefault();
          onContainerContextMenu(event);
        }}
      >
        <header className="module-focus__bar">
          <div>
            <p>{t("module.focusMode", "Focus Mode")}</p>
            <h3>{layerLabel}</h3>
            <span>{mods.length} {t("module.count")}</span>
          </div>
          <button onClick={onClose}>✕</button>
        </header>
        <div className="module-focus__grid">
          {mods.length ? (
            // Same card markup as the main-canvas folder rail so the focus view stays
            // visually consistent: select (click), open (double-click), context menu
            // (right-click). Remove lives in the context menu, not an inline button.
            mods.map((mod) => {
              const modId = moduleCatalogId(mod);
              const slot = moduleCatalogSlot(mod);
              const slotLabel = t(`module.slot.${slot}`, slot.toUpperCase());
              const category = String(mod.category || "general");
              const displayClass = moduleCatalogClass(mod);
              const status = String(mod.status);
              return (
                <button
                  key={modId}
                  type="button"
                  className={`submodule-card module-drop-card cat-${displayClass} status-${status.toLowerCase()} ${selectedModuleIds.has(modId) ? "is-selected" : ""}`}
                  style={moduleColors[modId] ? ({ "--mod-accent": moduleColors[modId] } as CSSProperties) : undefined}
                  onClick={(event) => {
                    event.stopPropagation();
                    onSelect(modId, event.ctrlKey || event.metaKey);
                  }}
                  onDoubleClick={(event) => {
                    event.preventDefault();
                    event.stopPropagation();
                    onOpen(modId);
                  }}
                  onContextMenu={(event) => {
                    event.preventDefault();
                    event.stopPropagation();
                    onContextMenu(event, modId);
                  }}
                  title={`${moduleCatalogName(mod, t)} · ${slotLabel} · ${t(`module.status.${status}`, status)}`}
                >
                  <span className="submodule-name">{moduleCatalogName(mod, t)}</span>
                  <span className="submodule-badge-row">
                    <span className="submodule-group">{mod.layer_id}</span>
                    <span className={`ai-slot-badge ai-slot-${category === "avatar" ? "ar" : category === "llm" || category === "memory" || category === "tts" || category === "runtime" ? category : "none"}`}>
                      {slotLabel}
                    </span>
                    <span className="submodule-tier">{t(`module.status.${status}`, status)}</span>
                  </span>
                </button>
              );
            })
          ) : (
            <div className="module-focus__empty">{t("module.empty", "暂无模块,从模块库拖入或右键添加")}</div>
          )}
        </div>
      </section>
    </div>
  );
}

function RightStudioPanel({
  assistantOpen,
  residentPreviewOpen,
  residentNeuralGraphOpen,
  activeFloatingDrawer,
  assistantTitle,
  assistantMeta,
  assistantRequest,
  assistantCanApplyPatch,
  moduleCatalog,
  moduleGraphs,
  layerModules,
  moduleInstanceRegistry,
  uiColors,
  moduleUiColors,
  resident,
  canLoadCompiledDR,
  loadedDRResult,
  previewLoadStatus,
  previewLoadError,
  t,
  onToggleAssistant,
  onToggleResidentPreview,
  onToggleResidentNeuralGraph,
  onToggleFloatingDrawer,
  onCloseAssistant,
  onCloseResidentPreview,
  onCloseResidentNeuralGraph,
  onAssistantPatch,
  onLoadCompiledDR
}: {
  assistantOpen: boolean;
  residentPreviewOpen: boolean;
  residentNeuralGraphOpen: boolean;
  activeFloatingDrawer: DrawerId | null;
  assistantTitle: string;
  assistantMeta: string;
  assistantRequest: StudioAssistantRequest;
  assistantCanApplyPatch: boolean;
  moduleCatalog: ModuleCatalogResponseV04 | null;
  moduleGraphs: ReturnType<typeof useCanvasStore.getState>["moduleGraphs"];
  layerModules: Record<string, string[]>;
  moduleInstanceRegistry: Record<string, ModuleInstance>;
  uiColors: Record<string, string>;
  moduleUiColors: Record<string, string>;
  resident: ResidentInstance | null;
  canLoadCompiledDR: boolean;
  loadedDRResult: DRLoadResult | null;
  previewLoadStatus: "idle" | "loading" | "success" | "error";
  previewLoadError: string | null;
  t: (key: string, fallback?: string) => string;
  onToggleAssistant: () => void;
  onToggleResidentPreview: () => void;
  onToggleResidentNeuralGraph: () => void;
  onToggleFloatingDrawer: (drawer: DrawerId) => void;
  onCloseAssistant: () => void;
  onCloseResidentPreview: () => void;
  onCloseResidentNeuralGraph: () => void;
  onAssistantPatch: (patch: StudioAssistantPatch) => void;
  onLoadCompiledDR: () => Promise<void>;
}) {
  const expanded = assistantOpen || residentPreviewOpen || residentNeuralGraphOpen;
  const floatingItems: { id: DrawerId; label: string }[] = [
    { id: "debugTrace", label: t("panel.debugTrace", "Debug / Trace") },
    { id: "layers", label: t("panel.layerNavigator", "Layers") },
    { id: "logs", label: t("panel.logs") },
    { id: "artifacts", label: t("panel.artifacts") },
    { id: "preview", label: t("panel.exportPreview") }
  ];
  return (
    <aside className={`right-studio-panel ${expanded ? "is-expanded" : "is-collapsed"}`}>
      <div className="right-studio-panel__rail" aria-label={t("panel.rightTools", "Right panels")}>
        <div className="right-studio-panel__rail-group" aria-label={t("panel.fixedTools", "Fixed panels")}>
          <button
            type="button"
            className={assistantOpen ? "is-active" : ""}
            title={t("assistant.floatingButton.title", "Assistant")}
            aria-label={t("assistant.floatingButton.title", "Assistant")}
            aria-pressed={assistantOpen}
            onClick={onToggleAssistant}
          >
            <DockIcon id="assistant" />
          </button>
          <button
            type="button"
            className={residentPreviewOpen ? "is-active" : ""}
            title={t("panel.residentPreview", "Resident Preview")}
            aria-label={t("panel.residentPreview", "Resident Preview")}
            aria-pressed={residentPreviewOpen}
            onClick={onToggleResidentPreview}
          >
            <DockIcon id="residentPreview" />
          </button>
          <button
            type="button"
            className={residentNeuralGraphOpen ? "is-active" : ""}
            title={t("panel.residentNeuralGraph", "Resident Neural Graph")}
            aria-label={t("panel.residentNeuralGraph", "Resident Neural Graph")}
            aria-pressed={residentNeuralGraphOpen}
            onClick={onToggleResidentNeuralGraph}
          >
            <DockIcon id="residentNeuralGraph" />
          </button>
        </div>
        <div className="right-studio-panel__rail-group right-studio-panel__rail-group--floating" aria-label={t("dock.ariaLabel")}>
          {floatingItems.map((item) => (
            <button
              key={item.id}
              type="button"
              className={activeFloatingDrawer === item.id ? "is-active" : ""}
              title={item.label}
              aria-label={item.label}
              aria-pressed={activeFloatingDrawer === item.id}
              onClick={() => onToggleFloatingDrawer(item.id)}
            >
              <DockIcon id={item.id} />
            </button>
          ))}
        </div>
      </div>
      {expanded ? (
        <div className="right-studio-panel__panels">
          {assistantOpen ? (
            <section className="right-studio-panel__section">
              <div className="right-studio-panel__header">
                <div>
                  <h2>{assistantTitle}</h2>
                  {assistantMeta ? <span>{assistantMeta}</span> : null}
                </div>
                <button
                  type="button"
                  title={t("assistant.panel.collapse", "Collapse")}
                  aria-label={t("assistant.panel.collapse", "Collapse")}
                  onClick={onCloseAssistant}
                >
                  x
                </button>
              </div>
              <div className="right-studio-panel__body">
                <StudioAssistantPanel
                  request={assistantRequest}
                  canApplyPatch={assistantCanApplyPatch}
                  t={t}
                  onApplyPatch={onAssistantPatch}
                />
              </div>
            </section>
          ) : null}
          {residentPreviewOpen ? (
            <section className="right-studio-panel__section resident-preview-panel">
              <div className="right-studio-panel__header">
                <div>
                  <h2>{t("panel.residentPreview", "Resident Preview")}</h2>
                  <span>{t("preview.mockLayer", "Mock preview")}</span>
                </div>
                <button
                  type="button"
                  title={t("canvas.sidebar.collapse", "Collapse")}
                  aria-label={t("canvas.sidebar.collapse", "Collapse")}
                  onClick={onCloseResidentPreview}
                >
                  x
                </button>
              </div>
              <div className="right-studio-panel__body">
                <ResidentPreviewPanel
                  resident={resident}
                  t={t}
                  canLoadCompiledDR={canLoadCompiledDR}
                  onLoadCompiledDR={onLoadCompiledDR}
                  loadedDRResult={loadedDRResult}
                  previewLoadStatus={previewLoadStatus}
                  previewLoadError={previewLoadError}
                />
              </div>
            </section>
          ) : null}
          {residentNeuralGraphOpen ? (
            <section className="right-studio-panel__section resident-neural-graph-panel-frame">
              <div className="right-studio-panel__header">
                <div>
                  <h2>{t("neuralGraph.title", "Resident Neural Graph")}</h2>
                  <span>{t("neuralGraph.subtitle", "3D brain-region view of the digital resident structure")}</span>
                </div>
                <button
                  type="button"
                  title={t("canvas.sidebar.collapse", "Collapse")}
                  aria-label={t("canvas.sidebar.collapse", "Collapse")}
                  onClick={onCloseResidentNeuralGraph}
                >
                  x
                </button>
              </div>
              <div className="right-studio-panel__body">
                <ResidentNeuralGraphPanel
                  moduleCatalog={moduleCatalog}
                  moduleGraphs={moduleGraphs}
                  layerModules={layerModules}
                  moduleInstanceRegistry={moduleInstanceRegistry}
                  uiColors={uiColors}
                  moduleUiColors={moduleUiColors}
                  t={t}
                />
              </div>
            </section>
          ) : null}
        </div>
      ) : null}
    </aside>
  );
}

function FloatingDock({
  activeDrawer,
  rightPanelExpanded,
  t,
  onToggle
}: {
  activeDrawer: DrawerId | null;
  rightPanelExpanded: boolean;
  t: (key: string, fallback?: string) => string;
  onToggle: (drawer: DrawerId) => void;
}) {
  const dockItems: { id: DrawerId; label: string }[] = [
    { id: "layers", label: t("panel.layerNavigator", "Layers") },
    { id: "logs", label: t("panel.logs") },
    { id: "artifacts", label: t("panel.artifacts") },
    { id: "preview", label: t("panel.exportPreview") }
  ];

  return (
    <FloatingPortal>
    <nav
      className={`floating-dock ${rightPanelExpanded ? "has-right-panel-open" : ""}`}
      aria-label={t("dock.ariaLabel")}
    >
      {dockItems.map((item) => (
        <button
          key={item.id}
          className={activeDrawer === item.id ? "is-active" : ""}
          title={item.label}
          aria-label={item.label}
          onClick={() => {
            onToggle(item.id);
          }}
        >
          <DockIcon id={item.id} />
        </button>
      ))}
    </nav>
    </FloatingPortal>
  );
}

function FloatingPortal({ children }: { children: ReactNode }) {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted || typeof document === "undefined") {
    return null;
  }

  return createPortal(children, document.body);
}

function DockIcon({ id }: { id: DrawerId }) {
  if (id === "assistant") {
    return (
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <path d="M12 4v3M12 17v3M5.6 6.6l2.1 2.1M16.3 15.3l2.1 2.1M4 12h3M17 12h3M5.6 17.4l2.1-2.1M16.3 8.7l2.1-2.1" />
        <path d="M10 10.2c.5-1.2 2.1-1.4 3-.5.8.8.7 2.2-.2 2.9-.6.4-.8.8-.8 1.4" />
        <path d="M12 16h.01" />
      </svg>
    );
  }
  if (id === "layers") {
    return (
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <path d="M4 6h16M4 12h16M4 18h16" />
        <path d="M7 4v4M12 10v4M17 16v4" />
      </svg>
    );
  }
  if (id === "debugTrace") {
    return (
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <path d="M7 8h10M7 12h7M7 16h10" />
        <path d="M5 4h14v16H5z" />
        <path d="M9 2v4M15 2v4M9 18v4M15 18v4" />
      </svg>
    );
  }
  if (id === "logs") {
    return (
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <path d="M6 5h12M6 10h12M6 15h8M6 20h10" />
      </svg>
    );
  }
  if (id === "artifacts") {
    return (
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <path d="M6 7h12v12H6z" />
        <path d="M9 4h12v12" />
      </svg>
    );
  }
  if (id === "residentPreview") {
    return (
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <path d="M12 5a4 4 0 0 1 4 4c0 1.4-.7 2.6-1.8 3.3" />
        <path d="M8 12.3A4 4 0 1 1 12 5" />
        <path d="M5 20c1.3-3 3.6-4.5 7-4.5s5.7 1.5 7 4.5" />
        <path d="M8 10h.01M16 10h.01" />
      </svg>
    );
  }
  if (id === "residentNeuralGraph") {
    return (
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <circle cx="6" cy="7" r="2" />
        <circle cx="18" cy="7" r="2" />
        <circle cx="12" cy="17" r="2" />
        <path d="M8 8l2.5 6.8M16 8l-2.5 6.8M8 7h8" />
      </svg>
    );
  }
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M4 6h16v12H4z" />
      <path d="M8 10h8M8 14h5" />
    </svg>
  );
}

function FloatingSidePanel({
  title,
  meta,
  children,
  className,
  rightPanelExpanded,
  onClose
}: {
  title: string;
  meta?: string;
  children: ReactNode;
  className?: string;
  rightPanelExpanded?: boolean;
  onClose: () => void;
}) {
  return (
    <FloatingPortal>
      <aside className={`floating-side-panel${rightPanelExpanded ? " is-right-panel-open" : ""}${className ? ` ${className}` : ""}`}>
        <div className="floating-panel-header">
          <div>
            <h2>{title}</h2>
            {meta ? <span>{meta}</span> : null}
          </div>
          <button onClick={onClose}>x</button>
        </div>
        <div className="floating-panel-body">{children}</div>
      </aside>
    </FloatingPortal>
  );
}

function FloatingBottomPanel({
  activeTab,
  t,
  children,
  onTab,
  onClose
}: {
  activeTab: BottomTab;
  t: (key: string, fallback?: string) => string;
  children: ReactNode;
  onTab: (tab: BottomTab) => void;
  onClose: () => void;
}) {
  const tabs: { id: BottomTab; label: string }[] = [
    { id: "logs", label: t("panel.logs") },
    { id: "artifacts", label: t("panel.artifacts") },
    { id: "preview", label: t("panel.exportPreview") }
  ];

  return (
    <FloatingPortal>
      <section className="floating-bottom-panel">
        <div className="bottom-tabs">
          {tabs.map((tab) => (
            <button key={tab.id} className={activeTab === tab.id ? "is-active" : ""} onClick={() => onTab(tab.id)}>
              {tab.label}
            </button>
          ))}
          <button className="drawer-close" onClick={onClose}>
            x
          </button>
        </div>
        <div className="bottom-drawer-body">{children}</div>
      </section>
    </FloatingPortal>
  );
}

function RuntimeLLMProfilesPanel({
  t,
  onClose
}: {
  t: (key: string, fallback?: string) => string;
  onClose: () => void;
}) {
  const llmProfiles = useCanvasStore((state) => state.llmProfiles);
  const saveLLMConfig = useCanvasStore((state) => state.saveLLMConfig);
  const testLLMConnection = useCanvasStore((state) => state.testLLMConnection);
  const [profileId, setProfileId] = useState(llmProfiles?.default_profile_id ?? "default");
  const [provider, setProvider] = useState("openai_compatible");
  const [baseUrl, setBaseUrl] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [model, setModel] = useState("");
  const [enabled, setEnabled] = useState(false);
  const [fallbackToMock, setFallbackToMock] = useState(true);

  const profileIds = llmProfiles?.profile_ids?.length ? llmProfiles.profile_ids : ["default", "deepseek", "mimo", "custom"];
  const current = llmProfiles?.profiles?.[profileId] ?? llmProfiles?.profiles?.[llmProfiles?.default_profile_id ?? "default"];

  useEffect(() => {
    const nextId = llmProfiles?.default_profile_id ?? "default";
    setProfileId((currentId) => (llmProfiles?.profiles?.[currentId] ? currentId : nextId));
  }, [llmProfiles]);

  useEffect(() => {
    const profile = llmProfiles?.profiles?.[profileId];
    if (!profile) {
      return;
    }
    setProvider(profile.provider || "openai_compatible");
    setBaseUrl(profile.base_url || "");
    setModel(profile.model || "");
    setEnabled(Boolean(profile.enabled));
    setFallbackToMock(Boolean(profile.fallback_to_mock));
    setApiKey("");
  }, [llmProfiles, profileId]);

  const saveProfile = (patch: Partial<LLMProfileInput> = {}) => {
    void saveLLMConfig({
      profile_id: profileId,
      provider,
      base_url: baseUrl,
      api_key: apiKey || undefined,
      model,
      enabled,
      fallback_to_mock: fallbackToMock,
      ...patch
    });
    setApiKey("");
  };

  const testProfile = () => {
    void testLLMConnection({
      profile_id: profileId,
      provider,
      base_url: baseUrl,
      api_key: apiKey || undefined,
      model,
      enabled,
      fallback_to_mock: fallbackToMock
    });
  };

  return (
    <FloatingSidePanel
      title={t("panel.runtimeLLMProfiles", "Runtime LLM Profiles")}
      meta={current?.has_api_key ? t("field.apiKeySet", "Configured") : t("field.apiKeyUnset", "Not configured")}
      onClose={onClose}
    >
      <section className="runtime-llm-profiles">
        <label className="runtime-llm-profiles__row">
          <span>{t("field.profile", "Profile")}</span>
          <select value={profileId} onChange={(event) => setProfileId(event.target.value)}>
            {profileIds.map((id) => (
              <option key={id} value={id}>
                {id}
              </option>
            ))}
          </select>
        </label>
        <label className="runtime-llm-profiles__row">
          <span>{t("field.provider", "Provider")}</span>
          <input value={provider} onChange={(event) => setProvider(event.target.value)} onBlur={() => saveProfile({ provider })} />
        </label>
        <label className="runtime-llm-profiles__row">
          <span>{t("field.apiUrl", "API URL")}</span>
          <input value={baseUrl} onChange={(event) => setBaseUrl(event.target.value)} onBlur={() => saveProfile({ base_url: baseUrl })} />
        </label>
        <label className="runtime-llm-profiles__row">
          <span>{t("field.apiKey", "API Key")}</span>
          <input
            type="password"
            value={apiKey}
            placeholder={current?.has_api_key ? t("field.apiKeySet", "Configured (leave blank to keep)") : t("field.apiKeyUnset", "Not configured")}
            onChange={(event) => setApiKey(event.target.value)}
            onBlur={() => {
              if (apiKey) {
                saveProfile({ api_key: apiKey });
              }
            }}
          />
        </label>
        <label className="runtime-llm-profiles__row">
          <span>{t("field.modelName", "Model")}</span>
          <input value={model} onChange={(event) => setModel(event.target.value)} onBlur={() => saveProfile({ model })} />
        </label>
        <label className="runtime-llm-profiles__row runtime-llm-profiles__row--toggle">
          <span>{t("field.enabled", "Enabled")}</span>
          <input
            type="checkbox"
            checked={enabled}
            onChange={(event) => {
              const checked = event.target.checked;
              setEnabled(checked);
              saveProfile({ enabled: checked });
            }}
          />
        </label>
        <label className="runtime-llm-profiles__row runtime-llm-profiles__row--toggle">
          <span>{t("field.fallbackToMock", "Fallback to mock")}</span>
          <input
            type="checkbox"
            checked={fallbackToMock}
            onChange={(event) => {
              const checked = event.target.checked;
              setFallbackToMock(checked);
              saveProfile({ fallback_to_mock: checked });
            }}
          />
        </label>
        <div className="runtime-llm-profiles__actions">
          <button type="button" onClick={() => saveProfile()}>
            {t("common.save", "Save")}
          </button>
          <button type="button" onClick={testProfile} disabled={llmProfiles === null}>
            {t("button.testConnection", "Test Connection")}
          </button>
        </div>
        <p className="runtime-llm-profiles__hint">{t("llm.profileHint", "Profiles are masked in GET responses; api_key never enters the store.")}</p>
      </section>
    </FloatingSidePanel>
  );
}

function LayerNavigator({
  layers,
  moduleCatalog,
  activeLayerId,
  collapsedLayerIds,
  t,
  onOpen,
  onToggle
}: {
  layers: CatalogLayerInput[];
  moduleCatalog: ModuleCatalogResponseV04 | null;
  activeLayerId: string | null;
  collapsedLayerIds: Set<string>;
  t: (key: string, fallback?: string) => string;
  onOpen: (layer: CatalogLayerInput, mode: WorkspaceMode) => void;
  onToggle: (layer: CatalogLayerInput) => void;
}) {
  if (!layers.length) {
    return <div className="empty-panel">{t("panel.noLayers", "No backend layers loaded")}</div>;
  }

  return (
    <div className="layer-navigator">
      {layers.map((layer) => {
        const language = useCanvasStore.getState().language;
        const label = moduleCatalog ? layerDisplayName(language, layer, moduleCatalog.layers.find((l) => l.layer_id === layer.layer_id)?.layer_name ?? "") : "";
        const collapsed = collapsedLayerIds.has(layer.layer_id);
        return (
          <div key={layer.layer_id} className="layer-nav-section">
          <article
            className={`layer-nav-item tier-core status-schema ${activeLayerId === layer.layer_id ? "is-active" : ""}`}
          >
            <button className="layer-nav-main" onClick={() => onOpen(layer, "inline")}>
              <span className="layer-index">{String(layer.layer_order).padStart(2, "0")}</span>
              <span className="layer-name">{label}</span>
              <span className="layer-status">{assemblyStatusLabel(language, "schema")}</span>
            </button>
            <div className="layer-nav-meta">
              <span>{assemblyStatusLabel(language, "core")}</span>
              <span>0 {t("assembly.field.nodes")}</span>
              <span>{t("lock.editable")}</span>
            </div>
            <div className="layer-nav-actions" aria-label={`${label} ${t("assembly.action.workspaceActions")}`}>
              <button onClick={() => onToggle(layer)}>{collapsed ? "+" : "-"}</button>
              <button onClick={() => onOpen(layer, "right")}>{t("workspace.rightShort")}</button>
              <button onClick={() => onOpen(layer, "split")}>{t("workspace.splitShort")}</button>
              <button onClick={() => onOpen(layer, "window")}>{t("workspace.windowShort")}</button>
            </div>
          </article>
          </div>
        );
      })}
    </div>
  );
}

function WorkspaceTabs({
  layers,
  moduleCatalog,
  tabs,
  activeId,
  mode,
  moduleTabs,
  activeModuleId,
  t,
  onSelect,
  onClose,
  onReturnToMain,
  onSelectModule,
  onCloseModule,
  onReorderModule,
  onPinModule
}: {
  layers: Map<string, CatalogLayerInput>;
  moduleCatalog: ModuleCatalogResponseV04 | null;
  tabs: string[];
  activeId: string | null;
  mode: WorkspaceMode;
  moduleTabs: { id: string; label: string }[];
  activeModuleId: string | null;
  t: (key: string, fallback?: string) => string;
  onSelect: (id: string) => void;
  onClose: (id: string) => void;
  onReturnToMain: () => void;
  onSelectModule: (id: string) => void;
  onCloseModule: (id: string) => void;
  onReorderModule: (fromId: string, toId: string) => void;
  onPinModule: (id: string) => void;
}) {
  const [dragModuleId, setDragModuleId] = useState<string | null>(null);
  return (
    <div className="workspace-tabs">
      <button
        type="button"
        className={`breadcrumb breadcrumb-home ${activeModuleId ? "" : "is-active"}`}
        onClick={onReturnToMain}
        title={t("workspace.backToCanvas")}
      >
        <span>{t("field.workflow")}</span>
        <span>/</span>
        <strong>
          {activeId && moduleCatalog && layers.get(activeId)
            ? layerDisplayName(useCanvasStore.getState().language, layers.get(activeId) as CatalogLayerInput, moduleCatalog.layers.find((l) => l.layer_id === activeId)?.layer_name ?? "")
            : t("common.pipeline")}
        </strong>
      </button>
      <div className="tab-strip">
        {tabs.map((id) => {
          const layer = layers.get(id);
          if (!layer) {
            return null;
          }
          return (
            <button key={id} className={activeId === id ? "is-active" : ""} onClick={() => onSelect(id)}>
              L{layer.layer_order}
              <span>{moduleCatalog ? layerDisplayName(useCanvasStore.getState().language, layer, moduleCatalog.layers.find((l) => l.layer_id === layer.layer_id)?.layer_name ?? "") : ""}</span>
              <small>{t(`workspace.${mode}`)}</small>
              <b
                role="button"
                tabIndex={0}
                onClick={(event) => {
                  event.stopPropagation();
                  onClose(id);
                }}
                onKeyDown={(event) => {
                  if (event.key === "Enter" || event.key === " ") {
                    event.preventDefault();
                    onClose(id);
                  }
                }}
              >
                x
              </b>
            </button>
          );
        })}
        {moduleTabs.map((moduleTab) => (
          <button
            key={moduleTab.id}
            className={`is-module ${activeModuleId === moduleTab.id ? "is-active" : ""} ${dragModuleId === moduleTab.id ? "is-dragging" : ""}`}
            draggable
            onClick={() => onSelectModule(moduleTab.id)}
            onDragStart={() => setDragModuleId(moduleTab.id)}
            onDragEnd={() => setDragModuleId(null)}
            onDragOver={(event) => event.preventDefault()}
            onDrop={(event) => {
              event.preventDefault();
              if (dragModuleId && dragModuleId !== moduleTab.id) {
                onReorderModule(dragModuleId, moduleTab.id);
              }
              setDragModuleId(null);
            }}
          >
            <i
              role="button"
              tabIndex={0}
              className="module-tab-pin"
              title={t("workspace.modulePin", "Pin to left")}
              onClick={(event) => {
                event.stopPropagation();
                onPinModule(moduleTab.id);
              }}
              onKeyDown={(event) => {
                if (event.key === "Enter" || event.key === " ") {
                  event.preventDefault();
                  onPinModule(moduleTab.id);
                }
              }}
            >
              ⤒
            </i>
            <span>{moduleTab.label}</span>
            <small>{t("workspace.moduleTab", "module")}</small>
            <b
              role="button"
              tabIndex={0}
              onMouseDown={(event) => {
                event.preventDefault();
                event.stopPropagation();
              }}
              onClick={(event) => {
                event.preventDefault();
                event.stopPropagation();
                onCloseModule(moduleTab.id);
              }}
              onKeyDown={(event) => {
                if (event.key === "Enter" || event.key === " ") {
                  event.preventDefault();
                  onCloseModule(moduleTab.id);
                }
              }}
            >
              x
            </b>
          </button>
        ))}
      </div>
    </div>
  );
}

function LayerWorkspacePanel({
  layer,
  moduleCatalog,
  edges,
  t,
  mode,
  moduleNames,
  onOpen,
  onSelectNode,
  onPreviewNode
}: {
  layer: CatalogLayerInput;
  moduleCatalog: ModuleCatalogResponseV04 | null;
  edges: EdgeLike[];
  t: (key: string, fallback?: string) => string;
  mode: WorkspaceMode;
  moduleNames: Record<string, string>;
  onOpen: (layer: CatalogLayerInput, mode: WorkspaceMode) => void;
  onSelectNode: (node: WorkflowNode) => void;
  onPreviewNode: (node: WorkflowNode) => void;
}) {
  const [collapsed, setCollapsed] = useState(false);
  const language = useCanvasStore.getState().language;
  const compiledDR = useCanvasStore((state) => state.compiledDR);
  const drCompileResult = useCanvasStore((state) => state.drCompileResult);
  const label = moduleCatalog ? layerDisplayName(language, layer, moduleCatalog.layers.find((l) => l.layer_id === layer.layer_id)?.layer_name ?? "") : "";
  const parameterCount = Object.keys(layer).length;
  const assembly = useMemo(() => layerAssemblyView(layer, compiledDR, drCompileResult), [compiledDR, drCompileResult, layer]);

  return (
    <section className={`layer-workspace mode-${mode} tier-core`}>
      <div className="workspace-header">
        <div className="folder-group-title">
          <span className="folder-icon" aria-hidden="true">
            ::
          </span>
          <div>
          <p>{t("workspace.breadcrumb", "Workflow / Layer / Folder")}</p>
          <h3>
            L{layer.layer_order} {label}
            <span className="module-count-badge">{assembly.moduleCount} {t("module.count")}</span>
          </h3>
          </div>
        </div>
        <div className="workspace-actions">
          <button onClick={() => setCollapsed((value) => !value)}>{collapsed ? "+" : "-"}</button>
          <button onClick={() => onOpen(layer, "right")}>{t("workspace.rightShort")}</button>
          <button onClick={() => onOpen(layer, "split")}>{t("workspace.splitShort")}</button>
          <button onClick={() => onOpen(layer, "window")}>{t("workspace.window")}</button>
        </div>
      </div>
      <div className="folder-group-meta">
        <span>{assemblyFieldLabel(language, "status", t("field.status"))}: {assemblyStatusLabel(language, assembly.status)}</span>
        <span>{assemblyFieldLabel(language, "tier")}: {assemblyStatusLabel(language, "core")}</span>
        <span>{t("field.data")}: {parameterCount}</span>
        <span>{t("field.childrenCount")}: {assembly.nodeCount}</span>
      </div>
      {!collapsed ? (
        <AssemblyContentView assembly={assembly} language={language} moduleCatalog={moduleCatalog} t={t} />
      ) : (
        <div className="folder-collapsed">{t("workspace.emptyFolder", "empty folder layer")}</div>
      )}
    </section>
  );
}

function FloatingNodeCanvas({
  index,
  node,
  nodes,
  edges,
  t,
  onClose
}: {
  index: number;
  node: WorkflowNode;
  nodes: WorkflowNode[];
  edges: EdgeLike[];
  t: (key: string, fallback?: string) => string;
  onClose: () => void;
}) {
  const neighborIds = new Set<string>([node.node_id]);
  for (const edge of edges) {
    if (edge.source === node.node_id) {
      neighborIds.add(edge.target);
    }
    if (edge.target === node.node_id) {
      neighborIds.add(edge.source);
    }
  }
  const previewNodes = nodes.filter((candidate) => neighborIds.has(candidate.node_id));
  const previewNodeIds = new Set(previewNodes.map((candidate) => candidate.node_id));
  const previewEdges = edges.filter((edge) => previewNodeIds.has(edge.source) && previewNodeIds.has(edge.target));
  const base = node.position ?? { x: 0, y: 0 };
  const flowPreviewNodes = previewNodes.map((candidate) => makeFlowNode(candidate, { x: base.x - 160, y: base.y - 90 }));
  const flowPreviewEdges = previewEdges.map((edge) => ({
    id: edge.edge_id,
    source: edge.source,
    target: edge.target,
    sourceHandle: edge.source_port,
    targetHandle: edge.target_port,
    type: CURVED_EDGE_DEFAULT_OPTIONS.type
  }));

  return (
    <FloatingPortal>
      <div className="floating-workspace node-preview" style={{ transform: `translate(${index * 22}px, ${index * 18}px)` }}>
        <div className="floating-titlebar">
          <strong>{t(node.title_key, node.title_fallback)}</strong>
          <button onClick={onClose}>x</button>
        </div>
        <div className="node-canvas-shell">
          <div className="node-canvas-title">
            <span>{t("workspace.nodeCanvas", "Node canvas")}</span>
            <small>{getNodeTypeLabel(node.type, t)}</small>
          </div>
          {flowPreviewNodes.length ? (
            <ReactFlow
              nodes={flowPreviewNodes}
              edges={flowPreviewEdges}
              nodeTypes={nodeTypes}
              defaultEdgeOptions={CURVED_EDGE_DEFAULT_OPTIONS}
              fitView
              minZoom={0.3}
              maxZoom={1.4}
              nodesDraggable={false}
              nodesConnectable={false}
              elementsSelectable={false}
            >
              <Background color="#383838" gap={18} />
              <Controls />
            </ReactFlow>
          ) : (
            <div className="empty-node-canvas">{t("workspace.noChildNodes", "No child nodes are present in backend data for this layer.")}</div>
          )}
        </div>
      </div>
    </FloatingPortal>
  );
}

type EdgeLike = {
  edge_id: string;
  source: string;
  target: string;
  source_port?: string | null;
  target_port?: string | null;
};

type LayerAssemblyView = {
  status: string;
  layerSnapshot: Record<string, unknown> | null;
  modules: Record<string, unknown>[];
  nodes: Record<string, unknown>[];
  policies: Record<string, unknown>;
  references: unknown[];
  findings: unknown[];
  moduleCount: number;
  nodeCount: number;
  raw: Record<string, unknown> | null;
};

const LAYER_POLICY_KEYS: Record<string, string[]> = {
  layer_1: ["resident_identity", "resident_blueprint"],
  layer_3: ["safety_policy", "audit_policy", "risk_policy"],
  layer_5: ["memory_policy", "memory_config"],
  layer_8: ["runtime_plan", "fallback_routes"],
  layer_9: ["runtime_requirements", "provider_requirements", "screen_capability_declaration"],
  layer_10: ["lattice_config", "voice_config", "screen_capability_declaration"],
  layer_13: ["manifest", "compile_info", "audit_report"]
};

function arrayFromRecordValue(record: Record<string, unknown>, key: string): Record<string, unknown>[] {
  const value = record[key];
  return Array.isArray(value) ? value.filter(isRecord) : [];
}

function compilePayload(
  compiledDR: unknown,
  drCompileResult: unknown
): { result: Record<string, unknown>; dr: Record<string, unknown>; payload: Record<string, unknown> } {
  const result = isRecord(drCompileResult) ? drCompileResult : {};
  const dr = isRecord(compiledDR) ? compiledDR : isRecord(result.compiled_dr) ? result.compiled_dr : {};
  const payload = isRecord(dr.payload) ? dr.payload : isRecord(result.dr_payload) ? result.dr_payload : {};
  return { result, dr, payload };
}

function payloadArray(payload: Record<string, unknown>, dr: Record<string, unknown>, key: string): Record<string, unknown>[] {
  const graph = isRecord(payload.graph_snapshot) ? payload.graph_snapshot : {};
  return arrayFromRecordValue(payload, key).length
    ? arrayFromRecordValue(payload, key)
    : arrayFromRecordValue(graph, key).length
      ? arrayFromRecordValue(graph, key)
      : arrayFromRecordValue(dr, key);
}

function collectValuesByKey(value: unknown, targetKey: string, depth = 0): unknown[] {
  if (depth > 5) {
    return [];
  }
  if (Array.isArray(value)) {
    return value.flatMap((item) => collectValuesByKey(item, targetKey, depth + 1));
  }
  if (!isRecord(value)) {
    return [];
  }
  const direct = value[targetKey];
  const nested = Object.entries(value).flatMap(([key, item]) => (key === targetKey ? [] : collectValuesByKey(item, targetKey, depth + 1)));
  return direct === undefined ? nested : [direct, ...nested];
}

function flattenReferences(values: unknown[]): unknown[] {
  return values.flatMap((value) => (Array.isArray(value) ? value : value === undefined || value === null ? [] : [value]));
}

function layerFindings(layerId: string, moduleIds: string[], drCompileResult: unknown): unknown[] {
  const result = isRecord(drCompileResult) ? drCompileResult : {};
  const layerAudit = isRecord(result.layer_audit) ? result.layer_audit : {};
  const compileAudit = isRecord(result.compile_audit) ? result.compile_audit : {};
  const candidates = [
    ...(Array.isArray(result.errors) ? result.errors : []),
    ...(Array.isArray(result.warnings) ? result.warnings : []),
    ...(Array.isArray(layerAudit.findings) ? layerAudit.findings : []),
    ...(Array.isArray(compileAudit.findings) ? compileAudit.findings : [])
  ];
  const needles = [layerId, ...moduleIds].filter(Boolean);
  const seen = new Set<string>();
  return candidates.filter((finding) => {
    const text = JSON.stringify(finding);
    if (!needles.some((needle) => text.includes(needle))) {
      return false;
    }
    if (seen.has(text)) {
      return false;
    }
    seen.add(text);
    return true;
  });
}

function layerAssemblyView(layer: CatalogLayerInput, compiledDR: unknown, drCompileResult: unknown): LayerAssemblyView {
  const { result, dr, payload } = compilePayload(compiledDR, drCompileResult);
  const layers =
    arrayFromRecordValue(payload, "13_layers_snapshot").length
      ? arrayFromRecordValue(payload, "13_layers_snapshot")
      : payloadArray(payload, dr, "layers");
  const layerSnapshot = layers.find((item) => item.layer_id === layer.layer_id) ?? null;
  const moduleIds = Array.isArray(layerSnapshot?.module_ids) ? layerSnapshot.module_ids.map(String) : [];
  const modules = payloadArray(payload, dr, "modules").filter((module) => module.layer_id === layer.layer_id || moduleIds.includes(String(module.module_id ?? "")));
  const nodes = payloadArray(payload, dr, "nodes").filter((node) => {
    const data = isRecord(node.data) ? node.data : {};
    return node.layer_id === layer.layer_id || data.layer_id === layer.layer_id || moduleIds.includes(String(data.parent_module ?? ""));
  });
  const policies = Object.fromEntries(
    (LAYER_POLICY_KEYS[layer.layer_id] ?? [])
      .map((key) => [key, payload[key] ?? dr[key] ?? result[key]])
      .filter(([, value]) => value !== undefined && value !== null)
  );
  const references = flattenReferences(collectValuesByKey({ layerSnapshot, modules, policies }, "field_references"));
  const findings = layerFindings(layer.layer_id, moduleIds, drCompileResult);
  const raw = layerSnapshot || modules.length || Object.keys(policies).length || findings.length ? { layer: layerSnapshot, modules, nodes, policies, references, findings } : null;
  const hasCompileResult = isRecord(drCompileResult);
  return {
    status: hasCompileResult ? (isRecord(result) && result.valid === false ? "error" : "compiled") : "uncompiled",
    layerSnapshot,
    modules,
    nodes,
    policies,
    references,
    findings,
    moduleCount: modules.length || moduleIds.length,
    nodeCount: nodes.length,
    raw
  };
}

function AssemblyValue({
  fieldKey,
  moduleCatalog,
  record,
  value,
  language
}: {
  fieldKey: string;
  moduleCatalog: ModuleCatalogResponseV04 | null;
  record: Record<string, unknown>;
  value: unknown;
  language: Language;
}) {
  if (Array.isArray(value)) {
    const primitiveItems = value.filter((item) => !isRecord(item) && !Array.isArray(item));
    if (primitiveItems.length === value.length) {
      return (
        <div className="assembly-chip-list assembly-chip-list--compact">
          {primitiveItems.map((item, index) => {
            const raw = String(item ?? "");
            const label = fieldKey === "module_ids" ? assemblyModuleIdLabel(language, raw, moduleCatalog) : assemblyPrimitiveLabel(language, item);
            return (
              <span className={fieldKey === "module_ids" ? "assembly-module-chip" : undefined} key={`${index}-${raw}`}>
                {fieldKey === "module_ids" ? (
                  <>
                    <strong>{label}</strong>
                    {raw && raw !== label ? <small>{raw}</small> : null}
                  </>
                ) : (
                  label
                )}
              </span>
            );
          })}
        </div>
      );
    }
    return <pre className="assembly-json-block">{safeStringify(value)}</pre>;
  }
  if (isRecord(value)) {
    return <pre className="assembly-json-block">{safeStringify(value)}</pre>;
  }
  if (fieldKey === "layer_name" && typeof value === "string") {
    const layerId = typeof record.layer_id === "string" ? record.layer_id : "";
    const layerOrder = typeof record.layer_order === "number" ? record.layer_order : "";
    return <span className="assembly-value-text">{i18nCandidate(language, [`layer.${layerId}`, `layer.${layerOrder}.name`], value)}</span>;
  }
  return <span className="assembly-value-text">{assemblyPrimitiveLabel(language, value)}</span>;
}

function AssemblyKeyValueList({
  emptyText,
  language,
  moduleCatalog,
  value
}: {
  emptyText: string;
  language: Language;
  moduleCatalog: ModuleCatalogResponseV04 | null;
  value: Record<string, unknown> | null;
}) {
  const entries = value ? Object.entries(value).filter(([, item]) => item !== undefined && item !== null && item !== "") : [];
  if (!entries.length) {
    return <p className="assembly-empty">{emptyText}</p>;
  }
  return (
    <dl className="assembly-kv-list">
      {entries.map(([key, item]) => (
        <div key={key}>
          <dt>{assemblyFieldLabel(language, key)}</dt>
          <dd>
            <AssemblyValue fieldKey={key} moduleCatalog={moduleCatalog} record={value ?? {}} value={item} language={language} />
          </dd>
        </div>
      ))}
    </dl>
  );
}

function AssemblyContentView({
  assembly,
  language,
  moduleCatalog,
  t
}: {
  assembly: LayerAssemblyView;
  language: Language;
  moduleCatalog: ModuleCatalogResponseV04 | null;
  t: (key: string, fallback?: string) => string;
}) {
  if (!assembly.raw) {
    return <div className="assembly-empty assembly-empty--panel">{t("assembly.panel.empty")}</div>;
  }
  return (
    <div className="assembly-content">
      <section className="assembly-section">
        <h4>{t("assembly.section.summary")}</h4>
        <AssemblyKeyValueList value={assembly.layerSnapshot} language={language} moduleCatalog={moduleCatalog} emptyText={t("assembly.panel.noFields")} />
      </section>
      <section className="assembly-section">
        <h4>{t("assembly.section.modules")}</h4>
        {assembly.modules.length ? (
          <div className="assembly-chip-list">
            {assembly.modules.map((module) => {
              const moduleId = String(module.module_id ?? module.id ?? "");
              const label = assemblyModuleLabel(language, module, moduleCatalog);
              return (
                <span className="assembly-module-chip" key={moduleId || label}>
                  <strong>{label}</strong>
                  {moduleId && moduleId !== label ? <small>{moduleId}</small> : null}
                </span>
              );
            })}
          </div>
        ) : (
          <p className="assembly-empty">{t("assembly.panel.noFields")}</p>
        )}
      </section>
      <section className="assembly-section">
        <h4>{t("assembly.section.policySummary")}</h4>
        <AssemblyKeyValueList value={assembly.policies} language={language} moduleCatalog={moduleCatalog} emptyText={t("assembly.panel.noFields")} />
      </section>
      <section className="assembly-section">
        <h4>{t("assembly.section.fieldReferences")}</h4>
        {assembly.references.length ? (
          <ul className="assembly-reference-list">
            {assembly.references.map((reference, index) => (
              <li key={`${index}-${String(typeof reference === "object" ? index : reference)}`}>{typeof reference === "object" ? safeStringify(reference) : String(reference)}</li>
            ))}
          </ul>
        ) : (
          <p className="assembly-empty">{t("assembly.panel.noReferences")}</p>
        )}
      </section>
      <section className="assembly-section">
        <h4>{t("assembly.section.validation")}</h4>
        {assembly.findings.length ? (
          <ul className="assembly-validation-list">
            {assembly.findings.map((finding, index) => (
              <li key={`${index}-${safeStringify(finding)}`}>
                <strong>{validationFindingMessage(language, finding)}</strong>
                {isRecord(finding) && typeof finding.code === "string" ? <code>{finding.code}</code> : null}
              </li>
            ))}
          </ul>
        ) : (
          <p className="assembly-empty">{t("assembly.validation.noWarnings")}</p>
        )}
      </section>
      <details className="assembly-section assembly-raw-json">
        <summary>{t("assembly.tab.rawJson")}</summary>
        <pre>{safeStringify(assembly.raw)}</pre>
      </details>
    </div>
  );
}

function FloatingWorkspace({
  index,
  layer,
  moduleCatalog,
  edges,
  t,
  moduleNames,
  onClose,
  onSelectNode,
  onPreviewNode
}: {
  index: number;
  layer: CatalogLayerInput;
  moduleCatalog: ModuleCatalogResponseV04 | null;
  edges: EdgeLike[];
  t: (key: string, fallback?: string) => string;
  moduleNames: Record<string, string>;
  onClose: () => void;
  onSelectNode: (node: WorkflowNode) => void;
  onPreviewNode: (node: WorkflowNode) => void;
}) {
  const label = moduleCatalog ? moduleCatalog.layers.find((l) => l.layer_id === layer.layer_id)?.layer_name ?? "" : "";
  return (
    <FloatingPortal>
      <div className="floating-workspace" style={{ transform: `translate(${index * 22}px, ${index * 18}px)` }}>
        <div className="floating-titlebar">
          <strong>
            L{layer.layer_order} {label}
          </strong>
          <button onClick={onClose}>x</button>
        </div>
        <LayerWorkspacePanel
          layer={layer}
          moduleCatalog={moduleCatalog}
          edges={edges}
          t={t}
          mode="window"
          moduleNames={moduleNames}
          onOpen={() => undefined}
          onSelectNode={onSelectNode}
          onPreviewNode={onPreviewNode}
        />
      </div>
    </FloatingPortal>
  );
}

// Circular-safe JSON for rendering execution results. A workflow result may
// contain shared/circular references; a raw JSON.stringify would throw during
// render and white-screen the app.
function safeStringify(value: unknown) {
  try {
    return safeSerialize(value, 2);
  } catch (error) {
    return String((error as Error)?.message ?? value);
  }
}

function validationFindings(validation: unknown, key: "errors" | "warnings") {
  if (!isRecord(validation)) {
    return [];
  }
  const value = validation[key];
  return Array.isArray(value) ? value : [];
}

function ValidationSummary({ validation, t }: { validation: unknown; t: (key: string, fallback?: string) => string }) {
  const language = useCanvasStore((state) => state.language);
  const errors = validationFindings(validation, "errors");
  const warnings = validationFindings(validation, "warnings");

  if (!validation) {
    return <p className="canvas-debug-trace-panel__empty">{t("inspector.noValidation")}</p>;
  }

  return (
    <div className="validation-summary">
      <section>
        <h4>{t("assembly.validation.errors")}</h4>
        {errors.length ? (
          <ul>
            {errors.map((error, index) => {
              const code = isRecord(error) && typeof error.code === "string" ? error.code : `${index}`;
              return (
                <li key={`${code}-${index}`}>
                  <strong>{validationFindingMessage(language, error)}</strong>
                  <details>
                    <summary>{t("assembly.validation.code")}</summary>
                    <code>{code}</code>
                  </details>
                </li>
              );
            })}
          </ul>
        ) : (
          <p>{t("assembly.validation.noErrors")}</p>
        )}
      </section>
      <section>
        <h4>{t("assembly.validation.warnings")}</h4>
        {warnings.length ? (
          <ul>
            {warnings.map((warning, index) => {
              const code = isRecord(warning) && typeof warning.code === "string" ? warning.code : `${index}`;
              return (
                <li key={`${code}-${index}`}>
                  <strong>{validationFindingMessage(language, warning)}</strong>
                  <details>
                    <summary>{t("assembly.validation.code")}</summary>
                    <code>{code}</code>
                  </details>
                </li>
              );
            })}
          </ul>
        ) : (
          <p>{t("assembly.validation.noWarnings")}</p>
        )}
      </section>
      <details>
        <summary>{t("inspector.rawJson")}</summary>
        <pre>{safeStringify(validation)}</pre>
      </details>
    </div>
  );
}

// Ensure a node exposes at least one in/out port so WorkflowNodeCard renders
// connectable handles inside the module canvas (handles use ids p_in / p_out).
function ensurePorts(node: WorkflowNode): WorkflowNode {
  const inputs = node.ports?.inputs?.length ? node.ports.inputs : [{ port_id: "p_in" }];
  const outputs = node.ports?.outputs?.length ? node.ports.outputs : [{ port_id: "p_out" }];
  return { ...node, ports: { ...(node.ports ?? {}), inputs, outputs } } as unknown as WorkflowNode;
}

function normalizeModuleGraphNodes(nodes: unknown[]): Node[] {
  return nodes.filter(isRecord).map((node, index) => {
    const existingSchema = isRecord(node.data) && isRecord(node.data.schemaNode) ? (node.data.schemaNode as unknown as WorkflowNode) : null;
    if (existingSchema) {
      return {
        ...node,
        id: typeof node.id === "string" ? node.id : existingSchema.node_id,
        type: typeof node.type === "string" ? node.type : "workflowNode",
        position: isRecord(node.position)
          ? { x: Number(node.position.x) || 0, y: Number(node.position.y) || 0 }
          : existingSchema.position ?? { x: 120, y: 70 + index * 130 },
        data: { ...(isRecord(node.data) ? node.data : {}), schemaNode: ensurePorts(existingSchema) },
      } as Node;
    }
    const workflowNode = ensurePorts(node as unknown as WorkflowNode);
    return {
      id: workflowNode.node_id,
      type: "workflowNode",
      position: workflowNode.position ?? { x: 120, y: 70 + index * 130 },
      deletable: true,
      data: { schemaNode: workflowNode },
    } as Node;
  });
}

function normalizeModuleGraphEdges(edges: unknown[]): Edge[] {
  return edges.filter(isRecord).map((edge, index) => {
    const source = String(edge.source || edge.source_node_id || "");
    const target = String(edge.target || edge.target_node_id || "");
    const id = String(edge.id || edge.edge_id || `${source}_to_${target}_${index + 1}`);
    return {
      ...edge,
      id,
      source,
      sourceHandle: typeof edge.sourceHandle === "string" ? edge.sourceHandle : String(edge.source_port || edge.source_output || "p_out"),
      target,
      targetHandle: typeof edge.targetHandle === "string" ? edge.targetHandle : String(edge.target_port || edge.target_input || "p_in"),
      type: typeof edge.type === "string" ? edge.type : "smoothstep",
    } as Edge;
  });
}

function nodeWidth(node: Node) {
  return node.measured?.width ?? node.width ?? 255;
}

function nodeHeight(node: Node) {
  return node.measured?.height ?? node.height ?? 100;
}

function selectedOrAllNodeIds(nodes: Node[]) {
  const selected = nodes.filter((node) => node.selected).map((node) => node.id);
  return selected.length ? new Set(selected) : new Set(nodes.map((node) => node.id));
}

function alignFlowNodes(nodes: Node[], ids: Set<string>, action: AlignAction) {
  const targets = nodes.filter((node) => ids.has(node.id));
  if (targets.length < 2) {
    return nodes;
  }
  const left = Math.min(...targets.map((node) => node.position.x));
  const right = Math.max(...targets.map((node) => node.position.x + nodeWidth(node)));
  const top = Math.min(...targets.map((node) => node.position.y));
  const bottom = Math.max(...targets.map((node) => node.position.y + nodeHeight(node)));
  const centerX = targets.reduce((sum, node) => sum + node.position.x + nodeWidth(node) / 2, 0) / targets.length;
  const centerY = targets.reduce((sum, node) => sum + node.position.y + nodeHeight(node) / 2, 0) / targets.length;

  return nodes.map((node) => {
    if (!ids.has(node.id)) {
      return node;
    }
    const nextPosition = { ...node.position };
    if (action === "left") nextPosition.x = left;
    if (action === "right") nextPosition.x = right - nodeWidth(node);
    if (action === "top") nextPosition.y = top;
    if (action === "bottom") nextPosition.y = bottom - nodeHeight(node);
    if (action === "center-x") nextPosition.x = centerX - nodeWidth(node) / 2;
    if (action === "center-y") nextPosition.y = centerY - nodeHeight(node) / 2;
    return { ...node, position: nextPosition };
  });
}

function distributeFlowNodes(nodes: Node[], ids: Set<string>, action: DistributeAction) {
  const targets = nodes.filter((node) => ids.has(node.id));
  if (targets.length < 3) {
    return nodes;
  }
  const sorted = [...targets].sort((a, b) => (action === "horizontal" ? a.position.x - b.position.x : a.position.y - b.position.y));
  const first = sorted[0];
  const last = sorted[sorted.length - 1];
  const start = action === "horizontal" ? first.position.x : first.position.y;
  const end = action === "horizontal" ? last.position.x : last.position.y;
  const step = (end - start) / (sorted.length - 1);
  const positions = new Map(sorted.map((node, index) => [node.id, start + step * index]));
  return nodes.map((node) => {
    const position = positions.get(node.id);
    if (position === undefined) {
      return node;
    }
    return {
      ...node,
      position: action === "horizontal" ? { ...node.position, x: position } : { ...node.position, y: position }
    };
  });
}

function arrangeFlowNodes(nodes: Node[]) {
  const columns = Math.max(1, Math.ceil(Math.sqrt(nodes.length || 1)));
  return nodes.map((node, index) => ({
    ...node,
    position: {
      x: 120 + (index % columns) * 320,
      y: 90 + Math.floor(index / columns) * 150
    }
  }));
}

function CanvasContextMenu({ menu, onClose }: { menu: CanvasContextMenuState; onClose: () => void }) {
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        onClose();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [onClose]);

  return (
    <div className="canvas-context-menu-backdrop" onClick={onClose} onContextMenu={(event) => event.preventDefault()}>
      <div
        className="canvas-context-menu"
        style={{ left: menu.x, top: menu.y }}
        role="menu"
        onClick={(event) => event.stopPropagation()}
      >
        {menu.items.map((item, index) => (
          <CanvasContextMenuRow key={`${index}-${item.label}`} item={item} onClose={onClose} />
        ))}
      </div>
    </div>
  );
}

function CanvasContextMenuRow({ item, onClose }: { item: CanvasContextMenuItem; onClose: () => void }) {
  const [open, setOpen] = useState(false);
  const closeTimerRef = useRef<number | null>(null);
  const cancelClose = () => {
    if (closeTimerRef.current !== null) {
      window.clearTimeout(closeTimerRef.current);
      closeTimerRef.current = null;
    }
  };
  const scheduleClose = () => {
    cancelClose();
    closeTimerRef.current = window.setTimeout(() => setOpen(false), 360);
  };
  useEffect(() => cancelClose, []);
  if (item.children?.length) {
    return (
      <div
        className={`canvas-context-menu__group ${open ? "is-open" : ""}`}
        onMouseEnter={() => {
          cancelClose();
          setOpen(true);
        }}
        onMouseLeave={scheduleClose}
      >
        <button
          type="button"
          role="menuitem"
          className="canvas-context-menu__parent"
          disabled={item.disabled}
          aria-expanded={open}
          onClick={(event) => {
            event.stopPropagation();
            if (!item.disabled) {
              cancelClose();
              setOpen((value) => !value);
            }
          }}
        >
          <span>{item.label}</span>
          <span className="canvas-context-menu__caret">▸</span>
        </button>
        {open ? (
          <div className="canvas-context-menu__submenu" role="menu">
            {item.children.map((child, index) => (
              <CanvasContextMenuRow key={`${index}-${child.label}`} item={child} onClose={onClose} />
            ))}
          </div>
        ) : null}
      </div>
    );
  }
  return (
    <button
      type="button"
      role="menuitem"
      className={item.danger ? "is-danger" : ""}
      disabled={item.disabled}
      onClick={() => {
        if (item.disabled) {
          return;
        }
        onClose();
        item.onSelect?.();
      }}
    >
      {item.label}
    </button>
  );
}


// Embedded, in-app module sub-canvas. Its ReactFlow state is isolated from the
// main canvas and persisted under the layer-scoped module instance id.
function ModuleCanvasPanel({
  moduleNode,
  workflow,
  initialSubnodes,
  pendingAdd,
  libraryNodeTypes,
  language,
  t,
  onRenameModule,
  onExecutionResult,
  onAssistantPanelChange,
  onClose
}: {
  moduleNode: WorkflowNode;
  workflow: Workflow | null;
  initialSubnodes: WorkflowNode[];
  pendingAdd: PendingModuleAdd | null;
  libraryNodeTypes: ModuleNodeType[];
  language: Language;
  t: (key: string, fallback?: string) => string;
  onRenameModule: (id: string, name: string) => void;
  onExecutionResult: (result: unknown) => void;
  onAssistantPanelChange: (panel: ModuleAssistantPanelState | null) => void;
  onClose: () => void;
}) {
  const title = translate(language, moduleNode.title_key, moduleNode.title_fallback);
  const handledAddRequestRef = useRef<number | null>(null);
  const moduleFlowRef = useRef<ReactFlowInstance | null>(null);
  const [contextMenu, setContextMenu] = useState<CanvasContextMenuState | null>(null);
  const [copiedModuleNode, setCopiedModuleNode] = useState<WorkflowNode | null>(null);
  const storedModuleGraph = useCanvasStore((state) => state.moduleGraphs[moduleNode.node_id]);

	  // Seed module sub-canvas from the current v0.4 schema-derived view only.
	  const initialGraph = useMemo<{ nodes: Node[]; edges: Edge[] }>(() => {
	    console.log("[NODE-E] initialGraph computing for moduleNode:", { moduleNodeId: moduleNode.node_id });
      if (storedModuleGraph?.nodes?.length || storedModuleGraph?.edges?.length) {
        console.log("[NODE-E-HYDRATE] moduleGraphs restored from store:", {
          moduleId: moduleNode.node_id,
          nodeCount: storedModuleGraph.nodes?.length ?? 0,
          edgeCount: storedModuleGraph.edges?.length ?? 0
        });
        return {
          nodes: normalizeModuleGraphNodes(storedModuleGraph.nodes ?? []),
          edges: normalizeModuleGraphEdges(storedModuleGraph.edges ?? [])
        };
      }
	    // 先尝试从 localStorage 恢复模块图
	    const saved = loadModuleGraphState(moduleNode.node_id);
	    if (saved) {
	      console.log("[NODE-E-HYDRATE] moduleGraphs restored from localStorage:", {
	        moduleId: moduleNode.node_id,
	        nodeCount: saved.nodes?.length ?? 0,
	        edgeCount: saved.edges?.length ?? 0
	      });
	      return {
	        nodes: normalizeModuleGraphNodes(saved.nodes ?? []),
	        edges: normalizeModuleGraphEdges(saved.edges ?? [])
	      };
	    }
	    
	    console.log("[NODE-E] no saved moduleGraphs, using initialSubnodes:", {
	      moduleId: moduleNode.node_id,
	      initialSubnodeCount: initialSubnodes.length
	    });
	    
	    // 如果没有保存的数据，则从初始子节点生成
	    // Module is a container, not an execution node — never show the module's own
	    // node inside its canvas. Only workflow nodes (input/transform/personality/...).
	    const seeds = initialSubnodes.filter((node) => String(node.type) !== "module");
	    return {
      nodes: seeds.map((node, index) => ({
        id: node.node_id,
        type: "workflowNode",
        position:
          node.position && (node.position.x || node.position.y) ? node.position : { x: 120, y: 70 + index * 130 },
        deletable: true,
        data: { schemaNode: ensurePorts(node) }
      })),
      edges: []
    };
  }, [moduleNode, initialSubnodes, storedModuleGraph]);

  const [moduleNodes, setModuleNodes] = useNodesState(initialGraph.nodes);
  const [moduleEdges, setModuleEdges] = useEdgesState<Edge>(initialGraph.edges);
  const [selectedId, setSelectedId] = useState<string>("");
  const [assistantFieldKey, setAssistantFieldKey] = useState("");
  const [executionResult, setExecutionResult] = useState<unknown>(null);
  const [executionError, setExecutionError] = useState<string | null>(null);
  const [runStatus, setRunStatus] = useState<RunWorkflowStatus>("idle");
  const [runInputText, setRunInputText] = useState("");
  const [showModuleMiniMap, setShowModuleMiniMap] = useState(true);
  const [showModuleDebugTracePanel, setShowModuleDebugTracePanel] = useState(true);
	  const addedRef = useRef(0);
  const moduleNodesRef = useRef(moduleNodes);
  const moduleEdgesRef = useRef(moduleEdges);
  const moduleHistoryRef = useRef<FlowHistoryState>({ past: [], future: [], restoring: false });
  const [moduleHistoryVersion, setModuleHistoryVersion] = useState(0);

  useEffect(() => {
    moduleNodesRef.current = moduleNodes;
  }, [moduleNodes]);

  useEffect(() => {
    moduleEdgesRef.current = moduleEdges;
  }, [moduleEdges]);

  const persistModuleGraphNow = useCallback(
    (nodesToPersist: Node[], edgesToPersist: Edge[] = moduleEdgesRef.current) => {
      const saved = saveModuleGraphState(moduleNode.node_id, nodesToPersist, edgesToPersist);
      if (!saved) {
        console.warn("[NODE-E-PERSIST] failed to persist module graph immediately", {
          moduleId: moduleNode.node_id,
          nodeCount: nodesToPersist.length,
          edgeCount: edgesToPersist.length
        });
      }
      useCanvasStore
        .getState()
        .updateModuleGraph(moduleNode.node_id, nodesToPersist as unknown as WorkflowNode[], edgesToPersist as unknown as WorkflowEdge[]);
    },
    [moduleNode.node_id]
  );

  const pushModuleHistory = useCallback(() => {
    if (moduleHistoryRef.current.restoring) {
      return;
    }
    moduleHistoryRef.current.past = [
      ...moduleHistoryRef.current.past.slice(-(CANVAS_HISTORY_LIMIT - 1)),
      cloneFlowHistorySnapshot(moduleNodesRef.current, moduleEdgesRef.current)
    ];
    moduleHistoryRef.current.future = [];
    setModuleHistoryVersion((version) => version + 1);
  }, []);

  const restoreModuleHistorySnapshot = useCallback(
    (snapshot: FlowHistorySnapshot) => {
      const nextNodes = cloneCanvasValue(snapshot.nodes);
      const nextEdges = cloneCanvasValue(snapshot.edges);
      moduleHistoryRef.current.restoring = true;
      moduleNodesRef.current = nextNodes;
      moduleEdgesRef.current = nextEdges;
      setModuleNodes(nextNodes);
      setModuleEdges(nextEdges);
      persistModuleGraphNow(nextNodes, nextEdges);
      window.queueMicrotask(() => {
        moduleHistoryRef.current.restoring = false;
      });
    },
    [persistModuleGraphNow, setModuleEdges, setModuleNodes]
  );

  const undoModuleCanvas = useCallback(() => {
    const previous = moduleHistoryRef.current.past.pop();
    if (!previous) {
      return;
    }
    moduleHistoryRef.current.future = [
      ...moduleHistoryRef.current.future.slice(-(CANVAS_HISTORY_LIMIT - 1)),
      cloneFlowHistorySnapshot(moduleNodesRef.current, moduleEdgesRef.current)
    ];
    restoreModuleHistorySnapshot(previous);
    setModuleHistoryVersion((version) => version + 1);
  }, [restoreModuleHistorySnapshot]);

  const redoModuleCanvas = useCallback(() => {
    const next = moduleHistoryRef.current.future.pop();
    if (!next) {
      return;
    }
    moduleHistoryRef.current.past = [
      ...moduleHistoryRef.current.past.slice(-(CANVAS_HISTORY_LIMIT - 1)),
      cloneFlowHistorySnapshot(moduleNodesRef.current, moduleEdgesRef.current)
    ];
    restoreModuleHistorySnapshot(next);
    setModuleHistoryVersion((version) => version + 1);
  }, [restoreModuleHistorySnapshot]);

  const canUndoModule = moduleHistoryVersion >= 0 && moduleHistoryRef.current.past.length > 0;
  const canRedoModule = moduleHistoryVersion >= 0 && moduleHistoryRef.current.future.length > 0;

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (shouldUseNativeContextMenu(event.target)) {
        return;
      }
      const action = isUndoRedoShortcut(event);
      if (!action) {
        return;
      }
      event.preventDefault();
      if (action === "undo") {
        undoModuleCanvas();
      } else {
        redoModuleCanvas();
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [redoModuleCanvas, undoModuleCanvas]);

  useEffect(() => {
    const flushModuleGraph = () => {
      persistModuleGraphNow(moduleNodesRef.current, moduleEdgesRef.current);
    };
    window.addEventListener("beforeunload", flushModuleGraph);
    window.addEventListener("pagehide", flushModuleGraph);
    return () => {
      flushModuleGraph();
      window.removeEventListener("beforeunload", flushModuleGraph);
      window.removeEventListener("pagehide", flushModuleGraph);
    };
  }, [persistModuleGraphNow]);

  const addModuleNode = useCallback((type: ModuleNodeType, position?: { x: number; y: number }) => {
    console.log("[P1-NODE-CRUD] addModuleNode: adding new node", { type, position });
    pushModuleHistory();
    addedRef.current += 1;
    const seq = addedRef.current;
    const ownerLayerId = String(moduleNode.data?.parent_layer || moduleNode.data?.layer_id || layerIdFromInstanceId(moduleNode.node_id) || "");
    const ownerModuleId = String(moduleNode.data?.module_catalog_id || moduleNode.data?.module_id || moduleIdFromInstanceId(moduleNode.node_id) || moduleNode.module_id || "");
    const ownerModuleInstanceId = ownerLayerId && ownerModuleId ? `${ownerLayerId}${MODULE_INSTANCE_SEPARATOR}${ownerModuleId}` : moduleNode.node_id;
    const id = `${ownerModuleInstanceId}_${type}_${Date.now()}_${seq}`;
    const definition = getNodeDefinition(type);
    const referenceParams = referenceNodeDefaultParams(type, ownerLayerId);
    const referenceColor = referenceNodeDefaultColor(type);
    const schemaNode = ensurePorts({
      node_id: id,
      type,
      category: definition?.category ?? backendNodeCategory(type),
      title_key: type === "reference_output" ? "nodes.referenceOutput.title" : type === "reference_input" ? "nodes.referenceInput.title" : `node.type.${type}`,
      title_fallback: definition?.display_name ?? type,
      position: { x: 0, y: 0 },
      lock_level: "editable",
      locale: null,
      data: {
        parent_module: ownerModuleInstanceId,
        module_instance_id: ownerModuleInstanceId,
        catalog_module_id: ownerModuleId,
        layer_id: ownerLayerId,
        module_id: ownerModuleId,
        ...(referenceColor ? { ui_color: referenceColor } : {}),
        ...(Object.keys(referenceParams).length ? { params: referenceParams, ...referenceParams } : {}),
        ...Object.fromEntries((definition?.input_schema ?? []).map((field: NodeInputField) => [field.key, field.default ?? ""]))
      },
      input_schema: definition?.input_schema,
      output_schema: definition?.output_schema,
      ports: { inputs: [], outputs: [] },
      validation: null,
      layer_id: ownerLayerId,
      module_id: ownerModuleId,
      collapsed_sections: type === "reference_input" || type === "reference_output" ? ["core", "advanced", "runtime"] : ["advanced", "runtime"]
    } as unknown as WorkflowNode);
    setModuleNodes((current) => {
      const next = [
        ...current,
        {
          id,
          type: "workflowNode",
          position: position ?? { x: 360, y: 80 + current.length * 70 },
          deletable: true,
          data: { schemaNode }
        }
      ];
      console.log("[P1-NODE-CRUD] addModuleNode success:", { 
        nodeId: id, 
        type, 
        totalNodesAfter: next.length 
      });
      return next;
    });
    setSelectedId(id);
    setAssistantFieldKey("");
  }, [moduleNode.node_id, pushModuleHistory, setModuleNodes]);

  const handleModuleCanvasDrop = useCallback(
    (event: ReactDragEvent) => {
      event.preventDefault();
      const type = readNodeDragType(event);
      if (!type) {
        return;
      }
      const instance = moduleFlowRef.current;
      const position = instance?.screenToFlowPosition
        ? instance.screenToFlowPosition({ x: event.clientX, y: event.clientY })
        : undefined;
      addModuleNode(type, position);
    },
    [addModuleNode]
  );

  useEffect(() => {
    if (!pendingAdd || pendingAdd.moduleId !== moduleNode.node_id || handledAddRequestRef.current === pendingAdd.requestId) {
      return;
    }
    handledAddRequestRef.current = pendingAdd.requestId;
    addModuleNode(pendingAdd.nodeType);
  }, [addModuleNode, moduleNode.node_id, pendingAdd]);

  const onConnect = useCallback(
    (connection: Connection) => {
      if (!connection.source || !connection.target) {
        return;
      }
      const currentNodeIds = new Set(moduleNodesRef.current.map((node) => node.id));
      if (!currentNodeIds.has(connection.source) || !currentNodeIds.has(connection.target)) {
        return;
      }
      pushModuleHistory();
      const nextEdges = addEdge(connection, moduleEdgesRef.current);
      moduleEdgesRef.current = nextEdges;
      setModuleEdges(nextEdges);
      persistModuleGraphNow(moduleNodesRef.current, nextEdges);
    },
    [persistModuleGraphNow, pushModuleHistory, setModuleEdges]
  );

  const onModuleNodesChange = useCallback(
    (changes: NodeChange[]) => {
      const removedIds = changes.filter((change) => change.type === "remove").map((change) => change.id);
      if (removedIds.length) {
        pushModuleHistory();
      }
      const nextNodes = applyNodeChanges(changes, moduleNodesRef.current);
      moduleNodesRef.current = nextNodes;
      setModuleNodes(nextNodes);

      let nextEdges = moduleEdgesRef.current;
      if (removedIds.length) {
        const removed = new Set(removedIds);
        nextEdges = nextEdges.filter((edge) => !removed.has(edge.source) && !removed.has(edge.target));
        moduleEdgesRef.current = nextEdges;
        setModuleEdges(nextEdges);
        setSelectedId((current) => (current && removed.has(current) ? "" : current));
        setAssistantFieldKey("");
      }

      const completedPositionChange = changes.some(
        (change) => change.type === "position" && change.dragging !== true
      );
      if (removedIds.length || completedPositionChange) {
        persistModuleGraphNow(nextNodes, nextEdges);
      }
    },
    [persistModuleGraphNow, pushModuleHistory, setModuleEdges, setModuleNodes]
  );

  const onModuleEdgesChange = useCallback(
    (changes: EdgeChange[]) => {
      if (changes.some((change) => change.type === "remove")) {
        pushModuleHistory();
      }
      const nextEdges = applyEdgeChanges(changes, moduleEdgesRef.current);
      moduleEdgesRef.current = nextEdges;
      setModuleEdges(nextEdges);
      persistModuleGraphNow(moduleNodesRef.current, nextEdges);
    },
    [persistModuleGraphNow, pushModuleHistory, setModuleEdges]
  );

  const handleModuleNodesDelete = useCallback(
    (deleted: Node[]) => {
      const removed = new Set(deleted.map((node) => node.id));
      if (!removed.size) {
        return;
      }
      const nextNodes = moduleNodesRef.current.filter((node) => !removed.has(node.id));
      const nextEdges = moduleEdgesRef.current.filter((edge) => !removed.has(edge.source) && !removed.has(edge.target));
      moduleNodesRef.current = nextNodes;
      moduleEdgesRef.current = nextEdges;
      setModuleNodes(nextNodes);
      setModuleEdges(nextEdges);
      persistModuleGraphNow(nextNodes, nextEdges);
      setSelectedId((current) => (current && removed.has(current) ? "" : current));
      setAssistantFieldKey("");
    },
    [persistModuleGraphNow, setModuleEdges, setModuleNodes]
  );

  const selectedSchema = useMemo(() => {
    const found = moduleNodes.find((node) => node.id === selectedId);
    return (found?.data as { schemaNode?: WorkflowNode } | undefined)?.schemaNode ?? null;
  }, [moduleNodes, selectedId]);

  const patchModuleNodeData = useCallback(
    (id: string, patch: Record<string, unknown>) => {
      pushModuleHistory();
      const nextNodes = moduleNodesRef.current.map((node) => {
        if (node.id !== id) {
          return node;
        }
        const existing = node.data as { schemaNode?: WorkflowNode };
        const schema = existing.schemaNode ?? ({} as WorkflowNode);
        return {
          ...node,
          data: {
            ...existing,
            schemaNode: { ...schema, data: { ...(schema.data ?? {}), ...patch } }
          }
        };
      });
      moduleNodesRef.current = nextNodes;
      setModuleNodes(nextNodes);
      persistModuleGraphNow(nextNodes);
    },
    [persistModuleGraphNow, pushModuleHistory, setModuleNodes]
  );

  const assistantRequest = useMemo<StudioAssistantRequest>(() => {
    const layerId = String(moduleNode.data?.parent_layer || layerIdFromInstanceId(moduleNode.node_id) || "");
    const moduleId = String(moduleNode.data?.module_catalog_id || moduleIdFromInstanceId(moduleNode.node_id) || moduleNode.module_id || moduleNode.node_id);
    const workflowModules = Array.isArray((workflow as unknown as { modules?: unknown[] } | null)?.modules)
      ? ((workflow as unknown as { modules?: unknown[] }).modules ?? [])
      : [];
    const currentModule =
      workflowModules.find((item) => isRecord(item) && String(item.module_id || "") === moduleId) ??
      {
        module_id: moduleId,
        module_instance_id: moduleNode.node_id,
        title: title,
      };
    const neighborModules = workflowModules.filter((item) => isRecord(item) && String(item.layer_id || "") === layerId);
    const nodeData = isRecord(selectedSchema?.data) ? selectedSchema.data : {};
    const compileFields = selectedSchema ? fieldsFromNodeData(nodeData) : [];
    const selectedCompileField =
      assistantFieldKey && compileFields.length
        ? compileFields.find((field, index) => compileTimeFieldMatches(field, index, assistantFieldKey)) ?? null
        : null;
    const schemaFields = selectedSchema
      ? (((selectedSchema as unknown as { input_schema?: NodeInputField[] }).input_schema ?? getNodeDefinition(String(selectedSchema.type))?.input_schema ?? []) as NodeInputField[])
      : [];
    const schemaField = assistantFieldKey ? schemaFields.find((field) => field.key === assistantFieldKey) ?? null : null;
    const currentField = selectedCompileField
      ? {
          field_key: assistantFieldKey,
          field: selectedCompileField,
          value: selectedCompileField.value,
        }
      : schemaField
        ? {
            field_key: assistantFieldKey,
            label: schemaField.label,
            type: schemaField.type,
            value: nodeData[assistantFieldKey],
          }
        : null;

    return {
      canvas_id: workflow?.template_type ?? "schema_v04",
      layer_id: layerId || undefined,
      module_id: moduleId || undefined,
      node_id: selectedSchema?.node_id ?? (selectedId || undefined),
      field_key: assistantFieldKey || undefined,
      selected_text: "",
      mode: "explain",
      context: {
        resident_identity: {
          source_layer: "layer_1",
        },
        current_layer: {
          layer_id: layerId,
        },
        current_module: currentModule,
        current_node: selectedSchema,
        current_field: currentField,
        field_references: [],
        neighbor_modules: neighborModules,
        module_graph: {
          module_node_id: moduleNode.node_id,
          nodes: moduleNodes.map((node) => (node.data as { schemaNode?: WorkflowNode } | undefined)?.schemaNode).filter(Boolean),
          edges: moduleEdges,
        },
      },
    };
  }, [assistantFieldKey, moduleEdges, moduleNode, moduleNodes, selectedId, selectedSchema, title, workflow]);

  const applyAssistantPatch = useCallback(
    (patch: StudioAssistantPatch) => {
      if (!selectedId) {
        return;
      }
      const targetField = patch.target_field || assistantFieldKey;
      if (!targetField) {
        return;
      }
      const targetNode = moduleNodesRef.current.find((node) => node.id === selectedId);
      const schemaNode = (targetNode?.data as { schemaNode?: WorkflowNode } | undefined)?.schemaNode;
      const nodeData = isRecord(schemaNode?.data) ? schemaNode.data : {};
      const fields = fieldsFromNodeData(nodeData);
      const fieldIndex = fields.findIndex((field, index) => compileTimeFieldMatches(field, index, targetField));
      if (fieldIndex >= 0) {
        const params = paramsFromNodeData(nodeData);
        const nextFields = updateFieldValue(fields, fieldIndex, patch.proposed_value);
        patchModuleNodeData(selectedId, { fields: nextFields, params: { ...params, fields: nextFields } });
        return;
      }
      patchModuleNodeData(selectedId, { [targetField]: patch.proposed_value });
    },
    [assistantFieldKey, patchModuleNodeData, selectedId]
  );

  useEffect(() => {
    onAssistantPanelChange({
      title: t("assistant.panel.title", "Assistant"),
      meta: title,
      request: assistantRequest,
      canApplyPatch: Boolean(selectedId && selectedSchema),
      onApplyPatch: applyAssistantPatch,
    });
    return () => onAssistantPanelChange(null);
  }, [applyAssistantPatch, assistantRequest, onAssistantPanelChange, selectedId, selectedSchema, t, title]);

  // 自动保存模块画布图 (nodes + edges) 到 localStorage
  useEffect(() => {
    const timer = setTimeout(() => {
      console.log("[NODE-E-PERSIST] saveModuleGraphState called:", {
        moduleId: moduleNode.node_id,
        nodeCount: moduleNodes.length,
        edgeCount: moduleEdges.length
      });
      const saved = saveModuleGraphState(moduleNode.node_id, moduleNodes, moduleEdges);
      if (!saved) {
        console.warn("[NODE-E-PERSIST] failed to persist module graph during autosave", {
          moduleId: moduleNode.node_id,
          nodeCount: moduleNodes.length,
          edgeCount: moduleEdges.length
        });
      }
      useCanvasStore.getState().updateModuleGraph(moduleNode.node_id, moduleNodes as unknown as WorkflowNode[], moduleEdges as unknown as WorkflowEdge[]);
    }, 500);
    return () => clearTimeout(timer);
  }, [moduleNode.node_id, moduleNodes, moduleEdges]);

  // Inject inline name / color edit callbacks so the node's collapsed param
  // panel can write back into the module canvas state.
  const moduleFlowNodes = useMemo<Node[]>(
    () =>
      moduleNodes.map((node) => ({
        ...node,
        data: {
          ...(node.data as Record<string, unknown>),
          onRename: (name: string) => patchModuleNodeData(node.id, { ui_name: name.trim() }),
          onColor: (color: string) => patchModuleNodeData(node.id, { ui_color: color }),
          onInput: (key: string, value: unknown) => patchModuleNodeData(node.id, { [key]: value }),
          onFieldFocus: (fieldKey: string) => {
            setSelectedId(node.id);
            setAssistantFieldKey(fieldKey);
          }
        }
      })),
    [moduleNodes, patchModuleNodeData]
  );

  const moduleRenderEdges = useMemo<Edge[]>(
    () =>
      moduleEdges.map((edge) => ({
        ...edge,
        type: CURVED_EDGE_DEFAULT_OPTIONS.type
      })),
    [moduleEdges]
  );

  const applyAlignment = useCallback(
    (action: AlignAction) => {
      pushModuleHistory();
      setModuleNodes((current) => alignFlowNodes(current, selectedOrAllNodeIds(current), action));
    },
    [pushModuleHistory, setModuleNodes]
  );

  const applyDistribution = useCallback(
    (action: DistributeAction) => {
      pushModuleHistory();
      setModuleNodes((current) => distributeFlowNodes(current, selectedOrAllNodeIds(current), action));
    },
    [pushModuleHistory, setModuleNodes]
  );

  const arrangeNodes = useCallback(() => {
    pushModuleHistory();
    setModuleNodes((current) => arrangeFlowNodes(current));
  }, [pushModuleHistory, setModuleNodes]);

  const deleteSelected = useCallback(() => {
    const selectedNodes = moduleNodes.filter((node) => node.selected).map((node) => node.id);
    const selectedEdges = moduleEdges.filter((edge) => edge.selected).map((edge) => edge.id);
    if (!selectedNodes.length && !selectedEdges.length) {
      return;
    }
    console.log("[P1-NODE-CRUD] deleteSelected:", {
      selectedNodeCount: selectedNodes.length,
      selectedEdgeCount: selectedEdges.length
    });
    pushModuleHistory();
    
    const removedNodes = new Set(selectedNodes);
    const removedEdges = new Set(selectedEdges);
    
    const nextNodes = moduleNodesRef.current.filter((node) => !removedNodes.has(node.id));
    const previousEdgeCount = moduleEdgesRef.current.length;
    const nextEdges = moduleEdgesRef.current.filter(
      (edge) => !removedEdges.has(edge.id) && !removedNodes.has(edge.source) && !removedNodes.has(edge.target)
    );
    moduleNodesRef.current = nextNodes;
    moduleEdgesRef.current = nextEdges;
    setModuleNodes(nextNodes);
    setModuleEdges(nextEdges);
    persistModuleGraphNow(nextNodes, nextEdges);
    console.log("[P1-NODE-CRUD] deleteSelected success:", {
      deletedNodeCount: selectedNodes.length,
      deletedEdgeCount: previousEdgeCount - nextEdges.length,
      totalNodesAfter: nextNodes.length,
      totalEdgesAfter: nextEdges.length,
    });
    
    setSelectedId((current) => (current && removedNodes.has(current) ? "" : current));
    setAssistantFieldKey("");
  }, [moduleEdges, moduleNodes, persistModuleGraphNow, pushModuleHistory, setModuleEdges, setModuleNodes]);

  const updateModuleNodeDataById = useCallback(
    (nodeId: string, updater: (schemaNode: WorkflowNode) => WorkflowNode) => {
      pushModuleHistory();
      setModuleNodes((current) =>
        current.map((node) => {
          if (node.id !== nodeId) {
            return node;
          }
          const schemaNode = (node.data as { schemaNode?: WorkflowNode }).schemaNode;
          if (!schemaNode) {
            return node;
          }
          return {
            ...node,
            data: {
              ...node.data,
              schemaNode: updater(schemaNode)
            }
          };
        })
      );
    },
    [pushModuleHistory, setModuleNodes]
  );

  const deleteModuleNodeById = useCallback(
    (nodeId: string) => {
      console.log("[P1-NODE-CRUD] deleteModuleNodeById:", { nodeId });
      pushModuleHistory();
      const nextNodes = moduleNodesRef.current.filter((node) => node.id !== nodeId);
      const previousEdgeCount = moduleEdgesRef.current.length;
      const nextEdges = moduleEdgesRef.current.filter((edge) => edge.source !== nodeId && edge.target !== nodeId);
      moduleNodesRef.current = nextNodes;
      moduleEdgesRef.current = nextEdges;
      setModuleNodes(nextNodes);
      setModuleEdges(nextEdges);
      persistModuleGraphNow(nextNodes, nextEdges);
      console.log("[P1-NODE-CRUD] deleteModuleNodeById success:", {
        deletedNodeId: nodeId,
        deletedEdgeCount: previousEdgeCount - nextEdges.length,
        totalNodesAfter: nextNodes.length,
        totalEdgesAfter: nextEdges.length,
      });
      setSelectedId((current) => (current === nodeId ? "" : current));
      setAssistantFieldKey("");
    },
    [persistModuleGraphNow, pushModuleHistory, setModuleEdges, setModuleNodes]
  );

  const resetModuleCanvasNodeById = useCallback(
    (nodeId: string) => {
      updateModuleNodeDataById(nodeId, (current) => {
        const schemaFields = ((current as unknown as { input_schema?: NodeInputField[] }).input_schema ?? getNodeDefinition(String(current.type))?.input_schema ?? []) as NodeInputField[];
        const resetData = { ...(current.data ?? {}) } as Record<string, unknown>;
        for (const field of schemaFields) {
          resetData[field.key] = field.default ?? "";
        }
        resetData.ui_name = "";
        resetData.ui_color = "";
        resetData.ui_tags = [];
        resetData.ui_group = "";
        return { ...current, data: resetData };
      });
    },
    [updateModuleNodeDataById]
  );

  const renameModuleCanvasNode = useCallback(
    (nodeId: string) => {
      const schemaNode = (moduleNodes.find((node) => node.id === nodeId)?.data as { schemaNode?: WorkflowNode } | undefined)?.schemaNode;
      if (!schemaNode) {
        return;
      }
      const nextName = window.prompt(t("common.renameNode", "Rename node"), translate(language, schemaNode.title_key, schemaNode.title_fallback));
      if (!nextName?.trim()) {
        return;
      }
      updateModuleNodeDataById(nodeId, (current) => ({ ...current, title_fallback: nextName.trim() }));
    },
    [language, moduleNodes, updateModuleNodeDataById]
  );

  const editModuleNodeTags = useCallback(
    (nodeId: string) => {
      const schemaNode = (moduleNodes.find((node) => node.id === nodeId)?.data as { schemaNode?: WorkflowNode } | undefined)?.schemaNode;
      const currentTags = schemaNode?.data?.ui_tags;
      const currentText = Array.isArray(currentTags) ? currentTags.join(", ") : "";
      const nextTags = window.prompt(t("common.nodeTags", "Node tags"), currentText);
      if (nextTags === null) {
        return;
      }
      updateModuleNodeDataById(nodeId, (current) => ({
        ...current,
        data: {
          ...(current.data ?? {}),
          ui_tags: nextTags
            .split(",")
            .map((tag) => tag.trim())
            .filter(Boolean)
        }
      }));
    },
    [moduleNodes, updateModuleNodeDataById]
  );

  const editModuleNodeGroup = useCallback(
    (nodeId: string) => {
      const schemaNode = (moduleNodes.find((node) => node.id === nodeId)?.data as { schemaNode?: WorkflowNode } | undefined)?.schemaNode;
      const currentGroup = typeof schemaNode?.data?.ui_group === "string" ? schemaNode.data.ui_group : "";
      const nextGroup = window.prompt(t("common.nodeGroup", "Node group"), currentGroup);
      if (nextGroup === null) {
        return;
      }
      updateModuleNodeDataById(nodeId, (current) => ({ ...current, data: { ...(current.data ?? {}), ui_group: nextGroup.trim() } }));
    },
    [moduleNodes, updateModuleNodeDataById]
  );

  const renameModuleNodeGroup = useCallback(
    (nodeId: string) => {
      const schemaNode = (moduleNodes.find((node) => node.id === nodeId)?.data as { schemaNode?: WorkflowNode } | undefined)?.schemaNode;
      const currentGroup = typeof schemaNode?.data?.ui_group === "string" ? schemaNode.data.ui_group : "";
      const nextGroup = window.prompt(t("common.renameGroup", "Rename group"), currentGroup);
      if (nextGroup === null) {
        return;
      }
      pushModuleHistory();
      setModuleNodes((current) =>
        current.map((node) => {
          const nodeSchema = (node.data as { schemaNode?: WorkflowNode }).schemaNode;
          if (!nodeSchema || nodeSchema.data?.ui_group !== currentGroup) {
            return node;
          }
          return {
            ...node,
            data: {
              ...node.data,
              schemaNode: { ...nodeSchema, data: { ...(nodeSchema.data ?? {}), ui_group: nextGroup.trim() } }
            }
          };
        })
      );
    },
    [moduleNodes, pushModuleHistory, setModuleNodes]
  );

  const dissolveModuleNodeGroup = useCallback(
    (nodeId: string) => {
      const schemaNode = (moduleNodes.find((node) => node.id === nodeId)?.data as { schemaNode?: WorkflowNode } | undefined)?.schemaNode;
      const currentGroup = typeof schemaNode?.data?.ui_group === "string" ? schemaNode.data.ui_group : "";
      if (!currentGroup) {
        return;
      }
      pushModuleHistory();
      setModuleNodes((current) =>
        current.map((node) => {
          const nodeSchema = (node.data as { schemaNode?: WorkflowNode }).schemaNode;
          if (!nodeSchema || nodeSchema.data?.ui_group !== currentGroup) {
            return node;
          }
          return {
            ...node,
            data: {
              ...node.data,
              schemaNode: { ...nodeSchema, data: { ...(nodeSchema.data ?? {}), ui_group: "" } }
            }
          };
        })
      );
    },
    [moduleNodes, pushModuleHistory, setModuleNodes]
  );

  const copyModuleNodeById = useCallback(
    (nodeId: string) => {
      const schemaNode = (moduleNodes.find((node) => node.id === nodeId)?.data as { schemaNode?: WorkflowNode } | undefined)?.schemaNode;
      if (schemaNode) {
        setCopiedModuleNode(schemaNode);
      }
    },
    [moduleNodes]
  );

  const pasteModuleNode = useCallback(() => {
    if (!copiedModuleNode) {
      return;
    }
    pushModuleHistory();
    const id = `${copiedModuleNode.node_id}_copy_${Date.now()}`;
    const schemaNode = ensurePorts({
      ...copiedModuleNode,
      node_id: id,
      title_fallback: `${copiedModuleNode.title_fallback} Copy`,
      position: {
        x: (copiedModuleNode.position?.x ?? 120) + 40,
        y: (copiedModuleNode.position?.y ?? 70) + 40
      }
    } as WorkflowNode);
    setModuleNodes((current) => [
      ...current,
      {
        id,
        type: "workflowNode",
        position: schemaNode.position ?? { x: 160, y: 110 },
        deletable: true,
        data: { schemaNode }
      }
    ]);
    setSelectedId(id);
    setAssistantFieldKey("");
  }, [copiedModuleNode, pushModuleHistory, setModuleNodes]);

  const deleteModuleEdgeById = useCallback(
    (edgeId: string) => {
      pushModuleHistory();
      setModuleEdges((current) => current.filter((edge) => edge.id !== edgeId));
    },
    [pushModuleHistory, setModuleEdges]
  );

  const handleModuleNodeContextMenu: NodeMouseHandler = useCallback(
    (event, node) => {
      setSelectedId(node.id);
      setAssistantFieldKey("");
      const schemaNode = (node.data as { schemaNode?: WorkflowNode } | undefined)?.schemaNode;
      const group = typeof schemaNode?.data?.ui_group === "string" ? schemaNode.data.ui_group : "";
      const menu = makeContextMenu(event, [
        { label: t("toolbar.undo", "撤销"), onSelect: undoModuleCanvas, disabled: !canUndoModule },
        { label: t("toolbar.redo", "重做"), onSelect: redoModuleCanvas, disabled: !canRedoModule },
        { label: t("menu.autoArrangeNodes", "自动整理节点"), onSelect: arrangeNodes },
        { label: t("common.rename", "Rename"), onSelect: () => renameModuleCanvasNode(node.id) },
        { label: t("common.reset", "Reset"), onSelect: () => resetModuleCanvasNodeById(node.id) },
        {
          label: t("menu.arrangeNodes", "整理排列节点"),
          children: [
            { label: t("menu.arrange", "整理节点"), onSelect: arrangeNodes },
            { label: t("align.left", "左对齐"), onSelect: () => applyAlignment("left") },
            { label: t("align.right", "右对齐"), onSelect: () => applyAlignment("right") },
            { label: t("align.top", "上对齐"), onSelect: () => applyAlignment("top") },
            { label: t("align.bottom", "下对齐"), onSelect: () => applyAlignment("bottom") },
            { label: t("align.centerX", "水平居中"), onSelect: () => applyAlignment("center-x") },
            { label: t("align.centerY", "垂直居中"), onSelect: () => applyAlignment("center-y") },
            { label: t("align.distributeX", "水平分布"), onSelect: () => applyDistribution("horizontal") },
            { label: t("align.distributeY", "垂直分布"), onSelect: () => applyDistribution("vertical") }
          ]
        },
        { label: t("common.deleteNode", "Delete node"), onSelect: () => deleteModuleNodeById(node.id), danger: true },
        { label: t("common.copyNode", "Copy node"), onSelect: () => copyModuleNodeById(node.id) },
        { label: t("common.addEditTags", "Add / edit tags"), onSelect: () => editModuleNodeTags(node.id) },
        { label: t("common.createGroup", "Create group"), onSelect: () => editModuleNodeGroup(node.id) },
        { label: t("common.renameGroup", "Rename group"), onSelect: () => renameModuleNodeGroup(node.id), disabled: !group },
        { label: t("common.dissolveGroup", "Dissolve group"), onSelect: () => dissolveModuleNodeGroup(node.id), disabled: !group }
      ]);
      if (menu) {
        setContextMenu(menu);
      }
    },
    [
      applyAlignment,
      applyDistribution,
      arrangeNodes,
      canRedoModule,
      canUndoModule,
      copyModuleNodeById,
      deleteModuleNodeById,
      dissolveModuleNodeGroup,
      editModuleNodeGroup,
      editModuleNodeTags,
      renameModuleCanvasNode,
      renameModuleNodeGroup,
      redoModuleCanvas,
      undoModuleCanvas,
      resetModuleCanvasNodeById
    ]
  );

  const handleModuleEdgeContextMenu = useCallback(
    (event: ContextMenuEvent, edge: Edge) => {
      const menu = makeContextMenu(event, [{ label: t("common.deleteEdge", "Delete edge"), onSelect: () => deleteModuleEdgeById(edge.id), danger: true }]);
      if (menu) {
        setContextMenu(menu);
      }
    },
    [deleteModuleEdgeById]
  );

  const renameModule = useCallback(() => {
    const nextName = window.prompt(t("common.renameModule", "Rename module"), title);
    if (nextName?.trim()) {
      onRenameModule(moduleNode.node_id, nextName.trim());
    }
  }, [moduleNode.node_id, onRenameModule, title]);

  const updateSelectedNodeData = useCallback(
    (updater: (data: Record<string, unknown>) => Record<string, unknown>) => {
      if (!selectedId) {
        return;
      }
      pushModuleHistory();
      setModuleNodes((current) =>
        current.map((node) => {
          if (node.id !== selectedId) {
            return node;
          }
          const schemaNode = (node.data as { schemaNode?: WorkflowNode }).schemaNode;
          if (!schemaNode) {
            return node;
          }
          return {
            ...node,
            data: {
              ...node.data,
              schemaNode: {
                ...schemaNode,
                data: updater({ ...(schemaNode.data ?? {}) })
              }
            }
          };
        })
      );
    },
    [pushModuleHistory, selectedId, setModuleNodes]
  );

  const editSelectedTags = useCallback(() => {
    const currentTags = selectedSchema?.data?.ui_tags;
    const currentText = Array.isArray(currentTags) ? currentTags.join(", ") : "";
    const nextTags = window.prompt(t("common.nodeTags", "Node tags"), currentText);
    if (nextTags === null) {
      return;
    }
    updateSelectedNodeData((data) => ({
      ...data,
      ui_tags: nextTags
        .split(",")
        .map((tag) => tag.trim())
        .filter(Boolean)
    }));
  }, [selectedSchema, updateSelectedNodeData]);

  const editSelectedGroup = useCallback(() => {
    const currentGroup = typeof selectedSchema?.data?.ui_group === "string" ? selectedSchema.data.ui_group : "";
    const nextGroup = window.prompt(t("common.nodeGroup", "Node group"), currentGroup);
    if (nextGroup === null) {
      return;
    }
    updateSelectedNodeData((data) => ({ ...data, ui_group: nextGroup.trim() }));
  }, [selectedSchema, updateSelectedNodeData]);

  // Module canvas: all toolbar actions live in the blank-canvas right-click menu.
  const handleModulePaneContextMenu = useCallback(
    (event: ContextMenuEvent) => {
      const hasSelection = moduleNodes.some((node) => node.selected);
      const items: CanvasContextMenuItem[] = [
        { label: t("toolbar.undo", "撤销"), onSelect: undoModuleCanvas, disabled: !canUndoModule },
        { label: t("toolbar.redo", "重做"), onSelect: redoModuleCanvas, disabled: !canRedoModule },
        { label: t("menu.autoArrangeNodes", "自动整理节点"), onSelect: arrangeNodes },
        {
          label: t("menu.addNode", "添加节点"),
          children: libraryNodeTypes.map((type) => ({
            label: getNodeTypeLabel(type, t),
            onSelect: () => addModuleNode(type)
          }))
        },
        {
          label: t("menu.alignDistribute", "对齐 / 分布"),
          disabled: !hasSelection,
          children: [
            { label: t("align.left", "左对齐"), onSelect: () => applyAlignment("left") },
            { label: t("align.right", "右对齐"), onSelect: () => applyAlignment("right") },
            { label: t("align.top", "上对齐"), onSelect: () => applyAlignment("top") },
            { label: t("align.bottom", "下对齐"), onSelect: () => applyAlignment("bottom") },
            { label: t("align.distributeX", "水平分布"), onSelect: () => applyDistribution("horizontal") },
            { label: t("align.distributeY", "垂直分布"), onSelect: () => applyDistribution("vertical") }
          ]
        },
        { label: t("menu.paste", "粘贴节点"), onSelect: pasteModuleNode, disabled: !copiedModuleNode },
        {
          label: t("menu.viewActions", "视图"),
          children: [
            { label: t("menu.fitView", "适配视图"), onSelect: () => moduleFlowRef.current?.fitView() },
            { label: t("menu.arrange", "整理节点"), onSelect: arrangeNodes }
          ]
        },
        { label: t("menu.tags", "标签"), onSelect: editSelectedTags, disabled: !selectedSchema },
        { label: t("menu.group", "打组"), onSelect: editSelectedGroup, disabled: !selectedSchema },
        { label: t("toolbar.delete", "删除"), onSelect: deleteSelected, disabled: !hasSelection, danger: true },
        { label: t("module.rename", "重命名模块"), onSelect: renameModule }
      ];
      const menu = makeContextMenu(event, items);
      if (menu) {
        setContextMenu(menu);
      }
    },
    [
      addModuleNode,
      applyAlignment,
      applyDistribution,
      arrangeNodes,
      canRedoModule,
      canUndoModule,
      copiedModuleNode,
      deleteSelected,
      editSelectedGroup,
      editSelectedTags,
      libraryNodeTypes,
      moduleNodes,
      pasteModuleNode,
      renameModule,
      redoModuleCanvas,
      selectedSchema,
      t,
      undoModuleCanvas
    ]
  );

  const handleModuleFlowContextMenuCapture = useCallback(
    (event: ReactMouseEvent<HTMLDivElement>) => {
      if (shouldSkipCanvasContextCapture(event.target) || shouldLetReactFlowElementContextMenuHandle(event.target)) {
        return;
      }
      handleModulePaneContextMenu(event);
    },
    [handleModulePaneContextMenu]
  );

  // Resolve the run input: prefer the module canvas's text_input node, then the
  // top-right run input (fallback), then a default. The UI never executes the LLM
  // itself — it only forwards the text to the backend Execution Engine.
  const resolveModuleInputText = useCallback((): string => {
    for (const node of moduleNodes) {
      const schemaNode = (node.data as { schemaNode?: WorkflowNode } | undefined)?.schemaNode;
      if (schemaNode && String(schemaNode.type) === "text_input") {
        const nodeData = (schemaNode.data ?? {}) as Record<string, unknown>;
        const candidate = [nodeData.source_text, nodeData.text, nodeData.prompt].find(
          (value) => typeof value === "string" && value.trim()
        );
        if (typeof candidate === "string" && candidate.trim()) {
          return candidate.trim();
        }
      }
    }
    if (runInputText.trim()) {
      return runInputText.trim();
    }
    return "manual run";
  }, [moduleNodes, runInputText]);

  // Stage 6: the UI only dispatches to the backend Execution Engine (the sole
  // runtime entry). It never calls a provider / memory / tool directly.
  const handleRunWorkflow = useCallback(async () => {
    if (!workflow) {
      setExecutionResult(null);
      setExecutionError(t("error.noWorkflow", "No workflow loaded"));
      setRunStatus("error");
      return;
    }
    const inputText = resolveModuleInputText();
    setRunStatus("running");
    setExecutionError(null);
    setExecutionResult(null);
    try {
      const response = await api.executeResidentStep(workflow, inputText, moduleNode.node_id);
      setExecutionResult(response);
      setRunStatus("success");
      onExecutionResult(response);
      // Write the runtime output_text back into the module canvas output node(s).
      // setModuleNodes triggers the debounced module-graph persistence, so the
      // result survives refresh.
      const outputText = typeof response.output_text === "string" ? response.output_text : "";
      const lastRunId = typeof response.run_id === "string" ? response.run_id : "";
      const lastStatus = typeof response.status === "string" ? response.status : "";
      pushModuleHistory();
      setModuleNodes((current) =>
        current.map((node) => {
          const schemaNode = (node.data as { schemaNode?: WorkflowNode } | undefined)?.schemaNode;
          if (!schemaNode || String(schemaNode.type) !== "output") {
            return node;
          }
          return {
            ...node,
            data: {
              ...(node.data as Record<string, unknown>),
              schemaNode: {
                ...schemaNode,
                data: {
                  ...((schemaNode.data ?? {}) as Record<string, unknown>),
                  output_text: outputText,
                  last_run_id: lastRunId,
                  last_status: lastStatus
                }
              }
            }
          };
        })
      );
    } catch (error) {
      setExecutionError((error as Error).message);
      setRunStatus("error");
    }
  }, [workflow, resolveModuleInputText, moduleNode.node_id, onExecutionResult, pushModuleHistory, setModuleNodes, t]);
  const runButtonLabel =
    runStatus === "running"
      ? t("run.running", "Running...")
      : runStatus === "success"
        ? t("run.success", "Run Complete")
        : runStatus === "error"
          ? t("run.error", "Run Failed")
          : t("workspace.runWorkflow", "Run Workflow");

  return (
    <section className="module-canvas-panel">
      <header className="module-canvas-panel__bar">
        <div>
          <p>{t("workspace.moduleCanvas", "Module Canvas")}</p>
          <h3>{title}</h3>
          <span>{moduleNode.node_id}</span>
        </div>
        <div className="module-canvas-panel__actions">
          <input
            className="module-run-input"
            value={runInputText}
            onChange={(event) => setRunInputText(event.target.value)}
            placeholder={t("run.inputPlaceholder", "运行输入（文本或 JSON）")}
            onKeyDown={(event) => {
              if (event.key === "Enter") {
                event.preventDefault();
                handleRunWorkflow();
              }
            }}
          />
          <button className={`run-workflow-button is-${runStatus}`} onClick={handleRunWorkflow} disabled={runStatus === "running"}>
            <span className="run-workflow-button__dot" />
            {runButtonLabel}
          </button>
          <button onClick={() => addModuleNode("transform")}>+ {t("workspace.addNode", "Add node")}</button>
          <button className="module-canvas-panel__close" onClick={onClose}>
            ✕
          </button>
        </div>
      </header>
      <div className="module-canvas-panel__body">
        <div
          className="module-canvas-panel__flow"
          onDragOver={(event) => {
            event.preventDefault();
            event.dataTransfer.dropEffect = "copy";
          }}
          onDrop={handleModuleCanvasDrop}
          onContextMenuCapture={handleModuleFlowContextMenuCapture}
        >
          {!moduleNodes.length ? (
            <div className="module-canvas-panel__empty-state">
              <strong>{t("empty.moduleTitle", "Module canvas is empty")}</strong>
              <span>{t("empty.moduleBody", "Start by adding nodes from the left library, then connect Input / Transform / Personality / Output.")}</span>
            </div>
          ) : null}
          <WorkflowNodeCardModuleNodesProvider nodes={moduleFlowNodes}>
            <ReactFlow
              nodes={moduleFlowNodes}
              edges={moduleRenderEdges}
              nodeTypes={nodeTypes}
              defaultEdgeOptions={CURVED_EDGE_DEFAULT_OPTIONS}
              fitView
              onInit={(instance) => {
                moduleFlowRef.current = instance;
              }}
              minZoom={0.3}
              maxZoom={1.6}
              onNodesChange={onModuleNodesChange}
              onEdgesChange={onModuleEdgesChange}
              onConnect={onConnect}
              onNodesDelete={handleModuleNodesDelete}
              onNodeDragStart={pushModuleHistory}
              onNodeClick={(_event, node) => {
                setContextMenu(null);
                setSelectedId(node.id);
                setAssistantFieldKey("");
              }}
              onNodeContextMenu={handleModuleNodeContextMenu}
              onEdgeContextMenu={handleModuleEdgeContextMenu}
              onPaneContextMenu={handleModulePaneContextMenu}
              onPaneClick={() => {
                setContextMenu(null);
                setAssistantFieldKey("");
              }}
              selectionOnDrag
              selectionKeyCode="Alt"
              selectNodesOnDrag={false}
              deleteKeyCode={["Backspace", "Delete"]}
            >
              <Background color="#333" gap={20} />
              <Controls />
              <CanvasDebugTracePanel
                open={showModuleDebugTracePanel}
                t={t}
                logs={executionError ? [{ level: "error", message: executionError }] : []}
                trace={executionResult}
                validation={selectedSchema?.validation ?? null}
                jsonPreview={{
                  selected_node: selectedSchema,
                  node_count: moduleNodes.length,
                  edge_count: moduleEdges.length,
                  run_status: runStatus
                }}
                onToggle={() => setShowModuleDebugTracePanel((value) => !value)}
              />
              {showModuleMiniMap ? (
                <>
                  <MiniMap pannable zoomable className="canvas-debug-panel__minimap" />
                  <button
                    type="button"
                    className="canvas-debug-panel__collapse nodrag nopan"
                    aria-label={t("debugPanel.collapse")}
                    title={t("debugPanel.collapse")}
                    onClick={() => setShowModuleMiniMap(false)}
                  >
                    {t("debugPanel.collapseGlyph")}
                  </button>
                </>
              ) : (
                <button
                  type="button"
                  className="canvas-debug-panel__expand nodrag nopan"
                  aria-label={t("debugPanel.expand")}
                  title={t("debugPanel.expand")}
                  onClick={() => setShowModuleMiniMap(true)}
                >
                  {t("debugPanel.expandLabel")}
                </button>
              )}
            </ReactFlow>
          </WorkflowNodeCardModuleNodesProvider>
          {contextMenu ? <CanvasContextMenu menu={contextMenu} onClose={() => setContextMenu(null)} /> : null}
        </div>
      </div>
    </section>
  );
}

function LogsPanel({
  logs,
  validation,
  emptyText,
  t
}: {
  logs: { ts?: string; level: string; message: string }[];
  validation: unknown;
  emptyText: string;
  t: (key: string, fallback?: string) => string;
}) {
  if (!logs.length && !validation) {
    return <div className="bottom-empty">{emptyText}</div>;
  }

  return (
    <div className="log-list">
      {logs.map((log, index) => (
        <div key={`${log.ts}-${index}`} className={`log-line log-${log.level}`}>
          <span>{log.ts ? new Date(log.ts).toLocaleTimeString() : "--:--:--"}</span>
          <strong>{log.level}</strong>
          <p>{log.message}</p>
        </div>
      ))}
      {validation ? <ValidationSummary validation={validation} t={t} /> : null}
    </div>
  );
}

function JsonPanel({ value, emptyText }: { value: unknown; emptyText: string }) {
  if (!value) {
    return <div className="bottom-empty">{emptyText}</div>;
  }

  return <pre className="json-panel">{JSON.stringify(value, null, 2)}</pre>;
}

function CanvasDebugTracePanel({
  open,
  embedded = false,
  t,
  logs,
  trace,
  validation,
  jsonPreview,
  memoryView,
  memoryClearResult,
  onToggle
}: {
  open: boolean;
  embedded?: boolean;
  t: (key: string, fallback?: string) => string;
  logs: { ts?: string; level: string; message: string }[];
  trace: unknown;
  validation: unknown;
  jsonPreview: unknown;
  memoryView?: unknown;
  memoryClearResult?: unknown;
  onToggle: () => void;
}) {
  if (!open) {
    return (
      <button
        type="button"
        className="canvas-debug-trace-panel__open nodrag nopan"
        aria-label={t("debugTrace.expand")}
        title={t("debugTrace.expand")}
        onClick={onToggle}
      >
        {t("debugTrace.openLabel")}
      </button>
    );
  }

  return (
    <aside className="canvas-debug-trace-panel nodrag nopan">
      {embedded ? null : (
        <header className="canvas-debug-trace-panel__header">
          <strong>{t("panel.debugTrace")}</strong>
          <button type="button" aria-label={t("debugTrace.collapse")} title={t("debugTrace.collapse")} onClick={onToggle}>
            {t("debugPanel.collapseGlyph")}
          </button>
        </header>
      )}
      <details>
        <summary>{t("panel.logs")}</summary>
        {logs.length ? (
          <div className="canvas-debug-trace-panel__logs">
            {logs.slice(0, 6).map((log, index) => (
              <p key={`${log.ts ?? "log"}-${index}`} className={`log-${log.level}`}>
                {log.message}
              </p>
            ))}
          </div>
        ) : (
          <p className="canvas-debug-trace-panel__empty">{t("panel.noLogs")}</p>
        )}
      </details>
      <details>
        <summary>{t("inspector.executionTrace")}</summary>
        <pre>{trace ? safeStringify(trace) : t("inspector.noTrace")}</pre>
      </details>
      <details>
        <summary>{t("inspector.validationResult")}</summary>
        <ValidationSummary validation={validation} t={t} />
      </details>
      <details>
        <summary>{t("inspector.jsonPreview")}</summary>
        <pre>{jsonPreview ? safeStringify(jsonPreview) : t("panel.noPreview")}</pre>
      </details>
      <details>
        <summary>{t("memory.debug.view", "Memory View")}</summary>
        <pre>{memoryView ? safeStringify(memoryView) : t("memory.debug.emptyView", "No memory view result")}</pre>
      </details>
      <details>
        <summary>{t("memory.debug.clear", "Memory Clear")}</summary>
        <pre>{memoryClearResult ? safeStringify(memoryClearResult) : t("memory.debug.emptyClear", "No memory clear result")}</pre>
      </details>
    </aside>
  );
}

function ResidentPreviewPanel({
  resident,
  t,
  canLoadCompiledDR,
  onLoadCompiledDR,
  loadedDRResult,
  previewLoadStatus,
  previewLoadError
}: {
  resident: ResidentInstance | null;
  t: (key: string, fallback?: string) => string;
  canLoadCompiledDR: boolean;
  onLoadCompiledDR: () => Promise<void>;
  loadedDRResult: DRLoadResult | null;
  previewLoadStatus: "idle" | "loading" | "success" | "error";
  previewLoadError: string | null;
}) {
  const [activeTab, setActiveTab] = useState<ResidentPreviewTab>("dialogue");
  const [chatInput, setChatInput] = useState("");
  const [chatMessages, setChatMessages] = useState<{ role: "user" | "resident"; text: string }[]>([]);
  const [voicePlaying, setVoicePlaying] = useState(false);
  const isPreviewLoading = previewLoadStatus === "loading";
  const memoryCount =
    loadedDRResult?.memory_snapshot?.count ??
    loadedDRResult?.memory_snapshot?.entries?.length ??
    0;
  const validationErrors = loadedDRResult?.validation_result?.errors ?? [];
  const runtimeState = (loadedDRResult?.runtime_state ?? {}) as Record<string, unknown>;
  const runtimeIdentity = (runtimeState.identity ?? {}) as Record<string, unknown>;
  const runtimeOutput = loadedDRResult?.output_text || "";
  const latticeData = (loadedDRResult?.lattice_state ?? null) as Record<string, unknown> | null;
  const primaryLanguage = (runtimeIdentity.primary_language as string | undefined) || t("preview.mockPrimaryLanguage", "mock");
  const supportedLanguages = Array.isArray(runtimeIdentity.supported_languages)
    ? runtimeIdentity.supported_languages.join(", ")
    : t("preview.mockSupportedLanguages", "zh, en");
  const voiceState = latticeData?.voice_state ? String(latticeData.voice_state) : loadedDRResult?.loaded ? t("preview.voiceStateMock", "mock voice ready") : t("preview.voiceStateIdle", "not loaded");
  const ttsState = loadedDRResult?.loaded ? t("preview.ttsMock", "TTS mock") : t("preview.ttsIdle", "TTS idle");
  const latticeState = latticeData ? t("preview.latticeStateLoaded", "lattice state loaded") : loadedDRResult?.loaded ? t("preview.latticeStateMock", "mock lattice active") : t("preview.latticeStateIdle", "not loaded");
  const avatarState = loadedDRResult?.loaded ? t("preview.avatarStateMock", "mock avatar ready") : t("preview.avatarStateIdle", "avatar idle");
  const emotion = latticeData?.emotion ? String(latticeData.emotion) : loadedDRResult?.loaded ? t("preview.emotionCalm", "calm") : "-";
  const energy = typeof latticeData?.energy === "number" ? String(latticeData.energy) : loadedDRResult?.loaded ? "0.72" : "-";
  const particleDensity = typeof latticeData?.particle_density === "number" ? String(latticeData.particle_density) : loadedDRResult?.loaded ? "0.60" : "-";
  const loadPreviewButton = (
    <button
      type="button"
      className="resident-preview-load-button"
      onClick={() => {
        void onLoadCompiledDR();
      }}
      disabled={!canLoadCompiledDR || isPreviewLoading}
      title={canLoadCompiledDR ? undefined : t("preview.loadCompiledBlocked")}
    >
      {isPreviewLoading ? t("preview.loading") : t("preview.loadCompiled")}
    </button>
  );
  const loadStatusPanel = (
      <div className={`resident-preview-load-status is-${previewLoadStatus}`}>
        <strong>
          {previewLoadStatus === "loading"
            ? t("preview.loading")
            : previewLoadStatus === "success" && loadedDRResult?.loaded
              ? t("preview.loaded")
              : previewLoadStatus === "error"
                ? t("preview.loadFailed")
                : t("preview.notLoaded")}
        </strong>
        {previewLoadStatus === "loading" ? <p>{t("preview.loadingHint", "Loading compiled file into preview…")}</p> : null}
        {previewLoadStatus === "success" && loadedDRResult?.loaded ? (
        <dl>
          <dt>{t("preview.residentId")}</dt>
          <dd>{loadedDRResult.resident_id}</dd>
          <dt>{t("preview.drVersion")}</dt>
          <dd>{loadedDRResult.dr_version ?? loadedDRResult.validation_result?.dr_version ?? "-"}</dd>
          <dt>{t("preview.status")}</dt>
          <dd>{loadedDRResult.status}</dd>
          <dt>{t("preview.memoryCount")}</dt>
          <dd>{memoryCount}</dd>
          <dt>{t("preview.outputText")}</dt>
          <dd>{loadedDRResult.output_text || "-"}</dd>
          <dt>{t("preview.latticeState")}</dt>
          <dd>{latticeState || "-"}</dd>
          <dt>{t("preview.focusTarget")}</dt>
          <dd>{latticeData?.focus_target ? String(latticeData.focus_target) : "-"}</dd>
        </dl>
        ) : null}
        {previewLoadStatus === "error" ? (
          validationErrors.length ? (
          <ul>
            {validationErrors.map((error, index) => (
              <li key={`${error.code}-${index}`}>
                {error.code}: {validationFindingMessage(useCanvasStore.getState().language, error)}
              </li>
            ))}
          </ul>
          ) : (
            <p>{previewLoadError || t("preview.loadFailedFallback")}</p>
          )
        ) : null}
        {previewLoadStatus === "idle" ? <p>{t("preview.notLoadedHint", "Compile or load a file to fill the preview.")}</p> : null}
      </div>
    );

  const dialogue: NonNullable<ResidentInstance["dialogue"]> = resident?.dialogue ?? { tone: "", formality: "", sample: "" };
  const voice: NonNullable<ResidentInstance["voice_profile"]> = resident?.voice_profile ?? { voice_id: "", pitch: "", speed: 1, timbre: "", mock: true };
  const avatar: NonNullable<ResidentInstance["avatar"]> = resident?.avatar ?? { preset: "", color: "#4f8cff", density: 0.6, motion: "", mock: true };
  const tone = dialogue.tone || t("preview.defaultTone", "calm");
  const sample = runtimeOutput || dialogue.sample || t("preview.noDialogueSample", "No dialogue sample is available yet.");
  const avatarColor = avatar.color || "#4f8cff";
  const density = Math.max(0.1, Math.min(1, clampPreviewNumber(avatar.density, 0.6)));
  const speed = clampPreviewNumber(voice.speed, 1);

  const handleSend = () => {
    const trimmed = chatInput.trim();
    if (!trimmed) {
      return;
    }
    setChatMessages((messages) => [
      ...messages,
      { role: "user", text: trimmed },
      { role: "resident", text: t("preview.mockReply", "I hear you. I will respond in a {tone} way.").replace("{tone}", tone) }
    ]);
    setChatInput("");
  };

  return (
    <div className="resident-preview">
      <div className="resident-preview-actions">{loadPreviewButton}</div>
      {loadStatusPanel}
      <div className="resident-preview-tabs">
        {(["dialogue", "voice", "avatar"] as ResidentPreviewTab[]).map((tab) => (
          <button key={tab} className={activeTab === tab ? "is-active" : ""} onClick={() => setActiveTab(tab)}>
            {t(`preview.tab.${tab}`, tab)}
          </button>
        ))}
      </div>

      {activeTab === "dialogue" ? (
        <section className="resident-preview-section">
          <div className="preview-meta-grid">
            <span>{t("preview.tone", "Tone")}</span>
            <strong>{tone}</strong>
            <span>{t("preview.formality", "Formality")}</span>
            <strong>{dialogue.formality || "-"}</strong>
            <span>{t("preview.runtimeOutput", "Runtime output")}</span>
            <strong>{runtimeOutput || "-"}</strong>
          </div>
          <div className="mock-chat">
            <div className="mock-chat-bubble mock-chat-bubble--resident">{sample}</div>
            {chatMessages.map((message, index) => (
              <div key={`${message.role}-${index}`} className={`mock-chat-bubble mock-chat-bubble--${message.role}`}>
                {message.text}
              </div>
            ))}
          </div>
          <div className="mock-chat-input">
            <input
              value={chatInput}
              onChange={(event) => setChatInput(event.target.value)}
              placeholder={t("preview.chatPlaceholder", "Say something to the resident")}
              onKeyDown={(event) => {
                if (event.key === "Enter") {
                  event.preventDefault();
                  handleSend();
                }
              }}
            />
            <button onClick={handleSend}>{t("preview.send", "Send")}</button>
          </div>
        </section>
      ) : null}

      {activeTab === "voice" ? (
        <section className="resident-preview-section">
          <button className={`mock-voice-button ${voicePlaying ? "is-playing" : ""}`} onClick={() => setVoicePlaying((playing) => !playing)}>
            <span className="mock-voice-bars" aria-hidden="true">
              <i />
              <i />
              <i />
            </span>
            {voicePlaying ? t("preview.playingVoice", "Playing mock voice") : t("preview.playMockVoice", "Play Mock Voice")}
          </button>
          <div className="preview-meta-grid">
            <span>{t("preview.voiceId", "Voice ID")}</span>
            <strong>{voice.voice_id || "-"}</strong>
            <span>{t("preview.pitch", "Pitch")}</span>
            <strong>{voice.pitch || "-"}</strong>
            <span>{t("preview.speed", "Speed")}</span>
            <strong>{speed}</strong>
            <span>{t("preview.timbre", "Timbre")}</span>
            <strong>{voice.timbre || "-"}</strong>
            <span>{t("preview.primaryLanguage", "Primary language")}</span>
            <strong>{primaryLanguage}</strong>
            <span>{t("preview.supportedLanguages", "Supported languages")}</span>
            <strong>{supportedLanguages}</strong>
            <span>{t("preview.voiceState", "Voice state")}</span>
            <strong>{voiceState}</strong>
            <span>{t("preview.motion", "Motion")}</span>
            <strong>{latticeData?.motion ? String(latticeData.motion) : "-"}</strong>
            <span>{t("preview.ttsState", "TTS")}</span>
            <strong>{ttsState}</strong>
          </div>
        </section>
      ) : null}

      {activeTab === "avatar" ? (
        <section className="resident-preview-section">
          <div className="avatar-preview-stage" style={{ "--avatar-color": avatarColor, "--avatar-density": density } as CSSProperties}>
            <span />
            <span />
            <span />
            <div />
          </div>
          <div className="preview-meta-grid">
            <span>{t("preview.preset", "Preset")}</span>
            <strong>{avatar.preset || "-"}</strong>
            <span>{t("preview.color", "Color")}</span>
            <strong>{avatarColor}</strong>
            <span>{t("preview.motion", "Motion")}</span>
            <strong>{avatar.motion || "-"}</strong>
            <span>{t("preview.density", "Density")}</span>
            <strong>{density}</strong>
            <span>{t("preview.latticeState", "Lattice state")}</span>
            <strong>{latticeState}</strong>
            <span>{t("preview.focusTarget")}</span>
            <strong>{latticeData?.focus_target ? String(latticeData.focus_target) : "-"}</strong>
            <span>{t("preview.avatarState", "Avatar state")}</span>
            <strong>{avatarState}</strong>
            <span>{t("preview.emotion", "Emotion")}</span>
            <strong>{emotion}</strong>
            <span>{t("preview.energy", "Energy")}</span>
            <strong>{energy}</strong>
            <span>{t("preview.particleDensity", "Particle density")}</span>
            <strong>{particleDensity}</strong>
          </div>
        </section>
      ) : null}
    </div>
  );
}
