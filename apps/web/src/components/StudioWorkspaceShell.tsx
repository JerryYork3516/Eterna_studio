"use client";

import { useEffect, useRef, useState } from "react";
import { CanvasShell } from "@/components/CanvasShell";
import { VisualBuilderWorkspace } from "@/components/visual-builder/VisualBuilderWorkspace";
import { translate } from "@/i18n";
import { useCanvasStore } from "@/store/canvas-store";

export type StudioWorkspaceId = "resident_builder" | "visual_builder";
export type ResidentWorkspaceFocusIntent = {
  requestId: number;
  moduleInstanceId: string;
};
export type VisualWorkspaceSelectIntent = {
  requestId: number;
  assetId: string;
};

export function StudioWorkspaceShell() {
  const [activeWorkspace, setActiveWorkspace] =
    useState<StudioWorkspaceId>("resident_builder");
  const navigationRequestId = useRef(0);
  const [residentFocusIntent, setResidentFocusIntent] =
    useState<ResidentWorkspaceFocusIntent | null>(null);
  const [visualSelectIntent, setVisualSelectIntent] =
    useState<VisualWorkspaceSelectIntent | null>(null);
  const language = useCanvasStore((state) => state.language);
  const t = (key: string, fallback?: string) =>
    translate(language, key, fallback);

  useEffect(() => {
    document.body.dataset.studioWorkspace = activeWorkspace;
    return () => {
      delete document.body.dataset.studioWorkspace;
    };
  }, [activeWorkspace]);

  const navigateToResidentModule = (moduleInstanceId: string) => {
    navigationRequestId.current += 1;
    setResidentFocusIntent({
      requestId: navigationRequestId.current,
      moduleInstanceId,
    });
    setActiveWorkspace("resident_builder");
  };

  const navigateToVisualAsset = (assetId: string) => {
    navigationRequestId.current += 1;
    setVisualSelectIntent({
      requestId: navigationRequestId.current,
      assetId,
    });
    setActiveWorkspace("visual_builder");
  };

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
          <CanvasShell
            focusModuleIntent={residentFocusIntent}
            onNavigateToVisualAsset={navigateToVisualAsset}
          />
        </section>
        <section
          className="studio-workspace-panel studio-workspace-panel--visual"
          hidden={activeWorkspace !== "visual_builder"}
          aria-hidden={activeWorkspace !== "visual_builder"}
        >
          <VisualBuilderWorkspace
            selectAssetIntent={visualSelectIntent}
            onNavigateToResidentModule={navigateToResidentModule}
          />
        </section>
      </div>
    </div>
  );
}
