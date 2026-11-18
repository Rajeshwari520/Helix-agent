# Work by week — Helix Agent (KGIT helpdesk)

## Week 1 (04–10 Nov) — Planning
| Task | Files |
|---|---|
| Requirements | `docs/requirements.md` |
| 50 tickets + 30 FAQs | `data/kgit/tickets.csv`, `data/kgit/faqs.csv`, `data/kgit/domain.json` (+ training/dev/frozen-test sets) |
| Rule-based baseline | `notebooks/01_baseline_routing.ipynb`, `docs/kgit/baseline_metrics.json` |
| Architecture + backlog | `docs/architecture.md`, `docs/architecture.png`, `docs/backlog.md` |

## Week 2 (11–17 Nov) — Backend + ML
| Task | Files |
|---|---|
| Ticket CRUD API + PostgreSQL schema | `app/main.py`, `app/db.py`, `app/repository.py`, `app/schemas.py`, `app/routers/tickets.py`, `app/migrations/` |
| Category classifier + metrics | `app/services/classifier.py`, `ml/train_classifier.py`, `ml/select_model.py`, `docs/kgit/week2_confusion_matrix.png` |
| Urgency scoring + routing | `app/services/priority.py`, `app/services/triage.py` |
| Tests + seeded scenarios | `tests/` (96 passed), `tests/scenarios.json` |
| Report | `docs/week2_report.md`, `docs/postgres_setup.md` |

## Week 3 (18–24 Nov) — AI answers + safety
| Task | Files |
|---|---|
| Versioned FAQ store | `app/services/knowledge.py`, `app/routers/faqs.py` |
| RAG with citations | `app/services/retriever.py`, `app/services/rag.py`, `app/routers/answers.py` |
| Guardrails + escalation tests | `app/services/guardrails.py`, `tests/test_rag_and_guardrails.py` |
| Demo + issue log | `docs/demo_script.md`, `docs/issue_log.md` |
| Report | `docs/week3_report.md`, `docs/kgit/week3_rag_scorecard.json` |
