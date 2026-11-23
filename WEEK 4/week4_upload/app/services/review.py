"""Human review of AI suggestions (Week 4): approve, edit or reject.

Rules (these are what make "human in the loop" real, not just a label):
  * Every AI suggestion can be decided once, and only the newest suggestion of its kind
    for a ticket can be decided (an older one was replaced by a re-run).
  * Triage  - approve keeps the AI's category/priority/team; edit changes them on the ticket;
              reject records that the AI was wrong (a reason is required).
  * Answer  - approve sends the AI draft; edit sends the reviewer's text instead (this is also how
              a person writes a reply when the AI refused or escalated); reject sends nothing
              (a reason is required).
  * "Sending" is simulated in this prototype: the reply is stored and logged, no email goes out.
  * Every decision is written to suggestion_reviews and the audit log with the reviewer's name.
"""
import json

from app import config, repository
from app.db import now_iso
from app.services import audit, rag

DECISIONS = {"approve": "approved", "edit": "edited", "reject": "rejected"}
REPLY_STATUS = "Waiting on Customer"  # after a reply is sent
MIN_REPLY = 5


class ReviewError(Exception):
    """Bad request (422)."""


class NotFound(ReviewError):
    """Ticket or suggestion does not exist (404)."""


class Conflict(ReviewError):
    """Already decided or out of date (409)."""


def draft_answer(conn, ticket_id: str, retriever, corpus_version: str) -> dict | None:
    """AI drafts a reply from approved FAQs. It is stored as a suggestion and never sent here."""
    ticket = repository.get_ticket(conn, ticket_id)
    if ticket is None:
        return None
    result = rag.answer(f"{ticket['subject']}. {ticket['body']}", retriever, corpus_version)
    sid = repository.save_suggestion(conn, ticket_id, "answer", result,
                                     f"{result['retriever_version']}|{corpus_version}", result["latency_ms"])
    audit.log(conn, "ai_answer_drafted", "ai", ticket_id, sid, {
        "status": result["status"], "confidence": result["confidence"],
        "citations": [f"{c['faq_id']} v{c['version']}" for c in result["citations"]],
        "corpus_version": corpus_version})
    if result["escalate"] and not ticket["needs_escalation"]:
        repository.update_ticket(conn, ticket_id, {"status": "Escalated"}, actor="ai")
    return {"ticket_id": ticket_id, "suggestion_id": sid, **result}


def _suggestion(conn, ticket_id: str, suggestion_id: int) -> dict:
    row = conn.execute("SELECT * FROM ai_suggestions WHERE id = ? AND ticket_id = ?",
                       (suggestion_id, ticket_id)).fetchone()
    if row is None:
        raise NotFound(f"Suggestion {suggestion_id} not found on ticket {ticket_id}")
    return {**dict(row), "payload": json.loads(row["payload"])}


def _check_triage_edit(edits: dict) -> dict:
    out = {}
    if edits.get("category") is not None:
        if edits["category"] not in config.domain().categories:
            raise ReviewError(f"category must be one of {config.domain().categories}")
        out["category"] = edits["category"]
    if edits.get("priority") is not None:
        if edits["priority"] not in config.PRIORITIES:
            raise ReviewError(f"priority must be one of {config.PRIORITIES}")
        out["priority"] = edits["priority"]
    if edits.get("team") is not None:
        teams = set(config.domain().teams.values()) | {config.ESCALATION_TEAM}
        if edits["team"] not in teams:
            raise ReviewError(f"team must be one of {sorted(teams)}")
        out["team"] = edits["team"]
    return out


def review(conn, ticket_id: str, suggestion_id: int, decision: str, reviewer: str, *,
           category: str | None = None, priority: str | None = None, team: str | None = None,
           reply: str | None = None, reason: str | None = None) -> dict:
    """Record a human decision on one AI suggestion and apply it. Returns the review + updated ticket."""
    if decision not in DECISIONS:
        raise ReviewError(f"decision must be one of {sorted(DECISIONS)}")
    reviewer = (reviewer or "").strip()
    if len(reviewer) < 2:
        raise ReviewError("reviewer name is required")
    reason = (reason or "").strip() or None

    ticket = repository.get_ticket(conn, ticket_id)
    if ticket is None:
        raise NotFound(f"Ticket {ticket_id} not found")
    sugg = _suggestion(conn, ticket_id, suggestion_id)
    if conn.execute("SELECT 1 FROM suggestion_reviews WHERE suggestion_id = ?", (suggestion_id,)).fetchone():
        raise Conflict(f"Suggestion {suggestion_id} has already been reviewed")
    newest = conn.execute("SELECT MAX(id) AS m FROM ai_suggestions WHERE ticket_id = ? AND kind = ?",
                          (ticket_id, sugg["kind"])).fetchone()["m"]
    if suggestion_id != newest:
        raise Conflict(f"Suggestion {suggestion_id} is out of date; review the newest {sugg['kind']} suggestion")
    if decision == "reject" and not reason:
        raise ReviewError("a reason is required to reject a suggestion")

    p = sugg["payload"]
    changes, final, sent_reply = {}, None, None
    if sugg["kind"] == "triage":
        ai = {"category": p["category"], "priority": p["priority"], "team": p["team"]}
        if decision == "approve":
            final = ai
        elif decision == "edit":
            changes = _check_triage_edit({"category": category, "priority": priority, "team": team})
            changes = {k: v for k, v in changes.items() if ai.get(k) != v or ticket.get(k) != v}
            if not changes:
                raise ReviewError("edit needs at least one change to category, priority or team")
            final = {**ai, **changes}
        else:
            final = None
    else:  # answer
        if decision == "approve":
            if not p.get("draft_reply"):
                raise ReviewError(f"there is no AI draft to approve (AI status: {p.get('status')}); "
                                  "use edit to write the reply yourself, or reject")
            sent_reply = p["draft_reply"]
        elif decision == "edit":
            sent_reply = (reply or "").strip()
            if len(sent_reply) < MIN_REPLY:
                raise ReviewError("edit needs the reply text you want to send")
        if sent_reply:
            final = {"reply": sent_reply, "ai_draft_used": decision == "approve",
                     "citations": [f"{c['faq_id']} v{c['version']}" for c in p.get("citations", [])]}

    stored = DECISIONS[decision]
    conn.execute(
        "INSERT INTO suggestion_reviews (suggestion_id, ticket_id, kind, decision, reviewer, final_payload, reason, "
        "created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (suggestion_id, ticket_id, sugg["kind"], stored, reviewer,
         json.dumps(final) if final is not None else None, reason, now_iso()))
    audit.log(conn, f"suggestion_{stored}", reviewer, ticket_id, suggestion_id,
              {"kind": sugg["kind"], "reason": reason,
               **({"changes": changes} if changes else {})}, commit=False)
    conn.commit()

    if changes:
        repository.update_ticket(conn, ticket_id, changes, actor=reviewer)
    if sent_reply:
        audit.log(conn, "reply_sent", reviewer, ticket_id, suggestion_id,
                  {"simulated": True, "ai_draft_used": decision == "approve", "chars": len(sent_reply)})
        repository.update_ticket(conn, ticket_id, {"status": REPLY_STATUS}, actor=reviewer)

    return {"ticket_id": ticket_id, "suggestion_id": suggestion_id, "kind": sugg["kind"], "decision": stored,
            "reviewer": reviewer, "final": final, "reason": reason, "reply_sent": bool(sent_reply),
            "ticket": repository.get_ticket(conn, ticket_id)}


def counts(conn) -> dict:
    """How often people approve / edit / reject the AI, per kind (used by the dashboard)."""
    out = {k: {"approved": 0, "edited": 0, "rejected": 0} for k in ("triage", "answer")}
    for r in conn.execute("SELECT kind, decision, COUNT(*) AS n FROM suggestion_reviews GROUP BY kind, decision"):
        out[r["kind"]][r["decision"]] = r["n"]
    return out


def pending(conn) -> dict[str, int]:
    """ticket_id -> number of newest suggestions (triage / answer) still waiting for a decision."""
    rows = conn.execute(
        "SELECT s.ticket_id, COUNT(*) AS n FROM ai_suggestions s "
        "JOIN (SELECT ticket_id, kind, MAX(id) AS id FROM ai_suggestions GROUP BY ticket_id, kind) latest "
        "  ON latest.id = s.id "
        "LEFT JOIN suggestion_reviews r ON r.suggestion_id = s.id "
        "WHERE r.id IS NULL GROUP BY s.ticket_id")
    return {r["ticket_id"]: r["n"] for r in rows}
