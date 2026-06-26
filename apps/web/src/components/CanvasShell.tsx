import { useCallback, useEffect, useMemo, useRef, useState, type CSSProperties, type DragEvent as ReactDragEvent, type MouseEvent as ReactMouseEvent, type ReactNode } from "react";
import { createPortal } from "react-dom";
import {
  addEdge,
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
  type Node,
  type NodeChange,
  type NodeMouseHandler,
  type ReactFlowInstance
} from "@xyflow/react";
import { translate, type Language } from "@/i18n";
import { aiSlotClass, aiSlotLabel, inferAiSlot } from "@/lib/ai-slot";
import { api } from "@/lib/api";
import type { ModuleCatalogEntryV04, ModuleCatalogResponseV04, NodeType, ResidentInstanceV03, Workflow, WorkflowNode } from "@/lib/schema-types";
import { safeSerialize } from "@/lib/safe-serialize";
import { downloadWorkflow } from "@/lib/workflow";
import { ModuleLibrary, readModuleDragId } from "@/components/ModuleLibrary";
import { getNodeDefinition, getNodeRegistryEntries, getNodeStatus, setBackendNodeRegistry, type NodeDefinition, type NodeInputField } from "@/registry/nodeRegistry";
import { useCanvasStore } from "@/store/canvas-store";
import { LayerContainerNode } from "@/components/canvas/LayerContainerNode";
import { WorkflowNodeCard } from "@/components/canvas/WorkflowNodeCard";

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
const FOLDER_GROUP_WIDTH = 1180;
const FOLDER_GROUP_HEIGHT = 216;
const FOLDER_TO_TRUNK_GAP = 120;
const TRUNK_LAYER_X = FOLDER_GROUP_X + FOLDER_GROUP_WIDTH + FOLDER_TO_TRUNK_GAP;
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

function modulesForLayer(layer: CatalogLayerInput, moduleCatalog: ModuleCatalogResponseV04) {
  return moduleCatalog.modules.filter((module) => module.layer_id === layer.layer_id);
}

function getLayerCatalogDisplayFields(layer: CatalogLayerInput, moduleCatalog: ModuleCatalogResponseV04) {
  const modules = modulesForLayer(layer, moduleCatalog);
  const categories = uniqueDisplayValues(modules.map((module) => displayText(module.category)));
  const statuses = modules.map((module) => displayText(module.status));
  const versions = modules.map((module) => displayText(module.module_version));
  const hasHumanConfirm = modules.some((module) => Boolean(module.human_confirm_required));
  const hasAuditRequired = modules.some((module) => Boolean(module.audit_required));
  const hasRuntimeEnabled = modules.some((module) => Boolean(module.runtime_enabled));
  const hasSlotBinding = modules.some((module) => Boolean(module.slot_type));
  const hasLaterModule = modules.some((module) => ["LATER", "PLANNED"].includes(displayText(module.status)));

  return {
    groupLabel: categories.length ? categories.join(" / ").toUpperCase() : displayText(layer.layer_id).toUpperCase(),
    status: mixedOrSingle(statuses, "empty"),
    version: mixedOrSingle(versions, displayText(moduleCatalog.protocol_version)),
    children_count: modules.length,
    review: hasHumanConfirm ? "Human Confirm Required" : hasAuditRequired ? "Audit Required" : "No Review Required",
    module_tier: hasLaterModule ? "later" : hasSlotBinding ? "plugin" : "core",
    lock_level: hasHumanConfirm || hasAuditRequired ? "review_required" : hasRuntimeEnabled ? "locked" : "editable"
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
  const catalogLayerName = layer.layer_name;
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
const collapsedNodeLabels: Partial<Record<ModuleNodeType, { zh: string; en: string }>> = {
  text_input: { zh: "文", en: "Tx" },
  identity: { zh: "身", en: "Id" },
  personality: { zh: "格", en: "Pe" },
  dialogue: { zh: "话", en: "Dl" },
  voice_profile: { zh: "声", en: "Vo" },
  particle_avatar: { zh: "粒", en: "Av" },
  model_adapter: { zh: "模", en: "Md" },
  memory: { zh: "记", en: "Me" },
  knowledge: { zh: "识", en: "Kn" },
  tools: { zh: "具", en: "To" },
  output: { zh: "出", en: "Ou" },
  compile_resident: { zh: "编", en: "Cp" },
  api_connector: { zh: "接", en: "Api" },
  model_loader: { zh: "载", en: "Ld" },
  local_model: { zh: "本", en: "Lm" },
  llm_adapter: { zh: "语", en: "Llm" },
  tts_adapter: { zh: "音", en: "Tts" },
  ar_particle: { zh: "增", en: "Ar" },
  particle_physics: { zh: "物", en: "Px" },
  avatar_preview: { zh: "览", en: "Av" },
  runtime_mock: { zh: "运", en: "Rt" },
  export_package: { zh: "包", en: "Pk" },
  input: { zh: "入", en: "In" },
  transform: { zh: "转", en: "Tr" }
};

function getCollapsedLabel(type: ModuleNodeType, language: Language): string {
  return collapsedNodeLabels[type]?.[language] ?? String(type).slice(0, 2);
}

type BottomTab = "logs" | "artifacts" | "preview";
type DrawerId = "layers" | "inspector" | "residentPreview" | BottomTab;
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

function moduleCatalogName(module: ModuleCatalogEntryV04) {
  return module.module_name;
}

function moduleCatalogSlot(module: ModuleCatalogEntryV04) {
  return module.slot_type || "unplanned";
}

type PendingModuleAdd = {
  requestId: number;
  moduleId: string;
  nodeType: ModuleNodeType;
};

const nodeTypes = {
  layerContainer: LayerContainerNode,
  workflowNode: WorkflowNodeCard,
  folderGroup: FolderGroupNode
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value && typeof value === "object" && !Array.isArray(value));
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

function computeLayerModuleCounts(layers: CatalogLayerInput[], layerModules: Record<string, string[]>) {
  return new Map(
    layers.map((layer) => {
      const layerId = layer.layer_id;
      return [layerId, (layerModules[layerId] ?? []).length] as const;
    })
  );
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
  uiColors
}: {
  layer: CatalogLayerInput;
  moduleCatalog: ModuleCatalogResponseV04;
  frame: LayerStackFrame;
  uiTags: Record<string, string[]>;
  uiGroups: Record<string, string>;
  uiColors: Record<string, string>;
}) {
  const layerId = layer.layer_id;
  const catalogLayerName = layer.layer_name;
  const displayFields = getLayerCatalogDisplayFields(layer, moduleCatalog);
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
    style: { width: 380, height: TRUNK_LAYER_HEIGHT },
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
      uiColor: uiColors[layerId] ?? ""
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
    type: "smoothstep",
    selectable: false,
    deletable: false,
    focusable: false,
    animated: false,
    style: { stroke: "rgba(110, 231, 183, 0.95)", strokeWidth: 2 }
  } satisfies Edge;
}

function buildLayerSpineEdge(layer: CatalogLayerInput, nextLayer: CatalogLayerInput) {
  return {
    id: `edge-layer-spine-${layer.layer_id}-${nextLayer.layer_id}`,
    source: layer.layer_id,
    target: nextLayer.layer_id,
    sourceHandle: "p_out",
    targetHandle: "p_in",
    type: "smoothstep",
    selectable: false,
    deletable: false,
    focusable: false,
    animated: false,
    style: { stroke: "rgba(148, 163, 184, 0.72)", strokeWidth: 1.8 }
  } satisfies Edge;
}

function checkCanvasStructureConsistency(layers: CatalogLayerInput[], nodes: WorkflowNode[], frames: Map<string, LayerStackFrame>, moduleCatalog: ModuleCatalogResponseV04) {
  const warnings: string[] = [];
  if (layers.length !== 13) {
    warnings.push(`expected 13 layers, received ${layers.length}`);
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
  const label = moduleCatalog.layers.find((l) => l.layer_id === layer.layer_id)?.layer_name ?? "";
  const parameterCount = Object.keys(layer).length;
  const visibleModules = modules.slice(0, 6);
  const visibleSubnodes: WorkflowNode[] = data.subnodes.slice(0, 6);
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
            title={translate(language, "module.viewAll", "查看全部模块")}
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
              <span className="module-count-badge">{visibleModules.length} {translate(language, "module.count", "个模块")}</span>
            </h3>
          </div>
        </div>
        <details className="folder-group-params nodrag nopan" onPointerDown={(event) => event.stopPropagation()}>
          <summary>{translate(language, "node.params", "参数")}</summary>
          <div className="folder-group-meta compact">
            <span>{translate(language, "field.status")}: schema</span>
            <span>Tier: core</span>
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
              return (
                <button
                  key={modId}
                  type="button"
                  className={`submodule-card module-drop-card cat-${category} status-${status.toLowerCase()} ${selectedModuleSet.has(modId) ? "is-selected" : ""}`}
                  style={moduleColors[modId] ? ({ "--mod-accent": moduleColors[modId] } as CSSProperties) : undefined}
                  onClick={(event) => {
                    onSelectDroppedModule(modId, event.ctrlKey || event.metaKey);
                  }}
                  onDoubleClick={(event) => {
                    event.preventDefault();
                    event.stopPropagation();
                    onOpenDroppedModule(modId);
                  }}
                  onContextMenu={(event) => {
                    event.preventDefault();
                    event.stopPropagation();
                    onDroppedModuleContextMenu(event, modId);
                  }}
                  title={`${moduleCatalogName(mod)} · ${slotLabel} · ${translate(language, `module.status.${status}`, status)}`}
                >
                  <span className="submodule-name">{moduleCatalogName(mod)}</span>
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

export function CanvasShell() {
  const mainFlowRef = useRef<ReactFlowInstance | null>(null);
  const libraryDefaultsAppliedRef = useRef(false);
  const consistencyWarningSignatureRef = useRef("");

  // uiState: shell navigation, drawers, panels, tabs, and visual editing state.
  const [bottomTab, setBottomTab] = useState<BottomTab>("logs");
  const [activeDrawer, setActiveDrawer] = useState<DrawerId | null>(null);
  const [selectedTemplateType, setSelectedTemplateType] = useState("schema_v04");
  const [loadingTemplateType, setLoadingTemplateType] = useState<string | null>(null);
  const [nodeLibraryCollapsed, setNodeLibraryCollapsed] = useState(false);
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

  // uiState: module tabs, naming, labels, groups, colors, and transient module UI.
  const [moduleTabs, setModuleTabs] = useState<string[]>([]);
  const [activeModuleTabId, setActiveModuleTabId] = useState<string | null>(null);
  const [pendingModuleAdd, setPendingModuleAdd] = useState<PendingModuleAdd | null>(null);
  const [focusedModuleId, setFocusedModuleId] = useState<string | null>(null);
  const [moduleNames, setModuleNames] = useState<Record<string, string>>({});
  const [uiNodeNames, setUiNodeNames] = useState<Record<string, string>>({});
  const [uiTags, setUiTags] = useState<Record<string, string[]>>({});
  const [uiGroups, setUiGroups] = useState<Record<string, string>>({});
  const [uiColors, setUiColors] = useState<Record<string, string>>({});
  const [uiInputs, setUiInputs] = useState<Record<string, Record<string, unknown>>>({});
  // Stage 5: capability modules attached to each left folder workspace (Module != Node,
  // not part of workflow execution). Keyed by layer node_id -> module ids.
  const [layerModules, setLayerModules] = useState<Record<string, string[]>>({});
  const [focusLayerId, setFocusLayerId] = useState<string | null>(null);
  const [moduleUiColors, setModuleUiColors] = useState<Record<string, string>>({});
  const [selectedLayerModuleKeys, setSelectedLayerModuleKeys] = useState<Set<string>>(() => new Set());

  // schemaState: backend catalog and registry snapshots used for rendering.
  const [moduleCatalog, setModuleCatalog] = useState<ModuleCatalogResponseV04 | null>(null);
  const [catalogRevision, setCatalogRevision] = useState(0);
  const moduleCatalogById = useMemo(() => new Map((moduleCatalog?.modules ?? []).map((module) => [module.module_id, module])), [moduleCatalog, catalogRevision]);
  const modulesByCatalogLayerId = useMemo(() => {
    const grouped = new Map<string, ModuleCatalogEntryV04[]>();
    for (const module of moduleCatalog?.modules ?? []) {
      grouped.set(module.layer_id, [...(grouped.get(module.layer_id) ?? []), module]);
    }
    return grouped;
  }, [moduleCatalog, catalogRevision]);
  const addModuleToLayer = useCallback(
    (layerNodeId: string, moduleId: string) => {
      if (!moduleCatalogById.has(moduleId)) {
        return;
      }
      setLayerModules((current) => {
        const existing = current[layerNodeId] ?? [];
        if (existing.includes(moduleId)) {
          return current;
        }
        return { ...current, [layerNodeId]: [...existing, moduleId] };
      });
      setSaveStatus("dirty");
    },
    [moduleCatalogById]
  );
  const removeModuleFromLayer = useCallback((layerNodeId: string, moduleId: string) => {
    setLayerModules((current) => ({ ...current, [layerNodeId]: (current[layerNodeId] ?? []).filter((id) => id !== moduleId) }));
    setSelectedLayerModuleKeys((current) => {
      const next = new Set(current);
      next.delete(`${layerNodeId}:${moduleId}`);
      return next;
    });
    setSaveStatus("dirty");
  }, []);
  const removeAllModulesFromLayer = useCallback((layerNodeId: string) => {
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
    setModuleUiColors((current) => ({ ...current, [`${layerNodeId}:${moduleId}`]: color }));
    setSaveStatus("dirty");
  }, []);
  const [selectedFlowNodeIds, setSelectedFlowNodeIds] = useState<Set<string>>(() => new Set());
  const [mainContextMenu, setMainContextMenu] = useState<CanvasContextMenuState | null>(null);
  const [showGrid, setShowGrid] = useState(true);
  const [showMiniMap, setShowMiniMap] = useState(true);
  const [collapsedCategories, setCollapsedCategories] = useState<Set<string>>(() => new Set());
  const [libraryBodyCollapsed, setLibraryBodyCollapsed] = useState(false);
  const [saveStatus, setSaveStatus] = useState<SaveStatus>("saved");

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
    apiReady,
    setSelectedNode,
    setLanguage,
    setValidation,
    setExportPreview,
    setApiReady,
    appendLog,
    clearRunOutput
  } = useCanvasStore();

  const t = useCallback((key: string, fallback?: string) => translate(language, key, fallback), [language]);
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
        setModuleCatalog(modules);
        setCatalogRevision((revision) => revision + 1);
        appendLog(`Module catalog loaded: ${modules.modules.length}; layers: ${modules.layers.length}`);
      })
      .catch((error) => {
        if (active) {
          appendLog(`Module catalog failed: ${(error as Error).message}`, "error");
        }
      });

    api
      .fetchSlotCatalog()
      .then((slots) => {
        if (active) {
          appendLog(`Slot catalog loaded: ${slots.slots.length}`);
        }
      })
      .catch((error) => {
        if (active) {
          appendLog(`Slot catalog failed: ${(error as Error).message}`, "error");
        }
      });

    api
      .fetchEngineRegistry()
      .then((engines) => {
        if (active) {
          appendLog(`Engine registry loaded: ${engines.engines.length}`);
        }
      })
      .catch((error) => {
        if (active) {
          appendLog(`Engine registry failed: ${(error as Error).message}`, "error");
        }
      });

    return () => {
      active = false;
    };
  }, [appendLog, language]);
  const selectedNodeId = useCanvasStore((state) => state.selectedNodeId);
  const handleUndo = useCallback(() => {
    appendLog(t("status.schemaOnly", "Schema-only canvas: workflow graph history is disabled."), "warn");
  }, [appendLog, t]);

  const handleRedo = useCallback(() => {
    appendLog(t("status.schemaOnly", "Schema-only canvas: workflow graph history is disabled."), "warn");
  }, [appendLog, t]);
  const templateOptions = useMemo(() => ["schema_v04"], []);

  useEffect(() => {
    if (libraryDefaultsAppliedRef.current || !nodeLibraryCategories.length) {
      return;
    }
    setCollapsedCategories(new Set(nodeLibraryCategories.map((category) => category.id)));
    setLibraryBodyCollapsed(false);
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
    setLayerModules({});
    setSelectedLayerModuleKeys(new Set());
    setModuleUiColors({});
  }, [moduleCatalog?.schema_version, catalogRevision]);

	  const layerById = useMemo(
	    () => new Map(catalogLayers.map((layer) => [layer.layer_id, layer])),
	    [catalogLayers]
	  );
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
          title_fallback: moduleCatalogName(mod),
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
	    if (workflow?.template_type) {
	      setSelectedTemplateType(workflow.template_type);
	    }
  }, [workflow?.template_type]);

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
      for (const id of layerById.keys()) {
        next.add(id);
      }
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
	    const frames = computeLayerStackFrames(catalogLayers, computeLayerModuleCounts(catalogLayers, layerModules));
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
      setActiveDrawer("inspector");
      appendLog(`${t("status.moduleSelected", "Module selected")}: ${t(node.title_key, node.title_fallback)}`);
    },
    [appendLog, setSelectedNode, t]
  );

  const handleChildModulePreview = useCallback(
    (node: WorkflowNode) => {
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
      const moduleNodeId = `${layerNodeId}${MODULE_INSTANCE_SEPARATOR}${moduleId}`;
      const mod = moduleCatalogById.get(moduleId);
      if (!mod) {
        return;
      }
      setModuleTabs((tabs) => (tabs.includes(moduleNodeId) ? tabs : [...tabs, moduleNodeId]));
      setActiveModuleTabId(moduleNodeId);
      setActiveDrawer(null);
      appendLog(`${t("status.moduleCanvasOpened", "Module canvas opened")}: ${moduleCatalogName(mod)}`);
    },
    [appendLog, moduleCatalogById, t]
  );

  const renameUiNode = useCallback(
    (nodeId: string, currentName: string) => {
      const nextName = window.prompt("Rename", currentName);
      if (!nextName?.trim()) {
        return;
      }
      setUiNodeNames((current) => ({ ...current, [nodeId]: nextName.trim() }));
      appendLog(`${t("status.nodeRenamed", "Node renamed")}: ${nextName.trim()}`);
    },
    [appendLog, t]
  );

  const renameUiModule = useCallback(
    (nodeId: string, currentName: string) => {
      const nextName = window.prompt("Module name", currentName);
      if (!nextName?.trim()) {
        return;
      }
      setModuleNames((current) => ({ ...current, [nodeId]: nextName.trim() }));
      appendLog(`${t("status.moduleRenamed", "Module renamed")}: ${nextName.trim()}`);
    },
    [appendLog, t]
  );

  const editUiTagsForIds = useCallback((nodeIds: string[], title = "Tags") => {
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
    setUiTags((current) => {
      const next = { ...current };
      for (const id of nodeIds) {
        next[id] = tags;
      }
      return next;
    });
    setSaveStatus("dirty");
  }, [uiTags]);

  const editUiGroupForIds = useCallback((nodeIds: string[], title = "Visual group") => {
    const firstId = nodeIds[0];
    if (!firstId) {
      return;
    }
    const nextGroup = window.prompt(title, uiGroups[firstId] ?? "");
    if (nextGroup === null) {
      return;
    }
    setUiGroups((current) => {
      const next = { ...current };
      for (const id of nodeIds) {
        next[id] = nextGroup.trim();
      }
      return next;
    });
    setSaveStatus("dirty");
  }, [uiGroups]);

  const renameVisualGroup = useCallback((nodeId: string) => {
    const currentGroup = uiGroups[nodeId] ?? "";
    const nextGroup = window.prompt("Rename group", currentGroup);
    if (nextGroup === null) {
      return;
    }
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
  }, [uiGroups]);

  const dissolveVisualGroup = useCallback((nodeId: string) => {
    const currentGroup = uiGroups[nodeId] ?? "";
    if (!currentGroup) {
      return;
    }
    setUiGroups((current) => {
      const next = { ...current };
      for (const [id, group] of Object.entries(current)) {
        if (group === currentGroup) {
          next[id] = "";
        }
      }
      return next;
    });
  }, [uiGroups]);

  const handleModuleContextMenu = useCallback(
    (event: ReactMouseEvent, node: WorkflowNode) => {
      const label = moduleNames[node.node_id] ?? translate(language, node.title_key, node.title_fallback);
      const group = uiGroups[node.node_id] ?? "";
      const menu = makeContextMenu(event, [
        {
          label: "放大查看",
          onSelect: () => {
            setFocusedModuleId(node.node_id);
            handleChildModulePreview(node);
          }
        },
        { label: "重命名 Module", onSelect: () => renameUiModule(node.node_id, label) },
        { label: "修改颜色", onSelect: () => {
          const nextColor = window.prompt(t("field.color", "Color"), uiColors[node.node_id] ?? "#4f8cff");
          if (nextColor) {
            setUiColors((current) => ({ ...current, [node.node_id]: nextColor.trim() }));
            setSaveStatus("dirty");
          }
        } },
        { label: "添加 / 编辑标签", onSelect: () => editUiTagsForIds([node.node_id], "Module tags") },
        { label: "创建分组", onSelect: () => editUiGroupForIds([node.node_id], "Module group") },
        { label: "重命名分组", onSelect: () => renameVisualGroup(node.node_id), disabled: !group },
        { label: "解散分组", onSelect: () => dissolveVisualGroup(node.node_id), disabled: !group }
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
      renameUiModule,
      renameVisualGroup,
      t,
      uiColors,
      uiGroups
    ]
  );

  const closeModuleTab = useCallback(
    (id: string) => {
      const index = moduleTabs.indexOf(id);
      const next = moduleTabs.filter((tabId) => tabId !== id);
      setModuleTabs(next);
      setActiveModuleTabId((current) => (current === id ? next[Math.max(0, index - 1)] ?? null : current));
      appendLog(`${t("status.moduleCanvasClosed", "Module canvas closed")}: ${id}`);
    },
    [appendLog, moduleTabs, t]
  );

  const reorderModuleTab = useCallback((fromId: string, toId: string) => {
    setModuleTabs((tabs) => {
      const from = tabs.indexOf(fromId);
      const to = tabs.indexOf(toId);
      if (from === -1 || to === -1 || from === to) {
        return tabs;
      }
      const next = [...tabs];
      const [moved] = next.splice(from, 1);
      next.splice(to, 0, moved);
      return next;
    });
  }, []);

  const pinModuleTab = useCallback((id: string) => {
    setModuleTabs((tabs) => (!tabs.includes(id) || tabs[0] === id ? tabs : [id, ...tabs.filter((tabId) => tabId !== id)]));
  }, []);

  const buildModuleAddMenu = useCallback(
    (layerNodeId: string, displayIndex: number): CanvasContextMenuItem[] => {
      const catalogLayerId = displayIndex >= 1 && displayIndex <= 13 ? `layer_${displayIndex}` : "general";
      const moduleChoices = [...(modulesByCatalogLayerId.get(catalogLayerId) ?? []), ...(modulesByCatalogLayerId.get("general") ?? [])];
      const byCategory = new Map<string, ModuleCatalogEntryV04[]>();
      for (const mod of moduleChoices) {
        byCategory.set(mod.category, [...(byCategory.get(mod.category) ?? []), mod]);
      }
      return [...byCategory.entries()].map(([category, mods]) => ({
        label: t(`module.category.${category}`, category),
        children: mods.map((mod) => ({
          label: `${moduleCatalogName(mod)} · ${mod.status}`,
          onSelect: () => addModuleToLayer(layerNodeId, moduleCatalogId(mod))
        }))
      }));
    },
    [addModuleToLayer, modulesByCatalogLayerId, t]
  );

  const openFolderContextMenu = useCallback(
    (event: ReactMouseEvent, layer: CatalogLayerInput) => {
      const menu = makeContextMenu(event, [
        {
          label: t("module.add", "添加模块"),
          children: buildModuleAddMenu(layer.layer_id, layer.layer_order)
        },
        { label: t("module.viewAll", "查看全部模块"), onSelect: () => setFocusLayerId(layer.layer_id) },
        { label: t("module.removeAll", "移除全部模块"), onSelect: () => removeAllModulesFromLayer(layer.layer_id), danger: true }
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
        { label: targetModuleIds.length > 1 ? `${targetModuleIds.length} ${t("module.count", "个模块")}` : mod ? moduleCatalogName(mod) : moduleId, disabled: true },
        {
          label: t("module.colorMenu", "修改颜色"),
          children: colorItems
        },
        { label: t("module.viewAll", "查看全部模块"), onSelect: () => setFocusLayerId(layer.layer_id) },
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
    [moduleCatalogById, removeModuleFromLayer, selectedLayerModuleKeys, setModuleColor, t]
  );

  const flowNodes = useMemo<Node[]>(() => {
    if (!moduleCatalog) {
      return [];
    }
    const catalogLayersForRender = moduleCatalog.layers.slice().sort((a, b) => catalogLayerOrder(a) - catalogLayerOrder(b));
    const stackFrames = computeLayerStackFrames(catalogLayersForRender, computeLayerModuleCounts(catalogLayersForRender, layerModules));
    const folderNodes = catalogLayersForRender.map((layer) => {
      const layerId = layer.layer_id;
      const subnodes: WorkflowNode[] = [];
      const attachedModuleIds = layerModules[layerId] ?? [];
      const attachedModules = attachedModuleIds
        .map((id) => moduleCatalogById.get(id))
        .filter((module): module is ModuleCatalogEntryV04 => Boolean(module));
      const attachedModuleColors = Object.fromEntries(attachedModuleIds.map((id) => [id, moduleUiColors[`${layerId}:${id}`] ?? ""]));
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
	        uiColors
      });
    });

    return [...folderNodes, ...layerSchemaNodes];
  }, [
    addModuleToLayer,
    focusedModuleId,
    handleChildModulePreview,
    handleChildModuleSelect,
    handleModuleContextMenu,
    layerModules,
    moduleCatalog,
    moduleCatalogById,
    moduleNames,
    moduleUiColors,
	    openCatalogModuleCanvas,
    openDroppedModuleContextMenu,
    openFolderContextMenu,
    selectLayerModule,
    selectedLayerModuleKeys,
    setModuleColor,
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

  const requireWorkflow = useCallback(() => {
    if (!workflow) {
      appendLog(t("error.noWorkflow"), "warn");
      return null;
    }
    return workflow;
  }, [appendLog, t, workflow]);

  const handleSave = useCallback(() => {
    const currentWorkflow = requireWorkflow();
    if (!currentWorkflow) {
      setSaveStatus("error");
      return;
    }
    downloadWorkflow(currentWorkflow);
    setSaveStatus("saved");
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

  // CLEAN V4: execution is backend-only (v0.3 via adapter). The UI never triggers
  // a run. This handler is a disabled stub kept only so existing buttons compile.
  const handleMockRun = useCallback(() => {
    appendLog(t("status.executionDisabled", "Execution is backend-only (v0.3 adapter). UI does not run workflows."), "warn");
  }, [appendLog, t]);

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

      if (templateType === "schema_v04") {
        setLoadingTemplateType(templateType);
        appendLog(`${t("status.templateLoading", "Loading template")}: ${t(`template.${templateType}`, templateType)}`);
        try {
          // CLEAN V4: re-derive the canvas from the v0.4 module-catalog schema
          // (no createPersonaBuilder / v0.3 workflow source).
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

  const openLayerWorkspace = useCallback(
    (layer: CatalogLayerInput, mode: WorkspaceMode) => {
      const catalogLayerName = moduleCatalog ? moduleCatalog.layers.find((l) => l.layer_id === layer.layer_id)?.layer_name ?? "" : "";
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
      if (mode === "right") {
        setActiveDrawer("inspector");
      }
      if (mode === "window") {
        setFloatingLayerIds((ids) => (ids.includes(layer.layer_id) ? ids : [...ids, layer.layer_id]));
      }
      appendLog(`${t("status.layerOpened", "Layer opened")}: L${layer.layer_order} ${catalogLayerName}`);
    },
    [appendLog, moduleCatalog, setSelectedNode, t]
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
          setActiveDrawer("inspector");
        }
        return;
      }
      setSelectedNode(node.id);
      setActiveDrawer("inspector");
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
      setSelectedNode(node.id);
    },
    [setSelectedNode]
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
    setDraggedNodeIds(new Set());
    appendLog(t("status.canvasArranged", "Canvas arranged"));
  }, [appendLog, t]);

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
	      const layerIndex = isLayer ? getLayerOrder(schemaNode) ?? 0 : 0;
      const menu = makeContextMenu(event, [
        ...(isLayer
          ? [
              { label: t("module.add", "添加模块"), children: buildModuleAddMenu(node.id, layerIndex) },
              { label: t("module.viewAll", "查看全部模块"), onSelect: () => setFocusLayerId(node.id) }
            ]
          : []),
        { label: "重命名", onSelect: () => renameUiNode(node.id, label) },
        { label: "修改颜色", onSelect: () => {
          const nextColor = window.prompt(t("field.color", "Color"), uiColors[node.id] ?? "#4f8cff");
          if (nextColor) {
            setUiColors((current) => ({ ...current, [node.id]: nextColor.trim() }));
            setSaveStatus("dirty");
          }
        } },
        { label: "删除节点", onSelect: () => deleteMainNodeById(node.id), disabled: isLayer, danger: true },
        { label: "复制节点", onSelect: () => copyMainNodeById(node.id), disabled: isLayer },
        { label: "添加 / 编辑标签", onSelect: () => editUiTagsForIds([node.id], "Node tags") },
        { label: "创建分组", onSelect: () => editUiGroupForIds([node.id], "Node group") },
        { label: "重命名分组", onSelect: () => renameVisualGroup(node.id), disabled: !group },
        { label: "解散分组", onSelect: () => dissolveVisualGroup(node.id), disabled: !group }
      ]);
      if (menu) {
        setMainContextMenu(menu);
      }
    },
    [
      buildModuleAddMenu,
      copyMainNodeById,
      deleteMainNodeById,
      dissolveVisualGroup,
      editUiGroupForIds,
      editUiTagsForIds,
      language,
      renameUiNode,
      renameVisualGroup,
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
          label: "删除连线",
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
    setUiColors((current) => {
      const next = { ...current };
      for (const id of selectedCanvasIds) {
        next[id] = nextColor.trim();
      }
      return next;
    });
    setSaveStatus("dirty");
  }, [appendLog, selectedCanvasIds, t, uiColors]);

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
    setUiTags((current) => {
      const next = { ...current };
      for (const id of selectedMainIds) {
        next[id] = tags;
      }
      return next;
    });
    setSaveStatus("dirty");
  }, [appendLog, selectedMainIds, t, uiTags]);

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
    setUiGroups((current) => {
      const next = { ...current };
      for (const id of selectedMainIds) {
        next[id] = nextGroup.trim();
      }
      return next;
    });
    setSaveStatus("dirty");
  }, [appendLog, selectedMainIds, t, uiGroups]);

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
	        { label: t("toolbar.undo", "撤销"), onSelect: handleUndo, disabled: true },
	        { label: t("toolbar.redo", "重做"), onSelect: handleRedo, disabled: true },
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

  const rightDockLayer = workspaceMode === "right" ? selectedLayer : null;
  const splitLayer = workspaceMode === "split" ? selectedLayer : null;
  const residentInstance = extractResidentInstance(residentPreviewOutput);
  const outputDrawer = activeDrawer === "logs" || activeDrawer === "artifacts" || activeDrawer === "preview" ? activeDrawer : null;
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
              {templateIsLoading ? t("toolbar.loading", "加载中") : t("toolbar.load")}
            </button>
          </div>
        </div>
        <div className="toolbar-actions">
	          <div className="run-bar" aria-label="Export validate mock run">
	            <button onClick={handleSave}>{t("toolbar.save")}</button>
	            <button onClick={handleValidate}>{t("toolbar.validate")}</button>
	            <button onClick={handleMockRun}>{t("toolbar.mockRun")}</button>
	            <button onClick={handleExportPreview}>{t("toolbar.exportPreview")}</button>
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

      <section className={`workspace-grid ${nodeLibraryCollapsed ? "is-library-collapsed" : ""}`}>
        <aside className={`panel left-panel ${nodeLibraryCollapsed ? "is-collapsed" : ""}`}>
          <button className="library-toggle" onClick={() => setNodeLibraryCollapsed((collapsed) => !collapsed)}>
            {nodeLibraryCollapsed ? ">" : "<"}
          </button>
          <section className="panel-section">
            <div className="section-title">
              {nodeLibraryCollapsed ? (
                <h2>{t("panel.nodeLibrary").slice(0, 1)}</h2>
              ) : (
                <button
                  type="button"
                  className="library-master-toggle"
                  onClick={() => setLibraryBodyCollapsed((value) => !value)}
                  aria-expanded={!libraryBodyCollapsed}
                >
                  <span className="node-library-category__chevron">{libraryBodyCollapsed ? "▸" : "▾"}</span>
                  <h2>{t("panel.nodeLibrary")}</h2>
                </button>
              )}
              <span>{libraryNodeTypes.length}</span>
            </div>
            {!nodeLibraryCollapsed && libraryBodyCollapsed ? null : nodeLibraryCollapsed ? (
              <div className="node-library mini">
                {libraryNodeTypes.map((type) => (
                  <div
                    key={type}
                    role="button"
                    tabIndex={0}
                    draggable
                    className={`library-item node-kind-${type}`}
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
                    <span className="library-item__icon">{getCollapsedLabel(type, language)}</span>
                  </div>
                ))}
              </div>
            ) : (
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
            collapsed={nodeLibraryCollapsed}
            layers={moduleCatalog?.layers ?? []}
            modules={moduleCatalog?.modules ?? []}
          />
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
                    selectNodesOnDrag={false}
                    deleteKeyCode={["Backspace", "Delete"]}
                  >
                    {showGrid ? <Background color="#3a3a3a" gap={24} /> : null}
                    <Controls />
                    {showMiniMap ? <MiniMap pannable zoomable /> : null}
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
	              <button disabled={templateIsLoading} onClick={() => handleTemplateClick("schema_v04")}>
	                {templateIsLoading ? t("toolbar.loading", "加载中") : t("toolbar.load")}
	              </button>
	            </div>
	          )}
        </section>
      </section>

      {focusLayerId ? (
        <ModuleFocusPanel
          layerLabel={moduleCatalog ? moduleCatalog.layers.find((l) => l.layer_id === focusLayerId)?.layer_name ?? "" : ""}
          moduleIds={layerModules[focusLayerId] ?? []}
          moduleCatalogById={moduleCatalogById}
          moduleColors={Object.fromEntries((layerModules[focusLayerId] ?? []).map((id) => [id, moduleUiColors[`${focusLayerId}:${id}`] ?? ""]))}
          t={t}
          onRemove={(moduleId) => removeModuleFromLayer(focusLayerId, moduleId)}
          onClose={() => setFocusLayerId(null)}
        />
      ) : null}

      <FloatingDock activeDrawer={activeDrawer} t={t} onToggle={toggleDrawer} />

      {activeDrawer === "layers" ? (
        <FloatingSidePanel
          title={t("panel.layerNavigator", "Layer Navigator")}
          meta={`${catalogLayers.length}/13`}
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

      {activeDrawer === "inspector" ? (
        <FloatingSidePanel
          title={t("panel.parameters")}
          meta={rightDockLayer ? t("workspace.right", "Right panel") : t("workspace.inspector", "Inspector")}
          onClose={() => setActiveDrawer(null)}
        >
          {rightDockLayer && (!selectedNode || selectedNode.type === "layer_container") ? (
            <LayerWorkspacePanel
              layer={rightDockLayer}
              moduleCatalog={moduleCatalog}
              edges={edges}
              t={t}
              mode="right"
              moduleNames={moduleNames}
              onOpen={openLayerWorkspace}
              onSelectNode={handleChildModuleSelect}
              onPreviewNode={handleChildModulePreview}
            />
          ) : (
            <ParameterPanel
              node={selectedNode}
              displayLabel={selectedNode && moduleCatalog ? moduleCatalog.layers.find((l) => l.layer_id === selectedNode.node_id)?.layer_name : undefined}
              workflow={workflow}
              logs={logs}
              output={exportPreview}
              uiColor={selectedNode ? uiColors[selectedNode.node_id] ?? "" : ""}
              uiTags={selectedNode ? uiTags[selectedNode.node_id] ?? [] : []}
              uiGroup={selectedNode ? uiGroups[selectedNode.node_id] ?? "" : ""}
              onColorChange={(color) => {
                if (!selectedNode) {
                  return;
                }
                setUiColors((current) => ({ ...current, [selectedNode.node_id]: color }));
                setSaveStatus("dirty");
              }}
              t={t}
            />
          )}
        </FloatingSidePanel>
      ) : null}

      {activeDrawer === "residentPreview" ? (
        <FloatingSidePanel
          title={t("panel.residentPreview", "Resident Preview")}
          meta={t("preview.mockLayer", "Mock preview")}
          className="resident-preview-panel"
          onClose={() => setActiveDrawer(null)}
        >
          <ResidentPreviewPanel resident={residentInstance} t={t} />
        </FloatingSidePanel>
      ) : null}

      {outputDrawer ? (
        <FloatingBottomPanel
          activeTab={bottomTab}
          t={t}
          onTab={(tab) => {
            setBottomTab(tab);
            setActiveDrawer(tab);
          }}
          onClose={() => setActiveDrawer(null)}
        >
          {bottomTab === "logs" ? <LogsPanel logs={logs} validation={validation} emptyText={t("panel.noLogs")} /> : null}
          {bottomTab === "artifacts" ? (
            <JsonPanel value={artifacts.length ? artifacts : null} emptyText={t("panel.noArtifacts")} />
          ) : null}
          {bottomTab === "preview" ? <JsonPanel value={exportPreview} emptyText={t("panel.noPreview")} /> : null}
        </FloatingBottomPanel>
      ) : null}
    </main>
  );
}

function ModuleFocusPanel({
  layerLabel,
  moduleIds,
  moduleCatalogById,
  moduleColors,
  t,
  onRemove,
  onClose
}: {
  layerLabel: string;
  moduleIds: string[];
  moduleCatalogById: Map<string, ModuleCatalogEntryV04>;
  moduleColors: Record<string, string>;
  t: (key: string, fallback?: string) => string;
  onRemove: (moduleId: string) => void;
  onClose: () => void;
}) {
  const mods = moduleIds
    .map((id) => moduleCatalogById.get(id))
    .filter((module): module is ModuleCatalogEntryV04 => Boolean(module));
  return (
    <div className="module-focus-backdrop" onClick={onClose}>
      <section className="module-focus" onClick={(event) => event.stopPropagation()}>
        <header className="module-focus__bar">
          <div>
            <p>{t("module.focusMode", "Focus Mode")}</p>
            <h3>{layerLabel}</h3>
            <span>{mods.length} {t("module.count", "modules")}</span>
          </div>
          <button onClick={onClose}>✕</button>
        </header>
        <div className="module-focus__grid">
          {mods.length ? (
            mods.map((mod) => {
              const modId = moduleCatalogId(mod);
              const slot = moduleCatalogSlot(mod);
              const slotLabel = t(`module.slot.${slot}`, slot.toUpperCase());
              const category = String(mod.category || "general");
              const status = String(mod.status);
              return (
                <div
                  key={modId}
                  className={`submodule-card module-drop-card cat-${category} status-${status.toLowerCase()}`}
                  style={moduleColors[modId] ? ({ "--mod-accent": moduleColors[modId] } as CSSProperties) : undefined}
                >
                  <span className="submodule-name">{moduleCatalogName(mod)}</span>
                  <span className="submodule-badge-row">
                    <span className="submodule-group">{mod.layer_id}</span>
                    <span className={`ai-slot-badge ai-slot-${category === "avatar" ? "ar" : category === "llm" || category === "memory" || category === "tts" || category === "runtime" ? category : "none"}`}>
                      {slotLabel}
                    </span>
                    <span className="submodule-tier">{t(`module.status.${status}`, status)}</span>
                    <button className="module-card__remove" onClick={() => onRemove(modId)}>
                      {t("module.remove", "移除")}
                    </button>
                  </span>
                </div>
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

function FloatingDock({
  activeDrawer,
  t,
  onToggle
}: {
  activeDrawer: DrawerId | null;
  t: (key: string, fallback?: string) => string;
  onToggle: (drawer: DrawerId) => void;
}) {
  const dockItems: { id: DrawerId; label: string }[] = [
    { id: "layers", label: t("panel.layerNavigator", "Layers") },
    { id: "inspector", label: t("workspace.inspector", "Inspector") },
    { id: "logs", label: t("panel.logs") },
    { id: "artifacts", label: t("panel.artifacts") },
    { id: "residentPreview", label: t("panel.residentPreview", "Resident Preview") },
    { id: "preview", label: t("panel.exportPreview") }
  ];
  const [dockOffset, setDockOffset] = useState({ x: 0, y: 0 });
  const suppressClickRef = useRef(false);

  const handleDockMouseDown = useCallback(
    (event: ReactMouseEvent<HTMLElement>) => {
      if (event.button !== 0) {
        return;
      }
      const startX = event.clientX;
      const startY = event.clientY;
      const startOffset = dockOffset;
      suppressClickRef.current = false;

      const handleMouseMove = (moveEvent: MouseEvent) => {
        const x = moveEvent.clientX - startX;
        const y = moveEvent.clientY - startY;
        if (Math.abs(x) + Math.abs(y) > 3) {
          suppressClickRef.current = true;
        }
        setDockOffset({ x: startOffset.x + x, y: startOffset.y + y });
      };
      const handleMouseUp = () => {
        window.removeEventListener("mousemove", handleMouseMove);
        window.removeEventListener("mouseup", handleMouseUp);
        window.setTimeout(() => {
          suppressClickRef.current = false;
        }, 0);
      };

      window.addEventListener("mousemove", handleMouseMove);
      window.addEventListener("mouseup", handleMouseUp);
    },
    [dockOffset]
  );

  return (
    <FloatingPortal>
    <nav
      className="floating-dock"
      style={{ transform: `translate(${dockOffset.x}px, ${dockOffset.y}px)` }}
      aria-label="Floating workspace dock"
      onMouseDown={handleDockMouseDown}
    >
      {dockItems.map((item) => (
        <button
          key={item.id}
          className={activeDrawer === item.id ? "is-active" : ""}
          title={item.label}
          aria-label={item.label}
          onClick={() => {
            if (!suppressClickRef.current) {
              onToggle(item.id);
            }
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
  if (id === "layers") {
    return (
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <path d="M4 6h16M4 12h16M4 18h16" />
        <path d="M7 4v4M12 10v4M17 16v4" />
      </svg>
    );
  }
  if (id === "inspector") {
    return (
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <path d="M5 5h14v14H5z" />
        <path d="M9 9h6M9 13h6M9 17h3" />
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
  onClose
}: {
  title: string;
  meta?: string;
  children: ReactNode;
  className?: string;
  onClose: () => void;
}) {
  return (
    <FloatingPortal>
      <aside className={`floating-side-panel${className ? ` ${className}` : ""}`}>
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
        const label = moduleCatalog ? moduleCatalog.layers.find((l) => l.layer_id === layer.layer_id)?.layer_name ?? "" : "";
        const collapsed = collapsedLayerIds.has(layer.layer_id);
        return (
          <div key={layer.layer_id} className="layer-nav-section">
          <article
            className={`layer-nav-item tier-core status-schema ${activeLayerId === layer.layer_id ? "is-active" : ""}`}
          >
            <button className="layer-nav-main" onClick={() => onOpen(layer, "inline")}>
              <span className="layer-index">{String(layer.layer_order).padStart(2, "0")}</span>
              <span className="layer-name">{label}</span>
              <span className="layer-status">schema</span>
            </button>
            <div className="layer-nav-meta">
              <span>core</span>
              <span>0 nodes</span>
              <span>{t("lock.editable", "editable")}</span>
            </div>
            <div className="layer-nav-actions" aria-label={`${label} workspace actions`}>
              <button onClick={() => onToggle(layer)}>{collapsed ? "+" : "-"}</button>
              <button onClick={() => onOpen(layer, "right")}>{t("workspace.rightShort", "Right")}</button>
              <button onClick={() => onOpen(layer, "split")}>{t("workspace.splitShort", "Split")}</button>
              <button onClick={() => onOpen(layer, "window")}>{t("workspace.windowShort", "Pop")}</button>
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
        title={t("workspace.backToCanvas", "Back to main canvas")}
      >
        <span>{t("field.workflow")}</span>
        <span>/</span>
        <strong>{activeId && moduleCatalog ? moduleCatalog.layers.find((l) => l.layer_id === activeId)?.layer_name ?? "" : "Pipeline"}</strong>
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
              <span>{moduleCatalog ? moduleCatalog.layers.find((l) => l.layer_id === layer.layer_id)?.layer_name ?? "" : ""}</span>
              <small>{mode}</small>
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
  const label = moduleCatalog ? moduleCatalog.layers.find((l) => l.layer_id === layer.layer_id)?.layer_name ?? "" : "";
  const parameterCount = Object.keys(layer).length;

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
            <span className="module-count-badge">0 modules</span>
          </h3>
          </div>
        </div>
        <div className="workspace-actions">
          <button onClick={() => setCollapsed((value) => !value)}>{collapsed ? "+" : "-"}</button>
          <button onClick={() => onOpen(layer, "right")}>{t("workspace.rightShort", "Right")}</button>
          <button onClick={() => onOpen(layer, "split")}>{t("workspace.splitShort", "Split")}</button>
          <button onClick={() => onOpen(layer, "window")}>{t("workspace.window", "New window")}</button>
        </div>
      </div>
      <div className="folder-group-meta">
        <span>{t("field.status")}: schema</span>
        <span>Tier: core</span>
        <span>{t("field.data")}: {parameterCount}</span>
        <span>{t("field.childrenCount")}: 0</span>
      </div>
      {!collapsed ? (
        <div className="submodule-rail">
          <div className="empty-node-canvas">0 modules</div>
        </div>
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
    type: "smoothstep"
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

// Ensure a node exposes at least one in/out port so WorkflowNodeCard renders
// connectable handles inside the module canvas (handles use ids p_in / p_out).
function ensurePorts(node: WorkflowNode): WorkflowNode {
  const inputs = node.ports?.inputs?.length ? node.ports.inputs : [{ port_id: "p_in" }];
  const outputs = node.ports?.outputs?.length ? node.ports.outputs : [{ port_id: "p_out" }];
  return { ...node, ports: { ...(node.ports ?? {}), inputs, outputs } } as unknown as WorkflowNode;
}

function nodeWidth(node: Node) {
  return node.measured?.width ?? node.width ?? 200;
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
      x: 120 + (index % columns) * 260,
      y: 90 + Math.floor(index / columns) * 170
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
        {menu.items.map((item) => (
          <CanvasContextMenuRow key={item.label} item={item} onClose={onClose} />
        ))}
      </div>
    </div>
  );
}

function CanvasContextMenuRow({ item, onClose }: { item: CanvasContextMenuItem; onClose: () => void }) {
  const [open, setOpen] = useState(false);
  if (item.children?.length) {
    return (
      <div
        className="canvas-context-menu__group"
        onMouseEnter={() => setOpen(true)}
        onMouseLeave={() => setOpen(false)}
      >
        <button type="button" role="menuitem" className="canvas-context-menu__parent" disabled={item.disabled}>
          <span>{item.label}</span>
          <span className="canvas-context-menu__caret">▸</span>
        </button>
        {open ? (
          <div className="canvas-context-menu__submenu" role="menu">
            {item.children.map((child) => (
              <CanvasContextMenuRow key={child.label} item={child} onClose={onClose} />
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


// Embedded, in-app module sub-canvas. Module-scoped state only: it owns its own
// ReactFlow nodes/edges (useNodesState/useEdgesState) and never touches the canvas
// store, so it does not render or mutate the 13-layer workflow. Unmounting on close
// destroys all of its state.
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
  onClose: () => void;
}) {
  const title = translate(language, moduleNode.title_key, moduleNode.title_fallback);
  const handledAddRequestRef = useRef<number | null>(null);
  const moduleFlowRef = useRef<ReactFlowInstance | null>(null);
  const [contextMenu, setContextMenu] = useState<CanvasContextMenuState | null>(null);
  const [copiedModuleNode, setCopiedModuleNode] = useState<WorkflowNode | null>(null);

	  // Seed module sub-canvas from the current v0.4 schema-derived view only.
	  const initialGraph = useMemo<{ nodes: Node[]; edges: Edge[] }>(() => {
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
  }, [moduleNode, initialSubnodes]);

  const [moduleNodes, setModuleNodes, onBaseModuleNodesChange] = useNodesState(initialGraph.nodes);
  const [moduleEdges, setModuleEdges, onModuleEdgesChange] = useEdgesState<Edge>(initialGraph.edges);
  const [selectedId, setSelectedId] = useState<string>("");
  const [executionResult, setExecutionResult] = useState<unknown>(null);
  const [executionError, setExecutionError] = useState<string | null>(null);
  const [runStatus, setRunStatus] = useState<RunWorkflowStatus>("idle");
	  const [runInputText, setRunInputText] = useState("");
	  const addedRef = useRef(0);

  const addModuleNode = useCallback((type: ModuleNodeType, position?: { x: number; y: number }) => {
    addedRef.current += 1;
    const seq = addedRef.current;
    const id = `${moduleNode.node_id}_${type}_${Date.now()}_${seq}`;
    const definition = getNodeDefinition(type);
    const schemaNode = ensurePorts({
      node_id: id,
      type,
      category: definition?.category ?? backendNodeCategory(type),
      title_key: `node.type.${type}`,
      title_fallback: definition?.display_name ?? type,
      position: { x: 0, y: 0 },
      lock_level: "editable",
      locale: null,
      data: {
        parent_module: moduleNode.node_id,
        ...Object.fromEntries((definition?.input_schema ?? []).map((field: NodeInputField) => [field.key, field.default ?? ""]))
      },
      input_schema: definition?.input_schema,
      output_schema: definition?.output_schema,
      ports: { inputs: [], outputs: [] },
      validation: null
    } as unknown as WorkflowNode);
    setModuleNodes((current) => [
      ...current,
      {
        id,
        type: "workflowNode",
        position: position ?? { x: 360, y: 80 + current.length * 70 },
        deletable: true,
        data: { schemaNode }
      }
    ]);
    setSelectedId(id);
  }, [moduleNode.node_id, setModuleNodes]);

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
      const currentNodeIds = new Set(moduleNodes.map((node) => node.id));
      if (!currentNodeIds.has(connection.source) || !currentNodeIds.has(connection.target)) {
        return;
      }
      setModuleEdges((eds) => addEdge({ ...connection, type: "smoothstep" }, eds));
    },
    [moduleNodes, setModuleEdges]
  );

  const onModuleNodesChange = useCallback(
    (changes: NodeChange[]) => {
      const removedIds = changes.filter((change) => change.type === "remove").map((change) => change.id);
      onBaseModuleNodesChange(changes);
      if (removedIds.length) {
        const removed = new Set(removedIds);
        setModuleEdges((current) => current.filter((edge) => !removed.has(edge.source) && !removed.has(edge.target)));
        setSelectedId((current) => (current && removed.has(current) ? "" : current));
      }
    },
    [onBaseModuleNodesChange, setModuleEdges]
  );

  const handleModuleNodesDelete = useCallback(
    (deleted: Node[]) => {
      const removed = new Set(deleted.map((node) => node.id));
      if (!removed.size) {
        return;
      }
      setModuleEdges((current) => current.filter((edge) => !removed.has(edge.source) && !removed.has(edge.target)));
      setSelectedId((current) => (current && removed.has(current) ? "" : current));
    },
    [setModuleEdges]
  );

  const selectedSchema = useMemo(() => {
    const found = moduleNodes.find((node) => node.id === selectedId);
    return (found?.data as { schemaNode?: WorkflowNode } | undefined)?.schemaNode ?? null;
  }, [moduleNodes, selectedId]);

  const patchModuleNodeData = useCallback(
    (id: string, patch: Record<string, unknown>) => {
      setModuleNodes((current) =>
        current.map((node) => {
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
        })
      );
    },
    [setModuleNodes]
  );

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
          onInput: (key: string, value: unknown) => patchModuleNodeData(node.id, { [key]: value })
        }
      })),
    [moduleNodes, patchModuleNodeData]
  );

  const applyAlignment = useCallback(
    (action: AlignAction) => {
      setModuleNodes((current) => alignFlowNodes(current, selectedOrAllNodeIds(current), action));
    },
    [setModuleNodes]
  );

  const applyDistribution = useCallback(
    (action: DistributeAction) => {
      setModuleNodes((current) => distributeFlowNodes(current, selectedOrAllNodeIds(current), action));
    },
    [setModuleNodes]
  );

  const arrangeNodes = useCallback(() => {
    setModuleNodes((current) => arrangeFlowNodes(current));
  }, [setModuleNodes]);

  const deleteSelected = useCallback(() => {
    const selectedNodes = moduleNodes.filter((node) => node.selected).map((node) => node.id);
    const selectedEdges = moduleEdges.filter((edge) => edge.selected).map((edge) => edge.id);
    if (!selectedNodes.length && !selectedEdges.length) {
      return;
    }
    const removedNodes = new Set(selectedNodes);
    const removedEdges = new Set(selectedEdges);
    setModuleNodes((current) => current.filter((node) => !removedNodes.has(node.id)));
    setModuleEdges((current) =>
      current.filter((edge) => !removedEdges.has(edge.id) && !removedNodes.has(edge.source) && !removedNodes.has(edge.target))
    );
    setSelectedId((current) => (current && removedNodes.has(current) ? "" : current));
  }, [moduleEdges, moduleNodes, setModuleEdges, setModuleNodes]);

  const updateModuleNodeDataById = useCallback(
    (nodeId: string, updater: (schemaNode: WorkflowNode) => WorkflowNode) => {
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
    [setModuleNodes]
  );

  const deleteModuleNodeById = useCallback(
    (nodeId: string) => {
      setModuleNodes((current) => current.filter((node) => node.id !== nodeId));
      setModuleEdges((current) => current.filter((edge) => edge.source !== nodeId && edge.target !== nodeId));
      setSelectedId((current) => (current === nodeId ? "" : current));
    },
    [setModuleEdges, setModuleNodes]
  );

  const renameModuleCanvasNode = useCallback(
    (nodeId: string) => {
      const schemaNode = (moduleNodes.find((node) => node.id === nodeId)?.data as { schemaNode?: WorkflowNode } | undefined)?.schemaNode;
      if (!schemaNode) {
        return;
      }
      const nextName = window.prompt("Rename node", translate(language, schemaNode.title_key, schemaNode.title_fallback));
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
      const nextTags = window.prompt("Node tags", currentText);
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
      const nextGroup = window.prompt("Node group", currentGroup);
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
      const nextGroup = window.prompt("Rename group", currentGroup);
      if (nextGroup === null) {
        return;
      }
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
    [moduleNodes, setModuleNodes]
  );

  const dissolveModuleNodeGroup = useCallback(
    (nodeId: string) => {
      const schemaNode = (moduleNodes.find((node) => node.id === nodeId)?.data as { schemaNode?: WorkflowNode } | undefined)?.schemaNode;
      const currentGroup = typeof schemaNode?.data?.ui_group === "string" ? schemaNode.data.ui_group : "";
      if (!currentGroup) {
        return;
      }
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
    [moduleNodes, setModuleNodes]
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
  }, [copiedModuleNode, setModuleNodes]);

  const deleteModuleEdgeById = useCallback(
    (edgeId: string) => {
      setModuleEdges((current) => current.filter((edge) => edge.id !== edgeId));
    },
    [setModuleEdges]
  );

  const handleModuleNodeContextMenu: NodeMouseHandler = useCallback(
    (event, node) => {
      setSelectedId(node.id);
      const schemaNode = (node.data as { schemaNode?: WorkflowNode } | undefined)?.schemaNode;
      const group = typeof schemaNode?.data?.ui_group === "string" ? schemaNode.data.ui_group : "";
      const menu = makeContextMenu(event, [
        { label: "重命名", onSelect: () => renameModuleCanvasNode(node.id) },
        { label: "删除节点", onSelect: () => deleteModuleNodeById(node.id), danger: true },
        { label: "复制节点", onSelect: () => copyModuleNodeById(node.id) },
        { label: "添加 / 编辑标签", onSelect: () => editModuleNodeTags(node.id) },
        { label: "创建分组", onSelect: () => editModuleNodeGroup(node.id) },
        { label: "重命名分组", onSelect: () => renameModuleNodeGroup(node.id), disabled: !group },
        { label: "解散分组", onSelect: () => dissolveModuleNodeGroup(node.id), disabled: !group }
      ]);
      if (menu) {
        setContextMenu(menu);
      }
    },
    [
      copyModuleNodeById,
      deleteModuleNodeById,
      dissolveModuleNodeGroup,
      editModuleNodeGroup,
      editModuleNodeTags,
      renameModuleCanvasNode,
      renameModuleNodeGroup
    ]
  );

  const handleModuleEdgeContextMenu = useCallback(
    (event: ContextMenuEvent, edge: Edge) => {
      const menu = makeContextMenu(event, [{ label: "删除连线", onSelect: () => deleteModuleEdgeById(edge.id), danger: true }]);
      if (menu) {
        setContextMenu(menu);
      }
    },
    [deleteModuleEdgeById]
  );

  const renameModule = useCallback(() => {
    const nextName = window.prompt("Module name", title);
    if (nextName?.trim()) {
      onRenameModule(moduleNode.node_id, nextName.trim());
    }
  }, [moduleNode.node_id, onRenameModule, title]);

  const updateSelectedNodeData = useCallback(
    (updater: (data: Record<string, unknown>) => Record<string, unknown>) => {
      if (!selectedId) {
        return;
      }
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
    [selectedId, setModuleNodes]
  );

  const editSelectedTags = useCallback(() => {
    const currentTags = selectedSchema?.data?.ui_tags;
    const currentText = Array.isArray(currentTags) ? currentTags.join(", ") : "";
    const nextTags = window.prompt("Node tags", currentText);
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
    const nextGroup = window.prompt("Node group", currentGroup);
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
      copiedModuleNode,
      deleteSelected,
      editSelectedGroup,
      editSelectedTags,
      libraryNodeTypes,
      moduleNodes,
      pasteModuleNode,
      renameModule,
      selectedSchema,
      t
    ]
  );

  // CLEAN V4: the UI must not trigger any execution / resident compile. This is a
  // disabled stub — execution happens only in backend v0.3 via the adapter.
  const handleRunWorkflow = useCallback(() => {
    setExecutionResult(null);
    setExecutionError(t("status.executionDisabled", "Execution is backend-only (v0.3 adapter). UI does not run workflows."));
    setRunStatus("idle");
  }, [t]);
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
        >
          {!moduleNodes.length ? (
            <div className="module-canvas-panel__empty-state">
              <strong>{t("empty.moduleTitle", "Module canvas is empty")}</strong>
              <span>{t("empty.moduleBody", "Start by adding nodes from the left library, then connect Input / Transform / Personality / Output.")}</span>
            </div>
          ) : null}
          <ReactFlow
            nodes={moduleFlowNodes}
            edges={moduleEdges}
            nodeTypes={nodeTypes}
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
            onNodeClick={(_event, node) => {
              setContextMenu(null);
              setSelectedId(node.id);
            }}
            onNodeContextMenu={handleModuleNodeContextMenu}
            onEdgeContextMenu={handleModuleEdgeContextMenu}
            onPaneContextMenu={handleModulePaneContextMenu}
            onPaneClick={() => setContextMenu(null)}
            selectionOnDrag
            selectNodesOnDrag={false}
            deleteKeyCode={["Backspace", "Delete"]}
          >
            <Background color="#333" gap={20} />
            <Controls />
            <MiniMap pannable zoomable />
          </ReactFlow>
          {contextMenu ? <CanvasContextMenu menu={contextMenu} onClose={() => setContextMenu(null)} /> : null}
        </div>
        <aside className="module-canvas-panel__inspector">
          <h4>{t("panel.parameters", "Inspector")}</h4>
          {executionError ? (
            <section className="module-canvas-panel__result is-error">
              <h4>{t("result.error", "error")}</h4>
              <pre>{executionError}</pre>
            </section>
          ) : executionResult !== null && executionResult !== undefined ? (
            <section className="module-canvas-panel__result is-success">
              <h4>{t("result.persona_result", "persona_result")}</h4>
              <pre>{safeStringify(executionResult)}</pre>
            </section>
          ) : null}
          {selectedSchema ? (
            <>
              <section className="inspector-section">
                <h4>{t("inspector.basic", "Basic")}</h4>
              <dl>
                <dt>{t("field.nodeId", "Node ID")}</dt>
                <dd>{selectedSchema.node_id}</dd>
                <dt>{t("field.type", "Type")}</dt>
                <dd>{selectedSchema.type}</dd>
                <dt>{t("field.lockLevel", "Lock")}</dt>
                <dd>{translate(language, `lock.${selectedSchema.lock_level}`, selectedSchema.lock_level)}</dd>
              </dl>
              </section>
              <section className="inspector-section">
                <h4>{t("inspector.parameters", "Parameters")}</h4>
                <label className="color-field">
                  <span>{t("field.color", "Color")}</span>
                  <input
                    type="color"
                    value={typeof selectedSchema.data?.ui_color === "string" && selectedSchema.data.ui_color ? selectedSchema.data.ui_color : "#4f8cff"}
                    onChange={(event) => updateSelectedNodeData((data) => ({ ...data, ui_color: event.target.value }))}
                  />
                </label>
              <pre>{safeStringify(selectedSchema.data ?? {})}</pre>
              </section>
            </>
          ) : (
            <div className="module-canvas-panel__empty">{t("panel.emptySelection", "Select a node")}</div>
          )}
        </aside>
      </div>
    </section>
  );
}

function ParameterPanel({
  node,
  displayLabel,
  workflow,
  logs,
  output,
  uiColor,
  uiTags,
  uiGroup,
  onColorChange,
  t
}: {
  node: WorkflowNode | null;
  displayLabel?: string;
  workflow: Workflow | null;
  logs: { ts?: string; level: string; message: string }[];
  output: unknown;
  uiColor: string;
  uiTags: string[];
  uiGroup: string;
  onColorChange: (color: string) => void;
  t: (key: string, fallback?: string) => string;
}) {
  if (!node) {
    return (
      <div className="empty-panel">
        <p>{t("panel.emptySelection")}</p>
        {workflow ? (
          <dl>
            <dt>{t("field.workflow")}</dt>
            <dd>{workflow.name}</dd>
            <dt>{t("field.template")}</dt>
            <dd>{workflow.template_type}</dd>
            <dt>Schema</dt>
            <dd>{workflow.schema_version}</dd>
          </dl>
        ) : null}
      </div>
    );
  }

  const position = node.position ?? { x: 0, y: 0 };

  return (
    <div className="parameter-content">
      <h3>{displayLabel ?? t(node.title_key, node.title_fallback)}</h3>
      <section className="inspector-section">
        <h4>{t("inspector.basic", "Basic")}</h4>
        <dl>
          <dt>{t("field.nodeId")}</dt>
          <dd>{node.node_id}</dd>
          <dt>{t("field.type")}</dt>
          <dd>{getNodeTypeLabel(node.type, t)}</dd>
          <dt>{t("field.category")}</dt>
          <dd>{node.category}</dd>
          <dt>{t("field.lockLevel")}</dt>
          <dd>{t(`lock.${node.lock_level}`, node.lock_level)}</dd>
          <dt>{t("field.position")}</dt>
          <dd>
            {Math.round(position.x)}, {Math.round(position.y)}
          </dd>
          <dt>{t("field.validation")}</dt>
          <dd>{node.validation?.status ?? "-"}</dd>
        </dl>
      </section>
      <section className="inspector-section">
        <h4>{t("inspector.parameters", "Parameters")}</h4>
        <label className="color-field">
          <span>{t("field.color", "Color")}</span>
          <input type="color" value={uiColor || "#4f8cff"} onChange={(event) => onColorChange(event.target.value)} />
        </label>
        <pre>{JSON.stringify(node.data ?? {}, null, 2)}</pre>
      </section>
      <section className="inspector-section">
        <h4>{t("inspector.tags", "Tags")}</h4>
        <p>{uiGroup ? `${t("field.group", "Group")}: ${uiGroup}` : t("inspector.noGroup", "No group")}</p>
        <p>{uiTags.length ? uiTags.join(", ") : t("inspector.noTags", "No tags")}</p>
      </section>
      <section className="inspector-section">
        <h4>{t("inspector.logs", "Logs")}</h4>
        <p>{logs[0]?.message ?? t("panel.noLogs")}</p>
      </section>
      <section className="inspector-section">
        <h4>{t("inspector.output", "Output")}</h4>
        <pre>{output ? safeStringify(output) : t("panel.noPreview")}</pre>
      </section>
    </div>
  );
}

function LogsPanel({
  logs,
  validation,
  emptyText
}: {
  logs: { ts?: string; level: string; message: string }[];
  validation: unknown;
  emptyText: string;
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
      {validation ? <pre>{JSON.stringify(validation, null, 2)}</pre> : null}
    </div>
  );
}

function JsonPanel({ value, emptyText }: { value: unknown; emptyText: string }) {
  if (!value) {
    return <div className="bottom-empty">{emptyText}</div>;
  }

  return <pre className="json-panel">{JSON.stringify(value, null, 2)}</pre>;
}

function ResidentPreviewPanel({ resident, t }: { resident: ResidentInstance | null; t: (key: string, fallback?: string) => string }) {
  const [activeTab, setActiveTab] = useState<ResidentPreviewTab>("dialogue");
  const [chatInput, setChatInput] = useState("");
  const [chatMessages, setChatMessages] = useState<{ role: "user" | "resident"; text: string }[]>([]);
  const [voicePlaying, setVoicePlaying] = useState(false);

  if (!resident) {
    return (
      <div className="resident-preview resident-preview--empty">
        <strong>{t("preview.emptyTitle", "No resident preview yet")}</strong>
        <p>{t("preview.emptyBody", "Run a module ending with compile_resident to preview dialogue, voice, and avatar state.")}</p>
      </div>
    );
  }

  const dialogue: NonNullable<ResidentInstance["dialogue"]> = resident.dialogue ?? { tone: "", formality: "", sample: "" };
  const voice: NonNullable<ResidentInstance["voice_profile"]> = resident.voice_profile ?? { voice_id: "", pitch: "", speed: 1, timbre: "", mock: true };
  const avatar: NonNullable<ResidentInstance["avatar"]> = resident.avatar ?? { preset: "", color: "#4f8cff", density: 0.6, motion: "", mock: true };
  const tone = dialogue.tone || t("preview.defaultTone", "calm");
  const sample = dialogue.sample || t("preview.noDialogueSample", "No dialogue sample is available yet.");
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
          </div>
        </section>
      ) : null}
    </div>
  );
}
