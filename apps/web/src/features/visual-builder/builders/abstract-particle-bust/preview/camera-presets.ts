import type { AbstractBustBounds } from "../types.ts";

export type AbstractBustCameraPose = Readonly<{
  target: readonly [number, number, number];
  position: readonly [number, number, number];
  near: number;
  far: number;
  minDistance: number;
  maxDistance: number;
}>;

export function deriveAbstractBustCameraPose(
  bounds: AbstractBustBounds,
  view: "front" | "side",
  fieldOfViewDegrees: number,
  aspect: number
): AbstractBustCameraPose {
  const center = bounds.min.map(
    (minimum, axis) => (minimum + bounds.max[axis]) * 0.5
  ) as [number, number, number];
  const halfExtents = bounds.min.map(
    (minimum, axis) => Math.max(0.001, (bounds.max[axis] - minimum) * 0.5)
  ) as [number, number, number];
  const radius = Math.hypot(...halfExtents);
  const verticalFov = fieldOfViewDegrees * Math.PI / 180;
  const horizontalFov = 2 * Math.atan(Math.tan(verticalFov * 0.5) * Math.max(aspect, 0.1));
  const limitingFov = Math.min(verticalFov, horizontalFov);
  const distance = Math.max(
    radius * 2.2,
    radius / Math.max(Math.sin(limitingFov * 0.5), 0.05) * 1.15
  );
  const direction = view === "front"
    ? ([0, 0, 1] as const)
    : ([1, 0, 0] as const);

  return Object.freeze({
    target: Object.freeze(center),
    position: Object.freeze([
      center[0] + direction[0] * distance,
      center[1] + direction[1] * distance,
      center[2] + direction[2] * distance,
    ] as [number, number, number]),
    near: Math.max(0.001, distance - radius * 2.5),
    far: distance + radius * 8,
    minDistance: Math.max(radius * 1.15, 0.25),
    maxDistance: Math.max(radius * 8, 4),
  });
}
