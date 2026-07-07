"""Studio Assistant DeepSeek client.

This client is intentionally separate from the runtime provider / engine /
slot chain. It reads credentials only from backend environment variables and
returns structured dictionaries instead of raising user-facing exceptions.
"""

from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, Optional

import httpx

DEFAULT_BASE_URL = "https://api.deepseek.com"
DEFAULT_MODEL = "deepseek-chat"
DEFAULT_TIMEOUT = 30.0


def env_flag(name: str, default: bool = True) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def deepseek_base_url() -> str:
    return (os.environ.get("DEEPSEEK_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")


def deepseek_model() -> str:
    return (os.environ.get("DEEPSEEK_MODEL") or DEFAULT_MODEL).strip() or DEFAULT_MODEL


def _endpoint(base_url: str) -> str:
    base = (base_url or DEFAULT_BASE_URL).rstrip("/")
    if base.endswith("/chat/completions"):
        return base
    return f"{base}/chat/completions"


def _extract_json_object(text: str) -> Dict[str, Any]:
    cleaned = (text or "").strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        parsed = json.loads(cleaned)
    except ValueError:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start < 0 or end <= start:
            raise
        parsed = json.loads(cleaned[start : end + 1])
    return parsed if isinstance(parsed, dict) else {"summary": str(parsed)}


class StudioAssistantDeepSeekClient:
    """OpenAI-compatible DeepSeek chat client for Studio Assistant only."""

    def __init__(self, *, api_key: Optional[str] = None, base_url: Optional[str] = None, model: Optional[str] = None, timeout: float = DEFAULT_TIMEOUT) -> None:
        self.api_key = api_key if api_key is not None else os.environ.get("DEEPSEEK_API_KEY", "")
        self.base_url = (base_url or deepseek_base_url()).rstrip("/")
        self.model = (model or deepseek_model()).strip() or DEFAULT_MODEL
        self.timeout = timeout

    def complete_json(self, *, system_prompt: str, user_prompt: str) -> Dict[str, Any]:
        if not self.api_key:
            return {
                "ok": False,
                "error": {
                    "code": "missing_api_key",
                    "message": "DEEPSEEK_API_KEY is not configured",
                },
                "diagnostics": {"provider": "deepseek", "model": self.model},
            }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        body = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.2,
            "response_format": {"type": "json_object"},
        }

        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(_endpoint(self.base_url), json=body, headers=headers)
        except httpx.TimeoutException:
            return {
                "ok": False,
                "error": {"code": "timeout", "message": "DeepSeek request timed out"},
                "diagnostics": {"provider": "deepseek", "model": self.model},
            }
        except httpx.HTTPError as exc:
            return {
                "ok": False,
                "error": {"code": "http_error", "message": f"DeepSeek request failed: {type(exc).__name__}"},
                "diagnostics": {"provider": "deepseek", "model": self.model},
            }

        if response.status_code >= 400:
            return {
                "ok": False,
                "error": {"code": "http_status", "message": f"DeepSeek HTTP {response.status_code}"},
                "diagnostics": {"provider": "deepseek", "model": self.model, "status_code": response.status_code},
            }

        try:
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            parsed = _extract_json_object(content if isinstance(content, str) else str(content))
        except (ValueError, KeyError, IndexError, TypeError):
            return {
                "ok": False,
                "error": {"code": "malformed_response", "message": "DeepSeek response was not valid assistant JSON"},
                "diagnostics": {"provider": "deepseek", "model": self.model},
            }

        return {
            "ok": True,
            "content": parsed,
            "diagnostics": {"provider": "deepseek", "model": self.model},
        }
