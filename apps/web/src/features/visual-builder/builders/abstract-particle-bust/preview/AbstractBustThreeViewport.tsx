"use client";

import {
  useEffect,
  useRef,
  useState,
} from "react";
import {
  normalizeAbstractBustBlueprint,
  type AbstractBustBlueprint,
} from "@eterna/shared-schema/abstract-bust-blueprint";

import { generateAbstractBust } from "../generator/generate-abstract-bust.ts";
import type { AbstractBustEditorTranslator } from "../editor/AbstractBustControlGroup.tsx";
import { AbstractBustThreeScene } from "./three-scene.ts";
import type {
  AbstractBustCameraMode,
  AbstractBustPreviewSummary,
} from "./preview-types.ts";

const EMPTY_SUMMARY: AbstractBustPreviewSummary = Object.freeze({
  particleCount: 0,
  digest: null,
  error: null,
  diagnostics: Object.freeze({
    initializationMs: 0,
    lastUpdateMs: 0,
    generationCount: 0,
    renderersCreated: 0,
    renderersDisposed: 0,
    activeContexts: 0,
  }),
});

export function AbstractBustThreeViewport({
  blueprint,
  onSummary,
  t,
}: {
  blueprint: AbstractBustBlueprint;
  onSummary: (summary: AbstractBustPreviewSummary) => void;
  t: AbstractBustEditorTranslator;
}) {
  const mountRef = useRef<HTMLDivElement>(null);
  const sceneRef = useRef<AbstractBustThreeScene | null>(null);
  const summaryRef = useRef<AbstractBustPreviewSummary>(EMPTY_SUMMARY);
  const onSummaryRef = useRef(onSummary);
  const generationFrameRef = useRef<number | null>(null);
  const generationCountRef = useRef(0);
  const [cameraMode, setCameraMode] =
    useState<AbstractBustCameraMode>("front");
  const [errorCode, setErrorCode] = useState<string | null>(null);

  useEffect(() => {
    onSummaryRef.current = onSummary;
  }, [onSummary]);

  const publishSummary = (summary: AbstractBustPreviewSummary) => {
    summaryRef.current = summary;
    onSummaryRef.current(summary);
  };

  useEffect(() => {
    const mount = mountRef.current;
    if (!mount) return;

    let scene: AbstractBustThreeScene;
    try {
      scene = new AbstractBustThreeScene(mount, (contextError) => {
        setErrorCode(contextError);
        const current = summaryRef.current;
        publishSummary(Object.freeze({
          ...current,
          error: contextError,
        }));
      });
      sceneRef.current = scene;
      publishSummary(Object.freeze({
        ...EMPTY_SUMMARY,
        diagnostics: scene.diagnostics(0, 0),
      }));
    } catch {
      setErrorCode("webgl_unavailable");
      publishSummary(Object.freeze({
        ...EMPTY_SUMMARY,
        error: "webgl_unavailable",
      }));
      return;
    }

    const resizeObserver = new ResizeObserver((entries) => {
      const entry = entries[0];
      if (!entry) return;
      scene.resize(entry.contentRect.width, entry.contentRect.height);
    });
    resizeObserver.observe(mount);
    scene.resize(mount.clientWidth, mount.clientHeight);

    return () => {
      resizeObserver.disconnect();
      scene.dispose();
      sceneRef.current = null;
    };
  }, []);

  useEffect(() => {
    if (generationFrameRef.current !== null) {
      window.cancelAnimationFrame(generationFrameRef.current);
    }
    generationFrameRef.current = window.requestAnimationFrame(() => {
      generationFrameRef.current = null;
      const scene = sceneRef.current;
      if (!scene) return;
      const startedAt = performance.now();
      try {
        const normalized = normalizeAbstractBustBlueprint(blueprint);
        const generated = generateAbstractBust(normalized);
        scene.updateGenerated(generated);
        generationCountRef.current += 1;
        const updateMs = performance.now() - startedAt;
        setErrorCode(null);
        publishSummary(Object.freeze({
          particleCount: generated.particleCount,
          digest: generated.digest,
          error: null,
          diagnostics: scene.diagnostics(
            generationCountRef.current,
            updateMs
          ),
        }));
      } catch {
        setErrorCode("generation_failed");
        publishSummary(Object.freeze({
          ...summaryRef.current,
          error: "generation_failed",
        }));
      }
    });

    return () => {
      if (generationFrameRef.current !== null) {
        window.cancelAnimationFrame(generationFrameRef.current);
        generationFrameRef.current = null;
      }
    };
  }, [blueprint]);

  const setMode = (mode: AbstractBustCameraMode) => {
    setCameraMode(mode);
    sceneRef.current?.setMode(mode);
  };

  const resetView = () => {
    setCameraMode("front");
    sceneRef.current?.resetView();
  };

  const errorMessage = errorCode
    ? t(
        `visualBuilder.error.${errorCode}`,
        errorCode === "webgl_context_lost"
          ? "WebGL context lost"
          : errorCode === "generation_failed"
            ? "Particle generation failed"
            : "WebGL is unavailable"
      )
    : null;

  return (
    <section
      className="abstract-bust-preview"
      aria-label={t("visualBuilder.viewport.title", "Visual viewport")}
      data-camera-mode={cameraMode}
      data-active-contexts={summaryRef.current.diagnostics.activeContexts}
      data-generation-count={summaryRef.current.diagnostics.generationCount}
    >
      <div className="abstract-bust-preview__toolbar">
        {(["front", "side", "free", "auto"] as const).map((mode) => (
          <button
            key={mode}
            type="button"
            className={cameraMode === mode ? "is-active" : ""}
            aria-pressed={cameraMode === mode}
            onClick={() => setMode(mode)}
          >
            {t(`visualBuilder.camera.${mode}`, mode)}
          </button>
        ))}
        <button type="button" onClick={resetView}>
          {t("visualBuilder.camera.reset", "Reset")}
        </button>
      </div>
      <div ref={mountRef} className="abstract-bust-preview__mount" />
      {errorMessage ? (
        <div className="abstract-bust-preview__error" role="alert">
          <strong>{t("visualBuilder.error.previewTitle", "Preview unavailable")}</strong>
          <span>{errorMessage}</span>
        </div>
      ) : null}
    </section>
  );
}
