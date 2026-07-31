import {
  normalizeAbstractBustBlueprintV2,
  type AbstractBustBlueprintV2,
} from "@eterna/shared-schema/abstract-bust-blueprint-v2";

import type { GeneratedAbstractBustV2 } from "../types.ts";
import {
  deriveAbstractBustV2Bounds,
  digestAbstractBustV2Positions,
} from "./digest.ts";
import { f32 } from "./float32.ts";
import { writeAbstractBustV2Positions } from "./geometry.ts";
import {
  deriveAbstractBustV2RegionRanges,
  writeAbstractBustV2Regions,
} from "./regions.ts";
import { applyAbstractBustV2SemanticWeights } from "./semantic-weights.ts";

export class AbstractBustV2GeneratorInputError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "AbstractBustV2GeneratorInputError";
  }
}

function canonicalValuesEqual(lhs: unknown, rhs: unknown): boolean {
  if (typeof lhs === "number" || typeof rhs === "number") {
    return (
      typeof lhs === "number" &&
      typeof rhs === "number" &&
      Object.is(lhs, rhs)
    );
  }
  if (
    lhs === null ||
    rhs === null ||
    typeof lhs !== "object" ||
    typeof rhs !== "object"
  ) {
    return lhs === rhs;
  }
  if (Array.isArray(lhs) || Array.isArray(rhs)) {
    return (
      Array.isArray(lhs) &&
      Array.isArray(rhs) &&
      lhs.length === rhs.length &&
      lhs.every((value, index) =>
        canonicalValuesEqual(value, rhs[index])
      )
    );
  }
  const lhsRecord = lhs as Record<string, unknown>;
  const rhsRecord = rhs as Record<string, unknown>;
  const lhsKeys = Object.keys(lhsRecord).sort();
  const rhsKeys = Object.keys(rhsRecord).sort();
  return (
    lhsKeys.length === rhsKeys.length &&
    lhsKeys.every((key, index) => key === rhsKeys[index]) &&
    lhsKeys.every((key) =>
      canonicalValuesEqual(lhsRecord[key], rhsRecord[key])
    )
  );
}

function toFloat32Blueprint(
  blueprint: AbstractBustBlueprintV2
): AbstractBustBlueprintV2 {
  return {
    generator_version: blueprint.generator_version,
    particle_count: blueprint.particle_count,
    presentation: blueprint.presentation,
    age_tendency: blueprint.age_tendency,
    seed: blueprint.seed,
    head: {
      width: f32(blueprint.head.width),
      height: f32(blueprint.head.height),
      depth: f32(blueprint.head.depth),
      roundness: f32(blueprint.head.roundness),
    },
    face: {
      eyes: {
        vertical_position: f32(blueprint.face.eyes.vertical_position),
        spacing: f32(blueprint.face.eyes.spacing),
        size: f32(blueprint.face.eyes.size),
        tilt: f32(blueprint.face.eyes.tilt),
        contour_strength: f32(blueprint.face.eyes.contour_strength),
      },
      nose: {
        vertical_position: f32(blueprint.face.nose.vertical_position),
        width: f32(blueprint.face.nose.width),
        length: f32(blueprint.face.nose.length),
        prominence: f32(blueprint.face.nose.prominence),
      },
      mouth: {
        vertical_position: f32(blueprint.face.mouth.vertical_position),
        width: f32(blueprint.face.mouth.width),
        curvature: f32(blueprint.face.mouth.curvature),
        contour_strength: f32(blueprint.face.mouth.contour_strength),
      },
      cheeks: {
        width: f32(blueprint.face.cheeks.width),
        vertical_position: f32(blueprint.face.cheeks.vertical_position),
        prominence: f32(blueprint.face.cheeks.prominence),
      },
      jaw: {
        width: f32(blueprint.face.jaw.width),
        taper: f32(blueprint.face.jaw.taper),
        length: f32(blueprint.face.jaw.length),
        roundness: f32(blueprint.face.jaw.roundness),
      },
    },
    neck: {
      width: f32(blueprint.neck.width),
      length: f32(blueprint.neck.length),
    },
    shoulders: {
      width: f32(blueprint.shoulders.width),
      slope: f32(blueprint.shoulders.slope),
    },
    torso: {
      width: f32(blueprint.torso.width),
      thickness: f32(blueprint.torso.thickness),
      length: f32(blueprint.torso.length),
      taper: f32(blueprint.torso.taper),
    },
    hair: {
      style: blueprint.hair.style,
      volume: f32(blueprint.hair.volume),
      length: f32(blueprint.hair.length),
    },
    contour: {
      softening: f32(blueprint.contour.softening),
      asymmetry: f32(blueprint.contour.asymmetry),
    },
  };
}

export function generateAbstractBustV2(
  blueprint: AbstractBustBlueprintV2
): GeneratedAbstractBustV2 {
  let normalized: AbstractBustBlueprintV2;
  try {
    normalized = normalizeAbstractBustBlueprintV2(blueprint);
  } catch (error) {
    throw new AbstractBustV2GeneratorInputError(
      error instanceof Error ? error.message : String(error)
    );
  }
  if (!canonicalValuesEqual(blueprint, normalized)) {
    throw new AbstractBustV2GeneratorInputError(
      "AbstractBustBlueprintV2 must already be complete and normalized"
    );
  }

  const floatBlueprint = applyAbstractBustV2SemanticWeights(
    toFloat32Blueprint(normalized)
  );
  const positions = new Float32Array(normalized.particle_count * 3);
  const regions = new Uint8Array(normalized.particle_count);
  const ranges = deriveAbstractBustV2RegionRanges(
    normalized.particle_count
  );
  writeAbstractBustV2Regions(ranges, regions);
  const anchors = writeAbstractBustV2Positions(
    floatBlueprint,
    ranges,
    positions
  );

  return Object.freeze({
    generatorVersion: normalized.generator_version,
    seed: normalized.seed,
    particleCount: normalized.particle_count,
    positions,
    regions,
    anchors,
    bounds: deriveAbstractBustV2Bounds(positions),
    digest: digestAbstractBustV2Positions(positions),
  });
}
