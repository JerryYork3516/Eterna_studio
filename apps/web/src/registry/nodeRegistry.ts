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
  current?: unknown;
  memory: Record<string, unknown>;
  intermediate: Record<string, unknown>;
};

function inputValue(context: NodeExecutionContext) {
  context.current = context.input;
  return context.current;
}

function passThrough(context: NodeExecutionContext) {
  return context.current;
}

function outputPersonaResult(context: NodeExecutionContext) {
  return {
    persona_result: context.current
  };
}

export const nodeRegistry = new Map<string, NodeDefinition>([
  ["input", { type: "input", label: "Input", input_schema: {}, output_schema: {}, tags: ["source"], execute: inputValue }],
  ["module", { type: "module", label: "Module", input_schema: {}, output_schema: {}, tags: ["module"], execute: passThrough }],
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
