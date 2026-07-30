"use client";

import {
  useEffect,
  useState,
} from "react";
import {
  getAbstractBustPresetBlueprint,
  getDefaultAbstractBustBlueprint,
  normalizeAbstractBustBlueprint,
  type AbstractBustBlueprint,
  type AbstractBustEditorFieldDescriptor,
  type AbstractBustPresentation,
} from "@eterna/shared-schema/abstract-bust-blueprint";

import type { AbstractParticleBustVisualAsset } from "../../../visual-asset.ts";
import { AbstractBustThreeViewport } from "../preview/AbstractBustThreeViewport.tsx";
import type { AbstractBustPreviewSummary } from "../preview/preview-types.ts";
import { AbstractBustInspector } from "./AbstractBustInspector.tsx";
import {
  type AbstractBustEditorTranslator,
} from "./AbstractBustControlGroup.tsx";
import { AbstractBustPresetBar } from "./AbstractBustPresetBar.tsx";
import {
  abstractBustBlueprintsEqual,
  updateAbstractBustDraftField,
} from "./editor-state.ts";

export type AbstractBustDraftController = Readonly<{
  draft: AbstractBustBlueprint | null;
  isDirty: boolean;
  errors: Readonly<Record<string, string>>;
  commitField: (
    field: AbstractBustEditorFieldDescriptor,
    value: number | string
  ) => void;
  markInvalid: (path: string) => void;
  applyPreset: (presentation: AbstractBustPresentation) => void;
  restoreDefault: () => void;
  cancel: () => void;
}>;

export function useAbstractBustDraft(
  asset: AbstractParticleBustVisualAsset | null
): AbstractBustDraftController {
  const [draft, setDraft] = useState<AbstractBustBlueprint | null>(
    asset ? normalizeAbstractBustBlueprint(asset.blueprint) : null
  );
  const [draftAssetId, setDraftAssetId] = useState<string | null>(
    asset?.asset_id ?? null
  );
  const [errors, setErrors] = useState<Record<string, string>>({});

  useEffect(() => {
    const assetId = asset?.asset_id ?? null;
    if (assetId === draftAssetId) return;
    setDraft(asset ? normalizeAbstractBustBlueprint(asset.blueprint) : null);
    setDraftAssetId(assetId);
    setErrors({});
  }, [asset, draftAssetId]);

  const alignedDraft =
    (asset?.asset_id ?? null) === draftAssetId
      ? draft
      : asset
        ? normalizeAbstractBustBlueprint(asset.blueprint)
        : null;
  const isDirty = Boolean(
    asset &&
    alignedDraft &&
    !abstractBustBlueprintsEqual(asset.blueprint, alignedDraft)
  );

  useEffect(() => {
    if (!isDirty) return;
    const warnBeforeUnload = (event: BeforeUnloadEvent) => {
      event.preventDefault();
    };
    window.addEventListener("beforeunload", warnBeforeUnload);
    return () => window.removeEventListener("beforeunload", warnBeforeUnload);
  }, [isDirty]);

  const clearError = (path: string) => {
    setErrors((current) => {
      if (!(path in current)) return current;
      const next = { ...current };
      delete next[path];
      return next;
    });
  };

  const applyPreset = (presentation: AbstractBustPresentation) => {
    setDraft(getAbstractBustPresetBlueprint(presentation));
    setErrors({});
  };

  const commitField = (
    field: AbstractBustEditorFieldDescriptor,
    value: number | string
  ) => {
    if (!alignedDraft) return;
    try {
      if (field.path === "presentation") {
        applyPreset(value as AbstractBustPresentation);
        return;
      }
      setDraft(updateAbstractBustDraftField(alignedDraft, field.path, value));
      clearError(field.path);
    } catch {
      setErrors((current) => ({
        ...current,
        [field.path]: "invalid_value",
      }));
    }
  };

  return Object.freeze({
    draft: alignedDraft,
    isDirty,
    errors,
    commitField,
    markInvalid: (path: string) =>
      setErrors((current) => ({ ...current, [path]: "invalid_number" })),
    applyPreset,
    restoreDefault: () => {
      setDraft(getDefaultAbstractBustBlueprint());
      setErrors({});
    },
    cancel: () => {
      setDraft(asset ? normalizeAbstractBustBlueprint(asset.blueprint) : null);
      setErrors({});
    },
  });
}

export function AbstractBustEditor({
  controller,
  onSave,
  onPreviewSummary,
  t,
}: {
  controller: AbstractBustDraftController;
  onSave: (blueprint: AbstractBustBlueprint) => void;
  onPreviewSummary: (summary: AbstractBustPreviewSummary) => void;
  t: AbstractBustEditorTranslator;
}) {
  if (!controller.draft) return null;

  return (
    <div className="abstract-bust-editor">
      <div className="abstract-bust-editor__viewport-column">
        <AbstractBustPresetBar
          isDirty={controller.isDirty}
          onPreset={controller.applyPreset}
          onDefault={controller.restoreDefault}
          onCancel={controller.cancel}
          onSave={() => onSave(controller.draft as AbstractBustBlueprint)}
          t={t}
        />
        <AbstractBustThreeViewport
          blueprint={controller.draft}
          onSummary={onPreviewSummary}
          t={t}
        />
      </div>
      <AbstractBustInspector
        blueprint={controller.draft}
        errors={Object.fromEntries(
          Object.entries(controller.errors).map(([path, errorCode]) => [
            path,
            t(`visualBuilder.error.${errorCode}`, "Invalid value"),
          ])
        )}
        onCommit={controller.commitField}
        onInvalid={controller.markInvalid}
        t={t}
      />
    </div>
  );
}
