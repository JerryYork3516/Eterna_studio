import { create } from "zustand";
import type { Language } from "@/i18n";
import type {
  Artifact,
  ExportPreview,
  ResidentStepResponse,
  RunLog,
  TemplateDefinition,
  ValidateResponse,
  Workflow,
  WorkflowEdge,
  WorkflowNode
} from "@/lib/schema-types";
import { hydrateRuntimeResult, type RuntimeDebugSummary } from "@/lib/runtime-hydration";
import { api, type DRCompileResult } from "@/lib/api";
import { sanitizeWorkflow, withUpdatedWorkflowGraph } from "@/lib/workflow";
import { loadWorkflow, saveWorkflow } from "@/lib/persistence";
import { loadCanvasStateFromLocalStorage, saveCanvasStateToLocalStorage } from "@/lib/canvas-persistence";
import type { ModuleGraphState } from "@/lib/canvas-persistence";

type LogLevel = RunLog["level"];

// P1-FIX：规范化 ModuleGraph 类型，替代 unknown[]
export type ModuleGraph = {
  moduleNodeId: string;
  nodes: WorkflowNode[];
  edges: WorkflowEdge[];
  viewport?: { x: number; y: number; zoom: number };
};

// P1-FIX：ModuleGraphs 集合
export type ModuleGraphsState = Record<string, ModuleGraph>;

// P1-FIX：类型转换函数
function convertLegacyModuleGraphs(
  legacyGraphs: Record<string, ModuleGraphState> | Record<string, unknown>
): ModuleGraphsState {
  const result: ModuleGraphsState = {};
  for (const [moduleId, graphData] of Object.entries(legacyGraphs)) {
    try {
      const data = graphData as any;
      if (data && typeof data === 'object') {
        result[moduleId] = {
          moduleNodeId: data.moduleId ?? moduleId,
          nodes: Array.isArray(data.nodes) ? (data.nodes as WorkflowNode[]) : [],
          edges: Array.isArray(data.edges) ? (data.edges as WorkflowEdge[]) : [],
          viewport: data.viewport,
        };
      }
    } catch (e) {
      console.warn(`[P1-STORE] Failed to convert graph for ${moduleId}:`, e);
    }
  }
  return result;
}

function convertModuleGraphsToLegacy(
  graphs: ModuleGraphsState
): Record<string, ModuleGraphState> {
  const result: Record<string, ModuleGraphState> = {};
  for (const [moduleId, graph] of Object.entries(graphs)) {
    result[moduleId] = {
      moduleId,
      nodes: graph.nodes,
      edges: graph.edges,
    };
  }
  return result;
}

type CanvasState = {
  workflow: Workflow | null;
  nodes: WorkflowNode[];
  edges: WorkflowEdge[];
  selectedNodeId: string | null;
  logs: RunLog[];
  artifacts: Artifact[];
  language: Language;
  currentTemplate: string;
  templates: TemplateDefinition[];
  validation: ValidateResponse | null;
  exportPreview: ExportPreview | null;
  apiReady: boolean;

  // Stage 6 Runtime Kernel: last /runtime/resident/step result + its debug summary.
  runtimeResult: ResidentStepResponse | null;
  runtimeDebug: RuntimeDebugSummary | null;

  // Stage 6.3.3 DR compile/export split: the compiled (validated) DR result.
  compiledDR: Record<string, unknown> | null;   // downloadable content (valid only)
  drCompileResult: DRCompileResult | null;        // full compile + audit result
  canExportDR: boolean;                           // true only when valid

  // P1-FIX：Module UI State（从 localStorage 提升到 store）
  moduleTabs: string[];
  activeModuleTabId: string | null;
  moduleNames: Record<string, string>;
  uiNodeNames: Record<string, string>;
  uiTags: Record<string, string[]>;
  uiGroups: Record<string, string>;
  uiColors: Record<string, string>;
  moduleUiColors: Record<string, string>;
  
  // P1-FIX：Module Graph State（规范化）
  moduleGraphs: ModuleGraphsState;
  
  // P1-FIX：Module Instance Registry（从 CanvasShell 提升到 store）
  layerModules: Record<string, string[]>;
  moduleInstanceRegistry: Record<string, { instanceId: string; moduleId: string; layerId: string }>;
  
  // 原有 actions
  setWorkflow: (workflow: Workflow) => void;
  hydrateWorkflow: () => void;
  setSelectedNode: (nodeId: string | null) => void;
  updateNodePosition: (nodeId: string, position: { x: number; y: number }) => void;
  removeEdges: (edgeIds: string[]) => void;
  setLanguage: (language: Language) => void;
  setTemplates: (templates: TemplateDefinition[]) => void;
  setValidation: (validation: ValidateResponse | null) => void;
  setArtifacts: (artifacts: Artifact[]) => void;
  setExportPreview: (preview: ExportPreview | null) => void;
  setApiReady: (ready: boolean) => void;
  appendLog: (message: string, level?: LogLevel) => void;
  clearRunOutput: () => void;
  // Stage 6 Runtime Kernel: hydrate one resident-step response into the panels.
  applyRuntimeResult: (response: ResidentStepResponse) => void;
  // Stage 6.3.3 DR Compile (validate, no download): POST /dr/compile and store
  // the result. Never downloads a file, never touches the runtime.
  compileDR: (workflow: Workflow) => Promise<void>;
  // Stage 6.3.3 DR Export: download the already-validated compiledDR. Blocked
  // unless a valid DR was compiled first.
  exportDR: () => Promise<void>;

  // P1-FIX：Module UI State actions
  setModuleTabs: (tabs: string[]) => void;
  setActiveModuleTabId: (id: string | null) => void;
  openModuleTab: (moduleId: string) => void;
  closeModuleTab: (moduleId: string) => void;
  setModuleNames: (names: Record<string, string>) => void;
  setUiNodeNames: (names: Record<string, string>) => void;
  setUiTags: (tags: Record<string, string[]>) => void;
  setUiGroups: (groups: Record<string, string>) => void;
  setUiColors: (colors: Record<string, string>) => void;
  setModuleUiColors: (colors: Record<string, string>) => void;
  
  // P1-FIX：Module Graph State actions
  setModuleGraphs: (graphs: ModuleGraphsState) => void;
  updateModuleGraph: (moduleNodeId: string, nodes: WorkflowNode[], edges: WorkflowEdge[], viewport?: { x: number; y: number; zoom: number }) => void;
  removeModuleGraph: (moduleNodeId: string) => void;
  
  // P1-FIX：Module Instance Registry actions
  setLayerModules: (layerModules: Record<string, string[]>) => void;
  setModuleInstanceRegistry: (registry: Record<string, { instanceId: string; moduleId: string; layerId: string }>) => void;
  
  // P1-FIX：Hydration and persistence
  hydrateModuleState: () => void;
  persistModuleState: () => void;
};

export const useCanvasStore = create<CanvasState>((set, get) => ({
  workflow: null,
  nodes: [],
  edges: [],
  selectedNodeId: null,
  logs: [],
  artifacts: [],
  language: "zh",
  currentTemplate: "blank",
  templates: [],
  validation: null,
  exportPreview: null,
  apiReady: false,
  runtimeResult: null,
  runtimeDebug: null,
  compiledDR: null,
  drCompileResult: null,
  canExportDR: false,

  // P1-FIX：初始化 Module UI State
  moduleTabs: [],
  activeModuleTabId: null,
  moduleNames: {},
  uiNodeNames: {},
  uiTags: {},
  uiGroups: {},
  uiColors: {},
  moduleUiColors: {},
  
  // P1-FIX：初始化 Module Graph State
  moduleGraphs: {},
  
  // P1-FIX：初始化 Module Instance Registry
  layerModules: {},
  moduleInstanceRegistry: {},
  
  setWorkflow: (workflow) => {
    const safeWorkflow = sanitizeWorkflow(workflow);
    saveWorkflow(safeWorkflow);
    set({
      workflow: safeWorkflow,
      nodes: safeWorkflow.nodes ?? [],
      edges: safeWorkflow.edges ?? [],
      selectedNodeId: null,
      currentTemplate: safeWorkflow.template_type,
      language: safeWorkflow.metadata?.ui_language === "en" ? "en" : "zh"
    });
  },
  hydrateWorkflow: () => {
    if (get().workflow) {
      return;
    }
    const persisted = loadWorkflow();
    if (!persisted) {
      return;
    }
    set({
      workflow: persisted,
      nodes: persisted.nodes ?? [],
      edges: persisted.edges ?? [],
      currentTemplate: persisted.template_type,
      language: persisted.metadata?.ui_language === "en" ? "en" : "zh"
    });
  },
  setSelectedNode: (nodeId) => set({ selectedNodeId: nodeId }),
  updateNodePosition: (nodeId, position) => {
    const nodes = get().nodes.map((node) => (node.node_id === nodeId ? { ...node, position } : node));
    const workflow = get().workflow;
    const safeWorkflow = workflow ? withUpdatedWorkflowGraph(workflow, nodes, get().edges) : workflow;
    if (safeWorkflow) {
      saveWorkflow(safeWorkflow);
    }
    set({
      nodes: safeWorkflow?.nodes ?? nodes,
      edges: safeWorkflow?.edges ?? get().edges,
      workflow: safeWorkflow
    });
  },
  removeEdges: (edgeIds) => {
    if (!edgeIds.length) {
      return;
    }
    const workflow = get().workflow;
    const edges = get().edges.filter((edge) => !edgeIds.includes(edge.edge_id));
    const safeWorkflow = workflow ? withUpdatedWorkflowGraph(workflow, get().nodes, edges) : workflow;
    if (safeWorkflow) {
      saveWorkflow(safeWorkflow);
    }
    set({
      nodes: safeWorkflow?.nodes ?? get().nodes,
      edges: safeWorkflow?.edges ?? edges,
      workflow: safeWorkflow
    });
  },
  setLanguage: (language) => {
    const workflow = get().workflow;
    const nextWorkflow = workflow
      ? sanitizeWorkflow({
          ...workflow,
          metadata: {
            ...workflow.metadata,
            ui_language: language
          }
        })
      : workflow;
    set({
      language,
      workflow: nextWorkflow,
      nodes: nextWorkflow?.nodes ?? get().nodes,
      edges: nextWorkflow?.edges ?? get().edges,
      currentTemplate: nextWorkflow?.template_type ?? get().currentTemplate
    });
  },
  setTemplates: (templates) => set({ templates }),
  setValidation: (validation) => set({ validation }),
  setArtifacts: (artifacts) => set({ artifacts }),
  setExportPreview: (exportPreview) => set({ exportPreview }),
  setApiReady: (apiReady) => set({ apiReady }),
  appendLog: (message, level = "info") =>
    set((state) => ({
      logs: [
        {
          ts: new Date().toISOString(),
          level,
          message
        },
        ...state.logs
      ].slice(0, 80)
    })),
  clearRunOutput: () =>
    set({
      logs: [],
      artifacts: [],
      exportPreview: null,
      validation: null,
      runtimeResult: null,
      runtimeDebug: null,
      compiledDR: null,
      drCompileResult: null,
      canExportDR: false
    }),

  // Stage 6 Runtime Kernel hydration: map the response into the existing panels.
  // execution_trace -> logs, memory_snapshot -> artifacts, status/run_id -> debug.
  applyRuntimeResult: (response) => {
    const hydrated = hydrateRuntimeResult(response);
    // appendLog prepends (newest-first); append in reverse so the run reads
    // top-to-bottom as: header, trace #0..#n, output, memory.
    const appendLog = get().appendLog;
    [...hydrated.logLines].reverse().forEach((line) => appendLog(line.message, line.level));
    set({
      artifacts: hydrated.memoryArtifacts,
      runtimeResult: response,
      runtimeDebug: hydrated.debug
    });
  },

  // Stage 6.3.3 Compile DR: POST /dr/compile (validate, NO download). Saves the
  // compiled DR + audit result; sets canExportDR only when valid. No runtime calls.
  compileDR: async (workflow) => {
    const appendLog = get().appendLog;
    appendLog("DR compile → /dr/compile (validate, no download)");
    try {
      const result: DRCompileResult = await api.compileDR(workflow, workflow.name);
      set({
        compiledDR: result.compiled_dr ?? null,
        drCompileResult: result,
        canExportDR: result.valid && result.compiled_dr != null
      });
      if (result.valid) {
        appendLog(
          `DR compiled OK — orchestration_compatible=${result.orchestration_compatibility}, ready to export ${result.filename}`
        );
      } else {
        appendLog(`DR compile FAILED — ${result.errors.length} error(s); export disabled`, "error");
      }
      result.errors.forEach((e) => appendLog(`  [error] ${e.code}: ${e.message}`, "error"));
      result.warnings.forEach((w) => appendLog(`  [warn] ${w.code}: ${w.message}`, "warn"));
    } catch (error) {
      set({ compiledDR: null, drCompileResult: null, canExportDR: false });
      appendLog(`DR compile failed: ${(error as Error).message}`, "error");
    }
  },

  // Stage 6.3.3 Export .digital_resident: download the already-validated
  // compiledDR. Blocked unless a valid DR was compiled first. No backend call.
  exportDR: async () => {
    const appendLog = get().appendLog;
    const { compiledDR, drCompileResult, canExportDR } = get();
    if (!compiledDR || !drCompileResult || !canExportDR) {
      appendLog("Export blocked: compile a valid DR first.", "warn");
      return;
    }
    const filename = drCompileResult.filename || "digital_resident.digital_resident";
    if (typeof window !== "undefined") {
      const blob = new Blob([JSON.stringify(compiledDR, null, 2)], { type: "application/x-digital-resident" });
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = filename;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      URL.revokeObjectURL(url);
    }
    appendLog(`DR exported: ${filename}`);
  },
  
  // P1-FIX：Module UI State actions
  setModuleTabs: (tabs: string[]) => {
    set({ moduleTabs: tabs });
    console.log("[P1-STORE] setModuleTabs:", { count: tabs.length });
    get().persistModuleState();
  },
  
  setActiveModuleTabId: (id: string | null) => {
    set({ activeModuleTabId: id });
    console.log("[P1-STORE] setActiveModuleTabId:", { id });
  },
  
  openModuleTab: (moduleId: string) => {
    const current = get().moduleTabs;
    if (!current.includes(moduleId)) {
      const next = [...current, moduleId];
      get().setModuleTabs(next);
      console.log("[P1-STORE] openModuleTab: tab added:", { moduleId, totalTabs: next.length });
    } else {
      console.log("[P1-STORE] openModuleTab: tab already exists:", { moduleId });
    }
    get().setActiveModuleTabId(moduleId);
  },
  
  closeModuleTab: (moduleId: string) => {
    const current = get().moduleTabs;
    const next = current.filter((id) => id !== moduleId);
    get().setModuleTabs(next);
    if (get().activeModuleTabId === moduleId) {
      const nextActive = next.length > 0 ? next[next.length - 1] : null;
      get().setActiveModuleTabId(nextActive);
    }
    console.log("[P1-STORE] closeModuleTab: tab closed:", { moduleId, remaining: next.length });
  },
  
  setModuleNames: (names: Record<string, string>) => {
    set({ moduleNames: names });
    get().persistModuleState();
  },
  
  setUiNodeNames: (names: Record<string, string>) => {
    set({ uiNodeNames: names });
    get().persistModuleState();
  },
  
  setUiTags: (tags: Record<string, string[]>) => {
    set({ uiTags: tags });
    get().persistModuleState();
  },
  
  setUiGroups: (groups: Record<string, string>) => {
    set({ uiGroups: groups });
    get().persistModuleState();
  },
  
  setUiColors: (colors: Record<string, string>) => {
    set({ uiColors: colors });
    get().persistModuleState();
  },
  
  setModuleUiColors: (colors: Record<string, string>) => {
    set({ moduleUiColors: colors });
    get().persistModuleState();
  },
  
  // P1-FIX：Module Graph State actions
  setModuleGraphs: (graphs: ModuleGraphsState) => {
    set({ moduleGraphs: graphs });
    console.log("[P1-STORE] setModuleGraphs:", { count: Object.keys(graphs).length });
    get().persistModuleState();
  },
  
  updateModuleGraph: (moduleNodeId: string, nodes: WorkflowNode[], edges: WorkflowEdge[], viewport?: { x: number; y: number; zoom: number }) => {
    const current = get().moduleGraphs;
    const next = {
      ...current,
      [moduleNodeId]: { moduleNodeId, nodes, edges, viewport: viewport ?? current[moduleNodeId]?.viewport }
    };
    set({ moduleGraphs: next });
    console.log("[P1-STORE] updateModuleGraph:", { moduleNodeId, nodeCount: nodes.length, edgeCount: edges.length });
    get().persistModuleState();
  },
  
  removeModuleGraph: (moduleNodeId: string) => {
    const current = get().moduleGraphs;
    const next = { ...current };
    delete next[moduleNodeId];
    set({ moduleGraphs: next });
    console.log("[P1-STORE] removeModuleGraph:", { moduleNodeId });
    get().persistModuleState();
  },
  
  // P1-FIX：Module Instance Registry actions
  setLayerModules: (layerModules: Record<string, string[]>) => {
    set({ layerModules });
    console.log("[P1-STORE] setLayerModules:", { layerCount: Object.keys(layerModules).length });
    get().persistModuleState();
  },
  
  setModuleInstanceRegistry: (registry: Record<string, { instanceId: string; moduleId: string; layerId: string }>) => {
    set({ moduleInstanceRegistry: registry });
    console.log("[P1-STORE] setModuleInstanceRegistry:", { instanceCount: Object.keys(registry).length });
    get().persistModuleState();
  },
  
  // P1-FIX：Hydration and persistence
  hydrateModuleState: () => {
    console.log("[P1-STORE] hydrateModuleState: loading from localStorage");
    const stored = loadCanvasStateFromLocalStorage();
    if (stored) {
      set({
        moduleTabs: stored.moduleTabs ?? [],
        moduleNames: stored.moduleNames ?? {},
        uiNodeNames: stored.uiNodeNames ?? {},
        uiTags: stored.uiTags ?? {},
        uiGroups: stored.uiGroups ?? {},
        uiColors: stored.uiColors ?? {},
        moduleUiColors: stored.moduleUiColors ?? {},
        layerModules: stored.layerModules ?? {},
        moduleInstanceRegistry: stored.moduleInstanceRegistry ?? {},
        moduleGraphs: convertLegacyModuleGraphs(stored.moduleGraphs ?? {}),
      });
      console.log("[P1-STORE] hydrateModuleState: restored", {
        tabCount: stored.moduleTabs?.length ?? 0,
        graphCount: Object.keys(stored.moduleGraphs ?? {}).length,
        instanceCount: Object.keys(stored.moduleInstanceRegistry ?? {}).length,
      });
    } else {
      console.log("[P1-STORE] hydrateModuleState: no stored state found");
    }
  },
  
  persistModuleState: () => {
    const state = get();
    const toSave = {
      version: "v4" as const,
      timestamp: new Date().toISOString(),
      moduleTabs: state.moduleTabs,
      moduleNames: state.moduleNames,
      uiNodeNames: state.uiNodeNames,
      uiTags: state.uiTags,
      uiGroups: state.uiGroups,
      uiColors: state.uiColors,
      moduleUiColors: state.moduleUiColors,
      layerModules: state.layerModules,
      moduleInstanceRegistry: state.moduleInstanceRegistry,
      moduleGraphs: convertModuleGraphsToLegacy(state.moduleGraphs),
    };
    saveCanvasStateToLocalStorage(toSave);
    console.log("[P1-STORE] persistModuleState: saved to localStorage");
  },
}));
