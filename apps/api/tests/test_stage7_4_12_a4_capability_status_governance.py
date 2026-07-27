"""Pure unit contracts for Stage 7.4.12 A4 status governance."""

from __future__ import annotations

from copy import deepcopy

from app.services.capability_status_governance import (
    CAPABILITY_STATUS_CLASSIFICATIONS,
    CAPABILITY_STATUS_ORDER,
    CAPABILITY_STATUS_VALUES,
    MODULE_STATUS_CLASSIFICATIONS,
    MODULE_SURFACE_CLASSIFICATIONS,
    STAGE7_4_12_A4_CONTENT_REVISION,
    STAGE7_4_12_NON_REQUIRED_CAPABILITIES,
    STAGE7_4_12_REQUIRED_CAPABILITIES,
    build_capability_status_governance,
    build_lattice_config_status,
    build_voice_config_status,
    capability_status_governance_errors,
    derive_lattice_config_status,
    derive_voice_config_status,
    validate_capability_status_governance,
)


def test_a4_status_vocabulary_revision_and_registry_order_are_frozen():
    assert STAGE7_4_12_A4_CONTENT_REVISION == (
        "stage7_4_12_a4_compatibility_authority_status_governance_v1"
    )
    assert CAPABILITY_STATUS_ORDER == (
        "active",
        "reserved",
        "placeholder",
        "runtime_disabled",
        "policy_only",
        "display_cache_only",
        "compatibility_fallback",
        "mock",
    )
    assert CAPABILITY_STATUS_VALUES == frozenset(CAPABILITY_STATUS_ORDER)

    registry = build_capability_status_governance()

    assert registry["status_order"] == list(CAPABILITY_STATUS_ORDER)
    assert list(registry["capabilities"]) == list(
        CAPABILITY_STATUS_CLASSIFICATIONS
    )
    assert list(registry["modules"]) == list(MODULE_STATUS_CLASSIFICATIONS)
    assert list(registry["module_surfaces"]) == list(
        MODULE_SURFACE_CLASSIFICATIONS
    )
    assert capability_status_governance_errors(registry) == []
    assert validate_capability_status_governance(registry) is True


def test_required_contract_belongs_to_llm_memory_and_lattice_not_providers():
    registry = build_capability_status_governance()
    capabilities = registry["capabilities"]
    required_subjects = [
        subject_id
        for subject_id, classification in capabilities.items()
        if classification["required_capability"] is True
    ]
    required_capability_ids = [
        classification["capability_id"]
        for classification in capabilities.values()
        if classification["required_capability"] is True
    ]

    assert STAGE7_4_12_REQUIRED_CAPABILITIES == (
        "llm",
        "memory",
        "lattice",
    )
    assert required_subjects == ["llm", "memory", "lattice"]
    assert required_capability_ids == ["llm", "memory", "lattice"]
    assert capabilities["llm"]["states"] == ["active", "mock"]
    assert capabilities["memory"]["states"] == ["active", "mock"]
    assert capabilities["lattice"]["states"] == [
        "active",
        "compatibility_fallback",
        "mock",
    ]

    assert capabilities["llm_provider"]["states"] == [
        "placeholder",
        "runtime_disabled",
        "mock",
    ]
    assert capabilities["llm_provider"]["required_capability"] is False
    assert capabilities["llm_provider"]["runtime_enabled"] is False
    assert capabilities["llm_provider"]["source_paths"] == [
        "payload.modules.llm_provider_router"
    ]
    assert capabilities["memory_provider"]["states"] == [
        "policy_only",
        "compatibility_fallback",
        "mock",
    ]
    assert capabilities["memory_provider"]["required_capability"] is False
    assert capabilities["memory_provider"]["runtime_enabled"] is False
    assert capabilities["memory_provider"]["source_paths"] == [
        "payload.modules.memory_provider_router"
    ]


def test_reserved_and_provider_subjects_are_never_active_or_required():
    capabilities = build_capability_status_governance()["capabilities"]
    prohibited_subjects = (
        "ar",
        "tool",
        "tts",
        "voice_config",
        "screen",
        "speech",
        "avatar_runtime",
        "abstract_bust",
        "llm_provider",
        "memory_provider",
    )

    assert STAGE7_4_12_NON_REQUIRED_CAPABILITIES == (
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
    for subject_id in prohibited_subjects:
        classification = capabilities[subject_id]
        assert classification["required_capability"] is False
        assert "active" not in classification["states"]
        assert classification["provider_profile_allowed"] is False


def test_particle_visual_projection_is_not_an_avatar_capability():
    classification = build_capability_status_governance()["capabilities"][
        "particle_visual_projection"
    ]

    assert classification["capability_id"] == "particle_visual_projection"
    assert classification["states"] == ["active", "policy_only"]
    assert classification["required_capability"] is False
    assert classification["runtime_enabled"] is False
    assert classification["configuration_consumable"] is True
    assert classification["provider_profile_allowed"] is False


def test_module_classifications_keep_provider_modules_declarative():
    modules = build_capability_status_governance()["modules"]

    assert modules["llm_provider_router"]["states"] == [
        "reserved",
        "placeholder",
        "runtime_disabled",
        "mock",
    ]
    assert modules["memory_provider_router"]["states"] == [
        "runtime_disabled",
        "policy_only",
        "mock",
    ]
    assert modules["memory_provider_router"]["legacy_status_values"] == [
        "READY"
    ]
    assert modules["memory_provider_router"][
        "legacy_status_semantics"
    ] == "catalog_configuration_ready_only_not_runtime_enabled"
    assert modules["particle_avatar"]["states"] == [
        "reserved",
        "runtime_disabled",
        "policy_only",
    ]
    for module in modules.values():
        assert module["runtime_enabled"] is False
        assert module["provider_profile_allowed"] is False
        assert "active" not in module["states"]


def test_voice_status_is_derived_without_mutating_existing_config():
    existing = {
        "schema_version": "0.3.0",
        "tts_profile": {"provider": "mock", "voice_id": "mock_voice"},
    }
    before = deepcopy(existing)

    status = build_voice_config_status()
    derived = derive_voice_config_status(existing)

    assert status["states"] == [
        "placeholder",
        "runtime_disabled",
        "compatibility_fallback",
        "mock",
    ]
    assert status["required_capability"] is False
    assert status["runtime_enabled"] is False
    assert existing == before
    assert derived["tts_profile"] == existing["tts_profile"]
    assert derived["tts_profile"] is not existing["tts_profile"]
    assert derived["status_classification"] == status

    derived["status_classification"]["states"].append("tampered")
    assert "tampered" not in build_voice_config_status()["states"]


def test_lattice_status_keeps_consumable_config_and_mock_fallback_separate():
    existing = {
        "schema_version": "0.3.0",
        "resident_id": "resident",
        "color_palette": ["#7aa2f7"],
    }
    before = deepcopy(existing)

    status = build_lattice_config_status()
    derived = derive_lattice_config_status(existing)

    assert status["states"] == [
        "active",
        "compatibility_fallback",
        "mock",
    ]
    assert status["required_capability"] is True
    assert status["runtime_enabled"] is True
    assert status["configuration_consumable"] is True
    assert existing == before
    assert derived["color_palette"] == ["#7aa2f7"]
    assert derived["status_classification"] == status


def test_module_surface_registry_has_one_module_authority_and_safe_mirrors():
    surfaces = build_capability_status_governance()["module_surfaces"]
    module_authorities = [
        surface_id
        for surface_id, classification in surfaces.items()
        if classification["role"] == "authoritative_module_source"
        and classification["authoritative"] is True
    ]

    assert module_authorities == ["payload.modules"]
    assert surfaces["modules"]["derived_from"] == "payload.modules"
    assert surfaces["modules"]["may_override_authority"] is False
    assert surfaces["payload.graph_snapshot"]["states"] == [
        "display_cache_only"
    ]
    assert "modules" in surfaces["payload.graph_snapshot"]["forbidden_keys"]
    layer_outputs = surfaces["payload.graph_snapshot.layer_outputs"]
    assert layer_outputs["states"] == ["display_cache_only"]
    assert layer_outputs["authoritative"] is False
    assert layer_outputs["may_override_authority"] is False
    assert layer_outputs["forbidden_keys"] == [
        "modules",
        "module_graph",
    ]
    assert surfaces["legacy_blueprint"]["states"] == [
        "compatibility_fallback"
    ]
    assert "modules" in surfaces["legacy_blueprint"]["forbidden_keys"]
    assert surfaces["fields"]["authoritative"] is True
    for mirror in ("legacy_fields", "legacy_data_fields"):
        assert surfaces[mirror]["derived_from"] == "fields"
        assert surfaces[mirror]["may_override_authority"] is False


def test_registry_validation_rejects_provider_and_surface_semantic_drift():
    registry = build_capability_status_governance()

    provider_drift = deepcopy(registry)
    provider_drift["capabilities"]["llm_provider"]["states"] = [
        "active",
        "placeholder",
        "runtime_disabled",
        "mock",
    ]
    provider_drift["capabilities"]["llm_provider"][
        "required_capability"
    ] = True
    provider_errors = capability_status_governance_errors(provider_drift)
    assert any("llm_provider" in error for error in provider_errors)
    assert any("exactly llm/memory/lattice" in error for error in provider_errors)

    particle_drift = deepcopy(registry)
    particle_drift["capabilities"]["particle_visual_projection"][
        "capability_id"
    ] = "avatar"
    assert any(
        "cannot identify as avatar capability" in error
        for error in capability_status_governance_errors(particle_drift)
    )

    surface_drift = deepcopy(registry)
    surface_drift["module_surfaces"]["legacy_blueprint"][
        "may_override_authority"
    ] = True
    surface_drift["module_surfaces"]["legacy_blueprint"][
        "forbidden_keys"
    ] = []
    surface_errors = capability_status_governance_errors(surface_drift)
    assert any("legacy_blueprint cannot override" in error for error in surface_errors)
    assert any("must forbid a modules copy" in error for error in surface_errors)


def test_registry_validation_rejects_status_and_registry_order_drift():
    registry = build_capability_status_governance()

    status_drift = deepcopy(registry)
    status_drift["capabilities"]["voice_config"]["states"] = [
        "mock",
        "placeholder",
        "runtime_disabled",
        "compatibility_fallback",
    ]
    status_errors = capability_status_governance_errors(status_drift)
    assert any("frozen status order" in error for error in status_errors)

    registry_order_drift = deepcopy(registry)
    registry_order_drift["capabilities"] = dict(
        reversed(list(registry_order_drift["capabilities"].items()))
    )
    order_errors = capability_status_governance_errors(registry_order_drift)
    assert "capability classifications changed or reordered" in order_errors
