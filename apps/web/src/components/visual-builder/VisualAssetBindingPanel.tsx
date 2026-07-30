"use client";

import type { VisualAssetBinding } from "@/features/visual-builder/visual-asset-binding";
import type { AbstractParticleBustVisualAsset } from "@/features/visual-builder/visual-asset";

type Translator = (key: string, fallback?: string) => string;

export type VisualAssetBindingPanelState =
  | "loading"
  | "unbound"
  | "in_sync"
  | "out_of_sync"
  | "invalid";

export function VisualAssetBindingPanel({
  asset,
  residentScopeId,
  moduleInstanceId,
  binding,
  bindingAssetId,
  state,
  error,
  actionsDisabled,
  unbindDisabled = false,
  canBind,
  canSync,
  canUnbind,
  onBind,
  onSync,
  onUnbind,
  onGoResident,
  t,
}: {
  asset: AbstractParticleBustVisualAsset | null;
  residentScopeId: string | null;
  moduleInstanceId: string | null;
  binding: VisualAssetBinding | null;
  bindingAssetId?: string | null;
  state: VisualAssetBindingPanelState;
  error?: string | null;
  actionsDisabled: boolean;
  unbindDisabled?: boolean;
  canBind: boolean;
  canSync: boolean;
  canUnbind: boolean;
  onBind: () => void;
  onSync: () => void;
  onUnbind: () => void;
  onGoResident: () => void;
  t: Translator;
}) {
  const replacing = Boolean(
    (binding?.asset_id ?? bindingAssetId) &&
      asset &&
      (binding?.asset_id ?? bindingAssetId) !== asset.asset_id
  );
  const statusLabel =
    state === "loading"
      ? t("visualBuilder.binding.loading", "Loading")
      : t(`visualBuilder.binding.status.${state}`, state);

  return (
    <section
      className="visual-asset-binding-panel"
      data-binding-state={state}
      aria-label={t("visualBuilder.binding.title", "Resident binding")}
    >
      <div className="visual-asset-binding-panel__heading">
        <div>
          <strong>{t("visualBuilder.binding.title", "Resident binding")}</strong>
          <span>
            {t(
              "visualBuilder.binding.subtitle",
              "Explicit Layer 10 snapshot adoption"
            )}
          </span>
        </div>
        <span
          className={`visual-asset-binding-panel__status is-${state}`}
          aria-live="polite"
        >
          {statusLabel}
        </span>
      </div>

      <dl>
        <div>
          <dt>{t("visualBuilder.binding.selectedAsset", "Selected asset")}</dt>
          <dd>
            {asset
              ? `${asset.name} · r${asset.revision}`
              : t("visualBuilder.binding.none", "None")}
          </dd>
        </div>
        <div>
          <dt>{t("visualBuilder.binding.resident", "Resident ID")}</dt>
          <dd>{residentScopeId ?? "—"}</dd>
        </div>
        <div>
          <dt>{t("visualBuilder.binding.module", "Layer 10 module")}</dt>
          <dd>{moduleInstanceId ?? "—"}</dd>
        </div>
        <div>
          <dt>{t("visualBuilder.binding.boundAsset", "Bound asset")}</dt>
          <dd>
            {binding
              ? `${binding.asset_id} · r${binding.asset_revision}`
              : bindingAssetId ??
                t("visualBuilder.binding.none", "None")}
          </dd>
        </div>
        <div>
          <dt>{t("visualBuilder.binding.lastSync", "Last synchronized")}</dt>
          <dd>{binding?.updated_at ?? "—"}</dd>
        </div>
      </dl>

      {error ? (
        <div className="visual-asset-binding-panel__error" role="alert">
          {error}
        </div>
      ) : null}
      {actionsDisabled && !error ? (
        <div className="visual-asset-binding-panel__hint">
          {t(
            "visualBuilder.binding.disabled.unsaved",
            "Save and persist the Blueprint before binding."
          )}
        </div>
      ) : null}

      <div className="visual-asset-binding-panel__actions">
        {canBind ? (
          <button
            type="button"
            className="is-primary"
            disabled={actionsDisabled}
            onClick={onBind}
          >
            {t(
              replacing
                ? "visualBuilder.binding.action.rebind"
                : "visualBuilder.binding.action.bind",
              replacing ? "Replace binding" : "Bind to resident"
            )}
          </button>
        ) : null}
        {canSync ? (
          <button
            type="button"
            className="is-primary"
            disabled={actionsDisabled}
            onClick={onSync}
          >
            {t("visualBuilder.binding.action.sync", "Sync snapshot")}
          </button>
        ) : null}
        {canUnbind ? (
          <button type="button" disabled={unbindDisabled} onClick={onUnbind}>
            {t("visualBuilder.binding.action.unbind", "Unbind")}
          </button>
        ) : null}
        <button
          type="button"
          disabled={!moduleInstanceId}
          onClick={onGoResident}
        >
          {t(
            "visualBuilder.binding.action.goResident",
            "Go to Resident Builder"
          )}
        </button>
      </div>
    </section>
  );
}
