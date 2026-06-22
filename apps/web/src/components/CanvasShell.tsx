import { useCallback, useEffect, useMemo, useRef, useState, type MouseEvent as ReactMouseEvent, type ReactNode } from "react";
import {
  addEdge,
  Background,
  Controls,
  Handle,
  MiniMap,
  Position,
  ReactFlow,
  useEdgesState,
  useNodesState,
  type Connection,
  type Edge,
  type EdgeChange,
  type Node,
  type NodeChange,
  type NodeMouseHandler,
  type OnNodeDrag
} from "@xyflow/react";
import { translate, type Language } from "@/i18n";
import { executeWorkflow } from "@/engine/executeWorkflow";
import { api } from "@/lib/api";
import type { Artifact, NodeType, Workflow, WorkflowEdge, WorkflowNode } from "@/lib/schema-types";
import { downloadWorkflow, readWorkflowFile, withUpdatedWorkflowGraph } from "@/lib/workflow";
import { loadModuleCanvas, saveModuleCanvas } from "@/lib/persistence";
import { getNodeDefinition } from "@/registry/nodeRegistry";
import { useCanvasStore } from "@/store/canvas-store";
import { LayerContainerNode } from "@/components/canvas/LayerContainerNode";
import { WorkflowNodeCard } from "@/components/canvas/WorkflowNodeCard";

const libraryNodeTypes: NodeType[] = ["input", "transform", "model", "agent", "review", "output", "export"];
const fallbackTemplateTypes = ["blank", "persona_builder", "agent", "knowledge_pipeline", "review_pipeline"];
const TRUNK_LAYER_X = 920;
const TRUNK_LAYER_HEIGHT = 216;
const FOLDER_GROUP_WIDTH = 950;
const FOLDER_GROUP_HEIGHT = 216;
const FOLDER_GROUP_GAP = 110;
const TRUNK_LAYER_Y_STEP = 270;
const TRUNK_LAYER_Y_OFFSET = 110;
const collapsedNodeLabels: Record<NodeType, { zh: string; en: string }> = {
  input: { zh: "入", en: "In" },
  transform: { zh: "转", en: "Tr" },
  model: { zh: "模", en: "Mo" },
  agent: { zh: "代", en: "Ag" },
  review: { zh: "审", en: "Rv" },
  layer_container: { zh: "层", en: "Ly" },
  output: { zh: "出", en: "Out" },
  export: { zh: "导", en: "Ex" }
};

type BottomTab = "logs" | "artifacts" | "preview";
type DrawerId = "layers" | "inspector" | BottomTab;
type WorkspaceMode = "inline" | "right" | "split" | "window";

type LayerSummary = {
  node: WorkflowNode;
  index: number;
  displayIndex: number;
  displayLabel: string;
  groupLabel: string;
  tier: string;
  status: string;
  childNodes: WorkflowNode[];
};

type FolderGroupNodeData = {
  layer: LayerSummary;
  subnodes: WorkflowNode[];
  onSelectNode: (node: WorkflowNode) => void;
  onPreviewNode: (node: WorkflowNode) => void;
};

const nodeTypes = {
  layerContainer: LayerContainerNode,
  workflowNode: WorkflowNodeCard,
  folderGroup: FolderGroupNode
};

type LayerViewConfig = {
  displayIndex: number;
  label: string;
  group: string;
};

const layerViewConfigByIndex: Record<number, LayerViewConfig> = {
  1: { displayIndex: 1, label: "Identity Core", group: "Group A: Identity & Constraints" },
  2: { displayIndex: 2, label: "Personality", group: "Group A: Identity & Constraints" },
  3: { displayIndex: 3, label: "Safety / Boundary", group: "Group A: Identity & Constraints" },
  4: { displayIndex: 4, label: "Legal / Permission", group: "Group A: Identity & Constraints" },
  5: { displayIndex: 5, label: "Memory", group: "Group B: Cognition System" },
  6: { displayIndex: 6, label: "Knowledge", group: "Group B: Cognition System" },
  7: { displayIndex: 7, label: "World / Context", group: "Group B: Cognition System" },
  8: { displayIndex: 8, label: "Behavior", group: "Group C: Action & Execution" },
  9: { displayIndex: 9, label: "Capability / Tools", group: "Group C: Action & Execution" },
  10: { displayIndex: 10, label: "Multimodal", group: "Group C: Action & Execution" },
  11: { displayIndex: 11, label: "Relationship", group: "Group D: Social & Meta" },
  12: { displayIndex: 12, label: "Meta / Self-Reflection", group: "Group D: Social & Meta" },
  13: { displayIndex: 13, label: "Export / Deployment", group: "Group E: Output" }
};

function getLayerViewConfig(layerIndex: number, fallbackLabel: string): LayerViewConfig {
  return layerViewConfigByIndex[layerIndex] ?? {
    displayIndex: layerIndex || 999,
    label: fallbackLabel,
    group: "Ungrouped"
  };
}

function dataString(node: WorkflowNode, key: string, fallback = "") {
  const value = node.data?.[key];
  return value === null || value === undefined || value === "" ? fallback : String(value);
}

function dataNumber(node: WorkflowNode, key: string) {
  const value = node.data?.[key];
  const numberValue = typeof value === "number" ? value : Number(value);
  return Number.isFinite(numberValue) ? numberValue : null;
}

function getLayerIndex(node: WorkflowNode) {
  return dataNumber(node, "layer_index");
}

function getNodeTypeLabel(type: string, t: (key: string, fallback?: string) => string) {
  return getNodeDefinition(type)?.label ?? t(`node.type.${type}`, type);
}

function inferNodeLayerIndex(node: WorkflowNode, layers: WorkflowNode[]) {
  const directLayer = getLayerIndex(node);
  if (directLayer !== null) {
    return directLayer;
  }

  const idMatch = node.node_id.match(/(?:^|_)l(\d{1,2})(?:_|$)/i);
  if (idMatch) {
    return Number(idMatch[1]);
  }

  const nodeY = node.position?.y;
  if (typeof nodeY !== "number") {
    return null;
  }

  let inferred: number | null = null;
  for (const layer of layers) {
    const layerIndex = getLayerIndex(layer);
    const layerY = layer.position?.y;
    if (layerIndex === null || typeof layerY !== "number") {
      continue;
    }
    if (nodeY >= layerY) {
      inferred = layerIndex;
    }
  }
  return inferred;
}

function dataStringValue(node: WorkflowNode, key: string) {
  const value = node.data?.[key];
  return typeof value === "string" && value ? value : null;
}

function resolveUiLayerId(schemaNode: WorkflowNode, layers: WorkflowNode[], allNodes: WorkflowNode[]) {
  const explicitLayerId =
    dataStringValue(schemaNode, "layer_id") ?? dataStringValue(schemaNode, "layerId") ?? dataStringValue(schemaNode, "parent_layer") ?? dataStringValue(schemaNode, "parentLayer");
  if (explicitLayerId) {
    return explicitLayerId;
  }

  if (schemaNode.type === "layer_container") {
    return schemaNode.node_id;
  }

  const inferredLayerIndex = inferNodeLayerIndex(schemaNode, layers);
  const inferredLayer = layers.find((layer) => getLayerIndex(layer) === inferredLayerIndex);
  if (inferredLayer) {
    return inferredLayer.node_id;
  }

  const nonLayerIndex = allNodes.filter((node) => node.type !== "layer_container").findIndex((node) => node.node_id === schemaNode.node_id);
  if (nonLayerIndex >= 0 && layers.length) {
    return layers[Math.min(nonLayerIndex, layers.length - 1)]?.node_id ?? null;
  }

  return null;
}

function makeFlowNode(schemaNode: WorkflowNode, offset?: { x: number; y: number }, uiLayerId?: string | null): Node {
  const position = schemaNode.position ?? { x: 0, y: 0 };
  return {
    id: schemaNode.node_id,
    type: schemaNode.type === "layer_container" ? "layerContainer" : "workflowNode",
    position: offset ? { x: position.x - offset.x, y: position.y - offset.y } : position,
    data: { schemaNode, layer_id: uiLayerId ?? schemaNode.data?.layer_id }
  };
}

function makeUiModuleFlowNodes(layer: LayerSummary): Node[] {
  const moduleCount = 3 + ((layer.displayIndex - 1) % 3);
  return Array.from({ length: moduleCount }, (_, index) => {
    const moduleNumber = index + 1;
    const moduleNode = {
      node_id: `${layer.node.node_id}_module_${moduleNumber}`,
      type: "module",
      category: "processing",
      title_key: `ui.module.${layer.node.node_id}.${moduleNumber}`,
      title_fallback: `Module ${moduleNumber}`,
      position: {
        x: 0,
        y: 0
      },
      lock_level: "editable",
      locale: null,
      data: {
        parent_layer: layer.node.node_id,
        layer_index: layer.index,
        module_tier: layer.tier,
        status: "ui-only"
      },
      ports: {
        inputs: [],
        outputs: []
      },
      validation: null
    } as unknown as WorkflowNode;

    return {
      id: moduleNode.node_id,
      type: "module",
      hidden: true,
      position: moduleNode.position ?? { x: 0, y: 0 },
      data: {
        schemaNode: moduleNode,
        parent_layer: layer.node.node_id,
        layer_index: layer.index
      }
    } satisfies Node;
  });
}

function FolderGroupNode({ data }: { data: FolderGroupNodeData }) {
  const language = useCanvasStore((state) => state.language);
  const { layer, subnodes, onSelectNode, onPreviewNode } = data;
  const label = layer.displayLabel;
  const parameterCount = Object.keys(layer.node.data ?? {}).length;

  return (
    <section className={`folder-group-node tier-${layer.tier}`}>
      <div className="folder-group-node__header">
        <div className="folder-group-title">
          <span className="folder-icon" aria-hidden="true">
            ::
          </span>
          <div>
            <p>{translate(language, "workspace.breadcrumb", "Workflow / Layer / Folder")}</p>
            <h3>
              L{layer.displayIndex} {label}
              <span className="module-count-badge">{subnodes.length} modules</span>
            </h3>
          </div>
        </div>
        <div className="folder-group-meta compact">
          <span>{translate(language, "field.status")}: {layer.status}</span>
          <span>Tier: {layer.tier}</span>
          <span>{translate(language, "field.data")}: {parameterCount}</span>
        </div>
      </div>
      <div className="submodule-rail">
        {subnodes.length ? (
          subnodes.slice(0, 6).map((node) => {
            const moduleTier = dataString(node, "module_tier", layer.tier);
            return (
              <button
                key={node.node_id}
                className={`submodule-card tier-${moduleTier}`}
                onClick={() => onSelectNode(node)}
                onDoubleClick={() => onPreviewNode(node)}
                onTouchEnd={(event) => {
                  event.preventDefault();
                  onSelectNode(node);
                }}
              >
                <span className="submodule-name">{translate(language, node.title_key, node.title_fallback)}</span>
                <span className="submodule-tier">{moduleTier}</span>
              </button>
            );
          })
        ) : null}
      </div>
      <Handle type="source" position={Position.Right} id="folder_out" className="flow-handle folder-flow-handle" />
    </section>
  );
}

export function CanvasShell() {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [bottomTab, setBottomTab] = useState<BottomTab>("logs");
  const [activeDrawer, setActiveDrawer] = useState<DrawerId | null>(null);
  const [selectedTemplateType, setSelectedTemplateType] = useState("persona_builder");
  const [nodeLibraryCollapsed, setNodeLibraryCollapsed] = useState(false);
  const [activeLayerId, setActiveLayerId] = useState<string | null>(null);
  const [workspaceTabs, setWorkspaceTabs] = useState<string[]>([]);
  const [activeWorkspaceId, setActiveWorkspaceId] = useState<string | null>(null);
  const [workspaceMode, setWorkspaceMode] = useState<WorkspaceMode>("inline");
  const [collapsedLayerIds, setCollapsedLayerIds] = useState<Set<string>>(() => new Set());
  const [floatingLayerIds, setFloatingLayerIds] = useState<string[]>([]);
  const [floatingNodeIds, setFloatingNodeIds] = useState<string[]>([]);
  const [draggedNodeIds, setDraggedNodeIds] = useState<Set<string>>(() => new Set());
  const [folderNodePositions, setFolderNodePositions] = useState<Record<string, { x: number; y: number }>>({});
  const [moduleTabs, setModuleTabs] = useState<string[]>([]);
  const [activeModuleTabId, setActiveModuleTabId] = useState<string | null>(null);
  const {
    workflow,
    nodes,
    edges,
    logs,
    artifacts,
    language,
    templates,
    validation,
    exportPreview,
    apiReady,
    setWorkflow,
    hydrateWorkflow,
    setSelectedNode,
    updateNodePosition,
    removeEdges,
    setLanguage,
    setTemplates,
    setValidation,
    setArtifacts,
    setExportPreview,
    setApiReady,
    appendLog,
    clearRunOutput
  } = useCanvasStore();

  const t = useCallback((key: string, fallback?: string) => translate(language, key, fallback), [language]);
  const selectedNodeId = useCanvasStore((state) => state.selectedNodeId);
  const templateOptions = useMemo(() => {
    const loadedTypes = new Set(templates.map((template) => template.template_type));
    const mergedTypes = [...templates.map((template) => template.template_type)];
    for (const templateType of fallbackTemplateTypes) {
      if (!loadedTypes.has(templateType)) {
        mergedTypes.push(templateType);
      }
    }
    return mergedTypes;
  }, [templates]);

  const layerNodes = useMemo(
    () =>
      nodes
        .filter((node) => node.type === "layer_container")
        .slice()
        .sort((a, b) => (getLayerIndex(a) ?? 999) - (getLayerIndex(b) ?? 999)),
    [nodes]
  );

  const layerSummaries = useMemo<LayerSummary[]>(
    () =>
      layerNodes
        .map((layer) => {
        const index = getLayerIndex(layer) ?? 0;
        const label = translate(language, layer.title_key, layer.title_fallback);
        const viewConfig = getLayerViewConfig(index, label);
        const childNodes = nodes.filter(
          (node) => node.type !== "layer_container" && inferNodeLayerIndex(node, layerNodes) === index
        );
        return {
          node: layer,
          index,
          displayIndex: viewConfig.displayIndex,
          displayLabel: viewConfig.label,
          groupLabel: viewConfig.group,
          tier: dataString(layer, "module_tier", "core"),
          status: dataString(layer, "status", "empty"),
          childNodes
        };
      })
        .sort((a, b) => a.displayIndex - b.displayIndex),
    [language, layerNodes, nodes]
  );

  // UI-only module placeholders are generated client-side (makeUiModuleFlowNodes)
  // and never live in store.nodes, so resolve the selected node against both sets.
  const uiModuleNodes = useMemo(
    () =>
      layerSummaries.flatMap((layer) =>
        makeUiModuleFlowNodes(layer).map((node) => (node.data as { schemaNode: WorkflowNode }).schemaNode)
      ),
    [layerSummaries]
  );
  const selectedNode = useMemo(
    () =>
      nodes.find((node) => node.node_id === selectedNodeId) ??
      uiModuleNodes.find((node) => node.node_id === selectedNodeId) ??
      null,
    [nodes, uiModuleNodes, selectedNodeId]
  );
  const resolveModuleNode = useCallback(
    (id: string) => nodes.find((node) => node.node_id === id) ?? uiModuleNodes.find((node) => node.node_id === id) ?? null,
    [nodes, uiModuleNodes]
  );
  const moduleTabItems = useMemo(
    () =>
      moduleTabs.map((id) => {
        const node = resolveModuleNode(id);
        return { id, label: node ? translate(language, node.title_key, node.title_fallback) : id };
      }),
    [language, moduleTabs, resolveModuleNode]
  );
  const activeModuleNode = useMemo(
    () => (activeModuleTabId ? resolveModuleNode(activeModuleTabId) : null),
    [activeModuleTabId, resolveModuleNode]
  );
  const activeModuleSubnodes = useMemo(
    () =>
      activeModuleTabId
        ? nodes.filter(
            (node) =>
              node.node_id !== activeModuleTabId &&
              (node.data?.parent_module === activeModuleTabId || node.data?.parent_layer === activeModuleTabId)
          )
        : [],
    [activeModuleTabId, nodes]
  );

  const layerById = useMemo(
    () => new Map(layerSummaries.map((layer) => [layer.node.node_id, layer])),
    [layerSummaries]
  );
  const selectedLayer = activeWorkspaceId ? layerById.get(activeWorkspaceId) ?? null : null;
  const activeLayer = activeLayerId ? layerById.get(activeLayerId) ?? null : selectedLayer;

  useEffect(() => {
    hydrateWorkflow();
  }, [hydrateWorkflow]);

  useEffect(() => {
    if (workflow?.template_type) {
      setSelectedTemplateType(workflow.template_type);
    }
  }, [workflow?.template_type]);

  useEffect(() => {
    let active = true;

    api
      .health()
      .then(() => {
        if (!active) {
          return;
        }
        setApiReady(true);
        appendLog(t("status.apiReady"));
      })
      .catch(() => {
        if (active) {
          setApiReady(false);
        }
      });

    api
      .listTemplates()
      .then((result) => {
        if (!active) {
          return;
        }
        setTemplates(result.templates);
        appendLog(t("status.templatesLoaded"));
      })
      .catch(() => {
        if (active) {
          setTemplates([]);
        }
      });

    return () => {
      active = false;
    };
  }, [appendLog, setApiReady, setTemplates, t]);

  useEffect(() => {
    if (activeLayerId && !layerById.has(activeLayerId)) {
      setActiveLayerId(null);
    }
    if (activeWorkspaceId && !layerById.has(activeWorkspaceId)) {
      setActiveWorkspaceId(null);
    }
    setWorkspaceTabs((tabs) => tabs.filter((id) => layerById.has(id)));
    setFloatingLayerIds((ids) => ids.filter((id) => layerById.has(id)));
    setFloatingNodeIds((ids) => ids.filter((id) => nodes.some((node) => node.node_id === id)));
  }, [activeLayerId, activeWorkspaceId, layerById, nodes]);

  const visibleNodeIds = useMemo(() => {
    const ids = new Set<string>();
    for (const node of nodes) {
      if (node.type === "layer_container") {
        ids.add(node.node_id);
        continue;
      }
      const layerIndex = inferNodeLayerIndex(node, layerNodes);
      const parentLayer = layerSummaries.find((layer) => layer.index === layerIndex);
      if (!parentLayer || !collapsedLayerIds.has(parentLayer.node.node_id)) {
        ids.add(node.node_id);
      }
    }
    return ids;
  }, [collapsedLayerIds, layerNodes, layerSummaries, nodes]);

  const handleChildModuleSelect = useCallback(
    (node: WorkflowNode) => {
      setSelectedNode(node.node_id);
      setActiveDrawer("inspector");
      appendLog(`${t("status.moduleSelected", "Module selected")}: ${t(node.title_key, node.title_fallback)}`);
    },
    [appendLog, setSelectedNode, t]
  );

  const handleChildModulePreview = useCallback(
    (node: WorkflowNode) => {
      setModuleTabs((tabs) => (tabs.includes(node.node_id) ? tabs : [...tabs, node.node_id]));
      setActiveModuleTabId(node.node_id);
      setActiveDrawer(null);
      appendLog(`${t("status.moduleCanvasOpened", "Module canvas opened")}: ${t(node.title_key, node.title_fallback)}`);
    },
    [appendLog, t]
  );

  const closeModuleTab = useCallback(
    (id: string) => {
      const index = moduleTabs.indexOf(id);
      const next = moduleTabs.filter((tabId) => tabId !== id);
      setModuleTabs(next);
      setActiveModuleTabId((current) => (current === id ? next[Math.max(0, index - 1)] ?? null : current));
      appendLog(`${t("status.moduleCanvasClosed", "Module canvas closed")}: ${id}`);
    },
    [appendLog, moduleTabs, t]
  );

  const reorderModuleTab = useCallback((fromId: string, toId: string) => {
    setModuleTabs((tabs) => {
      const from = tabs.indexOf(fromId);
      const to = tabs.indexOf(toId);
      if (from === -1 || to === -1 || from === to) {
        return tabs;
      }
      const next = [...tabs];
      const [moved] = next.splice(from, 1);
      next.splice(to, 0, moved);
      return next;
    });
  }, []);

  const pinModuleTab = useCallback((id: string) => {
    setModuleTabs((tabs) => (!tabs.includes(id) || tabs[0] === id ? tabs : [id, ...tabs.filter((tabId) => tabId !== id)]));
  }, []);

  const getLayerDisplayPosition = useCallback(
    (layerNode: WorkflowNode, displayIndex: number) => {
      if (draggedNodeIds.has(layerNode.node_id) && layerNode.position) {
        return layerNode.position;
      }
      return {
        x: TRUNK_LAYER_X,
        y: (displayIndex - 1) * TRUNK_LAYER_Y_STEP + TRUNK_LAYER_Y_OFFSET
      };
    },
    [draggedNodeIds]
  );

  const getFolderDisplayPosition = useCallback(
    (layer: LayerSummary) => {
      const folderNodeId = `ui-folder-${layer.node.node_id}`;
      const layerPosition = getLayerDisplayPosition(layer.node, layer.displayIndex);
      return (
        folderNodePositions[folderNodeId] ?? {
          x: layerPosition.x - FOLDER_GROUP_WIDTH - FOLDER_GROUP_GAP,
          y: layerPosition.y + (TRUNK_LAYER_HEIGHT - FOLDER_GROUP_HEIGHT) / 2
        }
      );
    },
    [folderNodePositions, getLayerDisplayPosition]
  );

  const flowNodes = useMemo<Node[]>(() => {
    const schemaFlowNodes = nodes
      .filter((node) => {
        if (!visibleNodeIds.has(node.node_id)) {
          return false;
        }
        if (node.type === "layer_container") {
          return true;
        }
        return inferNodeLayerIndex(node, layerNodes) === null;
      })
      .map((schemaNode) => {
        const flowNode = makeFlowNode(schemaNode, undefined, resolveUiLayerId(schemaNode, layerNodes, nodes));
        if (schemaNode.type !== "layer_container") {
          return flowNode;
        }
        const layer = layerById.get(schemaNode.node_id);
        const displayIndex = layer?.displayIndex ?? getLayerIndex(schemaNode) ?? 1;
        return {
          ...flowNode,
          position: getLayerDisplayPosition(schemaNode, displayIndex),
          style: { width: 380, height: TRUNK_LAYER_HEIGHT },
          data: {
            ...flowNode.data,
            viewLabel: layer?.displayLabel,
            viewIndex: displayIndex,
            groupLabel: layer?.groupLabel
          }
        };
      });
    const uiModuleFlowNodes = layerSummaries.flatMap((layer) => makeUiModuleFlowNodes(layer));

    if (!activeLayer) {
      return [...schemaFlowNodes, ...uiModuleFlowNodes];
    }

    const activeLayerId = activeLayer.node.node_id;
    const allReactFlowNodes = [...schemaFlowNodes, ...uiModuleFlowNodes];
    const reactFlowDataSample = allReactFlowNodes.slice(0, 5).map((node) => ({ id: node.id, data: node.data }));
    const missingLayerLinkCount = allReactFlowNodes.filter((node) => {
      const data = (node.data as { schemaNode: WorkflowNode }).schemaNode.data ?? {};
      return !("layer_id" in data) && !("layerId" in data) && !("parent_layer" in data) && !("parentLayer" in data);
    }).length;
    const activeLayerSubnodes = allReactFlowNodes
      .filter((node) => node.type === "module" && (node.data as { parent_layer?: unknown }).parent_layer === activeLayerId)
      .map((node) => (node.data as { schemaNode: WorkflowNode }).schemaNode);
    console.log("[ReactFlow nodes data sample]", reactFlowDataSample);
    console.log("[ReactFlow nodes missing layer fields]", missingLayerLinkCount);
    console.log("[LayerWorkspace] layer.id", activeLayerId);
    console.log("[LayerWorkspace] filtered nodes count", activeLayerSubnodes.length);

    return [
      ...schemaFlowNodes,
      ...uiModuleFlowNodes,
      {
        id: `ui-folder-${activeLayer.node.node_id}`,
        type: "folderGroup",
        position: getFolderDisplayPosition(activeLayer),
        style: { width: FOLDER_GROUP_WIDTH, height: FOLDER_GROUP_HEIGHT },
        draggable: true,
        selectable: true,
        data: {
          layer: activeLayer,
          subnodes: activeLayerSubnodes,
          onSelectNode: handleChildModuleSelect,
          onPreviewNode: handleChildModulePreview
        } satisfies FolderGroupNodeData
      }
    ];
  }, [
    activeLayer,
    getFolderDisplayPosition,
    getLayerDisplayPosition,
    handleChildModulePreview,
    handleChildModuleSelect,
    layerById,
    layerNodes,
    layerSummaries,
    nodes,
    visibleNodeIds
  ]);

  const flowEdges = useMemo<Edge[]>(
    () => {
      const schemaNodeIds = new Set(flowNodes.filter((node) => !node.id.startsWith("ui-folder-")).map((node) => node.id));
      const schemaEdges = edges
        .filter((edge) => schemaNodeIds.has(edge.source) && schemaNodeIds.has(edge.target))
        .map((edge) => ({
          id: edge.edge_id,
          source: edge.source,
          target: edge.target,
          sourceHandle: edge.source_port,
          targetHandle: edge.target_port,
          type: "smoothstep"
        }));

      if (!activeLayer) {
        return schemaEdges;
      }

      return [
        ...schemaEdges,
        {
          id: `ui-folder-edge-${activeLayer.node.node_id}`,
          source: `ui-folder-${activeLayer.node.node_id}`,
          target: activeLayer.node.node_id,
          sourceHandle: "folder_out",
          targetHandle: "p_left_in",
          type: "smoothstep",
          animated: false,
          style: { stroke: "#7aa2f7", strokeWidth: 1.5 }
        }
      ];
    },
    [activeLayer, edges, flowNodes]
  );

  const requireWorkflow = useCallback(() => {
    if (!workflow) {
      appendLog(t("error.noWorkflow"), "warn");
      return null;
    }
    try {
      return withUpdatedWorkflowGraph(workflow, nodes, edges);
    } catch (error) {
      appendLog(`${t("error.file")}: ${(error as Error).message}`, "error");
      return null;
    }
  }, [appendLog, edges, nodes, t, workflow]);

  const handleSave = useCallback(() => {
    const currentWorkflow = requireWorkflow();
    if (!currentWorkflow) {
      return;
    }
    downloadWorkflow(currentWorkflow);
    appendLog(t("status.saved"));
  }, [appendLog, requireWorkflow, t]);

  const handleLoad = useCallback(() => {
    fileInputRef.current?.click();
  }, []);

  const handleFileSelected = useCallback(
    async (file: File | undefined) => {
      if (!file) {
        return;
      }

      try {
        const loaded = await readWorkflowFile(file);
        setWorkflow(loaded);
        setActiveLayerId(null);
        setActiveWorkspaceId(null);
        setWorkspaceTabs([]);
        setFloatingLayerIds([]);
        setFloatingNodeIds([]);
        setDraggedNodeIds(new Set());
        setFolderNodePositions({});
        setModuleTabs([]);
        setActiveModuleTabId(null);
        appendLog(`${t("status.loaded")}: ${loaded.name}`);
      } catch (error) {
        appendLog(`${t("error.file")}: ${(error as Error).message}`, "error");
      } finally {
        if (fileInputRef.current) {
          fileInputRef.current.value = "";
        }
      }
    },
    [appendLog, setWorkflow, t]
  );

  const handleValidate = useCallback(async () => {
    const currentWorkflow = requireWorkflow();
    if (!currentWorkflow) {
      return;
    }

    try {
      const result = await api.validateWorkflow(currentWorkflow);
      setValidation(result);
      appendLog(`${t("status.validated")}: ${result.package.status}`);
      setBottomTab("logs");
      setActiveDrawer("logs");
    } catch (error) {
      appendLog(`${t("error.api")}: ${(error as Error).message}`, "error");
    }
  }, [appendLog, requireWorkflow, setValidation, t]);

  const handleMockRun = useCallback(async () => {
    const currentWorkflow = requireWorkflow();
    if (!currentWorkflow) {
      return;
    }

    try {
      const result = await api.mockRun(currentWorkflow);
      const runArtifacts = (result.run.artifacts ?? []) as Artifact[];
      setArtifacts(runArtifacts);
      appendLog(`${t("status.mockRun")}: ${String(result.run.status ?? "-")}`);
      setBottomTab("artifacts");
      setActiveDrawer("artifacts");
    } catch (error) {
      appendLog(`${t("error.api")}: ${(error as Error).message}`, "error");
    }
  }, [appendLog, requireWorkflow, setArtifacts, t]);

  const handleExportPreview = useCallback(async () => {
    const currentWorkflow = requireWorkflow();
    if (!currentWorkflow) {
      return;
    }

    try {
      const result = await api.exportPreview(currentWorkflow, "workflow_json");
      setExportPreview(result.preview);
      appendLog(`${t("status.exportPreview")}: ${result.preview.export_kind}`);
      setBottomTab("preview");
      setActiveDrawer("preview");
    } catch (error) {
      appendLog(`${t("error.api")}: ${(error as Error).message}`, "error");
    }
  }, [appendLog, requireWorkflow, setExportPreview, t]);

  const handleTemplateClick = useCallback(
    async (templateType: string) => {
      clearRunOutput();

      if (templateType === "persona_builder") {
        try {
          const result = await api.createPersonaBuilder(undefined, language);
          setWorkflow(result.workflow);
          setActiveLayerId(null);
          setActiveWorkspaceId(null);
          setWorkspaceTabs([]);
          setFloatingLayerIds([]);
          setFloatingNodeIds([]);
          setDraggedNodeIds(new Set());
          setFolderNodePositions({});
          setModuleTabs([]);
          setActiveModuleTabId(null);
          setActiveDrawer("layers");
          appendLog(t("status.personaLoaded"));
        } catch (error) {
          appendLog(`${t("error.api")}: ${(error as Error).message}`, "error");
        }
        return;
      }

      appendLog(
        `${t("status.templateUnavailable", language === "zh" ? "暂未开放" : "Not available yet")}: ${t(`template.${templateType}`, templateType)}`,
        "warn"
      );
    },
    [appendLog, clearRunOutput, language, setWorkflow, t]
  );

  const openLayerWorkspace = useCallback(
    (layer: LayerSummary, mode: WorkspaceMode) => {
      setSelectedNode(layer.node.node_id);
      setActiveLayerId(layer.node.node_id);
      setActiveWorkspaceId(layer.node.node_id);
      setWorkspaceMode(mode);
      setWorkspaceTabs((tabs) => (tabs.includes(layer.node.node_id) ? tabs : [...tabs, layer.node.node_id]));
      if (mode === "right") {
        setActiveDrawer("inspector");
      }
      if (mode === "window") {
        setFloatingLayerIds((ids) => (ids.includes(layer.node.node_id) ? ids : [...ids, layer.node.node_id]));
      }
      appendLog(`${t("status.layerOpened", "Layer opened")}: L${layer.displayIndex} ${layer.displayLabel} / ${mode}`);
    },
    [appendLog, setSelectedNode, t]
  );

  const toggleLayerCollapsed = useCallback(
    (layer: LayerSummary) => {
      setCollapsedLayerIds((current) => {
        const next = new Set(current);
        if (next.has(layer.node.node_id)) {
          next.delete(layer.node.node_id);
          appendLog(`${t("status.layerExpanded", "Layer expanded")}: L${layer.displayIndex}`);
        } else {
          next.add(layer.node.node_id);
          appendLog(`${t("status.layerCollapsed", "Layer collapsed")}: L${layer.displayIndex}`);
        }
        return next;
      });
    },
    [appendLog, t]
  );

  const closeWorkspaceTab = useCallback(
    (nodeId: string) => {
      setWorkspaceTabs((tabs) => tabs.filter((id) => id !== nodeId));
      setFloatingLayerIds((ids) => ids.filter((id) => id !== nodeId));
      if (activeWorkspaceId === nodeId) {
        setActiveWorkspaceId(null);
      }
      appendLog(`${t("status.workspaceClosed", "Workspace closed")}: ${nodeId}`);
    },
    [activeWorkspaceId, appendLog, t]
  );

  const handleNodeClick: NodeMouseHandler = useCallback(
    (_event, node) => {
      if (node.id.startsWith("ui-folder-")) {
        return;
      }
      setSelectedNode(node.id);
      setActiveDrawer("inspector");
      const layer = layerById.get(node.id);
      if (layer) {
        setActiveLayerId(layer.node.node_id);
        const layerPosition = getLayerDisplayPosition(layer.node, layer.displayIndex);
        setFolderNodePositions((current) => ({
          ...current,
          [`ui-folder-${layer.node.node_id}`]: {
            x: layerPosition.x - FOLDER_GROUP_WIDTH - FOLDER_GROUP_GAP,
            y: layerPosition.y + (TRUNK_LAYER_HEIGHT - FOLDER_GROUP_HEIGHT) / 2
          }
        }));
      }
    },
    [getLayerDisplayPosition, layerById, setSelectedNode]
  );

  const handleNodeDoubleClick: NodeMouseHandler = useCallback(
    (_event, node) => {
      if (node.id.startsWith("ui-folder-")) {
        return;
      }
      const layer = layerById.get(node.id);
      if (layer) {
        openLayerWorkspace(layer, "inline");
      }
    },
    [layerById, openLayerWorkspace, setSelectedNode]
  );

  const handlePaneClick = useCallback(() => setSelectedNode(null), [setSelectedNode]);

  const handleNodesChange = useCallback(
    (changes: NodeChange[]) => {
      changes.forEach((change) => {
        if (change.type === "position" && change.position) {
          if (change.id.startsWith("ui-folder-")) {
            return;
          }
          setDraggedNodeIds((current) => {
            if (current.has(change.id)) {
              return current;
            }
            const next = new Set(current);
            next.add(change.id);
            return next;
          });
          updateNodePosition(change.id, change.position);
        }
        if (change.type === "select" && change.selected) {
          if (change.id.startsWith("ui-folder-")) {
            return;
          }
          setSelectedNode(change.id);
        }
      });
    },
    [setSelectedNode, updateNodePosition]
  );

  const handleEdgesChange = useCallback(
    (changes: EdgeChange[]) => {
      const removedEdgeIds = changes.filter((change) => change.type === "remove").map((change) => change.id);
      removeEdges(removedEdgeIds);
      if (removedEdgeIds.length) {
        appendLog(`${t("status.edgeRemoved", "Edge removed")}: ${removedEdgeIds.join(", ")}`);
      }
    },
    [appendLog, removeEdges, t]
  );

  const handleNodeDragStop: OnNodeDrag<Node> = useCallback(
    (_event, node) => {
      if (node.id.startsWith("ui-folder-")) {
        setFolderNodePositions((current) => ({
          ...current,
          [node.id]: node.position
        }));
        appendLog(`${t("status.nodeMoved", "Node moved")}: ${node.id}`);
        return;
      }
      updateNodePosition(node.id, node.position);
      appendLog(`${t("status.nodeMoved", "Node moved")}: ${node.id}`);
    },
    [appendLog, t, updateNodePosition]
  );

  // Canvas <-> Workflow JSON sync. Every structural edit rebuilds the workflow
  // graph and commits it through setWorkflow, so workflow.nodes / workflow.edges
  // stay the single source of truth.
  const handleConnect = useCallback(
    (connection: Connection) => {
      if (!workflow || !connection.source || !connection.target) {
        return;
      }
      const isSchemaNode = (id: string) => nodes.some((node) => node.node_id === id);
      if (!isSchemaNode(connection.source) || !isSchemaNode(connection.target)) {
        return;
      }
      const newEdge = {
        edge_id: `edge_${Date.now()}_${Math.round(Math.random() * 10000)}`,
        source: connection.source,
        target: connection.target,
        source_port: connection.sourceHandle || "p_out",
        target_port: connection.targetHandle || "p_in"
      } as unknown as WorkflowEdge;
      setWorkflow(withUpdatedWorkflowGraph(workflow, nodes, [...edges, newEdge]));
      appendLog(`${t("status.edgeAdded", "Edge added")}: ${connection.source} -> ${connection.target}`);
    },
    [appendLog, edges, nodes, setWorkflow, t, workflow]
  );

  const handleNodesDelete = useCallback(
    (deleted: Node[]) => {
      if (!workflow) {
        return;
      }
      const removedIds = new Set(
        deleted.map((node) => node.id).filter((id) => nodes.some((candidate) => candidate.node_id === id))
      );
      if (!removedIds.size) {
        return;
      }
      const nextNodes = nodes.filter((node) => !removedIds.has(node.node_id));
      const nextEdges = edges.filter((edge) => !removedIds.has(edge.source) && !removedIds.has(edge.target));
      setWorkflow(withUpdatedWorkflowGraph(workflow, nextNodes, nextEdges));
      appendLog(`${t("status.nodeDeleted", "Node deleted")}: ${[...removedIds].join(", ")}`);
    },
    [appendLog, edges, nodes, setWorkflow, t, workflow]
  );

  const handleAddNode = useCallback(
    (type: NodeType) => {
      if (!workflow) {
        appendLog(t("error.noWorkflow"), "warn");
        return;
      }
      const category =
        type === "input"
          ? "source"
          : type === "output" || type === "export"
            ? "sink"
            : type === "layer_container"
              ? "container"
              : "processing";
      const newNode = {
        node_id: `nd_${type}_${Date.now()}`,
        type,
        category,
        title_key: `node.type.${type}`,
        title_fallback: type,
        position: { x: 160, y: -160 },
        lock_level: "editable",
        locale: null,
        data: {},
        ports: {
          inputs: [{ port_id: "p_in", name: "in", direction: "in" }],
          outputs: [{ port_id: "p_out", name: "out", direction: "out" }]
        },
        validation: null
      } as unknown as WorkflowNode;
      setWorkflow(withUpdatedWorkflowGraph(workflow, [...nodes, newNode], edges));
      appendLog(`${t("status.nodeAdded", "Node added")}: ${type}`);
    },
    [appendLog, edges, nodes, setWorkflow, t, workflow]
  );

  const rightDockLayer = workspaceMode === "right" ? selectedLayer : null;
  const splitLayer = workspaceMode === "split" ? selectedLayer : null;
  const outputDrawer = activeDrawer === "logs" || activeDrawer === "artifacts" || activeDrawer === "preview" ? activeDrawer : null;
  const toggleDrawer = useCallback(
    (drawer: DrawerId) => {
      setActiveDrawer((current) => (current === drawer ? null : drawer));
      if (drawer === "logs" || drawer === "artifacts" || drawer === "preview") {
        setBottomTab(drawer);
      }
    },
    []
  );

  return (
    <main className="canvas-shell">
      <header className="top-toolbar">
        <div className="brand">
          <div className="brand-copy">
            <strong>{t("app.title")}</strong>
            <span>{t("app.subtitle")}</span>
          </div>
          <div className="template-select">
            <span>{t("panel.templates")}</span>
            <select
              value={selectedTemplateType}
              onChange={(event) => {
                setSelectedTemplateType(event.target.value);
                handleTemplateClick(event.target.value);
              }}
            >
              {templateOptions.map((templateType) => (
                <option key={templateType} value={templateType}>
                  {t(`template.${templateType}`, templateType)}
                </option>
              ))}
            </select>
            <button
              type="button"
              className="template-load-button"
              onClick={() => handleTemplateClick(selectedTemplateType)}
              onTouchEnd={(event) => {
                event.preventDefault();
                handleTemplateClick(selectedTemplateType);
              }}
            >
              {t("toolbar.load")}
            </button>
          </div>
        </div>
        <div className="toolbar-actions">
          <div className="run-bar" aria-label="Export validate mock run">
            <button onClick={handleSave}>{t("toolbar.save")}</button>
            <button onClick={handleLoad}>{t("toolbar.load")}</button>
            <button onClick={handleValidate}>{t("toolbar.validate")}</button>
            <button onClick={handleMockRun}>{t("toolbar.mockRun")}</button>
            <button onClick={handleExportPreview}>{t("toolbar.exportPreview")}</button>
          </div>
          <label className="language-select">
            <span>{t("toolbar.language")}</span>
            <select value={language} onChange={(event) => setLanguage(event.target.value as Language)}>
              <option value="zh">中文</option>
              <option value="en">English</option>
            </select>
          </label>
          <span className={`api-pill ${apiReady ? "is-ready" : ""}`}>
            {apiReady ? t("toolbar.apiReady") : t("toolbar.apiUnknown")}
          </span>
          <input
            ref={fileInputRef}
            hidden
            type="file"
            accept="application/json,.json"
            onChange={(event) => handleFileSelected(event.target.files?.[0])}
          />
        </div>
      </header>

      <section className={`workspace-grid ${nodeLibraryCollapsed ? "is-library-collapsed" : ""}`}>
        <aside className={`panel left-panel ${nodeLibraryCollapsed ? "is-collapsed" : ""}`}>
          <button className="library-toggle" onClick={() => setNodeLibraryCollapsed((collapsed) => !collapsed)}>
            {nodeLibraryCollapsed ? ">" : "<"}
          </button>
          <section className="panel-section">
            <div className="section-title">
              <h2>{nodeLibraryCollapsed ? t("panel.nodeLibrary").slice(0, 1) : t("panel.nodeLibrary")}</h2>
              <span>{libraryNodeTypes.length}</span>
            </div>
            {nodeLibraryCollapsed ? (
              <div className="node-library mini">
                {libraryNodeTypes.map((type) => (
                  <div
                    key={type}
                    role="button"
                    tabIndex={0}
                    className={`library-item node-kind-${type}`}
                    title={getNodeTypeLabel(type, t)}
                    onClick={() => handleAddNode(type)}
                    onKeyDown={(event) => {
                      if (event.key === "Enter" || event.key === " ") {
                        event.preventDefault();
                        handleAddNode(type);
                      }
                    }}
                  >
                    <span>{collapsedNodeLabels[type][language]}</span>
                  </div>
                ))}
              </div>
            ) : (
              <div className="node-library">
                {libraryNodeTypes.map((type) => (
                  <div
                    key={type}
                    role="button"
                    tabIndex={0}
                    className={`library-item node-kind-${type}`}
                    onClick={() => handleAddNode(type)}
                    onKeyDown={(event) => {
                      if (event.key === "Enter" || event.key === " ") {
                        event.preventDefault();
                        handleAddNode(type);
                      }
                    }}
                  >
                    <span>{getNodeTypeLabel(type, t)}</span>
                    <small>{type}</small>
                  </div>
                ))}
              </div>
            )}
          </section>
        </aside>

        <section className="canvas-panel" aria-label={t("panel.canvas")}>
          {workflow ? (
            <>
              <WorkspaceTabs
                layers={layerById}
                tabs={workspaceTabs}
                activeId={activeWorkspaceId}
                mode={workspaceMode}
                moduleTabs={moduleTabItems}
                activeModuleId={activeModuleTabId}
                t={t}
                onSelect={(id) => {
                  setActiveWorkspaceId(id);
                  setActiveLayerId(id);
                  setSelectedNode(id);
                  setActiveModuleTabId(null);
                }}
                onClose={closeWorkspaceTab}
                onReturnToMain={() => setActiveModuleTabId(null)}
                onSelectModule={setActiveModuleTabId}
                onCloseModule={closeModuleTab}
                onReorderModule={reorderModuleTab}
                onPinModule={pinModuleTab}
              />
              <div className={`canvas-stage ${splitLayer ? "is-split" : ""}`}>
                <div className="flow-stage">
                  <ReactFlow
                    nodes={flowNodes}
                    edges={flowEdges}
                    nodeTypes={nodeTypes}
                    fitView
                    minZoom={0.2}
                    maxZoom={1.6}
                    onNodesChange={handleNodesChange}
                    onEdgesChange={handleEdgesChange}
                    onConnect={handleConnect}
                    onNodesDelete={handleNodesDelete}
                    onNodeClick={handleNodeClick}
                    onNodeDoubleClick={handleNodeDoubleClick}
                    onPaneClick={handlePaneClick}
                    onNodeDragStop={handleNodeDragStop}
                  >
                    <Background color="#3a3a3a" gap={24} />
                    <Controls />
                    <MiniMap pannable zoomable />
                  </ReactFlow>
                </div>
                {splitLayer ? (
                  <LayerWorkspacePanel
                    layer={splitLayer}
                    edges={edges}
                    t={t}
                    mode="split"
                    onOpen={openLayerWorkspace}
                    onSelectNode={handleChildModuleSelect}
                    onPreviewNode={handleChildModulePreview}
                  />
                ) : null}
                {activeModuleNode ? (
                  <ModuleCanvasPanel
                    key={activeModuleNode.node_id}
                    moduleNode={activeModuleNode}
                    initialSubnodes={activeModuleSubnodes}
                    language={language}
                    t={t}
                    onClose={() => closeModuleTab(activeModuleNode.node_id)}
                  />
                ) : null}
              </div>
              {floatingLayerIds.map((id, index) => {
                const layer = layerById.get(id);
                if (!layer) {
                  return null;
                }
                return (
                  <FloatingWorkspace
                    key={id}
                    index={index}
                    layer={layer}
                    edges={edges}
                    t={t}
                    onClose={() => {
                      setFloatingLayerIds((ids) => ids.filter((layerId) => layerId !== id));
                      appendLog(`${t("status.workspaceClosed", "Workspace closed")}: ${id}`);
                    }}
                    onSelectNode={handleChildModuleSelect}
                    onPreviewNode={handleChildModulePreview}
                  />
                );
              })}
              {floatingNodeIds.map((id, index) => {
                const node = nodes.find((candidate) => candidate.node_id === id);
                if (!node) {
                  return null;
                }
                return (
                  <FloatingNodeCanvas
                    key={id}
                    index={index + floatingLayerIds.length}
                    node={node}
                    nodes={nodes}
                    edges={edges}
                    t={t}
                    onClose={() => {
                      setFloatingNodeIds((ids) => ids.filter((nodeId) => nodeId !== id));
                      appendLog(`${t("status.workspaceClosed", "Workspace closed")}: ${id}`);
                    }}
                  />
                );
              })}
            </>
          ) : (
            <div className="empty-canvas">
              <h2>{t("panel.noWorkflow")}</h2>
              <button onClick={() => handleTemplateClick("persona_builder")} disabled={!apiReady}>
                {t("template.loadPersona")}
              </button>
            </div>
          )}
        </section>
      </section>

      <FloatingDock activeDrawer={activeDrawer} t={t} onToggle={toggleDrawer} />

      {activeDrawer === "layers" ? (
        <FloatingSidePanel
          title={t("panel.layerNavigator", "Layer Navigator")}
          meta={`${layerSummaries.length}/13`}
          onClose={() => setActiveDrawer(null)}
        >
          <LayerNavigator
            layers={layerSummaries}
            activeLayerId={activeLayer?.node.node_id ?? null}
            collapsedLayerIds={collapsedLayerIds}
            t={t}
            onOpen={openLayerWorkspace}
            onToggle={toggleLayerCollapsed}
          />
        </FloatingSidePanel>
      ) : null}

      {activeDrawer === "inspector" ? (
        <FloatingSidePanel
          title={t("panel.parameters")}
          meta={rightDockLayer ? t("workspace.right", "Right panel") : t("workspace.inspector", "Inspector")}
          onClose={() => setActiveDrawer(null)}
        >
          {rightDockLayer && (!selectedNode || selectedNode.type === "layer_container") ? (
            <LayerWorkspacePanel
              layer={rightDockLayer}
              edges={edges}
              t={t}
              mode="right"
              onOpen={openLayerWorkspace}
              onSelectNode={handleChildModuleSelect}
              onPreviewNode={handleChildModulePreview}
            />
          ) : (
            <ParameterPanel
              node={selectedNode}
              displayLabel={selectedNode ? layerById.get(selectedNode.node_id)?.displayLabel : undefined}
              workflow={workflow}
              t={t}
            />
          )}
        </FloatingSidePanel>
      ) : null}

      {outputDrawer ? (
        <FloatingBottomPanel
          activeTab={bottomTab}
          t={t}
          onTab={(tab) => {
            setBottomTab(tab);
            setActiveDrawer(tab);
          }}
          onClose={() => setActiveDrawer(null)}
        >
          {bottomTab === "logs" ? <LogsPanel logs={logs} validation={validation} emptyText={t("panel.noLogs")} /> : null}
          {bottomTab === "artifacts" ? (
            <JsonPanel value={artifacts.length ? artifacts : null} emptyText={t("panel.noArtifacts")} />
          ) : null}
          {bottomTab === "preview" ? <JsonPanel value={exportPreview} emptyText={t("panel.noPreview")} /> : null}
        </FloatingBottomPanel>
      ) : null}
    </main>
  );
}

function FloatingDock({
  activeDrawer,
  t,
  onToggle
}: {
  activeDrawer: DrawerId | null;
  t: (key: string, fallback?: string) => string;
  onToggle: (drawer: DrawerId) => void;
}) {
  const dockItems: { id: DrawerId; label: string }[] = [
    { id: "layers", label: t("panel.layerNavigator", "Layers") },
    { id: "inspector", label: t("workspace.inspector", "Inspector") },
    { id: "logs", label: t("panel.logs") },
    { id: "artifacts", label: t("panel.artifacts") },
    { id: "preview", label: t("panel.exportPreview") }
  ];
  const dockIcons: Record<DrawerId, string> = {
    layers: "L",
    inspector: "I",
    logs: "R",
    artifacts: "A",
    preview: "P"
  };
  const [dockOffset, setDockOffset] = useState({ x: 0, y: 0 });
  const suppressClickRef = useRef(false);

  const handleDockMouseDown = useCallback(
    (event: ReactMouseEvent<HTMLElement>) => {
      if (event.button !== 0) {
        return;
      }
      const startX = event.clientX;
      const startY = event.clientY;
      const startOffset = dockOffset;
      suppressClickRef.current = false;

      const handleMouseMove = (moveEvent: MouseEvent) => {
        const x = moveEvent.clientX - startX;
        const y = moveEvent.clientY - startY;
        if (Math.abs(x) + Math.abs(y) > 3) {
          suppressClickRef.current = true;
        }
        setDockOffset({ x: startOffset.x + x, y: startOffset.y + y });
      };
      const handleMouseUp = () => {
        window.removeEventListener("mousemove", handleMouseMove);
        window.removeEventListener("mouseup", handleMouseUp);
        window.setTimeout(() => {
          suppressClickRef.current = false;
        }, 0);
      };

      window.addEventListener("mousemove", handleMouseMove);
      window.addEventListener("mouseup", handleMouseUp);
    },
    [dockOffset]
  );

  return (
    <nav
      className="floating-dock"
      style={{ transform: `translate(${dockOffset.x}px, ${dockOffset.y}px)` }}
      aria-label="Floating workspace dock"
      onMouseDown={handleDockMouseDown}
    >
      {dockItems.map((item) => (
        <button
          key={item.id}
          className={activeDrawer === item.id ? "is-active" : ""}
          title={item.label}
          aria-label={item.label}
          onClick={() => {
            if (!suppressClickRef.current) {
              onToggle(item.id);
            }
          }}
        >
          <span aria-hidden="true">{dockIcons[item.id]}</span>
        </button>
      ))}
    </nav>
  );
}

function FloatingSidePanel({
  title,
  meta,
  children,
  onClose
}: {
  title: string;
  meta?: string;
  children: ReactNode;
  onClose: () => void;
}) {
  return (
    <aside className="floating-side-panel">
      <div className="floating-panel-header">
        <div>
          <h2>{title}</h2>
          {meta ? <span>{meta}</span> : null}
        </div>
        <button onClick={onClose}>x</button>
      </div>
      <div className="floating-panel-body">{children}</div>
    </aside>
  );
}

function FloatingBottomPanel({
  activeTab,
  t,
  children,
  onTab,
  onClose
}: {
  activeTab: BottomTab;
  t: (key: string, fallback?: string) => string;
  children: ReactNode;
  onTab: (tab: BottomTab) => void;
  onClose: () => void;
}) {
  const tabs: { id: BottomTab; label: string }[] = [
    { id: "logs", label: t("panel.logs") },
    { id: "artifacts", label: t("panel.artifacts") },
    { id: "preview", label: t("panel.exportPreview") }
  ];

  return (
    <section className="floating-bottom-panel">
      <div className="bottom-tabs">
        {tabs.map((tab) => (
          <button key={tab.id} className={activeTab === tab.id ? "is-active" : ""} onClick={() => onTab(tab.id)}>
            {tab.label}
          </button>
        ))}
        <button className="drawer-close" onClick={onClose}>
          x
        </button>
      </div>
      <div className="bottom-drawer-body">{children}</div>
    </section>
  );
}

function LayerNavigator({
  layers,
  activeLayerId,
  collapsedLayerIds,
  t,
  onOpen,
  onToggle
}: {
  layers: LayerSummary[];
  activeLayerId: string | null;
  collapsedLayerIds: Set<string>;
  t: (key: string, fallback?: string) => string;
  onOpen: (layer: LayerSummary, mode: WorkspaceMode) => void;
  onToggle: (layer: LayerSummary) => void;
}) {
  if (!layers.length) {
    return <div className="empty-panel">{t("panel.noLayers", "No backend layers loaded")}</div>;
  }

  return (
    <div className="layer-navigator">
      {layers.map((layer, position) => {
        const label = layer.displayLabel;
        const collapsed = collapsedLayerIds.has(layer.node.node_id);
        const previousLayer = layers[position - 1];
        const showGroup = !previousLayer || previousLayer.groupLabel !== layer.groupLabel;
        return (
          <div key={layer.node.node_id} className="layer-nav-section">
            {showGroup ? <div className="layer-group-header">{layer.groupLabel}</div> : null}
          <article
            className={`layer-nav-item tier-${layer.tier} status-${layer.status} ${activeLayerId === layer.node.node_id ? "is-active" : ""}`}
          >
            <button className="layer-nav-main" onClick={() => onOpen(layer, "inline")}>
              <span className="layer-index">{String(layer.displayIndex).padStart(2, "0")}</span>
              <span className="layer-name">{label}</span>
              <span className="layer-status">{layer.status}</span>
            </button>
            <div className="layer-nav-meta">
              <span>{layer.tier}</span>
              <span>{layer.childNodes.length} nodes</span>
              <span>{t(`lock.${layer.node.lock_level}`, layer.node.lock_level)}</span>
            </div>
            <div className="layer-nav-actions" aria-label={`${label} workspace actions`}>
              <button onClick={() => onToggle(layer)}>{collapsed ? "+" : "-"}</button>
              <button onClick={() => onOpen(layer, "right")}>{t("workspace.rightShort", "Right")}</button>
              <button onClick={() => onOpen(layer, "split")}>{t("workspace.splitShort", "Split")}</button>
              <button onClick={() => onOpen(layer, "window")}>{t("workspace.windowShort", "Pop")}</button>
            </div>
          </article>
          </div>
        );
      })}
    </div>
  );
}

function WorkspaceTabs({
  layers,
  tabs,
  activeId,
  mode,
  moduleTabs,
  activeModuleId,
  t,
  onSelect,
  onClose,
  onReturnToMain,
  onSelectModule,
  onCloseModule,
  onReorderModule,
  onPinModule
}: {
  layers: Map<string, LayerSummary>;
  tabs: string[];
  activeId: string | null;
  mode: WorkspaceMode;
  moduleTabs: { id: string; label: string }[];
  activeModuleId: string | null;
  t: (key: string, fallback?: string) => string;
  onSelect: (id: string) => void;
  onClose: (id: string) => void;
  onReturnToMain: () => void;
  onSelectModule: (id: string) => void;
  onCloseModule: (id: string) => void;
  onReorderModule: (fromId: string, toId: string) => void;
  onPinModule: (id: string) => void;
}) {
  const [dragModuleId, setDragModuleId] = useState<string | null>(null);
  return (
    <div className="workspace-tabs">
      <button
        type="button"
        className={`breadcrumb breadcrumb-home ${activeModuleId ? "" : "is-active"}`}
        onClick={onReturnToMain}
        title={t("workspace.backToCanvas", "Back to main canvas")}
      >
        <span>{t("field.workflow")}</span>
        <span>/</span>
        <strong>{activeId ? layers.get(activeId)?.displayLabel ?? "Pipeline" : "Pipeline"}</strong>
      </button>
      <div className="tab-strip">
        {tabs.map((id) => {
          const layer = layers.get(id);
          if (!layer) {
            return null;
          }
          return (
            <button key={id} className={activeId === id ? "is-active" : ""} onClick={() => onSelect(id)}>
              L{layer.displayIndex}
              <span>{layer.displayLabel}</span>
              <small>{mode}</small>
              <b
                role="button"
                tabIndex={0}
                onClick={(event) => {
                  event.stopPropagation();
                  onClose(id);
                }}
                onKeyDown={(event) => {
                  if (event.key === "Enter" || event.key === " ") {
                    event.preventDefault();
                    onClose(id);
                  }
                }}
              >
                x
              </b>
            </button>
          );
        })}
        {moduleTabs.map((moduleTab) => (
          <button
            key={moduleTab.id}
            className={`is-module ${activeModuleId === moduleTab.id ? "is-active" : ""} ${dragModuleId === moduleTab.id ? "is-dragging" : ""}`}
            draggable
            onClick={() => onSelectModule(moduleTab.id)}
            onDragStart={() => setDragModuleId(moduleTab.id)}
            onDragEnd={() => setDragModuleId(null)}
            onDragOver={(event) => event.preventDefault()}
            onDrop={(event) => {
              event.preventDefault();
              if (dragModuleId && dragModuleId !== moduleTab.id) {
                onReorderModule(dragModuleId, moduleTab.id);
              }
              setDragModuleId(null);
            }}
          >
            <i
              role="button"
              tabIndex={0}
              className="module-tab-pin"
              title={t("workspace.modulePin", "Pin to left")}
              onClick={(event) => {
                event.stopPropagation();
                onPinModule(moduleTab.id);
              }}
              onKeyDown={(event) => {
                if (event.key === "Enter" || event.key === " ") {
                  event.preventDefault();
                  onPinModule(moduleTab.id);
                }
              }}
            >
              ⤒
            </i>
            <span>{moduleTab.label}</span>
            <small>{t("workspace.moduleTab", "module")}</small>
            <b
              role="button"
              tabIndex={0}
              onMouseDown={(event) => {
                event.preventDefault();
                event.stopPropagation();
              }}
              onClick={(event) => {
                event.preventDefault();
                event.stopPropagation();
                onCloseModule(moduleTab.id);
              }}
              onKeyDown={(event) => {
                if (event.key === "Enter" || event.key === " ") {
                  event.preventDefault();
                  onCloseModule(moduleTab.id);
                }
              }}
            >
              x
            </b>
          </button>
        ))}
      </div>
    </div>
  );
}

function LayerWorkspacePanel({
  layer,
  edges,
  t,
  mode,
  onOpen,
  onSelectNode,
  onPreviewNode
}: {
  layer: LayerSummary;
  edges: EdgeLike[];
  t: (key: string, fallback?: string) => string;
  mode: WorkspaceMode;
  onOpen: (layer: LayerSummary, mode: WorkspaceMode) => void;
  onSelectNode: (node: WorkflowNode) => void;
  onPreviewNode: (node: WorkflowNode) => void;
}) {
  const [collapsed, setCollapsed] = useState(false);
  const label = layer.displayLabel;
  const parameterCount = Object.keys(layer.node.data ?? {}).length;

  return (
    <section className={`layer-workspace mode-${mode} tier-${layer.tier}`}>
      <div className="workspace-header">
        <div className="folder-group-title">
          <span className="folder-icon" aria-hidden="true">
            ::
          </span>
          <div>
          <p>{t("workspace.breadcrumb", "Workflow / Layer / Folder")}</p>
          <h3>
            L{layer.displayIndex} {label}
            <span className="module-count-badge">{layer.childNodes.length} modules</span>
          </h3>
          </div>
        </div>
        <div className="workspace-actions">
          <button onClick={() => setCollapsed((value) => !value)}>{collapsed ? "+" : "-"}</button>
          <button onClick={() => onOpen(layer, "right")}>{t("workspace.rightShort", "Right")}</button>
          <button onClick={() => onOpen(layer, "split")}>{t("workspace.splitShort", "Split")}</button>
          <button onClick={() => onOpen(layer, "window")}>{t("workspace.window", "New window")}</button>
        </div>
      </div>
      <div className="folder-group-meta">
        <span>{t("field.status")}: {layer.status}</span>
        <span>Tier: {layer.tier}</span>
        <span>{t("field.data")}: {parameterCount}</span>
        <span>{t("field.childrenCount")}: {layer.childNodes.length}</span>
      </div>
      {!collapsed ? (
        <div className="submodule-rail">
          {layer.childNodes.length ? (
            layer.childNodes.slice(0, 6).map((node) => {
              const moduleTier = dataString(node, "module_tier", layer.tier);
              return (
                <button
                  key={node.node_id}
                  className={`submodule-card tier-${moduleTier}`}
                  onClick={() => onSelectNode(node)}
                  onDoubleClick={() => onPreviewNode(node)}
                  onTouchEnd={(event) => {
                    event.preventDefault();
                    onSelectNode(node);
                  }}
                >
                  <span className="submodule-name">{t(node.title_key, node.title_fallback)}</span>
                  <span className="submodule-tier">{moduleTier}</span>
                </button>
              );
            })
          ) : (
            <div className="empty-node-canvas">0 modules</div>
          )}
        </div>
      ) : (
        <div className="folder-collapsed">{t("workspace.emptyFolder", "empty folder layer")}</div>
      )}
    </section>
  );
}

function FloatingNodeCanvas({
  index,
  node,
  nodes,
  edges,
  t,
  onClose
}: {
  index: number;
  node: WorkflowNode;
  nodes: WorkflowNode[];
  edges: EdgeLike[];
  t: (key: string, fallback?: string) => string;
  onClose: () => void;
}) {
  const neighborIds = new Set<string>([node.node_id]);
  for (const edge of edges) {
    if (edge.source === node.node_id) {
      neighborIds.add(edge.target);
    }
    if (edge.target === node.node_id) {
      neighborIds.add(edge.source);
    }
  }
  const previewNodes = nodes.filter((candidate) => neighborIds.has(candidate.node_id));
  const previewNodeIds = new Set(previewNodes.map((candidate) => candidate.node_id));
  const previewEdges = edges.filter((edge) => previewNodeIds.has(edge.source) && previewNodeIds.has(edge.target));
  const base = node.position ?? { x: 0, y: 0 };
  const flowPreviewNodes = previewNodes.map((candidate) => makeFlowNode(candidate, { x: base.x - 160, y: base.y - 90 }));
  const flowPreviewEdges = previewEdges.map((edge) => ({
    id: edge.edge_id,
    source: edge.source,
    target: edge.target,
    sourceHandle: edge.source_port,
    targetHandle: edge.target_port,
    type: "smoothstep"
  }));

  return (
    <div className="floating-workspace node-preview" style={{ transform: `translate(${index * 22}px, ${index * 18}px)` }}>
      <div className="floating-titlebar">
        <strong>{t(node.title_key, node.title_fallback)}</strong>
        <button onClick={onClose}>x</button>
      </div>
      <div className="node-canvas-shell">
        <div className="node-canvas-title">
          <span>{t("workspace.nodeCanvas", "Node canvas")}</span>
          <small>{getNodeTypeLabel(node.type, t)}</small>
        </div>
        {flowPreviewNodes.length ? (
          <ReactFlow
            nodes={flowPreviewNodes}
            edges={flowPreviewEdges}
            nodeTypes={nodeTypes}
            fitView
            minZoom={0.3}
            maxZoom={1.4}
            nodesDraggable={false}
            nodesConnectable={false}
            elementsSelectable={false}
          >
            <Background color="#383838" gap={18} />
            <Controls />
          </ReactFlow>
        ) : (
          <div className="empty-node-canvas">{t("workspace.noChildNodes", "No child nodes are present in backend data for this layer.")}</div>
        )}
      </div>
    </div>
  );
}

type EdgeLike = {
  edge_id: string;
  source: string;
  target: string;
  source_port?: string | null;
  target_port?: string | null;
};

function FloatingWorkspace({
  index,
  layer,
  edges,
  t,
  onClose,
  onSelectNode,
  onPreviewNode
}: {
  index: number;
  layer: LayerSummary;
  edges: EdgeLike[];
  t: (key: string, fallback?: string) => string;
  onClose: () => void;
  onSelectNode: (node: WorkflowNode) => void;
  onPreviewNode: (node: WorkflowNode) => void;
}) {
  return (
    <div className="floating-workspace" style={{ transform: `translate(${index * 22}px, ${index * 18}px)` }}>
      <div className="floating-titlebar">
        <strong>
          L{layer.displayIndex} {layer.displayLabel}
        </strong>
        <button onClick={onClose}>x</button>
      </div>
      <LayerWorkspacePanel
        layer={layer}
        edges={edges}
        t={t}
        mode="window"
        onOpen={() => undefined}
        onSelectNode={onSelectNode}
        onPreviewNode={onPreviewNode}
      />
    </div>
  );
}

// Ensure a node exposes at least one in/out port so WorkflowNodeCard renders
// connectable handles inside the module canvas (handles use ids p_in / p_out).
function ensurePorts(node: WorkflowNode): WorkflowNode {
  const inputs = node.ports?.inputs?.length ? node.ports.inputs : [{ port_id: "p_in" }];
  const outputs = node.ports?.outputs?.length ? node.ports.outputs : [{ port_id: "p_out" }];
  return { ...node, ports: { ...(node.ports ?? {}), inputs, outputs } } as unknown as WorkflowNode;
}

// Embedded, in-app module sub-canvas. Module-scoped state only: it owns its own
// ReactFlow nodes/edges (useNodesState/useEdgesState) and never touches the canvas
// store, so it does not render or mutate the 13-layer workflow. Unmounting on close
// destroys all of its state.
function ModuleCanvasPanel({
  moduleNode,
  initialSubnodes,
  language,
  t,
  onClose
}: {
  moduleNode: WorkflowNode;
  initialSubnodes: WorkflowNode[];
  language: Language;
  t: (key: string, fallback?: string) => string;
  onClose: () => void;
}) {
  const title = translate(language, moduleNode.title_key, moduleNode.title_fallback);

  // Restore this module's sub-canvas from localStorage if it was edited before;
  // otherwise seed it from the module node + its subnodes.
  const initialGraph = useMemo<{ nodes: Node[]; edges: Edge[] }>(() => {
    const snapshot = loadModuleCanvas(moduleNode.node_id);
    if (snapshot) {
      return { nodes: snapshot.nodes as Node[], edges: snapshot.edges as Edge[] };
    }
    const seeds = [moduleNode, ...initialSubnodes];
    return {
      nodes: seeds.map((node, index) => ({
        id: node.node_id,
        type: "workflowNode",
        position:
          node.position && (node.position.x || node.position.y) ? node.position : { x: 120, y: 70 + index * 130 },
        data: { schemaNode: ensurePorts(node) }
      })),
      edges: []
    };
  }, [moduleNode, initialSubnodes]);

  const [moduleNodes, , onModuleNodesChange] = useNodesState(initialGraph.nodes);
  const [moduleEdges, setModuleEdges, onModuleEdgesChange] = useEdgesState<Edge>(initialGraph.edges);
  const [selectedId, setSelectedId] = useState<string>(moduleNode.node_id);
  const [executionResult, setExecutionResult] = useState<unknown>(null);
  const [executionError, setExecutionError] = useState<string | null>(null);
  const addedRef = useRef(0);

  // Persist every structural change (add / connect / move / data) for this module.
  useEffect(() => {
    saveModuleCanvas(moduleNode.node_id, { nodes: moduleNodes, edges: moduleEdges });
  }, [moduleNode.node_id, moduleNodes, moduleEdges]);

  const onConnect = useCallback(
    (connection: Connection) => setModuleEdges((eds) => addEdge({ ...connection, type: "smoothstep" }, eds)),
    [setModuleEdges]
  );

  const handleAddNode = useCallback(() => {
    addedRef.current += 1;
    const seq = addedRef.current;
    const id = `${moduleNode.node_id}_new_${seq}`;
    const schemaNode = ensurePorts({
      node_id: id,
      type: "transform",
      category: "processing",
      title_key: id,
      title_fallback: `Node ${seq}`,
      position: { x: 0, y: 0 },
      lock_level: "editable",
      locale: null,
      data: { parent_module: moduleNode.node_id, status: "draft" },
      ports: { inputs: [], outputs: [] },
      validation: null
    } as unknown as WorkflowNode);
    onModuleNodesChange([
      {
        type: "add",
        item: {
          id,
          type: "workflowNode",
          position: { x: 360, y: 80 + moduleNodes.length * 70 },
          data: { schemaNode }
        }
      }
    ]);
    setSelectedId(id);
  }, [moduleNode.node_id, moduleNodes.length, onModuleNodesChange]);

  const selectedSchema = useMemo(() => {
    const found = moduleNodes.find((node) => node.id === selectedId);
    return (found?.data as { schemaNode?: WorkflowNode } | undefined)?.schemaNode ?? null;
  }, [moduleNodes, selectedId]);

  const handleRunWorkflow = useCallback(() => {
    const rawInput = window.prompt("Workflow input", JSON.stringify({ input: "string" }, null, 2));
    if (rawInput === null) {
      return;
    }

    try {
      const parsed = JSON.parse(rawInput) as { input?: unknown };
      const executableNodes = moduleNodes
        .map((node) => (node.data as { schemaNode?: WorkflowNode }).schemaNode)
        .filter((node): node is WorkflowNode => Boolean(node && String(node.type) !== "module"));
      const executableNodeIds = new Set(executableNodes.map((node) => node.node_id));
      const executableEdges = moduleEdges
        .filter((edge) => executableNodeIds.has(edge.source) && executableNodeIds.has(edge.target))
        .map((edge) => ({
          edge_id: edge.id,
          source: edge.source,
          source_port: typeof edge.sourceHandle === "string" ? edge.sourceHandle : "p_out",
          target: edge.target,
          target_port: typeof edge.targetHandle === "string" ? edge.targetHandle : "p_in"
        })) as WorkflowEdge[];

      const result = executeWorkflow(
        {
          schema_version: "0.2.0",
          name: title,
          version: "1.0.0",
          template_type: "module_canvas",
          nodes: executableNodes,
          edges: executableEdges,
          metadata: {}
        } as Workflow,
        parsed.input
      );
      setExecutionResult(result);
      setExecutionError(null);
    } catch (error) {
      setExecutionResult(null);
      setExecutionError((error as Error).message);
    }
  }, [moduleEdges, moduleNodes, title]);

  return (
    <section className="module-canvas-panel">
      <header className="module-canvas-panel__bar">
        <div>
          <p>{t("workspace.moduleCanvas", "Module Canvas")}</p>
          <h3>{title}</h3>
          <span>{moduleNode.node_id}</span>
        </div>
        <div className="module-canvas-panel__actions">
          <button onClick={handleRunWorkflow}>Run Workflow</button>
          <button onClick={handleAddNode}>+ {t("workspace.addNode", "Add node")}</button>
          <button className="module-canvas-panel__close" onClick={onClose}>
            ✕
          </button>
        </div>
      </header>
      <div className="module-canvas-panel__body">
        <div className="module-canvas-panel__flow">
          <ReactFlow
            nodes={moduleNodes}
            edges={moduleEdges}
            nodeTypes={nodeTypes}
            fitView
            minZoom={0.3}
            maxZoom={1.6}
            onNodesChange={onModuleNodesChange}
            onEdgesChange={onModuleEdgesChange}
            onConnect={onConnect}
            onNodeClick={(_event, node) => setSelectedId(node.id)}
          >
            <Background color="#333" gap={20} />
            <Controls />
            <MiniMap pannable zoomable />
          </ReactFlow>
        </div>
        <aside className="module-canvas-panel__inspector">
          <h4>{t("panel.parameters", "Inspector")}</h4>
          {selectedSchema ? (
            <>
              {executionResult || executionError ? (
                <section className="module-canvas-panel__result">
                  <h4>persona_result</h4>
                  {executionError ? <pre>{executionError}</pre> : <pre>{JSON.stringify(executionResult, null, 2)}</pre>}
                </section>
              ) : null}
              <dl>
                <dt>{t("field.nodeId", "Node ID")}</dt>
                <dd>{selectedSchema.node_id}</dd>
                <dt>{t("field.type", "Type")}</dt>
                <dd>{selectedSchema.type}</dd>
                <dt>{t("field.lockLevel", "Lock")}</dt>
                <dd>{translate(language, `lock.${selectedSchema.lock_level}`, selectedSchema.lock_level)}</dd>
              </dl>
              <pre>{JSON.stringify(selectedSchema.data ?? {}, null, 2)}</pre>
            </>
          ) : (
            <div className="module-canvas-panel__empty">{t("panel.emptySelection", "Select a node")}</div>
          )}
        </aside>
      </div>
    </section>
  );
}

function ParameterPanel({
  node,
  displayLabel,
  workflow,
  t
}: {
  node: WorkflowNode | null;
  displayLabel?: string;
  workflow: Workflow | null;
  t: (key: string, fallback?: string) => string;
}) {
  if (!node) {
    return (
      <div className="empty-panel">
        <p>{t("panel.emptySelection")}</p>
        {workflow ? (
          <dl>
            <dt>{t("field.workflow")}</dt>
            <dd>{workflow.name}</dd>
            <dt>{t("field.template")}</dt>
            <dd>{workflow.template_type}</dd>
            <dt>Schema</dt>
            <dd>{workflow.schema_version}</dd>
          </dl>
        ) : null}
      </div>
    );
  }

  const position = node.position ?? { x: 0, y: 0 };

  return (
    <div className="parameter-content">
      <h3>{displayLabel ?? t(node.title_key, node.title_fallback)}</h3>
      <dl>
        <dt>{t("field.nodeId")}</dt>
        <dd>{node.node_id}</dd>
        <dt>{t("field.type")}</dt>
        <dd>{getNodeTypeLabel(node.type, t)}</dd>
        <dt>{t("field.category")}</dt>
        <dd>{node.category}</dd>
        <dt>{t("field.lockLevel")}</dt>
        <dd>{t(`lock.${node.lock_level}`, node.lock_level)}</dd>
        <dt>{t("field.position")}</dt>
        <dd>
          {Math.round(position.x)}, {Math.round(position.y)}
        </dd>
        <dt>{t("field.validation")}</dt>
        <dd>{node.validation?.status ?? "-"}</dd>
      </dl>
      <h4>{t("field.data")}</h4>
      <pre>{JSON.stringify(node.data ?? {}, null, 2)}</pre>
    </div>
  );
}

function LogsPanel({
  logs,
  validation,
  emptyText
}: {
  logs: { ts?: string; level: string; message: string }[];
  validation: unknown;
  emptyText: string;
}) {
  if (!logs.length && !validation) {
    return <div className="bottom-empty">{emptyText}</div>;
  }

  return (
    <div className="log-list">
      {logs.map((log, index) => (
        <div key={`${log.ts}-${index}`} className={`log-line log-${log.level}`}>
          <span>{log.ts ? new Date(log.ts).toLocaleTimeString() : "--:--:--"}</span>
          <strong>{log.level}</strong>
          <p>{log.message}</p>
        </div>
      ))}
      {validation ? <pre>{JSON.stringify(validation, null, 2)}</pre> : null}
    </div>
  );
}

function JsonPanel({ value, emptyText }: { value: unknown; emptyText: string }) {
  if (!value) {
    return <div className="bottom-empty">{emptyText}</div>;
  }

  return <pre className="json-panel">{JSON.stringify(value, null, 2)}</pre>;
}
