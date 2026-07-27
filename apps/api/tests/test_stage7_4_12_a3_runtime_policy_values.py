"""Narrow Stage 7.4.12 A3 runtime-policy value projection tests."""

from __future__ import annotations

from copy import deepcopy

from app.services.daily_companion_runtime import (
    _TRANSLATED_SOURCE_RULE_REFS,
    build_runtime_dialogue_projection,
)


SUPPORTED_POLICY_KEYS = (
    "memory_usage_policy",
    "relationship_policy",
    "self_disclosure_policy",
    "advice_policy",
)


def _behavior_policy() -> dict:
    modules: dict[str, dict] = {}
    for rule_ref in sorted(_TRANSLATED_SOURCE_RULE_REFS):
        policy_key, option_id = rule_ref.split(":", 1)
        module = modules.setdefault(
            policy_key,
            {
                "selected_options": [],
                "custom_text": "",
            },
        )
        module["selected_options"].append(option_id)
    modules["detail_behavior"] = {
        "selected_options": ["neutral"],
        "custom_text": "",
    }
    return {
        "schema_version": "0.1",
        "source_layer": "layer_8",
        "modules": modules,
    }


def test_runtime_policy_values_are_deep_copied_only_into_supported_policies():
    behavior_policy = _behavior_policy()
    baseline = build_runtime_dialogue_projection(behavior_policy, [])
    runtime_policy_values = {
        "memory_usage_policy": {
            "access_policy": {"require_confirmation": True},
        },
        "relationship_policy": {
            "relationship_mode": {"default": "companion"},
        },
        "self_disclosure_policy": {
            "self_awareness": {"real_human_boundary": True},
        },
        "advice_policy": {
            "capability_limits": ["no_professional_replacement"],
        },
        "language_policy": {"must_not_project": True},
        "unknown_policy": {"must_not_project": True},
    }
    original_values = deepcopy(runtime_policy_values)

    projection = build_runtime_dialogue_projection(
        behavior_policy,
        [],
        runtime_policy_values=runtime_policy_values,
    )

    assert baseline is not None
    assert projection is not None
    assert set(projection) == set(baseline)
    for policy_key in SUPPORTED_POLICY_KEYS:
        assert projection[policy_key]["derived_values"] == original_values[
            policy_key
        ]
        assert projection[policy_key]["instruction"] == baseline[policy_key][
            "instruction"
        ]
        assert projection[policy_key]["source_rule_refs"] == baseline[
            policy_key
        ]["source_rule_refs"]
    assert "derived_values" not in projection["language_policy"]
    assert "unknown_policy" not in projection

    runtime_policy_values["memory_usage_policy"]["access_policy"][
        "require_confirmation"
    ] = False
    assert projection["memory_usage_policy"]["derived_values"] == (
        original_values["memory_usage_policy"]
    )


def test_omitted_or_none_runtime_policy_values_preserve_the_legacy_projection():
    behavior_policy = _behavior_policy()

    omitted = build_runtime_dialogue_projection(behavior_policy, [])
    explicit_none = build_runtime_dialogue_projection(
        behavior_policy,
        [],
        runtime_policy_values=None,
    )
    unsupported_only = build_runtime_dialogue_projection(
        behavior_policy,
        [],
        runtime_policy_values={
            "language_policy": {"must_not_project": True},
            "unknown_policy": {"must_not_project": True},
        },
    )

    assert omitted == explicit_none == unsupported_only
    assert omitted is not None
    assert all(
        "derived_values" not in omitted[policy_key]
        for policy_key in SUPPORTED_POLICY_KEYS
    )
