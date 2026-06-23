import { safeClone } from "@/lib/safe-serialize";

export type NodeStatus = "READY" | "MOCK" | "DISABLED";

export type NodeDefinition = {
  type: string;
  label: string;
  status: NodeStatus;
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

type PersonaDto = {
  name: string;
  identity: string;
  personality_traits: string[];
  speaking_style: string;
  boundaries: string[];
  source_input: string;
};

type ResidentInstanceDto = {
  identity: { name: string; role: string };
  personality: { traits: string[]; speaking_style: string; boundaries: string[] };
  dialogue: { tone: string; formality: string; sample: string };
  voice_profile: { voice_id: string; pitch: string; speed: number; timbre: string };
  avatar: { preset: string; color: string; density: number; motion: string };
};

function inputValue(context: NodeExecutionContext) {
  context.current = context.input;
  return context.current;
}

function passThrough(context: NodeExecutionContext) {
  return context.current;
}

function isStringifiedJson(value: string) {
  const trimmed = value.trim();
  if (!trimmed || !/^[{[]/.test(trimmed)) {
    return false;
  }
  try {
    JSON.parse(trimmed);
    return true;
  } catch {
    return /\{\s*["“]?(text_input|workflow|node|nodes|edges|runtime|resident_instance)["”]?\s*[:}]/i.test(trimmed);
  }
}

function cleanText(value: unknown, fallback = "") {
  if (typeof value !== "string") {
    return fallback;
  }
  const trimmed = value.trim();
  return isStringifiedJson(trimmed) ? fallback : trimmed;
}

function normalizePersonaInput(context: NodeExecutionContext) {
  const sourceText = cleanText(context.current, "");
  const normalized = {
    normalized_input: {
      source_text: sourceText,
      intent: "persona_generation"
    }
  };
  context.current = normalized;
  return normalized;
}

function createPersona(sourceInput: string): PersonaDto {
  return {
    name: "Unnamed Resident",
    identity: "digital_resident",
    personality_traits: ["温和", "理性"],
    speaking_style: "calm and supportive",
    boundaries: ["不伪装真人", "不提供危险建议"],
    source_input: sourceInput
  };
}

function getSourceInput(value: unknown) {
  if (isRecord(value)) {
    const normalizedInput = value.normalized_input;
    if (isRecord(normalizedInput) && typeof normalizedInput.source_text === "string") {
      return cleanText(normalizedInput.source_text, "");
    }
    if (typeof value.source_input === "string") {
      return cleanText(value.source_input, "");
    }
    const textInput = value.text_input;
    if (isRecord(textInput) && typeof textInput.text === "string") {
      return cleanText(textInput.text, "");
    }
  }
  return cleanText(value, "");
}

function isPersona(value: unknown): value is PersonaDto {
  return (
    isRecord(value) &&
    typeof value.name === "string" &&
    typeof value.identity === "string" &&
    Array.isArray(value.personality_traits) &&
    typeof value.speaking_style === "string" &&
    Array.isArray(value.boundaries) &&
    typeof value.source_input === "string"
  );
}

function generatePersona(context: NodeExecutionContext) {
  const persona = createPersona(getSourceInput(context.current));
  context.current = persona;
  return persona;
}

function outputPersonaResult(context: NodeExecutionContext) {
  if (isResidentOutput(context.current)) {
    return safeClone(context.current);
  }
  const persona = isPersona(context.current) ? context.current : createPersona(getSourceInput(context.current));
  return {
    persona_result: safeClone(persona),
    memory: safeClone(context.memory),
    intermediate: safeClone(context.intermediate)
  };
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value && typeof value === "object" && !Array.isArray(value));
}

function pickString(value: unknown, fallback: string) {
  const text = cleanText(value, "");
  return text || fallback;
}

function pickNumber(value: unknown, fallback: number) {
  const numberValue = typeof value === "number" ? value : Number(value);
  return Number.isFinite(numberValue) ? numberValue : fallback;
}

function pickStringArray(value: unknown, fallback: string[]) {
  if (!Array.isArray(value)) {
    return fallback;
  }
  const cleaned = value.map((item) => cleanText(item, "")).filter(Boolean);
  return cleaned.length ? cleaned : fallback;
}

function findIntermediateRecord(context: NodeExecutionContext, key: string) {
  for (const value of Object.values(context.intermediate)) {
    if (!isRecord(value)) {
      continue;
    }
    const direct = value[key];
    if (isRecord(direct)) {
      return direct;
    }
    const nested = value[`${key}_style`] ?? value[`${key}_profile`];
    if (isRecord(nested)) {
      return nested;
    }
  }
  return null;
}

function isResidentOutput(value: unknown) {
  return isRecord(value) && value.mock === true && isRecord(value.resident_instance);
}

function buildResidentInstance(context: NodeExecutionContext): ResidentInstanceDto {
  const persona = isPersona(context.current) ? context.current : createPersona(getSourceInput(context.current));
  const identity = findIntermediateRecord(context, "identity");
  const dialogue = findIntermediateRecord(context, "dialogue") ?? findIntermediateRecord(context, "dialogue_style");
  const voiceProfile = findIntermediateRecord(context, "voice_profile");
  const avatar = findIntermediateRecord(context, "avatar") ?? findIntermediateRecord(context, "particle_avatar");

  return safeClone({
    identity: {
      name: pickString(identity?.name, persona.name),
      role: pickString(identity?.role, persona.identity)
    },
    personality: {
      traits: pickStringArray(persona.personality_traits, ["温和", "理性"]),
      speaking_style: pickString(persona.speaking_style, "calm and supportive"),
      boundaries: pickStringArray(persona.boundaries, ["不伪装真人", "不提供危险建议"])
    },
    dialogue: {
      tone: pickString(dialogue?.tone, "warm"),
      formality: pickString(dialogue?.formality, "casual"),
      sample: pickString(dialogue?.sample, "你好，很高兴认识你。")
    },
    voice_profile: {
      voice_id: pickString(voiceProfile?.voice_id, "vp_mock_001"),
      pitch: pickString(voiceProfile?.pitch, "medium"),
      speed: pickNumber(voiceProfile?.speed, 1),
      timbre: pickString(voiceProfile?.timbre, "soft")
    },
    avatar: {
      preset: pickString(avatar?.preset, "nebula"),
      color: pickString(avatar?.color, "#7aa2f7"),
      density: pickNumber(avatar?.density, 0.6),
      motion: pickString(avatar?.motion, "drift")
    }
  });
}

// ---- Stage 1 frontend mock executors -------------------------------------
// All of these are front-end-only mocks: they return fixed / simple rule-based
// output and never call a backend, LLM, runtime or API.

function textInputMock(context: NodeExecutionContext, node: unknown) {
  // Prefer the text typed directly in the node's fold panel (data.source_text),
  // fall back to the workflow run input. No Inspector dependency.
  const nodeData = (node as { data?: Record<string, unknown> } | undefined)?.data;
  const ownText = typeof nodeData?.source_text === "string" && nodeData.source_text ? nodeData.source_text : null;
  const text = ownText ?? getSourceInput(context.current);
  // Normalize so downstream nodes (transform / personality) consume this text.
  context.current = { normalized_input: { source_text: text, intent: "persona_generation" } };
  return { text_input: { text } };
}

function identityMock(context: NodeExecutionContext) {
  const result = {
    identity: {
      name: "数字居民",
      role: "digital_resident"
    }
  };
  context.current = result;
  return result;
}

function dialogueMock(context: NodeExecutionContext) {
  const result = {
    dialogue_style: {
      tone: "warm",
      formality: "casual",
      sample: "你好，很高兴认识你。"
    }
  };
  context.current = result;
  return result;
}

function voiceProfileMock(context: NodeExecutionContext) {
  const result = {
    voice_profile: { voice_id: "vp_mock_001", pitch: "medium", speed: 1, timbre: "soft" }
  };
  context.current = result;
  return result;
}

function particleAvatarMock(context: NodeExecutionContext) {
  const result = {
    particle_avatar: { preset: "nebula", color: "#7aa2f7", density: 0.6, motion: "drift" }
  };
  context.current = result;
  return result;
}

function modelAdapterMock(context: NodeExecutionContext) {
  const result = {
    model_adapter: { provider: "mock", model: "mock-model-1", temperature: 0.7, max_tokens: 1024 }
  };
  context.current = result;
  return result;
}

function memoryMock(context: NodeExecutionContext) {
  const result = {
    memory: { short_term: [], long_term: [], capacity: 128, strategy: "rolling" }
  };
  context.current = result;
  return result;
}

function knowledgeMock(context: NodeExecutionContext) {
  const result = {
    knowledge: { sources: ["mock_kb"], chunks: 0, embedding: "mock-embed" }
  };
  context.current = result;
  return result;
}

function toolsDisabled(context: NodeExecutionContext) {
  // DISABLED node: shown but not runnable. Returns a safe no-op marker so the
  // chain never crashes if it is wired in.
  const result = { tools: { enabled: false, disabled: true, note: "tools 节点为禁用态，Stage 1 不执行" } };
  context.current = result;
  return result;
}

function compileResidentMock(context: NodeExecutionContext) {
  // DTO only: no workflow / node / edge / runtime / context / component graph refs.
  return {
    mock: true,
    resident_instance: buildResidentInstance(context)
  };
}

function def(
  type: string,
  label: string,
  status: NodeStatus,
  tags: string[],
  execute: NodeDefinition["execute"]
): [string, NodeDefinition] {
  return [type, { type, label, status, input_schema: {}, output_schema: {}, tags, execute }];
}

// Generic fixed-output mock factory. The registry status carries MOCK/DISABLED;
// field DTOs stay clean and do not embed mock flags.
function fixedMock(key: string, payload: Record<string, unknown>) {
  return (context: NodeExecutionContext) => {
    const result = { [key]: { ...payload } };
    context.current = result;
    return result;
  };
}

export const nodeRegistry = new Map<string, NodeDefinition>([
  // Stage 1 core node library (front-end mock only).
  def("text_input", "Text Input", "READY", ["source"], textInputMock),
  def("identity", "Identity", "READY", ["persona"], identityMock),
  def("personality", "Personality", "READY", ["persona"], generatePersona),
  def("dialogue", "Dialogue Style", "MOCK", ["persona"], dialogueMock),
  def("voice_profile", "Voice Profile", "MOCK", ["media"], voiceProfileMock),
  def("particle_avatar", "Particle Avatar", "MOCK", ["media"], particleAvatarMock),
  def("model_adapter", "Model Adapter", "MOCK", ["model"], modelAdapterMock),
  def("memory", "Memory", "MOCK", ["memory"], memoryMock),
  def("knowledge", "Knowledge", "MOCK", ["memory"], knowledgeMock),
  def("tools", "Tools", "DISABLED", ["tools"], toolsDisabled),
  def("output", "Output", "READY", ["sink"], outputPersonaResult),
  def("compile_resident", "Compile Resident", "MOCK", ["sink"], compileResidentMock),
  // Stage 2 batch: integration / model / media / runtime / export (front-end mock).
  def("api_connector", "API Connector", "MOCK", ["integration"], fixedMock("api_connector", { endpoint: "https://mock.api", method: "POST" })),
  def("model_loader", "Model Loader", "MOCK", ["model"], fixedMock("model_loader", { model: "mock-model", loaded: true })),
  def("local_model", "Local Model", "MOCK", ["model"], fixedMock("local_model", { path: "/mock/model.gguf", quant: "q4" })),
  def("llm_adapter", "LLM Adapter", "MOCK", ["model"], fixedMock("llm_adapter", { provider: "mock", model: "mock-llm" })),
  def("tts_adapter", "TTS Adapter", "MOCK", ["media"], fixedMock("tts_adapter", { voice: "mock_voice", format: "wav" })),
  def("ar_particle", "AR Particle", "MOCK", ["media"], fixedMock("ar_particle", { preset: "aurora", count: 2000 })),
  def("particle_physics", "Particle Physics", "MOCK", ["media"], fixedMock("particle_physics", { gravity: 0.2, turbulence: 0.5 })),
  def("avatar_preview", "Avatar Preview", "MOCK", ["media"], fixedMock("avatar_preview", { ready: true, thumbnail: "mock://avatar.png" })),
  def("runtime_mock", "Runtime Mock", "DISABLED", ["runtime"], fixedMock("runtime_mock", { disabled: true, note: "运行时占位，Stage 1 不执行" })),
  def("export_package", "Export Package", "MOCK", ["sink"], fixedMock("export_package", { format: "zip", size: "mock" })),
  // Stage 0 / backward-compatible types kept so the existing stable chain and
  // backend-provided node types still resolve.
  def("input", "Input", "READY", ["source"], inputValue),
  def("module", "Module", "READY", ["module"], passThrough),
  def("text", "Text", "READY", ["core"], passThrough),
  def("reasoning", "Reasoning", "MOCK", ["core"], passThrough),
  def("transform", "Transform", "READY", ["processing"], normalizePersonaInput)
]);

export function getNodeDefinition(type: string) {
  return nodeRegistry.get(type);
}

export function getNodeStatus(type: string): NodeStatus | undefined {
  return nodeRegistry.get(type)?.status;
}
