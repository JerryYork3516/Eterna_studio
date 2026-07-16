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

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value && typeof value === "object" && !Array.isArray(value));
}

export function normalizeFirstInteractionEnabled(value: unknown): unknown {
  if (!isRecord(value) || Object.prototype.hasOwnProperty.call(value, "enabled")) {
    return value;
  }
  return { ...value, enabled: true };
}

export function updateFirstInteractionEnabled(value: unknown, enabled: boolean): Record<string, unknown> {
  return { ...(isRecord(value) ? value : {}), enabled };
}

export function firstInteractionEnabledValue(value: unknown): boolean {
  return isRecord(value) && typeof value.enabled === "boolean" ? value.enabled : true;
}

export const LINXUAN_RESIDENT_ID = "dr_eterna_hum_cn_xian_linxuan_0001";
export const STAGE7_4_8_FIRST_INTERACTION_ENABLED_MIGRATION =
  "stage7_4_8_first_interaction_enabled_v1";
export const STAGE7_4_8_FIRST_GREETING_CONTENT_MIGRATION =
  "stage7_4_8_first_greeting_integrity_v1";
export const REMOVED_LINXUAN_FIRST_GREETING_VARIANT =
  "你好，我是林瑄。今天开始，我们可以慢慢熟悉。";

export function migrateLinxuanFirstInteractionEnabledValue(
  residentId: string,
  markerApplied: boolean,
  value: unknown
): { value: unknown; migrated: boolean; markComplete: boolean } {
  if (residentId !== LINXUAN_RESIDENT_ID || markerApplied) {
    return { value, migrated: false, markComplete: false };
  }
  const migratedValue = updateFirstInteractionEnabled(value, true);
  return {
    value: migratedValue,
    migrated: stableComparableValue(migratedValue) !== stableComparableValue(value),
    markComplete: true,
  };
}

export function migrateLinxuanFirstGreetingValue(
  residentId: string,
  markerApplied: boolean,
  value: unknown
): { value: unknown; migrated: boolean; markComplete: boolean } {
  if (
    residentId !== LINXUAN_RESIDENT_ID ||
    markerApplied ||
    !isRecord(value) ||
    !Array.isArray(value.variants)
  ) {
    return { value, migrated: false, markComplete: false };
  }
  const variants = value.variants.filter(
    (variant) => variant !== REMOVED_LINXUAN_FIRST_GREETING_VARIANT
  );
  const migratedValue = {
    ...value,
    content_status: variants.length > 0 ? "authored" : "pending_authoring",
    variants,
  };
  return {
    value: migratedValue,
    migrated: stableComparableValue(migratedValue) !== stableComparableValue(value),
    markComplete: true,
  };
}

function stableComparableValue(value: unknown): string {
  return JSON.stringify(value ?? null);
}

export function normalizeFirstInteractionMaxActivePrompts(value: unknown): unknown {
  if (!isRecord(value)) {
    return value;
  }
  const scenes = isRecord(value.scenes) ? value.scenes : {};
  const userSilence = isRecord(scenes.user_silence) ? scenes.user_silence : {};
  const current = userSilence.max_active_prompts;
  const normalized = Number.isInteger(current) && (current === 0 || current === 1) ? current : 1;
  return {
    ...value,
    scenes: {
      ...scenes,
      user_silence: {
        ...userSilence,
        max_active_prompts: normalized,
      },
    },
  };
}

export function normalizeCatalogNodeId(value: unknown): string {
  return String(value ?? "").split("::").pop() ?? "";
}

export function mergeCatalogFieldsPreservingValues(
  seedFields: Record<string, unknown>[],
  existingFields: Record<string, unknown>[]
) {
  const fieldId = (field: Record<string, unknown>) => String(field.field_id || field.field_key || "");
  const existingById = new Map(existingFields.map((field) => [fieldId(field), field]));
  const seededIds = new Set(seedFields.map(fieldId));
  const merged = seedFields.map((seedField) => {
    const currentFieldId = fieldId(seedField);
    const existingField = existingById.get(currentFieldId);
    const valueKey = "field_value" in seedField ? "field_value" : "value";
    const existingValue = existingField
      ? valueKey in existingField
        ? existingField[valueKey]
        : valueKey === "field_value"
          ? existingField.value
          : existingField.field_value
      : undefined;
    const preservedValue = existingField ? existingValue : seedField[valueKey];
    return {
      ...cloneJsonValue(seedField),
      [valueKey]: cloneJsonValue(
        currentFieldId === "first_interaction"
          ? normalizeFirstInteractionEnabled(
              normalizeFirstInteractionMaxActivePrompts(preservedValue)
            )
          : preservedValue
      ),
    };
  });
  return [
    ...merged,
    ...existingFields.filter((field) => !seededIds.has(fieldId(field))).map((field) => cloneJsonValue(field)),
  ];
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

function referenceDeclarationKey(reference: Record<string, unknown>) {
  const referenceId = typeof reference.reference_id === "string" ? reference.reference_id : "";
  return referenceId || `${reference.source_layer_id ?? ""}/${reference.source_module_id ?? ""}`;
}

export function mergeCatalogReferenceDeclarations(
  currentReferences: unknown,
  seedReferences: unknown,
  obsoleteSourceModuleIds: string[] = []
) {
  const current = Array.isArray(currentReferences)
    ? currentReferences.map(referenceRecord).filter((item): item is Record<string, unknown> => Boolean(item))
    : [];
  const seeds = Array.isArray(seedReferences)
    ? seedReferences.map(referenceRecord).filter((item): item is Record<string, unknown> => Boolean(item))
    : [];
  const obsoleteModules = new Set(obsoleteSourceModuleIds);
  const matchedCurrent = new Set<number>();
  const references = seeds.map((seed) => {
    const seedId = typeof seed.reference_id === "string" ? seed.reference_id : "";
    const currentIndex = current.findIndex((reference, index) => {
      if (matchedCurrent.has(index)) return false;
      const currentId = typeof reference.reference_id === "string" ? reference.reference_id : "";
      if (seedId && currentId === seedId) return true;
      return (
        reference.source_layer_id === seed.source_layer_id &&
        reference.source_module_id === seed.source_module_id
      );
    });
    if (currentIndex < 0) return cloneJsonValue(seed);
    matchedCurrent.add(currentIndex);
    return { ...cloneJsonValue(current[currentIndex]), ...cloneJsonValue(seed) };
  });
  references.push(
    ...current
      .filter(
        (reference, index) =>
          !matchedCurrent.has(index) &&
          !obsoleteModules.has(String(reference.source_module_id ?? "")) &&
          !seeds.some((seed) => referenceDeclarationKey(seed) === referenceDeclarationKey(reference))
      )
      .map((reference) => cloneJsonValue(reference))
  );
  return {
    references,
    changed: stableComparableValue(references) !== stableComparableValue(current),
  };
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
