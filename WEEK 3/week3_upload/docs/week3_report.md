# Week 3 Report — Knowledge, RAG, Guardrails, Review
**Period:** 18 Nov – 24 Nov 2026 · **Planned:** 34 h · **Intern:** Rajeshwari R
**Domain:** KGIT helpdesk (categories assumed, DEC-08) · **Database:** PostgreSQL 16 (SQLite fallback)

| Work package | Acceptance evidence | Where |
|---|---|---|
| Knowledge · 8 h | Versioned FAQ corpus | `app/migrations/*/0002_faq_store.sql`, `app/services/knowledge.py`, `app/routers/faqs.py`, `data/kgit/knowledge_snapshot_v1.json` |
| RAG · 12 h | Grounded answer endpoint | `app/services/retriever.py`, `app/services/rag.py`, `POST /tickets/{id}/answer`, `POST /ask` |
| Guardrails · 8 h | Escalation test cases | `app/services/guardrails.py`, `tests/test_rag_and_guardrails.py` |
| Review · 6 h | Demo + issue log | `docs/demo_script.md`, `docs/issue_log.md` |

---

## 1. Versioned FAQ knowledge store
- 30 KGIT FAQs (6 per category) in `data/kgit/faqs.csv`, loaded as version 1.
- Every FAQ has a stable id (`FAQ-001`) and **versions**. An edit creates a **draft**; it is **not used** until approved.
- Approving a version makes it **current** and **retires** the previous one; history is kept (`GET /faqs/{id}/history`).
- `corpus_version` (e.g. `kb-kgit-…`) is a hash of all current approved FAQ versions and is stored with **every** AI answer.
- Seed FAQs are marked `approved_by = "seed: synthetic prototype data"` — **mentor review required** (DEC-06).

| Endpoint | Purpose |
|---|---|
| `GET /faqs` | Current approved FAQs + corpus version |
| `POST /faqs` | Propose a new FAQ (draft) |
| `POST /faqs/{id}/versions` | Propose an edit (new draft version) |
| `POST /faqs/{id}/approve` | Approve a version → becomes current |
| `GET /faqs/{id}/history` | All versions with status |

## 2. RAG with source citations
**Retriever:** TF-IDF (word + character n-grams) + cosine similarity — offline, zero API cost.
**Flow:** guardrails → retrieve top-3 approved FAQs from **PII-redacted** text → if best score < **0.30**, no draft (`low_confidence`) → otherwise a reply built **only from FAQ text** with `[FAQ-xxx vN]` citations → `requires_human_approval: true` always.
The draft is **extractive**, so it cannot invent facts. An LLM can later rewrite the wording once a provider is approved (DEC-05).

### RAG scorecard (50 tickets, labels in `data/kgit/rag_eval.csv`)
| Metric | Value |
|---|---|
| Answer precision (drafts citing the right FAQ) | **1.00** |
| Answer coverage (answerable tickets answered correctly) | **0.97** |
| Escalation recall (sensitive tickets with no AI draft) | **1.00** |
| Wrong-FAQ answers | **0** |

| Outcome | Count |
|---|---|
| Correct answer | 30 |
| Correctly abstained (no FAQ exists) | 13 |
| Correctly escalated | 6 |
| Missed (FAQ exists, score too low — software install) | 1 |

**Threshold sweep** (`docs/kgit/week3_rag_scorecard.json`): 0.20 → precision 0.78; 0.25 → 0.91; **0.30 → 1.00** (chosen, coverage 0.97); 0.35 → 1.00 but coverage drops to 0.90.

## 3. Guardrails
| Check | What happens |
|---|---|
| **Prompt injection** ("ignore previous instructions", "reveal system prompt", "you are now admin", …) | `refused`, no draft, escalate |
| **Security / fraud** (unknown charge, hacked, unknown login, phishing, malware, ransomware, data leak) | `escalated`, no draft, Team Lead |
| **Legal / media** (legal notice, court, journalist) | `escalated`, no draft |
| **Privacy request** (delete my account / data) | `escalated`, no draft |
| **HR-sensitive** (harassment, discrimination, bullying, threats) | `escalated`, no draft |
| **Anger / complaint** | draft allowed but **flagged** |
| **Low retrieval confidence** | `low_confidence`, no draft |
| **PII** (card, email, UPI, phone, OTP, Aadhaar) | redacted before retrieval; types reported |

### Escalation test cases (`tests/test_rag_and_guardrails.py`)
7 grounded-answer · 6 sensitive-topic (fraud, phishing, legal, media, privacy, harassment) · 4 prompt-injection · 3 out-of-scope · 1 anger · 4 PII redaction · FAQ versioning (draft not used until approved, new version replaces old, history kept) · category validation.

## 4. Review
- Demo script: `docs/demo_script.md`
- Issue log: `docs/issue_log.md` — bugs found & fixed, open issues, **decisions needing mentor approval**

## 5. Next week (Week 4)
React ticket queue + ticket detail with approve / edit / reject, audit trail of AI suggestions and human decisions, 20 end-to-end scenarios.
