import type { AbstractBustBlueprintV2 } from "@eterna/shared-schema/abstract-bust-blueprint-v2";

import { f32, fadd, fmul } from "./float32.ts";

type SemanticWeights = Readonly<{
  headWidth: number;
  headHeight: number;
  headDepth: number;
  headRoundnessOffset: number;
  eyeSpacing: number;
  eyeSize: number;
  noseLength: number;
  noseProminence: number;
  mouthWidth: number;
  cheekWidth: number;
  cheekProminence: number;
  jawWidth: number;
  jawTaper: number;
  jawLength: number;
  jawRoundnessOffset: number;
  neckWidth: number;
  neckLength: number;
  shoulderWidth: number;
  shoulderSlope: number;
  torsoWidth: number;
  torsoThickness: number;
  torsoTaper: number;
}>;

const IDENTITY_WEIGHTS: SemanticWeights = Object.freeze({
  headWidth: 1,
  headHeight: 1,
  headDepth: 1,
  headRoundnessOffset: 0,
  eyeSpacing: 1,
  eyeSize: 1,
  noseLength: 1,
  noseProminence: 1,
  mouthWidth: 1,
  cheekWidth: 1,
  cheekProminence: 1,
  jawWidth: 1,
  jawTaper: 1,
  jawLength: 1,
  jawRoundnessOffset: 0,
  neckWidth: 1,
  neckLength: 1,
  shoulderWidth: 1,
  shoulderSlope: 1,
  torsoWidth: 1,
  torsoThickness: 1,
  torsoTaper: 1,
});

// These algorithm constants are deliberately small and contain only Float32
// multipliers/offsets so the Aftelle Swift adapter can port them literally.
export const ABSTRACT_BUST_V2_PRESENTATION_WEIGHTS = Object.freeze({
  neutral: IDENTITY_WEIGHTS,
  feminine: Object.freeze({
    ...IDENTITY_WEIGHTS,
    headWidth: 0.985,
    headHeight: 1.01,
    headDepth: 0.985,
    cheekWidth: 0.98,
    cheekProminence: 1.06,
    jawWidth: 0.96,
    jawTaper: 1.08,
    jawLength: 0.96,
    jawRoundnessOffset: 0.05,
    neckWidth: 0.96,
    neckLength: 0.98,
    shoulderWidth: 0.97,
    shoulderSlope: 1.05,
    torsoWidth: 0.98,
    torsoThickness: 0.98,
    torsoTaper: 1.03,
  }),
  masculine: Object.freeze({
    ...IDENTITY_WEIGHTS,
    headWidth: 1.015,
    headHeight: 0.995,
    headDepth: 1.02,
    cheekWidth: 1.02,
    cheekProminence: 1.08,
    jawWidth: 1.05,
    jawTaper: 0.92,
    jawLength: 1.06,
    jawRoundnessOffset: -0.05,
    neckWidth: 1.05,
    neckLength: 1.02,
    shoulderWidth: 1.04,
    shoulderSlope: 0.95,
    torsoWidth: 1.03,
    torsoThickness: 1.02,
    torsoTaper: 0.97,
  }),
} satisfies Record<
  AbstractBustBlueprintV2["presentation"],
  SemanticWeights
>);

export const ABSTRACT_BUST_V2_AGE_WEIGHTS = Object.freeze({
  youthful: Object.freeze({
    ...IDENTITY_WEIGHTS,
    headWidth: 1.01,
    headHeight: 1.015,
    headDepth: 0.985,
    headRoundnessOffset: 0.06,
    eyeSpacing: 0.99,
    eyeSize: 1.04,
    noseLength: 0.96,
    noseProminence: 0.94,
    mouthWidth: 1.02,
    cheekWidth: 0.98,
    cheekProminence: 0.90,
    jawWidth: 0.97,
    jawTaper: 1.08,
    jawLength: 0.92,
    jawRoundnessOffset: 0.06,
    neckWidth: 0.98,
    neckLength: 0.97,
    shoulderWidth: 0.99,
    shoulderSlope: 1.03,
    torsoWidth: 0.99,
    torsoThickness: 0.99,
    torsoTaper: 1.01,
  }),
  balanced: IDENTITY_WEIGHTS,
  mature: Object.freeze({
    ...IDENTITY_WEIGHTS,
    headWidth: 1.005,
    headHeight: 0.99,
    headDepth: 1.02,
    headRoundnessOffset: -0.06,
    eyeSpacing: 1.01,
    eyeSize: 0.97,
    noseLength: 1.05,
    noseProminence: 1.06,
    mouthWidth: 0.98,
    cheekWidth: 1.03,
    cheekProminence: 1.12,
    jawWidth: 1.04,
    jawTaper: 0.92,
    jawLength: 1.10,
    jawRoundnessOffset: -0.07,
    neckWidth: 1.04,
    neckLength: 1.03,
    shoulderWidth: 1.02,
    shoulderSlope: 0.97,
    torsoWidth: 1.02,
    torsoThickness: 1.02,
    torsoTaper: 0.99,
  }),
} satisfies Record<
  AbstractBustBlueprintV2["age_tendency"],
  SemanticWeights
>);

function combinedScale(
  presentation: SemanticWeights,
  age: SemanticWeights,
  key: keyof SemanticWeights
): number {
  return fmul(presentation[key], age[key]);
}

function scaled(
  value: number,
  presentation: SemanticWeights,
  age: SemanticWeights,
  key: keyof SemanticWeights
): number {
  return fmul(value, combinedScale(presentation, age, key));
}

export function applyAbstractBustV2SemanticWeights(
  blueprint: AbstractBustBlueprintV2
): AbstractBustBlueprintV2 {
  const presentation =
    ABSTRACT_BUST_V2_PRESENTATION_WEIGHTS[blueprint.presentation];
  const age = ABSTRACT_BUST_V2_AGE_WEIGHTS[blueprint.age_tendency];
  return {
    ...blueprint,
    head: {
      width: scaled(blueprint.head.width, presentation, age, "headWidth"),
      height: scaled(
        blueprint.head.height,
        presentation,
        age,
        "headHeight"
      ),
      depth: scaled(blueprint.head.depth, presentation, age, "headDepth"),
      roundness: fadd(
        fadd(
          blueprint.head.roundness,
          presentation.headRoundnessOffset
        ),
        age.headRoundnessOffset
      ),
    },
    face: {
      eyes: {
        ...blueprint.face.eyes,
        spacing: scaled(
          blueprint.face.eyes.spacing,
          presentation,
          age,
          "eyeSpacing"
        ),
        size: scaled(
          blueprint.face.eyes.size,
          presentation,
          age,
          "eyeSize"
        ),
      },
      nose: {
        ...blueprint.face.nose,
        length: scaled(
          blueprint.face.nose.length,
          presentation,
          age,
          "noseLength"
        ),
        prominence: scaled(
          blueprint.face.nose.prominence,
          presentation,
          age,
          "noseProminence"
        ),
      },
      mouth: {
        ...blueprint.face.mouth,
        width: scaled(
          blueprint.face.mouth.width,
          presentation,
          age,
          "mouthWidth"
        ),
      },
      cheeks: {
        ...blueprint.face.cheeks,
        width: scaled(
          blueprint.face.cheeks.width,
          presentation,
          age,
          "cheekWidth"
        ),
        prominence: scaled(
          blueprint.face.cheeks.prominence,
          presentation,
          age,
          "cheekProminence"
        ),
      },
      jaw: {
        ...blueprint.face.jaw,
        width: scaled(
          blueprint.face.jaw.width,
          presentation,
          age,
          "jawWidth"
        ),
        taper: scaled(
          blueprint.face.jaw.taper,
          presentation,
          age,
          "jawTaper"
        ),
        length: scaled(
          blueprint.face.jaw.length,
          presentation,
          age,
          "jawLength"
        ),
        roundness: fadd(
          fadd(
            blueprint.face.jaw.roundness,
            presentation.jawRoundnessOffset
          ),
          age.jawRoundnessOffset
        ),
      },
    },
    neck: {
      width: scaled(
        blueprint.neck.width,
        presentation,
        age,
        "neckWidth"
      ),
      length: scaled(
        blueprint.neck.length,
        presentation,
        age,
        "neckLength"
      ),
    },
    shoulders: {
      width: scaled(
        blueprint.shoulders.width,
        presentation,
        age,
        "shoulderWidth"
      ),
      slope: scaled(
        blueprint.shoulders.slope,
        presentation,
        age,
        "shoulderSlope"
      ),
    },
    torso: {
      ...blueprint.torso,
      width: scaled(
        blueprint.torso.width,
        presentation,
        age,
        "torsoWidth"
      ),
      thickness: scaled(
        blueprint.torso.thickness,
        presentation,
        age,
        "torsoThickness"
      ),
      taper: scaled(
        blueprint.torso.taper,
        presentation,
        age,
        "torsoTaper"
      ),
    },
  };
}
