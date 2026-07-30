import type { AbstractBustHairStyle } from "@eterna/shared-schema/abstract-bust-blueprint";

import { F32_PI, f32, fadd, fmul, fsub } from "./float32.ts";

const UINT64_MASK = (1n << 64n) - 1n;
const UINT64_MAX_AS_NUMBER = Number(UINT64_MASK);
const GOLDEN_RATIO_64 = 0x9e37_79b9_7f4a_7c15n;
const MIX_MULTIPLIER_1 = 0xbf58_476d_1ce4_e5b9n;
const MIX_MULTIPLIER_2 = 0x94d0_49bb_1331_11ebn;

function uint64(value: bigint): bigint {
  return BigInt.asUintN(64, value);
}

function mixedValue(value: bigint): bigint {
  let mixed = uint64((value ^ (value >> 30n)) * MIX_MULTIPLIER_1);
  mixed = uint64((mixed ^ (mixed >> 27n)) * MIX_MULTIPLIER_2);
  return uint64(mixed ^ (mixed >> 31n));
}

export function deterministicSignedUnit(
  index: number,
  seed: number,
  salt: bigint
): number {
  const initial = uint64(
    BigInt(seed) + uint64(BigInt(index) * GOLDEN_RATIO_64) + salt
  );
  const unit = f32(Number(mixedValue(initial)) / UINT64_MAX_AS_NUMBER);
  return fsub(fmul(unit, 2), 1);
}

export function seededPhase(seed: number, salt: bigint): number {
  const initial = uint64(BigInt(seed) + uint64(salt * GOLDEN_RATIO_64));
  const unit = f32(Number(mixedValue(initial)) / UINT64_MAX_AS_NUMBER);
  return fmul(fmul(unit, 2), F32_PI);
}

export function hairSalt(style: AbstractBustHairStyle): bigint {
  switch (style) {
    case "none":
      return 0x550n;
    case "short":
      return 0x551n;
    case "medium":
      return 0x552n;
    case "long":
      return 0x553n;
    case "tied":
      return 0x554n;
  }
}

export function addSalt(salt: bigint, offset: number): bigint {
  return uint64(salt + BigInt(offset));
}
