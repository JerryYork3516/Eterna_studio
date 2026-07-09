"""Studio Assistant LLM configuration.

The Studio Assistant has its own model configuration surface. It is not a
Runtime provider, engine, or slot, and it never stores credentials in canvas or
DR data. Credentials are read from backend environment variables only.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Dict

DEFAULT_PROVIDER = "deepseek"
DEFAULT_BASE_URL = "https://api.deepseek.com"
DEFAULT_MODEL = "deepseek-chat"
DEFAULT_TIMEOUT_SECONDS = 30.0


def env_flag(name: str, default: bool = True) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_text(name: str, fallback: str = "") -> str:
    return (os.environ.get(name) or fallback).strip()


def _env_float(name: str, fallback: float) -> float:
    value = os.environ.get(name)
    if value is None:
        return fallback
    try:
        parsed = float(value)
    except ValueError:
        return fallback
    return parsed if parsed > 0 else fallback


@dataclass(frozen=True)
class StudioAssistantConfig:
    provider: str
    api_key: str
    base_url: str
    model: str
    enabled: bool
    timeout_seconds: float

    def has_api_key(self) -> bool:
        return bool(self.api_key)

    def masked(self) -> Dict[str, Any]:
        return {
            "provider": self.provider,
            "base_url": self.base_url,
            "model": self.model,
            "enabled": self.enabled,
            "has_api_key": self.has_api_key(),
            "timeout_seconds": self.timeout_seconds,
        }


def load_studio_assistant_config() -> StudioAssistantConfig:
    provider = _env_text("STUDIO_ASSISTANT_PROVIDER", DEFAULT_PROVIDER) or DEFAULT_PROVIDER
    # Compatibility: older local setups may still use DeepSeek-specific env names.
    api_key = _env_text("STUDIO_ASSISTANT_API_KEY") or _env_text("DEEPSEEK_API_KEY")
    base_url = (
        _env_text("STUDIO_ASSISTANT_BASE_URL")
        or _env_text("DEEPSEEK_BASE_URL")
        or DEFAULT_BASE_URL
    ).rstrip("/")
    model = _env_text("STUDIO_ASSISTANT_MODEL") or _env_text("DEEPSEEK_MODEL") or DEFAULT_MODEL
    return StudioAssistantConfig(
        provider=provider,
        api_key=api_key,
        base_url=base_url,
        model=model,
        enabled=env_flag("STUDIO_ASSISTANT_ENABLED", default=True),
        timeout_seconds=_env_float("STUDIO_ASSISTANT_TIMEOUT_SECONDS", DEFAULT_TIMEOUT_SECONDS),
    )

