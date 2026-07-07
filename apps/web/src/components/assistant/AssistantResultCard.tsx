import type { StudioAssistantResponse } from "@/lib/studioAssistantApi";

function displayValue(value: unknown) {
  if (value === null || value === undefined) {
    return "";
  }
  if (typeof value === "string") {
    return value;
  }
  if (typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }
  return JSON.stringify(value, null, 2);
}

function ResultList({ values }: { values: unknown[] }) {
  if (!values.length) {
    return null;
  }
  return (
    <ul>
      {values.map((value, index) => (
        <li key={index}>{displayValue(value)}</li>
      ))}
    </ul>
  );
}

export function AssistantResultCard({
  result,
  canApply,
  copied,
  t,
  onApply,
  onCopy,
}: {
  result: StudioAssistantResponse;
  canApply: boolean;
  copied: boolean;
  t: (key: string, fallback?: string) => string;
  onApply: () => void;
  onCopy: () => void;
}) {
  const disabled = result.diagnostics?.status === "disabled";
  const patchText = result.patch ? displayValue(result.patch.proposed_value) : "";

  return (
    <article className={`assistant-result-card ${result.ok ? "is-ok" : "is-error"} ${disabled ? "is-disabled" : ""}`}>
      <section>
        <h3>{t("assistant.result.summary", "Summary")}</h3>
        <p>{result.summary || (disabled ? t("assistant.status.disabled", "Disabled") : t("assistant.status.error", "Error"))}</p>
      </section>

      {result.suggestions.length ? (
        <section>
          <h3>{t("assistant.result.suggestions", "Suggestions")}</h3>
          <ResultList values={result.suggestions} />
        </section>
      ) : null}

      {result.warnings.length ? (
        <section>
          <h3>{t("assistant.result.warnings", "Warnings")}</h3>
          <ResultList values={result.warnings} />
        </section>
      ) : null}

      {result.patch ? (
        <section>
          <h3>{t("assistant.result.patch", "Patch")}</h3>
          <div className="assistant-patch-preview">
            <strong>{result.patch.target_field}</strong>
            <pre>{patchText}</pre>
          </div>
          <div className="assistant-result-actions">
            <button type="button" disabled={!canApply} onClick={onApply}>
              {t("assistant.action.applySuggestion", "Apply suggestion")}
            </button>
            <button type="button" onClick={onCopy}>
              {copied ? t("assistant.status.copied", "Copied") : t("assistant.action.copySuggestion", "Copy suggestion")}
            </button>
          </div>
        </section>
      ) : null}
    </article>
  );
}

