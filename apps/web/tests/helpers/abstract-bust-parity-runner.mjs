import { readFileSync } from "node:fs";
import { basename } from "node:path";

import {
  AbstractBustBlueprintValidationError,
  normalizeAbstractBustBlueprint,
} from "../../../../packages/shared-schema/src/abstract-bust-blueprint.ts";

function outcome(value) {
  try {
    return { ok: true, value: normalizeAbstractBustBlueprint(value) };
  } catch (error) {
    if (!(error instanceof AbstractBustBlueprintValidationError)) throw error;
    return { ok: false, code: error.code, path: error.path };
  }
}

const arguments_ = process.argv.slice(2);
const normalized =
  arguments_[0] === "--stdin"
    ? Object.fromEntries(
        Object.entries(JSON.parse(readFileSync(0, "utf8"))).map(
          ([name, value]) => [name, outcome(value)]
        )
      )
    : Object.fromEntries(
        arguments_.map((path) => [
          basename(path),
          normalizeAbstractBustBlueprint(JSON.parse(readFileSync(path, "utf8"))),
        ])
      );

process.stdout.write(JSON.stringify(normalized));
