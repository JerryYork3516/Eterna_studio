"use client";

import { useCallback, useEffect, useMemo, useRef, useState, type WheelEvent as ReactWheelEvent } from "react";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { Html, Line, OrbitControls } from "@react-three/drei";
import { Vector3 } from "three";
import type { ThreeEvent } from "@react-three/fiber";
import type { NeuralGraphNode, NeuralGraphSelection, NeuralGraphToggles, ResidentNeuralGraph } from "./neuralGraphTypes";

type TFunction = (key: string, fallback?: string) => string;
const DEFAULT_CAMERA_POSITION: [number, number, number] = [6, 5, 8];
const DEFAULT_CAMERA_TARGET: [number, number, number] = [0, 0, 0];
type PreviewTransitionPhase = "idle" | "entering" | "exiting";

function moduleRadius(node: NeuralGraphNode, selected: boolean, focused: boolean) {
  const degreeBoost = Math.min(0.07, ((node.nodeCount ?? 0) / 40) * 0.04);
  const base = Math.min(0.18, 0.11 + degreeBoost);
  return focused ? base * 1.45 : selected ? base * 1.15 : base;
}

function nodeVisible(node: NeuralGraphNode, toggles: NeuralGraphToggles, focusedModuleId: string | null, activeLayerId: string | null) {
  if (node.kind === "module") {
    if (!toggles.modules) return false;
    if (focusedModuleId) return false;
    return !activeLayerId || node.layerId === activeLayerId;
  }
  if (node.kind === "node") {
    return toggles.nodes && Boolean(focusedModuleId) && node.moduleInstanceId && `module:${node.moduleInstanceId}` === focusedModuleId;
  }
  return false;
}

function edgeColor(kind: ResidentNeuralGraph["edges"][number]["kind"], fallback: string) {
  if (kind === "references") return "#60a5fa";
  if (kind === "outputs_to") return "#a78bfa";
  if (kind === "constrains") return "#e5e7eb";
  if (kind === "conflicts_with") return "#ef4444";
  if (kind === "overrides_forbidden") return "#f97316";
  return fallback;
}

function targetForCamera(focusedNode: NeuralGraphNode | null, orbitNode: NeuralGraphNode | null, coverNode: NeuralGraphNode | null) {
  if (coverNode) {
    const [x, y, z] = coverNode.position;
    return {
      position: new Vector3(x + 0.16, y + 0.1, z + 0.28),
      target: new Vector3(x, y, z),
    };
  }
  if (focusedNode) {
    return {
      position: new Vector3(0, 0.78, 4.35),
      target: new Vector3(0, 0, 0),
    };
  }
  if (orbitNode) {
    const [x, y, z] = orbitNode.position;
    return {
      position: new Vector3(x + 1.2, y + 0.82, z + 2.28),
      target: new Vector3(x, y, z),
    };
  }
  return {
    position: new Vector3(...DEFAULT_CAMERA_POSITION),
    target: new Vector3(...DEFAULT_CAMERA_TARGET),
  };
}

function CameraRig({
  focusedNode,
  orbitNode,
  coverNode,
}: {
  focusedNode: NeuralGraphNode | null;
  orbitNode: NeuralGraphNode | null;
  coverNode: NeuralGraphNode | null;
}) {
  const controlsRef = useRef<any>(null);
  const isTransitioningRef = useRef(false);
  const targetSignatureRef = useRef("");
  const { camera } = useThree();
  const target = useMemo(() => targetForCamera(focusedNode, orbitNode, coverNode), [coverNode, focusedNode, orbitNode]);

  useEffect(() => {
    const signature = [
      target.position.x.toFixed(3),
      target.position.y.toFixed(3),
      target.position.z.toFixed(3),
      target.target.x.toFixed(3),
      target.target.y.toFixed(3),
      target.target.z.toFixed(3),
    ].join(":");
    if (!targetSignatureRef.current) {
      targetSignatureRef.current = signature;
      isTransitioningRef.current = Boolean(focusedNode || orbitNode || coverNode);
      return;
    }
    if (targetSignatureRef.current !== signature) {
      targetSignatureRef.current = signature;
      isTransitioningRef.current = true;
    }
  }, [coverNode, focusedNode, orbitNode, target]);

  useFrame((_, delta) => {
    if (!isTransitioningRef.current) {
      return;
    }
    const step = 1 - Math.exp(-delta * 3.15);
    camera.position.lerp(target.position, step);
    if (controlsRef.current?.target) {
      controlsRef.current.target.lerp(target.target, step);
      controlsRef.current.update();
    }
    const cameraArrived = camera.position.distanceTo(target.position) < 0.015;
    const targetArrived = !controlsRef.current?.target || controlsRef.current.target.distanceTo(target.target) < 0.015;
    if (cameraArrived && targetArrived) {
      isTransitioningRef.current = false;
    }
  });

  return <OrbitControls ref={controlsRef} enableDamping dampingFactor={0.12} minDistance={0.26} maxDistance={28} />;
}

function BackgroundStars() {
  const stars = useMemo(() => {
    return Array.from({ length: 90 }, (_, index) => {
      const theta = index * Math.PI * (3 - Math.sqrt(5));
      const y = 1 - 2 * ((index + 0.5) / 90);
      const r = Math.sqrt(Math.max(0, 1 - y * y));
      const radius = 5.6 + (index % 7) * 0.38;
      return [Math.cos(theta) * r * radius, y * radius * 0.7, Math.sin(theta) * r * radius] as [number, number, number];
    });
  }, []);

  return (
    <>
      {stars.map((position, index) => (
        <mesh key={index} position={position}>
          <sphereGeometry args={[0.01 + (index % 3) * 0.004, 6, 6]} />
          <meshBasicMaterial color={index % 5 === 0 ? "#7aa2f7" : "#cbd5e1"} transparent opacity={0.22} />
        </mesh>
      ))}
    </>
  );
}

function LayerClusterAnchor({ node, showLabel, onSelect }: { node: NeuralGraphNode; showLabel: boolean; onSelect: (node: NeuralGraphNode) => void }) {
  const color = node.color ?? "#4f8cff";
  const label = `${node.shortLabel ?? `L${node.layerOrder ?? ""}`} ${node.label}`;

  return (
    <group position={node.position}>
      <mesh
        onClick={(event) => {
          event.stopPropagation();
          onSelect(node);
        }}
      >
        <sphereGeometry args={[node.layerOrder === 1 ? 0.085 : 0.055, 16, 12]} />
        <meshStandardMaterial color={color} emissive={color} emissiveIntensity={0.62} transparent opacity={node.layerOrder === 1 ? 0.74 : 0.48} />
      </mesh>
      <mesh scale={[1.9, 1.9, 1.9]}>
        <sphereGeometry args={[node.layerOrder === 1 ? 0.085 : 0.055, 16, 12]} />
        <meshBasicMaterial color={color} transparent opacity={node.layerOrder === 1 ? 0.1 : 0.055} depthWrite={false} />
      </mesh>
      {showLabel ? (
        <Html center position={[0, node.layerOrder === 1 ? 0.24 : 0.18, 0]} transform={false} occlude={false} style={{ pointerEvents: "none" }}>
          <div className="resident-neural-graph-layer-anchor" style={{ borderColor: color }}>
            {label}
          </div>
        </Html>
      ) : null}
    </group>
  );
}

function ResidentCore({ t }: { t: TFunction }) {
  return (
    <group position={[0, 0, 0]}>
      <mesh>
        <sphereGeometry args={[0.13, 24, 18]} />
        <meshStandardMaterial color="#dbeafe" emissive="#8fb7ff" emissiveIntensity={0.72} transparent opacity={0.82} />
      </mesh>
      <mesh scale={[2.5, 2.5, 2.5]}>
        <sphereGeometry args={[0.13, 24, 18]} />
        <meshBasicMaterial color="#8fb7ff" transparent opacity={0.08} depthWrite={false} />
      </mesh>
      <Html center position={[0, 0.32, 0]} transform={false} occlude={false} style={{ pointerEvents: "none" }}>
        <div className="resident-neural-graph-core-label">{t("neuralGraph.residentCore", "Resident Core")}</div>
      </Html>
    </group>
  );
}

function GraphNodeMesh({
  node,
  position,
  selected,
  faded,
  focused,
  related,
  onSelect,
  onOrbitFocusModule,
  showAmbientLabel,
}: {
  node: NeuralGraphNode;
  position: [number, number, number];
  selected: boolean;
  faded: boolean;
  focused: boolean;
  related: boolean;
  onSelect: (node: NeuralGraphNode) => void;
  onOrbitFocusModule: (nodeId: string) => void;
  showAmbientLabel: boolean;
}) {
  const [hovered, setHovered] = useState(false);
  const color = node.color ?? (node.kind === "node" ? "#dbeafe" : "#4f8cff");
  const radius = node.kind === "module" ? moduleRadius(node, selected, focused) : 0.055;
  const opacity = faded ? 0.26 : node.kind === "module" ? 0.94 : 0.9;
  const emissiveIntensity = node.kind === "module" ? (selected || focused || hovered ? 1.15 : related ? 0.88 : 0.58) : 1.0;

  function handleClick(event: ThreeEvent<MouseEvent>) {
    event.stopPropagation();
    onSelect(node);
  }

  function handleDoubleClick(event: ThreeEvent<MouseEvent>) {
    event.stopPropagation();
    onSelect(node);
    if (node.kind === "module") {
      onOrbitFocusModule(node.id);
    }
  }

  return (
    <group position={position}>
      {node.kind === "module" ? (
        <mesh onClick={handleClick} onDoubleClick={handleDoubleClick}>
          <sphereGeometry args={[radius * 2.2, 12, 10]} />
          <meshBasicMaterial transparent opacity={0} depthWrite={false} />
        </mesh>
      ) : null}
      {(selected || focused || hovered) && node.kind === "module" ? (
        <mesh scale={[1.7, 1.7, 1.7]}>
          <sphereGeometry args={[radius, 24, 18]} />
          <meshBasicMaterial color={color} transparent opacity={0.18} depthWrite={false} />
        </mesh>
      ) : null}
      <mesh
        onClick={handleClick}
        onDoubleClick={handleDoubleClick}
        scale={selected || focused ? [1.12, 1.12, 1.12] : [1, 1, 1]}
        onPointerOver={(event) => {
          event.stopPropagation();
          setHovered(true);
        }}
        onPointerOut={() => setHovered(false)}
      >
        <sphereGeometry args={[radius, node.kind === "node" ? 12 : 24, node.kind === "node" ? 10 : 18]} />
        <meshStandardMaterial
          color={color}
          emissive={color}
          emissiveIntensity={emissiveIntensity}
          transparent
          opacity={opacity}
          roughness={0.38}
        />
      </mesh>
      {node.kind === "module" && !faded && (showAmbientLabel || hovered || selected || focused) ? (
        <Html center position={[0, radius + 0.18, 0]} transform={false} occlude={false} style={{ pointerEvents: "none" }}>
          <div className={`resident-neural-graph-module-label ${selected || focused || hovered ? "is-selected" : ""}`} style={{ borderColor: color }}>
            {node.shortLabel ?? node.label}
          </div>
        </Html>
      ) : null}
      {node.kind === "node" ? (
        <Html center position={[0, radius + 0.1, 0]} transform={false} occlude={false} style={{ pointerEvents: "none" }}>
          <div className={`resident-neural-graph-preview-node ${selected || hovered ? "is-selected" : ""}`} style={{ borderColor: color }}>
            {node.shortLabel ?? node.label}
          </div>
        </Html>
      ) : null}
      {hovered && node.kind !== "module" && node.kind !== "node" ? (
        <Html center position={[0, radius + 0.31, 0]} transform={false} occlude={false} style={{ pointerEvents: "none" }}>
          <div className="resident-neural-graph__hover-label" style={{ borderColor: color }}>
            {node.label}
          </div>
        </Html>
      ) : null}
    </group>
  );
}

export function ResidentNeuralGraphScene({
  graph,
  toggles,
  selection,
  focusedModuleId,
  activeLayerId,
  t,
  onSelect,
  onFocusModule,
  onExitFocus,
}: {
  graph: ResidentNeuralGraph;
  toggles: NeuralGraphToggles;
  selection: NeuralGraphSelection;
  focusedModuleId: string | null;
  activeLayerId: string | null;
  t: TFunction;
  onSelect: (node: NeuralGraphNode | null) => void;
  onFocusModule: (nodeId: string) => void;
  onExitFocus: () => void;
}) {
  const [viewKey, setViewKey] = useState(0);
  const [orbitFocusModuleId, setOrbitFocusModuleId] = useState<string | null>(null);
  const [coverModuleId, setCoverModuleId] = useState<string | null>(null);
  const [transitionPhase, setTransitionPhase] = useState<PreviewTransitionPhase>("idle");
  const zoomIntentRef = useRef({ moduleId: "", amount: 0, steps: 0, lastAt: 0 });
  const transitionTimersRef = useRef<number[]>([]);
  const nodeById = useMemo(() => new Map(graph.nodes.map((node) => [node.id, node])), [graph.nodes]);
  const focusedNode = focusedModuleId ? nodeById.get(focusedModuleId) : null;
  const orbitNode = orbitFocusModuleId ? nodeById.get(orbitFocusModuleId) ?? null : null;
  const coverNode = coverModuleId ? nodeById.get(coverModuleId) ?? null : null;
  const relatedIds = useMemo(() => {
    if (!selection || selection.kind !== "module") return new Set<string>();
    const ids = new Set<string>([selection.id]);
    for (const edge of graph.edges) {
      if (edge.kind === "contains") continue;
      if (edge.source === selection.id) ids.add(edge.target);
      if (edge.target === selection.id) ids.add(edge.source);
    }
    return ids;
  }, [graph.edges, selection]);

  function renderPosition(node: NeuralGraphNode): [number, number, number] {
    if (!focusedNode) {
      return node.position;
    }
    if (node.id === focusedNode.id) {
      return [0, 0, 0];
    }
    if (node.kind === "node" && node.moduleInstanceId && `module:${node.moduleInstanceId}` === focusedNode.id) {
      return [
        node.position[0] - focusedNode.position[0],
        node.position[1] - focusedNode.position[1],
        node.position[2] - focusedNode.position[2],
      ];
    }
    return node.position;
  }

  const visibleNodes = useMemo(
    () => graph.nodes.filter((node) => nodeVisible(node, toggles, focusedModuleId, activeLayerId)),
    [activeLayerId, focusedModuleId, graph.nodes, toggles]
  );
  const layerAnchors = useMemo(
    () =>
      graph.nodes.filter(
        (node) => node.kind === "layer" && toggles.layers && !focusedModuleId && (!activeLayerId || node.layerId === activeLayerId || node.layerOrder === 1)
      ),
    [activeLayerId, focusedModuleId, graph.nodes, toggles.layers]
  );
  const visibleEdges = useMemo(() => {
    const selectedModuleId = selection?.kind === "module" ? selection.id : "";
    return graph.edges.filter((edge) => {
      if (edge.kind === "contains") {
        return false;
      }
      const source = nodeById.get(edge.source);
      const target = nodeById.get(edge.target);
      if (!source || !target) {
        return false;
      }
      if (focusedModuleId) {
        return Boolean(
          source.kind === "node" &&
            target.kind === "node" &&
            nodeVisible(source, toggles, focusedModuleId, activeLayerId) &&
            nodeVisible(target, toggles, focusedModuleId, activeLayerId)
        );
      }
      if (source.kind !== "module" || target.kind !== "module") {
        return false;
      }
      if (activeLayerId && source.layerId !== activeLayerId && target.layerId !== activeLayerId) {
        return false;
      }
      if (selectedModuleId) {
        return edge.source === selectedModuleId || edge.target === selectedModuleId;
      }
      return toggles.edges;
    });
  }, [activeLayerId, focusedModuleId, graph.edges, nodeById, selection, toggles]);
  const previewNodeCount = visibleNodes.filter((node) => node.kind === "node").length;
  const clearTransitionTimers = useCallback(() => {
    transitionTimersRef.current.forEach((timer) => window.clearTimeout(timer));
    transitionTimersRef.current = [];
  }, []);
  const scheduleTransition = useCallback((callback: () => void, delay: number) => {
    const timer = window.setTimeout(callback, delay);
    transitionTimersRef.current.push(timer);
  }, []);
  const beginPreviewTransition = useCallback(
    (moduleId: string) => {
      clearTransitionTimers();
      setOrbitFocusModuleId(moduleId);
      setCoverModuleId(moduleId);
      setTransitionPhase("entering");
      scheduleTransition(() => onFocusModule(moduleId), 560);
      scheduleTransition(() => setCoverModuleId(null), 680);
      scheduleTransition(() => setTransitionPhase("idle"), 980);
    },
    [clearTransitionTimers, onFocusModule, scheduleTransition]
  );
  const exitPreviewTransition = useCallback(() => {
    if (!focusedModuleId) {
      return;
    }
    clearTransitionTimers();
    const moduleId = focusedModuleId;
    setOrbitFocusModuleId(moduleId);
    setCoverModuleId(moduleId);
    setTransitionPhase("exiting");
    scheduleTransition(() => onExitFocus(), 460);
    scheduleTransition(() => setCoverModuleId(null), 620);
    scheduleTransition(() => setTransitionPhase("idle"), 980);
  }, [clearTransitionTimers, focusedModuleId, onExitFocus, scheduleTransition]);

  useEffect(() => () => clearTransitionTimers(), [clearTransitionTimers]);

  const handleCanvasWheel = useCallback(
    (event: ReactWheelEvent<HTMLDivElement>) => {
      if (focusedModuleId) {
        zoomIntentRef.current = { moduleId: "", amount: 0, steps: 0, lastAt: 0 };
        if (event.deltaY > 0) {
          exitPreviewTransition();
        }
        return;
      }
      if (selection?.kind !== "module") {
        zoomIntentRef.current = { moduleId: "", amount: 0, steps: 0, lastAt: 0 };
        return;
      }
      const now = Date.now();
      if (zoomIntentRef.current.moduleId !== selection.id) {
        zoomIntentRef.current = { moduleId: selection.id, amount: 0, steps: 0, lastAt: 0 };
      }
      if (now - zoomIntentRef.current.lastAt > 1400) {
        zoomIntentRef.current.amount = 0;
        zoomIntentRef.current.steps = 0;
      }
      if (event.deltaY >= 0) {
        zoomIntentRef.current.amount = 0;
        zoomIntentRef.current.steps = 0;
        zoomIntentRef.current.lastAt = now;
        return;
      }
      zoomIntentRef.current.amount += Math.min(140, Math.abs(event.deltaY));
      zoomIntentRef.current.steps += 1;
      zoomIntentRef.current.lastAt = now;
      if (zoomIntentRef.current.amount >= 1800 && zoomIntentRef.current.steps >= 8) {
        zoomIntentRef.current = { moduleId: selection.id, amount: 0, steps: 0, lastAt: 0 };
        beginPreviewTransition(selection.id);
      }
    },
    [beginPreviewTransition, exitPreviewTransition, focusedModuleId, selection]
  );

  useEffect(() => {
    zoomIntentRef.current = { moduleId: selection?.kind === "module" ? selection.id : "", amount: 0, steps: 0, lastAt: 0 };
  }, [focusedModuleId, selection?.id, selection?.kind]);

  return (
    <div className="resident-neural-graph-scene">
      <button
        type="button"
        className="resident-neural-graph-scene__reset"
        onClick={() => {
          setViewKey((value) => value + 1);
          clearTransitionTimers();
          setOrbitFocusModuleId(null);
          setCoverModuleId(null);
          setTransitionPhase("idle");
          onSelect(null);
          onExitFocus();
        }}
      >
        {t("neuralGraph.view.reset", "Reset View")}
      </button>
      <Canvas
        key={viewKey}
        gl={{ preserveDrawingBuffer: true }}
        camera={{ position: DEFAULT_CAMERA_POSITION, fov: 48 }}
        onWheel={handleCanvasWheel}
        onPointerMissed={() => {
          setOrbitFocusModuleId(null);
          setCoverModuleId(null);
          onSelect(null);
        }}
      >
        <color attach="background" args={["#060914"]} />
        <ambientLight intensity={0.58} />
        <pointLight position={[2, 4, 6]} intensity={0.95} />
        <pointLight position={[-5, -3, -6]} intensity={0.28} color="#7aa2f7" />
        <BackgroundStars />
        {!focusedModuleId ? <ResidentCore t={t} /> : null}
        {layerAnchors.map((node) => (
          <LayerClusterAnchor key={node.id} node={node} showLabel={toggles.layerLabels} onSelect={onSelect} />
        ))}
        {visibleEdges.map((edge) => {
          const source = nodeById.get(edge.source);
          const target = nodeById.get(edge.target);
          if (!source || !target) return null;
          const active = selection?.id === source.id || selection?.id === target.id || focusedModuleId === source.id;
          const color = edgeColor(edge.kind, source.color ?? "#60a5fa");
          const points = [renderPosition(source), renderPosition(target)] as [[number, number, number], [number, number, number]];
          return (
            <group key={edge.id}>
              <Line points={points} color={color} lineWidth={active ? 6.2 : 3.2} transparent opacity={active ? 0.28 : 0.12} depthWrite={false} />
              <Line points={points} color={color} lineWidth={active ? 2.6 : 1.45} transparent opacity={active ? 0.92 : 0.48} depthWrite={false} />
            </group>
          );
        })}
        {visibleNodes.map((node) => (
          <GraphNodeMesh
            key={node.id}
            node={node}
            position={renderPosition(node)}
            selected={selection?.id === node.id}
            faded={Boolean(selection?.kind === "module" && relatedIds.size > 1 && !relatedIds.has(node.id))}
            focused={node.id === focusedModuleId}
            related={relatedIds.has(node.id)}
            onSelect={onSelect}
            onOrbitFocusModule={setOrbitFocusModuleId}
            showAmbientLabel={node.kind === "module" && toggles.moduleLabels}
          />
        ))}
        {focusedModuleId ? (
          <Html center position={[0, 1.34, 0]} transform={false} occlude={false} style={{ pointerEvents: "none" }}>
            <div className="resident-neural-graph-preview-title">{t("neuralGraph.modulePreview", "Module Preview")}</div>
          </Html>
        ) : null}
        {focusedModuleId && previewNodeCount === 0 ? (
          <Html center position={[0, 0, 0]} transform={false} occlude={false} style={{ pointerEvents: "none" }}>
            <div className="resident-neural-graph-preview-empty">{t("neuralGraph.emptyModule", "This module has no internal nodes")}</div>
          </Html>
        ) : null}
        <CameraRig focusedNode={focusedNode ?? null} orbitNode={orbitNode} coverNode={coverNode} />
      </Canvas>
      <div className={`resident-neural-graph-scene__fade ${transitionPhase !== "idle" ? "is-active" : ""}`} />
    </div>
  );
}
