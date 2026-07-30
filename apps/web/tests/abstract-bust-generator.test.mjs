import assert from "node:assert/strict";
import { readFileSync, readdirSync } from "node:fs";
import { performance } from "node:perf_hooks";
import test from "node:test";

import {
  getDefaultAbstractBustBlueprint,
  normalizeAbstractBustBlueprint,
} from "../../../packages/shared-schema/src/abstract-bust-blueprint.ts";
import {
  ABSTRACT_BUST_PARTICLE_COUNT,
  ABSTRACT_BUST_REGION,
  AbstractBustGeneratorInputError,
  generateAbstractBust,
} from "../src/features/visual-builder/builders/abstract-particle-bust/index.ts";
import {
  getVisualBuilderGenerator,
  requireVisualBuilderGenerator,
} from "../src/features/visual-builder/builder-registry.ts";

const fixtureUrl = (name) =>
  new URL(
    `../../../packages/shared-schema/contracts/abstract_bust_v0_1/fixtures/${name}`,
    import.meta.url
  );
const readFixture = (name) =>
  JSON.parse(readFileSync(fixtureUrl(name), "utf8"));
const goldenManifest = readFixture("golden_manifest.json");
const generatorRoot = new URL(
  "../src/features/visual-builder/builders/abstract-particle-bust/generator/",
  import.meta.url
);

function clone(value) {
  return JSON.parse(JSON.stringify(value));
}

function generateFixture(name) {
  return generateAbstractBust(normalizeAbstractBustBlueprint(readFixture(name)));
}

function mutateDefault(mutator) {
  const blueprint = clone(getDefaultAbstractBustBlueprint());
  mutator(blueprint);
  return normalizeAbstractBustBlueprint(blueprint);
}

function independentDigest(positions) {
  const scratch = new ArrayBuffer(4);
  const view = new DataView(scratch);
  let digest = 0xcbf2_9ce4_8422_2325n;
  for (const coordinate of positions) {
    view.setFloat32(0, coordinate, true);
    for (let byteOffset = 0; byteOffset < 4; byteOffset += 1) {
      digest ^= BigInt(view.getUint8(byteOffset));
      digest = BigInt.asUintN(64, digest * 0x0000_0100_0000_01b3n);
    }
  }
  return digest.toString(16).padStart(16, "0");
}

function countRegions(regions) {
  const counts = new Map();
  for (const region of regions) {
    counts.set(region, (counts.get(region) ?? 0) + 1);
  }
  return counts;
}

test("default Blueprint produces the fixed finite typed-array output", () => {
  const result = generateAbstractBust(getDefaultAbstractBustBlueprint());
  assert.equal(result.generatorVersion, "abstract_bust_v0_1");
  assert.equal(result.seed, 2_818_040_094);
  assert.equal(result.particleCount, ABSTRACT_BUST_PARTICLE_COUNT);
  assert.equal(result.particleCount, 12_000);
  assert.ok(result.positions instanceof Float32Array);
  assert.ok(result.regions instanceof Uint8Array);
  assert.equal(result.positions.length, 36_000);
  assert.equal(result.regions.length, 12_000);
  assert.ok(result.positions.every(Number.isFinite));
  assert.equal(result.digest, independentDigest(result.positions));
  assert.ok(result.bounds.min.every(Number.isFinite));
  assert.ok(result.bounds.max.every(Number.isFinite));
  for (let axis = 0; axis < 3; axis += 1) {
    assert.ok(result.bounds.min[axis] <= result.bounds.max[axis]);
  }
});

test("all fourteen derived anchors are present and finite", () => {
  const anchors = generateAbstractBust(getDefaultAbstractBustBlueprint()).anchors;
  assert.deepEqual(Object.keys(anchors), [
    "headCenter",
    "headTop",
    "neckBase",
    "shoulderLeft",
    "shoulderRight",
    "chestCenter",
    "torsoCenter",
    "eyeLeft",
    "eyeRight",
    "noseCenter",
    "mouthCenter",
    "cheekLeft",
    "cheekRight",
    "chinCenter",
  ]);
  for (const point of Object.values(anchors)) {
    assert.equal(point.length, 3);
    assert.ok(point.every(Number.isFinite));
  }
});

test("all nine Studio snapshot fixtures match the Aftelle golden manifest", () => {
  assert.equal(goldenManifest.algorithm, "fnv1a64_float32_le_xyz_index_order");
  assert.equal(goldenManifest.particle_count, 12_000);
  assert.equal(goldenManifest.generator_version, "abstract_bust_v0_1");
  assert.equal(Object.keys(goldenManifest.fixtures).length, 9);
  for (const [fixtureName, expectedDigest] of Object.entries(
    goldenManifest.fixtures
  )) {
    const result = generateFixture(fixtureName);
    assert.equal(result.digest, expectedDigest, fixtureName);
    assert.equal(independentDigest(result.positions), expectedDigest, fixtureName);
  }
});

test("same normalized Blueprint keeps positions, regions, anchors, bounds, and digest stable", () => {
  const blueprint = getDefaultAbstractBustBlueprint();
  const first = generateAbstractBust(blueprint);
  const second = generateAbstractBust(blueprint);
  assert.deepEqual(second.positions, first.positions);
  assert.deepEqual(second.regions, first.regions);
  assert.deepEqual(second.anchors, first.anchors);
  assert.deepEqual(second.bounds, first.bounds);
  assert.equal(second.digest, first.digest);
});

test("one hundred sequential generations keep the same digest", (context) => {
  const blueprint = getDefaultAbstractBustBlueprint();
  const expected = generateAbstractBust(blueprint).digest;
  const startedAt = performance.now();
  for (let index = 0; index < 100; index += 1) {
    assert.equal(generateAbstractBust(blueprint).digest, expected);
  }
  const elapsed = performance.now() - startedAt;
  context.diagnostic(
    `100 generations: ${elapsed.toFixed(1)} ms; one output: `
      + `${36_000 * Float32Array.BYTES_PER_ELEMENT + 12_000} bytes of typed arrays`
  );
});

test("seed, presentation, age tendency, and every hair style affect generation", () => {
  const defaultDigest = generateAbstractBust(getDefaultAbstractBustBlueprint()).digest;
  const changedSeed = generateAbstractBust(
    mutateDefault((blueprint) => {
      blueprint.seed += 1;
    })
  ).digest;
  assert.notEqual(changedSeed, defaultDigest);

  // Aftelle treats presentation as preset identity; the frozen generator reads
  // the preset's shape fields rather than branching on the enum itself.
  const presentationDigests = new Set(
    ["neutral.json", "feminine.json", "masculine.json"].map(
      (fixtureName) => generateFixture(fixtureName).digest
    )
  );
  assert.equal(presentationDigests.size, 3);

  const ageDigests = new Set(
    ["youthful", "balanced", "mature"].map(
      (ageTendency) =>
        generateAbstractBust(
          mutateDefault((blueprint) => {
            blueprint.age_tendency = ageTendency;
          })
        ).digest
    )
  );
  assert.equal(ageDigests.size, 3);

  const hairDigests = new Set(
    ["none", "short", "medium", "long", "tied"].map(
      (style) =>
        generateAbstractBust(
          mutateDefault((blueprint) => {
            blueprint.hair.style = style;
          })
        ).digest
    )
  );
  assert.equal(hairDigests.size, 5);
});

test("face groups affect their matching anchors or local geometry", () => {
  const baseline = generateAbstractBust(getDefaultAbstractBustBlueprint());
  const cases = [
    ["eyes", "spacing", 0.21, "eyeLeft"],
    ["nose", "prominence", 0.04, "noseCenter"],
    ["mouth", "vertical_position", -0.28, "mouthCenter"],
    ["cheeks", "prominence", 0.03, "cheekLeft"],
    ["jaw", "length", 0.04, "chinCenter"],
  ];
  for (const [group, field, value, anchor] of cases) {
    const result = generateAbstractBust(
      mutateDefault((blueprint) => {
        blueprint.face[group][field] = value;
      })
    );
    assert.notDeepEqual(result.anchors[anchor], baseline.anchors[anchor], group);
    assert.notEqual(result.digest, baseline.digest, group);
  }
});

test("head, neck, shoulders, torso, softening, and asymmetry participate", () => {
  const baseline = generateAbstractBust(getDefaultAbstractBustBlueprint());
  const cases = [
    ["head.width", (blueprint) => { blueprint.head.width = 0.28; }],
    ["neck.width", (blueprint) => { blueprint.neck.width = 0.17; }],
    ["shoulders.width", (blueprint) => { blueprint.shoulders.width = 0.62; }],
    ["torso.width", (blueprint) => { blueprint.torso.width = 0.56; }],
    ["contour.softening", (blueprint) => { blueprint.contour.softening = 0.8; }],
    ["contour.asymmetry", (blueprint) => { blueprint.contour.asymmetry = 0.015; }],
  ];
  for (const [label, mutator] of cases) {
    const result = generateAbstractBust(mutateDefault(mutator));
    assert.notEqual(result.digest, baseline.digest, label);
  }
});

test("region codes and contiguous index allocation stay frozen", () => {
  assert.deepEqual(ABSTRACT_BUST_REGION, {
    head: 0,
    facialFeatures: 1,
    hair: 2,
    neck: 3,
    shouldersAndChest: 4,
    torso: 5,
  });
  const none = generateAbstractBust(getDefaultAbstractBustBlueprint());
  assert.deepEqual(Object.fromEntries(countRegions(none.regions)), {
    0: 2460,
    1: 180,
    3: 660,
    4: 3240,
    5: 5460,
  });
  assert.equal(none.regions.includes(ABSTRACT_BUST_REGION.hair), false);

  const short = generateFixture("hair_short.json");
  const counts = countRegions(short.regions);
  assert.equal(counts.get(ABSTRACT_BUST_REGION.facialFeatures), 180);
  assert.equal(counts.get(ABSTRACT_BUST_REGION.neck), 660);
  assert.equal(counts.get(ABSTRACT_BUST_REGION.shouldersAndChest), 3240);
  assert.equal(counts.get(ABSTRACT_BUST_REGION.torso), 5460);
  assert.ok((counts.get(ABSTRACT_BUST_REGION.hair) ?? 0) > 0);
  for (let index = 1; index < short.regions.length; index += 1) {
    assert.ok(short.regions[index] >= short.regions[index - 1]);
  }
});

test("generator rejects invalid, incomplete, and non-canonical input", () => {
  const invalidVersion = clone(getDefaultAbstractBustBlueprint());
  invalidVersion.generator_version = "abstract_bust_v9";
  assert.throws(() => generateAbstractBust(invalidVersion), /generator_version/);

  const nonFinite = clone(getDefaultAbstractBustBlueprint());
  nonFinite.head.width = Number.NaN;
  assert.throws(() => generateAbstractBust(nonFinite), /finite/);

  const incomplete = clone(getDefaultAbstractBustBlueprint());
  delete incomplete.face;
  assert.throws(
    () => generateAbstractBust(incomplete),
    AbstractBustGeneratorInputError
  );

  const needsClamp = clone(getDefaultAbstractBustBlueprint());
  needsClamp.shoulders.width = 100;
  assert.throws(
    () => generateAbstractBust(needsClamp),
    AbstractBustGeneratorInputError
  );
});

test("result remains preview-only and contains no rendering or runtime fields", () => {
  const result = generateAbstractBust(getDefaultAbstractBustBlueprint());
  assert.deepEqual(Object.keys(result), [
    "generatorVersion",
    "seed",
    "particleCount",
    "positions",
    "regions",
    "anchors",
    "digest",
    "bounds",
  ]);
  const serializedKeys = Object.keys(result).join(" ");
  assert.doesNotMatch(
    serializedKeys,
    /color|animation|morph|gpu|camera|runtime/i
  );
});

test("Builder Registry exposes the generator only for abstract_particle_bust", () => {
  const registered = getVisualBuilderGenerator("abstract_particle_bust");
  assert.equal(registered, generateAbstractBust);
  assert.equal(getVisualBuilderGenerator("realistic_portrait"), null);
  assert.equal(getVisualBuilderGenerator("unknown_builder"), null);
  assert.equal(requireVisualBuilderGenerator("abstract_particle_bust"), generateAbstractBust);
  assert.throws(
    () => requireVisualBuilderGenerator("unknown_builder"),
    /Unknown visual builder generator/
  );
  assert.equal(
    registered(getDefaultAbstractBustBlueprint()).digest,
    goldenManifest.fixtures["default.json"]
  );
});

test("generator sources contain no non-deterministic APIs", () => {
  const sources = readdirSync(generatorRoot)
    .filter((name) => name.endsWith(".ts"))
    .map((name) => readFileSync(new URL(name, generatorRoot), "utf8"))
    .join("\n");
  assert.doesNotMatch(sources, /Math\.random\s*\(/);
  assert.doesNotMatch(sources, /Date\.now\s*\(/);
  assert.doesNotMatch(sources, /randomUUID\s*\(/);
  assert.doesNotMatch(sources, /devicePixelRatio/);
});

test("Visual Asset, persistence, and stores do not save generated buffers", () => {
  const root = new URL("..", import.meta.url);
  const persistenceSources = [
    "src/features/visual-builder/visual-asset.ts",
    "src/features/visual-builder/visual-builder-persistence.ts",
    "src/store/visual-builder-store.ts",
    "src/store/canvas-store.ts",
  ]
    .map((path) => readFileSync(new URL(path, root), "utf8"))
    .join("\n");
  assert.doesNotMatch(
    persistenceSources,
    /\bpositions\b|\bregions\b|\banchors\b|Float32Array|Uint8Array/
  );
});
