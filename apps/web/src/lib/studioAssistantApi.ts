export type StudioAssistantMode = "explain" | "recommend" | "audit" | "check_conflicts";

export type StudioAssistantContext = {
  resident_identity?: unknown;
  current_layer?: unknown;
  current_module?: unknown;
  current_node?: unknown;
  current_field?: unknown;
  field_references?: unknown[];
  neighbor_modules?: unknown[];
  [key: string]: unknown;
};

export type StudioAssistantRequest = {
  canvas_id?: string;
  layer_id?: string;
  module_id?: string;
  node_id?: string;
  field_key?: string;
  selected_text?: string;
  mode: StudioAssistantMode;
  context: StudioAssistantContext;
};

export type StudioAssistantPatch = {
  target_field: string;
  proposed_value: unknown;
};

export type StudioAssistantResponse = {
  ok: boolean;
  provider: string;
  model: string;
  mode: StudioAssistantMode;
  summary: string;
  suggestions: unknown[];
  warnings: unknown[];
  patch: StudioAssistantPatch | null;
  requires_user_confirm: true;
  diagnostics: Record<string, unknown>;
};

function resolveStudioAssistantApiBase() {
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

const STUDIO_ASSISTANT_API_BASE = resolveStudioAssistantApiBase();

const modePaths: Record<StudioAssistantMode, string> = {
  explain: "/studio-assistant/explain",
  recommend: "/studio-assistant/recommend",
  audit: "/studio-assistant/audit",
  check_conflicts: "/studio-assistant/check-conflicts",
};

async function formatStudioAssistantError(response: Response) {
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

export async function callStudioAssistant(
  mode: StudioAssistantMode,
  request: StudioAssistantRequest
): Promise<StudioAssistantResponse> {
  let response: Response;
  try {
    response = await fetch(`${STUDIO_ASSISTANT_API_BASE}${modePaths[mode]}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ...request, mode }),
    });
  } catch (error) {
    throw new Error(`Network error: ${(error as Error).message}`);
  }

  if (!response.ok) {
    throw new Error(await formatStudioAssistantError(response));
  }

  try {
    return (await response.json()) as StudioAssistantResponse;
  } catch {
    throw new Error(`Invalid JSON response from ${modePaths[mode]}`);
  }
}
