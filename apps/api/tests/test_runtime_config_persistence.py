"""Runtime Config Persistence v1 acceptance.

Local private JSON persistence across sections (llm/memory/lattice/tts/screen),
masked GET (no secret leak), and llm compatibility with Stage 6.6.

Run: cd apps/api && .venv/bin/python -m pytest tests/test_runtime_config_persistence.py -q
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services import runtime_config_service as rcs
from app.services.runtime_llm_config import (
    get_runtime_llm_config,
    reset_runtime_llm_config,
)

client = TestClient(app)


@pytest.fixture(autouse=True)
def _reset_llm():
    reset_runtime_llm_config()
    yield
    reset_runtime_llm_config()


# --- llm persists across a simulated restart ---------------------------------
def test_llm_config_persists_across_restart():
    rcs.set_section("llm", {"base_url": "https://relay/v1", "api_key": "sk-secret", "model": "gpt-x", "enabled": True})
    assert rcs._LOCAL_PATH.exists()  # written to the (tmp) local JSON

    # Simulate a backend restart: clear in-process llm, reload from local JSON.
    reset_runtime_llm_config()
    assert get_runtime_llm_config().api_key == ""
    rcs.load()

    cfg = get_runtime_llm_config()
    assert cfg.api_key == "sk-secret"  # restored from local JSON
    assert cfg.model == "gpt-x"
    assert cfg.is_valid() is True  # workflow will use llm_primary


def test_llm_get_is_masked_no_secret():
    rcs.set_section("llm", {"base_url": "https://relay/v1", "api_key": "sk-secret", "model": "gpt-x", "enabled": True})
    got = client.get("/runtime/config/llm").json()
    assert got["has_api_key"] is True
    assert "api_key" not in got
    assert "sk-secret" not in json.dumps(got)


# --- memory/lattice/tts/screen save + read (not wired to real capability) -----
@pytest.mark.parametrize("section", ["memory", "lattice", "tts", "screen"])
def test_non_llm_sections_save_and_read(section):
    masked = rcs.set_section(section, {"enabled": True, "endpoint": "http://x", "token": "tok-123"})
    assert masked["enabled"] is True
    assert masked["endpoint"] == "http://x"
    assert masked["has_token"] is True
    assert "token" not in masked  # secret never returned

    # Simulate restart: clear store, reload from local JSON.
    rcs.reset()
    assert rcs.get_section_masked(section)["enabled"] is False
    rcs.load()
    reread = rcs.get_section_masked(section)
    assert reread["enabled"] is True
    assert reread["endpoint"] == "http://x"
    assert reread["has_token"] is True
    # Raw store keeps the secret locally (for backend use only).
    assert rcs.get_section_raw(section)["token"] == "tok-123"


def test_secret_empty_keeps_existing():
    rcs.set_section("tts", {"api_key": "secret-1", "voice": "v1"})
    rcs.set_section("tts", {"voice": "v2", "api_key": ""})  # empty = unchanged
    raw = rcs.get_section_raw("tts")
    assert raw["api_key"] == "secret-1"
    assert raw["voice"] == "v2"


# --- unified endpoints -------------------------------------------------------
def test_get_all_config_masked_no_secrets():
    rcs.set_section("llm", {"api_key": "sk-a", "base_url": "u", "model": "m", "enabled": True})
    rcs.set_section("screen", {"secret": "shh", "enabled": True})
    body = client.get("/runtime/config").json()
    assert set(body["sections"].keys()) == set(rcs.SECTIONS)
    blob = json.dumps(body)
    assert "sk-a" not in blob and "shh" not in blob
    assert body["sections"]["llm"]["has_api_key"] is True
    assert body["sections"]["screen"]["has_secret"] is True


def test_post_section_endpoint_and_get():
    saved = client.post("/runtime/config/lattice", json={"enabled": True, "url": "lat://x", "secret": "s1"}).json()
    assert saved["saved"] is True and saved["section"] == "lattice"
    assert saved["has_secret"] is True and "secret" not in saved
    got = client.get("/runtime/config/lattice").json()
    assert got["enabled"] is True and got["url"] == "lat://x"
    assert "secret" not in got


def test_post_all_sections_endpoint():
    client.post("/runtime/config", json={"sections": {"memory": {"enabled": True, "size": 10}, "tts": {"enabled": True}}})
    body = client.get("/runtime/config").json()
    assert body["sections"]["memory"]["enabled"] is True
    assert body["sections"]["memory"]["size"] == 10
    assert body["sections"]["tts"]["enabled"] is True


def test_unknown_section_returns_404():
    assert client.get("/runtime/config/does_not_exist").status_code == 404
    assert client.post("/runtime/config/does_not_exist", json={"x": 1}).status_code == 404


# --- .runtime is git-ignored -------------------------------------------------
def test_runtime_dir_is_gitignored():
    gitignore = Path(__file__).resolve().parents[1] / ".gitignore"
    assert ".runtime/" in gitignore.read_text(encoding="utf-8")
