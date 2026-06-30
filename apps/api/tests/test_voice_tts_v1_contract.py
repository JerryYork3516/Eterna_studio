"""Stage 6.9 voice / TTS module contract checks."""

from __future__ import annotations

from app.registry.module_catalog import get_module_catalog
from app.registry.node_registry import get_node_definition
from app.registry.slot_catalog import get_slot_catalog
from app.services.dr_compiler import compile_dr


def test_voice_tts_module_is_registered_and_declarative():
    catalog = {module.module_id: module for module in get_module_catalog()}
    module = catalog["voice_tts_module_v1"]

    assert module.layer_id == "layer_10"
    assert module.slot_type.value == "tts"
    assert module.is_placeholder is False
    assert module.runtime_enabled is False
    assert module.ui_config.get("strict_layers") is True
    assert module.dr_mapping == {
        "voice_config": "voice_config",
        "tts_provider_config": "tts_provider_config",
        "voice_profile_config": "voice_profile_config",
        "voice_lattice_sync_policy": "voice_lattice_sync_policy",
        "speech_event_schema": "speech_event_schema",
    }
    assert module.module_graph["slot_routes"] == ["tts.speak", "tts.preview", "voice.status", "speech.input_event"]


def test_voice_tts_slots_are_present():
    catalog = {slot.slot_id: slot for slot in get_slot_catalog()}

    assert set(catalog) >= {
        "slot_tts",
        "slot_voice_status",
        "slot_speech_input_event",
    }
    assert catalog["slot_tts"].runtime_capability == {"methods": ["tts.speak", "tts.preview"], "mode": "mock"}
    assert catalog["slot_voice_status"].runtime_capability == {"methods": ["voice.status", "voice.sync.lattice_voice"], "mode": "mock"}
    assert catalog["slot_speech_input_event"].runtime_capability == {"methods": ["speech.input_event"], "mode": "mock"}


def test_voice_node_registry_is_keyed_and_schema_only():
    required_types = [
        "voice_config",
        "tts_provider",
        "voice_profile",
        "audio_output",
        "speaking_status",
        "voice_lattice_sync",
        "speech_input_event_placeholder",
    ]

    for node_type in required_types:
        entry = get_node_definition(node_type)
        assert entry is not None, node_type
        assert entry.display_name == f"node.type.{node_type}"
        assert entry.description == f"node.{node_type}.description"

    voice_config = get_node_definition("voice_config")
    assert voice_config is not None
    assert [option.label for option in voice_config.input_schema[0].options] == [
        "input.option.default",
        "input.option.elevenlabs",
        "input.option.volcano",
    ]

    speaking_status = get_node_definition("speaking_status")
    assert speaking_status is not None
    assert [option.label for option in speaking_status.input_schema[0].options] == ["input.option.speaking", "input.option.idle"]

    sync = get_node_definition("voice_lattice_sync")
    assert sync is not None
    assert [option.label for option in sync.input_schema[1].options] == ["input.option.mirror", "input.option.append"]


def test_compile_dr_exposes_voice_state_idle():
    dr = compile_dr({"name": "Voice Module Smoke Test"})
    assert dr["lattice_state_schema"]["voice_state"] == "idle"
    assert dr["modules"]
    assert any(module["module_id"] == "voice_tts_module_v1" for module in dr["modules"])
