import schemaDocument from "../contracts/abstract_bust_v0_1/abstract_bust_blueprint_v0_1.schema.json" with { type: "json" };
import defaultDocument from "../contracts/abstract_bust_v0_1/fixtures/default.json" with { type: "json" };
import feminineDocument from "../contracts/abstract_bust_v0_1/fixtures/feminine.json" with { type: "json" };
import masculineDocument from "../contracts/abstract_bust_v0_1/fixtures/masculine.json" with { type: "json" };
import neutralDocument from "../contracts/abstract_bust_v0_1/fixtures/neutral.json" with { type: "json" };

export const ABSTRACT_BUST_GENERATOR_VERSION = "abstract_bust_v0_1" as const;

export type AbstractBustPresentation = "neutral" | "feminine" | "masculine";
export type AbstractBustAgeTendency = "youthful" | "balanced" | "mature";
export type AbstractBustHairStyle = "none" | "short" | "medium" | "long" | "tied";

export type AbstractBustEditorFieldDescriptor = Readonly<{
  path: string;
  valueType: "number" | "integer" | "enum";
  defaultValue: number | string;
  minimum?: number;
  maximum?: number;
  enumValues?: readonly string[];
}>;

export type AbstractBustBlueprint = {
  generator_version: typeof ABSTRACT_BUST_GENERATOR_VERSION;
  presentation: AbstractBustPresentation;
  age_tendency: AbstractBustAgeTendency;
  seed: number;
  head: {
    width: number;
    height: number;
    roundness: number;
  };
  face: {
    eyes: {
      vertical_position: number;
      spacing: number;
      size: number;
      tilt: number;
      contour_strength: number;
    };
    nose: {
      vertical_position: number;
      width: number;
      length: number;
      prominence: number;
    };
    mouth: {
      vertical_position: number;
      width: number;
      curvature: number;
      contour_strength: number;
    };
    cheeks: {
      width: number;
      vertical_position: number;
      prominence: number;
    };
    jaw: {
      width: number;
      taper: number;
      length: number;
      roundness: number;
    };
  };
  neck: {
    width: number;
    length: number;
  };
  shoulders: {
    width: number;
    slope: number;
  };
  torso: {
    width: number;
    thickness: number;
    length: number;
    taper: number;
  };
  hair: {
    style: AbstractBustHairStyle;
    volume: number;
    length: number;
  };
  contour: {
    softening: number;
    asymmetry: number;
  };
};

type JsonObject = Record<string, unknown>;
type SchemaNode = JsonObject & {
  $ref?: string;
  const?: unknown;
  enum?: unknown[];
  type?: string;
  minimum?: number;
  maximum?: number;
  default?: unknown;
  required?: string[];
  properties?: Record<string, SchemaNode>;
};

const schema = schemaDocument as unknown as SchemaNode & {
  $defs: Record<string, SchemaNode>;
};
const defaultBlueprint = defaultDocument as unknown as AbstractBustBlueprint;
const presetBlueprints = {
  neutral: neutralDocument,
  feminine: feminineDocument,
  masculine: masculineDocument,
} as const;

export const ABSTRACT_BUST_PRESENTATIONS = Object.freeze(
  [...((schema.properties?.presentation?.enum ?? []) as AbstractBustPresentation[])]
);
export const ABSTRACT_BUST_AGE_TENDENCIES = Object.freeze(
  [...((schema.properties?.age_tendency?.enum ?? []) as AbstractBustAgeTendency[])]
);
const hairSchemaReference = schema.properties?.hair?.$ref;
const hairSchemaName = hairSchemaReference?.replace("#/$defs/", "") ?? "";
export const ABSTRACT_BUST_HAIR_STYLES = Object.freeze(
  [...((schema.$defs[hairSchemaName]?.properties?.style?.enum ?? []) as AbstractBustHairStyle[])]
);

export class AbstractBustBlueprintValidationError extends Error {
  readonly code: string;
  readonly path: string;

  constructor(code: string, path: string, message: string) {
    super(`${code} at ${path}: ${message}`);
    this.name = "AbstractBustBlueprintValidationError";
    this.code = code;
    this.path = path;
  }
}

function isRecord(value: unknown): value is JsonObject {
  return Boolean(value && typeof value === "object" && !Array.isArray(value));
}

function cloneJson<T>(value: T): T {
  return JSON.parse(JSON.stringify(value)) as T;
}

function resolveSchema(value: SchemaNode): SchemaNode {
  if (!value.$ref) return value;
  const prefix = "#/$defs/";
  if (!value.$ref.startsWith(prefix)) {
    throw new Error(`Unsupported AbstractBustBlueprint schema reference: ${value.$ref}`);
  }
  const resolved = schema.$defs[value.$ref.slice(prefix.length)];
  if (!resolved) {
    throw new Error(`Missing AbstractBustBlueprint schema definition: ${value.$ref}`);
  }
  return resolved;
}

function collectEditorFields(
  schemaValue: SchemaNode,
  path: readonly string[] = []
): AbstractBustEditorFieldDescriptor[] {
  const currentSchema = resolveSchema(schemaValue);
  if (currentSchema.type === "object") {
    return Object.entries(currentSchema.properties ?? {}).flatMap(
      ([fieldName, fieldSchema]) => {
        if (path.length === 0 && fieldName === "generator_version") return [];
        return collectEditorFields(fieldSchema, [...path, fieldName]);
      }
    );
  }

  const defaultValue = currentSchema.default;
  const fieldPath = path.join(".");
  if (currentSchema.enum) {
    if (typeof defaultValue !== "string") {
      throw new Error(`Missing enum editor default at ${fieldPath}`);
    }
    return [{
      path: fieldPath,
      valueType: "enum",
      defaultValue,
      enumValues: Object.freeze(currentSchema.enum.map(String)),
    }];
  }
  if (currentSchema.type === "number" || currentSchema.type === "integer") {
    if (
      typeof defaultValue !== "number" ||
      typeof currentSchema.minimum !== "number" ||
      typeof currentSchema.maximum !== "number"
    ) {
      throw new Error(`Incomplete numeric editor schema at ${fieldPath}`);
    }
    return [{
      path: fieldPath,
      valueType: currentSchema.type,
      defaultValue,
      minimum: currentSchema.minimum,
      maximum: currentSchema.maximum,
    }];
  }
  return [];
}

export const ABSTRACT_BUST_EDITOR_FIELDS: readonly AbstractBustEditorFieldDescriptor[] =
  Object.freeze(
    collectEditorFields(schema).map((field) => Object.freeze(field))
  );

function fail(code: string, path: string, message: string): never {
  throw new AbstractBustBlueprintValidationError(code, path, message);
}

function normalizeValue(
  value: unknown,
  schemaValue: SchemaNode,
  defaultValue: unknown,
  path: string
): unknown {
  const currentSchema = resolveSchema(schemaValue);

  if (
    Object.prototype.hasOwnProperty.call(currentSchema, "const") &&
    (typeof value !== typeof currentSchema.const || value !== currentSchema.const)
  ) {
    fail(
      path === "$.generator_version" ? "unknown_generator_version" : "invalid_const",
      path,
      `expected ${JSON.stringify(currentSchema.const)}`
    );
  }

  if (
    currentSchema.enum &&
    !currentSchema.enum.some(
      (candidate) => typeof value === typeof candidate && value === candidate
    )
  ) {
    fail("unknown_enum", path, `unsupported value ${JSON.stringify(value)}`);
  }

  if (currentSchema.type === "object") {
    if (!isRecord(value)) fail("invalid_type", path, "expected object");
    const properties = currentSchema.properties;
    if (!properties) throw new Error(`Object schema has no properties at ${path}`);
    const unknownFields = Object.keys(value).filter((key) => !(key in properties)).sort();
    if (unknownFields.length) {
      fail(
        "unknown_field",
        `${path}.${unknownFields[0]}`,
        "additional properties are forbidden"
      );
    }
    const requiredFields = new Set(currentSchema.required ?? []);
    const missingRequired = [...requiredFields].filter((key) => !(key in value)).sort();
    if (missingRequired.length) {
      fail(
        "missing_required_field",
        `${path}.${missingRequired[0]}`,
        "required field is missing"
      );
    }

    const defaults = isRecord(defaultValue) ? defaultValue : {};
    const normalized: JsonObject = {};
    for (const [fieldName, fieldSchema] of Object.entries(properties)) {
      if (fieldName in value) {
        normalized[fieldName] = normalizeValue(
          value[fieldName],
          fieldSchema,
          defaults[fieldName],
          `${path}.${fieldName}`
        );
        continue;
      }
      if (requiredFields.has(fieldName)) continue;
      const hasFixtureDefault = fieldName in defaults;
      const hasSchemaDefault = Object.prototype.hasOwnProperty.call(fieldSchema, "default");
      if (!hasFixtureDefault && !hasSchemaDefault) continue;
      const optionalDefault = cloneJson(
        hasFixtureDefault ? defaults[fieldName] : fieldSchema.default
      );
      normalized[fieldName] = normalizeValue(
        optionalDefault,
        fieldSchema,
        optionalDefault,
        `${path}.${fieldName}`
      );
    }
    return normalized;
  }

  if (currentSchema.type === "integer") {
    if (typeof value !== "number" || !Number.isInteger(value)) {
      fail("invalid_type", path, "expected integer");
    }
    let normalized = value;
    if (typeof currentSchema.minimum === "number") {
      normalized = Math.max(currentSchema.minimum, normalized);
    }
    if (typeof currentSchema.maximum === "number") {
      normalized = Math.min(currentSchema.maximum, normalized);
    }
    return normalized;
  }

  if (currentSchema.type === "number") {
    if (typeof value !== "number") fail("invalid_type", path, "expected number");
    if (!Number.isFinite(value)) fail("non_finite_number", path, "number must be finite");
    let normalized = value;
    if (typeof currentSchema.minimum === "number") {
      normalized = Math.max(currentSchema.minimum, normalized);
    }
    if (typeof currentSchema.maximum === "number") {
      normalized = Math.min(currentSchema.maximum, normalized);
    }
    return normalized;
  }

  return value;
}

export function normalizeAbstractBustBlueprint(value: unknown): AbstractBustBlueprint {
  let parsed = value;
  if (typeof value === "string") {
    try {
      parsed = JSON.parse(value);
    } catch (error) {
      fail("invalid_json", "$", error instanceof Error ? error.message : String(error));
    }
  }
  return normalizeValue(parsed, schema, defaultBlueprint, "$") as AbstractBustBlueprint;
}

export const parseAbstractBustBlueprint = normalizeAbstractBustBlueprint;

export function getDefaultAbstractBustBlueprint(): AbstractBustBlueprint {
  return normalizeAbstractBustBlueprint(cloneJson(defaultBlueprint));
}

export function getAbstractBustPresetBlueprint(
  presentation: AbstractBustPresentation
): AbstractBustBlueprint {
  const preset = presetBlueprints[presentation];
  if (!preset) {
    fail(
      "unknown_enum",
      "$.presentation",
      `unsupported value ${JSON.stringify(presentation)}`
    );
  }
  return normalizeAbstractBustBlueprint(cloneJson(preset));
}
