import {
  AbstractBustBlueprintValidationError,
  getDefaultAbstractBustBlueprint,
  normalizeAbstractBustBlueprint,
} from "@eterna/shared-schema/abstract-bust-blueprint";

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

export const LEGACY_DIALOGUE_RUNTIME_PROFILE_ID =
  "legacy_daily_companion_v0_1";
const LEGACY_NAMED_DIALOGUE_RUNTIME_PROFILE_ID_PATTERN =
  /^[a-z][a-z0-9_]*_daily_companion_v0_1$/;
export const LEGACY_NUMBERED_DIALOGUE_RUNTIME_PROFILE_ID =
  "dialogue_profile_resident_0001_v0_1";
export const DIALOGUE_RUNTIME_PROFILE_ID = "dialogue_profile_resident_v0_1";
export const DIALOGUE_RUNTIME_PROFILE_CONTENT_REVISION =
  "stage7_4_10_few_shot_resident_name_decoupling_v1";
export const EXPRESSION_STATE_SEMANTICS_CONTENT_REVISION =
  "stage7_4_11_expression_state_semantics_v1";
export const PARTICLE_EXPRESSION_RELATIVE_MAPPING_CONTENT_REVISION =
  "stage7_4_11_particle_expression_relative_mapping_v1";
export const ABSTRACT_BUST_BLUEPRINT_CONTENT_REVISION =
  "stage7_4_15_b1_abstract_bust_blueprint_v0_1";
export const PARTICLE_MAPPING_SOURCE_PRIORITY_FIX_REVISION =
  "stage7_4_11_particle_mapping_source_priority_fix_v1";
export const EXPRESSION_VISUAL_VALIDATION_COMPATIBILITY_REVISION =
  "stage7_4_11_expression_visual_validation_compatibility_v1";
export const STAGE7_4_12_A2_SOURCE_OUTPUT_IDENTITY_CLEANUP_REVISION =
  "stage7_4_12_a2_source_output_identity_cleanup_v1";
export const STAGE7_4_12_A4_COMPATIBILITY_AUTHORITY_STATUS_GOVERNANCE_REVISION =
  "stage7_4_12_a4_compatibility_authority_status_governance_v1";
export const RELATIONSHIP_FORMATION_RULES_CONTENT_REVISION =
  "stage7_4_13_relationship_formation_rules_v0_1";
export const RELATIONSHIP_SINGLE_SOURCE_RUNTIME_STATE_FIX_REVISION =
  "stage7_4_13_relationship_single_source_runtime_state_fix_v1";
export const NARRATIVE_MEMORY_RULES_CONTENT_REVISION =
  "stage7_4_14_narrative_memory_rules_v0_1";
export const NARRATIVE_MEMORY_EXTENSION_COMPATIBILITY_FIX_REVISION =
  "stage7_4_14_narrative_memory_extension_compatibility_fix_v1";

export type Layer8BehaviorTextConfig = {
  nodeId: string;
  checkboxConfig: unknown;
};

export function materializeLayer8BehaviorPolicy(
  seedValue: Record<string, unknown>,
  textConfigs: Layer8BehaviorTextConfig[],
  fieldReferences: Record<string, unknown>[],
  sourceNodeIds: string[]
): Record<string, unknown> {
  const selectedOptions: string[] = [];
  const validationRules: string[] = [];
  const customTexts: string[] = [];
  let presetId = "";
  for (const item of textConfigs) {
    const checkbox = isRecord(item.checkboxConfig)
      ? item.checkboxConfig
      : {};
    if (!Object.keys(checkbox).length) continue;
    if (!presetId && typeof checkbox.preset_id === "string") {
      presetId = checkbox.preset_id;
    }
    let options = Array.isArray(checkbox.selected_options)
      ? checkbox.selected_options.filter(
          (option): option is string =>
            typeof option === "string" && Boolean(option)
        )
      : [];
    if (
      !Array.isArray(checkbox.selected_options) &&
      item.nodeId === "language_behavior_output_expression"
    ) {
      options = (
        Array.isArray(checkbox.default_selected_options)
          ? checkbox.default_selected_options
          : Array.isArray(checkbox.default_options)
            ? checkbox.default_options
                .filter(
                  (option) =>
                    isRecord(option) &&
                    option.default_selected !== false
                )
                .map((option) =>
                  isRecord(option) ? option.option_id : undefined
                )
            : []
      ).filter(
        (option): option is string =>
          typeof option === "string" &&
          Boolean(option) &&
          option !== "occasional_city_imagery"
      );
    }
    selectedOptions.push(...options);
    if (item.nodeId.endsWith("_validation")) {
      validationRules.push(...options);
    }
    if (
      typeof checkbox.custom_text === "string" &&
      checkbox.custom_text.trim()
    ) {
      customTexts.push(checkbox.custom_text.trim());
    }
  }
  return {
    ...cloneJsonValue(seedValue),
    preset_id: presetId || seedValue.preset_id,
    selected_options: [...new Set(selectedOptions)],
    custom_text: customTexts.join("\n\n"),
    field_references: cloneJsonValue(fieldReferences),
    validation_rules: [...new Set(validationRules)],
    source_nodes: [...sourceNodeIds],
  };
}

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
const PARTICLE_EXPRESSION_RELATIVE_MAPPING_NODE_ID =
  "particle_expression_state_relative_mapping";
const PARTICLE_RESIDENT_DEFAULT_BASE_COLOR_FIELD_KEY = "resident_default_base_color";
const ABSTRACT_BUST_BLUEPRINT_FIELD_KEY = "abstract_bust_blueprint";
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
  "abstract_bust_blueprint_content_revision",
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

function migratedDialogueRuntimeProfileId(value: unknown): unknown {
  if (
    (typeof value === "string" &&
      LEGACY_NAMED_DIALOGUE_RUNTIME_PROFILE_ID_PATTERN.test(value)) ||
    value === LEGACY_NUMBERED_DIALOGUE_RUNTIME_PROFILE_ID
  ) {
    return DIALOGUE_RUNTIME_PROFILE_ID;
  }
  return value;
}

function migrateDialogueRuntimeProfileIdentityPaths(
  value: unknown,
  directProfileId: boolean
): unknown {
  if (typeof value === "string") {
    return directProfileId
      ? migratedDialogueRuntimeProfileId(value)
      : value;
  }
  if (Array.isArray(value)) {
    return value.map((item) =>
      migrateDialogueRuntimeProfileIdentityPaths(item, false)
    );
  }
  if (isRecord(value)) {
    const fieldId = String(value.field_key || value.field_id || "");
    const sourceScope = String(value.source_scope || "");
    return Object.fromEntries(
      Object.entries(value).map(([key, item]) => {
        const isProfileIdPath =
          key === "profile_id" ||
          (fieldId === "profile_id" &&
            (key === "field_value" || key === "value")) ||
          (key === "source_id" && sourceScope === "resident_profile");
        return [
          key,
          migrateDialogueRuntimeProfileIdentityPaths(
            item,
            isProfileIdPath
          ),
        ];
      })
    );
  }
  return value;
}

export function migrateDialogueRuntimeProfileId(value: unknown): unknown {
  return migrateDialogueRuntimeProfileIdentityPaths(
    value,
    typeof value === "string"
  );
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
export const STAGE7_4_12_IDENTITY_LITERAL_EXPORT_GATE_FIX_REVISION =
  "stage7_4_12_identity_literal_export_gate_fix_v1";
const FIRST_GREETING_STALE_UNAUTHORED_DESCRIPTION =
  "Optional first-greeting presentation configuration; greeting copy remains unauthored.";
const FIRST_GREETING_AUTHORED_DESCRIPTION =
  "Optional first-greeting presentation configuration; content_status authored indicates that greeting variants have been authored.";
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

function escapeRegularExpression(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function firstGreetingTextContainsIdentityLiteral(
  text: string,
  identityLiterals: string[]
): boolean {
  return identityLiterals.some((literal) =>
    new RegExp(escapeRegularExpression(literal), "iu").test(text)
  );
}

function neutralizeFirstGreetingText(
  text: string,
  identityLiterals: string[]
): string {
  return identityLiterals.reduce((current, literal) => {
    const escaped = escapeRegularExpression(literal);
    return current
      .replace(new RegExp(`，(?:我叫|我是)${escaped}。`, "giu"), "。")
      .replace(new RegExp(`^(?:我叫|我是)${escaped}。`, "giu"), "");
  }, text);
}

export function migrateFirstGreetingIdentityLiterals(
  value: unknown,
  identityLiterals: string[]
): {
  value: unknown;
  migrated: boolean;
  markComplete: boolean;
} {
  if (!isRecord(value) || !Array.isArray(value.variants)) {
    return { value, migrated: false, markComplete: false };
  }
  const literals = Array.from(
    new Set(
      identityLiterals
        .map((literal) => literal.trim())
        .filter(Boolean)
        .sort((left, right) => right.length - left.length)
    )
  );
  if (literals.length === 0) {
    return { value, migrated: false, markComplete: false };
  }
  const variants = value.variants.map((variant) => {
    if (typeof variant === "string") {
      return neutralizeFirstGreetingText(variant, literals);
    }
    if (isRecord(variant) && typeof variant.text === "string") {
      return {
        ...variant,
        text: neutralizeFirstGreetingText(variant.text, literals),
      };
    }
    return variant;
  });
  const hasRemainingLiteral = variants.some((variant) => {
    const text =
      typeof variant === "string"
        ? variant
        : isRecord(variant) && typeof variant.text === "string"
          ? variant.text
          : "";
    return firstGreetingTextContainsIdentityLiteral(text, literals);
  });
  const migratedValue = {
    ...value,
    content_status: variants.length > 0 ? "authored" : "pending_authoring",
    variants,
  };
  return {
    value: migratedValue,
    migrated:
      stableComparableValue(migratedValue) !== stableComparableValue(value),
    markComplete: !hasRemainingLiteral,
  };
}

function firstGreetingIdentityGraphSchemaNode(
  value: unknown
): Record<string, unknown> | null {
  if (!isRecord(value)) {
    return null;
  }
  const wrapperData = isRecord(value.data) ? value.data : {};
  return isRecord(wrapperData.schemaNode)
    ? wrapperData.schemaNode
    : value;
}

function firstGreetingIdentityGraphNodeData(
  schemaNode: Record<string, unknown>
): Record<string, unknown> {
  return isRecord(schemaNode.data)
    ? schemaNode.data
    : schemaNode;
}

function firstGreetingIdentityGraphNodeId(value: unknown): string {
  const schemaNode = firstGreetingIdentityGraphSchemaNode(value);
  if (!schemaNode) {
    return "";
  }
  const data = firstGreetingIdentityGraphNodeData(schemaNode);
  return normalizeCatalogNodeId(
    data.catalog_node_id ||
      data.node_id ||
      schemaNode.node_id ||
      (isRecord(value) ? value.id : "")
  );
}

export function migrateFirstGreetingIdentityLiteralGraph<
  TGraph extends { nodes: unknown[]; edges: unknown[] },
>(
  graph: TGraph,
  identityLiterals: string[]
): {
  value: TGraph;
  migrated: boolean;
  markComplete: boolean;
} {
  let targetFound = false;
  let greetingIsIdentityFree = false;
  let authoritativeGreeting: unknown;
  const fieldSynchronizedNodes = graph.nodes.map((node) => {
    if (
      firstGreetingIdentityGraphNodeId(node) !==
      "visual_style_first_greeting_config"
    ) {
      return node;
    }
    const nextNode = cloneJsonValue(node);
    const schemaNode = firstGreetingIdentityGraphSchemaNode(nextNode);
    if (!schemaNode) {
      return node;
    }
    const data = firstGreetingIdentityGraphNodeData(schemaNode);
    const params = isRecord(data.params) ? { ...data.params } : {};
    if (!Array.isArray(params.fields)) {
      return node;
    }
    const nextFields = params.fields.map((field) => {
      if (
        !isRecord(field) ||
        String(field.field_id || field.field_key || "") !== "first_greeting"
      ) {
        return field;
      }
      targetFound = true;
      const valueKey = "field_value" in field ? "field_value" : "value";
      const migration = migrateFirstGreetingIdentityLiterals(
        field[valueKey],
        identityLiterals
      );
      greetingIsIdentityFree = migration.markComplete;
      authoritativeGreeting = migration.value;
      const description =
        field.description ===
        FIRST_GREETING_STALE_UNAUTHORED_DESCRIPTION
          ? FIRST_GREETING_AUTHORED_DESCRIPTION
          : field.description;
      return migration.migrated ||
        description !== field.description
        ? {
            ...field,
            [valueKey]: migration.value,
            description,
          }
        : field;
    });
    if (!targetFound) {
      return node;
    }
    params.fields = cloneJsonValue(nextFields);
    params.legacy_fields = cloneJsonValue(nextFields);
    params.legacy_data_fields = cloneJsonValue(nextFields);
    params.identity_literal_export_gate_revision =
      STAGE7_4_12_IDENTITY_LITERAL_EXPORT_GATE_FIX_REVISION;
    data.params = params;
    if (Array.isArray(data.fields)) {
      data.fields = cloneJsonValue(nextFields);
    }
    return nextNode;
  });

  let outputSynchronized = false;
  const synchronizedNodes = fieldSynchronizedNodes.map((node) => {
    if (
      authoritativeGreeting === undefined ||
      firstGreetingIdentityGraphNodeId(node) !==
        "visual_style_first_presence_output"
    ) {
      return node;
    }
    const nextNode = cloneJsonValue(node);
    const schemaNode = firstGreetingIdentityGraphSchemaNode(nextNode);
    if (!schemaNode) {
      return node;
    }
    const data = firstGreetingIdentityGraphNodeData(schemaNode);
    const outputs = isRecord(data.outputs) ? data.outputs : null;
    const output = outputs && isRecord(outputs.first_presence_config)
      ? outputs.first_presence_config
      : null;
    if (!outputs || !output) {
      return node;
    }
    data.outputs = {
      ...outputs,
      first_presence_config: {
        ...output,
        first_greeting: cloneJsonValue(authoritativeGreeting),
      },
    };
    outputSynchronized = true;
    return nextNode;
  });
  const value = {
    ...graph,
    nodes: synchronizedNodes,
  } as TGraph;
  return {
    value,
    migrated:
      stableComparableValue(value) !== stableComparableValue(graph),
    markComplete:
      targetFound &&
      greetingIsIdentityFree &&
      outputSynchronized,
  };
}

function stableComparableValue(value: unknown): string {
  return JSON.stringify(value ?? null);
}

export function synchronizeAuthoritativeFieldCompatibilityParams(
  params: Record<string, unknown>
): { value: Record<string, unknown>; migrated: boolean } {
  let authoritativeFields = params.fields;
  if (!Array.isArray(authoritativeFields)) {
    const legacyCandidates = [
      params.legacy_fields,
      params.legacy_data_fields,
    ].filter((value): value is unknown[] => Array.isArray(value));
    const distinctCandidates = new Set(
      legacyCandidates.map((value) => stableComparableValue(value))
    );
    if (legacyCandidates.length === 0 || distinctCandidates.size !== 1) {
      return { value: params, migrated: false };
    }
    authoritativeFields = cloneJsonValue(legacyCandidates[0]);
  }
  const mirrorsMatch =
    Array.isArray(params.legacy_fields) &&
    Array.isArray(params.legacy_data_fields) &&
    stableComparableValue(params.legacy_fields) ===
      stableComparableValue(authoritativeFields) &&
    stableComparableValue(params.legacy_data_fields) ===
      stableComparableValue(authoritativeFields);
  const revisionMatches =
    params.compatibility_authority_status_governance_revision ===
    STAGE7_4_12_A4_COMPATIBILITY_AUTHORITY_STATUS_GOVERNANCE_REVISION;
  if (
    Array.isArray(params.fields) &&
    mirrorsMatch &&
    revisionMatches
  ) {
    return { value: params, migrated: false };
  }
  return {
    value: {
      ...params,
      fields: cloneJsonValue(authoritativeFields),
      legacy_fields: cloneJsonValue(authoritativeFields),
      legacy_data_fields: cloneJsonValue(authoritativeFields),
      compatibility_authority_status_governance_revision:
        STAGE7_4_12_A4_COMPATIBILITY_AUTHORITY_STATUS_GOVERNANCE_REVISION,
    },
    migrated: true,
  };
}

function compileFieldId(
  field: Record<string, unknown>,
  index: number
): string {
  return String(
    field.field_id ||
      field.field_key ||
      field.key ||
      field.id ||
      `field_${index + 1}`
  );
}

export function materializeLegacyCompileFields(
  currentFields: Record<string, unknown>[],
  metadataSources: Record<string, unknown>[][]
): Record<string, unknown>[] {
  const metadataByFieldId = new Map<string, Record<string, unknown>>();
  metadataSources.forEach((fields) => {
    fields.forEach((field, index) => {
      const fieldId = compileFieldId(field, index);
      if (!metadataByFieldId.has(fieldId)) {
        metadataByFieldId.set(fieldId, field);
      }
    });
  });

  return currentFields.map((field, index) => {
    const fieldId = compileFieldId(field, index);
    const metadata = metadataByFieldId.get(fieldId) ?? {};
    const currentI18n = isRecord(field.i18n_keys)
      ? field.i18n_keys
      : {};
    const metadataI18n = isRecord(metadata.i18n_keys)
      ? metadata.i18n_keys
      : {};
    const value =
      "field_value" in field ? field.field_value : field.value;
    return {
      ...cloneJsonValue(metadata),
      ...cloneJsonValue(field),
      field_id: fieldId,
      value,
      required:
        typeof metadata.required === "boolean"
          ? metadata.required
          : typeof field.required === "boolean"
            ? field.required
            : false,
      edit_scope:
        metadata.edit_scope || field.edit_scope || "user_editable",
      update_level:
        metadata.update_level || field.update_level || "versioned_core",
      requires_recompile:
        typeof metadata.requires_recompile === "boolean"
          ? metadata.requires_recompile
          : typeof field.requires_recompile === "boolean"
            ? field.requires_recompile
            : true,
      i18n_keys: {
        ...currentI18n,
        ...metadataI18n,
        label:
          metadataI18n.label ||
          currentI18n.label ||
          `field.identity.${fieldId}.label`,
        placeholder:
          metadataI18n.placeholder ||
          currentI18n.placeholder ||
          `field.identity.${fieldId}.placeholder`,
        help:
          metadataI18n.help ||
          currentI18n.help ||
          `field.identity.${fieldId}.help`,
      },
    };
  });
}

function compatibilityGraphSchemaNode(
  value: unknown
): Record<string, unknown> | null {
  if (!isRecord(value)) {
    return null;
  }
  const outerData = isRecord(value.data) ? value.data : {};
  return isRecord(outerData.schemaNode) ? outerData.schemaNode : value;
}

export function migrateAuthoritativeFieldCompatibilityMirrors<
  TGraph extends { nodes: unknown[]; edges: unknown[] },
>(graph: TGraph): { value: TGraph; migrated: boolean } {
  let migrated = false;
  const nodes = graph.nodes.map((node) => {
    const schemaNode = compatibilityGraphSchemaNode(node);
    const data =
      schemaNode && isRecord(schemaNode.data) ? schemaNode.data : null;
    const params = data && isRecord(data.params) ? data.params : null;
    if (
      !params ||
      !(
        Array.isArray(params.fields) ||
        Array.isArray(params.legacy_fields) ||
        Array.isArray(params.legacy_data_fields)
      )
    ) {
      return node;
    }
    const synchronized =
      synchronizeAuthoritativeFieldCompatibilityParams(params);
    if (!synchronized.migrated) {
      return node;
    }
    const nextNode = cloneJsonValue(node);
    const nextSchemaNode = compatibilityGraphSchemaNode(nextNode);
    if (!nextSchemaNode) {
      return node;
    }
    const nextData = isRecord(nextSchemaNode.data)
      ? { ...nextSchemaNode.data }
      : {};
    const nextParams = isRecord(nextData.params) ? nextData.params : {};
    nextData.params =
      synchronizeAuthoritativeFieldCompatibilityParams(nextParams).value;
    nextSchemaNode.data = nextData;
    migrated = true;
    return nextNode;
  });
  return {
    value: (migrated ? { ...graph, nodes } : graph) as TGraph,
    migrated,
  };
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
  identityCleanupRevision?: unknown;
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
  const contentMigrationNeeded =
    typeof seed.profileContentRevision === "string" &&
    stored.profileContentRevision !== seed.profileContentRevision;
  const identityMigrationNeeded =
    typeof seed.identityCleanupRevision === "string" &&
    stored.identityCleanupRevision !== seed.identityCleanupRevision;
  if (!contentMigrationNeeded && !identityMigrationNeeded) {
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
  if (contentMigrationNeeded && !Array.isArray(seedFewShots)) {
    return { value: stored, migrated: false };
  }

  const migrateFields = (fields: Record<string, unknown>[] | undefined) =>
    fields?.map((field) => {
      const migratedField = (
        identityMigrationNeeded
          ? migrateDialogueRuntimeProfileId(field)
          : cloneJsonValue(field)
      ) as Record<string, unknown>;
      if (
        !contentMigrationNeeded ||
        fieldId(field) !== "few_shot_examples"
      ) {
        return migratedField;
      }
      const valueKey =
        "field_value" in migratedField ? "field_value" : "value";
      const currentValue = fieldValue(migratedField);
      return {
        ...migratedField,
        [valueKey]: cloneJsonValue(
          migrateDialogueRuntimeProfileFewShotExamples(
            currentValue,
            seedFewShots
          )
        ),
      };
    });

  const currentOutput =
    stored.output && identityMigrationNeeded
      ? migrateDialogueRuntimeProfileId(
          stored.output
        ) as Record<string, unknown>
      : stored.output
        ? cloneJsonValue(stored.output)
        : stored.output;
  const output =
    currentOutput && contentMigrationNeeded
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
    profileContentRevision: contentMigrationNeeded
      ? seed.profileContentRevision
      : stored.profileContentRevision,
    identityCleanupRevision: identityMigrationNeeded
      ? seed.identityCleanupRevision
      : stored.identityCleanupRevision,
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
    migrateDialogueRuntimeProfileId(
      fieldStoredValue(existingById.get("profile_id"))
    ) !== fieldStoredValue(existingById.get("profile_id"));
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
    const storedValue = existingField ? existingValue : seedValue;
    const migratedField = shouldMigrateDialogueProfileId
      ? migrateDialogueRuntimeProfileId({
          ...(existingField ?? seedField),
          [valueKey]: storedValue,
        })
      : null;
    const preservedValue =
      shouldMigrateDialogueProfileId && isRecord(migratedField)
        ? migratedField[valueKey]
        : storedValue;
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
      const normalized = typeof current === "string" ? current.trim().toLowerCase() : "";
      return setExpressionFieldValue(
        field,
        EXPRESSION_STATE_VALUES.has(normalized) ? normalized : "neutral"
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
        Number.isFinite(parsed) ? Math.min(1.0, Math.max(0.0, parsed)) : 0.0
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
  const seedValidationRevision =
    expressionGraphNodeParams(seedInput).validation_compatibility_revision;
  if (seedRevision !== EXPRESSION_STATE_SEMANTICS_CONTENT_REVISION) {
    return { value: stored, migrated: false };
  }
  if (
    seedValidationRevision !==
    EXPRESSION_VISUAL_VALIDATION_COMPATIBILITY_REVISION
  ) {
    return { value: stored, migrated: false };
  }

  const storedInput = stored.nodes.find(
    (node) => expressionGraphCatalogNodeId(node) === EXPRESSION_CONTEXT_INPUT_NODE_ID
  );
  if (
    expressionGraphNodeParams(storedInput).content_revision === seedRevision &&
    expressionGraphNodeParams(storedInput).validation_compatibility_revision ===
      seedValidationRevision
  ) {
    return migrateAuthoritativeFieldCompatibilityMirrors(stored);
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
  const synchronized =
    migrateAuthoritativeFieldCompatibilityMirrors(value);
  return {
    value: synchronized.value,
    migrated:
      stableComparableValue(synchronized.value) !==
      stableComparableValue(stored),
  };
}

export type RelationshipFormationRulesGraph = {
  nodes: unknown[];
  edges: unknown[];
};

const RELATIONSHIP_FORMATION_INPUT_NODE_IDS = new Set([
  "user_relationship_config_input",
  "user_relationship_rule_input",
  "relationship_evidence_candidate_input",
]);
const RELATIONSHIP_FORMATION_OUTPUT_NODE_IDS = new Set([
  "user_relationship_config_output",
  "relationship_behavior_config_output",
]);

function synchronizeRelationshipFormationOutputFields(
  node: Record<string, unknown>,
  fields: Record<string, unknown>[]
) {
  if (
    !RELATIONSHIP_FORMATION_OUTPUT_NODE_IDS.has(
      expressionGraphCatalogNodeId(node)
    )
  ) {
    return;
  }
  const fieldValues = Object.fromEntries(
    fields
      .map((field) => [
        expressionFieldKey(field),
        cloneJsonValue(expressionFieldValue(field)),
      ] as const)
      .filter(([fieldKey]) => Boolean(fieldKey))
  );
  const synchronizeOutputs = (outputs: unknown) => {
    if (!isRecord(outputs)) return outputs;
    return Object.fromEntries(
      Object.entries(outputs).map(([key, value]) => [
        key,
        isRecord(value) && isRecord(value.fields)
          ? { ...value, fields: { ...value.fields, ...fieldValues } }
          : value,
      ])
    );
  };
  if (isRecord(node.outputs)) {
    node.outputs = synchronizeOutputs(node.outputs);
  }
  const schemaNode = expressionGraphSchemaNode(node);
  if (!schemaNode) return;
  if (isRecord(schemaNode.outputs)) {
    schemaNode.outputs = synchronizeOutputs(schemaNode.outputs);
  }
  const data = isRecord(schemaNode.data) ? { ...schemaNode.data } : {};
  if (isRecord(data.outputs)) {
    data.outputs = synchronizeOutputs(data.outputs);
    schemaNode.data = data;
  }
}

/**
 * Rebuild the two catalog-owned Layer 11 graphs once while preserving all
 * resident-authored field values and compatibility mirrors. Relationship
 * stage state is deliberately absent: only rule configuration is migrated.
 */
export function migrateRelationshipFormationRulesGraph(
  stored: RelationshipFormationRulesGraph,
  seed: RelationshipFormationRulesGraph
): { value: RelationshipFormationRulesGraph; migrated: boolean } {
  const seedInput = seed.nodes.find((node) =>
    RELATIONSHIP_FORMATION_INPUT_NODE_IDS.has(
      expressionGraphCatalogNodeId(node)
    )
  );
  const seedRevision = expressionGraphNodeParams(seedInput).content_revision;
  if (seedRevision !== RELATIONSHIP_FORMATION_RULES_CONTENT_REVISION) {
    return { value: stored, migrated: false };
  }

  const allStoredFields = stored.nodes.flatMap(expressionGraphNodeFields);
  const storedFieldByKey = new Map(
    allStoredFields
      .map((field) => [expressionFieldKey(field), field] as const)
      .filter(([fieldKey]) => Boolean(fieldKey))
  );
  const storedByCatalogId = new Map(
    stored.nodes
      .map((node) => [expressionGraphCatalogNodeId(node), node] as const)
      .filter(([nodeId]) => Boolean(nodeId))
  );
  const seedFieldKeys = new Set(
    seed.nodes
      .flatMap(expressionGraphNodeFields)
      .map(expressionFieldKey)
      .filter(Boolean)
  );
  const customFields = allStoredFields.filter((field, index) => {
    const fieldKey = expressionFieldKey(field);
    return (
      Boolean(fieldKey) &&
      !seedFieldKeys.has(fieldKey) &&
      allStoredFields.findIndex(
        (candidate) => expressionFieldKey(candidate) === fieldKey
      ) === index
    );
  });
  let authoritativeFields: Record<string, unknown>[] = [];
  const nodes = seed.nodes.map((seedNode) => {
    const nextNode = cloneJsonValue(seedNode) as Record<string, unknown>;
    const catalogNodeId = expressionGraphCatalogNodeId(seedNode);
    const currentNode = storedByCatalogId.get(catalogNodeId);
    const currentPosition = expressionGraphNodePosition(currentNode);
    if (currentPosition) {
      setExpressionGraphNodePosition(nextNode, currentPosition);
    }
    const uiName = expressionGraphNodeUiName(currentNode);
    if (uiName) {
      setExpressionGraphNodeUiName(nextNode, uiName);
    }

    const seedFields = expressionGraphNodeFields(seedNode);
    if (seedFields.length) {
      const currentFields = seedFields
        .map((field) => storedFieldByKey.get(expressionFieldKey(field)))
        .filter((field): field is Record<string, unknown> => Boolean(field));
      let mergedFields = mergeCatalogFieldsPreservingValues(
        seedFields,
        currentFields
      );
      if (RELATIONSHIP_FORMATION_INPUT_NODE_IDS.has(catalogNodeId)) {
        mergedFields = [
          ...mergedFields,
          ...customFields.map((field) => cloneJsonValue(field)),
        ];
        authoritativeFields = mergedFields;
      }
      setExpressionGraphNodeFields(nextNode, mergedFields);
    }
    return nextNode;
  });
  if (authoritativeFields.length) {
    for (const node of nodes) {
      synchronizeRelationshipFormationOutputFields(node, authoritativeFields);
    }
  }
  const rebuilt = {
    nodes,
    edges: cloneJsonValue(seed.edges),
  };
  const synchronized = migrateAuthoritativeFieldCompatibilityMirrors(rebuilt);
  return {
    value: synchronized.value,
    migrated:
      stableComparableValue(synchronized.value) !== stableComparableValue(stored),
  };
}

export type NarrativeMemoryRulesGraph = {
  nodes: unknown[];
  edges: unknown[];
};

const NARRATIVE_MEMORY_INPUT_NODE_IDS = new Set([
  "narrative_event_input",
  "memory_update_request_input",
  "memory_access_request_input",
  // A1 stored instances are recognized and rebuilt to the frozen generic
  // access/update chains from the current catalog seed.
  "narrative_memory_change_input",
  "narrative_memory_request_input",
]);

/**
 * Rebuild the three catalog-owned Layer 5 narrative-memory rule chains once.
 * Any resident-authored field values are retained, while rules and topology
 * come from the current catalog seed. The graph contains policy only.
 */
export function migrateNarrativeMemoryRulesGraph(
  stored: NarrativeMemoryRulesGraph,
  seed: NarrativeMemoryRulesGraph
): { value: NarrativeMemoryRulesGraph; migrated: boolean } {
  const seedInput = seed.nodes.find((node) =>
    NARRATIVE_MEMORY_INPUT_NODE_IDS.has(
      expressionGraphCatalogNodeId(node)
    )
  );
  if (
    expressionGraphNodeParams(seedInput).content_revision !==
    NARRATIVE_MEMORY_EXTENSION_COMPATIBILITY_FIX_REVISION
  ) {
    return { value: stored, migrated: false };
  }

  const allStoredFields = stored.nodes.flatMap(expressionGraphNodeFields);
  const storedFieldByKey = new Map(
    allStoredFields
      .map((field) => [expressionFieldKey(field), field] as const)
      .filter(([fieldKey]) => Boolean(fieldKey))
  );
  const storedByCatalogId = new Map(
    stored.nodes
      .map((node) => [expressionGraphCatalogNodeId(node), node] as const)
      .filter(([nodeId]) => Boolean(nodeId))
  );
  const seedFieldKeys = new Set(
    seed.nodes
      .flatMap(expressionGraphNodeFields)
      .map(expressionFieldKey)
      .filter(Boolean)
  );
  const customFields = allStoredFields.filter((field, index) => {
    const fieldKey = expressionFieldKey(field);
    return (
      Boolean(fieldKey) &&
      !seedFieldKeys.has(fieldKey) &&
      allStoredFields.findIndex(
        (candidate) => expressionFieldKey(candidate) === fieldKey
      ) === index
    );
  });

  const nodes = seed.nodes.map((seedNode) => {
    const nextNode = cloneJsonValue(seedNode) as Record<string, unknown>;
    const catalogNodeId = expressionGraphCatalogNodeId(seedNode);
    const currentNode = storedByCatalogId.get(catalogNodeId);
    const currentPosition = expressionGraphNodePosition(currentNode);
    if (currentPosition) {
      setExpressionGraphNodePosition(nextNode, currentPosition);
    }
    const uiName = expressionGraphNodeUiName(currentNode);
    if (uiName) {
      setExpressionGraphNodeUiName(nextNode, uiName);
    }
    const seedFields = expressionGraphNodeFields(seedNode);
    if (seedFields.length) {
      const currentFields = seedFields
        .map((field) => storedFieldByKey.get(expressionFieldKey(field)))
        .filter((field): field is Record<string, unknown> => Boolean(field));
      setExpressionGraphNodeFields(
        nextNode,
        mergeCatalogFieldsPreservingValues(seedFields, currentFields)
      );
    } else if (
      NARRATIVE_MEMORY_INPUT_NODE_IDS.has(catalogNodeId) &&
      customFields.length
    ) {
      setExpressionGraphNodeFields(
        nextNode,
        customFields.map((field) => cloneJsonValue(field))
      );
    }
    return nextNode;
  });
  const rebuilt = {
    nodes,
    edges: cloneJsonValue(seed.edges),
  };
  const synchronized = migrateAuthoritativeFieldCompatibilityMirrors(rebuilt);
  return {
    value: synchronized.value,
    migrated:
      stableComparableValue(synchronized.value) !==
      stableComparableValue(stored),
  };
}

const RELATIONSHIP_SINGLE_SOURCE_INPUT_NODE_IDS = new Set([
  "relationship_stage_config_input",
  "self_state_input",
]);
const RELATIONSHIP_SINGLE_SOURCE_OUTPUT_NODE_IDS = new Set([
  "relationship_stage_config_output",
  "self_state_output",
]);

export function migrateRelationshipSingleSourceRuntimeStateGraph(
  stored: RelationshipFormationRulesGraph,
  seed: RelationshipFormationRulesGraph
): { value: RelationshipFormationRulesGraph; migrated: boolean } {
  const seedInput = seed.nodes.find((node) =>
    RELATIONSHIP_SINGLE_SOURCE_INPUT_NODE_IDS.has(
      expressionGraphCatalogNodeId(node)
    )
  );
  if (
    expressionGraphNodeParams(seedInput).content_revision !==
    RELATIONSHIP_SINGLE_SOURCE_RUNTIME_STATE_FIX_REVISION
  ) {
    return { value: stored, migrated: false };
  }

  const inputNodeId = expressionGraphCatalogNodeId(seedInput);
  const storedByCatalogId = new Map(
    stored.nodes
      .map((node) => [expressionGraphCatalogNodeId(node), node] as const)
      .filter(([nodeId]) => Boolean(nodeId))
  );
  const seedFields = expressionGraphNodeFields(seedInput);
  const seedKeys = new Set(seedFields.map(expressionFieldKey).filter(Boolean));
  const storedFields = stored.nodes.flatMap(expressionGraphNodeFields);
  const legacyKeys = new Set(
    inputNodeId === "self_state_input"
      ? ["current_relationship_state"]
      : []
  );
  const storedByFieldKey = new Map(
    storedFields
      .map((field) => [expressionFieldKey(field), field] as const)
      .filter(([fieldKey]) => Boolean(fieldKey))
  );
  const customFields = storedFields.filter((field, index) => {
    const fieldKey = expressionFieldKey(field);
    return (
      Boolean(fieldKey) &&
      !seedKeys.has(fieldKey) &&
      !legacyKeys.has(fieldKey) &&
      storedFields.findIndex(
        (candidate) => expressionFieldKey(candidate) === fieldKey
      ) === index
    );
  });
  const authoritativeFields =
    inputNodeId === "relationship_stage_config_input"
      ? [...seedFields.map(cloneJsonValue), ...customFields.map(cloneJsonValue)]
      : [
          ...mergeCatalogFieldsPreservingValues(
            seedFields,
            seedFields
              .map((field) => storedByFieldKey.get(expressionFieldKey(field)))
              .filter(
                (field): field is Record<string, unknown> => Boolean(field)
              )
          ),
          ...customFields.map(cloneJsonValue),
        ];
  const fieldValues = Object.fromEntries(
    authoritativeFields
      .map((field) => [
        expressionFieldKey(field),
        cloneJsonValue(expressionFieldValue(field)),
      ] as const)
      .filter(([fieldKey]) => Boolean(fieldKey))
  );

  const nodes = seed.nodes.map((seedNode) => {
    const nextNode = cloneJsonValue(seedNode) as Record<string, unknown>;
    const catalogNodeId = expressionGraphCatalogNodeId(seedNode);
    const currentNode = storedByCatalogId.get(catalogNodeId);
    const currentPosition = expressionGraphNodePosition(currentNode);
    if (currentPosition) setExpressionGraphNodePosition(nextNode, currentPosition);
    const uiName = expressionGraphNodeUiName(currentNode);
    if (uiName) setExpressionGraphNodeUiName(nextNode, uiName);
    if (catalogNodeId === inputNodeId) {
      setExpressionGraphNodeFields(nextNode, authoritativeFields);
    }
    if (
      RELATIONSHIP_SINGLE_SOURCE_OUTPUT_NODE_IDS.has(catalogNodeId)
    ) {
      const schemaNode = expressionGraphSchemaNode(nextNode);
      if (schemaNode) {
        const data = isRecord(schemaNode.data) ? { ...schemaNode.data } : {};
        const outputs = isRecord(data.outputs) ? { ...data.outputs } : {};
        data.outputs = Object.fromEntries(
          Object.entries(outputs).map(([key, value]) => {
            if (!isRecord(value)) return [key, value];
            const nextOutput: Record<string, unknown> = {
              ...value,
              fields: cloneJsonValue(fieldValues),
              content_revision:
                RELATIONSHIP_SINGLE_SOURCE_RUNTIME_STATE_FIX_REVISION,
            };
            delete nextOutput.current_relationship_state;
            if ("relationship_runtime_state_policy" in fieldValues) {
              nextOutput.relationship_runtime_state_policy = cloneJsonValue(
                fieldValues.relationship_runtime_state_policy
              );
            }
            return [key, nextOutput];
          })
        );
        schemaNode.data = data;
      }
    }
    return nextNode;
  });
  const synchronized = migrateAuthoritativeFieldCompatibilityMirrors({
    nodes,
    edges: cloneJsonValue(seed.edges),
  });
  return {
    value: synchronized.value,
    migrated:
      stableComparableValue(synchronized.value) !== stableComparableValue(stored),
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
  seedFields: Record<string, unknown>[],
  storedFieldKeys: Set<string>
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
    if (limits) {
      const current = particleFieldValue(field);
      const parsed =
        typeof current === "number"
          ? current
          : typeof current === "string" && current.trim()
            ? Number(current)
            : Number.NaN;
      const safeDefault = fieldKey.endsWith("_color_temperature_offset") ? 0.0 : 1.0;
      const normalized =
        storedFieldKeys.has(fieldKey) && Number.isFinite(parsed)
          ? Math.min(limits.maximum, Math.max(limits.minimum, parsed))
          : safeDefault;
      return setParticleFieldValue(field, normalized);
    }

    if (fieldKey === "transition_style") {
      return setParticleFieldValue(field, "smooth");
    }

    if (
      fieldKey !== "transition_duration" &&
      fieldKey !== "minimum_hold_duration"
    ) {
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
    const normalized =
      storedFieldKeys.has(fieldKey) && Number.isFinite(parsed)
        ? Math.min(10.0, Math.max(0.0, parsed))
        : seedDefault;
    return setParticleFieldValue(field, normalized);
  });
}

function normalizeParticleAbstractBustBlueprintField(
  fields: Record<string, unknown>[]
): Record<string, unknown>[] {
  return fields.map((field) => {
    if (particleFieldKey(field) !== ABSTRACT_BUST_BLUEPRINT_FIELD_KEY) {
      return field;
    }
    try {
      return setParticleFieldValue(
        field,
        normalizeAbstractBustBlueprint(particleFieldValue(field))
      );
    } catch (error) {
      if (!(error instanceof AbstractBustBlueprintValidationError)) {
        throw error;
      }
      return setParticleFieldValue(field, getDefaultAbstractBustBlueprint());
    }
  });
}

/**
 * Rebuild the catalog-owned particle configuration graph once for the frozen
 * expression and AbstractBustBlueprint revisions. Catalog structure comes from
 * the seed; resident-authored values and editor layout remain resident-owned.
 */
export function migrateParticleExpressionRelativeMappingGraph(
  stored: ParticleExpressionRelativeMappingGraph,
  seed: ParticleExpressionRelativeMappingGraph
): { value: ParticleExpressionRelativeMappingGraph; migrated: boolean } {
  const seedInput = seed.nodes.find(
    (node) => particleGraphCatalogNodeId(node) === PARTICLE_VISUAL_CONFIG_INPUT_NODE_ID
  );
  const seedMapping = seed.nodes.find(
    (node) =>
      particleGraphCatalogNodeId(node) ===
      PARTICLE_EXPRESSION_RELATIVE_MAPPING_NODE_ID
  );
  const seedRevision = particleGraphNodeParams(seedInput).content_revision;
  const seedAbstractBustRevision =
    particleGraphNodeParams(seedInput).abstract_bust_blueprint_content_revision;
  const seedValidationRevision =
    particleGraphNodeParams(seedInput).validation_compatibility_revision;
  const seedSourcePriorityRevision =
    particleGraphNodeParams(seedMapping).source_priority_revision;
  if (seedRevision !== PARTICLE_EXPRESSION_RELATIVE_MAPPING_CONTENT_REVISION) {
    return { value: stored, migrated: false };
  }
  if (
    seedAbstractBustRevision !==
    ABSTRACT_BUST_BLUEPRINT_CONTENT_REVISION
  ) {
    return { value: stored, migrated: false };
  }
  if (
    seedValidationRevision !==
    EXPRESSION_VISUAL_VALIDATION_COMPATIBILITY_REVISION
  ) {
    return { value: stored, migrated: false };
  }
  if (
    seedSourcePriorityRevision !==
    PARTICLE_MAPPING_SOURCE_PRIORITY_FIX_REVISION
  ) {
    return { value: stored, migrated: false };
  }

  const storedInput = stored.nodes.find(
    (node) => particleGraphCatalogNodeId(node) === PARTICLE_VISUAL_CONFIG_INPUT_NODE_ID
  );
  const storedMapping = stored.nodes.find(
    (node) =>
      particleGraphCatalogNodeId(node) ===
      PARTICLE_EXPRESSION_RELATIVE_MAPPING_NODE_ID
  );
  if (
    particleGraphNodeParams(storedInput).content_revision === seedRevision &&
    particleGraphNodeParams(storedInput)
      .abstract_bust_blueprint_content_revision ===
      seedAbstractBustRevision &&
    particleGraphNodeParams(storedInput).validation_compatibility_revision ===
      seedValidationRevision &&
    particleGraphNodeParams(storedMapping).source_priority_revision ===
      seedSourcePriorityRevision
  ) {
    return migrateAuthoritativeFieldCompatibilityMirrors(stored);
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
  for (const field of particleGraphNodeFields(storedMapping)) {
    const fieldKey = particleFieldKey(field);
    if (
      fieldKey &&
      PARTICLE_RELATIVE_FIELD_RANGES.some(({ suffix }) =>
        fieldKey.endsWith(suffix)
      )
    ) {
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
    mergedFields = normalizeParticleRelativeFields(
      mergedFields,
      nodeSeedFields,
      new Set(storedFieldByKey.keys())
    );
    if (catalogNodeId === PARTICLE_VISUAL_CONFIG_INPUT_NODE_ID) {
      mergedFields = normalizeParticleAbstractBustBlueprintField(mergedFields);
    }
    setParticleGraphNodeFields(nextNode, mergedFields);
    return nextNode;
  });

  const value = {
    nodes,
    edges: cloneJsonValue(seed.edges),
  };
  const synchronized =
    migrateAuthoritativeFieldCompatibilityMirrors(value);
  return {
    value: synchronized.value,
    migrated:
      stableComparableValue(synchronized.value) !==
      stableComparableValue(stored),
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

const LEGACY_MATERIALIZED_REFERENCE_OUTPUT_MODULE_IDS = new Set([
  "language_habit",
  "decision_pattern",
  "interaction_strategy",
  "behavior_habit",
  "emotion_mapper",
  "user_relationship",
  "intimacy_level",
  "event_memory",
  "memory_update",
  "memory_access_control",
]);
const LEGACY_LOCAL_REFERENCE_OUTPUT_ALIASES = new Map([
  [
    "memory_update::narrative_memory_update_reference_output",
    "memory_update_output",
  ],
]);

function compiledModuleGraphNodes(
  module: Record<string, unknown>
): Record<string, unknown>[] {
  const graph = isRecord(module.module_graph) ? module.module_graph : {};
  return Array.isArray(graph.nodes)
    ? graph.nodes.filter(isRecord)
    : [];
}

function isLegacyMaterializedReferenceOutputId(
  sourceNodeId: string,
  sourceLayerId: string,
  sourceModuleId: string
): boolean {
  const prefix =
    `${sourceLayerId}::${sourceModuleId}_reference_output_`;
  if (!sourceNodeId.startsWith(prefix)) {
    return false;
  }
  const suffix = sourceNodeId.slice(prefix.length).split("_");
  return (
    suffix.length === 2 &&
    suffix.every((part) => /^\d+$/.test(part))
  );
}

export function canonicalizeLegacyMaterializedReferencePointers(
  currentReferences: Record<string, unknown>[],
  sourceModules: Record<string, unknown>[]
): {
  references: Record<string, unknown>[];
  repairedCount: number;
} {
  const modulesById = new Map(
    sourceModules
      .map((module) => [String(module.module_id || ""), module] as const)
      .filter(([moduleId]) => Boolean(moduleId))
  );
  let repairedCount = 0;
  const references = currentReferences.map((reference) => {
    const sourceModuleId = String(reference.source_module_id || "");
    const sourceLayerId = String(reference.source_layer_id || "");
    const sourceNodeId = String(reference.source_node_id || "");
    const sourceModule = modulesById.get(sourceModuleId);
    const localPrefix =
      `${sourceLayerId}::${sourceModuleId}::`;
    const localSourceNodeId = sourceNodeId.startsWith(localPrefix)
      ? sourceNodeId.slice(localPrefix.length)
      : sourceNodeId;
    const legacyAliasTarget =
      LEGACY_LOCAL_REFERENCE_OUTPUT_ALIASES.get(
        `${sourceModuleId}::${localSourceNodeId}`
      );
    const isLegacyOutputPointer =
      isLegacyMaterializedReferenceOutputId(
        sourceNodeId,
        sourceLayerId,
        sourceModuleId
      ) || Boolean(legacyAliasTarget);
    if (
      !sourceModule ||
      !LEGACY_MATERIALIZED_REFERENCE_OUTPUT_MODULE_IDS.has(
        sourceModuleId
      ) ||
      String(sourceModule.layer_id || "") !== sourceLayerId ||
      String(reference.source_scope || "module") !== "module" ||
      (Array.isArray(reference.source_field_paths) &&
        reference.source_field_paths.length > 0) ||
      !isLegacyOutputPointer
    ) {
      return cloneJsonValue(reference);
    }
    const nodes = compiledModuleGraphNodes(sourceModule);
    const nodeIds = new Set<string>();
    nodes.forEach((node) => {
      const nodeId = String(node.node_id || node.id || "");
      if (!nodeId) {
        return;
      }
      nodeIds.add(nodeId);
      nodeIds.add(
        `${sourceLayerId}::${sourceModuleId}::${nodeId}`
      );
    });
    if (nodeIds.has(sourceNodeId)) {
      return cloneJsonValue(reference);
    }
    if (
      legacyAliasTarget &&
      nodeIds.has(legacyAliasTarget)
    ) {
      repairedCount += 1;
      return {
        ...cloneJsonValue(reference),
        source_node_id: legacyAliasTarget,
      };
    }
    const referenceOutputIds = [
      ...new Set(
        nodes
          .filter(
            (node) =>
              String(node.node_type || "") === "reference_output"
          )
          .map((node) => String(node.node_id || node.id || ""))
          .filter(Boolean)
      ),
    ];
    const moduleOutputIds =
      referenceOutputIds.length === 0
        ? [
            ...new Set(
              nodes
                .filter(
                  (node) =>
                    String(node.node_type || "") ===
                    "module_output"
                )
                .map((node) =>
                  String(node.node_id || node.id || "")
                )
                .filter(Boolean)
            ),
          ]
        : [];
    const canonicalOutputIds =
      referenceOutputIds.length === 1
        ? referenceOutputIds
        : moduleOutputIds.length === 1
          ? moduleOutputIds
          : [];
    if (canonicalOutputIds.length !== 1) {
      return cloneJsonValue(reference);
    }
    repairedCount += 1;
    return {
      ...cloneJsonValue(reference),
      source_node_id: canonicalOutputIds[0],
    };
  });
  return { references, repairedCount };
}
