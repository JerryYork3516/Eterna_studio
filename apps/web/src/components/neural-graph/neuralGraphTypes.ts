import type { ModuleCatalogEntryV04, ModuleCatalogResponseV04, ModuleLayerV04, WorkflowEdge, WorkflowNode } from "@/lib/schema-types";

export type NeuralGraphNodeKind = "layer" | "module" | "node" | "field" | "runtime" | "memory";

export type NeuralGraphEdgeKind =
  | "contains"
  | "references"
  | "outputs_to"
  | "constrains"
  | "conflicts_with"
  | "overrides_forbidden"
  | "slot_dependency"
  | "unknown";

export type NeuralGraphReferenceScope = "module" | "node" | "field";

export type NeuralGraphNode = {
  id: string;
  label: string;
  shortLabel?: string;
  kind: NeuralGraphNodeKind;
  color?: string;
  regionId?: string;
  layerId?: string;
  moduleId?: string;
  moduleInstanceId?: string;
  nodeId?: string;
  nodeType?: string;
  layerOrder?: number;
  moduleCount?: number;
  nodeCount?: number;
  hiddenNodeCount?: number;
  position: [number, number, number];
  previewPosition?: [number, number, number];
};

export type NeuralGraphEdge = {
  id: string;
  source: string;
  target: string;
  kind: NeuralGraphEdgeKind;
  sourceScope?: NeuralGraphReferenceScope;
  sourceNodeId?: string;
  sourceFieldPaths?: string[];
};

export type ResidentNeuralGraph = {
  nodes: NeuralGraphNode[];
  edges: NeuralGraphEdge[];
  regions: NeuralGraphRegion[];
};

export type NeuralGraphRegion = {
  id: string;
  labelKey: string;
  labelFallback: string;
  layerIds: string[];
  color: string;
  position: [number, number, number];
  scale: [number, number, number];
};

export type NeuralGraphToggles = {
  layers: boolean;
  layerLabels: boolean;
  modules: boolean;
  moduleLabels: boolean;
  nodes: boolean;
  edges: boolean;
};

export type NeuralGraphSelection = NeuralGraphNode | null;

export type ModuleGraphLike = {
  nodes?: unknown[];
  edges?: unknown[];
};

export type ModuleGraphsLike = Record<string, ModuleGraphLike | undefined>;

export type NeuralGraphModuleInstance = {
  instanceId: string;
  moduleId: string;
  layerId: string;
};

export type ResidentNeuralGraphInput = {
  moduleCatalog: ModuleCatalogResponseV04 | null;
  moduleGraphs?: ModuleGraphsLike;
  layerModules?: Record<string, string[]>;
  moduleInstanceRegistry?: Record<string, NeuralGraphModuleInstance>;
  uiColors?: Record<string, string>;
  moduleUiColors?: Record<string, string>;
  t?: (key: string, fallback?: string) => string;
};

export type NeuralGraphCatalogLayer = ModuleLayerV04;
export type NeuralGraphCatalogModule = ModuleCatalogEntryV04;
export type NeuralGraphWorkflowNode = WorkflowNode;
export type NeuralGraphWorkflowEdge = WorkflowEdge;
