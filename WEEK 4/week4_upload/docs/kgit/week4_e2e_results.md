# Week 4 — end-to-end scenario results

Generated 23 Nov 2026 04:46 by `python -m ml.run_e2e` (fresh in-memory database).

* **Workflow: 20/20 scenarios passed** every check (human decision before any reply, no AI draft for risky tickets, full audit trail, no double or stale decisions).
* **AI matched our expectation in 18/20** scenarios (reported only; misses below).
* Sending is simulated: replies are stored and logged, no email is sent.

| ID | Scenario | AI triage | AI reply | Person decided | Final status | Checks | Result |
|---|---|---|---|---|---|---|---|
| E2E-01 | Password reset, agent approves triage and reply | Access & Accounts · Medium | answered | triage approved, reply approved | Waiting on Customer | 9/9 | PASS |
| E2E-02 | Course missing, agent edits the AI reply | Training & Courses · Medium | answered | triage approved, reply edited | Waiting on Customer | 9/9 | PASS |
| E2E-03 | Whole-team outage, critical, lead writes the reply | IT Support · Critical · escalated | low_confidence | triage approved, reply edited | Waiting on Customer | 10/10 | PASS |
| E2E-04 | Phishing link clicked, AI must not draft, lead writes | IT Support · Critical · escalated | escalated | triage approved, reply edited | Waiting on Customer | 12/12 | PASS |
| E2E-05 | Suspicious login, AI draft rejected, nothing sent | Access & Accounts · Critical · escalated | escalated | triage approved, reply rejected | Escalated | 10/10 | PASS |
| E2E-06 | Salary not credited, approve both | HR & Admin · High | answered | triage approved, reply approved | Waiting on Customer | 9/9 | PASS |
| E2E-07 | Fee charged twice, refund reply | Billing & Finance · High | low_confidence | triage approved, reply edited | Waiting on Customer | 9/9 | PASS |
| E2E-08 | AI picks the wrong category, agent corrects it (team follows) | Training & Courses · Low | low_confidence | triage edited, reply edited | Waiting on Customer | 13/13 | PASS |
| E2E-09 | Agent raises priority, SLA deadline moves | Training & Courses · Medium | answered | triage edited, reply approved | Waiting on Customer | 11/11 | PASS |
| E2E-10 | Harassment report, HR sensitive, lead writes | HR & Admin · High · escalated | escalated | triage approved, reply edited | Waiting on Customer | 12/12 | PASS |
| E2E-11 | Data deletion request, privacy, AI draft rejected | Access & Accounts · High · escalated | escalated | triage approved, reply rejected | Escalated | 10/10 | PASS |
| E2E-12 | Prompt injection in a ticket, refused, rejected | Access & Accounts · Low · escalated | refused | triage rejected, reply rejected | Escalated | 9/9 | PASS |
| E2E-13 | Ticket with phone and email, PII hidden from the AI | Access & Accounts · High | low_confidence | triage approved, reply edited | Waiting on Customer | 11/11 | PASS |
| E2E-14 | Out-of-scope question, AI abstains, agent writes | HR & Admin · Low | low_confidence | triage approved, reply edited | Waiting on Customer | 10/10 | PASS |
| E2E-15 | Angry customer, agent softens the AI reply | Access & Accounts · Low · escalated | answered | triage approved, reply edited | Waiting on Customer | 9/9 | PASS |
| E2E-16 | Laptop crash, approve both | IT Support · Low | low_confidence | triage approved, reply edited | Waiting on Customer | 9/9 | PASS |
| E2E-17 | Legal threat, AI must not draft, lead writes | Billing & Finance · Critical · escalated | escalated | triage approved, reply edited | Waiting on Customer | 12/12 | PASS |
| E2E-18 | Agent rejects the triage, then sets the priority by hand | HR & Admin · Low | answered | triage rejected, reply approved | Waiting on Customer | 10/10 | PASS |
| E2E-19 | Same suggestion cannot be decided twice | HR & Admin · Medium | answered | triage approved, reply approved | Waiting on Customer | 10/10 | PASS |
| E2E-20 | Old draft cannot be approved after a new draft exists | Access & Accounts · High | answered | triage approved, reply approved | Waiting on Customer | 10/10 | PASS |

## Where the AI did not do what we expected

* **E2E-07** Fee charged twice, refund reply: answer: expected answered, AI said low_confidence
* **E2E-08** AI picks the wrong category, agent corrects it (team follows): category: expected IT Support, AI said Training & Courses

## Failed workflow checks

* None.
