import assert from "node:assert/strict";
import { readFileSync, readdirSync } from "node:fs";
import { performance } from "node:perf_hooks";
import test from "node:test";

import {
  ABSTRACT_BUST_V2_EDITOR_FIELDS,
  getAbstractBustPresetFixtureV2,
  getDefaultAbstractBustBlueprintV2,
  normalizeAbstractBustBlueprintV2,
} from "../../../packages/shared-schema/src/abstract-bust-blueprint-v2.ts";
import {
  ABSTRACT_BUST_V2_REGION,
  AbstractBustV2GeneratorInputError,
  generateAbstractBustV2,
} from "../src/features/visual-builder/builders/abstract-particle-bust-v2/index.ts";

function clone(value) {
  return JSON.parse(JSON.stringify(value));
}

function mutateDefault(mutator) {
  const blueprint = clone(getDefaultAbstractBustBlueprintV2());
  mutator(blueprint);
  return normalizeAbstractBustBlueprintV2(blueprint);
}

function generateCount(particleCount) {
  return generateAbstractBustV2(
    mutateDefault((blueprint) => {
      blueprint.particle_count = particleCount;
    })
  );
}

function countRegions(regions) {
  const counts = new Map();
  for (const region of regions) {
    counts.set(region, (counts.get(region) ?? 0) + 1);
  }
  return Object.fromEntries(counts);
}

function pointsForRegion(result, region) {
  const points = [];
  for (let index = 0; index < result.particleCount; index += 1) {
    if (result.regions[index] !== region) continue;
    points.push([
      result.positions[index * 3],
      result.positions[index * 3 + 1],
      result.positions[index * 3 + 2],
    ]);
  }
  return points;
}

function pointBounds(points) {
  const min = [Infinity, Infinity, Infinity];
  const max = [-Infinity, -Infinity, -Infinity];
  for (const point of points) {
    for (let axis = 0; axis < 3; axis += 1) {
      min[axis] = Math.min(min[axis], point[axis]);
      max[axis] = Math.max(max[axis], point[axis]);
    }
  }
  return {
    min,
    max,
    span: max.map((value, axis) => value - min[axis]),
  };
}

function regionRms(left, right, region) {
  assert.deepEqual(left.regions, right.regions);
  let squared = 0;
  let coordinates = 0;
  for (let index = 0; index < left.particleCount; index += 1) {
    if (left.regions[index] !== region) continue;
    for (let axis = 0; axis < 3; axis += 1) {
      const offset = index * 3 + axis;
      const difference = left.positions[offset] - right.positions[offset];
      squared += difference * difference;
      coordinates += 1;
    }
  }
  return Math.sqrt(squared / coordinates);
}

function average(points, projection) {
  return points.reduce((total, point) => total + projection(point), 0) /
    points.length;
}

function getAtPath(value, path) {
  return path.split(".").reduce((current, key) => current[key], value);
}

function setAtPath(value, path, nextValue) {
  const components = path.split(".");
  const target = components
    .slice(0, -1)
    .reduce((current, key) => current[key], value);
  target[components.at(-1)] = nextValue;
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
  return (
    "abstract_bust_v0_2:fnv1a64-f32le-xyz-index-order:" +
    digest.toString(16).padStart(16, "0")
  );
}

test("v0.2 dynamically generates 6000, 12000, and 24000 finite particles", () => {
  for (const particleCount of [6000, 12000, 24000]) {
    const result = generateCount(particleCount);
    assert.equal(result.generatorVersion, "abstract_bust_v0_2");
    assert.equal(result.particleCount, particleCount);
    assert.ok(result.positions instanceof Float32Array);
    assert.ok(result.regions instanceof Uint8Array);
    assert.equal(result.positions.length, particleCount * 3);
    assert.equal(result.regions.length, particleCount);
    assert.ok(result.positions.every(Number.isFinite));
    assert.ok(result.bounds.min.every(Number.isFinite));
    assert.ok(result.bounds.max.every(Number.isFinite));
    assert.equal(
      result.positions.byteLength + result.regions.byteLength,
      particleCount * 13
    );
    assert.equal(result.digest, independentDigest(result.positions));
  }
});

test("largest-remainder region allocation is exact and stably ordered", () => {
  assert.deepEqual(ABSTRACT_BUST_V2_REGION, {
    head: 0,
    facialFeatures: 1,
    hairScalp: 2,
    neck: 3,
    shouldersAndChest: 4,
    torso: 5,
  });
  assert.deepEqual(countRegions(generateCount(6000).regions), {
    0: 1500,
    1: 480,
    2: 660,
    3: 480,
    4: 1680,
    5: 1200,
  });
  assert.deepEqual(countRegions(generateCount(6001).regions), {
    0: 1500,
    1: 480,
    2: 660,
    3: 480,
    4: 1681,
    5: 1200,
  });
  const regions = generateCount(12000).regions;
  assert.equal(regions.length, 12000);
  for (let index = 1; index < regions.length; index += 1) {
    assert.ok(regions[index] >= regions[index - 1]);
  }
});

test("all fourteen Blueprint-derived anchors are finite and ordered", () => {
  const anchors = generateAbstractBustV2(
    getDefaultAbstractBustBlueprintV2()
  ).anchors;
  assert.deepEqual(Object.keys(anchors), [
    "headTop",
    "headCenter",
    "neckBase",
    "shoulderLeft",
    "shoulderRight",
    "chestCenter",
    "torsoCenter",
    "eyeLeft",
    "eyeRight",
    "nose",
    "mouth",
    "cheekLeft",
    "cheekRight",
    "chin",
  ]);
  for (const point of Object.values(anchors)) {
    assert.equal(point.length, 3);
    assert.ok(point.every(Number.isFinite));
  }
  assert.ok(anchors.headTop[1] > anchors.headCenter[1]);
  assert.ok(anchors.headCenter[1] > anchors.neckBase[1]);
  assert.ok(anchors.neckBase[1] > anchors.chestCenter[1]);
  assert.ok(anchors.chestCenter[1] > anchors.torsoCenter[1]);
  assert.ok(anchors.shoulderLeft[0] < anchors.neckBase[0]);
  assert.ok(anchors.shoulderRight[0] > anchors.neckBase[0]);
  assert.ok(anchors.nose[2] > anchors.mouth[2]);
});

test("same input is byte-stable, one hundred digests remain stable, and seed participates", (context) => {
  const blueprint = getDefaultAbstractBustBlueprintV2();
  const first = generateAbstractBustV2(blueprint);
  const second = generateAbstractBustV2(blueprint);
  assert.deepEqual(second.positions, first.positions);
  assert.deepEqual(second.regions, first.regions);
  assert.deepEqual(second.anchors, first.anchors);
  assert.deepEqual(second.bounds, first.bounds);
  assert.equal(second.digest, first.digest);

  const startedAt = performance.now();
  for (let index = 0; index < 100; index += 1) {
    assert.equal(generateAbstractBustV2(blueprint).digest, first.digest);
  }
  context.diagnostic(
    `100 default generations: ${(performance.now() - startedAt).toFixed(1)} ms`
  );

  const changedSeed = generateAbstractBustV2(
    mutateDefault((value) => {
      value.seed += 1;
    })
  );
  assert.notEqual(changedSeed.digest, first.digest);
});

test("fixed region allocation preserves index classes across all presets", () => {
  const baseline = generateAbstractBustV2(
    getDefaultAbstractBustBlueprintV2()
  );
  for (const [kind, values] of [
    ["presentation", ["neutral", "feminine", "masculine"]],
    ["age_tendency", ["youthful", "balanced", "mature"]],
    ["hair", ["none", "short", "medium", "long", "tied"]],
  ]) {
    for (const value of values) {
      const result = generateAbstractBustV2(
        getAbstractBustPresetFixtureV2(kind, value)
      );
      assert.deepEqual(result.regions, baseline.regions, `${kind}:${value}`);
    }
  }
});

test("all numeric shape fields participate without private defaults", () => {
  const defaultBlueprint = getDefaultAbstractBustBlueprintV2();
  const defaultResult = generateAbstractBustV2(defaultBlueprint);
  for (const field of ABSTRACT_BUST_V2_EDITOR_FIELDS) {
    if (
      field.valueType === "enum" ||
      field.path === "particle_count" ||
      field.path === "seed"
    ) {
      continue;
    }
    const baselineBlueprint = clone(defaultBlueprint);
    if (field.path.startsWith("hair.")) {
      baselineBlueprint.hair.style = "short";
    }
    const baseline = field.path.startsWith("hair.")
      ? generateAbstractBustV2(
          normalizeAbstractBustBlueprintV2(baselineBlueprint)
        )
      : defaultResult;
    const changedBlueprint = clone(baselineBlueprint);
    const current = getAtPath(changedBlueprint, field.path);
    const next =
      current === field.minimum ? field.maximum : field.minimum;
    setAtPath(changedBlueprint, field.path, next);
    const changed = generateAbstractBustV2(
      normalizeAbstractBustBlueprintV2(changedBlueprint)
    );
    assert.notEqual(changed.digest, baseline.digest, field.path);
  }
});

test("head dimensions and roundness change head geometry, with depth isolated on Z", () => {
  const baseline = generateAbstractBustV2(
    getDefaultAbstractBustBlueprintV2()
  );
  const baselineHead = pointBounds(
    pointsForRegion(baseline, ABSTRACT_BUST_V2_REGION.head)
  );
  assert.ok(Math.abs(baselineHead.span[0] - baselineHead.span[2]) > 0.05);
  assert.ok(Math.abs(baselineHead.span[1] - baselineHead.span[0]) > 0.10);

  for (const [label, mutate] of [
    ["width", (value) => { value.head.width = 0.30; }],
    ["height", (value) => { value.head.height = 0.38; }],
    ["roundness", (value) => { value.head.roundness = 0.75; }],
  ]) {
    const changed = generateAbstractBustV2(mutateDefault(mutate));
    assert.ok(
      regionRms(
        baseline,
        changed,
        ABSTRACT_BUST_V2_REGION.head
      ) > 0.000_1,
      label
    );
  }

  const deeper = generateAbstractBustV2(
    mutateDefault((value) => {
      value.head.depth = 0.27;
    })
  );
  const deeperHead = pointBounds(
    pointsForRegion(deeper, ABSTRACT_BUST_V2_REGION.head)
  );
  assert.ok(deeperHead.span[2] > baselineHead.span[2] + 0.05);
});

test("eyes, nose, mouth, cheeks, and jaw each create local face differences", () => {
  const baseline = generateAbstractBustV2(
    getDefaultAbstractBustBlueprintV2()
  );
  const cases = [
    ["eyes", (value) => { value.face.eyes.size = 0.06; }],
    ["nose", (value) => { value.face.nose.prominence = 0.055; }],
    ["mouth", (value) => { value.face.mouth.curvature = 0.20; }],
    ["cheeks", (value) => { value.face.cheeks.prominence = 0.045; }],
    ["jaw", (value) => { value.face.jaw.taper = 0.25; }],
  ];
  for (const [label, mutate] of cases) {
    const changed = generateAbstractBustV2(mutateDefault(mutate));
    assert.ok(
      regionRms(
        baseline,
        changed,
        ABSTRACT_BUST_V2_REGION.facialFeatures
      ) > 0.000_1,
      label
    );
  }
});

test("neck flares, shoulder curve drops, and torso tapers instead of forming primitives", () => {
  const result = generateAbstractBustV2(
    getDefaultAbstractBustBlueprintV2()
  );
  const centerX = result.anchors.headCenter[0];

  const neck = pointsForRegion(result, ABSTRACT_BUST_V2_REGION.neck);
  const neckY = neck.map((point) => point[1]).sort((a, b) => a - b);
  const neckLow = neckY[Math.floor(neckY.length * 0.25)];
  const neckHigh = neckY[Math.floor(neckY.length * 0.75)];
  const neckBottom = neck.filter((point) => point[1] <= neckLow);
  const neckTop = neck.filter((point) => point[1] >= neckHigh);
  assert.ok(
    average(neckBottom, (point) => Math.abs(point[0] - centerX)) >
      average(neckTop, (point) => Math.abs(point[0] - centerX)) + 0.02
  );
  assert.ok(
    average(neckBottom, (point) => Math.abs(point[2])) >
      average(neckTop, (point) => Math.abs(point[2])) + 0.02
  );

  const shoulder = pointsForRegion(
    result,
    ABSTRACT_BUST_V2_REGION.shouldersAndChest
  );
  const shoulderMaxX = Math.max(
    ...shoulder.map((point) => Math.abs(point[0] - centerX))
  );
  const shoulderOuter = shoulder.filter(
    (point) => Math.abs(point[0] - centerX) > shoulderMaxX * 0.82
  );
  const shoulderInner = shoulder.filter(
    (point) => Math.abs(point[0] - centerX) < shoulderMaxX * 0.25
  );
  assert.ok(
    average(shoulderOuter, (point) => point[1]) <
      average(shoulderInner, (point) => point[1]) - 0.05
  );

  const torso = pointsForRegion(result, ABSTRACT_BUST_V2_REGION.torso);
  const torsoY = torso.map((point) => point[1]).sort((a, b) => a - b);
  const torsoLow = torsoY[Math.floor(torsoY.length * 0.25)];
  const torsoHigh = torsoY[Math.floor(torsoY.length * 0.75)];
  const torsoBottom = torso.filter((point) => point[1] <= torsoLow);
  const torsoTop = torso.filter((point) => point[1] >= torsoHigh);
  const topBounds = pointBounds(torsoTop);
  const bottomBounds = pointBounds(torsoBottom);
  assert.ok(topBounds.span[0] > bottomBounds.span[0] + 0.15);
  assert.ok(topBounds.span[2] > bottomBounds.span[2] + 0.08);
});

test("hair styles and complete preset fixtures remain distinct", () => {
  for (const [kind, values] of [
    ["presentation", ["neutral", "feminine", "masculine"]],
    ["age_tendency", ["youthful", "balanced", "mature"]],
    ["hair", ["none", "short", "medium", "long", "tied"]],
  ]) {
    const digests = new Set(
      values.map((value) =>
        generateAbstractBustV2(
          getAbstractBustPresetFixtureV2(kind, value)
        ).digest
      )
    );
    assert.equal(digests.size, values.length, kind);
  }
});

test("presentation alone produces stable, finite, and restrained local differences", () => {
  const baseline = getDefaultAbstractBustBlueprintV2();
  const untouched = clone(baseline);
  const results = ["neutral", "feminine", "masculine"].map(
    (presentation) => {
      const blueprint = clone(baseline);
      blueprint.presentation = presentation;
      const before = clone(blueprint);
      const first = generateAbstractBustV2(blueprint);
      const second = generateAbstractBustV2(blueprint);
      assert.deepEqual(blueprint, before);
      assert.equal(second.digest, first.digest);
      assert.ok(first.positions.every(Number.isFinite));
      return first;
    }
  );
  assert.deepEqual(baseline, untouched);
  assert.equal(new Set(results.map((result) => result.digest)).size, 3);
  for (const result of results.slice(1)) {
    assert.deepEqual(result.regions, results[0].regions);
    for (const region of [
      ABSTRACT_BUST_V2_REGION.head,
      ABSTRACT_BUST_V2_REGION.facialFeatures,
      ABSTRACT_BUST_V2_REGION.neck,
      ABSTRACT_BUST_V2_REGION.shouldersAndChest,
      ABSTRACT_BUST_V2_REGION.torso,
    ]) {
      const rms = regionRms(results[0], result, region);
      assert.ok(rms > 0.000_5, `presentation region ${region}`);
      assert.ok(rms < 0.015, `presentation restraint ${region}`);
    }
  }
});

test("age tendency alone produces stable, finite, and restrained local differences", () => {
  const baseline = getDefaultAbstractBustBlueprintV2();
  const untouched = clone(baseline);
  const results = ["balanced", "youthful", "mature"].map(
    (ageTendency) => {
      const blueprint = clone(baseline);
      blueprint.age_tendency = ageTendency;
      const before = clone(blueprint);
      const first = generateAbstractBustV2(blueprint);
      const second = generateAbstractBustV2(blueprint);
      assert.deepEqual(blueprint, before);
      assert.equal(second.digest, first.digest);
      assert.ok(first.positions.every(Number.isFinite));
      return first;
    }
  );
  assert.deepEqual(baseline, untouched);
  assert.equal(new Set(results.map((result) => result.digest)).size, 3);
  for (const result of results.slice(1)) {
    assert.deepEqual(result.regions, results[0].regions);
    for (const region of [
      ABSTRACT_BUST_V2_REGION.head,
      ABSTRACT_BUST_V2_REGION.facialFeatures,
      ABSTRACT_BUST_V2_REGION.neck,
      ABSTRACT_BUST_V2_REGION.shouldersAndChest,
      ABSTRACT_BUST_V2_REGION.torso,
    ]) {
      const rms = regionRms(results[0], result, region);
      assert.ok(rms > 0.000_5, `age region ${region}`);
      assert.ok(rms < 0.015, `age restraint ${region}`);
    }
  }
});

test("generator rejects inputs that are invalid or not already canonical", () => {
  const invalidVersion = clone(getDefaultAbstractBustBlueprintV2());
  invalidVersion.generator_version = "abstract_bust_v9";
  assert.throws(
    () => generateAbstractBustV2(invalidVersion),
    AbstractBustV2GeneratorInputError
  );

  const nonFinite = clone(getDefaultAbstractBustBlueprintV2());
  nonFinite.head.depth = Number.NaN;
  assert.throws(
    () => generateAbstractBustV2(nonFinite),
    AbstractBustV2GeneratorInputError
  );

  const incomplete = clone(getDefaultAbstractBustBlueprintV2());
  delete incomplete.face;
  assert.throws(
    () => generateAbstractBustV2(incomplete),
    AbstractBustV2GeneratorInputError
  );

  const needsClamp = clone(getDefaultAbstractBustBlueprintV2());
  needsClamp.particle_count = 1;
  assert.throws(
    () => generateAbstractBustV2(needsClamp),
    AbstractBustV2GeneratorInputError
  );

  const needsDefault = clone(getDefaultAbstractBustBlueprintV2());
  delete needsDefault.particle_count;
  assert.throws(
    () => generateAbstractBustV2(needsDefault),
    AbstractBustV2GeneratorInputError
  );
});

test("output remains memory-only and v2 sources are isolated and deterministic", () => {
  const result = generateAbstractBustV2(
    getDefaultAbstractBustBlueprintV2()
  );
  assert.deepEqual(Object.keys(result), [
    "generatorVersion",
    "seed",
    "particleCount",
    "positions",
    "regions",
    "anchors",
    "bounds",
    "digest",
  ]);
  assert.doesNotMatch(
    Object.keys(result).join(" "),
    /color|camera|morph|animation|runtime/i
  );

  const generatorRoot = new URL(
    "../src/features/visual-builder/builders/abstract-particle-bust-v2/generator/",
    import.meta.url
  );
  const sources = readdirSync(generatorRoot)
    .filter((name) => name.endsWith(".ts"))
    .map((name) => readFileSync(new URL(name, generatorRoot), "utf8"))
    .join("\n");
  assert.doesNotMatch(sources, /Math\.random\s*\(/);
  assert.doesNotMatch(sources, /Date\.now\s*\(/);
  assert.doesNotMatch(sources, /randomUUID\s*\(/);
  assert.doesNotMatch(sources, /devicePixelRatio/);
  assert.doesNotMatch(sources, /abstract-particle-bust\/generator/);
  assert.doesNotMatch(sources, /new Float32Array\s*\(\s*36_?000/);
  assert.doesNotMatch(sources, /new Uint8Array\s*\(\s*12_?000/);
});

test("directed performance measurements are recorded without thresholds", (context) => {
  for (const count of [6000, 12000, 24000]) {
    const startedAt = performance.now();
    const result = generateCount(count);
    const elapsed = performance.now() - startedAt;
    context.diagnostic(
      `${count} particles: ${elapsed.toFixed(1)} ms; ` +
        `${result.positions.byteLength + result.regions.byteLength} typed-array bytes`
    );
  }
});
