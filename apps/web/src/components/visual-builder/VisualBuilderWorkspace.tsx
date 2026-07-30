"use client";

import {
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
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
import {
  deriveVisualAssetBindingStatus,
  prepareVisualAssetBind,
  prepareVisualAssetSync,
  prepareVisualAssetUnbind,
  type VisualAssetBindingStatus,
  type VisualAssetBindingCanvasSnapshot,
} from "@/features/visual-builder/visual-asset-binding";
import { translate } from "@/i18n";
import {
  fingerprintModuleGraph,
  useCanvasStore,
  type ModuleGraph,
} from "@/store/canvas-store";
import { useVisualBuilderStore } from "@/store/visual-builder-store";
import { VisualAssetBindingPanel } from "./VisualAssetBindingPanel";
import {
  VisualBuilderCanvasDialog,
  type VisualBuilderCanvasDialogState,
} from "./VisualBuilderCanvasDialog";

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
  bindingPanel,
  t,
}: {
  assets: AbstractParticleBustVisualAsset[];
  selectedAsset: AbstractParticleBustVisualAsset | null;
  onCreate: () => void;
  onSelect: (assetId: string) => void;
  onRename: (name: string) => void;
  bindingPanel?: ReactNode;
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
      {bindingPanel}
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

export function VisualBuilderWorkspace({
  selectAssetIntent = null,
  onNavigateToResidentModule,
}: {
  selectAssetIntent?: {
    requestId: number;
    assetId: string;
  } | null;
  onNavigateToResidentModule?: (moduleInstanceId: string) => void;
} = {}) {
  const language = useCanvasStore((state) => state.language);
  const layerModules = useCanvasStore((state) => state.layerModules);
  const moduleInstanceRegistry = useCanvasStore(
    (state) => state.moduleInstanceRegistry
  );
  const moduleGraphs = useCanvasStore((state) => state.moduleGraphs);
  const moduleStateHydrated = useCanvasStore(
    (state) => state.moduleStateHydrated
  );
  const commitExternalModuleGraphTransaction = useCanvasStore(
    (state) => state.commitExternalModuleGraphTransaction
  );
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
  const [bindingTransactionError, setBindingTransactionError] = useState<
    string | null
  >(null);
  const [preview, setPreview] = useState(EMPTY_PREVIEW_SUMMARY);
  const [canvasDialog, setCanvasDialog] =
    useState<VisualBuilderCanvasDialogState | null>(null);
  const handledSelectAssetIntentRef = useRef<number | null>(null);
  const t: Translator = (key, fallback) => translate(language, key, fallback);
  const builder = getVisualBuilderDefinition(activeBuilderId);
  const selectedAsset =
    visualAssets.find((asset) => asset.asset_id === selectedVisualAssetId) ??
    null;
  const draftController = useAbstractBustDraft(selectedAsset);
  const bindingCanvasSnapshot = useMemo<VisualAssetBindingCanvasSnapshot>(
    () => ({
      layerModules,
      moduleInstanceRegistry,
      moduleGraphs,
    }),
    [layerModules, moduleGraphs, moduleInstanceRegistry]
  );
  const bindingStatus = useMemo<VisualAssetBindingStatus | null>(
    () =>
      isHydrated && moduleStateHydrated
        ? deriveVisualAssetBindingStatus({
            ...bindingCanvasSnapshot,
            visualAssets,
          })
        : null,
    [
      bindingCanvasSnapshot,
      isHydrated,
      moduleStateHydrated,
      visualAssets,
    ]
  );

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

  const requestConfirmation = (
    dialog: Omit<
      VisualBuilderCanvasDialogState,
      "confirmLabel" | "cancelLabel"
    > & {
      confirmLabel?: string;
      cancelLabel?: string;
    }
  ) => {
    setCanvasDialog({
      ...dialog,
      confirmLabel:
        dialog.confirmLabel ??
        t("visualBuilder.dialog.confirm", "Confirm"),
      cancelLabel:
        dialog.cancelLabel ??
        t("visualBuilder.dialog.cancel", "Cancel"),
    });
  };

  const runAfterDiscard = (action: () => void) => {
    if (!draftController.isDirty) {
      action();
      return;
    }
    requestConfirmation({
      title: t(
        "visualBuilder.dialog.discardTitle",
        "Unsaved Blueprint"
      ),
      message: t(
        "visualBuilder.confirm.discardDraft",
        "Discard unsaved Blueprint changes?"
      ),
      destructive: true,
      onConfirm: action,
    });
  };

  useEffect(() => {
    if (
      !selectAssetIntent ||
      !isHydrated ||
      handledSelectAssetIntentRef.current === selectAssetIntent.requestId
    ) {
      return;
    }
    handledSelectAssetIntentRef.current = selectAssetIntent.requestId;
    const targetExists = visualAssets.some(
      (asset) => asset.asset_id === selectAssetIntent.assetId
    );
    if (!targetExists) {
      setCanvasDialog({
        title: t(
          "visualBuilder.dialog.noticeTitle",
          "Visual Builder"
        ),
        message: t(
          "visualBuilder.binding.error.navigation",
          "The requested binding target no longer exists."
        ),
        confirmLabel: t("visualBuilder.dialog.close", "Close"),
      });
      return;
    }
    if (selectAssetIntent.assetId !== selectedVisualAssetId) {
      runAfterDiscard(() => selectAsset(selectAssetIntent.assetId));
    }
  }, [
    isHydrated,
    selectAsset,
    selectAssetIntent,
    selectedVisualAssetId,
    visualAssets,
  ]);

  const handleCreate = () => {
    runAfterDiscard(() =>
      createAsset(t("visualBuilder.asset.defaultName", "Untitled Visual Asset"))
    );
  };

  const handleSelect = (assetId: string) => {
    if (assetId === selectedVisualAssetId) return;
    runAfterDiscard(() => selectAsset(assetId));
  };

  const currentCanvasSnapshot = (): VisualAssetBindingCanvasSnapshot => {
    const state = useCanvasStore.getState();
    return {
      layerModules: state.layerModules,
      moduleInstanceRegistry: state.moduleInstanceRegistry,
      moduleGraphs: state.moduleGraphs,
    };
  };

  const commitPreparedGraph = (
    prepared: {
      moduleInstanceId: string;
      nextGraph: VisualAssetBindingCanvasSnapshot["moduleGraphs"][string];
    },
    sourceSnapshot: VisualAssetBindingCanvasSnapshot,
    expectedAssetRevision: number,
    currentAssetRevision: number
  ) => {
    const currentGraph =
      sourceSnapshot.moduleGraphs[prepared.moduleInstanceId];
    const expectedInstance =
      sourceSnapshot.moduleInstanceRegistry[prepared.moduleInstanceId];
    if (!currentGraph || !expectedInstance) {
      setBindingTransactionError(
        t(
          "visualBuilder.binding.error.transaction",
          "The Layer 10 binding transaction failed."
        )
      );
      return false;
    }
    const result = commitExternalModuleGraphTransaction({
      moduleNodeId: prepared.moduleInstanceId,
      expectedFingerprint: fingerprintModuleGraph(
        currentGraph as unknown as ModuleGraph
      ),
      expectedInstance,
      expectedAssetRevision,
      currentAssetRevision,
      nextGraph: prepared.nextGraph as unknown as ModuleGraph,
    });
    if (!result.ok) {
      setBindingTransactionError(
        t(
          "visualBuilder.binding.error.transaction",
          "The Layer 10 binding transaction failed."
        )
      );
      return false;
    }
    setBindingTransactionError(null);
    return true;
  };

  const currentSavedAsset = () => {
    if (!selectedAsset) return null;
    return (
      useVisualBuilderStore
        .getState()
        .visualAssets.find(
          (asset) => asset.asset_id === selectedAsset.asset_id
        ) ?? null
    );
  };

  const handleBind = () => {
    const asset = currentSavedAsset();
    if (!asset || !bindingStatus) return;
    const replacing = Boolean(
      bindingStatus.bindingRecordPresent &&
        bindingStatus.bindingAssetId !== asset.asset_id
    );
    const commitBind = () => {
      try {
        const sourceSnapshot = currentCanvasSnapshot();
        const prepared = prepareVisualAssetBind({
          ...sourceSnapshot,
          asset,
          now: new Date().toISOString(),
          expectedAssetRevision: selectedAsset?.revision,
        });
        commitPreparedGraph(
          prepared,
          sourceSnapshot,
          selectedAsset?.revision ?? 0,
          asset.revision
        );
      } catch {
        setBindingTransactionError(
          t(
            "visualBuilder.binding.error.transaction",
            "The Layer 10 binding transaction failed."
          )
        );
      }
    };
    const confirmLayerOverwrite = () => {
      if (!bindingStatus.layerModified) {
        commitBind();
        return;
      }
      requestConfirmation({
        title: t(
          "visualBuilder.dialog.overwriteTitle",
          "Overwrite Layer 10 snapshot"
        ),
        message: t(
          "visualBuilder.binding.confirm.overwriteLayer",
          "Layer 10 was changed independently. Overwrite it with the saved Visual Asset snapshot?"
        ),
        destructive: true,
        onConfirm: commitBind,
      });
    };
    requestConfirmation({
      title: t(
        replacing
          ? "visualBuilder.dialog.replaceTitle"
          : "visualBuilder.dialog.bindTitle",
        replacing ? "Replace visual binding" : "Bind Visual Asset"
      ),
      message: t(
        replacing
          ? "visualBuilder.binding.confirm.replace"
          : "visualBuilder.binding.confirm.bind",
        replacing
          ? "Replace the current resident binding with the selected Visual Asset?"
          : "Bind this saved Visual Asset to the current resident Layer 10 snapshot?"
      ),
      destructive: replacing,
      onConfirm: confirmLayerOverwrite,
    });
  };

  const commitSync = (asset: AbstractParticleBustVisualAsset) => {
    try {
      const sourceSnapshot = currentCanvasSnapshot();
      const prepared = prepareVisualAssetSync({
        ...sourceSnapshot,
        asset,
        now: new Date().toISOString(),
        expectedAssetRevision: selectedAsset?.revision,
      });
      commitPreparedGraph(
        prepared,
        sourceSnapshot,
        selectedAsset?.revision ?? 0,
        asset.revision
      );
    } catch {
      setBindingTransactionError(
        t(
          "visualBuilder.binding.error.transaction",
          "The Layer 10 binding transaction failed."
        )
      );
    }
  };

  const handleSync = () => {
    const asset = currentSavedAsset();
    if (!asset || !bindingStatus?.binding) return;
    if (!bindingStatus.layerModified) {
      commitSync(asset);
      return;
    }
    requestConfirmation({
      title: t(
        "visualBuilder.dialog.overwriteTitle",
        "Overwrite Layer 10 snapshot"
      ),
      message: t(
        "visualBuilder.binding.confirm.overwriteLayer",
        "Layer 10 was changed independently. Overwrite it with the saved Visual Asset snapshot?"
      ),
      destructive: true,
      onConfirm: () => commitSync(asset),
    });
  };

  const handleUnbind = () => {
    if (!bindingStatus?.bindingRecordPresent) return;
    requestConfirmation({
      title: t(
        "visualBuilder.dialog.unbindTitle",
        "Remove visual binding"
      ),
      message: t(
        "visualBuilder.binding.confirm.unbind",
        "Remove the source binding while keeping the current Layer 10 Blueprint snapshot?"
      ),
      destructive: true,
      onConfirm: () => {
        try {
          const sourceSnapshot = currentCanvasSnapshot();
          const prepared = prepareVisualAssetUnbind(sourceSnapshot);
          commitPreparedGraph(prepared, sourceSnapshot, 0, 0);
        } catch {
          setBindingTransactionError(
            t(
              "visualBuilder.binding.error.transaction",
              "The Layer 10 binding transaction failed."
            )
          );
        }
      },
    });
  };

  const bindingActionsDisabled =
    !selectedAsset ||
    draftController.isDirty ||
    Object.keys(draftController.errors).length > 0 ||
    persistenceDirty ||
    persistenceFailed ||
    !isHydrated ||
    !moduleStateHydrated;
  const unbindDisabled =
    !isHydrated ||
    !moduleStateHydrated ||
    !bindingStatus?.bindingRecordPresent;
  const bindingPanelState = bindingStatus?.state ?? "loading";
  const bindingError =
    bindingTransactionError ??
    (bindingStatus?.state === "invalid"
      ? bindingStatus.assetMissing
        ? t(
            "visualBuilder.binding.error.missingAsset",
            "The bound Visual Asset no longer exists."
          )
        : `${t(
            "visualBuilder.binding.disabled.invalid",
            "The resident or Layer 10 target is not valid."
          )}${bindingStatus.reason ? ` (${bindingStatus.reason})` : ""}`
      : null);
  const canBind = Boolean(
    selectedAsset &&
      bindingStatus?.residentScopeId &&
      bindingStatus.moduleInstanceId &&
      (!bindingStatus.binding ||
        bindingStatus.binding.asset_id !== selectedAsset.asset_id ||
        bindingStatus.state === "invalid")
  );
  const canSync = Boolean(
    selectedAsset &&
      bindingStatus?.binding?.asset_id === selectedAsset.asset_id &&
      bindingStatus.state === "out_of_sync"
  );
  const canUnbind = Boolean(bindingStatus?.bindingRecordPresent);

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
        bindingPanel={
          <VisualAssetBindingPanel
            asset={selectedAsset}
            residentScopeId={bindingStatus?.residentScopeId ?? null}
            moduleInstanceId={bindingStatus?.moduleInstanceId ?? null}
            binding={bindingStatus?.binding ?? null}
            bindingAssetId={bindingStatus?.bindingAssetId ?? null}
            state={bindingPanelState}
            error={bindingError}
            actionsDisabled={bindingActionsDisabled}
            unbindDisabled={unbindDisabled}
            canBind={canBind}
            canSync={canSync}
            canUnbind={canUnbind}
            onBind={handleBind}
            onSync={handleSync}
            onUnbind={handleUnbind}
            onGoResident={() => {
              if (bindingStatus?.moduleInstanceId) {
                onNavigateToResidentModule?.(
                  bindingStatus.moduleInstanceId
                );
              }
            }}
            t={t}
          />
        }
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
      <VisualBuilderCanvasDialog
        dialog={canvasDialog}
        onCancel={() => setCanvasDialog(null)}
        onConfirm={() => {
          const onConfirm = canvasDialog?.onConfirm;
          setCanvasDialog(null);
          onConfirm?.();
        }}
      />
    </div>
  );
}
