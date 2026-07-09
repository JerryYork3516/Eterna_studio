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

const MODULE_INSTANCE_SEPARATOR = "::";
const CATALOG_GRAPH_REPLACE_MODULE_IDS = new Set([
  "memory_provider_router",
  "memory_access_control",
  "short_term_memory",
  "preference_memory",
  "event_memory",
  "memory_update",
]);

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value && typeof value === "object" && !Array.isArray(value));
}

function cloneJson<T>(value: T): T {
  return JSON.parse(JSON.stringify(value)) as T;
}

function stableJson(value: unknown) {
  return JSON.stringify(value ?? null);
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
    edges: graph.edges?.length ? graph.edges : initialEdges ?? [],
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
      if (!currentPosition || currentPosition.x !== seedPosition.x || currentPosition.y !== seedPosition.y) {
        setGraphNodePosition(nextNode, seedPosition);
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

  const nextEdges = initialEdges?.length ? initialEdges : graph.edges;
  if (initialEdges?.length && stableJson(graph.edges) !== stableJson(initialEdges)) {
    changed = true;
  }
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
      return graph;
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
      return graph;
    }
    const mergedGraph = mergeCatalogSeed(existingGraph, initialNodes, initialEdges);
    if (mergedGraph) {
      store.updateModuleGraph(moduleNodeId, mergedGraph.nodes, mergedGraph.edges, mergedGraph.viewport);
      console.log("[P1-BRIDGE] ensureModuleGraphExists: merged catalog field seed into existing graph");
      return mergedGraph;
    }
    console.log("[P1-BRIDGE] ensureModuleGraphExists: graph already in store");
    return existingGraph;
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
      return seedGraph;
    }
    const mergedGraph = mergeCatalogSeed(graph, initialNodes, initialEdges) ?? graph;
    store.updateModuleGraph(moduleNodeId, mergedGraph.nodes, mergedGraph.edges, mergedGraph.viewport);
    if (mergedGraph !== graph) {
      console.log("[P1-BRIDGE] ensureModuleGraphExists: merged catalog field seed into legacy graph");
    }
    return mergedGraph;
  }
  
  // 3. 创建新的空 graph
  const newGraph: ModuleGraph = {
    moduleNodeId,
    nodes: initialNodes ?? [],
    edges: initialEdges ?? [],
  };
  store.updateModuleGraph(moduleNodeId, newGraph.nodes, newGraph.edges);
  console.log(hasInitialGraph ? "[P1-BRIDGE] ensureModuleGraphExists: created graph from catalog seed" : "[P1-BRIDGE] ensureModuleGraphExists: created new empty graph");
  
  return newGraph;
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
