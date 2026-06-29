"""Engine Registry for Protocol v0.4 — Stage 6.5 mock provider registry.

Binding chain (frozen for this stage):

    Node.slot_binding  -> which Slot a node invokes
    Slot.engine_binding -> which Engine a slot binds
    Engine             -> the real capability adapter layer
    Provider           -> Provider Registry mock entry

Stage 6.5 hard limit: every engine resolves only to a mock provider registry
entry. No OpenAI/Claude/Gemini call, no URL, no API key read.
"""

from __future__ import annotations

from typing import Dict, List

from ..models.v0_4 import EngineType, EngineV04, ProtocolStatus, SlotType
from .provider_registry import PROVIDER_REGISTRY, provider_registry_map

ALLOWED_ENGINE_TYPES = set(EngineType)
ALLOWED_PROVIDERS = {provider.provider_id for provider in PROVIDER_REGISTRY}


ENGINE_REGISTRY: List[EngineV04] = [
    EngineV04(
        engine_id="llm_mock",
        engine_type=EngineType.llm,
        engine_name="LLM Mock Engine",
        supported_slot_types=[SlotType.llm],
        providers=["provider_llm_mock"],
        status=ProtocolStatus.mock,
    ),
    EngineV04(
        engine_id="memory_mock",
        engine_type=EngineType.memory,
        engine_name="Memory Mock Engine",
        supported_slot_types=[SlotType.memory],
        providers=["provider_memory_mock"],
        status=ProtocolStatus.mock,
    ),
    EngineV04(
        engine_id="tool_mock",
        engine_type=EngineType.tool,
        engine_name="Tool Mock Engine",
        supported_slot_types=[SlotType.tool],
        providers=["provider_tool_mock"],
        status=ProtocolStatus.mock,
    ),
    EngineV04(
        engine_id="tts_mock",
        engine_type=EngineType.tts,
        engine_name="TTS Mock Engine",
        supported_slot_types=[SlotType.tts],
        providers=["provider_tts_mock"],
        status=ProtocolStatus.mock,
    ),
    EngineV04(
        engine_id="avatar_mock",
        engine_type=EngineType.avatar,
        engine_name="Avatar Mock Engine",
        supported_slot_types=[SlotType.avatar],
        providers=["provider_avatar_mock"],
        status=ProtocolStatus.mock,
    ),
    EngineV04(
        engine_id="speech_mock",
        engine_type=EngineType.speech,
        engine_name="Speech Mock Engine",
        supported_slot_types=[SlotType.speech],
        providers=["provider_speech_mock"],
        status=ProtocolStatus.mock,
    ),
    EngineV04(
        engine_id="screen_mock",
        engine_type=EngineType.screen,
        engine_name="Screen Mock Engine",
        supported_slot_types=[SlotType.screen, SlotType.ar],
        providers=["provider_screen_mock"],
        status=ProtocolStatus.mock,
    ),
    EngineV04(
        engine_id="lattice_mock",
        engine_type=EngineType.screen,
        engine_name="Lattice Mock Engine",
        supported_slot_types=[SlotType.lattice],
        providers=["provider_screen_mock"],
        status=ProtocolStatus.mock,
    ),
]


def validate_engine_registry(engines: List[EngineV04]) -> List[str]:
    """Return a list of error strings; empty list means the registry is valid."""
    errors: List[str] = []
    seen: set[str] = set()
    providers = provider_registry_map()
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
                errors.append(f"engine {engine.engine_id} uses unknown provider registry id: {provider}")
                continue
            entry = providers.get(provider)
            if entry is None or not entry.mock:
                errors.append(f"engine {engine.engine_id} provider {provider} is not mock")
            elif entry.engine_id != engine.engine_id:
                errors.append(f"engine {engine.engine_id} provider {provider} belongs to {entry.engine_id}")
    return errors


def validate_protocol_chain(engines, slots, modules) -> List[str]:
    """Validate the engine -> slot -> module binding chain integrity.

    - every Slot.engine_binding must reference a registered Engine;
    - the referenced Engine must support the Slot's slot_type;
    - every Module.slot_type must be served by at least one Slot.
    No execution and no real provider are involved.
    """
    errors: List[str] = []
    engine_by_id = {e.engine_id: e for e in engines}
    served_slot_types = {s.slot_type for s in slots}
    for slot in slots:
        if slot.engine_binding:
            engine = engine_by_id.get(slot.engine_binding)
            if engine is None:
                errors.append(f"slot {slot.slot_id} binds unknown engine: {slot.engine_binding}")
            elif slot.slot_type not in engine.supported_slot_types:
                errors.append(f"engine {engine.engine_id} does not support slot_type {slot.slot_type} (slot {slot.slot_id})")
    for module in modules:
        if module.slot_type is not None and module.slot_type not in served_slot_types:
            errors.append(f"module {module.module_id} declares slot_type {module.slot_type} with no serving slot")
    return errors


def get_engine_registry() -> List[EngineV04]:
    return list(ENGINE_REGISTRY)


def engine_registry_map() -> Dict[str, EngineV04]:
    return {engine.engine_id: engine for engine in ENGINE_REGISTRY}


def get_engine(engine_id: str) -> EngineV04 | None:
    return engine_registry_map().get(engine_id)
