"""Database access for tickets and AI suggestions (plain SQL, no ORM)."""
import json
from datetime import datetime

from app import config, db
from app.db import now_iso
from app.services.triage import triage as run_triage

UPDATABLE = {"status", "category", "priority", "team", "assignee_id"}


def _row_to_dict(row) -> dict | None:
    if row is None:
        return None
    d = dict(row)
    d["needs_escalation"] = bool(d["needs_escalation"])
    d["escalation_reasons"] = json.loads(d["escalation_reasons"] or "[]")
    d.pop("is_deleted", None)
    return d


def _next_id(conn) -> str:
    row = conn.execute("SELECT id FROM tickets ORDER BY id DESC LIMIT 1").fetchone()
    n = int(row["id"].split("-")[1]) + 1 if row else 1
    return f"TCK-{n:04d}"


def create_ticket(conn, *, subject: str, body: str, channel: str, customer_ref: str,
                  auto_triage: bool = True, ticket_id: str | None = None, created_at: str | None = None) -> dict:
    ts = created_at or now_iso()
    tid = ticket_id or _next_id(conn)
    conn.execute(
        "INSERT INTO tickets (id, customer_ref, channel, subject, body, status, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?, 'New', ?, ?)", (tid, customer_ref, channel, subject, body, ts, ts))
    conn.commit()
    if auto_triage:
        triage_ticket(conn, tid)
    return get_ticket(conn, tid)


def get_ticket(conn, ticket_id: str) -> dict | None:
    row = conn.execute("SELECT * FROM tickets WHERE id = ? AND is_deleted = 0", (ticket_id,)).fetchone()
    return _row_to_dict(row)


def list_tickets(conn, *, status=None, priority=None, team=None, category=None,
                 escalated: bool | None = None, limit: int = 50, offset: int = 0) -> list[dict]:
    sql, args = "SELECT * FROM tickets WHERE is_deleted = 0", []
    for col, val in [("status", status), ("priority", priority), ("team", team), ("category", category)]:
        if val is not None:
            sql += f" AND {col} = ?"
            args.append(val)
    if escalated is not None:
        sql += " AND needs_escalation = ?"
        args.append(int(escalated))
    # Critical first, then oldest first
    sql += (" ORDER BY CASE priority WHEN 'Critical' THEN 0 WHEN 'High' THEN 1 "
            "WHEN 'Medium' THEN 2 WHEN 'Low' THEN 3 ELSE 4 END, created_at LIMIT ? OFFSET ?")
    args += [limit, offset]
    return [_row_to_dict(r) for r in conn.execute(sql, args)]


def update_ticket(conn, ticket_id: str, changes: dict) -> dict | None:
    changes = {k: v for k, v in changes.items() if k in UPDATABLE and v is not None}
    if get_ticket(conn, ticket_id) is None:
        return None
    if changes:
        cols = ", ".join(f"{k} = ?" for k in changes)
        conn.execute(f"UPDATE tickets SET {cols}, updated_at = ? WHERE id = ?",
                     [*changes.values(), now_iso(), ticket_id])
        conn.commit()
    return get_ticket(conn, ticket_id)


def delete_ticket(conn, ticket_id: str) -> bool:
    """Soft delete: the row is kept for audit purposes."""
    cur = conn.execute("UPDATE tickets SET is_deleted = 1, updated_at = ? WHERE id = ? AND is_deleted = 0",
                       (now_iso(), ticket_id))
    conn.commit()
    return cur.rowcount == 1


def triage_ticket(conn, ticket_id: str) -> dict | None:
    t = get_ticket(conn, ticket_id)
    if t is None:
        return None
    # SLA clock starts when the ticket was CREATED, not when triage runs
    result = run_triage(t["subject"], t["body"], datetime.fromisoformat(t["created_at"]))
    status = "Escalated" if result["needs_escalation"] else "Triaged"
    conn.execute(
        "UPDATE tickets SET category = ?, priority = ?, team = ?, needs_escalation = ?, escalation_reasons = ?, "
        "sla_first_response_due = ?, sla_resolution_due = ?, status = ?, updated_at = ? WHERE id = ?",
        (result["category"], result["priority"], result["team"], int(result["needs_escalation"]),
         json.dumps(result["escalation_reasons"]), result["sla"]["first_response_due"],
         result["sla"]["resolution_due"], status, now_iso(), ticket_id))
    save_suggestion(conn, ticket_id, "triage", result, result["model_version"], result["latency_ms"])
    return result


def save_suggestion(conn, ticket_id: str, kind: str, payload: dict, model_version: str, latency_ms: float):
    conn.execute(
        "INSERT INTO ai_suggestions (ticket_id, kind, payload, model_version, latency_ms, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?)", (ticket_id, kind, json.dumps(payload), model_version, latency_ms, now_iso()))
    conn.commit()


def list_suggestions(conn, ticket_id: str) -> list[dict]:
    rows = conn.execute("SELECT * FROM ai_suggestions WHERE ticket_id = ? ORDER BY id", (ticket_id,))
    return [{**dict(r), "payload": json.loads(r["payload"])} for r in rows]


def seed_tickets_from_csv(conn, csv_path=None) -> int:
    """Load data/tickets.csv into an empty database (demo data)."""
    import csv
    if db.count(conn, "tickets"):
        return 0
    with open(csv_path or config.domain().data_dir / "tickets.csv", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        create_ticket(conn, subject=r["subject"], body=r["body"], channel=r["channel"],
                      customer_ref=r["customer_id"], ticket_id=r["ticket_id"],
                      created_at=r["created_at"].replace(" ", "T") + ":00+00:00")
    return len(rows)
