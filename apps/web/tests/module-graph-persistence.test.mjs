import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

import {
  firstInteractionEnabledValue,
  LINXUAN_RESIDENT_ID,
  mergeCatalogReferenceDeclarations,
  mergeChecklistTemplateDefaults,
  mergeCatalogFieldsPreservingValues,
  migrateLinxuanFirstInteractionEnabledValue,
  migrateLinxuanFirstGreetingValue,
  normalizeCatalogNodeId,
  preserveStoredModuleEdges,
  preserveStoredModuleNodePosition,
  filterDanglingModuleGraphEdges,
  mergeAvailableModuleReferencePointers,
  STAGE7_4_8_FIRST_INTERACTION_ENABLED_MIGRATION,
  STAGE7_4_8_FIRST_GREETING_CONTENT_MIGRATION,
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
  assert.equal(mergedFields.length, 12);
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
  ];
  const savedReferences = seedReferences.map(({ reference_id: _referenceId, ...reference }) => ({
    ...reference,
    saved_editor_note: "keep",
  }));
  const mergedReferences = mergeCatalogReferenceDeclarations(savedReferences, seedReferences);
  assert.equal(mergedReferences.changed, true);
  assert.deepEqual(
    mergedReferences.references.map((reference) => reference.reference_id),
    ["dialogue_runtime_memory_policy", "dialogue_runtime_relationship_policy"]
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
      new URL("../../api/app/registry/dialogue_runtime_profile_linxuan.json", import.meta.url),
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
    ...["memoryPolicy", "relationshipPolicy"].flatMap((reference) => [
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
    "linxuan_daily_companion_v0_1",
    "humanistic_companion",
    "humanistic_companion_v0_1",
    "behavior_guidance_only",
    "public_rules",
    "type_template",
    "resident_profile",
    "layer_5_memory_authority",
    "layer_11_relationship_authority",
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
