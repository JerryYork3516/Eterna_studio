import {
  ABSTRACT_BUST_GENERATOR_VERSION,
  normalizeAbstractBustBlueprint,
  type AbstractBustBlueprint,
} from "@eterna/shared-schema/abstract-bust-blueprint";
import {
  ABSTRACT_PARTICLE_BUST_BUILDER_ID,
} from "./builder-registry.ts";
import {
  normalizeVisualAsset,
  type AbstractParticleBustVisualAsset,
} from "./visual-asset.ts";

export const VISUAL_ASSET_BINDING_DIGEST_VERSION =
  "fnv1a64-canonical-json-v1" as const;
export const VISUAL_ASSET_BINDING_DIGEST_PREFIX =
  `${VISUAL_ASSET_BINDING_DIGEST_VERSION}:` as const;

export const RESIDENT_IDENTITY_LAYER_ID = "layer_1" as const;
export const RESIDENT_IDENTITY_MODULE_ID = "module_basic_identity" as const;
export const RESIDENT_IDENTITY_FIELD_KEY = "resident_id" as const;
export const PARTICLE_AVATAR_LAYER_ID = "layer_10" as const;
export const PARTICLE_AVATAR_MODULE_ID = "particle_avatar" as const;
export const PARTICLE_VISUAL_CONFIG_INPUT_NODE_ID =
  "particle_visual_config_input" as const;
export const ABSTRACT_BUST_BLUEPRINT_FIELD_KEY =
  "abstract_bust_blueprint" as const;

export interface VisualAssetBinding {
  resident_scope_id: string;
  module_instance_id: string;
  asset_id: string;
  asset_revision: number;
  builder_id: typeof ABSTRACT_PARTICLE_BUST_BUILDER_ID;
  appearance_type: "abstract_particle_bust";
  generator_version: typeof ABSTRACT_BUST_GENERATOR_VERSION;
  blueprint_digest: `${typeof VISUAL_ASSET_BINDING_DIGEST_PREFIX}${string}`;
  bound_at: string;
  updated_at: string;
}

export interface ModuleGraphStudioMetadata {
  visualAssetBinding?: VisualAssetBinding;
  [key: string]: unknown;
}

export type VisualAssetBindingState =
  | "unbound"
  | "in_sync"
  | "out_of_sync"
  | "invalid";

export type VisualAssetBindingErrorCode =
  | "identity_attachment_missing"
  | "identity_attachment_duplicate"
  | "identity_registry_missing"
  | "identity_registry_duplicate"
  | "identity_registry_invalid"
  | "identity_graph_missing"
  | "resident_id_field_missing"
  | "resident_id_field_duplicate"
  | "resident_id_invalid"
  | "particle_attachment_missing"
  | "particle_attachment_duplicate"
  | "particle_registry_missing"
  | "particle_registry_duplicate"
  | "particle_registry_invalid"
  | "particle_graph_missing"
  | "particle_input_missing"
  | "particle_input_duplicate"
  | "blueprint_field_missing"
  | "blueprint_field_duplicate"
  | "blueprint_invalid"
  | "binding_invalid"
  | "binding_scope_mismatch"
  | "binding_instance_mismatch"
  | "binding_asset_missing"
  | "asset_invalid"
  | "asset_mismatch"
  | "asset_revision_stale"
  | "timestamp_invalid"
  | "canonical_json_invalid";

export class VisualAssetBindingError extends Error {
  readonly code: VisualAssetBindingErrorCode;
  readonly path?: string;

  constructor(
    code: VisualAssetBindingErrorCode,
    message: string,
    path?: string
  ) {
    super(message);
    this.name = "VisualAssetBindingError";
    this.code = code;
    this.path = path;
  }
}

export interface VisualAssetBindingModuleInstance {
  instanceId: string;
  moduleId: string;
  layerId: string;
}

export interface VisualAssetBindingModuleGraph {
  moduleNodeId?: string;
  moduleId?: string;
  nodes: unknown[];
  edges: unknown[];
  viewport?: { x: number; y: number; zoom: number };
  studioMetadata?: ModuleGraphStudioMetadata;
}

export interface VisualAssetBindingCanvasSnapshot {
  layerModules: Record<string, string[]>;
  moduleInstanceRegistry: Record<string, VisualAssetBindingModuleInstance>;
  moduleGraphs: Record<string, VisualAssetBindingModuleGraph>;
}

export interface ResidentScopeLocation {
  residentScopeId: string;
  identityInstanceId: string;
  graph: VisualAssetBindingModuleGraph;
}

export interface ParticleAvatarTargetLocation {
  moduleInstanceId: string;
  graph: VisualAssetBindingModuleGraph;
  blueprint: AbstractBustBlueprint;
  blueprintDigest: string;
  inputNodeIndex: number;
  blueprintFieldIndex: number;
}

export interface VisualAssetBindingContext
  extends ResidentScopeLocation,
    ParticleAvatarTargetLocation {
  binding?: VisualAssetBinding;
}

export interface VisualAssetBindingStatus {
  state: VisualAssetBindingState;
  reason?: VisualAssetBindingErrorCode;
  message?: string;
  residentScopeId?: string;
  moduleInstanceId?: string;
  binding?: VisualAssetBinding;
  bindingRecordPresent: boolean;
  bindingAssetId?: string;
  layerBlueprint?: AbstractBustBlueprint;
  layerBlueprintDigest?: string;
  asset?: AbstractParticleBustVisualAsset;
  assetBlueprintDigest?: string;
  layerModified: boolean;
  assetModified: boolean;
  assetMissing: boolean;
}

export interface DeriveVisualAssetBindingStatusInput
  extends VisualAssetBindingCanvasSnapshot {
  visualAssets:
    | readonly unknown[]
    | Readonly<Record<string, unknown>>;
}

export interface PrepareVisualAssetBindingInput
  extends VisualAssetBindingCanvasSnapshot {
  asset: unknown;
  now: string;
  expectedAssetRevision?: number;
}

export interface PreparedVisualAssetBinding {
  residentScopeId: string;
  moduleInstanceId: string;
  blueprint: AbstractBustBlueprint;
  blueprintDigest: string;
  previousBinding?: VisualAssetBinding;
  nextBinding: VisualAssetBinding;
  nextGraph: VisualAssetBindingModuleGraph;
}

export interface PrepareVisualAssetUnbindInput
  extends VisualAssetBindingCanvasSnapshot {}

export interface PreparedVisualAssetUnbind {
  residentScopeId: string;
  moduleInstanceId: string;
  blueprint: AbstractBustBlueprint;
  blueprintDigest: string;
  previousBinding?: VisualAssetBinding;
  nextBinding?: undefined;
  nextGraph: VisualAssetBindingModuleGraph;
}

const BINDING_KEYS = new Set([
  "resident_scope_id",
  "module_instance_id",
  "asset_id",
  "asset_revision",
  "builder_id",
  "appearance_type",
  "generator_version",
  "blueprint_digest",
  "bound_at",
  "updated_at",
]);
const FNV1A_64_OFFSET_BASIS = 0xcbf29ce484222325n;
const FNV1A_64_PRIME = 0x100000001b3n;
const DIGEST_PATTERN =
  /^fnv1a64-canonical-json-v1:[0-9a-f]{16}$/;

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

function cloneJson<T>(value: T): T {
  if (typeof structuredClone === "function") {
    return structuredClone(value);
  }
  return JSON.parse(JSON.stringify(value)) as T;
}

function requireNonEmptyString(
  value: unknown,
  code: VisualAssetBindingErrorCode,
  path: string
): string {
  if (typeof value !== "string" || !value.trim()) {
    throw new VisualAssetBindingError(
      code,
      `${path} must be a non-empty string`,
      path
    );
  }
  return value.trim();
}

function requireTimestamp(value: unknown, path: string): string {
  const timestamp = requireNonEmptyString(value, "timestamp_invalid", path);
  if (!Number.isFinite(Date.parse(timestamp))) {
    throw new VisualAssetBindingError(
      "timestamp_invalid",
      `${path} must be an ISO timestamp`,
      path
    );
  }
  return timestamp;
}

function canonicalizeJsonValue(
  value: unknown,
  path: string,
  ancestors: Set<object>
): unknown {
  if (
    value === null ||
    typeof value === "string" ||
    typeof value === "boolean"
  ) {
    return value;
  }
  if (typeof value === "number") {
    if (!Number.isFinite(value)) {
      throw new VisualAssetBindingError(
        "canonical_json_invalid",
        `${path} contains a non-finite number`,
        path
      );
    }
    return value;
  }
  if (typeof value !== "object") {
    throw new VisualAssetBindingError(
      "canonical_json_invalid",
      `${path} is not a JSON value`,
      path
    );
  }
  if (ancestors.has(value)) {
    throw new VisualAssetBindingError(
      "canonical_json_invalid",
      `${path} contains a circular reference`,
      path
    );
  }

  ancestors.add(value);
  try {
    if (Array.isArray(value)) {
      return value.map((item, index) =>
        canonicalizeJsonValue(item, `${path}[${index}]`, ancestors)
      );
    }
    const result: Record<string, unknown> = {};
    for (const key of Object.keys(value).sort()) {
      result[key] = canonicalizeJsonValue(
        (value as Record<string, unknown>)[key],
        `${path}.${key}`,
        ancestors
      );
    }
    return result;
  } finally {
    ancestors.delete(value);
  }
}

export function canonicalJsonStringify(value: unknown): string {
  return JSON.stringify(canonicalizeJsonValue(value, "$", new Set()));
}

export const stableCanonicalJsonStringify = canonicalJsonStringify;

export function fnv1a64CanonicalJsonDigest(value: unknown): string {
  const bytes = new TextEncoder().encode(canonicalJsonStringify(value));
  let digest = FNV1A_64_OFFSET_BASIS;
  for (const byte of bytes) {
    digest ^= BigInt(byte);
    digest = BigInt.asUintN(64, digest * FNV1A_64_PRIME);
  }
  return `${VISUAL_ASSET_BINDING_DIGEST_PREFIX}${digest
    .toString(16)
    .padStart(16, "0")}`;
}

export function digestAbstractBustBlueprint(value: unknown): string {
  return fnv1a64CanonicalJsonDigest(normalizeAbstractBustBlueprint(value));
}

export function digestVisualAssetBindingGraph(
  graph: VisualAssetBindingModuleGraph
): string {
  return fnv1a64CanonicalJsonDigest(graph);
}

export const fingerprintVisualAssetBindingGraph =
  digestVisualAssetBindingGraph;

function schemaNodeRecord(value: unknown): Record<string, unknown> | null {
  if (!isRecord(value)) {
    return null;
  }
  const outerData = isRecord(value.data) ? value.data : {};
  return isRecord(outerData.schemaNode) ? outerData.schemaNode : value;
}

function schemaNodeData(
  value: unknown
): Record<string, unknown> | null {
  const schemaNode = schemaNodeRecord(value);
  if (!schemaNode) {
    return null;
  }
  return isRecord(schemaNode.data) ? schemaNode.data : schemaNode;
}

function normalizedCatalogNodeId(value: unknown): string {
  const schemaNode = schemaNodeRecord(value);
  const data = schemaNodeData(value);
  const raw =
    data?.catalog_node_id ??
    schemaNode?.node_id ??
    (isRecord(value) ? value.id : "");
  return String(raw ?? "").split("::").pop() ?? "";
}

function authoritativeFields(
  node: unknown
): Record<string, unknown>[] | null {
  const data = schemaNodeData(node);
  if (!data) {
    return null;
  }
  const params = isRecord(data.params) ? data.params : {};
  if (Array.isArray(params.fields)) {
    return params.fields.filter(isRecord);
  }
  if (Array.isArray(data.fields)) {
    return data.fields.filter(isRecord);
  }
  return null;
}

function fieldKey(field: Record<string, unknown>): string {
  return String(field.field_key ?? field.field_id ?? "");
}

function fieldValue(field: Record<string, unknown>): unknown {
  return Object.prototype.hasOwnProperty.call(field, "field_value")
    ? field.field_value
    : field.value;
}

function locateUniqueAttachedInstance(
  snapshot: VisualAssetBindingCanvasSnapshot,
  layerId: string,
  moduleId: string,
  codes: {
    attachmentMissing: VisualAssetBindingErrorCode;
    attachmentDuplicate: VisualAssetBindingErrorCode;
    registryMissing: VisualAssetBindingErrorCode;
    registryDuplicate: VisualAssetBindingErrorCode;
    registryInvalid: VisualAssetBindingErrorCode;
    graphMissing: VisualAssetBindingErrorCode;
  }
): {
  instanceId: string;
  graph: VisualAssetBindingModuleGraph;
} {
  const attachmentLocations = Object.entries(snapshot.layerModules).flatMap(
    ([attachedLayerId, moduleIds]) =>
      Array.isArray(moduleIds)
        ? moduleIds
            .map((candidate, index) => ({
              attachedLayerId,
              candidate,
              index,
            }))
            .filter(({ candidate }) => candidate === moduleId)
        : []
  );
  if (attachmentLocations.length === 0) {
    throw new VisualAssetBindingError(
      codes.attachmentMissing,
      `${moduleId} is not attached exactly at ${layerId}`
    );
  }
  if (attachmentLocations.length !== 1) {
    throw new VisualAssetBindingError(
      codes.attachmentDuplicate,
      `${moduleId} must be attached exactly once and only at ${layerId}`
    );
  }
  if (attachmentLocations[0].attachedLayerId !== layerId) {
    throw new VisualAssetBindingError(
      codes.attachmentMissing,
      `${moduleId} is attached to ${attachmentLocations[0].attachedLayerId}, not ${layerId}`
    );
  }

  const registryMatches = Object.entries(
    snapshot.moduleInstanceRegistry
  ).filter(([, instance]) =>
    isRecord(instance) &&
    instance.moduleId === moduleId
  );
  if (registryMatches.length === 0) {
    throw new VisualAssetBindingError(
      codes.registryMissing,
      `${layerId}.${moduleId} has no registered instance`
    );
  }
  if (registryMatches.length !== 1) {
    throw new VisualAssetBindingError(
      codes.registryDuplicate,
      `${layerId}.${moduleId} has multiple registered instances`
    );
  }

  const [registryKey, instance] = registryMatches[0];
  const instanceId = requireNonEmptyString(
    instance.instanceId,
    codes.registryInvalid,
    "moduleInstanceRegistry.instanceId"
  );
  if (
    registryKey !== instanceId ||
    instance.layerId !== layerId ||
    instance.moduleId !== moduleId
  ) {
    throw new VisualAssetBindingError(
      codes.registryInvalid,
      `${layerId}.${moduleId} registry entry is inconsistent`
    );
  }

  const graph = snapshot.moduleGraphs[instanceId];
  if (
    !isRecord(graph) ||
    !Array.isArray(graph.nodes) ||
    !Array.isArray(graph.edges)
  ) {
    throw new VisualAssetBindingError(
      codes.graphMissing,
      `${instanceId} graph is missing or invalid`
    );
  }
  return {
    instanceId,
    graph: graph as unknown as VisualAssetBindingModuleGraph,
  };
}

function locateUniqueField(
  fields: Record<string, unknown>[] | null,
  key: string,
  missingCode: VisualAssetBindingErrorCode,
  duplicateCode: VisualAssetBindingErrorCode
): { field: Record<string, unknown>; index: number } {
  const matches = (fields ?? [])
    .map((field, index) => ({ field, index }))
    .filter(({ field }) => fieldKey(field) === key);
  if (matches.length === 0) {
    throw new VisualAssetBindingError(
      missingCode,
      `${key} field is missing`
    );
  }
  if (matches.length !== 1) {
    throw new VisualAssetBindingError(
      duplicateCode,
      `${key} field must appear exactly once`
    );
  }
  return matches[0];
}

export function locateResidentScope(
  snapshot: VisualAssetBindingCanvasSnapshot
): ResidentScopeLocation {
  const { instanceId, graph } = locateUniqueAttachedInstance(
    snapshot,
    RESIDENT_IDENTITY_LAYER_ID,
    RESIDENT_IDENTITY_MODULE_ID,
    {
      attachmentMissing: "identity_attachment_missing",
      attachmentDuplicate: "identity_attachment_duplicate",
      registryMissing: "identity_registry_missing",
      registryDuplicate: "identity_registry_duplicate",
      registryInvalid: "identity_registry_invalid",
      graphMissing: "identity_graph_missing",
    }
  );
  const residentFields = graph.nodes.flatMap(
    (node) => authoritativeFields(node) ?? []
  );
  const { field } = locateUniqueField(
    residentFields,
    RESIDENT_IDENTITY_FIELD_KEY,
    "resident_id_field_missing",
    "resident_id_field_duplicate"
  );
  const residentScopeId = requireNonEmptyString(
    fieldValue(field),
    "resident_id_invalid",
    RESIDENT_IDENTITY_FIELD_KEY
  );
  return {
    residentScopeId,
    identityInstanceId: instanceId,
    graph,
  };
}

export function locateParticleAvatarTarget(
  snapshot: VisualAssetBindingCanvasSnapshot
): ParticleAvatarTargetLocation {
  const { instanceId, graph } = locateUniqueAttachedInstance(
    snapshot,
    PARTICLE_AVATAR_LAYER_ID,
    PARTICLE_AVATAR_MODULE_ID,
    {
      attachmentMissing: "particle_attachment_missing",
      attachmentDuplicate: "particle_attachment_duplicate",
      registryMissing: "particle_registry_missing",
      registryDuplicate: "particle_registry_duplicate",
      registryInvalid: "particle_registry_invalid",
      graphMissing: "particle_graph_missing",
    }
  );
  const inputNodes = graph.nodes
    .map((node, index) => ({ node, index }))
    .filter(
      ({ node }) =>
        normalizedCatalogNodeId(node) === PARTICLE_VISUAL_CONFIG_INPUT_NODE_ID
    );
  if (inputNodes.length === 0) {
    throw new VisualAssetBindingError(
      "particle_input_missing",
      `${PARTICLE_VISUAL_CONFIG_INPUT_NODE_ID} is missing`
    );
  }
  if (inputNodes.length !== 1) {
    throw new VisualAssetBindingError(
      "particle_input_duplicate",
      `${PARTICLE_VISUAL_CONFIG_INPUT_NODE_ID} must appear exactly once`
    );
  }
  const { node, index: inputNodeIndex } = inputNodes[0];
  const { field, index: blueprintFieldIndex } = locateUniqueField(
    authoritativeFields(node),
    ABSTRACT_BUST_BLUEPRINT_FIELD_KEY,
    "blueprint_field_missing",
    "blueprint_field_duplicate"
  );
  let blueprint: AbstractBustBlueprint;
  try {
    blueprint = normalizeAbstractBustBlueprint(fieldValue(field));
  } catch (error) {
    throw new VisualAssetBindingError(
      "blueprint_invalid",
      error instanceof Error ? error.message : String(error),
      ABSTRACT_BUST_BLUEPRINT_FIELD_KEY
    );
  }
  return {
    moduleInstanceId: instanceId,
    graph,
    blueprint,
    blueprintDigest: digestAbstractBustBlueprint(blueprint),
    inputNodeIndex,
    blueprintFieldIndex,
  };
}

export function normalizeVisualAssetBinding(
  value: unknown
): VisualAssetBinding {
  if (!isRecord(value)) {
    throw new VisualAssetBindingError(
      "binding_invalid",
      "visualAssetBinding must be an object"
    );
  }
  const unknownKey = Object.keys(value).find(
    (key) => !BINDING_KEYS.has(key)
  );
  if (unknownKey) {
    throw new VisualAssetBindingError(
      "binding_invalid",
      `Unknown visualAssetBinding field: ${unknownKey}`,
      unknownKey
    );
  }
  if (
    typeof value.asset_revision !== "number" ||
    !Number.isInteger(value.asset_revision) ||
    value.asset_revision < 1
  ) {
    throw new VisualAssetBindingError(
      "binding_invalid",
      "visualAssetBinding.asset_revision must be a positive integer",
      "asset_revision"
    );
  }
  if (value.builder_id !== ABSTRACT_PARTICLE_BUST_BUILDER_ID) {
    throw new VisualAssetBindingError(
      "binding_invalid",
      "visualAssetBinding.builder_id is unsupported",
      "builder_id"
    );
  }
  if (value.appearance_type !== "abstract_particle_bust") {
    throw new VisualAssetBindingError(
      "binding_invalid",
      "visualAssetBinding.appearance_type is unsupported",
      "appearance_type"
    );
  }
  if (value.generator_version !== ABSTRACT_BUST_GENERATOR_VERSION) {
    throw new VisualAssetBindingError(
      "binding_invalid",
      "visualAssetBinding.generator_version is unsupported",
      "generator_version"
    );
  }
  if (
    typeof value.blueprint_digest !== "string" ||
    !DIGEST_PATTERN.test(value.blueprint_digest)
  ) {
    throw new VisualAssetBindingError(
      "binding_invalid",
      "visualAssetBinding.blueprint_digest is invalid",
      "blueprint_digest"
    );
  }
  return {
    resident_scope_id: requireNonEmptyString(
      value.resident_scope_id,
      "binding_invalid",
      "resident_scope_id"
    ),
    module_instance_id: requireNonEmptyString(
      value.module_instance_id,
      "binding_invalid",
      "module_instance_id"
    ),
    asset_id: requireNonEmptyString(
      value.asset_id,
      "binding_invalid",
      "asset_id"
    ),
    asset_revision: value.asset_revision,
    builder_id: ABSTRACT_PARTICLE_BUST_BUILDER_ID,
    appearance_type: "abstract_particle_bust",
    generator_version: ABSTRACT_BUST_GENERATOR_VERSION,
    blueprint_digest:
      value.blueprint_digest as VisualAssetBinding["blueprint_digest"],
    bound_at: requireTimestamp(value.bound_at, "bound_at"),
    updated_at: requireTimestamp(value.updated_at, "updated_at"),
  };
}

function bindingFromGraph(
  graph: VisualAssetBindingModuleGraph
): VisualAssetBinding | undefined {
  if (graph.studioMetadata === undefined) {
    return undefined;
  }
  if (!isRecord(graph.studioMetadata)) {
    throw new VisualAssetBindingError(
      "binding_invalid",
      "graph.studioMetadata must be an object",
      "studioMetadata"
    );
  }
  if (
    !Object.prototype.hasOwnProperty.call(
      graph.studioMetadata,
      "visualAssetBinding"
    )
  ) {
    return undefined;
  }
  return normalizeVisualAssetBinding(
    graph.studioMetadata.visualAssetBinding
  );
}

function rawBindingInfo(graph: VisualAssetBindingModuleGraph): {
  present: boolean;
  assetId?: string;
} {
  if (graph.studioMetadata === undefined) {
    return { present: false };
  }
  if (!isRecord(graph.studioMetadata)) {
    return { present: true };
  }
  if (
    !Object.prototype.hasOwnProperty.call(
      graph.studioMetadata,
      "visualAssetBinding"
    )
  ) {
    return { present: false };
  }
  const rawBinding = graph.studioMetadata.visualAssetBinding;
  const assetId =
    isRecord(rawBinding) &&
    typeof rawBinding.asset_id === "string" &&
    rawBinding.asset_id.trim()
      ? rawBinding.asset_id.trim()
      : undefined;
  return { present: true, assetId };
}

function locateVisualAssetBindingTargetContext(
  snapshot: VisualAssetBindingCanvasSnapshot
): VisualAssetBindingContext {
  return {
    ...locateResidentScope(snapshot),
    ...locateParticleAvatarTarget(snapshot),
  };
}

const RECOVERABLE_BINDING_ERROR_CODES =
  new Set<VisualAssetBindingErrorCode>([
    "binding_invalid",
    "binding_scope_mismatch",
    "binding_instance_mismatch",
    "timestamp_invalid",
  ]);

function locateVisualAssetBindingReplacementContext(
  snapshot: VisualAssetBindingCanvasSnapshot
): VisualAssetBindingContext {
  try {
    return locateVisualAssetBindingContext(snapshot);
  } catch (error) {
    if (
      !(error instanceof VisualAssetBindingError) ||
      !RECOVERABLE_BINDING_ERROR_CODES.has(error.code)
    ) {
      throw error;
    }
    const context = locateVisualAssetBindingTargetContext(snapshot);
    if (!rawBindingInfo(context.graph).present) {
      throw error;
    }
    return context;
  }
}

export function locateVisualAssetBindingContext(
  snapshot: VisualAssetBindingCanvasSnapshot
): VisualAssetBindingContext {
  const resident = locateResidentScope(snapshot);
  const particle = locateParticleAvatarTarget(snapshot);
  const binding = bindingFromGraph(particle.graph);
  if (
    binding &&
    binding.resident_scope_id !== resident.residentScopeId
  ) {
    throw new VisualAssetBindingError(
      "binding_scope_mismatch",
      "visualAssetBinding resident scope does not match Layer 1 resident_id"
    );
  }
  if (
    binding &&
    binding.module_instance_id !== particle.moduleInstanceId
  ) {
    throw new VisualAssetBindingError(
      "binding_instance_mismatch",
      "visualAssetBinding module instance does not match the Layer 10 target"
    );
  }
  return {
    ...resident,
    ...particle,
    binding,
  };
}

function visualAssetFromCollection(
  assets: DeriveVisualAssetBindingStatusInput["visualAssets"],
  assetId: string
): unknown {
  if (Array.isArray(assets)) {
    return assets.find(
      (candidate) =>
        isRecord(candidate) && candidate.asset_id === assetId
    );
  }
  return (assets as Readonly<Record<string, unknown>>)[assetId];
}

export function deriveVisualAssetBindingStatus(
  input: DeriveVisualAssetBindingStatusInput
): VisualAssetBindingStatus {
  let context: VisualAssetBindingContext;
  try {
    context = locateVisualAssetBindingContext(input);
  } catch (error) {
    const bindingError =
      error instanceof VisualAssetBindingError
        ? error
        : new VisualAssetBindingError(
            "binding_invalid",
            error instanceof Error ? error.message : String(error)
          );
    if (RECOVERABLE_BINDING_ERROR_CODES.has(bindingError.code)) {
      try {
        const targetContext =
          locateVisualAssetBindingTargetContext(input);
        const rawBinding = rawBindingInfo(targetContext.graph);
        if (rawBinding.present) {
          return {
            state: "invalid",
            reason: bindingError.code,
            message: bindingError.message,
            residentScopeId: targetContext.residentScopeId,
            moduleInstanceId: targetContext.moduleInstanceId,
            bindingRecordPresent: true,
            bindingAssetId: rawBinding.assetId,
            layerBlueprint: cloneJson(targetContext.blueprint),
            layerBlueprintDigest: targetContext.blueprintDigest,
            layerModified: false,
            assetModified: false,
            assetMissing: false,
          };
        }
      } catch {
        // Fall through to the original target error without guessing context.
      }
    }
    return {
      state: "invalid",
      reason: bindingError.code,
      message: bindingError.message,
      bindingRecordPresent: false,
      layerModified: false,
      assetModified: false,
      assetMissing: bindingError.code === "binding_asset_missing",
    };
  }

  const base = {
    residentScopeId: context.residentScopeId,
    moduleInstanceId: context.moduleInstanceId,
    binding: context.binding,
    bindingRecordPresent: Boolean(context.binding),
    bindingAssetId: context.binding?.asset_id,
    layerBlueprint: cloneJson(context.blueprint),
    layerBlueprintDigest: context.blueprintDigest,
  };
  if (!context.binding) {
    return {
      state: "unbound",
      ...base,
      layerModified: false,
      assetModified: false,
      assetMissing: false,
    };
  }

  const assetValue = visualAssetFromCollection(
    input.visualAssets,
    context.binding.asset_id
  );
  if (assetValue === undefined) {
    return {
      state: "invalid",
      reason: "binding_asset_missing",
      message: `Bound Visual Asset ${context.binding.asset_id} is missing`,
      ...base,
      layerModified:
        context.blueprintDigest !== context.binding.blueprint_digest,
      assetModified: false,
      assetMissing: true,
    };
  }

  let asset: AbstractParticleBustVisualAsset;
  try {
    asset = normalizeVisualAsset(assetValue);
  } catch (error) {
    return {
      state: "invalid",
      reason: "asset_invalid",
      message: error instanceof Error ? error.message : String(error),
      ...base,
      layerModified:
        context.blueprintDigest !== context.binding.blueprint_digest,
      assetModified: false,
      assetMissing: false,
    };
  }
  if (asset.asset_id !== context.binding.asset_id) {
    return {
      state: "invalid",
      reason: "asset_mismatch",
      message: "Bound Visual Asset ID does not match its collection key",
      ...base,
      asset,
      layerModified:
        context.blueprintDigest !== context.binding.blueprint_digest,
      assetModified: false,
      assetMissing: false,
    };
  }

  const assetBlueprintDigest = digestAbstractBustBlueprint(asset.blueprint);
  const layerModified =
    context.blueprintDigest !== context.binding.blueprint_digest;
  const assetModified =
    asset.revision !== context.binding.asset_revision ||
    assetBlueprintDigest !== context.binding.blueprint_digest;
  return {
    state:
      !layerModified && !assetModified ? "in_sync" : "out_of_sync",
    ...base,
    asset,
    assetBlueprintDigest,
    layerModified,
    assetModified,
    assetMissing: false,
  };
}

function normalizedAssetForPreparation(
  assetValue: unknown,
  expectedAssetRevision?: number
): AbstractParticleBustVisualAsset {
  let asset: AbstractParticleBustVisualAsset;
  try {
    asset = normalizeVisualAsset(assetValue);
  } catch (error) {
    throw new VisualAssetBindingError(
      "asset_invalid",
      error instanceof Error ? error.message : String(error)
    );
  }
  if (
    expectedAssetRevision !== undefined &&
    asset.revision !== expectedAssetRevision
  ) {
    throw new VisualAssetBindingError(
      "asset_revision_stale",
      `Expected Visual Asset revision ${expectedAssetRevision}, received ${asset.revision}`
    );
  }
  return asset;
}

function replaceFieldValue(
  field: Record<string, unknown>,
  value: unknown
): Record<string, unknown> {
  const valueKey = Object.prototype.hasOwnProperty.call(
    field,
    "field_value"
  )
    ? "field_value"
    : "value";
  return {
    ...field,
    [valueKey]: cloneJson(value),
  };
}

function graphWithBlueprintAndBinding(
  context: VisualAssetBindingContext,
  blueprint: AbstractBustBlueprint,
  binding: VisualAssetBinding
): VisualAssetBindingModuleGraph {
  const nextGraph = cloneJson(context.graph);
  const inputNode = nextGraph.nodes[context.inputNodeIndex];
  const schemaNode = schemaNodeRecord(inputNode);
  if (!schemaNode) {
    throw new VisualAssetBindingError(
      "particle_input_missing",
      `${PARTICLE_VISUAL_CONFIG_INPUT_NODE_ID} is missing`
    );
  }
  const data = isRecord(schemaNode.data)
    ? schemaNode.data
    : schemaNode;
  const params = isRecord(data.params) ? data.params : {};
  const sourceFields = Array.isArray(params.fields)
    ? params.fields.filter(isRecord)
    : Array.isArray(data.fields)
      ? data.fields.filter(isRecord)
      : [];
  const nextFields = sourceFields.map((field, index) =>
    index === context.blueprintFieldIndex
      ? replaceFieldValue(field, blueprint)
      : field
  );
  params.fields = cloneJson(nextFields);
  if (Array.isArray(params.legacy_fields)) {
    params.legacy_fields = cloneJson(nextFields);
  }
  if (Array.isArray(params.legacy_data_fields)) {
    params.legacy_data_fields = cloneJson(nextFields);
  }
  data.params = params;
  if (Array.isArray(data.fields)) {
    data.fields = cloneJson(nextFields);
  }
  if (schemaNode.data !== data && schemaNode !== data) {
    schemaNode.data = data;
  }

  const studioMetadata = isRecord(nextGraph.studioMetadata)
    ? nextGraph.studioMetadata
    : {};
  studioMetadata.visualAssetBinding = cloneJson(binding);
  nextGraph.studioMetadata =
    studioMetadata as ModuleGraphStudioMetadata;
  return nextGraph;
}

function graphWithoutBinding(
  graph: VisualAssetBindingModuleGraph
): VisualAssetBindingModuleGraph {
  const nextGraph = cloneJson(graph);
  if (nextGraph.studioMetadata === undefined) {
    return nextGraph;
  }
  if (!isRecord(nextGraph.studioMetadata)) {
    delete nextGraph.studioMetadata;
    return nextGraph;
  }
  delete nextGraph.studioMetadata.visualAssetBinding;
  return nextGraph;
}

function preparationTimestamp(now: string): string {
  return requireTimestamp(now, "now");
}

function createBinding(
  context: VisualAssetBindingContext,
  asset: AbstractParticleBustVisualAsset,
  blueprintDigest: string,
  timestamp: string,
  boundAt: string
): VisualAssetBinding {
  return {
    resident_scope_id: context.residentScopeId,
    module_instance_id: context.moduleInstanceId,
    asset_id: asset.asset_id,
    asset_revision: asset.revision,
    builder_id: ABSTRACT_PARTICLE_BUST_BUILDER_ID,
    appearance_type: "abstract_particle_bust",
    generator_version: ABSTRACT_BUST_GENERATOR_VERSION,
    blueprint_digest:
      blueprintDigest as VisualAssetBinding["blueprint_digest"],
    bound_at: boundAt,
    updated_at: timestamp,
  };
}

export function prepareVisualAssetBind(
  input: PrepareVisualAssetBindingInput
): PreparedVisualAssetBinding {
  const context = locateVisualAssetBindingReplacementContext(input);
  const asset = normalizedAssetForPreparation(
    input.asset,
    input.expectedAssetRevision
  );
  if (
    context.binding?.asset_id === asset.asset_id &&
    asset.revision < context.binding.asset_revision
  ) {
    throw new VisualAssetBindingError(
      "asset_revision_stale",
      `Visual Asset revision ${asset.revision} is older than bound revision ${context.binding.asset_revision}`
    );
  }
  const timestamp = preparationTimestamp(input.now);
  const blueprint = normalizeAbstractBustBlueprint(asset.blueprint);
  const blueprintDigest = digestAbstractBustBlueprint(blueprint);
  const nextBinding = createBinding(
    context,
    asset,
    blueprintDigest,
    timestamp,
    context.binding?.asset_id === asset.asset_id
      ? context.binding.bound_at
      : timestamp
  );
  return {
    residentScopeId: context.residentScopeId,
    moduleInstanceId: context.moduleInstanceId,
    blueprint: cloneJson(blueprint),
    blueprintDigest,
    previousBinding: context.binding
      ? cloneJson(context.binding)
      : undefined,
    nextBinding: cloneJson(nextBinding),
    nextGraph: graphWithBlueprintAndBinding(
      context,
      blueprint,
      nextBinding
    ),
  };
}

export function prepareVisualAssetSync(
  input: PrepareVisualAssetBindingInput
): PreparedVisualAssetBinding {
  const context = locateVisualAssetBindingContext(input);
  if (!context.binding) {
    throw new VisualAssetBindingError(
      "binding_invalid",
      "Cannot sync an unbound particle avatar"
    );
  }
  const asset = normalizedAssetForPreparation(
    input.asset,
    input.expectedAssetRevision
  );
  if (asset.asset_id !== context.binding.asset_id) {
    throw new VisualAssetBindingError(
      "asset_mismatch",
      `Expected bound Visual Asset ${context.binding.asset_id}, received ${asset.asset_id}`
    );
  }
  if (asset.revision < context.binding.asset_revision) {
    throw new VisualAssetBindingError(
      "asset_revision_stale",
      `Visual Asset revision ${asset.revision} is older than bound revision ${context.binding.asset_revision}`
    );
  }
  const timestamp = preparationTimestamp(input.now);
  const blueprint = normalizeAbstractBustBlueprint(asset.blueprint);
  const blueprintDigest = digestAbstractBustBlueprint(blueprint);
  const nextBinding = createBinding(
    context,
    asset,
    blueprintDigest,
    timestamp,
    context.binding.bound_at
  );
  return {
    residentScopeId: context.residentScopeId,
    moduleInstanceId: context.moduleInstanceId,
    blueprint: cloneJson(blueprint),
    blueprintDigest,
    previousBinding: cloneJson(context.binding),
    nextBinding: cloneJson(nextBinding),
    nextGraph: graphWithBlueprintAndBinding(
      context,
      blueprint,
      nextBinding
    ),
  };
}

export function prepareVisualAssetUnbind(
  input: PrepareVisualAssetUnbindInput
): PreparedVisualAssetUnbind {
  const context = locateVisualAssetBindingReplacementContext(input);
  return {
    residentScopeId: context.residentScopeId,
    moduleInstanceId: context.moduleInstanceId,
    blueprint: cloneJson(context.blueprint),
    blueprintDigest: context.blueprintDigest,
    previousBinding: context.binding
      ? cloneJson(context.binding)
      : undefined,
    nextBinding: undefined,
    nextGraph: graphWithoutBinding(context.graph),
  };
}

export const prepareBindParticleAvatar = prepareVisualAssetBind;
export const prepareSyncParticleAvatar = prepareVisualAssetSync;
export const prepareUnbindParticleAvatar = prepareVisualAssetUnbind;
