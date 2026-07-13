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

function cloneJsonValue<T>(value: T): T {
  return value === undefined ? value : JSON.parse(JSON.stringify(value)) as T;
}

export function normalizeCatalogNodeId(value: unknown): string {
  return String(value ?? "").split("::").pop() ?? "";
}

export function mergeChecklistTemplateDefaults(
  storedConfig: Record<string, unknown> | null | undefined,
  seedConfig: Record<string, unknown>
): Record<string, unknown> {
  if (!storedConfig) {
    return cloneJsonValue(seedConfig);
  }
  const merged = cloneJsonValue(storedConfig);
  for (const key of ["default_options", "default_selected_options"] as const) {
    if (key in seedConfig) {
      merged[key] = cloneJsonValue(seedConfig[key]);
    }
  }
  return merged;
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

export type AvailableModuleReferenceSource = {
  source_layer_id: string;
  source_module_id: string;
  source_node_ids: string[];
  reference_type: "references" | "constrains";
};

function referenceRecord(value: unknown): Record<string, unknown> | null {
  return value && typeof value === "object" && !Array.isArray(value)
    ? value as Record<string, unknown>
    : null;
}

export function mergeAvailableModuleReferencePointers(
  currentReferences: unknown,
  availableSources: AvailableModuleReferenceSource[]
) {
  const references = Array.isArray(currentReferences)
    ? currentReferences.map(referenceRecord).filter((item): item is Record<string, unknown> => Boolean(item))
    : [];
  let addedCount = 0;
  let repairedCount = 0;

  for (const source of availableSources) {
    const preferredNodeId = source.source_node_ids[0];
    if (!preferredNodeId) {
      continue;
    }
    const existingIndex = references.findIndex(
      (reference) =>
        reference.source_layer_id === source.source_layer_id &&
        reference.source_module_id === source.source_module_id
    );
    if (existingIndex < 0) {
      references.push({
        source_layer_id: source.source_layer_id,
        source_module_id: source.source_module_id,
        source_node_id: preferredNodeId,
        source_scope: "module",
        source_field_paths: [],
        reference_type: source.reference_type,
        required: true,
      });
      addedCount += 1;
      continue;
    }

    const existing = references[existingIndex];
    const currentNodeId = typeof existing.source_node_id === "string" ? existing.source_node_id : "";
    if (!source.source_node_ids.includes(currentNodeId)) {
      references[existingIndex] = {
        ...existing,
        source_node_id: preferredNodeId,
      };
      repairedCount += 1;
    }
  }

  return {
    references,
    addedCount,
    repairedCount,
    changed: addedCount > 0 || repairedCount > 0,
  };
}
