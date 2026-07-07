"""Studio Assistant API acceptance tests.

DeepSeek is always mocked here; no test performs a network call.
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
            "diagnostics": {"provider": "mock-deepseek"},
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
    monkeypatch.setattr(service, "StudioAssistantDeepSeekClient", MockStudioAssistantClient)

    body = client.post("/studio-assistant/recommend", json=_payload()).json()

    assert body["ok"] is True
    assert body["mode"] == "recommend"
    assert body["requires_user_confirm"] is True
    assert body["patch"] == {"target_field": "tone_boundary", "proposed_value": "calm and bounded"}
    assert body["diagnostics"]["provider"] == "mock-deepseek"
    assert body["diagnostics"]["system_prompt_seen"] is True


def test_studio_assistant_disabled_returns_structured_status(monkeypatch):
    monkeypatch.setenv("STUDIO_ASSISTANT_ENABLED", "false")

    body = client.post("/studio-assistant/explain", json=_payload("explain")).json()

    assert body["ok"] is False
    assert body["mode"] == "explain"
    assert body["requires_user_confirm"] is True
    assert body["patch"] is None
    assert body["diagnostics"]["status"] == "disabled"


def test_studio_assistant_deepseek_failure_is_structured(monkeypatch):
    monkeypatch.setenv("STUDIO_ASSISTANT_ENABLED", "true")
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)

    body = client.post("/studio-assistant/audit", json=_payload("audit")).json()

    assert body["ok"] is False
    assert body["mode"] == "audit"
    assert body["requires_user_confirm"] is True
    assert body["diagnostics"]["status"] == "missing_api_key"


def test_system_prompt_contains_required_boundaries():
    required = [
        "你是 Eterna Studio 的字段填写与审核助手。",
        "你只辅助 Studio 配置，不参与 Runtime 执行。",
        "不要生成 Runtime、Provider、Slot、Engine 代码。",
        "不要建议把 API Key 写入前端、Canvas 或 DR。",
        "不要硬编码居民姓名到非 Layer 1。",
        "只输出结构化建议。",
        "任何修改必须用户确认。",
        "优先保持身份稳定、边界稳定、语言稳定、记忆稳定。",
    ]
    for item in required:
        assert item in service.SYSTEM_PROMPT


def test_studio_assistant_files_do_not_use_runtime_registries():
    root = Path(__file__).resolve().parents[1]
    paths = [
        root / "app/routers/studio_assistant.py",
        root / "app/services/studio_assistant_service.py",
        root / "app/services/studio_assistant_deepseek_client.py",
    ]
    forbidden = ["provider_registry", "engine_registry", "slot_catalog", "execution_engine", "resident_runtime", "dr_compiler"]
    for path in paths:
        text = path.read_text()
        for token in forbidden:
            assert token not in text

