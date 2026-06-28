/**
 * Stage 6.5：Engine Registry 获取与 mock-only Provider Registry 展示
 * 
 * 前端从后端 /schema/engine-registry-v0.4 获取 Engine 列表，
 * 用于解析 Slot.engine_binding 并仅展示 mock 引擎信息。
 * 禁止调用真实 provider、读取 API key、执行真实能力。
 */

import type { EngineRegistryEntryV04, EngineRegistryResponseV04 } from "@/lib/schema-types";

/**
 * 当前阶段允许的 Engine 类型
 */
export const ALLOWED_ENGINE_TYPES = new Set(["llm", "memory", "tool", "tts", "avatar", "speech", "screen"]);

/**
 * 当前阶段允许的 Provider 名称（仅 mock）
 */
export const ALLOWED_PROVIDERS = new Set([
  "provider_llm_mock",
  "provider_memory_mock",
  "provider_tool_mock",
  "provider_tts_mock",
  "provider_avatar_mock",
  "provider_speech_mock",
  "provider_screen_mock",
]);

function readEngineProviders(engine: EngineRegistryEntryV04): string[] {
  const providers = (engine as { providers?: unknown }).providers;
  return Array.isArray(providers) ? providers.filter((provider): provider is string => typeof provider === "string") : [];
}

/**
 * 校验 Engine 类型是否有效
 */
export function isValidEngineType(engineType: string | null | undefined): boolean {
  return engineType !== null && engineType !== undefined && ALLOWED_ENGINE_TYPES.has(engineType);
}

/**
 * 校验 Provider 是否仅为 mock
 */
export function isValidProvider(provider: string | null | undefined): boolean {
  return provider !== null && provider !== undefined && ALLOWED_PROVIDERS.has(provider);
}

/**
 * 校验单个 Engine 条目
 * 
 * 禁止：真实 provider（openai, anthropic, 等）
 */
export function validateEngineEntry(engine: EngineRegistryEntryV04): { valid: boolean; errors: string[] } {
  const errors: string[] = [];

  // engine_id 必须非空
  if (!engine.engine_id || engine.engine_id.trim() === "") {
    errors.push("engine_id 为空");
  }

  // engine_type 必须有效
  if (!isValidEngineType(engine.engine_type)) {
    errors.push(
      `engine_type 无效："${engine.engine_type}"，当前仅允许：${Array.from(ALLOWED_ENGINE_TYPES).join(", ")}`
    );
  }

  const providers = readEngineProviders(engine);
  if (providers.length === 0) {
    errors.push(`engine "${engine.engine_id}" 未绑定 mock provider registry id`);
  }
  for (const provider of providers) {
    if (!isValidProvider(provider)) {
      errors.push(`provider 无效："${provider}"，当前仅允许 mock provider registry id`);
    }
  }

  // 禁止检查：真实 provider 名称
  const suspiciousProviders = [
    "openai",
    "anthropic",
    "gpt",
    "claude",
    "gemini",
    "llama",
    "groq",
    "together",
  ];
  if (engine.engine_id) {
    const lowerCaseId = engine.engine_id.toLowerCase();
    for (const suspicious of suspiciousProviders) {
      if (lowerCaseId.includes(suspicious)) {
        errors.push(`🔒 禁止：engine_id 包含真实 provider 名称："${suspicious}"`);
      }
    }
  }

  return {
    valid: errors.length === 0,
    errors,
  };
}

/**
 * 校验整个 Engine Registry
 */
export function validateEngineRegistry(registry: EngineRegistryResponseV04): { valid: boolean; errors: string[] } {
  const errors: string[] = [];
  const seenIds = new Set<string>();

  // 必须有 engines 数组
  if (!registry.engines || !Array.isArray(registry.engines)) {
    errors.push("Engine Registry 不包含 engines 数组");
    return { valid: false, errors };
  }

  // 逐个校验每个 Engine
  for (let i = 0; i < registry.engines.length; i += 1) {
    const engine = registry.engines[i];

    // 检查 engine_id 唯一性
    if (engine.engine_id && seenIds.has(engine.engine_id)) {
      errors.push(`第 ${i} 个 Engine：engine_id 重复："${engine.engine_id}"`);
    }
    if (engine.engine_id) {
      seenIds.add(engine.engine_id);
    }

    // 检查单个 Engine 有效性
    const engineValidation = validateEngineEntry(engine);
    if (!engineValidation.valid) {
      errors.push(`第 ${i} 个 Engine 验证失败：${engineValidation.errors.join("; ")}`);
    }
  }

  return {
    valid: errors.length === 0,
    errors,
  };
}

/**
 * 根据 engine_id 查找 Engine
 */
export function findEngineById(
  registry: EngineRegistryResponseV04,
  engineId: string
): EngineRegistryEntryV04 | undefined {
  return registry.engines?.find((engine) => engine.engine_id === engineId);
}

/**
 * 根据 engine_binding 查找 Engine
 * engine_binding 通常存储 engine_id
 */
export function findEngineByBinding(
  registry: EngineRegistryResponseV04 | undefined,
  engineBinding: string | null | undefined
): EngineRegistryEntryV04 | undefined {
  if (!engineBinding || !registry) {
    return undefined;
  }
  return findEngineById(registry, engineBinding);
}

/**
 * 获取 Engine 的显示信息（mock-only，仅用于 UI 展示）
 */
export function getEngineMockDisplay(
  engine: EngineRegistryEntryV04
): {
  engine_id: string;
  engine_type: string;
  status: string;
  provider: string;
  display_name: string;
} {
  return {
    engine_id: engine.engine_id,
    engine_type: engine.engine_type || "unknown",
    status: engine.status || "MOCK",
    provider: readEngineProviders(engine)[0] || "mock",
    display_name: `${engine.engine_id} (mock)`,
  };
}

/**
 * 获取 Engine Registry 的简要统计
 */
export function getEngineRegistryStats(registry: EngineRegistryResponseV04): {
  totalEngines: number;
  enginesByType: Record<string, number>;
  validEngines: number;
  invalidEngines: number;
} {
  const engines = registry.engines || [];
  const stats = {
    totalEngines: engines.length,
    enginesByType: {} as Record<string, number>,
    validEngines: 0,
    invalidEngines: 0,
  };

  for (const engine of engines) {
    const validation = validateEngineEntry(engine);
    if (validation.valid) {
      stats.validEngines += 1;
    } else {
      stats.invalidEngines += 1;
    }

    if (engine.engine_type) {
      stats.enginesByType[engine.engine_type] = (stats.enginesByType[engine.engine_type] || 0) + 1;
    }
  }

  return stats;
}

/**
 * 禁止列表检查：确认没有真实 provider 被引入
 * 这是一个安全检查函数，应在开发和部署前运行
 */
export function checkForRealProviders(registry: EngineRegistryResponseV04): {
  hasRealProviders: boolean;
  issues: string[];
} {
  const issues: string[] = [];
  const dangerousPatterns = [
    "openai",
    "gpt",
    "anthropic",
    "claude",
    "gemini",
    "llama",
    "groq",
    "together",
    "huggingface",
    "replicate",
  ];

  for (const engine of registry.engines || []) {
    const lowerCaseId = engine.engine_id?.toLowerCase() || "";
    for (const pattern of dangerousPatterns) {
      if (lowerCaseId.includes(pattern)) {
        issues.push(`Engine ID 包含真实 provider 模式："${engine.engine_id}" 包含 "${pattern}"`);
      }
    }
    for (const provider of readEngineProviders(engine)) {
      if (!ALLOWED_PROVIDERS.has(provider)) {
        issues.push(`Engine provider 未注册为 mock provider id："${provider}"`);
      }
    }
  }

  return {
    hasRealProviders: issues.length > 0,
    issues,
  };
}
