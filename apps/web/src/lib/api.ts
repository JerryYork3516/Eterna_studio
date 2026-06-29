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
  // Stage 6.3.3 DR Compile (validate, NO download). Backend runs dr_compiler +
  // validate_dr_v0_2 and returns a JSON result. The UI saves the result and only
  // downloads later via the separate Export action. Compile logic is backend-only.
  compileDR(workflow: Workflow, residentName?: string) {
    return request<DRCompileResult>("/dr/compile", {
      method: "POST",
      body: JSON.stringify({ workflow, resident_name: residentName })
    });
  },
  // Stage 6.4 Runtime Load DR: upload/read a validated .digital_resident JSON
  // payload and let the backend runtime run one mock resident step from it.
  loadDigitalResident(dr: Record<string, unknown>, inputText?: string) {
    return request<DRLoadResult>("/runtime/resident/load-dr", {
      method: "POST",
      body: JSON.stringify({ dr, input_text: inputText })
    });
  },
  // Stage 6 preview shortcut: load the already compiled payload without
  // requiring an export/download/import round trip.
  loadCompiledDigitalResident(dr: Record<string, unknown>, filename?: string) {
    return request<DRLoadResult>("/runtime/resident/load-dr", {
      method: "POST",
      body: JSON.stringify({ dr, input_text: `Load compiled file: ${filename || "compiled.digital_resident"}` })
    });
  },
  // Stage 6.6 real LLM v2 — the UI manages masked runtime profiles only.
  getLLMConfig() {
    return request<LLMProfilesView>("/runtime/config/llm");
  },
  saveLLMConfig(config: LLMProfileInput) {
    return request<LLMProfilesView & { saved: boolean }>("/runtime/config/llm", {
      method: "POST",
      body: JSON.stringify(config)
    });
  },
  testLLMConnection(config?: LLMProfileInput) {
    return request<LLMTestResult>("/runtime/config/llm/test", {
      method: "POST",
      body: JSON.stringify(config ?? {})
    });
  },
  // Stage 6.7 Memory Module v1 — the UI views/clears a resident's memory via the
  // backend (which resolves the memory provider). The UI never touches the store.
  memoryView(residentId: string, namespace = "default", memoryType = "interaction_log", limit = 20) {
    const params = new URLSearchParams({ resident_id: residentId, namespace, memory_type: memoryType, limit: String(limit) });
    return request<MemoryViewResult>(`/runtime/memory/view?${params.toString()}`);
  },
  memoryClear(residentId: string, namespace = "default", memoryType = "interaction_log") {
    return request<MemoryClearResult>("/runtime/memory/clear", {
      method: "POST",
      body: JSON.stringify({ resident_id: residentId, namespace, memory_type: memoryType })
    });
  }
};

// Stage 6.7 — memory view/clear result shapes.
export type MemoryItem = { memory_type: string; content: Record<string, unknown>; created_at: string };
export type MemoryViewResult = {
  resident_id: string;
  namespace: string;
  memory_type: string;
  storage_backend: string;
  entries: MemoryItem[];
  count: number;
  limit: number;
  items?: MemoryItem[];
};
export type MemoryClearResult = {
  resident_id: string;
  namespace: string;
  memory_type: string;
  storage_backend: string;
  cleared: boolean;
  deleted_count: number;
  count: number;
};

// Stage 6.6 — LLM runtime profiles (masked view: never carries the raw api_key).
export type LLMProfileView = {
  profile_id: string;
  provider: string;
  base_url: string;
  model: string;
  enabled: boolean;
  fallback_to_mock: boolean;
  has_api_key: boolean;
  is_valid: boolean;
};
export type LLMProfilesView = {
  default_profile_id: string;
  profile_ids: string[];
  profiles: Record<string, LLMProfileView>;
};
export type LLMProfileInput = {
  profile_id: string;
  provider?: string;
  base_url?: string;
  api_key?: string; // empty/omitted = leave stored key unchanged
  model?: string;
  enabled?: boolean;
  fallback_to_mock?: boolean;
};
export type LLMTestResult = { ok: boolean; model?: string; sample?: string; error?: string; provider?: string };

export type DRFinding = { status: string; code: string; message: string; path: string };

// Result of POST /dr/compile (Stage 6.3.3 compile-only). `compiled_dr` is the
// downloadable .digital_resident content, present only when valid.
export type DRCompileResult = {
  valid: boolean;
  dr_version: string;
  errors: DRFinding[];
  warnings: DRFinding[];
  module_audit: Record<string, unknown>;
  layer_audit: Record<string, unknown>;
  compile_audit: Record<string, unknown>;
  orchestration_compatibility: boolean;
  pseudo_dag: Array<Record<string, unknown>>;
  compiled_dr: Record<string, unknown> | null;
  dr_payload: Record<string, unknown>;
  filename: string;
  metadata: Record<string, unknown>;
};

export type DRValidationResult = {
  valid: boolean;
  dr_version: string | null;
  errors: DRFinding[];
  warnings: DRFinding[];
  module_audit: Record<string, unknown>;
  layer_audit: Record<string, unknown>;
  compile_audit: Record<string, unknown>;
  orchestration_compatibility: boolean;
  pseudo_dag: Array<Record<string, unknown>>;
};

export type DRLoadResult = ResidentStepResponse & {
  loaded: boolean;
  dr_version?: string | null;
  validation_result: DRValidationResult;
  runtime_state?: Record<string, unknown>;
};
