import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";

import {
  ABSTRACT_BUST_AGE_TENDENCIES,
  ABSTRACT_BUST_GENERATOR_VERSION,
  ABSTRACT_BUST_HAIR_STYLES,
  ABSTRACT_BUST_PRESENTATIONS,
  AbstractBustBlueprintValidationError,
  getDefaultAbstractBustBlueprint,
  normalizeAbstractBustBlueprint,
} from "../../../packages/shared-schema/src/abstract-bust-blueprint.ts";

const fixtureUrl = (name) =>
  new URL(
    `../../../packages/shared-schema/contracts/abstract_bust_v0_1/fixtures/${name}`,
    import.meta.url
  );
const readFixture = (name = "default.json") =>
  JSON.parse(readFileSync(fixtureUrl(name), "utf8"));
const fixtureNames = [
  "default.json",
  "neutral.json",
  "feminine.json",
  "masculine.json",
  "hair_none.json",
  "hair_short.json",
  "hair_medium.json",
  "hair_long.json",
  "hair_tied.json",
];

function clone(value) {
  return JSON.parse(JSON.stringify(value));
}

function assertContractError(value, code) {
  assert.throws(
    () => normalizeAbstractBustBlueprint(value),
    (error) =>
      error instanceof AbstractBustBlueprintValidationError &&
      error.code === code
  );
}

test("AbstractBustBlueprint default and all nine upstream fixtures normalize", () => {
  assert.deepEqual(getDefaultAbstractBustBlueprint(), readFixture());
  for (const fixtureName of fixtureNames) {
    const normalized = normalizeAbstractBustBlueprint(readFixture(fixtureName));
    assert.equal(normalized.generator_version, ABSTRACT_BUST_GENERATOR_VERSION);
    assert.deepEqual(Object.keys(normalized), [
      "generator_version",
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
  }
});

test("AbstractBustBlueprint runtime enums come from the frozen schema", () => {
  assert.deepEqual(ABSTRACT_BUST_PRESENTATIONS, [
    "neutral",
    "feminine",
    "masculine",
  ]);
  assert.deepEqual(ABSTRACT_BUST_AGE_TENDENCIES, [
    "youthful",
    "balanced",
    "mature",
  ]);
  assert.deepEqual(ABSTRACT_BUST_HAIR_STYLES, [
    "none",
    "short",
    "medium",
    "long",
    "tied",
  ]);
});

test("AbstractBustBlueprint rejects unknown versions, enums, fields, and types", () => {
  const version = readFixture();
  version.generator_version = "abstract_bust_v9";
  assertContractError(version, "unknown_generator_version");

  const enumValue = readFixture();
  enumValue.hair.style = "braided";
  assertContractError(enumValue, "unknown_enum");

  const extra = readFixture();
  extra.face.eyes.iris_detail = 0.5;
  assertContractError(extra, "unknown_field");

  const type = readFixture();
  type.head.width = "0.265";
  assertContractError(type, "invalid_type");

  const seedType = readFixture();
  seedType.seed = 1.5;
  assertContractError(seedType, "invalid_type");
});

test("AbstractBustBlueprint rejects non-finite and missing required values", () => {
  for (const invalidNumber of [Number.NaN, Number.POSITIVE_INFINITY, Number.NEGATIVE_INFINITY]) {
    const blueprint = readFixture();
    blueprint.head.width = invalidNumber;
    assertContractError(blueprint, "non_finite_number");
  }

  const missingTopLevel = readFixture();
  delete missingTopLevel.head;
  assertContractError(missingTopLevel, "missing_required_field");

  const missingNested = readFixture();
  delete missingNested.face.eyes.spacing;
  assertContractError(missingNested, "missing_required_field");
});

test("AbstractBustBlueprint fills only optional groups and clamps finite ranges", () => {
  const optional = readFixture();
  delete optional.age_tendency;
  delete optional.face;
  delete optional.contour;
  assert.deepEqual(normalizeAbstractBustBlueprint(optional), readFixture());

  const clamped = readFixture();
  clamped.seed = 0;
  clamped.head.width = -100;
  clamped.shoulders.width = 100;
  clamped.contour.asymmetry = -1;
  const normalized = normalizeAbstractBustBlueprint(clamped);
  assert.equal(normalized.seed, 1);
  assert.equal(normalized.head.width, 0.22);
  assert.equal(normalized.shoulders.width, 0.68);
  assert.equal(normalized.contour.asymmetry, 0);
});

test("AbstractBustBlueprint normalization stays nested without legacy flat fields", () => {
  const normalized = normalizeAbstractBustBlueprint(readFixture("hair_long.json"));
  assert.equal(typeof normalized.face.eyes, "object");
  assert.equal(typeof normalized.face.jaw, "object");
  const serialized = JSON.stringify(normalized);
  for (const forbidden of [
    "head_width",
    "head_height",
    "shoulders_width",
    "hair_style",
    "AbstractBustTuning",
  ]) {
    assert.equal(serialized.includes(forbidden), false);
  }

  const source = clone(normalized);
  source.head.width = 0.3;
  assert.equal(getDefaultAbstractBustBlueprint().head.width, 0.265);
});
