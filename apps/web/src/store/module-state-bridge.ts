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
  
  // 1. 检查 store 中是否已存在
  if (store.moduleGraphs[moduleNodeId]) {
    console.log("[P1-BRIDGE] ensureModuleGraphExists: graph already in store");
    return store.moduleGraphs[moduleNodeId];
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
    store.updateModuleGraph(moduleNodeId, graph.nodes, graph.edges);
    return graph;
  }
  
  // 3. 创建新的空 graph
  const newGraph: ModuleGraph = {
    moduleNodeId,
    nodes: initialNodes ?? [],
    edges: initialEdges ?? [],
  };
  store.updateModuleGraph(moduleNodeId, newGraph.nodes, newGraph.edges);
  console.log("[P1-BRIDGE] ensureModuleGraphExists: created new empty graph");
  
  return newGraph;
}

/**
 * 清理孤立的 graph（对应的 module 不在 moduleTabs 中）
 */
export function cleanupOrphanedGraphs() {
  console.log("[P1-BRIDGE] cleanupOrphanedGraphs: starting");
  
  const store = useCanvasStore.getState();
  const tabs = store.moduleTabs;
  const graphs = Object.keys(store.moduleGraphs);
  
  const orphaned = graphs.filter(graphId => !tabs.includes(graphId));
  
  if (orphaned.length > 0) {
    console.warn("[P1-BRIDGE] cleanupOrphanedGraphs: found orphaned graphs", { count: orphaned.length, ids: orphaned });
    
    // 创建新的 graphs 对象，排除孤立的
    const cleaned = { ...store.moduleGraphs };
    orphaned.forEach(graphId => {
      delete cleaned[graphId];
      // 注意：不删除 localStorage 中的旧 key，因为可能还需要
    });
    
    store.setModuleGraphs(cleaned);
    console.log("[P1-BRIDGE] cleanupOrphanedGraphs: removed orphaned graphs");
  } else {
    console.log("[P1-BRIDGE] cleanupOrphanedGraphs: no orphaned graphs found");
  }
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
export function handleTabOpened(moduleId: string) {
  console.log("[P1-BRIDGE] handleTabOpened:", { moduleId });
  
  const store = useCanvasStore.getState();
  
  // 1. 确保 tab 在 moduleTabs 中
  if (!store.moduleTabs.includes(moduleId)) {
    store.openModuleTab(moduleId);
  }
  
  // 2. 确保 graph 存在
  ensureModuleGraphExists(moduleId);
  
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
