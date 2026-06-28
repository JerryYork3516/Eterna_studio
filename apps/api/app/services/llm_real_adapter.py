"""Real LLM Adapter — Stage 6.6 real LLM v1 (OpenAI-compatible relay).

This is the ONLY file that performs a real network call. It POSTs to an
OpenAI-compatible `/chat/completions` endpoint. Every failure mode (timeout,
connection error, non-2xx, malformed body) is caught and returned as a
structured error dict so the caller can fall back to mock without crashing.

Security boundary:
  * The api_key is received as an argument and used only for the Authorization
    header. It is NEVER logged, never put into the returned dict, never raised in
    an exception message.
  * This module is intentionally NOT scanned by the `forbidden_import` test
    (which only scans llm_mock_engine.py and engine_registry.py), so importing
    httpx here is allowed.
"""

from __future__ import annotations

from typing import Any, Dict

import httpx

DEFAULT_TIMEOUT = 30.0
ENGINE_ID = "llm_primary"


def _endpoint(base_url: str) -> str:
    base = (base_url or "").rstrip("/")
    # Accept either a root base_url ("https://host/v1") or a full chat path.
    if base.endswith("/chat/completions"):
        return base
    return f"{base}/chat/completions"


def call_openai_compat(
    base_url: str,
    api_key: str,
    model: str,
    prompt: str,
    *,
    timeout: float = DEFAULT_TIMEOUT,
) -> Dict[str, Any]:
    """Call an OpenAI-compatible chat endpoint. Returns a structured dict.

    Success: {"status":"success","mock":False,"text":...,"model":...,"engine":...}
    Failure: {"status":"error","mock":False,"error":...,"model":...,"engine":...}
    Never raises; the api_key is never echoed back.
    """
    url = _endpoint(base_url)
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    body = {
        "model": model,
        "messages": [{"role": "user", "content": prompt or ""}],
    }
    try:
        with httpx.Client(timeout=timeout) as client:
            resp = client.post(url, json=body, headers=headers)
    except httpx.TimeoutException:
        return {"status": "error", "mock": False, "engine": ENGINE_ID, "model": model, "error": "llm request timed out"}
    except httpx.HTTPError as exc:
        return {"status": "error", "mock": False, "engine": ENGINE_ID, "model": model, "error": f"llm request failed: {type(exc).__name__}"}

    if resp.status_code >= 400:
        return {
            "status": "error",
            "mock": False,
            "engine": ENGINE_ID,
            "model": model,
            "error": f"llm http {resp.status_code}",
        }

    try:
        data = resp.json()
        text = data["choices"][0]["message"]["content"]
    except (ValueError, KeyError, IndexError, TypeError):
        return {"status": "error", "mock": False, "engine": ENGINE_ID, "model": model, "error": "llm response malformed"}

    return {
        "status": "success",
        "mock": False,
        "engine": ENGINE_ID,
        "provider": "real",
        "model": model,
        "text": text if isinstance(text, str) else str(text),
    }
