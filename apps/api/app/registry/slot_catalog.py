"""Built-in Slot catalog for Protocol v0.4.

Slots are capability interfaces. They never call a real provider this stage:
provider/engine_binding stay None, enabled=False, execution_mode=mock. First
batch of slot_type is restricted to: llm / tts / memory / avatar / ar / tool.
"""

from __future__ import annotations

from typing import Dict, List

from ..models.v0_4 import (
    FallbackPolicy,
    OnError,
    ProtocolStatus,
    SlotType,
    SlotV04,
)


def _slot(slot_id: str, slot_type: SlotType, *, engine_binding: str | None = None) -> SlotV04:
    return SlotV04(
        slot_id=slot_id,
        slot_type=slot_type,
        provider=None,
        engine_binding=engine_binding,  # binds an Engine, never a real provider this stage
        enabled=False,
        status=ProtocolStatus.mock,
        fallback_policy=FallbackPolicy(on_error=OnError.mock, retry=0, fallback_provider=None),
    )


# One mock slot per allowed slot_type. slot_id values are unique.
# slot_llm binds the LLM mock engine (engine_binding -> Engine -> mock provider).
SLOT_CATALOG: List[SlotV04] = [
    _slot("slot_llm", SlotType.llm, engine_binding="llm_mock"),
    _slot("slot_tts", SlotType.tts),
    _slot("slot_memory", SlotType.memory),
    _slot("slot_avatar", SlotType.avatar),
    _slot("slot_ar", SlotType.ar),
    _slot("slot_tool", SlotType.tool),
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
