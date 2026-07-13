"""Capability validation — slots / tools / fallback, plus the declarative
capability_profile and skill_policy checks.

Reads the static registries only (slot / engine / module catalogs). It resolves
whether bindings *exist*; it never invokes a slot, engine, tool, or MCP.
"""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Sequence, Tuple

from ....models.v0_4 import SCHEMA_VERSION_V0_4, SlotType
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

STAGE_7_4_REQUIRED_SLOT_TYPES: Tuple[str, ...] = ("llm", "memory", "lattice")
_STAGE_7_4_OPTIONAL_SLOT_TYPES = frozenset({"tts", "speech", "screen", "avatar", "ar", "tool"})


def _mapping(value: Any) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return value
    if hasattr(value, "model_dump"):
        dumped = value.model_dump(mode="json")
        return dumped if isinstance(dumped, Mapping) else {}
    return {}


def _v03_finding(status: str, code: str, message: str, path: str) -> Dict[str, str]:
    return {"status": status, "code": code, "message": message, "path": path}


def _slot_chain(slot_type: str, slots: Sequence[Any]) -> Tuple[str, str | None, Dict[str, Any] | None]:
    """Resolve one DR slot type through the frozen Slot -> Engine -> Provider chain."""
    catalog_slots = slot_catalog_map()
    engines = engine_registry_map()
    matched_slot_id: str | None = None
    for raw_slot in slots:
        slot = _mapping(raw_slot)
        if str(slot.get("slot_type") or "") != slot_type:
            continue
        slot_id = str(slot.get("slot_id") or "")
        catalog_slot = catalog_slots.get(slot_id)
        if catalog_slot is None or catalog_slot.slot_type.value != slot_type:
            continue
        matched_slot_id = slot_id
        engine_id = str(slot.get("engine_binding") or catalog_slot.engine_binding or "")
        engine = engines.get(engine_id)
        if engine is None or slot_type not in {item.value for item in engine.supported_slot_types}:
            continue
        return engine_id, slot_id, resolve_provider_for_engine(engine_id)
    return "", matched_slot_id, None


def build_v03_runtime_contract(slots: Sequence[Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Build Stage 7.4 requirements from the real registries, without Provider binding."""
    required_engines: List[str] = []
    required_provider_types: List[str] = []
    provider_requirements: Dict[str, Any] = {
        "llm": {"required": True, "mode": "mock", "capabilities": ["reasoning"]},
        "memory": {"required": True, "mode": "local_runtime", "capabilities": ["read", "write", "view", "clear"]},
        "lattice": {"required": True, "mode": "mock_fallback", "capabilities": ["state_update", "state_read"]},
        "tts": {"required": False, "mode": "reserved", "capabilities": ["speak", "preview"]},
        "speech": {"required": False, "mode": "reserved", "capabilities": ["input_event"]},
        "avatar": {"required": False, "mode": "reserved", "capabilities": ["render_state"]},
        "screen": {"required": False, "mode": "reserved", "capabilities": ["context", "anchor", "guidance"]},
        "ar": {"required": False, "mode": "reserved", "capabilities": ["render_state"]},
        "tool": {"required": False, "mode": "reserved", "capabilities": ["invoke"]},
    }

    for slot_type in STAGE_7_4_REQUIRED_SLOT_TYPES:
        engine_id, _slot_id, provider = _slot_chain(slot_type, slots)
        if engine_id and engine_id not in required_engines:
            required_engines.append(engine_id)
        provider_type = str((provider or {}).get("provider_type") or "")
        if provider_type == slot_type:
            if provider_type not in required_provider_types:
                required_provider_types.append(provider_type)
            provider_requirements[slot_type]["provider_type"] = provider_type
        elif slot_type == "lattice" and provider and bool(provider.get("mock")):
            # The frozen registry maps lattice_mock to a screen-typed mock
            # provider. Keep it as an explicit fallback so screen does not
            # become a Stage 7.4 required provider capability.
            provider_requirements[slot_type]["fallback_provider_type"] = provider_type

    return (
        {
            "required_slot_types": list(STAGE_7_4_REQUIRED_SLOT_TYPES),
            "required_engines": required_engines,
            "required_provider_types": required_provider_types,
            "runtime_api_version": SCHEMA_VERSION_V0_4,
            "execution_mode": "mock",
            "fallback_mode": "mock_fallback",
        },
        provider_requirements,
    )


def validate_v03_runtime_contract(dr: Mapping[str, Any]) -> List[Dict[str, str]]:
    """Validate a v0.3 DR against the current Slot/Engine/Provider registries."""
    findings: List[Dict[str, str]] = []
    manifest = _mapping(dr.get("manifest"))
    payload = _mapping(dr.get("payload"))
    runtime = _mapping(payload.get("runtime_requirements"))
    provider_requirements = _mapping(payload.get("provider_requirements"))
    slots = payload.get("slots") if isinstance(payload.get("slots"), list) else []

    expected = list(STAGE_7_4_REQUIRED_SLOT_TYPES)
    manifest_required = [str(item) for item in manifest.get("required_capabilities", []) if isinstance(item, str)]
    runtime_required = [str(item) for item in runtime.get("required_slot_types", []) if isinstance(item, str)]
    if manifest_required != expected:
        findings.append(
            _v03_finding(
                "FAIL",
                "DR_CAP_REQUIRED_CAPABILITIES",
                f"manifest.required_capabilities must be {expected!r}, got {manifest_required!r}",
                "manifest.required_capabilities",
            )
        )
    if runtime_required != expected:
        findings.append(
            _v03_finding(
                "FAIL",
                "DR_CAP_REQUIRED_SLOTS",
                f"runtime required_slot_types must be {expected!r}, got {runtime_required!r}",
                "payload.runtime_requirements.required_slot_types",
            )
        )

    illegal_required = (set(manifest_required) | set(runtime_required)) & (_STAGE_7_4_OPTIONAL_SLOT_TYPES | {"voice"})
    if illegal_required:
        findings.append(
            _v03_finding(
                "FAIL",
                "DR_CAP_OPTIONAL_MARKED_REQUIRED",
                f"optional or nonexistent capabilities cannot be required in Stage 7.4: {sorted(illegal_required)!r}",
                "payload.runtime_requirements.required_slot_types",
            )
        )

    derived_runtime, derived_providers = build_v03_runtime_contract(slots)
    for slot_type in expected:
        engine_id, slot_id, provider = _slot_chain(slot_type, slots)
        if slot_id is None:
            findings.append(
                _v03_finding(
                    "FAIL",
                    "DR_CAP_REQUIRED_SLOT_UNRESOLVED",
                    f"required slot_type {slot_type!r} has no matching real Slot Catalog entry in payload.slots",
                    "payload.slots",
                )
            )
            continue
        if not engine_id:
            findings.append(
                _v03_finding(
                    "FAIL",
                    "DR_CAP_REQUIRED_ENGINE_UNRESOLVED",
                    f"required slot_type {slot_type!r} cannot resolve a supporting Engine",
                    f"payload.slots[{slot_id}].engine_binding",
                )
            )
            continue
        if provider is None:
            findings.append(
                _v03_finding(
                    "FAIL",
                    "DR_CAP_REQUIRED_PROVIDER_UNRESOLVED",
                    f"required engine {engine_id!r} cannot resolve a Provider or legal mock fallback",
                    "payload.runtime_requirements.required_engines",
                )
            )
        elif slot_type in {"llm", "memory"} and provider.get("provider_type") != slot_type:
            findings.append(
                _v03_finding(
                    "FAIL",
                    "DR_CAP_REQUIRED_PROVIDER_TYPE_MISMATCH",
                    f"required {slot_type!r} engine {engine_id!r} resolves provider_type {provider.get('provider_type')!r}",
                    f"payload.provider_requirements.{slot_type}.provider_type",
                )
            )
        elif slot_type == "lattice" and not bool(provider.get("mock")):
            findings.append(
                _v03_finding(
                    "FAIL",
                    "DR_CAP_LATTICE_FALLBACK_INVALID",
                    "lattice must resolve through the frozen legal mock fallback",
                    "payload.provider_requirements.lattice",
                )
            )

    actual_engines = [str(item) for item in runtime.get("required_engines", []) if isinstance(item, str)]
    if actual_engines != derived_runtime["required_engines"]:
        findings.append(
            _v03_finding(
                "FAIL",
                "DR_CAP_REQUIRED_ENGINES_MISMATCH",
                f"required_engines must be registry-derived {derived_runtime['required_engines']!r}, got {actual_engines!r}",
                "payload.runtime_requirements.required_engines",
            )
        )
    actual_provider_types = [str(item) for item in runtime.get("required_provider_types", []) if isinstance(item, str)]
    if actual_provider_types != derived_runtime["required_provider_types"]:
        findings.append(
            _v03_finding(
                "FAIL",
                "DR_CAP_REQUIRED_PROVIDER_TYPES_MISMATCH",
                f"required_provider_types must be registry-derived {derived_runtime['required_provider_types']!r}, got {actual_provider_types!r}",
                "payload.runtime_requirements.required_provider_types",
            )
        )

    for capability, expected_requirement in derived_providers.items():
        actual = _mapping(provider_requirements.get(capability))
        if bool(actual.get("required")) != bool(expected_requirement.get("required")):
            findings.append(
                _v03_finding(
                    "FAIL",
                    "DR_CAP_PROVIDER_REQUIREMENT_MISMATCH",
                    f"provider requirement {capability!r} required flag must be {expected_requirement.get('required')!r}",
                    f"payload.provider_requirements.{capability}.required",
                )
            )
        if not expected_requirement.get("required"):
            continue
        for field_name in ("mode", "provider_type", "fallback_provider_type"):
            if field_name in expected_requirement and actual.get(field_name) != expected_requirement.get(field_name):
                findings.append(
                    _v03_finding(
                        "FAIL",
                        "DR_CAP_PROVIDER_REQUIREMENT_MISMATCH",
                        f"provider requirement {capability!r} {field_name} must be {expected_requirement.get(field_name)!r}",
                        f"payload.provider_requirements.{capability}.{field_name}",
                    )
                )
    expected_required_requirements = set(STAGE_7_4_REQUIRED_SLOT_TYPES)
    actual_required_requirements = {
        str(capability)
        for capability, requirement in provider_requirements.items()
        if bool(_mapping(requirement).get("required"))
    }
    if actual_required_requirements != expected_required_requirements:
        findings.append(
            _v03_finding(
                "FAIL",
                "DR_CAP_PROVIDER_REQUIRED_SET_MISMATCH",
                f"required provider requirements must be {sorted(expected_required_requirements)!r}, got {sorted(actual_required_requirements)!r}",
                "payload.provider_requirements",
            )
        )

    if not any(item["status"] == "FAIL" for item in findings):
        findings.append(
            _v03_finding(
                "PASS",
                "DR_CAPABILITY_CHAIN_VALID",
                "required llm, memory, and lattice Slot -> Engine -> Provider/fallback chains resolved; optional capabilities remain non-required",
                "payload.runtime_requirements",
            )
        )
    return findings


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
