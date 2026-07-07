import type { StudioAssistantMode } from "@/lib/studioAssistantApi";

const actionKeys: Array<{ mode: StudioAssistantMode; labelKey: string }> = [
  { mode: "explain", labelKey: "assistant.action.explain" },
  { mode: "recommend", labelKey: "assistant.action.recommend" },
  { mode: "audit", labelKey: "assistant.action.audit" },
  { mode: "check_conflicts", labelKey: "assistant.action.checkConflicts" },
];

export function AssistantActionList({
  loadingMode,
  disabled,
  t,
  onAction,
}: {
  loadingMode: StudioAssistantMode | null;
  disabled: boolean;
  t: (key: string, fallback?: string) => string;
  onAction: (mode: StudioAssistantMode) => void;
}) {
  return (
    <div className="assistant-actions">
      {actionKeys.map((action) => (
        <button
          key={action.mode}
          type="button"
          disabled={disabled || Boolean(loadingMode)}
          onClick={() => onAction(action.mode)}
        >
          {loadingMode === action.mode ? t("assistant.status.loading", "Loading") : t(action.labelKey, action.mode)}
        </button>
      ))}
    </div>
  );
}

