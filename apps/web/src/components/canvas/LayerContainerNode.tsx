import { Handle, Position, type NodeProps } from "@xyflow/react";
import type { CSSProperties } from "react";
import { translate, type Language } from "@/i18n";
import type { WorkflowNode } from "@/lib/schema-types";
import { getNodeDefinition } from "@/registry/nodeRegistry";
import { useCanvasStore } from "@/store/canvas-store";

type CanvasNodeData = {
  schemaNode: WorkflowNode;
  viewLabel?: string;
  viewIndex?: number;
  groupLabel?: string;
  uiGroup?: string;
  uiTags?: string[];
  uiColor?: string;
  onColor?: (color: string) => void;
  onOpenAssembly?: () => void;
};

function dataText(data: WorkflowNode["data"], key: string, fallback = "-") {
  const value = data?.[key];
  if (value === null || value === undefined || value === "") {
    return fallback;
  }
  return String(value);
}

function stableI18nKeyPart(value: string) {
  return value
    .trim()
    .replace(/([a-z0-9])([A-Z])/g, "$1_$2")
    .replace(/[^a-zA-Z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "")
    .toLowerCase();
}

function translateFirst(language: Language, keys: string[], fallback: string) {
  for (const key of keys) {
    const marker = `__missing__${key}`;
    const translated = translate(language, key, marker);
    if (translated !== marker) {
      return translated;
    }
  }
  return fallback;
}

function assemblyStatusText(language: Language, value: unknown, fallback = "-") {
  const raw = typeof value === "string" && value.trim() ? value.trim() : "";
  if (!raw || raw === "-") {
    return translate(language, "common.notGenerated");
  }
  const normalized = stableI18nKeyPart(raw);
  return translateFirst(language, [`assembly.status.${normalized}`, `module.status.${raw}`, `lock.${raw}`], fallback === "-" ? raw : fallback);
}

export function LayerContainerNode({ data, selected }: NodeProps) {
  const language = useCanvasStore((state) => state.language);
  const { schemaNode, viewLabel, viewIndex, groupLabel, uiGroup, uiTags = [], uiColor, onColor, onOpenAssembly } = data as CanvasNodeData;
  const label = viewLabel ?? translate(language, schemaNode.title_key, schemaNode.title_fallback);
  const typeLabel = translate(language, `node.type.${schemaNode.type}`, getNodeDefinition(schemaNode.type)?.display_name ?? schemaNode.type);
  const lockLabel = translate(language, `lock.${schemaNode.lock_level}`, schemaNode.lock_level);
  const moduleTier = typeof schemaNode.data?.module_tier === "string" ? schemaNode.data.module_tier : null;
  const reviewStatus =
    schemaNode.validation?.status ??
    (schemaNode.data?.validation && typeof schemaNode.data.validation === "object"
      ? String((schemaNode.data.validation as { status?: unknown }).status ?? "-")
      : "-");

  return (
    <div
      className={`layer-node lock-${schemaNode.lock_level} ${moduleTier ? `tier-${moduleTier}` : ""} ${selected ? "is-selected" : ""}`}
      style={uiColor ? ({ "--node-accent": uiColor } as CSSProperties) : undefined}
    >
      <Handle type="target" position={Position.Top} id="p_in" className="flow-handle layer-flow-handle-top" />
      {groupLabel ? <div className="layer-node__group">{groupLabel}</div> : null}
      <div className="layer-node__header">
        <div>
          <div className="layer-node__eyebrow">{typeLabel}</div>
          <div className="layer-node__title">
            {viewIndex ? <span>L{viewIndex}</span> : null}
            {translate(language, `layer.${schemaNode.layer_id}`, label)}
          </div>
        </div>
        <div className="layer-node__badges">
          {moduleTier ? <span className="tier-pill">{assemblyStatusText(language, moduleTier)}</span> : null}
          <span className="lock-pill">{lockLabel}</span>
          {onOpenAssembly ? (
            <button
              type="button"
              className="layer-node__assembly-button nodrag nopan"
              title={translate(language, "assembly.panel.layerAssembly")}
              aria-label={translate(language, "assembly.action.viewDetails")}
              onPointerDown={(event) => event.stopPropagation()}
              onClick={(event) => {
                event.preventDefault();
                event.stopPropagation();
                onOpenAssembly();
              }}
            >
              {translate(language, "assembly.action.viewDetails")}
            </button>
          ) : null}
        </div>
        {onColor ? (
          <label className="layer-node__color-picker nodrag">
            <span>{translate(language, "node.header.color")}</span>
            <input
              type="color"
              value={uiColor || "#4f8cff"}
              onChange={(event) => onColor(event.target.value)}
              aria-label={translate(language, "node.header.color")}
            />
          </label>
        ) : null}
      </div>
      <details className="layer-node__params nodrag nopan" onPointerDown={(event) => event.stopPropagation()}>
        <summary>{translate(language, "node.sections.core")}</summary>
        <div className="layer-node__description">{dataText(schemaNode.data, "description", schemaNode.title_fallback)}</div>
        <div className="layer-node__grid">
          <span>{translate(language, "field.status")}</span>
          <strong>{assemblyStatusText(language, dataText(schemaNode.data, "status"))}</strong>
          <span>{translate(language, "field.version")}</span>
          <strong>{dataText(schemaNode.data, "version")}</strong>
        </div>
      </details>
      <details className="layer-node__params nodrag nopan" onPointerDown={(event) => event.stopPropagation()}>
        <summary>{translate(language, "node.sections.advanced")}</summary>
        {uiGroup || uiTags.length ? (
          <div className="layer-node__ui-meta">
            {uiGroup ? <span className="layer-node__ui-group">{uiGroup}</span> : null}
            {uiTags.slice(0, 3).map((tag) => (
              <span key={tag} className="layer-node__ui-tag">
                {tag}
              </span>
            ))}
          </div>
        ) : null}
      </details>
      <details className="layer-node__params nodrag nopan" onPointerDown={(event) => event.stopPropagation()}>
        <summary>{translate(language, "node.sections.runtime")}</summary>
        <div className="layer-node__grid">
          <span>{translate(language, "field.childrenCount")}</span>
          <strong>{dataText(schemaNode.data, "children_count", "0")}</strong>
          <span>{translate(language, "field.review")}</span>
          <strong>{assemblyStatusText(language, reviewStatus)}</strong>
        </div>
      </details>
      <Handle type="target" position={Position.Left} id="p_left_in" className="flow-handle flow-handle-left" />
      <Handle type="source" position={Position.Bottom} id="p_out" className="flow-handle layer-flow-handle-bottom" />
    </div>
  );
}
