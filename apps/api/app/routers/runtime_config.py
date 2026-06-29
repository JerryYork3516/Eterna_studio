"""Runtime Config router — Stage 6.6 real LLM v2.

Exposes masked runtime LLM profiles for the settings page. The UI can save
multiple profiles, but it never receives or stores raw api_key values.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Body, HTTPException
from pydantic import BaseModel, Field

from ..services import runtime_config_service as config_service
from ..services.llm_real_adapter import call_openai_compat
from ..services.runtime_llm_config import (
    DEFAULT_PROFILE_ID,
    DEFAULT_PROFILE_IDS,
    get_runtime_llm_profile,
    get_runtime_llm_profiles,
)

router = APIRouter(prefix="/runtime/config", tags=["runtime-config"])


class LLMProfileSaveRequest(BaseModel):
    profile_id: str = Field(..., description="Profile identifier")
    provider: Optional[str] = None
    base_url: Optional[str] = None
    api_key: Optional[str] = None  # empty/omitted = leave stored key unchanged
    model: Optional[str] = None
    enabled: Optional[bool] = None
    fallback_to_mock: Optional[bool] = None


class LLMTestRequest(BaseModel):
    profile_id: Optional[str] = None
    # Optional overrides for a one-off test; when omitted, the stored profile is used.
    provider: Optional[str] = None
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    model: Optional[str] = None
    prompt: Optional[str] = None


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


@router.get("/llm")
def get_llm_config() -> Dict[str, Any]:
    """Return the masked runtime LLM profiles (never the raw api_key)."""
    profiles = get_runtime_llm_profiles()
    default_profile = profiles.get(DEFAULT_PROFILE_ID) or get_runtime_llm_profile(DEFAULT_PROFILE_ID)
    default_masked = default_profile.masked()
    return {
        **default_masked,
        "default_profile_id": DEFAULT_PROFILE_ID,
        "profile_ids": list(DEFAULT_PROFILE_IDS),
        "profiles": {profile_id: profile.masked() for profile_id, profile in profiles.items()},
    }


@router.post("/llm")
def save_llm_config(req: LLMProfileSaveRequest) -> Dict[str, Any]:
    """Persist one runtime LLM profile (process memory + local private JSON)."""
    masked = config_service.set_section(
        "llm",
        {
            "profiles": {
                req.profile_id: {
                    "profile_id": req.profile_id,
                    "provider": req.provider,
                    "base_url": req.base_url,
                    "api_key": req.api_key,
                    "model": req.model,
                    "enabled": req.enabled,
                    "fallback_to_mock": req.fallback_to_mock,
                }
            }
        },
    )
    profile = get_runtime_llm_profile(req.profile_id)
    return {"saved": True, "profile": profile.masked(), **masked, **profile.masked()}


@router.post("/llm/test")
def test_llm_connection(req: LLMTestRequest) -> Dict[str, Any]:
    """Probe one profile via the backend adapter. Returns ok/sample or error."""
    cfg = get_runtime_llm_profile(getattr(req, "profile_id", None))
    provider = (getattr(req, "provider", None) or cfg.provider or "").strip()
    base_url = (getattr(req, "base_url", None) or cfg.base_url or "").strip()
    api_key = getattr(req, "api_key", None) if getattr(req, "api_key", None) not in (None, "") else cfg.api_key
    model = (getattr(req, "model", None) or cfg.model or "").strip()
    prompt = getattr(req, "prompt", None) or "ping"

    if not (base_url and api_key and model):
        return {"ok": False, "error": "incomplete config: base_url / api_key / model required", "model": model, "provider": provider}

    result = call_openai_compat(base_url, api_key, model, prompt)
    if result.get("status") == "success":
        sample = result.get("text", "")
        return {"ok": True, "model": result.get("model", model), "provider": provider, "sample": sample[:200]}
    return {"ok": False, "model": model, "provider": provider, "error": result.get("error", "unknown error")}


@router.get("/{section}")
def get_section_config(section: str) -> Dict[str, Any]:
    if section not in config_service.SECTIONS:
        raise HTTPException(status_code=404, detail=f"unknown config section: {section!r}")
    return config_service.get_section_masked(section)


@router.post("/{section}")
def save_section_config(section: str, body: Dict[str, Any] = Body(default_factory=dict)) -> Dict[str, Any]:
    if section not in config_service.SECTIONS:
        raise HTTPException(status_code=404, detail=f"unknown config section: {section!r}")
    masked = config_service.set_section(section, body)
    return {"saved": True, "section": section, **masked}
