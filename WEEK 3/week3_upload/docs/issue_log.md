# Issue Log — Helix Agent (KGIT helpdesk)

Status: **Open / Fixed / Needs decision / Known limitation**

> **Project history:** Weeks 1–3 were first prototyped on e-commerce sample data. On **18 Nov 2026** the project moved to the **KGIT helpdesk only** (as the plan's Week 9 "KGIT helpdesk simulation" requires). All engine fixes below are still in the code and covered by tests.

## Defects found and fixed
| ID | Found | Issue | Cause | Fix | Status |
|---|---|---|---|---|---|
| ISS-01 | W2 (prototype data) | An invoice amount "4,500" scored **Critical** | Pattern `\b500\b` matched the amount as an HTTP 500 error | Pattern needs `error/http/status 500` or `internal server error`; regression test `test_invoice_amount_is_not_mistaken_for_http_500` | Fixed |
| ISS-02 | W2 (prototype data) | "Refund not received… 10 days ago" scored **High** | "N days ago" was treated as a failure signal | Removed that pattern | Fixed |
| ISS-03 | W2 (prototype data) | "What customer data do you store?" escalated as a privacy request | Information question treated like a deletion request | Only delete / erase / close-account requests escalate | Fixed |
| ISS-04 | W2 | Escalation precision was 0.53 | Low classifier confidence was mixed with risk escalation | Split into `needs_escalation` (risk → Team Lead) and `needs_human_review` (uncertain category) | Fixed |
| ISS-05 | W2 | "Debited two times" → **Low** | Wording not covered | Money signal covers charged/debited/deducted/paid + twice/two times | Fixed |
| ISS-06 | W2 | "Reset email is not arriving" → **Low** | "not arriving" not covered | Added to workaround signal | Fixed |
| ISS-07 | W3 | "API returning 401 **Unauthorized**" treated as fraud | Fraud pattern matched `unauthorized` alone | Needs `unauthorized login/access/transaction/charge/payment` | Fixed |
| ISS-12 | W3 (run on laptop) | SLA due dates calculated from triage time, not ticket creation time | `triage_ticket` did not pass `created_at` | Pass `created_at`; test `test_sla_starts_from_ticket_creation_time` | Fixed |
| ISS-15 | W3 (KGIT tests) | "Delete my **trainee** account and personal data" not recognised as a privacy request | Pattern expected "delete my account" with no word in between | Pattern allows one extra word (`delete my trainee account`) in guardrails and priority | Fixed |

## Accuracy improvement (18 Nov) — measured on a frozen test set
A new dev set (50) and a **frozen test set** (50, SHA-256 checked) were written. The dev set showed that priority rules were over-fitted (0.68 on new wording). After adding the hand-written tickets to training, widening templates and adding general helpdesk priority rules, the **frozen test set** (scored once) moved:
category 0.84 → **0.96**, priority 0.64 → **0.80**, risky tickets caught 0.71 → **1.00**, all three correct 0.54 → **0.76**. Details: `docs/week2_report.md`.

## Open issues (KGIT)
| ID | Issue | Impact | Plan | Status |
|---|---|---|---|---|
| ISS-14 | Category accuracy on synthetic data was 0.80 | Wrong team suggestion | **Improved to 0.96 on the frozen test set.** Still synthetic, same author for data and test → real anonymised KGIT tickets needed (DEC-09) | Mitigated |
| ISS-19 | Frozen test: 2 category errors — "Fake email received" → HR & Admin (should be IT Support, still escalated as security); "Certificate download" → HR & Admin | Wrong team suggestion (1 of the 2 flagged for review) | More training examples for phishing reports and certificate questions | Open |
| ISS-20 | Frozen test: 10 priority errors, mostly **under-prioritised** (High → Medium): "UPI failed, bank shows the amount debited", "SSO error", "course portal timing out", "canteen food made people sick"; also Medium → Low ("new phone for MFA", "login for consultant", "duplicate invoice"), Low → Medium ("mouse not responding") | Some urgent tickets wait longer | Week 7: priority model on the 100-case labeled set + a fresh test set; do **not** tune on the current test set | Open |
| ISS-21 | Frozen test: 2 **over-escalations** — "laptop won't boot + client call" and "lab session cancelled, whole batch waiting" scored Critical (label High) | Team Lead gets 2 extra tickets (safe side) | Review Critical policy with mentor | Open |
| ISS-17 | RAG missed 1 answerable ticket ("Install VS Code and Python" → FAQ-004 scored 0.22 < 0.30) | Agent replies manually | Compare sentence embeddings in Week 7 | Open |
| ISS-18 | Week 1 keyword rules: 0.98 on the 50 tickets they were written from, **0.69** on 450 template tickets and **0.76** on the frozen test set | Shows rules memorise; documented in the notebook | Compare methods on the frozen test set only | Known limitation |

## Decisions needing mentor approval
| ID | Decision | Proposal |
|---|---|---|
| DEC-01 | Classifier confidence threshold for human review | **0.45** (cross-validation: flags 9 %, 0.99 accuracy on the rest; frozen test: 3 of 50 flagged) |
| DEC-02 | Retrieval threshold for drafting an answer | **0.30** (precision 1.00, coverage 0.97, 0 wrong-FAQ answers) |
| DEC-03 | Low confidence → human review instead of Team Lead escalation | Keeps Team Lead queue for real risk only |
| DEC-04 | SLA hours per priority | Critical 1/8 h, High 4/24 h, Medium 8/48 h, Low 24/72 h |
| DEC-05 | LLM provider for rewriting drafts | Not used yet; extractive answers only until approved |
| DEC-06 | FAQ approval | 30 synthetic KGIT FAQs auto-approved as "seed" for the prototype — mentor review required |
| DEC-07 | Database | ✅ **Done: PostgreSQL 16** (full test suite verified on PostgreSQL 16); SQLite kept as fallback |
| DEC-08 | **KGIT helpdesk categories and teams** | **Assumed**: IT Support, Access & Accounts, Training & Courses, HR & Admin, Billing & Finance. Please confirm the real ones, and who raises tickets (employees / trainees / clients) |
| DEC-09 | Real KGIT data | Can anonymised KGIT helpdesk tickets / FAQs be used to retrain (needed for ISS-14)? |
| DEC-10 | Evaluation method | ✅ **Done:** dev set for tuning + frozen test set (scored once). Week 7: write a new frozen 100-case set |

## Known limitations
- All metrics use **synthetic** data and 50 test tickets — indicative, not production estimates. Week 7 adds a 100-case labeled set.
- Training data, rules, dev set and frozen test set were all written by the same person, so scores are likely higher than on real KGIT tickets. The frozen test set is the fairest number available.
- KGIT categories are **assumptions** until the mentor confirms them.
- No authentication / RBAC yet (planned Week 10). Demo users exist in the DB only.
- Retrieval is TF-IDF (keyword-based); it misses synonyms that embeddings would catch.
