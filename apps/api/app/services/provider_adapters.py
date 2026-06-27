"""Provider Adapter Layer — Stage 6 unified mock provider surface.

Execution boundary (do not violate):
  * Node / Module / Slot are protocol descriptors only — they never execute.
  * The Execution Engine (execution_engine.py) is the only runtime entry.
  * Providers are mock-only. They are reached ONLY through the Execution Engine
    (via resident_runtime). The UI never calls a provider directly.

This module exposes three deterministic mock providers (LLM / Memory / Tool)
behind one interface, plus a router that dispatches by provider_type. No real
model, no network, no API key, no database.
"""

from __future__ import annotations

from typing import Any, Dict, List

from .llm_mock_engine import run_mock_llm


class ProviderAdapter:
    """Unified provider interface: execute(payload) -> dict."""

    provider_type: str = "base"

    def execute(self, payload: Dict[str, Any]) -> Dict[str, Any]:  # pragma: no cover - abstract
        raise NotImplementedError


class MockLLMProvider(ProviderAdapter):
    """LLM provider. Calls ONLY the deterministic llm_mock_engine — never a real
    model, never an API key."""

    provider_type = "llm"

    def execute(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        prompt = payload.get("prompt") if isinstance(payload, dict) else None
        return run_mock_llm(prompt=prompt)


# Process-only memory store, isolated per resident_id. No database.
_STORE: Dict[str, List[Dict[str, Any]]] = {}


class InMemoryProvider(ProviderAdapter):
    """Memory provider backed by a process-local dict keyed by resident_id.

    Supports read / list / write. Isolated per resident_id. No persistence.
    """

    provider_type = "memory"

    def execute(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        op = payload.get("op")
        resident_id = payload.get("resident_id") or "resident_v1"
        bucket = _STORE.setdefault(resident_id, [])
        if op in ("read", "list"):
            return {
                "status": "success",
                "mock": True,
                "op": op,
                "resident_id": resident_id,
                "entries": list(bucket),
                "count": len(bucket),
            }
        if op == "write":
            entry = payload.get("entry") or {}
            bucket.append(entry)
            return {
                "status": "success",
                "mock": True,
                "op": "write",
                "resident_id": resident_id,
                "entry": entry,
                "count": len(bucket),
            }
        return {
            "status": "error",
            "mock": True,
            "resident_id": resident_id,
            "error": f"unknown memory op: {op!r}",
        }


class MockToolProvider(ProviderAdapter):
    """Tool provider with deterministic tools only (echo, status). No network."""

    provider_type = "tool"

    def execute(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        tool = payload.get("tool")
        args = payload.get("args") or {}
        if tool == "echo":
            return {"status": "success", "mock": True, "tool": "echo", "result": args.get("text", "")}
        if tool == "status":
            return {"status": "success", "mock": True, "tool": "status", "result": "ok"}
        return {"status": "error", "mock": True, "tool": tool, "error": f"unknown tool: {tool!r}"}


_PROVIDERS: Dict[str, ProviderAdapter] = {
    "llm": MockLLMProvider(),
    "memory": InMemoryProvider(),
    "tool": MockToolProvider(),
}


def route_provider(provider_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Dispatch to a mock provider by type: "llm" | "memory" | "tool".

    An unknown provider_type returns a structured error dict (never raises an
    unhandled exception).
    """
    provider = _PROVIDERS.get(provider_type)
    if provider is None:
        return {"status": "error", "mock": True, "error": f"unknown provider_type: {provider_type!r}"}
    return provider.execute(payload)


def reset_memory() -> None:
    """Test seam: clear the process-local memory store."""
    _STORE.clear()
