"use client";

import type { NeuralGraphSelection, NeuralGraphToggles, ResidentNeuralGraph } from "./neuralGraphTypes";

type TFunction = (key: string, fallback?: string) => string;

function Row({ label, value }: { label: string; value: unknown }) {
  return (
    <div className="resident-neural-graph-inspector__row">
      <span>{label}</span>
      <strong>{String(value ?? "")}</strong>
    </div>
  );
}

export function NeuralGraphInspector({
  graph,
  selection,
  toggles,
  focusedModuleId,
  activeLayerId,
  t,
  collapsed,
  onToggleCollapsed,
  onFocusModule,
  onExitFocus,
  onLayerFilter,
  onToggle,
}: {
  graph: ResidentNeuralGraph;
  selection: NeuralGraphSelection;
  toggles: NeuralGraphToggles;
  focusedModuleId: string | null;
  activeLayerId: string | null;
  t: TFunction;
  collapsed: boolean;
  onToggleCollapsed: () => void;
  onFocusModule: () => void;
  onExitFocus: () => void;
  onLayerFilter: (layerId: string | null) => void;
  onToggle: (key: keyof NeuralGraphToggles) => void;
}) {
  const layerCount = graph.nodes.filter((node) => node.kind === "layer").length;
  const moduleCount = graph.nodes.filter((node) => node.kind === "module").length;
  const nodeCount = graph.nodes.filter((node) => node.kind === "node").length;
  const layers = graph.nodes
    .filter((node) => node.kind === "layer")
    .sort((a, b) => (a.layerOrder ?? 0) - (b.layerOrder ?? 0));

  return (
    <aside className={`resident-neural-graph-inspector ${collapsed ? "is-collapsed" : ""}`}>
      <button
        type="button"
        className="resident-neural-graph-inspector__collapse"
        title={t(collapsed ? "residentNeuralGraph.expandParameters" : "residentNeuralGraph.collapseParameters", collapsed ? "Expand parameters" : "Collapse parameters")}
        aria-label={t(collapsed ? "residentNeuralGraph.expandParameters" : "residentNeuralGraph.collapseParameters", collapsed ? "Expand parameters" : "Collapse parameters")}
        aria-expanded={!collapsed}
        onClick={onToggleCollapsed}
      >
        {collapsed ? "‹" : "›"}
      </button>
      {collapsed ? null : (
        <>
      <section className="resident-neural-graph-toggle" aria-label={t("residentNeuralGraph.toggles", "Display toggles")}>
        {([
          ["layerLabels", "residentNeuralGraph.showLayerNames", "Show Layer Names"],
          ["modules", "residentNeuralGraph.showModules", "Show Modules"],
          ["moduleLabels", "residentNeuralGraph.showAllModuleNames", "Show All Module Names"],
          ["nodes", "residentNeuralGraph.showNodes", "Show Nodes"],
          ["edges", "residentNeuralGraph.showEdges", "Show Edges"],
        ] as const).map(([key, labelKey, fallback]) => (
          <label key={key}>
            <input type="checkbox" checked={toggles[key]} onChange={() => onToggle(key)} />
            <span>{t(labelKey, fallback)}</span>
          </label>
        ))}
      </section>

      <section className="resident-neural-graph-layer-legend">
        <div className="resident-neural-graph-layer-legend__header">
          <h3>{t("neuralGraph.layerLegend", "Layer Legend")}</h3>
          <button type="button" onClick={() => onLayerFilter(null)}>
            {t("neuralGraph.layerLegend.all", "All")}
          </button>
        </div>
        <div className="resident-neural-graph-layer-legend__grid">
          {layers.map((layer) => (
            <button
              key={layer.id}
              type="button"
              className={activeLayerId === layer.layerId ? "is-active" : ""}
              title={layer.label}
              onClick={() => onLayerFilter(activeLayerId === layer.layerId ? null : layer.layerId ?? null)}
            >
              <span style={{ background: layer.color ?? "#4f8cff" }} />
              <strong>L{layer.layerOrder}</strong>
            </button>
          ))}
        </div>
      </section>

      <section className="resident-neural-graph-inspector__card">
        <h3>
          {focusedModuleId
            ? t("neuralGraph.modulePreview", "Module Preview")
            : selection
              ? selection.label
              : t("residentNeuralGraph.selectionEmpty", "Select an item")}
        </h3>
        {selection?.kind === "layer" ? (
          <>
            <Row label="layer_id" value={selection.layerId} />
            <Row label="layer_name" value={selection.label} />
            <Row label="layer_order" value={selection.layerOrder} />
            <Row label="module_count" value={selection.moduleCount ?? 0} />
          </>
        ) : null}
        {selection?.kind === "module" ? (
          <>
            <Row label={t("neuralGraph.selectedModule", "Selected Module")} value={selection.label} />
            <Row label="module_id" value={selection.moduleId} />
            <Row label="module_instance_id" value={selection.moduleInstanceId} />
            <Row label="module_name" value={selection.label} />
            <Row label="layer_id" value={selection.layerId} />
            <Row label="node_count" value={selection.nodeCount ?? 0} />
            <Row label="hidden_node_count" value={selection.hiddenNodeCount ?? 0} />
            {selection.id !== focusedModuleId ? (
              <button type="button" className="resident-neural-graph-inspector__action" onClick={onFocusModule}>
                {t("neuralGraph.focus.enter", "Enter Module")}
              </button>
            ) : null}
          </>
        ) : null}
        {selection?.kind === "node" ? (
          <>
            <Row label="node_id" value={selection.nodeId} />
            <Row label="node_type" value={selection.nodeType} />
            <Row label="module_id" value={selection.moduleId} />
            <Row label="layer_id" value={selection.layerId} />
          </>
        ) : null}
        {!selection ? (
          <>
            <Row label={t("residentNeuralGraph.layers", "13 Layers")} value={layerCount} />
            <Row label={t("residentNeuralGraph.modules", "Module nodes")} value={moduleCount} />
            <Row label={t("residentNeuralGraph.neurons", "Neurons")} value={nodeCount} />
          </>
        ) : null}
        {focusedModuleId ? (
          <button type="button" className="resident-neural-graph-inspector__action" onClick={onExitFocus}>
            {t("neuralGraph.focus.exit", "Back to Global View")}
          </button>
        ) : null}
      </section>

      <section className="resident-neural-graph-legend">
        <h3>{t("residentNeuralGraph.legend", "Legend")}</h3>
        <span>{t("neuralGraph.legend.layer", "Layer")}</span>
        <span>{t("neuralGraph.legend.module", "Module")}</span>
        <span>{t("neuralGraph.legend.node", "Node")}</span>
        <span>{t("neuralGraph.legend.synapse", "Synapse Edge")}</span>
        <span>{t("neuralGraph.legend.neuralSignal", "Neural Signal")} · v0.1</span>
        <span>{t("neuralGraph.legend.runtimePulse", "Runtime Pulse")} · v0.1</span>
        <span>{t("neuralGraph.legend.memoryStar", "Memory Star")} · v0.1</span>
      </section>
        </>
      )}
    </aside>
  );
}
