"""Provider Registry — Stage 6.5 mock-only provider catalog.

Binding chain:
    Slot -> Engine -> Provider Adapter -> Execution Engine

This registry is declarative. It registers only deterministic mock providers and
never stores real provider config, credentials, URLs, tokens, or API keys.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class ProviderRegistryEntry:
    provider_id: str
    provider_type: str
    engine_id: str
    mock: bool = True
    status: str = "MOCK"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "provider_id": self.provider_id,
            "provider_type": self.provider_type,
            "engine_id": self.engine_id,
            "mock": self.mock,
            "status": self.status,
        }


PROVIDER_TYPES = frozenset({"llm", "memory", "tool", "tts", "avatar", "speech", "screen"})

PROVIDER_REGISTRY: List[ProviderRegistryEntry] = [
    ProviderRegistryEntry("provider_llm_mock", "llm", "llm_mock"),
    ProviderRegistryEntry("provider_memory_mock", "memory", "memory_mock"),
    ProviderRegistryEntry("provider_tool_mock", "tool", "tool_mock"),
    ProviderRegistryEntry("provider_tts_mock", "tts", "tts_mock"),
    ProviderRegistryEntry("provider_avatar_mock", "avatar", "avatar_mock"),
    ProviderRegistryEntry("provider_speech_mock", "speech", "speech_mock"),
    ProviderRegistryEntry("provider_screen_mock", "screen", "screen_mock"),
    ProviderRegistryEntry("provider_lattice_mock", "screen", "lattice_mock"),
    # Stage 6.6 real LLM v1 (additive — the seven mock providers above are
    # unchanged). llm_primary routes to the real OpenAI-compatible adapter;
    # llm_fallback is the mock used when the real call is unconfigured/fails.
    ProviderRegistryEntry("provider_llm_real", "llm", "llm_primary", mock=False, status="READY"),
    ProviderRegistryEntry("provider_llm_fallback", "llm", "llm_fallback", mock=True, status="MOCK"),
]

# Engine ids of the real-LLM mapping (Stage 6.6). The mock catalog is unchanged.
LLM_PRIMARY_ENGINE_ID = "llm_primary"
LLM_FALLBACK_ENGINE_ID = "llm_mock"


def list_providers() -> List[Dict[str, Any]]:
    return [provider.to_dict() for provider in PROVIDER_REGISTRY]


def provider_registry_map() -> Dict[str, ProviderRegistryEntry]:
    return {provider.provider_id: provider for provider in PROVIDER_REGISTRY}


def provider_engine_map() -> Dict[str, ProviderRegistryEntry]:
    return {provider.engine_id: provider for provider in PROVIDER_REGISTRY}


def get_provider(provider_id: str) -> Optional[Dict[str, Any]]:
    provider = provider_registry_map().get(provider_id)
    return provider.to_dict() if provider else None


def get_provider_entry(provider_id: str) -> Optional[ProviderRegistryEntry]:
    return provider_registry_map().get(provider_id)


def resolve_provider_for_engine(engine_id: str) -> Optional[Dict[str, Any]]:
    provider = provider_engine_map().get(engine_id)
    return provider.to_dict() if provider else None


def resolve_provider_entry_for_engine(engine_id: str) -> Optional[ProviderRegistryEntry]:
    return provider_engine_map().get(engine_id)
