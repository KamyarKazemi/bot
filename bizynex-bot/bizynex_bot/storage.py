"""SQLite lead storage.

The admin DM is the primary delivery channel; this file is the safety net. If
Telegram is unreachable at the moment of submission — a real possibility on an
Iranian connection — the lead is still on disk and can be re-sent.
"""

from __future__ import annotations

import json
import secrets
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator

from .localization import jalali_stamp, now_iran

_SCHEMA = """
CREATE TABLE IF NOT EXISTS leads (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    ticket        TEXT NOT NULL UNIQUE,
    user_id       INTEGER NOT NULL,
    username      TEXT,
    full_name     TEXT,
    service       TEXT,
    phone         TEXT,
    answers_json  TEXT NOT NULL,
    created_at    TEXT NOT NULL,
    created_jalali TEXT NOT NULL,
    delivered     INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_leads_user ON leads(user_id);
CREATE INDEX IF NOT EXISTS idx_leads_delivered ON leads(delivered);

CREATE TABLE IF NOT EXISTS followups (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    ticket     TEXT NOT NULL,
    user_id    INTEGER NOT NULL,
    body       TEXT NOT NULL,
    created_at TEXT NOT NULL
);
"""

_TICKET_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # no look-alike characters


class LeadStore:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.executescript(_SCHEMA)

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.path, timeout=10)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    # -- tickets -----------------------------------------------------------
    def new_ticket(self, when: datetime | None = None) -> str:
        """BZX-14050512-K7QF — Jalali date makes it readable at a glance."""
        stamp = jalali_stamp(when)
        for _ in range(20):
            suffix = "".join(secrets.choice(_TICKET_ALPHABET) for _ in range(4))
            ticket = f"BZX-{stamp}-{suffix}"
            with self._connect() as conn:
                exists = conn.execute(
                    "SELECT 1 FROM leads WHERE ticket = ?", (ticket,)
                ).fetchone()
            if not exists:
                return ticket
        raise RuntimeError("could not allocate a unique ticket")

    # -- writes ------------------------------------------------------------
    def save_lead(
        self,
        *,
        ticket: str,
        user: dict[str, Any],
        answers: dict[str, Any],
        delivered: bool = False,
    ) -> None:
        created = now_iran()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO leads
                    (ticket, user_id, username, full_name, service, phone,
                     answers_json, created_at, created_jalali, delivered)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(ticket) DO UPDATE SET
                    answers_json = excluded.answers_json,
                    delivered    = excluded.delivered
                """,
                (
                    ticket,
                    int(user.get("id", 0)),
                    user.get("username"),
                    user.get("full_name"),
                    str(answers.get("service", "")),
                    str(answers.get("t_phone", "")),
                    json.dumps(answers, ensure_ascii=False),
                    created.isoformat(),
                    jalali_stamp(created),
                    1 if delivered else 0,
                ),
            )

    def mark_delivered(self, ticket: str) -> None:
        with self._connect() as conn:
            conn.execute("UPDATE leads SET delivered = 1 WHERE ticket = ?", (ticket,))

    def save_followup(self, *, ticket: str, user_id: int, body: str) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO followups (ticket, user_id, body, created_at) VALUES (?, ?, ?, ?)",
                (ticket, int(user_id), body, now_iran().isoformat()),
            )

    # -- reads -------------------------------------------------------------
    def undelivered(self) -> list[sqlite3.Row]:
        with self._connect() as conn:
            return list(conn.execute("SELECT * FROM leads WHERE delivered = 0 ORDER BY id"))

    def stats(self) -> dict[str, int]:
        today = jalali_stamp()
        with self._connect() as conn:
            total = conn.execute("SELECT COUNT(*) FROM leads").fetchone()[0]
            today_count = conn.execute(
                "SELECT COUNT(*) FROM leads WHERE created_jalali = ?", (today,)
            ).fetchone()[0]
            pending = conn.execute(
                "SELECT COUNT(*) FROM leads WHERE delivered = 0"
            ).fetchone()[0]
        return {"total": total, "today": today_count, "pending": pending}

    def by_service(self) -> list[tuple[str, int]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT service, COUNT(*) AS n FROM leads GROUP BY service ORDER BY n DESC"
            ).fetchall()
        return [(row["service"] or "—", row["n"]) for row in rows]
