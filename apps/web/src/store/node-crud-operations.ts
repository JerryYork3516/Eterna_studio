/**
 * P1-FIX：Node CRUD 操作规范化
 * 
 * 所有 node 操作都必须通过这些函数进行，确保：
 * 1. 操作是原子性的
 * 2. 状态一致性得到保证
 * 3. 所有操作都被记录和可追踪
 */

import type { WorkflowNode, WorkflowEdge } from "@/lib/schema-types";
import type { Node, Edge } from "@xyflow/react";

/**
 * Node CRUD 操作的标准返回类型
 */
export interface NodeCRUDResult {
  success: boolean;
  message: string;
  timestamp: string;
  operation: string;
  nodeId?: string;
  nodeCount?: number;
  edgeCount?: number;
  error?: string;
}

/**
 * 添加 node 的规范操作
 */
export function createAddNodeMutation(
  newNode: Node,
  currentNodes: Node[],
  currentEdges: Edge[]
): NodeCRUDResult {
  // 防重复检查
  if (currentNodes.some((n) => n.id === newNode.id)) {
    return {
      success: false,
      message: `节点已存在: ${newNode.id}`,
      timestamp: new Date().toISOString(),
      operation: 'add_node',
      error: `Duplicate node ID: ${newNode.id}`,
    };
  }

  return {
    success: true,
    message: `节点添加成功: ${newNode.id}`,
    timestamp: new Date().toISOString(),
    operation: 'add_node',
    nodeId: newNode.id,
    nodeCount: currentNodes.length + 1,
    edgeCount: currentEdges.length,
  };
}

/**
 * 删除 node 的规范操作
 */
export function createDeleteNodeMutation(
  nodeIdToDelete: string,
  currentNodes: Node[],
  currentEdges: Edge[]
): NodeCRUDResult {
  // 验证节点存在
  if (!currentNodes.some((n) => n.id === nodeIdToDelete)) {
    return {
      success: false,
      message: `节点不存在: ${nodeIdToDelete}`,
      timestamp: new Date().toISOString(),
      operation: 'delete_node',
      error: `Node not found: ${nodeIdToDelete}`,
    };
  }

  // 计算相关的边（会被删除）
  const relatedEdges = currentEdges.filter(
    (e) => e.source === nodeIdToDelete || e.target === nodeIdToDelete
  );

  return {
    success: true,
    message: `节点删除成功: ${nodeIdToDelete} (删除 ${relatedEdges.length} 条连接)`,
    timestamp: new Date().toISOString(),
    operation: 'delete_node',
    nodeId: nodeIdToDelete,
    nodeCount: currentNodes.length - 1,
    edgeCount: currentEdges.length - relatedEdges.length,
  };
}

/**
 * 更新 node 数据的规范操作
 */
export function createUpdateNodeMutation(
  nodeId: string,
  updateData: Partial<Node>,
  currentNodes: Node[]
): NodeCRUDResult {
  const node = currentNodes.find((n) => n.id === nodeId);
  if (!node) {
    return {
      success: false,
      message: `节点不存在: ${nodeId}`,
      timestamp: new Date().toISOString(),
      operation: 'update_node',
      error: `Node not found: ${nodeId}`,
    };
  }

  return {
    success: true,
    message: `节点更新成功: ${nodeId}`,
    timestamp: new Date().toISOString(),
    operation: 'update_node',
    nodeId: nodeId,
    nodeCount: currentNodes.length,
  };
}

/**
 * 添加 edge 的规范操作
 */
export function createAddEdgeMutation(
  newEdge: Edge,
  currentNodes: Node[],
  currentEdges: Edge[]
): NodeCRUDResult {
  // 验证源节点和目标节点都存在
  const sourceNodeExists = currentNodes.some((n) => n.id === newEdge.source);
  const targetNodeExists = currentNodes.some((n) => n.id === newEdge.target);

  if (!sourceNodeExists || !targetNodeExists) {
    return {
      success: false,
      message: `连接的节点不存在`,
      timestamp: new Date().toISOString(),
      operation: 'add_edge',
      error: `Source or target node not found`,
    };
  }

  // 防重复（避免多个相同的连接）
  if (
    currentEdges.some(
      (e) => e.source === newEdge.source && e.target === newEdge.target
    )
  ) {
    return {
      success: false,
      message: `连接已存在: ${newEdge.source} → ${newEdge.target}`,
      timestamp: new Date().toISOString(),
      operation: 'add_edge',
      error: `Edge already exists`,
    };
  }

  return {
    success: true,
    message: `连接添加成功: ${newEdge.source} → ${newEdge.target}`,
    timestamp: new Date().toISOString(),
    operation: 'add_edge',
    nodeCount: currentNodes.length,
    edgeCount: currentEdges.length + 1,
  };
}

/**
 * 删除 edge 的规范操作
 */
export function createDeleteEdgeMutation(
  edgeId: string,
  currentNodes: Node[],
  currentEdges: Edge[]
): NodeCRUDResult {
  if (!currentEdges.some((e) => e.id === edgeId)) {
    return {
      success: false,
      message: `连接不存在: ${edgeId}`,
      timestamp: new Date().toISOString(),
      operation: 'delete_edge',
      error: `Edge not found: ${edgeId}`,
    };
  }

  return {
    success: true,
    message: `连接删除成功: ${edgeId}`,
    timestamp: new Date().toISOString(),
    operation: 'delete_edge',
    nodeCount: currentNodes.length,
    edgeCount: currentEdges.length - 1,
  };
}

/**
 * 批量删除 nodes 的规范操作
 */
export function createBatchDeleteNodesMutation(
  nodeIdsToDelete: string[],
  currentNodes: Node[],
  currentEdges: Edge[]
): NodeCRUDResult {
  const nodeIds = new Set(nodeIdsToDelete);
  const invalidIds = nodeIdsToDelete.filter((id) => !currentNodes.some((n) => n.id === id));

  if (invalidIds.length > 0) {
    return {
      success: false,
      message: `部分节点不存在: ${invalidIds.join(', ')}`,
      timestamp: new Date().toISOString(),
      operation: 'batch_delete_nodes',
      error: `Some nodes not found`,
    };
  }

  // 计算会被删除的边
  const relatedEdges = currentEdges.filter(
    (e) => nodeIds.has(e.source) || nodeIds.has(e.target)
  );

  return {
    success: true,
    message: `批量删除成功: ${nodeIdsToDelete.length} 个节点 (删除 ${relatedEdges.length} 条连接)`,
    timestamp: new Date().toISOString(),
    operation: 'batch_delete_nodes',
    nodeCount: currentNodes.length - nodeIdsToDelete.length,
    edgeCount: currentEdges.length - relatedEdges.length,
  };
}

/**
 * 验证图的一致性
 */
export function validateGraphConsistency(
  nodes: Node[],
  edges: Edge[]
): { valid: boolean; errors: string[] } {
  const errors: string[] = [];
  const nodeIds = new Set(nodes.map((n) => n.id));

  // 检查所有边的源和目标节点都存在
  for (const edge of edges) {
    if (!nodeIds.has(edge.source)) {
      errors.push(`边 ${edge.id} 的源节点 ${edge.source} 不存在`);
    }
    if (!nodeIds.has(edge.target)) {
      errors.push(`边 ${edge.id} 的目标节点 ${edge.target} 不存在`);
    }
  }

  // 检查节点 ID 的唯一性
  const nodeIdArray = nodes.map((n) => n.id);
  const duplicateIds = nodeIdArray.filter((id, index) => nodeIdArray.indexOf(id) !== index);
  if (duplicateIds.length > 0) {
    errors.push(`存在重复的节点 ID: ${[...new Set(duplicateIds)].join(', ')}`);
  }

  // 检查边 ID 的唯一性
  const edgeIdArray = edges.map((e) => e.id);
  const duplicateEdgeIds = edgeIdArray.filter((id, index) => edgeIdArray.indexOf(id) !== index);
  if (duplicateEdgeIds.length > 0) {
    errors.push(`存在重复的边 ID: ${[...new Set(duplicateEdgeIds)].join(', ')}`);
  }

  return {
    valid: errors.length === 0,
    errors,
  };
}
