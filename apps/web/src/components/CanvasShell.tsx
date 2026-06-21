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
  type NodeMouseHandler
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

const libraryNodeTypes: NodeType[] = [
  "input",
  "transform",
  "model",
  "agent",
  "review",
  "layer_container",
  "output",
  "export"
];

export function CanvasShell() {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [bottomTab, setBottomTab] = useState<"logs" | "artifacts" | "preview">("logs");
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

  const flowNodes = useMemo<Node[]>(
    () =>
      nodes.map((schemaNode) => ({
        id: schemaNode.node_id,
        type: schemaNode.type === "layer_container" ? "layerContainer" : "workflowNode",
        position: schemaNode.position ?? { x: 0, y: 0 },
        data: { schemaNode }
      })),
    [nodes]
  );

  const flowEdges = useMemo<Edge[]>(
    () =>
      edges.map((edge) => ({
        id: edge.edge_id,
        source: edge.source,
        target: edge.target,
        sourceHandle: edge.source_port,
        targetHandle: edge.target_port,
        type: "smoothstep"
      })),
    [edges]
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

  const handleNodeClick: NodeMouseHandler = useCallback(
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
    },
    [removeEdges]
  );

  return (
    <main className="canvas-shell">
      <header className="top-toolbar">
        <div className="brand">
          <strong>{t("app.title")}</strong>
          <span>{t("app.subtitle")}</span>
        </div>
        <div className="toolbar-actions">
          <button onClick={handleSave}>{t("toolbar.save")}</button>
          <button onClick={handleLoad}>{t("toolbar.load")}</button>
          <button onClick={handleValidate}>{t("toolbar.validate")}</button>
          <button onClick={handleMockRun}>{t("toolbar.mockRun")}</button>
          <button onClick={handleExportPreview}>{t("toolbar.exportPreview")}</button>
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
          <h2>{t("panel.nodeLibrary")}</h2>
          <div className="template-block">
            <h3>{t("panel.templates")}</h3>
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
            {templates.length ? (
              <p className="hint">{templates.map((template) => template.template_type).join(" / ")}</p>
            ) : null}
          </div>
          <div className="node-library">
            {libraryNodeTypes.map((type) => (
              <div key={type} className="library-item">
                <span>{t(`node.type.${type}`, type)}</span>
                <small>{type}</small>
              </div>
            ))}
          </div>
        </aside>

        <section className="canvas-panel" aria-label={t("panel.canvas")}>
          {workflow ? (
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
              onNodeDragStop={(_event, node) => updateNodePosition(node.id, node.position)}
            >
              <Background />
              <Controls />
              <MiniMap pannable zoomable />
            </ReactFlow>
          ) : (
            <div className="empty-canvas">
              <h2>{t("panel.noWorkflow")}</h2>
              {templates.some((template) => template.template_type === "blank") ? (
                <button onClick={() => handleTemplateClick("blank")}>{t("template.blank")}</button>
              ) : null}
              <button onClick={() => handleTemplateClick("persona_builder")} disabled={!apiReady}>
                {t("template.loadPersona")}
              </button>
            </div>
          )}
        </section>

        <aside className="panel right-panel">
          <h2>{t("panel.parameters")}</h2>
          <ParameterPanel node={selectedNode} workflow={workflow} t={t} />
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
