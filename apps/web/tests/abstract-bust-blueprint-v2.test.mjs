import assert from "node:assert/strict";
import { readdirSync, readFileSync } from "node:fs";
import { test } from "node:test";

import {
  ABSTRACT_BUST_V2_AGE_TENDENCIES,
  ABSTRACT_BUST_V2_EDITOR_FIELDS,
  ABSTRACT_BUST_V2_GENERATOR_VERSION,
  ABSTRACT_BUST_V2_HAIR_STYLES,
  ABSTRACT_BUST_V2_PRESENTATIONS,
  AbstractBustBlueprintV2ValidationError,
  applyAbstractBustPresetV2,
  getAbstractBustPresetFixtureV2,
  getDefaultAbstractBustBlueprintV2,
  normalizeAbstractBustBlueprintV2,
} from "../../../packages/shared-schema/src/abstract-bust-blueprint-v2.ts";
import {
  AbstractBustBlueprintRoutingError,
  normalizeAbstractBustBlueprintByVersion,
} from "../../../packages/shared-schema/src/abstract-bust-blueprint-router.ts";

const contractUrl = new URL(
  "../../../packages/shared-schema/contracts/abstract_bust_v0_2/",
  import.meta.url
);
const fixtureUrl = (name) => new URL(`fixtures/${name}`, contractUrl);
const readJson = (url) => JSON.parse(readFileSync(url, "utf8"));
const readFixture = (name = "default.json") => readJson(fixtureUrl(name));
const fixtureNames = [
  "default.json",
  "neutral.json",
  "feminine.json",
  "masculine.json",
  "youthful.json",
  "balanced.json",
  "mature.json",
  "hair_none.json",
  "hair_short.json",
  "hair_medium.json",
  "hair_long.json",
  "hair_tied.json",
];

function clone(value) {
  return JSON.parse(JSON.stringify(value));
}

function assertV2Error(value, code, path) {
  assert.throws(
    () => normalizeAbstractBustBlueprintV2(value),
    (error) =>
      error instanceof AbstractBustBlueprintV2ValidationError &&
      error.code === code &&
      (path === undefined || error.path === path)
  );
}

function resolveSchema(schema, node) {
  if (!node.$ref) return node;
  return schema.$defs[node.$ref.replace("#/$defs/", "")];
}

function collectSchemaFields(schema, node = schema, path = []) {
  const resolved = resolveSchema(schema, node);
  if (resolved.type === "object") {
    return Object.entries(resolved.properties).flatMap(([key, child]) => {
      if (path.length === 0 && key === "generator_version") return [];
      return collectSchemaFields(schema, child, [...path, key]);
    });
  }
  return [
    {
      path: path.join("."),
      valueType: resolved.enum ? "enum" : resolved.type,
      defaultValue: resolved.default,
      ...(resolved.minimum === undefined
        ? {}
        : { minimum: resolved.minimum }),
      ...(resolved.maximum === undefined
        ? {}
        : { maximum: resolved.maximum }),
      ...(resolved.enum ? { enumValues: resolved.enum } : {}),
    },
  ];
}

function getAtPath(value, path) {
  return path.split(".").reduce((current, key) => current[key], value);
}

function changedLeafPaths(left, right, path = []) {
  if (
    left &&
    right &&
    typeof left === "object" &&
    typeof right === "object" &&
    !Array.isArray(left) &&
    !Array.isArray(right)
  ) {
    return [...new Set([...Object.keys(left), ...Object.keys(right)])].flatMap(
      (key) => changedLeafPaths(left[key], right[key], [...path, key])
    );
  }
  return Object.is(left, right) ? [] : [path.join(".")];
}

test("v0.2 default and all 12 complete fixtures normalize without drift", () => {
  assert.deepEqual(getDefaultAbstractBustBlueprintV2(), readFixture());
  for (const fixtureName of fixtureNames) {
    const fixture = readFixture(fixtureName);
    const normalized = normalizeAbstractBustBlueprintV2(fixture);
    assert.deepEqual(normalized, fixture);
    assert.equal(
      normalized.generator_version,
      ABSTRACT_BUST_V2_GENERATOR_VERSION
    );
    assert.equal(normalized.particle_count, 12000);
    assert.equal(normalized.head.depth >= 0.18, true);
    assert.equal(normalized.head.depth <= 0.28, true);
  }
});

test("v0.2 exposes 41 editor fields entirely derived from the schema", () => {
  const schema = readJson(
    new URL("abstract_bust_blueprint_v0_2.schema.json", contractUrl)
  );
  const expected = collectSchemaFields(schema);
  assert.equal(expected.length, 41);
  assert.deepEqual(ABSTRACT_BUST_V2_EDITOR_FIELDS, expected);
  const defaultFixture = readFixture();
  for (const field of expected) {
    assert.deepEqual(
      getAtPath(defaultFixture, field.path),
      field.defaultValue,
      `${field.path} must use the schema default`
    );
  }
  assert.deepEqual(ABSTRACT_BUST_V2_PRESENTATIONS, [
    "neutral",
    "feminine",
    "masculine",
  ]);
  assert.deepEqual(ABSTRACT_BUST_V2_AGE_TENDENCIES, [
    "youthful",
    "balanced",
    "mature",
  ]);
  assert.deepEqual(ABSTRACT_BUST_V2_HAIR_STYLES, [
    "none",
    "short",
    "medium",
    "long",
    "tied",
  ]);
});

test("v0.2 fixtures preserve the frozen preset boundaries", () => {
  const defaultFixture = readFixture();
  assert.deepEqual(readFixture("neutral.json"), defaultFixture);
  assert.deepEqual(readFixture("balanced.json"), defaultFixture);
  assert.deepEqual(readFixture("hair_none.json"), defaultFixture);

  for (const name of [
    "hair_short.json",
    "hair_medium.json",
    "hair_long.json",
    "hair_tied.json",
  ]) {
    assert.equal(
      changedLeafPaths(defaultFixture, readFixture(name)).every((path) =>
        path.startsWith("hair.")
      ),
      true
    );
  }
  for (const name of ["neutral.json", "feminine.json", "masculine.json"]) {
    assert.equal(readFixture(name).hair.style, "none");
    assert.equal(readFixture(name).particle_count, defaultFixture.particle_count);
    assert.equal(readFixture(name).seed, defaultFixture.seed);
  }
});

test("v0.2 version router dispatches v0.1 and v0.2 without migration", () => {
  const v1 = readJson(
    new URL(
      "../../../packages/shared-schema/contracts/abstract_bust_v0_1/fixtures/default.json",
      import.meta.url
    )
  );
  assert.equal(
    normalizeAbstractBustBlueprintByVersion(v1).generator_version,
    "abstract_bust_v0_1"
  );
  assert.equal(
    normalizeAbstractBustBlueprintByVersion(readFixture()).generator_version,
    "abstract_bust_v0_2"
  );

  const missing = readFixture();
  delete missing.generator_version;
  assert.throws(
    () => normalizeAbstractBustBlueprintByVersion(missing),
    (error) =>
      error instanceof AbstractBustBlueprintRoutingError &&
      error.code === "missing_required_field" &&
      error.path === "$.generator_version"
  );
  const unknown = readFixture();
  unknown.generator_version = "abstract_bust_v0_3";
  assert.throws(
    () => normalizeAbstractBustBlueprintByVersion(unknown),
    (error) =>
      error instanceof AbstractBustBlueprintRoutingError &&
      error.code === "unknown_generator_version"
  );
});

test("v0.2 rejects unknown versions, enums, fields, and wrong types", () => {
  const version = readFixture();
  version.generator_version = "abstract_bust_v9";
  assertV2Error(version, "unknown_generator_version");

  const enumValue = readFixture();
  enumValue.age_tendency = "ancient";
  assertV2Error(enumValue, "unknown_enum", "$.age_tendency");

  const extra = readFixture();
  extra.head.crown = 0.2;
  assertV2Error(extra, "unknown_field", "$.head.crown");

  const type = readFixture();
  type.head.depth = "0.23";
  assertV2Error(type, "invalid_type", "$.head.depth");

  const root = [];
  assertV2Error(root, "invalid_type", "$");
});

test("v0.2 rejects non-finite numbers and missing required fields", () => {
  for (const invalidNumber of [
    Number.NaN,
    Number.POSITIVE_INFINITY,
    Number.NEGATIVE_INFINITY,
  ]) {
    const blueprint = readFixture();
    blueprint.head.depth = invalidNumber;
    assertV2Error(blueprint, "non_finite_number", "$.head.depth");
  }

  const missingHead = readFixture();
  delete missingHead.head;
  assertV2Error(missingHead, "missing_required_field", "$.head");

  const missingDepth = readFixture();
  delete missingDepth.head.depth;
  assertV2Error(
    missingDepth,
    "missing_required_field",
    "$.head.depth"
  );
});

test("particle_count defaults, clamps, and accepts only finite integers", () => {
  const missing = readFixture();
  delete missing.particle_count;
  assert.equal(normalizeAbstractBustBlueprintV2(missing).particle_count, 12000);

  const below = readFixture();
  below.particle_count = 1;
  assert.equal(normalizeAbstractBustBlueprintV2(below).particle_count, 6000);

  const above = readFixture();
  above.particle_count = 999999;
  assert.equal(normalizeAbstractBustBlueprintV2(above).particle_count, 24000);

  for (const invalid of [
    12000.5,
    "12000",
    true,
    Number.NaN,
    Number.POSITIVE_INFINITY,
    Number.NEGATIVE_INFINITY,
  ]) {
    const blueprint = readFixture();
    blueprint.particle_count = invalid;
    assertV2Error(blueprint, "invalid_type", "$.particle_count");
  }
});

test("v0.2 fills optional groups and clamps finite values from the schema", () => {
  const optional = readFixture();
  delete optional.particle_count;
  delete optional.age_tendency;
  delete optional.face;
  delete optional.contour;
  assert.deepEqual(normalizeAbstractBustBlueprintV2(optional), readFixture());

  const clamped = readFixture();
  clamped.seed = 0;
  clamped.head.depth = -100;
  clamped.shoulders.width = 100;
  clamped.contour.asymmetry = -1;
  const normalized = normalizeAbstractBustBlueprintV2(clamped);
  assert.equal(normalized.seed, 1);
  assert.equal(normalized.head.depth, 0.18);
  assert.equal(normalized.shoulders.width, 0.68);
  assert.equal(normalized.contour.asymmetry, 0);
});

test("v0.2 presets are complete fixtures and preserve seed and particle_count", () => {
  const current = readFixture();
  current.seed = 17;
  current.particle_count = 23001;

  for (const [kind, values] of [
    ["presentation", ABSTRACT_BUST_V2_PRESENTATIONS],
    ["age_tendency", ABSTRACT_BUST_V2_AGE_TENDENCIES],
    ["hair", ABSTRACT_BUST_V2_HAIR_STYLES],
  ]) {
    for (const value of values) {
      const fixture = getAbstractBustPresetFixtureV2(kind, value);
      const applied = applyAbstractBustPresetV2(current, kind, value);
      assert.equal(applied.seed, current.seed);
      assert.equal(applied.particle_count, current.particle_count);
      assert.deepEqual(
        { ...applied, seed: fixture.seed, particle_count: fixture.particle_count },
        fixture
      );
    }
  }

  const restored = getDefaultAbstractBustBlueprintV2();
  assert.equal(restored.seed, readFixture().seed);
  assert.equal(restored.particle_count, 12000);
});

test("v0.2 output stays nested and contract excludes generator artifacts", () => {
  const normalized = normalizeAbstractBustBlueprintV2(
    readFixture("hair_long.json")
  );
  assert.deepEqual(Object.keys(normalized), [
    "generator_version",
    "particle_count",
    "presentation",
    "age_tendency",
    "seed",
    "head",
    "face",
    "neck",
    "shoulders",
    "torso",
    "hair",
    "contour",
  ]);
  const serialized = JSON.stringify(normalized);
  for (const forbidden of [
    "head_width",
    "head_depth",
    "shoulders_width",
    "hair_style",
    "AbstractBustTuning",
    "positions",
    "regions",
    "anchors",
  ]) {
    assert.equal(serialized.includes(forbidden), false);
  }

  const contractEntries = readdirSync(contractUrl, { recursive: true }).map(
    String
  );
  for (const forbidden of [
    "golden",
    "digest",
    "coordinate",
    "coordinates",
    "oracle",
  ]) {
    assert.equal(
      contractEntries.some((entry) => entry.toLowerCase().includes(forbidden)),
      false
    );
  }
});

test("v0.2 implementations do not contain private fixed particle constants", () => {
  const sources = [
    new URL(
      "../../../packages/shared-schema/src/abstract-bust-blueprint-v2.ts",
      import.meta.url
    ),
    new URL(
      "../../../apps/api/app/services/abstract_bust_blueprint_v2.py",
      import.meta.url
    ),
  ];
  for (const source of sources) {
    const text = readFileSync(source, "utf8");
    assert.equal(/\b12000\b/.test(text), false);
    assert.equal(/Float32Array\s*\(\s*12000/.test(text), false);
  }
});
