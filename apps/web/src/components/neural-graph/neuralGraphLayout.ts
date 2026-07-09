import type { NeuralGraphNode, ResidentNeuralGraph } from "./neuralGraphTypes";

const NODE_RING_RADIUS = 0.48;
const OUTER_CLUSTER_RADIUS = 3.65;
const L1_CLUSTER_RADIUS = 0.78;

function layerClusterCenter(layerOrder: number, totalLayers: number, radius: number): [number, number, number] {
  if (layerOrder === 1) {
    return [0, 0, 0];
  }
  const index = Math.max(0, layerOrder - 2);
  const total = Math.max(1, totalLayers - 1);
  const goldenAngle = Math.PI * (3 - Math.sqrt(5));
  const t = total <= 1 ? 0 : index / (total - 1);
  const y = 1 - 2 * t;
  const ring = Math.sqrt(Math.max(0, 1 - y * y));
  const theta = index * goldenAngle;
  const shell = radius * (0.94 + (index % 3) * 0.035);

  return [Math.cos(theta) * ring * shell, y * shell * 0.9, Math.sin(theta) * ring * shell];
}

function moduleLocalOffset(index: number, total: number, clusterRadius: number, layerOrder: number): [number, number, number] {
  if (total <= 1) {
    return [0, 0, 0];
  }
  const goldenAngle = Math.PI * (3 - Math.sqrt(5));
  const t = index / (total - 1);
  const y = 1 - 2 * t;
  const ring = Math.sqrt(Math.max(0, 1 - y * y));
  const theta = index * goldenAngle + layerOrder * 0.31;
  const shell = clusterRadius * (0.86 + (index % 4) * 0.095);

  return [Math.cos(theta) * ring * shell, y * shell * 0.86, Math.sin(theta) * ring * shell];
}

function clusterRadiusFor(moduleCount: number, layerOrder: number) {
  if (layerOrder === 1) {
    return Math.max(0.5, Math.min(L1_CLUSTER_RADIUS, Math.sqrt(Math.max(1, moduleCount)) * 0.28));
  }
  return Math.max(1.02, Math.min(2.05, Math.sqrt(Math.max(1, moduleCount)) * 0.43));
}

function offsetAround(index: number, total: number, radius: number, verticalStep: number): [number, number, number] {
  const safeTotal = Math.max(1, total);
  const angle = (index / safeTotal) * Math.PI * 2;
  const z = Math.sin(index * 1.17) * radius * 0.42;
  const y = ((index % 5) - 2) * verticalStep;
  return [Math.cos(angle) * radius, y, Math.sin(angle) * radius + z];
}

export function applyNeuralGraphLayout(graph: ResidentNeuralGraph): ResidentNeuralGraph {
  const nodes = graph.nodes.map((node) => ({ ...node }));
  const modules = nodes.filter((node) => node.kind === "module");
  const layers = nodes.filter((node) => node.kind === "layer");
  const byId = new Map(nodes.map((node) => [node.id, node]));
  const totalLayers = Math.max(13, layers.length);
  const modulesByLayer = new Map<string, NeuralGraphNode[]>();
  const internalNodesByModule = new Map<string, NeuralGraphNode[]>();

  for (const layer of layers) {
    const layerOrder = layer.layerOrder ?? 1;
    layer.position = layerClusterCenter(layerOrder, totalLayers, OUTER_CLUSTER_RADIUS);
  }

  for (const module of modules) {
    const layerId = module.layerId ?? "";
    modulesByLayer.set(layerId, [...(modulesByLayer.get(layerId) ?? []), module]);
  }

  for (const [layerId, layerModules] of modulesByLayer) {
    const layer = byId.get(`layer:${layerId}`);
    const layerOrder = layer?.layerOrder ?? layerModules[0]?.layerOrder ?? 1;
    const center = layer?.position ?? layerClusterCenter(layerOrder, totalLayers, OUTER_CLUSTER_RADIUS);
    const clusterRadius = clusterRadiusFor(layerModules.length, layerOrder);
    layerModules
      .slice()
      .sort((a, b) => String(a.moduleId ?? a.id).localeCompare(String(b.moduleId ?? b.id)))
      .forEach((module, index) => {
        const [x, y, z] = moduleLocalOffset(index, layerModules.length, clusterRadius, layerOrder);
        module.position = [center[0] + x, center[1] + y, center[2] + z];
      });
  }

  for (const node of nodes) {
    if (node.kind === "node" && (node.moduleInstanceId || node.moduleId)) {
      const moduleKey = node.moduleInstanceId || node.moduleId || "";
      internalNodesByModule.set(moduleKey, [...(internalNodesByModule.get(moduleKey) ?? []), node]);
    }
  }

  for (const [moduleId, internalNodes] of internalNodesByModule) {
    const module = byId.get(`module:${moduleId}`);
    const anchor = module?.position ?? [0, 0, 0];
    internalNodes.forEach((node, index) => {
      if (node.previewPosition) {
        node.position = [
          anchor[0] + node.previewPosition[0],
          anchor[1] + node.previewPosition[1],
          anchor[2] + node.previewPosition[2],
        ];
        return;
      }
      const [x, y, z] = offsetAround(index, internalNodes.length, NODE_RING_RADIUS + (index % 4) * 0.035, 0.095);
      node.position = [anchor[0] + x, anchor[1] + y, anchor[2] + z];
    });
  }

  return { nodes, edges: graph.edges, regions: graph.regions };
}
