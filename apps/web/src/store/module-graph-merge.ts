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
export const EXPRESSION_STATE_SEMANTICS_CONTENT_REVISION =
  "stage7_4_11_expression_state_semantics_v1";
export const PARTICLE_EXPRESSION_RELATIVE_MAPPING_CONTENT_REVISION =
  "stage7_4_11_particle_expression_relative_mapping_v1";

const EXPRESSION_CONTEXT_INPUT_NODE_ID = "expression_context_input";
const RESIDENT_EXPRESSION_NOTES_FIELD_KEY = "resident_expression_notes";
const EXPRESSION_STATE_FIELD_KEY = "expression_state";
const EXPRESSION_INTENSITY_FIELD_KEY = "expression_intensity";
const EXPRESSION_STATE_VALUES = new Set(["neutral", "calm", "caring", "subdued", "joyful"]);
const LEGACY_EXPRESSION_NODE_INDEX = new Map<string, number>([
  ["detail_behavior_input_basis", 0],
  ["detail_behavior_core_rules", 2],
  ["detail_behavior_boundary_limits", 4],
  ["detail_behavior_validation", 6],
  ["detail_behavior_output_expression", 7],
]);
const PARTICLE_VISUAL_CONFIG_INPUT_NODE_ID = "particle_visual_config_input";
const PARTICLE_RESIDENT_DEFAULT_BASE_COLOR_FIELD_KEY = "resident_default_base_color";
const LEGACY_PARTICLE_BASE_COLOR_FIELD_KEYS = new Set(["color", "base_color"]);
const PARTICLE_RELATIVE_FIELD_RANGES: Array<{
  suffix: string;
  minimum: number;
  maximum: number;
}> = [
  { suffix: "_brightness_multiplier", minimum: 0.7, maximum: 1.25 },
  { suffix: "_saturation_multiplier", minimum: 0.65, maximum: 1.2 },
  { suffix: "_color_temperature_offset", minimum: -0.15, maximum: 0.15 },
  { suffix: "_energy_multiplier", minimum: 0.7, maximum: 1.25 },
  { suffix: "_motion_speed_multiplier", minimum: 0.75, maximum: 1.2 },
  { suffix: "_diffusion_multiplier", minimum: 0.75, maximum: 1.25 },
];
const LEGACY_PARTICLE_DIRECT_DATA_RESERVED_KEYS = new Set([
  "parent_module",
  "catalog_preconfigured",
  "module_instance_id",
  "catalog_module_id",
  "catalog_node_id",
  "node_type",
  "layer_id",
  "module_id",
  "params",
  "fields",
  "outputs",
  "metadata",
  "i18n_keys",
  "ui_name",
  "ui_color",
  "ui_tags",
  "ui_group",
  "references",
  "available_modules",
  "source_layer_id",
  "source_module_id",
  "source_node_id",
  "source_field_path",
  "reference_type",
  "required",
  "export_name",
  "export_description",
  "export_scope",
  "export_scopes",
  "export_fields",
]);
const LEGACY_PARTICLE_PARAM_RESERVED_KEYS = new Set([
  "fields",
  "legacy_fields",
  "legacy_data_fields",
  "field_registry",
  "mode",
  "content_revision",
  "references",
  "configuration_only",
  "config_mode",
  "input",
  "outputs",
  "output_key",
  "output_schema",
  "reference_input",
  "reference_ids",
  "checkbox_config",
  "checklist_config",
]);

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

export type ExpressionStateSemanticsGraph = {
  nodes: unknown[];
  edges: unknown[];
};

function expressionGraphSchemaNode(value: unknown): Record<string, unknown> | null {
  if (!isRecord(value)) {
    return null;
  }
  const outerData = isRecord(value.data) ? value.data : {};
  return isRecord(outerData.schemaNode) ? outerData.schemaNode : value;
}

function expressionGraphNodeData(value: unknown): Record<string, unknown> {
  const schemaNode = expressionGraphSchemaNode(value);
  return schemaNode && isRecord(schemaNode.data) ? schemaNode.data : {};
}

function expressionGraphCatalogNodeId(value: unknown): string {
  const schemaNode = expressionGraphSchemaNode(value);
  const data = expressionGraphNodeData(value);
  return normalizeCatalogNodeId(data.catalog_node_id || schemaNode?.node_id || (isRecord(value) ? value.id : ""));
}

function expressionGraphNodeParams(value: unknown): Record<string, unknown> {
  const data = expressionGraphNodeData(value);
  return isRecord(data.params) ? data.params : {};
}

function expressionGraphNodeFields(value: unknown): Record<string, unknown>[] {
  const data = expressionGraphNodeData(value);
  const params = expressionGraphNodeParams(value);
  if (Array.isArray(params.fields)) {
    return params.fields.filter(isRecord);
  }
  return Array.isArray(data.fields) ? data.fields.filter(isRecord) : [];
}

function expressionFieldKey(field: Record<string, unknown>): string {
  return String(field.field_key || field.field_id || "");
}

function expressionFieldValue(field: Record<string, unknown>): unknown {
  return "field_value" in field ? field.field_value : field.value;
}

function setExpressionFieldValue(field: Record<string, unknown>, value: unknown) {
  const valueKey = "field_value" in field ? "field_value" : "value";
  return { ...field, [valueKey]: value };
}

function expressionGraphNodePosition(value: unknown): Record<string, unknown> | null {
  if (!isRecord(value)) {
    return null;
  }
  if (isRecord(value.position)) {
    return value.position;
  }
  const schemaNode = expressionGraphSchemaNode(value);
  return schemaNode && isRecord(schemaNode.position) ? schemaNode.position : null;
}

function expressionGraphNodeUiName(value: unknown): string {
  const data = expressionGraphNodeData(value);
  return typeof data.ui_name === "string" ? data.ui_name : "";
}

function setExpressionGraphNodePosition(value: Record<string, unknown>, position: Record<string, unknown>) {
  value.position = cloneJsonValue(position);
  const schemaNode = expressionGraphSchemaNode(value);
  if (schemaNode && schemaNode !== value) {
    schemaNode.position = cloneJsonValue(position);
  }
}

function setExpressionGraphNodeUiName(value: Record<string, unknown>, uiName: string) {
  const schemaNode = expressionGraphSchemaNode(value);
  if (!schemaNode) {
    return;
  }
  const data = isRecord(schemaNode.data) ? { ...schemaNode.data } : {};
  data.ui_name = uiName;
  schemaNode.data = data;
}

function setExpressionGraphNodeFields(value: Record<string, unknown>, fields: Record<string, unknown>[]) {
  const schemaNode = expressionGraphSchemaNode(value);
  if (!schemaNode) {
    return;
  }
  const data = isRecord(schemaNode.data) ? { ...schemaNode.data } : {};
  const params = isRecord(data.params) ? { ...data.params } : {};
  params.fields = cloneJsonValue(fields);
  data.params = params;
  if (Array.isArray(data.fields)) {
    data.fields = cloneJsonValue(fields);
  }
  schemaNode.data = data;
}

function legacyExpressionCustomText(nodes: unknown[]): string[] {
  const values: string[] = [];
  for (const node of nodes) {
    const params = expressionGraphNodeParams(node);
    for (const candidate of [params.checkbox_config, params.checklist_config]) {
      if (!isRecord(candidate) || typeof candidate.custom_text !== "string") {
        continue;
      }
      const text = candidate.custom_text.trim();
      if (text && !values.includes(text)) {
        values.push(text);
      }
    }
  }
  return values;
}

function mergeResidentExpressionNotes(
  fields: Record<string, unknown>[],
  legacyNotes: string[]
): Record<string, unknown>[] {
  if (!legacyNotes.length) {
    return fields;
  }
  return fields.map((field) => {
    if (expressionFieldKey(field) !== RESIDENT_EXPRESSION_NOTES_FIELD_KEY) {
      return field;
    }
    const current = expressionFieldValue(field);
    const values = [typeof current === "string" ? current.trim() : "", ...legacyNotes]
      .filter(Boolean)
      .filter((item, index, items) => items.indexOf(item) === index);
    return setExpressionFieldValue(field, values.join("\n\n"));
  });
}

function normalizeExpressionStateFields(fields: Record<string, unknown>[]): Record<string, unknown>[] {
  return fields.map((field) => {
    const fieldKey = expressionFieldKey(field);
    const current = expressionFieldValue(field);
    if (fieldKey === EXPRESSION_STATE_FIELD_KEY) {
      return setExpressionFieldValue(
        field,
        typeof current === "string" && EXPRESSION_STATE_VALUES.has(current) ? current : "neutral"
      );
    }
    if (fieldKey === EXPRESSION_INTENSITY_FIELD_KEY) {
      const parsed = typeof current === "number"
        ? current
        : typeof current === "string" && current.trim()
          ? Number(current)
          : Number.NaN;
      return setExpressionFieldValue(
        field,
        Number.isFinite(parsed) && parsed >= 0 && parsed <= 1 ? parsed : 0.0
      );
    }
    return field;
  });
}

/**
 * Rebuild the catalog-owned Stage 7.4.11 expression graph once while retaining
 * resident-authored field values and editor-only layout/name customizations.
 */
export function migrateExpressionStateSemanticsGraph(
  stored: ExpressionStateSemanticsGraph,
  seed: ExpressionStateSemanticsGraph
): { value: ExpressionStateSemanticsGraph; migrated: boolean } {
  const seedInput = seed.nodes.find(
    (node) => expressionGraphCatalogNodeId(node) === EXPRESSION_CONTEXT_INPUT_NODE_ID
  );
  const seedRevision = expressionGraphNodeParams(seedInput).content_revision;
  if (seedRevision !== EXPRESSION_STATE_SEMANTICS_CONTENT_REVISION) {
    return { value: stored, migrated: false };
  }

  const storedInput = stored.nodes.find(
    (node) => expressionGraphCatalogNodeId(node) === EXPRESSION_CONTEXT_INPUT_NODE_ID
  );
  if (expressionGraphNodeParams(storedInput).content_revision === seedRevision) {
    return { value: stored, migrated: false };
  }

  const storedByCatalogId = new Map(
    stored.nodes
      .map((node) => [expressionGraphCatalogNodeId(node), node] as const)
      .filter(([nodeId]) => Boolean(nodeId))
  );
  const legacyNodeBySeedIndex = new Map<number, unknown>();
  for (const [legacyNodeId, seedIndex] of LEGACY_EXPRESSION_NODE_INDEX) {
    const legacyNode = storedByCatalogId.get(legacyNodeId);
    if (legacyNode) {
      legacyNodeBySeedIndex.set(seedIndex, legacyNode);
    }
  }

  const allStoredFields = stored.nodes.flatMap(expressionGraphNodeFields);
  const storedFieldByKey = new Map(
    allStoredFields
      .map((field) => [expressionFieldKey(field), field] as const)
      .filter(([fieldKey]) => Boolean(fieldKey))
  );
  const seedFieldKeys = new Set(seed.nodes.flatMap(expressionGraphNodeFields).map(expressionFieldKey).filter(Boolean));
  const customFields = allStoredFields.filter(
    (field, index) => {
      const fieldKey = expressionFieldKey(field);
      return Boolean(fieldKey) &&
        !seedFieldKeys.has(fieldKey) &&
        allStoredFields.findIndex((candidate) => expressionFieldKey(candidate) === fieldKey) === index;
    }
  );
  const customText = legacyExpressionCustomText(stored.nodes);

  const nodes = seed.nodes.map((seedNode, seedIndex) => {
    const nextNode = cloneJsonValue(seedNode) as Record<string, unknown>;
    const catalogNodeId = expressionGraphCatalogNodeId(seedNode);
    const currentNode = storedByCatalogId.get(catalogNodeId) ?? legacyNodeBySeedIndex.get(seedIndex);
    const currentPosition = expressionGraphNodePosition(currentNode);
    if (currentPosition) {
      setExpressionGraphNodePosition(nextNode, currentPosition);
    }
    const uiName = expressionGraphNodeUiName(currentNode);
    if (uiName) {
      setExpressionGraphNodeUiName(nextNode, uiName);
    }

    const seedFields = expressionGraphNodeFields(seedNode);
    if (!seedFields.length) {
      return nextNode;
    }
    const currentFieldByKey = new Map(
      expressionGraphNodeFields(currentNode)
        .map((field) => [expressionFieldKey(field), field] as const)
        .filter(([fieldKey]) => Boolean(fieldKey))
    );
    const existingFields = seedFields
      .map((field) => currentFieldByKey.get(expressionFieldKey(field)) ?? storedFieldByKey.get(expressionFieldKey(field)))
      .filter((field): field is Record<string, unknown> => Boolean(field));
    let mergedFields = mergeCatalogFieldsPreservingValues(seedFields, existingFields);
    if (catalogNodeId === EXPRESSION_CONTEXT_INPUT_NODE_ID) {
      mergedFields = normalizeExpressionStateFields(
        mergeResidentExpressionNotes(
          [...mergedFields, ...customFields.map((field) => cloneJsonValue(field))],
          customText
        )
      );
    }
    setExpressionGraphNodeFields(nextNode, mergedFields);
    return nextNode;
  });

  const value = {
    nodes,
    edges: cloneJsonValue(seed.edges),
  };
  return {
    value,
    migrated: stableComparableValue(value) !== stableComparableValue(stored),
  };
}

export type ParticleExpressionRelativeMappingGraph = {
  nodes: unknown[];
  edges: unknown[];
};

function particleGraphSchemaNode(value: unknown): Record<string, unknown> | null {
  if (!isRecord(value)) {
    return null;
  }
  const outerData = isRecord(value.data) ? value.data : {};
  return isRecord(outerData.schemaNode) ? outerData.schemaNode : value;
}

function particleGraphNodeData(value: unknown): Record<string, unknown> {
  const schemaNode = particleGraphSchemaNode(value);
  return schemaNode && isRecord(schemaNode.data) ? schemaNode.data : {};
}

function particleGraphCatalogNodeId(value: unknown): string {
  const schemaNode = particleGraphSchemaNode(value);
  const data = particleGraphNodeData(value);
  return normalizeCatalogNodeId(
    data.catalog_node_id || schemaNode?.node_id || (isRecord(value) ? value.id : "")
  );
}

function particleGraphNodeParams(value: unknown): Record<string, unknown> {
  const data = particleGraphNodeData(value);
  return isRecord(data.params) ? data.params : {};
}

function particleGraphNodeFields(value: unknown): Record<string, unknown>[] {
  const data = particleGraphNodeData(value);
  const params = particleGraphNodeParams(value);
  if (Array.isArray(params.fields)) {
    return params.fields.filter(isRecord);
  }
  return Array.isArray(data.fields) ? data.fields.filter(isRecord) : [];
}

function particleFieldKey(field: Record<string, unknown>): string {
  return String(field.field_key || field.field_id || "");
}

function particleFieldValue(field: Record<string, unknown>): unknown {
  return "field_value" in field ? field.field_value : field.value;
}

function setParticleFieldValue(field: Record<string, unknown>, value: unknown) {
  const valueKey = "field_value" in field ? "field_value" : "value";
  return { ...field, [valueKey]: cloneJsonValue(value) };
}

function particleGraphNodePosition(value: unknown): Record<string, unknown> | null {
  if (!isRecord(value)) {
    return null;
  }
  if (isRecord(value.position)) {
    return value.position;
  }
  const schemaNode = particleGraphSchemaNode(value);
  return schemaNode && isRecord(schemaNode.position) ? schemaNode.position : null;
}

function particleGraphNodeUiName(value: unknown): string {
  const data = particleGraphNodeData(value);
  return typeof data.ui_name === "string" ? data.ui_name : "";
}

function setParticleGraphNodePosition(
  value: Record<string, unknown>,
  position: Record<string, unknown>
) {
  value.position = cloneJsonValue(position);
  const schemaNode = particleGraphSchemaNode(value);
  if (schemaNode && schemaNode !== value) {
    schemaNode.position = cloneJsonValue(position);
  }
}

function setParticleGraphNodeUiName(value: Record<string, unknown>, uiName: string) {
  const schemaNode = particleGraphSchemaNode(value);
  if (!schemaNode) {
    return;
  }
  const data = isRecord(schemaNode.data) ? { ...schemaNode.data } : {};
  data.ui_name = uiName;
  schemaNode.data = data;
}

function setParticleGraphNodeFields(
  value: Record<string, unknown>,
  fields: Record<string, unknown>[]
) {
  const schemaNode = particleGraphSchemaNode(value);
  if (!schemaNode) {
    return;
  }
  const data = isRecord(schemaNode.data) ? { ...schemaNode.data } : {};
  const params = isRecord(data.params) ? { ...data.params } : {};
  params.fields = cloneJsonValue(fields);
  data.params = params;
  if (Array.isArray(data.fields)) {
    data.fields = cloneJsonValue(fields);
  }
  schemaNode.data = data;
}

function particleValueIsMissing(value: unknown): boolean {
  return value === undefined || value === null || (typeof value === "string" && value === "");
}

function particleLegacyBaseColor(nodes: unknown[], fields: Record<string, unknown>[]): unknown {
  for (const fieldKey of ["base_color", "color"]) {
    const field = fields.find(
      (candidate) =>
        particleFieldKey(candidate) === fieldKey &&
        !particleValueIsMissing(particleFieldValue(candidate))
    );
    if (field) {
      return particleFieldValue(field);
    }
    for (const node of nodes) {
      const data = particleGraphNodeData(node);
      const params = particleGraphNodeParams(node);
      for (const source of [data, params]) {
        if (!particleValueIsMissing(source[fieldKey])) {
          return source[fieldKey];
        }
      }
    }
  }
  return undefined;
}

function particleCustomFieldType(value: unknown): string {
  if (typeof value === "number") {
    return "number";
  }
  if (typeof value === "boolean") {
    return "boolean";
  }
  if (Array.isArray(value)) {
    return "list";
  }
  if (isRecord(value)) {
    return "object";
  }
  return typeof value === "string" && (value.length > 80 || value.includes("\n"))
    ? "long_text"
    : "text";
}

function particleLegacyDirectCustomFields(
  nodes: unknown[],
  knownFieldKeys: Set<string>
): Record<string, unknown>[] {
  const fields: Record<string, unknown>[] = [];
  const captured = new Set(knownFieldKeys);
  const capture = (fieldKey: string, value: unknown) => {
    if (
      !fieldKey ||
      captured.has(fieldKey) ||
      LEGACY_PARTICLE_BASE_COLOR_FIELD_KEYS.has(fieldKey) ||
      particleValueIsMissing(value)
    ) {
      return;
    }
    captured.add(fieldKey);
    fields.push({
      field_key: fieldKey,
      field_name: fieldKey,
      field_value: cloneJsonValue(value),
      field_type: particleCustomFieldType(value),
      description: "",
      dr_mapping: `payload.modules.particle_avatar.config.${fieldKey}`,
      reference_enabled: false,
      required: false,
      field_name_custom: true,
      description_custom: true,
    });
  };
  const captureUnique = (baseFieldKey: string, value: unknown) => {
    if (particleValueIsMissing(value)) {
      return;
    }
    let fieldKey = baseFieldKey;
    let suffix = 2;
    while (captured.has(fieldKey)) {
      fieldKey = `${baseFieldKey}_${suffix}`;
      suffix += 1;
    }
    capture(fieldKey, value);
  };

  for (const node of nodes) {
    const data = particleGraphNodeData(node);
    for (const [fieldKey, value] of Object.entries(data)) {
      if (!LEGACY_PARTICLE_DIRECT_DATA_RESERVED_KEYS.has(fieldKey)) {
        capture(fieldKey, value);
      }
    }
    const params = particleGraphNodeParams(node);
    for (const [fieldKey, value] of Object.entries(params)) {
      if (!LEGACY_PARTICLE_PARAM_RESERVED_KEYS.has(fieldKey)) {
        capture(fieldKey, value);
      }
    }
    for (const configKey of ["checkbox_config", "checklist_config"]) {
      const config = params[configKey];
      if (isRecord(config)) {
        captureUnique("legacy_custom_text", config.custom_text);
      }
    }
  }
  return fields;
}

function normalizeParticleRelativeFields(
  fields: Record<string, unknown>[],
  seedFields: Record<string, unknown>[]
): Record<string, unknown>[] {
  const seedByKey = new Map(seedFields.map((field) => [particleFieldKey(field), field]));
  return fields.map((field) => {
    const fieldKey = particleFieldKey(field);
    const seedField = seedByKey.get(fieldKey);
    if (!seedField) {
      return field;
    }
    const limits = PARTICLE_RELATIVE_FIELD_RANGES.find(({ suffix }) =>
      fieldKey.endsWith(suffix)
    );
    if (!limits) {
      return field;
    }
    const current = particleFieldValue(field);
    const parsed =
      typeof current === "number"
        ? current
        : typeof current === "string" && current.trim()
          ? Number(current)
          : Number.NaN;
    const seedDefault = particleFieldValue(seedField);
    const normalized = Number.isFinite(parsed)
      ? Math.min(limits.maximum, Math.max(limits.minimum, parsed))
      : seedDefault;
    return setParticleFieldValue(field, normalized);
  });
}

/**
 * Rebuild the catalog-owned Stage 7.4.11 particle configuration graph once.
 * Catalog structure comes from the seed; resident-authored values and editor
 * layout remain resident-owned.
 */
export function migrateParticleExpressionRelativeMappingGraph(
  stored: ParticleExpressionRelativeMappingGraph,
  seed: ParticleExpressionRelativeMappingGraph
): { value: ParticleExpressionRelativeMappingGraph; migrated: boolean } {
  const seedInput = seed.nodes.find(
    (node) => particleGraphCatalogNodeId(node) === PARTICLE_VISUAL_CONFIG_INPUT_NODE_ID
  );
  const seedRevision = particleGraphNodeParams(seedInput).content_revision;
  if (seedRevision !== PARTICLE_EXPRESSION_RELATIVE_MAPPING_CONTENT_REVISION) {
    return { value: stored, migrated: false };
  }

  const storedInput = stored.nodes.find(
    (node) => particleGraphCatalogNodeId(node) === PARTICLE_VISUAL_CONFIG_INPUT_NODE_ID
  );
  if (particleGraphNodeParams(storedInput).content_revision === seedRevision) {
    return { value: stored, migrated: false };
  }

  const storedByCatalogId = new Map(
    stored.nodes
      .map((node) => [particleGraphCatalogNodeId(node), node] as const)
      .filter(([nodeId]) => Boolean(nodeId))
  );
  const allStoredFields = stored.nodes.flatMap(particleGraphNodeFields);
  const storedFieldByKey = new Map<string, Record<string, unknown>>();
  for (const field of allStoredFields) {
    const fieldKey = particleFieldKey(field);
    if (fieldKey && !storedFieldByKey.has(fieldKey)) {
      storedFieldByKey.set(fieldKey, field);
    }
  }
  const existingFields = [
    ...storedFieldByKey.values(),
    ...particleLegacyDirectCustomFields(stored.nodes, new Set(storedFieldByKey.keys())),
  ].filter((field) => !LEGACY_PARTICLE_BASE_COLOR_FIELD_KEYS.has(particleFieldKey(field)));
  const residentDefaultField = existingFields.find(
    (field) =>
      particleFieldKey(field) === PARTICLE_RESIDENT_DEFAULT_BASE_COLOR_FIELD_KEY
  );
  const hasResidentDefaultBaseColor =
    residentDefaultField !== undefined &&
    !particleValueIsMissing(particleFieldValue(residentDefaultField));
  const legacyBaseColor = particleLegacyBaseColor(stored.nodes, allStoredFields);

  const nodes = seed.nodes.map((seedNode, seedIndex) => {
    const nextNode = cloneJsonValue(seedNode) as Record<string, unknown>;
    const catalogNodeId = particleGraphCatalogNodeId(seedNode);
    const currentNode = storedByCatalogId.get(catalogNodeId) ?? stored.nodes[seedIndex];
    const currentPosition = particleGraphNodePosition(currentNode);
    if (currentPosition) {
      setParticleGraphNodePosition(nextNode, currentPosition);
    }
    const uiName = particleGraphNodeUiName(currentNode);
    if (uiName) {
      setParticleGraphNodeUiName(nextNode, uiName);
    }

    const nodeSeedFields = particleGraphNodeFields(seedNode);
    if (!nodeSeedFields.length) {
      return nextNode;
    }
    let mergedFields = mergeCatalogFieldsPreservingValues(nodeSeedFields, existingFields);
    if (
      catalogNodeId === PARTICLE_VISUAL_CONFIG_INPUT_NODE_ID &&
      !hasResidentDefaultBaseColor &&
      !particleValueIsMissing(legacyBaseColor)
    ) {
      mergedFields = mergedFields.map((field) =>
        particleFieldKey(field) === PARTICLE_RESIDENT_DEFAULT_BASE_COLOR_FIELD_KEY
          ? setParticleFieldValue(field, legacyBaseColor)
          : field
      );
    }
    mergedFields = normalizeParticleRelativeFields(mergedFields, nodeSeedFields);
    setParticleGraphNodeFields(nextNode, mergedFields);
    return nextNode;
  });

  const value = {
    nodes,
    edges: cloneJsonValue(seed.edges),
  };
  return {
    value,
    migrated: stableComparableValue(value) !== stableComparableValue(stored),
  };
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
