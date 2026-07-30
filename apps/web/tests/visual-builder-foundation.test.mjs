import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

import { getDefaultAbstractBustBlueprint } from "../../../packages/shared-schema/src/abstract-bust-blueprint.ts";
import {
  ABSTRACT_PARTICLE_BUST_BUILDER_ID,
  VISUAL_BUILDER_DEFINITIONS,
  getVisualBuilderDefinition,
  requireVisualBuilderDefinition,
} from "../src/features/visual-builder/builder-registry.ts";
import {
  createVisualAsset,
  normalizeVisualAsset,
  updateVisualAssetMetadata,
} from "../src/features/visual-builder/visual-asset.ts";
import {
  VISUAL_BUILDER_STATE_VERSION,
  VISUAL_BUILDER_STORAGE_KEY,
  createEmptyVisualBuilderSnapshot,
  loadVisualBuilderSnapshot,
  normalizeVisualBuilderSnapshot,
  saveVisualBuilderSnapshot,
} from "../src/features/visual-builder/visual-builder-persistence.ts";

const root = new URL("..", import.meta.url);
const fixedTimestamp = "2026-07-30T12:00:00.000Z";

function clone(value) {
  return JSON.parse(JSON.stringify(value));
}

function createAsset(overrides = {}) {
  const asset = createVisualAsset(ABSTRACT_PARTICLE_BUST_BUILDER_ID, {
    name: "Portrait A",
    assetIdFactory: () => "visual_asset_test-001",
    now: () => fixedTimestamp,
  });
  return { ...asset, ...overrides };
}

function createMemoryStorage(initial = {}) {
  const data = new Map(Object.entries(initial));
  return {
    getItem(key) {
      return data.get(key) ?? null;
    },
    setItem(key, value) {
      data.set(key, value);
    },
    removeItem(key) {
      data.delete(key);
    },
    dump() {
      return Object.fromEntries(data);
    },
  };
}

test("Builder Registry registers only the available abstract particle bust", () => {
  assert.equal(VISUAL_BUILDER_DEFINITIONS.length, 1);
  assert.deepEqual(VISUAL_BUILDER_DEFINITIONS[0], {
    id: "abstract_particle_bust",
    displayNameKey: "visualBuilder.builder.abstractParticleBust",
    appearanceType: "abstract_particle_bust",
    generatorVersion: "abstract_bust_v0_1",
    status: "available",
  });
  assert.equal(
    getVisualBuilderDefinition("abstract_particle_bust")?.generatorVersion,
    "abstract_bust_v0_1"
  );
  assert.equal(getVisualBuilderDefinition("realistic_portrait"), null);
  assert.throws(
    () => requireVisualBuilderDefinition("unknown_builder"),
    /Unknown or unavailable visual builder/
  );
});

test("new Visual Asset uses the B1 default Blueprint and a resident-independent ID", () => {
  const asset = createAsset();
  assert.equal(asset.asset_id, "visual_asset_test-001");
  assert.equal(asset.builder_id, "abstract_particle_bust");
  assert.equal(asset.appearance_type, "abstract_particle_bust");
  assert.equal(asset.generator_version, "abstract_bust_v0_1");
  assert.equal(asset.created_at, fixedTimestamp);
  assert.equal(asset.updated_at, fixedTimestamp);
  assert.equal(asset.revision, 1);
  assert.deepEqual(asset.blueprint, getDefaultAbstractBustBlueprint());
  assert.equal("resident_id" in asset, false);
  assert.equal("module_id" in asset, false);
});

test("Visual Asset normalization is strict and excludes runtime or geometry state", () => {
  const asset = createAsset();
  for (const [fieldName, fieldValue] of [
    ["particle_coordinates", [[0, 0, 0]]],
    ["gpu_buffer", "buffer"],
    ["camera_state", { zoom: 1 }],
    ["morph_targets", []],
    ["runtime_state", { active: true }],
  ]) {
    assert.throws(
      () => normalizeVisualAsset({ ...asset, [fieldName]: fieldValue }),
      new RegExp(`Unknown VisualAsset field: ${fieldName}`)
    );
  }

  assert.throws(
    () =>
      normalizeVisualAsset({
        ...asset,
        builder_id: "unknown_builder",
      }),
    /Unknown or unavailable visual builder/
  );
  assert.throws(
    () =>
      normalizeVisualAsset({
        ...asset,
        generator_version: "abstract_bust_v9",
      }),
    /generator_version does not match/
  );
});

test("Visual Asset metadata updates revision without changing the B1 Blueprint", () => {
  const asset = createAsset();
  const renamed = updateVisualAssetMetadata(
    asset,
    { name: "Portrait B" },
    "2026-07-30T12:01:00.000Z"
  );
  assert.equal(renamed.name, "Portrait B");
  assert.equal(renamed.revision, 2);
  assert.equal(renamed.updated_at, "2026-07-30T12:01:00.000Z");
  assert.deepEqual(renamed.blueprint, asset.blueprint);
  assert.equal(renamed.created_at, asset.created_at);
});

test("Visual Builder persistence round-trips selection and nested Blueprint", () => {
  const storage = createMemoryStorage();
  const asset = createAsset();
  assert.equal(
    saveVisualBuilderSnapshot(
      {
        visualAssets: [asset],
        selectedVisualAssetId: asset.asset_id,
        activeBuilderId: ABSTRACT_PARTICLE_BUST_BUILDER_ID,
      },
      storage
    ),
    true
  );

  const restored = loadVisualBuilderSnapshot(storage);
  assert.equal(restored.version, VISUAL_BUILDER_STATE_VERSION);
  assert.equal(restored.selectedVisualAssetId, asset.asset_id);
  assert.equal(restored.activeBuilderId, ABSTRACT_PARTICLE_BUST_BUILDER_ID);
  assert.deepEqual(restored.visualAssets, [asset]);
  assert.deepEqual(
    restored.visualAssets[0].blueprint.face.eyes,
    getDefaultAbstractBustBlueprint().face.eyes
  );
  assert.ok(storage.dump()[VISUAL_BUILDER_STORAGE_KEY]);
  assert.notEqual(VISUAL_BUILDER_STORAGE_KEY, "eterna_canvas_v4");
});

test("old or missing project state initializes safely without Visual Assets", () => {
  const missing = loadVisualBuilderSnapshot(createMemoryStorage());
  assert.deepEqual(missing, createEmptyVisualBuilderSnapshot());

  const oldCanvasState = normalizeVisualBuilderSnapshot({
    version: "v4",
    moduleGraphs: {},
    layerModules: {},
  });
  assert.deepEqual(oldCanvasState, createEmptyVisualBuilderSnapshot());

  const omittedAssets = normalizeVisualBuilderSnapshot({
    version: VISUAL_BUILDER_STATE_VERSION,
    selectedVisualAssetId: "missing",
    activeBuilderId: ABSTRACT_PARTICLE_BUST_BUILDER_ID,
  });
  assert.deepEqual(omittedAssets.visualAssets, []);
  assert.equal(omittedAssets.selectedVisualAssetId, null);
});

test("persistence drops unknown builders and repairs invalid selection", () => {
  const validAsset = createAsset();
  const unknownBuilderAsset = {
    ...clone(validAsset),
    asset_id: "visual_asset_unknown",
    builder_id: "realistic_portrait",
    appearance_type: "realistic_portrait",
  };
  const restored = normalizeVisualBuilderSnapshot({
    version: VISUAL_BUILDER_STATE_VERSION,
    visualAssets: [unknownBuilderAsset, validAsset],
    selectedVisualAssetId: unknownBuilderAsset.asset_id,
    activeBuilderId: "realistic_portrait",
  });

  assert.deepEqual(restored.visualAssets, [validAsset]);
  assert.equal(restored.selectedVisualAssetId, null);
  assert.equal(restored.activeBuilderId, ABSTRACT_PARTICLE_BUST_BUILDER_ID);
});

test("top-level workspace switch keeps both builders mounted and stores isolated", () => {
  const workspaceShell = readFileSync(
    new URL("src/components/StudioWorkspaceShell.tsx", root),
    "utf8"
  );
  const page = readFileSync(new URL("app/page.tsx", root), "utf8");
  const visualStore = readFileSync(
    new URL("src/store/visual-builder-store.ts", root),
    "utf8"
  );
  const canvasStore = readFileSync(
    new URL("src/store/canvas-store.ts", root),
    "utf8"
  );

  assert.match(page, /<StudioWorkspaceShell \/>/);
  assert.match(workspaceShell, /setActiveWorkspace\("resident_builder"\)/);
  assert.match(workspaceShell, /setActiveWorkspace\("visual_builder"\)/);
  assert.match(
    workspaceShell,
    /hidden=\{activeWorkspace !== "resident_builder"\}[\s\S]*?<CanvasShell \/>/
  );
  assert.match(
    workspaceShell,
    /hidden=\{activeWorkspace !== "visual_builder"\}[\s\S]*?<VisualBuilderWorkspace \/>/
  );
  assert.match(
    workspaceShell,
    /document\.body\.dataset\.studioWorkspace = activeWorkspace/
  );
  assert.doesNotMatch(visualStore, /moduleGraphs|selectedNodeId/);
  assert.doesNotMatch(canvasStore, /VisualAsset|selectedVisualAssetId|activeBuilderId/);
});

test("B2 UI stays outside React Flow, Layer 10, DR projection, and preview generation", () => {
  const visualWorkspace = readFileSync(
    new URL(
      "src/components/visual-builder/VisualBuilderWorkspace.tsx",
      root
    ),
    "utf8"
  );
  const visualFeatureSources = [
    "src/features/visual-builder/builder-registry.ts",
    "src/features/visual-builder/visual-asset.ts",
    "src/features/visual-builder/visual-builder-persistence.ts",
    "src/store/visual-builder-store.ts",
  ]
    .map((path) => readFileSync(new URL(path, root), "utf8"))
    .join("\n");

  assert.match(visualWorkspace, /function VisualBuilderHeader/);
  assert.match(visualWorkspace, /function VisualAssetSidebar/);
  assert.match(visualWorkspace, /function VisualBuilderViewport/);
  assert.match(visualWorkspace, /function VisualBuilderInspector/);
  assert.match(visualWorkspace, /function VisualBuilderStatusBar/);
  assert.doesNotMatch(visualWorkspace, /@xyflow\/react|@react-three|WebGLRenderer/);
  assert.doesNotMatch(
    `${visualWorkspace}\n${visualFeatureSources}`,
    /particle_avatar|payload\.abstract_bust_blueprint|moduleGraphs|DRCompiler/
  );
});

test("Visual Builder navigation and workspace copy is complete in Chinese and English", () => {
  const zh = JSON.parse(
    readFileSync(new URL("locales/zh.json", root), "utf8")
  );
  const en = JSON.parse(
    readFileSync(new URL("locales/en.json", root), "utf8")
  );
  const keys = Object.keys(zh).filter(
    (key) => key.startsWith("workspace.") || key.startsWith("visualBuilder.")
  );

  assert.ok(keys.length >= 35);
  for (const key of keys) {
    assert.equal(typeof zh[key], "string", `missing zh key ${key}`);
    assert.ok(zh[key].trim(), `empty zh key ${key}`);
    assert.equal(typeof en[key], "string", `missing en key ${key}`);
    assert.ok(en[key].trim(), `empty en key ${key}`);
  }
  assert.equal(zh["workspace.residentBuilder"], "数字居民构建");
  assert.equal(zh["workspace.visualBuilder"], "视觉构建");
  assert.equal(en["workspace.residentBuilder"], "Resident Builder");
  assert.equal(en["workspace.visualBuilder"], "Visual Builder");
});
