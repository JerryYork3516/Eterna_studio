/**
 * Canvas 状态持久化工具
 * 支持自动保存到 localStorage 和手动导出/导入 JSON 文件
 */

export type ModuleInstance = {
  instanceId: string;
  moduleId: string;
  layerId: string;
};

// P1-FIX：改进 ModuleGraphState 类型定义
export type ModuleGraphState = {
  moduleId: string;
  nodes: any[];  // 仍然使用 any[]（兼容 Node 类型），但在 store 层使用 WorkflowNode[]
  edges: any[];  // 仍然使用 any[]（兼容 Edge 类型），但在 store 层使用 WorkflowEdge[]
};

export type CanvasState = {
  version: "v4";
  timestamp: string;
  
  // UI 状态
  moduleTabs: string[];
  moduleNames: Record<string, string>;
  uiNodeNames: Record<string, string>;
  uiTags: Record<string, string[]>;
  uiGroups: Record<string, string>;
  uiColors: Record<string, string>;
  moduleUiColors: Record<string, string>;
  
  // 模块状态
  layerModules: Record<string, string[]>;
  moduleInstanceRegistry: Record<string, ModuleInstance>;
  
  // 模块画布内的图（节点和边）
  moduleGraphs: Record<string, ModuleGraphState>;
  
  // 画布视口（可选）
  viewport?: {
    x: number;
    y: number;
    zoom: number;
  };
};

const CANVAS_STATE_KEY = "eterna_canvas_v4";
const EXPORT_FILE_PREFIX = "eterna_canvas_";
const MODULE_GRAPH_KEY_PREFIX = "module_graph_";
const MODULE_GRAPH_BACKUP_KEY_PREFIX = "module_graph_backup_";
const EDITOR_MIGRATION_KEY_PREFIX = "eterna_editor_migration_";

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

function clonePersistenceValue<T>(value: T): T {
  if (typeof structuredClone === "function") {
    try {
      return structuredClone(value);
    } catch {
      // Canvas/DR state is JSON data; use the JSON fallback for older browsers.
    }
  }
  return JSON.parse(JSON.stringify(value)) as T;
}

export function attachedModuleIdsFromLayerModules(layerModules: Record<string, string[]>): string[] {
  return [...new Set(Object.values(layerModules).flatMap((moduleIds) => moduleIds.filter((moduleId) => typeof moduleId === "string" && moduleId.length > 0)))];
}

function recoveredNodeId(instanceId: string, nodeId: string): string {
  return nodeId.includes("::") ? nodeId : `${instanceId}::${nodeId}`;
}

function readableNodeName(nodeId: string): string {
  return nodeId
    .split("_")
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

/**
 * Rebuild the editor-owned attachment/index state from an exported DR.
 *
 * A compiled DR does not carry tabs, viewport, selection, or the original
 * attachment subset. Older compilers also copied graphless catalog modules
 * into every DR, so only a non-empty compiled module_graph is evidence that an
 * editor instance existed. Recovery attaches those graph-backed modules and
 * preserves their compiled order within each layer.
 */
export function recoverCanvasStateFromDigitalResident(data: unknown): CanvasState | null {
  if (!isRecord(data) || data.file_type !== "digital_resident") {
    return null;
  }
  const payload = isRecord(data.payload) ? data.payload : data;
  const modules = Array.isArray(payload.modules) ? payload.modules.filter(isRecord) : [];
  if (modules.length === 0) {
    return null;
  }

  const state = createEmptyCanvasState();
  for (const module of modules) {
    const moduleId = typeof module.module_id === "string" ? module.module_id : "";
    const layerId = typeof module.layer_id === "string" ? module.layer_id : "";
    if (!moduleId || !layerId) {
      continue;
    }

    const moduleGraph = isRecord(module.module_graph) ? module.module_graph : {};
    const compiledNodes = Array.isArray(moduleGraph.nodes) ? moduleGraph.nodes.filter(isRecord) : [];
    const compiledEdges = Array.isArray(moduleGraph.edges) ? moduleGraph.edges.filter(isRecord) : [];
    if (compiledNodes.length === 0 && compiledEdges.length === 0) {
      continue;
    }

    const instanceId = `${layerId}::${moduleId}`;
    const attached = state.layerModules[layerId] ?? [];
    if (!attached.includes(moduleId)) {
      state.layerModules[layerId] = [...attached, moduleId];
    }
    state.moduleInstanceRegistry[instanceId] = { instanceId, moduleId, layerId };

    const editorNodeIdByCompiledId = new Map<string, string>();
    const nodes = compiledNodes.map((node, index) => {
      const compiledNodeId = String(node.node_id || node.id || `node_${index + 1}`);
      const nodeId = recoveredNodeId(instanceId, compiledNodeId);
      const nodeType = String(node.node_type || node.type || "transform");
      editorNodeIdByCompiledId.set(compiledNodeId, nodeId);
      const params = isRecord(node.params) ? clonePersistenceValue(node.params) : {};
      const outputs = isRecord(node.outputs) ? clonePersistenceValue(node.outputs) : {};
      const metadata = isRecord(node.metadata) ? clonePersistenceValue(node.metadata) : {};
      const i18nKeys = isRecord(node.i18n_keys) ? clonePersistenceValue(node.i18n_keys) : {};
      const position = isRecord(node.position)
        ? { x: Number(node.position.x) || 0, y: Number(node.position.y) || 0 }
        : { x: 120 + index * 360, y: 100 };
      return {
        node_id: nodeId,
        type: nodeType,
        category: "compile_time",
        title_key: String(i18nKeys.name || `node.type.${nodeType}`),
        title_fallback: readableNodeName(compiledNodeId),
        position,
        lock_level: "editable",
        locale: null,
        data: {
          parent_module: instanceId,
          catalog_preconfigured: true,
          module_instance_id: instanceId,
          catalog_module_id: moduleId,
          catalog_node_id: compiledNodeId,
          node_type: nodeType,
          params,
          fields: Array.isArray(params.fields) ? clonePersistenceValue(params.fields) : [],
          outputs,
          metadata,
          i18n_keys: i18nKeys,
        },
        input_schema: [],
        output_schema: [],
        ports: {
          inputs: [{ port_id: "p_in", name: "in", direction: "in" }],
          outputs: [{ port_id: "p_out", name: "out", direction: "out" }],
        },
        validation: null,
        layer_id: layerId,
        module_id: moduleId,
        i18n_keys: Object.fromEntries(Object.entries(i18nKeys).map(([key, value]) => [key, String(value)])),
        collapsed_sections:
          nodeType === "reference_input" || nodeType === "reference_output"
            ? ["core", "advanced", "runtime"]
            : ["advanced", "runtime"],
      };
    });
    const edges = compiledEdges.map((edge, index) => {
      const compiledSource = String(edge.source || edge.source_node_id || "");
      const compiledTarget = String(edge.target || edge.target_node_id || "");
      const source = editorNodeIdByCompiledId.get(compiledSource) || recoveredNodeId(instanceId, compiledSource);
      const target = editorNodeIdByCompiledId.get(compiledTarget) || recoveredNodeId(instanceId, compiledTarget);
      const edgeId = String(edge.edge_id || edge.id || `${source}_to_${target}_${index + 1}`);
      const sourcePort = String(edge.source_port || edge.source_output || "p_out");
      const targetPort = String(edge.target_port || edge.target_input || "p_in");
      return {
        edge_id: edgeId,
        id: edgeId,
        source,
        source_port: sourcePort,
        sourceHandle: sourcePort,
        target,
        target_port: targetPort,
        targetHandle: targetPort,
        type: "smoothstep",
      };
    });
    state.moduleGraphs[instanceId] = { moduleId: instanceId, nodes, edges };
  }

  return attachedModuleIdsFromLayerModules(state.layerModules).length > 0 ? state : null;
}

function isQuotaExceededError(error: unknown): boolean {
  return (
    error instanceof DOMException &&
    (error.name === "QuotaExceededError" || error.name === "NS_ERROR_DOM_QUOTA_REACHED")
  );
}

function removeModuleGraphBackups(): number {
  if (typeof window === "undefined") {
    return 0;
  }

  const keys: string[] = [];
  for (let index = 0; index < window.localStorage.length; index += 1) {
    const key = window.localStorage.key(index);
    if (key?.startsWith(MODULE_GRAPH_BACKUP_KEY_PREFIX)) {
      keys.push(key);
    }
  }

  for (const key of keys) {
    window.localStorage.removeItem(key);
  }

  return keys.length;
}

function removeModuleGraphBackupsForModule(moduleId: string): number {
  if (typeof window === "undefined") {
    return 0;
  }

  const prefix = `${MODULE_GRAPH_BACKUP_KEY_PREFIX}${moduleId}_`;
  const keys: string[] = [];
  for (let index = 0; index < window.localStorage.length; index += 1) {
    const key = window.localStorage.key(index);
    if (key?.startsWith(prefix)) {
      keys.push(key);
    }
  }

  for (const key of keys) {
    window.localStorage.removeItem(key);
  }

  return keys.length;
}

function compactLegacyCanvasState(): boolean {
  if (typeof window === "undefined") {
    return false;
  }

  const existing = window.localStorage.getItem(CANVAS_STATE_KEY);
  if (!existing) {
    return false;
  }

  try {
    const parsed = JSON.parse(existing) as Partial<CanvasState>;
    if (!parsed.moduleGraphs || Object.keys(parsed.moduleGraphs).length === 0) {
      return false;
    }

    window.localStorage.setItem(
      CANVAS_STATE_KEY,
      JSON.stringify({
        ...parsed,
        moduleGraphs: {},
        timestamp: new Date().toISOString(),
      })
    );
    return true;
  } catch (error) {
    console.warn("Failed to compact legacy canvas state:", error);
    return false;
  }
}

function setLocalStorageWithBackupPrune(key: string, value: string): boolean {
  try {
    window.localStorage.setItem(key, value);
    return true;
  } catch (error) {
    if (!isQuotaExceededError(error)) {
      throw error;
    }

    const removed = removeModuleGraphBackups();
    if (removed > 0) {
      window.localStorage.setItem(key, value);
      return true;
    }

    if (compactLegacyCanvasState()) {
      window.localStorage.setItem(key, value);
      return true;
    }

    throw error;
  }
}

/**
 * 创建空的 Canvas 状态
 */
export function createEmptyCanvasState(): CanvasState {
  return {
    version: "v4",
    timestamp: new Date().toISOString(),
    moduleTabs: [],
    moduleNames: {},
    uiNodeNames: {},
    uiTags: {},
    uiGroups: {},
    uiColors: {},
    moduleUiColors: {},
    layerModules: {},
    moduleInstanceRegistry: {},
    moduleGraphs: {},
  };
}

/**
 * 序列化 Canvas 状态
 */
export function serializeCanvasState(state: Partial<CanvasState>): CanvasState {
  return {
    version: "v4",
    timestamp: new Date().toISOString(),
    moduleTabs: state.moduleTabs ?? [],
    moduleNames: state.moduleNames ?? {},
    uiNodeNames: state.uiNodeNames ?? {},
    uiTags: state.uiTags ?? {},
    uiGroups: state.uiGroups ?? {},
    uiColors: state.uiColors ?? {},
    moduleUiColors: state.moduleUiColors ?? {},
    layerModules: state.layerModules ?? {},
    moduleInstanceRegistry: state.moduleInstanceRegistry ?? {},
    moduleGraphs: state.moduleGraphs ?? {},
    viewport: state.viewport,
  };
}

/**
 * 反序列化 Canvas 状态别名
 */
export const deserializeCanvasState = serializeCanvasState;

/**
 * 验证 Canvas 状态
 */
export function validateCanvasState(data: unknown): data is CanvasState {
  if (!data || typeof data !== "object") {
    return false;
  }

  const obj = data as Record<string, unknown>;
  
  // 检查必需字段
  if (obj.version !== "v4") {
    console.warn(`Invalid canvas state version: ${obj.version}`);
    return false;
  }

  if (typeof obj.timestamp !== "string") {
    console.warn("Missing or invalid timestamp");
    return false;
  }

  // 检查数据类型
  if (!Array.isArray(obj.moduleTabs)) {
    return false;
  }

  if (typeof obj.moduleNames !== "object" || obj.moduleNames === null) {
    return false;
  }

  if (typeof obj.layerModules !== "object" || obj.layerModules === null) {
    return false;
  }

  if (typeof obj.moduleInstanceRegistry !== "object" || obj.moduleInstanceRegistry === null) {
    return false;
  }

  return true;
}

/**
 * 保存 Canvas 状态到 localStorage
 */
export function saveCanvasStateToLocalStorage(state: CanvasState): boolean {
  if (typeof window === "undefined") {
    return false;
  }

  try {
    setLocalStorageWithBackupPrune(CANVAS_STATE_KEY, JSON.stringify(state));
    return true;
  } catch (error) {
    console.error("Failed to save canvas state to localStorage:", error);
    return false;
  }
}

/**
 * 从 localStorage 加载 Canvas 状态
 */
export function loadCanvasStateFromLocalStorage(): CanvasState | null {
  if (typeof window === "undefined") {
    return null;
  }

  try {
    const stored = window.localStorage.getItem(CANVAS_STATE_KEY);
    if (!stored) {
      return null;
    }

    const parsed = JSON.parse(stored);
    if (!validateCanvasState(parsed)) {
      console.warn("Invalid canvas state in localStorage");
      return null;
    }

    return parsed;
  } catch (error) {
    console.error("Failed to load canvas state from localStorage:", error);
    return null;
  }
}

/**
 * 清除 Canvas 状态（可选）
 */
export function clearCanvasStateFromLocalStorage(): void {
  if (typeof window === "undefined") {
    return;
  }

  try {
    window.localStorage.removeItem(CANVAS_STATE_KEY);
  } catch (error) {
    console.error("Failed to clear canvas state from localStorage:", error);
  }
}

/**
 * 导出 Canvas 状态为 JSON 文件
 */
export function downloadCanvasState(state: CanvasState): void {
  if (typeof window === "undefined") {
    return;
  }

  try {
    const json = JSON.stringify(state, null, 2);
    const blob = new Blob([json], { type: "application/json;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    
    const link = document.createElement("a");
    const timestamp = new Date().toISOString().replace(/[:.]/g, "-").slice(0, -5);
    link.href = url;
    link.download = `${EXPORT_FILE_PREFIX}${timestamp}.json`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  } catch (error) {
    console.error("Failed to download canvas state:", error);
  }
}

/**
 * 从文件内容导入 Canvas 状态
 */
export function importCanvasState(fileContent: string): { success: boolean; state?: CanvasState; error?: string } {
  try {
    const parsed = JSON.parse(fileContent);

    const recovered = recoverCanvasStateFromDigitalResident(parsed);
    if (recovered) {
      return { success: true, state: recovered };
    }

    if (validateCanvasState(parsed)) {
      return {
        success: true,
        state: serializeCanvasState(parsed),
      };
    }

    return {
      success: false,
      error: "Canvas 状态或 DR 格式无效",
    };
  } catch (error) {
    return {
      success: false,
      error: `解析文件失败: ${error instanceof Error ? error.message : "未知错误"}`,
    };
  }
}

/**
 * 从文件对象读取并导入 Canvas 状态
 */
export function readCanvasStateFromFile(file: File): Promise<{ success: boolean; state?: CanvasState; error?: string }> {
  return new Promise((resolve) => {
    const reader = new FileReader();
    
    reader.onload = (event) => {
      const content = event.target?.result;
      if (typeof content === "string") {
        resolve(importCanvasState(content));
      } else {
        resolve({
          success: false,
          error: "读取文件失败",
        });
      }
    };
    
    reader.onerror = () => {
      resolve({
        success: false,
        error: "读取文件失败",
      });
    };
    
    reader.readAsText(file);
  });
}

/**
 * 保存模块内画布图 (nodes + edges) 到 localStorage
 */
export function saveModuleGraphState(moduleId: string, nodes: unknown[], edges: unknown[]): boolean {
  if (typeof window === "undefined") {
    return false;
  }

  try {
    const key = `${MODULE_GRAPH_KEY_PREFIX}${moduleId}`;
    const nextValue = JSON.stringify({ moduleId, nodes, edges });
    setLocalStorageWithBackupPrune(key, nextValue);
    removeModuleGraphBackupsForModule(moduleId);
    return true;
  } catch (error) {
    console.error(`Failed to save module graph for ${moduleId}:`, error);
    return false;
  }
}

/**
 * 从 localStorage 加载模块内画布图
 */
export function loadModuleGraphState(moduleId: string): ModuleGraphState | null {
  if (typeof window === "undefined") {
    return null;
  }

  try {
    const key = `${MODULE_GRAPH_KEY_PREFIX}${moduleId}`;
    const stored = window.localStorage.getItem(key);
    if (!stored) {
      return null;
    }

    const parsed = JSON.parse(stored) as Partial<ModuleGraphState>;
    if (!Array.isArray(parsed.nodes) || !Array.isArray(parsed.edges)) {
      return null;
    }

    return {
      moduleId,
      nodes: parsed.nodes,
      edges: parsed.edges,
    };
  } catch (error) {
    console.error(`Failed to load module graph for ${moduleId}:`, error);
    return null;
  }
}

export function hasEditorMigrationMarker(marker: string, residentId: string): boolean {
  if (typeof window === "undefined") {
    return false;
  }
  return window.localStorage.getItem(`${EDITOR_MIGRATION_KEY_PREFIX}${marker}:${residentId}`) === "true";
}

export function saveEditorMigrationMarker(marker: string, residentId: string): boolean {
  if (typeof window === "undefined") {
    return false;
  }
  try {
    window.localStorage.setItem(`${EDITOR_MIGRATION_KEY_PREFIX}${marker}:${residentId}`, "true");
    return true;
  } catch (error) {
    console.error(`Failed to save editor migration marker ${marker}:`, error);
    return false;
  }
}
