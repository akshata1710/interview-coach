"""Sessions persisted as JSON documents in SQLite: simple, durable, and easy to swap for Postgres."""
from __future__ import annotations

import json
import sqlite3
import threading
from pathlib import Path
from typing import Any


class Store:
    def __init__(self, path: Path):
        self._lock = threading.Lock()
        self._db = sqlite3.connect(path, check_same_thread=False)
        self._db.execute(
            "CREATE TABLE IF NOT EXISTS sessions (id TEXT PRIMARY KEY, created_at REAL, doc TEXT NOT NULL)"
        )
        self._db.commit()

    def put(self, doc: dict[str, Any]) -> None:
        with self._lock:
            self._db.execute(
                "INSERT INTO sessions (id, created_at, doc) VALUES (?, ?, ?) "
                "ON CONFLICT(id) DO UPDATE SET doc = excluded.doc",
                (doc["id"], doc["created_at"], json.dumps(doc)),
            )
            self._db.commit()

    def get(self, session_id: str) -> dict[str, Any] | None:
        with self._lock:
            row = self._db.execute("SELECT doc FROM sessions WHERE id = ?", (session_id,)).fetchone()
        return json.loads(row[0]) if row else None

    def recent(self, limit: int = 20) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._db.execute(
                "SELECT doc FROM sessions ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
        return [json.loads(r[0]) for r in rows]
