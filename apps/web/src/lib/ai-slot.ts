import type { WorkflowNode } from "@/lib/schema-types";

export type AiSlot = "llm" | "tts" | "memory" | "ar" | "runtime" | "none";

export const AI_SLOT_LABELS: Record<AiSlot, string> = {
  llm: "LLM",
  tts: "TTS",
  memory: "MEMORY",
  ar: "AR",
  runtime: "RUNTIME",
  none: "UNPLANNED"
};

function normalizeAiSlot(value: string): AiSlot | null {
  const slot = value.trim().toLowerCase();
  if (slot === "llm" || slot === "tts" || slot === "memory" || slot === "runtime") {
    return slot;
  }
  if (slot === "ar" || slot === "avatar" || slot === "avatar/ar" || slot === "avatar_ar") {
    return "ar";
  }
  if (slot === "none" || slot === "unplanned" || slot === "未接入") {
    return "none";
  }
  return null;
}

export function inferAiSlot(node: Pick<WorkflowNode, "type" | "title_key" | "title_fallback" | "data">): AiSlot {
  const explicit =
    typeof node.data?.ai_slot === "string"
      ? normalizeAiSlot(node.data.ai_slot)
      : typeof node.data?.slot_type === "string"
        ? normalizeAiSlot(node.data.slot_type)
        : null;
  if (explicit) {
    return explicit;
  }
  return "none";
}

export function aiSlotLabel(slot: AiSlot) {
  return AI_SLOT_LABELS[slot];
}

export function aiSlotClass(slot: AiSlot) {
  return `ai-slot-${slot}`;
}
