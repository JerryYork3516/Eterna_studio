"""Shared test fixtures.

Isolate Runtime Config Persistence so no test ever writes to the real
apps/api/.runtime/ directory: every test gets a throwaway tmp path.
"""

from __future__ import annotations

import pytest

from app.services import runtime_config_service as rcs


@pytest.fixture(autouse=True)
def _isolate_runtime_config(tmp_path, monkeypatch):
    runtime_dir = tmp_path / ".runtime"
    monkeypatch.setattr(rcs, "_RUNTIME_DIR", runtime_dir)
    monkeypatch.setattr(rcs, "_LOCAL_PATH", runtime_dir / "runtime_config.local.json")
    rcs.reset()
    yield
    rcs.reset()
