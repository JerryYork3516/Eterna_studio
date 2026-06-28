"""Runtime Config Service — Stage 6.6.x Runtime Config Persistence v1.

A single, unified place for the backend's real runtime configuration across the
6.6–6.10 capabilities. Sections: llm / memory / lattice / tts / screen.

Persistence & privacy boundary (do not violate):
  * Real config (including secrets) is stored ONLY in a local, git-ignored file:
        apps/api/.runtime/runtime_config.local.json
  * Secret fields (api_key / token / secret) are persisted to that local file but
    are NEVER returned by any GET — `masked_section()` replaces each secret with a
    `has_<field>` boolean.
  * runtime_config is NEVER written into a Node / Module / Slot / DR / trace.
  * Load priority at startup: local JSON  >  environment  >  mock/disabled default.

Compatibility: the `llm` section delegates to the existing Stage 6.6
`runtime_llm_config` (the canonical store the reasoning loop reads). This service
adds persistence around it without changing the runtime loop.

This module is intentionally NOT one of the files scanned by the
`forbidden_import` test (which only scans llm_mock_engine.py and
engine_registry.py), so reading/writing secrets to a local file here is allowed.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from .runtime_llm_config import get_runtime_llm_config, set_runtime_llm_config

SECTIONS = ("llm", "memory", "lattice", "tts", "screen")
SECRET_KEYS = ("api_key", "token", "secret")
CONFIG_VERSION = 1

# apps/api/.runtime/runtime_config.local.json  (parents: services -> app -> apps/api)
_RUNTIME_DIR = Path(__file__).resolve().parents[2] / ".runtime"
_LOCAL_PATH = _RUNTIME_DIR / "runtime_config.local.json"

_LLM_KEYS = ("base_url", "api_key", "model", "enabled", "fallback_to_mock")

# Process-local store for the non-llm sections (llm lives in runtime_llm_config).
_STORE: Dict[str, Dict[str, Any]] = {}


def _default_section(section: str) -> Dict[str, Any]:
    """Mock/disabled default for a not-yet-connected section."""
    return {"enabled": False}


def _llm_raw() -> Dict[str, Any]:
    cfg = get_runtime_llm_config()
    return {
        "base_url": cfg.base_url,
        "api_key": cfg.api_key,
        "model": cfg.model,
        "enabled": cfg.enabled,
        "fallback_to_mock": cfg.fallback_to_mock,
    }


def get_section_raw(section: str) -> Dict[str, Any]:
    """Raw config for a section, INCLUDING secrets. Internal / persistence only."""
    if section == "llm":
        return _llm_raw()
    return dict(_STORE.get(section, _default_section(section)))


def mask_section(data: Dict[str, Any]) -> Dict[str, Any]:
    """Replace each secret field with a `has_<field>` boolean."""
    masked: Dict[str, Any] = {}
    for key, value in data.items():
        if key in SECRET_KEYS:
            masked[f"has_{key}"] = bool(value)
        else:
            masked[key] = value
    return masked


def get_section_masked(section: str) -> Dict[str, Any]:
    """Outward-safe view for a section. NEVER contains a raw secret."""
    if section == "llm":
        # Keep the exact Stage 6.6 masked shape (base_url/model/enabled/.../has_api_key/is_valid).
        return get_runtime_llm_config().masked()
    return mask_section(get_section_raw(section))


def get_all_masked() -> Dict[str, Any]:
    return {section: get_section_masked(section) for section in SECTIONS}


def set_section(section: str, patch: Dict[str, Any] | None) -> Dict[str, Any]:
    """Merge `patch` into a section and persist to the local JSON. Returns masked.

    For any secret field, an empty/None value means "leave the stored value
    unchanged" (so the UI can save without resubmitting a stored secret).
    """
    if section not in SECTIONS:
        raise KeyError(section)
    patch = patch or {}
    if section == "llm":
        kwargs = {key: patch[key] for key in _LLM_KEYS if key in patch}
        set_runtime_llm_config(**kwargs)
    else:
        current = _STORE.setdefault(section, _default_section(section))
        for key, value in patch.items():
            if key in SECRET_KEYS and (value is None or value == ""):
                continue  # keep existing secret
            if value is None:
                continue
            current[key] = value
    _save_local()
    return get_section_masked(section)


def set_sections(patch: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """Apply a {section: patch} map (saves once per section). Returns all masked."""
    for section, section_patch in (patch or {}).items():
        if section in SECTIONS and isinstance(section_patch, dict):
            set_section(section, section_patch)
    return get_all_masked()


def _save_local() -> None:
    """Write the full raw config (with secrets) to the local git-ignored file."""
    data = {
        "version": CONFIG_VERSION,
        "sections": {section: get_section_raw(section) for section in SECTIONS},
    }
    _RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    tmp = _LOCAL_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(_LOCAL_PATH)


def load() -> None:
    """Load config with priority: local JSON > env > mock/disabled default.

    The env layer for `llm` is already applied by runtime_llm_config at import;
    this only overlays the local JSON on top (local wins). Non-llm sections start
    from their disabled default and are overlaid by the local JSON when present.
    """
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
        return  # no local file -> env (llm) / defaults (others) already in place

    sections = data["sections"]
    llm = sections.get("llm")
    if isinstance(llm, dict):
        set_runtime_llm_config(**{key: llm[key] for key in _LLM_KEYS if key in llm})
    for section in SECTIONS:
        if section != "llm" and isinstance(sections.get(section), dict):
            _STORE[section] = dict(sections[section])


def reset() -> None:
    """Test seam: clear the non-llm in-process sections to defaults."""
    for section in SECTIONS:
        if section != "llm":
            _STORE[section] = _default_section(section)


# Startup load (local JSON > env > default). Read-only; never writes.
load()
