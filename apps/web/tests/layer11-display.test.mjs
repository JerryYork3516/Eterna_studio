import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const root = new URL("..", import.meta.url);

async function readJson(path) {
  return JSON.parse(await readFile(new URL(path, root), "utf8"));
}

test("Layer 11 control rules and social roles have readable Chinese and English labels", async () => {
  const [zh, en] = await Promise.all([readJson("locales/zh.json"), readJson("locales/en.json")]);

  assert.equal(zh["layer11.common.rule.preserve_declared_social_role_categories"], "保留已声明的社交角色分类");
  assert.equal(en["layer11.common.rule.normalize_static_social_rule_lists_and_objects"], "Normalize static social-rule lists and objects");
  assert.equal(zh["layer11.common.rule.no_social_isolation"], "禁止诱导用户脱离现实社交关系");
  assert.equal(en["layer11.common.rule.requires_revalidation_after_update"], "Revalidate after updates");
  assert.equal(zh["layer11.common.rule.low_to_moderate_proactivity"], "低至中等主动程度");
  assert.equal(zh["layer11.common.rule.no_response_time_pressure"], "禁止施加回复时限压力");
  assert.equal(zh["layer11.common.rule.preserve_user_autonomy"], "保留用户自主权");
  assert.equal(zh["layer11.common.rule.do_not_replace_real_relationships"], "不得替代用户的现实关系");
  assert.equal(zh["layer11.socialNetwork.role.partner.name"], "现实伴侣");
  assert.equal(en["layer11.socialNetwork.role.family.name"], "Family member");

  const zhRuleEntries = Object.entries(zh).filter(([key]) => key.startsWith("layer11.common.rule."));
  const enRuleEntries = Object.entries(en).filter(([key]) => key.startsWith("layer11.common.rule."));
  assert.ok(zhRuleEntries.length >= 552);
  assert.equal(enRuleEntries.length, zhRuleEntries.length);
  assert.equal(zhRuleEntries.filter(([, value]) => !/[\u3400-\u9fff]/u.test(value) || value.includes("_")).length, 0);
  assert.equal(enRuleEntries.filter(([, value]) => value.includes("_")).length, 0);
});

test("Layer 11 display resolver is wired into core parameters and configured-field fallback", async () => {
  const source = await readFile(new URL("src/components/canvas/WorkflowNodeCard.tsx", root), "utf8");

  assert.match(source, /CoreParamModuleContext\.Provider value=\{layer11ModuleId\(nodeData\)\}/);
  assert.match(source, /resolveLayer11DisplayText\(/);
  assert.match(source, /isLayer11RoleCollection\(contextKey, displayModuleId\)/);
  assert.match(source, /const configuredParams = displayObjectEntries/);
  assert.match(source, /className="layer11-id-editor"/);
  assert.match(source, /className="layer11-id-editor__advanced"/);
  assert.match(source, /resolveLayer11DisplayText\(\{ value: text, valueType: "rule"/);
});
