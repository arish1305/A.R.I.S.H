from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Iterator


@dataclass(frozen=True)
class MemoryRecord:
    id: int
    content: str
    tags: str
    created_at: str
    updated_at: str


@dataclass(frozen=True)
class MessageRecord:
    id: int
    session_id: str
    role: str
    content: str
    created_at: str


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class MemoryStore:
    def __init__(self, db_path: Path | str) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    @contextmanager
    def _session(self) -> Iterator[sqlite3.Connection]:
        connection = self._connect()
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

    def _initialize(self) -> None:
        with self._session() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    content TEXT NOT NULL,
                    tags TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_messages_session_created
                    ON messages(session_id, created_at);
                CREATE INDEX IF NOT EXISTS idx_memories_content
                    ON memories(content);
                """
            )

    def add_memory(self, content: str, tags: Iterable[str] | None = None) -> MemoryRecord:
        clean_content = " ".join(content.strip().split())
        if not clean_content:
            raise ValueError("Memory content cannot be empty.")

        tag_string = ",".join(tag.strip() for tag in tags or [] if tag.strip())
        now = _utc_now()
        with self._session() as connection:
            cursor = connection.execute(
                """
                INSERT INTO memories(content, tags, created_at, updated_at)
                VALUES (?, ?, ?, ?)
                """,
                (clean_content, tag_string, now, now),
            )
            memory_id = int(cursor.lastrowid)
        return MemoryRecord(memory_id, clean_content, tag_string, now, now)

    def list_memories(self, limit: int = 50) -> list[MemoryRecord]:
        with self._session() as connection:
            rows = connection.execute(
                """
                SELECT id, content, tags, created_at, updated_at
                FROM memories
                ORDER BY updated_at DESC, id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [self._memory_from_row(row) for row in rows]

    def search_memories(self, query: str, limit: int = 5) -> list[MemoryRecord]:
        terms = [term for term in query.strip().split() if len(term) > 2]
        if not terms:
            return self.list_memories(limit=limit)

        clauses = " OR ".join("content LIKE ?" for _ in terms)
        params = [f"%{term}%" for term in terms]
        params.append(limit)

        with self._session() as connection:
            rows = connection.execute(
                f"""
                SELECT id, content, tags, created_at, updated_at
                FROM memories
                WHERE {clauses}
                ORDER BY updated_at DESC, id DESC
                LIMIT ?
                """,
                params,
            ).fetchall()
        return [self._memory_from_row(row) for row in rows]

    def delete_memory(self, memory_id: int) -> bool:
        with self._session() as connection:
            cursor = connection.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
            return cursor.rowcount > 0

    def add_message(self, session_id: str, role: str, content: str) -> MessageRecord:
        if role not in {"user", "assistant", "system"}:
            raise ValueError("Message role must be user, assistant, or system.")
        clean_content = content.strip()
        if not clean_content:
            raise ValueError("Message content cannot be empty.")

        now = _utc_now()
        with self._session() as connection:
            cursor = connection.execute(
                """
                INSERT INTO messages(session_id, role, content, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (session_id, role, clean_content, now),
            )
            message_id = int(cursor.lastrowid)
        return MessageRecord(message_id, session_id, role, clean_content, now)

    def recent_messages(self, session_id: str, limit: int = 12) -> list[MessageRecord]:
        with self._session() as connection:
            rows = connection.execute(
                """
                SELECT id, session_id, role, content, created_at
                FROM messages
                WHERE session_id = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (session_id, limit),
            ).fetchall()

        messages = [self._message_from_row(row) for row in rows]
        messages.reverse()
        return messages

    def clear_session(self, session_id: str) -> int:
        with self._session() as connection:
            cursor = connection.execute(
                "DELETE FROM messages WHERE session_id = ?", (session_id,)
            )
            return cursor.rowcount

    @staticmethod
    def _memory_from_row(row: sqlite3.Row) -> MemoryRecord:
        return MemoryRecord(
            id=int(row["id"]),
            content=str(row["content"]),
            tags=str(row["tags"]),
            created_at=str(row["created_at"]),
            updated_at=str(row["updated_at"]),
        )

    @staticmethod
    def _message_from_row(row: sqlite3.Row) -> MessageRecord:
        return MessageRecord(
            id=int(row["id"]),
            session_id=str(row["session_id"]),
            role=str(row["role"]),
            content=str(row["content"]),
            created_at=str(row["created_at"]),
        )
