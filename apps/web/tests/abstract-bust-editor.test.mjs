import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

import {
  ABSTRACT_BUST_EDITOR_FIELDS,
  getAbstractBustPresetBlueprint,
  getDefaultAbstractBustBlueprint,
  normalizeAbstractBustBlueprint,
} from "../../../packages/shared-schema/src/abstract-bust-blueprint.ts";
import { generateAbstractBust } from "../src/features/visual-builder/builders/abstract-particle-bust/index.ts";
import {
  deriveAbstractBustCameraPose,
} from "../src/features/visual-builder/builders/abstract-particle-bust/preview/camera-presets.ts";
import {
  createAbstractBustWebGLRenderer,
  createAbstractBustPreviewGeometry,
  disposeAbstractBustPreviewResources,
  handleAbstractBustContextLost,
  handleAbstractBustContextRestored,
  updateAbstractBustPreviewGeometry,
} from "../src/features/visual-builder/builders/abstract-particle-bust/preview/three-scene.ts";
import {
  abstractBustBlueprintsEqual,
  editorStep,
  getAbstractBustFieldValue,
  updateAbstractBustDraftField,
} from "../src/features/visual-builder/builders/abstract-particle-bust/editor/editor-state.ts";
import {
  createAbstractParticleBustVisualAsset,
  updateVisualAssetBlueprint,
} from "../src/features/visual-builder/visual-asset.ts";
import {
  saveVisualBuilderSnapshot,
} from "../src/features/visual-builder/visual-builder-persistence.ts";

const root = new URL("..", import.meta.url);
const fixtureUrl = (name) =>
  new URL(
    `../../../packages/shared-schema/contracts/abstract_bust_v0_1/fixtures/${name}.json`,
    import.meta.url
  );
const readFixture = (name) =>
  JSON.parse(readFileSync(fixtureUrl(name), "utf8"));
const schemaDocument = JSON.parse(
  readFileSync(
    new URL(
      "../../../packages/shared-schema/contracts/abstract_bust_v0_1/abstract_bust_blueprint_v0_1.schema.json",
      import.meta.url
    ),
    "utf8"
  )
);

function collectSchemaEditorFields(schemaNode, path = []) {
  const resolved = schemaNode.$ref
    ? schemaDocument.$defs[schemaNode.$ref.replace("#/$defs/", "")]
    : schemaNode;
  if (resolved.type === "object") {
    return Object.entries(resolved.properties ?? {}).flatMap(
      ([name, child]) =>
        path.length === 0 && name === "generator_version"
          ? []
          : collectSchemaEditorFields(child, [...path, name])
    );
  }
  return [[path.join("."), resolved]];
}

function clone(value) {
  return JSON.parse(JSON.stringify(value));
}

function createMemoryStorage() {
  const data = new Map();
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

function createAsset() {
  return createAbstractParticleBustVisualAsset({
    name: "B4 portrait",
    assetIdFactory: () => "visual_asset_b4",
    now: () => "2026-07-30T14:00:00.000Z",
  });
}

test("B1 exposes exactly 39 schema-derived editor fields", () => {
  const schemaFields = new Map(collectSchemaEditorFields(schemaDocument));
  assert.equal(ABSTRACT_BUST_EDITOR_FIELDS.length, 39);
  assert.equal(schemaFields.size, 39);
  assert.equal(
    new Set(ABSTRACT_BUST_EDITOR_FIELDS.map((field) => field.path)).size,
    39
  );
  assert.equal(
    ABSTRACT_BUST_EDITOR_FIELDS.some(
      (field) => field.path === "generator_version"
    ),
    false
  );
  for (const field of ABSTRACT_BUST_EDITOR_FIELDS) {
    const schemaField = schemaFields.get(field.path);
    assert.ok(field.path);
    assert.ok(schemaField, field.path);
    assert.equal(field.defaultValue, schemaField.default, field.path);
    if (field.valueType === "enum") {
      assert.deepEqual(field.enumValues, schemaField.enum, field.path);
      assert.ok(field.enumValues.includes(field.defaultValue), field.path);
    } else {
      assert.equal(field.valueType, schemaField.type, field.path);
      assert.equal(field.minimum, schemaField.minimum, field.path);
      assert.equal(field.maximum, schemaField.maximum, field.path);
      assert.equal(typeof field.defaultValue, "number", field.path);
      assert.ok(field.minimum <= field.defaultValue, field.path);
      assert.ok(field.defaultValue <= field.maximum, field.path);
      assert.ok(editorStep(field) > 0, field.path);
    }
  }
});

test("neutral, feminine, and masculine presets are direct normalized B1 fixtures", () => {
  for (const presentation of ["neutral", "feminine", "masculine"]) {
    const preset = getAbstractBustPresetBlueprint(presentation);
    assert.deepEqual(preset, normalizeAbstractBustBlueprint(readFixture(presentation)));
    preset.head.width += 0.001;
    assert.deepEqual(
      getAbstractBustPresetBlueprint(presentation),
      normalizeAbstractBustBlueprint(readFixture(presentation))
    );
  }
});

test("draft field updates stay nested, clamp through B1, and keep invalid values out", () => {
  const original = getDefaultAbstractBustBlueprint();
  const widened = updateAbstractBustDraftField(
    original,
    "shoulders.width",
    100
  );
  assert.equal(widened.shoulders.width, 0.68);
  assert.equal(original.shoulders.width, 0.6);
  assert.equal(getAbstractBustFieldValue(widened, "shoulders.width"), 0.68);
  assert.throws(
    () => updateAbstractBustDraftField(original, "head.width", Number.NaN),
    /finite/
  );
  assert.throws(
    () => updateAbstractBustDraftField(original, "face.eyes.size", "invalid"),
    /number/
  );
  assert.equal(abstractBustBlueprintsEqual(original, widened), false);
});

test("presentation preset, age tendency, and all five hairstyles change preview digest", () => {
  assert.equal(
    new Set(
      ["neutral", "feminine", "masculine"].map(
        (value) => generateAbstractBust(getAbstractBustPresetBlueprint(value)).digest
      )
    ).size,
    3
  );
  assert.equal(
    new Set(
      ["youthful", "balanced", "mature"].map((value) =>
        generateAbstractBust(
          updateAbstractBustDraftField(
            getDefaultAbstractBustBlueprint(),
            "age_tendency",
            value
          )
        ).digest
      )
    ).size,
    3
  );
  assert.equal(
    new Set(
      ["none", "short", "medium", "long", "tied"].map((value) =>
        generateAbstractBust(
          updateAbstractBustDraftField(
            getDefaultAbstractBustBlueprint(),
            "hair.style",
            value
          )
        ).digest
      )
    ).size,
    5
  );
});

test("Blueprint save normalizes only the Blueprint and increments metadata", () => {
  const asset = createAsset();
  const draft = clone(asset.blueprint);
  draft.head.width = 100;
  const saved = updateVisualAssetBlueprint(
    asset,
    draft,
    "2026-07-30T14:01:00.000Z"
  );
  assert.equal(saved.head, undefined);
  assert.equal(saved.blueprint.head.width, 0.32);
  assert.equal(saved.revision, 2);
  assert.equal(saved.updated_at, "2026-07-30T14:01:00.000Z");
  assert.equal(saved.asset_id, asset.asset_id);
  for (const forbidden of [
    "positions",
    "regions",
    "anchors",
    "camera",
    "previewColor",
  ]) {
    assert.equal(forbidden in saved, false);
  }
});

test("saved snapshot contains Blueprint but no generated or camera data", () => {
  const storage = createMemoryStorage();
  const asset = createAsset();
  assert.equal(
    saveVisualBuilderSnapshot(
      {
        visualAssets: [asset],
        selectedVisualAssetId: asset.asset_id,
        activeBuilderId: "abstract_particle_bust",
      },
      storage
    ),
    true
  );
  const serialized = Object.values(storage.dump()).join("\n");
  assert.match(serialized, /"blueprint"/);
  assert.doesNotMatch(
    serialized,
    /"positions"|"regions"|"anchors"|"camera"|"previewColor"/
  );
});

test("Three.js geometry keeps one 12,000-point position attribute across updates", () => {
  const geometry = createAbstractBustPreviewGeometry();
  const firstResult = generateAbstractBust(getDefaultAbstractBustBlueprint());
  const firstAttribute = updateAbstractBustPreviewGeometry(
    geometry,
    firstResult.positions
  );
  assert.equal(firstAttribute.count, 12_000);
  assert.equal(firstAttribute.array.length, 36_000);
  assert.ok(geometry.boundingBox);
  assert.ok(geometry.boundingSphere);

  const secondResult = generateAbstractBust(
    updateAbstractBustDraftField(
      getDefaultAbstractBustBlueprint(),
      "seed",
      2_818_040_095
    )
  );
  const secondAttribute = updateAbstractBustPreviewGeometry(
    geometry,
    secondResult.positions
  );
  assert.equal(secondAttribute, firstAttribute);
  assert.notEqual(secondResult.digest, firstResult.digest);
  geometry.dispose();
});

test("front and side camera presets fit the same bounds from orthogonal directions", () => {
  const result = generateAbstractBust(getDefaultAbstractBustBlueprint());
  const front = deriveAbstractBustCameraPose(result.bounds, "front", 34, 16 / 9);
  const side = deriveAbstractBustCameraPose(result.bounds, "side", 34, 16 / 9);
  assert.deepEqual(front.target, side.target);
  assert.equal(front.position[0], front.target[0]);
  assert.equal(front.position[1], front.target[1]);
  assert.ok(front.position[2] > front.target[2]);
  assert.ok(side.position[0] > side.target[0]);
  assert.equal(side.position[1], side.target[1]);
  assert.equal(side.position[2], side.target[2]);
  assert.ok(front.near > 0);
  assert.ok(front.far > front.near);
});

test("WebGL creation and context lifecycle expose one deterministic failure path", () => {
  assert.throws(
    () =>
      createAbstractBustWebGLRenderer(() => {
        throw new Error("webgl unavailable");
      }),
    /webgl unavailable/
  );

  const events = [];
  handleAbstractBustContextLost(
    { preventDefault: () => events.push("prevented") },
    (error) => events.push(error)
  );
  handleAbstractBustContextRestored(
    () => events.push("reset"),
    (error) => events.push(error)
  );
  assert.deepEqual(events, [
    "prevented",
    "webgl_context_lost",
    "reset",
    null,
  ]);
});

test("preview lifecycle disposes controls, geometry, material, renderer, then context", () => {
  const disposed = [];
  disposeAbstractBustPreviewResources({
    controls: { dispose: () => disposed.push("controls") },
    geometry: { dispose: () => disposed.push("geometry") },
    material: { dispose: () => disposed.push("material") },
    renderer: {
      dispose: () => disposed.push("renderer"),
      forceContextLoss: () => disposed.push("context"),
    },
  });
  assert.deepEqual(disposed, [
    "controls",
    "geometry",
    "material",
    "renderer",
    "context",
  ]);
});

test("B4 source uses direct Three.js, reuses resources, and cleans every lifecycle handle", () => {
  const sceneSource = readFileSync(
    new URL(
      "src/features/visual-builder/builders/abstract-particle-bust/preview/three-scene.ts",
      root
    ),
    "utf8"
  );
  const viewportSource = readFileSync(
    new URL(
      "src/features/visual-builder/builders/abstract-particle-bust/preview/AbstractBustThreeViewport.tsx",
      root
    ),
    "utf8"
  );
  const editorSources = [
    "src/components/visual-builder/VisualBuilderWorkspace.tsx",
    "src/features/visual-builder/builders/abstract-particle-bust/editor/AbstractBustEditor.tsx",
    "src/features/visual-builder/builders/abstract-particle-bust/editor/AbstractBustInspector.tsx",
    "src/store/visual-builder-store.ts",
  ].map((path) => readFileSync(new URL(path, root), "utf8")).join("\n");

  assert.match(sceneSource, /from "three"/);
  assert.match(sceneSource, /three\/addons\/controls\/OrbitControls\.js/);
  assert.equal((sceneSource.match(/new THREE\.WebGLRenderer/g) ?? []).length, 1);
  assert.match(sceneSource, /target\.set\(positions\)/);
  assert.match(sceneSource, /controls\.dispose\(\)/);
  assert.match(sceneSource, /geometry\.dispose\(\)/);
  assert.match(sceneSource, /material\.dispose\(\)/);
  assert.match(sceneSource, /renderer\.dispose\(\)/);
  assert.match(sceneSource, /forceContextLoss\(\)/);
  assert.match(viewportSource, /ResizeObserver/);
  assert.match(viewportSource, /requestAnimationFrame/);
  assert.match(editorSources, /updateVisualAssetBlueprint/);
  assert.doesNotMatch(`${sceneSource}\n${viewportSource}\n${editorSources}`, /@react-three/);
  assert.doesNotMatch(
    editorSources,
    /particle_avatar|payload\.abstract_bust_blueprint|DRCompiler|moduleGraphs/
  );
});

test("every schema field and B4 action has Chinese and English copy", () => {
  const zh = JSON.parse(readFileSync(new URL("locales/zh.json", root), "utf8"));
  const en = JSON.parse(readFileSync(new URL("locales/en.json", root), "utf8"));
  for (const field of ABSTRACT_BUST_EDITOR_FIELDS) {
    const key = `visualBuilder.field.${field.path}`;
    assert.ok(zh[key], key);
    assert.ok(en[key], key);
  }
  for (const key of [
    "visualBuilder.action.save",
    "visualBuilder.action.cancel",
    "visualBuilder.action.restoreDefault",
    "visualBuilder.camera.front",
    "visualBuilder.camera.side",
    "visualBuilder.camera.free",
    "visualBuilder.camera.auto",
    "visualBuilder.camera.reset",
    "visualBuilder.confirm.discardDraft",
  ]) {
    assert.ok(zh[key], key);
    assert.ok(en[key], key);
  }
});
