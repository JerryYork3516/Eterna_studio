import type { Workflow, WorkflowEdge, WorkflowNode } from "@/lib/schema-types";

const SCHEMA_VERSION = "0.4.0";
const LOCK_LEVELS = new Set(["editable", "review_required", "locked", "system_locked", "mixed"]);
const MODULE_TIERS = new Set(["core", "plugin", "later"]);

function nowIso() {
  return new Date().toISOString();
}

export function withUpdatedWorkflowGraph(workflow: Workflow, nodes = workflow.nodes ?? [], edges = workflow.edges ?? []) {
  return sanitizeWorkflow({
    ...workflow,
    nodes,
    edges,
    updated_at: nowIso()
  });
}

export function downloadWorkflow(workflow: Workflow) {
  console.info("[workflow-download] start", {
    workflow_id: workflow.workflow_id,
    name: workflow.name
  });
  const blob = new Blob([JSON.stringify(workflow, null, 2)], {
    type: "application/json"
  });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = `${workflow.name || "workflow"}.workflow.json`;
  anchor.addEventListener("click", () => {
    console.info("[workflow-download] anchor-click");
  });
  document.body.appendChild(anchor);
  console.info("[workflow-download] click", {
    bytes: blob.size,
    filename: anchor.download
  });
  anchor.click();
  window.setTimeout(() => {
    anchor.remove();
    URL.revokeObjectURL(url);
    console.info("[workflow-download] cleanup");
  }, 1000);
}

export function readWorkflowFile(file: File): Promise<Workflow> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onerror = () => reject(reader.error);
    reader.onload = () => {
      try {
        resolve(sanitizeWorkflow(JSON.parse(String(reader.result))));
      } catch (error) {
        reject(error);
      }
    };
    reader.readAsText(file);
  });
}

export function sanitizeWorkflow(value: unknown): Workflow {
  const workflow = normalizeWorkflowShape(expectRecord(value, "workflow"));
  if (workflow.schema_version !== SCHEMA_VERSION) {
    throw new Error(`Unsupported workflow schema_version: ${String(workflow.schema_version ?? "missing")}`);
  }
  if (typeof workflow.name !== "string" || !workflow.name) {
    throw new Error("Invalid workflow: name is required");
  }
  if (!Array.isArray(workflow.nodes)) {
    throw new Error("Invalid workflow: nodes must be an array");
  }
  if (!Array.isArray(workflow.edges)) {
    throw new Error("Invalid workflow: edges must be an array");
  }
  if (!isRecord(workflow.metadata)) {
    throw new Error("Invalid workflow: metadata must be an object");
  }

  const nodeIds = new Set<string>();
  const nodes = workflow.nodes.map((node, index) => sanitizeNode(node, index, nodeIds));
  const edgeIds = new Set<string>();
  const edges = workflow.edges.map((edge, index) => sanitizeEdge(edge, index, nodeIds, edgeIds));

  return {
    ...workflow,
    schema_version: expectString(workflow.schema_version, "workflow.schema_version"),
    workflow_id: typeof workflow.workflow_id === "string" ? workflow.workflow_id : undefined,
    version: typeof workflow.version === "string" ? workflow.version : "1.0.0",
    template_type: typeof workflow.template_type === "string" ? workflow.template_type : "blank",
    content_locale: typeof workflow.content_locale === "string" ? workflow.content_locale : null,
    nodes,
    edges,
    viewport: workflow.viewport === undefined ? undefined : sanitizeViewport(workflow.viewport),
    metadata: workflow.metadata,
    created_at: typeof workflow.created_at === "string" ? workflow.created_at : undefined,
    updated_at: typeof workflow.updated_at === "string" ? workflow.updated_at : undefined
  } as Workflow;
}

function normalizeWorkflowShape(rawWorkflow: Record<string, unknown>): Record<string, unknown> {
  const rawNodes = Array.isArray(rawWorkflow.nodes) ? rawWorkflow.nodes.filter(isRecord) : [];
  const rawEdges = Array.isArray(rawWorkflow.edges) ? rawWorkflow.edges.filter(isRecord) : [];
  const rawLayers = Array.isArray(rawWorkflow.layers) ? rawWorkflow.layers.filter(isRecord) : [];
  const rawModules = Array.isArray(rawWorkflow.modules) ? rawWorkflow.modules.filter(isRecord) : [];
  const nodeById = new Map<string, Record<string, unknown>>();

  rawNodes.forEach((node, index) => {
    nodeById.set(rawNodeId(node, index), node);
  });

  const layerNodeByLayerId = new Map<string, string>();
  const layerIndexByLayerNodeId = new Map<string, number>();
  const parentLayerByNodeId = new Map<string, string>();
  const layerIndexByNodeId = new Map<string, number>();

  rawLayers.forEach((layer) => {
    const layerId = typeof layer.id === "string" ? layer.id : "";
    const nodeIds = Array.isArray(layer.node_ids) ? layer.node_ids.map(String) : [];
    const layerNodeId = nodeIds.find((nodeId) => nodeById.get(nodeId)?.type === "layer_container") ?? "";
    const layerNode = layerNodeId ? nodeById.get(layerNodeId) : null;
    const layerIndex = layerNode ? dataNumberFromRaw(layerNode, "layer_index") : null;

    if (layerId && layerNodeId) {
      layerNodeByLayerId.set(layerId, layerNodeId);
    }
    if (layerNodeId && layerIndex !== null) {
      layerIndexByLayerNodeId.set(layerNodeId, layerIndex);
    }
    for (const nodeId of nodeIds) {
      if (!layerNodeId || nodeId === layerNodeId) {
        continue;
      }
      parentLayerByNodeId.set(nodeId, layerNodeId);
      if (layerIndex !== null) {
        layerIndexByNodeId.set(nodeId, layerIndex);
      }
    }
  });

  rawModules.forEach((module) => {
    const layerId = typeof module.layer_id === "string" ? module.layer_id : "";
    const layerNodeId = layerNodeByLayerId.get(layerId);
    if (!layerNodeId) {
      return;
    }
    const layerIndex = layerIndexByLayerNodeId.get(layerNodeId) ?? null;
    const nodeIds = Array.isArray(module.node_ids) ? module.node_ids.map(String) : [];
    for (const nodeId of nodeIds) {
      const node = nodeById.get(nodeId);
      if (!node || node.type === "layer_container") {
        continue;
      }
      parentLayerByNodeId.set(nodeId, layerNodeId);
      if (layerIndex !== null) {
        layerIndexByNodeId.set(nodeId, layerIndex);
      }
    }
  });

  const nodes = rawNodes.map((node, index) => normalizeNodeShape(node, index, parentLayerByNodeId, layerIndexByNodeId, rawLayers));
  const edges = rawEdges.map((edge, index) => normalizeEdgeShape(edge, index));

  return {
    ...rawWorkflow,
    workflow_id: typeof rawWorkflow.workflow_id === "string" ? rawWorkflow.workflow_id : typeof rawWorkflow.id === "string" ? rawWorkflow.id : undefined,
    template_type:
      typeof rawWorkflow.template_type === "string"
        ? rawWorkflow.template_type
        : inferTemplateType(rawWorkflow.metadata, rawWorkflow.name),
    nodes,
    edges
  };
}

function normalizeNodeShape(
  node: Record<string, unknown>,
  index: number,
  parentLayerByNodeId: Map<string, string>,
  layerIndexByNodeId: Map<string, number>,
  rawLayers: Record<string, unknown>[]
) {
  const nodeId = rawNodeId(node, index);
  const type = typeof node.type === "string" ? node.type : "transform";
  const label = typeof node.label === "string" ? node.label : typeof node.title_fallback === "string" ? node.title_fallback : type;
  const data = {
    ...recordValue(node.inputs),
    ...recordValue(node.params),
    ...recordValue(node.data)
  };
  const parentLayer = parentLayerByNodeId.get(nodeId);
  if (parentLayer && typeof data.parent_layer !== "string") {
    data.parent_layer = parentLayer;
    data.layer_id = parentLayer;
  }
  const layerIndex = layerIndexByNodeId.get(nodeId);
  if (layerIndex !== undefined && data.layer_index === undefined) {
    data.layer_index = layerIndex;
  }
  if (data.status === undefined && typeof node.status === "string") {
    data.status = node.status;
  }
  if (data.version === undefined) {
    data.version = "1.0.0";
  }
  if (type === "layer_container" && data.children_count === undefined) {
    data.children_count = countLayerChildren(nodeId, rawLayers);
  }

  return {
    ...node,
    node_id: nodeId,
    type,
    category: typeof node.category === "string" ? node.category : inferCategory(type),
    title_key: typeof node.title_key === "string" ? node.title_key : `node.${type}`,
    title_fallback: label,
    position: normalizeRawPosition(node, index),
    lock_level: typeof node.lock_level === "string" ? node.lock_level : "editable",
    locale: typeof node.locale === "string" ? node.locale : null,
    data,
    ports: normalizeRawPorts(node)
  };
}

function normalizeEdgeShape(edge: Record<string, unknown>, index: number) {
  return {
    ...edge,
    edge_id: typeof edge.edge_id === "string" ? edge.edge_id : typeof edge.id === "string" ? edge.id : `edge_${index + 1}`,
    source: typeof edge.source === "string" ? edge.source : typeof edge.source_node_id === "string" ? edge.source_node_id : "",
    source_port: typeof edge.source_port === "string" ? edge.source_port : typeof edge.source_output === "string" ? edge.source_output : "p_out",
    target: typeof edge.target === "string" ? edge.target : typeof edge.target_node_id === "string" ? edge.target_node_id : "",
    target_port: typeof edge.target_port === "string" ? edge.target_port : typeof edge.target_input === "string" ? edge.target_input : "p_in"
  };
}

function rawNodeId(node: Record<string, unknown>, index: number) {
  return typeof node.node_id === "string" ? node.node_id : typeof node.id === "string" ? node.id : `node_${index + 1}`;
}

function recordValue(value: unknown): Record<string, unknown> {
  return isRecord(value) ? { ...value } : {};
}

function dataNumberFromRaw(node: Record<string, unknown>, key: string) {
  const inputs = recordValue(node.inputs);
  const data = recordValue(node.data);
  const value = data[key] ?? inputs[key] ?? node[key];
  const numberValue = typeof value === "number" ? value : Number(value);
  return Number.isFinite(numberValue) ? numberValue : null;
}

function normalizeRawPosition(node: Record<string, unknown>, index: number) {
  const direct = isRecord(node.position) ? node.position : null;
  const ui = isRecord(node.ui) ? node.ui : null;
  const uiPosition = ui && isRecord(ui.position) ? ui.position : null;
  const position = direct ?? uiPosition;
  return {
    x: typeof position?.x === "number" ? position.x : 0,
    y: typeof position?.y === "number" ? position.y : index * 120
  };
}

function normalizeRawPorts(node: Record<string, unknown>) {
  const ports = isRecord(node.ports) ? node.ports : null;
  if (ports && Array.isArray(ports.inputs) && Array.isArray(ports.outputs)) {
    return ports;
  }
  return {
    inputs: schemaFieldsToPorts(node.input_schema, "in"),
    outputs: schemaFieldsToPorts(node.output_schema, "out")
  };
}

function schemaFieldsToPorts(value: unknown, direction: "in" | "out") {
  if (!Array.isArray(value)) {
    return [];
  }
  return value.filter(isRecord).map((field, index) => {
    const key = typeof field.key === "string" ? field.key : `${direction}_${index + 1}`;
    return {
      port_id: key,
      name: typeof field.label === "string" ? field.label : key,
      direction
    };
  });
}

function inferCategory(type: string) {
  if (type === "layer_container" || type === "module") {
    return "container";
  }
  if (type.includes("input") || type === "text") {
    return "source";
  }
  if (type.includes("output") || type.includes("export") || type === "compile_resident") {
    return "sink";
  }
  if (type.includes("llm") || type.includes("model") || type.includes("personality")) {
    return "ai";
  }
  return "processing";
}

function inferTemplateType(metadata: unknown, name: unknown) {
  const meta = recordValue(metadata);
  if (typeof meta.template === "string") {
    return meta.template;
  }
  if (typeof name === "string" && name.toLowerCase().includes("persona")) {
    return "persona_builder";
  }
  return "blank";
}

function countLayerChildren(layerNodeId: string, rawLayers: Record<string, unknown>[]) {
  const layer = rawLayers.find((candidate) => Array.isArray(candidate.node_ids) && candidate.node_ids.map(String).includes(layerNodeId));
  if (!layer || !Array.isArray(layer.node_ids)) {
    return 0;
  }
  return Math.max(0, layer.node_ids.length - 1);
}

function sanitizeNode(value: unknown, index: number, nodeIds: Set<string>): WorkflowNode {
  const node = expectRecord(value, `nodes[${index}]`);
  const nodeId = expectString(node.node_id, `nodes[${index}].node_id`);
  if (nodeIds.has(nodeId)) {
    throw new Error(`Invalid workflow: duplicate node_id "${nodeId}"`);
  }
  nodeIds.add(nodeId);

  const type = expectString(node.type, `nodes[${index}].type`);
  const category = expectString(node.category, `nodes[${index}].category`);
  const lockLevel = expectEnum(node.lock_level, LOCK_LEVELS, `nodes[${index}].lock_level`);
  if (lockLevel === "mixed" && type !== "layer_container") {
    throw new Error(`Invalid workflow: mixed lock_level is only valid for layer_container (${nodeId})`);
  }

  return {
    ...node,
    node_id: nodeId,
    type,
    category,
    title_key: expectString(node.title_key, `nodes[${index}].title_key`),
    title_fallback: expectString(node.title_fallback, `nodes[${index}].title_fallback`),
    position: sanitizePosition(node.position, `nodes[${index}].position`),
    lock_level: lockLevel,
    locale: typeof node.locale === "string" ? node.locale : null,
    data: sanitizeNodeData(node.data, `nodes[${index}].data`),
    ports: sanitizePorts(node.ports, `nodes[${index}].ports`),
    validation: node.validation === undefined ? undefined : isRecord(node.validation) ? node.validation : null
  } as WorkflowNode;
}

function sanitizeEdge(
  value: unknown,
  index: number,
  nodeIds: Set<string>,
  edgeIds: Set<string>
): WorkflowEdge {
  const edge = expectRecord(value, `edges[${index}]`);
  const edgeId = expectString(edge.edge_id, `edges[${index}].edge_id`);
  if (edgeIds.has(edgeId)) {
    throw new Error(`Invalid workflow: duplicate edge_id "${edgeId}"`);
  }
  edgeIds.add(edgeId);

  const source = expectString(edge.source, `edges[${index}].source`);
  const target = expectString(edge.target, `edges[${index}].target`);
  if (!nodeIds.has(source)) {
    throw new Error(`Invalid workflow: edge "${edgeId}" source "${source}" does not exist`);
  }
  if (!nodeIds.has(target)) {
    throw new Error(`Invalid workflow: edge "${edgeId}" target "${target}" does not exist`);
  }

  return {
    ...edge,
    edge_id: edgeId,
    source,
    source_port: expectString(edge.source_port, `edges[${index}].source_port`),
    target,
    target_port: expectString(edge.target_port, `edges[${index}].target_port`)
  } as WorkflowEdge;
}

function sanitizeViewport(value: unknown) {
  if (!isRecord(value)) {
    return null;
  }
  return {
    x: typeof value.x === "number" ? value.x : 0,
    y: typeof value.y === "number" ? value.y : 0,
    zoom: typeof value.zoom === "number" ? value.zoom : 1
  };
}

function sanitizePosition(value: unknown, path: string) {
  const position = expectRecord(value, path);
  if (typeof position.x !== "number" || typeof position.y !== "number") {
    throw new Error(`Invalid workflow: ${path}.x and ${path}.y must be numbers`);
  }
  return { x: position.x, y: position.y };
}

function sanitizePorts(value: unknown, path: string) {
  const ports = expectRecord(value, path);
  if (!Array.isArray(ports.inputs) || !Array.isArray(ports.outputs)) {
    throw new Error(`Invalid workflow: ${path}.inputs and ${path}.outputs must be arrays`);
  }
  return {
    inputs: ports.inputs.map((port, index) => sanitizePort(port, `${path}.inputs[${index}]`, "in")),
    outputs: ports.outputs.map((port, index) => sanitizePort(port, `${path}.outputs[${index}]`, "out"))
  };
}

function sanitizePort(value: unknown, path: string, direction: "in" | "out") {
  const port = expectRecord(value, path);
  const actualDirection = expectString(port.direction, `${path}.direction`);
  if (actualDirection !== direction) {
    throw new Error(`Invalid workflow: ${path}.direction must be "${direction}"`);
  }
  return {
    port_id: expectString(port.port_id, `${path}.port_id`),
    name: expectString(port.name, `${path}.name`),
    direction
  };
}

function sanitizeNodeData(value: unknown, path: string) {
  const data = isRecord(value) ? value : {};
  const moduleTier = data.module_tier;
  if (moduleTier !== undefined && moduleTier !== null && !MODULE_TIERS.has(String(moduleTier))) {
    throw new Error(`Invalid workflow: ${path}.module_tier "${String(moduleTier)}" is not supported`);
  }
  return data;
}

function expectString(value: unknown, path: string) {
  if (typeof value !== "string" || !value) {
    throw new Error(`Invalid workflow: ${path} must be a non-empty string`);
  }
  return value;
}

function expectEnum<T extends string>(value: unknown, values: Set<string>, path: string) {
  const text = expectString(value, path);
  if (!values.has(text)) {
    throw new Error(`Invalid workflow: ${path} "${text}" is not supported`);
  }
  return text as T;
}

function expectRecord(value: unknown, path: string) {
  if (!isRecord(value)) {
    throw new Error(`Invalid workflow: ${path} must be an object`);
  }
  return value;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}
