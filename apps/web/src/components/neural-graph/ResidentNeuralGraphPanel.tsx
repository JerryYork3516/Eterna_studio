"use client";

import { useMemo, useState } from "react";
import type { ModuleCatalogResponseV04 } from "@/lib/schema-types";
import type { ModuleGraphsState } from "@/store/canvas-store";
import { buildResidentNeuralGraph } from "./buildResidentNeuralGraph";
import { NeuralGraphInspector } from "./NeuralGraphInspector";
import { ResidentNeuralGraphScene } from "./ResidentNeuralGraphScene";
import type { NeuralGraphModuleInstance, NeuralGraphSelection, NeuralGraphToggles } from "./neuralGraphTypes";

type TFunction = (key: string, fallback?: string) => string;

export function ResidentNeuralGraphPanel({
  moduleCatalog,
  moduleGraphs,
  layerModules,
  moduleInstanceRegistry,
  uiColors,
  moduleUiColors,
  t,
}: {
  moduleCatalog: ModuleCatalogResponseV04 | null;
  moduleGraphs: ModuleGraphsState;
  layerModules: Record<string, string[]>;
  moduleInstanceRegistry: Record<string, NeuralGraphModuleInstance>;
  uiColors: Record<string, string>;
  moduleUiColors: Record<string, string>;
  t: TFunction;
}) {
  const [selection, setSelection] = useState<NeuralGraphSelection>(null);
  const [focusedModuleId, setFocusedModuleId] = useState<string | null>(null);
  const [activeLayerId, setActiveLayerId] = useState<string | null>(null);
  const [inspectorCollapsed, setInspectorCollapsed] = useState(false);
  const [toggles, setToggles] = useState<NeuralGraphToggles>({
    layers: true,
    layerLabels: false,
    modules: true,
    moduleLabels: false,
    nodes: true,
    edges: true,
  });
  const graph = useMemo(
    () => buildResidentNeuralGraph({ moduleCatalog, moduleGraphs, layerModules, moduleInstanceRegistry, uiColors, moduleUiColors, t }),
    [moduleCatalog, moduleGraphs, layerModules, moduleInstanceRegistry, uiColors, moduleUiColors, t]
  );

  return (
    <div className={`resident-neural-graph-panel ${inspectorCollapsed ? "is-inspector-collapsed" : ""}`}>
      <div className="resident-neural-graph-panel__main">
        <div className="resident-neural-graph-panel__heading">
          <strong>{t("neuralGraph.layout.moduleGalaxy", "3D Module Relationship Galaxy")}</strong>
          <span>{t("neuralGraph.subtitle.moduleGalaxy", "Read-only module relationship star map")}</span>
        </div>
        <ResidentNeuralGraphScene
          graph={graph}
          toggles={toggles}
          selection={selection}
          focusedModuleId={focusedModuleId}
          activeLayerId={activeLayerId}
          t={t}
          onSelect={setSelection}
          onFocusModule={setFocusedModuleId}
          onExitFocus={() => setFocusedModuleId(null)}
        />
      </div>
      <NeuralGraphInspector
        graph={graph}
        selection={selection}
        toggles={toggles}
        focusedModuleId={focusedModuleId}
        activeLayerId={activeLayerId}
        t={t}
        collapsed={inspectorCollapsed}
        onToggleCollapsed={() => setInspectorCollapsed((value) => !value)}
        onFocusModule={() => selection?.kind === "module" && setFocusedModuleId(selection.id)}
        onExitFocus={() => setFocusedModuleId(null)}
        onLayerFilter={setActiveLayerId}
        onToggle={(key) => setToggles((current) => ({ ...current, [key]: !current[key] }))}
      />
    </div>
  );
}
