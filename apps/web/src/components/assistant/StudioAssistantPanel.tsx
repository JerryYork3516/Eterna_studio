import { useMemo, useState } from "react";
import { AssistantActionList } from "@/components/assistant/AssistantActionList";
import { AssistantResultCard } from "@/components/assistant/AssistantResultCard";
import {
  callStudioAssistant,
  type StudioAssistantMode,
  type StudioAssistantPatch,
  type StudioAssistantRequest,
  type StudioAssistantResponse,
} from "@/lib/studioAssistantApi";

function compactText(value: unknown) {
  if (value === null || value === undefined || value === "") {
    return "";
  }
  if (typeof value === "string") {
    return value;
  }
  if (typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }
  return JSON.stringify(value);
}

function asText(value: unknown) {
  return typeof value === "string" && value.trim() ? value.trim() : "";
}

export function StudioAssistantPanel({
  request,
  canApplyPatch,
  t,
  onApplyPatch,
}: {
  request: StudioAssistantRequest;
  canApplyPatch: boolean;
  t: (key: string, fallback?: string) => string;
  onApplyPatch: (patch: StudioAssistantPatch) => void;
}) {
  const [loadingMode, setLoadingMode] = useState<StudioAssistantMode | null>(null);
  const [result, setResult] = useState<StudioAssistantResponse | null>(null);
  const [error, setError] = useState("");
  const [copied, setCopied] = useState(false);

  const contextRows = useMemo<Array<[string, string | undefined]>>(
    () => [
      ["assistant.context.layer", request.layer_id],
      ["assistant.context.module", request.module_id],
      ["assistant.context.node", request.node_id],
      ["assistant.context.field", request.field_key],
    ],
    [request.field_key, request.layer_id, request.module_id, request.node_id]
  );

  const hasContext = Boolean(request.layer_id || request.module_id || request.node_id || request.field_key);
  const provider = result?.provider || asText(result?.diagnostics?.provider) || t("assistant.status.unknown", "Unknown");
  const model = result?.model || asText(result?.diagnostics?.model) || t("assistant.status.unknown", "Unknown");
  const assistantStatus = !result
    ? t("assistant.status.unknown", "Unknown")
    : result.diagnostics?.status === "disabled"
      ? t("assistant.status.disabled", "Assistant disabled")
      : result.ok
        ? t("assistant.status.enabled", "Assistant enabled")
        : t("assistant.status.error", "Assistant error");

  const runAction = async (mode: StudioAssistantMode) => {
    setLoadingMode(mode);
    setError("");
    setCopied(false);
    try {
      const next = await callStudioAssistant(mode, request);
      setResult(next);
    } catch (caught) {
      setResult(null);
      setError((caught as Error).message);
    } finally {
      setLoadingMode(null);
    }
  };

  const copySuggestion = async () => {
    const value = result?.patch?.proposed_value ?? result?.summary ?? "";
    const text = compactText(value);
    if (!text) {
      return;
    }
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
    } catch {
      setCopied(false);
    }
  };

  const applyPatch = () => {
    if (!result?.patch || !canApplyPatch) {
      return;
    }
    if (!window.confirm(t("assistant.confirm.applyPatch", "Apply this suggestion to the selected field?"))) {
      return;
    }
    onApplyPatch(result.patch);
  };

  return (
    <div className="studio-assistant-panel">
          <section className="assistant-context">
            <div className="assistant-runtime">
              <span>{t("assistant.runtime.provider", "Provider")}</span>
              <strong>{provider}</strong>
              <span>{t("assistant.runtime.model", "Model")}</span>
              <strong>{model}</strong>
              <span>{t("assistant.runtime.status", "Status")}</span>
              <strong>{assistantStatus}</strong>
            </div>
            <h3>{t("assistant.context.title", "Current context")}</h3>
            {hasContext ? (
              <dl>
                {contextRows.map(([key, value]) =>
                  value ? (
                    <div key={key}>
                      <dt>{t(key, key)}</dt>
                      <dd>{value}</dd>
                    </div>
                  ) : null
                )}
              </dl>
            ) : (
              <p>{t("assistant.context.noSelection", "Select a module, node, or field first.")}</p>
            )}
          </section>

          <AssistantActionList
            loadingMode={loadingMode}
            disabled={!hasContext}
            t={t}
            onAction={(mode) => {
              void runAction(mode);
            }}
          />

          {error ? (
            <div className="assistant-error">
              <strong>{t("assistant.status.error", "Error")}</strong>
              <p>{error}</p>
            </div>
          ) : null}

          {result ? (
            <AssistantResultCard
              result={result}
              canApply={canApplyPatch && Boolean(result.patch)}
              copied={copied}
              t={t}
              onApply={applyPatch}
              onCopy={() => {
                void copySuggestion();
              }}
            />
          ) : (
            <p className="assistant-empty">{t("assistant.result.empty", "Choose an assistant action.")}</p>
          )}
    </div>
  );
}
