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
  schema_version: "0.3.0" | string;
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
