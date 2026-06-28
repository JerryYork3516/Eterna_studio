"""Capability validation — slots / tools / fallback, plus the declarative
capability_profile and skill_policy checks.

Reads the static registries only (slot / engine / module catalogs). It resolves
whether bindings *exist*; it never invokes a slot, engine, tool, or MCP.
"""

from __future__ import annotations

from ....models.v0_4 import SlotType
from ....registry.engine_registry import engine_registry_map
from ....registry.module_catalog import module_catalog_map
from ....registry.provider_registry import resolve_provider_for_engine
from ....registry.slot_catalog import slot_catalog_map
from ..dr_v0_2_schema import DigitalResidentV02Gate, ResidentClass
from .compile_audit_validator import provider_boundary_findings
from .dr_validation_result import DRValidationResult, finding

_ALLOWED_SKILL_SOURCES = {"official", "verified"}
# Resident classes enabled this stage (civilization_synthesis is reserved only).
_ENABLED_RESIDENT_CLASSES = {ResidentClass.industry_expertise, ResidentClass.human_empathy}
_WEIGHT_TOL = 1e-9


def validate_capabilities(model: DigitalResidentV02Gate, result: DRValidationResult) -> None:
    slots = slot_catalog_map()
    engines = engine_registry_map()
    modules = module_catalog_map()
    cap = model.capabilities

    declared_slot_types = set()
    for i, ref in enumerate(cap.slots):
        path = f"capabilities.slots[{i}]"
        catalog_slot = slots.get(ref.slot_id)
        if catalog_slot is None:
            result.add(finding("FAIL", "DR_CAP_SLOT_UNKNOWN", f"slot {ref.slot_id} not in slot registry", path))
            continue
        declared_slot_types.add(ref.slot_type)
        if ref.slot_type != catalog_slot.slot_type.value:
            result.add(
                finding("FAIL", "DR_CAP_SLOT_TYPE_MISMATCH", f"slot {ref.slot_id} slot_type {ref.slot_type!r} != catalog {catalog_slot.slot_type.value!r}", path)
            )
        if ref.engine_binding:
            engine = engines.get(ref.engine_binding)
            if engine is None:
                result.add(finding("FAIL", "DR_CAP_ENGINE_UNKNOWN", f"engine {ref.engine_binding} not in engine registry", path))
            else:
                supported = {t.value for t in engine.supported_slot_types}
                if ref.slot_type not in supported:
                    result.add(
                        finding("FAIL", "DR_CAP_ENGINE_SLOT_UNSUPPORTED", f"engine {ref.engine_binding} does not support slot_type {ref.slot_type!r}", path)
                    )
                if resolve_provider_for_engine(ref.engine_binding) is None:
                    result.add(
                        finding("FAIL", "DR_CAP_ENGINE_PROVIDER_UNRESOLVED", f"engine {ref.engine_binding} has no registered mock provider", path)
                    )

    declared_tool_ids = set()
    for i, tool in enumerate(cap.tools):
        path = f"capabilities.tools[{i}]"
        declared_tool_ids.add(tool.tool_id)
        ref_id = tool.module_id or tool.tool_id
        module = modules.get(ref_id)
        if module is None:
            result.add(finding("FAIL", "DR_CAP_TOOL_UNKNOWN", f"tool {ref_id} not resolvable in module catalog", path))

    for i, pref in enumerate(cap.tool_preferences):
        if pref not in declared_tool_ids:
            result.add(
                finding("WARNING", "DR_CAP_TOOL_PREF_UNRESOLVED", f"tool_preference {pref!r} is not a declared tool", f"capabilities.tool_preferences[{i}]")
            )

    # required_slot_types must all be covered by a declared slot.
    for st in model.execution_policy.required_slot_types:
        if st not in declared_slot_types:
            result.add(
                finding("FAIL", "DR_CAP_REQUIRED_SLOT_UNMET", f"required slot_type {st!r} has no declared slot", "execution_policy.required_slot_types")
            )

    if not model.execution_policy.allow_tool_use and cap.tools:
        result.add(
            finding("WARNING", "DR_CAP_TOOL_USE_DISABLED", "tools declared but allow_tool_use is false", "execution_policy.allow_tool_use")
        )

    # slot_type values must be legal SlotType labels (defensive; schema is free str).
    legal_slot_types = {t.value for t in SlotType}
    for i, ref in enumerate(cap.slots):
        if ref.slot_type not in legal_slot_types:
            result.add(
                finding("FAIL", "DR_CAP_SLOT_TYPE_INVALID", f"slot_type {ref.slot_type!r} is not a known SlotType", f"capabilities.slots[{i}].slot_type")
            )

    result.add_all(provider_boundary_findings(model.model_dump(mode="json"), "dr", "DR_CAP_PROVIDER_CONFIG"))


def validate_capability_profile(model: DigitalResidentV02Gate, result: DRValidationResult) -> None:
    cp = model.capability_profile
    if cp.resident_class not in _ENABLED_RESIDENT_CLASSES:
        result.add(
            finding("FAIL", "DR_CAPROF_CLASS_NOT_ENABLED", f"resident_class {cp.resident_class.value!r} is reserved and not enabled this stage", "capability_profile.resident_class")
        )
    if not (0.7 <= cp.primary_weight <= 0.9):
        result.add(
            finding("FAIL", "DR_CAPROF_PRIMARY_WEIGHT_RANGE", "primary_weight must be in [0.7, 0.9]", "capability_profile.primary_weight")
        )
    if not (0.1 <= cp.secondary_weight <= 0.3):
        result.add(
            finding("FAIL", "DR_CAPROF_SECONDARY_WEIGHT_RANGE", "secondary_weight must be in [0.1, 0.3]", "capability_profile.secondary_weight")
        )
    if abs((cp.primary_weight + cp.secondary_weight) - 1.0) > _WEIGHT_TOL:
        result.add(
            finding("FAIL", "DR_CAPROF_WEIGHT_SUM", "primary_weight + secondary_weight must equal 1.0", "capability_profile")
        )
    if cp.primary_type == cp.secondary_type:
        result.add(
            finding("WARNING", "DR_CAPROF_TYPE_DUPLICATE", "primary_type equals secondary_type", "capability_profile.secondary_type")
        )


def validate_skill_policy(model: DigitalResidentV02Gate, result: DRValidationResult) -> None:
    sp = model.skill_policy
    if sp.unsigned_skill_policy.value != "deny":
        result.add(
            finding("FAIL", "DR_SKILL_UNSIGNED_POLICY", "unsigned_skill_policy must be 'deny'", "skill_policy.unsigned_skill_policy")
        )
    if sp.sandbox_required is not True:
        result.add(
            finding("FAIL", "DR_SKILL_SANDBOX_REQUIRED", "sandbox_required must be true", "skill_policy.sandbox_required")
        )
    for i, src in enumerate(sp.allowed_skill_sources):
        if src not in _ALLOWED_SKILL_SOURCES:
            result.add(
                finding("FAIL", "DR_SKILL_SOURCE_INVALID", f"allowed_skill_sources {src!r} must be one of {sorted(_ALLOWED_SKILL_SOURCES)}", f"skill_policy.allowed_skill_sources[{i}]")
            )
    # required_skills / skill_permissions are declarations only — type check, no step generation.
    for i, s in enumerate(sp.required_skills):
        if not isinstance(s, str):
            result.add(finding("WARNING", "DR_SKILL_DECL_TYPE", "required_skills entries must be strings", f"skill_policy.required_skills[{i}]"))
    for i, p in enumerate(sp.skill_permissions):
        if not isinstance(p, str):
            result.add(finding("WARNING", "DR_SKILL_DECL_TYPE", "skill_permissions entries must be strings", f"skill_policy.skill_permissions[{i}]"))
