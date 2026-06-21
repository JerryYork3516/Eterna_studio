import { create } from "zustand";
import type { Language } from "@/i18n";
import type {
  Artifact,
  ExportPreview,
  RunLog,
  TemplateDefinition,
  ValidateResponse,
  Workflow,
  WorkflowEdge,
  WorkflowNode
} from "@/lib/schema-types";
import { sanitizeWorkflow, withUpdatedWorkflowGraph } from "@/lib/workflow";

type LogLevel = RunLog["level"];

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
  setWorkflow: (workflow: Workflow) => void;
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
  setWorkflow: (workflow) => {
    const safeWorkflow = sanitizeWorkflow(workflow);
    set({
      workflow: safeWorkflow,
      nodes: safeWorkflow.nodes ?? [],
      edges: safeWorkflow.edges ?? [],
      selectedNodeId: null,
      currentTemplate: safeWorkflow.template_type,
      language: safeWorkflow.metadata?.ui_language === "en" ? "en" : "zh"
    });
  },
  setSelectedNode: (nodeId) => set({ selectedNodeId: nodeId && get().nodes.some((node) => node.node_id === nodeId) ? nodeId : null }),
  updateNodePosition: (nodeId, position) => {
    const nodes = get().nodes.map((node) => (node.node_id === nodeId ? { ...node, position } : node));
    const workflow = get().workflow;
    const safeWorkflow = workflow ? withUpdatedWorkflowGraph(workflow, nodes, get().edges) : workflow;
    set({
      nodes: safeWorkflow?.nodes ?? nodes,
      edges: safeWorkflow?.edges ?? get().edges,
      workflow: safeWorkflow,
      selectedNodeId: get().selectedNodeId && nodes.some((node) => node.node_id === get().selectedNodeId) ? get().selectedNodeId : null
    });
  },
  removeEdges: (edgeIds) => {
    if (!edgeIds.length) {
      return;
    }
    const workflow = get().workflow;
    const edges = get().edges.filter((edge) => !edgeIds.includes(edge.edge_id));
    const safeWorkflow = workflow ? withUpdatedWorkflowGraph(workflow, get().nodes, edges) : workflow;
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
      currentTemplate: nextWorkflow?.template_type ?? get().currentTemplate,
      selectedNodeId:
        get().selectedNodeId && (nextWorkflow?.nodes ?? get().nodes).some((node) => node.node_id === get().selectedNodeId)
          ? get().selectedNodeId
          : null
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
  clearRunOutput: () => set({ logs: [], artifacts: [], exportPreview: null, validation: null })
}));
