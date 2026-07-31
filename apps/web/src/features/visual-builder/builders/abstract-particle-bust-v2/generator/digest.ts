import type { AbstractBustV2Bounds } from "../types.ts";
import { fpoint } from "./float32.ts";

const FNV1A_64_OFFSET_BASIS = 0xcbf2_9ce4_8422_2325n;
const FNV1A_64_PRIME = 0x0000_0100_0000_01b3n;
const DIGEST_PREFIX =
  "abstract_bust_v0_2:fnv1a64-f32le-xyz-index-order:";

export function digestAbstractBustV2Positions(
  positions: Float32Array
): string {
  const scratch = new ArrayBuffer(4);
  const view = new DataView(scratch);
  let digest = FNV1A_64_OFFSET_BASIS;

  for (const coordinate of positions) {
    view.setFloat32(0, coordinate, true);
    for (let byteOffset = 0; byteOffset < 4; byteOffset += 1) {
      digest ^= BigInt(view.getUint8(byteOffset));
      digest = BigInt.asUintN(64, digest * FNV1A_64_PRIME);
    }
  }
  return `${DIGEST_PREFIX}${digest.toString(16).padStart(16, "0")}`;
}

export function deriveAbstractBustV2Bounds(
  positions: Float32Array
): AbstractBustV2Bounds {
  let minX = Number.POSITIVE_INFINITY;
  let minY = Number.POSITIVE_INFINITY;
  let minZ = Number.POSITIVE_INFINITY;
  let maxX = Number.NEGATIVE_INFINITY;
  let maxY = Number.NEGATIVE_INFINITY;
  let maxZ = Number.NEGATIVE_INFINITY;

  for (let offset = 0; offset < positions.length; offset += 3) {
    const x = positions[offset];
    const y = positions[offset + 1];
    const z = positions[offset + 2];
    minX = Math.min(minX, x);
    minY = Math.min(minY, y);
    minZ = Math.min(minZ, z);
    maxX = Math.max(maxX, x);
    maxY = Math.max(maxY, y);
    maxZ = Math.max(maxZ, z);
  }
  return Object.freeze({
    min: fpoint(minX, minY, minZ),
    max: fpoint(maxX, maxY, maxZ),
  });
}
