"""SQLite-backed store for captures. Audio bytes go to files under data/audio/,
metadata to a single SQLite database at data/captures.db. Both are disposable:
deleting the data/ directory resets all state.
"""

from __future__ import annotations

import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS captures (
    id INTEGER PRIMARY KEY,
    created_at TEXT NOT NULL,
    audio_path TEXT NOT NULL,
    mime TEXT NOT NULL,
    transcript TEXT,
    class TEXT CHECK(class IN ('idea','task','lead','noise'))
);
"""


@dataclass
class CaptureRow:
    id: int
    created_at: str
    audio_path: str
    mime: str
    transcript: str | None
    cls: str | None


class CaptureStore:
    def __init__(self, db_path: Path, audio_dir: Path) -> None:
        self.db_path = db_path
        self.audio_dir = audio_dir

    def _conn(self) -> sqlite3.Connection:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init(self) -> None:
        with self._conn() as conn:
            conn.executescript(SCHEMA)

    def save_audio(self, audio: bytes, mime: str) -> str:
        self.audio_dir.mkdir(parents=True, exist_ok=True)
        suffix = ".webm" if "webm" in mime else ".m4a" if "mp4" in mime else ".bin"
        name = f"{uuid.uuid4().hex}{suffix}"
        (self.audio_dir / name).write_bytes(audio)
        return f"audio/{name}"

    def add(self, audio_path: str, mime: str, transcript: str | None, cls: str | None) -> int:
        created = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with self._conn() as conn:
            cur = conn.execute(
                "INSERT INTO captures (created_at, audio_path, mime, transcript, class)"
                " VALUES (?, ?, ?, ?, ?)",
                (created, audio_path, mime, transcript, cls),
            )
            return int(cur.lastrowid)

    def get(self, id: int) -> CaptureRow | None:
        with self._conn() as conn:
            row = conn.execute("SELECT * FROM captures WHERE id = ?", (id,)).fetchone()
        return _to_row(row) if row else None

    def list(self, limit: int = 50) -> list[CaptureRow]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM captures ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
        return [_to_row(r) for r in rows]


def _to_row(r: sqlite3.Row) -> CaptureRow:
    return CaptureRow(
        id=r["id"],
        created_at=r["created_at"],
        audio_path=r["audio_path"],
        mime=r["mime"],
        transcript=r["transcript"],
        cls=r["class"],
    )
