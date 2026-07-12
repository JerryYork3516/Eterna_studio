import { translate, type Language } from "@/i18n";

type Layer11DisplayKind = "key" | "value" | "rule" | "policy" | "output" | "status";

const MODULE_PREFIX: Record<string, string> = {
  user_relationship: "userRelationship",
  intimacy_level: "relationshipStage",
  role_positioning: "trustMechanism",
  relationship_rule: "relationshipBehavior",
  module_social: "socialNetwork",
  interaction_history: "groupRelationship",
};

const OUTPUT_MODULES: Record<string, string> = {
  user_relationship_config: "userRelationship",
  relationship_stage_config: "relationshipStage",
  trust_mechanism_config: "trustMechanism",
  relationship_behavior_config: "relationshipBehavior",
  social_network_config: "socialNetwork",
  group_relationship_config: "groupRelationship",
};

const ROLE_COLLECTIONS: Record<string, string> = {
  social_role_categories: "role",
  group_role_categories: "role",
};

function translateIfPresent(language: Language, key: string): string {
  const marker = `__missing_${key}__`;
  const result = translate(language, key, marker);
  return result === marker ? "" : result;
}

function camelCase(value: string): string {
  return value.replace(/_([a-z0-9])/g, (_, letter: string) => letter.toUpperCase());
}

function readableIdentifier(value: string): string {
  return value
    .replace(/([a-z0-9])([A-Z])/g, "$1 $2")
    .replace(/[_-]+/g, " ")
    .replace(/\s+/g, " ")
    .trim()
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

export function layer11ModuleId(data: Record<string, unknown>): string | undefined {
  const direct = [data.module_id, data.catalog_module_id, data.moduleId].find((value) => typeof value === "string" && MODULE_PREFIX[value]);
  if (typeof direct === "string") return direct;
  const parentModule = typeof data.parent_module === "string" ? data.parent_module : "";
  const moduleId = parentModule.split("::")[1];
  return moduleId && MODULE_PREFIX[moduleId] ? moduleId : undefined;
}

export function isLayer11Module(moduleId?: string): boolean {
  return Boolean(moduleId && MODULE_PREFIX[moduleId]);
}

export function resolveLayer11DisplayText({
  value,
  valueType,
  moduleId,
  language,
}: {
  value: string;
  valueType: Layer11DisplayKind;
  moduleId?: string;
  language: Language;
}): string {
  const prefix = moduleId ? MODULE_PREFIX[moduleId] : undefined;
  const normalized = value.replace(/([a-z0-9])([A-Z])/g, "$1_$2").toLowerCase();
  const fieldKey = camelCase(normalized);
  const outputPrefix = OUTPUT_MODULES[value];
  const candidates = [
    outputPrefix ? `layer11.${outputPrefix}.output` : "",
    prefix ? `layer11.${prefix}.field.${fieldKey}.label` : "",
    prefix ? `layer11.${prefix}.validation.${fieldKey}` : "",
    prefix === "relationshipStage" ? `layer11.relationshipStage.stage.${value}.name` : "",
    prefix === "trustMechanism" ? `layer11.trustMechanism.dimension.${value}.name` : "",
    prefix === "socialNetwork" ? `layer11.socialNetwork.role.${value}.name` : "",
    prefix === "groupRelationship" ? `layer11.groupRelationship.role.${value}.name` : "",
    `layer11.common.${valueType === "policy" ? "policy" : "rule"}.${value}`,
    `layer11.common.${valueType === "policy" ? "rule" : "policy"}.${value}`,
    `layer11.common.status.${value}`,
    `node.coreParams.value.${value}`,
    `node.coreParams.key.${value}`,
    `validation.${value}`,
  ];
  const translated = candidates.map((key) => (key ? translateIfPresent(language, key) : "")).find(Boolean);
  if (translated) return translated;
  return language === "zh" ? translate(language, "layer11.common.unmappedIdentifier", "配置规则") : readableIdentifier(value);
}

export function resolveLayer11RoleDescription({
  roleId,
  moduleId,
  language,
}: {
  roleId: string;
  moduleId?: string;
  language: Language;
}): string {
  const prefix = moduleId ? MODULE_PREFIX[moduleId] : undefined;
  const key = prefix === "socialNetwork" ? `layer11.socialNetwork.role.${roleId}.description` : prefix === "groupRelationship" ? `layer11.groupRelationship.role.${roleId}.description` : "";
  return key ? translateIfPresent(language, key) : "";
}

export function isLayer11RoleCollection(key: string, moduleId?: string): boolean {
  return Boolean(moduleId && ROLE_COLLECTIONS[key] && (moduleId === "module_social" || moduleId === "interaction_history"));
}
