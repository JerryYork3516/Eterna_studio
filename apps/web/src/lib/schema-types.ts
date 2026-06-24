import type { components } from "@eterna/shared-schema/openapi";

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
  layer_index: number;
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
  workflow_id?: string;
  name: string;
  version?: string;
  template_type: string;
  content_locale?: string | null;
  nodes: WorkflowNode[];
  edges: WorkflowEdge[];
  viewport?: { x: number; y: number; zoom: number } | null;
  metadata: Record<string, unknown> & { ui_language?: "zh" | "en" | string };
  created_at?: string;
  updated_at?: string;
};
