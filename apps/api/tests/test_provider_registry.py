"""Stage 6.5 Provider Registry acceptance — mock-only Engine -> Provider path.

Run: cd apps/api && .venv/bin/python -m pytest tests/test_provider_registry.py -q
"""

from __future__ import annotations

from app.registry.engine_registry import get_engine_registry, validate_engine_registry
from app.registry.provider_registry import get_provider, list_providers, resolve_provider_for_engine
from app.services.provider_adapters import route_provider_by_id, route_provider_for_engine


EXPECTED_PROVIDER_TYPES = {"llm", "memory", "tool", "tts", "avatar", "speech", "screen"}


def test_provider_registry_has_seven_mock_provider_types():
    providers = list_providers()
    assert {provider["provider_type"] for provider in providers} == EXPECTED_PROVIDER_TYPES
    assert len(providers) == len(EXPECTED_PROVIDER_TYPES)
    assert all(provider["mock"] is True for provider in providers)


def test_existing_mock_providers_are_registered():
    assert resolve_provider_for_engine("llm_mock")["provider_id"] == "provider_llm_mock"
    assert resolve_provider_for_engine("memory_mock")["provider_id"] == "provider_memory_mock"
    assert resolve_provider_for_engine("tool_mock")["provider_id"] == "provider_tool_mock"


def test_placeholder_mock_adapters_return_deterministic_responses():
    assert route_provider_for_engine("tts_mock", {"text": "hello"})["voice"] == "mock_voice"
    assert route_provider_for_engine("avatar_mock", {"pose": "wave"})["avatar_state"]["pose"] == "wave"
    assert route_provider_for_engine("speech_mock", {"transcript": "hello"})["transcript"] == "hello"
    assert route_provider_for_engine("screen_mock", {"state": "visible"})["screen_state"] == "visible"


def test_engine_registry_resolves_only_registered_mock_providers():
    engines = get_engine_registry()
    assert validate_engine_registry(engines) == []
    for engine in engines:
        provider = resolve_provider_for_engine(engine.engine_id)
        assert provider is not None
        assert provider["provider_id"] in engine.providers
        assert provider["mock"] is True


def test_unknown_engine_and_provider_return_clear_errors():
    unknown_engine = route_provider_for_engine("missing_engine", {})
    assert unknown_engine["status"] == "error"
    assert "unknown engine_id" in unknown_engine["error"]

    unknown_provider = route_provider_by_id("missing_provider", {})
    assert unknown_provider["status"] == "error"
    assert "unknown provider_id" in unknown_provider["error"]
    assert get_provider("missing_provider") is None
