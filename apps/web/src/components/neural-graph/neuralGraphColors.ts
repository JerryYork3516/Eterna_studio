const FALLBACK_LAYER_COLORS = [
  "#4f8cff",
  "#22c55e",
  "#f59e0b",
  "#ef4444",
  "#06b6d4",
  "#8b5cf6",
  "#14b8a6",
  "#f97316",
  "#a855f7",
  "#38bdf8",
  "#ec4899",
  "#84cc16",
  "#eab308",
];

type Rgb = {
  r: number;
  g: number;
  b: number;
};

function clampChannel(value: number) {
  return Math.max(0, Math.min(255, Math.round(value)));
}

function normalizeHex(value: string) {
  const trimmed = value.trim();
  if (/^#[0-9a-fA-F]{6}$/.test(trimmed)) {
    return trimmed;
  }
  if (/^#[0-9a-fA-F]{3}$/.test(trimmed)) {
    const [, r, g, b] = trimmed;
    return `#${r}${r}${g}${g}${b}${b}`;
  }
  return "";
}

function hexToRgb(value: string): Rgb | null {
  const hex = normalizeHex(value);
  if (!hex) {
    return null;
  }
  return {
    r: Number.parseInt(hex.slice(1, 3), 16),
    g: Number.parseInt(hex.slice(3, 5), 16),
    b: Number.parseInt(hex.slice(5, 7), 16),
  };
}

function rgbToHex({ r, g, b }: Rgb) {
  return `#${clampChannel(r).toString(16).padStart(2, "0")}${clampChannel(g).toString(16).padStart(2, "0")}${clampChannel(b).toString(16).padStart(2, "0")}`;
}

export function softenColor(color: string, amount = 0.22) {
  const rgb = hexToRgb(color);
  if (!rgb) {
    return color;
  }
  return rgbToHex({
    r: rgb.r + (255 - rgb.r) * amount,
    g: rgb.g + (255 - rgb.g) * amount,
    b: rgb.b + (255 - rgb.b) * amount,
  });
}

export function fallbackLayerColor(layerOrder?: number) {
  const index = Math.max(0, (layerOrder ?? 1) - 1);
  return FALLBACK_LAYER_COLORS[index % FALLBACK_LAYER_COLORS.length];
}

export function resolveLayerColor(layerId: string, layerOrder: number | undefined, uiColors?: Record<string, string>) {
  return normalizeHex(uiColors?.[layerId] ?? "") || normalizeHex(uiColors?.[`ui-folder-${layerId}`] ?? "") || fallbackLayerColor(layerOrder);
}

export function resolveModuleColor({
  moduleId,
  layerId,
  storedLayerId,
  layerColor,
  moduleUiColors,
}: {
  moduleId: string;
  layerId: string;
  storedLayerId: string;
  layerColor: string;
  moduleUiColors?: Record<string, string>;
}) {
  const suffixMatch = Object.entries(moduleUiColors ?? {}).find(([key, value]) => key.endsWith(`:${moduleId}`) && normalizeHex(value));
  return (
    normalizeHex(moduleUiColors?.[`${layerId}:${moduleId}`] ?? "") ||
    normalizeHex(moduleUiColors?.[`${storedLayerId}:${moduleId}`] ?? "") ||
    normalizeHex(suffixMatch?.[1] ?? "") ||
    layerColor
  );
}

export function mixColors(colors: string[]) {
  const rgbs = colors.map(hexToRgb).filter((rgb): rgb is Rgb => Boolean(rgb));
  if (!rgbs.length) {
    return "#4f8cff";
  }
  const total = rgbs.reduce(
    (sum, rgb) => ({
      r: sum.r + rgb.r,
      g: sum.g + rgb.g,
      b: sum.b + rgb.b,
    }),
    { r: 0, g: 0, b: 0 }
  );
  return softenColor(
    rgbToHex({
      r: total.r / rgbs.length,
      g: total.g / rgbs.length,
      b: total.b / rgbs.length,
    }),
    0.16
  );
}
