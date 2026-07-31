import type { AbstractBustBlueprintV2 } from "@eterna/shared-schema/abstract-bust-blueprint-v2";

import {
  ABSTRACT_BUST_V2_REGION,
  type AbstractBustV2DerivedAnchors,
  type AbstractBustV2Point,
  type AbstractBustV2RegionCode,
} from "../types.ts";
import {
  ABSTRACT_BUST_V2_HEAD_CENTER_Y,
  abstractBustV2CenterX,
  abstractBustV2HeadFrontDepth,
  deriveAbstractBustV2Anchors,
} from "./anchors.ts";
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
import {
  ABSTRACT_BUST_V2_FEATURE,
  deriveAbstractBustV2FeatureRanges,
  type AbstractBustV2FeatureCode,
  type AbstractBustV2FeatureRange,
  type AbstractBustV2RegionRanges,
} from "./regions.ts";
import {
  deterministicPhaseV2,
  deterministicSignedUnitV2,
} from "./seeded-random.ts";

type MutablePoint = [number, number, number];

const GOLDEN_ANGLE = f32(2.399_963_1);
const VERTICAL_JITTER = f32(0.38);
const ANGULAR_JITTER = f32(0.065);
const RADIAL_JITTER = f32(0.009);

function copySign(value: number, signSource: number): number {
  const magnitude = fabs(value);
  return signSource < 0 || Object.is(signSource, -0)
    ? fmul(magnitude, -1)
    : magnitude;
}

function addPoint(
  center: AbstractBustV2Point,
  x: number,
  y: number,
  z: number
): MutablePoint {
  return [
    fadd(center[0], x),
    fadd(center[1], y),
    fadd(center[2], z),
  ];
}

function sampleUnit(
  localIndex: number,
  count: number,
  globalIndex: number,
  region: AbstractBustV2RegionCode,
  seed: number,
  salt: bigint
): number {
  const jitter = fmul(
    deterministicSignedUnitV2(globalIndex, region, seed, salt),
    VERTICAL_JITTER
  );
  return fmin(
    0.999_999,
    fmax(
      0.000_001,
      fdiv(
        fadd(fadd(localIndex, 0.5), fmul(jitter, 0.5)),
        Math.max(count, 1)
      )
    )
  );
}

function sampleAngle(
  localIndex: number,
  globalIndex: number,
  region: AbstractBustV2RegionCode,
  seed: number,
  salt: bigint
): number {
  return fadd(
    fadd(
      fmul(GOLDEN_ANGLE, localIndex),
      deterministicPhaseV2(region, seed, salt + 1n)
    ),
    fmul(
      deterministicSignedUnitV2(
        globalIndex,
        region,
        seed,
        salt + 2n
      ),
      ANGULAR_JITTER
    )
  );
}

function radialScale(
  globalIndex: number,
  region: AbstractBustV2RegionCode,
  seed: number,
  salt: bigint
): number {
  return fadd(
    1,
    fmul(
      deterministicSignedUnitV2(globalIndex, region, seed, salt),
      RADIAL_JITTER
    )
  );
}

function fibonacciSample(
  localIndex: number,
  count: number,
  globalIndex: number,
  region: AbstractBustV2RegionCode,
  seed: number,
  salt: bigint
): MutablePoint {
  const unit = sampleUnit(
    localIndex,
    count,
    globalIndex,
    region,
    seed,
    salt
  );
  const y = fsub(1, fmul(2, unit));
  const planar = fsqrt(fmax(0, fsub(1, fmul(y, y))));
  const angle = sampleAngle(
    localIndex,
    globalIndex,
    region,
    seed,
    salt
  );
  return [fmul(fcos(angle), planar), y, fmul(fsin(angle), planar)];
}

function applyAsymmetry(
  point: MutablePoint,
  blueprint: AbstractBustBlueprintV2,
  phase: number
): MutablePoint {
  const centerX = abstractBustV2CenterX(blueprint);
  const relativeX = fsub(point[0], centerX);
  const sideScale =
    relativeX >= 0
      ? fadd(1, blueprint.contour.asymmetry)
      : fsub(1, blueprint.contour.asymmetry);
  point[0] = fadd(centerX, fmul(relativeX, sideScale));
  point[0] = fadd(
    point[0],
    fmul(
      fmul(blueprint.contour.asymmetry, 0.18),
      fsin(fadd(fmul(point[1], 3.4), phase))
    )
  );
  return point;
}

function shapeHeadSample(
  sample: MutablePoint,
  blueprint: AbstractBustBlueprintV2,
  anchors: AbstractBustV2DerivedAnchors
): MutablePoint {
  const roundnessExponent = fmix(
    1.10,
    0.90,
    blueprint.head.roundness
  );
  const shapedY = copySign(
    fpow(fabs(sample[1]), roundnessExponent),
    sample[1]
  );
  const crown = fsmoothstep(0.28, 0.92, shapedY);
  const lowerUnit = fmul(fsub(1, shapedY), 0.5);
  const lower = fsmoothstep(0.53, 0.97, lowerUnit);
  const middle = fsub(1, fabs(shapedY));
  const crownScale = fmix(1, 0.84, crown);
  const roundnessScale = fadd(
    1,
    fmul(fsub(blueprint.head.roundness, 0.5), fmul(middle, 0.12))
  );
  const jawRatio = fmul(
    fdiv(blueprint.face.jaw.width, blueprint.head.width),
    fsub(1, fmul(blueprint.face.jaw.taper, 0.25))
  );
  const jawScale = fmix(1, jawRatio, lower);
  const x = fmul(
    fmul(
      fmul(sample[0], blueprint.head.width),
      crownScale
    ),
    fmul(roundnessScale, jawScale)
  );

  const frontProfile = fdiv(
    abstractBustV2HeadFrontDepth(blueprint, shapedY),
    blueprint.head.depth
  );
  const backProfile = fsub(
    fadd(
      fadd(0.96, fmul(crown, 0.10)),
      fmul(middle, 0.08)
    ),
    fmul(lower, 0.04)
  );
  const depthProfile = sample[2] >= 0 ? frontProfile : backProfile;
  const z = fmul(
    fmul(sample[2], blueprint.head.depth),
    fmul(depthProfile, fmix(1, jawScale, 0.42))
  );
  const y = fsub(
    fadd(
      anchors.headCenter[1],
      fmul(shapedY, blueprint.head.height)
    ),
    fmul(blueprint.face.jaw.length, lower)
  );

  const neckBlend = fsmoothstep(0.86, 1, lowerUnit);
  const planarLength = fmax(
    fsqrt(fadd(fmul(sample[0], sample[0]), fmul(sample[2], sample[2]))),
    0.000_01
  );
  const neckX = fadd(
    anchors.headCenter[0],
    fmul(
      fmul(fdiv(sample[0], planarLength), blueprint.neck.width),
      0.88
    )
  );
  const neckZ = fmul(
    fmul(fdiv(sample[2], planarLength), blueprint.head.depth),
    0.44
  );
  return [
    fmix(fadd(anchors.headCenter[0], x), neckX, neckBlend),
    y,
    fmix(z, neckZ, neckBlend),
  ];
}

function headPoint(
  localIndex: number,
  count: number,
  globalIndex: number,
  blueprint: AbstractBustBlueprintV2,
  anchors: AbstractBustV2DerivedAnchors
): MutablePoint {
  const sample = fibonacciSample(
    localIndex,
    count,
    globalIndex,
    ABSTRACT_BUST_V2_REGION.head,
    blueprint.seed,
    0x110n
  );
  return applyAsymmetry(
    shapeHeadSample(sample, blueprint, anchors),
    blueprint,
    deterministicPhaseV2(
      ABSTRACT_BUST_V2_REGION.head,
      blueprint.seed,
      0x119n
    )
  );
}

function eyePoint(
  localIndex: number,
  count: number,
  globalIndex: number,
  center: AbstractBustV2Point,
  blueprint: AbstractBustBlueprintV2
): MutablePoint {
  const unit = sampleUnit(
    localIndex,
    count,
    globalIndex,
    ABSTRACT_BUST_V2_REGION.facialFeatures,
    blueprint.seed,
    0x210n
  );
  const angle = fmul(fmul(2, F32_PI), unit);
  const x = fmul(fcos(angle), blueprint.face.eyes.size);
  const y = fmul(
    fmul(fsin(angle), blueprint.face.eyes.size),
    0.42
  );
  const tilt = blueprint.face.eyes.tilt;
  return addPoint(
    center,
    fsub(fmul(x, fcos(tilt)), fmul(y, fsin(tilt))),
    fadd(fmul(x, fsin(tilt)), fmul(y, fcos(tilt))),
    fmul(
      fmul(
        fsin(fmul(angle, 2)),
        blueprint.face.eyes.contour_strength
      ),
      0.003
    )
  );
}

function nosePoint(
  localIndex: number,
  count: number,
  globalIndex: number,
  blueprint: AbstractBustBlueprintV2,
  anchors: AbstractBustV2DerivedAnchors
): MutablePoint {
  const unit = sampleUnit(
    localIndex,
    count,
    globalIndex,
    ABSTRACT_BUST_V2_REGION.facialFeatures,
    blueprint.seed,
    0x220n
  );
  const side = localIndex % 2 === 0 ? -1 : 1;
  const ridge = fsin(fmul(F32_PI, unit));
  return addPoint(
    anchors.nose,
    fmul(
      fmul(side, blueprint.face.nose.width),
      fmix(0.10, 0.48, unit)
    ),
    fmul(fsub(0.5, unit), blueprint.face.nose.length),
    fmul(
      fmul(ridge, blueprint.face.nose.prominence),
      fmix(0.25, 0.72, unit)
    )
  );
}

function mouthPoint(
  localIndex: number,
  count: number,
  globalIndex: number,
  blueprint: AbstractBustBlueprintV2,
  anchors: AbstractBustV2DerivedAnchors
): MutablePoint {
  const unit = sampleUnit(
    localIndex,
    count,
    globalIndex,
    ABSTRACT_BUST_V2_REGION.facialFeatures,
    blueprint.seed,
    0x230n
  );
  const horizontal = fsub(fmul(unit, 2), 1);
  const curve = fmul(
    fmul(
      fsub(1, fmul(horizontal, horizontal)),
      blueprint.face.mouth.curvature
    ),
    0.04
  );
  return addPoint(
    anchors.mouth,
    fmul(fmul(horizontal, blueprint.face.mouth.width), 0.5),
    curve,
    fmul(
      fmul(
        fsin(fmul(horizontal, F32_PI)),
        blueprint.face.mouth.contour_strength
      ),
      0.004
    )
  );
}

function cheekPoint(
  localIndex: number,
  count: number,
  globalIndex: number,
  blueprint: AbstractBustBlueprintV2,
  anchors: AbstractBustV2DerivedAnchors
): MutablePoint {
  const leftCount = Math.ceil(count / 2);
  const left = localIndex < leftCount;
  const sideIndex = left ? localIndex : localIndex - leftCount;
  const sideCount = left ? leftCount : Math.max(1, count - leftCount);
  const unit = sampleUnit(
    sideIndex,
    sideCount,
    globalIndex,
    ABSTRACT_BUST_V2_REGION.facialFeatures,
    blueprint.seed,
    0x240n
  );
  const angle = fmul(fmul(2, F32_PI), unit);
  const center = left ? anchors.cheekLeft : anchors.cheekRight;
  return addPoint(
    center,
    fmul(fcos(angle), fmul(blueprint.face.cheeks.width, 0.15)),
    fmul(fsin(angle), 0.032),
    fadd(
      fmul(
        fmul(fsub(1, fabs(fcos(angle))), blueprint.face.cheeks.prominence),
        0.55
      ),
      fmul(
        deterministicSignedUnitV2(
          globalIndex,
          ABSTRACT_BUST_V2_REGION.facialFeatures,
          blueprint.seed,
          0x241n
        ),
        0.003
      )
    )
  );
}

function jawPoint(
  localIndex: number,
  count: number,
  globalIndex: number,
  blueprint: AbstractBustBlueprintV2,
  anchors: AbstractBustV2DerivedAnchors
): MutablePoint {
  const unit = sampleUnit(
    localIndex,
    count,
    globalIndex,
    ABSTRACT_BUST_V2_REGION.facialFeatures,
    blueprint.seed,
    0x250n
  );
  const horizontal = fsub(fmul(unit, 2), 1);
  const rounded = fpow(
    fabs(horizontal),
    fmix(1.25, 2.25, blueprint.face.jaw.roundness)
  );
  const taperScale = fsub(
    1,
    fmul(blueprint.face.jaw.taper, fsub(1, fabs(horizontal)))
  );
  return addPoint(
    anchors.chin,
    fmul(
      fmul(horizontal, blueprint.face.jaw.width),
      taperScale
    ),
    fmul(
      rounded,
      fadd(
        blueprint.face.jaw.length,
        fmul(blueprint.head.height, 0.075)
      )
    ),
    fmul(
      fmul(
        abstractBustV2HeadFrontDepth(blueprint, -0.82),
        fsub(1, fabs(horizontal))
      ),
      fmix(0.06, 0.14, blueprint.face.jaw.roundness)
    )
  );
}

function featurePoint(
  featureRange: AbstractBustV2FeatureRange,
  featureRegionStart: number,
  globalIndex: number,
  blueprint: AbstractBustBlueprintV2,
  anchors: AbstractBustV2DerivedAnchors
): MutablePoint {
  const localIndex = globalIndex - featureRegionStart - featureRange.start;
  const count = featureRange.end - featureRange.start;
  switch (featureRange.code) {
    case ABSTRACT_BUST_V2_FEATURE.eyeLeft:
      return eyePoint(
        localIndex,
        count,
        globalIndex,
        anchors.eyeLeft,
        blueprint
      );
    case ABSTRACT_BUST_V2_FEATURE.eyeRight:
      return eyePoint(
        localIndex,
        count,
        globalIndex,
        anchors.eyeRight,
        blueprint
      );
    case ABSTRACT_BUST_V2_FEATURE.nose:
      return nosePoint(
        localIndex,
        count,
        globalIndex,
        blueprint,
        anchors
      );
    case ABSTRACT_BUST_V2_FEATURE.mouth:
      return mouthPoint(
        localIndex,
        count,
        globalIndex,
        blueprint,
        anchors
      );
    case ABSTRACT_BUST_V2_FEATURE.cheeks:
      return cheekPoint(
        localIndex,
        count,
        globalIndex,
        blueprint,
        anchors
      );
    case ABSTRACT_BUST_V2_FEATURE.jaw:
      return jawPoint(
        localIndex,
        count,
        globalIndex,
        blueprint,
        anchors
      );
  }
}

function scalpSample(
  localIndex: number,
  count: number,
  globalIndex: number,
  blueprint: AbstractBustBlueprintV2
): MutablePoint {
  const unit = sampleUnit(
    localIndex,
    count,
    globalIndex,
    ABSTRACT_BUST_V2_REGION.hairScalp,
    blueprint.seed,
    0x310n
  );
  const y = fmix(1, -0.38, fsoftenedUnit(unit, blueprint.contour.softening));
  const planar = fsqrt(fmax(0, fsub(1, fmul(y, y))));
  const angle = sampleAngle(
    localIndex,
    globalIndex,
    ABSTRACT_BUST_V2_REGION.hairScalp,
    blueprint.seed,
    0x311n
  );
  return [fmul(fcos(angle), planar), y, fmul(fsin(angle), planar)];
}

function hairShellPoint(
  localIndex: number,
  count: number,
  globalIndex: number,
  blueprint: AbstractBustBlueprintV2,
  anchors: AbstractBustV2DerivedAnchors
): MutablePoint {
  const sample = scalpSample(
    localIndex,
    count,
    globalIndex,
    blueprint
  );
  if (blueprint.hair.style === "none") {
    return applyAsymmetry(
      shapeHeadSample(sample, blueprint, anchors),
      blueprint,
      sampleAngle(
        localIndex,
        globalIndex,
        ABSTRACT_BUST_V2_REGION.hairScalp,
        blueprint.seed,
        0x318n
      )
    );
  }

  const base = shapeHeadSample(sample, blueprint, anchors);
  const side = fabs(sample[0]);
  const back = fmax(0, fmul(sample[2], -1));
  const front = fmax(0, sample[2]);
  const volume = blueprint.hair.volume;
  let expansion = fadd(0.018, fmul(volume, 0.035));
  let drop = 0;

  if (blueprint.hair.style === "short") {
    expansion = fadd(expansion, fmul(blueprint.hair.length, 0.012));
  } else if (blueprint.hair.style === "medium") {
    expansion = fadd(expansion, fmul(side, fmul(volume, 0.045)));
    drop = fmul(
      fmul(
        fsmoothstep(0.30, 1, fsub(1, sample[1])),
        blueprint.hair.length
      ),
      fadd(0.08, fmul(side, 0.14))
    );
  } else if (blueprint.hair.style === "long") {
    expansion = fadd(expansion, fmul(side, fmul(volume, 0.065)));
    drop = fmul(
      fmul(
        fsmoothstep(0.20, 1, fsub(1, sample[1])),
        blueprint.hair.length
      ),
      fadd(0.18, fmul(side, 0.32))
    );
  }

  const faceProtection = fmix(1, 0.25, fmul(front, fsmoothstep(-0.05, 0.55, sample[1])));
  const outward = fmul(
    expansion,
    fmul(faceProtection, fadd(0.65, fmul(back, 0.35)))
  );
  const planar = fmax(
    fsqrt(fadd(fmul(sample[0], sample[0]), fmul(sample[2], sample[2]))),
    0.000_01
  );
  base[0] = fadd(base[0], fmul(fdiv(sample[0], planar), outward));
  base[2] = fadd(base[2], fmul(fdiv(sample[2], planar), outward));
  base[1] = fsub(base[1], drop);
  return applyAsymmetry(base, blueprint, sample[1]);
}

function tiedHairPoint(
  localIndex: number,
  count: number,
  globalIndex: number,
  blueprint: AbstractBustBlueprintV2,
  anchors: AbstractBustV2DerivedAnchors
): MutablePoint {
  const gatheredCount = Math.max(1, Math.round(count * 0.28));
  const capCount = count - gatheredCount;
  if (localIndex < capCount) {
    const capBlueprint: AbstractBustBlueprintV2 = {
      ...blueprint,
      hair: {
        ...blueprint.hair,
        style: "short",
        length: f32(0.28),
      },
    };
    return hairShellPoint(
      localIndex,
      capCount,
      globalIndex,
      capBlueprint,
      anchors
    );
  }
  const gatheredIndex = localIndex - capCount;
  const sample = fibonacciSample(
    gatheredIndex,
    gatheredCount,
    globalIndex,
    ABSTRACT_BUST_V2_REGION.hairScalp,
    blueprint.seed,
    0x350n
  );
  const volume = fadd(0.065, fmul(blueprint.hair.volume, 0.055));
  const length = fadd(0.09, fmul(blueprint.hair.length, 0.22));
  return applyAsymmetry(
    [
      fadd(
        anchors.headCenter[0],
        fmul(fmul(sample[0], volume), 0.72)
      ),
      fadd(
        fsub(anchors.headCenter[1], fmul(blueprint.head.height, 0.10)),
        fmul(sample[1], length)
      ),
      fsub(
        fmul(sample[2], volume),
        fadd(blueprint.head.depth, fmul(volume, 0.38))
      ),
    ],
    blueprint,
    sample[1]
  );
}

function hairPoint(
  localIndex: number,
  count: number,
  globalIndex: number,
  blueprint: AbstractBustBlueprintV2,
  anchors: AbstractBustV2DerivedAnchors
): MutablePoint {
  return blueprint.hair.style === "tied"
    ? tiedHairPoint(
        localIndex,
        count,
        globalIndex,
        blueprint,
        anchors
      )
    : hairShellPoint(
        localIndex,
        count,
        globalIndex,
        blueprint,
        anchors
      );
}

function neckPoint(
  localIndex: number,
  count: number,
  globalIndex: number,
  blueprint: AbstractBustBlueprintV2,
  anchors: AbstractBustV2DerivedAnchors
): MutablePoint {
  const unit = sampleUnit(
    localIndex,
    count,
    globalIndex,
    ABSTRACT_BUST_V2_REGION.neck,
    blueprint.seed,
    0x410n
  );
  const softened = fsoftenedUnit(unit, blueprint.contour.softening);
  const angle = sampleAngle(
    localIndex,
    globalIndex,
    ABSTRACT_BUST_V2_REGION.neck,
    blueprint.seed,
    0x411n
  );
  const scale = radialScale(
    globalIndex,
    ABSTRACT_BUST_V2_REGION.neck,
    blueprint.seed,
    0x412n
  );
  const bottomWidth = fmin(
    fmul(blueprint.torso.width, 0.42),
    fmul(blueprint.neck.width, 1.35)
  );
  const width = fmul(
    fmix(fmul(blueprint.neck.width, 0.88), bottomWidth, softened),
    scale
  );
  const depth = fmul(
    fmix(
      fmul(blueprint.head.depth, 0.46),
      fmul(blueprint.torso.thickness, 0.68),
      softened
    ),
    scale
  );
  const headBottomY = fsub(
    ABSTRACT_BUST_V2_HEAD_CENTER_Y,
    blueprint.head.height
  );
  const neckTopY = fadd(headBottomY, 0.045);
  return applyAsymmetry(
    [
      fadd(abstractBustV2CenterX(blueprint), fmul(fcos(angle), width)),
      fsub(neckTopY, fmul(unit, blueprint.neck.length)),
      fmul(fsin(angle), depth),
    ],
    blueprint,
    angle
  );
}

function shouldersAndChestPoint(
  localIndex: number,
  count: number,
  globalIndex: number,
  blueprint: AbstractBustBlueprintV2,
  anchors: AbstractBustV2DerivedAnchors
): MutablePoint {
  const unit = sampleUnit(
    localIndex,
    count,
    globalIndex,
    ABSTRACT_BUST_V2_REGION.shouldersAndChest,
    blueprint.seed,
    0x510n
  );
  const softened = fsoftenedUnit(unit, blueprint.contour.softening);
  const angle = sampleAngle(
    localIndex,
    globalIndex,
    ABSTRACT_BUST_V2_REGION.shouldersAndChest,
    blueprint.seed,
    0x511n
  );
  const scale = radialScale(
    globalIndex,
    ABSTRACT_BUST_V2_REGION.shouldersAndChest,
    blueprint.seed,
    0x512n
  );
  const shoulderBlend = fsmoothstep(0, 0.55, softened);
  const chestBlend = fsmoothstep(0.55, 1, softened);
  const neckBaseWidth = fmin(
    fmul(blueprint.torso.width, 0.42),
    fmul(blueprint.neck.width, 1.35)
  );
  const shoulderWidth = fmix(
    neckBaseWidth,
    blueprint.shoulders.width,
    shoulderBlend
  );
  const width = fmul(
    fmix(
      shoulderWidth,
      fmul(blueprint.torso.width, 0.96),
      chestBlend
    ),
    scale
  );
  const depth = fmul(
    fmix(
      fmul(blueprint.torso.thickness, 0.68),
      blueprint.torso.thickness,
      shoulderBlend
    ),
    fmul(
      fmix(1, 0.92, chestBlend),
      fadd(0.92, fmul(fsin(fmul(F32_PI, softened)), 0.08))
    )
  );
  const normalizedX = fcos(angle);
  const outerDrop = fmul(
    fmul(
      blueprint.shoulders.slope,
      fpow(fabs(normalizedX), 1.6)
    ),
    fsub(1, chestBlend)
  );
  const endRound = fmul(
    fmul(
      fsmoothstep(0.82, 1, fabs(normalizedX)),
      fsub(1, chestBlend)
    ),
    0.035
  );
  const topY = fadd(anchors.neckBase[1], 0.015);
  const point: MutablePoint = [
    fadd(
      abstractBustV2CenterX(blueprint),
      fmul(normalizedX, width)
    ),
    fsub(
      fsub(fsub(topY, fmul(unit, 0.34)), outerDrop),
      endRound
    ),
    fmul(fsin(angle), depth),
  ];
  if (point[2] > 0) {
    point[2] = fadd(
      point[2],
      fmul(
        fmul(
          fsin(fmul(F32_PI, softened)),
          blueprint.torso.thickness
        ),
        0.055
      )
    );
  }
  return applyAsymmetry(point, blueprint, angle);
}

function torsoPoint(
  localIndex: number,
  count: number,
  globalIndex: number,
  blueprint: AbstractBustBlueprintV2,
  anchors: AbstractBustV2DerivedAnchors
): MutablePoint {
  const unit = sampleUnit(
    localIndex,
    count,
    globalIndex,
    ABSTRACT_BUST_V2_REGION.torso,
    blueprint.seed,
    0x610n
  );
  const softened = fsoftenedUnit(unit, blueprint.contour.softening);
  const angle = sampleAngle(
    localIndex,
    globalIndex,
    ABSTRACT_BUST_V2_REGION.torso,
    blueprint.seed,
    0x611n
  );
  const scale = radialScale(
    globalIndex,
    ABSTRACT_BUST_V2_REGION.torso,
    blueprint.seed,
    0x612n
  );
  const chestArc = fmul(fsin(fmul(F32_PI, softened)), 0.07);
  const width = fmul(
    fmul(
      blueprint.torso.width,
      fmix(1, fsub(1, blueprint.torso.taper), softened)
    ),
    fmul(fadd(1, fmul(chestArc, 0.45)), scale)
  );
  const depth = fmul(
    fmul(
      blueprint.torso.thickness,
      fmix(1, 0.72, softened)
    ),
    fmul(fadd(1, fmul(chestArc, 0.55)), scale)
  );
  const topY = fsub(anchors.neckBase[1], 0.21);
  return applyAsymmetry(
    [
      fadd(
        abstractBustV2CenterX(blueprint),
        fmul(fcos(angle), width)
      ),
      fsub(topY, fmul(unit, blueprint.torso.length)),
      fmul(fsin(angle), depth),
    ],
    blueprint,
    angle
  );
}

function findFeatureRange(
  ranges: readonly AbstractBustV2FeatureRange[],
  localIndex: number
): AbstractBustV2FeatureRange {
  const range = ranges.find(
    (candidate) =>
      localIndex >= candidate.start && localIndex < candidate.end
  );
  if (!range) {
    throw new Error(`Missing facial feature range for index ${localIndex}`);
  }
  return range;
}

function pointForRegion(
  rangeCode: AbstractBustV2RegionCode,
  localIndex: number,
  count: number,
  globalIndex: number,
  regionStart: number,
  featureRanges: readonly AbstractBustV2FeatureRange[],
  blueprint: AbstractBustBlueprintV2,
  anchors: AbstractBustV2DerivedAnchors
): MutablePoint {
  switch (rangeCode) {
    case ABSTRACT_BUST_V2_REGION.head:
      return headPoint(
        localIndex,
        count,
        globalIndex,
        blueprint,
        anchors
      );
    case ABSTRACT_BUST_V2_REGION.facialFeatures:
      return featurePoint(
        findFeatureRange(featureRanges, localIndex),
        regionStart,
        globalIndex,
        blueprint,
        anchors
      );
    case ABSTRACT_BUST_V2_REGION.hairScalp:
      return hairPoint(
        localIndex,
        count,
        globalIndex,
        blueprint,
        anchors
      );
    case ABSTRACT_BUST_V2_REGION.neck:
      return neckPoint(
        localIndex,
        count,
        globalIndex,
        blueprint,
        anchors
      );
    case ABSTRACT_BUST_V2_REGION.shouldersAndChest:
      return shouldersAndChestPoint(
        localIndex,
        count,
        globalIndex,
        blueprint,
        anchors
      );
    case ABSTRACT_BUST_V2_REGION.torso:
      return torsoPoint(
        localIndex,
        count,
        globalIndex,
        blueprint,
        anchors
      );
  }
}

export function writeAbstractBustV2Positions(
  blueprint: AbstractBustBlueprintV2,
  ranges: AbstractBustV2RegionRanges,
  output: Float32Array
): AbstractBustV2DerivedAnchors {
  const anchors = deriveAbstractBustV2Anchors(blueprint);
  const featureRange = ranges.find(
    (range) => range.code === ABSTRACT_BUST_V2_REGION.facialFeatures
  );
  if (!featureRange) {
    throw new Error("AbstractBustV2 facial feature region is missing");
  }
  const featureRanges = deriveAbstractBustV2FeatureRanges(
    featureRange.end - featureRange.start
  );

  for (const range of ranges) {
    const count = range.end - range.start;
    for (
      let globalIndex = range.start;
      globalIndex < range.end;
      globalIndex += 1
    ) {
      const point = pointForRegion(
        range.code,
        globalIndex - range.start,
        count,
        globalIndex,
        range.start,
        featureRanges,
        blueprint,
        anchors
      );
      const offset = globalIndex * 3;
      output[offset] = point[0];
      output[offset + 1] = point[1];
      output[offset + 2] = point[2];
    }
  }
  return anchors;
}
