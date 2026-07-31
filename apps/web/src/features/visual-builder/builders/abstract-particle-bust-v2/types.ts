import type { AbstractBustBlueprintV2 } from "@eterna/shared-schema/abstract-bust-blueprint-v2";

export const ABSTRACT_BUST_V2_REGION = Object.freeze({
  head: 0,
  facialFeatures: 1,
  hairScalp: 2,
  neck: 3,
  shouldersAndChest: 4,
  torso: 5,
} as const);

export type AbstractBustV2RegionCode =
  (typeof ABSTRACT_BUST_V2_REGION)[keyof typeof ABSTRACT_BUST_V2_REGION];

export type AbstractBustV2Point = readonly [number, number, number];

export type AbstractBustV2DerivedAnchors = Readonly<{
  headTop: AbstractBustV2Point;
  headCenter: AbstractBustV2Point;
  neckBase: AbstractBustV2Point;
  shoulderLeft: AbstractBustV2Point;
  shoulderRight: AbstractBustV2Point;
  chestCenter: AbstractBustV2Point;
  torsoCenter: AbstractBustV2Point;
  eyeLeft: AbstractBustV2Point;
  eyeRight: AbstractBustV2Point;
  nose: AbstractBustV2Point;
  mouth: AbstractBustV2Point;
  cheekLeft: AbstractBustV2Point;
  cheekRight: AbstractBustV2Point;
  chin: AbstractBustV2Point;
}>;

export type AbstractBustV2Bounds = Readonly<{
  min: AbstractBustV2Point;
  max: AbstractBustV2Point;
}>;

export type GeneratedAbstractBustV2 = Readonly<{
  generatorVersion: AbstractBustBlueprintV2["generator_version"];
  seed: number;
  particleCount: number;
  positions: Float32Array;
  regions: Uint8Array;
  anchors: AbstractBustV2DerivedAnchors;
  bounds: AbstractBustV2Bounds;
  digest: string;
}>;

export type AbstractBustV2Generator = (
  blueprint: AbstractBustBlueprintV2
) => GeneratedAbstractBustV2;
