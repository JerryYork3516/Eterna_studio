/**
 * Stage 5 P2-D：Slot Catalog 获取与校验
 * 
 * 前端从后端 /schema/slot-catalog-v0.4 获取 Slot 列表，
 * 并用于验证 Node.slot_binding 是否有效。
 */

import type { SlotCatalogEntryV04, SlotCatalogResponseV04 } from "@/lib/schema-types";

/**
 * Slot 类型的允许值（当前阶段）
 */
export const ALLOWED_SLOT_TYPES = new Set([
  "llm",
  "tts",
  "memory",
  "avatar",
  "ar",
  "tool",
]);

/**
 * 校验 Slot 类型是否有效
 */
export function isValidSlotType(slotType: string | null | undefined): boolean {
  return slotType !== null && slotType !== undefined && ALLOWED_SLOT_TYPES.has(slotType);
}

/**
 * 校验单个 Slot 条目
 */
export function validateSlotEntry(slot: SlotCatalogEntryV04): { valid: boolean; errors: string[] } {
  const errors: string[] = [];

  // slot_id 必须非空
  if (!slot.slot_id || slot.slot_id.trim() === "") {
    errors.push("slot_id 为空");
  }

  // slot_type 必须有效
  if (!isValidSlotType(slot.slot_type)) {
    errors.push(`slot_type 无效："${slot.slot_type}"，允许值：${Array.from(ALLOWED_SLOT_TYPES).join(", ")}`);
  }

  // status 应该存在（可选的严格检查）
  // if (!slot.status) {
  //   errors.push("status 未定义");
  // }

  return {
    valid: errors.length === 0,
    errors,
  };
}

/**
 * 校验整个 Slot Catalog
 */
export function validateSlotCatalog(catalog: SlotCatalogResponseV04): { valid: boolean; errors: string[] } {
  const errors: string[] = [];
  const seenIds = new Set<string>();

  // 必须有 slots 数组
  if (!catalog.slots || !Array.isArray(catalog.slots)) {
    errors.push("Slot Catalog 不包含 slots 数组");
    return { valid: false, errors };
  }

  // 逐个校验每个 Slot
  for (let i = 0; i < catalog.slots.length; i += 1) {
    const slot = catalog.slots[i];

    // 检查 slot_id 唯一性
    if (slot.slot_id && seenIds.has(slot.slot_id)) {
      errors.push(`第 ${i} 个 Slot：slot_id 重复："${slot.slot_id}"`);
    }
    if (slot.slot_id) {
      seenIds.add(slot.slot_id);
    }

    // 检查单个 Slot 有效性
    const slotValidation = validateSlotEntry(slot);
    if (!slotValidation.valid) {
      errors.push(`第 ${i} 个 Slot 验证失败：${slotValidation.errors.join("; ")}`);
    }
  }

  return {
    valid: errors.length === 0,
    errors,
  };
}

/**
 * 根据 slot_id 查找 Slot
 */
export function findSlotById(
  catalog: SlotCatalogResponseV04,
  slotId: string
): SlotCatalogEntryV04 | undefined {
  return catalog.slots?.find((slot) => slot.slot_id === slotId);
}

/**
 * 检查 slot_binding 是否有效
 */
export function validateSlotBinding(
  slotBinding: string | null | undefined,
  catalog: SlotCatalogResponseV04 | undefined
): { valid: boolean; message: string } {
  // slot_binding 可以为空（节点可以不需要 Slot）
  if (!slotBinding) {
    return {
      valid: true,
      message: "slot_binding 为空（可选）",
    };
  }

  // 必须能获取到 Slot Catalog
  if (!catalog || !catalog.slots) {
    return {
      valid: false,
      message: `无法校验 slot_binding：Slot Catalog 未加载`,
    };
  }

  // 在 Catalog 中查找
  const slot = findSlotById(catalog, slotBinding);
  if (!slot) {
    return {
      valid: false,
      message: `slot_binding "${slotBinding}" 在 Slot Catalog 中不存在`,
    };
  }

  return {
    valid: true,
    message: `slot_binding "${slotBinding}" 有效（类型：${slot.slot_type}）`,
  };
}

/**
 * 获取 Slot Catalog 的简要统计
 */
export function getSlotCatalogStats(catalog: SlotCatalogResponseV04): {
  totalSlots: number;
  slotsByType: Record<string, number>;
  validSlots: number;
  invalidSlots: number;
} {
  const slots = catalog.slots || [];
  const stats = {
    totalSlots: slots.length,
    slotsByType: {} as Record<string, number>,
    validSlots: 0,
    invalidSlots: 0,
  };

  for (const slot of slots) {
    const validation = validateSlotEntry(slot);
    if (validation.valid) {
      stats.validSlots += 1;
    } else {
      stats.invalidSlots += 1;
    }

    if (slot.slot_type) {
      stats.slotsByType[slot.slot_type] = (stats.slotsByType[slot.slot_type] || 0) + 1;
    }
  }

  return stats;
}
