export function preserveStoredModuleEdges<T>(storedEdges: T[] | undefined, seedEdges: T[] | undefined): T[] {
  return Array.isArray(storedEdges) ? storedEdges : seedEdges ?? [];
}

export type ModuleNodePosition = { x: number; y: number };

export function preserveStoredModuleNodePosition(
  storedPosition: ModuleNodePosition | null | undefined,
  seedPosition: ModuleNodePosition | undefined
): ModuleNodePosition | undefined {
  return storedPosition ?? seedPosition;
}

function edgeEndpoint(edge: unknown, key: "source" | "target"): string {
  if (!edge || typeof edge !== "object" || Array.isArray(edge)) {
    return "";
  }
  const record = edge as Record<string, unknown>;
  const direct = record[key];
  if (typeof direct === "string") {
    return direct;
  }
  const legacy = record[`${key}_node_id`];
  return typeof legacy === "string" ? legacy : "";
}

export function filterDanglingModuleGraphEdges(nodeIds: Iterable<string>, edges: unknown[] | undefined) {
  const knownNodeIds = new Set(nodeIds);
  const valid: unknown[] = [];
  const pruned: Array<{ source: string; target: string }> = [];

  for (const edge of edges ?? []) {
    const source = edgeEndpoint(edge, "source");
    const target = edgeEndpoint(edge, "target");
    if (!source || !target || !knownNodeIds.has(source) || !knownNodeIds.has(target)) {
      pruned.push({ source, target });
      continue;
    }
    valid.push(edge);
  }

  return { edges: valid, pruned };
}
