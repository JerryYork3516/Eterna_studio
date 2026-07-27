"""Stage 7.4.12 A4 capability and compatibility-status governance.

This module is deliberately declarative.  It provides one stable vocabulary
for compile-time status projections and audit checks; it does not enable a
runtime capability, bind a Provider, or mutate caller-owned configuration.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, Mapping, Sequence


STAGE7_4_12_A4_CONTENT_REVISION = (
    "stage7_4_12_a4_compatibility_authority_status_governance_v1"
)

# Serialization and comparison order is part of the A4 contract.
CAPABILITY_STATUS_ORDER = (
    "active",
    "reserved",
    "placeholder",
    "runtime_disabled",
    "policy_only",
    "display_cache_only",
    "compatibility_fallback",
    "mock",
)
CAPABILITY_STATUS_VALUES = frozenset(CAPABILITY_STATUS_ORDER)

STAGE7_4_12_REQUIRED_CAPABILITIES = ("llm", "memory", "lattice")
STAGE7_4_12_NON_REQUIRED_CAPABILITIES = (
    "ar",
    "tool",
    "tts",
    "voice",
    "screen",
    "speech",
    "avatar",
    "abstract_bust",
    "llm_provider",
    "memory_provider",
)


def _ordered_states(*states: str) -> tuple[str, ...]:
    """Return unique states in the frozen A4 order."""

    unknown = set(states) - CAPABILITY_STATUS_VALUES
    if unknown:
        raise ValueError(f"unknown A4 status states: {sorted(unknown)!r}")
    requested = set(states)
    return tuple(state for state in CAPABILITY_STATUS_ORDER if state in requested)


def _classification(
    subject_id: str,
    capability_id: str,
    *,
    states: Sequence[str],
    required_capability: bool,
    runtime_enabled: bool,
    configuration_consumable: bool,
    source_paths: Sequence[str],
) -> Dict[str, Any]:
    return {
        "subject_id": subject_id,
        "capability_id": capability_id,
        "states": _ordered_states(*states),
        "required_capability": required_capability,
        "runtime_enabled": runtime_enabled,
        "configuration_consumable": configuration_consumable,
        # Provider Profiles remain a Runtime-owned concern and are never
        # serialized into Studio capability-status declarations.
        "provider_profile_allowed": False,
        "source_paths": tuple(source_paths),
        "content_revision": STAGE7_4_12_A4_CONTENT_REVISION,
    }


# Capability status describes two planes explicitly:
# - configuration_consumable: Studio/Runtime/Aftelle may read the declaration;
# - runtime_enabled: the DR capability contract currently has a runtime route.
#
# An ``active`` configuration surface never implies a real Provider binding.
CAPABILITY_STATUS_CLASSIFICATIONS: Dict[str, Dict[str, Any]] = {
    "ar": _classification(
        "ar",
        "ar",
        states=("reserved", "runtime_disabled"),
        required_capability=False,
        runtime_enabled=False,
        configuration_consumable=False,
        source_paths=("payload.provider_requirements.ar",),
    ),
    "tool": _classification(
        "tool",
        "tool",
        states=("reserved", "runtime_disabled"),
        required_capability=False,
        runtime_enabled=False,
        configuration_consumable=False,
        source_paths=("payload.provider_requirements.tool",),
    ),
    "tts": _classification(
        "tts",
        "tts",
        states=("reserved", "placeholder", "runtime_disabled"),
        required_capability=False,
        runtime_enabled=False,
        configuration_consumable=True,
        source_paths=(
            "payload.provider_requirements.tts",
            "payload.voice_config.tts_profile",
        ),
    ),
    "voice_config": _classification(
        "voice_config",
        "voice",
        states=(
            "placeholder",
            "runtime_disabled",
            "compatibility_fallback",
            "mock",
        ),
        required_capability=False,
        runtime_enabled=False,
        configuration_consumable=True,
        source_paths=("payload.voice_config", "voice_config"),
    ),
    "screen": _classification(
        "screen",
        "screen",
        states=("reserved", "runtime_disabled", "policy_only", "mock"),
        required_capability=False,
        runtime_enabled=False,
        configuration_consumable=True,
        source_paths=(
            "payload.provider_requirements.screen",
            "payload.screen_capability_declaration",
        ),
    ),
    "speech": _classification(
        "speech",
        "speech",
        states=("reserved", "placeholder", "runtime_disabled"),
        required_capability=False,
        runtime_enabled=False,
        configuration_consumable=True,
        source_paths=(
            "payload.provider_requirements.speech",
            "payload.voice_config.speech_event_schema",
        ),
    ),
    "avatar_runtime": _classification(
        "avatar_runtime",
        "avatar",
        states=("reserved", "runtime_disabled"),
        required_capability=False,
        runtime_enabled=False,
        configuration_consumable=False,
        source_paths=("payload.provider_requirements.avatar",),
    ),
    "particle_visual_projection": _classification(
        "particle_visual_projection",
        "particle_visual_projection",
        states=("active", "policy_only"),
        required_capability=False,
        runtime_enabled=False,
        configuration_consumable=True,
        source_paths=(
            "payload.modules.particle_avatar",
            "visual_expression_mapping.particle_core_mapping",
        ),
    ),
    "abstract_bust": _classification(
        "abstract_bust",
        "abstract_bust",
        states=("reserved", "placeholder", "runtime_disabled"),
        required_capability=False,
        runtime_enabled=False,
        configuration_consumable=False,
        source_paths=("visual_expression_mapping.abstract_bust_mapping",),
    ),
    "llm": _classification(
        "llm",
        "llm",
        states=("active", "mock"),
        required_capability=True,
        runtime_enabled=True,
        configuration_consumable=True,
        source_paths=(
            "payload.runtime_requirements",
            "payload.provider_requirements.llm",
        ),
    ),
    "memory": _classification(
        "memory",
        "memory",
        states=("active", "mock"),
        required_capability=True,
        runtime_enabled=True,
        configuration_consumable=True,
        source_paths=(
            "payload.runtime_requirements",
            "payload.provider_requirements.memory",
        ),
    ),
    "llm_provider": _classification(
        "llm_provider",
        "llm_provider",
        states=("placeholder", "runtime_disabled", "mock"),
        required_capability=False,
        runtime_enabled=False,
        configuration_consumable=True,
        source_paths=("payload.modules.llm_provider_router",),
    ),
    "memory_provider": _classification(
        "memory_provider",
        "memory_provider",
        states=("policy_only", "compatibility_fallback", "mock"),
        required_capability=False,
        runtime_enabled=False,
        configuration_consumable=True,
        source_paths=("payload.modules.memory_provider_router",),
    ),
    "lattice": _classification(
        "lattice",
        "lattice",
        states=("active", "compatibility_fallback", "mock"),
        required_capability=True,
        runtime_enabled=True,
        configuration_consumable=True,
        source_paths=(
            "payload.lattice_config",
            "payload.provider_requirements.lattice",
            "payload.fallback_routes",
        ),
    ),
}


def _module_classification(
    module_id: str,
    *,
    states: Sequence[str],
    runtime_enabled: bool,
    configuration_consumable: bool,
    legacy_status_values: Sequence[str] = (),
    legacy_status_semantics: str = "",
) -> Dict[str, Any]:
    return {
        "module_id": module_id,
        "states": _ordered_states(*states),
        "runtime_enabled": runtime_enabled,
        "configuration_consumable": configuration_consumable,
        "provider_profile_allowed": False,
        "legacy_status_values": tuple(legacy_status_values),
        "legacy_status_semantics": legacy_status_semantics,
        "content_revision": STAGE7_4_12_A4_CONTENT_REVISION,
    }


# These module declarations must not be confused with their capability
# contracts.  In particular, the LLM and Memory router modules remain
# declarative even though the llm/memory capabilities are required.
MODULE_STATUS_CLASSIFICATIONS: Dict[str, Dict[str, Any]] = {
    "particle_avatar": _module_classification(
        "particle_avatar",
        states=("reserved", "runtime_disabled", "policy_only"),
        runtime_enabled=False,
        configuration_consumable=True,
    ),
    "llm_provider_router": _module_classification(
        "llm_provider_router",
        states=("reserved", "placeholder", "runtime_disabled", "mock"),
        runtime_enabled=False,
        configuration_consumable=True,
    ),
    "memory_provider_router": _module_classification(
        "memory_provider_router",
        states=("runtime_disabled", "policy_only", "mock"),
        runtime_enabled=False,
        configuration_consumable=True,
        legacy_status_values=("READY",),
        legacy_status_semantics=(
            "catalog_configuration_ready_only_not_runtime_enabled"
        ),
    ),
    "voice_tts_module_v1": _module_classification(
        "voice_tts_module_v1",
        states=("reserved", "placeholder", "runtime_disabled"),
        runtime_enabled=False,
        configuration_consumable=True,
    ),
    "avatar_runtime": _module_classification(
        "avatar_runtime",
        states=("reserved", "placeholder", "runtime_disabled"),
        runtime_enabled=False,
        configuration_consumable=False,
    ),
    "module_lattice_update": _module_classification(
        "module_lattice_update",
        states=("runtime_disabled", "mock"),
        runtime_enabled=False,
        configuration_consumable=True,
    ),
    "module_lattice_read": _module_classification(
        "module_lattice_read",
        states=("runtime_disabled", "mock"),
        runtime_enabled=False,
        configuration_consumable=True,
    ),
    "module_lattice_preview": _module_classification(
        "module_lattice_preview",
        states=("runtime_disabled", "mock"),
        runtime_enabled=False,
        configuration_consumable=True,
    ),
}


def _surface_classification(
    surface_id: str,
    *,
    states: Sequence[str],
    role: str,
    authoritative: bool,
    derived_from: str,
    may_override_authority: bool,
    forbidden_keys: Sequence[str] = (),
) -> Dict[str, Any]:
    return {
        "surface_id": surface_id,
        "states": _ordered_states(*states),
        "role": role,
        "authoritative": authoritative,
        "derived_from": derived_from,
        "may_override_authority": may_override_authority,
        "forbidden_keys": tuple(forbidden_keys),
        "content_revision": STAGE7_4_12_A4_CONTENT_REVISION,
    }


MODULE_SURFACE_CLASSIFICATIONS: Dict[str, Dict[str, Any]] = {
    "payload.modules": _surface_classification(
        "payload.modules",
        states=("active",),
        role="authoritative_module_source",
        authoritative=True,
        derived_from="current_normalized_module_collection",
        may_override_authority=True,
    ),
    "modules": _surface_classification(
        "modules",
        states=("compatibility_fallback",),
        role="v0_3_read_only_compatibility_projection",
        authoritative=False,
        derived_from="payload.modules",
        may_override_authority=False,
    ),
    "payload.graph_snapshot": _surface_classification(
        "payload.graph_snapshot",
        states=("display_cache_only",),
        role="lightweight_canvas_display_cache",
        authoritative=False,
        derived_from="current_normalized_graph",
        may_override_authority=False,
        forbidden_keys=("modules",),
    ),
    "payload.graph_snapshot.layer_outputs": _surface_classification(
        "payload.graph_snapshot.layer_outputs",
        states=("display_cache_only",),
        role="derived_layer_output_display_cache",
        authoritative=False,
        derived_from="payload.modules_and_current_top_level_projections",
        may_override_authority=False,
        forbidden_keys=("modules", "module_graph"),
    ),
    "legacy_blueprint": _surface_classification(
        "legacy_blueprint",
        states=("compatibility_fallback",),
        role="v0_3_legacy_compatibility_shell",
        authoritative=False,
        derived_from="current_payload_and_frozen_legacy_shape",
        may_override_authority=False,
        forbidden_keys=("modules",),
    ),
    "fields": _surface_classification(
        "fields",
        states=("active",),
        role="current_module_field_source",
        authoritative=True,
        derived_from="current_canvas_module_fields",
        may_override_authority=True,
    ),
    "legacy_fields": _surface_classification(
        "legacy_fields",
        states=("compatibility_fallback",),
        role="legacy_field_compatibility_mirror",
        authoritative=False,
        derived_from="fields",
        may_override_authority=False,
    ),
    "legacy_data_fields": _surface_classification(
        "legacy_data_fields",
        states=("compatibility_fallback",),
        role="legacy_data_field_compatibility_mirror",
        authoritative=False,
        derived_from="fields",
        may_override_authority=False,
    ),
}


def _mutable_classification(value: Mapping[str, Any]) -> Dict[str, Any]:
    item = deepcopy(dict(value))
    for key in (
        "states",
        "source_paths",
        "forbidden_keys",
        "legacy_status_values",
    ):
        if isinstance(item.get(key), tuple):
            item[key] = list(item[key])
    return item


def capability_status_classification(subject_id: str) -> Dict[str, Any]:
    """Return a detached classification for one capability-facing subject."""

    return _mutable_classification(CAPABILITY_STATUS_CLASSIFICATIONS[subject_id])


def module_status_classification(module_id: str) -> Dict[str, Any]:
    """Return a detached classification for one declarative module."""

    return _mutable_classification(MODULE_STATUS_CLASSIFICATIONS[module_id])


def module_surface_classification(surface_id: str) -> Dict[str, Any]:
    """Return a detached classification for one authority/compatibility surface."""

    return _mutable_classification(MODULE_SURFACE_CLASSIFICATIONS[surface_id])


def build_voice_config_status() -> Dict[str, Any]:
    """Build the frozen mock/placeholder/compatibility/disabled Voice status."""

    return capability_status_classification("voice_config")


def build_lattice_config_status() -> Dict[str, Any]:
    """Build the active-config plus mock-fallback Lattice status."""

    return capability_status_classification("lattice")


def derive_voice_config_status(config: Any) -> Dict[str, Any]:
    """Attach a derived status without mutating the caller-owned Voice config."""

    result = deepcopy(dict(config)) if isinstance(config, Mapping) else {}
    result["status_classification"] = build_voice_config_status()
    return result


def derive_lattice_config_status(config: Any) -> Dict[str, Any]:
    """Attach a derived status without mutating the caller-owned Lattice config."""

    result = deepcopy(dict(config)) if isinstance(config, Mapping) else {}
    result["status_classification"] = build_lattice_config_status()
    return result


def build_capability_status_governance() -> Dict[str, Any]:
    """Return the complete detached A4 status registry in stable order."""

    return {
        "content_revision": STAGE7_4_12_A4_CONTENT_REVISION,
        "status_order": list(CAPABILITY_STATUS_ORDER),
        "required_capabilities": list(STAGE7_4_12_REQUIRED_CAPABILITIES),
        "non_required_capabilities": list(
            STAGE7_4_12_NON_REQUIRED_CAPABILITIES
        ),
        "capabilities": {
            subject_id: _mutable_classification(classification)
            for subject_id, classification in CAPABILITY_STATUS_CLASSIFICATIONS.items()
        },
        "modules": {
            module_id: _mutable_classification(classification)
            for module_id, classification in MODULE_STATUS_CLASSIFICATIONS.items()
        },
        "module_surfaces": {
            surface_id: _mutable_classification(classification)
            for surface_id, classification in MODULE_SURFACE_CLASSIFICATIONS.items()
        },
    }


def _classification_errors(
    section_name: str,
    classifications: Any,
    id_field: str,
) -> list[str]:
    errors: list[str] = []
    if not isinstance(classifications, Mapping):
        return [f"{section_name} must be an object"]
    order_index = {
        status: index for index, status in enumerate(CAPABILITY_STATUS_ORDER)
    }
    for classification_id, raw in classifications.items():
        path = f"{section_name}.{classification_id}"
        if not isinstance(raw, Mapping):
            errors.append(f"{path} must be an object")
            continue
        if raw.get(id_field) != classification_id:
            errors.append(f"{path}.{id_field} must equal {classification_id!r}")
        states = raw.get("states")
        if not isinstance(states, (list, tuple)) or not states:
            errors.append(f"{path}.states must be a non-empty list")
            continue
        normalized = [str(state) for state in states]
        unknown = set(normalized) - CAPABILITY_STATUS_VALUES
        if unknown:
            errors.append(f"{path}.states contains unknown values {sorted(unknown)!r}")
        if len(normalized) != len(set(normalized)):
            errors.append(f"{path}.states contains duplicates")
        known = [state for state in normalized if state in order_index]
        if known != sorted(known, key=order_index.__getitem__):
            errors.append(f"{path}.states does not follow the frozen status order")
        if raw.get("content_revision") != STAGE7_4_12_A4_CONTENT_REVISION:
            errors.append(f"{path}.content_revision is stale or missing")
    return errors


def capability_status_governance_errors(value: Any = None) -> list[str]:
    """Validate a generated or externally supplied A4 governance registry."""

    registry = (
        build_capability_status_governance()
        if value is None
        else value
    )
    if not isinstance(registry, Mapping):
        return ["capability status governance must be an object"]

    errors: list[str] = []
    if registry.get("content_revision") != STAGE7_4_12_A4_CONTENT_REVISION:
        errors.append("content_revision is stale or missing")
    if list(registry.get("status_order") or []) != list(CAPABILITY_STATUS_ORDER):
        errors.append("status_order must equal the frozen A4 status order")
    if list(registry.get("required_capabilities") or []) != list(
        STAGE7_4_12_REQUIRED_CAPABILITIES
    ):
        errors.append("required_capabilities must remain llm/memory/lattice")
    if list(registry.get("non_required_capabilities") or []) != list(
        STAGE7_4_12_NON_REQUIRED_CAPABILITIES
    ):
        errors.append("non_required_capabilities changed or reordered")

    capabilities = registry.get("capabilities")
    modules = registry.get("modules")
    surfaces = registry.get("module_surfaces")
    if isinstance(capabilities, Mapping) and list(capabilities) != list(
        CAPABILITY_STATUS_CLASSIFICATIONS
    ):
        errors.append("capability classifications changed or reordered")
    if isinstance(modules, Mapping) and list(modules) != list(
        MODULE_STATUS_CLASSIFICATIONS
    ):
        errors.append("module classifications changed or reordered")
    if isinstance(surfaces, Mapping) and list(surfaces) != list(
        MODULE_SURFACE_CLASSIFICATIONS
    ):
        errors.append("module surface classifications changed or reordered")
    errors.extend(
        _classification_errors(
            "capabilities", capabilities, "subject_id"
        )
    )
    errors.extend(
        _classification_errors("modules", modules, "module_id")
    )
    errors.extend(
        _classification_errors(
            "module_surfaces", surfaces, "surface_id"
        )
    )

    if isinstance(capabilities, Mapping):
        required = {
            str(raw.get("capability_id"))
            for raw in capabilities.values()
            if isinstance(raw, Mapping) and raw.get("required_capability") is True
        }
        if required != set(STAGE7_4_12_REQUIRED_CAPABILITIES):
            errors.append(
                "capability classifications must require exactly llm/memory/lattice"
            )
        prohibited_active = {
            str(raw.get("capability_id"))
            for raw in capabilities.values()
            if isinstance(raw, Mapping)
            and raw.get("capability_id")
            in STAGE7_4_12_NON_REQUIRED_CAPABILITIES
            and "active" in list(raw.get("states") or [])
        }
        if prohibited_active:
            errors.append(
                "reserved capabilities cannot be active: "
                + ", ".join(sorted(prohibited_active))
            )
        prohibited_required = {
            str(raw.get("capability_id"))
            for raw in capabilities.values()
            if isinstance(raw, Mapping)
            and raw.get("capability_id")
            in STAGE7_4_12_NON_REQUIRED_CAPABILITIES
            and raw.get("required_capability") is True
        }
        if prohibited_required:
            errors.append(
                "non-required capabilities cannot be required: "
                + ", ".join(sorted(prohibited_required))
            )
        for subject_id, raw in capabilities.items():
            if not isinstance(raw, Mapping):
                continue
            states = list(raw.get("states") or [])
            if "runtime_disabled" in states and raw.get("runtime_enabled") is not False:
                errors.append(
                    f"capabilities.{subject_id}.runtime_enabled must be false"
                )
            if raw.get("provider_profile_allowed") is not False:
                errors.append(
                    f"capabilities.{subject_id}.provider_profile_allowed must be false"
                )

        for capability_id in ("llm", "memory"):
            capability = capabilities.get(capability_id)
            if not isinstance(capability, Mapping):
                continue
            if list(capability.get("states") or []) != list(
                _ordered_states("active", "mock")
            ):
                errors.append(
                    f"{capability_id} capability states must remain active/mock"
                )
            if capability.get("required_capability") is not True:
                errors.append(
                    f"{capability_id} capability must remain required"
                )

        llm_provider = capabilities.get("llm_provider")
        if isinstance(llm_provider, Mapping):
            if list(llm_provider.get("states") or []) != list(
                _ordered_states("placeholder", "runtime_disabled", "mock")
            ):
                errors.append(
                    "llm_provider states must remain placeholder/disabled/mock"
                )
            if llm_provider.get("required_capability") is not False:
                errors.append("llm_provider must remain non-required")
        memory_provider = capabilities.get("memory_provider")
        if isinstance(memory_provider, Mapping):
            if list(memory_provider.get("states") or []) != list(
                _ordered_states(
                    "policy_only",
                    "compatibility_fallback",
                    "mock",
                )
            ):
                errors.append(
                    "memory_provider states must remain policy/compatibility/mock"
                )
            if memory_provider.get("required_capability") is not False:
                errors.append("memory_provider must remain non-required")

        particle_projection = capabilities.get("particle_visual_projection")
        if isinstance(particle_projection, Mapping):
            if particle_projection.get("capability_id") != (
                "particle_visual_projection"
            ):
                errors.append(
                    "particle_visual_projection cannot identify as avatar capability"
                )
            if particle_projection.get("required_capability") is not False:
                errors.append(
                    "particle_visual_projection must remain non-required"
                )
            if particle_projection.get("runtime_enabled") is not False:
                errors.append(
                    "particle_visual_projection must remain projection-only"
                )

        voice = capabilities.get("voice_config")
        if isinstance(voice, Mapping) and list(voice.get("states") or []) != list(
            _ordered_states(
                "placeholder",
                "runtime_disabled",
                "compatibility_fallback",
                "mock",
            )
        ):
            errors.append("voice_config states must remain mock/placeholder/compatibility/disabled")
        lattice = capabilities.get("lattice")
        if isinstance(lattice, Mapping):
            if list(lattice.get("states") or []) != list(
                _ordered_states("active", "compatibility_fallback", "mock")
            ):
                errors.append("lattice states must remain active with mock fallback")
            if lattice.get("required_capability") is not True:
                errors.append("lattice must remain a required capability")
            if lattice.get("configuration_consumable") is not True:
                errors.append("lattice configuration must remain consumable")

    if isinstance(modules, Mapping):
        for module_id, raw in modules.items():
            if not isinstance(raw, Mapping):
                continue
            states = list(raw.get("states") or [])
            if "runtime_disabled" in states and raw.get("runtime_enabled") is not False:
                errors.append(f"modules.{module_id}.runtime_enabled must be false")
            if raw.get("provider_profile_allowed") is not False:
                errors.append(
                    f"modules.{module_id}.provider_profile_allowed must be false"
                )
            legacy_status_values = list(
                raw.get("legacy_status_values") or []
            )
            if legacy_status_values and (
                raw.get("runtime_enabled") is not False
                or not str(raw.get("legacy_status_semantics") or "")
            ):
                errors.append(
                    f"modules.{module_id} legacy status must be explicitly "
                    "non-runtime and semantically described"
                )

    if isinstance(surfaces, Mapping):
        authoritative = [
            surface_id
            for surface_id, raw in surfaces.items()
            if isinstance(raw, Mapping)
            and raw.get("role") == "authoritative_module_source"
            and raw.get("authoritative") is True
        ]
        if authoritative != ["payload.modules"]:
            errors.append(
                "payload.modules must be the sole authoritative module surface"
            )
        for surface_id in ("modules", "payload.graph_snapshot", "legacy_blueprint"):
            raw = surfaces.get(surface_id)
            if isinstance(raw, Mapping) and raw.get("may_override_authority") is not False:
                errors.append(
                    f"module_surfaces.{surface_id} cannot override payload.modules"
                )
        for surface_id in ("payload.graph_snapshot", "legacy_blueprint"):
            raw = surfaces.get(surface_id)
            if isinstance(raw, Mapping) and "modules" not in list(
                raw.get("forbidden_keys") or []
            ):
                errors.append(
                    f"module_surfaces.{surface_id} must forbid a modules copy"
                )

    return errors


def validate_capability_status_governance(value: Any = None) -> bool:
    """Return True only when all A4 classification invariants hold."""

    return not capability_status_governance_errors(value)


__all__ = [
    "CAPABILITY_STATUS_CLASSIFICATIONS",
    "CAPABILITY_STATUS_ORDER",
    "CAPABILITY_STATUS_VALUES",
    "MODULE_STATUS_CLASSIFICATIONS",
    "MODULE_SURFACE_CLASSIFICATIONS",
    "STAGE7_4_12_A4_CONTENT_REVISION",
    "STAGE7_4_12_NON_REQUIRED_CAPABILITIES",
    "STAGE7_4_12_REQUIRED_CAPABILITIES",
    "build_capability_status_governance",
    "build_lattice_config_status",
    "build_voice_config_status",
    "capability_status_classification",
    "capability_status_governance_errors",
    "derive_lattice_config_status",
    "derive_voice_config_status",
    "module_status_classification",
    "module_surface_classification",
    "validate_capability_status_governance",
]
