"""Built-in Slot catalog for Protocol v0.4.

Slots are capability interfaces. They never call a real provider this stage:
provider stays None, enabled=False, execution_mode=mock. engine_binding points
to a mock Engine, which resolves to a mock Provider Registry entry.
"""

from __future__ import annotations

from typing import Dict, List

from ..models.v0_4 import (
    ContractStatus,
    FallbackPolicy,
    OnError,
    ProtocolStatus,
    SlotType,
    SlotV04,
)


def _slot(
    slot_id: str,
    slot_type: SlotType,
    *,
    engine_binding: str | None = None,
    runtime_capability: Dict[str, object] | None = None,
    trace_schema: Dict[str, object] | None = None,
    i18n_keys: Dict[str, str] | None = None,
) -> SlotV04:
    return SlotV04(
        slot_id=slot_id,
        slot_type=slot_type,
        provider=None,
        engine_binding=engine_binding,  # binds an Engine, never a real provider this stage
        enabled=False,
        status=ContractStatus.mock,
        fallback_policy=FallbackPolicy(on_error=OnError.mock, retry=0, fallback_provider=None),
        runtime_capability=runtime_capability or {},
        trace_schema=trace_schema or {},
        i18n_keys=i18n_keys or {},
    )


# One mock slot per allowed slot_type. slot_id values are unique.
# Slots bind Engines only; no Slot binds a real provider directly.
SLOT_CATALOG: List[SlotV04] = [
    _slot("slot_llm", SlotType.llm, engine_binding="llm_mock"),
    _slot(
        "slot_tts",
        SlotType.tts,
        engine_binding="tts_mock",
        runtime_capability={"methods": ["tts.speak", "tts.preview"], "mode": "mock"},
        trace_schema={"fields": [{"key": "voice_trace", "type": "array"}, {"key": "voice_state", "type": "string"}]},
        i18n_keys={"display_name": "slot.tts", "description": "slot.tts.description"},
    ),
    _slot(
        "slot_voice_status",
        SlotType.lattice,
        engine_binding="lattice_mock",
        runtime_capability={"methods": ["voice.status", "voice.sync.lattice_voice"], "mode": "mock"},
        trace_schema={"fields": [{"key": "voice_state", "type": "string"}, {"key": "lattice_state.voice_state", "type": "string"}]},
        i18n_keys={"display_name": "slot.voice_status", "description": "slot.voice_status.description"},
    ),
    _slot(
        "slot_speech_input_event",
        SlotType.speech,
        engine_binding="speech_mock",
        runtime_capability={"methods": ["speech.input_event"], "mode": "mock"},
        trace_schema={"fields": [{"key": "speech.input_event", "type": "object"}]},
        i18n_keys={"display_name": "slot.speech_input_event", "description": "slot.speech_input_event.description"},
    ),
    _slot("slot_memory", SlotType.memory, engine_binding="memory_mock"),
    _slot("slot_avatar", SlotType.avatar, engine_binding="avatar_mock"),
    _slot("slot_speech", SlotType.speech, engine_binding="speech_mock"),
    _slot("slot_screen", SlotType.screen, engine_binding="screen_mock"),
    _slot("slot_ar", SlotType.ar, engine_binding="screen_mock"),
    _slot("slot_tool", SlotType.tool, engine_binding="tool_mock"),
    _slot("slot_lattice_update", SlotType.lattice, engine_binding="lattice_mock"),
    _slot("slot_lattice_read", SlotType.lattice, engine_binding="lattice_mock"),
    _slot("slot_lattice_preview", SlotType.lattice, engine_binding="lattice_mock"),
]


def validate_slot_catalog(slots: List[SlotV04]) -> List[str]:
    """Return a list of error strings; empty list means the catalog is valid."""
    errors: List[str] = []
    seen: set[str] = set()
    for slot in slots:
        if not slot.slot_id:
            errors.append("slot_id is empty")
            continue
        if slot.slot_id in seen:
            errors.append(f"duplicate slot_id: {slot.slot_id}")
        seen.add(slot.slot_id)
    return errors


def get_slot_catalog() -> List[SlotV04]:
    return list(SLOT_CATALOG)


def slot_catalog_map() -> Dict[str, SlotV04]:
    return {slot.slot_id: slot for slot in SLOT_CATALOG}
