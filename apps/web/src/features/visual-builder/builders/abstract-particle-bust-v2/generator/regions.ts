import {
  ABSTRACT_BUST_V2_REGION,
  type AbstractBustV2RegionCode,
} from "../types.ts";

export type AbstractBustV2RegionRange = Readonly<{
  code: AbstractBustV2RegionCode;
  start: number;
  end: number;
}>;

export type AbstractBustV2RegionRanges =
  readonly AbstractBustV2RegionRange[];

type WeightedCode<T extends number> = Readonly<{
  code: T;
  weight: number;
}>;

// Percent weights are frozen generator constants, not Blueprint fields.
export const ABSTRACT_BUST_V2_REGION_WEIGHTS = Object.freeze([
  Object.freeze({ code: ABSTRACT_BUST_V2_REGION.head, weight: 25 }),
  Object.freeze({ code: ABSTRACT_BUST_V2_REGION.facialFeatures, weight: 8 }),
  Object.freeze({ code: ABSTRACT_BUST_V2_REGION.hairScalp, weight: 11 }),
  Object.freeze({ code: ABSTRACT_BUST_V2_REGION.neck, weight: 8 }),
  Object.freeze({
    code: ABSTRACT_BUST_V2_REGION.shouldersAndChest,
    weight: 28,
  }),
  Object.freeze({ code: ABSTRACT_BUST_V2_REGION.torso, weight: 20 }),
] as const);

export const ABSTRACT_BUST_V2_FEATURE = Object.freeze({
  eyeLeft: 0,
  eyeRight: 1,
  nose: 2,
  mouth: 3,
  cheeks: 4,
  jaw: 5,
} as const);

export type AbstractBustV2FeatureCode =
  (typeof ABSTRACT_BUST_V2_FEATURE)[keyof typeof ABSTRACT_BUST_V2_FEATURE];

export const ABSTRACT_BUST_V2_FEATURE_WEIGHTS = Object.freeze([
  Object.freeze({ code: ABSTRACT_BUST_V2_FEATURE.eyeLeft, weight: 14 }),
  Object.freeze({ code: ABSTRACT_BUST_V2_FEATURE.eyeRight, weight: 14 }),
  Object.freeze({ code: ABSTRACT_BUST_V2_FEATURE.nose, weight: 18 }),
  Object.freeze({ code: ABSTRACT_BUST_V2_FEATURE.mouth, weight: 18 }),
  Object.freeze({ code: ABSTRACT_BUST_V2_FEATURE.cheeks, weight: 18 }),
  Object.freeze({ code: ABSTRACT_BUST_V2_FEATURE.jaw, weight: 18 }),
] as const);

export type AbstractBustV2FeatureRange = Readonly<{
  code: AbstractBustV2FeatureCode;
  start: number;
  end: number;
}>;

function allocateLargestRemainder<T extends number>(
  count: number,
  weightedCodes: readonly WeightedCode<T>[]
): readonly number[] {
  const totalWeight = weightedCodes.reduce(
    (total, entry) => total + entry.weight,
    0
  );
  if (totalWeight <= 0) {
    throw new Error("AbstractBustV2 allocation weights must be positive");
  }
  const allocations = weightedCodes.map((entry) =>
    Math.floor((count * entry.weight) / totalWeight)
  );
  const assigned = allocations.reduce((total, value) => total + value, 0);
  const ranked = weightedCodes
    .map((entry, index) => ({
      index,
      code: entry.code,
      remainder: (count * entry.weight) % totalWeight,
    }))
    .sort(
      (left, right) =>
        right.remainder - left.remainder || left.code - right.code
    );
  for (let offset = 0; offset < count - assigned; offset += 1) {
    allocations[ranked[offset].index] += 1;
  }
  return allocations;
}

export function deriveAbstractBustV2RegionRanges(
  particleCount: number
): AbstractBustV2RegionRanges {
  const allocations = allocateLargestRemainder(
    particleCount,
    ABSTRACT_BUST_V2_REGION_WEIGHTS
  );
  let cursor = 0;
  return Object.freeze(
    ABSTRACT_BUST_V2_REGION_WEIGHTS.map((entry, index) => {
      const start = cursor;
      cursor += allocations[index];
      return Object.freeze({ code: entry.code, start, end: cursor });
    })
  );
}

export function deriveAbstractBustV2FeatureRanges(
  featureCount: number
): readonly AbstractBustV2FeatureRange[] {
  const allocations = allocateLargestRemainder(
    featureCount,
    ABSTRACT_BUST_V2_FEATURE_WEIGHTS
  );
  let cursor = 0;
  return Object.freeze(
    ABSTRACT_BUST_V2_FEATURE_WEIGHTS.map((entry, index) => {
      const start = cursor;
      cursor += allocations[index];
      return Object.freeze({ code: entry.code, start, end: cursor });
    })
  );
}

export function writeAbstractBustV2Regions(
  ranges: AbstractBustV2RegionRanges,
  output: Uint8Array
): void {
  for (const range of ranges) {
    output.fill(range.code, range.start, range.end);
  }
}
