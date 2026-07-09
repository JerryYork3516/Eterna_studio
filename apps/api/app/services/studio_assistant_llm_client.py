"""Configurable Studio Assistant LLM client.

This client speaks the OpenAI-compatible chat completions protocol, but it is
owned by Studio Assistant only. It does not use the Runtime provider registry,
engine registry, slot catalog, execution engine, or DR compiler.
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, Optional

import httpx

from .studio_assistant_config import StudioAssistantConfig, load_studio_assistant_config


def _endpoint(base_url: str) -> str:
    base = (base_url or "").rstrip("/")
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


class StudioAssistantLLMClient:
    """OpenAI-compatible chat client with configurable provider/base/model."""

    def __init__(self, config: Optional[StudioAssistantConfig] = None) -> None:
        self.config = config or load_studio_assistant_config()

    def metadata(self) -> Dict[str, Any]:
        return {
            "provider": self.config.provider,
            "model": self.config.model,
            "enabled": self.config.enabled,
            "base_url": self.config.base_url,
        }

    def complete_json(self, *, system_prompt: str, user_prompt: str) -> Dict[str, Any]:
        metadata = self.metadata()
        if not self.config.enabled:
            return {
                "ok": False,
                "error": {"code": "disabled", "message": "Studio Assistant is disabled"},
                "diagnostics": metadata,
            }
        if not self.config.api_key:
            return {
                "ok": False,
                "error": {"code": "missing_api_key", "message": "STUDIO_ASSISTANT_API_KEY is not configured"},
                "diagnostics": metadata,
            }

        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
        }
        body = {
            "model": self.config.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.2,
        }

        try:
            with httpx.Client(timeout=self.config.timeout_seconds) as client:
                response = client.post(_endpoint(self.config.base_url), json=body, headers=headers)
        except httpx.TimeoutException:
            return {
                "ok": False,
                "error": {"code": "timeout", "message": "Assistant LLM request timed out"},
                "diagnostics": metadata,
            }
        except httpx.HTTPError as exc:
            return {
                "ok": False,
                "error": {"code": "http_error", "message": f"Assistant LLM request failed: {type(exc).__name__}"},
                "diagnostics": metadata,
            }

        if response.status_code >= 400:
            return {
                "ok": False,
                "error": {"code": "http_status", "message": f"Assistant LLM HTTP {response.status_code}"},
                "diagnostics": {**metadata, "status_code": response.status_code},
            }

        try:
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            parsed = _extract_json_object(content if isinstance(content, str) else str(content))
        except (ValueError, KeyError, IndexError, TypeError):
            return {
                "ok": False,
                "error": {"code": "malformed_response", "message": "Assistant LLM response was not structured JSON"},
                "diagnostics": metadata,
            }

        return {
            "ok": True,
            "content": parsed,
            "diagnostics": metadata,
        }

