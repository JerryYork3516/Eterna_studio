import type { AbstractBustBlueprintV2 } from "@eterna/shared-schema/abstract-bust-blueprint-v2";

import type {
  AbstractBustV2DerivedAnchors,
  AbstractBustV2Point,
} from "../types.ts";
import {
  f32,
  fabs,
  fadd,
  fmix,
  fmul,
  fpoint,
  fsmoothstep,
  fsub,
} from "./float32.ts";

export const ABSTRACT_BUST_V2_HEAD_CENTER_Y = f32(0.52);

export function abstractBustV2CenterX(
  blueprint: AbstractBustBlueprintV2
): number {
  return fmul(blueprint.contour.asymmetry, 0.25);
}

export function abstractBustV2HeadFrontDepth(
  blueprint: AbstractBustBlueprintV2,
  normalizedY: number
): number {
  const crown = fsmoothstep(0.25, 0.90, normalizedY);
  const lowerUnit = fmul(fsub(1, normalizedY), 0.5);
  const lower = fsmoothstep(0.55, 0.96, lowerUnit);
  const middle = fsub(1, fabs(normalizedY));
  const profile = fsub(
    fadd(
      fadd(0.90, fmul(crown, 0.06)),
      fmul(middle, 0.03)
    ),
    fmul(lower, 0.10)
  );
  return fmul(blueprint.head.depth, profile);
}

function pointWithCenter(
  centerX: number,
  x: number,
  y: number,
  z: number
): AbstractBustV2Point {
  return fpoint(fadd(centerX, x), y, z);
}

export function deriveAbstractBustV2Anchors(
  blueprint: AbstractBustBlueprintV2
): AbstractBustV2DerivedAnchors {
  const centerX = abstractBustV2CenterX(blueprint);
  const headCenter = fpoint(centerX, ABSTRACT_BUST_V2_HEAD_CENTER_Y, 0);
  const headBottomY = fsub(
    ABSTRACT_BUST_V2_HEAD_CENTER_Y,
    blueprint.head.height
  );
  const neckTopY = fadd(headBottomY, 0.045);
  const neckBaseY = fsub(neckTopY, blueprint.neck.length);
  const shoulderY = fsub(fadd(neckBaseY, 0.015), blueprint.shoulders.slope);
  const chestY = fsub(neckBaseY, 0.16);
  const torsoCenterY = fsub(
    fsub(neckBaseY, 0.18),
    fmul(blueprint.torso.length, 0.45)
  );

  const eyeY = fadd(
    ABSTRACT_BUST_V2_HEAD_CENTER_Y,
    fmul(blueprint.face.eyes.vertical_position, blueprint.head.height)
  );
  const eyeNormalizedY = fdivByHeight(
    eyeY,
    ABSTRACT_BUST_V2_HEAD_CENTER_Y,
    blueprint.head.height
  );
  const eyeZ = fsub(
    abstractBustV2HeadFrontDepth(blueprint, eyeNormalizedY),
    fmul(blueprint.face.eyes.contour_strength, 0.006)
  );

  const noseY = fsub(
    fadd(
      ABSTRACT_BUST_V2_HEAD_CENTER_Y,
      fmul(blueprint.face.nose.vertical_position, blueprint.head.height)
    ),
    fmul(blueprint.face.nose.length, 0.12)
  );
  const noseNormalizedY = fdivByHeight(
    noseY,
    ABSTRACT_BUST_V2_HEAD_CENTER_Y,
    blueprint.head.height
  );
  const noseZ = fadd(
    abstractBustV2HeadFrontDepth(blueprint, noseNormalizedY),
    fmul(blueprint.face.nose.prominence, 0.65)
  );

  const mouthY = fadd(
    fadd(
      ABSTRACT_BUST_V2_HEAD_CENTER_Y,
      fmul(blueprint.face.mouth.vertical_position, blueprint.head.height)
    ),
    fmul(blueprint.face.mouth.curvature, 0.012)
  );
  const mouthNormalizedY = fdivByHeight(
    mouthY,
    ABSTRACT_BUST_V2_HEAD_CENTER_Y,
    blueprint.head.height
  );
  const mouthZ = fsub(
    abstractBustV2HeadFrontDepth(blueprint, mouthNormalizedY),
    fmul(blueprint.face.mouth.contour_strength, 0.005)
  );

  const cheekY = fadd(
    ABSTRACT_BUST_V2_HEAD_CENTER_Y,
    fmul(blueprint.face.cheeks.vertical_position, blueprint.head.height)
  );
  const cheekNormalizedY = fdivByHeight(
    cheekY,
    ABSTRACT_BUST_V2_HEAD_CENTER_Y,
    blueprint.head.height
  );
  const cheekZ = fadd(
    abstractBustV2HeadFrontDepth(blueprint, cheekNormalizedY),
    fmul(blueprint.face.cheeks.prominence, 0.50)
  );

  return Object.freeze({
    headTop: pointWithCenter(
      centerX,
      0,
      fadd(ABSTRACT_BUST_V2_HEAD_CENTER_Y, blueprint.head.height),
      0
    ),
    headCenter,
    neckBase: pointWithCenter(centerX, 0, neckBaseY, 0),
    shoulderLeft: pointWithCenter(
      centerX,
      fmul(blueprint.shoulders.width, -1),
      shoulderY,
      0
    ),
    shoulderRight: pointWithCenter(
      centerX,
      blueprint.shoulders.width,
      fadd(
        shoulderY,
        fmul(blueprint.contour.asymmetry, 0.25)
      ),
      0
    ),
    chestCenter: pointWithCenter(
      centerX,
      0,
      chestY,
      fmul(blueprint.torso.thickness, 0.12)
    ),
    torsoCenter: pointWithCenter(centerX, 0, torsoCenterY, 0),
    eyeLeft: pointWithCenter(
      centerX,
      fmul(blueprint.face.eyes.spacing, -0.5),
      eyeY,
      eyeZ
    ),
    eyeRight: pointWithCenter(
      centerX,
      fmul(blueprint.face.eyes.spacing, 0.5),
      eyeY,
      eyeZ
    ),
    nose: pointWithCenter(centerX, 0, noseY, noseZ),
    mouth: pointWithCenter(centerX, 0, mouthY, mouthZ),
    cheekLeft: pointWithCenter(
      centerX,
      fmul(blueprint.face.cheeks.width, -0.5),
      cheekY,
      cheekZ
    ),
    cheekRight: pointWithCenter(
      centerX,
      fmul(blueprint.face.cheeks.width, 0.5),
      cheekY,
      cheekZ
    ),
    chin: pointWithCenter(
      centerX,
      0,
      fsub(headBottomY, fmul(blueprint.face.jaw.length, 0.65)),
      fmul(
        abstractBustV2HeadFrontDepth(blueprint, -1),
        fmix(0.40, 0.62, blueprint.face.jaw.roundness)
      )
    ),
  });
}

function fdivByHeight(
  value: number,
  center: number,
  height: number
): number {
  return f32((f32(value) - f32(center)) / f32(height));
}
