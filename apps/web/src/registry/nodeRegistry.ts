import type { NodeInputField, NodeRegistryEntry, NodeStatus, WorkflowNode } from "@/lib/schema-types";

export type { NodeInputField, NodeRegistryEntry, NodeStatus };

export type NodeExecutionContext = {
  input: unknown;
  current?: unknown;
  memory: Record<string, unknown>;
  intermediate: Record<string, unknown>;
};

export type NodeDefinition = NodeRegistryEntry & {
  label: string;
  tags: string[];
  execute?: (context: NodeExecutionContext, node?: WorkflowNode) => unknown;
};

export const nodeRegistry = new Map<string, NodeDefinition>();

function normalizeEntry(entry: NodeRegistryEntry): NodeDefinition {
  return {
    ...entry,
    label: entry.display_name,
    tags: entry.audit_rules ?? []
  };
}

export function setBackendNodeRegistry(entries: Record<string, NodeRegistryEntry>) {
  nodeRegistry.clear();
  for (const entry of Object.values(entries)) {
    nodeRegistry.set(entry.type, normalizeEntry(entry));
  }
}

export function getNodeDefinition(type: string): NodeDefinition | undefined {
  return nodeRegistry.get(type);
}

export function getNodeStatus(type: string): NodeStatus | undefined {
  return nodeRegistry.get(type)?.status;
}

export function getNodeRegistryEntries(): NodeDefinition[] {
  return [...nodeRegistry.values()].sort((a, b) => a.display_name.localeCompare(b.display_name));
}

export function getNodeRegistryTypes(): string[] {
  return getNodeRegistryEntries().map((entry) => entry.type);
}
