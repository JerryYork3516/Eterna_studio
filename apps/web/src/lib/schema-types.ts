import type { components } from "@eterna/shared-schema/openapi";
import {
  CANONICAL_LAYERS,
  CANONICAL_LAYER_IDS,
  CANONICAL_LAYER_NAMES,
  CANONICAL_LAYER_ORDERS,
  CANONICAL_LAYER_ID_TO_NAME,
  CANONICAL_LAYER_ID_TO_ORDER,
  validateCanonicalLayers,
  isValidLayerId,
  getLayerName,
  getLayerOrder,
  type CanonicalLayerTuple,
} from "./canonical-layers";

export {
  CANONICAL_LAYERS,
  CANONICAL_LAYER_IDS,
  CANONICAL_LAYER_NAMES,
  CANONICAL_LAYER_ORDERS,
  CANONICAL_LAYER_ID_TO_NAME,
  CANONICAL_LAYER_ID_TO_ORDER,
  validateCanonicalLayers,
  isValidLayerId,
  getLayerName,
  getLayerOrder,
  type CanonicalLayerTuple,
};

// P2-D：Slot Catalog 校验
export {
  ALLOWED_SLOT_TYPES,
  isValidSlotType,
  validateSlotEntry,
  validateSlotCatalog,
  findSlotById,
  validateSlotBinding,
  getSlotCatalogStats,
} from "./slot-catalog-v0.4";

// P2-E：Engine Registry 校验
export {
  ALLOWED_ENGINE_TYPES,
  ALLOWED_PROVIDERS,
  isValidEngineType,
  isValidProvider,
  validateEngineEntry,
  validateEngineRegistry,
  findEngineById,
  findEngineByBinding,
  getEngineMockDisplay,
  getEngineRegistryStats,
  checkForRealProviders,
} from "./engine-registry-v0.4";

export type Artifact = components["schemas"]["Artifact"];
export type ExportPreview = components["schemas"]["ExportPreview"];
export type RunLog = components["schemas"]["RunLog"];
export type RunResult = components["schemas"]["RunResult"];
export type TemplateDefinition = components["schemas"]["TemplateDefinition"];
export type ValidateResponse = components["schemas"]["WorkflowValidationResponseV03"];
export type WorkflowV03 = components["schemas"]["WorkflowV03"];
export type ResidentInstanceV03 = components["schemas"]["ResidentInstanceV03"];
export type AuditReportV03 = components["schemas"]["AuditReportV03"];
export type NodeInputField = components["schemas"]["NodeInputField"];
export type ResidentCompileResponseV03 = components["schemas"]["ResidentCompileResponseV03"];
export type OutputSchemaField = components["schemas"]["OutputSchemaField"];
export type NodeStatus = components["schemas"]["NodeStatus"];
export type ProtocolStatus = "CORE" | "READY" | "MOCK" | "PLANNED" | "LATER" | "DISABLED";
export type NodeRegistryEntry = {
  type: string;
  category: string;
  display_name: string;
  description: string;
  input_schema: NodeInputField[];
  output_schema: OutputSchemaField[];
  status: NodeStatus | ProtocolStatus | string;
  mock_executor?: string | null;
  audit_rules: string[];
};

export type ModuleCatalogEntryV04 = {
  module_id: string;
  module_name: string;
  layer_id: string;
  category: string;
  status: ProtocolStatus | string;
  slot_type?: string | null;
  engine_binding?: string | null;
  description?: string | null;
  [key: string]: unknown;
};

export type ModuleLayerV04 = {
  layer_id: string;
  layer_order: number;
  layer_index?: number;
  layer_name: string;
  [key: string]: unknown;
};

export type ModuleCatalogResponseV04 = {
  schema_version: "0.4.0";
  protocol_version: "0.4.0";
  layers: ModuleLayerV04[];
  modules: ModuleCatalogEntryV04[];
};

export type SlotCatalogEntryV04 = {
  slot_id: string;
  slot_type: string;
  status: ProtocolStatus | string;
  engine_binding?: string | null;
  [key: string]: unknown;
};

export type SlotCatalogResponseV04 = {
  schema_version: "0.4.0";
  protocol_version: "0.4.0";
  slots: SlotCatalogEntryV04[];
};

export type EngineRegistryEntryV04 = {
  engine_id: string;
  engine_type: string;
  status: ProtocolStatus | string;
  [key: string]: unknown;
};

export type EngineRegistryResponseV04 = {
  schema_version: "0.4.0";
  protocol_version: "0.4.0";
  engines: EngineRegistryEntryV04[];
};

export type ResidentCompileResponse = ResidentCompileResponseV03 | Record<string, unknown>;

export type NodeType =
  | "input"
  | "transform"
  | "model"
  | "agent"
  | "review"
  | "layer_container"
  | "output"
  | "export"
  | "module"
  | "text"
  | "reasoning"
  | string;

export type LockLevel = "editable" | "review_required" | "locked" | "system_locked" | "mixed";

export type WorkflowPort = {
  port_id: string;
  name: string;
  direction: "in" | "out";
};

export type WorkflowNode = {
  node_id: string;
  type: NodeType;
  category: string;
  title_key: string;
  title_fallback: string;
  position: { x: number; y: number };
  lock_level: LockLevel;
  locale?: string | null;
  data: Record<string, unknown>;
  ports: {
    inputs: WorkflowPort[];
    outputs: WorkflowPort[];
  };
  validation?: { status?: string; [key: string]: unknown } | null;
  /**
   * P2-C：Node slot binding
   * 指向 Slot Catalog 中的某个 slot_id
   * 如果存在，表示该节点需要调用该 Slot 对应的能力
   * 当前阶段仅支持 mock slot
   */
  slot_binding?: string | null;
  /**
   * P2-C：Node layer reference
   * 指向某个 layer_id（必须是 CANONICAL_LAYER_IDS 中的值）
   * 用于在 UI 上展示 node 所属的层级
   */
  layer_id?: string | null;
  /**
   * P2-C：Node module reference
   * 指向某个 module_id
   * 当前阶段可为空
   */
  module_id?: string | null;
};

export type WorkflowEdge = {
  edge_id: string;
  source: string;
  source_port: string;
  target: string;
  target_port: string;
};

export type Workflow = {
  // Schema lock: v0.4 single-source enforcement — exactly "0.4.0", no string union.
  schema_version: "0.4.0";
  /**
   * P2-C：Protocol version
   * 必须为 "0.4.0"
   */
  protocol_version?: "0.4.0";
  workflow_id?: string;
  name: string;
  version?: string;
  template_type: string;
  content_locale?: string | null;
  nodes: WorkflowNode[];
  edges: WorkflowEdge[];
  viewport?: { x: number; y: number; zoom: number } | null;
  /**
   * P2-C：Module registry
   * 当前在这个 workflow 中使用的所有 module
   */
  modules?: Array<{
    module_id: string;
    module_name?: string;
    layer_id?: string;
    [key: string]: unknown;
  }>;
  /**
   * P2-C：Workflow permissions
   * 工作流级别的权限声明
   */
  permissions?: string[];
  /**
   * P2-C：Risk level
   * 工作流的风险等级
   */
  risk_level?: "none" | "low" | "medium" | "high" | "critical";
  /**
   * P2-C：Audit log
   * 审计日志列表
   */
  audit_log?: Array<{
    timestamp?: string;
    action?: string;
    actor?: string;
    [key: string]: unknown;
  }>;
  /**
   * P2-C：Extensions
   * 扩展字段，保存 v0.3 兼容信息等
   */
  extensions?: Record<string, unknown>;
  metadata: Record<string, unknown> & { ui_language?: "zh" | "en" | string };
  created_at?: string;
  updated_at?: string;
};
