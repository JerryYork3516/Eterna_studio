import type {
  ExportPreview,
  EngineRegistryResponseV04,
  ModuleCatalogResponseV04,
  NodeRegistryEntry,
  ResidentCompileResponse,
  ResidentStepResponse,
  RunResult,
  SlotCatalogResponseV04,
  TemplateDefinition,
  ValidateResponse,
  Workflow
} from "@/lib/schema-types";

function resolveApiBase() {
  const configuredBase = process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/+$/, "");

  if (typeof window === "undefined") {
    return configuredBase || "http://127.0.0.1:8000";
  }

  const isLocalHost = window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1";
  const isPrivateHost =
    /^10\./.test(window.location.hostname) ||
    /^192\.168\./.test(window.location.hostname) ||
    /^172\.(1[6-9]|2\d|3[0-1])\./.test(window.location.hostname);

  if (configuredBase && !(window.location.protocol === "https:" && configuredBase.startsWith("http://"))) {
    return configuredBase;
  }

  if (isLocalHost || isPrivateHost) {
    return `${window.location.protocol}//${window.location.hostname}:8000`;
  }

  return "/api";
}

const API_BASE = resolveApiBase();

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      ...init,
      headers: {
        "Content-Type": "application/json",
        ...init?.headers
      }
    });
  } catch (error) {
    throw new Error(`Network error: ${(error as Error).message}`);
  }

  if (!response.ok) {
    throw new Error(await formatErrorResponse(response));
  }

  if (response.status === 204) {
    throw new Error(`Empty response (204 No Content) from ${path}`);
  }

  const text = await response.text();
  if (!text) {
    throw new Error(`Empty response (${response.status}) from ${path}`);
  }

  const contentType = response.headers.get("content-type") ?? "";
  if (contentType && !contentType.includes("application/json")) {
    throw new Error(`Expected JSON response from ${path}, received ${contentType}`);
  }

  try {
    return JSON.parse(text) as T;
  } catch {
    throw new Error(`Invalid JSON response from ${path}`);
  }
}

async function formatErrorResponse(response: Response) {
  const text = await response.text();
  const prefix = `${response.status} ${response.statusText || "Error"}`;
  if (!text) {
    return prefix;
  }

  try {
    const body = JSON.parse(text) as { detail?: unknown; message?: unknown; error?: unknown };
    const detail = body.detail ?? body.message ?? body.error;
    return detail ? `${prefix}: ${typeof detail === "string" ? detail : JSON.stringify(detail)}` : `${prefix}: ${text}`;
  } catch {
    return `${prefix}: ${text.slice(0, 500)}`;
  }
}

export const api = {
  health() {
    return request<{ status: string; schema_version: string }>("/health");
  },
  listTemplates() {
    return request<{ templates: TemplateDefinition[] }>("/templates/list");
  },
  createPersonaBuilder(name: string | undefined, uiLanguage: string) {
    return request<{ workflow: Workflow }>("/templates/persona-builder", {
      method: "POST",
      body: JSON.stringify({ name, ui_language: uiLanguage })
    });
  },
  validateWorkflow(workflow: Workflow) {
    return request<ValidateResponse>("/workflow/validate", {
      method: "POST",
      body: JSON.stringify({ workflow })
    });
  },
  /**
   * @deprecated REPLACED by the Stage 6 Runtime Kernel. Do NOT call from the UI.
   * The v0.3 workflow adapter (/workflow/mock-run) is no longer the execution
   * path — use `executeResidentStep` (POST /runtime/resident/step) instead.
   * Kept only for legacy/back-compat callers; the Studio Run button never uses it.
   */
  mockRun(workflow: Workflow) {
    return request<{ run: RunResult }>("/workflow/mock-run", {
      method: "POST",
      body: JSON.stringify({ workflow })
    });
  },
  exportPreview(workflow: Workflow, exportKind: "workflow_json" | "persona" | "resident") {
    return request<{ preview: ExportPreview }>("/workflow/export-preview", {
      method: "POST",
      body: JSON.stringify({ workflow, export_kind: exportKind })
    });
  },
  fetchNodeRegistry() {
    return request<Record<string, NodeRegistryEntry>>("/schema/node-registry-v0.4");
  },
  fetchModuleCatalog() {
    return request<ModuleCatalogResponseV04>("/schema/module-catalog-v0.4");
  },
  fetchSlotCatalog() {
    return request<SlotCatalogResponseV04>("/schema/slot-catalog-v0.4");
  },
  fetchEngineRegistry() {
    return request<EngineRegistryResponseV04>("/schema/engine-registry-v0.4");
  },
  /**
   * @deprecated Execution is backend-only (v0.3 adapter). UI does not directly compile residents.
   * This method is kept for compatibility but should not be called from the UI.
   */
  fetchResidentInstance(workflow: Workflow) {
    return request<ResidentCompileResponse>("/resident/compile", {
      method: "POST",
      body: JSON.stringify({ workflow })
    });
  },
  // Stage 6 Runtime Kernel — THE execution entry. The Studio Run button dispatches
  // here; the backend Execution Engine is the sole runtime entry (UI never calls a
  // provider). The response carries trace / memory_snapshot / status / run_id /
  // output_text for the panels (see runtime-hydration.ts).
  executeResidentStep(workflow: Workflow, inputText: string, residentId?: string) {
    return request<ResidentStepResponse>("/runtime/resident/step", {
      method: "POST",
      body: JSON.stringify({ workflow, input_text: inputText, resident_id: residentId })
    });
  },
  // Stage 6.2 DR Compiler — compile the canvas into a downloadable
  // .digital_resident file. The compile logic is backend-only (dr_compiler); the
  // UI just posts the canvas and receives the file blob (never bare JSON).
  async compileDR(workflow: Workflow, residentName?: string): Promise<{ blob: Blob; filename: string; auditValid: boolean }> {
    let response: Response;
    try {
      response = await fetch(`${API_BASE}/dr/compile`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ workflow, resident_name: residentName })
      });
    } catch (error) {
      throw new Error(`Network error: ${(error as Error).message}`);
    }
    if (!response.ok) {
      throw new Error(await formatErrorResponse(response));
    }
    const blob = await response.blob();
    const headerName = response.headers.get("X-DR-Filename");
    const filename = headerName || `${(residentName || workflow.name || "digital_resident").toLowerCase().replace(/[^a-z0-9]+/g, "_")}.digital_resident`;
    const auditValid = (response.headers.get("X-DR-Audit-Valid") ?? "true") === "true";
    return { blob, filename, auditValid };
  }
};
