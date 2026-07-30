"use client";

import { useEffect, type ReactNode } from "react";
import {
  getVisualBuilderDefinition,
  type VisualBuilderDefinition,
} from "@/features/visual-builder/builder-registry";
import type { AbstractParticleBustVisualAsset } from "@/features/visual-builder/visual-asset";
import { translate } from "@/i18n";
import { useCanvasStore } from "@/store/canvas-store";
import { useVisualBuilderStore } from "@/store/visual-builder-store";

type Translator = (key: string, fallback?: string) => string;

function VisualBuilderHeader({
  builder,
  asset,
  isDirty,
  t,
}: {
  builder: VisualBuilderDefinition | null;
  asset: AbstractParticleBustVisualAsset | null;
  isDirty: boolean;
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
          <dd className={isDirty ? "is-dirty" : "is-saved"}>
            {isDirty ? t("save.dirty", "Unsaved") : t("save.saved", "Saved")}
          </dd>
        </div>
      </dl>
    </header>
  );
}

function VisualAssetSidebar({
  assets,
  selectedAssetId,
  onCreate,
  onSelect,
  t,
}: {
  assets: AbstractParticleBustVisualAsset[];
  selectedAssetId: string | null;
  onCreate: () => void;
  onSelect: (assetId: string) => void;
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
        <div className="visual-asset-list">
          {assets.map((asset) => (
            <button
              key={asset.asset_id}
              type="button"
              className={asset.asset_id === selectedAssetId ? "is-active" : ""}
              aria-pressed={asset.asset_id === selectedAssetId}
              onClick={() => onSelect(asset.asset_id)}
            >
              <strong>{asset.name}</strong>
              <span>{asset.appearance_type}</span>
            </button>
          ))}
        </div>
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

function VisualBuilderViewport({
  asset,
  t,
}: {
  asset: AbstractParticleBustVisualAsset | null;
  t: Translator;
}) {
  return (
    <section
      className="visual-builder-viewport"
      aria-label={t("visualBuilder.viewport.title", "Visual viewport")}
    >
      <div className="visual-builder-viewport__placeholder">
        <span aria-hidden="true">◇</span>
        <strong>
          {asset
            ? t("visualBuilder.viewport.previewPending", "Preview not available in B2")
            : t("visualBuilder.viewport.selectAsset", "Select or create a Visual Asset")}
        </strong>
        <p>
          {t(
            "visualBuilder.viewport.staticDescription",
            "This workspace does not generate particles or start WebGL."
          )}
        </p>
      </div>
    </section>
  );
}

function InspectorRow({
  label,
  children,
}: {
  label: string;
  children: ReactNode;
}) {
  return (
    <div className="visual-builder-inspector__row">
      <dt>{label}</dt>
      <dd>{children}</dd>
    </div>
  );
}

function VisualBuilderInspector({
  builder,
  asset,
  onRename,
  t,
}: {
  builder: VisualBuilderDefinition | null;
  asset: AbstractParticleBustVisualAsset | null;
  onRename: (name: string) => void;
  t: Translator;
}) {
  return (
    <aside className="visual-builder-inspector">
      <div className="visual-builder-section-heading">
        <div>
          <strong>{t("visualBuilder.inspector.title", "Inspector")}</strong>
          <span>{t("visualBuilder.inspector.metadataOnly", "Metadata only")}</span>
        </div>
      </div>
      <dl>
        <InspectorRow label={t("visualBuilder.inspector.builderId", "Builder ID")}>
          {builder?.id ?? "—"}
        </InspectorRow>
        <InspectorRow
          label={t("visualBuilder.inspector.protocolVersion", "Protocol version")}
        >
          {builder?.generatorVersion ?? "—"}
        </InspectorRow>
        <InspectorRow
          label={t("visualBuilder.inspector.appearanceType", "Appearance type")}
        >
          {builder?.appearanceType ?? "—"}
        </InspectorRow>
        <InspectorRow label={t("visualBuilder.inspector.assetName", "Asset name")}>
          {asset ? (
            <input
              value={asset.name}
              aria-label={t("visualBuilder.inspector.assetName", "Asset name")}
              onChange={(event) => onRename(event.target.value)}
            />
          ) : (
            "—"
          )}
        </InspectorRow>
        <InspectorRow label={t("visualBuilder.inspector.assetId", "Asset ID")}>
          <code>{asset?.asset_id ?? "—"}</code>
        </InspectorRow>
        <InspectorRow label={t("visualBuilder.inspector.revision", "Revision")}>
          {asset?.revision ?? "—"}
        </InspectorRow>
        <InspectorRow label={t("visualBuilder.inspector.updatedAt", "Updated")}>
          {asset?.updated_at ?? "—"}
        </InspectorRow>
      </dl>
      <div className="visual-builder-inspector__notice">
        {t(
          "visualBuilder.inspector.parametersDeferred",
          "Blueprint controls are deferred to a later stage."
        )}
      </div>
    </aside>
  );
}

function VisualBuilderStatusBar({
  builder,
  asset,
  isDirty,
  t,
}: {
  builder: VisualBuilderDefinition | null;
  asset: AbstractParticleBustVisualAsset | null;
  isDirty: boolean;
  t: Translator;
}) {
  return (
    <footer className="visual-builder-status-bar">
      <span>
        {t("visualBuilder.status.validation", "Validation")}:{" "}
        <strong>
          {asset
            ? t("visualBuilder.status.valid", "Valid")
            : t("visualBuilder.status.waiting", "Waiting for asset")}
        </strong>
      </span>
      <span>
        {t("visualBuilder.status.upstreamProtocol", "Upstream protocol")}:{" "}
        <strong>{builder?.generatorVersion ?? "—"}</strong>
      </span>
      <span>
        {t("visualBuilder.status.changes", "Changes")}:{" "}
        <strong className={isDirty ? "is-dirty" : "is-saved"}>
          {isDirty ? t("save.dirty", "Unsaved") : t("save.saved", "Saved")}
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
  const isDirty = useVisualBuilderStore((state) => state.isDirty);
  const isHydrated = useVisualBuilderStore((state) => state.isHydrated);
  const createAsset = useVisualBuilderStore((state) => state.createVisualAsset);
  const selectAsset = useVisualBuilderStore((state) => state.selectVisualAsset);
  const renameAsset = useVisualBuilderStore((state) => state.renameVisualAsset);
  const hydrate = useVisualBuilderStore(
    (state) => state.hydrateVisualBuilderState
  );
  const persist = useVisualBuilderStore(
    (state) => state.persistVisualBuilderState
  );
  const t: Translator = (key, fallback) => translate(language, key, fallback);
  const builder = getVisualBuilderDefinition(activeBuilderId);
  const selectedAsset =
    visualAssets.find((asset) => asset.asset_id === selectedVisualAssetId) ??
    null;

  useEffect(() => {
    hydrate();
  }, [hydrate]);

  useEffect(() => {
    if (!isHydrated || !isDirty) {
      return;
    }
    const timer = window.setTimeout(() => persist(), 250);
    return () => window.clearTimeout(timer);
  }, [isDirty, isHydrated, persist, selectedVisualAssetId, visualAssets]);

  const handleCreate = () => {
    createAsset(t("visualBuilder.asset.defaultName", "Untitled Visual Asset"));
  };

  return (
    <div className="visual-builder-workspace">
      <VisualBuilderHeader
        builder={builder}
        asset={selectedAsset}
        isDirty={isDirty}
        t={t}
      />
      <VisualAssetSidebar
        assets={visualAssets}
        selectedAssetId={selectedVisualAssetId}
        onCreate={handleCreate}
        onSelect={selectAsset}
        t={t}
      />
      <VisualBuilderViewport asset={selectedAsset} t={t} />
      <VisualBuilderInspector
        builder={builder}
        asset={selectedAsset}
        onRename={(name) => {
          if (selectedAsset) {
            renameAsset(selectedAsset.asset_id, name);
          }
        }}
        t={t}
      />
      <VisualBuilderStatusBar
        builder={builder}
        asset={selectedAsset}
        isDirty={isDirty}
        t={t}
      />
    </div>
  );
}
