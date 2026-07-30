export type AbstractBustCameraMode =
  | "front"
  | "side"
  | "free"
  | "auto";

export type AbstractBustPreviewDiagnostics = Readonly<{
  initializationMs: number;
  lastUpdateMs: number;
  generationCount: number;
  renderersCreated: number;
  renderersDisposed: number;
  activeContexts: number;
}>;

export type AbstractBustPreviewSummary = Readonly<{
  particleCount: number;
  digest: string | null;
  error: string | null;
  diagnostics: AbstractBustPreviewDiagnostics;
}>;
