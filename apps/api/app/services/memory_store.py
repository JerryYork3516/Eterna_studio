"""Memory Store — Stage 6.7 Memory Module v1 storage backend.

A small, local, single-resident memory store with three-tier fallback:

    SQLite (preferred)  ->  JSON file  ->  in-process mock dict

It supports the four memory capabilities (read / write / view / clear), a
`memory_type` (short_term_memory / profile_memory / preference_memory /
interaction_log) and a `namespace`. Storage is local-only under apps/api/.runtime
(git-ignored). There is NO vector memory, NO cross-resident sharing, NO scoring,
NO cloud — by design.

This module is intentionally NOT one of the files scanned by the
`forbidden_import` test (which only scans llm_mock_engine.py and
engine_registry.py); sqlite3 is the stdlib and not a forbidden network import.
"""

from __future__ import annotations

import json
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

MEMORY_TYPES = ("short_term_memory", "profile_memory", "preference_memory", "interaction_log")
DEFAULT_MEMORY_TYPE = "interaction_log"
DEFAULT_NAMESPACE = "default"

# Local private storage (apps/api/.runtime). The dir is already git-ignored.
_RUNTIME_DIR = Path(__file__).resolve().parents[2] / ".runtime"
_SQLITE_PATH = _RUNTIME_DIR / "memory.sqlite3"
_JSON_PATH = _RUNTIME_DIR / "memory.json"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class MemoryStore:
    """Local memory store with SQLite -> JSON -> mock fallback."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._conn: Optional[sqlite3.Connection] = None
        # mock tier: (resident_id, namespace, memory_type) -> list of records
        self._mock: List[Dict[str, Any]] = []
        self.backend = "mock"
        self._init_backend()

    # --- backend selection ---------------------------------------------------
    def _init_backend(self) -> None:
        if self._try_sqlite():
            self.backend = "sqlite"
            return
        if self._try_json():
            self.backend = "json"
            return
        self.backend = "mock"

    def _try_sqlite(self) -> bool:
        try:
            _RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
            conn = sqlite3.connect(str(_SQLITE_PATH), check_same_thread=False)
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS memory_entries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    resident_id TEXT NOT NULL,
                    namespace TEXT NOT NULL,
                    memory_type TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.commit()
            self._conn = conn
            return True
        except Exception:
            self._conn = None
            return False

    def _try_json(self) -> bool:
        try:
            _RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
            if not _JSON_PATH.exists():
                _JSON_PATH.write_text("[]", encoding="utf-8")
            json.loads(_JSON_PATH.read_text(encoding="utf-8"))
            return True
        except Exception:
            return False

    # --- JSON helpers --------------------------------------------------------
    def _json_load(self) -> List[Dict[str, Any]]:
        try:
            return json.loads(_JSON_PATH.read_text(encoding="utf-8"))
        except Exception:
            return []

    def _json_save(self, rows: List[Dict[str, Any]]) -> None:
        _JSON_PATH.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")

    # --- capabilities --------------------------------------------------------
    def write(self, resident_id: str, namespace: str, memory_type: str, content: Dict[str, Any]) -> int:
        """Append one memory record. Returns the new count for this bucket."""
        with self._lock:
            record = {
                "resident_id": resident_id,
                "namespace": namespace,
                "memory_type": memory_type,
                "content": content,
                "created_at": _now(),
            }
            if self.backend == "sqlite" and self._conn is not None:
                try:
                    self._conn.execute(
                        "INSERT INTO memory_entries (resident_id, namespace, memory_type, content, created_at) VALUES (?,?,?,?,?)",
                        (resident_id, namespace, memory_type, json.dumps(content, ensure_ascii=False), record["created_at"]),
                    )
                    self._conn.commit()
                    return self._count(resident_id, namespace, memory_type)
                except Exception:
                    self.backend = "json" if self._try_json() else "mock"
            if self.backend == "json":
                rows = self._json_load()
                rows.append(record)
                self._json_save(rows)
                return self._count(resident_id, namespace, memory_type)
            self._mock.append(record)
            return self._count(resident_id, namespace, memory_type)

    def _matches(self, row: Dict[str, Any], resident_id: str, namespace: str, memory_type: Optional[str]) -> bool:
        if row.get("resident_id") != resident_id or row.get("namespace") != namespace:
            return False
        if memory_type is not None and row.get("memory_type") != memory_type:
            return False
        return True

    def _rows(
        self,
        resident_id: str,
        namespace: str,
        memory_type: Optional[str],
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        if self.backend == "sqlite" and self._conn is not None:
            try:
                if memory_type is None:
                    cur = self._conn.execute(
                        "SELECT memory_type, content, created_at FROM memory_entries WHERE resident_id=? AND namespace=? ORDER BY id",
                        (resident_id, namespace),
                    )
                else:
                    cur = self._conn.execute(
                        "SELECT memory_type, content, created_at FROM memory_entries WHERE resident_id=? AND namespace=? AND memory_type=? ORDER BY id",
                        (resident_id, namespace, memory_type),
                    )
                rows = [
                    {"memory_type": mt, "content": json.loads(content), "created_at": created_at}
                    for (mt, content, created_at) in cur.fetchall()
                ]
                return rows[:limit] if isinstance(limit, int) and limit >= 0 else rows
            except Exception:
                self.backend = "json" if self._try_json() else "mock"
        source = self._json_load() if self.backend == "json" else self._mock
        rows = [
            {"memory_type": r["memory_type"], "content": r["content"], "created_at": r["created_at"]}
            for r in source
            if self._matches(r, resident_id, namespace, memory_type)
        ]
        return rows[:limit] if isinstance(limit, int) and limit >= 0 else rows

    def _count(self, resident_id: str, namespace: str, memory_type: Optional[str]) -> int:
        return len(self._rows(resident_id, namespace, memory_type))

    def read(self, resident_id: str, namespace: str, memory_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """Return the raw content payloads (ordered oldest -> newest)."""
        with self._lock:
            return [row["content"] for row in self._rows(resident_id, namespace, memory_type)]

    def view(
        self,
        resident_id: str,
        namespace: str,
        memory_type: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Return records with metadata (memory_type / content / created_at)."""
        with self._lock:
            rows = self._rows(resident_id, namespace, memory_type, limit=limit)
            return rows if limit is None else rows[:limit]

    def clear(self, resident_id: str, namespace: Optional[str] = None, memory_type: Optional[str] = None) -> int:
        """Delete records for a resident (optionally scoped to ns / type). Returns deleted count."""
        with self._lock:
            if self.backend == "sqlite" and self._conn is not None:
                try:
                    clauses = ["resident_id=?"]
                    params: List[Any] = [resident_id]
                    if namespace is not None:
                        clauses.append("namespace=?")
                        params.append(namespace)
                    if memory_type is not None:
                        clauses.append("memory_type=?")
                        params.append(memory_type)
                    where = " AND ".join(clauses)
                    before = self._conn.execute(f"SELECT COUNT(*) FROM memory_entries WHERE {where}", params).fetchone()[0]
                    self._conn.execute(f"DELETE FROM memory_entries WHERE {where}", params)
                    self._conn.commit()
                    return int(before)
                except Exception:
                    self.backend = "json" if self._try_json() else "mock"

            def keep(row: Dict[str, Any]) -> bool:
                if row.get("resident_id") != resident_id:
                    return True
                if namespace is not None and row.get("namespace") != namespace:
                    return True
                if memory_type is not None and row.get("memory_type") != memory_type:
                    return True
                return False

            if self.backend == "json":
                rows = self._json_load()
                kept = [r for r in rows if keep(r)]
                deleted = len(rows) - len(kept)
                self._json_save(kept)
                return deleted
            kept = [r for r in self._mock if keep(r)]
            deleted = len(self._mock) - len(kept)
            self._mock = kept
            return deleted

    def reset(self) -> None:
        """Test seam: drop all data and re-select the backend (reads current paths)."""
        with self._lock:
            if self._conn is not None:
                try:
                    self._conn.close()
                except Exception:
                    pass
                self._conn = None
            self._mock = []
            try:
                if _SQLITE_PATH.exists():
                    _SQLITE_PATH.unlink()
            except Exception:
                pass
            try:
                if _JSON_PATH.exists():
                    _JSON_PATH.unlink()
            except Exception:
                pass
            self._init_backend()


_STORE = MemoryStore()


def get_memory_store() -> MemoryStore:
    return _STORE


def reset_memory_store() -> None:
    _STORE.reset()
