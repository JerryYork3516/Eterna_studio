"use client";

import { useEffect, useState } from "react";
import {
  AbstractBustEditor,
  useAbstractBustDraft,
} from "@/features/visual-builder/builders/abstract-particle-bust/editor/AbstractBustEditor";
import type { AbstractBustPreviewSummary } from "@/features/visual-builder/builders/abstract-particle-bust/preview/preview-types";
import {
  getVisualBuilderDefinition,
  type VisualBuilderDefinition,
} from "@/features/visual-builder/builder-registry";
import type { AbstractParticleBustVisualAsset } from "@/features/visual-builder/visual-asset";
import { translate } from "@/i18n";
import { useCanvasStore } from "@/store/canvas-store";
import { useVisualBuilderStore } from "@/store/visual-builder-store";

type Translator = (key: string, fallback?: string) => string;
type SaveStatus = "draft" | "saving" | "failed" | "saved";

const EMPTY_PREVIEW_SUMMARY: AbstractBustPreviewSummary = {
  particleCount: 0,
  digest: null,
  error: null,
  diagnostics: {
    initializationMs: 0,
    lastUpdateMs: 0,
    generationCount: 0,
    renderersCreated: 0,
    renderersDisposed: 0,
    activeContexts: 0,
  },
};

function VisualBuilderHeader({
  builder,
  asset,
  saveStatus,
  t,
}: {
  builder: VisualBuilderDefinition | null;
  asset: AbstractParticleBustVisualAsset | null;
  saveStatus: SaveStatus;
  t: Translator;
}) {
  return (
    <header className="visual-builder-header">
      <div>
        <strong>{t("visualBuilder.title", "Visual Builder")}</strong>
        <span>{t("visualBuilder.subtitle", "Digital resident visual workspace")}</span>
      </div>
      <dl>
        <div>
          <dt>{t("visualBuilder.currentBuilder", "Builder")}</dt>
          <dd>
            {builder
              ? t(builder.displayNameKey, builder.id)
              : t("visualBuilder.builder.unavailable", "Unavailable")}
          </dd>
        </div>
        <div>
          <dt>{t("visualBuilder.currentAsset", "Visual Asset")}</dt>
          <dd>{asset?.name ?? t("visualBuilder.asset.noneSelected", "None selected")}</dd>
        </div>
        <div>
          <dt>{t("visualBuilder.saveStatus", "Save status")}</dt>
          <dd className={saveStatus === "saved" ? "is-saved" : "is-dirty"}>
            {t(`visualBuilder.save.${saveStatus}`, saveStatus)}
          </dd>
        </div>
      </dl>
    </header>
  );
}

function VisualAssetSidebar({
  assets,
  selectedAsset,
  onCreate,
  onSelect,
  onRename,
  t,
}: {
  assets: AbstractParticleBustVisualAsset[];
  selectedAsset: AbstractParticleBustVisualAsset | null;
  onCreate: () => void;
  onSelect: (assetId: string) => void;
  onRename: (name: string) => void;
  t: Translator;
}) {
  return (
    <aside className="visual-asset-sidebar">
      <div className="visual-builder-section-heading">
        <div>
          <strong>{t("visualBuilder.assets.title", "Visual Assets")}</strong>
          <span>{t("visualBuilder.assets.projectData", "Studio project data")}</span>
        </div>
        <button type="button" onClick={onCreate}>
          {t("visualBuilder.assets.create", "New Visual Asset")}
        </button>
      </div>
      {assets.length ? (
        <>
          <div className="visual-asset-list">
            {assets.map((asset) => (
              <button
                key={asset.asset_id}
                type="button"
                className={
                  asset.asset_id === selectedAsset?.asset_id ? "is-active" : ""
                }
                aria-pressed={asset.asset_id === selectedAsset?.asset_id}
                onClick={() => onSelect(asset.asset_id)}
              >
                <strong>{asset.name}</strong>
                <span>{asset.appearance_type}</span>
              </button>
            ))}
          </div>
          {selectedAsset ? (
            <label className="visual-asset-sidebar__rename">
              <span>{t("visualBuilder.inspector.assetName", "Asset name")}</span>
              <input
                value={selectedAsset.name}
                onChange={(event) => onRename(event.target.value)}
              />
            </label>
          ) : null}
        </>
      ) : (
        <div className="visual-builder-empty-copy">
          <strong>{t("visualBuilder.assets.emptyTitle", "No Visual Assets")}</strong>
          <span>
            {t(
              "visualBuilder.assets.emptyDescription",
              "Create an asset to begin the visual workspace."
            )}
          </span>
        </div>
      )}
    </aside>
  );
}

function VisualBuilderEmptyState({
  message,
}: {
  message: string;
}) {
  return (
    <section className="visual-builder-viewport">
      <div className="visual-builder-viewport__placeholder">
        <span aria-hidden="true">◇</span>
        <strong>{message}</strong>
      </div>
    </section>
  );
}

function VisualBuilderStatusBar({
  builder,
  asset,
  draftDirty,
  preview,
  t,
}: {
  builder: VisualBuilderDefinition | null;
  asset: AbstractParticleBustVisualAsset | null;
  draftDirty: boolean;
  preview: AbstractBustPreviewSummary;
  t: Translator;
}) {
  return (
    <footer
      className="visual-builder-status-bar"
      data-preview-contexts={preview.diagnostics.activeContexts}
      data-preview-generations={preview.diagnostics.generationCount}
    >
      <span>
        {t("visualBuilder.status.validation", "Validation")}:{" "}
        <strong className={preview.error ? "is-dirty" : ""}>
          {preview.error
            ? t("visualBuilder.status.error", "Error")
            : asset
              ? t("visualBuilder.status.valid", "Valid")
              : t("visualBuilder.status.waiting", "Waiting for asset")}
        </strong>
      </span>
      <span>
        {t("visualBuilder.status.particles", "Particles")}:{" "}
        <strong>{preview.particleCount || "—"}</strong>
      </span>
      <span>
        {t("visualBuilder.status.digest", "Digest")}:{" "}
        <strong>{preview.digest ?? "—"}</strong>
      </span>
      <span>
        {t("visualBuilder.status.performance", "Update")}:{" "}
        <strong>{preview.diagnostics.lastUpdateMs.toFixed(1)} ms</strong>
      </span>
      <span>
        {t("visualBuilder.status.contexts", "Contexts")}:{" "}
        <strong>{preview.diagnostics.activeContexts}</strong>
      </span>
      <span>
        {t("visualBuilder.status.upstreamProtocol", "Upstream protocol")}:{" "}
        <strong>{builder?.generatorVersion ?? "—"}</strong>
      </span>
      <span>
        {t("visualBuilder.status.changes", "Changes")}:{" "}
        <strong className={draftDirty ? "is-dirty" : "is-saved"}>
          {draftDirty ? t("save.dirty", "Unsaved") : t("save.saved", "Saved")}
        </strong>
      </span>
    </footer>
  );
}

export function VisualBuilderWorkspace() {
  const language = useCanvasStore((state) => state.language);
  const visualAssets = useVisualBuilderStore((state) => state.visualAssets);
  const selectedVisualAssetId = useVisualBuilderStore(
    (state) => state.selectedVisualAssetId
  );
  const activeBuilderId = useVisualBuilderStore(
    (state) => state.activeBuilderId
  );
  const persistenceDirty = useVisualBuilderStore((state) => state.isDirty);
  const isHydrated = useVisualBuilderStore((state) => state.isHydrated);
  const createAsset = useVisualBuilderStore((state) => state.createVisualAsset);
  const selectAsset = useVisualBuilderStore((state) => state.selectVisualAsset);
  const renameAsset = useVisualBuilderStore((state) => state.renameVisualAsset);
  const saveBlueprint = useVisualBuilderStore(
    (state) => state.updateVisualAssetBlueprint
  );
  const hydrate = useVisualBuilderStore(
    (state) => state.hydrateVisualBuilderState
  );
  const persist = useVisualBuilderStore(
    (state) => state.persistVisualBuilderState
  );
  const [persistenceFailed, setPersistenceFailed] = useState(false);
  const [preview, setPreview] = useState(EMPTY_PREVIEW_SUMMARY);
  const t: Translator = (key, fallback) => translate(language, key, fallback);
  const builder = getVisualBuilderDefinition(activeBuilderId);
  const selectedAsset =
    visualAssets.find((asset) => asset.asset_id === selectedVisualAssetId) ??
    null;
  const draftController = useAbstractBustDraft(selectedAsset);

  useEffect(() => {
    hydrate();
  }, [hydrate]);

  useEffect(() => {
    if (!isHydrated || !persistenceDirty) return;
    const timer = window.setTimeout(() => {
      setPersistenceFailed(!persist());
    }, 250);
    return () => window.clearTimeout(timer);
  }, [
    isHydrated,
    persistenceDirty,
    persist,
    selectedVisualAssetId,
    visualAssets,
  ]);

  const confirmDiscard = () =>
    !draftController.isDirty ||
    window.confirm(
      t(
        "visualBuilder.confirm.discardDraft",
        "Discard unsaved Blueprint changes?"
      )
    );

  const handleCreate = () => {
    if (!confirmDiscard()) return;
    createAsset(t("visualBuilder.asset.defaultName", "Untitled Visual Asset"));
  };

  const handleSelect = (assetId: string) => {
    if (assetId === selectedVisualAssetId || !confirmDiscard()) return;
    selectAsset(assetId);
  };

  const saveStatus: SaveStatus = draftController.isDirty
    ? "draft"
    : persistenceFailed
      ? "failed"
      : persistenceDirty
        ? "saving"
        : "saved";

  return (
    <div className="visual-builder-workspace">
      <VisualBuilderHeader
        builder={builder}
        asset={selectedAsset}
        saveStatus={saveStatus}
        t={t}
      />
      <VisualAssetSidebar
        assets={visualAssets}
        selectedAsset={selectedAsset}
        onCreate={handleCreate}
        onSelect={handleSelect}
        onRename={(name) => {
          if (selectedAsset && name.trim()) {
            renameAsset(selectedAsset.asset_id, name);
          }
        }}
        t={t}
      />
      {selectedAsset && builder ? (
        <AbstractBustEditor
          controller={draftController}
          onSave={(blueprint) => {
            if (saveBlueprint(selectedAsset.asset_id, blueprint)) {
              setPersistenceFailed(false);
            }
          }}
          onPreviewSummary={setPreview}
          t={t}
        />
      ) : (
        <VisualBuilderEmptyState
          message={
            builder
              ? t(
                  "visualBuilder.viewport.selectAsset",
                  "Select or create a Visual Asset"
                )
              : t(
                  "visualBuilder.error.unknownBuilder",
                  "The selected visual builder is unavailable"
                )
          }
        />
      )}
      <VisualBuilderStatusBar
        builder={builder}
        asset={selectedAsset}
        draftDirty={draftController.isDirty}
        preview={preview}
        t={t}
      />
    </div>
  );
}
