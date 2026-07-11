import assert from "node:assert/strict";
import test from "node:test";

import {
  preserveStoredModuleEdges,
  preserveStoredModuleNodePosition,
  filterDanglingModuleGraphEdges,
} from "../src/store/module-graph-merge.ts";

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
