import {
  normalizeAbstractBustBlueprint,
  type AbstractBustBlueprint,
  type AbstractBustEditorFieldDescriptor,
} from "@eterna/shared-schema/abstract-bust-blueprint";

type MutableRecord = Record<string, unknown>;

export function abstractBustBlueprintsEqual(
  lhs: AbstractBustBlueprint,
  rhs: AbstractBustBlueprint
): boolean {
  return JSON.stringify(lhs) === JSON.stringify(rhs);
}

export function getAbstractBustFieldValue(
  blueprint: AbstractBustBlueprint,
  path: string
): number | string {
  let current: unknown = blueprint;
  for (const segment of path.split(".")) {
    if (!current || typeof current !== "object" || Array.isArray(current)) {
      throw new Error(`Unknown AbstractBustBlueprint field: ${path}`);
    }
    current = (current as MutableRecord)[segment];
  }
  if (typeof current !== "number" && typeof current !== "string") {
    throw new Error(`AbstractBustBlueprint field is not editable: ${path}`);
  }
  return current;
}

export function updateAbstractBustDraftField(
  blueprint: AbstractBustBlueprint,
  path: string,
  value: number | string
): AbstractBustBlueprint {
  const next = JSON.parse(JSON.stringify(blueprint)) as MutableRecord;
  const segments = path.split(".");
  let current = next;
  for (const segment of segments.slice(0, -1)) {
    const child = current[segment];
    if (!child || typeof child !== "object" || Array.isArray(child)) {
      throw new Error(`Unknown AbstractBustBlueprint field: ${path}`);
    }
    current = child as MutableRecord;
  }
  current[segments.at(-1) ?? path] = value;
  return normalizeAbstractBustBlueprint(next);
}

export function editorStep(
  field: AbstractBustEditorFieldDescriptor
): number {
  if (field.valueType === "integer") return 1;
  const span = (field.maximum ?? 1) - (field.minimum ?? 0);
  if (span <= 0.2) return 0.001;
  if (span <= 1) return 0.01;
  return 0.1;
}

export function editorPrecision(
  field: AbstractBustEditorFieldDescriptor
): number {
  const step = editorStep(field);
  if (step < 0.01) return 3;
  if (step < 0.1) return 2;
  if (step < 1) return 1;
  return 0;
}

export function displayAbstractBustNumber(
  value: number,
  field: AbstractBustEditorFieldDescriptor
): string {
  if (field.valueType === "integer") return String(value);
  return value.toFixed(editorPrecision(field)).replace(/\.?0+$/, "");
}
