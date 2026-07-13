import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

import {
  mergeChecklistTemplateDefaults,
  normalizeCatalogNodeId,
  preserveStoredModuleEdges,
  preserveStoredModuleNodePosition,
  filterDanglingModuleGraphEdges,
  mergeAvailableModuleReferencePointers,
} from "../src/store/module-graph-merge.ts";
import {
  attachedModuleIdsFromLayerModules,
  importCanvasState,
  recoverCanvasStateFromDigitalResident,
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
