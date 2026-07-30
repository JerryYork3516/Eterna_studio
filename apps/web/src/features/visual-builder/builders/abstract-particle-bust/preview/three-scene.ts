import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";

import {
  ABSTRACT_BUST_PARTICLE_COUNT,
  type GeneratedAbstractBust,
} from "../types.ts";
import { deriveAbstractBustCameraPose } from "./camera-presets.ts";
import type {
  AbstractBustCameraMode,
  AbstractBustPreviewDiagnostics,
} from "./preview-types.ts";

const PREVIEW_COLOR = 0x7a_a2_f7;
const CAMERA_FOV = 34;

const rendererCounters = {
  created: 0,
  disposed: 0,
  active: 0,
};

type AbstractBustRendererFactory = (
  parameters: THREE.WebGLRendererParameters
) => THREE.WebGLRenderer;

export function createAbstractBustWebGLRenderer(
  factory: AbstractBustRendererFactory = (parameters) =>
    new THREE.WebGLRenderer(parameters)
): THREE.WebGLRenderer {
  return factory({
    alpha: true,
    antialias: true,
    powerPreference: "high-performance",
  });
}

export function handleAbstractBustContextLost(
  event: Pick<Event, "preventDefault">,
  onContextError: (message: string | null) => void
): void {
  event.preventDefault();
  onContextError("webgl_context_lost");
}

export function handleAbstractBustContextRestored(
  resetRendererState: () => void,
  onContextError: (message: string | null) => void
): void {
  resetRendererState();
  onContextError(null);
}

export function disposeAbstractBustPreviewResources(resources: {
  controls: Pick<OrbitControls, "dispose">;
  geometry: Pick<THREE.BufferGeometry, "dispose">;
  material: Pick<THREE.Material, "dispose">;
  renderer: Pick<THREE.WebGLRenderer, "dispose" | "forceContextLoss">;
}): void {
  resources.controls.dispose();
  resources.geometry.dispose();
  resources.material.dispose();
  resources.renderer.dispose();
  resources.renderer.forceContextLoss();
}

export function createAbstractBustPreviewGeometry(): THREE.BufferGeometry {
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute(
    "position",
    new THREE.BufferAttribute(
      new Float32Array(ABSTRACT_BUST_PARTICLE_COUNT * 3),
      3
    )
  );
  return geometry;
}

export function updateAbstractBustPreviewGeometry(
  geometry: THREE.BufferGeometry,
  positions: Float32Array
): THREE.BufferAttribute {
  if (positions.length !== ABSTRACT_BUST_PARTICLE_COUNT * 3) {
    throw new Error(
      `Abstract bust preview requires ${ABSTRACT_BUST_PARTICLE_COUNT * 3} coordinates`
    );
  }
  const attribute = geometry.getAttribute("position");
  if (!(attribute instanceof THREE.BufferAttribute)) {
    throw new Error("Abstract bust preview position attribute is missing");
  }
  const target = attribute.array;
  if (!(target instanceof Float32Array) || target.length !== positions.length) {
    throw new Error("Abstract bust preview position attribute has an invalid shape");
  }
  target.set(positions);
  attribute.needsUpdate = true;
  geometry.computeBoundingBox();
  geometry.computeBoundingSphere();
  return attribute;
}

export class AbstractBustThreeScene {
  private readonly container: HTMLElement;
  private readonly scene: THREE.Scene;
  private readonly renderer: THREE.WebGLRenderer;
  private readonly camera: THREE.PerspectiveCamera;
  private readonly controls: OrbitControls;
  private readonly geometry: THREE.BufferGeometry;
  private readonly material: THREE.PointsMaterial;
  private readonly points: THREE.Points;
  private readonly initializedAt: number;
  private readonly onContextError: (message: string | null) => void;
  private frameId: number | null = null;
  private disposed = false;
  private hasGeometry = false;
  private lastGenerated: GeneratedAbstractBust | null = null;
  private mode: AbstractBustCameraMode = "front";

  constructor(
    container: HTMLElement,
    onContextError: (message: string | null) => void
  ) {
    const startedAt = performance.now();
    this.container = container;
    this.onContextError = onContextError;
    this.scene = new THREE.Scene();
    this.camera = new THREE.PerspectiveCamera(CAMERA_FOV, 1, 0.01, 20);
    this.renderer = createAbstractBustWebGLRenderer();
    rendererCounters.created += 1;
    rendererCounters.active += 1;
    this.renderer.setClearColor(0x00_00_00, 0);
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    this.renderer.domElement.className = "abstract-bust-preview__canvas";
    this.renderer.domElement.setAttribute("aria-label", "Abstract bust particle preview");
    this.renderer.domElement.addEventListener(
      "webglcontextlost",
      this.handleContextLost
    );
    this.renderer.domElement.addEventListener(
      "webglcontextrestored",
      this.handleContextRestored
    );
    container.appendChild(this.renderer.domElement);

    this.geometry = createAbstractBustPreviewGeometry();
    this.material = new THREE.PointsMaterial({
      color: PREVIEW_COLOR,
      size: 0.008,
      sizeAttenuation: true,
      transparent: false,
      depthWrite: true,
    });
    this.points = new THREE.Points(this.geometry, this.material);
    this.scene.add(this.points);

    this.controls = new OrbitControls(
      this.camera,
      this.renderer.domElement
    );
    this.controls.enableDamping = true;
    this.controls.dampingFactor = 0.1;
    this.controls.enablePan = false;
    this.controls.minPolarAngle = 0.08;
    this.controls.maxPolarAngle = Math.PI - 0.08;
    this.controls.autoRotateSpeed = 1.25;
    this.initializedAt = performance.now() - startedAt;
    this.startRendering();
  }

  private readonly handleContextLost = (event: Event) => {
    handleAbstractBustContextLost(event, this.onContextError);
  };

  private readonly handleContextRestored = () => {
    handleAbstractBustContextRestored(
      () => this.renderer.resetState(),
      this.onContextError
    );
  };

  private startRendering(): void {
    const render = () => {
      if (this.disposed) return;
      this.controls.update();
      this.renderer.render(this.scene, this.camera);
      this.frameId = window.requestAnimationFrame(render);
    };
    this.frameId = window.requestAnimationFrame(render);
  }

  resize(width: number, height: number): void {
    if (this.disposed || width <= 0 || height <= 0) return;
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    this.renderer.setSize(width, height, false);
    this.camera.aspect = width / height;
    this.camera.updateProjectionMatrix();
    if (this.lastGenerated && this.mode !== "free" && this.mode !== "auto") {
      this.applyView(this.mode);
    }
  }

  updateGenerated(result: GeneratedAbstractBust): void {
    updateAbstractBustPreviewGeometry(this.geometry, result.positions);
    this.lastGenerated = result;
    if (!this.hasGeometry) {
      this.hasGeometry = true;
      this.applyView("front");
    } else {
      const center = result.bounds.min.map(
        (minimum, axis) => (minimum + result.bounds.max[axis]) * 0.5
      );
      this.controls.target.set(center[0], center[1], center[2]);
      this.controls.update();
    }
  }

  setMode(mode: AbstractBustCameraMode): void {
    this.mode = mode;
    this.controls.autoRotate = mode === "auto";
    this.controls.enabled = true;
    if (mode === "front" || mode === "side") {
      this.applyView(mode);
    }
  }

  resetView(): void {
    this.mode = "front";
    this.controls.autoRotate = false;
    this.applyView("front");
  }

  private applyView(view: "front" | "side"): void {
    if (!this.lastGenerated) return;
    const pose = deriveAbstractBustCameraPose(
      this.lastGenerated.bounds,
      view,
      CAMERA_FOV,
      this.camera.aspect
    );
    this.camera.position.set(...pose.position);
    this.camera.near = pose.near;
    this.camera.far = pose.far;
    this.camera.updateProjectionMatrix();
    this.controls.target.set(...pose.target);
    this.controls.minDistance = pose.minDistance;
    this.controls.maxDistance = pose.maxDistance;
    this.controls.update();
  }

  diagnostics(
    generationCount: number,
    lastUpdateMs: number
  ): AbstractBustPreviewDiagnostics {
    return Object.freeze({
      initializationMs: this.initializedAt,
      lastUpdateMs,
      generationCount,
      renderersCreated: rendererCounters.created,
      renderersDisposed: rendererCounters.disposed,
      activeContexts: rendererCounters.active,
    });
  }

  dispose(): void {
    if (this.disposed) return;
    this.disposed = true;
    if (this.frameId !== null) {
      window.cancelAnimationFrame(this.frameId);
      this.frameId = null;
    }
    this.renderer.domElement.removeEventListener(
      "webglcontextlost",
      this.handleContextLost
    );
    this.renderer.domElement.removeEventListener(
      "webglcontextrestored",
      this.handleContextRestored
    );
    disposeAbstractBustPreviewResources({
      controls: this.controls,
      geometry: this.geometry,
      material: this.material,
      renderer: this.renderer,
    });
    this.renderer.domElement.remove();
    rendererCounters.disposed += 1;
    rendererCounters.active = Math.max(0, rendererCounters.active - 1);
  }
}
