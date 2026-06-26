/**
 * Canvas 状态持久化工具
 * 支持自动保存到 localStorage 和手动导出/导入 JSON 文件
 */

export type ModuleInstance = {
  instanceId: string;
  moduleId: string;
  layerId: string;
};

export type ModuleGraphState = {
  moduleId: string;
  nodes: unknown[];
  edges: unknown[];
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
    window.localStorage.setItem(CANVAS_STATE_KEY, JSON.stringify(state));
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
    
    if (!validateCanvasState(parsed)) {
      return {
        success: false,
        error: "Canvas 状态格式无效",
      };
    }

    return {
      success: true,
      state: parsed,
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
    const key = `module_graph_${moduleId}`;
    window.localStorage.setItem(
      key,
      JSON.stringify({ moduleId, nodes, edges })
    );
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
    const key = `module_graph_${moduleId}`;
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
