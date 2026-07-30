import {
  ABSTRACT_PARTICLE_BUST_BUILDER_ID,
  getVisualBuilderDefinition,
} from "./builder-registry.ts";
import {
  normalizeVisualAsset,
  type AbstractParticleBustVisualAsset,
} from "./visual-asset.ts";

export const VISUAL_BUILDER_STATE_VERSION = "v1" as const;
export const VISUAL_BUILDER_STORAGE_KEY = "eterna_visual_builder_v1";

export interface VisualBuilderSnapshot {
  version: typeof VISUAL_BUILDER_STATE_VERSION;
  visualAssets: AbstractParticleBustVisualAsset[];
  selectedVisualAssetId: string | null;
  activeBuilderId: string;
}

type StorageLike = Pick<Storage, "getItem" | "setItem" | "removeItem">;

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value && typeof value === "object" && !Array.isArray(value));
}

function browserStorage(): StorageLike | null {
  return typeof window === "undefined" ? null : window.localStorage;
}

export function createEmptyVisualBuilderSnapshot(): VisualBuilderSnapshot {
  return {
    version: VISUAL_BUILDER_STATE_VERSION,
    visualAssets: [],
    selectedVisualAssetId: null,
    activeBuilderId: ABSTRACT_PARTICLE_BUST_BUILDER_ID,
  };
}

export function normalizeVisualBuilderSnapshot(
  value: unknown
): VisualBuilderSnapshot {
  if (!isRecord(value) || value.version !== VISUAL_BUILDER_STATE_VERSION) {
    return createEmptyVisualBuilderSnapshot();
  }

  const assets: AbstractParticleBustVisualAsset[] = [];
  const seenAssetIds = new Set<string>();
  for (const candidate of Array.isArray(value.visualAssets)
    ? value.visualAssets
    : []) {
    try {
      const asset = normalizeVisualAsset(candidate);
      if (!seenAssetIds.has(asset.asset_id)) {
        seenAssetIds.add(asset.asset_id);
        assets.push(asset);
      }
    } catch {
      // Corrupt or unknown-builder assets do not block recovery of valid assets.
    }
  }

  const activeBuilderId =
    typeof value.activeBuilderId === "string" &&
    getVisualBuilderDefinition(value.activeBuilderId)?.status === "available"
      ? value.activeBuilderId
      : ABSTRACT_PARTICLE_BUST_BUILDER_ID;
  const selectedVisualAssetId =
    typeof value.selectedVisualAssetId === "string" &&
    seenAssetIds.has(value.selectedVisualAssetId)
      ? value.selectedVisualAssetId
      : null;

  return {
    version: VISUAL_BUILDER_STATE_VERSION,
    visualAssets: assets,
    selectedVisualAssetId,
    activeBuilderId,
  };
}

export function saveVisualBuilderSnapshot(
  snapshot: Omit<VisualBuilderSnapshot, "version">,
  storage: StorageLike | null = browserStorage()
): boolean {
  if (!storage) {
    return false;
  }
  try {
    const normalized = normalizeVisualBuilderSnapshot({
      ...snapshot,
      version: VISUAL_BUILDER_STATE_VERSION,
    });
    storage.setItem(VISUAL_BUILDER_STORAGE_KEY, JSON.stringify(normalized));
    return true;
  } catch {
    return false;
  }
}

export function loadVisualBuilderSnapshot(
  storage: StorageLike | null = browserStorage()
): VisualBuilderSnapshot {
  if (!storage) {
    return createEmptyVisualBuilderSnapshot();
  }
  try {
    const stored = storage.getItem(VISUAL_BUILDER_STORAGE_KEY);
    return stored
      ? normalizeVisualBuilderSnapshot(JSON.parse(stored))
      : createEmptyVisualBuilderSnapshot();
  } catch {
    return createEmptyVisualBuilderSnapshot();
  }
}

export function clearVisualBuilderSnapshot(
  storage: StorageLike | null = browserStorage()
): void {
  storage?.removeItem(VISUAL_BUILDER_STORAGE_KEY);
}
