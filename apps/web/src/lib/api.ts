import type {
  ExportPreview,
  RunResult,
  TemplateDefinition,
  ValidateResponse,
  Workflow
} from "@/lib/schema-types";

function resolveApiBase() {
  if (process.env.NEXT_PUBLIC_API_BASE_URL) {
    return process.env.NEXT_PUBLIC_API_BASE_URL;
  }

  if (typeof window !== "undefined") {
    return `${window.location.protocol}//${window.location.hostname}:8000`;
  }

  return "http://127.0.0.1:8000";
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
  mockRun(workflow: Workflow) {
    return request<{ run: RunResult }>("/workflow/mock-run", {
      method: "POST",
      body: JSON.stringify({ workflow })
    });
  },
  exportPreview(workflow: Workflow, exportKind: "workflow_json" | "persona") {
    return request<{ preview: ExportPreview }>("/workflow/export-preview", {
      method: "POST",
      body: JSON.stringify({ workflow, export_kind: exportKind })
    });
  }
};
