import type { Workflow } from "@/lib/schema-types";
import { sanitizeWorkflow } from "@/lib/workflow";

// Persistence layer for the workflow JSON. Stores the full graph (nodes / edges /
// position / data) under localStorage key `workflow_<workflow_id>`. Only two
// functions are exposed: saveWorkflow() and loadWorkflow().

const KEY_PREFIX = "workflow_";

function workflowKey(workflow: Pick<Workflow, "workflow_id" | "name">) {
  return `${KEY_PREFIX}${workflow.workflow_id ?? workflow.name ?? "default"}`;
}

export function saveWorkflow(workflow: Workflow) {
  if (typeof window === "undefined") {
    return;
  }
  try {
    window.localStorage.setItem(workflowKey(workflow), JSON.stringify(workflow));
  } catch {
    // ignore storage quota / serialization errors
  }
}

export function loadWorkflow(): Workflow | null {
  if (typeof window === "undefined") {
    return null;
  }
  const candidates: Workflow[] = [];
  try {
    for (let index = 0; index < window.localStorage.length; index += 1) {
      const key = window.localStorage.key(index);
      if (!key || !key.startsWith(KEY_PREFIX)) {
        continue;
      }
      try {
        const raw = window.localStorage.getItem(key);
        if (raw) {
          candidates.push(sanitizeWorkflow(JSON.parse(raw)));
        }
      } catch {
        try {
          window.localStorage.removeItem(key);
        } catch {
          // ignore storage cleanup errors
        }
      }
    }
  } catch {
    return null;
  }
  if (!candidates.length) {
    return null;
  }
  // Most recently updated workflow wins.
  candidates.sort((a, b) => String(b.updated_at ?? "").localeCompare(String(a.updated_at ?? "")));
  return candidates[0];
}

// Module sub-canvas persistence. Module-canvas nodes are UI-shaped (not schema
// WorkflowNodes), so they are stored raw under their own key and never run
// through the workflow sanitizer or pollute workflow_<id>.
const MODULE_KEY_PREFIX = "module_canvas_";

export type ModuleCanvasSnapshot = {
  nodes: unknown[];
  edges: unknown[];
};

export function saveModuleCanvas(moduleId: string, snapshot: ModuleCanvasSnapshot) {
  if (typeof window === "undefined") {
    return;
  }
  try {
    window.localStorage.setItem(`${MODULE_KEY_PREFIX}${moduleId}`, JSON.stringify(snapshot));
  } catch {
    // ignore storage quota / serialization errors
  }
}

export function loadModuleCanvas(moduleId: string): ModuleCanvasSnapshot | null {
  if (typeof window === "undefined") {
    return null;
  }
  try {
    const raw = window.localStorage.getItem(`${MODULE_KEY_PREFIX}${moduleId}`);
    if (!raw) {
      return null;
    }
    const parsed = JSON.parse(raw) as Partial<ModuleCanvasSnapshot>;
    if (!Array.isArray(parsed.nodes) || !Array.isArray(parsed.edges)) {
      return null;
    }
    const nodes = parsed.nodes.filter(
      (node): node is Record<string, unknown> => Boolean(node && typeof node === "object" && typeof (node as { id?: unknown }).id === "string")
    );
    const edges = parsed.edges.filter(
      (edge): edge is Record<string, unknown> => Boolean(edge && typeof edge === "object" && typeof (edge as { id?: unknown }).id === "string")
    );
    return { nodes, edges };
  } catch {
    try {
      window.localStorage.removeItem(`${MODULE_KEY_PREFIX}${moduleId}`);
    } catch {
      // ignore storage cleanup errors
    }
    return null;
  }
}
