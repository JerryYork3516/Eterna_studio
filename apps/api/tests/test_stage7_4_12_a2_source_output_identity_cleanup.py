"""Stage 7.4.12 A2 source, output, and identity cleanup contracts."""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

from app.models.v0_4 import STAGE7_4_12_A2_CONTENT_REVISION
from app.registry.module_catalog import (
    DETAIL_BEHAVIOR_MODULE_ID,
    EXPRESSION_STATE_NODE_IDS,
    EXPRESSION_STATE_VALUES,
    PARTICLE_AVATAR_MODULE_ID,
    PARTICLE_AVATAR_OUTPUT_KEY,
    SELF_AWARENESS_FACT_SOURCE_BINDINGS,
    get_module_catalog,
)
from app.services.dr_compiler import (
    compile_dr_result_v0_3,
    dialogue_runtime_profile_id,
)
from app.services.visual_expression_projection import (
    VISUAL_EXPRESSION_TRANSITION_DEFAULTS,
    particle_transition_rule_source_value,
)


LAYER8_OUTPUT_SPECS = {
    "language_habit": (
        "language_behavior",
        "language_behavior_config",
        "language_behavior_reference_output",
    ),
    "decision_pattern": (
        "decision_behavior",
        "decision_behavior_config",
        "decision_behavior_reference_output",
    ),
    "interaction_strategy": (
        "interaction_behavior",
        "interaction_behavior_config",
        "interaction_behavior_reference_output",
    ),
    "emotion_mapper": (
        "social_behavior",
        "social_behavior_config",
        "social_behavior_reference_output",
    ),
    "behavior_habit": (
        "task_behavior",
        "task_behavior_config",
        "task_behavior_reference_output",
    ),
}


def _modules() -> list[dict]:
    return [
        module.model_dump(mode="json")
        for module in get_module_catalog()
    ]


def _canvas(
    modules: list[dict], name: str = "stage_7_4_12_a2_contract"
) -> dict:
    return {
        "workflow": {
            "name": name,
            "nodes": [
                {"node_id": f"layer_{index}"}
                for index in range(1, 14)
            ],
        },
        "modules": modules,
    }


def _compile(
    modules: list[dict], name: str = "stage_7_4_12_a2_contract"
) -> dict:
    result = compile_dr_result_v0_3(_canvas(modules, name))
    assert result["valid"] is True, result["errors"]
    return result["compiled_dr"]


def _module(modules: list[dict], module_id: str) -> dict:
    return next(
        module
        for module in modules
        if module["module_id"] == module_id
    )


def _node(module: dict, node_id: str) -> dict:
    return next(
        node
        for node in module["module_graph"]["nodes"]
        if node["node_id"] == node_id
    )


def _set_field(module: dict, field_key: str, value: object) -> None:
    for node in module["module_graph"]["nodes"]:
        params = node.get("params")
        if not isinstance(params, dict):
            continue
        fields = params.get("fields")
        if not isinstance(fields, list):
            continue
        for field in fields:
            if not isinstance(field, dict):
                continue
            if (field.get("field_key") or field.get("field_id")) != field_key:
                continue
            if "field_value" in field:
                field["field_value"] = deepcopy(value)
            else:
                field["value"] = deepcopy(value)
            return
    raise AssertionError(f"field {field_key!r} was not found")


def _field_records(module: dict) -> dict[str, dict]:
    records: dict[str, dict] = {}
    for node in module["module_graph"]["nodes"]:
        params = node.get("params")
        fields = params.get("fields") if isinstance(params, dict) else None
        if not isinstance(fields, list):
            continue
        for field in fields:
            if not isinstance(field, dict):
                continue
            field_key = field.get("field_key") or field.get("field_id")
            if isinstance(field_key, str):
                records[field_key] = field
    return records


def _field_value(field: dict) -> object:
    return (
        field.get("field_value")
        if "field_value" in field
        else field.get("value")
    )


def _expected_behavior_output(module: dict) -> dict:
    selected_options: list[str] = []
    validation_rules: list[str] = []
    custom_texts: list[str] = []
    preset_id = ""
    source_nodes: list[str] = []
    for node in module["module_graph"]["nodes"]:
        if node["node_type"] not in {"module_output", "reference_output"}:
            source_nodes.append(node["node_id"])
        if node["node_type"] != "text_config":
            continue
        params = node.get("params", {})
        config = (
            params.get("checkbox_config")
            if "checkbox_config" in params
            else params.get("checklist_config")
        )
        if not isinstance(config, dict):
            continue
        if not preset_id and isinstance(config.get("preset_id"), str):
            preset_id = config["preset_id"]
        options = config.get("selected_options")
        if isinstance(options, list):
            selected_options.extend(
                item
                for item in options
                if isinstance(item, str) and item
            )
            if node["node_id"].endswith("_validation"):
                validation_rules.extend(
                    item
                    for item in options
                    if isinstance(item, str) and item
                )
        custom_text = config.get("custom_text")
        if isinstance(custom_text, str) and custom_text.strip():
            custom_texts.append(custom_text.strip())
    return {
        "preset_id": preset_id,
        "selected_options": list(dict.fromkeys(selected_options)),
        "custom_text": "\n\n".join(custom_texts),
        "validation_rules": list(dict.fromkeys(validation_rules)),
        "source_nodes": source_nodes,
    }


def _resident_profile_source_ids(value: object) -> set[str]:
    source_ids: set[str] = set()
    if isinstance(value, list):
        for item in value:
            source_ids.update(_resident_profile_source_ids(item))
    elif isinstance(value, dict):
        if (
            value.get("source_scope") == "resident_profile"
            and isinstance(value.get("source_id"), str)
        ):
            source_ids.add(value["source_id"])
        for item in value.values():
            source_ids.update(_resident_profile_source_ids(item))
    return source_ids


def test_empty_layer_design_states_are_explicit_localized_and_not_capabilities():
    dr = _compile(_modules())
    layers = {
        layer["layer_id"]: layer
        for layer in dr["payload"]["13_layers_snapshot"]
    }
    expected_states = {
        "layer_4": "policy_only",
        "layer_6": "reserved",
        "layer_13": "compatibility_only",
    }
    locale_root = Path(__file__).parents[2] / "web" / "locales"
    en = json.loads((locale_root / "en.json").read_text(encoding="utf-8"))
    zh = json.loads((locale_root / "zh.json").read_text(encoding="utf-8"))

    for layer_id, content_state in expected_states.items():
        layer = layers[layer_id]
        assert layer["content_state"] == content_state
        assert layer["empty_by_design"] is True
        assert layer["runtime_enabled"] is False
        assert layer["declares_capability"] is False
        assert (
            layer["content_revision"]
            == STAGE7_4_12_A2_CONTENT_REVISION
        )
        description_key = layer["status_description_key"]
        assert en[description_key].strip()
        assert zh[description_key].strip()
        assert en[f"ui.layer.contentState.{content_state}"].strip()
        assert zh[f"ui.layer.contentState.{content_state}"].strip()

    assert dr["dr_version"] == "0.3"
    assert dr["manifest"]["dr_schema_version"] == "0.3.0"
    assert dr["manifest"]["required_capabilities"] == [
        "llm",
        "memory",
        "lattice",
    ]


def test_five_layer8_outputs_derive_current_checkbox_values_and_share_one_mirror():
    modules = _modules()
    for index, module_id in enumerate(LAYER8_OUTPUT_SPECS, start=1):
        module = _module(modules, module_id)
        current_node = next(
            node
            for node in module["module_graph"]["nodes"]
            if node["node_type"] == "text_config"
            and not node["node_id"].endswith("_validation")
        )
        checkbox = current_node["params"]["checkbox_config"]
        checkbox["selected_options"] = [f"a2_current_{index}"]
        checkbox["custom_text"] = f"A2 current text {index}"
        output_key = LAYER8_OUTPUT_SPECS[module_id][1]
        module["outputs"][output_key] = {"selected_options": ["stale"]}
        for node in module["module_graph"]["nodes"]:
            if node["node_type"] in {"module_output", "reference_output"}:
                node["outputs"][output_key] = {
                    "selected_options": ["stale"]
                }
    before = deepcopy(modules)

    first = _compile(modules)
    second = _compile(modules)

    assert modules == before
    assert (
        first["payload"]["behavior_policy"]
        == second["payload"]["behavior_policy"]
    )
    for module_id, (
        policy_key,
        output_key,
        _reference_output_id,
    ) in LAYER8_OUTPUT_SPECS.items():
        source = _module(before, module_id)
        expected = _expected_behavior_output(source)
        compiled = _module(first["payload"]["modules"], module_id)
        module_output = compiled["outputs"][output_key]
        behavior_output = first["payload"]["behavior_policy"]["modules"][
            policy_key
        ]
        assert module_output == behavior_output
        for key, value in expected.items():
            assert module_output[key] == value
        assert module_output["selected_options"]
        assert "stale" not in module_output["selected_options"]

        output_nodes = [
            node
            for node in compiled["module_graph"]["nodes"]
            if node["node_type"] == "module_output"
        ]
        reference_nodes = [
            node
            for node in compiled["module_graph"]["nodes"]
            if node["node_type"] == "reference_output"
        ]
        assert len(output_nodes) == len(reference_nodes) == 1
        assert output_nodes[0]["outputs"][output_key] == module_output
        assert reference_nodes[0]["outputs"][output_key] == module_output
        node_ids = [
            node["node_id"]
            for node in compiled["module_graph"]["nodes"]
        ]
        edge_pairs = [
            (edge["source"], edge["target"])
            for edge in compiled["module_graph"]["edges"]
        ]
        assert len(node_ids) == len(set(node_ids))
        assert len(edge_pairs) == len(set(edge_pairs))


def test_old_layer8_graphs_gain_one_output_chain_and_migration_is_idempotent():
    modules = _modules()
    legacy_reference_ids: dict[str, str] = {}
    for module_id in LAYER8_OUTPUT_SPECS:
        module = _module(modules, module_id)
        graph = module["module_graph"]
        graph["nodes"] = [
            node
            for node in graph["nodes"]
            if node["node_type"] != "module_output"
        ]
        reference = next(
            node
            for node in graph["nodes"]
            if node["node_type"] == "reference_output"
        )
        old_id = reference["node_id"]
        legacy_id = f"layer_8::{module_id}_reference_output_saved"
        reference["node_id"] = legacy_id
        legacy_reference_ids[module_id] = legacy_id
        graph["edges"] = [
            edge
            for edge in graph["edges"]
            if old_id not in {edge["source"], edge["target"]}
            and not edge["target"].endswith("_output")
        ]

    first = _compile(modules)
    recompiled = _compile(deepcopy(first["payload"]["modules"]))

    for module_id, (
        _policy_key,
        output_key,
        _reference_output_id,
    ) in LAYER8_OUTPUT_SPECS.items():
        first_module = _module(first["payload"]["modules"], module_id)
        second_module = _module(
            recompiled["payload"]["modules"], module_id
        )
        for compiled in (first_module, second_module):
            output_nodes = [
                node
                for node in compiled["module_graph"]["nodes"]
                if node["node_type"] == "module_output"
            ]
            reference_nodes = [
                node
                for node in compiled["module_graph"]["nodes"]
                if node["node_type"] == "reference_output"
            ]
            assert len(output_nodes) == len(reference_nodes) == 1
            assert (
                reference_nodes[0]["node_id"]
                == legacy_reference_ids[module_id]
            )
            assert output_nodes[0]["outputs"][output_key]
            assert reference_nodes[0]["outputs"][output_key]
            edge_pairs = [
                (edge["source"], edge["target"])
                for edge in compiled["module_graph"]["edges"]
            ]
            assert (
                output_nodes[0]["node_id"],
                reference_nodes[0]["node_id"],
            ) in edge_pairs

        assert [
            (node["node_id"], node["node_type"])
            for node in first_module["module_graph"]["nodes"]
        ] == [
            (node["node_id"], node["node_type"])
            for node in second_module["module_graph"]["nodes"]
        ]


def test_twenty_nine_legacy_references_resolve_and_stable_explicit_pointers_are_preserved():
    modules = _modules()
    targets = [
        (
            module_id,
            f"layer_8::{module_id}_reference_output_1783861767696_2",
        )
        for module_id in LAYER8_OUTPUT_SPECS
    ]
    references = []
    for index in range(29):
        module_id, old_source_node_id = targets[index % len(targets)]
        references.append(
            {
                "reference_id": f"a2_required_{index + 1}",
                "source_scope": "module",
                "source_layer_id": "layer_8",
                "source_module_id": module_id,
                "source_node_id": old_source_node_id,
                "reference_type": "required",
                "required": True,
            }
        )
    consumer = _module(modules, "emotion_mapper")
    consumer["module_graph"]["nodes"].append(
        {
            "node_id": "a2_required_reference_consumer",
            "node_type": "reference_input",
            "layer_id": "layer_8",
            "module_id": "emotion_mapper",
            "params": {"references": references},
            "outputs": {},
            "metadata": {
                "compile_time_only": True,
                "runtime_enabled": False,
                "no_execution": True,
            },
            "i18n_keys": {},
        }
    )

    dr = _compile(modules)
    compiled_modules = dr["payload"]["modules"]
    compiled_consumer = _module(compiled_modules, "emotion_mapper")
    compiled_references = _node(
        compiled_consumer, "a2_required_reference_consumer"
    )["params"]["references"]

    assert len(compiled_references) == 29
    assert all(
        reference["reference_type"] == "required"
        and reference["required"] is True
        for reference in compiled_references
    )
    for reference in compiled_references:
        source_module = _module(
            compiled_modules, reference["source_module_id"]
        )
        source_node = _node(
            source_module, reference["source_node_id"]
        )
        output_key = LAYER8_OUTPUT_SPECS[
            reference["source_module_id"]
        ][1]
        assert source_node["node_type"] == "reference_output"
        assert source_node["outputs"][output_key]

    visual_style = _module(compiled_modules, "visual_style")
    visual_reference_input = next(
        node
        for node in visual_style["module_graph"]["nodes"]
        if node["node_type"] == "reference_input"
    )
    interaction_reference = next(
        reference
        for reference in visual_reference_input["params"]["references"]
        if reference["reference_id"]
        == "first_presence_interaction_strategy"
    )
    interaction_module = _module(
        compiled_modules, "interaction_strategy"
    )
    interaction_output = _node(
        interaction_module, interaction_reference["source_node_id"]
    )
    assert interaction_reference["source_node_id"] == "interaction_behavior_core_rules"
    assert interaction_output["node_type"] == "text_config"


def test_emotion_reaction_schema_migrates_to_the_real_wrapped_output():
    modules = _modules()
    expression = _module(modules, DETAIL_BEHAVIOR_MODULE_ID)
    expression["output_schema"] = [
        {"key": "expression_state", "type": "string"},
        {"key": "expression_intensity", "type": "number"},
    ]

    dr = _compile(modules)
    compiled = _module(
        dr["payload"]["modules"], DETAIL_BEHAVIOR_MODULE_ID
    )

    assert [
        field["key"] for field in compiled["output_schema"]
    ] == ["detail_behavior_config"]
    assert compiled["output_schema"][0]["type"] == "object"
    actual = compiled["outputs"]["detail_behavior_config"]
    assert set(actual) == {
        "expression_state",
        "expression_intensity",
    }
    output_node = _node(
        compiled, EXPRESSION_STATE_NODE_IDS["output"]
    )
    output_fields = output_node["params"]["output_schema"]["fields"]
    assert output_node["outputs"]["detail_behavior_config"] == actual
    assert output_fields["expression_state"]["enum"] == list(
        EXPRESSION_STATE_VALUES
    )
    assert output_fields["expression_state"]["default"] == "neutral"
    assert output_fields["expression_intensity"]["minimum"] == 0.0
    assert output_fields["expression_intensity"]["maximum"] == 1.0


def test_self_awareness_resolves_layer1_layer7_layer11_without_overwriting_compatibility_fields():
    modules = _modules()
    existence = _module(modules, "module_existence_mode")
    identity = _module(modules, "module_basic_identity")
    environment = _module(modules, "environment_setting")
    relationship = _module(modules, "user_relationship")
    self_awareness = _module(modules, "self_awareness")

    _set_field(existence, "digital_resident_type", "权威数字居民类型")
    _set_field(identity, "primary_language", ["权威中文"])
    _set_field(environment, "city_environment", "权威地域语境")
    _set_field(
        relationship,
        "default_relationship_position",
        "权威关系定位",
    )
    compatibility_values = {
        "identity_type": "旧身份兼容值",
        "resident_type": "旧居民兼容值",
        "primary_language": ["旧语言兼容值"],
        "regional_identity_type": "旧地域兼容值",
        "default_relationship_role": "旧关系兼容值",
    }
    for field_key, value in compatibility_values.items():
        _set_field(self_awareness, field_key, value)

    dr = _compile(modules)
    compiled = _module(dr["payload"]["modules"], "self_awareness")
    output = compiled["outputs"]["self_awareness_config"]

    for field_key, value in compatibility_values.items():
        assert output["fields"][field_key] == value
    assert output["resolved_facts"] == {
        "identity_type": "权威数字居民类型",
        "resident_type": "权威数字居民类型",
        "primary_language": ["权威中文"],
        "regional_identity_type": "权威地域语境",
        "default_relationship_role": "权威关系定位",
    }
    assert (
        output["fact_source_policy"][
            "compatibility_fields_may_override_current_facts"
        ]
        is False
    )
    assert output["fact_source_policy"]["bindings"] == (
        SELF_AWARENESS_FACT_SOURCE_BINDINGS
    )
    assert all(
        source["selected_source"] == "current_source_node"
        and source["used_compatibility_fallback"] is False
        for source in output["resolved_fact_sources"].values()
    )
    fields = _field_records(compiled)
    for field_key, binding in (
        SELF_AWARENESS_FACT_SOURCE_BINDINGS.items()
    ):
        assert fields[field_key]["value_role"] == "compatibility_fallback"
        assert fields[field_key]["source_binding"] == binding
        assert _field_value(fields[field_key]) == compatibility_values[
            field_key
        ]
    assert (
        compiled["config"]["source_output_identity_cleanup_revision"]
        == STAGE7_4_12_A2_CONTENT_REVISION
    )
    assert (
        compiled["module_graph"][
            "source_output_identity_cleanup_revision"
        ]
        == STAGE7_4_12_A2_CONTENT_REVISION
    )
    output_node = next(
        node
        for node in compiled["module_graph"]["nodes"]
        if node["node_type"] == "module_output"
    )
    assert output_node["outputs"]["self_awareness_config"] == output


def test_transition_priority_reads_layer10_before_defaults_and_keeps_visual_semantics():
    modules = _modules()
    particle = _module(modules, PARTICLE_AVATAR_MODULE_ID)
    transition_node = _node(
        particle, "particle_state_transition_rules"
    )
    expected = {
        "uses_accumulated_idle_time_as_progress": False,
        "minimum_hold_prevents_flicker": True,
        "transition_executor": "aftelle",
    }
    lower_priority = {
        "uses_accumulated_idle_time_as_progress": True,
        "minimum_hold_prevents_flicker": False,
        "transition_executor": "runtime_core",
    }
    particle["config"]["transition_rules"].update(lower_priority)
    particle["outputs"][PARTICLE_AVATAR_OUTPUT_KEY][
        "transition_rules"
    ].update(lower_priority)
    output_node = next(
        node
        for node in particle["module_graph"]["nodes"]
        if node["node_type"] == "module_output"
    )
    output_node["outputs"][PARTICLE_AVATAR_OUTPUT_KEY][
        "transition_rules"
    ].update(lower_priority)

    for field_key, value in expected.items():
        found, resolved, source = particle_transition_rule_source_value(
            particle, field_key
        )
        assert found is True
        assert resolved == value
        assert source == "current_node"

    baseline = _compile(_modules())["visual_expression_mapping"]
    mapping = _compile(modules)["visual_expression_mapping"]
    for field_key, value in expected.items():
        assert mapping["transition_policy"][field_key] == value
    assert mapping["particle_core_mapping"] == baseline[
        "particle_core_mapping"
    ]
    for field_key in (
        "transition_duration",
        "minimum_hold_duration",
        "transition_style",
        "repeat_same_state_restarts_transition",
        "continue_from_current_visual_value",
    ):
        assert mapping["transition_policy"][field_key] == baseline[
            "transition_policy"
        ][field_key]

    for field_key in expected:
        fallback_particle = _module(
            _modules(), PARTICLE_AVATAR_MODULE_ID
        )
        fallback_transition_node = _node(
            fallback_particle, "particle_state_transition_rules"
        )
        fallback_output_node = next(
            node
            for node in fallback_particle["module_graph"]["nodes"]
            if node["node_type"] == "module_output"
        )
        fallback_transition_node["params"].pop(field_key, None)
        found, value, source = particle_transition_rule_source_value(
            fallback_particle, field_key
        )
        assert found is True
        assert value == expected[field_key]
        assert source == "structured_config"

        fallback_particle["config"]["transition_rules"].pop(
            field_key, None
        )
        found, value, source = particle_transition_rule_source_value(
            fallback_particle, field_key
        )
        assert found is True
        assert value == expected[field_key]
        assert source == "module_output"

        fallback_particle["outputs"][PARTICLE_AVATAR_OUTPUT_KEY][
            "transition_rules"
        ].pop(field_key, None)
        found, value, source = particle_transition_rule_source_value(
            fallback_particle, field_key
        )
        assert found is True
        assert value == expected[field_key]
        assert source == "compatibility_mirror"

        fallback_output_node["outputs"][PARTICLE_AVATAR_OUTPUT_KEY][
            "transition_rules"
        ].pop(field_key, None)
        found, value, source = particle_transition_rule_source_value(
            fallback_particle, field_key
        )
        assert found is False
        assert value is None
        assert source == "protocol_default"
        assert VISUAL_EXPRESSION_TRANSITION_DEFAULTS[field_key] == (
            expected[field_key]
        )


def test_profile_id_is_layer1_derived_stable_nonconflicting_and_synchronized():
    def modules_for(resident_id: str) -> list[dict]:
        modules = _modules()
        _set_field(
            _module(modules, "module_basic_identity"),
            "resident_id",
            resident_id,
        )
        return modules

    alpha_modules = modules_for("resident-alpha")
    before = deepcopy(alpha_modules)
    alpha_first = _compile(alpha_modules, "ignored-workflow-name")
    alpha_second = _compile(
        modules_for("resident-alpha"), "other-workflow-name"
    )
    beta = _compile(
        modules_for("resident-beta"), "ignored-workflow-name"
    )
    alpha_id = dialogue_runtime_profile_id("resident-alpha")
    beta_id = dialogue_runtime_profile_id("resident-beta")

    assert alpha_modules == before
    assert alpha_id == dialogue_runtime_profile_id("resident-alpha")
    assert alpha_id != beta_id
    for dr, expected_id in (
        (alpha_first, alpha_id),
        (alpha_second, alpha_id),
        (beta, beta_id),
    ):
        profile = _module(
            dr["payload"]["modules"], "dialogue_runtime_profile"
        )
        profile_fields = _field_records(profile)
        assert _field_value(profile_fields["profile_id"]) == expected_id
        assert (
            profile["outputs"]["dialogue_runtime_profile_config"][
                "profile_id"
            ]
            == expected_id
        )
        profile_output = next(
            node
            for node in profile["module_graph"]["nodes"]
            if node["node_type"] == "module_output"
        )
        assert (
            profile_output["outputs"][
                "dialogue_runtime_profile_config"
            ]["profile_id"]
            == expected_id
        )
        assert _resident_profile_source_ids(profile) == {expected_id}
        assert _resident_profile_source_ids(
            dr["payload"]["runtime_dialogue_projection"]
        ) == {expected_id}
        assert _resident_profile_source_ids(dr["modules"]) == {
            expected_id
        }
        assert (
            profile["config"]["source_output_identity_cleanup_revision"]
            == STAGE7_4_12_A2_CONTENT_REVISION
        )
        assert (
            profile["module_graph"][
                "source_output_identity_cleanup_revision"
            ]
            == STAGE7_4_12_A2_CONTENT_REVISION
        )
        serialized = json.dumps(profile, ensure_ascii=False).lower()
        assert "resident_0001" not in serialized
        assert "linxuan" not in serialized
        assert dr["dr_version"] == "0.3"
        assert dr["manifest"]["dr_schema_version"] == "0.3.0"
        assert dr["manifest"]["required_capabilities"] == [
            "llm",
            "memory",
            "lattice",
        ]


def test_a2_i18n_and_active_profile_resource_have_no_stale_identity_key():
    repo_root = Path(__file__).parents[3]
    en = json.loads(
        (repo_root / "apps/web/locales/en.json").read_text(
            encoding="utf-8"
        )
    )
    zh = json.loads(
        (repo_root / "apps/web/locales/zh.json").read_text(
            encoding="utf-8"
        )
    )
    for field_suffix in (
        "identityType",
        "residentType",
        "primaryLanguage",
        "regionalIdentityType",
        "defaultRelationshipRole",
    ):
        key = (
            "layer12.engineeringSelfAwareness.field."
            f"{field_suffix}.source"
        )
        assert en[key].strip()
        assert zh[key].strip()
    neutral_profile_key = (
        "stage7_4_9.dialogueRuntime.value."
        "dialogue_profile_resident_v0_1"
    )
    assert en[neutral_profile_key].strip()
    assert zh[neutral_profile_key].strip()

    registry = repo_root / "apps/api/app/registry"
    assert (registry / "dialogue_runtime_profile.json").is_file()
    assert not (
        registry / "dialogue_runtime_profile_resident_0001.json"
    ).exists()
    active_source = (
        registry / "dialogue_runtime_profile.json"
    ).read_text(encoding="utf-8")
    assert "dialogue_profile_resident_0001_v0_1" not in active_source
