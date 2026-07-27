import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

import {
  canonicalizeLegacyMaterializedReferencePointers,
  firstInteractionEnabledValue,
  DIALOGUE_RUNTIME_PROFILE_ID,
  DIALOGUE_RUNTIME_PROFILE_CONTENT_REVISION,
  EXPRESSION_STATE_SEMANTICS_CONTENT_REVISION,
  EXPRESSION_VISUAL_VALIDATION_COMPATIBILITY_REVISION,
  PARTICLE_EXPRESSION_RELATIVE_MAPPING_CONTENT_REVISION,
  PARTICLE_MAPPING_SOURCE_PRIORITY_FIX_REVISION,
  LEGACY_DIALOGUE_RUNTIME_PROFILE_ID,
  LINXUAN_RESIDENT_ID,
  mergeCatalogReferenceDeclarations,
  mergeChecklistTemplateDefaults,
  mergeCatalogFieldsPreservingValues,
  materializeLegacyCompileFields,
  materializeLayer8BehaviorPolicy,
  migrateAuthoritativeFieldCompatibilityMirrors,
  migrateDialogueRuntimeProfileId,
  migrateDialogueRuntimeProfileContentCopies,
  migrateExpressionStateSemanticsGraph,
  migrateFirstGreetingIdentityLiteralGraph,
  migrateFirstGreetingIdentityLiterals,
  migrateParticleExpressionRelativeMappingGraph,
  normalizeEmotionalDialogueExampleIsolation,
  migrateLinxuanFirstInteractionEnabledValue,
  migrateLinxuanFirstGreetingValue,
  normalizeCatalogNodeId,
  preserveStoredModuleEdges,
  preserveStoredModuleNodePosition,
  filterDanglingModuleGraphEdges,
  mergeAvailableModuleReferencePointers,
  STAGE7_4_8_FIRST_INTERACTION_ENABLED_MIGRATION,
  STAGE7_4_8_FIRST_GREETING_CONTENT_MIGRATION,
  STAGE7_4_12_IDENTITY_LITERAL_EXPORT_GATE_FIX_REVISION,
  STAGE7_4_12_A2_SOURCE_OUTPUT_IDENTITY_CLEANUP_REVISION,
  STAGE7_4_12_A4_COMPATIBILITY_AUTHORITY_STATUS_GOVERNANCE_REVISION,
  synchronizeAuthoritativeFieldCompatibilityParams,
  REMOVED_LINXUAN_FIRST_GREETING_VARIANT,
  updateFirstInteractionEnabled,
} from "../src/store/module-graph-merge.ts";
import {
  attachedModuleIdsFromLayerModules,
  hasEditorMigrationMarker,
  importCanvasState,
  recoverCanvasStateFromDigitalResident,
  saveEditorMigrationMarker,
  serializeCanvasState,
} from "../src/lib/canvas-persistence.ts";
import { resolveLayerColor, resolveModuleColor } from "../src/components/neural-graph/neuralGraphColors.ts";

test("A4 authoritative fields regenerate compatibility mirrors without replacing resident values", () => {
  const authoritativeFields = [
    {
      field_key: "resident_rule",
      field_value: "保留当前居民规则",
      custom_metadata: { keep: true },
    },
    {
      field_key: "custom_resident_field",
      field_value: { authored: true },
    },
  ];
  const displayFields = [
    {
      field_key: "display_cache",
      field_value: "保留既有 data.fields 显示缓存",
    },
  ];
  const graph = {
    nodes: [
      {
        id: "layer_8::language_habit::language_behavior_core_rules",
        data: {
          schemaNode: {
            node_id:
              "layer_8::language_habit::language_behavior_core_rules",
            type: "text_config",
            data: {
              node_type: "text_config",
              params: {
                fields: authoritativeFields,
                legacy_fields: [
                  { field_key: "resident_rule", field_value: "旧值" },
                ],
                legacy_data_fields: [],
                resident_owned_setting: { keep: true },
              },
              fields: displayFields,
            },
          },
        },
      },
      {
        node_id: "expression_context_input",
        type: "reference_input",
        data: {
          node_type: "reference_input",
          params: {
            fields: [
              {
                field_key: "expression_state",
                field_value: "caring",
              },
            ],
          },
        },
      },
    ],
    edges: [{ source: "first", target: "second" }],
  };
  const before = JSON.parse(JSON.stringify(graph));

  const first =
    migrateAuthoritativeFieldCompatibilityMirrors(graph);

  assert.equal(first.migrated, true);
  assert.deepEqual(graph, before);
  const firstParams =
    first.value.nodes[0].data.schemaNode.data.params;
  assert.deepEqual(firstParams.fields, authoritativeFields);
  assert.deepEqual(firstParams.legacy_fields, authoritativeFields);
  assert.deepEqual(firstParams.legacy_data_fields, authoritativeFields);
  assert.notStrictEqual(firstParams.legacy_fields, firstParams.fields);
  assert.notStrictEqual(firstParams.legacy_data_fields, firstParams.fields);
  assert.notStrictEqual(
    firstParams.legacy_fields[0],
    firstParams.fields[0]
  );
  assert.deepEqual(firstParams.resident_owned_setting, { keep: true });
  assert.deepEqual(
    first.value.nodes[0].data.schemaNode.data.fields,
    displayFields
  );
  assert.equal(
    firstParams.compatibility_authority_status_governance_revision,
    STAGE7_4_12_A4_COMPATIBILITY_AUTHORITY_STATUS_GOVERNANCE_REVISION
  );

  const secondParams = first.value.nodes[1].data.params;
  assert.deepEqual(secondParams.legacy_fields, secondParams.fields);
  assert.deepEqual(secondParams.legacy_data_fields, secondParams.fields);
  assert.equal(
    secondParams.compatibility_authority_status_governance_revision,
    STAGE7_4_12_A4_COMPATIBILITY_AUTHORITY_STATUS_GOVERNANCE_REVISION
  );

  const repeated =
    migrateAuthoritativeFieldCompatibilityMirrors(first.value);
  assert.equal(repeated.migrated, false);
  assert.strictEqual(repeated.value, first.value);

  const userEdited = JSON.parse(JSON.stringify(first.value));
  userEdited.nodes[0].data.schemaNode.data.params.fields[0].field_value =
    "用户修订后的当前规则";
  const afterUserEdit =
    migrateAuthoritativeFieldCompatibilityMirrors(userEdited);
  assert.equal(afterUserEdit.migrated, true);
  assert.equal(
    afterUserEdit.value.nodes[0].data.schemaNode.data.params
      .legacy_fields[0].field_value,
    "用户修订后的当前规则"
  );
  assert.equal(
    afterUserEdit.value.nodes[0].data.schemaNode.data.params
      .legacy_data_fields[0].field_value,
    "用户修订后的当前规则"
  );
  assert.equal(
    migrateAuthoritativeFieldCompatibilityMirrors(afterUserEdit.value)
      .migrated,
    false
  );
});

test("A4 promotes only unambiguous legacy-only fields and preserves conflicts", () => {
  const legacyOnly = {
    nodes: [
      {
        node_id: "legacy-only",
        data: {
          params: {
            legacy_fields: [
              { field_key: "resident_rule", field_value: "保留旧居民值" },
            ],
            legacy_data_fields: [
              { field_key: "resident_rule", field_value: "保留旧居民值" },
            ],
          },
        },
      },
    ],
    edges: [],
  };

  const promoted =
    migrateAuthoritativeFieldCompatibilityMirrors(legacyOnly);
  assert.equal(promoted.migrated, true);
  const promotedParams = promoted.value.nodes[0].data.params;
  assert.deepEqual(promotedParams.fields, legacyOnly.nodes[0].data.params.legacy_fields);
  assert.deepEqual(promotedParams.legacy_fields, promotedParams.fields);
  assert.deepEqual(promotedParams.legacy_data_fields, promotedParams.fields);

  const ambiguous = JSON.parse(JSON.stringify(legacyOnly));
  ambiguous.nodes[0].data.params.legacy_data_fields[0].field_value =
    "冲突的旧值";
  const before = JSON.parse(JSON.stringify(ambiguous));
  const preserved =
    migrateAuthoritativeFieldCompatibilityMirrors(ambiguous);
  assert.equal(preserved.migrated, false);
  assert.deepEqual(preserved.value, before);
  assert.equal("fields" in preserved.value.nodes[0].data.params, false);
});

test("A4 compile materializes catalog field metadata and re-synchronizes compatibility mirrors", () => {
  const genericFields = [
    {
      field_key: "name",
      field_value: "保留居民姓名",
      custom_metadata: { keep: true },
    },
    {
      field_key: "custom_resident_field",
      field_value: "保留自定义字段",
    },
  ];
  const catalogFields = [
    {
      field_id: "name",
      value: "",
      required: true,
      edit_scope: "developer_only",
      update_level: "locked_core",
      requires_recompile: true,
      i18n_keys: {
        label: "field.identity.name.label",
        placeholder: "field.identity.name.placeholder",
        help: "field.identity.name.help",
      },
    },
  ];

  const compiledFields = materializeLegacyCompileFields(
    genericFields,
    [catalogFields, genericFields]
  );

  assert.equal(compiledFields[0].field_id, "name");
  assert.equal(compiledFields[0].value, "保留居民姓名");
  assert.equal(compiledFields[0].field_value, "保留居民姓名");
  assert.equal(compiledFields[0].required, true);
  assert.equal(compiledFields[0].edit_scope, "developer_only");
  assert.equal(compiledFields[0].update_level, "locked_core");
  assert.equal(compiledFields[0].requires_recompile, true);
  assert.deepEqual(compiledFields[0].i18n_keys, catalogFields[0].i18n_keys);
  assert.deepEqual(compiledFields[0].custom_metadata, { keep: true });

  assert.equal(compiledFields[1].field_id, "custom_resident_field");
  assert.equal(compiledFields[1].value, "保留自定义字段");
  assert.equal(compiledFields[1].required, false);
  assert.equal(compiledFields[1].edit_scope, "user_editable");
  assert.equal(compiledFields[1].update_level, "versioned_core");
  assert.deepEqual(compiledFields[1].i18n_keys, {
    label: "field.identity.custom_resident_field.label",
    placeholder: "field.identity.custom_resident_field.placeholder",
    help: "field.identity.custom_resident_field.help",
  });

  const synchronized =
    synchronizeAuthoritativeFieldCompatibilityParams({
      fields: compiledFields,
      legacy_fields: genericFields,
      legacy_data_fields: genericFields,
    });
  assert.equal(synchronized.migrated, true);
  assert.deepEqual(synchronized.value.legacy_fields, compiledFields);
  assert.deepEqual(synchronized.value.legacy_data_fields, compiledFields);
  assert.equal(
    synchronizeAuthoritativeFieldCompatibilityParams(synchronized.value)
      .migrated,
    false
  );
});

test("compile canonicalizes verified Layer 8 legacy reference-output pointers without guessing", () => {
  const sourceSpecs = [
    {
      moduleId: "language_habit",
      oldNodeId:
        "layer_8::language_habit_reference_output_1783764276372_1",
      outputNodeId: "language_behavior_reference_output",
      count: 4,
    },
    {
      moduleId: "decision_pattern",
      oldNodeId:
        "layer_8::decision_pattern_reference_output_1783765320559_2",
      outputNodeId: "decision_behavior_reference_output",
      count: 9,
    },
    {
      moduleId: "interaction_strategy",
      oldNodeId:
        "layer_8::interaction_strategy_reference_output_1783764912319_2",
      outputNodeId: "interaction_behavior_reference_output",
      count: 10,
    },
    {
      moduleId: "behavior_habit",
      oldNodeId:
        "layer_8::behavior_habit_reference_output_1783764954151_2",
      outputNodeId: "task_behavior_reference_output",
      count: 3,
    },
    {
      moduleId: "emotion_mapper",
      oldNodeId:
        "layer_8::emotion_mapper_reference_output_1783765131641_2",
      outputNodeId: "social_behavior_reference_output",
      count: 1,
    },
  ];
  const sourceModules = sourceSpecs.map((source) => ({
    module_id: source.moduleId,
    layer_id: "layer_8",
    module_graph: {
      nodes: [
        {
          node_id: `${source.moduleId}_core_rules`,
          node_type: "text_config",
        },
        {
          node_id: source.outputNodeId,
          node_type: "reference_output",
        },
      ],
    },
  }));
  const references = sourceSpecs.flatMap((source) =>
    Array.from({ length: source.count }, (_, index) => ({
      reference_id: `${source.moduleId}_${index + 1}`,
      source_layer_id: "layer_8",
      source_module_id: source.moduleId,
      source_node_id: source.oldNodeId,
      source_scope: "module",
      source_field_paths: [],
      reference_type: "references",
      required: index % 2 === 0,
    }))
  );
  const before = JSON.parse(JSON.stringify(references));

  const first =
    canonicalizeLegacyMaterializedReferencePointers(
      references,
      sourceModules
    );

  assert.equal(first.repairedCount, 27);
  assert.deepEqual(references, before);
  first.references.forEach((reference) => {
    const source = sourceSpecs.find(
      (item) => item.moduleId === reference.source_module_id
    );
    assert.ok(source);
    assert.equal(reference.source_node_id, source.outputNodeId);
    const original = before.find(
      (item) => item.reference_id === reference.reference_id
    );
    assert.ok(original);
    assert.deepEqual(
      { ...reference, source_node_id: original.source_node_id },
      original
    );
  });

  const repeated =
    canonicalizeLegacyMaterializedReferencePointers(
      first.references,
      sourceModules
    );
  assert.equal(repeated.repairedCount, 0);
  assert.deepEqual(repeated.references, first.references);

  const preserved = [
    {
      ...before[0],
      reference_id: "valid_stable",
      source_node_id: "language_behavior_reference_output",
    },
    {
      ...before[0],
      reference_id: "unknown_manual",
      source_node_id:
        "layer_8::language_habit_reference_output_custom",
    },
    {
      ...before[0],
      reference_id: "field_scope",
      source_scope: "field",
      source_field_paths: [
        "language_behavior_config.fields.tone",
      ],
    },
    {
      ...before[0],
      reference_id: "node_scope",
      source_scope: "node",
    },
    {
      ...before[0],
      reference_id: "missing_source",
      source_module_id: "missing_module",
    },
  ];
  const ambiguousModules = sourceModules.map((module) =>
    module.module_id === "language_habit"
      ? {
          ...module,
          module_graph: {
            nodes: [
              ...module.module_graph.nodes,
              {
                node_id:
                  "language_behavior_reference_output_secondary",
                node_type: "reference_output",
              },
            ],
          },
        }
      : module
  );
  const ambiguous = [
    {
      ...before[0],
      reference_id: "ambiguous_output",
    },
  ];

  const preservedResult =
    canonicalizeLegacyMaterializedReferencePointers(
      preserved,
      sourceModules
    );
  assert.equal(preservedResult.repairedCount, 0);
  assert.deepEqual(preservedResult.references, preserved);
  const ambiguousResult =
    canonicalizeLegacyMaterializedReferencePointers(
      ambiguous,
      ambiguousModules
    );
  assert.equal(ambiguousResult.repairedCount, 0);
  assert.deepEqual(ambiguousResult.references, ambiguous);
});

const RECOVERY_DR_FIXTURE = {
  file_type: "digital_resident",
  dr_version: "0.3",
  payload: {
    modules: [
      {
        module_id: "module_basic_identity",
        layer_id: "layer_1",
        module_graph: {
          nodes: [
            {
              node_id: "basic_identity_field_input",
              node_type: "field_input",
              module_id: "module_basic_identity",
              layer_id: "layer_1",
              params: { fields: [{ field_id: "name", value: "fixture" }] },
              outputs: {},
              metadata: {},
              i18n_keys: {},
            },
            {
              node_id: "layer_1::module_basic_identity_reference_output_123_1",
              node_type: "reference_output",
              module_id: "module_basic_identity",
              layer_id: "layer_1",
              params: { export_scope: "module" },
              outputs: {},
              metadata: {},
              i18n_keys: {},
            },
          ],
          edges: [
            {
              edge_id: "identity-to-reference",
              source: "basic_identity_field_input",
              source_port: "p_out",
              target: "layer_1::module_basic_identity_reference_output_123_1",
              target_port: "p_in",
            },
          ],
        },
      },
      {
        module_id: "module_growth_background",
        layer_id: "layer_1",
        module_graph: {
          nodes: [
            {
              node_id: "layer_1::module_growth_background_reference_input_456_1",
              node_type: "reference_input",
              module_id: "module_growth_background",
              layer_id: "layer_1",
              params: {
                references: [
                  {
                    source_layer_id: "layer_1",
                    source_module_id: "module_basic_identity",
                    source_node_id: "layer_1::module_basic_identity_reference_output_123_1",
                    source_scope: "module",
                    source_field_paths: [],
                    reference_type: "references",
                    required: true,
                  },
                ],
              },
              outputs: {},
              metadata: {},
              i18n_keys: {},
            },
            {
              node_id: "growth_background_output",
              node_type: "module_output",
              module_id: "module_growth_background",
              layer_id: "layer_1",
              params: {},
              outputs: {},
              metadata: {},
              i18n_keys: {},
            },
          ],
          edges: [
            {
              edge_id: "reference-to-output",
              source: "layer_1::module_growth_background_reference_input_456_1",
              source_port: "p_out",
              target: "growth_background_output",
              target_port: "p_in",
            },
          ],
        },
      },
      {
        module_id: "catalog_only_graphless_module",
        layer_id: "layer_2",
        module_graph: {},
      },
    ],
  },
};

test("React Flow curved edges use the registered default Bezier type", () => {
  const source = readFileSync(new URL("../src/components/CanvasShell.tsx", import.meta.url), "utf8");

  assert.match(source, /CURVED_EDGE_DEFAULT_OPTIONS\s*=\s*\{\s*type:\s*["']default["']/s);
  assert.doesNotMatch(source, /type:\s*["']bezier["']/);
});

test("a compiled DR recovers module attachments and preserves hand-built reference ids", () => {
  const state = recoverCanvasStateFromDigitalResident(RECOVERY_DR_FIXTURE);

  assert.ok(state);
  assert.deepEqual(state.layerModules, {
    layer_1: ["module_basic_identity", "module_growth_background"],
  });
  assert.equal(Object.keys(state.moduleInstanceRegistry).length, 2);
  assert.equal(state.layerModules.layer_2, undefined);
  assert.equal(state.moduleInstanceRegistry["layer_2::catalog_only_graphless_module"], undefined);

  const identityGraph = state.moduleGraphs["layer_1::module_basic_identity"];
  const growthGraph = state.moduleGraphs["layer_1::module_growth_background"];
  assert.equal(identityGraph.nodes[0].node_id, "layer_1::module_basic_identity::basic_identity_field_input");
  assert.equal(identityGraph.nodes[0].data.catalog_node_id, "basic_identity_field_input");
  assert.equal(identityGraph.nodes[1].node_id, "layer_1::module_basic_identity_reference_output_123_1");
  assert.equal(identityGraph.edges[0].source, "layer_1::module_basic_identity::basic_identity_field_input");
  assert.equal(identityGraph.edges[0].target, "layer_1::module_basic_identity_reference_output_123_1");
  assert.equal(growthGraph.nodes[0].node_id, "layer_1::module_growth_background_reference_input_456_1");
  assert.equal(
    growthGraph.nodes[0].data.params.references[0].source_node_id,
    "layer_1::module_basic_identity_reference_output_123_1"
  );
  assert.equal(growthGraph.edges[0].target, "layer_1::module_growth_background::growth_background_output");
});

test("Canvas import accepts digital_resident files without changing the DR payload", () => {
  const before = JSON.parse(JSON.stringify(RECOVERY_DR_FIXTURE));
  const result = importCanvasState(JSON.stringify(RECOVERY_DR_FIXTURE));

  assert.equal(result.success, true);
  assert.equal(attachedModuleIdsFromLayerModules(result.state.layerModules).length, 2);
  assert.deepEqual(RECOVERY_DR_FIXTURE, before);
});

test("catalog optional config fields are added on reopen without replacing saved values", () => {
  const merged = mergeCatalogFieldsPreservingValues(
    [
      {
        field_id: "first_interaction",
        value: {
          enabled: true,
          initiative_level: "low",
          scenes: { user_silence: { enabled: true, max_active_prompts: 1 } },
        },
        required: false,
      },
      { field_id: "new_optional", value: "catalog-default", required: false },
    ],
    [
      {
        field_id: "first_interaction",
        value: {
          enabled: false,
          initiative_level: "low",
          scenes: { user_silence: { enabled: false, max_active_prompts: 0 } },
        },
      },
      { field_id: "user_field", value: "keep-me" },
    ]
  );

  assert.deepEqual(merged[0].value, {
    enabled: false,
    initiative_level: "low",
    scenes: { user_silence: { enabled: false, max_active_prompts: 0 } },
  });
  assert.equal(merged[1].value, "catalog-default");
  assert.equal(merged[2].field_id, "user_field");
  assert.equal(merged[2].value, "keep-me");
});

test("Stage 7.4.8 preserves explicit first-interaction enabled values and defaults only missing data", () => {
  const seedField = {
    field_id: "first_interaction",
    value: {
      enabled: true,
      scenes: {
        first_load: { enabled: true, repeat_introduction: false },
        return_session: { enabled: true, repeat_introduction: false, continue_previous_context: true },
        identity_question: { enabled: true, use_existing_identity: true, allow_fabrication: false },
        user_silence: { enabled: true, max_active_prompts: 1 },
      },
    },
    required: false,
  };
  const savedScenes = {
    first_load: { enabled: false, repeat_introduction: true },
    return_session: { enabled: false, repeat_introduction: true, continue_previous_context: false },
    identity_question: { enabled: false, use_existing_identity: false, allow_fabrication: true },
    user_silence: { enabled: false, max_active_prompts: 1 },
  };
  const valueAfterMerge = (savedValue) => {
    const [merged] = mergeCatalogFieldsPreservingValues(
      [seedField],
      [{ field_id: "first_interaction", value: savedValue }]
    );
    return merged.value;
  };

  for (const enabled of [true, false]) {
    const value = valueAfterMerge({ enabled, scenes: savedScenes });
    assert.equal(value.enabled, enabled);
    assert.deepEqual(value.scenes, savedScenes);
  }
  const legacyValue = valueAfterMerge({ scenes: savedScenes });
  assert.equal(legacyValue.enabled, true);
  assert.deepEqual(legacyValue.scenes, savedScenes);

  const savedFalse = { enabled: false, tone: "warm_calm_reserved", scenes: savedScenes };
  const rechecked = updateFirstInteractionEnabled(savedFalse, true);
  assert.equal(rechecked.enabled, true);
  assert.equal(rechecked.tone, "warm_calm_reserved");
  assert.deepEqual(rechecked.scenes, savedScenes);
  assert.equal(savedFalse.enabled, false);
});

test("Stage 7.4.8 migrates only the unmarked Linxuan value and then preserves user false", () => {
  const scenes = {
    first_load: { enabled: false, repeat_introduction: true },
    return_session: { enabled: true, repeat_introduction: false, continue_previous_context: true },
    identity_question: { enabled: true, use_existing_identity: true, allow_fabrication: false },
    user_silence: { enabled: true, max_active_prompts: 1 },
  };
  const stored = {
    enabled: false,
    tone: "warm_calm_reserved",
    interaction_style: "natural_conversational",
    initiative_level: "low",
    wait_for_user_response: true,
    identity_disclosure_mode: "contextual_or_on_request",
    scenes,
  };

  const firstLoad = migrateLinxuanFirstInteractionEnabledValue(LINXUAN_RESIDENT_ID, false, stored);
  assert.equal(firstLoad.migrated, true);
  assert.equal(firstLoad.markComplete, true);
  assert.deepEqual(firstLoad.value, { ...stored, enabled: true });
  assert.equal(stored.enabled, false);

  const reload = migrateLinxuanFirstInteractionEnabledValue(LINXUAN_RESIDENT_ID, true, firstLoad.value);
  assert.equal(reload.migrated, false);
  assert.equal(reload.value.enabled, true);

  const userDisabled = { ...firstLoad.value, enabled: false };
  const afterUserSave = migrateLinxuanFirstInteractionEnabledValue(
    LINXUAN_RESIDENT_ID,
    true,
    userDisabled
  );
  assert.equal(afterUserSave.migrated, false);
  assert.equal(afterUserSave.value.enabled, false);
  assert.deepEqual(afterUserSave.value.scenes, scenes);

  const otherResident = migrateLinxuanFirstInteractionEnabledValue(
    "dr_other_resident",
    false,
    stored
  );
  assert.equal(otherResident.migrated, false);
  assert.equal(otherResident.markComplete, false);
  assert.equal(otherResident.value.enabled, false);
});

test("Stage 7.4.8 migrates only Linxuan greeting content once", () => {
  const retainedVariants = [
    "你好，我叫林瑄。刚见面，先认识一下吧。",
    "你好，我是林瑄。第一次见面，请多关照。",
    "你好，我是林瑄。你叫什么名字？",
  ];
  const stored = {
    locale: "zh-CN",
    content_status: "pending_authoring",
    variants: [...retainedVariants, REMOVED_LINXUAN_FIRST_GREETING_VARIANT],
    max_sentences: 2,
  };

  const firstLoad = migrateLinxuanFirstGreetingValue(LINXUAN_RESIDENT_ID, false, stored);
  assert.equal(firstLoad.migrated, true);
  assert.equal(firstLoad.markComplete, true);
  assert.equal(firstLoad.value.content_status, "authored");
  assert.deepEqual(firstLoad.value.variants, retainedVariants);
  assert.equal(firstLoad.value.max_sentences, 2);
  assert.equal(stored.variants.length, 4);

  const reload = migrateLinxuanFirstGreetingValue(LINXUAN_RESIDENT_ID, true, firstLoad.value);
  assert.equal(reload.migrated, false);
  assert.deepEqual(reload.value, firstLoad.value);

  const empty = migrateLinxuanFirstGreetingValue(
    LINXUAN_RESIDENT_ID,
    false,
    { content_status: "pending_authoring", variants: [] }
  );
  assert.equal(empty.migrated, false);
  assert.equal(empty.markComplete, true);
  assert.equal(empty.value.content_status, "pending_authoring");
  assert.deepEqual(empty.value.variants, []);

  const otherResident = migrateLinxuanFirstGreetingValue("dr_other_resident", false, stored);
  assert.equal(otherResident.migrated, false);
  assert.equal(otherResident.markComplete, false);
  assert.deepEqual(otherResident.value, stored);
});

test("Stage 7.4.12 removes only the resident self-introduction from first greetings", () => {
  const stored = {
    locale: "zh-CN",
    content_status: "authored",
    variants: [
      "你好，我叫林瑄。刚见面，先认识一下吧。",
      "你好，我是林瑄。第一次见面，请多关照。",
      { text: "你好，我是林瑄。你叫什么名字？", variant_id: "question" },
    ],
    max_sentences: 2,
  };
  const migrated = migrateFirstGreetingIdentityLiterals(stored, [
    "林瑄",
    "linxuan_hum_cn_xian_01",
  ]);
  assert.equal(migrated.migrated, true);
  assert.equal(migrated.markComplete, true);
  assert.equal(migrated.value.content_status, "authored");
  assert.deepEqual(migrated.value.variants, [
    "你好。刚见面，先认识一下吧。",
    "你好。第一次见面，请多关照。",
    { text: "你好。你叫什么名字？", variant_id: "question" },
  ]);
  assert.equal(migrated.value.max_sentences, 2);
  assert.doesNotMatch(JSON.stringify(migrated.value), /林瑄|linxuan/i);

  const repeated = migrateFirstGreetingIdentityLiterals(
    migrated.value,
    ["林瑄", "linxuan_hum_cn_xian_01"]
  );
  assert.equal(repeated.migrated, false);
  assert.equal(repeated.markComplete, true);
  assert.deepEqual(repeated.value, migrated.value);

  const unsupported = migrateFirstGreetingIdentityLiterals(
    {
      content_status: "authored",
      variants: ["你好。叫我林瑄就好。"],
    },
    ["林瑄"]
  );
  assert.equal(unsupported.migrated, false);
  assert.equal(unsupported.markComplete, false);
});

test("Stage 7.4.8 checkbox derives true and false from the stored nested value", () => {
  assert.equal(firstInteractionEnabledValue({ enabled: false }), false);
  assert.equal(firstInteractionEnabledValue({ enabled: true }), true);
  assert.equal(firstInteractionEnabledValue({}), true);
});

test("Stage 7.4.8 editor migration marker is local-only and resident-scoped", () => {
  const values = new Map();
  const previousWindow = globalThis.window;
  globalThis.window = {
    localStorage: {
      getItem: (key) => values.get(key) ?? null,
      setItem: (key, value) => values.set(key, String(value)),
    },
  };
  try {
    assert.equal(
      hasEditorMigrationMarker(STAGE7_4_8_FIRST_INTERACTION_ENABLED_MIGRATION, LINXUAN_RESIDENT_ID),
      false
    );
    assert.equal(
      saveEditorMigrationMarker(STAGE7_4_8_FIRST_INTERACTION_ENABLED_MIGRATION, LINXUAN_RESIDENT_ID),
      true
    );
    assert.equal(
      hasEditorMigrationMarker(STAGE7_4_8_FIRST_INTERACTION_ENABLED_MIGRATION, LINXUAN_RESIDENT_ID),
      true
    );
    assert.equal(
      hasEditorMigrationMarker(STAGE7_4_8_FIRST_INTERACTION_ENABLED_MIGRATION, "dr_other_resident"),
      false
    );
    assert.equal(
      saveEditorMigrationMarker(STAGE7_4_8_FIRST_GREETING_CONTENT_MIGRATION, LINXUAN_RESIDENT_ID),
      true
    );
    assert.equal(
      hasEditorMigrationMarker(STAGE7_4_8_FIRST_GREETING_CONTENT_MIGRATION, LINXUAN_RESIDENT_ID),
      true
    );
    assert.equal(
      saveEditorMigrationMarker(
        STAGE7_4_12_IDENTITY_LITERAL_EXPORT_GATE_FIX_REVISION,
        LINXUAN_RESIDENT_ID
      ),
      true
    );
    assert.equal(
      hasEditorMigrationMarker(
        STAGE7_4_12_IDENTITY_LITERAL_EXPORT_GATE_FIX_REVISION,
        LINXUAN_RESIDENT_ID
      ),
      true
    );
    assert.doesNotMatch(
      JSON.stringify(serializeCanvasState({})),
      /stage7_4_8_first_(interaction_enabled|greeting_integrity)_v1/
    );
  } finally {
    if (previousWindow === undefined) {
      delete globalThis.window;
    } else {
      globalThis.window = previousWindow;
    }
  }
});

test("Stage 7.4.8 greeting content migration writes the exact visual-style field", () => {
  const bridgeSource = readFileSync(new URL("../src/store/module-state-bridge.ts", import.meta.url), "utf8");
  assert.match(bridgeSource, /VISUAL_STYLE_GRAPH_ID = ["']layer_10::visual_style["']/);
  assert.match(bridgeSource, /catalogNodeIdFromGraphNode\(node\) !== ["']visual_style_first_greeting_config["']/);
  assert.match(bridgeSource, /String\(field\.field_id \|\| field\.field_key \|\| ["']["']\) !== ["']first_greeting["']/);
  assert.match(bridgeSource, /migrateLinxuanFirstGreetingValue\([\s\S]*?field\[valueKey\][\s\S]*?\{ \.\.\.field, \[valueKey\]: migration\.value \}/s);
  assert.match(bridgeSource, /STAGE7_4_8_FIRST_GREETING_CONTENT_MIGRATION/);
  assert.match(bridgeSource, /hasFirstGreetingConfigField[\s\S]*?Array\.isArray\(params\.fields\)/s);
  assert.match(bridgeSource, /moduleNodeId === VISUAL_STYLE_GRAPH_ID[\s\S]*?saveModuleGraphState\(moduleNodeId, mergedGraph\.nodes, mergedGraph\.edges\)/s);
});

test("Stage 7.4.12 greeting identity migration synchronizes real Studio graph copies and output", () => {
  const greeting = {
    locale: "zh-CN",
    content_status: "authored",
    variants: ["你好，我是林瑄。第一次见面，请多关照。"],
  };
  const firstPresence = {
    particle_state: "calm",
    custom_visual_note: "resident-authored",
  };
  const greetingField = {
    field_key: "first_greeting",
    field_value: greeting,
    description:
      "Optional first-greeting presentation configuration; greeting copy remains unauthored.",
  };
  const presenceField = {
    field_key: "first_presence",
    field_value: firstPresence,
  };
  const graph = {
    moduleNodeId: "layer_10::visual_style",
    nodes: [
      {
        id: "input-wrapper",
        data: {
          schemaNode: {
            data: {
              catalog_node_id: "visual_style_first_greeting_config",
              params: {
                fields: [greetingField, presenceField],
                legacy_fields: [greetingField, presenceField],
                legacy_data_fields: [greetingField, presenceField],
                unrelated: "preserved",
              },
              fields: [greetingField, presenceField],
            },
          },
        },
      },
      {
        id: "output-wrapper",
        data: {
          schemaNode: {
            data: {
              catalog_node_id: "visual_style_first_presence_output",
              outputs: {
                first_presence_config: {
                  first_greeting: greeting,
                  first_presence: firstPresence,
                  unrelated_output: "preserved",
                },
                module_output: "first_presence_config",
              },
            },
          },
        },
      },
    ],
    edges: [],
  };

  const migration = migrateFirstGreetingIdentityLiteralGraph(
    graph,
    ["林瑄", "linxuan_hum_cn_xian_01"]
  );
  assert.equal(migration.migrated, true);
  assert.equal(migration.markComplete, true);
  const inputData = migration.value.nodes[0].data.schemaNode.data;
  const outputData = migration.value.nodes[1].data.schemaNode.data;
  for (const key of ["fields", "legacy_fields", "legacy_data_fields"]) {
    assert.equal(
      inputData.params[key][0].field_value.variants[0],
      "你好。第一次见面，请多关照。"
    );
    assert.doesNotMatch(
      inputData.params[key][0].description,
      /unauthored/
    );
    assert.match(
      inputData.params[key][0].description,
      /authored/
    );
    assert.deepEqual(inputData.params[key][1].field_value, firstPresence);
  }
  assert.equal(
    inputData.fields[0].field_value.variants[0],
    "你好。第一次见面，请多关照。"
  );
  assert.equal(inputData.params.unrelated, "preserved");
  assert.equal(
    inputData.params.identity_literal_export_gate_revision,
    STAGE7_4_12_IDENTITY_LITERAL_EXPORT_GATE_FIX_REVISION
  );
  assert.equal(
    outputData.outputs.first_presence_config.first_greeting.variants[0],
    "你好。第一次见面，请多关照。"
  );
  assert.deepEqual(
    outputData.outputs.first_presence_config.first_presence,
    firstPresence
  );
  assert.equal(
    outputData.outputs.first_presence_config.unrelated_output,
    "preserved"
  );

  const repeated = migrateFirstGreetingIdentityLiteralGraph(
    migration.value,
    ["林瑄", "linxuan_hum_cn_xian_01"]
  );
  assert.equal(repeated.migrated, false);
  assert.equal(repeated.markComplete, true);

  const incomplete = migrateFirstGreetingIdentityLiteralGraph(
    { ...graph, nodes: [graph.nodes[0]] },
    ["林瑄"]
  );
  assert.equal(incomplete.migrated, true);
  assert.equal(incomplete.markComplete, false);
});

test("Stage 7.4.8 first-interaction enabled uses params fields through save and reload", () => {
  const savedScenes = {
    first_load: { enabled: false, repeat_introduction: true },
    return_session: { enabled: true, repeat_introduction: false, continue_previous_context: false },
    identity_question: { enabled: false, use_existing_identity: true, allow_fabrication: false },
    user_silence: { enabled: true, max_active_prompts: 1 },
  };
  const reopen = (enabled) => {
    const state = serializeCanvasState({
      moduleGraphs: {
        "layer_8::interaction_strategy": {
          moduleId: "layer_8::interaction_strategy",
          nodes: [
            {
              id: "interaction_behavior_core_rules",
              data: {
                schemaNode: {
                  node_id: "interaction_behavior_core_rules",
                  data: {
                    catalog_module_id: "interaction_strategy",
                    catalog_node_id: "interaction_behavior_core_rules",
                    params: {
                      fields: [
                        {
                          field_id: "first_interaction",
                          value: { enabled, tone: "warm_calm_reserved", scenes: savedScenes },
                        },
                      ],
                    },
                  },
                },
              },
            },
          ],
          edges: [],
        },
      },
    });
    const imported = importCanvasState(JSON.stringify(state));
    assert.equal(imported.success, true);
    return imported.state.moduleGraphs["layer_8::interaction_strategy"].nodes[0]
      .data.schemaNode.data.params.fields[0].value;
  };

  const savedFalse = reopen(false);
  assert.equal(savedFalse.enabled, false);
  assert.deepEqual(savedFalse.scenes, savedScenes);
  const savedTrue = reopen(true);
  assert.equal(savedTrue.enabled, true);
  assert.deepEqual(savedTrue.scenes, savedScenes);
});

test("WorkflowNodeCard binds the interaction core toggle to params.fields first_interaction", () => {
  const cardSource = readFileSync(new URL("../src/components/canvas/WorkflowNodeCard.tsx", import.meta.url), "utf8");
  const bridgeSource = readFileSync(new URL("../src/store/module-state-bridge.ts", import.meta.url), "utf8");

  assert.match(cardSource, /schemaModuleId === ["']interaction_strategy["']/);
  assert.match(cardSource, /catalogNodeId === ["']interaction_behavior_core_rules["']/);
  assert.match(cardSource, /firstInteractionValue = isRecord\(firstInteractionField\?\.value\)/);
  assert.match(cardSource, /firstInteractionEnabledValue\(firstInteractionValue\)/);
  assert.match(
    cardSource,
    /if \(usesFirstInteractionEnabled\) \{[\s\S]*?updateFirstInteractionEnabled\([\s\S]*?onInput\?\.\(["']params["'], \{ \.\.\.compileTimeParams, fields: nextFields \}\);[\s\S]*?return;/s
  );
  assert.match(cardSource, /checked=\{isEnabled\}/);
  assert.match(
    bridgeSource,
    /\(hasFirstInteractionField \|\| hasFirstGreetingConfigField\) && Array\.isArray\(params\.fields\)/
  );
  assert.match(bridgeSource, /hasLegacyFirstInteractionFields[\s\S]*?delete data\.fields;/s);
  assert.match(bridgeSource, /LINXUAN_IDENTITY_GRAPH_ID = ["']layer_1::module_basic_identity["']/);
  assert.match(bridgeSource, /LINXUAN_INTERACTION_GRAPH_ID = ["']layer_8::interaction_strategy["']/);
  assert.match(bridgeSource, /graphFieldValue\(identityGraph, ["']resident_id["']\) !== LINXUAN_RESIDENT_ID/);
  assert.match(
    bridgeSource,
    /migrateLinxuanFirstInteractionEnabledValue\([\s\S]*?LINXUAN_RESIDENT_ID,[\s\S]*?false,[\s\S]*?field\.value[\s\S]*?return \{ \.\.\.field, value: migration\.value \};/s
  );
  assert.match(
    bridgeSource,
    /saveModuleGraphState\(nextGraph\.moduleNodeId, nextGraph\.nodes, nextGraph\.edges\)[\s\S]*?saveEditorMigrationMarker\(/s
  );
  assert.match(
    bridgeSource,
    /ensureModuleGraphExists\([\s\S]*?LINXUAN_IDENTITY_GRAPH_ID[\s\S]*?LINXUAN_INTERACTION_GRAPH_ID[\s\S]*?migrateLinxuanFirstInteractionEnabledOnce\(\)/s
  );
});

test("Stage 7.4.8 normalizes saved first-interaction prompt limits during catalog graph merge", () => {
  const seedField = {
    field_id: "first_interaction",
    value: {
      enabled: true,
      scenes: { user_silence: { enabled: true, max_active_prompts: 1 } },
    },
    required: false,
  };
  const promptLimitAfterMerge = (firstInteraction) => {
    const [merged] = mergeCatalogFieldsPreservingValues(
      [seedField],
      [{ field_id: "first_interaction", value: firstInteraction }]
    );
    return merged.value.scenes.user_silence.max_active_prompts;
  };

  assert.equal(promptLimitAfterMerge({ scenes: { user_silence: { enabled: true, max_active_prompts: -4 } } }), 1);
  assert.equal(promptLimitAfterMerge({ scenes: { user_silence: { enabled: true } } }), 1);
  for (const invalid of ["1", 0.5, -1, 2]) {
    assert.equal(
      promptLimitAfterMerge({ scenes: { user_silence: { enabled: true, max_active_prompts: invalid } } }),
      1
    );
  }
  assert.equal(promptLimitAfterMerge({ scenes: { user_silence: { enabled: true, max_active_prompts: 0 } } }), 0);
  assert.equal(promptLimitAfterMerge({ scenes: { user_silence: { enabled: true, max_active_prompts: 1 } } }), 1);
});

test("Stage 7.4.8 first-presence fields, references, and exact edges survive save and reopen", () => {
  const nodeSpecs = [
    [
      "visual_style_first_greeting_config",
      "text_input",
      {
        mode: "generic_fields",
        fields: [
          {
            field_key: "first_greeting",
            field_value: {
              content_status: "authored",
              variants: ["fixture greeting"],
              max_sentences: 1,
            },
            required: false,
          },
          { field_key: "first_presence", field_value: { particle_state: "calm" }, required: false },
        ],
      },
    ],
    [
      "visual_style_reference_input",
      "reference_input",
      {
        references: [
          {
            reference_id: "first_presence_identity_core",
            source_layer_id: "layer_1",
            source_module_id: "module_basic_identity",
            source_node_id: "basic_identity_output",
            source_scope: "module",
            source_field_paths: [],
            reference_type: "references",
            required: true,
          },
          {
            reference_id: "first_presence_personality",
            source_layer_id: "layer_2",
            source_module_id: "personality_traits",
            source_node_id: "personality_traits_output_summary",
            source_scope: "module",
            source_field_paths: [],
            reference_type: "references",
            required: true,
          },
          {
            reference_id: "first_presence_safety_boundary",
            source_layer_id: "layer_3",
            source_module_id: "humanistic_interaction_boundary_config_v0_1",
            source_node_id: "interaction_boundary_config_output",
            source_scope: "module",
            source_field_paths: [],
            reference_type: "constrains",
            required: true,
          },
          {
            reference_id: "first_presence_memory_policy",
            source_layer_id: "layer_5",
            source_module_id: "memory_access_control",
            source_node_id: "memory_access_output",
            source_scope: "module",
            source_field_paths: [],
            reference_type: "references",
            required: true,
          },
          {
            reference_id: "first_presence_world_context",
            source_layer_id: "layer_7",
            source_module_id: "world_setting",
            source_node_id: "worldview_module_output",
            source_scope: "module",
            source_field_paths: [],
            reference_type: "references",
            required: true,
          },
          {
            reference_id: "first_presence_interaction_strategy",
            source_layer_id: "layer_8",
            source_module_id: "interaction_strategy",
            source_node_id: "interaction_behavior_core_rules",
            source_scope: "module",
            source_field_paths: [],
            reference_type: "references",
            required: true,
            usage_key: "stage7_4_8.expression.reference.interactionStrategy.usage",
          },
          {
            reference_id: "first_presence_user_relationship",
            source_layer_id: "layer_11",
            source_module_id: "user_relationship",
            source_node_id: "user_relationship_config_output",
            source_scope: "module",
            source_field_paths: [],
            reference_type: "references",
            required: true,
          },
        ],
      },
    ],
    ["visual_style_config_normalize", "structure_normalize", {}],
    ["visual_style_first_greeting_validation", "validation", {}],
    ["visual_style_first_presence_validation", "validation", {}],
    ["visual_style_first_presence_output", "module_output", { output_key: "first_presence_config" }],
    [
      "visual_style_reference_output",
      "reference_output",
      {
        export_scope: "module",
        export_fields: [
          {
            field_key: "first_greeting",
            field_path: "expression.first_greeting",
            label_key: "stage7_4_8.expression.referenceOutput.field.firstGreeting",
            required: false,
          },
        ],
      },
    ],
  ];
  const edgePairs = [
    ["visual_style_first_greeting_config", "visual_style_config_normalize"],
    ["visual_style_config_normalize", "visual_style_first_greeting_validation"],
    ["visual_style_first_greeting_validation", "visual_style_first_presence_validation"],
    ["visual_style_first_presence_validation", "visual_style_first_presence_output"],
    ["visual_style_first_presence_output", "visual_style_reference_output"],
    ["visual_style_reference_input", "visual_style_first_greeting_validation"],
    ["visual_style_reference_input", "visual_style_first_presence_validation"],
    ["visual_style_reference_input", "visual_style_first_presence_output"],
  ];
  const dr = {
    file_type: "digital_resident",
    dr_version: "0.3",
    payload: {
      modules: [
        {
          module_id: "visual_style",
          layer_id: "layer_10",
          module_graph: {
            nodes: nodeSpecs.map(([node_id, node_type, params], index) => ({
              node_id,
              node_type,
              module_id: "visual_style",
              layer_id: "layer_10",
              position: { x: 120 + index * 360, y: 120 },
              params,
              outputs: {},
              metadata: { compile_time_only: true },
              i18n_keys: {},
            })),
            edges: edgePairs.map(([source, target]) => ({
              edge_id: `${source}_to_${target}`,
              source,
              source_port: "p_out",
              target,
              target_port: "p_in",
            })),
          },
        },
      ],
    },
  };

  const recovered = recoverCanvasStateFromDigitalResident(dr);
  assert.ok(recovered);
  const saved = serializeCanvasState(recovered);
  const reopened = importCanvasState(JSON.stringify(saved));
  assert.equal(reopened.success, true);

  const graph = reopened.state.moduleGraphs["layer_10::visual_style"];
  assert.equal(graph.nodes.length, 7);
  assert.equal(graph.edges.length, 8);
  const byCatalogId = new Map(graph.nodes.map((node) => [node.data.catalog_node_id, node]));
  assert.deepEqual(
    byCatalogId.get("visual_style_first_greeting_config").data.params.fields[0].field_value,
    { content_status: "authored", variants: ["fixture greeting"], max_sentences: 1 }
  );
  const references = byCatalogId.get("visual_style_reference_input").data.params.references;
  assert.equal(references.length, 7);
  assert.ok(references.every((reference) => reference.reference_id));
  assert.ok(references.every((reference) => reference.source_scope === "module" && reference.required === true));
  assert.equal(
    references.find((reference) => reference.reference_id === "first_presence_safety_boundary").source_module_id,
    "humanistic_interaction_boundary_config_v0_1"
  );
  assert.equal(
    references.find((reference) => reference.reference_id === "first_presence_safety_boundary").source_node_id,
    "interaction_boundary_config_output"
  );
  assert.equal(
    references.some((reference) => reference.source_module_id === "humanistic_behavior_boundary_config_v0_1"),
    false
  );
  assert.equal(
    references.find((reference) => reference.reference_id === "first_presence_interaction_strategy").usage_key,
    "stage7_4_8.expression.reference.interactionStrategy.usage"
  );
  assert.equal(
    byCatalogId.get("visual_style_reference_output").data.params.export_fields[0].label_key,
    "stage7_4_8.expression.referenceOutput.field.firstGreeting"
  );
  assert.deepEqual(
    new Set(
      graph.edges.map((edge) => [
        edge.source.split("::").at(-1),
        edge.target.split("::").at(-1),
      ].join("->"))
    ),
    new Set(edgePairs.map(([source, target]) => `${source}->${target}`))
  );
});

test("Stage 7.4.8 content-status selector has localized pending and authored options", () => {
  const cardSource = readFileSync(new URL("../src/components/canvas/WorkflowNodeCard.tsx", import.meta.url), "utf8");
  const en = JSON.parse(readFileSync(new URL("../locales/en.json", import.meta.url), "utf8"));
  const zh = JSON.parse(readFileSync(new URL("../locales/zh.json", import.meta.url), "utf8"));
  assert.match(cardSource, /field\.enum_options\.map/);
  for (const messages of [en, zh]) {
    assert.ok(messages["stage7_4_8.expression.enum.contentStatus.pending_authoring"]);
    assert.ok(messages["stage7_4_8.expression.enum.contentStatus.authored"]);
    assert.ok(messages["stage7_4_8.expression.value.content_status_must_match_variants"]);
    assert.ok(messages["stage7_4_8.expression.value.greeting_variants_must_contain_valid_copy"]);
    assert.equal(messages["stage7_4_8.expression.value.content_status_must_remain_pending_authoring"], undefined);
  }
});

test("attached module ids are deduplicated without inventing catalog modules", () => {
  assert.deepEqual(
    attachedModuleIdsFromLayerModules({ layer_1: ["identity", "identity"], layer_2: [], layer_3: ["safety"] }),
    ["identity", "safety"]
  );
  assert.deepEqual(attachedModuleIdsFromLayerModules({ layer_1: [], layer_2: [] }), []);
});

test("Canvas import/export and compile paths retain graphs and consume attached modules only", () => {
  const source = readFileSync(new URL("../src/components/CanvasShell.tsx", import.meta.url), "utf8");
  const bridgeSource = readFileSync(new URL("../src/store/module-state-bridge.ts", import.meta.url), "utf8");

  assert.match(source, /moduleGraphs:\s*exportedGraphs/);
  assert.match(source, /saveModuleGraphState\(instanceId, graph\.nodes, graph\.edges\)/);
  assert.match(source, /store\.setModuleGraphs\(restoredGraphs\)/);
  assert.match(source, /const recovered = await readCanvasStateFromFile\(file\)/);
  assert.match(source, /restoreCanvasState\(recovered\.state\)/);
  assert.match(source, /const restored = initializeModuleState\(\)/);
  assert.match(source, /setLayerModules\(restored\.layerModules\)/);
  assert.match(source, /attachedModuleIdsFromLayerModules\(layerModules\)/);
  assert.match(source, /const attachedCatalogModules = moduleCatalog\.modules\.filter/);
  assert.match(source, /attachedCatalogModules\.map/);
  assert.match(source, /if \(!graph\)\s*\{\s*continue;/s);
  assert.match(source, /cloneCanvasValue\(module\)/);
  assert.doesNotMatch(source, /withoutLegacyModuleOutputFallback\(safeClone\(module\)/);
  assert.match(
    bridgeSource,
    /nodeType === ["']reference_input["'] \|\| nodeType === ["']reference_output["']\)\s*\{\s*return false;/s
  );
  assert.match(
    bridgeSource,
    /visual_style:\s*\{[\s\S]*?layerId:\s*["']layer_10["'][\s\S]*?seedAllNodes:\s*true/s
  );
  assert.match(bridgeSource, /CATALOG_GRAPH_REPLACE_MODULE_IDS[\s\S]*?["']visual_style["']/s);
});

test("a manually connected module edge survives switching modules and project hydration", () => {
  const catalogEdges = [{ id: "seed", source: "input", target: "output" }];
  const languageBehaviorEdges = [
    ...catalogEdges,
    { id: "manual", source: "input", target: "validation" },
  ];

  const reopenedEdges = preserveStoredModuleEdges(languageBehaviorEdges, catalogEdges);
  const hydratedEdges = JSON.parse(JSON.stringify(reopenedEdges));

  assert.deepEqual(hydratedEdges, languageBehaviorEdges);
  assert.equal(hydratedEdges.some((edge) => edge.id === "manual"), true);
});

test("an intentionally empty saved graph is not restored from the catalog template", () => {
  const catalogEdges = [{ id: "seed", source: "input", target: "output" }];

  assert.deepEqual(preserveStoredModuleEdges([], catalogEdges), []);
});

test("the catalog template is used only when no saved edge collection exists", () => {
  const catalogEdges = [{ id: "seed", source: "input", target: "output" }];

  assert.deepEqual(preserveStoredModuleEdges(undefined, catalogEdges), catalogEdges);
});

test("a manually moved module node keeps its saved position when the catalog is merged", () => {
  const savedPosition = { x: 740, y: 315 };
  const catalogPosition = { x: 120, y: 70 };

  assert.deepEqual(
    preserveStoredModuleNodePosition(savedPosition, catalogPosition),
    savedPosition
  );
});

test("the catalog position is used only when a stored node has no position", () => {
  const catalogPosition = { x: 120, y: 70 };

  assert.deepEqual(
    preserveStoredModuleNodePosition(undefined, catalogPosition),
    catalogPosition
  );
});

test("reapplying the language preset keeps explicit choices but uses the current city imagery default", () => {
  const stored = {
    preset_id: "human_empathy_cn_v0_1",
    selected_options: ["warm", "occasional_city_imagery"],
    default_selected_options: ["warm", "occasional_city_imagery"],
    default_options: [
      { option_id: "warm", default_selected: true },
      { option_id: "occasional_city_imagery", default_selected: true },
    ],
    custom_text: "keep this instance text",
  };
  const seed = {
    preset_id: "human_empathy_cn_v0_1",
    selected_options: ["warm"],
    default_selected_options: ["warm"],
    default_options: [
      { option_id: "warm", default_selected: true },
      { option_id: "occasional_city_imagery", default_selected: false },
    ],
    custom_text: "",
  };
  const before = JSON.parse(JSON.stringify(stored));

  const merged = mergeChecklistTemplateDefaults(stored, seed);

  assert.deepEqual(merged.selected_options, ["warm", "occasional_city_imagery"]);
  assert.equal(merged.custom_text, "keep this instance text");
  assert.deepEqual(merged.default_selected_options, ["warm"]);
  assert.equal(
    merged.default_options.find((option) => option.option_id === "occasional_city_imagery").default_selected,
    false
  );
  assert.deepEqual(stored, before);
});

test("reapplying the language preset without an explicit choice keeps city imagery disabled", () => {
  const stored = {
    preset_id: "human_empathy_cn_v0_1",
    default_selected_options: ["warm", "occasional_city_imagery"],
    default_options: [
      { option_id: "warm", default_selected: true },
      { option_id: "occasional_city_imagery", default_selected: true },
    ],
  };
  const seed = {
    preset_id: "human_empathy_cn_v0_1",
    selected_options: ["warm"],
    default_selected_options: ["warm"],
    default_options: [
      { option_id: "warm", default_selected: true },
      { option_id: "occasional_city_imagery", default_selected: false },
    ],
  };

  const merged = mergeChecklistTemplateDefaults(stored, seed);

  assert.equal("selected_options" in merged, false);
  assert.deepEqual(merged.default_selected_options, ["warm"]);
  assert.equal(
    merged.default_options.find((option) => option.option_id === "occasional_city_imagery").default_selected,
    false
  );
});

test("legacy prefixed node ids resolve to the current catalog node during hydration", () => {
  assert.equal(
    normalizeCatalogNodeId("layer_8::language_habit::language_behavior_output_expression"),
    "language_behavior_output_expression"
  );
});

test("dangling module edges are pruned while valid edges keep their order", () => {
  const result = filterDanglingModuleGraphEdges(
    ["input", "normalize", "output"],
    [
      { id: "valid", source: "input", target: "normalize" },
      { id: "deleted-source", source: "old_input_basis", target: "normalize" },
      { id: "deleted-target", source: "normalize", target: "old_core_rules" },
      { id: "later-valid", source: "normalize", target: "output" },
    ]
  );

  assert.deepEqual(result.edges.map((edge) => edge.id), ["valid", "later-valid"]);
  assert.deepEqual(result.pruned, [
    { source: "old_input_basis", target: "normalize" },
    { source: "normalize", target: "old_core_rules" },
  ]);
});

test("persisted module edge cleanup is idempotent", () => {
  const first = filterDanglingModuleGraphEdges(
    ["input", "output"],
    [
      { id: "valid", source: "input", target: "output" },
      { id: "stale", source: "deleted", target: "output" },
    ]
  );
  const second = filterDanglingModuleGraphEdges(["input", "output"], first.edges);

  assert.deepEqual(second.edges, first.edges);
  assert.deepEqual(second.pruned, []);
});

test("the neural graph reserves a distinct bright color for Layer 5 modules", () => {
  assert.equal(resolveLayerColor("layer_5", 5, { layer_5: "#314a77" }), "#fde047");
  assert.equal(
    resolveModuleColor({
      moduleId: "memory_access_control",
      layerId: "layer_5",
      storedLayerId: "layer_5",
      layerColor: "#fde047",
      moduleUiColors: { "layer_5:memory_access_control": "#314a77" },
    }),
    "#fde047"
  );
});

test("Layer 12 references use available output node ids without duplicating existing pointers", () => {
  const result = mergeAvailableModuleReferencePointers(
    [
      {
        source_layer_id: "layer_1",
        source_module_id: "module_basic_identity",
        source_node_id: "stale-output",
        source_scope: "module",
        source_field_paths: [],
        reference_type: "references",
        required: true,
      },
    ],
    [
      {
        source_layer_id: "layer_1",
        source_module_id: "module_basic_identity",
        source_node_ids: ["basic-identity-output"],
        reference_type: "references",
      },
      {
        source_layer_id: "layer_3",
        source_module_id: "humanistic_behavior_boundary_config_v0_1",
        source_node_ids: ["behavior-boundary-output"],
        reference_type: "constrains",
      },
      {
        source_layer_id: "layer_9",
        source_module_id: "builtin_capability",
        source_node_ids: [],
        reference_type: "references",
      },
    ]
  );

  assert.equal(result.changed, true);
  assert.equal(result.addedCount, 1);
  assert.equal(result.repairedCount, 1);
  assert.deepEqual(result.references, [
    {
      source_layer_id: "layer_1",
      source_module_id: "module_basic_identity",
      source_node_id: "basic-identity-output",
      source_scope: "module",
      source_field_paths: [],
      reference_type: "references",
      required: true,
    },
    {
      source_layer_id: "layer_3",
      source_module_id: "humanistic_behavior_boundary_config_v0_1",
      source_node_id: "behavior-boundary-output",
      source_scope: "module",
      source_field_paths: [],
      reference_type: "constrains",
      required: true,
    },
  ]);

  const reloadedReferences = JSON.parse(JSON.stringify(result.references));
  const reopened = mergeAvailableModuleReferencePointers(reloadedReferences, [
    {
      source_layer_id: "layer_1",
      source_module_id: "module_basic_identity",
      source_node_ids: ["basic-identity-output"],
      reference_type: "references",
    },
    {
      source_layer_id: "layer_3",
      source_module_id: "humanistic_behavior_boundary_config_v0_1",
      source_node_ids: ["behavior-boundary-output"],
      reference_type: "constrains",
    },
  ]);
  assert.equal(reopened.changed, false);
  assert.deepEqual(reopened.references, result.references);
});

test("Stage 7.4.8 visual-style seed repairs reference ids and the Layer 3 interaction boundary", () => {
  const seedReferences = [
    ["first_presence_identity_core", "layer_1", "module_basic_identity", "basic_identity_output", "references"],
    ["first_presence_personality", "layer_2", "personality_traits", "personality_traits_output_summary", "references"],
    ["first_presence_safety_boundary", "layer_3", "humanistic_interaction_boundary_config_v0_1", "interaction_boundary_config_output", "constrains"],
    ["first_presence_memory_policy", "layer_5", "memory_access_control", "memory_access_output", "references"],
    ["first_presence_world_context", "layer_7", "world_setting", "worldview_module_output", "references"],
    ["first_presence_interaction_strategy", "layer_8", "interaction_strategy", "interaction_behavior_core_rules", "references"],
    ["first_presence_user_relationship", "layer_11", "user_relationship", "user_relationship_config_output", "references"],
  ].map(([reference_id, source_layer_id, source_module_id, source_node_id, reference_type]) => ({
    reference_id,
    source_layer_id,
    source_module_id,
    source_node_id,
    source_scope: "module",
    source_field_paths: [],
    reference_type,
    required: true,
  }));
  const oldReferences = seedReferences.map(({ reference_id: _referenceId, ...reference }) => ({ ...reference }));
  oldReferences[2] = {
    ...oldReferences[2],
    source_module_id: "humanistic_behavior_boundary_config_v0_1",
    source_node_id: "reference_output",
  };

  const repaired = mergeCatalogReferenceDeclarations(
    oldReferences,
    seedReferences,
    ["humanistic_behavior_boundary_config_v0_1"]
  );
  assert.equal(repaired.changed, true);
  assert.equal(repaired.references.length, 7);
  assert.deepEqual(
    repaired.references.map((reference) => reference.reference_id),
    seedReferences.map((reference) => reference.reference_id)
  );
  assert.ok(repaired.references.every((reference) => reference.source_scope === "module"));
  assert.ok(repaired.references.every((reference) => reference.required === true));
  assert.ok(repaired.references.every((reference) => typeof reference.reference_id === "string"));
  assert.equal(
    repaired.references.find((reference) => reference.reference_id === "first_presence_safety_boundary").source_module_id,
    "humanistic_interaction_boundary_config_v0_1"
  );
  assert.equal(
    repaired.references.find((reference) => reference.reference_id === "first_presence_safety_boundary").source_node_id,
    "interaction_boundary_config_output"
  );
  assert.equal(
    repaired.references.some((reference) => reference.source_module_id === "humanistic_behavior_boundary_config_v0_1"),
    false
  );

  const reopened = mergeCatalogReferenceDeclarations(
    JSON.parse(JSON.stringify(repaired.references)),
    seedReferences,
    ["humanistic_behavior_boundary_config_v0_1"]
  );
  assert.equal(reopened.changed, false);
  assert.deepEqual(reopened.references, repaired.references);
});

test("growth governance references keep available predecessors and skip sources without outputs", () => {
  const availableSources = [
    {
      source_layer_id: "layer_1",
      source_module_id: "module_basic_identity",
      source_node_ids: ["basic-identity-reference-output"],
      reference_type: "references",
    },
    {
      source_layer_id: "layer_3",
      source_module_id: "humanistic_data_boundary_config_v0_1",
      source_node_ids: ["data-boundary-reference-output"],
      reference_type: "constrains",
    },
    {
      source_layer_id: "layer_12",
      source_module_id: "self_evaluation",
      source_node_ids: ["consistency-correction-reference-output"],
      reference_type: "references",
    },
    {
      source_layer_id: "layer_13",
      source_module_id: "version_management",
      source_node_ids: [],
      reference_type: "references",
    },
  ];

  const result = mergeAvailableModuleReferencePointers([], availableSources);
  assert.equal(result.addedCount, 3);
  assert.deepEqual(
    result.references.map((reference) => [
      reference.source_layer_id,
      reference.source_module_id,
      reference.source_node_id,
      reference.reference_type,
    ]),
    [
      ["layer_1", "module_basic_identity", "basic-identity-reference-output", "references"],
      ["layer_3", "humanistic_data_boundary_config_v0_1", "data-boundary-reference-output", "constrains"],
      ["layer_12", "self_evaluation", "consistency-correction-reference-output", "references"],
    ]
  );

  const reloaded = mergeAvailableModuleReferencePointers(
    JSON.parse(JSON.stringify(result.references)),
    availableSources
  );
  assert.equal(reloaded.changed, false);
  assert.deepEqual(reloaded.references, result.references);
});

test("Stage 7.4.9 dialogue runtime profile preserves all catalog fields and authority references", () => {
  const fieldKeys = [
    "profile_id",
    "resident_type",
    "template_id",
    "response_style",
    "scenario_overrides",
    "few_shot_examples",
    "self_disclosure_style",
    "prohibited_language_overrides",
    "fallback_behavior",
    "memory_policy_reference",
    "relationship_policy_reference",
    "source_trace",
    "emotional_dialogue",
  ];
  const seedFields = fieldKeys.map((fieldKey, index) => ({
    field_key: fieldKey,
    field_value: { source: "catalog", index },
    field_type: index < 3 ? "text" : "object",
    required: false,
    i18n_keys: {
      label: `stage7_4_9.dialogueRuntime.field.${fieldKey}.label`,
    },
  }));
  const savedFields = fieldKeys.map((fieldKey, index) => ({
    field_key: fieldKey,
    field_value: { source: "saved", index, nested: { enabled: index % 2 === 0 } },
  }));

  const mergedFields = mergeCatalogFieldsPreservingValues(seedFields, savedFields);
  assert.equal(mergedFields.length, 13);
  for (const [index, field] of mergedFields.entries()) {
    assert.equal(field.field_key, fieldKeys[index]);
    assert.deepEqual(field.field_value, {
      source: "saved",
      index,
      nested: { enabled: index % 2 === 0 },
    });
    assert.equal(field.required, false);
  }
  assert.deepEqual(
    mergeCatalogFieldsPreservingValues(seedFields, JSON.parse(JSON.stringify(mergedFields))),
    mergedFields
  );

  const seedReferences = [
    {
      reference_id: "dialogue_runtime_personality_traits",
      source_layer_id: "layer_2",
      source_module_id: "personality_traits",
      source_node_id: "personality_traits_output_summary",
      source_scope: "module",
      source_field_paths: [],
      reference_type: "constrains",
      required: true,
    },
    {
      reference_id: "dialogue_runtime_emotion_pattern",
      source_layer_id: "layer_2",
      source_module_id: "emotion_pattern",
      source_node_id: "emotion_pattern_output_summary",
      source_scope: "module",
      source_field_paths: [],
      reference_type: "constrains",
      required: true,
    },
    {
      reference_id: "dialogue_runtime_high_risk_safety",
      source_layer_id: "layer_3",
      source_module_id: "humanistic_risk_response_config_v0_1",
      source_node_id: "risk_response_output",
      source_scope: "module",
      source_field_paths: [],
      reference_type: "constrains",
      required: true,
    },
    {
      reference_id: "dialogue_runtime_memory_policy",
      source_layer_id: "layer_5",
      source_module_id: "memory_access_control",
      source_node_id: "memory_access_output",
      source_scope: "module",
      source_field_paths: [],
      reference_type: "constrains",
      required: true,
    },
    {
      reference_id: "dialogue_runtime_relationship_policy",
      source_layer_id: "layer_11",
      source_module_id: "relationship_rule",
      source_node_id: "relationship_behavior_config_output",
      source_scope: "module",
      source_field_paths: [],
      reference_type: "constrains",
      required: true,
    },
    {
      reference_id: "dialogue_runtime_professional_limits",
      source_layer_id: "layer_12",
      source_module_id: "self_awareness",
      source_node_id: "self_awareness_output",
      source_scope: "module",
      source_field_paths: [],
      reference_type: "constrains",
      required: true,
    },
  ];
  const savedReferences = seedReferences.map(({ reference_id: _referenceId, ...reference }) => ({
    ...reference,
    saved_editor_note: "keep",
  }));
  const mergedReferences = mergeCatalogReferenceDeclarations(savedReferences, seedReferences);
  assert.equal(mergedReferences.changed, true);
  assert.deepEqual(
    mergedReferences.references.map((reference) => reference.reference_id),
    [
      "dialogue_runtime_personality_traits",
      "dialogue_runtime_emotion_pattern",
      "dialogue_runtime_high_risk_safety",
      "dialogue_runtime_memory_policy",
      "dialogue_runtime_relationship_policy",
      "dialogue_runtime_professional_limits",
    ]
  );
  assert.ok(mergedReferences.references.every((reference) => reference.source_scope === "module"));
  assert.ok(mergedReferences.references.every((reference) => reference.required === true));
  assert.ok(mergedReferences.references.every((reference) => reference.saved_editor_note === "keep"));

  const reopenedReferences = mergeCatalogReferenceDeclarations(
    JSON.parse(JSON.stringify(mergedReferences.references)),
    seedReferences
  );
  assert.equal(reopenedReferences.changed, false);
  assert.deepEqual(reopenedReferences.references, mergedReferences.references);
});

test("Stage 7.4.10 legacy emotional examples are separated before persistence and compile", () => {
  const sourceMetadata = {
    source_scope: "resident_profile",
    source_id: "dialogue_profile_resident_0001_v0_1",
    source_layer: "layer_8",
    template_id: "humanistic_companion_v0_1",
    override_source: "dialogue_runtime_profile",
  };
  const recommended = Array.from({ length: 20 }, (_, index) => ({
    example_id: `recommended_${index + 1}`,
    scene_id: `scene_${Math.floor(index / 2) + 1}`,
    status: "recommended",
    turns: [{ role: "user", text: `用户 ${index + 1}` }, { role: "assistant", text: `回应 ${index + 1}` }],
    usage: "behavior_guidance_only",
    not_fixed_response: true,
    not_keyword_matching: true,
  }));
  const prohibited = Array.from({ length: 10 }, (_, index) => ({
    example_id: `prohibited_${index + 1}`,
    scene_id: `scene_${index + 1}`,
    status: "prohibited",
    turns: [{ role: "user", text: `用户 ${index + 1}` }, { role: "assistant", text: `错误回应 ${index + 1}` }],
    why_forbidden: `原因 ${index + 1}`,
    preferred_response: `正确回应 ${index + 1}`,
    usage: "behavior_guidance_only",
    not_fixed_response: true,
    not_keyword_matching: true,
  }));
  const seedValue = {
    few_shot_selection: {
      usage: "behavior_guidance_only",
      selection_mode: "semantic_relevance",
      generation_allowed_statuses: ["recommended"],
      prohibited_examples_usage: "evaluation_only",
      inject_negative_examples: false,
      use_preferred_response_for_generation: true,
    },
    few_shot_examples: recommended.map((example) => ({ ...example, ...sourceMetadata })),
    negative_examples: prohibited.map((example) => ({
      ...example,
      usage: "evaluation_only",
      generation_allowed: false,
      ...sourceMetadata,
    })),
  };
  const legacyValue = {
    enabled: true,
    few_shot_selection: {
      usage: "behavior_guidance_only",
      selection_mode: "semantic_relevance",
    },
    few_shot_examples: [...recommended, ...prohibited],
  };

  const normalized = normalizeEmotionalDialogueExampleIsolation(legacyValue, seedValue);
  assert.equal(normalized.few_shot_examples.length, 20);
  assert.ok(normalized.few_shot_examples.every((example) => example.status === "recommended"));
  assert.equal(normalized.negative_examples.length, 10);
  assert.ok(normalized.negative_examples.every((example) => example.status === "prohibited"));
  assert.ok(normalized.negative_examples.every((example) => example.usage === "evaluation_only"));
  assert.ok(normalized.negative_examples.every((example) => example.generation_allowed === false));
  assert.deepEqual(normalized.few_shot_selection.generation_allowed_statuses, ["recommended"]);
  assert.equal(normalized.few_shot_selection.prohibited_examples_usage, "evaluation_only");
  assert.equal(normalized.few_shot_selection.inject_negative_examples, false);
  assert.equal(normalized.few_shot_selection.use_preferred_response_for_generation, true);
  assert.equal(normalized.enabled, true);
  assert.ok(
    [...normalized.few_shot_examples, ...normalized.negative_examples].every((example) =>
      Object.entries(sourceMetadata).every(([key, expected]) => example[key] === expected)
    )
  );

  const merged = mergeCatalogFieldsPreservingValues(
    [{ field_key: "emotional_dialogue", field_value: seedValue, required: false }],
    [{ field_key: "emotional_dialogue", field_value: legacyValue }]
  );
  assert.deepEqual(merged[0].field_value, normalized);
  assert.deepEqual(
    normalizeEmotionalDialogueExampleIsolation(normalized, seedValue),
    normalized
  );

  const alreadySeparatedWithoutSource = {
    ...legacyValue,
    few_shot_examples: recommended,
    negative_examples: seedValue.negative_examples.map(({ source_scope, source_id, source_layer, template_id, override_source, ...example }) => example),
  };
  const sourceRepaired = normalizeEmotionalDialogueExampleIsolation(
    alreadySeparatedWithoutSource,
    seedValue
  );
  assert.equal(sourceRepaired.few_shot_examples.length, 20);
  assert.equal(sourceRepaired.negative_examples.length, 10);
  assert.ok(
    [...sourceRepaired.few_shot_examples, ...sourceRepaired.negative_examples].every((example) =>
      Object.entries(sourceMetadata).every(([key, expected]) => example[key] === expected)
    )
  );
});

test("Stage 7.4.10 migrates only the legacy dialogue profile id across saved fields", () => {
  const seedFields = [
    { field_key: "profile_id", field_value: DIALOGUE_RUNTIME_PROFILE_ID },
    {
      field_key: "scenario_overrides",
      field_value: [
        {
          source_scope: "resident_profile",
          source_id: DIALOGUE_RUNTIME_PROFILE_ID,
        },
      ],
    },
    {
      field_key: "emotional_dialogue",
      field_value: {
        source_trace: {
          source_scope: "resident_profile",
          source_id: DIALOGUE_RUNTIME_PROFILE_ID,
        },
        few_shot_examples: [],
        negative_examples: [],
      },
    },
    {
      field_key: "custom_field",
      field_value: "catalog default",
    },
  ];
  const savedFields = [
    { field_key: "profile_id", field_value: LEGACY_DIALOGUE_RUNTIME_PROFILE_ID },
    {
      field_key: "scenario_overrides",
      field_value: [
        {
          source_scope: "resident_profile",
          source_id: LEGACY_DIALOGUE_RUNTIME_PROFILE_ID,
          text: "preserved",
        },
      ],
    },
    {
      field_key: "emotional_dialogue",
      field_value: {
        source_trace: {
          source_scope: "resident_profile",
          source_id: LEGACY_DIALOGUE_RUNTIME_PROFILE_ID,
        },
        few_shot_examples: [],
        negative_examples: [],
      },
    },
    {
      field_key: "custom_field",
      field_value: LEGACY_DIALOGUE_RUNTIME_PROFILE_ID,
    },
  ];

  const merged = mergeCatalogFieldsPreservingValues(seedFields, savedFields);
  assert.equal(merged[0].field_value, DIALOGUE_RUNTIME_PROFILE_ID);
  assert.equal(merged[1].field_value[0].source_id, DIALOGUE_RUNTIME_PROFILE_ID);
  assert.equal(merged[1].field_value[0].text, "preserved");
  assert.equal(
    merged[2].field_value.source_trace.source_id,
    DIALOGUE_RUNTIME_PROFILE_ID
  );
  assert.equal(
    merged[3].field_value,
    LEGACY_DIALOGUE_RUNTIME_PROFILE_ID
  );
  assert.equal(migrateDialogueRuntimeProfileId("resident_b_companion_v0_1"), "resident_b_companion_v0_1");
});

test("Stage 7.4.12 A2 identity cleanup preserves customized Few-shots and unrelated strings", () => {
  const customizedFewShots = [
    {
      example_id: "customized_example",
      source_scope: "resident_profile",
      source_id: LEGACY_DIALOGUE_RUNTIME_PROFILE_ID,
      turns: [{ role: "resident", text: "保留用户当前填写的示例。" }],
    },
  ];
  const fields = [
    {
      field_key: "profile_id",
      field_value: LEGACY_DIALOGUE_RUNTIME_PROFILE_ID,
    },
    {
      field_key: "few_shot_examples",
      field_value: customizedFewShots,
    },
    {
      field_key: "custom_field",
      field_value: LEGACY_DIALOGUE_RUNTIME_PROFILE_ID,
    },
  ];
  const stored = {
    profileContentRevision: DIALOGUE_RUNTIME_PROFILE_CONTENT_REVISION,
    identityCleanupRevision: "legacy_identity_revision",
    fields: JSON.parse(JSON.stringify(fields)),
    dataFields: JSON.parse(JSON.stringify(fields)),
    legacyFields: JSON.parse(JSON.stringify(fields)),
    legacyDataFields: JSON.parse(JSON.stringify(fields)),
    output: {
      profile_id: LEGACY_DIALOGUE_RUNTIME_PROFILE_ID,
      few_shot_examples: JSON.parse(JSON.stringify(customizedFewShots)),
      custom_output: LEGACY_DIALOGUE_RUNTIME_PROFILE_ID,
    },
  };
  const seed = {
    profileContentRevision: DIALOGUE_RUNTIME_PROFILE_CONTENT_REVISION,
    identityCleanupRevision:
      STAGE7_4_12_A2_SOURCE_OUTPUT_IDENTITY_CLEANUP_REVISION,
  };

  const migrated = migrateDialogueRuntimeProfileContentCopies(stored, seed);
  assert.equal(migrated.migrated, true);
  assert.equal(
    migrated.value.identityCleanupRevision,
    STAGE7_4_12_A2_SOURCE_OUTPUT_IDENTITY_CLEANUP_REVISION
  );
  assert.equal(
    migrated.value.profileContentRevision,
    DIALOGUE_RUNTIME_PROFILE_CONTENT_REVISION
  );
  for (const copy of [
    migrated.value.fields,
    migrated.value.dataFields,
    migrated.value.legacyFields,
    migrated.value.legacyDataFields,
  ]) {
    assert.equal(
      copy.find((field) => field.field_key === "profile_id").field_value,
      DIALOGUE_RUNTIME_PROFILE_ID
    );
    const examples = copy.find(
      (field) => field.field_key === "few_shot_examples"
    ).field_value;
    assert.equal(examples[0].source_id, DIALOGUE_RUNTIME_PROFILE_ID);
    assert.equal(
      examples[0].turns[0].text,
      "保留用户当前填写的示例。"
    );
    assert.equal(
      copy.find((field) => field.field_key === "custom_field").field_value,
      LEGACY_DIALOGUE_RUNTIME_PROFILE_ID
    );
  }
  assert.equal(migrated.value.output.profile_id, DIALOGUE_RUNTIME_PROFILE_ID);
  assert.equal(
    migrated.value.output.few_shot_examples[0].source_id,
    DIALOGUE_RUNTIME_PROFILE_ID
  );
  assert.equal(
    migrated.value.output.few_shot_examples[0].turns[0].text,
    "保留用户当前填写的示例。"
  );
  assert.equal(
    migrated.value.output.custom_output,
    LEGACY_DIALOGUE_RUNTIME_PROFILE_ID
  );

  const reopened = migrateDialogueRuntimeProfileContentCopies(
    migrated.value,
    seed
  );
  assert.equal(reopened.migrated, false);
  assert.deepEqual(reopened.value, migrated.value);
});

test("Stage 7.4.10 migrates stale dialogue Few-shots across Canvas compatibility copies once", () => {
  const profile = JSON.parse(
    readFileSync(
      new URL("../../api/app/registry/dialogue_runtime_profile.json", import.meta.url),
      "utf8"
    )
  );
  const seedExamples = profile.few_shot_examples;
  const staleExamples = JSON.parse(JSON.stringify(seedExamples));
  staleExamples[0].turns.at(-1).text =
    "你好，我叫林瑄，是一位以西安为生活语境的数字居民。";
  staleExamples[22].turns.at(-1).text =
    "不是。我可以和你认真聊日常，但不会把我们的关系默认成恋爱。叫我林瑄就好。";
  staleExamples[5].saved_editor_note = "preserve unrelated customization";
  const fields = [
    { field_key: "response_style", field_value: { saved: true } },
    { field_key: "few_shot_examples", field_value: staleExamples },
    { field_key: "custom_field", field_value: { nested: ["keep"] } },
  ];
  const stored = {
    fields: JSON.parse(JSON.stringify(fields)),
    dataFields: JSON.parse(JSON.stringify(fields)),
    legacyFields: JSON.parse(JSON.stringify(fields)),
    legacyDataFields: JSON.parse(JSON.stringify(fields)),
    output: {
      profile_id: DIALOGUE_RUNTIME_PROFILE_ID,
      few_shot_examples: JSON.parse(JSON.stringify(staleExamples)),
      custom_output: { keep: true },
    },
  };
  const seed = {
    profileContentRevision: DIALOGUE_RUNTIME_PROFILE_CONTENT_REVISION,
    fields: [{ field_key: "few_shot_examples", field_value: seedExamples }],
    output: { few_shot_examples: seedExamples },
  };

  const migrated = migrateDialogueRuntimeProfileContentCopies(stored, seed);
  assert.equal(migrated.migrated, true);
  assert.equal(migrated.value.profileContentRevision, DIALOGUE_RUNTIME_PROFILE_CONTENT_REVISION);
  for (const copy of [
    migrated.value.fields,
    migrated.value.dataFields,
    migrated.value.legacyFields,
    migrated.value.legacyDataFields,
  ]) {
    const examples = copy.find((field) => field.field_key === "few_shot_examples").field_value;
    assert.deepEqual(examples[0], seedExamples[0]);
    assert.deepEqual(examples[22], seedExamples[22]);
    assert.equal(examples[5].saved_editor_note, "preserve unrelated customization");
    assert.doesNotMatch(JSON.stringify(examples), /林瑄/);
    assert.deepEqual(copy.find((field) => field.field_key === "response_style").field_value, {
      saved: true,
    });
    assert.deepEqual(copy.find((field) => field.field_key === "custom_field").field_value, {
      nested: ["keep"],
    });
  }
  assert.deepEqual(migrated.value.output.few_shot_examples[0], seedExamples[0]);
  assert.deepEqual(migrated.value.output.few_shot_examples[22], seedExamples[22]);
  assert.deepEqual(migrated.value.output.custom_output, { keep: true });

  const reopened = migrateDialogueRuntimeProfileContentCopies(migrated.value, seed);
  assert.equal(reopened.migrated, false);
  assert.deepEqual(reopened.value, migrated.value);

  const savedCanvas = serializeCanvasState({
    moduleGraphs: {
      "layer_8::dialogue_runtime_profile": {
        moduleId: "layer_8::dialogue_runtime_profile",
        nodes: [
          {
            id: "dialogue_runtime_profile_config_input",
            data: {
              schemaNode: {
                node_id: "dialogue_runtime_profile_config_input",
                data: {
                  catalog_module_id: "dialogue_runtime_profile",
                  catalog_node_id: "dialogue_runtime_profile_config_input",
                  params: {
                    profile_content_revision: migrated.value.profileContentRevision,
                    fields: migrated.value.fields,
                    legacy_fields: migrated.value.legacyFields,
                    legacy_data_fields: migrated.value.legacyDataFields,
                  },
                  fields: migrated.value.dataFields,
                },
              },
            },
          },
          {
            id: "dialogue_runtime_profile_output",
            data: {
              schemaNode: {
                node_id: "dialogue_runtime_profile_output",
                data: {
                  catalog_module_id: "dialogue_runtime_profile",
                  catalog_node_id: "dialogue_runtime_profile_output",
                  params: {},
                  outputs: { dialogue_runtime_profile_config: migrated.value.output },
                },
              },
            },
          },
        ],
        edges: [],
      },
    },
  });
  const imported = importCanvasState(JSON.stringify(savedCanvas));
  assert.equal(imported.success, true);
  const reopenedNodes = imported.state.moduleGraphs["layer_8::dialogue_runtime_profile"].nodes;
  const reopenedInput = reopenedNodes[0].data.schemaNode.data;
  const reopenedOutput = reopenedNodes[1].data.schemaNode.data.outputs.dialogue_runtime_profile_config;
  assert.equal(
    reopenedInput.params.profile_content_revision,
    DIALOGUE_RUNTIME_PROFILE_CONTENT_REVISION
  );
  assert.deepEqual(reopenedInput.params.fields, migrated.value.fields);
  assert.deepEqual(reopenedInput.fields, migrated.value.dataFields);
  assert.deepEqual(reopenedInput.params.legacy_fields, migrated.value.legacyFields);
  assert.deepEqual(reopenedInput.params.legacy_data_fields, migrated.value.legacyDataFields);
  assert.deepEqual(reopenedOutput, migrated.value.output);
  assert.doesNotMatch(JSON.stringify(reopenedNodes), /林瑄/);

  const newCanvas = { ...stored, profileContentRevision: DIALOGUE_RUNTIME_PROFILE_CONTENT_REVISION };
  const untouched = migrateDialogueRuntimeProfileContentCopies(newCanvas, seed);
  assert.equal(untouched.migrated, false);
  assert.equal(untouched.value, newCanvas);
});

test("Stage 7.4.11 rebuilds the legacy expression graph once and preserves resident-authored fields", () => {
  const instanceId = "layer_8::emotion_reaction";
  const nodeIds = [
    "expression_context_input",
    "expression_allowed_state_recognition",
    "expression_state_selection_rules",
    "expression_personality_consistency_validation",
    "expression_relationship_safety_validation",
    "expression_intensity_calculation",
    "expression_state_normalize_fallback_validation",
    "expression_state_output",
    "expression_state_reference_output",
  ];
  const flowId = (nodeId) => `${instanceId}::${nodeId}`;
  const seedFields = [
    {
      field_key: "expression_state",
      field_value: "neutral",
      field_type: "text",
      i18n_keys: { label: "layer8.emotionalExpression.field.state.label" },
    },
    {
      field_key: "expression_intensity",
      field_value: 0,
      field_type: "number",
      minimum: 0,
      maximum: 1,
      i18n_keys: { label: "layer8.emotionalExpression.field.intensity.label" },
    },
    {
      field_key: "resident_expression_notes",
      field_value: "",
      field_type: "long_text",
      i18n_keys: { label: "layer8.emotionalExpression.field.notes.label" },
    },
  ];
  const seedNodes = nodeIds.map((catalogNodeId, index) => {
    const nodeType = index === 0
      ? "reference_input"
      : index === nodeIds.length - 1
        ? "reference_output"
        : index === nodeIds.length - 2
          ? "module_output"
          : "text_config";
    const fields = index === 0 ? JSON.parse(JSON.stringify(seedFields)) : [];
    return {
      node_id: flowId(catalogNodeId),
      type: nodeType,
      title_key: `layer8.emotionalExpression.node.${catalogNodeId}.title`,
      title_fallback: catalogNodeId,
      position: { x: index * 260, y: 40 },
      data: {
        catalog_preconfigured: true,
        catalog_module_id: "emotion_reaction",
        catalog_node_id: catalogNodeId,
        node_type: nodeType,
        params: index === 0
          ? {
              mode: "generic_fields",
              content_revision: EXPRESSION_STATE_SEMANTICS_CONTENT_REVISION,
              validation_compatibility_revision:
                EXPRESSION_VISUAL_VALIDATION_COMPATIBILITY_REVISION,
              fields,
            }
          : { semantic_rule: catalogNodeId },
        fields: JSON.parse(JSON.stringify(fields)),
        i18n_keys: {
          name: `layer8.emotionalExpression.node.${catalogNodeId}.title`,
          description: `layer8.emotionalExpression.node.${catalogNodeId}.description`,
        },
      },
    };
  });
  const seedEdges = nodeIds.slice(0, -1).map((sourceId, index) => ({
    id: `${sourceId}_to_${nodeIds[index + 1]}`,
    edge_id: `${sourceId}_to_${nodeIds[index + 1]}`,
    source: flowId(sourceId),
    target: flowId(nodeIds[index + 1]),
  }));
  seedEdges.push(
    {
      id: "expression_context_to_selection_references",
      edge_id: "expression_context_to_selection_references",
      source: flowId(nodeIds[0]),
      target: flowId(nodeIds[2]),
    },
    {
      id: "expression_context_to_personality_references",
      edge_id: "expression_context_to_personality_references",
      source: flowId(nodeIds[0]),
      target: flowId(nodeIds[3]),
    },
    {
      id: "expression_context_to_safety_references",
      edge_id: "expression_context_to_safety_references",
      source: flowId(nodeIds[0]),
      target: flowId(nodeIds[4]),
    },
    {
      id: "expression_context_to_intensity_references",
      edge_id: "expression_context_to_intensity_references",
      source: flowId(nodeIds[0]),
      target: flowId(nodeIds[5]),
    },
    {
      id: "expression_context_to_fallback_references",
      edge_id: "expression_context_to_fallback_references",
      source: flowId(nodeIds[0]),
      target: flowId(nodeIds[6]),
    }
  );

  const legacyNode = (catalogNodeId, index, params, fields = []) => ({
    id: flowId(catalogNodeId),
    type: "workflowNode",
    position: { x: 700 + index * 15, y: 300 + index * 10 },
    data: {
      schemaNode: {
        node_id: flowId(catalogNodeId),
        type: index === 0 ? "field_reference" : "text_config",
        title_key: `layer8.detailBehavior.node.${catalogNodeId}.title`,
        position: { x: 700 + index * 15, y: 300 + index * 10 },
        data: {
          catalog_preconfigured: true,
          catalog_module_id: "emotion_reaction",
          catalog_node_id: catalogNodeId,
          node_type: index === 0 ? "field_reference" : "text_config",
          ui_name: index === 0 ? "保留的表达上下文名称" : "",
          params: { ...params, ...(fields.length ? { fields } : {}) },
          fields,
          i18n_keys: { name: `layer8.detailBehavior.node.${catalogNodeId}.title` },
        },
      },
    },
  });
  const legacyFields = [
    { field_key: "expression_state", field_value: "caring" },
    { field_key: "expression_intensity", field_value: 0.72 },
    { field_key: "resident_expression_notes", field_value: "既有居民表达备注。" },
    { field_key: "custom_resident_rule", field_value: "保留居民自定义字段", field_type: "long_text" },
  ];
  const legacyNodes = [
    legacyNode(
      "detail_behavior_input_basis",
      0,
      {
        recommended_references: [{ source_module_id: "particle_avatar" }],
        checkbox_config: { selected_options: [], custom_text: "" },
      },
      legacyFields
    ),
    legacyNode("detail_behavior_core_rules", 1, {
      checkbox_config: {
        selected_options: ["more_particle_hint_friendly"],
        optional_options: [{ option_id: "more_particle_hint_friendly" }],
        custom_text: "先听完居民表达，再选择合适状态。",
      },
    }),
    legacyNode("detail_behavior_boundary_limits", 2, {
      particle_energy: 0.4,
      checkbox_config: { selected_options: ["no_gaze_behavior_description"], custom_text: "" },
    }),
    legacyNode("detail_behavior_output_expression", 3, {
      checkbox_config: {
        selected_options: ["low_amplitude_particle_hint"],
        default_options: [{ option_id: "low_amplitude_particle_hint" }],
        custom_text: "关系紧张时降低表达强度。",
      },
    }),
    legacyNode("detail_behavior_validation", 4, {
      checkbox_config: { selected_options: ["check_template_style"], custom_text: "" },
    }),
  ];
  const legacyEdges = legacyNodes.slice(0, -1).map((node, index) => ({
    id: `legacy_${index}`,
    source: node.id,
    target: legacyNodes[index + 1].id,
  }));
  const stored = { nodes: legacyNodes, edges: legacyEdges };
  const seed = { nodes: seedNodes, edges: seedEdges };

  const migrated = migrateExpressionStateSemanticsGraph(stored, seed);
  assert.equal(migrated.migrated, true);
  assert.equal(migrated.value.nodes.length, 9);
  assert.equal(migrated.value.edges.length, 13);
  assert.deepEqual(
    migrated.value.nodes.map((node) => node.data.catalog_node_id),
    nodeIds
  );
  assert.deepEqual(
    migrated.value.edges.slice(0, 8).map((edge) => [edge.source.split("::").at(-1), edge.target.split("::").at(-1)]),
    nodeIds.slice(0, -1).map((sourceId, index) => [sourceId, nodeIds[index + 1]])
  );

  const input = migrated.value.nodes[0];
  assert.equal(input.data.params.content_revision, EXPRESSION_STATE_SEMANTICS_CONTENT_REVISION);
  assert.equal(
    input.data.params.validation_compatibility_revision,
    EXPRESSION_VISUAL_VALIDATION_COMPATIBILITY_REVISION
  );
  assert.deepEqual(input.position, legacyNodes[0].position);
  assert.equal(input.data.ui_name, "保留的表达上下文名称");
  const migratedFields = input.data.params.fields;
  assert.deepEqual(input.data.params.legacy_fields, migratedFields);
  assert.deepEqual(input.data.params.legacy_data_fields, migratedFields);
  assert.equal(
    input.data.params.compatibility_authority_status_governance_revision,
    STAGE7_4_12_A4_COMPATIBILITY_AUTHORITY_STATUS_GOVERNANCE_REVISION
  );
  assert.equal(migratedFields.find((field) => field.field_key === "expression_state").field_value, "caring");
  assert.equal(migratedFields.find((field) => field.field_key === "expression_intensity").field_value, 0.72);
  assert.equal(
    migratedFields.find((field) => field.field_key === "resident_expression_notes").field_value,
    "既有居民表达备注。\n\n先听完居民表达，再选择合适状态。\n\n关系紧张时降低表达强度。"
  );
  assert.equal(
    migratedFields.find((field) => field.field_key === "custom_resident_rule").field_value,
    "保留居民自定义字段"
  );
  assert.equal(seedNodes[0].data.params.fields[2].field_value, "");
  assert.doesNotMatch(
    JSON.stringify(migrated.value),
    /particle|checkbox_config|selected_options|low_amplitude|shader|glow/i
  );

  const invalidStored = JSON.parse(JSON.stringify(stored));
  const invalidFields = invalidStored.nodes[0].data.schemaNode.data.params.fields;
  invalidFields.find((field) => field.field_key === "expression_state").field_value = "unsupported";
  invalidFields.find((field) => field.field_key === "expression_intensity").field_value = 2.4;
  const normalized = migrateExpressionStateSemanticsGraph(invalidStored, seed);
  const normalizedFields = normalized.value.nodes[0].data.params.fields;
  assert.equal(normalizedFields.find((field) => field.field_key === "expression_state").field_value, "neutral");
  assert.equal(normalizedFields.find((field) => field.field_key === "expression_intensity").field_value, 1);
  assert.equal(
    normalizedFields.find((field) => field.field_key === "resident_expression_notes").field_value,
    "既有居民表达备注。\n\n先听完居民表达，再选择合适状态。\n\n关系紧张时降低表达强度。"
  );

  const caseStored = JSON.parse(JSON.stringify(stored));
  const caseFields = caseStored.nodes[0].data.schemaNode.data.params.fields;
  caseFields.find((field) => field.field_key === "expression_state").field_value = " CaLm ";
  caseFields.find((field) => field.field_key === "expression_intensity").field_value = -4;
  const caseNormalized = migrateExpressionStateSemanticsGraph(caseStored, seed);
  const caseNormalizedFields = caseNormalized.value.nodes[0].data.params.fields;
  assert.equal(
    caseNormalizedFields.find((field) => field.field_key === "expression_state").field_value,
    "calm"
  );
  assert.equal(
    caseNormalizedFields.find((field) => field.field_key === "expression_intensity").field_value,
    0
  );
  for (const lifecycleState of ["thinking", "speaking", "loading", "error"]) {
    const lifecycleStored = JSON.parse(JSON.stringify(stored));
    lifecycleStored.nodes[0].data.schemaNode.data.params.fields.find(
      (field) => field.field_key === "expression_state"
    ).field_value = lifecycleState;
    const lifecycleNormalized = migrateExpressionStateSemanticsGraph(
      lifecycleStored,
      seed
    );
    assert.equal(
      lifecycleNormalized.value.nodes[0].data.params.fields.find(
        (field) => field.field_key === "expression_state"
      ).field_value,
      "neutral"
    );
  }

  const reopened = migrateExpressionStateSemanticsGraph(migrated.value, seed);
  assert.equal(reopened.migrated, false);
  assert.equal(reopened.value, migrated.value);

  const bridgeSource = readFileSync(new URL("../src/store/module-state-bridge.ts", import.meta.url), "utf8");
  assert.match(bridgeSource, /EXPRESSION_STATE_GRAPH_ID = ["']layer_8::emotion_reaction["']/);
  assert.match(
    bridgeSource,
    /migrateExpressionStateSemanticsSeed[\s\S]*?migrateExpressionStateSemanticsGraph\([\s\S]*?const expressionMigrated = migrateExpressionStateSemanticsSeed/s
  );
  assert.match(
    bridgeSource,
    /moduleNodeId === EXPRESSION_STATE_GRAPH_ID[\s\S]*?saveModuleGraphState\(moduleNodeId, mergedGraph\.nodes, mergedGraph\.edges\)/s
  );
});

test("Stage 7.4.11 rebuilds legacy particle configuration once and preserves resident visual content", () => {
  const instanceId = "layer_10::particle_avatar";
  const nodeIds = [
    "particle_visual_config_input",
    "particle_base_color_resolution",
    "particle_user_color_override_rules",
    "particle_expression_state_relative_mapping",
    "particle_expression_intensity_adaptation",
    "particle_lifecycle_priority_validation",
    "particle_parameter_range_validation",
    "particle_state_transition_rules",
    "particle_mapping_config_output",
    "particle_mapping_reference_output",
  ];
  const flowId = (nodeId) => `${instanceId}::${nodeId}`;
  const relativeLimits = {
    brightness_multiplier: [0.7, 1.25],
    saturation_multiplier: [0.65, 1.2],
    color_temperature_offset: [-0.15, 0.15],
    energy_multiplier: [0.7, 1.25],
    motion_speed_multiplier: [0.75, 1.2],
    diffusion_multiplier: [0.75, 1.25],
  };
  const relativeDefaults = {
    neutral: [1, 1, 0, 1, 1, 1],
    calm: [0.96, 0.9, -0.03, 0.88, 0.86, 0.92],
    caring: [1.06, 1.04, 0.05, 1.02, 0.94, 1.02],
    subdued: [0.82, 0.75, -0.08, 0.78, 0.8, 0.86],
    joyful: [1.15, 1.12, 0.08, 1.18, 1.12, 1.14],
  };
  const parameterNames = Object.keys(relativeLimits);
  const seedFields = [
    ["user_current_base_color", ""],
    ["resident_default_base_color", "#7aa2f7"],
    ["primary_color", ""],
    ["secondary_color", ""],
    ["highlight_color", ""],
  ].map(([field_key, field_value]) => ({
    field_key,
    field_value,
    field_type: "text",
  }));
  for (const [state, defaults] of Object.entries(relativeDefaults)) {
    parameterNames.forEach((parameter, index) => {
      const [minimum, maximum] = relativeLimits[parameter];
      seedFields.push({
        field_key: `${state}_${parameter}`,
        field_value: defaults[index],
        field_type: "number",
        minimum,
        maximum,
      });
    });
  }
  seedFields.push(
    {
      field_key: "transition_duration",
      field_value: 0.6,
      field_type: "number",
      minimum: 0,
      maximum: 10,
    },
    {
      field_key: "minimum_hold_duration",
      field_value: 0.35,
      field_type: "number",
      minimum: 0,
      maximum: 10,
    },
    {
      field_key: "transition_style",
      field_value: "smooth",
      field_type: "text",
    }
  );
  const nodeTypes = [
    "reference_input",
    "text_config",
    "text_config",
    "text_config",
    "text_config",
    "validation",
    "validation",
    "text_config",
    "module_output",
    "reference_output",
  ];
  const seedNodes = nodeIds.map((catalogNodeId, index) => {
    const fields = index === 0 ? JSON.parse(JSON.stringify(seedFields)) : [];
    return {
      node_id: flowId(catalogNodeId),
      type: nodeTypes[index],
      position: { x: index * 360, y: 120 },
      data: {
        catalog_preconfigured: true,
        catalog_module_id: "particle_avatar",
        catalog_node_id: catalogNodeId,
        node_type: nodeTypes[index],
        params:
          index === 0
            ? {
                mode: "generic_fields",
                content_revision: PARTICLE_EXPRESSION_RELATIVE_MAPPING_CONTENT_REVISION,
                source_priority_revision:
                  PARTICLE_MAPPING_SOURCE_PRIORITY_FIX_REVISION,
                validation_compatibility_revision:
                  EXPRESSION_VISUAL_VALIDATION_COMPATIBILITY_REVISION,
                fields,
              }
            : {
                config_mode: catalogNodeId,
                ...(index === 3
                  ? {
                      source_priority_revision:
                        PARTICLE_MAPPING_SOURCE_PRIORITY_FIX_REVISION,
                    }
                  : {}),
              },
        fields: JSON.parse(JSON.stringify(fields)),
      },
    };
  });
  const seedEdges = nodeIds.slice(0, -1).map((sourceId, index) => ({
    id: `${sourceId}_to_${nodeIds[index + 1]}`,
    edge_id: `${sourceId}_to_${nodeIds[index + 1]}`,
    source: flowId(sourceId),
    target: flowId(nodeIds[index + 1]),
  }));
  seedEdges.push(
    {
      id: "particle_visual_config_input_to_particle_expression_state_relative_mapping",
      edge_id: "particle_visual_config_input_to_particle_expression_state_relative_mapping",
      source: flowId(nodeIds[0]),
      target: flowId(nodeIds[3]),
    },
    {
      id: "particle_visual_config_input_to_particle_expression_intensity_adaptation",
      edge_id: "particle_visual_config_input_to_particle_expression_intensity_adaptation",
      source: flowId(nodeIds[0]),
      target: flowId(nodeIds[4]),
    }
  );
  const legacyFields = [
    { field_key: "user_current_base_color", field_value: "#010203" },
    { field_key: "primary_color", field_value: "#112233" },
    { field_key: "secondary_color", field_value: "#445566" },
    { field_key: "highlight_color", field_value: "#778899" },
    { field_key: "neutral_brightness_multiplier", field_value: 9 },
    { field_key: "calm_saturation_multiplier", field_value: 0.2 },
    { field_key: "caring_color_temperature_offset", field_value: "not-a-number" },
    { field_key: "subdued_energy_multiplier", field_value: -3 },
    { field_key: "joyful_motion_speed_multiplier", field_value: 8 },
    { field_key: "neutral_diffusion_multiplier", field_value: 0 },
    { field_key: "transition_duration", field_value: -5 },
    { field_key: "minimum_hold_duration", field_value: "not-a-number" },
    { field_key: "transition_style", field_value: "flash" },
    {
      field_key: "custom_particle_note",
      field_value: "保留已有粒子配置说明。",
      field_type: "long_text",
    },
  ];
  const legacyNode = {
    id: `${instanceId}::legacy_particle_avatar`,
    type: "workflowNode",
    position: { x: 720, y: 380 },
    data: {
      schemaNode: {
        node_id: `${instanceId}::legacy_particle_avatar`,
        type: "particle_avatar",
        position: { x: 720, y: 380 },
        data: {
          catalog_preconfigured: true,
          catalog_module_id: "particle_avatar",
          node_type: "particle_avatar",
          ui_name: "保留的粒子视觉输入",
          preset: "aurora",
          color: "#2468ac",
          density: 0.82,
          resident_visual_note: { keep: true },
          params: {
            fields: legacyFields,
            custom_strength: 0.44,
            checkbox_config: { custom_text: "保留旧参数中的用户视觉备注。" },
          },
          fields: legacyFields,
        },
      },
    },
  };
  const stored = { nodes: [legacyNode], edges: [] };
  const seed = { nodes: seedNodes, edges: seedEdges };

  const migrated = migrateParticleExpressionRelativeMappingGraph(stored, seed);
  assert.equal(migrated.migrated, true);
  assert.equal(migrated.value.nodes.length, 10);
  assert.equal(migrated.value.edges.length, 11);
  assert.deepEqual(
    migrated.value.nodes.map((node) => node.data.catalog_node_id),
    nodeIds
  );
  assert.deepEqual(
    migrated.value.edges.slice(0, 9).map((edge) => [
      edge.source.split("::").at(-1),
      edge.target.split("::").at(-1),
    ]),
    nodeIds.slice(0, -1).map((sourceId, index) => [sourceId, nodeIds[index + 1]])
  );

  const input = migrated.value.nodes[0];
  assert.equal(
    input.data.params.content_revision,
    PARTICLE_EXPRESSION_RELATIVE_MAPPING_CONTENT_REVISION
  );
  assert.equal(
    input.data.params.validation_compatibility_revision,
    EXPRESSION_VISUAL_VALIDATION_COMPATIBILITY_REVISION
  );
  assert.equal(
    migrated.value.nodes[3].data.params.source_priority_revision,
    PARTICLE_MAPPING_SOURCE_PRIORITY_FIX_REVISION
  );
  assert.deepEqual(input.position, legacyNode.position);
  assert.equal(input.data.ui_name, "保留的粒子视觉输入");
  const fields = input.data.params.fields;
  assert.deepEqual(input.data.params.legacy_fields, fields);
  assert.deepEqual(input.data.params.legacy_data_fields, fields);
  assert.equal(
    input.data.params.compatibility_authority_status_governance_revision,
    STAGE7_4_12_A4_COMPATIBILITY_AUTHORITY_STATUS_GOVERNANCE_REVISION
  );
  const valueOf = (fieldKey) =>
    fields.find((field) => field.field_key === fieldKey)?.field_value;
  assert.equal(valueOf("resident_default_base_color"), "#2468ac");
  assert.equal(valueOf("user_current_base_color"), "#010203");
  assert.equal(valueOf("primary_color"), "#112233");
  assert.equal(valueOf("secondary_color"), "#445566");
  assert.equal(valueOf("highlight_color"), "#778899");
  assert.equal(valueOf("neutral_brightness_multiplier"), 1.25);
  assert.equal(valueOf("calm_saturation_multiplier"), 0.65);
  assert.equal(valueOf("caring_color_temperature_offset"), 0);
  assert.equal(valueOf("subdued_energy_multiplier"), 0.7);
  assert.equal(valueOf("joyful_motion_speed_multiplier"), 1.2);
  assert.equal(valueOf("neutral_diffusion_multiplier"), 0.75);
  assert.equal(valueOf("calm_brightness_multiplier"), 1);
  assert.equal(valueOf("transition_duration"), 0);
  assert.equal(valueOf("minimum_hold_duration"), 0.35);
  assert.equal(valueOf("transition_style"), "smooth");
  assert.equal(valueOf("custom_particle_note"), "保留已有粒子配置说明。");
  assert.equal(valueOf("preset"), "aurora");
  assert.equal(valueOf("density"), 0.82);
  assert.equal(valueOf("custom_strength"), 0.44);
  assert.equal(valueOf("legacy_custom_text"), "保留旧参数中的用户视觉备注。");
  assert.deepEqual(valueOf("resident_visual_note"), { keep: true });
  assert.equal(valueOf("color"), undefined);
  assert.equal(seedNodes[0].data.params.fields[1].field_value, "#7aa2f7");
  for (const [parameter, [minimum, maximum]] of Object.entries(relativeLimits)) {
    const field = fields.find((candidate) =>
      candidate.field_key.endsWith(`_${parameter}`)
    );
    assert.equal(field.minimum, minimum);
    assert.equal(field.maximum, maximum);
  }

  const explicitResidentColor = JSON.parse(JSON.stringify(stored));
  explicitResidentColor.nodes[0].data.schemaNode.data.params.fields.push({
    field_key: "resident_default_base_color",
    field_value: "#abcdef",
  });
  const explicitMigration = migrateParticleExpressionRelativeMappingGraph(
    explicitResidentColor,
    seed
  );
  assert.equal(
    explicitMigration.value.nodes[0].data.params.fields.find(
      (field) => field.field_key === "resident_default_base_color"
    ).field_value,
    "#abcdef"
  );

  const paramsColor = JSON.parse(JSON.stringify(stored));
  delete paramsColor.nodes[0].data.schemaNode.data.color;
  paramsColor.nodes[0].data.schemaNode.data.params.color = "#13579b";
  const paramsColorMigration = migrateParticleExpressionRelativeMappingGraph(
    paramsColor,
    seed
  );
  assert.equal(
    paramsColorMigration.value.nodes[0].data.params.fields.find(
      (field) => field.field_key === "resident_default_base_color"
    ).field_value,
    "#13579b"
  );

  const fieldBaseColor = JSON.parse(JSON.stringify(stored));
  delete fieldBaseColor.nodes[0].data.schemaNode.data.color;
  fieldBaseColor.nodes[0].data.schemaNode.data.params.fields.push({
    field_key: "base_color",
    field_value: "#97531f",
  });
  const fieldBaseColorMigration = migrateParticleExpressionRelativeMappingGraph(
    fieldBaseColor,
    seed
  );
  assert.equal(
    fieldBaseColorMigration.value.nodes[0].data.params.fields.find(
      (field) => field.field_key === "resident_default_base_color"
    ).field_value,
    "#97531f"
  );

  const reopened = migrateParticleExpressionRelativeMappingGraph(migrated.value, seed);
  assert.equal(reopened.migrated, false);
  assert.equal(reopened.value, migrated.value);

  const staleCopies = JSON.parse(JSON.stringify(seed));
  const staleInputFields = staleCopies.nodes[0].data.params.fields;
  for (const field of staleInputFields) {
    if (
      ["calm", "caring", "subdued", "joyful"].some((state) =>
        field.field_key.startsWith(`${state}_`)
      )
    ) {
      field.field_value = field.field_key.endsWith(
        "_color_temperature_offset"
      )
        ? 0
        : 1;
    }
  }
  delete staleCopies.nodes[3].data.params.source_priority_revision;
  staleCopies.nodes[3].data.params.fields = [
    { field_key: "calm_brightness_multiplier", field_value: 0.96 },
    { field_key: "caring_brightness_multiplier", field_value: 1.06 },
    { field_key: "subdued_energy_multiplier", field_value: 0.78 },
    { field_key: "joyful_diffusion_multiplier", field_value: 1.14 },
  ];
  const priorityMigrated = migrateParticleExpressionRelativeMappingGraph(
    staleCopies,
    seed
  );
  assert.equal(priorityMigrated.migrated, true);
  const priorityFields = priorityMigrated.value.nodes[0].data.params.fields;
  const priorityValue = (fieldKey) =>
    priorityFields.find((field) => field.field_key === fieldKey)?.field_value;
  assert.equal(priorityValue("calm_brightness_multiplier"), 0.96);
  assert.equal(priorityValue("caring_brightness_multiplier"), 1.06);
  assert.equal(priorityValue("subdued_energy_multiplier"), 0.78);
  assert.equal(priorityValue("joyful_diffusion_multiplier"), 1.14);
  const priorityReopened = migrateParticleExpressionRelativeMappingGraph(
    priorityMigrated.value,
    seed
  );
  assert.equal(priorityReopened.migrated, false);
  assert.equal(priorityReopened.value, priorityMigrated.value);

  const bridgeSource = readFileSync(
    new URL("../src/store/module-state-bridge.ts", import.meta.url),
    "utf8"
  );
  assert.match(
    bridgeSource,
    /PARTICLE_AVATAR_GRAPH_ID = ["']layer_10::particle_avatar["']/
  );
  assert.match(
    bridgeSource,
    /function migrateParticleExpressionRelativeMappingSeed[\s\S]*?migrateParticleExpressionRelativeMappingGraph/s
  );
  assert.match(
    bridgeSource,
    /const expressionMigrated = migrateExpressionStateSemanticsSeed[\s\S]*?const particleMigrated = migrateParticleExpressionRelativeMappingSeed/s
  );
  assert.match(
    bridgeSource,
    /CATALOG_GRAPH_REPLACE_MODULE_IDS[\s\S]*?["']particle_avatar["']/s
  );
  assert.match(
    bridgeSource,
    /moduleNodeId === PARTICLE_AVATAR_GRAPH_ID[\s\S]*?saveModuleGraphState\(moduleNodeId, mergedGraph\.nodes, mergedGraph\.edges\)/s
  );
});

test("Stage 7.4.12 A2 hydrates one Layer 8 output chain with a revision-gated idempotent merge", () => {
  const bridgeSource = readFileSync(
    new URL("../src/store/module-state-bridge.ts", import.meta.url),
    "utf8"
  );

  assert.match(
    bridgeSource,
    /LAYER8_MATERIALIZED_OUTPUT_MODULE_IDS = new Set\(\[[\s\S]*?"language_habit"[\s\S]*?"decision_pattern"[\s\S]*?"interaction_strategy"[\s\S]*?"behavior_habit"[\s\S]*?"emotion_mapper"/s
  );
  assert.match(
    bridgeSource,
    /function mergeLayer8MaterializedOutputSeed\([\s\S]*?nodeType === "module_output" \|\| nodeType === "reference_output"/s
  );
  assert.match(
    bridgeSource,
    /catalogNodeIdFromGraphNode\(node\) === seedCatalogNodeId \|\|[\s\S]*?graphNodeTypeFromGraphNode\(node\) === seedNodeType/s
  );
  assert.match(
    bridgeSource,
    /params\.content_revision ===[\s\S]*?STAGE7_4_12_A2_SOURCE_OUTPUT_IDENTITY_CLEANUP_REVISION[\s\S]*?continue;/s
  );
  assert.match(
    bridgeSource,
    /existingPairs = new Set\([\s\S]*?existingPairs\.has\(pair\)[\s\S]*?existingPairs\.add\(pair\)/s
  );
  assert.match(
    bridgeSource,
    /const layer8OutputMerged = mergeLayer8MaterializedOutputSeed\([\s\S]*?layer8OutputMerged \?\? graphAfterParticleMigration/s
  );
});

test("Stage 7.4.12 A2 materializes Layer 8 output from current checkbox values", () => {
  const seed = {
    module_id: "language_habit",
    preset_id: "seed_preset",
    selected_options: ["seed_option"],
    custom_text: "seed custom text",
    field_references: [],
    validation_rules: ["seed_validation"],
    source_nodes: [],
  };
  const references = [
    {
      reference_id: "language_current_reference",
      module_id: "dialogue_runtime_profile",
    },
  ];
  const sourceNodes = [
    "language_behavior_input_basis",
    "language_behavior_core_rules",
    "language_behavior_validation",
  ];

  const materialized = materializeLayer8BehaviorPolicy(
    seed,
    [
      {
        nodeId: "language_behavior_core_rules",
        checkboxConfig: {
          preset_id: "current_preset",
          selected_options: ["current_core"],
          custom_text: "current custom text",
        },
      },
      {
        nodeId: "language_behavior_validation",
        checkboxConfig: {
          preset_id: "current_preset",
          selected_options: ["current_validation"],
          custom_text: "",
        },
      },
    ],
    references,
    sourceNodes
  );

  assert.equal(materialized.module_id, "language_habit");
  assert.equal(materialized.preset_id, "current_preset");
  assert.deepEqual(materialized.selected_options, [
    "current_core",
    "current_validation",
  ]);
  assert.equal(materialized.custom_text, "current custom text");
  assert.deepEqual(materialized.validation_rules, ["current_validation"]);
  assert.deepEqual(materialized.field_references, references);
  assert.deepEqual(materialized.source_nodes, sourceNodes);
  assert.deepEqual(seed.selected_options, ["seed_option"]);
  assert.equal(seed.custom_text, "seed custom text");
});

test("Stage 7.4.11 emotional expression catalog strings and enum labels are localized", () => {
  const cardSource = readFileSync(new URL("../src/components/canvas/WorkflowNodeCard.tsx", import.meta.url), "utf8");
  const en = JSON.parse(readFileSync(new URL("../locales/en.json", import.meta.url), "utf8"));
  const zh = JSON.parse(readFileSync(new URL("../locales/zh.json", import.meta.url), "utf8"));
  const prefix = "layer8.emotionalExpression";

  assert.match(cardSource, /moduleId === ["']emotion_reaction["']/);
  assert.match(cardSource, /moduleId === ["']emotion_reaction["'] \? ["']layer8\.emotionalExpression["']/);
  assert.match(cardSource, /showReferenceInputGenericFields[\s\S]*?<GenericTextInputRenderer[\s\S]*?<ReferenceInputRenderer/);
  assert.match(cardSource, /field\.i18n_keys\?\.help/);
  assert.match(cardSource, /field\.i18n_keys\?\.default/);
  assert.match(cardSource, /field\.i18n_keys\?\.validation_error/);

  for (const suffix of [
    "module.title",
    "module.description",
    "module.type",
    "node.contextInput.title",
    "node.allowedStateRecognition.title",
    "node.stateSelectionRules.title",
    "node.personalityConsistencyValidation.title",
    "node.relationshipSafetyValidation.title",
    "node.intensityCalculation.title",
    "node.normalizeFallback.title",
    "node.output.title",
    "node.referenceOutput.title",
    "field.expressionState.label",
    "field.expressionState.help",
    "field.expressionState.default",
    "field.expressionState.validation.invalid",
    "field.expressionIntensity.label",
    "field.expressionIntensity.help",
    "field.expressionIntensity.default",
    "field.expressionIntensity.validation.invalid",
  ]) {
    const key = `${prefix}.${suffix}`;
    assert.equal(typeof zh[key], "string", `missing Chinese localization: ${key}`);
    assert.equal(typeof en[key], "string", `missing English localization: ${key}`);
    assert.ok(zh[key].length > 0, `blank Chinese localization: ${key}`);
    assert.ok(en[key].length > 0, `blank English localization: ${key}`);
  }

  const expectedChineseLabels = {
    neutral: "中性",
    calm: "平静",
    caring: "关怀",
    subdued: "低落",
    joyful: "愉悦",
  };
  for (const [value, label] of Object.entries(expectedChineseLabels)) {
    const key = `${prefix}.enum.expressionState.${value}`;
    assert.equal(zh[key], label);
    assert.equal(typeof en[key], "string");
    assert.notEqual(zh[key], value);
  }
});

test("compile-time reference normalization preserves stable declaration ids", () => {
  const source = readFileSync(new URL("../src/components/CanvasShell.tsx", import.meta.url), "utf8");
  const bridgeSource = readFileSync(new URL("../src/store/module-state-bridge.ts", import.meta.url), "utf8");

  assert.match(
    source,
    /REFERENCE_INPUT_POINTER_KEYS\s*=\s*new Set\(\[\s*["']reference_id["']/s
  );
  assert.match(source, /const referenceId = referenceInputString\(item\.reference_id\)/);
  assert.match(source, /\.\.\.\(referenceId \? \{ reference_id: referenceId \} : \{\}\)/);
  assert.match(
    source,
    /module\.module_id === ["']dialogue_runtime_profile["'][\s\S]*mergeCatalogReferenceDeclarations\([\s\S]*seedParams\.references/
  );
  assert.match(
    bridgeSource,
    /DIALOGUE_RUNTIME_PROFILE_GRAPH_ID = ["']layer_8::dialogue_runtime_profile["'][\s\S]*mergeDialogueRuntimeProfileReferenceSeed/
  );
});

test("Stage 7.4.9 dialogue runtime profile catalog strings and structured ids are localized", () => {
  const cardSource = readFileSync(new URL("../src/components/canvas/WorkflowNodeCard.tsx", import.meta.url), "utf8");
  const catalogSource = readFileSync(new URL("../../api/app/registry/module_catalog.py", import.meta.url), "utf8");
  const profile = JSON.parse(
    readFileSync(
      new URL("../../api/app/registry/dialogue_runtime_profile.json", import.meta.url),
      "utf8"
    )
  );
  const en = JSON.parse(readFileSync(new URL("../locales/en.json", import.meta.url), "utf8"));
  const zh = JSON.parse(readFileSync(new URL("../locales/zh.json", import.meta.url), "utf8"));

  assert.match(cardSource, /moduleId === ["']dialogue_runtime_profile["']/);
  assert.match(cardSource, /return ["']stage7_4_9\.dialogueRuntime["']/);
  assert.match(cardSource, /A-Za-z0-9_:-/);
  assert.match(catalogSource, /DIALOGUE_RUNTIME_PROFILE_MODULE_ID = ["']dialogue_runtime_profile["']/);

  const fieldSuffixes = [
    "profileId",
    "residentType",
    "templateId",
    "responseStyle",
    "scenarioOverrides",
    "fewShotExamples",
    "selfDisclosureStyle",
    "prohibitedLanguageOverrides",
    "fallbackBehavior",
    "memoryPolicyReference",
    "relationshipPolicyReference",
    "sourceTrace",
    "emotionalDialogue",
  ];
  const expectedCatalogKeys = [
    "module.title",
    "module.description",
    "module.output",
    "module.type",
    ...[
      "configInput",
      "referenceInput",
      "templateBinding",
      "residentOverride",
      "scenarioConfig",
      "fewShotConfig",
      "authorityValidation",
      "output",
      "referenceOutput",
    ].flatMap((node) => [`node.${node}.title`, `node.${node}.description`]),
    ...["text_input", "reference_input", "text_config", "validation", "module_output", "reference_output"].map(
      (nodeType) => `nodeType.${nodeType}`
    ),
    ...fieldSuffixes.flatMap((field) => [
      `field.${field}.label`,
      `field.${field}.description`,
      `field.${field}.placeholder`,
    ]),
    ...["personalityTraits", "emotionPattern", "highRiskSafety", "memoryPolicy", "relationshipPolicy", "professionalLimits"].flatMap((reference) => [
      `reference.${reference}.label`,
      `reference.${reference}.description`,
      `reference.${reference}.usage`,
    ]),
    "referenceOutput.exportName",
    "referenceOutput.exportDescription",
    ...fieldSuffixes.flatMap((field) => [
      `referenceOutput.field.${field}`,
      `referenceOutput.field.${field}.description`,
    ]),
  ].map((suffix) => `stage7_4_9.dialogueRuntime.${suffix}`);

  const sceneIds = [
    "ordinary_greeting",
    "daily_small_talk",
    "work_or_study_wrap_up",
    "feeling_tired",
    "quiet_company",
    "small_joy",
    "mild_frustration",
    "resident_preference_or_life_tone",
    "conversation_ending",
    "language_switch_or_mixed_input",
  ];
  const exampleIds = sceneIds.flatMap((sceneId) =>
    [1, 2, 3].map((index) => `${sceneId}_${String(index).padStart(2, "0")}`)
  );
  const structuredKeys = [
    "resident_type",
    "template_id",
    "scene_id",
    "example_id",
    "usage",
    "recommended_length",
    "source_scope",
    "source_layer",
    "override_source",
    "merge_stage",
    "merge_order",
    "validation_rules",
    "validation_status",
    "source_id",
    "system_instruction_override",
  ];
  const sourceRuleRefs = new Set();
  const collectSourceRuleRefs = (value) => {
    if (Array.isArray(value)) {
      value.forEach(collectSourceRuleRefs);
      return;
    }
    if (!value || typeof value !== "object") return;
    for (const [key, item] of Object.entries(value)) {
      if (key === "source_rule_refs" && Array.isArray(item)) {
        item.forEach((reference) => sourceRuleRefs.add(reference));
      } else {
        collectSourceRuleRefs(item);
      }
    }
  };
  collectSourceRuleRefs(profile);
  const structuredValues = [
    DIALOGUE_RUNTIME_PROFILE_ID,
    "humanistic_companion",
    "humanistic_companion_v0_1",
    "behavior_guidance_only",
    "public_rules",
    "type_template",
    "resident_profile",
    "layer_2_personality_emotion_authority",
    "layer_3_high_risk_safety_authority",
    "layer_5_memory_authority",
    "layer_11_relationship_authority",
    "layer_12_professional_limits_authority",
    "runtime_projection",
    "public_rules_remain_authoritative",
    "type_template_precedes_resident_profile",
    "resident_profile_cannot_override_layer_5_memory_authority",
    "resident_profile_cannot_override_layer_11_relationship_authority",
    "runtime_projection_is_derived",
    "no_behavior_policy_write",
    "no_authority_override",
    ...sceneIds,
    ...exampleIds,
    ...sourceRuleRefs,
  ];

  for (const messages of [en, zh]) {
    for (const key of expectedCatalogKeys) {
      assert.equal(typeof messages[key], "string", `missing locale key ${key}`);
      assert.ok(messages[key].trim(), `empty locale key ${key}`);
    }
    for (const rawKey of structuredKeys) {
      const key = `stage7_4_9.dialogueRuntime.key.${rawKey}`;
      assert.equal(typeof messages[key], "string", `missing structured key ${key}`);
      assert.notEqual(messages[key], rawKey);
    }
    for (const rawValue of structuredValues) {
      const key = `stage7_4_9.dialogueRuntime.value.${rawValue}`;
      assert.equal(typeof messages[key], "string", `missing structured value ${key}`);
      assert.notEqual(messages[key], rawValue);
    }
  }
});
