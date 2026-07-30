import { create } from "zustand";
import {
  ABSTRACT_PARTICLE_BUST_BUILDER_ID,
  getVisualBuilderDefinition,
} from "@/features/visual-builder/builder-registry";
import {
  createVisualAsset,
  updateVisualAssetBlueprint as updateAssetBlueprint,
  updateVisualAssetMetadata as updateAssetMetadata,
  type AbstractParticleBustVisualAsset,
} from "@/features/visual-builder/visual-asset";
import type { AbstractBustBlueprint } from "@eterna/shared-schema/abstract-bust-blueprint";
import {
  createEmptyVisualBuilderSnapshot,
  loadVisualBuilderSnapshot,
  saveVisualBuilderSnapshot,
} from "@/features/visual-builder/visual-builder-persistence";

type VisualAssetMetadataPatch = {
  name?: string;
};

type VisualBuilderState = {
  visualAssets: AbstractParticleBustVisualAsset[];
  selectedVisualAssetId: string | null;
  activeBuilderId: string;
  isDirty: boolean;
  isHydrated: boolean;
  createVisualAsset: (name: string) => string | null;
  selectVisualAsset: (assetId: string | null) => void;
  renameVisualAsset: (assetId: string, name: string) => void;
  updateVisualAssetMetadata: (
    assetId: string,
    patch: VisualAssetMetadataPatch
  ) => void;
  updateVisualAssetBlueprint: (
    assetId: string,
    blueprint: AbstractBustBlueprint
  ) => boolean;
  hydrateVisualBuilderState: () => void;
  persistVisualBuilderState: () => boolean;
  resetVisualBuilderState: () => void;
};

const emptySnapshot = createEmptyVisualBuilderSnapshot();

export const useVisualBuilderStore = create<VisualBuilderState>((set, get) => ({
  visualAssets: emptySnapshot.visualAssets,
  selectedVisualAssetId: emptySnapshot.selectedVisualAssetId,
  activeBuilderId: emptySnapshot.activeBuilderId,
  isDirty: false,
  isHydrated: false,

  createVisualAsset: (name) => {
    const state = get();
    if (getVisualBuilderDefinition(state.activeBuilderId)?.status !== "available") {
      return null;
    }
    try {
      const asset = createVisualAsset(state.activeBuilderId, { name });
      set({
        visualAssets: [...state.visualAssets, asset],
        selectedVisualAssetId: asset.asset_id,
        isDirty: true,
      });
      return asset.asset_id;
    } catch {
      return null;
    }
  },

  selectVisualAsset: (assetId) => {
    if (
      assetId !== null &&
      !get().visualAssets.some((asset) => asset.asset_id === assetId)
    ) {
      return;
    }
    set({ selectedVisualAssetId: assetId, isDirty: true });
  },

  renameVisualAsset: (assetId, name) => {
    get().updateVisualAssetMetadata(assetId, { name });
  },

  updateVisualAssetMetadata: (assetId, patch) => {
    const current = get().visualAssets;
    let changed = false;
    const visualAssets = current.map((asset) => {
      if (asset.asset_id !== assetId) {
        return asset;
      }
      try {
        const next = updateAssetMetadata(asset, patch);
        changed = true;
        return next;
      } catch {
        return asset;
      }
    });
    if (changed) {
      set({ visualAssets, isDirty: true });
    }
  },

  updateVisualAssetBlueprint: (assetId, blueprint) => {
    const current = get().visualAssets;
    let changed = false;
    const visualAssets = current.map((asset) => {
      if (asset.asset_id !== assetId) {
        return asset;
      }
      try {
        const next = updateAssetBlueprint(asset, blueprint);
        changed = true;
        return next;
      } catch {
        return asset;
      }
    });
    if (changed) {
      set({ visualAssets, isDirty: true });
    }
    return changed;
  },

  hydrateVisualBuilderState: () => {
    if (get().isHydrated) {
      return;
    }
    const restored = loadVisualBuilderSnapshot();
    set({
      visualAssets: restored.visualAssets,
      selectedVisualAssetId: restored.selectedVisualAssetId,
      activeBuilderId: restored.activeBuilderId,
      isDirty: false,
      isHydrated: true,
    });
  },

  persistVisualBuilderState: () => {
    const state = get();
    const saved = saveVisualBuilderSnapshot({
      visualAssets: state.visualAssets,
      selectedVisualAssetId: state.selectedVisualAssetId,
      activeBuilderId: state.activeBuilderId,
    });
    set({ isDirty: !saved });
    return saved;
  },

  resetVisualBuilderState: () => {
    set({
      visualAssets: [],
      selectedVisualAssetId: null,
      activeBuilderId: ABSTRACT_PARTICLE_BUST_BUILDER_ID,
      isDirty: true,
      isHydrated: true,
    });
  },
}));
