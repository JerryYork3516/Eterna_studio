"""Runtime Config Service — Stage 6.6.x Runtime Config Persistence v2.

Persistence & privacy boundary (do not violate):
  * Real config (including secrets) is stored ONLY in a local, git-ignored file:
        apps/api/.runtime/runtime_config.local.json
  * Secret fields (api_key / token / secret) are persisted to that local file but
    are NEVER returned by any GET — `masked_section()` replaces each secret with
    a `has_<field>` boolean.
  * runtime_config is NEVER written into a Node / Module / Slot / DR / trace.
  * Load priority at startup: local JSON  >  environment  >  mock/disabled default.

Compatibility:
  * The `llm` section now stores a map of runtime profiles, but the old flat
    shape (base_url / api_key / model / enabled / fallback_to_mock) is still
    accepted for backward compatibility and mapped to the `default` profile.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Mapping

from .runtime_llm_config import (
    DEFAULT_PROFILE_ID,
    DEFAULT_PROFILE_IDS,
    get_runtime_llm_profile,
    get_runtime_llm_profiles,
    reset_runtime_llm_config,
    set_runtime_llm_profile,
    set_runtime_llm_profiles,
)

SECTIONS = ("llm", "memory", "lattice", "tts", "screen")
SECRET_KEYS = ("api_key", "token", "secret")
CONFIG_VERSION = 2

_RUNTIME_DIR = Path(__file__).resolve().parents[2] / ".runtime"
_LOCAL_PATH = _RUNTIME_DIR / "runtime_config.local.json"

# Process-local store for the non-llm sections (llm lives in runtime_llm_config).
_STORE: Dict[str, Dict[str, Any]] = {}


def _default_section(section: str) -> Dict[str, Any]:
    return {"enabled": False}


def _llm_raw() -> Dict[str, Any]:
    profiles = {profile_id: profile.raw() for profile_id, profile in get_runtime_llm_profiles().items()}
    return {"default_profile_id": DEFAULT_PROFILE_ID, "profiles": profiles}


def _llm_masked() -> Dict[str, Any]:
    profiles = {profile_id: profile.masked() for profile_id, profile in get_runtime_llm_profiles().items()}
    default_profile = profiles.get(DEFAULT_PROFILE_ID) or get_runtime_llm_profile(DEFAULT_PROFILE_ID).masked()
    return {
        "default_profile_id": DEFAULT_PROFILE_ID,
        "profile_ids": list(get_runtime_llm_profiles().keys()),
        "profiles": profiles,
        **default_profile,
        "has_api_key": bool(default_profile.get("has_api_key")),
    }


def get_section_raw(section: str) -> Dict[str, Any]:
    if section == "llm":
        return _llm_raw()
    return dict(_STORE.get(section, _default_section(section)))


def mask_section(data: Dict[str, Any]) -> Dict[str, Any]:
    masked: Dict[str, Any] = {}
    for key, value in data.items():
        if key in SECRET_KEYS:
            masked[f"has_{key}"] = bool(value)
        else:
            masked[key] = value
    return masked


def get_section_masked(section: str) -> Dict[str, Any]:
    if section == "llm":
        return _llm_masked()
    return mask_section(get_section_raw(section))


def get_all_masked() -> Dict[str, Any]:
    return {section: get_section_masked(section) for section in SECTIONS}


def _apply_llm_patch(section_patch: Mapping[str, Any]) -> None:
    if "profiles" in section_patch and isinstance(section_patch["profiles"], Mapping):
        set_runtime_llm_profiles(section_patch["profiles"])  # type: ignore[arg-type]
        return

    profile_id = str(section_patch.get("profile_id") or DEFAULT_PROFILE_ID)
    set_runtime_llm_profile(
        profile_id,
        {
            "profile_id": profile_id,
            "provider": section_patch.get("provider"),
            "base_url": section_patch.get("base_url"),
            "api_key": section_patch.get("api_key"),
            "model": section_patch.get("model"),
            "enabled": section_patch.get("enabled"),
            "fallback_to_mock": section_patch.get("fallback_to_mock"),
        },
    )


def set_section(section: str, patch: Dict[str, Any] | None) -> Dict[str, Any]:
    if section not in SECTIONS:
        raise KeyError(section)
    patch = patch or {}
    if section == "llm":
        _apply_llm_patch(patch)
    else:
        current = _STORE.setdefault(section, _default_section(section))
        for key, value in patch.items():
            if key in SECRET_KEYS and (value is None or value == ""):
                continue
            if value is None:
                continue
            current[key] = value
    _save_local()
    return get_section_masked(section)


def set_sections(patch: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    for section, section_patch in (patch or {}).items():
        if section in SECTIONS and isinstance(section_patch, dict):
            set_section(section, section_patch)
    return get_all_masked()


def _save_local() -> None:
    data = {
        "version": CONFIG_VERSION,
        "sections": {section: get_section_raw(section) for section in SECTIONS},
    }
    _RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    tmp = _LOCAL_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(_LOCAL_PATH)


def _load_llm_section(raw_llm: Any) -> None:
    if isinstance(raw_llm, dict) and isinstance(raw_llm.get("profiles"), dict):
        set_runtime_llm_profiles(raw_llm.get("profiles"))
        return
    if isinstance(raw_llm, dict):
        set_runtime_llm_profile(DEFAULT_PROFILE_ID, raw_llm)


def load() -> None:
    for section in SECTIONS:
        if section != "llm":
            _STORE[section] = _default_section(section)

    data: Any = None
    if _LOCAL_PATH.exists():
        try:
            data = json.loads(_LOCAL_PATH.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            data = None

    if not (isinstance(data, dict) and isinstance(data.get("sections"), dict)):
        return

    sections = data["sections"]
    _load_llm_section(sections.get("llm"))
    for section in SECTIONS:
        if section != "llm" and isinstance(sections.get(section), dict):
            _STORE[section] = dict(sections[section])


def reset() -> None:
    for section in SECTIONS:
        if section != "llm":
            _STORE[section] = _default_section(section)
    reset_runtime_llm_config()


load()
