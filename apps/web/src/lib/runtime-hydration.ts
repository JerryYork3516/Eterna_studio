/**
 * Runtime result hydration layer — Stage 6 Runtime Kernel.
 *
 * Pure, UI-agnostic data mapping. It takes the raw POST /runtime/resident/step
 * response (the backend Execution Engine is the sole runtime entry — the UI
 * never executes a workflow or calls a provider directly) and maps it into the
 * shapes the existing panels already render:
 *
 *   execution_trace  -> log lines        (运行日志面板 / Debug Panel)
 *   memory_snapshot  -> artifacts        (产物 / 记忆面板)
 *   output_text      -> node output      (节点输出)
 *   status / run_id  -> debug summary    (Debug Panel)
 *
 * This does NOT restructure any UI; it only normalizes data. It must never call
 * the v0.3 workflow adapter and never fabricates LLM / memory data.
 */

import type {
  Artifact,
  ResidentStepResponse,
  RuntimeMemorySnapshot,
  RuntimeTraceStep
} from "@/lib/schema-types";

export type RuntimeLogLine = {
  level: "info" | "warn" | "error";
  message: string;
};

export type RuntimeDebugSummary = {
  runId: string;
  status: string;
  turnCount: number;
  residentId: string;
  stepCount: number;
  memoryCount: number;
};

export type HydratedRuntimeResult = {
  /** Ordered (by index) log lines for the run log / debug panel. */
  logLines: RuntimeLogLine[];
  /** Memory snapshot entries mapped into Artifact shape for the 产物/记忆面板. */
  memoryArtifacts: Artifact[];
  /** Composed node output text. */
  outputText: string;
  /** Compact debug summary (status / run_id / counts). */
  debug: RuntimeDebugSummary;
  /** Raw trace, sorted by index, for any structured viewer. */
  trace: RuntimeTraceStep[];
  /** Raw snapshot for the memory panel. */
  memorySnapshot: RuntimeMemorySnapshot;
};

function readTrace(response: ResidentStepResponse): RuntimeTraceStep[] {
  const raw = response.trace ?? response.execution_trace ?? [];
  // Defensive copy + stable order by index so replay is always 0..n-1.
  return [...raw].sort((a, b) => (a?.index ?? 0) - (b?.index ?? 0));
}

function summarizeStep(step: RuntimeTraceStep): string {
  const phase = step.phase ?? step.step ?? "step";
  // Surface the most useful flat convenience key per phase without leaking
  // huge payloads into the log line.
  const detailKeys = ["text", "result", "count", "output_text", "tool", "provider"];
  const parts: string[] = [];
  for (const key of detailKeys) {
    const value = step[key];
    if (value === undefined || value === null || value === "") continue;
    const rendered = typeof value === "string" ? value : JSON.stringify(value);
    parts.push(`${key}=${rendered}`);
  }
  const detail = parts.length ? ` · ${parts.join(" ")}` : "";
  return `[trace #${step.index}] ${phase}${detail}`;
}

function readMemorySnapshot(response: ResidentStepResponse): RuntimeMemorySnapshot {
  return response.memory_snapshot ?? { entries: [], count: 0 };
}

function mapMemoryToArtifacts(
  snapshot: RuntimeMemorySnapshot,
  residentId: string
): Artifact[] {
  const entries = snapshot.entries ?? [];
  return entries.map((entry, index) => {
    const turn = (entry.turn as number | undefined) ?? index + 1;
    return {
      artifact_id: `${residentId}:mem:${turn}`,
      node_id: residentId,
      kind: "memory",
      name: `memory turn ${turn}`,
      preview: entry as Record<string, unknown>
    };
  });
}

/**
 * Map a raw runtime response into the structures the existing panels render.
 * Pure: no side effects, no network.
 */
export function hydrateRuntimeResult(response: ResidentStepResponse): HydratedRuntimeResult {
  const residentId = response.resident_id ?? "resident_v1";
  const runId = response.run_id ?? "(no run_id)";
  const status = response.status ?? "unknown";
  const turnCount = response.turn_count ?? 0;
  const trace = readTrace(response);
  const memorySnapshot = readMemorySnapshot(response);
  const memoryCount = memorySnapshot.count ?? memorySnapshot.entries?.length ?? 0;
  const outputText = response.output_text ?? "";

  const logLines: RuntimeLogLine[] = [];
  // Header (status / run_id / turn) for the debug panel.
  logLines.push({
    level: status === "error" ? "error" : "info",
    message: `▶ runtime run ${runId} · status=${status} · turn=${turnCount} · resident=${residentId}`
  });
  // Trace steps, in index order (0..n-1).
  for (const step of trace) {
    logLines.push({ level: "info", message: summarizeStep(step) });
  }
  // Output line.
  if (outputText) {
    logLines.push({ level: "info", message: `↳ output: ${outputText}` });
  }
  // Memory delta line.
  logLines.push({ level: "info", message: `🧠 memory snapshot: ${memoryCount} entr${memoryCount === 1 ? "y" : "ies"}` });

  return {
    logLines,
    memoryArtifacts: mapMemoryToArtifacts(memorySnapshot, residentId),
    outputText,
    debug: {
      runId,
      status,
      turnCount,
      residentId,
      stepCount: trace.length,
      memoryCount
    },
    trace,
    memorySnapshot
  };
}
