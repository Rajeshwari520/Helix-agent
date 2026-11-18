# 🛠 Build Guide: Weeks 1–3 (step by step)

Indha folder-la irukura code **reference**. Neengalae step by step build pannunga.
**Paathu, purinjukittu, type pannunga.** Ovvoru step-kum ✅ check run pannunga.

---

## 🧰 Step 0: Setup (30 min)

```bash
mkdir helix-agent
cd helix-agent
python -m venv venv
venv\Scripts\activate            # macOS/Linux: source venv/bin/activate
pip install fastapi uvicorn pydantic "psycopg[binary]" pandas scikit-learn joblib matplotlib openpyxl pytest httpx jupyter
git init
git remote add origin https://github.com/Rajeshwari520/helix-agent.git
```

Folders:
```powershell
mkdir app\services, app\routers, app\migrations, data, docs, ml, notebooks, scripts, tests
```

---

## 🗓 WEEK 1: Planning (Day 1–2)

### 1.1 Requirements (1 hr)
📄 `docs/requirements.md`: unga words-la ezhudhunga:
- Ticket stages (New → Triaged → Assigned → In Progress → Resolved → Closed)
- 5 user roles (Customer, Agent, Team Lead, Admin, AI)
- 8 escalation rules
- Categories → teams table, SLA table

✅ "Ticket eppo escalate aagum?" nu file paakaama solla mudiyumaa?

### 1.2 Data (1 hr)
📄 `scripts/generate_data.py`: 5–10 tickets unga own words-la maathunga.
```bash
python scripts/generate_data.py
```
✅ `data/kgit/tickets.csv` (50 rows), `data/kgit/faqs.csv` (30 rows), `data/kgit/train_tickets.csv` (300 rows) Excel-la check.
📄 `data/kgit/domain.json`: KGIT categories → teams (assumed; mentor confirm pannanum).

### 1.3 Baseline notebook (2 hr)
`jupyter notebook` → `notebooks/01_baseline_routing.ipynb`. Cells order:
1. CSV load
2. `CATEGORY_KEYWORDS` dictionary
3. `predict_category()`, `predict_priority()`, `predict_escalation()`
4. Accuracy + macro-F1 (vs majority-class baseline)
5. Confusion matrix
6. Errors list + conclusion

✅ Category ~98% on these 50 (rules memorise them) but only ~74% on the 300 unseen-wording tickets (section 4b).

### 1.4 Architecture (1 hr)
📄 `docs/architecture.md` + diagram (draw.io-la neengalae draw pannalaam, illa `docs/architecture.png` use pannunga)
📄 `docs/backlog.md`

```bash
git add .
git commit -m "Week 1: requirements, synthetic data, baseline, architecture"
git push -u origin main
```

---

## 🗓 WEEK 2: Backend + ML (Day 3–5)

**Order:** config → database → ML → priority → guardrails/triage → API → tests

### 2.1 Config (15 min)
📄 `app/__init__.py` (empty)
📄 `app/config.py`: categories, teams, SLA hours, thresholds

### 2.2 Database: PostgreSQL (1.5 hr)
First PostgreSQL install pannunga: `docs/postgres_setup.md` (installer or Docker).

📄 `app/migrations/postgres/0001_init.sql`: teams, categories, users, tickets, ai_suggestions (SERIAL ids)
📄 `app/migrations/sqlite/0001_init.sql`: same tables for the SQLite fallback
📄 `app/db.py`: `Database` wrapper (`?` → `%s` for PostgreSQL), `connect()`, `migrate()`, `seed_reference_data()`, `ensure_domain()`

✅ Test (PostgreSQL):
```powershell
python -c "from app import db; c=db.connect('postgresql://helix:helix@localhost:5432/helix_test'); print(c.dialect, db.migrate(c))"
```
First time `postgres ['0001_init.sql', ...]`, second time `[]`.

### 2.3 ML classifier (2.5 hr) ⭐
📄 Training data `scripts/generate_data.py`-laye create aagum → `data/kgit/train_tickets.csv` (450)
📄 `data/kgit/dev_tickets.csv` (50, tuning-ku) + `data/kgit/test_tickets.csv` (50, **FROZEN** — training/tuning-ku use pannave koodadhu)
📄 `app/services/__init__.py` (empty)
📄 `app/services/classifier.py`: TF-IDF (word + char n-grams) + Logistic Regression; training = templates + hand-written tickets (3×)
📄 `ml/__init__.py` (empty), `ml/select_model.py`, `ml/train_classifier.py`, `ml/evaluate_triage.py`

```bash
python -m ml.select_model                                 # model choose (cross-validation, test set illama)
python -m ml.train_classifier                             # train + frozen test score
python -m ml.evaluate_triage data/kgit/test_tickets.csv   # category + priority + escalation
```
✅ Category ~0.96, priority ~0.80, risky caught 1.00 on frozen test set; `docs/kgit/week2_confusion_matrix.png`

⚠️ **Rule:** test set errors paathu tuning pannaadheenga. Dev set-la mattum tune pannunga — illana score fake aagidum.

### 2.4 Priority engine (1.5 hr)
📄 `app/services/priority.py`: signals + points (≥5 Critical, ≥3 High, ≥1.5 Medium)

✅ Test:
```bash
python -c "from app.services.priority import score; print(score('I was charged twice for the course fee'))"
```
→ `High`

### 2.5 Guardrails + Triage (1 hr)
📄 `app/services/guardrails.py`: PII redaction, injection check, sensitive topics
📄 `app/services/triage.py`: classifier + priority + routing + SLA

✅ Test:
```bash
python -c "from app.services.triage import triage; print(triage('Hacked','Someone logged in to my account'))"
```
→ `Critical`, `Team Lead`, `needs_escalation: True`

### 2.6 API (2 hr)
📄 `app/repository.py`: create / get / list / update / delete / triage
📄 `app/schemas.py`: pydantic models
📄 `app/deps.py`
📄 `app/routers/__init__.py` (empty), `app/routers/tickets.py`
📄 `app/main.py`: **Week 2-ku tickets router mattum**

```bash
uvicorn app.main:app --reload
```
✅ http://127.0.0.1:8000/docs → `POST /tickets` try pannunga.

### 2.7 Tests (1.5 hr)
📄 `tests/__init__.py`, `tests/conftest.py`, `tests/scenarios.json`
📄 `tests/test_db_and_repository.py`, `tests/test_triage_engine.py`

```bash
python -m pytest -q
```
✅ All pass.

```bash
git add .
git commit -m "Week 2: ticket API, SQL migrations, ML classifier, priority engine, tests"
git push
```

---

## 🗓 WEEK 3: AI answers (Day 6–7)

### 3.1 FAQ knowledge store (1.5 hr)
📄 `app/migrations/0002_faq_store.sql`
📄 `app/services/knowledge.py`: load, propose version, approve, history, corpus_version

### 3.2 Retriever + RAG (2 hr) ⭐
📄 `app/services/retriever.py`: TF-IDF + cosine similarity
📄 `app/services/rag.py`: guardrails → search → threshold (0.30) → draft + citation

✅ Test:
```bash
python -c "from app import db; from app.services import knowledge, rag; from app.services.retriever import FAQRetriever; c=db.connect(':memory:'); db.migrate(c); knowledge.load_from_csv(c); r=FAQRetriever(knowledge.current_faqs(c)); print(rag.answer('How do I reset my LMS password?', r, 'v1')['draft_reply'])"
```
→ reply-la `[FAQ-007 v1]`

### 3.3 API endpoints (1 hr)
📄 `app/routers/answers.py`: `/tickets/{id}/answer`, `/ask`
📄 `app/routers/faqs.py`: FAQ versions
📄 `app/main.py`: answers + faqs routers add + lifespan-la `knowledge.load_from_csv`

### 3.4 Tests (1.5 hr)
📄 `tests/test_rag_and_guardrails.py`, `tests/test_api.py`
```bash
python -m pytest -q
```

### 3.5 Evaluation + docs (1.5 hr)
📄 `data/kgit/rag_eval.csv`, `ml/evaluate_rag.py` → `python -m ml.evaluate_rag`
📄 `docs/week2_report.md`, `docs/week3_report.md`, `docs/issue_log.md`, `docs/demo_script.md`, `README.md`

```bash
git add .
git commit -m "Week 3: FAQ store, RAG with citations, guardrails, demo, issue log"
git push
```

---

## 📋 Timeline

| Day | Build | Hours |
|---|---|---|
| 1–2 | Week 1: docs, data, baseline, architecture | ~5 h |
| 3 | Config, database, ML classifier | ~3.5 h |
| 4 | Priority, guardrails, triage | ~2.5 h |
| 5 | API + tests | ~3.5 h |
| 6 | FAQ store, retriever, RAG | ~3.5 h |
| 7 | Endpoints, tests, evaluation, docs | ~4 h |

## 💡 Tips
1. Copy-paste pannaadheenga. Type pannumbodhu dhaan purium.
2. Ovvoru step-kum ✅ check run pannunga. Error vandha adhe step-la fix pannunga.
3. Puriyaadha line: file name + line number kelunga.
4. Error vandha full error message copy pannunga.
