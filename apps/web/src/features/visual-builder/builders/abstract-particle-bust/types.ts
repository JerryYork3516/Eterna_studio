import type { AbstractBustBlueprint } from "@eterna/shared-schema/abstract-bust-blueprint";

export const ABSTRACT_BUST_PARTICLE_COUNT = 12_000 as const;

export const ABSTRACT_BUST_REGION = Object.freeze({
  head: 0,
  facialFeatures: 1,
  hair: 2,
  neck: 3,
  shouldersAndChest: 4,
  torso: 5,
} as const);

export type AbstractBustRegionCode =
  (typeof ABSTRACT_BUST_REGION)[keyof typeof ABSTRACT_BUST_REGION];

export type AbstractBustPoint = readonly [number, number, number];

export type AbstractBustVisualAnchors = Readonly<{
  headCenter: AbstractBustPoint;
  headTop: AbstractBustPoint;
  neckBase: AbstractBustPoint;
  shoulderLeft: AbstractBustPoint;
  shoulderRight: AbstractBustPoint;
  chestCenter: AbstractBustPoint;
  torsoCenter: AbstractBustPoint;
  eyeLeft: AbstractBustPoint;
  eyeRight: AbstractBustPoint;
  noseCenter: AbstractBustPoint;
  mouthCenter: AbstractBustPoint;
  cheekLeft: AbstractBustPoint;
  cheekRight: AbstractBustPoint;
  chinCenter: AbstractBustPoint;
}>;

export type AbstractBustBounds = Readonly<{
  min: AbstractBustPoint;
  max: AbstractBustPoint;
}>;

export type GeneratedAbstractBust = Readonly<{
  generatorVersion: AbstractBustBlueprint["generator_version"];
  seed: number;
  particleCount: typeof ABSTRACT_BUST_PARTICLE_COUNT;
  positions: Float32Array;
  regions: Uint8Array;
  anchors: AbstractBustVisualAnchors;
  digest: string;
  bounds: AbstractBustBounds;
}>;

export type AbstractBustGenerator = (
  blueprint: AbstractBustBlueprint
) => GeneratedAbstractBust;
