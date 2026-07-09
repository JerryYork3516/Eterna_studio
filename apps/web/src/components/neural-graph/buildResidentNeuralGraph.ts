import type { ModuleCatalogEntryV04 } from "@/lib/schema-types";
import { resolveLayerColor, resolveModuleColor } from "./neuralGraphColors";
import { applyNeuralGraphLayout } from "./neuralGraphLayout";
import type {
  ModuleGraphLike,
  ModuleGraphsLike,
  NeuralGraphNode,
  NeuralGraphReferenceScope,
  NeuralGraphModuleInstance,
  ResidentNeuralGraph,
  ResidentNeuralGraphInput,
} from "./neuralGraphTypes";

const MAX_INTERNAL_NODES_PER_MODULE = 20;
const MODULE_INSTANCE_SEPARATOR = "::";
const PREVIEW_WIDTH = 3.2;
const PREVIEW_HEIGHT = 1.9;

function readRecord(value: unknown): Record<string, unknown> | null {
  return value && typeof value === "object" && !Array.isArray(value) ? (value as Record<string, unknown>) : null;
}

function readString(value: unknown) {
  return typeof value === "string" ? value : "";
}

function readStringArray(value: unknown): string[] {
  return Array.isArray(value) ? value.map((item) => readString(item)).filter(Boolean) : [];
}

function translatedModuleName(module: ModuleCatalogEntryV04, t?: (key: string, fallback?: string) => string) {
  const fallback = readString(module.module_name) || readString(module.module_id) || "Module";
  const i18nKeys = readRecord(module.i18n_keys);
  const displayNameKey = readString(i18nKeys?.display_name) || readString(i18nKeys?.name);
  if (!t) {
    return fallback;
  }
  return displayNameKey ? t(displayNameKey, t(`module.${module.module_id}`, fallback)) : t(`module.${module.module_id}`, fallback);
}

function translatedLayerName(layerId: string, layerName: string, t?: (key: string, fallback?: string) => string) {
  return t ? t(`layer.${layerId}`, layerName) : layerName;
}

function compactLabel(value: string, maxCjk = 8, maxLatin = 20) {
  const trimmed = value.trim();
  const cjkCount = Array.from(trimmed).filter((char) => /[\u3400-\u9fff]/.test(char)).length;
  const limit = cjkCount > 0 ? maxCjk : maxLatin;
  const chars = Array.from(trimmed);
  return chars.length > limit ? `${chars.slice(0, limit).join("")}...` : trimmed;
}

type GraphNodeView = {
  schema: Record<string, unknown>;
  raw: Record<string, unknown>;
  data: Record<string, unknown>;
  position?: { x: number; y: number };
};

function readPosition(value: unknown): { x: number; y: number } | undefined {
  const record = readRecord(value);
  const x = typeof record?.x === "number" ? record.x : Number(record?.x);
  const y = typeof record?.y === "number" ? record.y : Number(record?.y);
  return Number.isFinite(x) && Number.isFinite(y) ? { x, y } : undefined;
}

function graphNodeView(value: unknown): GraphNodeView | null {
  const record = readRecord(value);
  if (!record) {
    return null;
  }
  const data = readRecord(record.data);
  const schemaNode = readRecord(data?.schemaNode);
  const schema = schemaNode ?? record;
  const schemaData = readRecord(schema.data) ?? {};
  return {
    schema,
    raw: record,
    data: schemaData,
    position: readPosition(schema.position) ?? readPosition(record.position),
  };
}

function translatedNodeName(node: GraphNodeView, t?: (key: string, fallback?: string) => string) {
  const i18nKeys = readRecord(node.schema.i18n_keys) ?? readRecord(node.data.i18n_keys);
  const fallback =
    readString(node.schema.title_fallback) ||
    readString(node.data.label) ||
    readString(node.data.title) ||
    readString(node.schema.name) ||
    readString(node.schema.node_id) ||
    readString(node.schema.id) ||
    "Node";
  const key =
    readString(i18nKeys?.display_name) ||
    readString(i18nKeys?.title) ||
    readString(i18nKeys?.name) ||
    readString(node.schema.title_key) ||
    readString(node.data.title_key);
  return key && t ? t(key, fallback) : fallback;
}

function previewPositionsForNodes(nodes: GraphNodeView[]): [number, number, number][] {
  const positioned = nodes.map((node) => node.position).filter((position): position is { x: number; y: number } => Boolean(position));
  if (positioned.length === nodes.length && positioned.length > 0) {
    const minX = Math.min(...positioned.map((position) => position.x));
    const maxX = Math.max(...positioned.map((position) => position.x));
    const minY = Math.min(...positioned.map((position) => position.y));
    const maxY = Math.max(...positioned.map((position) => position.y));
    const centerX = (minX + maxX) / 2;
    const centerY = (minY + maxY) / 2;
    const spanX = Math.max(1, maxX - minX);
    const spanY = Math.max(1, maxY - minY);
    return positioned.map((position, index) => [
      ((position.x - centerX) / spanX) * PREVIEW_WIDTH,
      -((position.y - centerY) / spanY) * PREVIEW_HEIGHT,
      ((index % 3) - 1) * 0.025,
    ]);
  }

  const columns = Math.max(1, Math.ceil(Math.sqrt(nodes.length)));
  return nodes.map((_, index) => {
    const row = Math.floor(index / columns);
    const column = index % columns;
    const rowCount = Math.ceil(nodes.length / columns);
    return [
      (column - (columns - 1) / 2) * 0.72,
      ((rowCount - 1) / 2 - row) * 0.46,
      ((index % 3) - 1) * 0.025,
    ];
  });
}

function graphEdgeRecord(value: unknown): Record<string, unknown> | null {
  return readRecord(value);
}

function relationKind(value: unknown): ResidentNeuralGraph["edges"][number]["kind"] {
  const raw = readString(value);
  return raw === "references" ||
    raw === "outputs_to" ||
    raw === "constrains" ||
    raw === "conflicts_with" ||
    raw === "overrides_forbidden"
    ? raw
    : "unknown";
}

function referenceScope(value: unknown, fallback: NeuralGraphReferenceScope = "module"): NeuralGraphReferenceScope {
  const raw = readString(value);
  return raw === "module" || raw === "node" || raw === "field" ? raw : fallback;
}

function paramsFromGraphNode(node: GraphNodeView): Record<string, unknown> {
  return readRecord(node.data.params) ?? readRecord(node.schema.params) ?? {};
}

function edgeEndpoint(value: unknown) {
  return readString(value);
}

function resolveGraphEndpoint(endpoint: string, nodeIdByEndpoint: Map<string, string>) {
  if (nodeIdByEndpoint.has(endpoint)) {
    return nodeIdByEndpoint.get(endpoint);
  }
  const withoutHandle = endpoint.split(".")[0] ?? endpoint;
  if (nodeIdByEndpoint.has(withoutHandle)) {
    return nodeIdByEndpoint.get(withoutHandle);
  }
  const parts = endpoint.split(MODULE_INSTANCE_SEPARATOR);
  const suffix = parts[parts.length - 1] ?? endpoint;
  if (nodeIdByEndpoint.has(suffix)) {
    return nodeIdByEndpoint.get(suffix);
  }
  const nodePrefix = endpoint.split(":").pop() ?? endpoint;
  return nodeIdByEndpoint.get(nodePrefix);
}

function moduleGraphFromCatalog(module: ModuleCatalogEntryV04): ModuleGraphLike {
  const graph = readRecord(module.module_graph);
  return {
    nodes: Array.isArray(graph?.nodes) ? graph.nodes : [],
    edges: Array.isArray(graph?.edges) ? graph.edges : [],
  };
}

function moduleDisplayLayerId(module: ModuleCatalogEntryV04, storedLayerId: string) {
  return module.layer_id === "general" ? storedLayerId : module.layer_id;
}

function graphForModule(module: ModuleCatalogEntryV04, instanceId: string, moduleGraphs?: ModuleGraphsLike): ModuleGraphLike {
  const instance = moduleGraphs?.[instanceId];
  if (instance) {
    return instance;
  }
  const exact = moduleGraphs?.[module.module_id];
  if (exact) {
    return exact;
  }
  const suffix = `::${module.module_id}`;
  const instanceGraph = Object.entries(moduleGraphs ?? {}).find(([key]) => key.endsWith(suffix))?.[1];
  return instanceGraph ?? moduleGraphFromCatalog(module);
}

function instanceForModule(
  moduleId: string,
  layerId: string,
  moduleInstanceRegistry?: Record<string, NeuralGraphModuleInstance>
) {
  const preferredId = `${layerId}${MODULE_INSTANCE_SEPARATOR}${moduleId}`;
  return (
    moduleInstanceRegistry?.[preferredId] ??
    Object.values(moduleInstanceRegistry ?? {}).find((instance) => instance.moduleId === moduleId && instance.layerId === layerId) ??
    Object.values(moduleInstanceRegistry ?? {}).find((instance) => instance.moduleId === moduleId) ?? {
      instanceId: preferredId,
      moduleId,
      layerId,
    }
  );
}

export function buildResidentNeuralGraph({
  moduleCatalog,
  moduleGraphs,
  layerModules = {},
  moduleInstanceRegistry,
  uiColors,
  moduleUiColors,
  t,
}: ResidentNeuralGraphInput): ResidentNeuralGraph {
  if (!moduleCatalog) {
    return { nodes: [], edges: [], regions: [] };
  }

  const nodes: NeuralGraphNode[] = [];
  const edges: ResidentNeuralGraph["edges"] = [];
  const moduleCatalogById = new Map(moduleCatalog.modules.map((module) => [module.module_id, module]));
  const attachedModulesByLayer = new Map<string, { module: ModuleCatalogEntryV04; instance: NeuralGraphModuleInstance }[]>();
  const layerOrderById = new Map(moduleCatalog.layers.map((layer) => [layer.layer_id, layer.layer_order]));
  const layerColorById = new Map<string, string>();
  const moduleNodeByLayerAndModule = new Map<string, string>();
  const referenceOutputIndex = new Map<string, { fieldPaths: Set<string> }>();
  const moduleRelationRequests: Array<{
    sourceLayerId: string;
    sourceModuleId: string;
    targetModuleNodeId: string;
    kind: ResidentNeuralGraph["edges"][number]["kind"];
    sourceScope: NeuralGraphReferenceScope;
    sourceNodeId: string;
    sourceFieldPaths: string[];
  }> = [];

  for (const layer of moduleCatalog.layers) {
    const color = resolveLayerColor(layer.layer_id, layer.layer_order, uiColors);
    layerColorById.set(layer.layer_id, color);
  }

  for (const [storedLayerId, moduleIds] of Object.entries(layerModules)) {
    for (const moduleId of moduleIds) {
      const module = moduleCatalogById.get(moduleId);
      if (!module) {
        continue;
      }
      const displayLayerId = moduleDisplayLayerId(module, storedLayerId);
      const instance = instanceForModule(moduleId, displayLayerId, moduleInstanceRegistry);
      attachedModulesByLayer.set(displayLayerId, [...(attachedModulesByLayer.get(displayLayerId) ?? []), { module, instance }]);
    }
  }

  for (const layer of moduleCatalog.layers.slice().sort((a, b) => a.layer_order - b.layer_order)) {
    const modules = attachedModulesByLayer.get(layer.layer_id) ?? [];
    nodes.push({
      id: `layer:${layer.layer_id}`,
      label: translatedLayerName(layer.layer_id, layer.layer_name, t),
      shortLabel: `L${layer.layer_order}`,
      kind: "layer",
      color: layerColorById.get(layer.layer_id),
      layerId: layer.layer_id,
      layerOrder: layer.layer_order,
      moduleCount: modules.length,
      position: [0, 0, 0],
    });
  }

  for (const [layerId, attachedModules] of attachedModulesByLayer) {
    for (const { module, instance } of attachedModules) {
      const moduleId = module.module_id;
      const graph = graphForModule(module, instance.instanceId, moduleGraphs);
      const graphNodes = (graph.nodes ?? []).map(graphNodeView).filter((node): node is GraphNodeView => Boolean(node));
      const visibleGraphNodes = graphNodes.slice(0, MAX_INTERNAL_NODES_PER_MODULE);
      const previewPositions = previewPositionsForNodes(visibleGraphNodes);
      const hiddenNodeCount = Math.max(0, graphNodes.length - visibleGraphNodes.length);
      const moduleNodeId = `module:${instance.instanceId}`;
      const nodeIdByEndpoint = new Map<string, string>();
      const layerColor = layerColorById.get(layerId) ?? resolveLayerColor(layerId, layerOrderById.get(layerId), uiColors);
      const moduleColor = resolveModuleColor({
        moduleId,
        layerId,
        storedLayerId: instance.layerId,
        layerColor,
        moduleUiColors,
      });

      nodes.push({
        id: moduleNodeId,
        label: translatedModuleName(module, t),
        shortLabel: compactLabel(translatedModuleName(module, t)),
        kind: "module",
        color: moduleColor,
        layerId,
        moduleId,
        moduleInstanceId: instance.instanceId,
        layerOrder: layerOrderById.get(layerId),
        nodeCount: graphNodes.length,
        hiddenNodeCount,
        position: [0, 0, 0],
      });
      moduleNodeByLayerAndModule.set(`${layerId}:${moduleId}`, moduleNodeId);
      moduleNodeByLayerAndModule.set(`:${moduleId}`, moduleNodeId);
      const referenceOutputNodes = graphNodes.filter((graphNode) => {
        const nodeType = readString(graphNode.schema.node_type) || readString(graphNode.schema.type);
        return nodeType === "reference_output";
      });
      if (referenceOutputNodes.length) {
        const fieldPaths = new Set<string>();
        for (const outputNode of referenceOutputNodes) {
          const outputParams = paramsFromGraphNode(outputNode);
          const exportFields = Array.isArray(outputParams.export_fields) ? outputParams.export_fields : [];
          for (const fieldValue of exportFields) {
            const field = readRecord(fieldValue);
            const fieldPath = readString(field?.field_path) || readString(field?.field_key);
            if (fieldPath) {
              fieldPaths.add(fieldPath);
            }
          }
        }
        const outputIndexEntry = { fieldPaths };
        referenceOutputIndex.set(`${layerId}:${moduleId}`, outputIndexEntry);
        referenceOutputIndex.set(`:${moduleId}`, outputIndexEntry);
      }
      edges.push({
        id: `contains:layer:${layerId}->module:${instance.instanceId}`,
        source: `layer:${layerId}`,
        target: moduleNodeId,
        kind: "contains",
      });

      visibleGraphNodes.forEach((graphNode, index) => {
        const nodeId = readString(graphNode.schema.node_id) || readString(graphNode.schema.id) || `${moduleId}:node:${index}`;
        const nodeType = readString(graphNode.schema.node_type) || readString(graphNode.schema.type) || "node";
        const graphNodeId = `node:${instance.instanceId}:${nodeId}`;
        nodeIdByEndpoint.set(nodeId, graphNodeId);
        nodeIdByEndpoint.set(graphNodeId, graphNodeId);
        if (readString(graphNode.schema.id)) {
          nodeIdByEndpoint.set(readString(graphNode.schema.id), graphNodeId);
        }
        if (readString(graphNode.raw.id)) {
          nodeIdByEndpoint.set(readString(graphNode.raw.id), graphNodeId);
        }
        nodes.push({
          id: graphNodeId,
          label: translatedNodeName(graphNode, t),
          shortLabel: compactLabel(translatedNodeName(graphNode, t), 9, 22),
          kind: "node",
          color: moduleColor,
          layerId,
          moduleId,
          moduleInstanceId: instance.instanceId,
          nodeId,
          nodeType,
          position: [0, 0, 0],
          previewPosition: previewPositions[index],
        });
        edges.push({
          id: `contains:module:${instance.instanceId}->${graphNodeId}`,
          source: moduleNodeId,
          target: graphNodeId,
          kind: "contains",
        });
      });

      graphNodes
        .filter((graphNode) => {
          const nodeType = readString(graphNode.schema.node_type) || readString(graphNode.schema.type);
          return nodeType === "reference_input";
        })
        .forEach((graphNode) => {
          const params = paramsFromGraphNode(graphNode);
          const references = Array.isArray(params.references) ? params.references.filter((item): item is Record<string, unknown> => Boolean(readRecord(item))) : [];
          for (const reference of references) {
            const sourceModuleId = readString(reference.source_module_id);
            if (!sourceModuleId) {
              continue;
            }
            const sourceFieldPaths = readStringArray(reference.source_field_paths);
            moduleRelationRequests.push({
              sourceLayerId: readString(reference.source_layer_id),
              sourceModuleId,
              targetModuleNodeId: moduleNodeId,
              kind: relationKind(reference.reference_type),
              sourceScope: referenceScope(reference.source_scope, sourceFieldPaths.length ? "field" : "module"),
              sourceNodeId: readString(reference.source_node_id),
              sourceFieldPaths,
            });
          }
        });

      (graph.edges ?? []).forEach((edgeValue, index) => {
        const edge = graphEdgeRecord(edgeValue);
        if (!edge) {
          return;
        }
        const sourceEndpoint = edgeEndpoint(edge.source) || edgeEndpoint(edge.source_node_id);
        const targetEndpoint = edgeEndpoint(edge.target) || edgeEndpoint(edge.target_node_id);
        const source = resolveGraphEndpoint(sourceEndpoint, nodeIdByEndpoint);
        const target = resolveGraphEndpoint(targetEndpoint, nodeIdByEndpoint);
        if (!source || !target || source === target) {
          return;
        }
        edges.push({
          id: `internal:${instance.instanceId}:${readString(edge.edge_id) || `${sourceEndpoint}->${targetEndpoint}:${index}`}`,
          source,
          target,
          kind: "unknown",
        });
      });
    }
  }

  moduleRelationRequests.forEach((request, index) => {
    const source =
      moduleNodeByLayerAndModule.get(`${request.sourceLayerId}:${request.sourceModuleId}`) ??
      moduleNodeByLayerAndModule.get(`:${request.sourceModuleId}`);
    const referenceOutput =
      referenceOutputIndex.get(`${request.sourceLayerId}:${request.sourceModuleId}`) ??
      referenceOutputIndex.get(`:${request.sourceModuleId}`);
    if (!source || !referenceOutput || source === request.targetModuleNodeId) {
      return;
    }
    edges.push({
      id: `reference:${source}->${request.targetModuleNodeId}:${request.kind}:${index}`,
      source,
      target: request.targetModuleNodeId,
      kind: request.kind,
      sourceScope: request.sourceScope,
      sourceNodeId: request.sourceNodeId || undefined,
      sourceFieldPaths: request.sourceFieldPaths,
    });
  });

  return applyNeuralGraphLayout({ nodes, edges, regions: [] });
}
