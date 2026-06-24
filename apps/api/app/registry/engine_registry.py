"""Engine Registry for Protocol v0.4 — Stage 5 (LLM mock only).

Binding chain (frozen for this stage):

    Node.slot_binding  -> which Slot a node invokes
    Slot.engine_binding -> which Engine/Provider a slot binds
    Engine             -> the real capability adapter layer
    Provider           -> "mock" only this stage

Stage 5 hard limits: engine_type is restricted to "llm" and provider to "mock".
No TTS/Image/Video engine, no OpenAI/Claude/Gemini call, no API key read.
"""

from __future__ import annotations

from typing import Dict, List

from ..models.v0_4 import EngineType, EngineV04, ProtocolStatus, SlotType

ALLOWED_ENGINE_TYPES = {EngineType.llm}
ALLOWED_PROVIDERS = {"mock"}


ENGINE_REGISTRY: List[EngineV04] = [
    EngineV04(
        engine_id="llm_mock",
        engine_type=EngineType.llm,
        engine_name="LLM Mock Engine",
        supported_slot_types=[SlotType.llm],
        providers=["mock"],
        status=ProtocolStatus.mock,
    ),
]


def validate_engine_registry(engines: List[EngineV04]) -> List[str]:
    """Return a list of error strings; empty list means the registry is valid."""
    errors: List[str] = []
    seen: set[str] = set()
    for engine in engines:
        if not engine.engine_id:
            errors.append("engine_id is empty")
            continue
        if engine.engine_id in seen:
            errors.append(f"duplicate engine_id: {engine.engine_id}")
        seen.add(engine.engine_id)
        if engine.engine_type not in ALLOWED_ENGINE_TYPES:
            errors.append(f"engine {engine.engine_id} uses disallowed engine_type: {engine.engine_type}")
        for provider in engine.providers:
            if provider not in ALLOWED_PROVIDERS:
                errors.append(f"engine {engine.engine_id} uses disallowed provider: {provider}")
    return errors


def get_engine_registry() -> List[EngineV04]:
    return list(ENGINE_REGISTRY)


def engine_registry_map() -> Dict[str, EngineV04]:
    return {engine.engine_id: engine for engine in ENGINE_REGISTRY}


def get_engine(engine_id: str) -> EngineV04 | None:
    return engine_registry_map().get(engine_id)
