"""Runtime Config router — Stage 6.6 real LLM v1.

Lets the UI configure the backend's global Runtime LLM config (base_url / api_key
/ model / enabled / fallback_to_mock) and test the connection. The UI submits
config here; it NEVER calls the external LLM directly.

Security boundary:
  * The api_key is accepted in the request body and stored ONLY in process
    memory (runtime_llm_config). Responses are always the masked view — the raw
    key is never echoed back. The test endpoint returns only ok/sample/error.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Body, HTTPException
from pydantic import BaseModel

from ..services import runtime_config_service as config_service
from ..services.llm_real_adapter import call_openai_compat
from ..services.runtime_llm_config import get_runtime_llm_config

router = APIRouter(prefix="/runtime/config", tags=["runtime-config"])


class LLMConfigRequest(BaseModel):
    base_url: Optional[str] = None
    api_key: Optional[str] = None  # empty/omitted = leave stored key unchanged
    model: Optional[str] = None
    enabled: Optional[bool] = None
    fallback_to_mock: Optional[bool] = None


class LLMTestRequest(BaseModel):
    # Optional overrides for a one-off test; when omitted, the stored config is used.
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    model: Optional[str] = None
    prompt: Optional[str] = None


# --- Unified Runtime Config (all sections) -----------------------------------
@router.get("")
def get_all_config() -> Dict[str, Any]:
    """Masked view of every config section (never raw secrets)."""
    return {"sections": config_service.get_all_masked()}


@router.post("")
def save_all_config(body: Dict[str, Any] = Body(default_factory=dict)) -> Dict[str, Any]:
    """Save multiple sections at once. Body: {"sections": {<section>: {...}}} or a
    flat {<section>: {...}} map. Persists to the local private JSON."""
    sections = body.get("sections") if isinstance(body.get("sections"), dict) else body
    config_service.set_sections(sections if isinstance(sections, dict) else {})
    return {"saved": True, "sections": config_service.get_all_masked()}


# --- LLM section (Stage 6.6 compatibility; declared before /{section}) --------
@router.get("/llm")
def get_llm_config() -> Dict[str, Any]:
    """Return the masked runtime LLM config (never the raw api_key)."""
    return get_runtime_llm_config().masked()


@router.post("/llm")
def save_llm_config(req: LLMConfigRequest) -> Dict[str, Any]:
    """Persist the runtime LLM config (process memory + local private JSON)."""
    masked = config_service.set_section(
        "llm",
        {
            "base_url": req.base_url,
            "api_key": req.api_key,
            "model": req.model,
            "enabled": req.enabled,
            "fallback_to_mock": req.fallback_to_mock,
        },
    )
    return {"saved": True, **masked}


@router.post("/llm/test")
def test_llm_connection(req: LLMTestRequest) -> Dict[str, Any]:
    """Probe the LLM once via the backend adapter. Returns ok/sample or error.

    Uses request overrides when provided, else the stored config. The api_key is
    never returned. This performs a real call only on the backend.
    """
    cfg = get_runtime_llm_config()
    base_url = (req.base_url or cfg.base_url or "").strip()
    api_key = req.api_key if (req.api_key not in (None, "")) else cfg.api_key
    model = (req.model or cfg.model or "").strip()
    prompt = req.prompt or "ping"

    if not (base_url and api_key and model):
        return {"ok": False, "error": "incomplete config: base_url / api_key / model required", "model": model}

    result = call_openai_compat(base_url, api_key, model, prompt)
    if result.get("status") == "success":
        sample = result.get("text", "")
        return {"ok": True, "model": result.get("model", model), "sample": sample[:200]}
    return {"ok": False, "model": model, "error": result.get("error", "unknown error")}


# --- Generic per-section endpoints (memory / lattice / tts / screen / llm) -----
# Declared AFTER the literal /llm routes so those keep precedence. These store and
# read config only; only the llm section is wired to a real capability for now.
@router.get("/{section}")
def get_section_config(section: str) -> Dict[str, Any]:
    """Masked view of a single section. 404 for an unknown section."""
    if section not in config_service.SECTIONS:
        raise HTTPException(status_code=404, detail=f"unknown config section: {section!r}")
    return config_service.get_section_masked(section)


@router.post("/{section}")
def save_section_config(section: str, body: Dict[str, Any] = Body(default_factory=dict)) -> Dict[str, Any]:
    """Persist a single section to the local private JSON. Returns masked view."""
    if section not in config_service.SECTIONS:
        raise HTTPException(status_code=404, detail=f"unknown config section: {section!r}")
    masked = config_service.set_section(section, body)
    return {"saved": True, "section": section, **masked}
