import type { AbstractBustBlueprint } from "@eterna/shared-schema/abstract-bust-blueprint";

import type {
  AbstractBustPoint,
  AbstractBustVisualAnchors,
} from "../types.ts";
import {
  f32,
  fadd,
  fmax,
  fmix,
  fmul,
  fpoint,
  fsub,
} from "./float32.ts";

function point(
  centerX: number,
  xOffset: number,
  y: number,
  z: number
): AbstractBustPoint {
  return fpoint(fadd(centerX, xOffset), y, z);
}

export function deriveAbstractBustVisualAnchors(
  blueprint: AbstractBustBlueprint
): AbstractBustVisualAnchors {
  const centerX = fmul(blueprint.contour.asymmetry, 0.30);
  const headCenter = fpoint(centerX, 0.59, 0);
  const headDepth = fmul(blueprint.torso.thickness, 0.82);
  const neckBaseY = fsub(
    fsub(headCenter[1], blueprint.head.height),
    blueprint.neck.length
  );
  const neckBase = fpoint(centerX, neckBaseY, 0);
  const shoulderY = fsub(fadd(neckBaseY, 0.08), blueprint.shoulders.slope);

  let cheekProminence = 0;
  let noseLengthOffset = 0;
  let chinLengthOffset = 0;
  switch (blueprint.age_tendency) {
    case "youthful":
      cheekProminence = f32(-0.003);
      noseLengthOffset = f32(-0.006);
      chinLengthOffset = f32(-0.003);
      break;
    case "balanced":
      break;
    case "mature":
      cheekProminence = f32(0.006);
      noseLengthOffset = f32(0.008);
      chinLengthOffset = f32(0.004);
      break;
  }

  const eyeY = fadd(
    headCenter[1],
    fmul(blueprint.face.eyes.vertical_position, blueprint.head.height)
  );
  const cheekY = fadd(
    headCenter[1],
    fmul(blueprint.face.cheeks.vertical_position, blueprint.head.height)
  );
  const eyeZ = fmul(
    headDepth,
    fadd(0.88, fmul(blueprint.face.eyes.contour_strength, 0.06))
  );
  const cheekZ = fadd(
    fmul(headDepth, 0.82),
    fmax(0, fadd(blueprint.face.cheeks.prominence, cheekProminence))
  );

  return Object.freeze({
    headCenter,
    headTop: point(centerX, 0, fadd(headCenter[1], blueprint.head.height), 0),
    neckBase,
    shoulderLeft: point(
      centerX,
      fmul(blueprint.shoulders.width, -1),
      shoulderY,
      0
    ),
    shoulderRight: point(
      centerX,
      blueprint.shoulders.width,
      fadd(shoulderY, fmul(blueprint.contour.asymmetry, 0.30)),
      0
    ),
    chestCenter: point(
      centerX,
      0,
      fsub(neckBaseY, 0.20),
      fmul(blueprint.torso.thickness, 0.08)
    ),
    torsoCenter: point(
      centerX,
      0,
      fsub(
        fsub(
          fsub(
            fsub(headCenter[1], blueprint.head.height),
            blueprint.neck.length
          ),
          0.39
        ),
        fmul(blueprint.torso.length, 0.5)
      ),
      0
    ),
    eyeLeft: point(
      centerX,
      fmul(fmul(blueprint.face.eyes.spacing, 0.5), -1),
      eyeY,
      eyeZ
    ),
    eyeRight: point(
      centerX,
      fmul(blueprint.face.eyes.spacing, 0.5),
      eyeY,
      eyeZ
    ),
    noseCenter: point(
      centerX,
      0,
      fsub(
        fadd(
          headCenter[1],
          fmul(blueprint.face.nose.vertical_position, blueprint.head.height)
        ),
        fmul(noseLengthOffset, 0.15)
      ),
      fadd(
        fmul(headDepth, 0.90),
        fmul(blueprint.face.nose.prominence, 0.45)
      )
    ),
    mouthCenter: point(
      centerX,
      0,
      fadd(
        headCenter[1],
        fmul(blueprint.face.mouth.vertical_position, blueprint.head.height)
      ),
      fadd(
        fmul(headDepth, 0.88),
        fmul(blueprint.face.mouth.contour_strength, 0.004)
      )
    ),
    cheekLeft: point(
      centerX,
      fmul(fmul(blueprint.face.cheeks.width, 0.5), -1),
      cheekY,
      cheekZ
    ),
    cheekRight: point(
      centerX,
      fmul(blueprint.face.cheeks.width, 0.5),
      cheekY,
      cheekZ
    ),
    chinCenter: point(
      centerX,
      0,
      fsub(
        fsub(fsub(headCenter[1], blueprint.head.height), blueprint.face.jaw.length),
        chinLengthOffset
      ),
      fmul(headDepth, 0.18)
    ),
  });
}
