import type { Workflow, WorkflowEdge, WorkflowNode } from "@/lib/schema-types";
import { safeClone } from "@/lib/safe-serialize";
import { nodeRegistry, type NodeExecutionContext } from "@/registry/nodeRegistry";

type WorkflowWithEntry = Workflow & {
  entry?: string | null;
  entry_node?: string | null;
};

type MetadataWithEntry = NonNullable<Workflow["metadata"]> & {
  entry?: string | null;
  entry_node?: string | null;
};

function getEntryNodeId(workflow: WorkflowWithEntry, nodes: WorkflowNode[], edges: WorkflowEdge[]) {
  const metadata = workflow.metadata as MetadataWithEntry | undefined;
  const explicitEntry = workflow.entry ?? workflow.entry_node ?? metadata?.entry ?? metadata?.entry_node;
  if (explicitEntry && nodes.some((node) => node.node_id === explicitEntry)) {
    return explicitEntry;
  }

  const targets = new Set(edges.map((edge) => edge.target));
  return nodes.find((node) => !targets.has(node.node_id))?.node_id ?? nodes[0]?.node_id ?? null;
}

function getNextNodeId(currentNode: WorkflowNode, edges: WorkflowEdge[], nodeById: Map<string, WorkflowNode>, visited: Set<string>) {
  const candidates = edges
    .filter((edge) => edge.source === currentNode.node_id && !visited.has(edge.target))
    .sort((a, b) => getExecutionPriority(nodeById.get(a.target)) - getExecutionPriority(nodeById.get(b.target)));
  return candidates[0]?.target ?? null;
}

function getExecutionPriority(node: WorkflowNode | undefined) {
  const type = String(node?.type ?? "");
  if (type === "transform") {
    return 1;
  }
  if (type === "personality") {
    return 2;
  }
  if (type === "output") {
    return 9;
  }
  return 5;
}

function isResidentOutput(value: unknown) {
  return Boolean(
    value &&
      typeof value === "object" &&
      !Array.isArray(value) &&
      (value as { mock?: unknown; resident_instance?: unknown }).mock === true &&
      (value as { resident_instance?: unknown }).resident_instance &&
      typeof (value as { resident_instance?: unknown }).resident_instance === "object"
  );
}

export function executeWorkflow(workflow: Workflow, input: unknown) {
  // Module is a container, never an execution node: drop module nodes and any
  // edge that touches them so they cannot enter the execution chain.
  const nodes = (workflow.nodes ?? []).filter((node) => String(node.type) !== "module");
  const validNodeIds = new Set(nodes.map((node) => node.node_id));
  const edges = (workflow.edges ?? []).filter(
    (edge) => validNodeIds.has(edge.source) && validNodeIds.has(edge.target)
  );
  const nodeById = new Map(nodes.map((node) => [node.node_id, node]));
  const entryNodeId = getEntryNodeId(workflow as WorkflowWithEntry, nodes, edges);

  if (!entryNodeId) {
    throw new Error("Workflow has no executable entry node");
  }

  const context: NodeExecutionContext = {
    input,
    current: input,
    memory: {},
    intermediate: {}
  };
  const visited = new Set<string>();
  let currentNodeId: string | null = entryNodeId;
  let lastOutput: unknown = input;

  while (currentNodeId) {
    if (visited.has(currentNodeId)) {
      throw new Error(`Workflow execution cycle detected at node "${currentNodeId}"`);
    }
    visited.add(currentNodeId);

    const node = nodeById.get(currentNodeId);
    if (!node) {
      throw new Error(`Workflow node "${currentNodeId}" does not exist`);
    }

    const definition = nodeRegistry.get(node.type);
    if (!definition?.execute) {
      return { error: `node type ${node.type} missing execute function` };
    }

    let stepOutput: unknown;
    try {
      stepOutput = definition.execute(context, node);
    } catch (error) {
      return { error: `node "${node.node_id}" (${node.type}) failed: ${(error as Error).message}` };
    }
    // execute returning undefined must not break the chain.
    lastOutput = safeClone(stepOutput ?? context.current ?? null);
    context.current = lastOutput;

    // The output node's result embeds context.intermediate; return it BEFORE
    // writing it back into intermediate, otherwise intermediate would reference
    // an object that references intermediate (circular -> JSON.stringify throws).
    if (String(node.type) === "output") {
      return safeClone(lastOutput);
    }

    context.intermediate[node.node_id] = safeClone(lastOutput);
    currentNodeId = getNextNodeId(node, edges, nodeById, visited);
  }

  if (isResidentOutput(lastOutput)) {
    return safeClone(lastOutput);
  }

  return safeClone({
    persona_result: lastOutput,
    memory: context.memory,
    intermediate: context.intermediate
  });
}
