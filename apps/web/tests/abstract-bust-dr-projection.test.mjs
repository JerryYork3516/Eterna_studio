import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";


const readRepoFile = (relativePath) =>
  readFileSync(new URL(`../../../${relativePath}`, import.meta.url), "utf8");


test("B6 compiler projects only the normalized saved Layer 10 Blueprint", () => {
  const compiler = readRepoFile("apps/api/app/services/dr_compiler.py");

  assert.match(
    compiler,
    /normalize_abstract_bust_blueprint\(raw_value\)/
  );
  assert.match(
    compiler,
    /PARTICLE_AVATAR_NODE_IDS\["config_input"\]/
  );
  assert.match(
    compiler,
    /field\.get\("field_key"\)\s*==\s*_ABSTRACT_BUST_BLUEPRINT_FIELD_KEY/
  );
  assert.match(
    compiler,
    /config\[_ABSTRACT_BUST_BLUEPRINT_FIELD_KEY\]\s*=\s*deepcopy\(normalized\)/
  );
  assert.match(
    compiler,
    /payload\[_ABSTRACT_BUST_BLUEPRINT_FIELD_KEY\]\s*=\s*deepcopy/
  );
  assert.doesNotMatch(
    compiler,
    /payload\[_ABSTRACT_BUST_BLUEPRINT_FIELD_KEY\]\s*=.*get\("config"\)/
  );
});


test("B6 formal DR schema keeps the root Blueprint optional and read-only", () => {
  const schema = readRepoFile(
    "apps/api/app/dr/v3/dr_v0_3_schema.py"
  );

  assert.match(
    schema,
    /abstract_bust_blueprint:\s*Optional\[AbstractBustBlueprint\]\s*=\s*None/
  );
  assert.match(
    schema,
    /def _abstract_bust_projection_is_read_only/
  );
  assert.match(
    schema,
    /module_blueprint\s*!=\s*self\.abstract_bust_blueprint\.model_dump/
  );
  assert.doesNotMatch(
    schema,
    /abstract_bust_blueprint:\s*AbstractBustBlueprint(?!\])/
  );
});


test("B6 frontend keeps compile and export behind the existing server gate", () => {
  const store = readRepoFile("apps/web/src/store/canvas-store.ts");
  const api = readRepoFile("apps/web/src/lib/api.ts");

  assert.match(
    store,
    /canExportDR:\s*result\.valid\s*&&\s*result\.compiled_dr\s*!=\s*null/
  );
  assert.match(
    store,
    /set\(\{\s*compiledDR:\s*null,\s*drCompileResult:\s*null,\s*canExportDR:\s*false\s*\}\)/
  );
  assert.match(
    api,
    /compiled_dr:\s*Record<string,\s*unknown>\s*\|\s*null/
  );
  assert.doesNotMatch(
    store,
    /abstract_bust_blueprint\s*[:=]\s*(?:getDefault|normalize)/
  );
});


test("B6 adds no frontend projection store or runtime rendering state", () => {
  const packageJson = JSON.parse(
    readRepoFile("apps/web/package.json")
  );
  const script = packageJson.scripts["test:abstract-bust-dr-projection"];

  assert.equal(
    script,
    "node --experimental-strip-types --test tests/abstract-bust-dr-projection.test.mjs"
  );
  assert.equal(
    JSON.stringify(packageJson).includes("abstract_bust_blueprint"),
    false
  );
});
