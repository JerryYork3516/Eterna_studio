import {
  ABSTRACT_BUST_GENERATOR_VERSION,
  getDefaultAbstractBustBlueprint,
  normalizeAbstractBustBlueprint,
  type AbstractBustBlueprint,
} from "@eterna/shared-schema/abstract-bust-blueprint";
import {
  ABSTRACT_PARTICLE_BUST_BUILDER_ID,
  requireVisualBuilderDefinition,
} from "./builder-registry.ts";

export interface VisualAsset<TBlueprint = unknown> {
  asset_id: string;
  name: string;
  appearance_type: string;
  builder_id: string;
  generator_version: string;
  blueprint: TBlueprint;
  created_at: string;
  updated_at: string;
  revision: number;
}

export type AbstractParticleBustVisualAsset =
  VisualAsset<AbstractBustBlueprint> & {
    appearance_type: "abstract_particle_bust";
    builder_id: typeof ABSTRACT_PARTICLE_BUST_BUILDER_ID;
    generator_version: typeof ABSTRACT_BUST_GENERATOR_VERSION;
  };

export type CreateVisualAssetOptions = {
  name: string;
  assetIdFactory?: () => string;
  now?: () => string;
};

const VISUAL_ASSET_KEYS = new Set([
  "asset_id",
  "name",
  "appearance_type",
  "builder_id",
  "generator_version",
  "blueprint",
  "created_at",
  "updated_at",
  "revision",
]);

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value && typeof value === "object" && !Array.isArray(value));
}

function defaultAssetId(): string {
  const uuid = globalThis.crypto?.randomUUID?.();
  if (uuid) {
    return `visual_asset_${uuid}`;
  }
  return `visual_asset_${Date.now().toString(36)}_${Math.random().toString(36).slice(2)}`;
}

function requireNonEmptyString(
  value: unknown,
  fieldName: string
): string {
  if (typeof value !== "string" || !value.trim()) {
    throw new Error(`VisualAsset.${fieldName} must be a non-empty string`);
  }
  return value.trim();
}

function requireTimestamp(value: unknown, fieldName: string): string {
  const timestamp = requireNonEmptyString(value, fieldName);
  if (!Number.isFinite(Date.parse(timestamp))) {
    throw new Error(`VisualAsset.${fieldName} must be an ISO timestamp`);
  }
  return timestamp;
}

export function createAbstractParticleBustVisualAsset(
  options: CreateVisualAssetOptions
): AbstractParticleBustVisualAsset {
  const definition = requireVisualBuilderDefinition(
    ABSTRACT_PARTICLE_BUST_BUILDER_ID
  );
  const timestamp = (options.now ?? (() => new Date().toISOString()))();
  const assetId = (options.assetIdFactory ?? defaultAssetId)();

  return normalizeVisualAsset({
    asset_id: assetId,
    name: options.name,
    appearance_type: definition.appearanceType,
    builder_id: definition.id,
    generator_version: definition.generatorVersion,
    blueprint: getDefaultAbstractBustBlueprint(),
    created_at: timestamp,
    updated_at: timestamp,
    revision: 1,
  });
}

export function createVisualAsset(
  builderId: string,
  options: CreateVisualAssetOptions
): AbstractParticleBustVisualAsset {
  requireVisualBuilderDefinition(builderId);
  if (builderId !== ABSTRACT_PARTICLE_BUST_BUILDER_ID) {
    throw new Error(`Unsupported visual asset builder: ${builderId}`);
  }
  return createAbstractParticleBustVisualAsset(options);
}

export function normalizeVisualAsset(
  value: unknown
): AbstractParticleBustVisualAsset {
  if (!isRecord(value)) {
    throw new Error("VisualAsset must be an object");
  }

  const unknownField = Object.keys(value).find(
    (fieldName) => !VISUAL_ASSET_KEYS.has(fieldName)
  );
  if (unknownField) {
    throw new Error(`Unknown VisualAsset field: ${unknownField}`);
  }

  const builderId = requireNonEmptyString(value.builder_id, "builder_id");
  const definition = requireVisualBuilderDefinition(builderId);
  if (definition.id !== ABSTRACT_PARTICLE_BUST_BUILDER_ID) {
    throw new Error(`Unsupported visual asset builder: ${builderId}`);
  }

  const appearanceType = requireNonEmptyString(
    value.appearance_type,
    "appearance_type"
  );
  if (appearanceType !== definition.appearanceType) {
    throw new Error("VisualAsset appearance_type does not match its builder");
  }

  const generatorVersion = requireNonEmptyString(
    value.generator_version,
    "generator_version"
  );
  if (generatorVersion !== definition.generatorVersion) {
    throw new Error("VisualAsset generator_version does not match its builder");
  }

  if (
    typeof value.revision !== "number" ||
    !Number.isInteger(value.revision) ||
    value.revision < 1
  ) {
    throw new Error("VisualAsset.revision must be a positive integer");
  }

  return {
    asset_id: requireNonEmptyString(value.asset_id, "asset_id"),
    name: requireNonEmptyString(value.name, "name"),
    appearance_type: appearanceType,
    builder_id: builderId,
    generator_version: generatorVersion,
    blueprint: normalizeAbstractBustBlueprint(value.blueprint),
    created_at: requireTimestamp(value.created_at, "created_at"),
    updated_at: requireTimestamp(value.updated_at, "updated_at"),
    revision: value.revision,
  } as AbstractParticleBustVisualAsset;
}

export function updateVisualAssetMetadata(
  asset: AbstractParticleBustVisualAsset,
  patch: { name?: string },
  now = new Date().toISOString()
): AbstractParticleBustVisualAsset {
  return normalizeVisualAsset({
    ...asset,
    name: patch.name ?? asset.name,
    updated_at: now,
    revision: asset.revision + 1,
  });
}
