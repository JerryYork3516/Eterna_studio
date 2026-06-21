// Module = Workflow run container (NOT a graph container).
// A Module only does two things:
//   1. bind a workflow_id (which workflow to open)
//   2. manage UI state
// It never stores nodes, edges, or any graph structure. The actual graph lives
// in the Workflow JSON / Node Registry, which this type deliberately does not touch.

export type ModuleRuntimeStatus = "idle" | "running" | "success" | "error";

export type ModuleUiState = {
  collapsed?: boolean;
  position?: { x: number; y: number };
  active_tab?: string;
};

export type ModuleRuntimeState = {
  status: ModuleRuntimeStatus;
};

export type Module = {
  module_id: string;
  workflow_id: string;
  ui_state: ModuleUiState;
  runtime_state?: ModuleRuntimeState;
};

// Construct a Module bound to a workflow_id. UI state defaults to empty.
export function createModule(module_id: string, workflow_id: string, ui_state: ModuleUiState = {}): Module {
  return { module_id, workflow_id, ui_state };
}
