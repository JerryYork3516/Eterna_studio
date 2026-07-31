import {
  normalizeAbstractBustBlueprint,
  type AbstractBustBlueprint,
} from "./abstract-bust-blueprint.ts";
import {
  normalizeAbstractBustBlueprintV2,
  type AbstractBustBlueprintV2,
} from "./abstract-bust-blueprint-v2.ts";

export type AnyAbstractBustBlueprint =
  | AbstractBustBlueprint
  | AbstractBustBlueprintV2;

export class AbstractBustBlueprintRoutingError extends Error {
  readonly code: string;
  readonly path: string;

  constructor(code: string, path: string, message: string) {
    super(`${code} at ${path}: ${message}`);
    this.name = "AbstractBustBlueprintRoutingError";
    this.code = code;
    this.path = path;
  }
}

function parseRoutingInput(value: unknown): Record<string, unknown> {
  let parsed = value;
  if (typeof value === "string") {
    try {
      parsed = JSON.parse(value);
    } catch (error) {
      throw new AbstractBustBlueprintRoutingError(
        "invalid_json",
        "$",
        error instanceof Error ? error.message : String(error)
      );
    }
  }
  if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
    throw new AbstractBustBlueprintRoutingError(
      "invalid_root_type",
      "$",
      "expected object"
    );
  }
  return parsed as Record<string, unknown>;
}

export function normalizeAbstractBustBlueprintByVersion(
  value: unknown
): AnyAbstractBustBlueprint {
  const parsed = parseRoutingInput(value);
  if (!Object.prototype.hasOwnProperty.call(parsed, "generator_version")) {
    throw new AbstractBustBlueprintRoutingError(
      "missing_required_field",
      "$.generator_version",
      "required field is missing"
    );
  }
  if (parsed.generator_version === "abstract_bust_v0_1") {
    return normalizeAbstractBustBlueprint(parsed);
  }
  if (parsed.generator_version === "abstract_bust_v0_2") {
    return normalizeAbstractBustBlueprintV2(parsed);
  }
  throw new AbstractBustBlueprintRoutingError(
    "unknown_generator_version",
    "$.generator_version",
    `unsupported value ${JSON.stringify(parsed.generator_version)}`
  );
}

export const parseAbstractBustBlueprintByVersion =
  normalizeAbstractBustBlueprintByVersion;
