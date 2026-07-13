import { create } from "zustand";
import { translate, type Language } from "@/i18n";
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
import { api, type DRCompileResult, type DRLoadResult, type LLMProfileInput, type LLMProfilesView, type MemoryClearResult, type MemoryViewResult } from "@/lib/api";
import { sanitizeWorkflow, withUpdatedWorkflowGraph } from "@/lib/workflow";
import { loadWorkflow, saveWorkflow } from "@/lib/persistence";
import { loadCanvasStateFromLocalStorage, saveCanvasStateToLocalStorage } from "@/lib/canvas-persistence";
import type { ModuleGraphState } from "@/lib/canvas-persistence";
import { filterDanglingModuleGraphEdges } from "@/store/module-graph-merge";

type LogLevel = RunLog["level"];

function formatMessage(template: string, values: Record<string, string | number | boolean | null | undefined> = {}) {
  return template.replace(/\{(\w+)\}/g, (_match, key: string) => String(values[key] ?? ""));
}

const REFERENCE_POINTER_KEYS = [
  "source_layer_id",
  "source_module_id",
  "source_node_id",
  "source_scope",
  "source_field_paths",
  "reference_type",
  "required",
] as const;

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

function recordValue(value: unknown): Record<string, unknown> {
  return isRecord(value) ? value : {};
}

function arrayValue(value: unknown): unknown[] {
  return Array.isArray(value) ? value : [];
}

function stringValue(value: unknown): string {
  return typeof value === "string" ? value : "";
}

function pickReferencePointer(reference: Record<string, unknown>) {
  const next: Record<string, unknown> = {};
  for (const key of REFERENCE_POINTER_KEYS) {
    if (key in reference) {
      next[key] = reference[key];
    }
  }
  return next;
}

function nodeTypeOf(node: Record<string, unknown>) {
  const data = recordValue(node.data);
  return stringValue(node.node_type) || stringValue(data.node_type) || stringValue(node.type);
}

function nodeIdOf(node: Record<string, unknown>) {
  const data = recordValue(node.data);
  return stringValue(node.node_id) || stringValue(data.node_id) || stringValue(node.id);
}

function nodeNameOf(node: Record<string, unknown>) {
  const data = recordValue(node.data);
  return (
    stringValue(node.name) ||
    stringValue(node.title) ||
    stringValue(data.label) ||
    stringValue(data.title) ||
    stringValue(data.name) ||
    stringValue(data.title_fallback) ||
    nodeIdOf(node)
  );
}

function paramsOf(node: Record<string, unknown>) {
  const data = recordValue(node.data);
  return recordValue(node.params ?? data.params);
}

function auditNodeParams(node: Record<string, unknown>) {
  const params = { ...paramsOf(node) };
  delete params.legacy_fields;
  delete params.legacy_data_fields;
  if (nodeTypeOf(node) !== "reference_input") {
    return params;
  }
  return {
    ...params,
    references: arrayValue(params.references).filter(isRecord).map(pickReferencePointer),
  };
}

function moduleGraphOf(module: Record<string, unknown>) {
  return recordValue(module.module_graph ?? module.graph);
}

function moduleNodesOf(module: Record<string, unknown>) {
  const graph = moduleGraphOf(module);
  return arrayValue(graph.nodes ?? module.nodes).filter(isRecord);
}

function moduleEdgesOf(module: Record<string, unknown>) {
  const graph = moduleGraphOf(module);
  return arrayValue(graph.edges ?? module.edges).filter(isRecord);
}

function auditModuleEdges(module: Record<string, unknown>) {
  const integrity = filterDanglingModuleGraphEdges(
    moduleNodesOf(module).map(nodeIdOf).filter(Boolean),
    moduleEdgesOf(module)
  );
  return integrity.edges.filter(isRecord);
}

function moduleIdOf(module: Record<string, unknown>) {
  return stringValue(module.module_id) || stringValue(module.id);
}

function moduleLayerIdOf(module: Record<string, unknown>) {
  return stringValue(module.layer_id);
}

function moduleNameOf(module: Record<string, unknown>) {
  return stringValue(module.name) || stringValue(module.module_name) || stringValue(module.title) || moduleIdOf(module);
}

function layerIdOf(layer: Record<string, unknown>) {
  return stringValue(layer.layer_id) || stringValue(layer.id);
}

function layerNameOf(layer: Record<string, unknown>) {
  return stringValue(layer.name) || stringValue(layer.layer_name) || stringValue(layer.title) || layerIdOf(layer);
}

function edgeTypeOf(edge: Record<string, unknown>) {
  return stringValue(edge.type) || stringValue(edge.edge_type) || stringValue(edge.kind);
}

function auditResidentName(dr: Record<string, unknown>) {
  const manifest = recordValue(dr.manifest);
  const resident = recordValue(dr.resident);
  const payload = recordValue(dr.payload);
  const residentIdentity = recordValue(payload.resident_identity);
  const residentBlueprint = recordValue(payload.resident_blueprint);
  return (
    stringValue(manifest.resident_name) ||
    stringValue(resident.name) ||
    stringValue(residentIdentity.name) ||
    stringValue(residentBlueprint.resident_name) ||
    "digital_resident"
  );
}

function auditResidentId(dr: Record<string, unknown>) {
  const manifest = recordValue(dr.manifest);
  const resident = recordValue(dr.resident);
  const payload = recordValue(dr.payload);
  const residentIdentity = recordValue(payload.resident_identity);
  return stringValue(manifest.resident_id) || stringValue(resident.resident_id) || stringValue(residentIdentity.resident_id);
}

function auditFilename(name: string) {
  const safeName = name.replace(/[\\/:*?"<>|]+/g, "_").trim() || "digital_resident";
  return `${safeName}.audit.digital_resident.json`;
}

function auditModulesFromDR(dr: Record<string, unknown>) {
  const payload = recordValue(dr.payload);
  return arrayValue(payload.modules ?? dr.modules).filter(isRecord);
}

function auditLayersFromDR(dr: Record<string, unknown>, modules: Record<string, unknown>[]) {
  const payload = recordValue(dr.payload);
  const rawLayers = arrayValue(payload["13_layers_snapshot"] ?? dr["13_layers_snapshot"] ?? payload.layers ?? dr.layers).filter(isRecord);
  const layerMap = new Map<string, { layer_id: string; name: string; module_ids: string[] }>();

  for (const layer of rawLayers) {
    const layerId = layerIdOf(layer);
    if (!layerId) {
      continue;
    }
    const moduleIds = arrayValue(layer.module_ids ?? layer.modules)
      .map((item) => (typeof item === "string" ? item : isRecord(item) ? moduleIdOf(item) : ""))
      .filter(Boolean);
    layerMap.set(layerId, {
      layer_id: layerId,
      name: layerNameOf(layer),
      module_ids: moduleIds,
    });
  }

  for (const module of modules) {
    const layerId = moduleLayerIdOf(module);
    const moduleId = moduleIdOf(module);
    if (!layerId || !moduleId) {
      continue;
    }
    const layer = layerMap.get(layerId) ?? { layer_id: layerId, name: layerId, module_ids: [] };
    if (!layer.module_ids.includes(moduleId)) {
      layer.module_ids.push(moduleId);
    }
    layerMap.set(layerId, layer);
  }

  return Array.from(layerMap.values());
}

function auditReferenceRecords(modules: Record<string, unknown>[]) {
  const references: Record<string, unknown>[] = [];
  for (const module of modules) {
    const targetModuleId = moduleIdOf(module);
    const targetLayerId = moduleLayerIdOf(module);
    for (const node of moduleNodesOf(module)) {
      if (nodeTypeOf(node) !== "reference_input") {
        continue;
      }
      const params = paramsOf(node);
      for (const reference of arrayValue(params.references).filter(isRecord)) {
        references.push({
          target_layer_id: targetLayerId,
          target_module_id: targetModuleId,
          target_node_id: nodeIdOf(node),
          ...pickReferencePointer(reference),
        });
      }
    }
  }
  return references;
}

function buildAuditDR(compiledDR: Record<string, unknown>, result: DRCompileResult | null) {
  const modules = auditModulesFromDR(compiledDR);
  return {
    schema_version: compiledDR.schema_version ?? compiledDR.dr_version ?? result?.dr_version ?? null,
    resident_id: auditResidentId(compiledDR),
    resident_name: auditResidentName(compiledDR),
    layers: auditLayersFromDR(compiledDR, modules),
    modules: modules.map((module) => ({
      module_id: moduleIdOf(module),
      layer_id: moduleLayerIdOf(module),
      name: moduleNameOf(module),
      nodes: moduleNodesOf(module).map((node) => ({
        node_id: nodeIdOf(node),
        node_type: nodeTypeOf(node),
        name: nodeNameOf(node),
        params: auditNodeParams(node),
      })),
      edges: auditModuleEdges(module).map((edge) => ({
        source: edge.source,
        target: edge.target,
        type: edgeTypeOf(edge),
      })),
    })),
    references: auditReferenceRecords(modules),
    validation_result: result
      ? {
          valid: result.valid,
          dr_version: result.dr_version,
          errors: result.errors,
          warnings: result.warnings,
          orchestration_compatibility: result.orchestration_compatibility,
        }
      : null,
  };
}

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
  // Stage 6.4 Runtime Load DR: last /runtime/resident/load-dr response.
  loadedDRResult: DRLoadResult | null;
  previewLoadStatus: "idle" | "loading" | "success" | "error";
  previewLoadError: string | null;

  // Stage 6.6 real LLM v2: masked runtime profiles view + test state.
  llmProfiles: LLMProfilesView | null;
  llmTestStatus: "idle" | "testing" | "success" | "error";
  llmTestMessage: string | null;

  // Stage 6.7 Memory Module v1: last memory view + clear result + load status.
  memoryView: MemoryViewResult | null;
  memoryClearResult: MemoryClearResult | null;
  memoryStatus: "idle" | "loading" | "success" | "error";

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
  // Audit-only DR export: a compact JSON view for humans/AI review. Not loadable
  // by Aftelle and does not change the official DR contract.
  exportAuditDR: () => Promise<void>;
  // Stage 6.4 Runtime Load DR: read a .digital_resident file and run mock loop.
  loadDRFile: (file: File) => Promise<void>;
  // Stage 6 preview flow: load the already compiled .digital_resident payload
  // into the mock runtime without exporting/importing it first.
  loadCompiledDRToPreview: () => Promise<void>;
  // Stage 6.6 real LLM v2: runtime profile actions.
  loadLLMConfig: () => Promise<void>;
  saveLLMConfig: (config: LLMProfileInput) => Promise<void>;
  testLLMConnection: (config?: LLMProfileInput) => Promise<void>;
  // Stage 6.7 memory viewer / clear.
  viewMemory: (residentId: string, namespace?: string, memoryType?: string, limit?: number) => Promise<MemoryViewResult | null>;
  clearMemory: (residentId: string, namespace?: string, memoryType?: string) => Promise<MemoryClearResult | null>;

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
  loadedDRResult: null,
  previewLoadStatus: "idle",
  previewLoadError: null,
  llmProfiles: null,
  llmTestStatus: "idle",
  llmTestMessage: null,
  memoryView: null,
  memoryClearResult: null,
  memoryStatus: "idle",

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
      canExportDR: false,
      loadedDRResult: null,
      previewLoadStatus: "idle",
      previewLoadError: null,
      memoryView: null,
      memoryClearResult: null
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
    const t = (key: string, fallback?: string, values?: Record<string, string | number | boolean | null | undefined>) =>
      formatMessage(translate(get().language, key, fallback), values);
    const auditMessage = (code: string, message: string) => translate(get().language, `audit.${code}`, message);
    // Clear any previously compiled DR first so a stale payload can never be
    // exported after a recompile (or while the new compile is in flight).
    set({ compiledDR: null, drCompileResult: null, canExportDR: false });
    appendLog(t("status.drCompile.started", "DR compile -> /dr/compile (validate, no download)"));
    try {
      const result: DRCompileResult = await api.compileDR(workflow, workflow.name);
      set({
        compiledDR: result.compiled_dr ?? null,
        drCompileResult: result,
        canExportDR: result.valid && result.compiled_dr != null
      });
      if (result.valid) {
        appendLog(
          t("status.drCompile.ok", "DR compiled OK - dr_version={version}, orchestration_compatible={compatible}, ready to export {filename}", {
            version: result.dr_version,
            compatible: result.orchestration_compatibility,
            filename: result.filename
          })
        );
      } else {
        appendLog(
          t("status.drCompile.failed", "DR compile FAILED (dr_version={version}) - {count} error(s); export disabled", {
            version: result.dr_version,
            count: result.errors.length
          }),
          "error"
        );
      }
      result.errors.forEach((e) => appendLog(t("status.drCompile.errorFinding", "  [error] {code}: {message}", { code: e.code, message: auditMessage(e.code, e.message) }), "error"));
      result.warnings.forEach((w) => appendLog(t("status.drCompile.warningFinding", "  [warn] {code}: {message}", { code: w.code, message: auditMessage(w.code, w.message) }), "warn"));
    } catch (error) {
      set({ compiledDR: null, drCompileResult: null, canExportDR: false });
      appendLog(t("status.drCompile.exception", "DR compile failed: {message}", { message: (error as Error).message }), "error");
    }
  },

  // Stage 6.3.3 Export .digital_resident: download the already-validated
  // compiledDR. Blocked unless a valid DR was compiled first. No backend call.
  exportDR: async () => {
    const appendLog = get().appendLog;
    const t = (key: string, fallback?: string, values?: Record<string, string | number | boolean | null | undefined>) =>
      formatMessage(translate(get().language, key, fallback), values);
    const { compiledDR, drCompileResult, canExportDR } = get();
    if (!compiledDR || !drCompileResult || !canExportDR) {
      appendLog(t("status.drExport.blocked", "Export blocked: compile a valid DR first."), "warn");
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
    appendLog(t("status.drExport.ok", "DR exported: {filename} (dr_version={version})", { filename, version: drCompileResult.dr_version }));
  },

  exportAuditDR: async () => {
    const appendLog = get().appendLog;
    const t = (key: string, fallback?: string, values?: Record<string, string | number | boolean | null | undefined>) =>
      formatMessage(translate(get().language, key, fallback), values);
    const { compiledDR, drCompileResult, canExportDR } = get();
    if (!compiledDR || !drCompileResult || !canExportDR) {
      appendLog(t("status.drAuditExport.blocked", "Audit export blocked: compile a valid DR first."), "warn");
      return;
    }
    const auditDR = buildAuditDR(compiledDR, drCompileResult);
    const filename = auditFilename(auditDR.resident_name);
    if (typeof window !== "undefined") {
      const blob = new Blob([JSON.stringify(auditDR, null, 2)], { type: "application/json;charset=utf-8" });
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = filename;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      URL.revokeObjectURL(url);
    }
    appendLog(t("status.drAuditExport.ok", "Audit DR exported: {filename}", { filename }));
  },

  // Stage 6.4 Load .digital_resident: the browser reads the JSON file, then the
  // backend validates and runs the existing mock runtime loop. No multipart or
  // real provider is introduced here.
  loadDRFile: async (file) => {
    const appendLog = get().appendLog;
    const t = (key: string, fallback?: string, values?: Record<string, string | number | boolean | null | undefined>) =>
      formatMessage(translate(get().language, key, fallback), values);
    const auditMessage = (code: string, message: string) => translate(get().language, `audit.${code}`, message);
    set({ loadedDRResult: null });
    appendLog(t("status.drLoad.fileStarted", "Load DR -> /runtime/resident/load-dr ({filename})", { filename: file.name }));
    try {
      const parsed = JSON.parse(await file.text()) as Record<string, unknown>;
      const result: DRLoadResult = await api.loadDigitalResident(parsed, `Load DR: ${file.name}`);
      set({ loadedDRResult: result });
      if (result.loaded) {
        appendLog(t("status.drLoad.ok", "DR loaded OK - resident={resident}, dr_version={version}", { resident: result.resident_id, version: result.dr_version ?? "unknown" }));
        get().applyRuntimeResult(result);
      } else {
        const validation = result.validation_result;
        appendLog(
          t("status.drLoad.rejected", "DR load rejected - dr_version={version} - {count} error(s)", {
            version: result.dr_version ?? validation.dr_version ?? "unknown",
            count: validation.errors.length
          }),
          "error"
        );
        validation.errors.forEach((e) => appendLog(t("status.drCompile.errorFinding", "  [error] {code}: {message}", { code: e.code, message: auditMessage(e.code, e.message) }), "error"));
        validation.warnings.forEach((w) => appendLog(t("status.drCompile.warningFinding", "  [warn] {code}: {message}", { code: w.code, message: auditMessage(w.code, w.message) }), "warn"));
      }
    } catch (error) {
      set({ loadedDRResult: null });
      appendLog(t("status.drLoad.failed", "DR load failed: {message}", { message: (error as Error).message }), "error");
    }
  },

  // Stage 6 preview shortcut: compiledDR -> /runtime/resident/load-dr. Export
  // remains download-only; local Load File remains file-picker-only.
  loadCompiledDRToPreview: async () => {
    const appendLog = get().appendLog;
    const t = (key: string, fallback?: string, values?: Record<string, string | number | boolean | null | undefined>) =>
      formatMessage(translate(get().language, key, fallback), values);
    const auditMessage = (code: string, message: string) => translate(get().language, `audit.${code}`, message);
    const { compiledDR, drCompileResult, canExportDR } = get();
    if (!compiledDR || !drCompileResult || !canExportDR) {
      set({
        previewLoadStatus: "error",
        previewLoadError: t("preview.loadCompiledBlocked", "Compile a valid file first."),
        loadedDRResult: null
      });
      appendLog(t("status.drLoad.previewBlocked", "Preview load blocked: compile a valid file first."), "warn");
      return;
    }
    set({ loadedDRResult: null, previewLoadStatus: "loading", previewLoadError: null });
    appendLog(t("status.drLoad.previewStarted", "Load compiled file -> /runtime/resident/load-dr ({filename})", { filename: drCompileResult.filename }));
    try {
      const result: DRLoadResult = await api.loadCompiledDigitalResident(compiledDR, drCompileResult.filename);
      set({ loadedDRResult: result, previewLoadStatus: result.loaded ? "success" : "error", previewLoadError: null });
      if (result.loaded) {
        appendLog(t("status.drLoad.ok", "DR loaded OK - resident={resident}, dr_version={version}", { resident: result.resident_id, version: result.dr_version ?? "unknown" }));
        get().applyRuntimeResult(result);
      } else {
        const validation = result.validation_result;
        set({ previewLoadError: validation.errors.map((e) => `${e.code}: ${auditMessage(e.code, e.message)}`).join("\n") || t("preview.loadFailed", "Load failed.") });
        appendLog(
          t("status.drLoad.rejected", "DR load rejected - dr_version={version} - {count} error(s)", {
            version: result.dr_version ?? validation.dr_version ?? "unknown",
            count: validation.errors.length
          }),
          "error"
        );
        validation.errors.forEach((e) => appendLog(t("status.drCompile.errorFinding", "  [error] {code}: {message}", { code: e.code, message: auditMessage(e.code, e.message) }), "error"));
        validation.warnings.forEach((w) => appendLog(t("status.drCompile.warningFinding", "  [warn] {code}: {message}", { code: w.code, message: auditMessage(w.code, w.message) }), "warn"));
      }
    } catch (error) {
      set({ loadedDRResult: null, previewLoadStatus: "error", previewLoadError: (error as Error).message });
      appendLog(t("status.drLoad.failed", "DR load failed: {message}", { message: (error as Error).message }), "error");
    }
  },

  // Stage 6.6 — fetch the masked runtime profiles (no raw api_key ever returned).
  loadLLMConfig: async () => {
    try {
      const cfg = await api.getLLMConfig();
      set({ llmProfiles: cfg });
    } catch {
      // Non-fatal: leave llmProfiles as-is; the form falls back to empty values.
    }
  },

  // Stage 6.6 — save one runtime profile to the backend Runtime Config.
  saveLLMConfig: async (config) => {
    const appendLog = get().appendLog;
    try {
      const saved = await api.saveLLMConfig(config);
      set({ llmProfiles: saved });
      const profile = saved.profiles?.[config.profile_id];
      appendLog(
        `LLM profile saved — profile=${config.profile_id}, provider=${profile?.provider || config.provider || "(none)"}, model=${profile?.model || config.model || "(none)"}, enabled=${profile?.enabled ?? config.enabled ?? false}`
      );
    } catch (error) {
      appendLog(`LLM profile save failed: ${(error as Error).message}`, "error");
    }
  },

  // Stage 6.6 — test a runtime profile via the backend (real call is backend-only).
  testLLMConnection: async (config) => {
    const appendLog = get().appendLog;
    set({ llmTestStatus: "testing", llmTestMessage: null });
    appendLog("LLM test connection → /runtime/config/llm/test");
    try {
      const result = await api.testLLMConnection(config);
      if (result.ok) {
        set({ llmTestStatus: "success", llmTestMessage: result.sample ?? "" });
        appendLog(`LLM connection OK — provider=${result.provider ?? "?"}, model=${result.model ?? "?"} · ${(result.sample ?? "").slice(0, 80)}`);
      } else {
        set({ llmTestStatus: "error", llmTestMessage: result.error ?? "failed" });
        appendLog(`LLM connection FAILED — ${result.error ?? "unknown error"}`, "error");
      }
    } catch (error) {
      set({ llmTestStatus: "error", llmTestMessage: (error as Error).message });
      appendLog(`LLM connection error: ${(error as Error).message}`, "error");
    }
  },

  // Stage 6.7 — view a resident's memory (read-only) via the backend.
  viewMemory: async (residentId, namespace = "default", memoryType = "interaction_log", limit = 20) => {
    const appendLog = get().appendLog;
    set({ memoryStatus: "loading" });
    try {
      const result = await api.memoryView(residentId, namespace, memoryType, limit);
      const entries = result.entries ?? result.items ?? [];
      const normalized = { ...result, entries, items: result.items ?? entries };
      set({ memoryView: normalized, memoryStatus: "success" });
      appendLog(`Memory view → ${normalized.count} record(s) [${normalized.storage_backend}]`);
      return normalized;
    } catch (error) {
      set({ memoryStatus: "error" });
      appendLog(`Memory view error: ${(error as Error).message}`, "error");
      return null;
    }
  },

  // Stage 6.7 — clear a resident's memory, then refresh the view.
  clearMemory: async (residentId, namespace = "default", memoryType = "interaction_log") => {
    const appendLog = get().appendLog;
    set({ memoryStatus: "loading" });
    try {
      const result = await api.memoryClear(residentId, namespace, memoryType);
      set({ memoryClearResult: result });
      appendLog(`Memory clear → deleted ${result.deleted_count} record(s)`);
      const view = await api.memoryView(residentId, namespace, memoryType, 20);
      const entries = view.entries ?? view.items ?? [];
      const normalized = { ...view, entries, items: view.items ?? entries };
      set({ memoryView: normalized, memoryStatus: "success" });
      return result;
    } catch (error) {
      set({ memoryStatus: "error" });
      appendLog(`Memory clear error: ${(error as Error).message}`, "error");
      return null;
    }
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
      moduleGraphs: {},
    };
    const saved = saveCanvasStateToLocalStorage(toSave);
    console.log(saved ? "[P1-STORE] persistModuleState: saved to localStorage" : "[P1-STORE] persistModuleState: save skipped");
  },
}));
