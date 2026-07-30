"use client";

import {
  ABSTRACT_BUST_EDITOR_FIELDS,
  type AbstractBustBlueprint,
  type AbstractBustEditorFieldDescriptor,
} from "@eterna/shared-schema/abstract-bust-blueprint";

import {
  AbstractBustControlGroup,
  type AbstractBustEditorTranslator,
} from "./AbstractBustControlGroup.tsx";

type InspectorProps = {
  blueprint: AbstractBustBlueprint;
  errors: Readonly<Record<string, string>>;
  onCommit: (field: AbstractBustEditorFieldDescriptor, value: number | string) => void;
  onInvalid: (path: string) => void;
  t: AbstractBustEditorTranslator;
};

function fieldsFor(...prefixes: string[]): AbstractBustEditorFieldDescriptor[] {
  return ABSTRACT_BUST_EDITOR_FIELDS.filter((field) =>
    prefixes.some(
      (prefix) => field.path === prefix || field.path.startsWith(`${prefix}.`)
    )
  );
}

const SECTIONS = [
  {
    key: "basic",
    groups: [{ key: "basic", fields: fieldsFor("presentation", "age_tendency", "seed") }],
  },
  {
    key: "head",
    groups: [{ key: "head", fields: fieldsFor("head") }],
  },
  {
    key: "face",
    groups: [
      { key: "eyes", fields: fieldsFor("face.eyes") },
      { key: "nose", fields: fieldsFor("face.nose") },
      { key: "mouth", fields: fieldsFor("face.mouth") },
      { key: "cheeks", fields: fieldsFor("face.cheeks") },
      { key: "jaw", fields: fieldsFor("face.jaw") },
    ],
  },
  {
    key: "body",
    groups: [
      { key: "neck", fields: fieldsFor("neck") },
      { key: "shoulders", fields: fieldsFor("shoulders") },
      { key: "torso", fields: fieldsFor("torso") },
    ],
  },
  {
    key: "hair",
    groups: [{ key: "hair", fields: fieldsFor("hair") }],
  },
  {
    key: "contour",
    groups: [{ key: "contour", fields: fieldsFor("contour") }],
  },
] as const;

export function AbstractBustInspector({
  blueprint,
  errors,
  onCommit,
  onInvalid,
  t,
}: InspectorProps) {
  return (
    <aside className="visual-builder-inspector abstract-bust-inspector">
      <div className="visual-builder-section-heading">
        <div>
          <strong>{t("visualBuilder.inspector.title", "Inspector")}</strong>
          <span>
            {t(
              "visualBuilder.inspector.schemaDriven",
              "Ranges and defaults come from AbstractBustBlueprint v0.1"
            )}
          </span>
        </div>
      </div>
      {SECTIONS.map((section) => (
        <section
          key={section.key}
          className="abstract-bust-inspector__section"
        >
          <h2>
            {t(`visualBuilder.group.${section.key}`, section.key)}
          </h2>
          {section.groups.map((group) => (
            <div
              key={group.key}
              className="abstract-bust-inspector__subgroup"
            >
              {section.groups.length > 1 ? (
                <h3>
                  {t(`visualBuilder.group.${group.key}`, group.key)}
                </h3>
              ) : null}
              <AbstractBustControlGroup
                fields={group.fields}
                blueprint={blueprint}
                errors={errors}
                onCommit={onCommit}
                onInvalid={onInvalid}
                t={t}
              />
            </div>
          ))}
        </section>
      ))}
    </aside>
  );
}
