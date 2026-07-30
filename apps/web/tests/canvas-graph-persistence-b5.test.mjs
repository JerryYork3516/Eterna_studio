import assert from "node:assert/strict";
import test from "node:test";

import {
  fingerprintModuleGraph,
  importCanvasState,
  loadModuleGraphState,
  saveModuleGraphState,
  saveModuleGraphStateAtomically,
  serializeCanvasState,
} from "../src/lib/canvas-persistence.ts";

function installLocalStorage() {
  const values = new Map();
  let failWrites = false;
  let writeAttempts = 0;
  const previousWindow = globalThis.window;
  globalThis.window = {
    localStorage: {
      get length() {
        return values.size;
      },
      getItem: (key) => values.get(key) ?? null,
      key: (index) => [...values.keys()][index] ?? null,
      removeItem: (key) => values.delete(key),
      setItem: (key, value) => {
        writeAttempts += 1;
        if (failWrites) {
          throw new Error("simulated persistence failure");
        }
        values.set(key, String(value));
      },
    },
  };
  return {
    values,
    get writeAttempts() {
      return writeAttempts;
    },
    failWrites(value) {
      failWrites = value;
    },
    restore() {
      if (previousWindow === undefined) {
        delete globalThis.window;
      } else {
        globalThis.window = previousWindow;
      }
    },
  };
}

test("B5 module graph persistence round-trips Studio-only metadata without upgrading Canvas v4", () => {
  const metadata = {
    visualAssetBinding: {
      asset_id: "asset_1",
      asset_revision: 3,
      blueprint_digest: "fnv1a64-canonical-json-v1:abc",
    },
  };
  const state = serializeCanvasState({
    moduleGraphs: {
      "layer_10::particle_avatar": {
        moduleId: "layer_10::particle_avatar",
        nodes: [{ id: "particle_visual_config_input" }],
        edges: [],
        viewport: { x: 1, y: 2, zoom: 0.8 },
        studioMetadata: metadata,
      },
    },
  });

  assert.equal(state.version, "v4");
  const imported = importCanvasState(JSON.stringify(state));
  assert.equal(imported.success, true);
  assert.deepEqual(
    imported.state?.moduleGraphs["layer_10::particle_avatar"].studioMetadata,
    metadata
  );
});

test("B5 legacy three-argument graph saves preserve metadata and failed writes preserve old storage", () => {
  const storage = installLocalStorage();
  try {
    const moduleId = "layer_10::particle_avatar";
    const metadata = {
      visualAssetBinding: {
        asset_id: "asset_1",
        asset_revision: 3,
      },
    };
    const writesBeforeAtomicSave = storage.writeAttempts;
    assert.equal(
      saveModuleGraphStateAtomically(moduleId, [{ id: "before" }], [], {
        viewport: { x: 4, y: 5, zoom: 1.2 },
        studioMetadata: metadata,
      }),
      true
    );
    assert.equal(storage.writeAttempts, writesBeforeAtomicSave + 1);

    assert.equal(saveModuleGraphState(moduleId, [{ id: "after" }], []), true);
    assert.deepEqual(loadModuleGraphState(moduleId), {
      moduleId,
      nodes: [{ id: "after" }],
      edges: [],
      viewport: { x: 4, y: 5, zoom: 1.2 },
      studioMetadata: metadata,
    });

    const persistedBeforeFailure = storage.values.get(`module_graph_${moduleId}`);
    storage.failWrites(true);
    const previousConsoleError = console.error;
    console.error = () => {};
    try {
      assert.equal(
        saveModuleGraphStateAtomically(moduleId, [{ id: "must-not-persist" }], [], {
          studioMetadata: {},
        }),
        false
      );
    } finally {
      console.error = previousConsoleError;
    }
    assert.equal(storage.values.get(`module_graph_${moduleId}`), persistedBeforeFailure);
    assert.deepEqual(loadModuleGraphState(moduleId)?.studioMetadata, metadata);
  } finally {
    storage.restore();
  }
});

test("B5 module graph fingerprint is canonical and covers metadata", () => {
  const left = {
    moduleId: "layer_10::particle_avatar",
    nodes: [{ id: "node", data: { b: 2, a: 1 } }],
    edges: [],
    studioMetadata: {
      visualAssetBinding: { asset_revision: 1, asset_id: "asset_1" },
    },
  };
  const sameWithDifferentKeyOrder = {
    studioMetadata: {
      visualAssetBinding: { asset_id: "asset_1", asset_revision: 1 },
    },
    edges: [],
    nodes: [{ data: { a: 1, b: 2 }, id: "node" }],
    moduleId: "layer_10::particle_avatar",
  };
  const changed = {
    ...left,
    studioMetadata: {
      visualAssetBinding: { asset_revision: 2, asset_id: "asset_1" },
    },
  };

  assert.equal(
    fingerprintModuleGraph(left),
    fingerprintModuleGraph(sameWithDifferentKeyOrder)
  );
  assert.notEqual(fingerprintModuleGraph(left), fingerprintModuleGraph(changed));
});
