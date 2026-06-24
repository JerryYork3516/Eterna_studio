"""LLM Mock Engine — Stage 5 mock provider adapter.

This is the ONLY engine implementation this stage. It returns a stable, fully
deterministic mock result. It NEVER calls a real LLM API and NEVER reads an API
key. A Slot binds it via Slot.engine_binding = "llm_mock".
"""

from __future__ import annotations

from typing import Any, Dict, Optional

ENGINE_ID = "llm_mock"
PROVIDER = "mock"


def run_mock_llm(prompt: Optional[str] = None, **_ignored: Any) -> Dict[str, Any]:
    """Return a stable mock LLM result. No network, no API key.

    The shape is intentionally fixed so callers/tests can assert on it.
    """
    return {
        "status": "success",
        "mock": True,
        "text": "This is a mock LLM response.",
        "engine": ENGINE_ID,
        "provider": PROVIDER,
    }


def mock_call(engine_id: str, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Resolve a mock engine call by engine_id. Only "llm_mock" is supported."""
    if engine_id != ENGINE_ID:
        return {
            "status": "error",
            "mock": True,
            "text": "",
            "engine": engine_id,
            "provider": PROVIDER,
            "error": f"unknown or non-mock engine: {engine_id}",
        }
    prompt = (payload or {}).get("prompt") if isinstance(payload, dict) else None
    return run_mock_llm(prompt=prompt)
