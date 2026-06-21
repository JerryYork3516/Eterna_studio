import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  Background,
  Controls,
  MiniMap,
  ReactFlow,
  type Edge,
  type EdgeChange,
  type Node,
  type NodeChange,
  type NodeMouseHandler,
  type OnNodeDrag
} from "@xyflow/react";
import { translate, type Language } from "@/i18n";
import { api } from "@/lib/api";
import type { Artifact, NodeType, Workflow, WorkflowNode } from "@/lib/schema-types";
import { downloadWorkflow, readWorkflowFile, withUpdatedWorkflowGraph } from "@/lib/workflow";
import { useCanvasStore } from "@/store/canvas-store";
import { LayerContainerNode } from "@/components/canvas/LayerContainerNode";
import { WorkflowNodeCard } from "@/components/canvas/WorkflowNodeCard";

const nodeTypes = {
  layerContainer: LayerContainerNode,
  workflowNode: WorkflowNodeCard
};

const libraryNodeTypes: NodeType[] = ["input", "transform", "model", "agent", "review", "output", "export"];

type BottomTab = "logs" | "artifacts" | "preview";
type WorkspaceMode = "inline" | "right" | "split" | "window";

type LayerSummary = {
  node: WorkflowNode;
  index: number;
  tier: string;
  status: string;
  childNodes: WorkflowNode[];
};

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

function makeFlowNode(schemaNode: WorkflowNode, offset?: { x: number; y: number }): Node {
  const position = schemaNode.position ?? { x: 0, y: 0 };
  return {
    id: schemaNode.node_id,
    type: schemaNode.type === "layer_container" ? "layerContainer" : "workflowNode",
    position: offset ? { x: position.x - offset.x, y: position.y - offset.y } : position,
    data: { schemaNode }
  };
}

export function CanvasShell() {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [bottomTab, setBottomTab] = useState<BottomTab>("logs");
  const [activeLayerId, setActiveLayerId] = useState<string | null>(null);
  const [workspaceTabs, setWorkspaceTabs] = useState<string[]>([]);
  const [activeWorkspaceId, setActiveWorkspaceId] = useState<string | null>(null);
  const [workspaceMode, setWorkspaceMode] = useState<WorkspaceMode>("inline");
  const [collapsedLayerIds, setCollapsedLayerIds] = useState<Set<string>>(() => new Set());
  const [floatingLayerIds, setFloatingLayerIds] = useState<string[]>([]);
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
  const selectedNode = useMemo(
    () => nodes.find((node) => node.node_id === selectedNodeId) ?? null,
    [nodes, selectedNodeId]
  );

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
      layerNodes.map((layer) => {
        const index = getLayerIndex(layer) ?? 0;
        const childNodes = nodes.filter(
          (node) => node.node_id !== layer.node_id && inferNodeLayerIndex(node, layerNodes) === index
        );
        return {
          node: layer,
          index,
          tier: dataString(layer, "module_tier", "core"),
          status: dataString(layer, "status", "empty"),
          childNodes
        };
      }),
    [layerNodes, nodes]
  );

  const layerById = useMemo(
    () => new Map(layerSummaries.map((layer) => [layer.node.node_id, layer])),
    [layerSummaries]
  );
  const selectedLayer = activeWorkspaceId ? layerById.get(activeWorkspaceId) ?? null : null;
  const activeLayer = activeLayerId ? layerById.get(activeLayerId) ?? null : selectedLayer;

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
  }, [activeLayerId, activeWorkspaceId, layerById]);

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

  const flowNodes = useMemo<Node[]>(
    () => nodes.filter((node) => visibleNodeIds.has(node.node_id)).map((schemaNode) => makeFlowNode(schemaNode)),
    [nodes, visibleNodeIds]
  );

  const flowEdges = useMemo<Edge[]>(
    () =>
      edges
        .filter((edge) => visibleNodeIds.has(edge.source) && visibleNodeIds.has(edge.target))
        .map((edge) => ({
          id: edge.edge_id,
          source: edge.source,
          target: edge.target,
          sourceHandle: edge.source_port,
          targetHandle: edge.target_port,
          type: "smoothstep"
        })),
    [edges, visibleNodeIds]
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
      if (mode === "window") {
        setFloatingLayerIds((ids) => (ids.includes(layer.node.node_id) ? ids : [...ids, layer.node.node_id]));
      }
      appendLog(`${t("status.layerOpened", "Layer opened")}: L${layer.index} / ${mode}`);
    },
    [appendLog, setSelectedNode, t]
  );

  const toggleLayerCollapsed = useCallback(
    (layer: LayerSummary) => {
      setCollapsedLayerIds((current) => {
        const next = new Set(current);
        if (next.has(layer.node.node_id)) {
          next.delete(layer.node.node_id);
          appendLog(`${t("status.layerExpanded", "Layer expanded")}: L${layer.index}`);
        } else {
          next.add(layer.node.node_id);
          appendLog(`${t("status.layerCollapsed", "Layer collapsed")}: L${layer.index}`);
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
      setSelectedNode(node.id);
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
          updateNodePosition(change.id, change.position);
        }
        if (change.type === "select" && change.selected) {
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
      updateNodePosition(node.id, node.position);
      appendLog(`${t("status.nodeMoved", "Node moved")}: ${node.id}`);
    },
    [appendLog, t, updateNodePosition]
  );

  const rightDockLayer = workspaceMode === "right" ? selectedLayer : null;
  const splitLayer = workspaceMode === "split" ? selectedLayer : null;
  const inlineLayer = workspaceMode === "inline" ? selectedLayer : null;

  return (
    <main className="canvas-shell">
      <header className="top-toolbar">
        <div className="brand">
          <strong>{t("app.title")}</strong>
          <span>{t("app.subtitle")}</span>
        </div>
        <div className="run-bar" aria-label="Export validate mock run">
          <button onClick={handleSave}>{t("toolbar.save")}</button>
          <button onClick={handleLoad}>{t("toolbar.load")}</button>
          <button onClick={handleValidate}>{t("toolbar.validate")}</button>
          <button onClick={handleMockRun}>{t("toolbar.mockRun")}</button>
          <button onClick={handleExportPreview}>{t("toolbar.exportPreview")}</button>
        </div>
        <div className="toolbar-actions">
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

      <section className="workspace-grid">
        <aside className="panel left-panel">
          <section className="panel-section">
            <div className="section-title">
              <h2>{t("panel.nodeLibrary")}</h2>
              <span>{libraryNodeTypes.length}</span>
            </div>
            <div className="node-library">
              {libraryNodeTypes.map((type) => (
                <div key={type} className={`library-item node-kind-${type}`}>
                  <span>{t(`node.type.${type}`, type)}</span>
                  <small>{type}</small>
                </div>
              ))}
            </div>
          </section>

          <section className="panel-section">
            <div className="section-title">
              <h2>{t("panel.layerNavigator", "Layer Navigator")}</h2>
              <span>{layerSummaries.length}/13</span>
            </div>
            <LayerNavigator
              layers={layerSummaries}
              activeLayerId={activeLayer?.node.node_id ?? null}
              collapsedLayerIds={collapsedLayerIds}
              t={t}
              onOpen={openLayerWorkspace}
              onToggle={toggleLayerCollapsed}
            />
          </section>

          <section className="panel-section">
            <div className="section-title">
              <h2>{t("panel.templates")}</h2>
            </div>
            <div className="template-list">
              {templates.map((template) => (
                <button
                  key={template.template_type}
                  className={workflow?.template_type === template.template_type ? "is-active" : ""}
                  onClick={() => handleTemplateClick(template.template_type)}
                  disabled={!apiReady && template.template_type === "persona_builder"}
                >
                  {t(`template.${template.template_type}`, template.name)}
                </button>
              ))}
            </div>
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
                t={t}
                onSelect={(id) => {
                  setActiveWorkspaceId(id);
                  setActiveLayerId(id);
                  setSelectedNode(id);
                }}
                onClose={closeWorkspaceTab}
              />
              <div className={`canvas-stage ${splitLayer ? "is-split" : ""} ${inlineLayer ? "has-inline-workspace" : ""}`}>
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
                    onNodeClick={handleNodeClick}
                    onPaneClick={handlePaneClick}
                    onNodeDragStop={handleNodeDragStop}
                  >
                    <Background color="#314158" gap={24} />
                    <Controls />
                    <MiniMap pannable zoomable />
                  </ReactFlow>
                </div>
                {splitLayer ? (
                  <LayerWorkspacePanel layer={splitLayer} edges={edges} t={t} mode="split" onOpen={openLayerWorkspace} />
                ) : null}
                {inlineLayer ? (
                  <LayerWorkspacePanel layer={inlineLayer} edges={edges} t={t} mode="inline" onOpen={openLayerWorkspace} />
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

        <aside className="panel right-panel">
          <div className="section-title">
            <h2>{t("panel.parameters")}</h2>
            <span>{rightDockLayer ? t("workspace.right", "Right panel") : t("workspace.inspector", "Inspector")}</span>
          </div>
          {rightDockLayer ? (
            <LayerWorkspacePanel layer={rightDockLayer} edges={edges} t={t} mode="right" onOpen={openLayerWorkspace} />
          ) : (
            <ParameterPanel node={selectedNode} workflow={workflow} t={t} />
          )}
        </aside>
      </section>

      <section className="bottom-panel">
        <div className="bottom-tabs">
          <button className={bottomTab === "logs" ? "is-active" : ""} onClick={() => setBottomTab("logs")}>
            {t("panel.logs")}
          </button>
          <button className={bottomTab === "artifacts" ? "is-active" : ""} onClick={() => setBottomTab("artifacts")}>
            {t("panel.artifacts")}
          </button>
          <button className={bottomTab === "preview" ? "is-active" : ""} onClick={() => setBottomTab("preview")}>
            {t("panel.exportPreview")}
          </button>
        </div>
        {bottomTab === "logs" ? <LogsPanel logs={logs} validation={validation} emptyText={t("panel.noLogs")} /> : null}
        {bottomTab === "artifacts" ? (
          <JsonPanel value={artifacts.length ? artifacts : null} emptyText={t("panel.noArtifacts")} />
        ) : null}
        {bottomTab === "preview" ? <JsonPanel value={exportPreview} emptyText={t("panel.noPreview")} /> : null}
      </section>
    </main>
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
      {layers.map((layer) => {
        const label = t(layer.node.title_key, layer.node.title_fallback);
        const collapsed = collapsedLayerIds.has(layer.node.node_id);
        return (
          <article
            key={layer.node.node_id}
            className={`layer-nav-item tier-${layer.tier} status-${layer.status} ${activeLayerId === layer.node.node_id ? "is-active" : ""}`}
          >
            <button className="layer-nav-main" onClick={() => onOpen(layer, "inline")}>
              <span className="layer-index">{String(layer.index).padStart(2, "0")}</span>
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
  t,
  onSelect,
  onClose
}: {
  layers: Map<string, LayerSummary>;
  tabs: string[];
  activeId: string | null;
  mode: WorkspaceMode;
  t: (key: string, fallback?: string) => string;
  onSelect: (id: string) => void;
  onClose: (id: string) => void;
}) {
  return (
    <div className="workspace-tabs">
      <div className="breadcrumb">
        <span>{t("field.workflow")}</span>
        <span>/</span>
        <strong>{activeId ? t(layers.get(activeId)?.node.title_key ?? "", layers.get(activeId)?.node.title_fallback) : "Pipeline"}</strong>
      </div>
      <div className="tab-strip">
        {tabs.map((id) => {
          const layer = layers.get(id);
          if (!layer) {
            return null;
          }
          return (
            <button key={id} className={activeId === id ? "is-active" : ""} onClick={() => onSelect(id)}>
              L{layer.index}
              <span>{t(layer.node.title_key, layer.node.title_fallback)}</span>
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
      </div>
    </div>
  );
}

function LayerWorkspacePanel({
  layer,
  edges,
  t,
  mode,
  onOpen
}: {
  layer: LayerSummary;
  edges: EdgeLike[];
  t: (key: string, fallback?: string) => string;
  mode: WorkspaceMode;
  onOpen: (layer: LayerSummary, mode: WorkspaceMode) => void;
}) {
  const label = t(layer.node.title_key, layer.node.title_fallback);
  const childIds = new Set(layer.childNodes.map((node) => node.node_id));
  const childOffset = layer.node.position ?? { x: 0, y: 0 };
  const childFlowNodes = layer.childNodes.map((node) => makeFlowNode(node, { x: childOffset.x - 40, y: childOffset.y - 40 }));
  const childFlowEdges = edges
    .filter((edge) => childIds.has(edge.source) && childIds.has(edge.target))
    .map((edge) => ({
      id: edge.edge_id,
      source: edge.source,
      target: edge.target,
      sourceHandle: edge.source_port,
      targetHandle: edge.target_port,
      type: "smoothstep"
    }));

  return (
    <section className={`layer-workspace mode-${mode}`}>
      <div className="workspace-header">
        <div>
          <p>{t("workspace.breadcrumb", "Workflow / Layer / Folder")}</p>
          <h3>
            L{layer.index} {label}
          </h3>
        </div>
        <div className="workspace-actions">
          <button onClick={() => onOpen(layer, "inline")}>{t("workspace.inline", "Inline")}</button>
          <button onClick={() => onOpen(layer, "right")}>{t("workspace.right", "Right panel")}</button>
          <button onClick={() => onOpen(layer, "split")}>{t("workspace.split", "Split view")}</button>
          <button onClick={() => onOpen(layer, "window")}>{t("workspace.window", "New window")}</button>
        </div>
      </div>
      <div className="folder-layer">
        <div className="folder-card">
          <span>{t("field.status")}</span>
          <strong>{layer.status}</strong>
        </div>
        <div className="folder-card">
          <span>Tier</span>
          <strong>{layer.tier}</strong>
        </div>
        <div className="folder-card">
          <span>{t("field.childrenCount")}</span>
          <strong>{layer.childNodes.length}</strong>
        </div>
        <div className="folder-card">
          <span>{t("field.lockLevel")}</span>
          <strong>{t(`lock.${layer.node.lock_level}`, layer.node.lock_level)}</strong>
        </div>
      </div>
      <div className="node-canvas-shell">
        <div className="node-canvas-title">
          <span>{t("workspace.nodeCanvas", "Node canvas")}</span>
          <small>{layer.childNodes.length ? t("workspace.backendNodes", "backend nodes") : t("workspace.emptyFolder", "empty folder layer")}</small>
        </div>
        {layer.childNodes.length ? (
          <ReactFlow
            nodes={childFlowNodes}
            edges={childFlowEdges}
            nodeTypes={nodeTypes}
            fitView
            minZoom={0.3}
            maxZoom={1.4}
            nodesDraggable={false}
            nodesConnectable={false}
            elementsSelectable={false}
          >
            <Background color="#243247" gap={18} />
            <Controls />
          </ReactFlow>
        ) : (
          <div className="empty-node-canvas">{t("workspace.noChildNodes", "No child nodes are present in backend data for this layer.")}</div>
        )}
      </div>
    </section>
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
  onClose
}: {
  index: number;
  layer: LayerSummary;
  edges: EdgeLike[];
  t: (key: string, fallback?: string) => string;
  onClose: () => void;
}) {
  return (
    <div className="floating-workspace" style={{ transform: `translate(${index * 22}px, ${index * 18}px)` }}>
      <div className="floating-titlebar">
        <strong>
          L{layer.index} {t(layer.node.title_key, layer.node.title_fallback)}
        </strong>
        <button onClick={onClose}>x</button>
      </div>
      <LayerWorkspacePanel layer={layer} edges={edges} t={t} mode="window" onOpen={() => undefined} />
    </div>
  );
}

function ParameterPanel({
  node,
  workflow,
  t
}: {
  node: WorkflowNode | null;
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
      <h3>{t(node.title_key, node.title_fallback)}</h3>
      <dl>
        <dt>{t("field.nodeId")}</dt>
        <dd>{node.node_id}</dd>
        <dt>{t("field.type")}</dt>
        <dd>{node.type}</dd>
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
