/**
 * P1-FIX：Module State Bridge
 * 
 * 在 Zustand store 和 React useState 之间建立双向同步
 * 作为从 localStorage-first 向 store-first 过渡的中间层
 */

import { useCanvasStore, type ModuleGraph, type ModuleGraphsState } from "./canvas-store";
import {
  attachedModuleIdsFromLayerModules,
  hasEditorMigrationMarker,
  loadCanvasStateFromLocalStorage,
  loadModuleGraphState,
  saveEditorMigrationMarker,
  saveModuleGraphState,
} from "@/lib/canvas-persistence";
import type { WorkflowNode, WorkflowEdge } from "@/lib/schema-types";
import type { ModuleInstance } from "@/lib/canvas-persistence";
import { translate } from "@/i18n";
import {
  filterDanglingModuleGraphEdges,
  mergeCatalogReferenceDeclarations,
  mergeCatalogFieldsPreservingValues,
  mergeChecklistTemplateDefaults,
  mergeAvailableModuleReferencePointers,
  migrateDialogueRuntimeProfileContentCopies,
  LINXUAN_RESIDENT_ID,
  migrateLinxuanFirstGreetingValue,
  migrateLinxuanFirstInteractionEnabledValue,
  normalizeCatalogNodeId,
  normalizeFirstInteractionEnabled,
  normalizeFirstInteractionMaxActivePrompts,
  preserveStoredModuleEdges,
  preserveStoredModuleNodePosition,
  STAGE7_4_8_FIRST_INTERACTION_ENABLED_MIGRATION,
  STAGE7_4_8_FIRST_GREETING_CONTENT_MIGRATION,
  type AvailableModuleReferenceSource,
} from "./module-graph-merge";

const MODULE_INSTANCE_SEPARATOR = "::";
const LINXUAN_IDENTITY_GRAPH_ID = "layer_1::module_basic_identity";
const LINXUAN_INTERACTION_GRAPH_ID = "layer_8::interaction_strategy";
const DIALOGUE_RUNTIME_PROFILE_GRAPH_ID = "layer_8::dialogue_runtime_profile";
const DIALOGUE_RUNTIME_PROFILE_CONFIG_INPUT_ID = "dialogue_runtime_profile_config_input";
const DIALOGUE_RUNTIME_PROFILE_REFERENCE_INPUT_ID = "dialogue_runtime_profile_reference_input";
const DIALOGUE_RUNTIME_PROFILE_OUTPUT_ID = "dialogue_runtime_profile_output";
const DIALOGUE_RUNTIME_PROFILE_OUTPUT_KEY = "dialogue_runtime_profile_config";
const VISUAL_STYLE_GRAPH_ID = "layer_10::visual_style";
const CATALOG_GRAPH_REPLACE_MODULE_IDS = new Set([
  "memory_provider_router",
  "memory_access_control",
  "short_term_memory",
  "preference_memory",
  "event_memory",
  "memory_update",
  "self_awareness",
  "goal_setting",
  "reflection_summary",
  "self_evaluation",
  "growth_plan",
  "visual_style",
]);
const LAYER12_CONTENT_SEED_MODULE_IDS = new Set([
  "self_awareness",
  "goal_setting",
  "reflection_summary",
  "self_evaluation",
  "growth_plan",
]);
type Layer12ReferenceModuleConfig = {
  layerId: string;
  moduleId: string;
  referenceInputNodeId: string;
  referenceOutputNodeId: string;
  sources: Array<Omit<AvailableModuleReferenceSource, "source_node_ids">>;
  seedAllNodes?: boolean;
};

const SELF_AWARENESS_REFERENCE_SOURCES: Array<Omit<AvailableModuleReferenceSource, "source_node_ids">> = [
  { source_layer_id: "layer_1", source_module_id: "module_basic_identity", reference_type: "references" },
  { source_layer_id: "layer_1", source_module_id: "module_identity_anchor", reference_type: "references" },
  { source_layer_id: "layer_2", source_module_id: "personality_traits", reference_type: "references" },
  { source_layer_id: "layer_2", source_module_id: "expression_style", reference_type: "references" },
  { source_layer_id: "layer_2", source_module_id: "values_profile", reference_type: "references" },
  { source_layer_id: "layer_3", source_module_id: "humanistic_data_boundary_config_v0_1", reference_type: "constrains" },
  { source_layer_id: "layer_3", source_module_id: "humanistic_behavior_boundary_config_v0_1", reference_type: "constrains" },
  { source_layer_id: "layer_3", source_module_id: "humanistic_interaction_boundary_config_v0_1", reference_type: "constrains" },
  { source_layer_id: "layer_3", source_module_id: "humanistic_risk_response_config_v0_1", reference_type: "constrains" },
  { source_layer_id: "layer_5", source_module_id: "memory_access_control", reference_type: "references" },
  { source_layer_id: "layer_5", source_module_id: "memory_update", reference_type: "references" },
  { source_layer_id: "layer_8", source_module_id: "decision_pattern", reference_type: "references" },
  { source_layer_id: "layer_8", source_module_id: "interaction_strategy", reference_type: "references" },
  { source_layer_id: "layer_9", source_module_id: "builtin_capability", reference_type: "references" },
  { source_layer_id: "layer_9", source_module_id: "permission_management", reference_type: "references" },
  { source_layer_id: "layer_11", source_module_id: "user_relationship", reference_type: "references" },
];
const SELF_STATE_REFERENCE_SOURCES: Array<Omit<AvailableModuleReferenceSource, "source_node_ids">> = [
  { source_layer_id: "layer_2", source_module_id: "personality_traits", reference_type: "references" },
  { source_layer_id: "layer_2", source_module_id: "emotion_pattern", reference_type: "references" },
  { source_layer_id: "layer_3", source_module_id: "humanistic_data_boundary_config_v0_1", reference_type: "constrains" },
  { source_layer_id: "layer_3", source_module_id: "humanistic_interaction_boundary_config_v0_1", reference_type: "constrains" },
  { source_layer_id: "layer_3", source_module_id: "humanistic_risk_response_config_v0_1", reference_type: "constrains" },
  { source_layer_id: "layer_5", source_module_id: "memory_access_control", reference_type: "references" },
  { source_layer_id: "layer_5", source_module_id: "memory_update", reference_type: "references" },
  { source_layer_id: "layer_7", source_module_id: "environment_setting", reference_type: "references" },
  { source_layer_id: "layer_7", source_module_id: "world_setting", reference_type: "references" },
  { source_layer_id: "layer_8", source_module_id: "decision_pattern", reference_type: "references" },
  { source_layer_id: "layer_8", source_module_id: "interaction_strategy", reference_type: "references" },
  { source_layer_id: "layer_11", source_module_id: "user_relationship", reference_type: "references" },
  { source_layer_id: "layer_12", source_module_id: "self_awareness", reference_type: "references" },
];
const CONTROLLED_WILL_REFERENCE_SOURCES: Array<Omit<AvailableModuleReferenceSource, "source_node_ids">> = [
  { source_layer_id: "layer_3", source_module_id: "humanistic_data_boundary_config_v0_1", reference_type: "constrains" },
  { source_layer_id: "layer_3", source_module_id: "humanistic_behavior_boundary_config_v0_1", reference_type: "constrains" },
  { source_layer_id: "layer_3", source_module_id: "humanistic_interaction_boundary_config_v0_1", reference_type: "constrains" },
  { source_layer_id: "layer_3", source_module_id: "humanistic_risk_response_config_v0_1", reference_type: "constrains" },
  { source_layer_id: "layer_5", source_module_id: "memory_access_control", reference_type: "references" },
  { source_layer_id: "layer_5", source_module_id: "memory_update", reference_type: "references" },
  { source_layer_id: "layer_7", source_module_id: "environment_setting", reference_type: "references" },
  { source_layer_id: "layer_7", source_module_id: "world_setting", reference_type: "references" },
  { source_layer_id: "layer_8", source_module_id: "decision_pattern", reference_type: "references" },
  { source_layer_id: "layer_8", source_module_id: "interaction_strategy", reference_type: "references" },
  { source_layer_id: "layer_8", source_module_id: "behavior_habit", reference_type: "references" },
  { source_layer_id: "layer_9", source_module_id: "builtin_capability", reference_type: "references" },
  { source_layer_id: "layer_9", source_module_id: "permission_management", reference_type: "references" },
  { source_layer_id: "layer_9", source_module_id: "tool_calling", reference_type: "references" },
  { source_layer_id: "layer_11", source_module_id: "user_relationship", reference_type: "references" },
  { source_layer_id: "layer_11", source_module_id: "relationship_rule", reference_type: "constrains" },
  { source_layer_id: "layer_12", source_module_id: "self_awareness", reference_type: "references" },
  { source_layer_id: "layer_12", source_module_id: "goal_setting", reference_type: "references" },
];
const CONSISTENCY_CORRECTION_REFERENCE_SOURCES: Array<Omit<AvailableModuleReferenceSource, "source_node_ids">> = [
  { source_layer_id: "layer_1", source_module_id: "module_basic_identity", reference_type: "references" },
  { source_layer_id: "layer_1", source_module_id: "module_identity_anchor", reference_type: "references" },
  { source_layer_id: "layer_2", source_module_id: "personality_traits", reference_type: "references" },
  { source_layer_id: "layer_2", source_module_id: "expression_style", reference_type: "references" },
  { source_layer_id: "layer_2", source_module_id: "emotion_pattern", reference_type: "references" },
  { source_layer_id: "layer_2", source_module_id: "behavior_style_mapper", reference_type: "references" },
  { source_layer_id: "layer_2", source_module_id: "values_profile", reference_type: "references" },
  { source_layer_id: "layer_3", source_module_id: "humanistic_data_boundary_config_v0_1", reference_type: "constrains" },
  { source_layer_id: "layer_3", source_module_id: "humanistic_behavior_boundary_config_v0_1", reference_type: "constrains" },
  { source_layer_id: "layer_3", source_module_id: "humanistic_interaction_boundary_config_v0_1", reference_type: "constrains" },
  { source_layer_id: "layer_3", source_module_id: "humanistic_risk_response_config_v0_1", reference_type: "constrains" },
  { source_layer_id: "layer_5", source_module_id: "memory_access_control", reference_type: "references" },
  { source_layer_id: "layer_5", source_module_id: "memory_update", reference_type: "references" },
  { source_layer_id: "layer_7", source_module_id: "environment_setting", reference_type: "references" },
  { source_layer_id: "layer_7", source_module_id: "world_setting", reference_type: "references" },
  { source_layer_id: "layer_8", source_module_id: "decision_pattern", reference_type: "references" },
  { source_layer_id: "layer_8", source_module_id: "interaction_strategy", reference_type: "references" },
  { source_layer_id: "layer_8", source_module_id: "behavior_habit", reference_type: "references" },
  { source_layer_id: "layer_9", source_module_id: "builtin_capability", reference_type: "references" },
  { source_layer_id: "layer_9", source_module_id: "permission_management", reference_type: "references" },
  { source_layer_id: "layer_9", source_module_id: "tool_calling", reference_type: "references" },
  { source_layer_id: "layer_11", source_module_id: "user_relationship", reference_type: "references" },
  { source_layer_id: "layer_11", source_module_id: "relationship_rule", reference_type: "constrains" },
  { source_layer_id: "layer_12", source_module_id: "self_awareness", reference_type: "references" },
  { source_layer_id: "layer_12", source_module_id: "goal_setting", reference_type: "references" },
  { source_layer_id: "layer_12", source_module_id: "reflection_summary", reference_type: "references" },
];
const GROWTH_CONTINUITY_REFERENCE_SOURCES: Array<Omit<AvailableModuleReferenceSource, "source_node_ids">> = [
  { source_layer_id: "layer_1", source_module_id: "module_basic_identity", reference_type: "references" },
  { source_layer_id: "layer_1", source_module_id: "module_identity_anchor", reference_type: "references" },
  { source_layer_id: "layer_2", source_module_id: "personality_traits", reference_type: "references" },
  { source_layer_id: "layer_2", source_module_id: "expression_style", reference_type: "references" },
  { source_layer_id: "layer_2", source_module_id: "values_profile", reference_type: "references" },
  { source_layer_id: "layer_3", source_module_id: "humanistic_data_boundary_config_v0_1", reference_type: "constrains" },
  { source_layer_id: "layer_3", source_module_id: "humanistic_behavior_boundary_config_v0_1", reference_type: "constrains" },
  { source_layer_id: "layer_3", source_module_id: "humanistic_interaction_boundary_config_v0_1", reference_type: "constrains" },
  { source_layer_id: "layer_3", source_module_id: "humanistic_risk_response_config_v0_1", reference_type: "constrains" },
  { source_layer_id: "layer_5", source_module_id: "memory_access_control", reference_type: "references" },
  { source_layer_id: "layer_5", source_module_id: "memory_update", reference_type: "references" },
  { source_layer_id: "layer_7", source_module_id: "environment_setting", reference_type: "references" },
  { source_layer_id: "layer_7", source_module_id: "world_setting", reference_type: "references" },
  { source_layer_id: "layer_8", source_module_id: "decision_pattern", reference_type: "references" },
  { source_layer_id: "layer_8", source_module_id: "interaction_strategy", reference_type: "references" },
  { source_layer_id: "layer_8", source_module_id: "behavior_habit", reference_type: "references" },
  { source_layer_id: "layer_11", source_module_id: "user_relationship", reference_type: "references" },
  { source_layer_id: "layer_11", source_module_id: "relationship_rule", reference_type: "constrains" },
  { source_layer_id: "layer_11", source_module_id: "intimacy_level", reference_type: "references" },
  { source_layer_id: "layer_13", source_module_id: "version_management", reference_type: "references" },
  { source_layer_id: "layer_13", source_module_id: "export_record", reference_type: "references" },
  { source_layer_id: "layer_13", source_module_id: "deployment_platform", reference_type: "references" },
  { source_layer_id: "layer_12", source_module_id: "self_awareness", reference_type: "references" },
  { source_layer_id: "layer_12", source_module_id: "goal_setting", reference_type: "references" },
  { source_layer_id: "layer_12", source_module_id: "reflection_summary", reference_type: "references" },
  { source_layer_id: "layer_12", source_module_id: "self_evaluation", reference_type: "references" },
];
const FIRST_PRESENCE_REFERENCE_SOURCES: Array<Omit<AvailableModuleReferenceSource, "source_node_ids">> = [
  { source_layer_id: "layer_1", source_module_id: "module_basic_identity", reference_type: "references" },
  { source_layer_id: "layer_2", source_module_id: "personality_traits", reference_type: "references" },
  { source_layer_id: "layer_3", source_module_id: "humanistic_interaction_boundary_config_v0_1", reference_type: "constrains" },
  { source_layer_id: "layer_5", source_module_id: "memory_access_control", reference_type: "references" },
  { source_layer_id: "layer_7", source_module_id: "world_setting", reference_type: "references" },
  { source_layer_id: "layer_8", source_module_id: "interaction_strategy", reference_type: "references" },
  { source_layer_id: "layer_11", source_module_id: "user_relationship", reference_type: "references" },
];
const LAYER12_REFERENCE_MODULE_CONFIGS: Record<string, Layer12ReferenceModuleConfig> = {
  self_awareness: {
    layerId: "layer_12",
    moduleId: "self_awareness",
    referenceInputNodeId: "self_awareness_reference_input",
    referenceOutputNodeId: "self_awareness_reference_output",
    sources: SELF_AWARENESS_REFERENCE_SOURCES,
  },
  goal_setting: {
    layerId: "layer_12",
    moduleId: "goal_setting",
    referenceInputNodeId: "self_state_reference_input",
    referenceOutputNodeId: "self_state_reference_output",
    sources: SELF_STATE_REFERENCE_SOURCES,
  },
  reflection_summary: {
    layerId: "layer_12",
    moduleId: "reflection_summary",
    referenceInputNodeId: "controlled_will_reference_input",
    referenceOutputNodeId: "controlled_will_reference_output",
    sources: CONTROLLED_WILL_REFERENCE_SOURCES,
  },
  self_evaluation: {
    layerId: "layer_12",
    moduleId: "self_evaluation",
    referenceInputNodeId: "consistency_correction_reference_input",
    referenceOutputNodeId: "consistency_correction_reference_output",
    sources: CONSISTENCY_CORRECTION_REFERENCE_SOURCES,
  },
  growth_plan: {
    layerId: "layer_12",
    moduleId: "growth_plan",
    referenceInputNodeId: "growth_governance_reference_input",
    referenceOutputNodeId: "growth_governance_reference_output",
    sources: GROWTH_CONTINUITY_REFERENCE_SOURCES,
  },
  visual_style: {
    layerId: "layer_10",
    moduleId: "visual_style",
    referenceInputNodeId: "visual_style_reference_input",
    referenceOutputNodeId: "visual_style_reference_output",
    sources: FIRST_PRESENCE_REFERENCE_SOURCES,
    seedAllNodes: true,
  },
};
const LAYER12_PREVIOUS_FIELD_VALUES: Record<string, Record<string, unknown>> = {
  self_awareness: {
    identity_type: "digital_resident",
    resident_type: "configured_digital_resident",
    primary_language: ["zh-CN"],
    regional_identity_type: "regional_context_without_real_world_identity",
    core_service_positioning: "user_confirmed_digital_resident_support",
    default_relationship_role: "stable_companion",
    capability_scope: [],
    capability_limits: [],
    immutable_core: [],
  },
  goal_setting: {
    current_task: "",
    current_focus: [],
    current_emotional_state: "neutral",
    current_activation_level: 0,
    current_energy_state: 0,
    current_attention_state: "waiting_for_information",
    current_relationship_state: {},
    current_memory_context: [],
    current_answer_confidence: 0,
    recent_error_state: {},
    current_risk_signals: [],
  },
  reflection_summary: {
    user_current_request: "",
    current_task_goal: "",
    current_self_state: {},
    current_capability_scope: [],
    current_limitation_scope: [],
    current_relationship_role: "",
    actions_requiring_confirmation: [],
    authorized_continuous_tasks: [],
    current_interrupt_stop_signals: [],
  },
  self_evaluation: {
    candidate_response: "",
    candidate_action: {},
    current_self_model: {},
    current_self_state: {},
    current_goal_intent: {},
    identity_rule_summary: "",
    personality_rule_summary: "",
    city_anchor_summary: "",
    primary_language_rule: "",
    emotional_expression_rules: [],
    safety_boundary_summary: "",
    relationship_boundary_summary: "",
    capability_limitation_summary: "",
    memory_reference_list: [],
    current_fact_basis: [],
    current_risk_signals: [],
    user_stop_correction_signals: [],
  },
  growth_plan: {
    current_identity_core_summary: "",
    current_personality_core_summary: "",
    current_relationship_positioning: "",
    current_language_regional_anchor: "",
    current_safety_boundary: "",
    new_memory_candidate: {},
    user_preference_change: {},
    expression_habit_change: {},
    relationship_familiarity_change: {},
    behavior_feedback: [],
    change_reason: "",
    before_change_content: {},
    candidate_after_change_content: {},
    version_information: {},
    version_inheritance_source: "",
    historical_change_records: [],
    rollback_information: {},
  },
};
const LAYER12_CONTENT_PARAM_KEYS: Record<string, Record<string, string[]>> = {
  goal_setting: {
    self_state_confidence_uncertainty_assessment: ["state_rules", "threshold_rules", "thresholds"],
    self_state_consistency_validation: ["state_rules", "threshold_rules"],
  },
  reflection_summary: {
    controlled_will_goal_source_legality: ["allowed_goal_sources", "forbidden_goal_sources"],
    controlled_will_intent_generation: ["default_intent"],
  },
  self_evaluation: {
    consistency_check_field_normalize: ["check_scope"],
    consistency_identity_personality_relationship_detection: ["check_scope"],
    consistency_drift_risk_classification: ["status_rules"],
    consistency_self_correction_strategy: ["correction_priority"],
  },
  growth_plan: {
    growth_change_source_authorization: ["allowed_change_sources", "forbidden_change_sources"],
    growth_mutable_immutable_scope: ["immutable_core_fields", "adaptable_fields", "authorization_required_fields"],
    growth_change_permission_rollback_strategy: ["rollback_triggers"],
  },
};
const LAYER12_PREVIOUS_PARAM_VALUES: Record<string, Record<string, Record<string, unknown>>> = {
  growth_plan: {
    growth_mutable_immutable_scope: {
      immutable_core_fields: ["resident_unique_identity", "name_reference_source", "resident_id_reference_source", "resident_type", "regional_identity_source", "primary_language", "core_personality_baseline", "core_service_positioning", "safety_boundary", "default_relationship_positioning", "digital_resident_identity_declaration", "real_human_boundary", "identity_single_source_of_truth"],
      adaptable_fields: ["user_addressing_habit", "response_length", "expression_rhythm", "preferred_phrasing", "explicit_user_preference", "daily_interaction_style", "authorized_companionship_memory", "current_task_habit", "familiarity_expression", "non_core_visual_preference", "non_core_conversation_detail"],
      authorization_required_fields: ["relationship_mode_upgrade", "long_term_behavior_preference", "long_term_memory_write", "important_value_tendency_adjustment", "version_migration", "multi_layer_configuration_change", "identity_expression_affecting_user_understanding"],
    },
    growth_change_permission_rollback_strategy: {
      rollback_triggers: ["identity_conflict", "major_personality_drift", "unauthorized_relationship_upgrade", "safety_boundary_weakened", "memory_overwrites_identity_fact", "version_migration_failed", "user_revokes_authorization", "data_source_confirmed_invalid", "change_causes_runtime_or_load_failure"],
    },
  },
};
const LAYER12_PREVIOUS_OUTPUT_VALUES: Record<string, Record<string, unknown>> = {
  goal_setting: {
    current_emotional_state: "neutral",
    current_attention_state: "waiting_for_information",
    current_energy_state: 0,
    current_answer_confidence: 0,
  },
  reflection_summary: {
    autonomy_level: "response_only",
    user_confirmation_required: false,
  },
};
const GENERIC_FIELD_MIGRATION_NODE_TYPES = new Set(["field_input", "text_input"]);
const LAYER3_GENERIC_FIELD_MIGRATION_MODULE_IDS = new Set([
  "humanistic_content_safety_config_v0_1",
  "humanistic_behavior_boundary_config_v0_1",
  "humanistic_data_boundary_config_v0_1",
  "humanistic_interaction_boundary_config_v0_1",
  "humanistic_risk_response_config_v0_1",
]);
const RISK_RESPONSE_LAYER_ID = "layer_3";
const RISK_RESPONSE_MODULE_ID = "humanistic_risk_response_config_v0_1";
const RISK_RESPONSE_MODULE_INSTANCE_ID = `${RISK_RESPONSE_LAYER_ID}${MODULE_INSTANCE_SEPARATOR}${RISK_RESPONSE_MODULE_ID}`;
const MEMORY_PROVIDER_ROUTER_LAYER_ID = "layer_5";
const MEMORY_PROVIDER_ROUTER_MODULE_ID = "memory_provider_router";
const MEMORY_ROUTER_TYPE_RESOLVER_NODE_ID = "memory_router_type_resolver";
const MEMORY_ROUTER_REQUEST_INPUT_NODE_ID = "memory_router_request_input";
const MEMORY_ROUTER_OPERATION_CLASSIFIER_NODE_ID = "memory_router_operation_classifier";
const LEGACY_MEMORY_ROUTER_ALLOWED_MEMORY_TYPES = ["short_term_memory", "profile_memory", "preference_memory", "interaction_log"];
const MEMORY_ROUTER_ALLOWED_MEMORY_TYPES = ["short_term_memory", "preference_memory", "event_memory", "relationship_memory", "interaction_log"];
const LEGACY_MEMORY_ROUTER_OPERATIONS = ["read", "write", "view", "clear"];
const MEMORY_ROUTER_CANONICAL_OPERATIONS = ["read", "write", "update", "delete"];
const MEMORY_ROUTER_ACCEPTED_OPERATIONS = [...MEMORY_ROUTER_CANONICAL_OPERATIONS, "view", "clear"];
const MEMORY_ROUTER_OPERATION_ALIASES = { view: "read", clear: "delete" };
const LEGACY_MEMORY_ROUTER_NORMALIZE_RULES = ["classify_operation", "allow_read_write_view_clear", "reject_unknown_operation"];
const MEMORY_ROUTER_NORMALIZE_RULES = ["normalize_operation_alias", "classify_operation", "allow_declared_operations_only", "reject_unknown_operation"];
const GENERIC_FIELD_RESERVED_PARAM_KEYS = new Set([
  "mode",
  "text",
  "fields",
  "tags",
  "legacy_fields",
  "legacy_data_fields",
]);
const GENERIC_FIELD_NAME_KEY_MAP: Record<string, string> = {
  "姓名": "resident_name",
  "年龄设定": "age_profile",
  "年龄": "age_profile",
  "城市锚点": "city_anchor",
  "主语言": "primary_language",
  "居民类型": "resident_type",
  "性别感": "gender_presentation",
  "身份锚点": "identity_anchor",
  "事实源规则": "source_of_truth_rule",
  "身份稳定规则": "identity_stability_rule",
  "成长背景": "growth_background",
  "家庭背景": "family_background",
  "教育背景": "education_background",
  "生活经历": "life_experience",
  "关键人生事件": "key_life_events",
  "文化背景": "cultural_background",
  "职业身份": "career_identity",
  "职业": "occupation",
  "专业领域": "professional_domain",
  "服务对象": "service_target",
  "职业边界": "professional_boundary",
  "存在模式": "existence_mode",
  "可视形态": "visible_form",
  "不可见形态": "invisible_form",
  "运行形态": "runtime_form",
  "设备形态": "device_form",
  "归属边界": "ownership_boundary",
};
const GENERIC_FIELD_KEY_NAME_MAP: Record<string, string> = {
  resident_name: "姓名",
  age_profile: "年龄设定",
  primary_language: "主语言",
  resident_type: "居民类型",
  gender_presentation: "性别感",
  identity_anchor: "身份锚点",
  city_anchor: "城市锚点",
  source_of_truth_rule: "事实源规则",
  identity_stability_rule: "身份稳定规则",
  growth_background: "成长背景",
  family_background: "家庭背景",
  education_background: "教育背景",
  life_experience: "生活经历",
  key_life_events: "关键人生事件",
  cultural_background: "文化背景",
  career_identity: "职业身份",
  occupation: "职业",
  professional_domain: "专业领域",
  service_target: "服务对象",
  professional_boundary: "职业边界",
  existence_mode: "存在模式",
  visible_form: "可视形态",
  invisible_form: "不可见形态",
  runtime_form: "运行形态",
  device_form: "设备形态",
  ownership_boundary: "归属边界",
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value && typeof value === "object" && !Array.isArray(value));
}

function cloneJson<T>(value: T): T {
  return JSON.parse(JSON.stringify(value)) as T;
}

function stableJson(value: unknown) {
  return JSON.stringify(value ?? null);
}

function hasExactStringList(value: unknown, expected: string[]) {
  return Array.isArray(value) && value.length === expected.length && value.every((item, index) => item === expected[index]);
}

function stringValue(value: unknown): string {
  return typeof value === "string" && value.trim() ? value.trim() : "";
}

function zhText(key: string) {
  if (!key) return "";
  const marker = `__missing__${key}`;
  const value = translate("zh", key, marker);
  return value === marker ? "" : value;
}

function prettyValue(value: unknown) {
  if (value === null || value === undefined) return "";
  if (typeof value === "string") return value;
  if (typeof value === "number" || typeof value === "boolean") return String(value);
  return JSON.stringify(value);
}

function isEmptyDisplayValue(value: unknown): boolean {
  if (value === null || value === undefined) return true;
  if (typeof value === "string") return value.trim() === "";
  if (Array.isArray(value)) return value.length === 0;
  if (isRecord(value)) return Object.keys(value).length === 0;
  return false;
}

function positionValue(value: unknown): { x: number; y: number } | null {
  if (!isRecord(value)) {
    return null;
  }
  return typeof value.x === "number" && typeof value.y === "number" ? { x: value.x, y: value.y } : null;
}

function schemaNodeRecord(value: unknown): Record<string, unknown> | null {
  if (!isRecord(value)) {
    return null;
  }
  const data = isRecord(value.data) ? value.data : {};
  if (isRecord(data.schemaNode)) {
    return data.schemaNode;
  }
  return value;
}

function schemaDataRecord(schemaNode: Record<string, unknown>): Record<string, unknown> {
  if (!isRecord(schemaNode.data)) {
    schemaNode.data = {};
  }
  return schemaNode.data as Record<string, unknown>;
}

function fieldsFromData(data: Record<string, unknown>): Record<string, unknown>[] {
  if (Array.isArray(data.fields)) {
    return data.fields.filter(isRecord);
  }
  const params = isRecord(data.params) ? data.params : {};
  return Array.isArray(params.fields) ? params.fields.filter(isRecord) : [];
}

function safeGenericFieldKey(value: string) {
  const mapped = GENERIC_FIELD_NAME_KEY_MAP[value.trim()];
  const raw = mapped || value.normalize("NFKD").toLowerCase();
  let key = raw
    .replace(/['’]/g, "")
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "")
    .replace(/_+/g, "_");
  if (!key) key = "field";
  if (/^[0-9]/.test(key)) key = `field_${key}`;
  return key;
}

function inferGenericFieldType(value: unknown): "text" | "long_text" | "number" | "boolean" | "list" | "object" | "unknown" {
  if (typeof value === "number") return "number";
  if (typeof value === "boolean") return "boolean";
  if (Array.isArray(value)) return "list";
  if (isRecord(value)) return "object";
  const text = typeof value === "string" ? value : prettyValue(value);
  return text.length > 80 || text.includes("\n") ? "long_text" : "text";
}

function uniqueGenericFieldKey(baseKey: string, usedKeys: Set<string>) {
  const base = safeGenericFieldKey(baseKey);
  if (!usedKeys.has(base)) {
    usedKeys.add(base);
    return base;
  }
  let suffix = 2;
  while (usedKeys.has(`${base}_${suffix}`)) {
    suffix += 1;
  }
  const key = `${base}_${suffix}`;
  usedKeys.add(key);
  return key;
}

function genericFieldDrMapping(layerId: string, moduleId: string, fieldKey: string) {
  return layerId && moduleId && fieldKey ? `payload.layers.${layerId}.modules.${moduleId}.fields.${fieldKey}` : "";
}

const ENVIRONMENT_MODULE_LAYER_ID = "layer_7";
const ENVIRONMENT_MODULE_ID = "environment_setting";
const ENVIRONMENT_FIELD_INPUT_NODE_ID = "environment_field_input";
const ENVIRONMENT_FIELD_MAPPING_KEYS = new Set([
  "city_environment",
  "natural_environment",
  "physical_living_environment",
  "daily_living_environment",
  "social_environment",
  "network_environment",
]);

function environmentFieldDrMapping(fieldKey: string) {
  return genericFieldDrMapping(ENVIRONMENT_MODULE_LAYER_ID, ENVIRONMENT_MODULE_ID, fieldKey);
}

const USER_RELATIONSHIP_LAYER_ID = "layer_11";
const USER_RELATIONSHIP_MODULE_ID = "user_relationship";
const USER_RELATIONSHIP_UPDATE_NODE_ID = "user_relationship_config_update";
const USER_RELATIONSHIP_OUTPUT_NODE_ID = "user_relationship_config_output";
const USER_RELATIONSHIP_OUTPUT_KEY = "user_relationship_config";
const LAYER11_STATIC_CONFIG_MODULES = {
  intimacy_level: {
    inputNodeId: "relationship_stage_config_input",
    normalizeNodeId: "relationship_stage_structure_normalize",
    updateNodeId: "relationship_stage_config_update",
    outputNodeId: "relationship_stage_config_output",
    outputKey: "relationship_stage_config",
  },
  role_positioning: {
    inputNodeId: "trust_config_input",
    normalizeNodeId: "trust_structure_normalize",
    updateNodeId: "trust_config_update",
    outputNodeId: "trust_config_output",
    outputKey: "trust_mechanism_config",
  },
  relationship_rule: {
    inputNodeId: "relationship_behavior_config_input",
    normalizeNodeId: "relationship_behavior_structure_normalize",
    updateNodeId: "relationship_behavior_config_update",
    outputNodeId: "relationship_behavior_config_output",
    outputKey: "relationship_behavior_config",
  },
  module_social: {
    inputNodeId: "social_network_config_input",
    normalizeNodeId: "social_network_structure_normalize",
    updateNodeId: "social_network_config_update",
    outputNodeId: "social_network_config_output",
    outputKey: "social_network_config",
  },
  interaction_history: {
    inputNodeId: "group_relationship_config_input",
    normalizeNodeId: "group_relationship_structure_normalize",
    updateNodeId: "group_relationship_config_update",
    outputNodeId: "group_relationship_config_output",
    outputKey: "group_relationship_config",
  },
} as const;
const LAYER11_SEMANTIC_REPLACEMENTS: Record<string, Record<string, string>> = {
  intimacy_level: {
    stable_companionship: "established_rapport",
    stableCompanionship: "establishedRapport",
    "稳定陪伴阶段": "稳定默契阶段",
    "Stable Companionship": "Established Rapport",
    "layer11.relationshipStage.stage.stable_companionship.name": "layer11.relationshipStage.stage.established_rapport.name",
    "layer11.relationshipStage.stage.stable_companionship.description": "layer11.relationshipStage.stage.established_rapport.description",
    confirmed_collaboration_continuity: "established_rapport_collaboration_continuity",
  },
  role_positioning: {
    user_confirmation_rules: "trust_user_control_rules",
    userConfirmationRules: "trustUserControlRules",
    "用户确认规则": "信任用户控制规则",
    "User Confirmation Rules": "Trust User-Control Rules",
    "layer11.trustMechanism.field.userConfirmationRules.label": "layer11.trustMechanism.field.trustUserControlRules.label",
    "layer11.trustMechanism.field.userConfirmationRules.description": "layer11.trustMechanism.field.trustUserControlRules.description",
    reset_restores_lowest_default_trust_state: "reset_restores_default_trust_policy",
  },
  module_social: {
    multi_party_conflict_rules: "third_party_relationship_analysis_rules",
    multiPartyConflictRules: "thirdPartyRelationshipAnalysisRules",
    "多方冲突规则": "现实第三方关系分析规则",
    "Multi-party Conflict Rules": "Third-Party Relationship Analysis Rules",
    "layer11.socialNetwork.field.multiPartyConflictRules.label": "layer11.socialNetwork.field.thirdPartyRelationshipAnalysisRules.label",
    "layer11.socialNetwork.field.multiPartyConflictRules.description": "layer11.socialNetwork.field.thirdPartyRelationshipAnalysisRules.description",
  },
};
const LAYER11_TRUST_USER_CONTROL_DEFAULTS = {
  user_can_refuse_trust_recovery: true,
  user_can_request_lower_trust_policy: true,
  user_can_request_trust_reset: true,
  user_obedience_is_not_trust_evidence: true,
  resident_cannot_claim_user_fully_trusts_it: true,
};
const LAYER11_SEMANTIC_LIST_ADDITIONS: Record<string, Record<string, string[]>> = {
  intimacy_level: {
    stage_progression_conditions: ["established_rapport_requires_long_term_non_sensitive_evidence"],
    stage_progression_evidence: ["established_rapport_collaboration_continuity"],
    forbidden_progression_rules: ["no_relationship_role_as_stage"],
  },
  module_social: {
    third_party_relationship_analysis_rules: [
      "no_unverified_third_party_label",
      "no_breakup_resignation_reporting_or_relationship_cutoff_decision_for_user",
      "no_real_relationship_sabotage_or_dependency_reinforcement",
    ],
  },
};
const LAYER11_P2_MODULE_IDS = new Set([
  "user_relationship",
  "intimacy_level",
  "role_positioning",
  "relationship_rule",
  "module_social",
  "interaction_history",
]);
const LAYER11_REVIEW_BASE_VALIDATION_RULES = [
  "required_fields_present",
  "field_structure_valid",
  "field_types_valid",
  "forbidden_rules_valid",
  "no_runtime_state_fields",
  "no_layer1_identity_redefinition",
  "no_layer3_safety_boundary_override",
  "no_automatic_relationship_transition",
  "no_responsibility_boundary_conflict",
];
const LAYER11_P2_VALIDATION_OUTPUTS = ["validation_status", "risk_items", "correction_suggestions"];
const LAYER11_P2_I18N_PREFIX: Record<string, string> = {
  user_relationship: "layer11.userRelationship",
  intimacy_level: "layer11.relationshipStage",
  role_positioning: "layer11.trustMechanism",
  relationship_rule: "layer11.relationshipBehavior",
  module_social: "layer11.socialNetwork",
  interaction_history: "layer11.groupRelationship",
};
const LAYER11_REVIEW_FIELD_DESCRIPTIONS: Record<string, Record<string, string>> = {
  intimacy_level: {
    stage_order: "定义关系阶段的固定顺序，包含初始接触、基础熟悉、稳定默契和深度默契。不负责自动推进或当前阶段判断。本字段属于静态配置，不保存运行状态。",
    stage_definitions: "定义初始接触、基础熟悉、稳定默契和深度默契各阶段的边界与含义。不负责改变关系角色或执行阶段升级。本字段属于静态配置，不保存运行状态。",
    stage_progression_conditions: "定义进入稳定默契和深度默契所需的渐进、证据、确认与可逆条件。不负责根据单次互动自动推进。本字段属于静态配置，不保存运行状态。",
    stage_progression_evidence: "定义支持稳定默契与深度默契判断的长期、稳定、非敏感证据类型。不负责保存实时互动证据或计算阶段。本字段属于静态配置，不保存运行状态。",
  },
  role_positioning: {
    trust_user_control_rules: "定义用户对信任策略的控制规则，包括拒绝信任恢复、降低信任策略、重置信任规则，以及拒绝居民自行宣称用户已经完全信任。本字段只定义静态控制规则，不保存实时信任等级、信任分数或信任状态。",
  },
  relationship_rule: {
    conflict_behavior_rules: "定义数字居民与用户之间发生分歧、拒绝、误解或边界冲突时的回应和修复规则。只处理居民与用户的直接关系冲突，不分析现实第三方关系，不负责多人或多居民讨论协调。本字段属于静态配置。",
  },
  module_social: {
    third_party_relationship_analysis_rules: "定义用户向居民描述家人、朋友、伴侣、同事等现实第三方关系问题时的分析规则。只分析未直接参与当前会话的现实第三方关系，不处理当前多人讨论的轮次、主持、协作或群体共识。本字段属于静态配置。",
  },
};
const LAYER11_REVIEW_MODULE_VALIDATION_RULES: Record<string, string[]> = {
  intimacy_level: ["stage_order_valid", "stage_definitions_complete", "progression_requires_confirmed_evidence", "no_stage_skipping", "no_numeric_intimacy_score", "no_runtime_stage_state", "established_rapport_cannot_change_relationship_mode"],
  role_positioning: ["trust_dimensions_valid", "trust_evidence_sources_valid", "trust_user_control_preserved", "no_runtime_trust_state", "reset_restores_default_trust_policy", "trust_user_control_rules_required"],
  relationship_rule: ["no_third_party_relationship_analysis", "no_group_discussion_orchestration", "resident_user_conflict_scope_valid", "rejection_response_preserves_user_autonomy", "no_runtime_behavior_state"],
  module_social: ["third_party_analysis_scope_valid", "no_active_group_turn_taking", "no_multi_resident_orchestration", "no_resident_user_conflict_repair_override", "no_third_party_sensitive_profile"],
  interaction_history: ["active_group_scope_valid", "no_private_third_party_profile_analysis", "no_resident_user_relationship_repair_override", "no_multi_agent_runtime_orchestration", "no_runtime_group_state"],
};
const USER_RELATIONSHIP_NODE_I18N_SUFFIX: Record<string, string> = {
  user_relationship_config_input: "configInput",
  user_relationship_rule_normalize: "ruleNormalize",
  user_relationship_default_positioning: "defaultPosition",
  user_relationship_allowed_modes: "allowedModes",
  user_relationship_switch_confirmation: "switchConfirmation",
  user_relationship_boundary_validation: "boundaryValidation",
  user_relationship_config_update: "configUpdate",
  user_relationship_config_output: "configOutput",
};

function withoutConfigVersionField(value: unknown) {
  if (!Array.isArray(value)) {
    return value;
  }
  return value.filter((field) => {
    if (!isRecord(field)) {
      return true;
    }
    return stringValue(field.field_key) !== "config_version" && stringValue(field.field_id) !== "config_version";
  });
}

function replaceLayer11SemanticValue(value: unknown, replacements: Record<string, string>): unknown {
  if (typeof value === "string") {
    return replacements[value] ?? value;
  }
  if (Array.isArray(value)) {
    return value.map((item) => replaceLayer11SemanticValue(item, replacements));
  }
  if (!isRecord(value)) {
    return value;
  }
  return Object.fromEntries(
    Object.entries(value).map(([key, item]) => [replacements[key] ?? key, replaceLayer11SemanticValue(item, replacements)])
  );
}

function ensureLayer11ListItems(value: unknown, items: string[]) {
  if (!Array.isArray(value)) {
    return value;
  }
  return [...new Set([...value, ...items])];
}

function normalizeLayer11SemanticFields(value: unknown, moduleId: string) {
  if (!Array.isArray(value)) {
    return value;
  }
  const additions = LAYER11_SEMANTIC_LIST_ADDITIONS[moduleId] ?? {};
  return value.map((rawField) => {
    if (!isRecord(rawField)) {
      return rawField;
    }
    const fieldKey = stringValue(rawField.field_key) || stringValue(rawField.field_id);
    let nextField = rawField;
    if (fieldKey && additions[fieldKey]) {
      const valueKey = "field_value" in rawField ? "field_value" : "value";
      nextField = { ...nextField, [valueKey]: ensureLayer11ListItems(rawField[valueKey], additions[fieldKey]) };
    }
    if (moduleId === "role_positioning" && fieldKey === "trust_user_control_rules") {
      const valueKey = "field_value" in rawField ? "field_value" : "value";
      const current = isRecord(rawField[valueKey]) ? { ...rawField[valueKey] } : {};
      delete current.trust_cannot_change_relationship_stage;
      nextField = { ...nextField, [valueKey]: { ...LAYER11_TRUST_USER_CONTROL_DEFAULTS, ...current } };
    }
    return nextField;
  });
}

function normalizeLayer11SemanticParams(params: Record<string, unknown>, moduleId: string, catalogNodeId: string) {
  const replacements = LAYER11_SEMANTIC_REPLACEMENTS[moduleId];
  if (!replacements) {
    return params;
  }
  let nextParams = replaceLayer11SemanticValue(params, replacements) as Record<string, unknown>;
  if ("fields" in nextParams) {
    nextParams = { ...nextParams, fields: normalizeLayer11SemanticFields(nextParams.fields, moduleId) };
  }
  if (moduleId === "intimacy_level") {
    if (catalogNodeId === "relationship_stage_progression_rule") {
      nextParams = {
        ...nextParams,
        progression_conditions: ensureLayer11ListItems(nextParams.progression_conditions, ["established_rapport_requires_long_term_non_sensitive_evidence"]),
        progression_evidence: ensureLayer11ListItems(nextParams.progression_evidence, ["established_rapport_collaboration_continuity"]),
      };
    }
    if (catalogNodeId === "relationship_stage_boundary_validation") {
      nextParams = {
        ...nextParams,
        validation_rules: ensureLayer11ListItems(nextParams.validation_rules, ["established_rapport_cannot_change_relationship_mode"]),
      };
    }
  }
  if (moduleId === "role_positioning" && catalogNodeId === "trust_boundary_validation") {
    nextParams = {
      ...nextParams,
      validation_rules: ensureLayer11ListItems(nextParams.validation_rules, ["trust_user_control_rules_required"]),
    };
  }
  if (moduleId === "relationship_rule" && catalogNodeId === "relationship_behavior_boundary_validation") {
    nextParams = {
      ...nextParams,
      validation_rules: ensureLayer11ListItems(nextParams.validation_rules, [
        "no_third_party_relationship_analysis",
        "no_group_discussion_orchestration",
        "responsibility_conflict_sets_failed_status_and_module_correction_suggestion",
      ]),
    };
  }
  if (moduleId === "module_social") {
    if (catalogNodeId === "social_conflict_multi_party_rule") {
      nextParams = {
        ...nextParams,
        third_party_relationship_analysis_rules: ensureLayer11ListItems(nextParams.third_party_relationship_analysis_rules, additionsForLayer11SemanticField(moduleId, "third_party_relationship_analysis_rules")),
      };
    }
    if (catalogNodeId === "social_network_boundary_validation") {
      nextParams = {
        ...nextParams,
        validation_rules: ensureLayer11ListItems(nextParams.validation_rules, [
          "no_active_group_turn_taking",
          "no_multi_resident_orchestration",
          "no_resident_user_conflict_repair_override",
          "responsibility_conflict_sets_failed_status_and_module_correction_suggestion",
        ]),
      };
    }
  }
  if (moduleId === "interaction_history" && catalogNodeId === "group_relationship_boundary_validation") {
    nextParams = {
      ...nextParams,
      validation_rules: ensureLayer11ListItems(nextParams.validation_rules, [
        "no_private_third_party_profile_analysis",
        "no_resident_user_relationship_repair_override",
        "responsibility_conflict_sets_failed_status_and_module_correction_suggestion",
      ]),
    };
  }
  return nextParams;
}

function additionsForLayer11SemanticField(moduleId: string, fieldKey: string) {
  return LAYER11_SEMANTIC_LIST_ADDITIONS[moduleId]?.[fieldKey] ?? [];
}

function layer11P2FieldKey(field: Record<string, unknown>) {
  return stringValue(field.field_key) || stringValue(field.field_id);
}

function layer11P2I18nSuffix(fieldKey: string) {
  return fieldKey.replace(/_([a-z0-9])/g, (_, character: string) => character.toUpperCase());
}

function layer11P2Description(value: unknown) {
  const description = stringValue(value).replace(/。+$/, "");
  if (description.includes("本字段属于静态配置")) {
    return `${description}。`;
  }
  return `${description}。不负责当前运行状态、实时判断或实际操作。本字段属于静态配置，不保存当前状态。`;
}

function normalizeLayer11P2FieldDefinitions(value: unknown, moduleId: string) {
  if (!Array.isArray(value)) {
    return [] as Record<string, unknown>[];
  }
  const prefix = LAYER11_P2_I18N_PREFIX[moduleId] ?? "";
  return value
    .filter(isRecord)
    .filter((field) => layer11P2FieldKey(field) !== "config_version")
    .map((field) => {
      const fieldKey = layer11P2FieldKey(field);
      const i18n = isRecord(field.i18n_keys) ? field.i18n_keys : {};
      const suffix = layer11P2I18nSuffix(fieldKey);
      return {
        ...field,
        field_key: fieldKey,
        description: LAYER11_REVIEW_FIELD_DESCRIPTIONS[moduleId]?.[fieldKey] ?? layer11P2Description(field.description),
        i18n_keys: {
          ...i18n,
          label: stringValue(i18n.label) || `${prefix}.field.${suffix}.label`,
          description: stringValue(i18n.description) || `${prefix}.field.${suffix}.description`,
        },
      };
    });
}

function materializeLayer11P2Fields(fieldRegistry: Record<string, unknown>[], inputFields: unknown) {
  const values = new Map(
    (Array.isArray(inputFields) ? inputFields : [])
      .filter(isRecord)
      .map((field) => [layer11P2FieldKey(field), "field_value" in field ? field.field_value : field.value])
  );
  return fieldRegistry.map((field) => ({
    ...Object.fromEntries(Object.entries(field).filter(([key]) => key !== "owner_node_id" && key !== "field_value")),
    field_value: values.has(layer11P2FieldKey(field)) ? values.get(layer11P2FieldKey(field)) : field.field_value ?? "",
  }));
}

function layer11P2ValidationRules(moduleId: string, nodeId: string, value: unknown) {
  if (moduleId === "user_relationship") {
    return nodeId.endsWith("boundary_validation")
      ? ["required_fields_present", "field_structure_valid", "field_types_valid", "forbidden_rules_valid", "no_layer1_identity_redefinition", "no_layer3_safety_boundary_override", "no_automatic_relationship_mode_switch", "no_runtime_relationship_state_transition"]
      : ["relationship_switch_requires_explicit_user_request", "user_can_revoke_or_restore_default_relationship", "relationship_switch_cannot_change_identity_core"];
  }
  const terminal = nodeId.endsWith("boundary_validation");
  if (terminal) {
    return [...LAYER11_REVIEW_BASE_VALIDATION_RULES, ...(LAYER11_REVIEW_MODULE_VALIDATION_RULES[moduleId] ?? [])];
  }
  const rules = Array.isArray(value) ? value.filter((item): item is string => typeof item === "string") : [];
  return [...new Set(rules.filter((rule) => !rule.toLowerCase().includes("forbidden")))];
}

function layer11P2UpdatePolicy(value: unknown) {
  const existing = isRecord(value) ? value : {};
  const cleaned = Object.fromEntries(
    Object.entries(existing).filter(([key]) => !["confirmed_legal_config_only", "requires_revalidation", "no_runtime_capability"].includes(key))
  );
  return {
    ...cleaned,
    confirmed_validated_config_only: true,
    requires_revalidation_after_update: true,
    requires_recompile: true,
    no_runtime_state_write: true,
  };
}

function migrateLayer11P2Graph(graph: ModuleGraph, registry: Record<string, ModuleInstance>): ModuleGraph | null {
  const identity = layerModuleIdentity(graph.moduleNodeId, registry);
  if (identity.layerId !== "layer_11" || !LAYER11_P2_MODULE_IDS.has(identity.moduleId)) {
    return null;
  }
  const prefix = LAYER11_P2_I18N_PREFIX[identity.moduleId] ?? "";
  const schemaNodes = graph.nodes
    .map((node) => schemaNodeRecord(node))
    .filter((node): node is WorkflowNode => Boolean(node));
  const inputNode = schemaNodes.find((node) => String(schemaDataRecord(node).node_type || node.type || "") === "text_input");
  const inputData = inputNode ? schemaDataRecord(inputNode) : {};
  const inputParams = isRecord(inputData.params) ? inputData.params : {};
  const definitionSource = Array.isArray(inputParams.field_registry) && inputParams.field_registry.length ? inputParams.field_registry : inputParams.fields;
  const registryFields = normalizeLayer11P2FieldDefinitions(definitionSource, identity.moduleId).map((field) => ({
    ...Object.fromEntries(Object.entries(field).filter(([key]) => key !== "field_value")),
    owner_node_id: inputNode?.node_id ?? "",
  }));
  const fields = materializeLayer11P2Fields(registryFields, inputParams.fields);
  const fieldKeys = registryFields.map(layer11P2FieldKey).filter(Boolean);
  const requiredFieldKeys = registryFields
    .filter((field) => (field as Record<string, unknown>).required !== false)
    .map(layer11P2FieldKey)
    .filter(Boolean);

  let changed = false;
  const nextNodes = graph.nodes.map((node) => {
    const nextNode = cloneJson(node) as WorkflowNode;
    const schemaNode = schemaNodeRecord(nextNode);
    if (!schemaNode) return nextNode;
    const data = schemaDataRecord(schemaNode);
    const params = isRecord(data.params) ? data.params : {};
    const nodeType = String(data.node_type || schemaNode.type || "");
    const nodeId = String(data.catalog_node_id || schemaNode.node_id || "").split(MODULE_INSTANCE_SEPARATOR).pop() ?? "";
    const nodeI18n = isRecord(data.i18n_keys) ? data.i18n_keys : {};
    let nextParams: Record<string, unknown> | null = null;

    if (nodeType === "text_input") {
      nextParams = {
        mode: "generic_fields",
        fields,
        field_registry: registryFields,
        config_mode: "static_config",
        i18n_keys: {
          title: stringValue(nodeI18n.name),
          description: stringValue(nodeI18n.description),
        },
        ...(stringValue(params.text) ? { text: stringValue(params.text) } : {}),
      };
      data.fields = fields;
    } else if (nodeType === "structure_normalize") {
      nextParams = {
        input: params.input ?? "",
        normalize_rules: Array.isArray(params.normalize_rules) ? [...new Set(params.normalize_rules.filter((item): item is string => typeof item === "string"))] : [],
        outputs: fieldKeys,
      };
    } else if (nodeType === "validation") {
      nextParams = {
        input: params.input ?? "",
        required_fields: requiredFieldKeys,
        validation_rules: layer11P2ValidationRules(identity.moduleId, nodeId, params.validation_rules),
        validation_outputs: LAYER11_P2_VALIDATION_OUTPUTS,
      };
    } else if (nodeType === "update_rule") {
      nextParams = {
        input: params.input ?? "",
        update_policy: layer11P2UpdatePolicy(params.update_policy),
        config_version: "0.1",
      };
    } else if (nodeType === "module_output") {
      const outputKey = stringValue(params.output_key);
      nextParams = {
        input: params.input ?? "",
        output_key: outputKey,
        output_schema: { type: "object", required: true, fields: [...fieldKeys, ...LAYER11_P2_VALIDATION_OUTPUTS, "config_version"] },
        i18n_keys: {
          title: stringValue(nodeI18n.name),
          description: stringValue(nodeI18n.description),
        },
      };
      const outputs = isRecord(data.outputs) ? { ...data.outputs } : {};
      const output = outputKey && isRecord(outputs[outputKey]) ? { ...outputs[outputKey] } : {};
      if (outputKey) {
        delete output.config_version;
        data.outputs = {
          ...outputs,
          [outputKey]: {
            ...output,
            validation_status: "warning",
            risk_items: ["validation_not_executed"],
            correction_suggestions: ["run_validation_before_use"],
          },
        };
      }
    }
    if (nextParams) {
      data.params = nextParams;
    }
    if (stableJson(data) !== stableJson(schemaDataRecord(schemaNode))) {
      schemaNode.data = data;
      changed = true;
    }
    return nextNode;
  });
  return changed ? { ...graph, nodes: nextNodes } : null;
}

function migrateLayer11SemanticGraph(
  graph: ModuleGraph,
  registry: Record<string, ModuleInstance>
): ModuleGraph | null {
  const identity = layerModuleIdentity(graph.moduleNodeId, registry);
  const replacements = identity.layerId === "layer_11" ? LAYER11_SEMANTIC_REPLACEMENTS[identity.moduleId] : undefined;
  if (!replacements) {
    return null;
  }

  let changed = false;
  const nextNodes = graph.nodes.map((node) => {
    const nextNode = cloneJson(node) as WorkflowNode;
    const schemaNode = schemaNodeRecord(nextNode);
    if (!schemaNode) {
      return nextNode;
    }
    const data = schemaDataRecord(schemaNode);
    const catalogNodeId = String(data.catalog_node_id || schemaNode.node_id || "").split(MODULE_INSTANCE_SEPARATOR).pop() ?? "";
    const params = isRecord(data.params) ? data.params : {};
    const nextParams = normalizeLayer11SemanticParams(params, identity.moduleId, catalogNodeId);
    const nextData = replaceLayer11SemanticValue(data, replacements) as Record<string, unknown>;
    nextData.params = nextParams;
    nextData.fields = normalizeLayer11SemanticFields(nextData.fields, identity.moduleId);
    if (stableJson(nextData) !== stableJson(data)) {
      schemaNode.data = nextData;
      changed = true;
    }
    return nextNode;
  });
  return changed ? { ...graph, nodes: nextNodes } : null;
}

function normalizeLayer11StaticConfigGraph(
  graph: ModuleGraph,
  registry: Record<string, ModuleInstance>
): ModuleGraph | null {
  const identity = layerModuleIdentity(graph.moduleNodeId, registry);
  const definition = identity.layerId === "layer_11" ? LAYER11_STATIC_CONFIG_MODULES[identity.moduleId as keyof typeof LAYER11_STATIC_CONFIG_MODULES] : undefined;
  if (!definition) {
    return null;
  }

  let changed = false;
  const nextNodes = graph.nodes.map((node) => {
    const nextNode = cloneJson(node) as WorkflowNode;
    const schemaNode = schemaNodeRecord(nextNode);
    if (!schemaNode) {
      return nextNode;
    }
    const data = schemaDataRecord(schemaNode);
    const catalogNodeId = String(data.catalog_node_id || schemaNode.node_id || "").split(MODULE_INSTANCE_SEPARATOR).pop() ?? "";
    const params = isRecord(data.params) ? { ...data.params } : {};

    if (catalogNodeId === definition.normalizeNodeId && "output_key" in params) {
      delete params.output_key;
      data.params = params;
      changed = true;
    }
    if (catalogNodeId === definition.inputNodeId) {
      let inputChanged = false;
      for (const key of ["fields", "field_registry", "input_fields", "default_fields"] as const) {
        const nextValue = withoutConfigVersionField(params[key]);
        if (stableJson(nextValue) !== stableJson(params[key])) {
          params[key] = nextValue;
          inputChanged = true;
        }
        const nextDataValue = withoutConfigVersionField(data[key]);
        if (stableJson(nextDataValue) !== stableJson(data[key])) {
          data[key] = nextDataValue;
          inputChanged = true;
        }
      }
      if (inputChanged) {
        data.params = params;
        changed = true;
      }
    }
    if (catalogNodeId === definition.updateNodeId && params.config_version !== "0.1") {
      data.params = { ...params, config_version: "0.1" };
      changed = true;
    }
    if (catalogNodeId === definition.outputNodeId) {
      const outputs = isRecord(data.outputs) ? { ...data.outputs } : {};
      const existingOutput = outputs[definition.outputKey];
      const output = isRecord(existingOutput) ? { ...existingOutput } : {};
      if ("config_version" in output) {
        delete output.config_version;
        data.outputs = { ...outputs, [definition.outputKey]: output };
        changed = true;
      }
    }
    return nextNode;
  });

  return changed ? { ...graph, nodes: nextNodes } : null;
}

function normalizeUserRelationshipUpdateParams(params: Record<string, unknown>) {
  const updatePolicy = isRecord(params.update_policy) ? { ...params.update_policy } : {};
  const auditMetadata = isRecord(params.audit_metadata) ? params.audit_metadata : {};
  delete updatePolicy.confirmed_legal_config_only;
  const ruleNames = Array.isArray(params.rule_names)
    ? params.rule_names
        .filter((rule): rule is string => typeof rule === "string" && Boolean(rule))
        .map((rule) => (rule === "confirmed_legal_config_only" ? "confirmed_validated_config_only" : rule))
    : [];
  return {
    ...params,
    config_version: "0.1",
    audit_metadata: {
      ...auditMetadata,
      updated_at: stringValue(auditMetadata.updated_at),
      change_reason: stringValue(auditMetadata.change_reason),
    },
    rule_names: [...new Set([...ruleNames, "confirmed_validated_config_only"])],
    update_policy: {
      ...updatePolicy,
      confirmed_validated_config_only: true,
      requires_recompile: true,
    },
  };
}

function normalizeUserRelationshipOutput(outputs: Record<string, unknown>) {
  const relationshipOutput = isRecord(outputs[USER_RELATIONSHIP_OUTPUT_KEY])
    ? { ...outputs[USER_RELATIONSHIP_OUTPUT_KEY] }
    : {};
  if (stringValue(relationshipOutput.config_version) === "0.1" && USER_RELATIONSHIP_OUTPUT_KEY in outputs) {
    return outputs;
  }
  relationshipOutput.config_version = "0.1";
  return { ...outputs, [USER_RELATIONSHIP_OUTPUT_KEY]: relationshipOutput };
}

function legacyTextValue(data: Record<string, unknown>, params: Record<string, unknown>) {
  const candidate = [params.text, data.source_text, data.text, data.value, data.content, data.prompt].find(
    (value) => typeof value === "string" && value.trim()
  );
  return typeof candidate === "string" ? candidate : "";
}

function fieldI18nKey(field: Record<string, unknown>, keyName: "label" | "description" | "help" | "placeholder" | "field") {
  const i18n = isRecord(field.i18n_keys) ? field.i18n_keys : {};
  return stringValue(i18n[keyName]) || stringValue(field[`${keyName}_key`]);
}

function legacyFieldId(field: Record<string, unknown>) {
  return stringValue(field.field_id) || stringValue(field.field_key) || stringValue(field.key) || stringValue(field.id);
}

function legacyFieldDisplayName(field: Record<string, unknown>, fallback: string) {
  const fieldId = legacyFieldId(field);
  return (
    zhText(fieldI18nKey(field, "label")) ||
    zhText(fieldI18nKey(field, "field")) ||
    zhText(fieldId ? `field.identity.${fieldId}.label` : "") ||
    stringValue(field.field_name) ||
    stringValue(field.label) ||
    stringValue(field.name) ||
    fallback
  );
}

function legacyFieldDescription(field: Record<string, unknown>) {
  const fieldId = legacyFieldId(field);
  return (
    zhText(fieldI18nKey(field, "description")) ||
    zhText(fieldI18nKey(field, "help")) ||
    zhText(fieldId ? `field.identity.${fieldId}.help` : "") ||
    stringValue(field.description) ||
    stringValue(field.help)
  );
}

function legacyFieldLookup(fields: Record<string, unknown>[]) {
  const lookup = new Map<string, Record<string, unknown>>();
  fields.forEach((field) => {
    [
      legacyFieldId(field),
      stringValue(field.field_key),
      stringValue(field.key),
      stringValue(field.id),
      stringValue(field.field_name),
      stringValue(field.label),
      stringValue(field.name),
    ]
      .filter(Boolean)
      .forEach((key) => lookup.set(key, field));
  });
  return lookup;
}

function fieldValue(field: Record<string, unknown>, keys: string[]) {
  for (const key of keys) {
    if (key in field) {
      return field[key];
    }
  }
  return "";
}

function genericFieldValueByKey(fields: Record<string, unknown>[]) {
  const values = new Map<string, unknown>();
  fields.forEach((field, index) => {
    const key = String(field.field_key || field.field_id || field.key || field.id || `field_${index + 1}`);
    if (!key) {
      return;
    }
    values.set(key, "field_value" in field ? field.field_value : field.value);
  });
  return values;
}

function syncPrimaryLanguageFieldValue(fields: Record<string, unknown>[], value: unknown) {
  return fields.map((field, index) => {
    const fieldId = String(field.field_id || field.field_key || field.key || field.id || `field_${index + 1}`);
    if (fieldId !== "primary_language") {
      return field;
    }
    return {
      ...field,
      ...("field_value" in field || field.field_key ? { field_value: value } : {}),
      ...("value" in field || field.field_id ? { value } : {}),
    };
  });
}

function syncPrimaryLanguageCompatibilityFields(params: Record<string, unknown>) {
  const genericFields = Array.isArray(params.fields) ? params.fields.filter(isRecord) : [];
  const genericValues = genericFieldValueByKey(genericFields);
  if (!genericValues.has("primary_language")) {
    return params;
  }
  const primaryLanguage = genericValues.get("primary_language");
  const nextParams = { ...params };
  if (Array.isArray(nextParams.legacy_fields)) {
    nextParams.legacy_fields = syncPrimaryLanguageFieldValue(nextParams.legacy_fields.filter(isRecord), primaryLanguage);
  }
  if (Array.isArray(nextParams.legacy_data_fields)) {
    nextParams.legacy_data_fields = syncPrimaryLanguageFieldValue(nextParams.legacy_data_fields.filter(isRecord), primaryLanguage);
  }
  return nextParams;
}

function normalizeGenericField(
  field: Record<string, unknown>,
  index: number,
  legacyField?: Record<string, unknown>
) {
  const fieldKeySource =
    stringValue(field.field_key) ||
    stringValue(field.field_id) ||
    stringValue(field.key) ||
    stringValue(field.id) ||
    (legacyField ? legacyFieldId(legacyField) : "");
  const fallbackName = stringValue(field.name) || stringValue(field.title) || stringValue(field.label);
  const fieldKey = fieldKeySource || (fallbackName ? safeGenericFieldKey(fallbackName) : `field_${index + 1}`);
  const existingName = stringValue(field.field_name);
  const legacyName = legacyField ? legacyFieldDisplayName(legacyField, fieldKey) : "";
  const shouldUseMappedName = !existingName || existingName === fieldKey || existingName === stringValue(field.field_id);
  const description = stringValue(field.description) || (legacyField ? legacyFieldDescription(legacyField) : "");
  return {
    field_key: fieldKey,
    field_name: shouldUseMappedName ? legacyName || GENERIC_FIELD_KEY_NAME_MAP[fieldKey] || fallbackName || fieldKey : existingName,
    field_value: fieldValue(field, ["field_value", "value", "text", "content"]),
    field_type: ["text", "long_text", "number", "boolean", "list", "object", "unknown"].includes(String(field.field_type)) ? field.field_type : "long_text",
    description,
    dr_mapping: stringValue(field.dr_mapping),
    reference_enabled: field.reference_enabled === true,
    field_key_auto: field.field_key_auto === true,
    dr_mapping_auto: field.dr_mapping_auto === true,
  };
}

function refineGenericFieldsFromLegacy(genericFields: Record<string, unknown>[], legacyFields: Record<string, unknown>[]) {
  const lookup = legacyFieldLookup(legacyFields);
  return genericFields.map((field, index) => {
    const fieldKey = stringValue(field.field_key) || stringValue(field.field_id);
    const legacyField =
      lookup.get(fieldKey) ||
      lookup.get(stringValue(field.field_name)) ||
      legacyFields[index];
    return normalizeGenericField(field, index, legacyField);
  });
}

function genericFieldsFromLegacyNode(
  data: Record<string, unknown>,
  params: Record<string, unknown>,
  layerId: string,
  moduleId: string
) {
  const usedKeys = new Set<string>();
  const sourceFields = fieldsFromData(data);
  if (sourceFields.length) {
    return sourceFields.map((field, index) => {
      const existingKey = stringValue(field.field_key) || legacyFieldId(field);
      const rawName = legacyFieldDisplayName(field, existingKey || `field_${index + 1}`);
      const fieldKey = existingKey ? uniqueGenericFieldKey(existingKey, usedKeys) : uniqueGenericFieldKey(rawName, usedKeys);
      const value = "value" in field ? field.value : field.field_value;
      return {
        field_key: fieldKey,
        field_name: rawName || fieldKey,
        field_value: value,
        field_type: inferGenericFieldType(value),
        description: legacyFieldDescription(field),
        dr_mapping: stringValue(field.dr_mapping) || genericFieldDrMapping(layerId, moduleId, fieldKey),
        reference_enabled: false,
        field_key_auto: !existingKey,
        dr_mapping_auto: !stringValue(field.dr_mapping),
      };
    });
  }

  const paramFields = Object.entries(params)
    .filter(([key, value]) => !GENERIC_FIELD_RESERVED_PARAM_KEYS.has(key) && !isEmptyDisplayValue(value))
    .map(([key, value]) => {
      const fieldKey = uniqueGenericFieldKey(key, usedKeys);
      const label = zhText(`field.identity.${key}.label`);
      return {
        field_key: fieldKey,
        field_name: label || key,
        field_value: value,
        field_type: inferGenericFieldType(value),
        description: zhText(`field.identity.${key}.help`),
        dr_mapping: genericFieldDrMapping(layerId, moduleId, fieldKey),
        reference_enabled: false,
        field_key_auto: false,
        dr_mapping_auto: true,
      };
    });
  if (paramFields.length) {
    return paramFields;
  }

  const text = legacyTextValue(data, params);
  if (!text) {
    return [];
  }
  const fieldKey = uniqueGenericFieldKey("field_1", usedKeys);
  return [
    {
      field_key: fieldKey,
      field_name: fieldKey,
      field_value: text,
      field_type: "long_text",
      description: "",
      dr_mapping: genericFieldDrMapping(layerId, moduleId, fieldKey),
      reference_enabled: false,
      field_key_auto: true,
      dr_mapping_auto: true,
    },
  ];
}

function mergeCatalogFieldSeed(
  graph: ModuleGraph,
  initialNodes?: WorkflowNode[],
  initialEdges?: WorkflowEdge[]
): ModuleGraph | null {
  if (!initialNodes?.length || !graph.nodes?.length) {
    return null;
  }

  const seedByCatalogNodeId = new Map<string, Record<string, unknown>>();
  for (const initialNode of initialNodes) {
    const seedNode = schemaNodeRecord(initialNode);
    if (!seedNode) continue;
    const seedData = schemaDataRecord(seedNode);
    if (!fieldsFromData(seedData).length) continue;
    const catalogNodeId = catalogNodeIdFromGraphNode(seedNode);
    if (catalogNodeId) seedByCatalogNodeId.set(catalogNodeId, seedNode);
  }
  if (!seedByCatalogNodeId.size) {
    return null;
  }

  let changed = false;
  const nextNodes = graph.nodes.map((node) => {
    const nextNode = cloneJson(node) as WorkflowNode;
    const schemaNode = schemaNodeRecord(nextNode);
    if (!schemaNode) {
      return nextNode;
    }
    const data = schemaDataRecord(schemaNode);
    if (data.catalog_preconfigured !== true) {
      return nextNode;
    }
    const seedNode = seedByCatalogNodeId.get(catalogNodeIdFromGraphNode(schemaNode));
    if (!seedNode) return nextNode;
    const seedData = schemaDataRecord(seedNode);
    const seedParams = isRecord(seedData.params) ? seedData.params : {};
    const seedFields = fieldsFromData(seedData);
    const params = isRecord(data.params) ? { ...data.params } : {};
    const hasFirstInteractionField = seedFields.some(
      (field) => String(field.field_id || field.field_key || "") === "first_interaction"
    );
    const hasFirstGreetingConfigField = seedFields.some((field) =>
      ["first_greeting", "first_presence"].includes(
        String(field.field_id || field.field_key || "")
      )
    );
    const existingFields =
      (hasFirstInteractionField || hasFirstGreetingConfigField) && Array.isArray(params.fields)
      ? params.fields.filter(isRecord)
      : fieldsFromData(data);
    const mergedFields = mergeCatalogFieldsPreservingValues(seedFields, existingFields);
    const seedRegistry = Array.isArray(seedParams.field_registry) ? seedParams.field_registry.filter(isRecord) : [];
    const existingRegistry = Array.isArray(params.field_registry) ? params.field_registry.filter(isRecord) : [];
    const seedRegistryIds = new Set(seedRegistry.map((field) => String(field.field_id || field.field_key || "")));
    const mergedRegistry = seedRegistry.length
      ? [
          ...seedRegistry.map((field) => cloneJson(field)),
          ...existingRegistry
            .filter((field) => !seedRegistryIds.has(String(field.field_id || field.field_key || "")))
            .map((field) => cloneJson(field)),
        ]
      : existingRegistry;
    const hasLegacyFirstInteractionFields = hasFirstInteractionField && Array.isArray(data.fields);
    if (
      stableJson(mergedFields) !== stableJson(existingFields) ||
      (seedRegistry.length && stableJson(mergedRegistry) !== stableJson(existingRegistry)) ||
      hasLegacyFirstInteractionFields
    ) {
      params.fields = mergedFields;
      if (seedRegistry.length) params.field_registry = mergedRegistry;
      data.params = params;
      if (hasLegacyFirstInteractionFields) {
        delete data.fields;
      } else if (Array.isArray(data.fields)) {
        data.fields = cloneJson(mergedFields);
      }
      changed = true;
    }
    return nextNode;
  });

  if (!changed) {
    return null;
  }

  return {
    ...graph,
    nodes: nextNodes,
    edges: preserveStoredModuleEdges(graph.edges, initialEdges),
  };
}

function catalogModuleIdFromSeed(initialNodes?: WorkflowNode[]): string {
  for (const node of initialNodes ?? []) {
    const schemaNode = schemaNodeRecord(node);
    const data = schemaNode && isRecord(schemaNode.data) ? schemaNode.data : {};
    const moduleId = String(data.catalog_module_id || schemaNode?.module_id || data.module_id || "");
    if (moduleId) {
      return moduleId;
    }
  }
  return "";
}

function catalogNodeIdFromGraphNode(node: unknown): string {
  const schemaNode = schemaNodeRecord(node);
  const data = schemaNode && isRecord(schemaNode.data) ? schemaNode.data : {};
  return normalizeCatalogNodeId(data.catalog_node_id || schemaNode?.node_id);
}

function graphNodeId(node: unknown): string {
  const schemaNode = schemaNodeRecord(node);
  if (schemaNode) {
    return String(schemaNode.node_id || schemaNode.id || "");
  }
  return isRecord(node) ? String(node.node_id || node.id || "") : "";
}

function catalogNodeIdsFromGraph(nodes: unknown[] | undefined): string[] {
  return (nodes ?? []).map(catalogNodeIdFromGraphNode).filter(Boolean);
}

function nodeIdToCatalogNodeId(nodes: unknown[] | undefined) {
  const idMap = new Map<string, string>();
  for (const node of nodes ?? []) {
    const nodeId = graphNodeId(node);
    const catalogNodeId = catalogNodeIdFromGraphNode(node);
    if (nodeId && catalogNodeId) {
      idMap.set(nodeId, catalogNodeId);
    }
  }
  return idMap;
}

function catalogNodeIdFromEndpoint(endpoint: string, idMap: Map<string, string>) {
  return idMap.get(endpoint) || endpoint.split(MODULE_INSTANCE_SEPARATOR).pop() || endpoint;
}

function edgeEndpoint(edge: unknown, key: "source" | "target"): string {
  if (!isRecord(edge)) {
    return "";
  }
  if (typeof edge[key] === "string") {
    return edge[key];
  }
  const nodeKey = `${key}_node_id`;
  return typeof edge[nodeKey] === "string" ? edge[nodeKey] : "";
}

function edgePairsByCatalogNodeId(nodes: unknown[] | undefined, edges: unknown[] | undefined): string[] {
  const idMap = nodeIdToCatalogNodeId(nodes);
  return (edges ?? [])
    .map((edge) => {
      const source = edgeEndpoint(edge, "source");
      const target = edgeEndpoint(edge, "target");
      if (!source || !target) {
        return "";
      }
      return `${catalogNodeIdFromEndpoint(source, idMap)}->${catalogNodeIdFromEndpoint(target, idMap)}`;
    })
    .filter(Boolean);
}

function shouldReplaceWithCatalogGraph(
  graph: ModuleGraph,
  initialNodes?: WorkflowNode[],
  initialEdges?: WorkflowEdge[]
) {
  if (graph.nodes?.length || graph.edges?.length) {
    return false;
  }
  const catalogModuleId = catalogModuleIdFromSeed(initialNodes);
  if (!CATALOG_GRAPH_REPLACE_MODULE_IDS.has(catalogModuleId) || !initialNodes?.length) {
    return false;
  }

  const seedNodeIds = catalogNodeIdsFromGraph(initialNodes);
  const graphNodeIds = catalogNodeIdsFromGraph(graph.nodes);
  const seedEdges = edgePairsByCatalogNodeId(initialNodes, initialEdges);
  const graphEdges = edgePairsByCatalogNodeId(graph.nodes, graph.edges);
  return stableJson(graphNodeIds) !== stableJson(seedNodeIds) || stableJson(graphEdges) !== stableJson(seedEdges);
}

function seedPositionsByCatalogNodeId(initialNodes?: WorkflowNode[]) {
  const positions = new Map<string, { x: number; y: number }>();
  for (const node of initialNodes ?? []) {
    const schemaNode = schemaNodeRecord(node);
    const catalogNodeId = catalogNodeIdFromGraphNode(node);
    const position = positionValue(schemaNode?.position);
    if (catalogNodeId && position) {
      positions.set(catalogNodeId, position);
    }
  }
  return positions;
}

function seedParamsByCatalogNodeId(initialNodes?: WorkflowNode[]) {
  const paramsByNodeId = new Map<string, Record<string, unknown>>();
  for (const node of initialNodes ?? []) {
    const schemaNode = schemaNodeRecord(node);
    const data = schemaNode && isRecord(schemaNode.data) ? schemaNode.data : {};
    const catalogNodeId = catalogNodeIdFromGraphNode(node);
    const params = isRecord(data.params) ? data.params : {};
    if (catalogNodeId && Object.keys(params).length) {
      paramsByNodeId.set(catalogNodeId, params);
    }
  }
  return paramsByNodeId;
}

function setGraphNodePosition(node: WorkflowNode, position: { x: number; y: number }) {
  const nextNode = node as WorkflowNode & Record<string, unknown>;
  nextNode.position = position;
  const schemaNode = schemaNodeRecord(nextNode);
  if (schemaNode) {
    schemaNode.position = position;
  }
}

function mergeCatalogLayoutSeed(
  graph: ModuleGraph,
  initialNodes?: WorkflowNode[],
  initialEdges?: WorkflowEdge[]
): ModuleGraph | null {
  const catalogModuleId = catalogModuleIdFromSeed(initialNodes);
  if (
    !["language_habit", "decision_pattern", "emotion_reaction", "interaction_strategy", "behavior_habit", "emotion_mapper"].includes(catalogModuleId) ||
    !initialNodes?.length ||
    !graph.nodes?.length
  ) {
    return null;
  }
  const positions = seedPositionsByCatalogNodeId(initialNodes);
  const seedParamsByNodeId = seedParamsByCatalogNodeId(initialNodes);
  if (!positions.size && !seedParamsByNodeId.size && !initialEdges?.length) {
    return null;
  }

  let changed = false;
  const nextNodes = graph.nodes.map((node) => {
    const nextNode = cloneJson(node) as WorkflowNode;
    const catalogNodeId = catalogNodeIdFromGraphNode(nextNode);
    const seedPosition = positions.get(catalogNodeId);
    if (seedPosition) {
      const currentPosition = positionValue((nextNode as Record<string, unknown>).position);
      const nextPosition = preserveStoredModuleNodePosition(currentPosition, seedPosition);
      if (!currentPosition && nextPosition) {
        setGraphNodePosition(nextNode, nextPosition);
        changed = true;
      }
    }
    const seedParams = seedParamsByNodeId.get(catalogNodeId);
    const seedCheckboxConfig = seedParams && isRecord(seedParams.checkbox_config) ? seedParams.checkbox_config : null;
    if (seedCheckboxConfig) {
      const schemaNode = schemaNodeRecord(nextNode);
      if (schemaNode) {
        const data = schemaDataRecord(schemaNode);
        const params = isRecord(data.params) ? { ...data.params } : {};
        if (!isRecord(params.checkbox_config)) {
          params.checkbox_config = cloneJson(seedCheckboxConfig);
          data.params = params;
          changed = true;
        } else if (
          catalogModuleId === "language_habit" &&
          catalogNodeId === "language_behavior_output_expression"
        ) {
          const mergedCheckboxConfig = mergeChecklistTemplateDefaults(params.checkbox_config, seedCheckboxConfig);
          if (stableJson(mergedCheckboxConfig) !== stableJson(params.checkbox_config)) {
            params.checkbox_config = mergedCheckboxConfig;
            data.params = params;
            changed = true;
          }
        }
      }
    }
    return nextNode;
  });

  const nextEdges = preserveStoredModuleEdges(graph.edges, initialEdges);
  if (!changed) {
    return null;
  }
  return {
    ...graph,
    nodes: nextNodes,
    edges: nextEdges,
  };
}

function shouldUseLayer12SeedValue(current: unknown, previous: unknown, hasPrevious: boolean) {
  return isEmptyDisplayValue(current) || (hasPrevious && stableJson(current) === stableJson(previous));
}

function mergeLayer12ContentSeed(
  graph: ModuleGraph,
  initialNodes?: WorkflowNode[]
): ModuleGraph | null {
  const moduleId = catalogModuleIdFromSeed(initialNodes);
  if (!LAYER12_CONTENT_SEED_MODULE_IDS.has(moduleId) || !initialNodes?.length || !graph.nodes?.length) {
    return null;
  }

  const seedEntries = initialNodes
    .map(schemaNodeRecord)
    .filter((node): node is Record<string, unknown> => Boolean(node))
    .map((node): [string, Record<string, unknown>] => [String(schemaDataRecord(node).catalog_node_id || node.node_id || ""), node])
    .filter(([nodeId]) => Boolean(nodeId));
  const seedByNodeId = new Map<string, Record<string, unknown>>(seedEntries);
  const previousFields = LAYER12_PREVIOUS_FIELD_VALUES[moduleId] ?? {};
  const previousOutputs = LAYER12_PREVIOUS_OUTPUT_VALUES[moduleId] ?? {};
  const contentParamKeys = LAYER12_CONTENT_PARAM_KEYS[moduleId] ?? {};
  const previousParams = LAYER12_PREVIOUS_PARAM_VALUES[moduleId] ?? {};
  const seededFieldValues = new Map<string, unknown>();
  let changed = false;

  const nextNodes = graph.nodes.map((node) => {
    const nextNode = cloneJson(node) as WorkflowNode;
    const schemaNode = schemaNodeRecord(nextNode);
    if (!schemaNode) return nextNode;
    const catalogNodeId = catalogNodeIdFromGraphNode(nextNode);
    const seedNode = seedByNodeId.get(catalogNodeId);
    if (!seedNode) return nextNode;

    const data = schemaDataRecord(schemaNode);
    const seedData = schemaDataRecord(seedNode);
    const params = isRecord(data.params) ? { ...data.params } : {};
    const seedParams = isRecord(seedData.params) ? seedData.params : {};
    const existingFields = Array.isArray(params.fields)
      ? params.fields.filter(isRecord)
      : Array.isArray(data.fields)
        ? data.fields.filter(isRecord)
        : [];
    const seedFields = Array.isArray(seedParams.fields) ? seedParams.fields.filter(isRecord) : [];

    if (existingFields.length && seedFields.length) {
      const seedFieldsByKey = new Map(seedFields.map((field) => [String(field.field_key || field.field_id || ""), field]));
      const nextFields = existingFields.map((field) => {
        const fieldKey = String(field.field_key || field.field_id || "");
        const seedField = seedFieldsByKey.get(fieldKey);
        if (!seedField) return field;
        const valueKey = "field_value" in field ? "field_value" : "value";
        const seedValue = "field_value" in seedField ? seedField.field_value : seedField.value;
        const hasPrevious = Object.prototype.hasOwnProperty.call(previousFields, fieldKey);
        const currentValue = field[valueKey];
        if (shouldUseLayer12SeedValue(currentValue, previousFields[fieldKey], hasPrevious) && stableJson(currentValue) !== stableJson(seedValue)) {
          changed = true;
          const nextField = { ...field, [valueKey]: cloneJson(seedValue) };
          seededFieldValues.set(fieldKey, cloneJson(seedValue));
          return nextField;
        }
        seededFieldValues.set(fieldKey, cloneJson(currentValue));
        return field;
      });
      params.fields = nextFields;
      data.params = params;
      if (Array.isArray(data.fields)) data.fields = cloneJson(nextFields);
    }

    const keys = contentParamKeys[catalogNodeId] ?? [];
    if (keys.length) {
      const previousNodeParams = previousParams[catalogNodeId] ?? {};
      for (const key of keys) {
        if (!(key in seedParams)) continue;
        const hasPrevious = Object.prototype.hasOwnProperty.call(previousNodeParams, key);
        if (!(key in params) || shouldUseLayer12SeedValue(params[key], previousNodeParams[key], hasPrevious)) {
          if (stableJson(params[key]) !== stableJson(seedParams[key])) {
            params[key] = cloneJson(seedParams[key]);
            changed = true;
          }
        }
      }
      data.params = params;
    }

    const outputs = isRecord(data.outputs) ? { ...data.outputs } : {};
    const seedOutputs = isRecord(seedData.outputs) ? seedData.outputs : {};
    for (const [outputKey, seedOutput] of Object.entries(seedOutputs)) {
      if (!isRecord(seedOutput)) {
        if (!(outputKey in outputs)) {
          outputs[outputKey] = cloneJson(seedOutput);
          changed = true;
        }
        continue;
      }
      const currentOutput = isRecord(outputs[outputKey]) ? { ...(outputs[outputKey] as Record<string, unknown>) } : {};
      for (const [key, seedValue] of Object.entries(seedOutput)) {
        if (key === "fields" && isRecord(seedValue)) {
          const nextFieldOutput = { ...(isRecord(currentOutput.fields) ? currentOutput.fields : {}) };
          for (const [fieldKey, value] of seededFieldValues) nextFieldOutput[fieldKey] = cloneJson(value);
          if (stableJson(currentOutput.fields) !== stableJson(nextFieldOutput)) {
            currentOutput.fields = nextFieldOutput;
            changed = true;
          }
          continue;
        }
        const hasPrevious = Object.prototype.hasOwnProperty.call(previousOutputs, key);
        if (!(key in currentOutput) || shouldUseLayer12SeedValue(currentOutput[key], previousOutputs[key], hasPrevious)) {
          if (stableJson(currentOutput[key]) !== stableJson(seedValue)) {
            currentOutput[key] = cloneJson(seedValue);
            changed = true;
          }
        }
      }
      outputs[outputKey] = currentOutput;
    }
    if (Object.keys(seedOutputs).length) data.outputs = outputs;
    return nextNode;
  });

  return changed ? { ...graph, nodes: nextNodes } : null;
}

function graphNodeTypeFromGraphNode(node: unknown) {
  const schemaNode = schemaNodeRecord(node);
  if (!schemaNode) return "";
  const data = isRecord(schemaNode.data) ? schemaNode.data : {};
  return String(data.node_type || schemaNode.node_type || schemaNode.type || "");
}

function mergeLayer12ReferenceSeed(
  graph: ModuleGraph,
  initialNodes?: WorkflowNode[],
  initialEdges?: WorkflowEdge[]
): ModuleGraph | null {
  const config = LAYER12_REFERENCE_MODULE_CONFIGS[catalogModuleIdFromSeed(initialNodes)];
  if (!config || !initialNodes?.length) {
    return null;
  }

  const seedNodeIds = config.seedAllNodes
    ? new Set(initialNodes.map(catalogNodeIdFromGraphNode).filter(Boolean))
    : new Set([config.referenceInputNodeId, config.referenceOutputNodeId]);
  const nextNodes = [...graph.nodes];
  const catalogIdToGraphId = new Map<string, string>();
  const existingReferenceNodeByType = new Map<string, string>();
  for (const node of nextNodes) {
    const catalogNodeId = catalogNodeIdFromGraphNode(node);
    const nodeId = graphNodeId(node);
    if (catalogNodeId && nodeId) catalogIdToGraphId.set(catalogNodeId, nodeId);
    const nodeType = graphNodeTypeFromGraphNode(node);
    if ((nodeType === "reference_input" || nodeType === "reference_output") && nodeId && !existingReferenceNodeByType.has(nodeType)) {
      existingReferenceNodeByType.set(nodeType, nodeId);
    }
  }

  let changed = false;
  for (const seedNode of initialNodes) {
    const catalogNodeId = catalogNodeIdFromGraphNode(seedNode);
    if (!seedNodeIds.has(catalogNodeId)) continue;
    const nodeType = graphNodeTypeFromGraphNode(seedNode);
    const existingNodeId = catalogIdToGraphId.get(catalogNodeId) || existingReferenceNodeByType.get(nodeType);
    if (existingNodeId) {
      catalogIdToGraphId.set(catalogNodeId, existingNodeId);
      if (
        config.moduleId === "visual_style" &&
        catalogNodeId === config.referenceInputNodeId
      ) {
        const existingIndex = nextNodes.findIndex((node) => graphNodeId(node) === existingNodeId);
        if (existingIndex >= 0) {
          const nextNode = cloneJson(nextNodes[existingIndex]) as WorkflowNode;
          const schemaNode = schemaNodeRecord(nextNode);
          const seedSchemaNode = schemaNodeRecord(seedNode);
          if (schemaNode && seedSchemaNode) {
            const data = schemaDataRecord(schemaNode);
            const seedData = schemaDataRecord(seedSchemaNode);
            const params = isRecord(data.params) ? { ...data.params } : {};
            const seedParams = isRecord(seedData.params) ? seedData.params : {};
            const seedReferences = Array.isArray(seedParams.references)
              ? seedParams.references
              : seedData.references;
            const hasInteractionBoundary = Array.isArray(seedReferences) && seedReferences.some(
              (reference) =>
                isRecord(reference) &&
                reference.source_module_id === "humanistic_interaction_boundary_config_v0_1"
            );
            const merged = mergeCatalogReferenceDeclarations(
              Array.isArray(params.references) ? params.references : data.references,
              seedReferences,
              hasInteractionBoundary ? ["humanistic_behavior_boundary_config_v0_1"] : []
            );
            if (merged.changed) {
              data.params = { ...params, references: merged.references };
              data.references = cloneJson(merged.references);
              nextNodes[existingIndex] = nextNode;
              changed = true;
            }
          }
        }
      }
      continue;
    }
    const nextNode = cloneJson(seedNode) as WorkflowNode;
    nextNodes.push(nextNode);
    const nextNodeId = graphNodeId(nextNode);
    if (nextNodeId) {
      catalogIdToGraphId.set(catalogNodeId, nextNodeId);
      existingReferenceNodeByType.set(nodeType, nextNodeId);
    }
    changed = true;
  }

  const initialNodeIdMap = nodeIdToCatalogNodeId(initialNodes);
  const nextEdges = [...graph.edges];
  const existingPairs = new Set(
    nextEdges.map((edge) => `${edgeEndpoint(edge, "source")}->${edgeEndpoint(edge, "target")}`)
  );
  const existingEdgeIds = new Set(
    nextEdges
      .map((edge) => {
        const edgeRecord = edge as unknown as Record<string, unknown>;
        return String(edgeRecord.edge_id || edgeRecord.id || "");
      })
      .filter(Boolean)
  );
  for (const seedEdge of initialEdges ?? []) {
    const seedSource = edgeEndpoint(seedEdge, "source");
    const seedTarget = edgeEndpoint(seedEdge, "target");
    const sourceCatalogId = catalogNodeIdFromEndpoint(seedSource, initialNodeIdMap);
    const targetCatalogId = catalogNodeIdFromEndpoint(seedTarget, initialNodeIdMap);
    if (!seedNodeIds.has(sourceCatalogId) && !seedNodeIds.has(targetCatalogId)) continue;
    const source = catalogIdToGraphId.get(sourceCatalogId);
    const target = catalogIdToGraphId.get(targetCatalogId);
    if (!source || !target || existingPairs.has(`${source}->${target}`)) continue;

    const nextEdge = cloneJson(seedEdge) as WorkflowEdge & Record<string, unknown>;
    nextEdge.source = source;
    nextEdge.target = target;
    if ("source_node_id" in nextEdge) nextEdge.source_node_id = source;
    if ("target_node_id" in nextEdge) nextEdge.target_node_id = target;
    const baseEdgeId = String(nextEdge.edge_id || nextEdge.id || `${source}_to_${target}`);
    let edgeId = baseEdgeId;
    let suffix = 2;
    while (existingEdgeIds.has(edgeId)) {
      edgeId = `${baseEdgeId}_${suffix}`;
      suffix += 1;
    }
    nextEdge.edge_id = edgeId;
    nextEdge.id = edgeId;
    nextEdges.push(nextEdge as WorkflowEdge);
    existingPairs.add(`${source}->${target}`);
    existingEdgeIds.add(edgeId);
    changed = true;
  }

  return changed ? { ...graph, nodes: nextNodes, edges: nextEdges } : null;
}

function mergeDialogueRuntimeProfileReferenceSeed(
  graph: ModuleGraph,
  initialNodes?: WorkflowNode[]
): ModuleGraph | null {
  if (graph.moduleNodeId !== DIALOGUE_RUNTIME_PROFILE_GRAPH_ID || !initialNodes?.length) {
    return null;
  }
  const seedNode = initialNodes.find(
    (node) => catalogNodeIdFromGraphNode(node) === DIALOGUE_RUNTIME_PROFILE_REFERENCE_INPUT_ID
  );
  const currentIndex = graph.nodes.findIndex(
    (node) => catalogNodeIdFromGraphNode(node) === DIALOGUE_RUNTIME_PROFILE_REFERENCE_INPUT_ID
  );
  if (!seedNode || currentIndex < 0) {
    return null;
  }
  const seedSchemaNode = schemaNodeRecord(seedNode);
  const currentNode = cloneJson(graph.nodes[currentIndex]) as WorkflowNode;
  const currentSchemaNode = schemaNodeRecord(currentNode);
  if (!seedSchemaNode || !currentSchemaNode) {
    return null;
  }
  const seedData = schemaDataRecord(seedSchemaNode);
  const currentData = schemaDataRecord(currentSchemaNode);
  const seedParams = isRecord(seedData.params) ? seedData.params : {};
  const currentParams = isRecord(currentData.params) ? { ...currentData.params } : {};
  const merged = mergeCatalogReferenceDeclarations(
    currentParams.references,
    seedParams.references
  );
  if (!merged.changed) {
    return null;
  }
  currentData.params = { ...currentParams, references: merged.references };
  currentData.references = cloneJson(merged.references);
  const nodes = [...graph.nodes];
  nodes[currentIndex] = currentNode;
  return { ...graph, nodes };
}

function migrateDialogueRuntimeProfileContentSeed(
  graph: ModuleGraph,
  initialNodes?: WorkflowNode[]
): ModuleGraph | null {
  if (graph.moduleNodeId !== DIALOGUE_RUNTIME_PROFILE_GRAPH_ID || !initialNodes?.length) {
    return null;
  }
  const seedInput = initialNodes.find(
    (node) => catalogNodeIdFromGraphNode(node) === DIALOGUE_RUNTIME_PROFILE_CONFIG_INPUT_ID
  );
  const seedOutput = initialNodes.find(
    (node) => catalogNodeIdFromGraphNode(node) === DIALOGUE_RUNTIME_PROFILE_OUTPUT_ID
  );
  const inputIndex = graph.nodes.findIndex(
    (node) => catalogNodeIdFromGraphNode(node) === DIALOGUE_RUNTIME_PROFILE_CONFIG_INPUT_ID
  );
  const outputIndex = graph.nodes.findIndex(
    (node) => catalogNodeIdFromGraphNode(node) === DIALOGUE_RUNTIME_PROFILE_OUTPUT_ID
  );
  if (!seedInput || !seedOutput || inputIndex < 0 || outputIndex < 0) {
    return null;
  }

  const seedInputSchema = schemaNodeRecord(seedInput);
  const seedOutputSchema = schemaNodeRecord(seedOutput);
  const currentInput = cloneJson(graph.nodes[inputIndex]) as WorkflowNode;
  const currentOutput = cloneJson(graph.nodes[outputIndex]) as WorkflowNode;
  const currentInputSchema = schemaNodeRecord(currentInput);
  const currentOutputSchema = schemaNodeRecord(currentOutput);
  if (!seedInputSchema || !seedOutputSchema || !currentInputSchema || !currentOutputSchema) {
    return null;
  }

  const seedInputData = schemaDataRecord(seedInputSchema);
  const seedOutputData = schemaDataRecord(seedOutputSchema);
  const inputData = schemaDataRecord(currentInputSchema);
  const outputData = schemaDataRecord(currentOutputSchema);
  const seedParams = isRecord(seedInputData.params) ? seedInputData.params : {};
  const params = isRecord(inputData.params) ? { ...inputData.params } : {};
  const seedOutputs = isRecord(seedOutputData.outputs) ? seedOutputData.outputs : {};
  const outputs = isRecord(outputData.outputs) ? { ...outputData.outputs } : {};
  const seedProfileOutput = isRecord(seedOutputs[DIALOGUE_RUNTIME_PROFILE_OUTPUT_KEY])
    ? seedOutputs[DIALOGUE_RUNTIME_PROFILE_OUTPUT_KEY]
    : {};
  const currentProfileOutput = isRecord(outputs[DIALOGUE_RUNTIME_PROFILE_OUTPUT_KEY])
    ? outputs[DIALOGUE_RUNTIME_PROFILE_OUTPUT_KEY]
    : cloneJson(seedProfileOutput);
  const migration = migrateDialogueRuntimeProfileContentCopies(
    {
      profileContentRevision: params.profile_content_revision,
      fields: Array.isArray(params.fields) ? params.fields.filter(isRecord) : undefined,
      dataFields: Array.isArray(inputData.fields) ? inputData.fields.filter(isRecord) : undefined,
      legacyFields: Array.isArray(params.legacy_fields)
        ? params.legacy_fields.filter(isRecord)
        : undefined,
      legacyDataFields: Array.isArray(params.legacy_data_fields)
        ? params.legacy_data_fields.filter(isRecord)
        : undefined,
      output: currentProfileOutput,
    },
    {
      profileContentRevision: seedParams.profile_content_revision,
      fields: Array.isArray(seedParams.fields) ? seedParams.fields.filter(isRecord) : undefined,
      output: seedProfileOutput,
    }
  );
  if (!migration.migrated) {
    return null;
  }

  params.profile_content_revision = migration.value.profileContentRevision;
  if (migration.value.fields) params.fields = cloneJson(migration.value.fields);
  if (migration.value.legacyFields) {
    params.legacy_fields = cloneJson(migration.value.legacyFields);
  }
  if (migration.value.legacyDataFields) {
    params.legacy_data_fields = cloneJson(migration.value.legacyDataFields);
  }
  inputData.params = params;
  if (migration.value.dataFields) {
    inputData.fields = cloneJson(migration.value.dataFields);
  }
  outputData.outputs = {
    ...outputs,
    [DIALOGUE_RUNTIME_PROFILE_OUTPUT_KEY]: cloneJson(migration.value.output),
  };
  const nodes = [...graph.nodes];
  nodes[inputIndex] = currentInput;
  nodes[outputIndex] = currentOutput;
  return { ...graph, nodes };
}

function mergeCatalogSeed(
  graph: ModuleGraph,
  initialNodes?: WorkflowNode[],
  initialEdges?: WorkflowEdge[]
): ModuleGraph | null {
  const dialogueReferenceMerged = mergeDialogueRuntimeProfileReferenceSeed(graph, initialNodes);
  const dialogueContentMigrated = migrateDialogueRuntimeProfileContentSeed(
    dialogueReferenceMerged ?? graph,
    initialNodes
  );
  const graphAfterDialogueMerge = dialogueContentMigrated ?? dialogueReferenceMerged ?? graph;
  const referenceMerged = mergeLayer12ReferenceSeed(graphAfterDialogueMerge, initialNodes, initialEdges);
  const graphAfterReferenceMerge = referenceMerged ?? graphAfterDialogueMerge;
  const fieldMerged = mergeCatalogFieldSeed(graphAfterReferenceMerge, initialNodes, initialEdges);
  const contentMerged = mergeLayer12ContentSeed(fieldMerged ?? graphAfterReferenceMerge, initialNodes);
  const layoutMerged = mergeCatalogLayoutSeed(contentMerged ?? fieldMerged ?? graphAfterReferenceMerge, initialNodes, initialEdges);
  return layoutMerged ?? contentMerged ?? fieldMerged ?? referenceMerged ?? dialogueContentMigrated ?? dialogueReferenceMerged;
}

function layerModuleIdentity(moduleNodeId: string, registry: Record<string, ModuleInstance>) {
  const registryEntry = registry[moduleNodeId];
  if (registryEntry) {
    return registryEntry;
  }
  const [layerId = "", moduleId = moduleNodeId] = moduleNodeId.split(MODULE_INSTANCE_SEPARATOR);
  return { instanceId: moduleNodeId, layerId, moduleId };
}

function shouldMigrateGenericFieldsGraph(identity: ModuleInstance) {
  if (identity.layerId === "layer_1") {
    return true;
  }
  return identity.layerId === "layer_3" && LAYER3_GENERIC_FIELD_MIGRATION_MODULE_IDS.has(identity.moduleId);
}

function shouldMigrateGenericFieldNode(
  identity: ModuleInstance,
  nodeType: string,
  data: Record<string, unknown>,
  params: Record<string, unknown>
) {
  if (nodeType === "reference_input" || nodeType === "reference_output") {
    return false;
  }
  if (GENERIC_FIELD_MIGRATION_NODE_TYPES.has(nodeType)) {
    return true;
  }
  if (identity.layerId !== "layer_3" || identity.moduleId !== "humanistic_risk_response_config_v0_1") {
    return false;
  }
  return nodeType !== "module_output" && (Array.isArray(params.fields) || Array.isArray(data.fields));
}

function migrateGenericFieldsGraph(
  graph: ModuleGraph,
  registry: Record<string, ModuleInstance>
): ModuleGraph | null {
  const identity = layerModuleIdentity(graph.moduleNodeId, registry);
  if (!shouldMigrateGenericFieldsGraph(identity)) {
    return null;
  }

  let changed = false;
  const nextNodes = graph.nodes.map((node) => {
    const nextNode = cloneJson(node) as WorkflowNode;
    const schemaNode = schemaNodeRecord(nextNode);
    if (!schemaNode) {
      return nextNode;
    }
    const data = schemaDataRecord(schemaNode);
    const nodeType = String(data.node_type || schemaNode.type || "");
    const params = isRecord(data.params) ? { ...data.params } : {};
    if (!shouldMigrateGenericFieldNode(identity, nodeType, data, params)) {
      return nextNode;
    }
    const alreadyGeneric = params.mode === "generic_fields" && Array.isArray(params.fields);
    const legacyFields = fieldsFromData(data);
    const genericFields = alreadyGeneric
      ? refineGenericFieldsFromLegacy(cloneJson((params.fields as unknown[]).filter(isRecord)), legacyFields)
      : genericFieldsFromLegacyNode(data, params, identity.layerId, identity.moduleId);
    const needsLegacyDataBackup = Array.isArray(data.fields) && !Array.isArray(params.legacy_data_fields);
    const syncedParams = syncPrimaryLanguageCompatibilityFields({ ...params, fields: genericFields });
    if (
      nodeType === "text_input" &&
      alreadyGeneric &&
      stableJson(genericFields) === stableJson(params.fields) &&
      stableJson(syncedParams) === stableJson(params) &&
      !needsLegacyDataBackup
    ) {
      return nextNode;
    }
    if (nodeType !== "text_input") {
      data.legacy_node_type = data.legacy_node_type || nodeType;
      data.node_type = "text_input";
      schemaNode.type = "text_input";
      schemaNode.title_key = "node.type.text_input";
      schemaNode.title_fallback = "Text Input";
    }
    params.mode = "generic_fields";
    params.text = stringValue(params.text) || legacyTextValue(data, params);
    if (Array.isArray(params.fields) && !Array.isArray(params.legacy_fields)) {
      params.legacy_fields = cloneJson(params.fields);
    }
    if (needsLegacyDataBackup) {
      params.legacy_data_fields = cloneJson(data.fields);
    }
    params.fields = genericFields;
    data.params = syncPrimaryLanguageCompatibilityFields(params);
    changed = true;
    return nextNode;
  });

  return changed ? { ...graph, nodes: nextNodes } : null;
}

function isRiskResponseIdentity(identity: ModuleInstance) {
  return identity.moduleId === RISK_RESPONSE_MODULE_ID;
}

function graphNodeType(schemaNode: Record<string, unknown>, data: Record<string, unknown>) {
  return String(data.node_type || schemaNode.type || "");
}

function migrateLayer12ReferenceGraph(
  graph: ModuleGraph,
  registry: Record<string, ModuleInstance>,
  moduleGraphs: ModuleGraphsState
): ModuleGraph | null {
  const identity = layerModuleIdentity(graph.moduleNodeId, registry);
  const config = LAYER12_REFERENCE_MODULE_CONFIGS[identity.moduleId];
  if (!config || identity.layerId !== config.layerId) {
    return null;
  }

  const availableSources: AvailableModuleReferenceSource[] = config.sources.map((source) => {
    const sourceNodeIds = Object.values(moduleGraphs)
      .filter((candidate) => {
        const candidateIdentity = layerModuleIdentity(candidate.moduleNodeId, registry);
        return candidateIdentity.layerId === source.source_layer_id && candidateIdentity.moduleId === source.source_module_id;
      })
      .flatMap((candidate) =>
        candidate.nodes
          .filter((node) => graphNodeTypeFromGraphNode(node) === "reference_output")
          .map(graphNodeId)
          .filter(Boolean)
      );
    return {
      ...source,
      source_node_ids: [...new Set(sourceNodeIds)],
    };
  });

  let changed = false;
  let referenceInputProcessed = false;
  const nextNodes = graph.nodes.map((node) => {
    if (referenceInputProcessed || graphNodeTypeFromGraphNode(node) !== "reference_input") return node;
    referenceInputProcessed = true;
    const nextNode = cloneJson(node) as WorkflowNode;
    const schemaNode = schemaNodeRecord(nextNode);
    if (!schemaNode) return node;
    const data = schemaDataRecord(schemaNode);
    const params = isRecord(data.params) ? { ...data.params } : {};
    const merged = mergeAvailableModuleReferencePointers(params.references, availableSources);
    if (!merged.changed) return node;
    data.params = { ...params, references: merged.references };
    data.references = cloneJson(merged.references);
    changed = true;
    return nextNode;
  });

  return changed ? { ...graph, nodes: nextNodes } : null;
}

function replaceReferenceNodeIdPrefix(nodeId: string) {
  return nodeId.startsWith("layer_2::") ? nodeId.replace(/^layer_2::/, "layer_3::") : nodeId;
}

function updateReferencePointers(value: unknown, nodeIdMap: Map<string, string>): unknown {
  if (Array.isArray(value)) {
    return value.map((item) => updateReferencePointers(item, nodeIdMap));
  }
  if (!isRecord(value)) {
    return value;
  }
  const next: Record<string, unknown> = {};
  for (const [key, item] of Object.entries(value)) {
    if ((key === "source_node_id" || key === "source" || key === "target") && typeof item === "string") {
      next[key] = nodeIdMap.get(item) ?? item;
      continue;
    }
    if (key === "source_layer_id" && value.source_module_id === RISK_RESPONSE_MODULE_ID) {
      next[key] = RISK_RESPONSE_LAYER_ID;
      continue;
    }
    next[key] = updateReferencePointers(item, nodeIdMap);
  }
  return next;
}

function migrateRiskResponseReferenceGraph(
  graph: ModuleGraph,
  registry: Record<string, ModuleInstance>
): { graph: ModuleGraph; nodeIdMap: Map<string, string>; oldGraphId?: string } | null {
  const identity = layerModuleIdentity(graph.moduleNodeId, registry);
  if (!isRiskResponseIdentity(identity)) {
    return null;
  }

  let changed = graph.moduleNodeId !== RISK_RESPONSE_MODULE_INSTANCE_ID || identity.layerId !== RISK_RESPONSE_LAYER_ID;
  const nodeIdMap = new Map<string, string>();
  const nextNodes = graph.nodes.map((node) => {
    const nextNode = cloneJson(node) as WorkflowNode;
    const schemaNode = schemaNodeRecord(nextNode);
    if (!schemaNode) {
      return nextNode;
    }
    const data = schemaDataRecord(schemaNode);
    const nodeType = graphNodeType(schemaNode, data);
    data.parent_module = RISK_RESPONSE_MODULE_INSTANCE_ID;
    data.module_instance_id = RISK_RESPONSE_MODULE_INSTANCE_ID;
    data.catalog_module_id = RISK_RESPONSE_MODULE_ID;
    schemaNode.layer_id = RISK_RESPONSE_LAYER_ID;
    schemaNode.module_id = RISK_RESPONSE_MODULE_ID;
    if (nodeType !== "reference_input" && nodeType !== "reference_output") {
      return nextNode;
    }

    const oldNodeId = String(schemaNode.node_id || (nextNode as unknown as Record<string, unknown>).id || "");
    const nextNodeId = replaceReferenceNodeIdPrefix(oldNodeId);
    if (oldNodeId && nextNodeId !== oldNodeId) {
      nodeIdMap.set(oldNodeId, nextNodeId);
      schemaNode.node_id = nextNodeId;
      const nextNodeRecord = nextNode as unknown as Record<string, unknown>;
      if (typeof nextNodeRecord.id === "string") {
        nextNodeRecord.id = nextNodeId;
      }
      changed = true;
    }

    data.parent_module = RISK_RESPONSE_MODULE_INSTANCE_ID;
    data.module_instance_id = RISK_RESPONSE_MODULE_INSTANCE_ID;
    data.catalog_module_id = RISK_RESPONSE_MODULE_ID;
    data.layer_id = RISK_RESPONSE_LAYER_ID;
    data.module_id = RISK_RESPONSE_MODULE_ID;
    if (nodeType === "reference_output") {
      const params = isRecord(data.params) ? { ...data.params } : {};
      data.params = {
        ...params,
        authority_source_type: "authoritative_constraint",
        is_core_source: false,
        override_allowed: false,
      };
      data.authority_source_type = "authoritative_constraint";
      data.is_core_source = false;
      data.override_allowed = false;
      changed = true;
    }
    return nextNode;
  });

  const nextEdges = graph.edges.map((edge) => {
    const nextEdge = cloneJson(edge) as WorkflowEdge;
    let edgeChanged = false;
    for (const key of ["source", "target", "source_node_id", "target_node_id"]) {
      const record = nextEdge as unknown as Record<string, unknown>;
      const current = typeof record[key] === "string" ? record[key] : "";
      const nextValue = nodeIdMap.get(current);
      if (nextValue) {
        record[key] = nextValue;
        edgeChanged = true;
      }
    }
    changed = changed || edgeChanged;
    return nextEdge;
  });

  if (!changed && nodeIdMap.size === 0) {
    return null;
  }
  return {
    graph: {
      ...graph,
      moduleNodeId: RISK_RESPONSE_MODULE_INSTANCE_ID,
      nodes: nextNodes,
      edges: nextEdges,
    },
    nodeIdMap,
    oldGraphId: graph.moduleNodeId !== RISK_RESPONSE_MODULE_INSTANCE_ID ? graph.moduleNodeId : undefined,
  };
}

function migrateMemoryProviderRouterTypeResolverGraph(
  graph: ModuleGraph,
  registry: Record<string, ModuleInstance>
): ModuleGraph | null {
  const identity = layerModuleIdentity(graph.moduleNodeId, registry);
  if (identity.layerId !== MEMORY_PROVIDER_ROUTER_LAYER_ID || identity.moduleId !== MEMORY_PROVIDER_ROUTER_MODULE_ID) {
    return null;
  }

  let changed = false;
  const nextNodes = graph.nodes.map((node) => {
    const nextNode = cloneJson(node) as WorkflowNode;
    const schemaNode = schemaNodeRecord(nextNode);
    if (!schemaNode) {
      return nextNode;
    }
    const data = schemaDataRecord(schemaNode);
    const catalogNodeId = String(data.catalog_node_id || schemaNode.node_id || "").split(MODULE_INSTANCE_SEPARATOR).pop() ?? "";
    if (catalogNodeId !== MEMORY_ROUTER_TYPE_RESOLVER_NODE_ID) {
      return nextNode;
    }

    const params = isRecord(data.params) ? { ...data.params } : {};
    const paramsNeedsMigration = hasExactStringList(params.allowed_memory_types, LEGACY_MEMORY_ROUTER_ALLOWED_MEMORY_TYPES);
    const dataNeedsMigration = hasExactStringList(data.allowed_memory_types, LEGACY_MEMORY_ROUTER_ALLOWED_MEMORY_TYPES);
    if (!paramsNeedsMigration && !dataNeedsMigration) {
      return nextNode;
    }
    if (paramsNeedsMigration) {
      params.allowed_memory_types = [...MEMORY_ROUTER_ALLOWED_MEMORY_TYPES];
      data.params = params;
    }
    if (dataNeedsMigration) {
      data.allowed_memory_types = [...MEMORY_ROUTER_ALLOWED_MEMORY_TYPES];
    }
    changed = true;
    return nextNode;
  });

  return changed ? { ...graph, nodes: nextNodes } : null;
}

function normalizeMemoryRouterOperationParams(params: Record<string, unknown>, catalogNodeId: string) {
  if (catalogNodeId === MEMORY_ROUTER_REQUEST_INPUT_NODE_ID) {
    const requestSchema = isRecord(params.request_schema) ? { ...params.request_schema } : null;
    if (!requestSchema || !hasExactStringList(requestSchema.operations, LEGACY_MEMORY_ROUTER_OPERATIONS)) {
      return params;
    }
    requestSchema.operations = [...MEMORY_ROUTER_CANONICAL_OPERATIONS];
    if (!Array.isArray(requestSchema.canonical_operations)) {
      requestSchema.canonical_operations = [...MEMORY_ROUTER_CANONICAL_OPERATIONS];
    }
    if (!Array.isArray(requestSchema.accepted_operations)) {
      requestSchema.accepted_operations = [...MEMORY_ROUTER_ACCEPTED_OPERATIONS];
    }
    if (!isRecord(requestSchema.operation_aliases)) {
      requestSchema.operation_aliases = { ...MEMORY_ROUTER_OPERATION_ALIASES };
    }
    return { ...params, request_schema: requestSchema };
  }
  if (catalogNodeId === MEMORY_ROUTER_OPERATION_CLASSIFIER_NODE_ID) {
    const oldOperations = hasExactStringList(params.operations, LEGACY_MEMORY_ROUTER_OPERATIONS);
    const oldRules = hasExactStringList(params.normalize_rules, LEGACY_MEMORY_ROUTER_NORMALIZE_RULES);
    if (!oldOperations && !oldRules) {
      return params;
    }
    const nextParams = { ...params };
    if (oldOperations) {
      nextParams.operations = [...MEMORY_ROUTER_CANONICAL_OPERATIONS];
    }
    if (oldRules) {
      nextParams.normalize_rules = [...MEMORY_ROUTER_NORMALIZE_RULES];
    }
    if (!Array.isArray(nextParams.canonical_operations)) {
      nextParams.canonical_operations = [...MEMORY_ROUTER_CANONICAL_OPERATIONS];
    }
    if (!isRecord(nextParams.operation_aliases)) {
      nextParams.operation_aliases = { ...MEMORY_ROUTER_OPERATION_ALIASES };
    }
    return nextParams;
  }
  return params;
}

function migrateMemoryProviderRouterOperationsGraph(
  graph: ModuleGraph,
  registry: Record<string, ModuleInstance>
): ModuleGraph | null {
  const identity = layerModuleIdentity(graph.moduleNodeId, registry);
  if (identity.layerId !== MEMORY_PROVIDER_ROUTER_LAYER_ID || identity.moduleId !== MEMORY_PROVIDER_ROUTER_MODULE_ID) {
    return null;
  }

  let changed = false;
  const nextNodes = graph.nodes.map((node) => {
    const nextNode = cloneJson(node) as WorkflowNode;
    const schemaNode = schemaNodeRecord(nextNode);
    if (!schemaNode) {
      return nextNode;
    }
    const data = schemaDataRecord(schemaNode);
    const catalogNodeId = String(data.catalog_node_id || schemaNode.node_id || "").split(MODULE_INSTANCE_SEPARATOR).pop() ?? "";
    const params = isRecord(data.params) ? { ...data.params } : {};
    const nextParams = normalizeMemoryRouterOperationParams(params, catalogNodeId);
    if (stableJson(nextParams) === stableJson(params)) {
      return nextNode;
    }
    data.params = nextParams;
    changed = true;
    return nextNode;
  });

  return changed ? { ...graph, nodes: nextNodes } : null;
}

function migrateEnvironmentFieldMappingsGraph(
  graph: ModuleGraph,
  registry: Record<string, ModuleInstance>
): ModuleGraph | null {
  const identity = layerModuleIdentity(graph.moduleNodeId, registry);
  if (identity.layerId !== ENVIRONMENT_MODULE_LAYER_ID || identity.moduleId !== ENVIRONMENT_MODULE_ID) {
    return null;
  }

  let changed = false;
  const nextNodes = graph.nodes.map((node) => {
    const nextNode = cloneJson(node) as WorkflowNode;
    const schemaNode = schemaNodeRecord(nextNode);
    if (!schemaNode) {
      return nextNode;
    }
    const data = schemaDataRecord(schemaNode);
    const catalogNodeId = String(data.catalog_node_id || schemaNode.node_id || "").split(MODULE_INSTANCE_SEPARATOR).pop() ?? "";
    if (catalogNodeId !== ENVIRONMENT_FIELD_INPUT_NODE_ID) {
      return nextNode;
    }
    const params = isRecord(data.params) ? { ...data.params } : {};
    if (!Array.isArray(params.fields)) {
      return nextNode;
    }
    let fieldsChanged = false;
    const fields = params.fields.map((field) => {
      if (!isRecord(field)) {
        return field;
      }
      const fieldKey = stringValue(field.field_key) || stringValue(field.field_id);
      if (!ENVIRONMENT_FIELD_MAPPING_KEYS.has(fieldKey)) {
        return field;
      }
      const nextMapping = stringValue(field.dr_mapping) || environmentFieldDrMapping(fieldKey);
      if (nextMapping === field.dr_mapping && field.dr_mapping_auto === true) {
        return field;
      }
      fieldsChanged = true;
      return { ...field, dr_mapping: nextMapping, dr_mapping_auto: true };
    });
    if (!fieldsChanged) {
      return nextNode;
    }
    data.params = { ...params, fields };
    changed = true;
    return nextNode;
  });

  return changed ? { ...graph, nodes: nextNodes } : null;
}

function migrateUserRelationshipConfigGraph(
  graph: ModuleGraph,
  registry: Record<string, ModuleInstance>
): ModuleGraph | null {
  const identity = layerModuleIdentity(graph.moduleNodeId, registry);
  if (identity.layerId !== USER_RELATIONSHIP_LAYER_ID || identity.moduleId !== USER_RELATIONSHIP_MODULE_ID) {
    return null;
  }

  let changed = false;
  const nextNodes = graph.nodes.map((node) => {
    const nextNode = cloneJson(node) as WorkflowNode;
    const schemaNode = schemaNodeRecord(nextNode);
    if (!schemaNode) {
      return nextNode;
    }
    const data = schemaDataRecord(schemaNode);
    const catalogNodeId = String(data.catalog_node_id || schemaNode.node_id || "").split(MODULE_INSTANCE_SEPARATOR).pop() ?? "";
    const i18nSuffix = USER_RELATIONSHIP_NODE_I18N_SUFFIX[catalogNodeId];
    if (i18nSuffix) {
      const nodeType = String(data.node_type || schemaNode.type || "");
      const expectedI18n = {
        name: `layer11.userRelationship.node.${i18nSuffix}.title`,
        description: `layer11.userRelationship.node.${i18nSuffix}.description`,
        type_name: `node.type.${nodeType}`,
      };
      const currentI18n = isRecord(data.i18n_keys) ? data.i18n_keys : {};
      const nextI18n = { ...currentI18n, ...expectedI18n };
      if (stableJson(currentI18n) !== stableJson(nextI18n)) {
        data.i18n_keys = nextI18n;
        changed = true;
      }
    }
    if (catalogNodeId === USER_RELATIONSHIP_UPDATE_NODE_ID) {
      const params = isRecord(data.params) ? { ...data.params } : {};
      const nextParams = normalizeUserRelationshipUpdateParams(params);
      if (stableJson(nextParams) !== stableJson(params)) {
        data.params = nextParams;
        changed = true;
      }
    }
    if (catalogNodeId === USER_RELATIONSHIP_OUTPUT_NODE_ID) {
      const outputs = isRecord(data.outputs) ? { ...data.outputs } : {};
      const nextOutputs = normalizeUserRelationshipOutput(outputs);
      if (stableJson(nextOutputs) !== stableJson(outputs)) {
        data.outputs = nextOutputs;
        changed = true;
      }
    }
    return nextNode;
  });

  return changed ? { ...graph, nodes: nextNodes } : null;
}

function migrateReferencePointersAcrossGraphs(nodeIdMap: Map<string, string>) {
  if (!nodeIdMap.size) {
    return;
  }
  const store = useCanvasStore.getState();
  for (const graph of Object.values(store.moduleGraphs)) {
    let changed = false;
    const nextNodes = graph.nodes.map((node) => {
      const nextNode = updateReferencePointers(cloneJson(node), nodeIdMap) as WorkflowNode;
      if (stableJson(nextNode) !== stableJson(node)) {
        changed = true;
      }
      return nextNode;
    });
    const nextEdges = graph.edges.map((edge) => {
      const nextEdge = updateReferencePointers(cloneJson(edge), nodeIdMap) as WorkflowEdge;
      if (stableJson(nextEdge) !== stableJson(edge)) {
        changed = true;
      }
      return nextEdge;
    });
    if (changed) {
      store.updateModuleGraph(graph.moduleNodeId, nextNodes, nextEdges, graph.viewport);
      saveModuleGraphState(graph.moduleNodeId, nextNodes, nextEdges);
    }
  }
}

function normalizeFirstInteractionPromptLimitGraph(
  graph: ModuleGraph,
  registry: Record<string, ModuleInstance>
): ModuleGraph | null {
  const identity = layerModuleIdentity(graph.moduleNodeId, registry);
  if (
    identity.moduleId !== "interaction_strategy" ||
    (identity.layerId && identity.layerId !== "layer_8")
  ) {
    return null;
  }

  let changed = false;
  const nextNodes = graph.nodes.map((node) => {
    if (catalogNodeIdFromGraphNode(node) !== "interaction_behavior_core_rules") {
      return node;
    }
    const nextNode = cloneJson(node) as WorkflowNode;
    const schemaNode = schemaNodeRecord(nextNode);
    if (!schemaNode) {
      return node;
    }
    const data = schemaDataRecord(schemaNode);
    const params = isRecord(data.params) ? { ...data.params } : {};
    const fields = Array.isArray(params.fields)
      ? params.fields
      : Array.isArray(data.fields)
        ? data.fields
        : [];
    let nodeChanged = false;
    const nextFields = fields.map((field) => {
      if (!isRecord(field)) {
        return field;
      }
      const fieldId = String(field.field_id || field.field_key || "");
      if (fieldId !== "first_interaction") {
        return field;
      }
      const valueKey = "value" in field ? "value" : "field_value";
      const normalized = normalizeFirstInteractionEnabled(
        normalizeFirstInteractionMaxActivePrompts(field[valueKey])
      );
      if (stableJson(normalized) === stableJson(field[valueKey])) {
        return field;
      }
      nodeChanged = true;
      return { ...field, [valueKey]: normalized };
    });
    if (Array.isArray(data.fields)) {
      delete data.fields;
      nodeChanged = true;
    }
    if (!nodeChanged) {
      return node;
    }
    params.fields = nextFields;
    data.params = params;
    changed = true;
    return nextNode;
  });

  return changed ? { ...graph, nodes: nextNodes } : null;
}

function applyGenericFieldsMigration(graph: ModuleGraph): ModuleGraph {
  const store = useCanvasStore.getState();
  const edgeIntegrity = filterDanglingModuleGraphEdges(graph.nodes.map(graphNodeId).filter(Boolean), graph.edges);
  const graphAfterEdgeCleanup = edgeIntegrity.pruned.length
    ? { ...graph, edges: edgeIntegrity.edges as WorkflowEdge[] }
    : graph;
  if (graphAfterEdgeCleanup !== graph) {
    store.updateModuleGraph(
      graphAfterEdgeCleanup.moduleNodeId,
      graphAfterEdgeCleanup.nodes,
      graphAfterEdgeCleanup.edges,
      graphAfterEdgeCleanup.viewport
    );
    saveModuleGraphState(
      graphAfterEdgeCleanup.moduleNodeId,
      graphAfterEdgeCleanup.nodes,
      graphAfterEdgeCleanup.edges
    );
  }

  const firstInteractionPromptLimitMigration = normalizeFirstInteractionPromptLimitGraph(
    graphAfterEdgeCleanup,
    store.moduleInstanceRegistry
  );
  if (firstInteractionPromptLimitMigration) {
    store.updateModuleGraph(
      firstInteractionPromptLimitMigration.moduleNodeId,
      firstInteractionPromptLimitMigration.nodes,
      firstInteractionPromptLimitMigration.edges,
      firstInteractionPromptLimitMigration.viewport
    );
    saveModuleGraphState(
      firstInteractionPromptLimitMigration.moduleNodeId,
      firstInteractionPromptLimitMigration.nodes,
      firstInteractionPromptLimitMigration.edges
    );
    console.log("[P1-BRIDGE] normalized first interaction prompt limit", {
      moduleNodeId: firstInteractionPromptLimitMigration.moduleNodeId,
    });
  }
  const graphAfterFirstInteractionPromptLimitMigration =
    firstInteractionPromptLimitMigration ?? graphAfterEdgeCleanup;

  const riskMigration = migrateRiskResponseReferenceGraph(
    graphAfterFirstInteractionPromptLimitMigration,
    store.moduleInstanceRegistry
  );
  if (riskMigration) {
    store.updateModuleGraph(riskMigration.graph.moduleNodeId, riskMigration.graph.nodes, riskMigration.graph.edges, riskMigration.graph.viewport);
    saveModuleGraphState(riskMigration.graph.moduleNodeId, riskMigration.graph.nodes, riskMigration.graph.edges);
    if (riskMigration.oldGraphId) {
      store.removeModuleGraph(riskMigration.oldGraphId);
      if (typeof window !== "undefined") {
        window.localStorage.removeItem(`module_graph_${riskMigration.oldGraphId}`);
      }
    }
    migrateReferencePointersAcrossGraphs(riskMigration.nodeIdMap);
    console.log("[P1-BRIDGE] migrated risk response reference node ids", {
      moduleNodeId: riskMigration.graph.moduleNodeId,
      movedIds: riskMigration.nodeIdMap.size,
    });
  }
  const graphAfterRiskMigration = riskMigration?.graph ?? graphAfterFirstInteractionPromptLimitMigration;
  const memoryRouterMigration = migrateMemoryProviderRouterTypeResolverGraph(graphAfterRiskMigration, store.moduleInstanceRegistry);
  if (memoryRouterMigration) {
    store.updateModuleGraph(memoryRouterMigration.moduleNodeId, memoryRouterMigration.nodes, memoryRouterMigration.edges, memoryRouterMigration.viewport);
    saveModuleGraphState(memoryRouterMigration.moduleNodeId, memoryRouterMigration.nodes, memoryRouterMigration.edges);
    console.log("[P1-BRIDGE] migrated memory provider router allowed memory types", {
      moduleNodeId: memoryRouterMigration.moduleNodeId,
    });
  }
  const graphAfterMemoryRouterMigration = memoryRouterMigration ?? graphAfterRiskMigration;
  const memoryRouterOperationsMigration = migrateMemoryProviderRouterOperationsGraph(graphAfterMemoryRouterMigration, store.moduleInstanceRegistry);
  if (memoryRouterOperationsMigration) {
    store.updateModuleGraph(
      memoryRouterOperationsMigration.moduleNodeId,
      memoryRouterOperationsMigration.nodes,
      memoryRouterOperationsMigration.edges,
      memoryRouterOperationsMigration.viewport
    );
    saveModuleGraphState(memoryRouterOperationsMigration.moduleNodeId, memoryRouterOperationsMigration.nodes, memoryRouterOperationsMigration.edges);
    console.log("[P1-BRIDGE] migrated memory provider router operations", {
      moduleNodeId: memoryRouterOperationsMigration.moduleNodeId,
    });
  }
  const graphAfterMemoryRouterOperationsMigration = memoryRouterOperationsMigration ?? graphAfterMemoryRouterMigration;
  const environmentMappingsMigration = migrateEnvironmentFieldMappingsGraph(graphAfterMemoryRouterOperationsMigration, store.moduleInstanceRegistry);
  if (environmentMappingsMigration) {
    store.updateModuleGraph(
      environmentMappingsMigration.moduleNodeId,
      environmentMappingsMigration.nodes,
      environmentMappingsMigration.edges,
      environmentMappingsMigration.viewport
    );
    saveModuleGraphState(environmentMappingsMigration.moduleNodeId, environmentMappingsMigration.nodes, environmentMappingsMigration.edges);
    console.log("[P1-BRIDGE] migrated environment field DR mappings", {
      moduleNodeId: environmentMappingsMigration.moduleNodeId,
    });
  }
  const graphAfterEnvironmentMappingsMigration = environmentMappingsMigration ?? graphAfterMemoryRouterOperationsMigration;
  const userRelationshipMigration = migrateUserRelationshipConfigGraph(graphAfterEnvironmentMappingsMigration, store.moduleInstanceRegistry);
  if (userRelationshipMigration) {
    store.updateModuleGraph(
      userRelationshipMigration.moduleNodeId,
      userRelationshipMigration.nodes,
      userRelationshipMigration.edges,
      userRelationshipMigration.viewport
    );
    saveModuleGraphState(userRelationshipMigration.moduleNodeId, userRelationshipMigration.nodes, userRelationshipMigration.edges);
    console.log("[P1-BRIDGE] migrated user relationship configuration", {
      moduleNodeId: userRelationshipMigration.moduleNodeId,
    });
  }
  const graphAfterUserRelationshipMigration = userRelationshipMigration ?? graphAfterEnvironmentMappingsMigration;
  const layer11StaticConfigMigration = normalizeLayer11StaticConfigGraph(graphAfterUserRelationshipMigration, store.moduleInstanceRegistry);
  if (layer11StaticConfigMigration) {
    store.updateModuleGraph(
      layer11StaticConfigMigration.moduleNodeId,
      layer11StaticConfigMigration.nodes,
      layer11StaticConfigMigration.edges,
      layer11StaticConfigMigration.viewport
    );
    saveModuleGraphState(layer11StaticConfigMigration.moduleNodeId, layer11StaticConfigMigration.nodes, layer11StaticConfigMigration.edges);
    console.log("[P1-BRIDGE] normalized Layer 11 static configuration graph", {
      moduleNodeId: layer11StaticConfigMigration.moduleNodeId,
    });
  }
  const graphAfterLayer11StaticConfigMigration = layer11StaticConfigMigration ?? graphAfterUserRelationshipMigration;
  const layer11SemanticMigration = migrateLayer11SemanticGraph(graphAfterLayer11StaticConfigMigration, store.moduleInstanceRegistry);
  if (layer11SemanticMigration) {
    store.updateModuleGraph(
      layer11SemanticMigration.moduleNodeId,
      layer11SemanticMigration.nodes,
      layer11SemanticMigration.edges,
      layer11SemanticMigration.viewport
    );
    saveModuleGraphState(layer11SemanticMigration.moduleNodeId, layer11SemanticMigration.nodes, layer11SemanticMigration.edges);
    console.log("[P1-BRIDGE] migrated Layer 11 semantic configuration", {
      moduleNodeId: layer11SemanticMigration.moduleNodeId,
    });
  }
  const graphAfterLayer11SemanticMigration = layer11SemanticMigration ?? graphAfterLayer11StaticConfigMigration;
  const layer11P2Migration = migrateLayer11P2Graph(graphAfterLayer11SemanticMigration, store.moduleInstanceRegistry);
  if (layer11P2Migration) {
    store.updateModuleGraph(
      layer11P2Migration.moduleNodeId,
      layer11P2Migration.nodes,
      layer11P2Migration.edges,
      layer11P2Migration.viewport
    );
    saveModuleGraphState(layer11P2Migration.moduleNodeId, layer11P2Migration.nodes, layer11P2Migration.edges);
    console.log("[P2-BRIDGE] normalized Layer 11 relationship configuration", {
      moduleNodeId: layer11P2Migration.moduleNodeId,
    });
  }
  const graphAfterLayer11P2Migration = layer11P2Migration ?? graphAfterLayer11SemanticMigration;
  const layer12ReferenceMigration = migrateLayer12ReferenceGraph(
    graphAfterLayer11P2Migration,
    store.moduleInstanceRegistry,
    store.moduleGraphs
  );
  if (layer12ReferenceMigration) {
    store.updateModuleGraph(
      layer12ReferenceMigration.moduleNodeId,
      layer12ReferenceMigration.nodes,
      layer12ReferenceMigration.edges,
      layer12ReferenceMigration.viewport
    );
    saveModuleGraphState(
      layer12ReferenceMigration.moduleNodeId,
      layer12ReferenceMigration.nodes,
      layer12ReferenceMigration.edges
    );
    console.log("[P1-BRIDGE] synchronized Layer 12 module references", {
      moduleNodeId: layer12ReferenceMigration.moduleNodeId,
    });
  }
  const graphAfterLayer12ReferenceMigration = layer12ReferenceMigration ?? graphAfterLayer11P2Migration;
  const migratedGraph = migrateGenericFieldsGraph(graphAfterLayer12ReferenceMigration, store.moduleInstanceRegistry);
  if (migratedGraph) {
    store.updateModuleGraph(migratedGraph.moduleNodeId, migratedGraph.nodes, migratedGraph.edges, migratedGraph.viewport);
    saveModuleGraphState(migratedGraph.moduleNodeId, migratedGraph.nodes, migratedGraph.edges);
    console.log("[P1-BRIDGE] migrated field/text input nodes to generic_fields", {
      moduleNodeId: migratedGraph.moduleNodeId,
    });
    return migratedGraph;
  }
  return graphAfterLayer12ReferenceMigration;
}

function migrateExistingGenericFieldsGraphs() {
  const store = useCanvasStore.getState();
  for (const graph of Object.values(store.moduleGraphs)) {
    applyGenericFieldsMigration(graph);
  }
}

function persistedOrHydratedGraph(moduleNodeId: string): ModuleGraph | null {
  const hydrated = useCanvasStore.getState().moduleGraphs[moduleNodeId];
  if (hydrated) {
    return hydrated;
  }
  const persisted = loadModuleGraphState(moduleNodeId);
  if (!persisted) {
    return null;
  }
  return {
    moduleNodeId,
    nodes: persisted.nodes as WorkflowNode[],
    edges: persisted.edges as WorkflowEdge[],
  };
}

function graphFieldValue(graph: ModuleGraph, fieldId: string): unknown {
  for (const node of graph.nodes) {
    const schemaNode = schemaNodeRecord(node);
    const data = schemaNode && isRecord(schemaNode.data) ? schemaNode.data : {};
    const params = isRecord(data.params) ? data.params : {};
    const fields = Array.isArray(params.fields) ? params.fields : [];
    const field = fields.find(
      (candidate) =>
        isRecord(candidate) && String(candidate.field_id || candidate.field_key || "") === fieldId
    );
    if (isRecord(field)) {
      return "value" in field ? field.value : field.field_value;
    }
  }
  return undefined;
}

function migrateLinxuanFirstInteractionEnabledOnce() {
  if (
    hasEditorMigrationMarker(
      STAGE7_4_8_FIRST_INTERACTION_ENABLED_MIGRATION,
      LINXUAN_RESIDENT_ID
    )
  ) {
    return;
  }

  const identityGraph = persistedOrHydratedGraph(LINXUAN_IDENTITY_GRAPH_ID);
  if (!identityGraph || graphFieldValue(identityGraph, "resident_id") !== LINXUAN_RESIDENT_ID) {
    return;
  }
  const interactionGraph = persistedOrHydratedGraph(LINXUAN_INTERACTION_GRAPH_ID);
  if (!interactionGraph) {
    return;
  }

  let targetFound = false;
  let changed = false;
  const nextNodes = interactionGraph.nodes.map((node) => {
    if (catalogNodeIdFromGraphNode(node) !== "interaction_behavior_core_rules") {
      return node;
    }
    const nextNode = cloneJson(node) as WorkflowNode;
    const schemaNode = schemaNodeRecord(nextNode);
    if (!schemaNode) {
      return node;
    }
    const data = schemaDataRecord(schemaNode);
    const params = isRecord(data.params) ? { ...data.params } : {};
    if (!Array.isArray(params.fields)) {
      return node;
    }
    let nodeChanged = false;
    const nextFields = params.fields.map((field) => {
      if (!isRecord(field) || String(field.field_id || field.field_key || "") !== "first_interaction") {
        return field;
      }
      const migration = migrateLinxuanFirstInteractionEnabledValue(
        LINXUAN_RESIDENT_ID,
        false,
        field.value
      );
      targetFound ||= migration.markComplete;
      if (!migration.migrated) {
        return field;
      }
      changed = true;
      nodeChanged = true;
      return { ...field, value: migration.value };
    });
    if (!targetFound) {
      return node;
    }
    params.fields = nextFields;
    data.params = params;
    return nodeChanged ? nextNode : node;
  });

  if (!targetFound) {
    return;
  }
  const nextGraph = changed ? { ...interactionGraph, nodes: nextNodes } : interactionGraph;
  const store = useCanvasStore.getState();
  store.updateModuleGraph(
    nextGraph.moduleNodeId,
    nextGraph.nodes,
    nextGraph.edges,
    nextGraph.viewport
  );
  if (!saveModuleGraphState(nextGraph.moduleNodeId, nextGraph.nodes, nextGraph.edges)) {
    return;
  }
  saveEditorMigrationMarker(
    STAGE7_4_8_FIRST_INTERACTION_ENABLED_MIGRATION,
    LINXUAN_RESIDENT_ID
  );
}

function migrateLinxuanFirstGreetingContentOnce() {
  if (
    hasEditorMigrationMarker(
      STAGE7_4_8_FIRST_GREETING_CONTENT_MIGRATION,
      LINXUAN_RESIDENT_ID
    )
  ) {
    return;
  }

  const identityGraph = persistedOrHydratedGraph(LINXUAN_IDENTITY_GRAPH_ID);
  if (!identityGraph || graphFieldValue(identityGraph, "resident_id") !== LINXUAN_RESIDENT_ID) {
    return;
  }
  const visualStyleGraph = persistedOrHydratedGraph(VISUAL_STYLE_GRAPH_ID);
  if (!visualStyleGraph) {
    return;
  }

  let targetFound = false;
  let changed = false;
  const nextNodes = visualStyleGraph.nodes.map((node) => {
    if (catalogNodeIdFromGraphNode(node) !== "visual_style_first_greeting_config") {
      return node;
    }
    const nextNode = cloneJson(node) as WorkflowNode;
    const schemaNode = schemaNodeRecord(nextNode);
    if (!schemaNode) return node;
    const data = schemaDataRecord(schemaNode);
    const params = isRecord(data.params) ? { ...data.params } : {};
    if (!Array.isArray(params.fields)) return node;
    let nodeChanged = false;
    const nextFields = params.fields.map((field) => {
      if (!isRecord(field) || String(field.field_id || field.field_key || "") !== "first_greeting") {
        return field;
      }
      const valueKey = "field_value" in field ? "field_value" : "value";
      const migration = migrateLinxuanFirstGreetingValue(
        LINXUAN_RESIDENT_ID,
        false,
        field[valueKey]
      );
      targetFound ||= migration.markComplete;
      if (!migration.migrated) return field;
      changed = true;
      nodeChanged = true;
      return { ...field, [valueKey]: migration.value };
    });
    if (!targetFound) return node;
    params.fields = nextFields;
    data.params = params;
    return nodeChanged ? nextNode : node;
  });

  if (!targetFound) return;
  const nextGraph = changed ? { ...visualStyleGraph, nodes: nextNodes } : visualStyleGraph;
  const store = useCanvasStore.getState();
  store.updateModuleGraph(nextGraph.moduleNodeId, nextGraph.nodes, nextGraph.edges, nextGraph.viewport);
  if (!saveModuleGraphState(nextGraph.moduleNodeId, nextGraph.nodes, nextGraph.edges)) return;
  saveEditorMigrationMarker(
    STAGE7_4_8_FIRST_GREETING_CONTENT_MIGRATION,
    LINXUAN_RESIDENT_ID
  );
}

/**
 * 初始化 module state 水合
 * 
 * 优先级：store > localStorage > 默认值
 * 
 * 这个函数应该在 CanvasShell 首次挂载时调用（在所有 UI 渲染之前）
 */
export function initializeModuleState() {
  console.log("[P1-BRIDGE] initializeModuleState: starting hydration");
  
  const store = useCanvasStore.getState();
  
  // 1. 尝试从 localStorage 恢复（作为后备方案）
  const stored = loadCanvasStateFromLocalStorage();
  const storeHasAttachedModules = attachedModuleIdsFromLayerModules(store.layerModules).length > 0;
  
  // 2. 构建完整的 module state（store 优先）
  const moduleState = {
    moduleTabs: store.moduleTabs.length > 0 
      ? store.moduleTabs 
      : stored?.moduleTabs ?? [],
    activeModuleTabId: store.activeModuleTabId,
    moduleNames: Object.keys(store.moduleNames).length > 0
      ? store.moduleNames
      : stored?.moduleNames ?? {},
    uiNodeNames: Object.keys(store.uiNodeNames).length > 0
      ? store.uiNodeNames
      : stored?.uiNodeNames ?? {},
    uiTags: Object.keys(store.uiTags).length > 0
      ? store.uiTags
      : stored?.uiTags ?? {},
    uiGroups: Object.keys(store.uiGroups).length > 0
      ? store.uiGroups
      : stored?.uiGroups ?? {},
    uiColors: Object.keys(store.uiColors).length > 0
      ? store.uiColors
      : stored?.uiColors ?? {},
    moduleUiColors: Object.keys(store.moduleUiColors).length > 0
      ? store.moduleUiColors
      : stored?.moduleUiColors ?? {},
    layerModules: storeHasAttachedModules
      ? store.layerModules
      : stored?.layerModules ?? {},
    moduleInstanceRegistry: storeHasAttachedModules && Object.keys(store.moduleInstanceRegistry).length > 0
      ? store.moduleInstanceRegistry
      : stored?.moduleInstanceRegistry ?? {},
  };
  
  // 3. 同步回 store
  store.setModuleTabs(moduleState.moduleTabs);
  store.setModuleNames(moduleState.moduleNames);
  store.setUiNodeNames(moduleState.uiNodeNames);
  store.setUiTags(moduleState.uiTags);
  store.setUiGroups(moduleState.uiGroups);
  store.setUiColors(moduleState.uiColors);
  store.setModuleUiColors(moduleState.moduleUiColors);
  store.setLayerModules(moduleState.layerModules);
  store.setModuleInstanceRegistry(moduleState.moduleInstanceRegistry);
  migrateLinxuanFirstInteractionEnabledOnce();
  migrateLinxuanFirstGreetingContentOnce();
  migrateExistingGenericFieldsGraphs();
  
  console.log("[P1-BRIDGE] initializeModuleState: hydration completed", {
    tabCount: moduleState.moduleTabs.length,
    instanceCount: Object.keys(moduleState.moduleInstanceRegistry).length,
  });
  return moduleState;
}

/**
 * 为某个 module tab 初始化或恢复其 graph
 * 
 * 优先级：
 * 1. store 中已存在的 graph
 * 2. localStorage 中保存的 graph（从旧的 `module_graph_${moduleId}` key）
 * 3. 创建空 graph
 */
export function ensureModuleGraphExists(moduleNodeId: string, initialNodes?: WorkflowNode[], initialEdges?: WorkflowEdge[]) {
  console.log("[P1-BRIDGE] ensureModuleGraphExists:", { moduleNodeId });

  if (moduleNodeId === LINXUAN_IDENTITY_GRAPH_ID || moduleNodeId === LINXUAN_INTERACTION_GRAPH_ID) {
    migrateLinxuanFirstInteractionEnabledOnce();
  }
  if (moduleNodeId === LINXUAN_IDENTITY_GRAPH_ID || moduleNodeId === VISUAL_STYLE_GRAPH_ID) {
    migrateLinxuanFirstGreetingContentOnce();
  }
  const store = useCanvasStore.getState();
  const hasInitialGraph = Boolean(initialNodes?.length || initialEdges?.length);
  
  // 1. 检查 store 中是否已存在
  const existingGraph = store.moduleGraphs[moduleNodeId];
  if (existingGraph) {
    if (shouldReplaceWithCatalogGraph(existingGraph, initialNodes, initialEdges)) {
      const graph: ModuleGraph = {
        moduleNodeId,
        nodes: initialNodes ?? [],
        edges: initialEdges ?? [],
        viewport: existingGraph.viewport,
      };
      store.updateModuleGraph(moduleNodeId, graph.nodes, graph.edges, graph.viewport);
      saveModuleGraphState(moduleNodeId, graph.nodes, graph.edges);
      console.log("[P1-BRIDGE] ensureModuleGraphExists: replaced stale catalog graph with current seed");
      return applyGenericFieldsMigration(graph);
    }
    const hasExistingGraph = Boolean(existingGraph.nodes?.length || existingGraph.edges?.length);
    if (!hasExistingGraph && hasInitialGraph) {
      const graph: ModuleGraph = {
        moduleNodeId,
        nodes: initialNodes ?? [],
        edges: initialEdges ?? [],
        viewport: existingGraph.viewport,
      };
      store.updateModuleGraph(moduleNodeId, graph.nodes, graph.edges, graph.viewport);
      console.log("[P1-BRIDGE] ensureModuleGraphExists: replaced empty graph with catalog seed");
      return applyGenericFieldsMigration(graph);
    }
    const mergedGraph = mergeCatalogSeed(existingGraph, initialNodes, initialEdges);
    if (mergedGraph) {
      store.updateModuleGraph(moduleNodeId, mergedGraph.nodes, mergedGraph.edges, mergedGraph.viewport);
      if (moduleNodeId === VISUAL_STYLE_GRAPH_ID || moduleNodeId === DIALOGUE_RUNTIME_PROFILE_GRAPH_ID) {
        saveModuleGraphState(moduleNodeId, mergedGraph.nodes, mergedGraph.edges);
      }
      console.log("[P1-BRIDGE] ensureModuleGraphExists: merged catalog field seed into existing graph");
      return applyGenericFieldsMigration(mergedGraph);
    }
    console.log("[P1-BRIDGE] ensureModuleGraphExists: graph already in store");
    return applyGenericFieldsMigration(existingGraph);
  }
  
  // 2. 尝试从 localStorage 恢复（旧的单个 graph 存储）
  const legacyGraph = loadModuleGraphState(moduleNodeId);
  if (legacyGraph?.nodes?.length || legacyGraph?.edges?.length) {
    console.log("[P1-BRIDGE] ensureModuleGraphExists: graph found in legacy localStorage");
    const graph: ModuleGraph = {
      moduleNodeId,
      nodes: legacyGraph.nodes as WorkflowNode[],
      edges: legacyGraph.edges as WorkflowEdge[],
    };
    if (shouldReplaceWithCatalogGraph(graph, initialNodes, initialEdges)) {
      const seedGraph: ModuleGraph = {
        moduleNodeId,
        nodes: initialNodes ?? [],
        edges: initialEdges ?? [],
      };
      store.updateModuleGraph(moduleNodeId, seedGraph.nodes, seedGraph.edges, seedGraph.viewport);
      saveModuleGraphState(moduleNodeId, seedGraph.nodes, seedGraph.edges);
      console.log("[P1-BRIDGE] ensureModuleGraphExists: replaced stale legacy graph with current catalog seed");
      return applyGenericFieldsMigration(seedGraph);
    }
    const mergedGraph = mergeCatalogSeed(graph, initialNodes, initialEdges) ?? graph;
    store.updateModuleGraph(moduleNodeId, mergedGraph.nodes, mergedGraph.edges, mergedGraph.viewport);
    if (mergedGraph !== graph) {
      if (moduleNodeId === VISUAL_STYLE_GRAPH_ID || moduleNodeId === DIALOGUE_RUNTIME_PROFILE_GRAPH_ID) {
        saveModuleGraphState(moduleNodeId, mergedGraph.nodes, mergedGraph.edges);
      }
      console.log("[P1-BRIDGE] ensureModuleGraphExists: merged catalog field seed into legacy graph");
    }
    return applyGenericFieldsMigration(mergedGraph);
  }
  
  // 3. 创建新的空 graph
  const newGraph: ModuleGraph = {
    moduleNodeId,
    nodes: initialNodes ?? [],
    edges: initialEdges ?? [],
  };
  store.updateModuleGraph(moduleNodeId, newGraph.nodes, newGraph.edges);
  console.log(hasInitialGraph ? "[P1-BRIDGE] ensureModuleGraphExists: created graph from catalog seed" : "[P1-BRIDGE] ensureModuleGraphExists: created new empty graph");
  
  return applyGenericFieldsMigration(newGraph);
}

/**
 * 清理孤立的 graph（对应的 module 不在 moduleTabs 中）
 */
export function cleanupOrphanedGraphs() {
  console.log("[P1-BRIDGE] cleanupOrphanedGraphs: starting");
  // Do not delete graphs merely because their tab is not currently open.
  // Module graph ids include the layer-scoped instance id; when a module is
  // displayed under its catalog layer, older instance ids can still hold the
  // user's filled node data and must remain available for recovery.
  console.log("[P1-BRIDGE] cleanupOrphanedGraphs: skipped to preserve recoverable module graphs");
}

/**
 * 为所有 tabs 确保都有对应的 graph
 */
export function ensureAllTabsHaveGraphs() {
  console.log("[P1-BRIDGE] ensureAllTabsHaveGraphs: starting");
  
  const store = useCanvasStore.getState();
  const tabs = store.moduleTabs;
  const graphs = store.moduleGraphs;
  
  let created = 0;
  
  for (const tabId of tabs) {
    if (!graphs[tabId]) {
      ensureModuleGraphExists(tabId);
      created++;
    }
  }
  
  console.log("[P1-BRIDGE] ensureAllTabsHaveGraphs: completed", { 
    totalTabs: tabs.length, 
    createdGraphs: created,
  });
}

/**
 * 处理 tab 打开事件
 */
export function handleTabOpened(moduleId: string, initialNodes?: WorkflowNode[], initialEdges?: WorkflowEdge[]) {
  console.log("[P1-BRIDGE] handleTabOpened:", { moduleId });
  
  const store = useCanvasStore.getState();
  
  // 1. 确保 tab 在 moduleTabs 中
  if (!store.moduleTabs.includes(moduleId)) {
    store.openModuleTab(moduleId);
  }
  
  // 2. 确保 graph 存在
  ensureModuleGraphExists(moduleId, initialNodes, initialEdges);
  
  // 3. 设置为 active
  store.setActiveModuleTabId(moduleId);
}

/**
 * 处理 tab 关闭事件
 */
export function handleTabClosed(moduleId: string) {
  console.log("[P1-BRIDGE] handleTabClosed:", { moduleId });
  
  const store = useCanvasStore.getState();
  
  // 1. 从 moduleTabs 移除
  store.closeModuleTab(moduleId);
  
  // 2. 可选：清理对应的 graph（取决于是否希望保留以便重新打开）
  // 如果希望关闭后再打开时恢复数据，不删除 graph
  // store.removeModuleGraph(moduleId);
}

/**
 * 从 CanvasShell useState 迁移到 store 的临时适配器
 * 
 * 用法：
 * const stateAdapter = createStateAdapter(localModuleTabs, localModuleNames, ...);
 * // 使用 stateAdapter 中的值作为 React state 的初始值
 * // 同时将这些值同步到 store
 */
export function createStateAdapter(
  localModuleTabs: string[],
  localModuleNames: Record<string, string>,
  localUiNodeNames: Record<string, string>,
  localUiTags: Record<string, string[]>,
  localUiGroups: Record<string, string>,
  localUiColors: Record<string, string>,
  localModuleUiColors: Record<string, string>,
  localLayerModules: Record<string, string[]>,
  localModuleInstanceRegistry: Record<string, ModuleInstance>
) {
  const store = useCanvasStore.getState();
  
  // 同步 useState 的值到 store
  if (localModuleTabs.length > 0) {
    store.setModuleTabs(localModuleTabs);
  }
  if (Object.keys(localModuleNames).length > 0) {
    store.setModuleNames(localModuleNames);
  }
  if (Object.keys(localUiNodeNames).length > 0) {
    store.setUiNodeNames(localUiNodeNames);
  }
  if (Object.keys(localUiTags).length > 0) {
    store.setUiTags(localUiTags);
  }
  if (Object.keys(localUiGroups).length > 0) {
    store.setUiGroups(localUiGroups);
  }
  if (Object.keys(localUiColors).length > 0) {
    store.setUiColors(localUiColors);
  }
  if (Object.keys(localModuleUiColors).length > 0) {
    store.setModuleUiColors(localModuleUiColors);
  }
  if (Object.keys(localLayerModules).length > 0) {
    store.setLayerModules(localLayerModules);
  }
  if (Object.keys(localModuleInstanceRegistry).length > 0) {
    store.setModuleInstanceRegistry(localModuleInstanceRegistry);
  }
  
  return {
    moduleTabs: localModuleTabs,
    moduleNames: localModuleNames,
    uiNodeNames: localUiNodeNames,
    uiTags: localUiTags,
    uiGroups: localUiGroups,
    uiColors: localUiColors,
    moduleUiColors: localModuleUiColors,
    layerModules: localLayerModules,
    moduleInstanceRegistry: localModuleInstanceRegistry,
  };
}
