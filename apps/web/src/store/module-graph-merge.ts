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

export const LEGACY_DIALOGUE_RUNTIME_PROFILE_ID = "linxuan_daily_companion_v0_1";
export const DIALOGUE_RUNTIME_PROFILE_ID = "dialogue_profile_resident_0001_v0_1";
export const DIALOGUE_RUNTIME_PROFILE_CONTENT_REVISION =
  "stage7_4_10_few_shot_resident_name_decoupling_v1";

const DIALOGUE_RUNTIME_PROFILE_MIGRATED_EXAMPLE_IDS = new Set([
  "ordinary_greeting_01",
  "resident_preference_or_life_tone_02",
]);

export function migrateDialogueRuntimeProfileId(value: unknown): unknown {
  if (value === LEGACY_DIALOGUE_RUNTIME_PROFILE_ID) {
    return DIALOGUE_RUNTIME_PROFILE_ID;
  }
  if (Array.isArray(value)) {
    return value.map(migrateDialogueRuntimeProfileId);
  }
  if (isRecord(value)) {
    return Object.fromEntries(
      Object.entries(value).map(([key, item]) => [key, migrateDialogueRuntimeProfileId(item)])
    );
  }
  return value;
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

export function normalizeEmotionalDialogueExampleIsolation(
  value: unknown,
  seedValue?: unknown
): unknown {
  if (!isRecord(value) || !Array.isArray(value.few_shot_examples)) {
    return value;
  }
  const examples = value.few_shot_examples;
  const recommended = examples.filter(
    (example) => isRecord(example) && example.status === "recommended"
  );
  const prohibited = examples.filter(
    (example) => isRecord(example) && example.status === "prohibited"
  );
  const hasOnlyKnownStatuses = recommended.length + prohibited.length === examples.length;
  const existingNegativeExamples = Array.isArray(value.negative_examples)
    ? value.negative_examples
    : [];
  const needsLegacySplit = prohibited.length > 0 && existingNegativeExamples.length === 0;
  if (prohibited.length && (!hasOnlyKnownStatuses || existingNegativeExamples.length)) {
    return value;
  }

  const seed = isRecord(seedValue) ? seedValue : {};
  const seedRecommendedById = new Map(
    (Array.isArray(seed.few_shot_examples) ? seed.few_shot_examples : [])
      .filter(isRecord)
      .map((example) => [String(example.example_id || ""), example])
  );
  const seedNegativeById = new Map(
    (Array.isArray(seed.negative_examples) ? seed.negative_examples : [])
      .filter(isRecord)
      .map((example) => [String(example.example_id || ""), example])
  );
  const selection = isRecord(value.few_shot_selection) ? value.few_shot_selection : {};
  const seedSelection = isRecord(seed.few_shot_selection) ? seed.few_shot_selection : {};
  const sourceKeys = [
    "source_scope",
    "source_id",
    "source_layer",
    "template_id",
    "override_source",
  ];
  const withMissingSourceMetadata = (
    example: unknown,
    seedExample: Record<string, unknown> | undefined
  ) => {
    if (!isRecord(example) || !seedExample) {
      return example;
    }
    const missingSourceMetadata = Object.fromEntries(
      sourceKeys
        .filter((key) => example[key] === undefined && seedExample[key] !== undefined)
        .map((key) => [key, seedExample[key]])
    );
    return { ...example, ...missingSourceMetadata };
  };
  const generationExamples = needsLegacySplit ? recommended : examples;
  const negativeExamples = needsLegacySplit ? prohibited : existingNegativeExamples;

  return {
    ...value,
    few_shot_selection: {
      ...seedSelection,
      ...selection,
      generation_allowed_statuses: ["recommended"],
      prohibited_examples_usage: "evaluation_only",
      inject_negative_examples: false,
      use_preferred_response_for_generation: true,
    },
    few_shot_examples: generationExamples.map((example) =>
      withMissingSourceMetadata(
        example,
        isRecord(example) ? seedRecommendedById.get(String(example.example_id || "")) : undefined
      )
    ),
    negative_examples: negativeExamples.map((example) => {
      const normalized = withMissingSourceMetadata(
        example,
        isRecord(example) ? seedNegativeById.get(String(example.example_id || "")) : undefined
      );
      return needsLegacySplit && isRecord(normalized)
        ? { ...normalized, usage: "evaluation_only", generation_allowed: false }
        : normalized;
    }),
  };
}

export function migrateDialogueRuntimeProfileFewShotExamples(
  value: unknown,
  seedValue: unknown
): unknown {
  if (!Array.isArray(value) || !Array.isArray(seedValue)) {
    return value;
  }
  const seedById = new Map(
    seedValue
      .filter(isRecord)
      .map((example) => [String(example.example_id || ""), example])
  );
  const migrated = value.map((example) => {
    if (!isRecord(example)) {
      return example;
    }
    const exampleId = String(example.example_id || "");
    const seedExample = seedById.get(exampleId);
    if (!DIALOGUE_RUNTIME_PROFILE_MIGRATED_EXAMPLE_IDS.has(exampleId) || !seedExample) {
      return example;
    }
    return { ...example, ...cloneJsonValue(seedExample) };
  });
  return stableComparableValue(migrated) === stableComparableValue(value) ? value : migrated;
}

export type DialogueRuntimeProfileContentCopies = {
  profileContentRevision?: unknown;
  fields?: Record<string, unknown>[];
  dataFields?: Record<string, unknown>[];
  legacyFields?: Record<string, unknown>[];
  legacyDataFields?: Record<string, unknown>[];
  output?: Record<string, unknown>;
};

export function migrateDialogueRuntimeProfileContentCopies(
  stored: DialogueRuntimeProfileContentCopies,
  seed: DialogueRuntimeProfileContentCopies
): { value: DialogueRuntimeProfileContentCopies; migrated: boolean } {
  if (
    typeof seed.profileContentRevision !== "string" ||
    stored.profileContentRevision === seed.profileContentRevision
  ) {
    return { value: stored, migrated: false };
  }

  const fieldId = (field: Record<string, unknown>) =>
    String(field.field_key || field.field_id || "");
  const fieldValue = (field: Record<string, unknown> | undefined) =>
    field && ("field_value" in field ? field.field_value : field.value);
  const seedFewShotField = seed.fields?.find(
    (field) => fieldId(field) === "few_shot_examples"
  );
  const seedFewShots = fieldValue(seedFewShotField);
  if (!Array.isArray(seedFewShots)) {
    return { value: stored, migrated: false };
  }

  const migrateFields = (fields: Record<string, unknown>[] | undefined) =>
    fields?.map((field) => {
      if (fieldId(field) !== "few_shot_examples") {
        return field;
      }
      const valueKey = "field_value" in field ? "field_value" : "value";
      const currentValue = fieldValue(field);
      return {
        ...field,
        [valueKey]: cloneJsonValue(
          migrateDialogueRuntimeProfileFewShotExamples(currentValue, seedFewShots)
        ),
      };
    });

  const currentOutput = stored.output;
  const output = currentOutput
    ? {
        ...currentOutput,
        few_shot_examples: cloneJsonValue(
          migrateDialogueRuntimeProfileFewShotExamples(
            currentOutput.few_shot_examples ?? seedFewShots,
            seedFewShots
          )
        ),
      }
    : currentOutput;
  const value = {
    ...stored,
    profileContentRevision: seed.profileContentRevision,
    fields: migrateFields(stored.fields),
    dataFields: migrateFields(stored.dataFields),
    legacyFields: migrateFields(stored.legacyFields),
    legacyDataFields: migrateFields(stored.legacyDataFields),
    output,
  };
  return {
    value,
    migrated: stableComparableValue(value) !== stableComparableValue(stored),
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
  const fieldStoredValue = (field: Record<string, unknown> | undefined) =>
    field && ("field_value" in field ? field.field_value : field.value);
  const shouldMigrateDialogueProfileId =
    fieldStoredValue(seedFields.find((field) => fieldId(field) === "profile_id")) ===
      DIALOGUE_RUNTIME_PROFILE_ID &&
    fieldStoredValue(existingById.get("profile_id")) === LEGACY_DIALOGUE_RUNTIME_PROFILE_ID;
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
    const seedValue = seedField[valueKey];
    const preservedValue = shouldMigrateDialogueProfileId
      ? migrateDialogueRuntimeProfileId(existingField ? existingValue : seedValue)
      : existingField
        ? existingValue
        : seedValue;
    return {
      ...cloneJsonValue(seedField),
      [valueKey]: cloneJsonValue(
        currentFieldId === "first_interaction"
          ? normalizeFirstInteractionEnabled(
              normalizeFirstInteractionMaxActivePrompts(preservedValue)
            )
          : currentFieldId === "emotional_dialogue"
            ? normalizeEmotionalDialogueExampleIsolation(preservedValue, seedValue)
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
