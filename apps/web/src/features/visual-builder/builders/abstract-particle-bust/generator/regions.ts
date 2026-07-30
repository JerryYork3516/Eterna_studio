import type { AbstractBustBlueprint } from "@eterna/shared-schema/abstract-bust-blueprint";

import {
  ABSTRACT_BUST_PARTICLE_COUNT,
  ABSTRACT_BUST_REGION,
  type AbstractBustRegionCode,
} from "../types.ts";
import { f32, fmul, fmix } from "./float32.ts";

export type AbstractBustRegionRange = Readonly<{
  code: AbstractBustRegionCode;
  start: number;
  end: number;
}>;

export type AbstractBustRegionRanges = readonly AbstractBustRegionRange[];

export function deriveAbstractBustRegionRanges(
  blueprint: AbstractBustBlueprint
): AbstractBustRegionRanges {
  const count = ABSTRACT_BUST_PARTICLE_COUNT;
  const headEnd = Math.trunc(fmul(f32(count), 0.22));
  const hairCount =
    blueprint.hair.style === "none"
      ? 0
      : Math.trunc(
          fmul(f32(headEnd), fmix(0.22, 0.42, blueprint.hair.volume))
        );
  const hairStart = headEnd - hairCount;
  const featureCount = Math.trunc(fmul(f32(count), 0.015));
  const featureStart = hairStart - featureCount;
  const neckEnd = headEnd + Math.trunc(fmul(f32(count), 0.055));
  const shouldersEnd = neckEnd + Math.trunc(fmul(f32(count), 0.27));

  return Object.freeze([
    Object.freeze({ code: ABSTRACT_BUST_REGION.head, start: 0, end: featureStart }),
    Object.freeze({
      code: ABSTRACT_BUST_REGION.facialFeatures,
      start: featureStart,
      end: hairStart,
    }),
    Object.freeze({
      code: ABSTRACT_BUST_REGION.hair,
      start: hairStart,
      end: headEnd,
    }),
    Object.freeze({
      code: ABSTRACT_BUST_REGION.neck,
      start: headEnd,
      end: neckEnd,
    }),
    Object.freeze({
      code: ABSTRACT_BUST_REGION.shouldersAndChest,
      start: neckEnd,
      end: shouldersEnd,
    }),
    Object.freeze({
      code: ABSTRACT_BUST_REGION.torso,
      start: shouldersEnd,
      end: count,
    }),
  ]);
}

export function writeAbstractBustRegions(
  ranges: AbstractBustRegionRanges,
  output: Uint8Array
): void {
  for (const range of ranges) {
    output.fill(range.code, range.start, range.end);
  }
}
