import type { Workflow, WorkflowEdge, WorkflowNode } from "@/lib/schema-types";
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

export function executeWorkflow(workflow: Workflow, input: unknown) {
  const nodes = workflow.nodes ?? [];
  const edges = workflow.edges ?? [];
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

    lastOutput = definition.execute(context, node);
    context.current = lastOutput;
    context.intermediate[node.node_id] = lastOutput;

    if (node.type === "output") {
      return lastOutput;
    }

    currentNodeId = edges.find((edge) => edge.source === node.node_id)?.target ?? null;
  }

  return {
    persona_result: lastOutput,
    memory: context.memory,
    intermediate: context.intermediate
  };
}
