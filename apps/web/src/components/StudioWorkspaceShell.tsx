"use client";

import { useEffect, useState } from "react";
import { CanvasShell } from "@/components/CanvasShell";
import { VisualBuilderWorkspace } from "@/components/visual-builder/VisualBuilderWorkspace";
import { translate } from "@/i18n";
import { useCanvasStore } from "@/store/canvas-store";

export type StudioWorkspaceId = "resident_builder" | "visual_builder";

export function StudioWorkspaceShell() {
  const [activeWorkspace, setActiveWorkspace] =
    useState<StudioWorkspaceId>("resident_builder");
  const language = useCanvasStore((state) => state.language);
  const t = (key: string, fallback?: string) =>
    translate(language, key, fallback);

  useEffect(() => {
    document.body.dataset.studioWorkspace = activeWorkspace;
    return () => {
      delete document.body.dataset.studioWorkspace;
    };
  }, [activeWorkspace]);

  return (
    <div className="studio-workspace-shell">
      <nav
        className="studio-workspace-nav"
        aria-label={t("workspace.navigation", "Studio workspaces")}
      >
        <button
          type="button"
          className={
            activeWorkspace === "resident_builder" ? "is-active" : ""
          }
          aria-pressed={activeWorkspace === "resident_builder"}
          onClick={() => setActiveWorkspace("resident_builder")}
        >
          {t("workspace.residentBuilder", "Resident Builder")}
        </button>
        <button
          type="button"
          className={
            activeWorkspace === "visual_builder" ? "is-active" : ""
          }
          aria-pressed={activeWorkspace === "visual_builder"}
          onClick={() => setActiveWorkspace("visual_builder")}
        >
          {t("workspace.visualBuilder", "Visual Builder")}
        </button>
      </nav>

      <div className="studio-workspace-surface">
        <section
          className="studio-workspace-panel studio-workspace-panel--resident"
          hidden={activeWorkspace !== "resident_builder"}
          aria-hidden={activeWorkspace !== "resident_builder"}
        >
          <CanvasShell />
        </section>
        <section
          className="studio-workspace-panel studio-workspace-panel--visual"
          hidden={activeWorkspace !== "visual_builder"}
          aria-hidden={activeWorkspace !== "visual_builder"}
        >
          <VisualBuilderWorkspace />
        </section>
      </div>
    </div>
  );
}
