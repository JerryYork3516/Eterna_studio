/**
 * Stage 5 P2：13层 canonical 常量定义与校验
 * 
 * 这是前端的冻结 CANONICAL_LAYERS 定义，必须与后端
 * apps/api/app/models/v0_4.py 的 CANONICAL_LAYERS 完全一致。
 * 
 * 禁止修改：
 * - layer_id 顺序与值
 * - layer_name 名称与顺序
 * - layer_order 数值
 */

export type CanonicalLayerTuple = [layerId: string, layerName: string, layerOrder: number];

/**
 * 前端 13-layer trunk 冻结定义
 * 必须与后端 CANONICAL_LAYERS 完全一致
 */
export const CANONICAL_LAYERS: CanonicalLayerTuple[] = [
  ["layer_1", "Identity Core", 1],
  ["layer_2", "Personality", 2],
  ["layer_3", "Safety Boundary", 3],
  ["layer_4", "Legal Permission", 4],
  ["layer_5", "Memory", 5],
  ["layer_6", "Knowledge", 6],
  ["layer_7", "World / Context", 7],
  ["layer_8", "Behavior", 8],
  ["layer_9", "Capability / Tools", 9],
  ["layer_10", "Multimodal", 10],
  ["layer_11", "Relationship", 11],
  ["layer_12", "Meta / Self-Reflection", 12],
  ["layer_13", "Export / Deployment", 13],
];

/**
 * 冻结的 layer_id 集合，用于快速校验
 */
export const CANONICAL_LAYER_IDS = new Set(CANONICAL_LAYERS.map(([id]) => id));

/**
 * 冻结的 layer_name 数组，按 layer_order 顺序
 */
export const CANONICAL_LAYER_NAMES = CANONICAL_LAYERS.map(([_, name]) => name);

/**
 * 冻结的 layer_order 数组，应该是 1-13
 */
export const CANONICAL_LAYER_ORDERS = CANONICAL_LAYERS.map(([_, __, order]) => order);

/**
 * layer_id → layer_name 映射
 */
export const CANONICAL_LAYER_ID_TO_NAME: Record<string, string> = Object.fromEntries(
  CANONICAL_LAYERS.map(([id, name]) => [id, name])
);

/**
 * layer_id → layer_order 映射
 */
export const CANONICAL_LAYER_ID_TO_ORDER: Record<string, number> = Object.fromEntries(
  CANONICAL_LAYERS.map(([id, _, order]) => [id, order])
);

/**
 * 校验层数据是否符合 canonical 定义
 * 
 * @param layers 后端返回的 layer 数组
 * @returns 校验结果 { valid: boolean; errors: string[] }
 */
export function validateCanonicalLayers(
  layers: Array<{
    layer_id?: string;
    layer_name?: string;
    layer_order?: number;
    [key: string]: unknown;
  }>
): { valid: boolean; errors: string[] } {
  const errors: string[] = [];

  // 检查 1：数量必须是 13
  if (layers.length !== 13) {
    errors.push(`层数量不符合预期：期望 13，实际 ${layers.length}`);
    return { valid: false, errors };
  }

  // 检查 2：layer_id 必须完全匹配
  const expectedIds = CANONICAL_LAYERS.map(([id]) => id);
  const actualIds = layers.map((l) => l.layer_id);
  if (JSON.stringify(actualIds) !== JSON.stringify(expectedIds)) {
    errors.push(`层 ID 不匹配：期望 ${JSON.stringify(expectedIds)}，实际 ${JSON.stringify(actualIds)}`);
  }

  // 检查 3：layer_name 必须完全匹配
  const expectedNames = CANONICAL_LAYER_NAMES;
  const actualNames = layers.map((l) => l.layer_name);
  if (JSON.stringify(actualNames) !== JSON.stringify(expectedNames)) {
    errors.push(`层名称不匹配：期望 ${JSON.stringify(expectedNames)}，实际 ${JSON.stringify(actualNames)}`);
  }

  // 检查 4：layer_order 必须完全匹配
  const expectedOrders = CANONICAL_LAYER_ORDERS;
  const actualOrders = layers.map((l) => l.layer_order);
  if (JSON.stringify(actualOrders) !== JSON.stringify(expectedOrders)) {
    errors.push(`层顺序不匹配：期望 ${JSON.stringify(expectedOrders)}，实际 ${JSON.stringify(actualOrders)}`);
  }

  // 检查 5：每个层逐项验证
  for (let i = 0; i < 13; i += 1) {
    const [expectedId, expectedName, expectedOrder] = CANONICAL_LAYERS[i];
    const actual = layers[i];

    if (actual.layer_id !== expectedId) {
      errors.push(
        `第 ${i} 层 layer_id 不符：期望 "${expectedId}"，实际 "${actual.layer_id}"`
      );
    }
    if (actual.layer_name !== expectedName) {
      errors.push(
        `第 ${i} 层 layer_name 不符：期望 "${expectedName}"，实际 "${actual.layer_name}"`
      );
    }
    if (actual.layer_order !== expectedOrder) {
      errors.push(
        `第 ${i} 层 layer_order 不符：期望 ${expectedOrder}，实际 ${actual.layer_order}`
      );
    }
  }

  return {
    valid: errors.length === 0,
    errors,
  };
}

/**
 * 检查单个 layer_id 是否有效
 */
export function isValidLayerId(layerId: string | null | undefined): boolean {
  return layerId !== null && layerId !== undefined && CANONICAL_LAYER_IDS.has(layerId);
}

/**
 * 获取 layer_id 对应的 layer_name
 */
export function getLayerName(layerId: string): string | undefined {
  return CANONICAL_LAYER_ID_TO_NAME[layerId];
}

/**
 * 获取 layer_id 对应的 layer_order
 */
export function getLayerOrder(layerId: string): number | undefined {
  return CANONICAL_LAYER_ID_TO_ORDER[layerId];
}
