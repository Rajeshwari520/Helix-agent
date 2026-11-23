"""Audit trail (Week 4): an append-only log of what the AI suggested and what people decided.

There is deliberately no update or delete function: rows are only ever inserted.
Actors: "ai" for model output, "customer:<ref>" for the person who raised a ticket,
and the reviewer's name for human decisions (no login yet; RBAC is planned for Week 10).
"""
import json

from app.db import now_iso

EVENTS = {
    "ticket_created", "ai_triage", "ai_answer_drafted",
    "suggestion_approved", "suggestion_edited", "suggestion_rejected",
    "reply_sent", "ticket_updated", "ticket_deleted",
}


def log(conn, event: str, actor: str, ticket_id: str | None = None,
        suggestion_id: int | None = None, details: dict | None = None, commit: bool = True) -> None:
    if event not in EVENTS:
        raise ValueError(f"unknown audit event {event!r}")
    conn.execute(
        "INSERT INTO audit_log (ticket_id, event, actor, suggestion_id, details, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (ticket_id, event, actor, suggestion_id, json.dumps(details or {}), now_iso()))
    if commit:
        conn.commit()


def _rows(cur) -> list[dict]:
    return [{**dict(r), "details": json.loads(r["details"] or "{}")} for r in cur]


def for_ticket(conn, ticket_id: str) -> list[dict]:
    return _rows(conn.execute("SELECT * FROM audit_log WHERE ticket_id = ? ORDER BY id", (ticket_id,)))


def recent(conn, limit: int = 100, event: str | None = None) -> list[dict]:
    if event:
        return _rows(conn.execute("SELECT * FROM audit_log WHERE event = ? ORDER BY id DESC LIMIT ?", (event, limit)))
    return _rows(conn.execute("SELECT * FROM audit_log ORDER BY id DESC LIMIT ?", (limit,)))
