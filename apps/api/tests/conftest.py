"""Shared test fixtures.

Isolate Runtime Config Persistence so no test ever writes to the real
apps/api/.runtime/ directory: every test gets a throwaway tmp path.
"""

from __future__ import annotations

import pytest

from app.services import memory_store as ms
from app.services import runtime_config_service as rcs


@pytest.fixture(autouse=True)
def _isolate_runtime_config(tmp_path, monkeypatch):
    runtime_dir = tmp_path / ".runtime"
    monkeypatch.setattr(rcs, "_RUNTIME_DIR", runtime_dir)
    monkeypatch.setattr(rcs, "_LOCAL_PATH", runtime_dir / "runtime_config.local.json")
    # Isolate the memory store (Stage 6.7) to a throwaway tmp dir too.
    monkeypatch.setattr(ms, "_RUNTIME_DIR", runtime_dir)
    monkeypatch.setattr(ms, "_SQLITE_PATH", runtime_dir / "memory.sqlite3")
    monkeypatch.setattr(ms, "_JSON_PATH", runtime_dir / "memory.json")
    rcs.reset()
    ms.reset_memory_store()
    yield
    rcs.reset()
    ms.reset_memory_store()
