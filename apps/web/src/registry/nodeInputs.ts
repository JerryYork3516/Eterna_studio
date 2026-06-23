// Front-end Node Input schemas. These describe how each node type's inputs are
// rendered inside the node fold panel. They are UI-only: values are stored on the
// node's free-form `data` object (no backend schema / NodeType change).

export type NodeInputField = {
  key: string;
  type: "text" | "textarea" | "number" | "select" | "slider" | "boolean";
  labelKey: string;
  labelFallback: string;
  placeholder?: string;
  options?: { value: string; labelFallback: string }[];
  min?: number;
  max?: number;
  step?: number;
};

const FALLBACK_FIELD: NodeInputField = {
  key: "source_text",
  type: "textarea",
  labelKey: "input.sourceText",
  labelFallback: "Source text"
};

export const NODE_INPUT_SCHEMAS: Record<string, NodeInputField[]> = {
  text_input: [{ key: "source_text", type: "textarea", labelKey: "input.sourceText", labelFallback: "Source text" }],
  identity: [
    { key: "name", type: "text", labelKey: "input.name", labelFallback: "Name" },
    { key: "role", type: "text", labelKey: "input.role", labelFallback: "Role" }
  ],
  personality: [
    { key: "traits", type: "text", labelKey: "input.traits", labelFallback: "Traits" },
    { key: "warmth", type: "slider", labelKey: "input.warmth", labelFallback: "Warmth", min: 0, max: 1, step: 0.1 }
  ],
  dialogue: [
    {
      key: "style",
      type: "select",
      labelKey: "input.style",
      labelFallback: "Style",
      options: [
        { value: "calm", labelFallback: "Calm" },
        { value: "playful", labelFallback: "Playful" },
        { value: "formal", labelFallback: "Formal" }
      ]
    }
  ],
  voice_profile: [
    {
      key: "voice",
      type: "select",
      labelKey: "input.voice",
      labelFallback: "Voice",
      options: [
        { value: "neutral", labelFallback: "Neutral" },
        { value: "female", labelFallback: "Female" },
        { value: "male", labelFallback: "Male" }
      ]
    }
  ],
  model_adapter: [{ key: "model", type: "text", labelKey: "input.model", labelFallback: "Model" }],
  llm_adapter: [{ key: "model", type: "text", labelKey: "input.model", labelFallback: "Model" }],
  memory: [{ key: "capacity", type: "number", labelKey: "input.capacity", labelFallback: "Capacity", min: 0, step: 1 }],
  knowledge: [{ key: "source", type: "text", labelKey: "input.source", labelFallback: "Source" }],
  tools: [{ key: "enabled", type: "boolean", labelKey: "input.enabled", labelFallback: "Enabled" }]
};

export function getNodeInputSchema(type: string): NodeInputField[] {
  return NODE_INPUT_SCHEMAS[type] ?? [FALLBACK_FIELD];
}
