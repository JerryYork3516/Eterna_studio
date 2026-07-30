import type { AbstractBustBlueprint } from "@eterna/shared-schema/abstract-bust-blueprint";

import {
  ABSTRACT_BUST_REGION,
  type AbstractBustPoint,
  type AbstractBustRegionCode,
  type AbstractBustVisualAnchors,
} from "../types.ts";
import { deriveAbstractBustVisualAnchors } from "./anchors.ts";
import {
  F32_PI,
  f32,
  fabs,
  fadd,
  fclamp,
  fcos,
  fdiv,
  fmax,
  fmin,
  fmix,
  fmul,
  fpow,
  fsin,
  fsmoothstep,
  fsoftenedUnit,
  fsqrt,
  fsub,
} from "./float32.ts";
import type { AbstractBustRegionRanges } from "./regions.ts";
import {
  addSalt,
  deterministicSignedUnit,
  hairSalt,
  seededPhase,
} from "./seeded-random.ts";

type MutablePoint = [number, number, number];

const VERTICAL_SAMPLE_JITTER = f32(0.42);
const ANGULAR_JITTER = f32(0.075);
const RADIAL_JITTER = f32(0.012);
const GOLDEN_ANGLE = f32(2.399_963_1);

function addPoints(lhs: AbstractBustPoint, rhs: MutablePoint): MutablePoint {
  return [
    fadd(lhs[0], rhs[0]),
    fadd(lhs[1], rhs[1]),
    fadd(lhs[2], rhs[2]),
  ];
}

function multiplyPoint(point: MutablePoint, scale: number): MutablePoint {
  return [
    fmul(point[0], scale),
    fmul(point[1], scale),
    fmul(point[2], scale),
  ];
}

function copySign(value: number, signSource: number): number {
  const magnitude = fabs(value);
  return signSource < 0 || Object.is(signSource, -0)
    ? fmul(magnitude, -1)
    : magnitude;
}

function stratifiedUnitSample(
  index: number,
  count: number,
  seed: number,
  salt: bigint,
  jitter: number
): number {
  const offset = fmul(
    fmul(deterministicSignedUnit(index, seed, salt), fclamp(jitter)),
    0.5
  );
  return fmin(
    0.999_999,
    fmax(
      0.000_001,
      fdiv(fadd(fadd(f32(index), 0.5), offset), f32(Math.max(count, 1)))
    )
  );
}

function jitteredAngle(
  index: number,
  seed: number,
  salt: bigint,
  phase: number,
  jitter: number
): number {
  return fadd(
    fadd(fmul(GOLDEN_ANGLE, f32(index)), phase),
    fmul(deterministicSignedUnit(index, seed, salt), fmax(0, jitter))
  );
}

function jitteredRadialScale(
  index: number,
  seed: number,
  salt: bigint,
  amount: number
): number {
  return fadd(
    1,
    fmul(deterministicSignedUnit(index, seed, salt), fmax(0, amount))
  );
}

function fibonacciSphere(
  index: number,
  count: number,
  seed: number,
  phase: number
): MutablePoint {
  const unit = stratifiedUnitSample(
    index,
    count,
    seed,
    0x111n,
    VERTICAL_SAMPLE_JITTER
  );
  const y = fsub(1, fmul(2, unit));
  const radius = fmul(
    fsqrt(fmax(0, fsub(1, fmul(y, y)))),
    jitteredRadialScale(index, seed, 0x113n, RADIAL_JITTER)
  );
  const angle = jitteredAngle(
    index,
    seed,
    0x112n,
    phase,
    ANGULAR_JITTER
  );
  return [fmul(fcos(angle), radius), y, fmul(fsin(angle), radius)];
}

function adjustedHeadRoundness(blueprint: AbstractBustBlueprint): number {
  let offset = 0;
  if (blueprint.age_tendency === "youthful") offset = f32(0.08);
  if (blueprint.age_tendency === "mature") offset = f32(-0.06);
  return fmin(1, fmax(0, fadd(blueprint.head.roundness, offset)));
}

function adjustedJawWidth(blueprint: AbstractBustBlueprint): number {
  let offset = 0;
  if (blueprint.age_tendency === "youthful") offset = f32(-0.008);
  if (blueprint.age_tendency === "mature") offset = f32(0.008);
  return fmin(0.25, fmax(0.17, fadd(blueprint.face.jaw.width, offset)));
}

function adjustedNoseLength(blueprint: AbstractBustBlueprint): number {
  let offset = 0;
  if (blueprint.age_tendency === "youthful") offset = f32(-0.006);
  if (blueprint.age_tendency === "mature") offset = f32(0.008);
  return fmin(0.14, fmax(0.075, fadd(blueprint.face.nose.length, offset)));
}

function applyAsymmetry(
  anchor: MutablePoint,
  phase: number,
  blueprint: AbstractBustBlueprint
): MutablePoint {
  const sideScale =
    anchor[0] >= 0
      ? fadd(1, blueprint.contour.asymmetry)
      : fsub(1, blueprint.contour.asymmetry);
  anchor[0] = fmul(anchor[0], sideScale);
  anchor[0] = fadd(
    anchor[0],
    fmul(
      fmul(blueprint.contour.asymmetry, 0.24),
      fsin(fadd(fmul(anchor[1], 3.7), phase))
    )
  );
  return anchor;
}

function headAnchor(
  index: number,
  count: number,
  seed: number,
  phase: number,
  blueprint: AbstractBustBlueprint,
  anchors: AbstractBustVisualAnchors
): MutablePoint {
  const sample = fibonacciSphere(index, count, seed, phase);
  const roundness = fsub(adjustedHeadRoundness(blueprint), 0.5);
  const shapedY = copySign(
    fpow(fabs(sample[1]), fmax(0.75, fsub(1, fmul(roundness, 0.30)))),
    sample[1]
  );
  const middleRoundness = fadd(
    1,
    fmul(fmul(roundness, 0.14), fsub(1, fabs(sample[1])))
  );
  const headDepth = fmul(blueprint.torso.thickness, 0.82);
  const headCenter = anchors.headCenter;
  const anchor = addPoints(headCenter, [
    fmul(fmul(sample[0], blueprint.head.width), middleRoundness),
    fmul(shapedY, blueprint.head.height),
    fmul(fmul(sample[2], headDepth), middleRoundness),
  ]);
  const lowerHead = fmul(fsub(1, shapedY), 0.5);
  const jawBlend = fsmoothstep(
    fmix(0.48, 0.62, blueprint.face.jaw.roundness),
    1,
    lowerHead
  );
  const jawScale = fmix(
    1,
    fmul(
      fdiv(adjustedJawWidth(blueprint), blueprint.head.width),
      fsub(1, fmul(blueprint.face.jaw.taper, 0.18))
    ),
    jawBlend
  );
  anchor[1] = fsub(anchor[1], fmul(blueprint.face.jaw.length, jawBlend));
  const neckBlend = fsmoothstep(fsub(1, 0.22), 1, lowerHead);
  const planarLength = fmax(
    fsqrt(fadd(fmul(sample[0], sample[0]), fmul(sample[2], sample[2]))),
    0.000_01
  );
  const planarX = fdiv(sample[0], planarLength);
  const planarZ = fdiv(sample[2], planarLength);
  anchor[0] = fmul(anchor[0], jawScale);
  anchor[2] = fmul(anchor[2], fmix(1, jawScale, 0.55));
  anchor[0] = fmix(
    anchor[0],
    fadd(headCenter[0], fmul(fmul(planarX, blueprint.neck.width), 0.90)),
    neckBlend
  );
  anchor[2] = fmix(
    anchor[2],
    fmul(fmul(planarZ, blueprint.torso.thickness), 0.46),
    neckBlend
  );
  anchor[0] = fadd(
    anchor[0],
    fmul(
      blueprint.contour.asymmetry,
      fadd(0.22, fmul(0.18, sample[1]))
    )
  );
  return anchor;
}

function eyeAnchor(
  index: number,
  count: number,
  center: AbstractBustPoint,
  blueprint: AbstractBustBlueprint
): MutablePoint {
  const angle = fdiv(
    fmul(fmul(2, F32_PI), fadd(f32(index), 0.5)),
    f32(Math.max(count, 1))
  );
  const localX = fmul(fcos(angle), blueprint.face.eyes.size);
  const localY = fmul(
    fmul(fsin(angle), blueprint.face.eyes.size),
    0.42
  );
  const tilt = blueprint.face.eyes.tilt;
  return addPoints(center, [
    fsub(fmul(localX, fcos(tilt)), fmul(localY, fsin(tilt))),
    fadd(fmul(localX, fsin(tilt)), fmul(localY, fcos(tilt))),
    fmul(
      fmul(fsin(fmul(angle, 2)), blueprint.face.eyes.contour_strength),
      0.004
    ),
  ]);
}

function noseAnchor(
  index: number,
  count: number,
  blueprint: AbstractBustBlueprint,
  anchors: AbstractBustVisualAnchors
): MutablePoint {
  const unit = fdiv(
    fadd(f32(index), 0.5),
    f32(Math.max(count, 1))
  );
  const signedSide = index % 2 === 0 ? -1 : 1;
  const ridge = fsin(fmul(F32_PI, unit));
  return addPoints(anchors.noseCenter, [
    fmul(
      fmul(signedSide, blueprint.face.nose.width),
      fmix(0.12, 0.50, unit)
    ),
    fmul(fsub(0.5, unit), adjustedNoseLength(blueprint)),
    fmul(fmul(ridge, blueprint.face.nose.prominence), 0.55),
  ]);
}

function mouthAnchor(
  index: number,
  count: number,
  blueprint: AbstractBustBlueprint,
  anchors: AbstractBustVisualAnchors
): MutablePoint {
  const horizontal = fsub(
    fdiv(fmul(2, fadd(f32(index), 0.5)), f32(Math.max(count, 1))),
    1
  );
  const arc = fmul(
    fmul(
      fsub(1, fmul(horizontal, horizontal)),
      blueprint.face.mouth.curvature
    ),
    0.035
  );
  return addPoints(anchors.mouthCenter, [
    fmul(fmul(horizontal, blueprint.face.mouth.width), 0.5),
    arc,
    fmul(
      fmul(fsin(fmul(horizontal, F32_PI)), blueprint.face.mouth.contour_strength),
      0.004
    ),
  ]);
}

function cheekAnchor(
  index: number,
  count: number,
  seed: number,
  blueprint: AbstractBustBlueprint,
  anchors: AbstractBustVisualAnchors
): MutablePoint {
  const halfCount = Math.max(1, Math.trunc(count / 2));
  const isLeft = index < halfCount;
  const localIndex = isLeft ? index : index - halfCount;
  const localCount = isLeft ? halfCount : Math.max(1, count - halfCount);
  const center = isLeft ? anchors.cheekLeft : anchors.cheekRight;
  const angle = fdiv(
    fmul(fmul(2, F32_PI), fadd(f32(localIndex), 0.5)),
    f32(localCount)
  );
  const jitter = fmul(
    deterministicSignedUnit(index, seed, 0x661n),
    RADIAL_JITTER
  );
  return addPoints(center, [
    fmul(fcos(angle), 0.045),
    fmul(fsin(angle), 0.032),
    jitter,
  ]);
}

function jawAnchor(
  index: number,
  count: number,
  blueprint: AbstractBustBlueprint,
  anchors: AbstractBustVisualAnchors
): MutablePoint {
  const horizontal = fsub(
    fdiv(fmul(2, fadd(f32(index), 0.5)), f32(Math.max(count, 1))),
    1
  );
  const rounded = fpow(
    fabs(horizontal),
    fmix(1.3, 2.2, blueprint.face.jaw.roundness)
  );
  return addPoints(anchors.chinCenter, [
    fmul(horizontal, adjustedJawWidth(blueprint)),
    fmul(
      rounded,
      fadd(blueprint.face.jaw.length, fmul(blueprint.head.height, 0.08))
    ),
    fmul(
      fmul(blueprint.torso.thickness, 0.10),
      fsub(1, fabs(horizontal))
    ),
  ]);
}

function facialFeatureAnchor(
  index: number,
  count: number,
  seed: number,
  blueprint: AbstractBustBlueprint,
  anchors: AbstractBustVisualAnchors
): MutablePoint {
  const unit = fdiv(f32(index), f32(Math.max(count, 1)));
  if (unit < f32(0.15)) {
    return eyeAnchor(
      index,
      Math.max(1, Math.trunc(fmul(f32(count), 0.15))),
      anchors.eyeLeft,
      blueprint
    );
  }
  if (unit < f32(0.30)) {
    const start = Math.trunc(fmul(f32(count), 0.15));
    return eyeAnchor(
      index - start,
      Math.max(1, Math.trunc(fmul(f32(count), 0.15))),
      anchors.eyeRight,
      blueprint
    );
  }
  if (unit < f32(0.45)) {
    const start = Math.trunc(fmul(f32(count), 0.30));
    return noseAnchor(
      index - start,
      Math.max(1, Math.trunc(fmul(f32(count), 0.15))),
      blueprint,
      anchors
    );
  }
  if (unit < f32(0.60)) {
    const start = Math.trunc(fmul(f32(count), 0.45));
    return mouthAnchor(
      index - start,
      Math.max(1, Math.trunc(fmul(f32(count), 0.15))),
      blueprint,
      anchors
    );
  }
  if (unit < f32(0.80)) {
    const start = Math.trunc(fmul(f32(count), 0.60));
    return cheekAnchor(
      index - start,
      Math.max(1, Math.trunc(fmul(f32(count), 0.20))),
      seed,
      blueprint,
      anchors
    );
  }
  const start = Math.trunc(fmul(f32(count), 0.80));
  return jawAnchor(
    index - start,
    Math.max(1, count - start),
    blueprint,
    anchors
  );
}

function hairBottom(blueprint: AbstractBustBlueprint): number {
  switch (blueprint.hair.style) {
    case "none":
    case "tied":
      return 0;
    case "short":
      return fsub(0.05, fmul(blueprint.hair.length, 0.35));
    case "medium":
      return fsub(-1, fmul(blueprint.hair.length, 0.35));
    case "long":
      return fsub(-1, fmul(blueprint.hair.length, 1.80));
  }
}

function hairSideVolume(blueprint: AbstractBustBlueprint): number {
  switch (blueprint.hair.style) {
    case "none":
    case "tied":
      return 0;
    case "short":
      return f32(0.18);
    case "medium":
      return f32(0.34);
    case "long":
      return f32(0.48);
  }
}

function tiedHairAnchor(
  index: number,
  count: number,
  seed: number,
  blueprint: AbstractBustBlueprint,
  anchors: AbstractBustVisualAnchors
): MutablePoint {
  const gatheredCount = Math.max(1, Math.trunc(fmul(f32(count), 0.28)));
  if (index < count - gatheredCount) {
    const capBlueprint: AbstractBustBlueprint = {
      ...blueprint,
      hair: {
        ...blueprint.hair,
        style: "short",
        length: f32(0.28),
      },
    };
    return hairAnchor(
      index,
      count - gatheredCount,
      seed,
      capBlueprint,
      anchors
    );
  }
  const localIndex = index - (count - gatheredCount);
  const sample = fibonacciSphere(
    localIndex,
    gatheredCount,
    seed,
    seededPhase(seed, 0x556n)
  );
  const volume = fadd(0.07, fmul(blueprint.hair.volume, 0.06));
  const length = fadd(0.10, fmul(blueprint.hair.length, 0.22));
  const headCenter = anchors.headCenter;
  return [
    fadd(headCenter[0], fmul(fmul(sample[0], volume), 0.72)),
    fadd(
      fsub(headCenter[1], fmul(blueprint.head.height, 0.08)),
      fmul(sample[1], length)
    ),
    fadd(
      fmul(fmul(blueprint.torso.thickness, -0.92), 1),
      fmul(sample[2], volume)
    ),
  ];
}

function hairAnchor(
  index: number,
  count: number,
  seed: number,
  blueprint: AbstractBustBlueprint,
  anchors: AbstractBustVisualAnchors
): MutablePoint {
  if (blueprint.hair.style === "tied") {
    return tiedHairAnchor(index, count, seed, blueprint, anchors);
  }
  const salt = hairSalt(blueprint.hair.style);
  const unit = stratifiedUnitSample(
    index,
    count,
    seed,
    salt,
    VERTICAL_SAMPLE_JITTER
  );
  const angle = jitteredAngle(
    index,
    seed,
    addSalt(salt, 1),
    seededPhase(seed, addSalt(salt, 2)),
    ANGULAR_JITTER
  );
  const localY = fmix(
    1,
    hairBottom(blueprint),
    fsoftenedUnit(unit, blueprint.contour.softening)
  );
  const sphereY = fmax(-1, localY);
  const capRadius = fsqrt(fmax(0, fsub(1, fmul(sphereY, sphereY))));
  const radius = fmax(
    capRadius,
    fmul(hairSideVolume(blueprint), fsmoothstep(0.24, 1, unit))
  );
  const volumeScale = fadd(1.02, fmul(blueprint.hair.volume, 0.16));
  const radialScale = jitteredRadialScale(
    index,
    seed,
    addSalt(salt, 3),
    RADIAL_JITTER
  );
  const headCenter = anchors.headCenter;
  let anchor: MutablePoint = [
    fadd(
      headCenter[0],
      fmul(
        fmul(fmul(fcos(angle), blueprint.head.width), radius),
        volumeScale
      )
    ),
    fadd(headCenter[1], fmul(localY, blueprint.head.height)),
    fmul(
      fmul(
        fmul(fmul(fsin(angle), blueprint.torso.thickness), 0.82),
        radius
      ),
      volumeScale
    ),
  ];
  anchor = multiplyPoint(anchor, radialScale);
  anchor[1] = fadd(anchor[1], fmul(headCenter[1], fsub(1, radialScale)));
  anchor[2] = fsub(
    anchor[2],
    fmul(
      fmul(blueprint.torso.thickness, blueprint.hair.volume),
      0.08
    )
  );
  return applyAsymmetry(anchor, angle, blueprint);
}

function neckAnchor(
  index: number,
  count: number,
  seed: number,
  phase: number,
  blueprint: AbstractBustBlueprint,
  anchors: AbstractBustVisualAnchors
): MutablePoint {
  const unit = stratifiedUnitSample(
    index,
    count,
    seed,
    0x221n,
    VERTICAL_SAMPLE_JITTER
  );
  const softened = fsoftenedUnit(unit, blueprint.contour.softening);
  const angle = jitteredAngle(
    index,
    seed,
    0x222n,
    phase,
    ANGULAR_JITTER
  );
  const radialScale = jitteredRadialScale(
    index,
    seed,
    0x223n,
    RADIAL_JITTER
  );
  const width = fmul(
    fmul(blueprint.neck.width, fmix(0.90, 1.20, softened)),
    radialScale
  );
  const depth = fmul(
    fmul(blueprint.torso.thickness, fmix(0.46, 0.65, softened)),
    radialScale
  );
  const top = fadd(
    fsub(anchors.headCenter[1], blueprint.head.height),
    0.02
  );
  const anchor: MutablePoint = [
    fmul(fcos(angle), width),
    fsub(top, fmul(unit, blueprint.neck.length)),
    fmul(fsin(angle), depth),
  ];
  anchor[0] = fadd(anchor[0], fmul(blueprint.contour.asymmetry, 0.18));
  return anchor;
}

function shouldersAndChestAnchor(
  index: number,
  count: number,
  seed: number,
  phase: number,
  blueprint: AbstractBustBlueprint,
  anchors: AbstractBustVisualAnchors
): MutablePoint {
  const unit = fpow(
    stratifiedUnitSample(
      index,
      count,
      seed,
      0x331n,
      VERTICAL_SAMPLE_JITTER
    ),
    0.82
  );
  const softened = fsoftenedUnit(unit, blueprint.contour.softening);
  const angle = jitteredAngle(
    index,
    seed,
    0x332n,
    phase,
    ANGULAR_JITTER
  );
  const radialScale = jitteredRadialScale(
    index,
    seed,
    0x333n,
    RADIAL_JITTER
  );
  const shoulderRise = fsmoothstep(0, 0.42, softened);
  const chestSettle = fsmoothstep(0.38, 1, softened);
  const chestArc = fmul(fsin(fmul(F32_PI, softened)), 0.075);
  let width = fmul(
    fmix(
      fmul(fmul(blueprint.neck.width, 1.20), 0.96),
      blueprint.shoulders.width,
      shoulderRise
    ),
    fmix(1, 0.90, chestSettle)
  );
  width = fmul(
    width,
    fmul(fadd(1, fmul(chestArc, 0.35)), radialScale)
  );
  const depth = fmul(
    fmul(
      fmul(
        fmul(
          blueprint.torso.thickness,
          fmix(0.62, 1.02, shoulderRise)
        ),
        fmix(1, 0.96, chestSettle)
      ),
      fadd(1, chestArc)
    ),
    radialScale
  );
  const normalizedX = fcos(angle);
  const outerShoulderDrop = fmul(
    fmul(
      fmul(
        blueprint.shoulders.slope,
        fpow(fabs(normalizedX), 1.7)
      ),
      fsub(1, chestSettle)
    ),
    1
  );
  const top = fadd(
    fsub(
      fsub(anchors.headCenter[1], blueprint.head.height),
      blueprint.neck.length
    ),
    0.08
  );
  const anchor: MutablePoint = [
    fmul(normalizedX, width),
    fsub(fsub(top, fmul(unit, 0.47)), outerShoulderDrop),
    fmul(fsin(angle), depth),
  ];
  anchor[2] = fadd(
    anchor[2],
    fmul(
      fmul(
        fmul(fmax(0, fsin(angle)), fsin(fmul(F32_PI, softened))),
        blueprint.torso.thickness
      ),
      0.08
    )
  );
  return applyAsymmetry(anchor, phase, blueprint);
}

function torsoAnchor(
  index: number,
  count: number,
  seed: number,
  phase: number,
  blueprint: AbstractBustBlueprint,
  anchors: AbstractBustVisualAnchors
): MutablePoint {
  const unit = fpow(
    stratifiedUnitSample(
      index,
      count,
      seed,
      0x441n,
      VERTICAL_SAMPLE_JITTER
    ),
    1.10
  );
  const softened = fsoftenedUnit(unit, blueprint.contour.softening);
  const angle = jitteredAngle(
    index,
    seed,
    0x442n,
    phase,
    ANGULAR_JITTER
  );
  const radialScale = jitteredRadialScale(
    index,
    seed,
    0x443n,
    RADIAL_JITTER
  );
  const chestArc = fmul(fsin(fmul(F32_PI, softened)), 0.075);
  const width = fmul(
    fmul(
      fmul(
        blueprint.torso.width,
        fmix(1, fsub(1, blueprint.torso.taper), softened)
      ),
      fadd(1, fmul(chestArc, 0.45))
    ),
    radialScale
  );
  const depth = fmul(
    fmul(
      fmul(
        blueprint.torso.thickness,
        fmix(0.96, 0.72, softened)
      ),
      fadd(1, fmul(chestArc, 0.55))
    ),
    radialScale
  );
  const top = fsub(
    fsub(
      fsub(anchors.headCenter[1], blueprint.head.height),
      blueprint.neck.length
    ),
    0.39
  );
  const anchor: MutablePoint = [
    fmul(fcos(angle), width),
    fsub(top, fmul(unit, blueprint.torso.length)),
    fmul(fsin(angle), depth),
  ];
  return applyAsymmetry(anchor, phase, blueprint);
}

function anchorForRegion(
  region: AbstractBustRegionCode,
  index: number,
  count: number,
  seed: number,
  blueprint: AbstractBustBlueprint,
  anchors: AbstractBustVisualAnchors
): MutablePoint {
  switch (region) {
    case ABSTRACT_BUST_REGION.head:
      return headAnchor(
        index,
        count,
        seed,
        seededPhase(seed, 0x11n),
        blueprint,
        anchors
      );
    case ABSTRACT_BUST_REGION.facialFeatures:
      return facialFeatureAnchor(index, count, seed, blueprint, anchors);
    case ABSTRACT_BUST_REGION.hair:
      return hairAnchor(index, count, seed, blueprint, anchors);
    case ABSTRACT_BUST_REGION.neck:
      return neckAnchor(
        index,
        count,
        seed,
        seededPhase(seed, 0x22n),
        blueprint,
        anchors
      );
    case ABSTRACT_BUST_REGION.shouldersAndChest:
      return shouldersAndChestAnchor(
        index,
        count,
        seed,
        seededPhase(seed, 0x33n),
        blueprint,
        anchors
      );
    case ABSTRACT_BUST_REGION.torso:
      return torsoAnchor(
        index,
        count,
        seed,
        seededPhase(seed, 0x44n),
        blueprint,
        anchors
      );
  }
}

export function writeAbstractBustPositions(
  blueprint: AbstractBustBlueprint,
  ranges: AbstractBustRegionRanges,
  output: Float32Array
): AbstractBustVisualAnchors {
  const anchors = deriveAbstractBustVisualAnchors(blueprint);
  for (const range of ranges) {
    const localCount = range.end - range.start;
    for (let globalIndex = range.start; globalIndex < range.end; globalIndex += 1) {
      const anchor = anchorForRegion(
        range.code,
        globalIndex - range.start,
        localCount,
        blueprint.seed,
        blueprint,
        anchors
      );
      const offset = globalIndex * 3;
      output[offset] = anchor[0];
      output[offset + 1] = anchor[1];
      output[offset + 2] = anchor[2];
    }
  }
  return anchors;
}
