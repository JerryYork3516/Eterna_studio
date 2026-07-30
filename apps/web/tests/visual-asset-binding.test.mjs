import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

import {
  getDefaultAbstractBustBlueprint,
} from "../../../packages/shared-schema/src/abstract-bust-blueprint.ts";
import {
  generateAbstractBust,
} from "../src/features/visual-builder/builders/abstract-particle-bust/index.ts";
import {
  ABSTRACT_PARTICLE_BUST_BUILDER_ID,
} from "../src/features/visual-builder/builder-registry.ts";
import {
  createVisualAsset,
  updateVisualAssetBlueprint,
} from "../src/features/visual-builder/visual-asset.ts";
import {
  VISUAL_ASSET_BINDING_DIGEST_PREFIX,
  VisualAssetBindingError,
  canonicalJsonStringify,
  deriveVisualAssetBindingStatus,
  digestAbstractBustBlueprint,
  locateParticleAvatarTarget,
  locateResidentScope,
  locateVisualAssetBindingContext,
  prepareVisualAssetBind,
  prepareVisualAssetSync,
  prepareVisualAssetUnbind,
} from "../src/features/visual-builder/visual-asset-binding.ts";

const IDENTITY_INSTANCE_ID = "layer_1::module_basic_identity";
const PARTICLE_INSTANCE_ID = "layer_10::particle_avatar";
const CREATED_AT = "2026-07-30T10:00:00.000Z";
const BOUND_AT = "2026-07-30T10:05:00.000Z";
const SYNCED_AT = "2026-07-30T10:10:00.000Z";

function clone(value) {
  return JSON.parse(JSON.stringify(value));
}

function field(fieldKey, fieldValue, extra = {}) {
  return {
    field_key: fieldKey,
    field_value: clone(fieldValue),
    ...extra,
  };
}

function createSnapshot() {
  const blueprint = getDefaultAbstractBustBlueprint();
  const particleFields = [
    field("abstract_bust_blueprint", blueprint, { field_type: "object" }),
    field("resident_default_base_color", "#7aa2f7", {
      field_type: "text",
    }),
  ];
  return {
    layerModules: {
      layer_1: ["module_basic_identity"],
      layer_10: ["particle_avatar"],
    },
    moduleInstanceRegistry: {
      [IDENTITY_INSTANCE_ID]: {
        instanceId: IDENTITY_INSTANCE_ID,
        moduleId: "module_basic_identity",
        layerId: "layer_1",
      },
      [PARTICLE_INSTANCE_ID]: {
        instanceId: PARTICLE_INSTANCE_ID,
        moduleId: "particle_avatar",
        layerId: "layer_10",
      },
    },
    moduleGraphs: {
      [IDENTITY_INSTANCE_ID]: {
        moduleNodeId: IDENTITY_INSTANCE_ID,
        nodes: [
          {
            node_id: `${IDENTITY_INSTANCE_ID}::basic_identity_field_input`,
            type: "field_input",
            position: { x: 10, y: 20 },
            data: {
              catalog_node_id: "basic_identity_field_input",
              params: {
                fields: [
                  field("name", "Test Resident"),
                  field("resident_id", "resident-binding-test"),
                ],
              },
            },
          },
        ],
        edges: [],
      },
      [PARTICLE_INSTANCE_ID]: {
        moduleNodeId: PARTICLE_INSTANCE_ID,
        nodes: [
          {
            id: `${PARTICLE_INSTANCE_ID}::wrapper`,
            type: "workflowNode",
            position: { x: 100, y: 200 },
            data: {
              schemaNode: {
                node_id:
                  `${PARTICLE_INSTANCE_ID}::particle_visual_config_input`,
                type: "reference_input",
                position: { x: 100, y: 200 },
                data: {
                  catalog_node_id: "particle_visual_config_input",
                  params: {
                    fields: clone(particleFields),
                    legacy_fields: clone(particleFields),
                    legacy_data_fields: clone(particleFields),
                    keep_parameter: { untouched: true },
                  },
                  fields: clone(particleFields),
                  ui_name: "Particle Visual Config",
                },
              },
            },
          },
          {
            node_id: `${PARTICLE_INSTANCE_ID}::particle_mapping_config_output`,
            type: "module_output",
            position: { x: 640, y: 200 },
            data: {
              catalog_node_id: "particle_mapping_config_output",
              params: { keep_output: true },
            },
          },
        ],
        edges: [
          {
            id: "particle-config-to-output",
            source:
              `${PARTICLE_INSTANCE_ID}::particle_visual_config_input`,
            target:
              `${PARTICLE_INSTANCE_ID}::particle_mapping_config_output`,
          },
        ],
        viewport: { x: 4, y: 5, zoom: 0.85 },
        studioMetadata: {
          unrelatedStudioMetadata: { keep: true },
        },
      },
    },
  };
}

function createAsset(assetId = "visual-asset-a", name = "Portrait A") {
  return createVisualAsset(ABSTRACT_PARTICLE_BUST_BUILDER_ID, {
    name,
    assetIdFactory: () => assetId,
    now: () => CREATED_AT,
  });
}

function updateAsset(asset, mutate, timestamp = SYNCED_AT) {
  const blueprint = clone(asset.blueprint);
  mutate(blueprint);
  return updateVisualAssetBlueprint(asset, blueprint, timestamp);
}

function expectBindingError(callback, code) {
  assert.throws(
    callback,
    (error) =>
      error instanceof VisualAssetBindingError && error.code === code
  );
}

function particleData(graph) {
  return graph.nodes[0].data.schemaNode.data;
}

function particleBlueprint(graph) {
  return particleData(graph).params.fields.find(
    (candidate) => candidate.field_key === "abstract_bust_blueprint"
  ).field_value;
}

function withParticleGraph(snapshot, graph) {
  return {
    ...snapshot,
    moduleGraphs: {
      ...snapshot.moduleGraphs,
      [PARTICLE_INSTANCE_ID]: graph,
    },
  };
}

function reverseObjectKeys(value) {
  if (Array.isArray(value)) {
    return value.map(reverseObjectKeys);
  }
  if (!value || typeof value !== "object") {
    return value;
  }
  return Object.fromEntries(
    Object.entries(value)
      .reverse()
      .map(([key, child]) => [key, reverseObjectKeys(child)])
  );
}

test("strictly locates the unique Layer 1 resident and Layer 10 particle target", () => {
  const snapshot = createSnapshot();
  const resident = locateResidentScope(snapshot);
  const particle = locateParticleAvatarTarget(snapshot);
  const context = locateVisualAssetBindingContext(snapshot);

  assert.equal(resident.residentScopeId, "resident-binding-test");
  assert.equal(resident.identityInstanceId, IDENTITY_INSTANCE_ID);
  assert.equal(particle.moduleInstanceId, PARTICLE_INSTANCE_ID);
  assert.deepEqual(particle.blueprint, getDefaultAbstractBustBlueprint());
  assert.equal(context.residentScopeId, resident.residentScopeId);
  assert.equal(context.moduleInstanceId, particle.moduleInstanceId);
  assert.equal(context.binding, undefined);
});

test("rejects missing, duplicate, and wrong-layer resident identity targets", () => {
  const missing = createSnapshot();
  missing.layerModules.layer_1 = [];
  expectBindingError(
    () => locateResidentScope(missing),
    "identity_attachment_missing"
  );

  const duplicate = createSnapshot();
  duplicate.layerModules.layer_1.push("module_basic_identity");
  expectBindingError(
    () => locateResidentScope(duplicate),
    "identity_attachment_duplicate"
  );

  const wrongLayer = createSnapshot();
  wrongLayer.layerModules = {
    ...wrongLayer.layerModules,
    layer_1: [],
    layer_2: ["module_basic_identity"],
  };
  wrongLayer.moduleInstanceRegistry = {
    ...wrongLayer.moduleInstanceRegistry,
    [IDENTITY_INSTANCE_ID]: {
      ...wrongLayer.moduleInstanceRegistry[IDENTITY_INSTANCE_ID],
      layerId: "layer_2",
    },
  };
  expectBindingError(
    () => locateResidentScope(wrongLayer),
    "identity_attachment_missing"
  );

  const duplicateRegistry = createSnapshot();
  duplicateRegistry.moduleInstanceRegistry["identity-copy"] = {
    instanceId: "identity-copy",
    moduleId: "module_basic_identity",
    layerId: "layer_1",
  };
  expectBindingError(
    () => locateResidentScope(duplicateRegistry),
    "identity_registry_duplicate"
  );
});

test("rejects missing, duplicate, and invalid resident_id fields", () => {
  const missing = createSnapshot();
  const fields =
    missing.moduleGraphs[IDENTITY_INSTANCE_ID].nodes[0].data.params.fields;
  missing.moduleGraphs[IDENTITY_INSTANCE_ID].nodes[0].data.params.fields =
    fields.filter((candidate) => candidate.field_key !== "resident_id");
  expectBindingError(
    () => locateResidentScope(missing),
    "resident_id_field_missing"
  );

  const duplicate = createSnapshot();
  duplicate.moduleGraphs[
    IDENTITY_INSTANCE_ID
  ].nodes[0].data.params.fields.push(
    field("resident_id", "resident-duplicate")
  );
  expectBindingError(
    () => locateResidentScope(duplicate),
    "resident_id_field_duplicate"
  );

  const blank = createSnapshot();
  blank.moduleGraphs[
    IDENTITY_INSTANCE_ID
  ].nodes[0].data.params.fields.find(
    (candidate) => candidate.field_key === "resident_id"
  ).field_value = "  ";
  expectBindingError(() => locateResidentScope(blank), "resident_id_invalid");
});

test("rejects missing, duplicate, and wrong-layer particle instances", () => {
  const missing = createSnapshot();
  missing.layerModules.layer_10 = [];
  expectBindingError(
    () => locateParticleAvatarTarget(missing),
    "particle_attachment_missing"
  );

  const duplicate = createSnapshot();
  duplicate.layerModules.layer_10.push("particle_avatar");
  expectBindingError(
    () => locateParticleAvatarTarget(duplicate),
    "particle_attachment_duplicate"
  );

  const wrongLayer = createSnapshot();
  wrongLayer.layerModules = {
    ...wrongLayer.layerModules,
    layer_10: [],
    layer_9: ["particle_avatar"],
  };
  wrongLayer.moduleInstanceRegistry = {
    ...wrongLayer.moduleInstanceRegistry,
    [PARTICLE_INSTANCE_ID]: {
      ...wrongLayer.moduleInstanceRegistry[PARTICLE_INSTANCE_ID],
      layerId: "layer_9",
    },
  };
  expectBindingError(
    () => locateParticleAvatarTarget(wrongLayer),
    "particle_attachment_missing"
  );

  const duplicateRegistry = createSnapshot();
  duplicateRegistry.moduleInstanceRegistry["particle-copy"] = {
    instanceId: "particle-copy",
    moduleId: "particle_avatar",
    layerId: "layer_10",
  };
  expectBindingError(
    () => locateParticleAvatarTarget(duplicateRegistry),
    "particle_registry_duplicate"
  );
});

test("strictly requires one particle input and one nested Blueprint field", () => {
  const missingInput = createSnapshot();
  particleData(
    missingInput.moduleGraphs[PARTICLE_INSTANCE_ID]
  ).catalog_node_id = "renamed_particle_input";
  expectBindingError(
    () => locateParticleAvatarTarget(missingInput),
    "particle_input_missing"
  );

  const duplicateInput = createSnapshot();
  duplicateInput.moduleGraphs[PARTICLE_INSTANCE_ID].nodes.push(
    clone(duplicateInput.moduleGraphs[PARTICLE_INSTANCE_ID].nodes[0])
  );
  expectBindingError(
    () => locateParticleAvatarTarget(duplicateInput),
    "particle_input_duplicate"
  );

  const missingField = createSnapshot();
  const missingFieldData = particleData(
    missingField.moduleGraphs[PARTICLE_INSTANCE_ID]
  );
  missingFieldData.params.fields =
    missingFieldData.params.fields.filter(
      (candidate) =>
        candidate.field_key !== "abstract_bust_blueprint"
    );
  expectBindingError(
    () => locateParticleAvatarTarget(missingField),
    "blueprint_field_missing"
  );

  const duplicateField = createSnapshot();
  const duplicateFieldData = particleData(
    duplicateField.moduleGraphs[PARTICLE_INSTANCE_ID]
  );
  duplicateFieldData.params.fields.push(
    field(
      "abstract_bust_blueprint",
      getDefaultAbstractBustBlueprint()
    )
  );
  expectBindingError(
    () => locateParticleAvatarTarget(duplicateField),
    "blueprint_field_duplicate"
  );
});

test("canonical Blueprint digest is recursively key-stable and separate from B3 coordinates", () => {
  const blueprint = getDefaultAbstractBustBlueprint();
  const reversed = reverseObjectKeys(blueprint);
  const digest = digestAbstractBustBlueprint(blueprint);
  const reorderedDigest = digestAbstractBustBlueprint(reversed);
  const positionsDigest = generateAbstractBust(blueprint).digest;

  assert.equal(digest, reorderedDigest);
  assert.ok(digest.startsWith(VISUAL_ASSET_BINDING_DIGEST_PREFIX));
  assert.match(digest, /^fnv1a64-canonical-json-v1:[0-9a-f]{16}$/);
  assert.match(positionsDigest, /^[0-9a-f]{16}$/);
  assert.notEqual(digest, positionsDigest);
  assert.equal(
    canonicalJsonStringify({ z: { b: 2, a: 1 }, a: 0 }),
    '{"a":0,"z":{"a":1,"b":2}}'
  );
});

test("bind deep-clones the normalized Blueprint and changes no unrelated graph data", () => {
  const snapshot = createSnapshot();
  const originalSnapshot = clone(snapshot);
  const asset = updateAsset(createAsset(), (blueprint) => {
    blueprint.head.width = 0.3;
    blueprint.shoulders.width = 0.68;
  });
  const prepared = prepareVisualAssetBind({
    ...snapshot,
    asset,
    expectedAssetRevision: asset.revision,
    now: BOUND_AT,
  });
  const nextData = particleData(prepared.nextGraph);

  assert.deepEqual(snapshot, originalSnapshot);
  assert.notEqual(prepared.nextGraph, snapshot.moduleGraphs[PARTICLE_INSTANCE_ID]);
  assert.notEqual(particleBlueprint(prepared.nextGraph), asset.blueprint);
  assert.equal(particleBlueprint(prepared.nextGraph).head.width, 0.3);
  assert.equal(particleBlueprint(prepared.nextGraph).shoulders.width, 0.68);
  assert.deepEqual(nextData.params.fields, nextData.params.legacy_fields);
  assert.deepEqual(nextData.params.fields, nextData.params.legacy_data_fields);
  assert.deepEqual(nextData.params.fields, nextData.fields);
  assert.deepEqual(
    prepared.nextGraph.nodes[1],
    snapshot.moduleGraphs[PARTICLE_INSTANCE_ID].nodes[1]
  );
  assert.deepEqual(
    prepared.nextGraph.edges,
    snapshot.moduleGraphs[PARTICLE_INSTANCE_ID].edges
  );
  assert.deepEqual(
    prepared.nextGraph.viewport,
    snapshot.moduleGraphs[PARTICLE_INSTANCE_ID].viewport
  );
  assert.deepEqual(
    prepared.nextGraph.studioMetadata.unrelatedStudioMetadata,
    { keep: true }
  );
  assert.equal(prepared.nextBinding.resident_scope_id, "resident-binding-test");
  assert.equal(prepared.nextBinding.module_instance_id, PARTICLE_INSTANCE_ID);
  assert.equal(prepared.nextBinding.asset_id, asset.asset_id);
  assert.equal(prepared.nextBinding.asset_revision, asset.revision);
  assert.equal(prepared.nextBinding.bound_at, BOUND_AT);
  assert.equal(prepared.nextBinding.updated_at, BOUND_AT);
  assert.equal(
    prepared.nextBinding.blueprint_digest,
    digestAbstractBustBlueprint(asset.blueprint)
  );

  particleBlueprint(prepared.nextGraph).head.width = 0.25;
  assert.equal(asset.blueprint.head.width, 0.3);
  assert.deepEqual(snapshot, originalSnapshot);
});

test("derives unbound, in_sync, out_of_sync, and invalid states", () => {
  const snapshot = createSnapshot();
  const asset = createAsset();
  const unbound = deriveVisualAssetBindingStatus({
    ...snapshot,
    visualAssets: [asset],
  });
  assert.equal(unbound.state, "unbound");
  assert.equal(unbound.layerModified, false);
  assert.equal(unbound.assetMissing, false);

  const prepared = prepareVisualAssetBind({
    ...snapshot,
    asset,
    expectedAssetRevision: asset.revision,
    now: BOUND_AT,
  });
  const boundSnapshot = withParticleGraph(snapshot, prepared.nextGraph);
  const inSync = deriveVisualAssetBindingStatus({
    ...boundSnapshot,
    visualAssets: [asset],
  });
  assert.equal(inSync.state, "in_sync");
  assert.equal(inSync.layerModified, false);
  assert.equal(inSync.assetModified, false);

  const changedAsset = updateAsset(asset, (blueprint) => {
    blueprint.face.mouth.curvature = 0.2;
  });
  const assetOutOfSync = deriveVisualAssetBindingStatus({
    ...boundSnapshot,
    visualAssets: [changedAsset],
  });
  assert.equal(assetOutOfSync.state, "out_of_sync");
  assert.equal(assetOutOfSync.assetModified, true);
  assert.equal(assetOutOfSync.layerModified, false);

  const independentlyEditedGraph = clone(prepared.nextGraph);
  particleBlueprint(independentlyEditedGraph).head.height = 0.35;
  const layerOutOfSync = deriveVisualAssetBindingStatus({
    ...withParticleGraph(snapshot, independentlyEditedGraph),
    visualAssets: [asset],
  });
  assert.equal(layerOutOfSync.state, "out_of_sync");
  assert.equal(layerOutOfSync.layerModified, true);
  assert.equal(layerOutOfSync.assetModified, false);

  const invalid = deriveVisualAssetBindingStatus({
    ...boundSnapshot,
    visualAssets: [],
  });
  assert.equal(invalid.state, "invalid");
  assert.equal(invalid.reason, "binding_asset_missing");
  assert.equal(invalid.assetMissing, true);
});

test("invalid binding metadata keeps exact target context and can be replaced or removed", () => {
  const snapshot = createSnapshot();
  const originalAsset = createAsset("visual-asset-invalid-source");
  const prepared = prepareVisualAssetBind({
    ...snapshot,
    asset: originalAsset,
    expectedAssetRevision: originalAsset.revision,
    now: BOUND_AT,
  });
  const invalidGraph = clone(prepared.nextGraph);
  invalidGraph.studioMetadata.visualAssetBinding.unknown_field =
    "must-be-rejected";
  const invalidSnapshot = withParticleGraph(snapshot, invalidGraph);

  const invalid = deriveVisualAssetBindingStatus({
    ...invalidSnapshot,
    visualAssets: [originalAsset],
  });
  assert.equal(invalid.state, "invalid");
  assert.equal(invalid.reason, "binding_invalid");
  assert.equal(invalid.residentScopeId, "resident-binding-test");
  assert.equal(invalid.moduleInstanceId, PARTICLE_INSTANCE_ID);
  assert.equal(invalid.bindingRecordPresent, true);
  assert.equal(invalid.bindingAssetId, originalAsset.asset_id);
  assert.equal(invalid.binding, undefined);

  const replacementAsset = createAsset("visual-asset-replacement");
  const replaced = prepareVisualAssetBind({
    ...invalidSnapshot,
    asset: replacementAsset,
    expectedAssetRevision: replacementAsset.revision,
    now: SYNCED_AT,
  });
  assert.equal(replaced.nextBinding.asset_id, replacementAsset.asset_id);
  assert.equal(
    replaced.nextGraph.studioMetadata.visualAssetBinding.asset_id,
    replacementAsset.asset_id
  );

  const unbound = prepareVisualAssetUnbind(invalidSnapshot);
  assert.equal(
    Object.prototype.hasOwnProperty.call(
      unbound.nextGraph.studioMetadata,
      "visualAssetBinding"
    ),
    false
  );
  assert.deepEqual(
    unbound.nextGraph.studioMetadata.unrelatedStudioMetadata,
    { keep: true }
  );
  assert.deepEqual(
    particleBlueprint(unbound.nextGraph),
    particleBlueprint(invalidGraph)
  );
});

test("binding state follows the recorded asset rather than a different selected asset", () => {
  const snapshot = createSnapshot();
  const assetA = createAsset("visual-asset-a", "Portrait A");
  const assetB = createAsset("visual-asset-b", "Portrait B");
  const prepared = prepareVisualAssetBind({
    ...snapshot,
    asset: assetA,
    expectedAssetRevision: assetA.revision,
    now: BOUND_AT,
  });
  const status = deriveVisualAssetBindingStatus({
    ...withParticleGraph(snapshot, prepared.nextGraph),
    visualAssets: [assetB, assetA],
  });

  assert.equal(status.state, "in_sync");
  assert.equal(status.binding.asset_id, assetA.asset_id);
  assert.equal(status.asset.asset_id, assetA.asset_id);
});

test("sync rejects stale revisions and assets that do not match the binding", () => {
  const snapshot = createSnapshot();
  const assetV1 = createAsset();
  const assetV2 = updateAsset(assetV1, (blueprint) => {
    blueprint.neck.width = 0.15;
  });
  const bound = prepareVisualAssetBind({
    ...snapshot,
    asset: assetV2,
    expectedAssetRevision: 2,
    now: BOUND_AT,
  });
  const boundSnapshot = withParticleGraph(snapshot, bound.nextGraph);

  expectBindingError(
    () =>
      prepareVisualAssetSync({
        ...boundSnapshot,
        asset: assetV1,
        expectedAssetRevision: 1,
        now: SYNCED_AT,
      }),
    "asset_revision_stale"
  );
  expectBindingError(
    () =>
      prepareVisualAssetSync({
        ...boundSnapshot,
        asset: assetV2,
        expectedAssetRevision: 1,
        now: SYNCED_AT,
      }),
    "asset_revision_stale"
  );
  expectBindingError(
    () =>
      prepareVisualAssetSync({
        ...boundSnapshot,
        asset: createAsset("visual-asset-b", "Portrait B"),
        expectedAssetRevision: 1,
        now: SYNCED_AT,
      }),
    "asset_mismatch"
  );
});

test("rebind, sync, and unbind preserve the intended binding lifecycle", () => {
  const snapshot = createSnapshot();
  const assetA = createAsset("visual-asset-a", "Portrait A");
  const assetB = updateAsset(
    createAsset("visual-asset-b", "Portrait B"),
    (blueprint) => {
      blueprint.presentation = "feminine";
      blueprint.hair.style = "long";
      blueprint.hair.length = 0.3;
    }
  );
  const boundA = prepareVisualAssetBind({
    ...snapshot,
    asset: assetA,
    expectedAssetRevision: 1,
    now: BOUND_AT,
  });
  const reboundAt = "2026-07-30T10:07:00.000Z";
  const reboundB = prepareVisualAssetBind({
    ...withParticleGraph(snapshot, boundA.nextGraph),
    asset: assetB,
    expectedAssetRevision: 2,
    now: reboundAt,
  });

  assert.equal(reboundB.previousBinding.asset_id, assetA.asset_id);
  assert.equal(reboundB.nextBinding.asset_id, assetB.asset_id);
  assert.equal(reboundB.nextBinding.bound_at, reboundAt);
  assert.equal(particleBlueprint(reboundB.nextGraph).hair.style, "long");

  const assetB3 = updateAsset(assetB, (blueprint) => {
    blueprint.hair.style = "tied";
  });
  const syncedB = prepareVisualAssetSync({
    ...withParticleGraph(snapshot, reboundB.nextGraph),
    asset: assetB3,
    expectedAssetRevision: 3,
    now: SYNCED_AT,
  });
  assert.equal(syncedB.nextBinding.bound_at, reboundAt);
  assert.equal(syncedB.nextBinding.updated_at, SYNCED_AT);
  assert.equal(syncedB.nextBinding.asset_revision, 3);
  assert.equal(particleBlueprint(syncedB.nextGraph).hair.style, "tied");

  const unbound = prepareVisualAssetUnbind(
    withParticleGraph(snapshot, syncedB.nextGraph)
  );
  assert.equal(unbound.previousBinding.asset_id, assetB.asset_id);
  assert.equal(unbound.nextBinding, undefined);
  assert.equal(
    Object.hasOwn(
      unbound.nextGraph.studioMetadata,
      "visualAssetBinding"
    ),
    false
  );
  assert.deepEqual(
    unbound.nextGraph.studioMetadata.unrelatedStudioMetadata,
    { keep: true }
  );
  assert.equal(particleBlueprint(unbound.nextGraph).hair.style, "tied");
  assert.deepEqual(
    particleBlueprint(unbound.nextGraph),
    particleBlueprint(syncedB.nextGraph)
  );
});

test("binding persistence contains only Blueprint source metadata and no preview state", () => {
  const snapshot = createSnapshot();
  const asset = createAsset();
  const prepared = prepareVisualAssetBind({
    ...snapshot,
    asset,
    expectedAssetRevision: asset.revision,
    now: BOUND_AT,
  });
  const serialized = JSON.stringify(prepared.nextGraph);

  assert.match(serialized, /"abstract_bust_blueprint"/);
  assert.match(serialized, /"visualAssetBinding"/);
  assert.doesNotMatch(
    serialized,
    /"positions"|"regions"|"anchors"|"camera"|"previewColor"|"WebGL"|"Three"/
  );
});

test("B5 UI uses explicit transactions, one-time navigation intents, and a read-only resident snapshot", () => {
  const workspace = readFileSync(
    new URL(
      "../src/components/visual-builder/VisualBuilderWorkspace.tsx",
      import.meta.url
    ),
    "utf8"
  );
  const shell = readFileSync(
    new URL("../src/components/StudioWorkspaceShell.tsx", import.meta.url),
    "utf8"
  );
  const canvas = readFileSync(
    new URL("../src/components/CanvasShell.tsx", import.meta.url),
    "utf8"
  );
  const card = readFileSync(
    new URL(
      "../src/components/canvas/WorkflowNodeCard.tsx",
      import.meta.url
    ),
    "utf8"
  );

  assert.match(workspace, /prepareVisualAssetBind/);
  assert.match(workspace, /prepareVisualAssetSync/);
  assert.match(workspace, /prepareVisualAssetUnbind/);
  assert.match(workspace, /commitExternalModuleGraphTransaction/);
  assert.match(workspace, /draftController\.isDirty/);
  assert.match(workspace, /persistenceDirty/);
  assert.match(workspace, /requestConfirmation/);
  assert.match(workspace, /VisualBuilderCanvasDialog/);
  assert.match(shell, /navigationRequestId\.current \+= 1/);
  assert.match(shell, /focusModuleIntent=\{residentFocusIntent\}/);
  assert.match(shell, /selectAssetIntent=\{visualSelectIntent\}/);
  assert.match(canvas, /externalModuleGraphRevisions/);
  assert.match(canvas, /handledExternalGraphRevisionRef/);
  assert.match(canvas, /VisualAssetBindingSummary/);
  assert.match(
    canvas,
    /moduleInstanceRegistry\[activeModuleTabId\]\?\.moduleId ===[\s\S]*?"particle_avatar"/s
  );
  assert.doesNotMatch(
    canvas,
    /activeModuleTabId === ["']layer_10::particle_avatar["']/
  );
  assert.match(canvas, /studioMetadata:\s*cloneCanvasValue/);
  assert.match(card, /data-readonly-field="abstract_bust_blueprint"/);
  assert.match(card, /residentBuilder\.binding\.readOnly/);
  assert.doesNotMatch(
    workspace,
    /generateAbstractBust|Float32Array|WebGLRenderer|OrbitControls/
  );
});

test("B5 hydration restores exact identity and particle graph keys before binding status becomes ready", () => {
  const bridge = readFileSync(
    new URL("../src/store/module-state-bridge.ts", import.meta.url),
    "utf8"
  );
  const hydrationStart = bridge.indexOf("function hydrateVisualBindingGraphs");
  const hydration = bridge.slice(
    hydrationStart,
    bridge.indexOf("function persistedOrHydratedGraph", hydrationStart)
  );
  const initializeStart = bridge.indexOf("export function initializeModuleState");
  const initialize = bridge.slice(
    initializeStart,
    bridge.indexOf("export function ensureModuleGraphExists", initializeStart)
  );

  assert.match(hydration, /instance\.instanceId/);
  assert.match(hydration, /loadModuleGraphState\(instance\.instanceId\)/);
  assert.match(hydration, /module_basic_identity/);
  assert.match(hydration, /particle_avatar/);
  assert.ok(
    initialize.indexOf("hydrateVisualBindingGraphs") <
      initialize.indexOf("markModuleStateHydrated")
  );
});

test("B5 Canvas transaction is single-key, particle-targeted, and updates memory only after persistence", () => {
  const store = readFileSync(
    new URL("../src/store/canvas-store.ts", import.meta.url),
    "utf8"
  );
  const persistence = readFileSync(
    new URL("../src/lib/canvas-persistence.ts", import.meta.url),
    "utf8"
  );
  const transactionStart = store.lastIndexOf(
    "commitExternalModuleGraphTransaction: ("
  );
  const transaction = store.slice(
    transactionStart,
    store.indexOf("removeModuleGraph:", transactionStart)
  );

  assert.match(transaction, /moduleId !== "particle_avatar"/);
  assert.match(transaction, /layerId !== "layer_10"/);
  assert.match(
    transaction,
    /expectedAssetRevision !== input\.currentAssetRevision/
  );
  assert.match(transaction, /fingerprintModuleGraph\(currentGraph\)/);
  assert.match(transaction, /saveModuleGraphStateAtomically/);
  assert.ok(
    transaction.indexOf("saveModuleGraphStateAtomically") <
      transaction.indexOf("set((currentState)")
  );
  assert.match(
    persistence,
    /saveModuleGraphStateAtomically[\s\S]*?window\.localStorage\.setItem/s
  );
  assert.doesNotMatch(
    transaction,
    /useVisualBuilderStore|selectedVisualAssetId/
  );
});

test("B5 binding and resident summary copy exists in Chinese and English", () => {
  const zh = JSON.parse(
    readFileSync(new URL("../locales/zh.json", import.meta.url), "utf8")
  );
  const en = JSON.parse(
    readFileSync(new URL("../locales/en.json", import.meta.url), "utf8")
  );
  for (const key of [
    "visualBuilder.binding.title",
    "visualBuilder.binding.status.unbound",
    "visualBuilder.binding.status.in_sync",
    "visualBuilder.binding.status.out_of_sync",
    "visualBuilder.binding.status.invalid",
    "visualBuilder.binding.action.bind",
    "visualBuilder.binding.action.sync",
    "visualBuilder.binding.action.unbind",
    "visualBuilder.binding.action.goResident",
    "visualBuilder.binding.confirm.overwriteLayer",
    "residentBuilder.binding.title",
    "residentBuilder.binding.readOnly",
    "residentBuilder.binding.action.goVisual",
  ]) {
    assert.ok(zh[key], `missing zh ${key}`);
    assert.ok(en[key], `missing en ${key}`);
  }
});

test("B5 confirmations use an in-canvas dialog instead of blocking browser dialogs", () => {
  const workspace = readFileSync(
    new URL(
      "../src/components/visual-builder/VisualBuilderWorkspace.tsx",
      import.meta.url
    ),
    "utf8"
  );
  const dialog = readFileSync(
    new URL(
      "../src/components/visual-builder/VisualBuilderCanvasDialog.tsx",
      import.meta.url
    ),
    "utf8"
  );

  assert.doesNotMatch(workspace, /window\.(confirm|alert)\(/);
  assert.match(workspace, /<VisualBuilderCanvasDialog/);
  assert.match(dialog, /role="dialog"/);
  assert.match(dialog, /aria-modal="true"/);
  assert.match(dialog, /data-visual-builder-dialog/);
});
