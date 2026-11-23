"""Dashboard numbers (Week 3+): one call returns everything the dashboard page shows.

Read-only. Works on PostgreSQL and SQLite (plain SQL + Python counting).
"""
import json
from collections import Counter
from datetime import datetime, timedelta, timezone

from app import config
from app.services import knowledge, review

OPEN_STATUSES = {"New", "Triaged", "Assigned", "Escalated", "In Progress"}
PRIORITY_ORDER = ["Critical", "High", "Medium", "Low"]
DUE_SOON_HOURS = 4
METRIC_FILES = {
    "classifier": "test_set_after.json",       # frozen test set results
    "baseline": "test_set_week1_rules.json",   # Week 1 keyword rules on the same set
    "rag": "week3_rag_scorecard.json",
}


def _parse(ts: str | None):
    if not ts:
        return None
    d = datetime.fromisoformat(ts)
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def sla_state(ticket: dict, now: datetime) -> str:
    """breached / due_soon / on_track / closed, based on the first-response deadline."""
    if ticket["status"] not in OPEN_STATUSES:
        return "closed"
    due = _parse(ticket.get("sla_first_response_due"))
    if due is None:
        return "on_track"
    if due < now:
        return "breached"
    if due < now + timedelta(hours=DUE_SOON_HOURS):
        return "due_soon"
    return "on_track"


def _latest_triage(conn) -> dict:
    """ticket_id -> latest triage suggestion payload."""
    latest = {}
    for r in conn.execute("SELECT ticket_id, payload FROM ai_suggestions WHERE kind = 'triage' ORDER BY id"):
        latest[r["ticket_id"]] = json.loads(r["payload"])
    return latest


def _metrics() -> dict:
    out = {}
    folder = config.ROOT / "docs" / config.domain().name
    for key, name in METRIC_FILES.items():
        path = folder / name
        if path.exists():
            out[key] = json.loads(path.read_text(encoding="utf-8"))
    return out


def demo_clock(conn) -> datetime | None:
    """1 hour after the newest ticket. The seeded demo tickets are dated early Nov 2026,
    so against the real clock every one of them is already past its SLA."""
    row = conn.execute("SELECT MAX(created_at) AS m FROM tickets WHERE is_deleted = 0").fetchone()
    return _parse(row["m"]) + timedelta(hours=1) if row and row["m"] else None


def resolve_clock(conn, clock: str = "now", now: datetime | None = None) -> tuple[str, datetime]:
    if now is None and clock == "demo":
        now = demo_clock(conn)
    if now is None:
        return "now", datetime.now(timezone.utc)
    return clock, now


def ticket_rows(conn, now: datetime) -> list[dict]:
    """Every ticket (not deleted) with its SLA state, AI confidence and pending human decisions."""
    rows = [dict(r) for r in conn.execute("SELECT * FROM tickets WHERE is_deleted = 0")]
    triage = _latest_triage(conn)
    waiting = review.pending(conn)
    out = []
    for t in rows:
        p = triage.get(t["id"], {})
        out.append({
            "id": t["id"], "subject": t["subject"], "status": t["status"],
            "category": t["category"], "priority": t["priority"], "team": t["team"],
            "channel": t["channel"], "created_at": t["created_at"], "updated_at": t["updated_at"],
            "sla_first_response_due": t["sla_first_response_due"],
            "escalated": bool(t["needs_escalation"]),
            "escalation_reasons": json.loads(t["escalation_reasons"] or "[]"),
            "confidence": p.get("category_confidence"),
            "needs_review": bool(p.get("needs_human_review")),
            "pending_decisions": waiting.get(t["id"], 0),
            "sla": sla_state(t, now),
        })
    return out


PRIORITY_RANK = {p: i for i, p in enumerate(PRIORITY_ORDER)}


def queue(conn, clock: str = "now", include_closed: bool = False) -> dict:
    """Agent queue: open tickets (or all), most urgent first, then oldest first."""
    clock, now = resolve_clock(conn, clock)
    rows = [t for t in ticket_rows(conn, now) if include_closed or t["status"] in OPEN_STATUSES]
    rows.sort(key=lambda t: (PRIORITY_RANK.get(t["priority"], 9), t["created_at"]))
    return {"sla_clock": {"mode": clock, "as_of": now.replace(microsecond=0).isoformat()}, "tickets": rows}


def stats(conn, now: datetime | None = None, clock: str = "now") -> dict:
    """clock='now' uses the real time; clock='demo' uses demo_clock() (labelled in the response)."""
    clock, now = resolve_clock(conn, clock, now)
    tickets = ticket_rows(conn, now)

    open_t = [t for t in tickets if t["status"] in OPEN_STATUSES]
    rank = {p: i for i, p in enumerate(PRIORITY_ORDER)}
    ordered = sorted(open_t, key=lambda t: (rank.get(t["priority"], 9), t["created_at"]))
    sla = Counter(t["sla"] for t in open_t)
    confs = [t["confidence"] for t in tickets if t["confidence"] is not None]

    return {
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "sla_clock": {"mode": clock, "as_of": now.replace(microsecond=0).isoformat()},
        "domain": config.domain().name,
        "kpis": {
            "total": len(tickets),
            "open": len(open_t),
            "escalated": sum(t["escalated"] for t in open_t),
            "needs_review": sum(t["needs_review"] for t in open_t),
            "awaiting_decision": sum(t["pending_decisions"] > 0 for t in open_t),
            "sla_breached": sla.get("breached", 0),
            "sla_due_soon": sla.get("due_soon", 0),
            "avg_confidence": round(sum(confs) / len(confs), 2) if confs else None,
        },
        "by_priority": {p: sum(t["priority"] == p for t in tickets) for p in PRIORITY_ORDER},
        "by_category": dict(Counter(t["category"] or "Untriaged" for t in tickets).most_common()),
        "by_team": dict(Counter(t["team"] or "Unassigned" for t in tickets).most_common()),
        "by_status": dict(Counter(t["status"] for t in tickets).most_common()),
        "by_channel": dict(Counter(t["channel"] for t in tickets).most_common()),
        "sla": {k: sla.get(k, 0) for k in ("breached", "due_soon", "on_track")},
        "escalation_reasons": dict(Counter(r for t in open_t for r in t["escalation_reasons"]).most_common()),
        "knowledge": {"corpus_version": knowledge.corpus_version(conn),
                      "approved_faqs": len(knowledge.current_faqs(conn))},
        "model_metrics": _metrics(),
        "human_decisions": review.counts(conn),
        "queue": ordered[:200],
    }
