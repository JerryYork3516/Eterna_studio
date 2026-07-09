"""Studio Assistant API acceptance tests.

Assistant LLM calls are mocked or stopped before network. No test calls a real
provider endpoint.
"""

from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app
from app.services import studio_assistant_service as service

client = TestClient(app)


class MockStudioAssistantClient:
    def complete_json(self, *, system_prompt: str, user_prompt: str):
        payload = json.loads(user_prompt)
        return {
            "ok": True,
            "content": {
                "summary": f"{payload['mode']} summary",
                "suggestions": ["Keep the field stable."],
                "warnings": ["User confirmation required."],
                "patch": {
                    "target_field": payload.get("field_key") or "tone",
                    "proposed_value": "calm and bounded",
                },
                "diagnostics": {"mock": True, "system_prompt_seen": "Eterna Studio" in system_prompt},
            },
            "diagnostics": {"provider": "mock-provider", "model": "mock-model", "enabled": True},
        }


def _payload(mode: str = "recommend") -> dict:
    return {
        "canvas_id": "studio-canvas",
        "layer_id": "layer_8",
        "module_id": "language_behavior_module_v0",
        "node_id": "node-field-input",
        "field_key": "tone_boundary",
        "selected_text": "",
        "mode": mode,
        "context": {
            "resident_identity": {"source_layer": "layer_1"},
            "current_layer": {"layer_id": "layer_8"},
            "current_module": {"module_id": "language_behavior_module_v0"},
            "current_node": {"node_id": "node-field-input"},
            "field_references": [],
            "neighbor_modules": [],
        },
    }


def test_studio_assistant_recommend_uses_mock_client(monkeypatch):
    monkeypatch.setenv("STUDIO_ASSISTANT_ENABLED", "true")
    monkeypatch.setattr(service, "StudioAssistantLLMClient", MockStudioAssistantClient)

    body = client.post("/studio-assistant/recommend", json=_payload()).json()

    assert body["ok"] is True
    assert body["provider"] == "mock-provider"
    assert body["model"] == "mock-model"
    assert body["mode"] == "recommend"
    assert body["requires_user_confirm"] is True
    assert body["patch"] == {"target_field": "tone_boundary", "proposed_value": "calm and bounded"}
    assert body["diagnostics"]["provider"] == "mock-provider"
    assert body["diagnostics"]["system_prompt_seen"] is True


def test_studio_assistant_disabled_returns_structured_status(monkeypatch):
    monkeypatch.setenv("STUDIO_ASSISTANT_ENABLED", "false")

    body = client.post("/studio-assistant/explain", json=_payload("explain")).json()

    assert body["ok"] is False
    assert body["provider"] == "deepseek"
    assert body["model"] == "deepseek-chat"
    assert body["mode"] == "explain"
    assert body["requires_user_confirm"] is True
    assert body["patch"] is None
    assert body["diagnostics"]["status"] == "disabled"


def test_studio_assistant_missing_api_key_is_structured(monkeypatch):
    monkeypatch.setenv("STUDIO_ASSISTANT_ENABLED", "true")
    monkeypatch.delenv("STUDIO_ASSISTANT_API_KEY", raising=False)
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)

    body = client.post("/studio-assistant/audit", json=_payload("audit")).json()

    assert body["ok"] is False
    assert body["provider"] == "deepseek"
    assert body["model"] == "deepseek-chat"
    assert body["mode"] == "audit"
    assert body["requires_user_confirm"] is True
    assert body["diagnostics"]["status"] == "missing_api_key"


def test_audit_does_not_write_fields(monkeypatch):
    monkeypatch.setenv("STUDIO_ASSISTANT_ENABLED", "true")
    monkeypatch.setattr(service, "StudioAssistantLLMClient", MockStudioAssistantClient)
    payload = _payload("audit")
    payload["context"]["current_field"] = {"field_key": "tone_boundary", "value": "original"}

    body = client.post("/studio-assistant/audit", json=payload).json()

    assert body["ok"] is True
    assert body["requires_user_confirm"] is True
    assert payload["context"]["current_field"]["value"] == "original"


def test_api_key_never_leaks_in_response(monkeypatch):
    monkeypatch.setenv("STUDIO_ASSISTANT_ENABLED", "true")
    monkeypatch.setenv("STUDIO_ASSISTANT_API_KEY", "studio-secret-key")
    monkeypatch.setattr(service, "StudioAssistantLLMClient", MockStudioAssistantClient)

    body = client.post("/studio-assistant/recommend", json=_payload()).json()
    serialized = json.dumps(body)

    assert "studio-secret-key" not in serialized
    assert "api_key" not in serialized


def test_provider_and_model_switch_from_environment(monkeypatch):
    monkeypatch.setenv("STUDIO_ASSISTANT_ENABLED", "true")
    monkeypatch.setenv("STUDIO_ASSISTANT_PROVIDER", "qwen-compatible")
    monkeypatch.setenv("STUDIO_ASSISTANT_BASE_URL", "https://qwen.example/v1")
    monkeypatch.setenv("STUDIO_ASSISTANT_MODEL", "qwen-max")
    monkeypatch.delenv("STUDIO_ASSISTANT_API_KEY", raising=False)
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)

    body = client.post("/studio-assistant/recommend", json=_payload()).json()

    assert body["ok"] is False
    assert body["provider"] == "qwen-compatible"
    assert body["model"] == "qwen-max"
    assert body["diagnostics"]["status"] == "missing_api_key"


def test_legacy_deepseek_api_key_maps_to_assistant_config(monkeypatch):
    from app.services.studio_assistant_config import load_studio_assistant_config

    monkeypatch.delenv("STUDIO_ASSISTANT_API_KEY", raising=False)
    monkeypatch.setenv("DEEPSEEK_API_KEY", "legacy-secret-key")

    cfg = load_studio_assistant_config()

    assert cfg.provider == "deepseek"
    assert cfg.api_key == "legacy-secret-key"
    assert cfg.masked()["has_api_key"] is True
    assert "legacy-secret-key" not in json.dumps(cfg.masked())


def test_llm_client_uses_configurable_openai_compatible_endpoint(monkeypatch):
    from app.services import studio_assistant_llm_client as llm_client
    from app.services.studio_assistant_config import StudioAssistantConfig

    calls = []

    class FakeResponse:
        status_code = 200

        def json(self):
            return {"choices": [{"message": {"content": "{\"summary\":\"ok\",\"suggestions\":[],\"warnings\":[],\"patch\":null}"}}]}

    class FakeHTTPXClient:
        def __init__(self, timeout):
            self.timeout = timeout

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def post(self, url, json, headers):
            calls.append({"url": url, "json": json, "headers": headers, "timeout": self.timeout})
            return FakeResponse()

    monkeypatch.setattr(llm_client.httpx, "Client", FakeHTTPXClient)
    cfg = StudioAssistantConfig(
        provider="openai-compatible",
        api_key="client-secret-key",
        base_url="https://llm.example/v1",
        model="model-x",
        enabled=True,
        timeout_seconds=12.0,
    )

    result = llm_client.StudioAssistantLLMClient(cfg).complete_json(system_prompt="system", user_prompt="user")

    assert result["ok"] is True
    assert result["diagnostics"]["provider"] == "openai-compatible"
    assert result["diagnostics"]["model"] == "model-x"
    assert calls[0]["url"] == "https://llm.example/v1/chat/completions"
    assert calls[0]["json"]["model"] == "model-x"
    assert calls[0]["timeout"] == 12.0
    assert calls[0]["headers"]["Authorization"] == "Bearer client-secret-key"
    assert "client-secret-key" not in json.dumps(result)


def test_system_prompt_contains_required_boundaries():
    required = [
        "你是 Eterna Studio 的字段填写与审核助手。",
        "你只辅助 Studio 配置，不参与 Runtime 执行。",
        "你不能建议修改 Runtime、Provider、Slot、Engine。",
        "你不能建议把 API Key 写入前端、Canvas、DR 文件或 GitHub。",
        "你不能在非 Layer 1 硬编码居民姓名、resident_id、codename、昵称。",
        "你必须保持身份稳定、语言稳定、边界稳定、记忆稳定。",
        "你的输出必须是结构化 JSON。",
        "任何修改都必须等待用户确认。",
    ]
    for item in required:
        assert item in service.SYSTEM_PROMPT


def test_studio_assistant_files_do_not_use_runtime_registries():
    root = Path(__file__).resolve().parents[1]
    paths = [
        root / "app/routers/studio_assistant.py",
        root / "app/services/studio_assistant_service.py",
        root / "app/services/studio_assistant_config.py",
        root / "app/services/studio_assistant_llm_client.py",
    ]
    forbidden = ["provider_registry", "engine_registry", "slot_catalog", "execution_engine", "resident_runtime", "dr_compiler"]
    for path in paths:
        text = path.read_text()
        for token in forbidden:
            assert token not in text
