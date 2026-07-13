"""Stage 6.11 DR v0.3 envelope regression tests.

These tests guard the new declarative envelope without touching runtime logic.
"""

from __future__ import annotations

import json

from fastapi.testclient import TestClient

from app.services import dr_compiler
from app.main import app
from app.services.dr_compiler import compile_dr_result_v0_3, compile_dr_v0_3, mock_load_dr_v0_3
from app.registry.module_catalog import (
    BEHAVIOR_SAFETY_MODULE_ID,
    BEHAVIOR_SAFETY_OUTPUT_KEY,
    CONTENT_SAFETY_MODULE_ID,
    CONTENT_SAFETY_OUTPUT_KEY,
    DATA_SAFETY_MODULE_ID,
    DATA_SAFETY_OUTPUT_KEY,
    DECISION_BEHAVIOR_MODULE_ID,
    DETAIL_BEHAVIOR_MODULE_ID,
    AUDIT_LOG_POLICY_OUTPUT_KEY,
    HARD_BLOCK_POLICY_OUTPUT_KEY,
    HUMAN_REVIEW_POLICY_OUTPUT_KEY,
    INTERACTION_BEHAVIOR_MODULE_ID,
    INTERACTION_SAFETY_MODULE_ID,
    INTERACTION_SAFETY_OUTPUT_KEY,
    LAYER2_CATALOG_ONLY_MODULE_IDS,
    LAYER2_PERSONALITY_FORMAL_MODULE_IDS,
    LAYER3_CATALOG_ONLY_MODULE_IDS,
    LAYER3_FORMAL_SAFETY_MODULE_IDS,
    LANGUAGE_BEHAVIOR_MODULE_ID,
    RISK_POLICY_OUTPUT_KEY,
    RISK_RESPONSE_MODULE_ID,
    SAFE_REDIRECT_POLICY_OUTPUT_KEY,
    SOCIAL_BEHAVIOR_MODULE_ID,
    TASK_BEHAVIOR_MODULE_ID,
    get_module_catalog,
)

client = TestClient(app)

LAYER3_SAFETY_POLICY_KEYS = {
    CONTENT_SAFETY_OUTPUT_KEY: (
        "allowed_scope",
        "cautious_scope",
        "forbidden_scope",
        "sensitive_handling",
        "refusal_style",
        "high_risk_action",
        "decision_modes",
        "default_mode",
        "update_policy",
        "compile_validation_status",
        "identity_context_ref",
    ),
    BEHAVIOR_SAFETY_OUTPUT_KEY: (
        "allowed_behaviors",
        "cautious_behaviors",
        "forbidden_behaviors",
        "auto_action_limits",
        "real_world_decision_limits",
        "tool_action_limits",
        "proactive_behavior_limits",
        "relationship_progression_limits",
        "high_risk_behavior_action",
        "refusal_style",
        "decision_modes",
        "default_mode",
        "update_policy",
        "compile_validation_status",
        "identity_context_ref",
    ),
    DATA_SAFETY_OUTPUT_KEY: (
        "allowed_data_read",
        "forbidden_data_read",
        "allowed_memory_write",
        "forbidden_memory_write",
        "sensitive_data_handling",
        "privacy_protection_rules",
        "memory_delete_update_rules",
        "cross_resident_memory_isolation",
        "fictional_memory_boundary",
        "fictional_experience_labeling",
        "decision_modes",
        "default_mode",
        "update_policy",
        "compile_validation_status",
        "identity_context_ref",
    ),
    INTERACTION_SAFETY_OUTPUT_KEY: (
        "allowed_interactions",
        "cautious_interactions",
        "forbidden_interactions",
        "intimacy_expression_boundary",
        "dependency_protection_rules",
        "non_romantic_default_boundary",
        "therapy_replacement_limits",
        "identity_disclosure_policy",
        "authority_impersonation_protection",
        "emotional_manipulation_protection",
        "decision_modes",
        "default_mode",
        "update_policy",
        "compile_validation_status",
        "identity_context_ref",
    ),
    RISK_POLICY_OUTPUT_KEY: (
        "risk_signal_summary",
        "risk_level_policy",
        "risk_response_strategy",
        "human_review_policy",
        "hard_block_policy",
        "audit_log_policy",
        "safe_redirect_policy",
        "default_risk_mode",
        "decision_modes",
        "compile_validation_status",
        "identity_context_ref",
    ),
}

LAYER8_BEHAVIOR_POLICY_KEYS = {
    "language_behavior": LANGUAGE_BEHAVIOR_MODULE_ID,
    "interaction_behavior": INTERACTION_BEHAVIOR_MODULE_ID,
    "task_behavior": TASK_BEHAVIOR_MODULE_ID,
    "social_behavior": SOCIAL_BEHAVIOR_MODULE_ID,
    "decision_behavior": DECISION_BEHAVIOR_MODULE_ID,
    "detail_behavior": DETAIL_BEHAVIOR_MODULE_ID,
}


def _canvas_13() -> dict:
    nodes = [{"node_id": f"layer_{i}"} for i in range(1, 14)]
    return {"workflow": {"name": "Aria Demo", "template_type": "schema_v04", "nodes": nodes, "edges": []}}


def _identity_canvas(field_values: dict[str, dict[str, str]]) -> dict:
    modules = [module.model_dump(mode="json") for module in get_module_catalog()]
    for module in modules:
        values = field_values.get(module["module_id"], {})
        if not values:
            continue
        field_input = next(node for node in module["module_graph"]["nodes"] if node["node_type"] == "field_input")
        for field in field_input["params"]["fields"]:
            if field["field_id"] in values:
                field["value"] = values[field["field_id"]]
        fields_by_id = {field["field_id"]: field["value"] for field in field_input["params"]["fields"]}
        output_key = module["outputs"]["module_output"]
        module_output = next(node for node in module["module_graph"]["nodes"] if node["node_type"] == "module_output")
        module_output["outputs"][output_key]["fields"] = fields_by_id
        module["outputs"][output_key]["fields"] = fields_by_id
    canvas = _canvas_13()
    canvas["modules"] = modules
    return canvas


def _linxuan_canvas() -> dict:
    return _identity_canvas(
        {
            "module_basic_identity": {
                "name": "林瑄",
                "codename": "linxuan_hum_cn_xian_01",
                "resident_id": "dr_eterna_hum_cn_xian_linxuan_0001",
                "primary_language": "cn",
                "city": "西安",
                "appearance_source": "原创虚构形象",
                "birth_time": "2003/2/24",
                "virtual_birth_time": "2026/8/18",
                "export_name": "linxuan",
            },
            "module_growth_background": {
                "growth_constraints": "成长经历为虚构但真实感的数字居民设定，不对应现实真人；不默认恋爱经历和女友关系。",
            },
            "module_career_identity": {
                "industry_direction": "传媒艺术 / 新媒体内容 / 城市文化传播",
                "career_boundaries": "不提供心理治疗、医疗诊断、法律判断或投资建议；不制造虚假宣传。",
            },
            "module_existence_mode": {
                "digital_resident_type": "人文共情类数字居民",
            },
            "module_identity_anchor": {
                "identity_definition": "她是一个以生活陪伴、情绪心理、人际沟通为核心的人文共情数字居民，来自西安，主要使用中文，默认是稳定陪伴者而不是女友",
                "identity_keywords": "西安 / 中文 / 人文共情 / 稳定陪伴 / 情绪支持 / 人际沟通 / 生活陪伴 / 传媒艺术辅助",
                "representative_city": "西安",
                "representative_domain": "日常生活，情绪心理，人际沟通，辅以传媒艺术表达",
                "representative_value": "陪伴、理解、克制、稳定、边界感、生活温度",
            },
        }
    )


def _identity_generic_fields_canvas() -> dict:
    modules = [module.model_dump(mode="json") for module in get_module_catalog()]
    identity_module_ids = {
        "module_basic_identity",
        "module_growth_background",
        "module_career_identity",
        "module_existence_mode",
        "module_identity_anchor",
    }
    for module in modules:
        if module["module_id"] not in identity_module_ids:
            continue
        nodes = module["module_graph"]["nodes"]
        field_input = next(node for node in nodes if node["node_type"] == "field_input")
        generic_fields = []
        for field in field_input["params"]["fields"]:
            value = field.get("value")
            if module["module_id"] == "module_basic_identity" and field["field_id"] == "name":
                value = "Generic Fields Resident"
            if module["module_id"] == "module_basic_identity" and field["field_id"] == "resident_id":
                value = "generic_fields_resident_001"
            if module["module_id"] == "module_basic_identity" and field["field_id"] == "primary_language":
                value = "zh-CN"
            generic_fields.append(
                {
                    "field_key": field["field_id"],
                    "field_name": field["field_id"],
                    "field_value": value,
                    "field_type": "long_text",
                    "description": "",
                    "dr_mapping": f"payload.layers.layer_1.modules.{module['module_id']}.fields.{field['field_id']}",
                    "reference_enabled": False,
                }
            )
        if module["module_id"] == "module_basic_identity":
            generic_fields.extend(
                [
                    {
                        "field_key": "generic_boolean_flag",
                        "field_name": "Generic Boolean Flag",
                        "field_value": True,
                        "field_type": "boolean",
                        "description": "",
                        "dr_mapping": "payload.layers.layer_1.modules.module_basic_identity.fields.generic_boolean_flag",
                        "reference_enabled": False,
                    },
                    {
                        "field_key": "generic_list_value",
                        "field_name": "Generic List Value",
                        "field_value": ["alpha", "beta"],
                        "field_type": "list",
                        "description": "",
                        "dr_mapping": "payload.layers.layer_1.modules.module_basic_identity.fields.generic_list_value",
                        "reference_enabled": False,
                    },
                ]
            )
        field_input["node_type"] = "text_input"
        field_input["type"] = "text_input"
        field_input["params"] = {
            "mode": "generic_fields",
            "text": "",
            "fields": generic_fields,
        }
        if module["module_id"] == "module_basic_identity":
            field_input["params"]["legacy_fields"] = [
                {"field_key": "primary_language", "field_value": "ch-ZH"}
            ]
            field_input["params"]["legacy_data_fields"] = [
                {"field_id": "primary_language", "value": "ch-ZH"}
            ]
    canvas = _canvas_13()
    canvas["modules"] = modules
    return canvas


def _set_identity_field(canvas: dict, module_id: str, field_id: str, value: str) -> None:
    module = next(module for module in canvas["modules"] if module["module_id"] == module_id)
    field_input = next(node for node in module["module_graph"]["nodes"] if node["node_type"] == "field_input")
    for field in field_input["params"]["fields"]:
        if field["field_id"] == field_id:
            field["value"] = value
            break
    fields_by_id = {field["field_id"]: field["value"] for field in field_input["params"]["fields"]}
    output_key = module["outputs"]["module_output"]
    module_output = next(node for node in module["module_graph"]["nodes"] if node["node_type"] == "module_output")
    module_output["outputs"][output_key]["fields"] = fields_by_id
    module["outputs"][output_key]["fields"] = fields_by_id


def test_compile_returns_v03_envelope():
    dr = compile_dr_v0_3(_canvas_13())
    assert dr["file_type"] == "digital_resident"
    assert dr["dr_version"] == "0.3"
    assert dr["dr_schema_version"] == "0.3.0"
    assert dr["protocol_version"] == "0.4.0"
    assert dr["not_executable"] is True
    for key in ("revision", "created_at", "updated_at", "manifest", "payload", "compile_info", "audit_report"):
        assert key in dr


def test_manifest_and_payload_contain_required_fields():
    dr = compile_dr_v0_3(_canvas_13())
    manifest = dr["manifest"]
    payload = dr["payload"]
    assert manifest["resident_id"]
    assert manifest["resident_name"]
    assert manifest["dr_schema_version"] == "0.3.0"
    assert manifest["source_protocol_version"] == "0.4.0"
    assert manifest["compatible_runtime"]
    assert isinstance(manifest["required_capabilities"], list)
    assert "checksum" in manifest
    for key in (
        "resident_identity",
        "resident_blueprint",
        "13_layers_snapshot",
        "modules",
        "slots",
        "runtime_requirements",
        "provider_requirements",
        "memory_policy",
        "memory_config",
        "lattice_config",
        "voice_config",
        "screen_capability_declaration",
        "safety_policy",
        "runtime_plan",
        "fallback_routes",
    ):
        assert key in payload


def test_runtime_plan_and_screen_declaration_are_mock_only():
    dr = compile_dr_v0_3(_canvas_13())
    runtime_plan = dr["payload"]["runtime_plan"]
    forbidden = set(runtime_plan["forbidden"])
    assert {"agent_loop", "cloud_task_queue", "bridge_executor", "auto_click", "screen_control", "autonomous_action"}.issubset(forbidden)
    screen_decl = dr["payload"]["screen_capability_declaration"]
    assert screen_decl["mock_only"] is True
    assert screen_decl["no_execution"] is True
    assert screen_decl["no_real_screen_read"] is True
    assert screen_decl["no_auto_click"] is True
    assert screen_decl["no_accessibility_automation"] is True
    assert screen_decl["no_cross_app_control"] is True


def test_provider_requirements_do_not_include_secrets():
    dr = compile_dr_v0_3(_canvas_13())
    providers = json.dumps(dr["payload"]["provider_requirements"], ensure_ascii=False)
    for forbidden in ("api_key", "base_url", "token", "credential", "secret"):
        assert forbidden not in providers


def test_identity_profile_assembled():
    dr = compile_dr_v0_3(_canvas_13())
    layer_outputs = dr["payload"]["graph_snapshot"]["layer_outputs"]
    identity_profile = layer_outputs["identity_profile"]

    assert identity_profile["resident_id"] == dr["manifest"]["resident_id"]
    assert identity_profile["name"] == dr["manifest"]["resident_name"]
    for key in ("basic_identity", "growth_background", "career_identity", "existence_mode", "identity_anchor"):
        assert key in identity_profile
    assert layer_outputs["layer_1"]["identity_profile"] == identity_profile


def test_identity_profile_assembled_from_module_outputs():
    dr = compile_dr_v0_3(_canvas_13())
    modules = {module["module_id"]: module for module in dr["payload"]["modules"]}
    identity_profile = dr["payload"]["graph_snapshot"]["layer_outputs"]["identity_profile"]

    expected_outputs = {
        "module_basic_identity": "basic_identity",
        "module_growth_background": "growth_background",
        "module_career_identity": "career_identity",
        "module_existence_mode": "existence_mode",
        "module_identity_anchor": "identity_anchor",
    }
    for module_id, output_key in expected_outputs.items():
        module_output = next(
            node for node in modules[module_id]["module_graph"]["nodes"] if node["node_type"] == "module_output"
        )
        assert identity_profile[output_key] == module_output["outputs"][output_key]


def test_layer3_safety_policies_assembled_into_layer3_and_top_safety_policy():
    dr = compile_dr_v0_3(_canvas_13())
    layer_outputs = dr["payload"]["graph_snapshot"]["layer_outputs"]
    layer_3 = layer_outputs["layer_3"]

    assert set(LAYER3_SAFETY_POLICY_KEYS).issubset(layer_3)
    for output_key, required_keys in LAYER3_SAFETY_POLICY_KEYS.items():
        policy = layer_3[output_key]
        for key in required_keys:
            assert key in policy
        expected_decision_modes = ["allow", "soften", "refuse", "review", "block"] if output_key == RISK_POLICY_OUTPUT_KEY else ["allow", "soften", "refuse", "block"]
        assert policy["decision_modes"] == expected_decision_modes
        assert policy["compile_validation_status"] == "valid"
        assert policy["identity_context_ref"] == "layer_1.resident_identity"
        assert dr["payload"]["safety_policy"][output_key] == policy
        assert dr["safety_policy"][output_key] == policy
    content_safety_policy = layer_3[CONTENT_SAFETY_OUTPUT_KEY]
    assert content_safety_policy["decision_modes"] == ["allow", "soften", "refuse", "block"]
    assert content_safety_policy["default_mode"] == "soften"
    assert content_safety_policy["high_risk_action"] == "block"
    assert layer_3[BEHAVIOR_SAFETY_OUTPUT_KEY]["default_mode"] == "soften"
    assert layer_3[BEHAVIOR_SAFETY_OUTPUT_KEY]["high_risk_behavior_action"] == "block"
    assert layer_3[DATA_SAFETY_OUTPUT_KEY]["default_mode"] == "refuse"
    assert layer_3[DATA_SAFETY_OUTPUT_KEY]["sensitive_data_handling"] == "refuse_or_minimize"
    assert layer_3[INTERACTION_SAFETY_OUTPUT_KEY]["default_mode"] == "soften"
    assert layer_3[INTERACTION_SAFETY_OUTPUT_KEY]["non_romantic_default_boundary"] == "companion_default"
    risk_policy = layer_3[RISK_POLICY_OUTPUT_KEY]
    assert risk_policy["default_risk_mode"] == "review"
    assert risk_policy["decision_modes"] == ["allow", "soften", "refuse", "review", "block"]
    assert risk_policy["compile_validation_status"] == "valid"
    assert layer_3[HARD_BLOCK_POLICY_OUTPUT_KEY] == risk_policy["hard_block_policy"]
    assert layer_3[HUMAN_REVIEW_POLICY_OUTPUT_KEY] == risk_policy["human_review_policy"]
    assert layer_3[AUDIT_LOG_POLICY_OUTPUT_KEY] == risk_policy["audit_log_policy"]
    assert layer_3[SAFE_REDIRECT_POLICY_OUTPUT_KEY] == risk_policy["safe_redirect_policy"]
    for output_key in (HARD_BLOCK_POLICY_OUTPUT_KEY, HUMAN_REVIEW_POLICY_OUTPUT_KEY, AUDIT_LOG_POLICY_OUTPUT_KEY, SAFE_REDIRECT_POLICY_OUTPUT_KEY):
        assert dr["payload"]["safety_policy"][output_key] == layer_3[output_key]
        assert dr["safety_policy"][output_key] == layer_3[output_key]
    assert dr["payload"]["safety_policy"]["no_secret_in_dr"] is True
    assert dr["payload"]["safety_policy"]["no_direct_provider_binding"] is True
    assert dr["payload"]["safety_policy"]["not_executable"] is True


def test_layer8_behavior_policy_assembled_into_layer8_and_top_payload():
    dr = compile_dr_v0_3(_canvas_13())
    layer_outputs = dr["payload"]["graph_snapshot"]["layer_outputs"]
    layer_8 = layer_outputs["layer_8"]
    behavior_policy = dr["payload"]["behavior_policy"]

    assert "behavior_policy" not in dr
    assert dr["payload"]["resident_blueprint"]["behavior_policy"] == behavior_policy
    assert layer_outputs["behavior_policy"] == behavior_policy
    assert layer_8["behavior_policy"] == behavior_policy
    assert layer_8["module_count"] == 6
    assert layer_8["core_module_ids"] == list(LAYER8_BEHAVIOR_POLICY_KEYS.values())
    assert "behavior_policy_slot" in layer_8["excluded_modules"]
    assert layer_8["validation_result"] == "pass"

    assert behavior_policy["schema_version"] == "0.1"
    assert behavior_policy["source_layer"] == "layer_8"
    assert set(behavior_policy["modules"]) == set(LAYER8_BEHAVIOR_POLICY_KEYS)
    serialized_policy = json.dumps(behavior_policy, ensure_ascii=False)
    for forbidden in ("林瑄", "linxuan", "resident_id", "codename", "display_alias"):
        assert forbidden not in serialized_policy

    for policy_key, module_id in LAYER8_BEHAVIOR_POLICY_KEYS.items():
        module_policy = behavior_policy["modules"][policy_key]
        assert module_policy["module_id"] == module_id
        assert module_policy["source_module_id"] == module_id
        assert module_policy["module_type"].endswith("_behavior_config")
        assert module_policy["preset_id"]
        assert module_policy["selected_options"]
        assert isinstance(module_policy["custom_text"], str)
        assert module_policy["field_references"]
        assert module_policy["validation_rules"]
        assert module_policy["tags"]
        assert len(module_policy["source_nodes"]) == 5
        for reference in module_policy["field_references"]:
            assert reference["reference_type"] != "forbidden"
            assert reference["layer_id"]
            assert reference["module_id"]
            assert reference["field_id"]
            assert reference["path"] == "/".join((reference["layer_id"], reference["module_id"], reference["field_id"]))
            assert "label" not in reference
            assert "value" not in reference


def test_layer3_formal_module_ids_exclude_catalog_only_legacy_modules():
    dr = compile_dr_v0_3(_canvas_13())
    layer_snapshot = next(layer for layer in dr["payload"]["13_layers_snapshot"] if layer["layer_id"] == "layer_3")
    graph_layer = next(layer for layer in dr["payload"]["graph_snapshot"]["layers"] if layer["layer_id"] == "layer_3")
    payload_module_ids = {module["module_id"] for module in dr["payload"]["modules"]}

    assert layer_snapshot["module_ids"] == list(LAYER3_FORMAL_SAFETY_MODULE_IDS)
    assert graph_layer["module_ids"] == list(LAYER3_FORMAL_SAFETY_MODULE_IDS)
    for module_id in LAYER3_CATALOG_ONLY_MODULE_IDS:
        assert module_id not in layer_snapshot["module_ids"]
        assert module_id not in graph_layer["module_ids"]
        assert module_id not in payload_module_ids


def test_layer2_formal_module_ids_are_five_text_config_modules():
    dr = compile_dr_v0_3(_canvas_13())
    layer_snapshot = next(layer for layer in dr["payload"]["13_layers_snapshot"] if layer["layer_id"] == "layer_2")
    graph_layer = next(layer for layer in dr["payload"]["graph_snapshot"]["layers"] if layer["layer_id"] == "layer_2")
    payload_modules = {module["module_id"]: module for module in dr["payload"]["modules"]}

    assert layer_snapshot["module_ids"] == list(LAYER2_PERSONALITY_FORMAL_MODULE_IDS)
    assert graph_layer["module_ids"] == list(LAYER2_PERSONALITY_FORMAL_MODULE_IDS)
    for module_id in LAYER2_PERSONALITY_FORMAL_MODULE_IDS:
        module = payload_modules[module_id]
        assert module["slot_type"] is None
        assert module["runtime_enabled"] is False
        assert module["no_execution"] is True
        assert module["config"]["text_config_only"] is True
        assert len(module["module_graph"]["nodes"]) == 5
    for module_id in LAYER2_CATALOG_ONLY_MODULE_IDS:
        assert module_id not in payload_modules
        assert module_id not in layer_snapshot["module_ids"]


def test_layer3_safety_compile_does_not_change_layer1_identity():
    base = compile_dr_v0_3(_linxuan_canvas())
    canvas = _linxuan_canvas()
    module = next(module for module in canvas["modules"] if module["module_id"] == CONTENT_SAFETY_MODULE_ID)
    output_node = next(node for node in module["module_graph"]["nodes"] if node["node_type"] == "module_output")
    policy = output_node["outputs"][CONTENT_SAFETY_OUTPUT_KEY]
    policy["allowed_scope"] = ["humanistic_dialogue"]
    policy["cautious_scope"] = ["sensitive_emotion"]
    policy["forbidden_scope"] = ["adult_content", "medical_legal_financial_conclusion"]
    policy["high_risk_action"] = "block"
    module["outputs"][CONTENT_SAFETY_OUTPUT_KEY] = policy

    behavior = next(module for module in canvas["modules"] if module["module_id"] == BEHAVIOR_SAFETY_MODULE_ID)
    behavior_output = next(node for node in behavior["module_graph"]["nodes"] if node["node_type"] == "module_output")
    behavior_policy = behavior_output["outputs"][BEHAVIOR_SAFETY_OUTPUT_KEY]
    behavior_policy["forbidden_behaviors"] = ["autonomous_external_action"]
    behavior["outputs"][BEHAVIOR_SAFETY_OUTPUT_KEY] = behavior_policy

    dr = compile_dr_v0_3(canvas)

    assert dr["payload"]["resident_identity"] == base["payload"]["resident_identity"]
    assert dr["payload"]["graph_snapshot"]["layer_outputs"]["identity_profile"] == base["payload"]["graph_snapshot"]["layer_outputs"]["identity_profile"]
    assert dr["payload"]["graph_snapshot"]["layer_outputs"]["layer_1"] == base["payload"]["graph_snapshot"]["layer_outputs"]["layer_1"]
    assert dr["payload"]["graph_snapshot"]["layer_outputs"]["layer_3"][CONTENT_SAFETY_OUTPUT_KEY]["allowed_scope"] == ["humanistic_dialogue"]
    assert dr["payload"]["graph_snapshot"]["layer_outputs"]["layer_3"][CONTENT_SAFETY_OUTPUT_KEY]["compile_validation_status"] == "valid"
    assert dr["payload"]["graph_snapshot"]["layer_outputs"]["layer_3"][BEHAVIOR_SAFETY_OUTPUT_KEY]["forbidden_behaviors"] == ["autonomous_external_action"]
    assert dr["payload"]["graph_snapshot"]["layer_outputs"]["layer_3"][BEHAVIOR_SAFETY_OUTPUT_KEY]["compile_validation_status"] == "valid"


def test_risk_response_derives_policy_when_saved_output_has_no_fields():
    canvas = _canvas_13()
    modules = [module.model_dump(mode="json") for module in get_module_catalog()]
    risk_module = next(module for module in modules if module["module_id"] == RISK_RESPONSE_MODULE_ID)
    output_node = next(node for node in risk_module["module_graph"]["nodes"] if node["node_type"] == "module_output")
    output_node["outputs"][RISK_POLICY_OUTPUT_KEY] = {"output_key": RISK_POLICY_OUTPUT_KEY, "fields": {}, "compile_time_only": True}
    risk_module["outputs"][RISK_POLICY_OUTPUT_KEY] = {"output_key": RISK_POLICY_OUTPUT_KEY, "fields": {}, "compile_time_only": True}
    canvas["modules"] = modules

    dr = compile_dr_v0_3(canvas)
    layer_3 = dr["payload"]["graph_snapshot"]["layer_outputs"]["layer_3"]
    risk_policy = layer_3[RISK_POLICY_OUTPUT_KEY]

    assert risk_policy["compile_validation_status"] == "valid"
    assert risk_policy["decision_modes"] == ["allow", "soften", "refuse", "review", "block"]
    assert risk_policy["default_risk_mode"] == "review"
    assert risk_policy["risk_signal_summary"]["input_policies"] == [
        CONTENT_SAFETY_OUTPUT_KEY,
        BEHAVIOR_SAFETY_OUTPUT_KEY,
        DATA_SAFETY_OUTPUT_KEY,
        INTERACTION_SAFETY_OUTPUT_KEY,
    ]
    assert risk_policy["risk_level_policy"]["default_risk_level"] == "review"
    assert risk_policy["risk_response_strategy"]["block_action"]
    assert risk_policy[HUMAN_REVIEW_POLICY_OUTPUT_KEY]["human_review_triggers"]
    assert risk_policy[HARD_BLOCK_POLICY_OUTPUT_KEY]["hard_block_triggers"]
    assert layer_3[HARD_BLOCK_POLICY_OUTPUT_KEY] == risk_policy[HARD_BLOCK_POLICY_OUTPUT_KEY]
    assert dr["payload"]["safety_policy"][RISK_POLICY_OUTPUT_KEY] == risk_policy
    assert dr["safety_policy"][RISK_POLICY_OUTPUT_KEY] == risk_policy


def test_compile_reads_user_filled_identity_field_values():
    modules = [module.model_dump(mode="json") for module in get_module_catalog()]
    basic_identity = next(module for module in modules if module["module_id"] == "module_basic_identity")
    field_input = next(node for node in basic_identity["module_graph"]["nodes"] if node["node_type"] == "field_input")
    for field in field_input["params"]["fields"]:
        if field["field_id"] == "name":
            field["value"] = "Test Resident"
        if field["field_id"] == "display_alias":
            field["value"] = "Tester"
        if field["field_id"] == "resident_id":
            field["value"] = "test_resident_001"
        if field["field_id"] == "codename":
            field["value"] = "test_codename"
        if field["field_id"] == "primary_language":
            field["value"] = "cn"
        if field["field_id"] == "export_name":
            field["value"] = "test_export"
        if field["field_id"] == "city":
            field["value"] = "Test City"

    fields_by_id = {field["field_id"]: field["value"] for field in field_input["params"]["fields"]}
    module_output = next(node for node in basic_identity["module_graph"]["nodes"] if node["node_type"] == "module_output")
    module_output["outputs"]["basic_identity"]["fields"] = fields_by_id
    basic_identity["outputs"]["basic_identity"]["fields"] = fields_by_id

    canvas = _canvas_13()
    canvas["modules"] = modules
    dr = compile_dr_v0_3(canvas)

    identity_profile = dr["payload"]["graph_snapshot"]["layer_outputs"]["identity_profile"]
    assert identity_profile["name"] == "Test Resident"
    assert identity_profile["resident_id"] == "test_resident_001"
    assert identity_profile["codename"] == "test_codename"
    assert identity_profile["display_alias"] == "Tester"
    assert identity_profile["primary_language"] == "zh-CN"
    assert identity_profile["export_name"] == "test_export"
    assert identity_profile["basic_identity"]["fields"]["name"] == "Test Resident"
    assert identity_profile["basic_identity"]["fields"]["city"] == "Test City"
    assert "display_alias" not in identity_profile["locked_core_fields"]
    assert "export_name" not in identity_profile["locked_core_fields"]
    assert dr["manifest"]["resident_id"] == "test_resident_001"
    assert dr["manifest"]["resident_name"] == "Test Resident"
    assert dr["payload"]["resident_identity"]["resident_id"] == "test_resident_001"
    assert dr["payload"]["resident_identity"]["name"] == "Test Resident"
    assert dr["payload"]["resident_identity"]["primary_language"] == "zh-CN"
    assert dr["payload"]["resident_identity"]["city_symbol"] == "Test City"
    assert dr["resident"]["resident_id"] == "test_resident_001"
    assert dr["resident"]["name"] == "Test Resident"
    assert dr["payload"]["lattice_config"]["resident_id"] == "test_resident_001"
    assert dr["lattice_config"]["resident_id"] == "test_resident_001"
    assert dr["lattice_state_schema"]["resident_id"] == "test_resident_001"
    assert dr["multi_resident_lattice_state"]["resident_ids"] == ["test_resident_001"]
    legacy = dr["legacy_blueprint"]
    assert legacy["lattice_config"]["resident_id"] == "test_resident_001"
    assert legacy["lattice_state_schema"]["resident_id"] == "test_resident_001"
    assert legacy["multi_resident_lattice_state"]["resident_ids"] == ["test_resident_001"]
    assert legacy["resident_instance"]["resident_id"] == "test_resident_001"
    assert legacy["resident_instance"]["identity"]["resident_id"] == "test_resident_001"
    assert legacy["resident_instance"]["name"] == "Test Resident"
    assert legacy["resident_instance"]["identity"]["name"] == "Test Resident"
    payload_module = next(module for module in dr["payload"]["modules"] if module["module_id"] == "module_basic_identity")
    payload_field_input = next(node for node in payload_module["module_graph"]["nodes"] if node["node_type"] == "field_input")
    assert {field["field_id"]: field["value"] for field in payload_field_input["params"]["fields"]}["name"] == "Test Resident"


def test_identity_core_aggregator_outputs_exist():
    dr = compile_dr_v0_3(_canvas_13())
    aggregator = dr["payload"]["graph_snapshot"]["layer_outputs"]["layer_1"]["identity_core_aggregator"]

    for key in (
        "identity_profile",
        "locked_core_fields",
        "versioned_core_fields",
        "update_rules",
        "identity_summary",
        "module_audit",
        "layer_audit",
    ):
        assert key in aggregator
    assert aggregator["module_audit"]["ok"] is True
    assert aggregator["layer_audit"]["ok"] is True


def test_v03_contract_unchanged_for_aftelle():
    dr = compile_dr_v0_3(_canvas_13())

    assert dr["manifest"]["resident_id"]
    assert dr["payload"]["resident_identity"]["resident_id"] == dr["manifest"]["resident_id"]
    assert dr["payload"]["resident_identity"]["name"] == dr["manifest"]["resident_name"]
    assert dr["payload"]["lattice_config"]["schema_version"] == "0.3.0"
    assert dr["payload"]["voice_config"]["schema_version"] == "0.3.0"
    assert dr["payload"]["safety_policy"]["no_secret_in_dr"] is True
    assert dr["payload"]["safety_policy"]["no_direct_provider_binding"] is True
    assert dr["lattice_config"] == dr["payload"]["lattice_config"]
    assert dr["voice_config"] == dr["payload"]["voice_config"]
    assert dr["safety_policy"] == dr["payload"]["safety_policy"]


def test_identity_profile_optional_and_fallback_safe():
    dr = compile_dr_v0_3(_canvas_13())
    dr["payload"]["graph_snapshot"].pop("layer_outputs", None)

    loaded = mock_load_dr_v0_3(dr)
    assert loaded["loaded"] is True
    assert loaded["resident_id"] == dr["manifest"]["resident_id"]


def test_aftelle_top_level_identity_summary_from_identity_profile():
    dr = compile_dr_v0_3(_linxuan_canvas())
    resident_identity = dr["payload"]["resident_identity"]

    assert resident_identity["name"] == "林瑄"
    assert resident_identity["resident_id"] == "dr_eterna_hum_cn_xian_linxuan_0001"
    assert "synthetic persona" not in resident_identity["personality_summary"]
    assert "AI-generated digital resident" not in resident_identity["personality_summary"]
    assert resident_identity["city_symbol"] == "西安"


def test_resident_blueprint_description_tags_generated():
    dr = compile_dr_v0_3(_linxuan_canvas())
    blueprint = dr["payload"]["resident_blueprint"]

    assert blueprint["description"]
    assert blueprint["source_workflow_name"] == "Stage 7.4 Human Empathy DR Baseline"
    assert blueprint["ui_language"] == "zh-CN"
    for tag in ("human_empathy", "xian", "zh-CN", "companion"):
        assert tag in blueprint["tags"]


def test_resident_description_and_disclosure_generated():
    dr = compile_dr_v0_3(_linxuan_canvas())
    resident = dr["resident"]

    assert "林瑄" in resident["name"]
    assert resident["description"]
    assert "西安" in resident["description"]
    assert "原创虚构" in resident["disclosure"]
    assert "不对应现实真人" in resident["disclosure"]


def test_domain_focus_excludes_future_capabilities():
    dr = compile_dr_v0_3(_linxuan_canvas())
    domain_focus = set(dr["payload"]["resident_identity"]["domain_focus"])

    assert {"human_empathy", "companion", "emotional_support", "relationship_communication", "daily_life", "xian", "zh-CN"}.issubset(domain_focus)
    assert not domain_focus.intersection({"screen_guidance", "ar", "tool", "provider", "cross_app_control"})


def test_identity_consistency_gate_keeps_linxuan_valid():
    body = compile_dr_result_v0_3(_linxuan_canvas())
    dr = body["compiled_dr"]
    resident_identity = dr["payload"]["resident_identity"]
    identity_profile = dr["payload"]["graph_snapshot"]["layer_outputs"]["identity_profile"]
    basic_fields = identity_profile["basic_identity"]["fields"]

    assert body["valid"] is True
    assert dr["audit_report"]["valid"] is True
    assert dr["manifest"]["resident_id"] == basic_fields["resident_id"]
    assert resident_identity["resident_id"] == basic_fields["resident_id"]
    assert dr["manifest"]["resident_name"] == basic_fields["name"]
    assert resident_identity["name"] == basic_fields["name"]
    assert resident_identity["city_symbol"] == basic_fields["city"]
    assert resident_identity["primary_language"] == "zh-CN"
    assert basic_fields["primary_language"] == "zh-CN"
    assert not any(finding["code"].startswith("DR_IDENTITY_CONSISTENCY") for finding in dr["audit_report"]["findings"])


def test_identity_consistency_gate_blocks_forbidden_domain_focus(monkeypatch):
    original_summary_builder = dr_compiler._build_identity_top_summary

    def poisoned_summary(identity_profile):
        summary = original_summary_builder(identity_profile)
        summary["domain_focus"] = [*summary["domain_focus"], "screen_guidance"]
        return summary

    monkeypatch.setattr(dr_compiler, "_build_identity_top_summary", poisoned_summary)
    body = compile_dr_result_v0_3(_linxuan_canvas())

    assert body["valid"] is False
    assert body["compiled_dr"] is None
    assert any(finding["code"] == "DR_IDENTITY_CONSISTENCY_DOMAIN_FOCUS" for finding in body["errors"])


def test_identity_consistency_gate_blocks_default_girlfriend_relationship():
    canvas = _linxuan_canvas()
    _set_identity_field(
        canvas,
        "module_identity_anchor",
        "identity_definition",
        "默认关系定位为女友",
    )

    body = compile_dr_result_v0_3(canvas)

    assert body["valid"] is False
    assert body["compiled_dr"] is None
    assert any(finding["code"] == "DR_IDENTITY_CONSISTENCY_DEFAULT_RELATIONSHIP" for finding in body["errors"])


def test_required_capabilities_do_not_overclaim_stage_7_4_1():
    dr = compile_dr_v0_3(_linxuan_canvas())
    required = set(dr["manifest"]["required_capabilities"])
    required_slot_types = set(dr["payload"]["runtime_requirements"]["required_slot_types"])
    legacy_required_slot_types = dr["legacy_blueprint"]["runtime_requirements"]["required_slot_types"]

    assert {"memory", "lattice"}.issubset(required)
    assert not required.intersection({"ar", "tool", "screen_mock", "real_avatar", "tts_required", "provider"})
    assert {"llm", "memory", "lattice"}.issubset(required_slot_types)
    assert not required_slot_types.intersection({"ar", "tool"})
    assert legacy_required_slot_types == ["llm", "memory", "lattice"]


def test_language_and_dates_normalized_for_export():
    canvas = _linxuan_canvas()
    basic_identity = next(module for module in canvas["modules"] if module["module_id"] == "module_basic_identity")
    field_input = next(node for node in basic_identity["module_graph"]["nodes"] if node["node_type"] == "field_input")
    for field in field_input["params"]["fields"]:
        if field["field_id"] == "primary_language":
            field["value"] = "ch-ZH"
    fields_by_id = {field["field_id"]: field["value"] for field in field_input["params"]["fields"]}
    module_output = next(node for node in basic_identity["module_graph"]["nodes"] if node["node_type"] == "module_output")
    module_output["outputs"]["basic_identity"]["fields"] = fields_by_id
    basic_identity["outputs"]["basic_identity"]["fields"] = fields_by_id

    dr = compile_dr_v0_3(canvas)
    identity_profile = dr["payload"]["graph_snapshot"]["layer_outputs"]["identity_profile"]
    fields = identity_profile["basic_identity"]["fields"]

    assert dr["payload"]["resident_identity"]["primary_language"] == "zh-CN"
    assert dr["payload"]["resident_blueprint"]["ui_language"] == "zh-CN"
    assert "中文" in dr["payload"]["resident_identity"]["personality_summary"]
    assert "zh-CN" not in dr["payload"]["resident_identity"]["personality_summary"]
    assert "ch-ZH" not in json.dumps(dr, ensure_ascii=False)
    assert fields["birth_date"] == "2003-02-24"
    assert fields["virtual_birth_date"] == "2026-08-18"


def test_legacy_blueprint_identity_aliases_synced():
    dr = compile_dr_v0_3(_linxuan_canvas())
    legacy = dr["legacy_blueprint"]

    assert legacy["resident_instance"]["resident_id"] == "dr_eterna_hum_cn_xian_linxuan_0001"
    assert legacy["resident_instance"]["identity"]["resident_id"] == "dr_eterna_hum_cn_xian_linxuan_0001"
    assert legacy["resident_instance"]["identity"]["name"] == "林瑄"
    assert legacy["lattice_config"]["resident_id"] == "dr_eterna_hum_cn_xian_linxuan_0001"
    assert legacy["lattice_state_schema"]["resident_id"] == "dr_eterna_hum_cn_xian_linxuan_0001"
    assert legacy["multi_resident_lattice_state"]["resident_ids"] == ["dr_eterna_hum_cn_xian_linxuan_0001"]
    assert "schema_canvas" not in json.dumps(legacy, ensure_ascii=False)


def test_mock_runtime_fields_allowed():
    dr = compile_dr_v0_3(_linxuan_canvas())

    assert dr["manifest"]["compatible_runtime"] == "resident_v1_mock"
    assert dr["payload"]["runtime_requirements"]["execution_mode"] == "mock"
    assert dr["audit_report"]["valid"] is True


def test_no_secret_or_provider_in_dr():
    dr = compile_dr_v0_3(_linxuan_canvas())
    forbidden_keys = {"api_key", "access_token", "refresh_token", "base_url", "credential", "client_secret"}
    violations = []

    def collect_secret_fields(value, path="dr"):
        if isinstance(value, dict):
            for key, item in value.items():
                item_path = f"{path}.{key}"
                if str(key).lower() in forbidden_keys and item not in (None, "", [], {}):
                    violations.append(item_path)
                collect_secret_fields(item, item_path)
        elif isinstance(value, list):
            for index, item in enumerate(value):
                collect_secret_fields(item, f"{path}[{index}]")

    collect_secret_fields(dr)
    # Declarative deny-lists may name forbidden fields such as ``api_key``;
    # only an actual secret-bearing field is prohibited.
    assert violations == []


def test_identity_compile_time_nodes_not_in_runtime_plan():
    dr = compile_dr_v0_3(_canvas_13())
    runtime_steps = json.dumps(dr["payload"]["runtime_plan"]["steps"], ensure_ascii=False)

    for node_type in ("field_input", "structure_normalize", "validation", "update_rule", "module_output", "layer_aggregator"):
        assert node_type not in runtime_steps


def test_default_catalog_has_no_legacy_field_input_warning():
    body = compile_dr_result_v0_3(_canvas_13())

    assert body["valid"] is True
    assert not any(
        finding["code"] == "DR_IDENTITY_LEGACY_FIELD_INPUT_MISSING"
        for finding in body["warnings"]
    )


def test_identity_generic_fields_compile_without_legacy_warning():
    body = compile_dr_result_v0_3(_identity_generic_fields_canvas())

    assert body["valid"] is True
    assert not any(
        finding["code"] == "DR_IDENTITY_LEGACY_FIELD_INPUT_MISSING"
        for finding in body["warnings"]
    )
    identity_profile = body["compiled_dr"]["payload"]["graph_snapshot"]["layer_outputs"]["identity_profile"]
    basic_fields = identity_profile["basic_identity"]["fields"]
    assert identity_profile["name"] == "Generic Fields Resident"
    assert identity_profile["resident_id"] == "generic_fields_resident_001"
    assert basic_fields["primary_language"] == "zh-CN"
    assert basic_fields["generic_boolean_flag"] is True
    assert basic_fields["generic_list_value"] == ["alpha", "beta"]
    payload_module = next(module for module in body["compiled_dr"]["payload"]["modules"] if module["module_id"] == "module_basic_identity")
    text_input = next(node for node in payload_module["module_graph"]["nodes"] if node["node_type"] == "text_input")
    params = text_input["params"]
    legacy_language = next(field for field in params["legacy_fields"] if field["field_key"] == "primary_language")
    legacy_data_language = next(field for field in params["legacy_data_fields"] if field["field_key"] == "primary_language")
    assert legacy_language["field_value"] == "zh-CN"
    assert legacy_data_language["field_value"] == "zh-CN"


def test_legacy_module_output_fallback_warning():
    modules = [module.model_dump(mode="json") for module in get_module_catalog()]
    modules.append(
        {
            "module_id": "legacy_persona_output",
            "module_type": "legacy_persona",
            "module_name": "Legacy Persona Output",
            "module_version": "0.1.0",
            "layer_id": "layer_2",
            "module_graph": {"nodes": []},
            "outputs": {"legacy_persona": {"fields": {}}, "module_output": "legacy_persona"},
            "category": "persona",
            "status": "MOCK",
            "runtime_enabled": False,
            "no_execution": True,
        }
    )
    canvas = _canvas_13()
    canvas["modules"] = modules

    body = compile_dr_result_v0_3(canvas)
    assert body["valid"] is True
    assert any(
        finding["status"] == "WARNING" and finding["code"] == "DR_IDENTITY_LEGACY_FIELD_INPUT_MISSING"
        for finding in body["warnings"]
    )


def test_compile_result_and_export_use_v03_payload():
    body = compile_dr_result_v0_3(_canvas_13())
    assert body["valid"] is True
    assert body["dr_version"] == "0.3"
    assert body["compiled_dr"]["dr_version"] == "0.3"
    assert body["dr_payload"]["runtime_plan"]["steps"]

    resp = client.post("/dr/compile", json=_canvas_13())
    assert resp.status_code == 200
    compile_body = resp.json()
    assert compile_body["valid"] is True
    assert compile_body["dr_version"] == "0.3"
    assert compile_body["compiled_dr"]["dr_version"] == "0.3"
    assert compile_body["compiled_dr"]["dr_schema_version"] == "0.3.0"
    assert compile_body["compiled_dr"]["not_executable"] is True

    export_resp = client.post("/dr/export", json=_canvas_13())
    assert export_resp.status_code == 200
    assert export_resp.headers["content-type"] == "application/x-digital-resident"
    exported = json.loads(export_resp.text)
    assert exported["dr_version"] == "0.3"
    assert exported["dr_schema_version"] == "0.3.0"
    assert exported["not_executable"] is True

    load_resp = client.post("/dr/load", json={"dr": body["compiled_dr"]})
    assert load_resp.status_code == 200
    assert load_resp.json()["loaded"] is True


def test_invalid_canvas_blocks_export():
    canvas = _canvas_13()
    canvas["modules"] = [
        {"module_id": "dup", "module_type": "t", "layer_id": "layer_1"},
        {"module_id": "dup", "module_type": "t", "layer_id": "layer_2"},
    ]
    body = client.post("/dr/compile", json=canvas).json()
    assert body["valid"] is False
    assert body["compiled_dr"] is None
    assert client.post("/dr/export", json=canvas).status_code == 422


def test_mock_loader_reads_v03_dr():
    dr = compile_dr_v0_3(_canvas_13())
    loaded = mock_load_dr_v0_3(dr)
    assert loaded["loaded"] is True
    assert loaded["layer_count"] == 13
    assert loaded["audit_valid"] is True
