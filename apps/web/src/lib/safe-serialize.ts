const FORBIDDEN_REFERENCE_KEYS = new Set([
  "workflow",
  "workflows",
  "nodes",
  "edges",
  "runtime",
  "context",
  "parent",
  "parents",
  "graph",
  "node",
  "edge",
  "components",
  "component",
  "source_input",
  "summary"
]);

function looksLikeStringifiedJson(value: string) {
  const trimmed = value.trim();
  if (!trimmed || !/^[{[]/.test(trimmed)) {
    return false;
  }
  try {
    JSON.parse(trimmed);
    return true;
  } catch {
    return /\{\s*["“]?(text_input|workflow|node|nodes|edges|runtime|resident_instance)["”]?\s*[:}]/i.test(trimmed);
  }
}

function referenceId(value: Record<string, unknown>) {
  const id = value.node_id ?? value.edge_id ?? value.workflow_id ?? value.id;
  return typeof id === "string" || typeof id === "number" ? id : null;
}

function isPlainSerializableObject(value: unknown): value is Record<string, unknown> {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    return false;
  }
  const prototype = Object.getPrototypeOf(value);
  return prototype === Object.prototype || prototype === null;
}

export function safeClone<T>(value: T): T {
  const seen = new WeakSet<object>();

  const clone = (input: unknown): unknown => {
    if (input === null || typeof input === "number" || typeof input === "boolean") {
      return input;
    }
    if (typeof input === "string") {
      return looksLikeStringifiedJson(input) ? "" : input;
    }
    if (input === undefined || typeof input === "function" || typeof input === "symbol" || typeof input === "bigint") {
      return null;
    }
    if (input instanceof Date) {
      return input.toISOString();
    }
    if (Array.isArray(input)) {
      if (seen.has(input)) {
        return null;
      }
      seen.add(input);
      return input.map((item) => clone(item));
    }
    if (typeof input === "object") {
      const record = input as Record<string, unknown>;
      if (seen.has(input)) {
        return referenceId(record) ?? null;
      }
      seen.add(input);
      if (!isPlainSerializableObject(input)) {
        return referenceId(record) ?? null;
      }
      const output: Record<string, unknown> = {};
      for (const [key, item] of Object.entries(record)) {
        if (FORBIDDEN_REFERENCE_KEYS.has(key)) {
          const id = item && typeof item === "object" ? referenceId(item as Record<string, unknown>) : null;
          if (id !== null) {
            output[`${key}_id`] = id;
          }
          continue;
        }
        output[key] = clone(item);
      }
      return output;
    }
    return null;
  };

  return clone(value) as T;
}

export function safeSerialize(value: unknown, space = 2) {
  return JSON.stringify(safeClone(value), null, space);
}
