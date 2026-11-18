# Helix Agent — AI Customer Support & Ticket Management (KGIT Helpdesk)

Human-in-the-loop AI for the **KGIT helpdesk** that **classifies, prioritizes and routes** tickets and drafts **FAQ-grounded answers with citations**. Risky tickets are escalated, and **a support agent approves every reply**.

**Intern:** Rajeshwari R · **Organization:** KGIT · **Duration:** 12 weeks (04 Nov 2026 – 26 Jan 2027)

| Category *(assumed — confirm with mentor)* | Team |
|---|---|
| IT Support | IT Service Desk |
| Access & Accounts | Identity & Access Team |
| Training & Courses | Learning Team |
| HR & Admin | HR & Admin Team |
| Billing & Finance | Finance Team |

**Database:** PostgreSQL 16 (main) · SQLite fallback for zero-setup runs.

## 📍 Status — Weeks 1–3 complete
| Week | Deliverables | Evidence |
|---|---|---|
| **1** | Requirements, 50 synthetic tickets + 30 FAQs, rule baseline, architecture, backlog | [requirements](docs/requirements.md) · [data](data/kgit/) · [baseline notebook](notebooks/01_baseline_routing.ipynb) · [architecture](docs/architecture.md) · [backlog](docs/backlog.md) |
| **2** | Ticket CRUD API + **PostgreSQL schema & migrations**, ML classifier, urgency scoring + routing, test suite | [Week 2 report](docs/week2_report.md) · [PostgreSQL setup](docs/postgres_setup.md) · [metrics](docs/kgit/) |
| **3** | Versioned FAQ store, RAG with citations, guardrails, escalation tests, demo + issue log | [Week 3 report](docs/week3_report.md) · [demo script](docs/demo_script.md) · [issue log](docs/issue_log.md) |

Tracking: [task tracker (Excel)](docs/task_tracker.xlsx)

## 📊 Key results — frozen test set (50 unseen tickets, never used for training or tuning)
| What | Week 1 rules | Before improvement | **Now** |
|---|---|---|---|
| Category accuracy | 0.76 | 0.84 | **0.96** |
| Priority accuracy | 0.54 | 0.64 | **0.80** |
| Risky tickets caught | 0.29 | 0.71 | **1.00** |
| All three correct | — | 0.54 | **0.76** |

| Also | Result |
|---|---|
| RAG answer precision / coverage | **1.00 / 0.97**, 0 wrong-FAQ answers |
| Seeded scenarios written in new words | **12 / 12** |
| Tests | **85 passed** on **PostgreSQL 16** and SQLite (+ 12 API tests) |

All data is synthetic and written by the same author, so real-world accuracy will be lower — see the [issue log](docs/issue_log.md).

## ⚙️ How it works
```
Ticket ─► Guardrails (PII redaction, injection check) ─► Classifier (category + confidence)
       ─► Urgency scoring (priority + reasons) ─► Routing (team / Team Lead) + SLA
       ─► RAG: approved FAQs ─► draft with [FAQ-xxx vN] citations ─► HUMAN APPROVAL ─► User
```

## ▶ Run (Windows, PowerShell)
Python **3.10+**. Install PostgreSQL first → [docs/postgres_setup.md](docs/postgres_setup.md).
```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt

$env:DATABASE_URL="postgresql://helix:helix@localhost:5432/helix_kgit"
uvicorn app.main:app --reload            # API -> http://127.0.0.1:8000/docs

python -m pytest -q                      # tests (SQLite); for PostgreSQL set $env:TEST_DATABASE_URL
```
No PostgreSQL yet? Leave `DATABASE_URL` unset and a local SQLite file `helix_kgit.db` is used.

**Re-run the evaluations**
```powershell
python scripts/generate_data.py     # regenerate the synthetic KGIT data
python -m ml.select_model           # choose model by cross-validation (no test set)
python -m ml.train_classifier       # train + score on the frozen test set -> docs/kgit/
python -m ml.evaluate_triage data/kgit/test_tickets.csv   # category + priority + escalation
python -m ml.evaluate_rag           # Week 3 RAG scorecard -> docs/kgit/
```

## 🔌 API
| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/tickets` | Create ticket (auto-triaged) |
| GET | `/tickets` | Queue with filters `status, priority, team, category, escalated` |
| GET / PATCH / DELETE | `/tickets/{id}` | Read / human override / soft delete |
| POST | `/tickets/{id}/triage` | Triage with explanation |
| POST | `/tickets/{id}/answer` | Grounded draft reply with citations |
| GET | `/tickets/{id}/suggestions` | Stored AI suggestions |
| POST | `/ask` | Ask a question (same guardrails) |
| GET / POST | `/faqs`, `/faqs/{id}/versions`, `/faqs/{id}/approve`, `/faqs/{id}/history` | Versioned knowledge store |
| GET | `/health` | Health check |

## 📁 Structure
```
app/
  main.py  config.py  db.py  repository.py  schemas.py  deps.py
  migrations/postgres/   0001_init.sql, 0002_faq_store.sql, 0003_app_settings.sql
  migrations/sqlite/     same, for the SQLite fallback
  routers/               tickets.py, answers.py, faqs.py
  services/              classifier.py, priority.py, triage.py, guardrails.py,
                         knowledge.py, retriever.py, rag.py
ml/                      train_classifier.py, select_model.py, evaluate_triage.py, evaluate_rag.py
data/kgit/               domain.json (categories/teams), train_tickets.csv (450 templates),
                         tickets.csv + dev_tickets.csv (100 hand-written, training),
                         test_tickets.csv (50, FROZEN test), faqs.csv, rag_eval.csv
docs/                    requirements, architecture, backlog, reports, issue log, demo script,
                         postgres_setup.md, task_tracker.xlsx, kgit/ (metrics & charts)
notebooks/               01_baseline_routing.ipynb
scripts/                 generate_data.py, build_notebook.py, init_databases.sql
tests/                   unit, scenario, guardrail and API tests
docker-compose.yml       PostgreSQL 16 for local development
```

## 🔒 Data & safety
- **Synthetic data only** — no real users, credentials or Microsoft 365 access.
- PII is redacted before retrieval; prompt injection is refused; fraud / legal / privacy / HR-sensitive tickets get **no AI draft**.
- `requires_human_approval` is always `true` — nothing is sent automatically.
- Categories and teams live in `data/kgit/domain.json`, so they can be changed once the mentor confirms KGIT's real ones.
