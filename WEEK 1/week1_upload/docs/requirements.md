# Requirements — AI Customer Support & Ticket Management Agent (Helix Agent)

| | |
|---|---|
| **Intern** | Rajeshwari R |
| **Organization** | KGIT |
| **Week** | 01 (04 Nov – 10 Nov 2026) |
| **Status** | Draft — awaiting mentor approval |
| **Version** | v1.3 (18 Nov: KGIT helpdesk only; PostgreSQL; thresholds set from data) |

---

## 1. Purpose
Build a demonstrable multi-channel support triage product that **classifies, prioritizes and assigns** tickets and drafts **knowledge-grounded answers** from approved FAQs. **A human approves every customer-facing message.**

## 2. Scope

**In scope:** ticket intake (web form, mock email, chat), classification, priority scoring, team assignment, RAG answers with citations, escalation, human approval, audit log, SLA tracking, admin settings, reporting.

**Out of scope:** Goutam's Moodle Wrapper; the existing KwantumG lead-generation and marketing agents; production customer data; real Microsoft 365 / SharePoint credentials without written authorization.

---

## 3. User roles

| Role | Who | Can do |
|---|---|---|
| **Customer / requester** | Person raising an issue — KGIT employee, trainee or client (*to confirm with mentor*) | Submit ticket, view own ticket status, reply to agent |
| **Support Agent** | Front-line support staff | View queue, open ticket, accept/edit/reject AI suggestions, reply, change status, escalate |
| **Team Lead / Supervisor** | Senior agent | Everything an agent can do + reassign tickets, handle escalations, override priority, view SLA breaches |
| **Admin** | System owner | Manage users and roles, categories, teams, FAQs, SLA rules; view reports and audit log |
| **AI Agent (system)** | Helix Agent | Suggest category, priority, team and draft answer — **never acts on the customer without human approval** |

---

## 4. Ticket lifecycle

```
          ┌──────────┐
 Customer │   NEW    │  ticket created from any channel
 submits  └────┬─────┘
               ▼
          ┌──────────┐  AI suggests category, priority, team
          │ TRIAGED  │  (human can accept / change)
          └────┬─────┘
               ▼
          ┌──────────┐
          │ ASSIGNED │  ticket owned by a team / agent
          └────┬─────┘
               ▼
          ┌─────────────┐   AI drafts answer with FAQ citations
          │ IN PROGRESS │   agent reviews → approves / edits / rejects
          └──┬───────┬──┘
             │       │ needs customer info
             │       ▼
             │  ┌──────────────────┐
             │  │ WAITING ON       │──(customer replies)──► IN PROGRESS
             │  │ CUSTOMER         │
             │  └──────────────────┘
             │
             │ risk / low confidence / SLA breach
             ├──────────────────► ┌───────────┐
             │                    │ ESCALATED │──► Team Lead ──► IN PROGRESS
             │                    └───────────┘
             ▼
          ┌──────────┐  approved answer sent
          │ RESOLVED │
          └────┬─────┘
               │ no reply in 72 h, or customer confirms
               ▼
          ┌──────────┐
          │  CLOSED  │  (customer can reopen within 7 days → IN PROGRESS)
          └──────────┘
```

| Status | Meaning | Who moves it |
|---|---|---|
| New | Just received | System |
| Triaged | AI suggestions attached | System / Agent |
| Assigned | Owned by a team or agent | System / Team Lead |
| In Progress | Agent is working on it | Agent |
| Waiting on Customer | Need more information | Agent |
| Escalated | Sent to Team Lead | System / Agent |
| Resolved | Answer sent and approved | Agent |
| Closed | Finished | System / Customer |

---

## 5. Categories, priority and routing

**KGIT helpdesk — categories ASSUMED, to be confirmed by mentor (DEC-08)**

| Category | Examples | Team |
|---|---|---|
| IT Support | VPN, laptop, email, printer, Wi-Fi, phishing | IT Service Desk |
| Access & Accounts | passwords, MFA, tool access, joiners/leavers | Identity & Access Team |
| Training & Courses | LMS videos, certificates, batches, exams | Learning Team |
| HR & Admin | salary, leave, letters, ID card, facilities, HR complaints | HR & Admin Team |
| Billing & Finance | course fees, receipts, refunds, invoices, vendor payments | Finance Team |

| Priority | Definition | First response SLA | Resolution SLA |
|---|---|---|---|
| **Critical** | Security/fraud, service fully down, legal threat | 1 h | 8 h |
| **High** | Customer blocked or money lost | 4 h | 24 h |
| **Medium** | Problem with a workaround | 8 h | 48 h |
| **Low** | Question, feedback, cosmetic issue | 24 h | 72 h |

*(SLA values are proposals — to be confirmed with the KGIT operations lead.)*

---

## 6. Escalation policy

A ticket is **escalated to a Team Lead** when any of these is true:

1. **Security or fraud:** unauthorized login, hacked account, unknown charge, phishing, malware/ransomware, data leak.
2. **Legal or reputational risk:** legal threats, media/journalist enquiries, formal complaints.
3. **Data privacy request:** account/data deletion requests.
3b. **HR-sensitive matter:** harassment, discrimination, bullying, threats (no AI draft).
4. **Critical priority** or a full service outage.
5. ~~AI confidence is low~~ → *changed in Week 2:* low classifier confidence (< 0.45) sets **needs_human_review** (agent confirms the category) instead of escalating; a weak FAQ match (< 0.30) means **no AI draft**. See `issue_log.md` DEC-01…03.
6. **SLA breach:** first-response or resolution time exceeded.
7. **Repeated contact:** same customer, same issue, 3+ times, or the customer is angry about support.
8. **Prompt-injection or unsafe content** detected in the ticket.

**Escalation rules**
- AI must **not** draft a final answer for categories 1–3; it only summarises the issue.
- Escalated tickets notify the Team Lead and are flagged in the queue.
- Every escalation reason is stored in the audit log.

---

## 7. Functional requirements

| ID | Requirement | Week |
|---|---|---|
| FR-01 | Create, read, update and list tickets via REST API | 2 |
| FR-02 | Auto-classify ticket category with confidence score | 2 |
| FR-03 | Score urgency and assign priority | 2 |
| FR-04 | Route ticket to the correct team | 2 |
| FR-05 | Retrieve relevant FAQs and draft an answer **with citations** | 3 |
| FR-06 | Refuse / escalate when unsure or unsafe | 3 |
| FR-07 | Agent ticket queue and ticket detail UI | 4 |
| FR-08 | Agent can accept, edit or reject each AI suggestion | 4 |
| FR-09 | Log every AI suggestion and human decision (audit trail) | 4 |
| FR-10 | Intake from mock email inbox | 5 |
| FR-11 | Detect duplicate tickets and customer threads | 5 |
| FR-12 | SLA timers and breach flags | 5 |
| FR-13 | Microsoft Lists mapping + mock connector (optional) | 6 |
| FR-14 | Admin-configurable categories and FAQs | 8 |
| FR-15 | Reports: volume, SLA, quality metrics | 8 |

## 8. Non-functional requirements

| ID | Requirement |
|---|---|
| NFR-01 | **Human-in-the-loop:** no customer-facing message is sent without agent approval |
| NFR-02 | **Data:** synthetic or approved anonymized data only; no secrets in Git |
| NFR-03 | **Security:** role-based access control; secrets in environment variables |
| NFR-04 | **Privacy:** PII redacted before text is sent to any external AI model |
| NFR-05 | **Traceability:** answers show FAQ sources; uncertainty and cost are recorded |
| NFR-06 | **Performance:** triage suggestion returned in < 3 s for a single ticket (target) |
| NFR-07 | **Quality:** unit tests for API and routing; evaluation on labeled cases |
| NFR-08 | **Accessibility:** keyboard navigation and readable contrast in the UI |

---

## 9. Data and permissions
- `data/kgit/tickets.csv` + `dev_tickets.csv` (100 hand-written labeled tickets), `train_tickets.csv` (450 template tickets), `faqs.csv` (30 FAQs) — training/development.
- `data/kgit/test_tickets.csv` (50 tickets) — **frozen test set**, never used for training or tuning.
- All data is **fully synthetic**.
- No real KGIT user data, SharePoint or Microsoft 365 access is used.
- FAQs are marked `pending_mentor_review` until approved.

## 10. Open questions for mentor
1. Confirm SLA hours per priority.
2. Confirm the KGIT category list and team names (currently assumed).
3. Confirm the thresholds: classifier review 0.45, retrieval 0.30 (chosen from data in Weeks 2–3).
4. Which LLM / embedding provider is allowed, and the cost budget per ticket?
5. Is a Microsoft 365 sandbox tenant available, or should Week 6 use a mock only?
6. What are KGIT's real helpdesk categories and teams? Can anonymised KGIT tickets be used? (DEC-08, DEC-09)

---

**Approval**

| Role | Name | Decision | Date |
|---|---|---|---|
| Mentor | | ☐ Approved ☐ Changes needed | |
| KGIT Operations Lead | | ☐ Approved ☐ Changes needed | |
