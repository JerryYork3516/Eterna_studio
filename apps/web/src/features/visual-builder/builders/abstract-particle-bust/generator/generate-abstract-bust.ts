import {
  normalizeAbstractBustBlueprint,
  type AbstractBustBlueprint,
} from "@eterna/shared-schema/abstract-bust-blueprint";

import {
  ABSTRACT_BUST_PARTICLE_COUNT,
  type GeneratedAbstractBust,
} from "../types.ts";
import {
  deriveAbstractBustBounds,
  digestAbstractBustPositions,
} from "./digest.ts";
import { f32 } from "./float32.ts";
import { writeAbstractBustPositions } from "./geometry.ts";
import {
  deriveAbstractBustRegionRanges,
  writeAbstractBustRegions,
} from "./regions.ts";

export class AbstractBustGeneratorInputError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "AbstractBustGeneratorInputError";
  }
}

function canonicalValuesEqual(lhs: unknown, rhs: unknown): boolean {
  if (typeof lhs === "number" || typeof rhs === "number") {
    return typeof lhs === "number" && typeof rhs === "number" && Object.is(lhs, rhs);
  }
  if (lhs === null || rhs === null || typeof lhs !== "object" || typeof rhs !== "object") {
    return lhs === rhs;
  }
  if (Array.isArray(lhs) || Array.isArray(rhs)) {
    if (!Array.isArray(lhs) || !Array.isArray(rhs) || lhs.length !== rhs.length) return false;
    return lhs.every((value, index) => canonicalValuesEqual(value, rhs[index]));
  }
  const lhsRecord = lhs as Record<string, unknown>;
  const rhsRecord = rhs as Record<string, unknown>;
  const lhsKeys = Object.keys(lhsRecord).sort();
  const rhsKeys = Object.keys(rhsRecord).sort();
  if (
    lhsKeys.length !== rhsKeys.length ||
    lhsKeys.some((key, index) => key !== rhsKeys[index])
  ) {
    return false;
  }
  return lhsKeys.every((key) =>
    canonicalValuesEqual(lhsRecord[key], rhsRecord[key])
  );
}

function toFloat32Blueprint(
  blueprint: AbstractBustBlueprint
): AbstractBustBlueprint {
  return {
    generator_version: blueprint.generator_version,
    presentation: blueprint.presentation,
    age_tendency: blueprint.age_tendency,
    seed: blueprint.seed,
    head: {
      width: f32(blueprint.head.width),
      height: f32(blueprint.head.height),
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

export function generateAbstractBust(
  blueprint: AbstractBustBlueprint
): GeneratedAbstractBust {
  const normalized = normalizeAbstractBustBlueprint(blueprint);
  if (!canonicalValuesEqual(blueprint, normalized)) {
    throw new AbstractBustGeneratorInputError(
      "AbstractBustBlueprint must already be complete and normalized"
    );
  }

  const floatBlueprint = toFloat32Blueprint(normalized);
  const positions = new Float32Array(ABSTRACT_BUST_PARTICLE_COUNT * 3);
  const regions = new Uint8Array(ABSTRACT_BUST_PARTICLE_COUNT);
  const ranges = deriveAbstractBustRegionRanges(floatBlueprint);
  writeAbstractBustRegions(ranges, regions);
  const anchors = writeAbstractBustPositions(
    floatBlueprint,
    ranges,
    positions
  );

  return Object.freeze({
    generatorVersion: normalized.generator_version,
    seed: normalized.seed,
    particleCount: ABSTRACT_BUST_PARTICLE_COUNT,
    positions,
    regions,
    anchors,
    digest: digestAbstractBustPositions(positions),
    bounds: deriveAbstractBustBounds(positions),
  });
}
