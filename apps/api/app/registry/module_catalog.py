"""Built-in Module catalog for Protocol v0.4.

Modules are capability containers bound to an existing 13-layer layer_id. They
do not execute and never write into resident_instance. Future capabilities
(Agent / Wallet / Phone / Social / AR / Emergency Contact) are registered here
as placeholders only — no real logic this stage.
"""

from __future__ import annotations

from typing import Dict, List

from ..models.v0_4 import (
    CANONICAL_LAYER_IDS,
    ModuleV04,
    ProtocolStatus,
    RiskLevel,
    SlotType,
)


def _module(
    module_id: str,
    module_type: str,
    module_name: str,
    layer_id: str,
    *,
    status: ProtocolStatus = ProtocolStatus.mock,
    slot_type: SlotType | None = None,
    risk_level: RiskLevel = RiskLevel.none,
    category: str = "",
    is_placeholder: bool = True,
    audit_required: bool = False,
    human_confirm_required: bool = False,
    color_status: str = "gray",
) -> ModuleV04:
    return ModuleV04(
        module_id=module_id,
        module_type=module_type,
        module_name=module_name,
        layer_id=layer_id,
        status=status,
        slot_type=slot_type,
        risk_level=risk_level,
        category=category,
        is_placeholder=is_placeholder,
        audit_required=audit_required,
        human_confirm_required=human_confirm_required,
        color_status=color_status,
    )


# Catalog: each module bound to a frozen layer_id. module_id values are unique.
MODULE_CATALOG: List[ModuleV04] = [
    # Active / core trunk capabilities
    _module("module_identity_core", "identity", "Identity Core", "layer_1", status=ProtocolStatus.core, category="persona", is_placeholder=False, color_status="green"),
    _module("module_personality", "personality", "Personality", "layer_2", status=ProtocolStatus.core, category="persona", is_placeholder=False, color_status="green"),
    _module("module_safety_boundary", "safety", "Safety Boundary", "layer_3", status=ProtocolStatus.core, risk_level=RiskLevel.high, category="governance", is_placeholder=False, audit_required=True, color_status="green"),
    _module("module_legal_permission", "permission", "Legal Permission", "layer_4", status=ProtocolStatus.core, risk_level=RiskLevel.medium, category="governance", is_placeholder=False, audit_required=True, color_status="green"),
    _module("module_memory", "memory", "Memory", "layer_5", status=ProtocolStatus.mock, slot_type=SlotType.memory, category="cognition", color_status="amber"),
    _module("module_knowledge", "knowledge", "Knowledge", "layer_6", status=ProtocolStatus.mock, slot_type=SlotType.llm, category="cognition", color_status="amber"),
    _module("module_voice", "voice", "Voice Profile", "layer_10", status=ProtocolStatus.mock, slot_type=SlotType.tts, category="multimodal", color_status="amber"),
    _module("module_avatar", "avatar", "Particle Avatar", "layer_10", status=ProtocolStatus.mock, slot_type=SlotType.avatar, category="multimodal", color_status="amber"),
    _module("module_audit_export", "audit", "Audit / Export / Deploy", "layer_13", status=ProtocolStatus.ready, category="governance", is_placeholder=False, audit_required=True, color_status="green"),
    # Future capabilities — registered as placeholders only (no logic this stage)
    _module("module_agent", "agent", "Agent", "layer_9", status=ProtocolStatus.planned, slot_type=SlotType.tool, risk_level=RiskLevel.high, category="capability", audit_required=True, human_confirm_required=True),
    _module("module_wallet", "wallet", "Wallet", "layer_9", status=ProtocolStatus.later, slot_type=SlotType.tool, risk_level=RiskLevel.critical, category="capability", audit_required=True, human_confirm_required=True),
    _module("module_phone", "phone", "Phone", "layer_9", status=ProtocolStatus.later, slot_type=SlotType.tool, risk_level=RiskLevel.high, category="capability", audit_required=True, human_confirm_required=True),
    _module("module_social", "social", "Social", "layer_11", status=ProtocolStatus.planned, slot_type=SlotType.tool, risk_level=RiskLevel.medium, category="relationship", audit_required=True),
    _module("module_ar", "ar", "AR Presence", "layer_10", status=ProtocolStatus.planned, slot_type=SlotType.ar, risk_level=RiskLevel.medium, category="multimodal"),
    _module("module_emergency_contact", "emergency_contact", "Emergency Contact", "layer_4", status=ProtocolStatus.later, risk_level=RiskLevel.high, category="governance", audit_required=True, human_confirm_required=True),
]


def validate_module_catalog(modules: List[ModuleV04]) -> List[str]:
    """Return a list of error strings; empty list means the catalog is valid."""
    errors: List[str] = []
    seen: set[str] = set()
    for module in modules:
        if not module.module_id:
            errors.append("module_id is empty")
            continue
        if module.module_id in seen:
            errors.append(f"duplicate module_id: {module.module_id}")
        seen.add(module.module_id)
        if module.layer_id not in CANONICAL_LAYER_IDS:
            errors.append(f"module {module.module_id} bound to unknown layer_id: {module.layer_id}")
    return errors


def get_module_catalog() -> List[ModuleV04]:
    return list(MODULE_CATALOG)


def module_catalog_map() -> Dict[str, ModuleV04]:
    return {module.module_id: module for module in MODULE_CATALOG}
