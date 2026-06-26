/**
 * 画布持久化工具库
 * 支持序列化/反序列化/导出/导入 CanvasState
 */

export interface ModuleInstance {
  instanceId: string;
  moduleId: string;
  layerId: string;
}

export interface CanvasState {
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
}

/**
 * 验证 CanvasState 数据结构完整性
 */
export function validateCanvasState(state: unknown): state is CanvasState {
  if (!state || typeof state !== "object") {
    return false;
  }

  const s = state as Record<string, unknown>;

  // 检查必要字段
  if (s.version !== "v4" || typeof s.timestamp !== "string") {
    return false;
  }

  // 检查 UI 状态字段类型
  if (
    !Array.isArray(s.moduleTabs) ||
    typeof s.moduleNames !== "object" ||
    typeof s.uiNodeNames !== "object" ||
    typeof s.uiTags !== "object" ||
    typeof s.uiGroups !== "object" ||
    typeof s.uiColors !== "object" ||
    typeof s.moduleUiColors !== "object"
  ) {
    return false;
  }

  // 检查模块状态字段类型
  if (typeof s.layerModules !== "object" || typeof s.moduleInstanceRegistry !== "object") {
    return false;
  }

  return true;
}

/**
 * 序列化 CanvasState 为 JSON 字符串
 */
export function serializeCanvasState(state: CanvasState): string {
  return JSON.stringify(state, null, 2);
}

/**
 * 反序列化 JSON 字符串为 CanvasState
 * 失败时返回 null 并记录错误
 */
export function deserializeCanvasState(jsonString: string): CanvasState | null {
  try {
    const parsed = JSON.parse(jsonString);
    if (validateCanvasState(parsed)) {
      return parsed;
    }
    console.error("Invalid CanvasState structure:", parsed);
    return null;
  } catch (error) {
    console.error("Failed to parse CanvasState JSON:", error);
    return null;
  }
}

/**
 * 从 File 对象读取 CanvasState
 */
export async function readCanvasStateFromFile(file: File): Promise<CanvasState | null> {
  try {
    const text = await file.text();
    return deserializeCanvasState(text);
  } catch (error) {
    console.error("Failed to read CanvasState from file:", error);
    return null;
  }
}

/**
 * 生成 CanvasState 文件并下载
 */
export function downloadCanvasState(state: CanvasState): void {
  try {
    const json = serializeCanvasState(state);
    const blob = new Blob([json], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    
    // 文件名格式: eterna_canvas_{YYYYMMDD_HHmmss}.json
    const now = new Date(state.timestamp);
    const year = now.getFullYear();
    const month = String(now.getMonth() + 1).padStart(2, "0");
    const day = String(now.getDate()).padStart(2, "0");
    const hours = String(now.getHours()).padStart(2, "0");
    const minutes = String(now.getMinutes()).padStart(2, "0");
    const seconds = String(now.getSeconds()).padStart(2, "0");
    
    link.href = url;
    link.download = `eterna_canvas_${year}${month}${day}_${hours}${minutes}${seconds}.json`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  } catch (error) {
    console.error("Failed to download CanvasState:", error);
  }
}

/**
 * 保存 CanvasState 到 localStorage
 * 键名: eterna_canvas_v4
 */
export function saveCanvasStateToLocalStorage(state: CanvasState): boolean {
  if (typeof window === "undefined") {
    return false;
  }

  try {
    const json = serializeCanvasState(state);
    window.localStorage.setItem("eterna_canvas_v4", json);
    return true;
  } catch (error) {
    console.error("Failed to save CanvasState to localStorage:", error);
    return false;
  }
}

/**
 * 从 localStorage 加载 CanvasState
 */
export function loadCanvasStateFromLocalStorage(): CanvasState | null {
  if (typeof window === "undefined") {
    return null;
  }

  try {
    const json = window.localStorage.getItem("eterna_canvas_v4");
    if (!json) {
      return null;
    }
    return deserializeCanvasState(json);
  } catch (error) {
    console.error("Failed to load CanvasState from localStorage:", error);
    return null;
  }
}

/**
 * 清除 localStorage 中的 CanvasState
 */
export function clearCanvasStateFromLocalStorage(): void {
  if (typeof window === "undefined") {
    return;
  }

  try {
    window.localStorage.removeItem("eterna_canvas_v4");
  } catch (error) {
    console.error("Failed to clear CanvasState from localStorage:", error);
  }
}

/**
 * 创建新的空 CanvasState
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
  };
}

/**
 * 合并两个 CanvasState（用于导入时覆盖）
 * 后者覆盖前者的所有字段
 */
export function mergeCanvasState(base: CanvasState, override: CanvasState): CanvasState {
  return {
    version: "v4",
    timestamp: new Date().toISOString(),
    moduleTabs: override.moduleTabs ?? base.moduleTabs,
    moduleNames: { ...base.moduleNames, ...override.moduleNames },
    uiNodeNames: { ...base.uiNodeNames, ...override.uiNodeNames },
    uiTags: { ...base.uiTags, ...override.uiTags },
    uiGroups: { ...base.uiGroups, ...override.uiGroups },
    uiColors: { ...base.uiColors, ...override.uiColors },
    moduleUiColors: { ...base.moduleUiColors, ...override.moduleUiColors },
    layerModules: { ...base.layerModules, ...override.layerModules },
    moduleInstanceRegistry: { ...base.moduleInstanceRegistry, ...override.moduleInstanceRegistry },
  };
}
