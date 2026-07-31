import type { AbstractBustV2Point } from "../types.ts";

export const f32 = Math.fround;

// Swift 6.3's Float.pi bit pattern on the frozen Aftelle baseline is 0x40490fda.
export const F32_PI = f32(3.141592502593994140625);

const floatBitsScratch = new Float32Array(1);
const uintBitsScratch = new Uint32Array(floatBitsScratch.buffer);
const doubleBitsScratch = new DataView(new ArrayBuffer(8));

function float32Bits(value: number): number {
  floatBitsScratch[0] = value;
  return uintBitsScratch[0];
}

function float32FromBits(bits: number): number {
  uintBitsScratch[0] = bits >>> 0;
  return floatBitsScratch[0];
}

function doubleFromBits(bits: bigint): number {
  doubleBitsScratch.setBigUint64(0, BigInt.asUintN(64, bits), true);
  return doubleBitsScratch.getFloat64(0, true);
}

function doubleFma(multiplier: number, multiplicand: number, addend: number): number {
  const product = multiplier * multiplicand;
  const splitter = 134_217_729;
  const splitMultiplier = splitter * multiplier;
  const multiplierHigh = splitMultiplier - (splitMultiplier - multiplier);
  const multiplierLow = multiplier - multiplierHigh;
  const splitMultiplicand = splitter * multiplicand;
  const multiplicandHigh =
    splitMultiplicand - (splitMultiplicand - multiplicand);
  const multiplicandLow = multiplicand - multiplicandHigh;
  const productError =
    ((multiplierHigh * multiplicandHigh - product)
      + multiplierHigh * multiplicandLow
      + multiplierLow * multiplicandHigh)
    + multiplierLow * multiplicandLow;
  const sum = product + addend;
  const virtualAddend = sum - product;
  const sumError =
    (product - (sum - virtualAddend)) + (addend - virtualAddend);
  return sum + (productError + sumError);
}

const TRIG_SIGN = [1, 1, -1, -1] as const;
const INVERSE_PI_OVER_TWO = 0.63661977236758138243;
const PI_OVER_TWO = 1.570796326794896558;
const PI_OVER_TWO_TAIL = 6.1232339957367660359e-17;
const COSINE_1 = -0.49999999694475988354;
const COSINE_2 = 0.041666620357131374519;
const COSINE_3 = -0.0013886681647984318658;
const COSINE_4 = 0.000024383567311838599356;
const SINE_1 = -0.16666654609548575694;
const SINE_2 = 0.0083321607618555750679;
const SINE_3 = -0.00019515283191485737336;

function roundTiesToEven(value: number): number {
  const lower = Math.floor(value);
  const fraction = value - lower;
  if (fraction < 0.5) return lower;
  if (fraction > 0.5) return lower + 1;
  return (lower & 1) === 0 ? lower : lower + 1;
}

function reduceFast(
  value: number,
  extendedPrecision: boolean
): readonly [number, number] {
  const scaled = value * INVERSE_PI_OVER_TWO;
  const quadrant = roundTiesToEven(scaled);
  let reduced = doubleFma(-quadrant, PI_OVER_TWO, value);
  if (extendedPrecision) {
    reduced = doubleFma(-quadrant, PI_OVER_TWO_TAIL, reduced);
  }
  return [quadrant, reduced];
}

function trigPolynomial(
  value: number,
  squared: number,
  negateCosine: boolean,
  quadrant: number
): number {
  if ((quadrant & 1) === 0) {
    const cubed = value * squared;
    const tail = doubleFma(squared, SINE_3, SINE_2);
    const seventh = cubed * squared;
    const leading = doubleFma(cubed, SINE_1, value);
    return f32(doubleFma(seventh, tail, leading));
  }

  const cosineSign = negateCosine ? -1 : 1;
  const fourth = squared * squared;
  const high = doubleFma(squared, COSINE_4 * cosineSign, COSINE_3 * cosineSign);
  const low = doubleFma(squared, COSINE_1 * cosineSign, cosineSign);
  const sixth = fourth * squared;
  const leading = doubleFma(fourth, COSINE_2 * cosineSign, low);
  return f32(doubleFma(sixth, high, leading));
}

function exponentTableSin(value: number, cosine: boolean): number {
  const inversePi = 0.3183098863810300827;
  const inversePiTail = -1.9723941116486920464e-10;
  const scaled = value * inversePi + (cosine ? 0.5 : 0);
  const nearest = roundTiesToEven(scaled);
  const fraction = scaled - nearest + value * inversePiTail;
  const signedFraction = (nearest & 1) === 0 ? fraction : -fraction;
  const squared = fraction * fraction;
  const factor1 = doubleFma(
    squared,
    squared - 4.1647719829166298666,
    15.485466333375713432
  );
  const factor2 = 0.076492480587904088107 * doubleFma(
    squared,
    squared - 3.6493923712207774201,
    2.6522034727867631609
  );
  return f32(signedFraction * factor1 * factor2);
}

function reducedTrig(input: number, cosine: boolean): number {
  const rawBits = float32Bits(input);
  const magnitudeBits = rawBits & 0x7fff_ffff;
  const [baseQuadrant, reduced] = reduceFast(
    input,
    magnitudeBits >= 0x42f0_0000
  );
  const quadrant = cosine ? baseQuadrant + 1 : baseQuadrant;
  const magnitude = trigPolynomial(
    reduced,
    reduced * reduced,
    false,
    quadrant
  );
  return TRIG_SIGN[quadrant & 3] < 0 ? f32(-magnitude) : magnitude;
}

const POWF_LOG_POLYNOMIAL = Object.freeze([
  doubleFromBits(0xc047_1559_dca8_27ebn),
  doubleFromBits(0x404e_c71c_53b3_b1e8n),
  doubleFromBits(0xc057_1547_6529_654cn),
  doubleFromBits(0x4067_1547_652a_ef42n),
]);

const POWF_EXP_POLYNOMIAL = Object.freeze([
  doubleFromBits(0x3eee_bfbd_ff30_d656n),
  doubleFromBits(0x3f76_2e44_53e1_0daen),
]);

const POWF_LOG_CENTER_BITS =
  "c05042bd4b9a7c99c050014332be0033c04f804ae8d0cd02c04efec61b011f85c04e7df5fe538ab3c04dfdd89d586e2bc04d7e6c0abc3579c04cffae611ad12b"
  + "c04c819dc2d45fe4c04c043859e2fdb3c04b877c57b1b070c04b0b67f4f46810c04a8ff971810a5ec04a152f142981b4c0499b072a96c6b2c04921800924dd3c"
  + "c048a8980abfbd32c048304d90c11fd3c047b89f02cf2aadc047418acebbf18fc046cb0f6865c8eac046552b49986277c045dfdcf1eeae0ec0456b22e6b578e5"
  + "c044f6fbb2cec598c0448365e695d797c044106017c3eca3c0439de8e1559f70c0432bfee370ee68c042baa0c34be1ecc04249cd2b13cd6cc041d982c9d52708"
  + "c04169c05363f158c040fa848044b351c0408bce0d95fa38c0401d9bbcfa61d4c03f5fd8a9063e35c03e857d3d361368c03dac22d3e441d3c03cd3c712d31109"
  + "c03bfc67a7fff4ccc03b2602497d5346c03a5094b54d2828c0397c1cb13c7ec1c038a8980abfbd32c037d60496cfbb4cc037046031c79f85c03633a8bf437ce1"
  + "c03563dc29ffacb2c03494f863b8df35c033c6fb650cde51c032f9e32d5bfdd1c0322dadc2ab3497c03162593186da70c03097e38ce60649c02f9c95dc1d1165"
  + "c02e0b1ae8f2fd56c02c7b528b70f1c5c02aed391ab6674ec02960caf9abb7cac027d60496cfbb4cc0264ce26c067157c024c560fe68af88c0233f7cde14cf5a"
  + "c021bb32a600549dc020387efbca869ec01d6ebd1f1febfec01a6f9c377dd31bc0177394c9d958d5c0147aa07357704fc01184b8e4c56af8c00d23afc49139f9"
  + "c00743ee861f3556c0016a21e20a0a45bff72c7ba20f7327bfe720d9c06a835f00000000000000003ff6fe50b6ef08514006e79685c2d22a40111cd1d5133413"
  + "4016bad3758efd87401c4dfab90aab5f4020eb389fa29f9b4023aa2fdd27f1c3402663f6fac91316402918a16e46335b402bc84240adabba402e72ec117fa5b2"
  + "40308c588cda79e44031dcd197552b7b40332ae9e278ae1a403476a9f983f74d4035c01a39fbd68840370742d4ef027f40384c2bd02f03b340398edd077e70df"
  + "403acf5e2db4ec94403c0db6cdd94dee403d49ee4c325970403e840be74e6a4d403fbc16b902680a4040790adbb0300940411307dad30b764041ac05b291f070"
  + "40424407ab0e073a4042db10fc4d9aaf40437124cea4cded404406463b1b044940449a784bcd1b8b40452dbdfc4c96b34045c01a39fbd6884046518fe4677ba7"
  + "4046e221cd9d0cde404771d2ba7efb3c404800a563161c5440488e9c72e0b22640491bba891f17094049a802391e232f404a33760a7f6051404abe18797f1f49"
  + "404b47ebf73882a1404bd0f2e9e79031404c592fad295b56404ce0a4923a587d404d6753e032ea0f404ded3fd442364c404e726aa1e754d2404ef6d67328e220";

const POWF_EXP_BITS =
  "3ff00000000000003feff63da9fb33353fefec9a3e7780613fefe315e86e7f853fefd9b0d31585743fefd06b29ddf6de3fefc74518759bc83fefbe3ecac6f383"
  + "3fefb5586cf9890f3fefac922b7247f73fefa3ec32d3d1a23fef9b66affed31b3fef9301d0125b513fef8abdc06c31cc3fef829aaea92de03fef7a98c8a58e51"
  + "3fef72b83c7d517b3fef6af9388c8dea3fef635beb6fcb753fef5be084045cd43fef54873168b9aa3fef4d5022fcd91d3fef463b88628cd63fef3f49917ddc96"
  + "3fef387a6e7562383fef31ce4fb2a63f3fef2b4565e27cdd3fef24dfe1f563813fef1e9df51fdee13fef187fd0dad9903fef1285a6e4030b3fef0cafa93e2f56"
  + "3fef06fe0a31b7153fef0170fc4cd8313feefc08b26416ff3feef6c55f929ff13feef1a7373aa9cb3feeecae6d05d8663feee7db34e59ff73feee32dc313a8e5"
  + "3feedea64c1234223feeda4504ac801c3feed60a21f72e2a3feed1f5d950a8973feece086061892d3feeca41ed1d00573feec6a2b5c13cd03feec32af0d7d3de"
  + "3feebfdad5362a273feebcb299fddd0d3feeb9b2769d2ca73feeb6daa2cf66423feeb42b569d4f823feeb1a4ca5d920f3feeaf4736b527da3feead12d497c7fd"
  + "3feeab07dd4854293feea9268a5946b73feea76f15ad21483feea5e1b976dc093feea47eb03a55853feea34634ccc3203feea238825522253feea155d44ca973"
  + "3feea09e667f3bcd3feea012750bdabf3fee9fb23c651a2f3fee9f7df95194843fee9f75e8ec5f743fee9f9a48a581743fee9feb564267c93feea0694fde5d3f"
  + "3feea11473eb01873feea1ed0130c1323feea2f336cf4e623feea427543e1a123feea589994cce133feea71a4623c7ad3feea8d99b4492ed3feeaac7d98a6699"
  + "3feeace5422aa0db3feeaf3216b5448c3feeb1ae991577363feeb45b0b91ffc63feeb737b0cdc5e53feeba44cbc8520f3feebd829fde4e503feec0f170ca07ba"
  + "3feec49182a3f0903feec86319e323233feecc667b5de5653feed09bec4a2d333feed503b23e255d3feed99e1330b3583feede6b5579fdbf3feee36bbfd3f37a"
  + "3feee89f995ad3ad3feeee07298db6663feef3a2b84f15fb3feef9728de5593a3feeff76f2fb5e473fef05b030a1064a3fef0c1e904bc1d23fef12c25bd71e09"
  + "3fef199bdd85529c3fef20ab5fffd07a3fef27f12e57d14b3fef2f6d9406e7b53fef3720dcef90693fef3f0b555dc3fa3fef472d4a07897c3fef4f87080d89f2"
  + "3fef5818dcfba4873fef60e316c983983fef69e603db32853fef7321f301b4603fef7c97337b9b5f3fef864614f5a1293fef902ee78b3ff63fef9a51fbc74c83"
  + "3fefa4afa2a490da3fefaf482d8e67f13fefba1bee615a273fefc52b376bba973fefd0765b6e45403fefdbfdad9cbe143fefe7c1819e90d83feff3c22b8f71f1";

function decodeDoubleBitTable(encoded: string): readonly number[] {
  return Object.freeze(
    Array.from({ length: encoded.length / 16 }, (_, index) =>
      doubleFromBits(BigInt(`0x${encoded.slice(index * 16, index * 16 + 16)}`))
    )
  );
}

const POWF_LOG_CENTERS = decodeDoubleBitTable(POWF_LOG_CENTER_BITS);

const POWF_LOG_TABLE = Object.freeze(
  Array.from({ length: 128 }, (_, index) => {
    const center = index <= 76
      ? (180 + index) / 256
      : (52 + index) / 128;
    return Object.freeze([1 / center, POWF_LOG_CENTERS[index]] as const);
  })
);

const POWF_EXP_TABLE = Object.freeze(
  Array.from({ length: 128 }, (_, index) =>
    BigInt(`0x${POWF_EXP_BITS.slice(index * 16, index * 16 + 16)}`)
  )
);

function powfLog2(rawBits: number): number {
  const offset = 0x3f33_8000;
  const temporary = (rawBits - offset) >>> 0;
  const tableIndex = (temporary >>> 16) & 0x7f;
  const top = temporary & 0xff80_0000;
  const normalizedBits = (rawBits - top) >>> 0;
  const exponent = (top | 0) >> 16;
  const [inverseCenter, logCenter] = POWF_LOG_TABLE[tableIndex];
  const normalized = float32FromBits(normalizedBits);
  const remainder = doubleFma(normalized, inverseCenter, -1);
  const leading = logCenter + exponent;
  const squared = remainder * remainder;
  let high = doubleFma(
    POWF_LOG_POLYNOMIAL[0],
    remainder,
    POWF_LOG_POLYNOMIAL[1]
  );
  const low = doubleFma(
    POWF_LOG_POLYNOMIAL[2],
    remainder,
    POWF_LOG_POLYNOMIAL[3]
  );
  high = doubleFma(high, squared, low);
  return doubleFma(high, remainder, leading);
}

function powfExp2(scaledExponent: number): number {
  const clamped = Math.min(32_768, Math.max(-32_768, scaledExponent));
  const nearest = Math.round(clamped);
  const remainder = clamped - nearest;
  const tableIndex = ((nearest % 128) + 128) % 128;
  const tableBits = BigInt.asUintN(
    64,
    POWF_EXP_TABLE[tableIndex] + (BigInt(nearest) << 45n)
  );
  const scale = doubleFromBits(tableBits);
  const polynomial = doubleFma(
    POWF_EXP_POLYNOMIAL[0],
    remainder,
    POWF_EXP_POLYNOMIAL[1]
  );
  return f32(doubleFma(polynomial * remainder, scale, scale));
}

function applePowfPositive(base: number, exponent: number): number {
  const scaledExponent = exponent * powfLog2(float32Bits(base));
  return powfExp2(scaledExponent);
}

export function fadd(lhs: number, rhs: number): number {
  return f32(f32(lhs) + f32(rhs));
}

export function fsub(lhs: number, rhs: number): number {
  return f32(f32(lhs) - f32(rhs));
}

export function fmul(lhs: number, rhs: number): number {
  return f32(f32(lhs) * f32(rhs));
}

export function fdiv(lhs: number, rhs: number): number {
  return f32(f32(lhs) / f32(rhs));
}

export function fsin(value: number): number {
  const input = f32(value);
  const rawBits = float32Bits(input);
  const magnitudeBits = rawBits & 0x7fff_ffff;

  if (magnitudeBits <= 0x3f49_0fda) {
    if (magnitudeBits < 0x3980_0000) {
      if (magnitudeBits < 0x3280_0000) {
        return f32(f32(input * f32(67_108_864) + input) * f32(1 / 67_108_864));
      }
      return input;
    }
    return trigPolynomial(input, input * input, false, 0);
  }
  if (magnitudeBits >= 0x7f80_0000) return Number.NaN;
  if (magnitudeBits >= 0x42f0_0000) {
    return exponentTableSin(input, false);
  }
  return reducedTrig(input, false);
}

export function fcos(value: number): number {
  const input = f32(Math.abs(f32(value)));
  const magnitudeBits = float32Bits(input);

  if (magnitudeBits <= 0x3f49_0fda) {
    if (magnitudeBits < 0x3980_0000) {
      return f32(
        f32(f32(67_108_864) - input) * f32(1 / 67_108_864)
      );
    }
    return trigPolynomial(input, input * input, false, 1);
  }
  if (magnitudeBits >= 0x7f80_0000) return Number.NaN;
  if (magnitudeBits >= 0x4c80_0000) {
    return exponentTableSin(input, true);
  }
  return reducedTrig(input, true);
}

export function fsqrt(value: number): number {
  return f32(Math.sqrt(f32(value)));
}

export function fpow(base: number, exponent: number): number {
  const input = f32(base);
  const power = f32(exponent);
  if (!(input > 0) || !Number.isFinite(input) || !Number.isFinite(power)) {
    return f32(Math.pow(input, power));
  }
  return applePowfPositive(input, power);
}

export function fabs(value: number): number {
  return f32(Math.abs(f32(value)));
}

export function fmax(lhs: number, rhs: number): number {
  return f32(Math.max(f32(lhs), f32(rhs)));
}

export function fmin(lhs: number, rhs: number): number {
  return f32(Math.min(f32(lhs), f32(rhs)));
}

export function fclamp(value: number): number {
  return fmin(1, fmax(0, value));
}

export function fmix(lhs: number, rhs: number, amount: number): number {
  return fadd(lhs, fmul(fsub(rhs, lhs), amount));
}

export function fsmoothstep(
  edge0: number,
  edge1: number,
  value: number
): number {
  const unit = fclamp(fdiv(fsub(value, edge0), fmax(fsub(edge1, edge0), 0.000_01)));
  return fmul(fmul(unit, unit), fsub(3, fmul(2, unit)));
}

export function fsoftenedUnit(value: number, amount: number): number {
  const curved = fmul(fmul(value, value), fsub(3, fmul(2, value)));
  return fmix(value, curved, fclamp(amount));
}

export function fpoint(
  x: number,
  y: number,
  z: number
): AbstractBustV2Point {
  return Object.freeze([f32(x), f32(y), f32(z)]) as AbstractBustV2Point;
}
