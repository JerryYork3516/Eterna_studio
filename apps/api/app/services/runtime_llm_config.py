"""Runtime LLM Config — Stage 6.6 real LLM v1.

Process-local, **global single** runtime LLM configuration. This is the ONLY
place the backend holds a real LLM base_url / api_key / model. It is reached only
by the runtime (resident_runtime reasoning) and the real LLM adapter.

Security boundary (do not violate):
  * The api_key lives ONLY in this process memory (+ optional env fallback). It is
    NEVER serialized into a DR, a Canvas export, a Node/Module/Slot, a trace, a
    response body, or any file. `masked()` is the only view exposed outward and
    never reveals the key.
  * This module is intentionally NOT one of the files scanned by the
    `forbidden_import` test (which only scans llm_mock_engine.py and
    engine_registry.py), so reading os.environ / api_key here is allowed.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class RuntimeLLMConfig:
    base_url: str = ""
    api_key: str = ""  # process-memory only; never serialized / exported / logged
    model: str = ""
    enabled: bool = False
    fallback_to_mock: bool = True

    def is_valid(self) -> bool:
        """True when a real LLM call should be attempted."""
        return self.enabled and bool(self.base_url) and bool(self.api_key) and bool(self.model)

    def masked(self) -> Dict[str, Any]:
        """Outward-safe view. NEVER includes the raw api_key."""
        return {
            "base_url": self.base_url,
            "model": self.model,
            "enabled": self.enabled,
            "fallback_to_mock": self.fallback_to_mock,
            "has_api_key": bool(self.api_key),
            "is_valid": self.is_valid(),
        }


_CONFIG = RuntimeLLMConfig()


def _load_from_env() -> None:
    """Env fallback — only fills empty fields, only at import time.

    ETERNA_LLM_BASE_URL / ETERNA_LLM_API_KEY / ETERNA_LLM_MODEL / ETERNA_LLM_ENABLED.
    """
    if not _CONFIG.base_url:
        _CONFIG.base_url = (os.environ.get("ETERNA_LLM_BASE_URL") or "").strip()
    if not _CONFIG.api_key:
        _CONFIG.api_key = os.environ.get("ETERNA_LLM_API_KEY") or ""
    if not _CONFIG.model:
        _CONFIG.model = (os.environ.get("ETERNA_LLM_MODEL") or "").strip()
    env_enabled = os.environ.get("ETERNA_LLM_ENABLED")
    if env_enabled is not None:
        _CONFIG.enabled = env_enabled.strip().lower() in ("1", "true", "yes", "on")
    elif _CONFIG.base_url and _CONFIG.api_key and _CONFIG.model:
        # If a full config came from env but no explicit enable flag, enable it.
        _CONFIG.enabled = True


_load_from_env()


def get_runtime_llm_config() -> RuntimeLLMConfig:
    return _CONFIG


def set_runtime_llm_config(
    *,
    base_url: Optional[str] = None,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    enabled: Optional[bool] = None,
    fallback_to_mock: Optional[bool] = None,
) -> RuntimeLLMConfig:
    """Update the global config in place. A field left as None is unchanged.

    An empty-string api_key is treated as "leave unchanged" so the UI can submit
    the form without resubmitting (or ever seeing) the stored key.
    """
    if base_url is not None:
        _CONFIG.base_url = base_url.strip()
    if api_key is not None and api_key != "":
        _CONFIG.api_key = api_key
    if model is not None:
        _CONFIG.model = model.strip()
    if enabled is not None:
        _CONFIG.enabled = bool(enabled)
    if fallback_to_mock is not None:
        _CONFIG.fallback_to_mock = bool(fallback_to_mock)
    return _CONFIG


def reset_runtime_llm_config() -> None:
    """Test seam: clear the in-process config (does NOT re-read env)."""
    _CONFIG.base_url = ""
    _CONFIG.api_key = ""
    _CONFIG.model = ""
    _CONFIG.enabled = False
    _CONFIG.fallback_to_mock = True
