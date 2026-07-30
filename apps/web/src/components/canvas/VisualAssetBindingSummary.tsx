"use client";

import type { VisualAssetBinding } from "@/features/visual-builder/visual-asset-binding";

type Translator = (key: string, fallback?: string) => string;
type BindingState = "unbound" | "in_sync" | "out_of_sync" | "invalid";

export function VisualAssetBindingSummary({
  binding,
  state,
  residentScopeId,
  moduleInstanceId,
  assetName,
  bindingAssetId,
  error,
  onGoVisual,
  t,
}: {
  binding: VisualAssetBinding | null;
  state: BindingState;
  residentScopeId?: string | null;
  moduleInstanceId?: string | null;
  assetName?: string | null;
  bindingAssetId?: string | null;
  error?: string | null;
  onGoVisual?: ((assetId: string) => void) | null;
  t: Translator;
}) {
  return (
    <section
      className="resident-visual-binding-summary"
      data-binding-state={state}
      aria-label={t("residentBuilder.binding.title", "Visual Asset binding")}
    >
      <div className="resident-visual-binding-summary__heading">
        <div>
          <strong>
            {t("residentBuilder.binding.title", "Visual Asset binding")}
          </strong>
          <span>
            {t(
              "residentBuilder.binding.readOnly",
              "Blueprint editing is owned by Visual Builder."
            )}
          </span>
        </div>
        <span
          className={`resident-visual-binding-summary__status is-${state}`}
        >
          {t(`visualBuilder.binding.status.${state}`, state)}
        </span>
      </div>
      <dl>
        <div>
          <dt>{t("visualBuilder.binding.resident", "Resident ID")}</dt>
          <dd>{binding?.resident_scope_id ?? residentScopeId ?? "—"}</dd>
        </div>
        <div>
          <dt>{t("visualBuilder.binding.module", "Layer 10 module")}</dt>
          <dd>
            {binding?.module_instance_id ??
              moduleInstanceId ??
              "layer_10::particle_avatar"}
          </dd>
        </div>
        <div>
          <dt>{t("visualBuilder.binding.boundAsset", "Bound asset")}</dt>
          <dd>
            {binding
              ? `${assetName ?? binding.asset_id} · r${binding.asset_revision}`
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
      {(binding?.asset_id ?? bindingAssetId) && onGoVisual ? (
        <div className="resident-visual-binding-summary__actions">
          <span />
          <button
            type="button"
            onClick={() =>
              onGoVisual((binding?.asset_id ?? bindingAssetId) as string)
            }
          >
            {t(
              "residentBuilder.binding.action.goVisual",
              "Go to Visual Builder"
            )}
          </button>
        </div>
      ) : null}
    </section>
  );
}
