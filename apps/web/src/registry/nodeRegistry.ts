import type { NodeInputField, NodeRegistryEntry, NodeStatus } from "@/lib/schema-types";

export type { NodeInputField, NodeRegistryEntry, NodeStatus };

export type NodeDefinition = NodeRegistryEntry & {
  label: string;
  tags: string[];
};

// Frontend cache only. Definitions are hydrated exclusively from
// GET /schema/node-registry-v0.4; no local registry entries live here.
export const nodeRegistry = new Map<string, NodeDefinition>();

const STUDIO_ONLY_NODE_ENTRIES: Record<string, NodeRegistryEntry> = {
  reference_output: {
    type: "reference_output",
    category: "reference",
    display_name: "Reference Output Node",
    description: "Declares module, node, or field outputs that other modules may reference.",
    input_schema: [],
    output_schema: [],
    status: "ready",
    mock_executor: null,
    audit_rules: ["studio_only", "no_runtime_execution"],
    node_role: "reference_output",
    i18n_keys: {
      name: "nodes.referenceOutput.title",
      description: "nodes.referenceOutput.description"
    },
    collapsed_sections: ["advanced", "input_schema", "output_schema", "slot_binding", "runtime"]
  },
  reference_input: {
    type: "reference_input",
    category: "reference",
    display_name: "Reference Input Node",
    description: "Selects modules, nodes, or fields referenced by this module.",
    input_schema: [],
    output_schema: [],
    status: "ready",
    mock_executor: null,
    audit_rules: ["studio_only", "no_runtime_execution"],
    node_role: "reference_input",
    i18n_keys: {
      name: "nodes.referenceInput.title",
      description: "nodes.referenceInput.description"
    },
    collapsed_sections: ["advanced", "input_schema", "output_schema", "slot_binding", "runtime"]
  }
};

function normalizeEntry(entry: NodeRegistryEntry): NodeDefinition {
  return {
    ...entry,
    label: entry.display_name,
    tags: entry.audit_rules ?? []
  };
}

export function setBackendNodeRegistry(entries: Record<string, NodeRegistryEntry>) {
  nodeRegistry.clear();
  for (const entry of [...Object.values(entries), ...Object.values(STUDIO_ONLY_NODE_ENTRIES)]) {
    nodeRegistry.set(entry.type, normalizeEntry(entry));
  }
}

export function getNodeDefinition(type: string): NodeDefinition | undefined {
  return nodeRegistry.get(type);
}

export function getNodeStatus(type: string): string | undefined {
  return nodeRegistry.get(type)?.status;
}

export function getNodeRegistryEntries(): NodeDefinition[] {
  return [...nodeRegistry.values()].sort((a, b) => a.display_name.localeCompare(b.display_name));
}

export function getNodeRegistryTypes(): string[] {
  return getNodeRegistryEntries().map((entry) => entry.type);
}
