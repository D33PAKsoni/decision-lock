"""SQLite records only human-locked verdicts; retries are idempotent."""

import json
import sqlite3
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

from .models import AgentReply


class StorageError(RuntimeError):
    """Friendly storage failure with no private data in its message."""


class DecisionStore:
    def __init__(self, path: Path | str):
        self.path = Path(path)

    @contextmanager
    def _connection(self):
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            connection = sqlite3.connect(self.path, timeout=5)
            connection.row_factory = sqlite3.Row
            try:
                connection.execute("PRAGMA foreign_keys = ON")
                with connection:
                    yield connection
            finally:
                connection.close()
        except (sqlite3.Error, OSError):
            raise StorageError(
                "Local storage is unavailable. Check the data folder permissions."
            ) from None

    def initialize(self) -> None:
        with self._connection() as connection:
            connection.executescript("""
                CREATE TABLE IF NOT EXISTS decisions (
                    id INTEGER PRIMARY KEY,
                    lock_token TEXT NOT NULL UNIQUE,
                    created_at TEXT NOT NULL,
                    user_problem TEXT NOT NULL,
                    recommendation TEXT NOT NULL,
                    next_action TEXT NOT NULL,
                    reasoning_summary TEXT NOT NULL,
                    provider TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS feedback (
                    id INTEGER PRIMARY KEY,
                    decision_id INTEGER NOT NULL UNIQUE REFERENCES decisions(id),
                    helpful INTEGER NOT NULL CHECK(helpful IN (0, 1)),
                    created_at TEXT NOT NULL
                );
            """)

    def lock(self, token: str, problem: str, reply: AgentReply, provider: str) -> int:
        if reply.kind != "recommendation":
            raise ValueError("Only a completed recommendation can be locked.")
        if not token or not problem.strip() or not provider.strip():
            raise ValueError("A lock needs a token, problem and provider.")
        with self._connection() as connection:
            connection.execute(
                """
                INSERT INTO decisions
                    (lock_token, created_at, user_problem, recommendation,
                     next_action, reasoning_summary, provider)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(lock_token) DO NOTHING
            """,
                (
                    token,
                    datetime.now(UTC).isoformat(),
                    problem,
                    reply.recommendation,
                    reply.next_action,
                    json.dumps({"reasons": reply.reasons, "assumptions": reply.assumptions}),
                    provider,
                ),
            )
            row = connection.execute(
                "SELECT id FROM decisions WHERE lock_token = ?", (token,)
            ).fetchone()
            return int(row["id"])

    def recent(self, limit: int = 5) -> list[dict]:
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 10:
            raise ValueError("History limit must be an integer between 1 and 10.")
        with self._connection() as connection:
            rows = connection.execute(
                """
                SELECT d.id, d.created_at, d.user_problem, d.recommendation, d.next_action,
                       d.reasoning_summary, d.provider, f.helpful
                FROM decisions d LEFT JOIN feedback f ON f.decision_id = d.id
                ORDER BY d.id DESC LIMIT ?
            """,
                (limit,),
            ).fetchall()
            return [dict(row) for row in rows]

    def feedback(self, decision_id: int, helpful: bool) -> None:
        if type(helpful) is not bool:
            raise ValueError("Feedback must be true or false.")
        with self._connection() as connection:
            if not connection.execute(
                "SELECT 1 FROM decisions WHERE id = ?", (decision_id,)
            ).fetchone():
                raise ValueError("Feedback needs an existing locked decision.")
            connection.execute(
                """
                INSERT INTO feedback (decision_id, helpful, created_at) VALUES (?, ?, ?)
                ON CONFLICT(decision_id) DO UPDATE SET
                    helpful = excluded.helpful, created_at = excluded.created_at
            """,
                (decision_id, int(helpful), datetime.now(UTC).isoformat()),
            )
