"""Runtime LLM Profiles — Stage 6.6 real LLM v2.

The backend keeps a small, process-local registry of named LLM profiles. The
runtime selects a profile by `llm_profile_id`, the node only carries routing
and per-call overrides, and the raw api_key never leaves this module boundary.

Security boundary:
  * api_key is stored only in process memory and the local git-ignored runtime
    JSON. It is never returned by GET, never written into a DR, and never
    recorded in trace data or frontend store state.
  * `masked()` is the only outward view of a profile.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Dict, Iterable, Mapping, Optional

DEFAULT_PROFILE_ID = "default"
DEFAULT_PROFILE_IDS = ("default", "deepseek", "mimo", "custom")


@dataclass
class RuntimeLLMProfile:
    profile_id: str
    provider: str = "openai_compatible"
    base_url: str = ""
    model: str = ""
    api_key: str = ""
    enabled: bool = False
    fallback_to_mock: bool = True

    def is_valid(self) -> bool:
        return self.enabled and bool(self.base_url) and bool(self.api_key) and bool(self.model)

    def masked(self) -> Dict[str, Any]:
        return {
            "profile_id": self.profile_id,
            "provider": self.provider,
            "base_url": self.base_url,
            "model": self.model,
            "enabled": self.enabled,
            "fallback_to_mock": self.fallback_to_mock,
            "has_api_key": bool(self.api_key),
            "is_valid": self.is_valid(),
        }

    def raw(self) -> Dict[str, Any]:
        return {
            "profile_id": self.profile_id,
            "provider": self.provider,
            "base_url": self.base_url,
            "model": self.model,
            "api_key": self.api_key,
            "enabled": self.enabled,
            "fallback_to_mock": self.fallback_to_mock,
        }


_PROFILES: Dict[str, RuntimeLLMProfile] = {}


def _env_enabled(name: str) -> bool:
    value = os.environ.get(name)
    if value is None:
        return False
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _default_profile_values(profile_id: str) -> Dict[str, Any]:
    profile_id = (profile_id or DEFAULT_PROFILE_ID).strip() or DEFAULT_PROFILE_ID
    if profile_id == "default":
        return {
            "provider": "openai_compatible",
            "base_url": (os.environ.get("ETERNA_LLM_BASE_URL") or "").strip(),
            "model": (os.environ.get("ETERNA_LLM_MODEL") or "gpt-4o-mini").strip(),
            "api_key": os.environ.get("ETERNA_LLM_API_KEY") or "",
            "enabled": _env_enabled("ETERNA_LLM_ENABLED"),
            "fallback_to_mock": True,
        }
    if profile_id == "deepseek":
        return {
            "provider": "deepseek",
            "base_url": "https://api.deepseek.com/v1",
            "model": "deepseek-chat",
            "api_key": "",
            "enabled": False,
            "fallback_to_mock": True,
        }
    if profile_id == "mimo":
        return {
            "provider": "mimo",
            "base_url": "",
            "model": "",
            "api_key": "",
            "enabled": False,
            "fallback_to_mock": True,
        }
    return {
        "provider": "custom",
        "base_url": "",
        "model": "",
        "api_key": "",
        "enabled": False,
        "fallback_to_mock": True,
    }


def _seed_defaults() -> None:
    _PROFILES.clear()
    for profile_id in DEFAULT_PROFILE_IDS:
        _PROFILES[profile_id] = RuntimeLLMProfile(profile_id=profile_id, **_default_profile_values(profile_id))


def _ensure_profile(profile_id: Optional[str]) -> RuntimeLLMProfile:
    profile_id = (profile_id or DEFAULT_PROFILE_ID).strip() or DEFAULT_PROFILE_ID
    profile = _PROFILES.get(profile_id)
    if profile is None:
        profile = RuntimeLLMProfile(profile_id=profile_id, **_default_profile_values(profile_id))
        _PROFILES[profile_id] = profile
    return profile


def _coerce_profile_id(profile_id: Optional[str]) -> str:
    return (profile_id or DEFAULT_PROFILE_ID).strip() or DEFAULT_PROFILE_ID


def _apply_patch(profile: RuntimeLLMProfile, patch: Mapping[str, Any]) -> RuntimeLLMProfile:
    if "profile_id" in patch and isinstance(patch["profile_id"], str) and patch["profile_id"].strip():
        profile.profile_id = patch["profile_id"].strip()
    if "provider" in patch and patch["provider"] is not None:
        profile.provider = str(patch["provider"]).strip() or profile.provider
    if "base_url" in patch and patch["base_url"] is not None:
        profile.base_url = str(patch["base_url"]).strip()
    if "model" in patch and patch["model"] is not None:
        profile.model = str(patch["model"]).strip()
    if "api_key" in patch and patch["api_key"] not in (None, ""):
        profile.api_key = str(patch["api_key"])
    if "enabled" in patch and patch["enabled"] is not None:
        profile.enabled = bool(patch["enabled"])
    if "fallback_to_mock" in patch and patch["fallback_to_mock"] is not None:
        profile.fallback_to_mock = bool(patch["fallback_to_mock"])
    return profile


def _load_from_env() -> None:
    default = _ensure_profile(DEFAULT_PROFILE_ID)
    if not default.base_url:
        default.base_url = (os.environ.get("ETERNA_LLM_BASE_URL") or "").strip()
    if not default.api_key:
        default.api_key = os.environ.get("ETERNA_LLM_API_KEY") or ""
    if not default.model:
        default.model = (os.environ.get("ETERNA_LLM_MODEL") or "gpt-4o-mini").strip()
    env_enabled = os.environ.get("ETERNA_LLM_ENABLED")
    if env_enabled is not None:
        default.enabled = _env_enabled("ETERNA_LLM_ENABLED")
    elif default.base_url and default.api_key and default.model:
        default.enabled = True


def get_runtime_llm_profile(profile_id: Optional[str] = None) -> RuntimeLLMProfile:
    return _ensure_profile(_coerce_profile_id(profile_id))


def get_runtime_llm_profiles() -> Dict[str, RuntimeLLMProfile]:
    for profile_id in DEFAULT_PROFILE_IDS:
        _ensure_profile(profile_id)
    return dict(_PROFILES)


def get_runtime_llm_profile_ids() -> Iterable[str]:
    return tuple(get_runtime_llm_profiles().keys())


def get_runtime_llm_config() -> RuntimeLLMProfile:
    return get_runtime_llm_profile(DEFAULT_PROFILE_ID)


def set_runtime_llm_profile(profile_id: str, patch: Mapping[str, Any] | None = None) -> RuntimeLLMProfile:
    key = _coerce_profile_id(profile_id)
    profile = _ensure_profile(key)
    if patch:
        _apply_patch(profile, patch)
    profile.profile_id = key
    _PROFILES[key] = profile
    return profile


def set_runtime_llm_profiles(profiles: Mapping[str, Mapping[str, Any]] | None) -> Dict[str, RuntimeLLMProfile]:
    if profiles:
        for profile_id, patch in profiles.items():
            if isinstance(patch, Mapping):
                set_runtime_llm_profile(profile_id, patch)
    for profile_id in DEFAULT_PROFILE_IDS:
        _ensure_profile(profile_id)
    return dict(_PROFILES)


def set_runtime_llm_config(
    *,
    profile_id: Optional[str] = None,
    provider: Optional[str] = None,
    base_url: Optional[str] = None,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    enabled: Optional[bool] = None,
    fallback_to_mock: Optional[bool] = None,
) -> RuntimeLLMProfile:
    key = _coerce_profile_id(profile_id)
    patch = {
        "profile_id": key,
        "provider": provider,
        "base_url": base_url,
        "api_key": api_key,
        "model": model,
        "enabled": enabled,
        "fallback_to_mock": fallback_to_mock,
    }
    return set_runtime_llm_profile(key, patch)


def reset_runtime_llm_config() -> None:
    _seed_defaults()
    _load_from_env()


_seed_defaults()
_load_from_env()
