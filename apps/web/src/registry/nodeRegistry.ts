export type NodeDefinition = {
  type: string;
  label: string;
  input_schema: Record<string, unknown>;
  output_schema: Record<string, unknown>;
  tags: string[];
  execute: (context: NodeExecutionContext, node: unknown) => unknown;
};

export type NodeExecutionContext = {
  input: unknown;
  memory: Record<string, unknown>;
  intermediate: Record<string, unknown>;
};

function passThrough(context: NodeExecutionContext) {
  return context.input;
}

function outputPersonaResult(context: NodeExecutionContext) {
  return {
    persona_result: context.input,
    memory: context.memory,
    intermediate: context.intermediate
  };
}

export const nodeRegistry = new Map<string, NodeDefinition>([
  ["text", { type: "text", label: "Text", input_schema: {}, output_schema: {}, tags: ["core"], execute: passThrough }],
  ["memory", { type: "memory", label: "Memory", input_schema: {}, output_schema: {}, tags: ["core"], execute: passThrough }],
  ["reasoning", { type: "reasoning", label: "Reasoning", input_schema: {}, output_schema: {}, tags: ["core"], execute: passThrough }],
  ["personality", { type: "personality", label: "Personality", input_schema: {}, output_schema: {}, tags: ["persona"], execute: passThrough }],
  ["transform", { type: "transform", label: "Transform", input_schema: {}, output_schema: {}, tags: ["processing"], execute: passThrough }],
  ["output", { type: "output", label: "Output", input_schema: {}, output_schema: {}, tags: ["sink"], execute: outputPersonaResult }]
]);

export function getNodeDefinition(type: string) {
  return nodeRegistry.get(type);
}
