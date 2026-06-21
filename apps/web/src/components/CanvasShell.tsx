import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { Background, Controls, MiniMap, ReactFlow, type Edge, type EdgeChange, type Node, type NodeChange, type NodeMouseHandler, type OnNodeDrag } from "@xyflow/react";
import { translate, type Language } from "@/i18n";
import { api } from "@/lib/api";
import type { Artifact, Workflow, WorkflowNode } from "@/lib/schema-types";
import { downloadWorkflow, readWorkflowFile, withUpdatedWorkflowGraph } from "@/lib/workflow";
import { useCanvasStore } from "@/store/canvas-store";
import { WorkflowNodeCard } from "@/components/canvas/WorkflowNodeCard";

const fallbackTemplateTypes = ["blank", "persona_builder", "agent", "knowledge_pipeline", "review_pipeline"];

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

const nodeTypes = {
  workflowNode: WorkflowNodeCard
};

type LayerViewConfig = {
  displayIndex: number;
  label: string;
  group: string;
};

const layerViewConfigByIndex: Record<number, LayerViewConfig> = {
  1: { displayIndex: 1, label: "Identity", group: "Identity related modules" },
  2: { displayIndex: 2, label: "Personality", group: "Personality related modules" },
  3: { displayIndex: 3, label: "Multimodal", group: "Multimodal related modules" },
  4: { displayIndex: 4, label: "Behavior", group: "Behavior related modules" },
  5: { displayIndex: 5, label: "Memory", group: "Memory related modules" },
  6: { displayIndex: 6, label: "Knowledge", group: "Knowledge related modules" },
  7: { displayIndex: 7, label: "Relationship", group: "Relationship related modules" },
  8: { displayIndex: 8, label: "World / Context", group: "World related modules" },
  9: { displayIndex: 9, label: "Tools", group: "Tools related modules" },
  10: { displayIndex: 10, label: "Safety", group: "Safety related modules" },
  11: { displayIndex: 11, label: "Legal", group: "Legal related modules" },
  12: { displayIndex: 12, label: "Audit", group: "Audit related modules" },
  13: { displayIndex: 13, label: "Meta", group: "Meta related modules" }
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
    type: "workflowNode",
    position: offset ? { x: position.x - offset.x, y: position.y - offset.y } : position,
    data: { schemaNode }
  };
}

export function CanvasShell() {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [bottomTab, setBottomTab] = useState<BottomTab>("logs");
  const [activeDrawer, setActiveDrawer] = useState<DrawerId | null>(null);
  const [selectedTemplateType, setSelectedTemplateType] = useState("persona_builder");
  const [activeLayerId, setActiveLayerId] = useState<string | null>(null);
  const [collapsedLayerIds, setCollapsedLayerIds] = useState<Set<string>>(() => new Set());
  const [floatingNodeIds, setFloatingNodeIds] = useState<string[]>([]);
  const [draggedNodeIds, setDraggedNodeIds] = useState<Set<string>>(() => new Set());
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
          (node) => node.node_id !== layer.node_id && inferNodeLayerIndex(node, layerNodes) === index
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

  const layerById = useMemo(
    () => new Map(layerSummaries.map((layer) => [layer.node.node_id, layer])),
    [layerSummaries]
  );
  const activeLayer = activeLayerId ? layerById.get(activeLayerId) ?? null : null;

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
    setFloatingNodeIds((ids) => ids.filter((id) => nodes.some((node) => node.node_id === id)));
  }, [activeLayerId, layerById, nodes]);

  const handleChildModuleSelect = useCallback(
    (node: WorkflowNode) => {
      setSelectedNode(node.node_id);
      const parentLayerIndex = inferNodeLayerIndex(node, layerNodes);
      const parentLayer = layerSummaries.find((layer) => layer.index === parentLayerIndex);
      if (parentLayer) {
        setActiveLayerId(parentLayer.node.node_id);
      }
      appendLog(`${t("status.moduleSelected", "Module selected")}: ${t(node.title_key, node.title_fallback)}`);
    },
    [appendLog, layerNodes, layerSummaries, setSelectedNode, t]
  );

  const handleChildModulePreview = useCallback(
    (node: WorkflowNode) => {
      setSelectedNode(node.node_id);
      setFloatingNodeIds((ids) => (ids.includes(node.node_id) ? ids : [...ids, node.node_id]));
      appendLog(`${t("status.modulePreview", "Module preview opened")}: ${t(node.title_key, node.title_fallback)}`);
    },
    [appendLog, setSelectedNode, t]
  );

  const flowNodes = useMemo<Node[]>(() => {
    return nodes
      .filter((node) => node.type !== "layer_container")
      .map((schemaNode, index) => {
        const flowNode = makeFlowNode(schemaNode);
        return {
          ...flowNode,
          position: schemaNode.position ?? { x: 120 + (index % 4) * 240, y: 100 + Math.floor(index / 4) * 160 }
        };
      });
  }, [nodes]);

  const flowEdges = useMemo<Edge[]>(
    () => {
      const schemaNodeIds = new Set(flowNodes.map((node) => node.id));
      return edges
        .filter((edge) => schemaNodeIds.has(edge.source) && schemaNodeIds.has(edge.target))
        .map((edge) => ({
          id: edge.edge_id,
          source: edge.source,
          target: edge.target,
          sourceHandle: edge.source_port,
          targetHandle: edge.target_port,
          type: "smoothstep"
        }));
    },
    [edges, flowNodes]
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
        setFloatingNodeIds([]);
        setDraggedNodeIds(new Set());
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
          setFloatingNodeIds([]);
          setDraggedNodeIds(new Set());
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

  const handleNodeClick: NodeMouseHandler = useCallback(
    (_event, node) => {
      setSelectedNode(node.id);
      const schemaNode = nodes.find((candidate) => candidate.node_id === node.id);
      if (schemaNode) {
        const parentLayerIndex = inferNodeLayerIndex(schemaNode, layerNodes);
        const parentLayer = layerSummaries.find((layer) => layer.index === parentLayerIndex);
        if (parentLayer) {
          setActiveLayerId(parentLayer.node.node_id);
        }
      }
    },
    [layerNodes, layerSummaries, nodes, setSelectedNode]
  );

  const handleNodeDoubleClick: NodeMouseHandler = useCallback(
    (_event, node) => {
      setSelectedNode(node.id);
    },
    [setSelectedNode]
  );

  const handlePaneClick = useCallback(() => setSelectedNode(null), [setSelectedNode]);

  const handleNodesChange = useCallback(
    (changes: NodeChange[]) => {
      changes.forEach((change) => {
        if (change.type === "position" && change.position) {
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
      updateNodePosition(node.id, node.position);
      appendLog(`${t("status.nodeMoved", "Node moved")}: ${node.id}`);
    },
    [appendLog, t, updateNodePosition]
  );

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
          <label className="template-select">
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
            <button className="template-load-button" onClick={() => handleTemplateClick(selectedTemplateType)}>
              {t("toolbar.load")}
            </button>
          </label>
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

      <section className="workspace-grid">
        <aside className="panel left-panel module-panel">
          <ModuleGroupContainer
            layers={layerSummaries}
            activeLayerId={activeLayer?.node.node_id ?? null}
            selectedNodeId={selectedNodeId}
            collapsedLayerIds={collapsedLayerIds}
            t={t}
            onSelectLayer={(layer) => {
              setActiveLayerId(layer.node.node_id);
              setSelectedNode(layer.node.node_id);
            }}
            onToggleLayer={toggleLayerCollapsed}
            onSelectNode={handleChildModuleSelect}
            onPreviewNode={handleChildModulePreview}
          />
        </aside>

        <section className="canvas-panel" aria-label={t("panel.canvas")}>
          {workflow ? (
            <>
              <div className="canvas-header">
                <div>
                  <span>{t("field.workflow")}</span>
                  <strong>{workflow.name}</strong>
                </div>
                <small>{activeLayer ? `${activeLayer.displayIndex}. ${activeLayer.displayLabel}` : "Pipeline"}</small>
              </div>
              <div className="canvas-stage">
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
                    onNodeDoubleClick={handleNodeDoubleClick}
                    onPaneClick={handlePaneClick}
                    onNodeDragStop={handleNodeDragStop}
                  >
                    <Background color="#3a3a3a" gap={24} />
                    <Controls />
                    <MiniMap pannable zoomable />
                  </ReactFlow>
                </div>
              </div>
              {floatingNodeIds.map((id, index) => {
                const node = nodes.find((candidate) => candidate.node_id === id);
                if (!node) {
                  return null;
                }
                return (
                  <FloatingNodeCanvas
                    key={id}
                    index={index}
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

        <aside className="panel right-panel">
          <div className="section-title">
            <h2>{t("panel.parameters")}</h2>
            <span>{activeLayer ? activeLayer.displayLabel : t("workspace.inspector", "Inspector")}</span>
          </div>
          <ParameterPanel node={selectedNode} workflow={workflow} t={t} />
        </aside>
      </section>

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

  return (
    <nav className="floating-dock" aria-label="Floating workspace dock">
      {dockItems.map((item) => (
        <button key={item.id} className={activeDrawer === item.id ? "is-active" : ""} onClick={() => onToggle(item.id)}>
          {item.label}
        </button>
      ))}
    </nav>
  );
}

function ModuleGroupContainer({
  layers,
  activeLayerId,
  selectedNodeId,
  collapsedLayerIds,
  t,
  onSelectLayer,
  onToggleLayer,
  onSelectNode,
  onPreviewNode
}: {
  layers: LayerSummary[];
  activeLayerId: string | null;
  selectedNodeId: string | null;
  collapsedLayerIds: Set<string>;
  t: (key: string, fallback?: string) => string;
  onSelectLayer: (layer: LayerSummary) => void;
  onToggleLayer: (layer: LayerSummary) => void;
  onSelectNode: (node: WorkflowNode) => void;
  onPreviewNode: (node: WorkflowNode) => void;
}) {
  if (!layers.length) {
    return <div className="empty-panel">{t("panel.noLayers", "No backend layers loaded")}</div>;
  }

  return (
    <section className="module-group-container">
      <div className="module-group-container__header">
        <div>
          <h2>Module Group Container</h2>
          <p>{t("panel.layerNavigator", "Layer Navigator")} / {layers.length}</p>
        </div>
      </div>
      <div className="module-group-list">
        {layers.map((layer) => {
          const collapsed = collapsedLayerIds.has(layer.node.node_id);
          const isActive = activeLayerId === layer.node.node_id;
          return (
            <article key={layer.node.node_id} className={`module-group-block tier-${layer.tier} ${isActive ? "is-active" : ""}`}>
              <button
                className="module-group-summary"
                onClick={() => {
                  onSelectLayer(layer);
                  onToggleLayer(layer);
                }}
              >
                <span>{String(layer.displayIndex).padStart(2, "0")}</span>
                <strong>{layer.displayLabel}</strong>
                <small>{collapsed ? "+" : "-"}</small>
              </button>
              {!collapsed ? (
                <div className="module-group-body">
                  <div className="module-group-meta">
                    <span>{layer.groupLabel}</span>
                    <span>{layer.status}</span>
                    <span>{layer.tier}</span>
                  </div>
                  <div className="module-list">
                    {layer.childNodes.length ? (
                      layer.childNodes.map((node) => {
                        const moduleTier = dataString(node, "module_tier", layer.tier);
                        const status = node.validation?.status ?? dataString(node, "status", "-");
                        return (
                          <button
                            key={node.node_id}
                            className={`module-list-item tier-${moduleTier} ${selectedNodeId === node.node_id ? "is-selected" : ""}`}
                            onClick={() => onSelectNode(node)}
                            onDoubleClick={() => onPreviewNode(node)}
                          >
                            <strong>{t(node.title_key, node.title_fallback)}</strong>
                            <span>{t(`node.type.${node.type}`, node.type)}</span>
                            <small>{status}</small>
                          </button>
                        );
                      })
                    ) : (
                      <div className="module-empty">{t("workspace.noChildNodes", "No child nodes are present in backend data for this layer.")}</div>
                    )}
                  </div>
                </div>
              ) : null}
            </article>
          );
        })}
      </div>
    </section>
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
        <strong>{activeId ? layers.get(activeId)?.displayLabel ?? "Pipeline" : "Pipeline"}</strong>
      </div>
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
          <div>
          <p>{t("workspace.breadcrumb", "Workflow / Layer / Folder")}</p>
          <h3>
            L{layer.displayIndex} {label}
          </h3>
          <span className="layer-group-pill">{layer.groupLabel}</span>
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
            layer.childNodes.map((node) => {
              const moduleTier = dataString(node, "module_tier", layer.tier);
              const status = node.validation?.status ?? dataString(node, "status", "-");
              return (
                <button
                  key={node.node_id}
                  className={`submodule-card tier-${moduleTier}`}
                  onClick={() => onSelectNode(node)}
                  onDoubleClick={() => onPreviewNode(node)}
                >
                  <span className="submodule-name">{t(node.title_key, node.title_fallback)}</span>
                  <span className="submodule-type">{t(`node.type.${node.type}`, node.type)}</span>
                  <span className="submodule-status">{status}</span>
                  <span className="submodule-tier">{moduleTier}</span>
                </button>
              );
            })
          ) : (
            <div className="empty-node-canvas">{t("workspace.noChildNodes", "No child nodes are present in backend data for this layer.")}</div>
          )}
          <button className="submodule-add" disabled title={t("workspace.addFromBackend", "Add from backend data")}>
            +
          </button>
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
          <small>{t(`node.type.${node.type}`, node.type)}</small>
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
