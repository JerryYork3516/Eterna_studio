import { F32_PI, f32, fmul, fsub } from "./float32.ts";

const UINT64_MAX_AS_NUMBER = Number((1n << 64n) - 1n);
const GOLDEN_RATIO_64 = 0x9e37_79b9_7f4a_7c15n;
const REGION_STRIDE_64 = 0xd1b5_4a32_d192_ed03n;
const MIX_MULTIPLIER_1 = 0xbf58_476d_1ce4_e5b9n;
const MIX_MULTIPLIER_2 = 0x94d0_49bb_1331_11ebn;

function uint64(value: bigint): bigint {
  return BigInt.asUintN(64, value);
}

function splitMix64Finalizer(value: bigint): bigint {
  let mixed = uint64((value ^ (value >> 30n)) * MIX_MULTIPLIER_1);
  mixed = uint64((mixed ^ (mixed >> 27n)) * MIX_MULTIPLIER_2);
  return uint64(mixed ^ (mixed >> 31n));
}

function indexedValue(
  globalIndex: number,
  regionCode: number,
  seed: number,
  channelSalt: bigint
): bigint {
  return splitMix64Finalizer(
    uint64(
      BigInt(seed) +
        uint64(BigInt(globalIndex) * GOLDEN_RATIO_64) +
        uint64(BigInt(regionCode) * REGION_STRIDE_64) +
        channelSalt
    )
  );
}

export function deterministicSignedUnitV2(
  globalIndex: number,
  regionCode: number,
  seed: number,
  channelSalt: bigint
): number {
  const unit = f32(
    Number(indexedValue(globalIndex, regionCode, seed, channelSalt)) /
      UINT64_MAX_AS_NUMBER
  );
  return fsub(fmul(unit, 2), 1);
}

export function deterministicPhaseV2(
  regionCode: number,
  seed: number,
  channelSalt: bigint
): number {
  const unit = f32(
    Number(indexedValue(0, regionCode, seed, channelSalt)) /
      UINT64_MAX_AS_NUMBER
  );
  return fmul(fmul(unit, 2), F32_PI);
}
