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
