"""Week 4 — human review (approve / edit / reject) of AI suggestions and the audit trail."""
from datetime import datetime, timedelta

import pytest

from app import config, repository
from app.services import audit, dashboard, review


@pytest.fixture
def ticket(conn):
    """A fresh, auto-triaged ticket: (ticket, triage suggestion)."""
    t = repository.create_ticket(conn, subject="Forgot LMS password",
                                 body="I forgot my LMS portal password and the reset mail is not coming.",
                                 channel="email", customer_ref="EMP-1")
    tri = [s for s in repository.list_suggestions(conn, t["id"]) if s["kind"] == "triage"][-1]
    return t, tri


def events(conn, tid):
    return [e["event"] for e in audit.for_ticket(conn, tid)]


# ---------- triage ----------
def test_approve_triage_keeps_ai_values(conn, ticket):
    t, tri = ticket
    out = review.review(conn, t["id"], tri["id"], "approve", "Raj")
    assert out["decision"] == "approved" and out["final"]["category"] == t["category"]
    after = repository.get_ticket(conn, t["id"])
    assert (after["category"], after["priority"], after["team"]) == (t["category"], t["priority"], t["team"])
    assert events(conn, t["id"])[-1] == "suggestion_approved"


def test_edit_triage_changes_ticket_and_moves_sla(conn, ticket):
    t, tri = ticket
    out = review.review(conn, t["id"], tri["id"], "edit", "Raj", priority="Critical", reason="exam today")
    after = out["ticket"]
    assert after["priority"] == "Critical"
    due = datetime.fromisoformat(after["created_at"]) + timedelta(hours=config.SLA_HOURS["Critical"][0])
    assert datetime.fromisoformat(after["sla_first_response_due"]) == due
    trail = audit.for_ticket(conn, t["id"])
    assert trail[-2]["event"] == "suggestion_edited" and trail[-2]["details"]["changes"] == {"priority": "Critical"}
    assert trail[-1]["event"] == "ticket_updated" and trail[-1]["details"]["priority"]["from"] == t["priority"]
    assert all(e["actor"] == "Raj" for e in trail[-2:])


def test_edit_triage_needs_a_real_change(conn, ticket):
    t, tri = ticket
    with pytest.raises(review.ReviewError):
        review.review(conn, t["id"], tri["id"], "edit", "Raj", category=t["category"])


@pytest.mark.parametrize("field,value", [("category", "Delivery"), ("priority", "Urgent"), ("team", "Nobody")])
def test_edit_triage_rejects_unknown_values(conn, ticket, field, value):
    t, tri = ticket
    with pytest.raises(review.ReviewError):
        review.review(conn, t["id"], tri["id"], "edit", "Raj", **{field: value})


def test_reject_needs_a_reason(conn, ticket):
    t, tri = ticket
    with pytest.raises(review.ReviewError):
        review.review(conn, t["id"], tri["id"], "reject", "Raj")
    out = review.review(conn, t["id"], tri["id"], "reject", "Raj", reason="wrong team")
    assert out["decision"] == "rejected" and out["final"] is None


def test_reviewer_name_is_required(conn, ticket):
    t, tri = ticket
    with pytest.raises(review.ReviewError):
        review.review(conn, t["id"], tri["id"], "approve", " ")


def test_cannot_decide_twice(conn, ticket):
    t, tri = ticket
    review.review(conn, t["id"], tri["id"], "approve", "Raj")
    with pytest.raises(review.Conflict):
        review.review(conn, t["id"], tri["id"], "reject", "Someone else", reason="changed my mind")


def test_unknown_suggestion_or_ticket(conn, ticket):
    t, tri = ticket
    with pytest.raises(review.NotFound):
        review.review(conn, t["id"], 999999, "approve", "Raj")
    with pytest.raises(review.NotFound):
        review.review(conn, "TCK-9999", tri["id"], "approve", "Raj")


# ---------- replies ----------
def test_ai_draft_is_never_sent_on_its_own(conn, ticket, retriever):
    t, _ = ticket
    ans = review.draft_answer(conn, t["id"], *retriever)
    assert ans["status"] == "answered" and ans["draft_reply"]
    assert "reply_sent" not in events(conn, t["id"])
    assert repository.get_ticket(conn, t["id"])["status"] != review.REPLY_STATUS


def test_approve_reply_sends_the_ai_draft(conn, ticket, retriever):
    t, _ = ticket
    ans = review.draft_answer(conn, t["id"], *retriever)
    out = review.review(conn, t["id"], ans["suggestion_id"], "approve", "Raj")
    assert out["reply_sent"] and out["final"]["reply"] == ans["draft_reply"] and out["final"]["ai_draft_used"]
    assert out["ticket"]["status"] == review.REPLY_STATUS
    sent = [e for e in audit.for_ticket(conn, t["id"]) if e["event"] == "reply_sent"]
    assert len(sent) == 1 and sent[0]["details"]["simulated"] is True


def test_edit_reply_sends_the_person_text(conn, ticket, retriever):
    t, _ = ticket
    ans = review.draft_answer(conn, t["id"], *retriever)
    out = review.review(conn, t["id"], ans["suggestion_id"], "edit", "Raj", reply="Hi, I reset it for you.")
    assert out["final"]["reply"] == "Hi, I reset it for you." and out["final"]["ai_draft_used"] is False
    with pytest.raises(review.Conflict):
        review.review(conn, t["id"], ans["suggestion_id"], "approve", "Raj")


def test_reject_reply_sends_nothing(conn, ticket, retriever):
    t, _ = ticket
    ans = review.draft_answer(conn, t["id"], *retriever)
    out = review.review(conn, t["id"], ans["suggestion_id"], "reject", "Raj", reason="too generic")
    assert not out["reply_sent"] and "reply_sent" not in events(conn, t["id"])


def test_escalated_ticket_has_no_draft_to_approve(conn, retriever):
    t = repository.create_ticket(conn, subject="Unknown login", channel="email", customer_ref="EMP-2",
                                 body="Someone logged in to my account from another country. It was not me.")
    ans = review.draft_answer(conn, t["id"], *retriever)
    assert ans["status"] == "escalated" and ans["draft_reply"] is None
    with pytest.raises(review.ReviewError):
        review.review(conn, t["id"], ans["suggestion_id"], "approve", "Lead")
    out = review.review(conn, t["id"], ans["suggestion_id"], "edit", "Lead",
                        reply="We locked the account; security will call you.")
    assert out["reply_sent"] and out["final"]["ai_draft_used"] is False


def test_only_the_newest_draft_can_be_decided(conn, ticket, retriever):
    t, _ = ticket
    old = review.draft_answer(conn, t["id"], *retriever)
    new = review.draft_answer(conn, t["id"], *retriever)
    with pytest.raises(review.Conflict):
        review.review(conn, t["id"], old["suggestion_id"], "approve", "Raj")
    assert review.review(conn, t["id"], new["suggestion_id"], "approve", "Raj")["reply_sent"]


def test_edit_reply_needs_text(conn, ticket, retriever):
    t, _ = ticket
    ans = review.draft_answer(conn, t["id"], *retriever)
    with pytest.raises(review.ReviewError):
        review.review(conn, t["id"], ans["suggestion_id"], "edit", "Raj", reply="  ")


# ---------- audit + counts ----------
def test_full_trail_in_order(conn, ticket, retriever):
    t, tri = ticket
    review.review(conn, t["id"], tri["id"], "approve", "Raj")
    ans = review.draft_answer(conn, t["id"], *retriever)
    review.review(conn, t["id"], ans["suggestion_id"], "approve", "Raj")
    assert events(conn, t["id"]) == ["ticket_created", "ai_triage", "suggestion_approved", "ai_answer_drafted",
                                     "suggestion_approved", "reply_sent", "ticket_updated"]
    trail = audit.for_ticket(conn, t["id"])
    assert trail[1]["actor"] == "ai" and trail[1]["suggestion_id"] == tri["id"]


def test_audit_has_no_update_or_delete():
    assert not [n for n in dir(audit) if n.startswith(("update", "delete", "remove", "edit"))]


def test_unknown_audit_event_is_refused(conn):
    with pytest.raises(ValueError):
        audit.log(conn, "made_up_event", "Raj")


def test_manual_update_and_delete_are_audited(conn, ticket):
    t, _ = ticket
    repository.update_ticket(conn, t["id"], {"status": "In Progress"}, actor="Raj")
    repository.update_ticket(conn, t["id"], {"status": "In Progress"}, actor="Raj")  # no change -> no event
    repository.delete_ticket(conn, t["id"], actor="Lead")
    trail = audit.for_ticket(conn, t["id"])
    updates = [e for e in trail if e["event"] == "ticket_updated"]
    assert len(updates) == 1 and updates[0]["details"]["status"] == {"from": t["status"], "to": "In Progress"}
    assert trail[-1]["event"] == "ticket_deleted" and trail[-1]["actor"] == "Lead"


def test_suggestions_show_their_review(conn, ticket):
    t, tri = ticket
    assert repository.list_suggestions(conn, t["id"])[0]["review"] is None
    review.review(conn, t["id"], tri["id"], "approve", "Raj")
    rv = repository.list_suggestions(conn, t["id"])[0]["review"]
    assert rv["decision"] == "approved" and rv["reviewer"] == "Raj"


def test_pending_and_counts_feed_the_dashboard(conn, ticket, retriever):
    t, tri = ticket
    assert review.pending(conn)[t["id"]] == 1
    ans = review.draft_answer(conn, t["id"], *retriever)
    assert review.pending(conn)[t["id"]] == 2
    review.review(conn, t["id"], tri["id"], "approve", "Raj")
    review.review(conn, t["id"], ans["suggestion_id"], "reject", "Raj", reason="generic")
    assert t["id"] not in review.pending(conn)
    c = review.counts(conn)
    assert c["triage"]["approved"] == 1 and c["answer"]["rejected"] == 1
    s = dashboard.stats(conn)
    assert s["human_decisions"] == c and s["kpis"]["awaiting_decision"] == 0


def test_queue_hides_replied_tickets_unless_asked(conn, ticket, retriever):
    t, _ = ticket
    ans = review.draft_answer(conn, t["id"], *retriever)
    review.review(conn, t["id"], ans["suggestion_id"], "approve", "Raj")
    assert t["id"] not in [r["id"] for r in dashboard.queue(conn)["tickets"]]
    row = [r for r in dashboard.queue(conn, include_closed=True)["tickets"] if r["id"] == t["id"]][0]
    assert row["status"] == review.REPLY_STATUS and row["sla"] == "closed"


def test_system_info_counts(conn, ticket):
    from app.services import system
    s = system.info(conn)
    assert s["database"]["rows"]["tickets"] == 1 and s["database"]["rows"]["audit_log"] >= 2
    assert s["ai"]["latency"]["triage"]["count"] == 1
