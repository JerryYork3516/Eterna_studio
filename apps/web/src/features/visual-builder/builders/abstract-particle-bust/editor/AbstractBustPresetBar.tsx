"use client";

import type { AbstractBustPresentation } from "@eterna/shared-schema/abstract-bust-blueprint";

import type { AbstractBustEditorTranslator } from "./AbstractBustControlGroup.tsx";

export function AbstractBustPresetBar({
  isDirty,
  onPreset,
  onDefault,
  onCancel,
  onSave,
  t,
}: {
  isDirty: boolean;
  onPreset: (presentation: AbstractBustPresentation) => void;
  onDefault: () => void;
  onCancel: () => void;
  onSave: () => void;
  t: AbstractBustEditorTranslator;
}) {
  return (
    <div className="abstract-bust-preset-bar">
      <div className="abstract-bust-preset-bar__presets">
        <span>{t("visualBuilder.preset.title", "Preset")}</span>
        {(["neutral", "feminine", "masculine"] as const).map((preset) => (
          <button key={preset} type="button" onClick={() => onPreset(preset)}>
            {t(`visualBuilder.enum.${preset}`, preset)}
          </button>
        ))}
      </div>
      <div className="abstract-bust-preset-bar__actions">
        <button type="button" onClick={onDefault}>
          {t("visualBuilder.action.restoreDefault", "Restore default")}
        </button>
        <button type="button" disabled={!isDirty} onClick={onCancel}>
          {t("visualBuilder.action.cancel", "Cancel")}
        </button>
        <button
          type="button"
          className="is-primary"
          disabled={!isDirty}
          onClick={onSave}
        >
          {t("visualBuilder.action.save", "Save Blueprint")}
        </button>
      </div>
    </div>
  );
}
