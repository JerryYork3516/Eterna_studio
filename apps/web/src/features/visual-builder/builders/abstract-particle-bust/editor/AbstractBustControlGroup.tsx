"use client";

import {
  useEffect,
  useState,
  type KeyboardEvent,
} from "react";
import type {
  AbstractBustBlueprint,
  AbstractBustEditorFieldDescriptor,
} from "@eterna/shared-schema/abstract-bust-blueprint";

import {
  displayAbstractBustNumber,
  editorStep,
  getAbstractBustFieldValue,
} from "./editor-state.ts";

export type AbstractBustEditorTranslator = (
  key: string,
  fallback?: string
) => string;

type ControlGroupProps = {
  fields: readonly AbstractBustEditorFieldDescriptor[];
  blueprint: AbstractBustBlueprint;
  errors: Readonly<Record<string, string>>;
  onCommit: (field: AbstractBustEditorFieldDescriptor, value: number | string) => void;
  onInvalid: (path: string) => void;
  t: AbstractBustEditorTranslator;
};

function fieldLabel(
  field: AbstractBustEditorFieldDescriptor,
  t: AbstractBustEditorTranslator
): string {
  return t(
    `visualBuilder.field.${field.path}`,
    field.path.split(".").at(-1) ?? field.path
  );
}

function NumericControl({
  field,
  blueprint,
  error,
  onCommit,
  onInvalid,
  t,
}: {
  field: AbstractBustEditorFieldDescriptor;
  blueprint: AbstractBustBlueprint;
  error?: string;
  onCommit: (field: AbstractBustEditorFieldDescriptor, value: number) => void;
  onInvalid: (path: string) => void;
  t: AbstractBustEditorTranslator;
}) {
  const value = Number(getAbstractBustFieldValue(blueprint, field.path));
  const canonicalText = displayAbstractBustNumber(value, field);
  const [text, setText] = useState(canonicalText);

  useEffect(() => {
    setText(canonicalText);
  }, [canonicalText, field.path]);

  const commitText = () => {
    const parsed = Number(text);
    if (!text.trim() || !Number.isFinite(parsed)) {
      onInvalid(field.path);
      setText(canonicalText);
      return;
    }
    onCommit(field, parsed);
  };

  const handleKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
    if (event.key === "Enter") {
      event.currentTarget.blur();
    } else if (event.key === "Escape") {
      setText(canonicalText);
      event.currentTarget.blur();
    }
  };

  return (
    <label className="abstract-bust-control" data-field-path={field.path}>
      <span className="abstract-bust-control__label">
        {fieldLabel(field, t)}
      </span>
      <div className="abstract-bust-control__numeric">
        <input
          type="range"
          min={field.minimum}
          max={field.maximum}
          step={editorStep(field)}
          value={value}
          aria-label={`${fieldLabel(field, t)} ${t("visualBuilder.control.slider", "slider")}`}
          onChange={(event) => onCommit(field, Number(event.target.value))}
        />
        <input
          type="text"
          inputMode="decimal"
          value={text}
          aria-invalid={Boolean(error)}
          aria-label={fieldLabel(field, t)}
          onChange={(event) => setText(event.target.value)}
          onBlur={commitText}
          onKeyDown={handleKeyDown}
        />
      </div>
      <span className="abstract-bust-control__range">
        {field.minimum} – {field.maximum}
      </span>
      {error ? (
        <span className="abstract-bust-control__error" role="alert">
          {error}
        </span>
      ) : null}
    </label>
  );
}

export function AbstractBustControlGroup({
  fields,
  blueprint,
  errors,
  onCommit,
  onInvalid,
  t,
}: ControlGroupProps) {
  return (
    <div className="abstract-bust-control-group">
      {fields.map((field) => {
        const value = getAbstractBustFieldValue(blueprint, field.path);
        if (field.valueType === "enum") {
          return (
            <label
              key={field.path}
              className="abstract-bust-control"
              data-field-path={field.path}
            >
              <span className="abstract-bust-control__label">
                {fieldLabel(field, t)}
              </span>
              <select
                value={String(value)}
                aria-label={fieldLabel(field, t)}
                onChange={(event) => onCommit(field, event.target.value)}
              >
                {(field.enumValues ?? []).map((option) => (
                  <option key={option} value={option}>
                    {t(`visualBuilder.enum.${option}`, option)}
                  </option>
                ))}
              </select>
            </label>
          );
        }
        return (
          <NumericControl
            key={field.path}
            field={field}
            blueprint={blueprint}
            error={errors[field.path]}
            onCommit={onCommit}
            onInvalid={onInvalid}
            t={t}
          />
        );
      })}
    </div>
  );
}
