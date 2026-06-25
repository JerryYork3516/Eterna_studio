"use client";

import { useMemo, useState, type DragEvent as ReactDragEvent } from "react";
import type { ModuleCatalogEntryV04, ModuleLayerV04 } from "@/lib/schema-types";

export const MODULE_DND_MIME = "application/eterna-module";

export function setModuleDragData(event: ReactDragEvent, moduleId: string) {
  event.dataTransfer.setData(MODULE_DND_MIME, moduleId);
  event.dataTransfer.setData("text/plain", moduleId);
  event.dataTransfer.effectAllowed = "copy";
}

export function readModuleDragId(event: ReactDragEvent): string | null {
  const value = event.dataTransfer.getData(MODULE_DND_MIME);
  return value || null;
}

function statusLabel(status: string, t: (key: string, fallback?: string) => string) {
  return t(`module.status.${status}`, status);
}

function moduleId(mod: ModuleCatalogEntryV04) {
  return mod.module_id;
}

function moduleName(mod: ModuleCatalogEntryV04) {
  return mod.module_name;
}

function slotLabel(slot: string | null | undefined, t: (key: string, fallback?: string) => string) {
  const value = slot || "unplanned";
  return t(`module.slot.${value}`, value);
}

function layerOrder(layer: ModuleLayerV04) {
  return Number(layer.layer_order);
}

export function ModuleLibrary({
  t,
  collapsed,
  layers,
  modules,
  onDragStartModule
}: {
  t: (key: string, fallback?: string) => string;
  collapsed: boolean;
  layers: ModuleLayerV04[];
  modules: ModuleCatalogEntryV04[];
  onDragStartModule?: (moduleId: string) => void;
}) {
  const [query, setQuery] = useState("");
  const [bodyCollapsed, setBodyCollapsed] = useState(true);
  const [collapsedLayers, setCollapsedLayers] = useState<Set<string>>(() => new Set());

  const sortedLayers = useMemo(
    () => layers.slice().sort((a, b) => layerOrder(a) - layerOrder(b)),
    [layers]
  );

  const modulesByLayer = useMemo(() => {
    const next = new Map<string, ModuleCatalogEntryV04[]>();
    for (const mod of modules) {
      const layerId = mod.layer_id || "general";
      next.set(layerId, [...(next.get(layerId) ?? []), mod]);
    }
    return next;
  }, [modules]);

  const allLayerIds = useMemo(() => sortedLayers.map((layer) => layer.layer_id), [sortedLayers]);

  const matches = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) {
      return null;
    }
    const ids = new Set<string>();
    for (const mod of modules) {
      const haystack = [mod.module_name, mod.slot_type, mod.layer_id, mod.category, mod.status].filter(Boolean).join(" ").toLowerCase();
      if (haystack.includes(q)) {
        ids.add(moduleId(mod));
      }
    }
    return ids;
  }, [modules, query]);

  const totalCount = modules.length;

  const toggleLayer = (id: string) =>
    setCollapsedLayers((current) => {
      const next = current.size ? new Set(current) : new Set(allLayerIds);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  const isLayerCollapsed = (id: string) => !matches && (collapsedLayers.size ? collapsedLayers.has(id) : true);
  if (collapsed) {
    return (
      <section className="panel-section module-library is-rail">
        <div className="section-title">
          <h2>{t("panel.moduleLibrary", "模块库").slice(0, 1)}</h2>
          <span>{totalCount}</span>
        </div>
      </section>
    );
  }

  return (
    <section className="panel-section module-library">
      <div className="section-title">
        <button type="button" className="library-master-toggle" onClick={() => setBodyCollapsed((value) => !value)} aria-expanded={!bodyCollapsed}>
          <span className="node-library-category__chevron">{bodyCollapsed ? "▸" : "▾"}</span>
          <h2>{t("panel.moduleLibrary", "模块库")}</h2>
        </button>
        <span>{totalCount}</span>
      </div>
      {bodyCollapsed ? null : (
        <>
      <input
        className="module-library__search"
        value={query}
        onChange={(event) => setQuery(event.target.value)}
        placeholder={t("module.search", "搜索模块…")}
      />
      <div className="module-library__body">
        {sortedLayers.map((layer) => {
          const mods = (modulesByLayer.get(layer.layer_id) ?? []).filter((mod) => (matches ? matches.has(moduleId(mod)) : true));
          if (matches && !mods.length) {
            return null;
          }
          const layerCollapsed = isLayerCollapsed(layer.layer_id);
          return (
            <section key={layer.layer_id} className={`module-cat ${layerCollapsed ? "is-collapsed" : ""}`}>
              <button type="button" className="module-cat__header" onClick={() => toggleLayer(layer.layer_id)} aria-expanded={!layerCollapsed}>
                <span className="module-cat__chevron">{layerCollapsed ? "▸" : "▾"}</span>
                <strong>{layer.layer_name}</strong>
                <span className="module-cat__count">{mods.length}</span>
              </button>
              {!layerCollapsed ? (
                <div className="module-cat__items">
                  {mods.map((mod) => (
                    <div
                      key={moduleId(mod)}
                      role="button"
                      tabIndex={0}
                      draggable
                      className={`module-card cat-${mod.category} status-${String(mod.status).toLowerCase()}`}
                      title={`${moduleName(mod)} · ${slotLabel(mod.slot_type, t)} · ${statusLabel(String(mod.status), t)}`}
                      onDragStart={(event) => {
                        setModuleDragData(event, moduleId(mod));
                        onDragStartModule?.(moduleId(mod));
                      }}
                    >
                      <div className="module-card__top">
                        <span className="module-card__name">{moduleName(mod)}</span>
                        <span className={`module-card__status is-${String(mod.status).toLowerCase()}`}>{statusLabel(String(mod.status), t)}</span>
                      </div>
                      <div className="module-card__meta">
                        <span className="module-card__layer">{layer.layer_id}</span>
                        <span className="module-card__slot">{slotLabel(mod.slot_type, t)}</span>
                      </div>
                    </div>
                  ))}
                </div>
              ) : null}
            </section>
          );
        })}
      </div>
        </>
      )}
    </section>
  );
}
