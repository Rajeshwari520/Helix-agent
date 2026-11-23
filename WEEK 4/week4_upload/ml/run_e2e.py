"""Week 4 — 20 end-to-end ticket scenarios (data/<domain>/e2e_scenarios.json).

Each scenario walks one ticket through the whole workflow, using the same service functions
the API routes call:

    create ticket -> AI triage -> human approves / edits / rejects the triage
                  -> AI drafts a reply from FAQs -> human approves / edits / rejects the reply

Two kinds of checks:
  * workflow checks (must pass): nothing is sent without a named person's decision, risky tickets
    never get an AI draft, every step is in the audit trail, a suggestion can be decided only once,
    an out-of-date draft cannot be approved, edits really change the ticket and its SLA.
  * AI expectations (reported, not a gate): did the AI pick the category / priority / escalation
    / answer type we expected? Misses are listed in the results so they can be improved.

Run from the project root (uses a fresh in-memory SQLite database, so your data is untouched):
    python -m ml.run_e2e
Writes docs/<domain>/week4_e2e_results.csv and .md
"""
import argparse
import json
from datetime import datetime, timedelta

from app import config, db, repository
from app.services import audit, knowledge, review
from app.services.retriever import FAQRetriever

REVIEWER = "E2E Agent"
LEAD = "E2E Team Lead"


def fresh_db():
    conn = db.connect(":memory:")
    db.migrate(conn)
    db.ensure_domain(conn)
    db.seed_reference_data(conn)
    knowledge.load_from_csv(conn)
    return conn


def load_scenarios(path=None) -> list[dict]:
    path = path or config.domain().data_dir / "e2e_scenarios.json"
    with open(path, encoding="utf-8") as f:
        return json.load(f)["scenarios"]


class Run:
    def __init__(self, sc):
        self.sc, self.checks, self.ai_misses, self.notes = sc, [], [], []

    def check(self, name, ok, detail=""):
        self.checks.append((name, bool(ok), detail))
        return ok

    def expect_error(self, name, kind, fn):
        err = {"conflict": review.Conflict, "invalid": review.ReviewError}[kind]
        try:
            fn()
        except err:
            return self.check(name, True)
        except Exception as exc:  # noqa: BLE001
            return self.check(name, False, f"wrong error {type(exc).__name__}: {exc}")
        return self.check(name, False, "no error raised")


def run_one(conn, sc: dict, retriever, corpus_version: str) -> dict:
    r = Run(sc)
    exp, ai_exp = sc.get("expect", {}), sc.get("expect_ai", {})
    who = LEAD if (sc.get("answer", {}).get("decision") == "edit" and ai_exp.get("escalated")) else REVIEWER

    # 1. ticket arrives -> AI triage (automatic)
    t = repository.create_ticket(conn, subject=sc["subject"], body=sc["body"], channel=sc["channel"],
                                 customer_ref="CUST-E2E")
    tid = t["id"]
    tri = [s for s in repository.list_suggestions(conn, tid) if s["kind"] == "triage"][-1]
    p = tri["payload"]
    events = [e["event"] for e in audit.for_ticket(conn, tid)]
    r.check("ticket_created and ai_triage are audited", events[:2] == ["ticket_created", "ai_triage"], str(events))

    # AI expectations (reported only)
    for key, got in [("category", p["category"]), ("priority", p["priority"]), ("escalated", p["needs_escalation"])]:
        if key in ai_exp and ai_exp[key] != got:
            r.ai_misses.append(f"{key}: expected {ai_exp[key]}, AI said {got}")
    if "pii" in ai_exp and sorted(p.get("pii_found", [])) != sorted(ai_exp["pii"]):
        r.ai_misses.append(f"pii: expected {ai_exp['pii']}, found {p.get('pii_found')}")

    # 2. human decision on triage
    td = sc["triage"]
    tr = review.review(conn, tid, tri["id"], td["decision"], who, category=td.get("category"),
                       priority=td.get("priority"), team=td.get("team"), reason=td.get("reason"))
    r.check("triage decision stored with reviewer", tr["decision"] == review.DECISIONS[td["decision"]]
            and tr["reviewer"] == who)
    if td["decision"] == "edit":
        t2 = repository.get_ticket(conn, tid)
        for k in ("category", "priority", "team"):
            if td.get(k):
                r.check(f"edit changed {k}", t2[k] == td[k], f"{t2[k]} != {td[k]}")
        if td.get("priority"):
            first = config.SLA_HOURS[td["priority"]][0]
            due = datetime.fromisoformat(t2["created_at"]) + timedelta(hours=first)
            r.check("SLA deadline follows the new priority",
                    datetime.fromisoformat(t2["sla_first_response_due"]) == due.replace(microsecond=0))
    if sc.get("manual_update"):
        repository.update_ticket(conn, tid, sc["manual_update"], actor=who)

    # 3. AI drafts a reply (never sent by itself)
    ans = review.draft_answer(conn, tid, retriever, corpus_version)
    r.check("AI draft is not sent on its own", not any(e["event"] == "reply_sent" for e in audit.for_ticket(conn, tid)))
    r.check("AI draft requires human approval", ans["requires_human_approval"] is True)
    if ans["status"] in ("refused", "escalated"):
        r.check("risky ticket gets no AI draft", ans["draft_reply"] is None)
    if "answer_status" in ai_exp and ai_exp["answer_status"] != ans["status"]:
        r.ai_misses.append(f"answer: expected {ai_exp['answer_status']}, AI said {ans['status']}")
    if exp.get("no_ai_draft"):
        r.check("no AI draft for this ticket", ans["draft_reply"] is None, ans["status"])
    for secret in exp.get("pii_not_in_ai_output", []):
        stored = json.dumps([s["payload"] for s in repository.list_suggestions(conn, tid)])
        r.check(f"personal data '{secret[:4]}…' not in AI output", secret not in stored)
    stale_id = None
    if sc.get("redraft_before_decision"):
        stale_id = ans["suggestion_id"]
        ans = review.draft_answer(conn, tid, retriever, corpus_version)
        r.expect_error("old draft cannot be decided", sc["stale_decision"]["expect_error"],
                       lambda: review.review(conn, tid, stale_id, sc["stale_decision"]["decision"], who))

    # approving an empty draft must be refused
    if ans["draft_reply"] is None:
        r.expect_error("cannot approve a missing draft", "invalid",
                       lambda: review.review(conn, tid, ans["suggestion_id"], "approve", who))

    # 4. human decision on the reply
    ad = dict(sc["answer"])
    if ad["decision"] == "approve_or_write":
        ad["decision"] = "approve" if ans["draft_reply"] else "edit"
    ar = review.review(conn, tid, ans["suggestion_id"], ad["decision"], who, reply=ad.get("reply"),
                       reason=ad.get("reason"))
    r.notes.append(f"reply: {ad['decision']}")
    if sc.get("second_decision"):
        sd = sc["second_decision"]
        r.expect_error("a suggestion can be decided only once", sd["expect_error"],
                       lambda: review.review(conn, tid, ans["suggestion_id"], sd["decision"], who))

    # 5. final checks
    final = repository.get_ticket(conn, tid)
    trail = audit.for_ticket(conn, tid)
    sent = [e for e in trail if e["event"] == "reply_sent"]
    if "status" in exp:
        r.check("final status", final["status"] == exp["status"], f"{final['status']} != {exp['status']}")
    for k in ("category", "team", "priority"):
        if k in exp:
            r.check(f"final {k}", final[k] == exp[k], f"{final[k]} != {exp[k]}")
    r.check("reply sent only if a person sent it", bool(sent) == exp.get("reply_sent", False) == ar["reply_sent"])
    if "replies_sent" in exp:
        r.check("exactly the expected number of replies", len(sent) == exp["replies_sent"], str(len(sent)))
    if sent and "ai_draft_used" in exp:
        r.check("audit says whether the AI draft was used", sent[-1]["details"]["ai_draft_used"] == exp["ai_draft_used"])
    human = [e for e in trail if e["event"].startswith("suggestion_") or e["event"] == "reply_sent"]
    r.check("every human decision is audited with a name", human and all(e["actor"] == who for e in human))
    order = [e["event"] for e in trail]
    if sent:
        first_sent = order.index("reply_sent")
        r.check("reply only after a human decision on that draft",
                any(o in ("suggestion_approved", "suggestion_edited") for o in order[:first_sent]))

    failed = [(n, d) for n, ok, d in r.checks if not ok]
    return {
        "id": sc["id"], "title": sc["title"], "ticket": tid,
        "ai_category": p["category"], "ai_priority": p["priority"], "ai_escalated": p["needs_escalation"],
        "ai_answer": ans["status"],
        "ai_as_expected": "yes" if not r.ai_misses else "no",
        "ai_misses": "; ".join(r.ai_misses),
        "human_triage": review.DECISIONS[td["decision"]], "human_reply": review.DECISIONS[ad["decision"]],
        "final_status": final["status"], "reply_sent": bool(sent),
        "checks_passed": f"{len(r.checks) - len(failed)}/{len(r.checks)}",
        "result": "PASS" if not failed else "FAIL",
        "failed_checks": "; ".join(f"{n} ({d})" if d else n for n, d in failed),
    }


def run_all(path=None) -> list[dict]:
    conn = fresh_db()
    try:
        retriever = FAQRetriever(knowledge.current_faqs(conn))
        cv = knowledge.corpus_version(conn)
        out = []
        for sc in load_scenarios(path):
            try:
                out.append(run_one(conn, sc, retriever, cv))
            except Exception as exc:  # a crash is a failed scenario, not a crashed run
                out.append({"id": sc["id"], "title": sc["title"], "ticket": "", "ai_category": "", "ai_priority": "",
                            "ai_escalated": "", "ai_answer": "", "ai_as_expected": "", "ai_misses": "",
                            "human_triage": "", "human_reply": "", "final_status": "", "reply_sent": "",
                            "checks_passed": "0/1", "result": "FAIL",
                            "failed_checks": f"error {type(exc).__name__}: {exc}"})
        return out
    finally:
        conn.close()


def write_report(results: list[dict], out_dir) -> None:
    import csv
    out_dir.mkdir(parents=True, exist_ok=True)
    with open(out_dir / "week4_e2e_results.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(results[0]))
        w.writeheader()
        w.writerows(results)
    passed = sum(r["result"] == "PASS" for r in results)
    ai_ok = sum(r["ai_as_expected"] == "yes" for r in results)
    lines = [
        "# Week 4 — end-to-end scenario results", "",
        f"Generated {datetime.now().strftime('%d %b %Y %H:%M')} by `python -m ml.run_e2e` (fresh in-memory database).", "",
        f"* **Workflow: {passed}/{len(results)} scenarios passed** every check "
        "(human decision before any reply, no AI draft for risky tickets, full audit trail, no double or stale decisions).",
        f"* **AI matched our expectation in {ai_ok}/{len(results)}** scenarios (reported only; misses below).",
        "* Sending is simulated: replies are stored and logged, no email is sent.", "",
        "| ID | Scenario | AI triage | AI reply | Person decided | Final status | Checks | Result |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for r in results:
        lines.append(f"| {r['id']} | {r['title']} | {r['ai_category']} · {r['ai_priority']}"
                     f"{' · escalated' if r['ai_escalated'] else ''} | {r['ai_answer']} | "
                     f"triage {r['human_triage']}, reply {r['human_reply']} | {r['final_status']} | "
                     f"{r['checks_passed']} | {r['result']} |")
    misses = [r for r in results if r["ai_misses"]]
    lines += ["", "## Where the AI did not do what we expected", ""]
    lines += [f"* **{r['id']}** {r['title']}: {r['ai_misses']}" for r in misses] or ["* None."]
    fails = [r for r in results if r["result"] == "FAIL"]
    lines += ["", "## Failed workflow checks", ""]
    lines += [f"* **{r['id']}**: {r['failed_checks']}" for r in fails] or ["* None."]
    (out_dir / "week4_e2e_results.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--domain", default=None)
    args = ap.parse_args()
    if args.domain:
        config.set_domain(args.domain)
    results = run_all()
    out = config.ROOT / "docs" / config.domain().name
    write_report(results, out)
    for r in results:
        print(f"{r['id']}  {r['result']}  {r['checks_passed']:>5}  AI {r['ai_as_expected']:>3}  {r['title']}")
        if r["failed_checks"]:
            print("      FAILED:", r["failed_checks"])
        if r["ai_misses"]:
            print("      AI:", r["ai_misses"])
    print(f"\n{sum(r['result'] == 'PASS' for r in results)}/{len(results)} passed -> {out / 'week4_e2e_results.md'}")


if __name__ == "__main__":
    main()
