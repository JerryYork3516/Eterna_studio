"""Provider Adapter Layer — Stage 6.5 mock provider registry surface.

Execution boundary (do not violate):
  * Node / Module / Slot are protocol descriptors only — they never execute.
  * The Execution Engine (execution_engine.py) is the only runtime entry.
  * Providers are mock-only. Runtime resolves Engine -> Provider Registry ->
    Adapter. The UI never calls a provider directly.

No real model, no network, no API key, no database.
"""

from __future__ import annotations

from typing import Any, Dict, List

from ..registry.provider_registry import (
    PROVIDER_REGISTRY,
    get_provider_entry,
    resolve_provider_entry_for_engine,
)
from .llm_mock_engine import run_mock_llm
from .llm_real_adapter import call_openai_compat
from .runtime_llm_config import get_runtime_llm_config


class ProviderAdapter:
    """Unified provider interface: execute(payload) -> dict."""

    provider_id: str = ""
    provider_type: str = "base"

    def execute(self, payload: Dict[str, Any]) -> Dict[str, Any]:  # pragma: no cover - abstract
        raise NotImplementedError


class MockLLMProvider(ProviderAdapter):
    """LLM provider. Calls ONLY the deterministic llm_mock_engine — never a real
    model, never an API key."""

    provider_id = "provider_llm_mock"
    provider_type = "llm"

    def execute(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        prompt = payload.get("prompt") if isinstance(payload, dict) else None
        return run_mock_llm(prompt=prompt)


class RealLLMProvider(ProviderAdapter):
    """Stage 6.6 real LLM. Reads the global RuntimeLLMConfig and calls the
    OpenAI-compatible relay via llm_real_adapter. NEVER receives or echoes the
    api_key in its payload — it pulls it from the process-local config. Any
    failure is returned as a structured error so the runtime can fall back."""

    provider_id = "provider_llm_real"
    provider_type = "llm"

    def execute(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        cfg = get_runtime_llm_config()
        prompt = payload.get("prompt") if isinstance(payload, dict) else None
        if not cfg.is_valid():
            return {
                "status": "error",
                "mock": False,
                "engine": "llm_primary",
                "error": "llm config not enabled or incomplete",
            }
        return call_openai_compat(cfg.base_url, cfg.api_key, cfg.model, prompt or "")


# Process-only memory store, isolated per resident_id. No database.
_STORE: Dict[str, List[Dict[str, Any]]] = {}


class InMemoryProvider(ProviderAdapter):
    """Memory provider backed by a process-local dict keyed by resident_id.

    Supports read / list / write. Isolated per resident_id. No persistence.
    """

    provider_id = "provider_memory_mock"
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

    provider_id = "provider_tool_mock"
    provider_type = "tool"

    def execute(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        tool = payload.get("tool")
        args = payload.get("args") or {}
        if tool == "echo":
            return {"status": "success", "mock": True, "tool": "echo", "result": args.get("text", "")}
        if tool == "status":
            return {"status": "success", "mock": True, "tool": "status", "result": "ok"}
        return {"status": "error", "mock": True, "tool": tool, "error": f"unknown tool: {tool!r}"}


class MockTTSProvider(ProviderAdapter):
    """TTS placeholder. Deterministic mock only; no audio engine."""

    provider_id = "provider_tts_mock"
    provider_type = "tts"

    def execute(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        text = payload.get("text", "") if isinstance(payload, dict) else ""
        return {"status": "success", "mock": True, "audio_url": "", "text": text, "voice": "mock_voice"}


class MockAvatarProvider(ProviderAdapter):
    """Avatar placeholder. Deterministic mock only; no renderer."""

    provider_id = "provider_avatar_mock"
    provider_type = "avatar"

    def execute(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        pose = payload.get("pose", "idle") if isinstance(payload, dict) else "idle"
        return {"status": "success", "mock": True, "avatar_state": {"pose": pose, "style": "mock_particle"}}


class MockSpeechProvider(ProviderAdapter):
    """Speech placeholder. Deterministic mock only; no ASR or mic access."""

    provider_id = "provider_speech_mock"
    provider_type = "speech"

    def execute(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return {"status": "success", "mock": True, "transcript": payload.get("transcript", "") if isinstance(payload, dict) else ""}


class MockScreenProvider(ProviderAdapter):
    """Screen placeholder. Deterministic mock only; no screen capture."""

    provider_id = "provider_screen_mock"
    provider_type = "screen"

    def execute(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return {"status": "success", "mock": True, "screen_state": payload.get("state", "mock_screen") if isinstance(payload, dict) else "mock_screen"}


_mock_llm_adapter = MockLLMProvider()

_ADAPTERS_BY_PROVIDER_ID: Dict[str, ProviderAdapter] = {
    "provider_llm_mock": _mock_llm_adapter,
    "provider_memory_mock": InMemoryProvider(),
    "provider_tool_mock": MockToolProvider(),
    "provider_tts_mock": MockTTSProvider(),
    "provider_avatar_mock": MockAvatarProvider(),
    "provider_speech_mock": MockSpeechProvider(),
    "provider_screen_mock": MockScreenProvider(),
    # Stage 6.6 real LLM v1.
    "provider_llm_real": RealLLMProvider(),
    "provider_llm_fallback": _mock_llm_adapter,  # llm_fallback reuses the mock LLM
}


def _with_provider_metadata(
    result: Dict[str, Any], *, provider_id: str, provider_type: str, engine_id: str
) -> Dict[str, Any]:
    enriched = dict(result)
    # Respect the adapter's own mock flag (defaults True for the mock providers).
    # The real LLM adapter returns mock=False so the trace can distinguish them.
    enriched["mock"] = bool(result.get("mock", True))
    enriched["provider_id"] = provider_id
    enriched["provider_type"] = provider_type
    enriched["engine_id"] = engine_id
    return enriched


def route_provider_for_engine(engine_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Resolve Engine -> Provider Registry -> Adapter and execute mock payload."""
    provider = resolve_provider_entry_for_engine(engine_id)
    if provider is None:
        return {
            "status": "error",
            "mock": True,
            "engine_id": engine_id,
            "error": f"unknown engine_id: {engine_id!r}",
        }
    adapter = _ADAPTERS_BY_PROVIDER_ID.get(provider.provider_id)
    if adapter is None:
        return {
            "status": "error",
            "mock": True,
            "engine_id": engine_id,
            "provider_id": provider.provider_id,
            "provider_type": provider.provider_type,
            "error": f"no adapter for provider_id: {provider.provider_id!r}",
        }
    result = adapter.execute(payload or {})
    return _with_provider_metadata(
        result,
        provider_id=provider.provider_id,
        provider_type=provider.provider_type,
        engine_id=engine_id,
    )


def route_provider(provider_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Compatibility wrapper: dispatch to the first mock provider by type.

    An unknown provider_type returns a structured error dict (never raises an
    unhandled exception).
    """
    for provider in PROVIDER_REGISTRY:
        if provider.provider_type == provider_type:
            return route_provider_for_engine(provider.engine_id, payload)
    return {"status": "error", "mock": True, "error": f"unknown provider_type: {provider_type!r}"}


def route_provider_by_id(provider_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Self-test seam: resolve a provider id directly without exposing it to UI."""
    provider = get_provider_entry(provider_id)
    if provider is None:
        return {"status": "error", "mock": True, "provider_id": provider_id, "error": f"unknown provider_id: {provider_id!r}"}
    return route_provider_for_engine(provider.engine_id, payload)


def reset_memory() -> None:
    """Test seam: clear the process-local memory store."""
    _STORE.clear()
