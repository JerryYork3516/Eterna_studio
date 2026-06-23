import type { Workflow, WorkflowEdge, WorkflowNode } from "@/lib/schema-types";

const SCHEMA_VERSION = "0.3.0";
const NODE_TYPES = new Set(["input", "transform", "model", "agent", "review", "layer_container", "output", "export"]);
const NODE_CATEGORIES = new Set(["source", "processing", "ai", "control", "container", "sink"]);
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
  const workflow = expectRecord(value, "workflow");
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

function sanitizeNode(value: unknown, index: number, nodeIds: Set<string>): WorkflowNode {
  const node = expectRecord(value, `nodes[${index}]`);
  const nodeId = expectString(node.node_id, `nodes[${index}].node_id`);
  if (nodeIds.has(nodeId)) {
    throw new Error(`Invalid workflow: duplicate node_id "${nodeId}"`);
  }
  nodeIds.add(nodeId);

  const type = expectEnum(node.type, NODE_TYPES, `nodes[${index}].type`);
  const category = expectEnum(node.category, NODE_CATEGORIES, `nodes[${index}].category`);
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
