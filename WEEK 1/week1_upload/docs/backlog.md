# Product Backlog — Helix Agent

Status values: **Not Started / In Progress / Blocked / Done / Deferred**
Priority: **P1** = must have · **P2** = should have · **P3** = nice to have
Tip: create each row as a **GitHub Issue** with labels `week-XX` and `P1/P2/P3`.

## Week 1 — Foundation ✅
| ID | Item | Priority | Status | Evidence |
|---|---|---|---|---|
| W1-1 | Map ticket lifecycle, roles, escalation policy | P1 | Done | `docs/requirements.md` |
| W1-2 | Create 50 synthetic tickets + 30 FAQs with labels | P1 | Done | `data/kgit/` |
| W1-3 | Rule-based routing + baseline metrics | P1 | Done | `notebooks/01_baseline_routing.ipynb` |
| W1-4 | Architecture diagram, API, DB, UI, deployment plan | P1 | Done | `docs/architecture.md` |
| W1-5 | Mentor approval of requirements & data permissions | P1 | In Progress | Signed table in requirements.md |

## Week 2 — Backend & classification ✅
| ID | Item | Priority | Status |
|---|---|---|---|
| W2-1 | FastAPI project setup + `/health` | P1 | Done |
| W2-2 | PostgreSQL schema + SQL migrations (tickets, users, teams, categories); SQLite fallback | P1 | Done |
| W2-7 | Switch to KGIT helpdesk domain (assumed categories), data + model + tests | P1 | Done (categories need mentor confirmation) |
| W2-3 | Ticket CRUD endpoints | P1 | Done |
| W2-4 | Train TF-IDF + Logistic Regression classifier; metrics + confusion matrix vs baseline | P1 | Done |
| W2-5 | Urgency scoring + routing rules engine | P1 | Done |
| W2-6 | Unit tests + seeded scenarios (pytest) | P1 | Done |

## Week 3 — Knowledge & RAG ✅
| ID | Item | Priority | Status |
|---|---|---|---|
| W3-1 | Versioned FAQ store (approved only) | P1 | Done |
| W3-2 | Retrieval index (TF-IDF now; embeddings to compare in Week 7) | P1 | Done |
| W3-3 | Grounded answer endpoint with citations | P1 | Done |
| W3-4 | Refusal, low-confidence and escalation handling + tests | P1 | Done |
| W3-5 | Mentor demo of triage + RAG; issue log | P1 | In Progress (script + log ready, demo pending) |

## Week 4 — Agent UI & audit (Gate: functional core)
| ID | Item | Priority | Status |
|---|---|---|---|
| W4-1 | React ticket queue | P1 | Not Started |
| W4-2 | Ticket detail + approve / edit / reject | P1 | Not Started |
| W4-3 | Audit trail of AI suggestions and human decisions | P1 | Not Started |
| W4-4 | 20 end-to-end ticket scenarios | P1 | Not Started |

## Weeks 5–8 — Integration & evaluation (Gate: Week 8)
| ID | Item | Priority | Status |
|---|---|---|---|
| W5-1 | Mock email inbox adapter | P1 | Not Started |
| W5-2 | Duplicate / thread detection | P2 | Not Started |
| W5-3 | SLA timers, breach flags, SLA dashboard | P1 | Not Started |
| W5-4 | Security & usability review | P1 | Not Started |
| W6-1 | Microsoft Lists field mapping | P3 | Not Started |
| W6-2 | Mock / sandbox Lists connector | P3 | Not Started |
| W6-3 | Human-approved notifications | P2 | Not Started |
| W6-4 | API failure, retry and duplicate resilience tests | P2 | Not Started |
| W7-1 | Evaluate 100 labeled synthetic cases (classification + RAG scorecard) | P1 | Not Started |
| W7-2 | Prompt-injection and PII redaction tests | P1 | Not Started |
| W7-3 | Latency + per-ticket cost sheet | P1 | Not Started |
| W8-1 | Admin-configurable categories and FAQs | P2 | Not Started |
| W8-2 | Reports: volume, SLA, quality | P2 | Not Started |
| W8-3 | Accessibility & usability checklist | P2 | Not Started |
| W8-4 | Operator & deployment guide (draft) | P1 | Not Started |

## Weeks 9–12 — Pilot, release & handover (Gate: Week 12)
| ID | Item | Priority | Status |
|---|---|---|---|
| W9-1 | Synthetic KGIT helpdesk pilot + log | P1 | Not Started |
| W9-2 | Stakeholder feedback register; fix top defects | P1 | Not Started |
| W10-1 | Client setup checklist; feature tiers + operating cost | P2 | Not Started |
| W10-2 | Security review: RBAC, secrets, backups, retention | P1 | Not Started |
| W10-3 | Regression + acceptance testing | P1 | Not Started |
| W11-1 | Tagged release `v1.0.0` + deployment package | P1 | Not Started |
| W11-2 | API & architecture docs; 5-minute video | P1 | Not Started |
| W12-1 | Monitoring checklist; backup & restore test | P1 | Not Started |
| W12-2 | Accessibility validation; final sign-off | P1 | Not Started |

## Risks (initial)
| Risk | Impact | Mitigation |
|---|---|---|
| Rule baseline looks too good (rules written from same 50 tickets) | Misleading metrics | Week 2: held-out test split + 100 new cases in Week 7 |
| No Microsoft 365 sandbox | Week 6 blocked | Build mock connector; integration optional |
| LLM cost / provider not approved | RAG delayed | Start with local embeddings + extractive answers |
| PII sent to external API | Data breach | Redact before any API call; synthetic data only |
