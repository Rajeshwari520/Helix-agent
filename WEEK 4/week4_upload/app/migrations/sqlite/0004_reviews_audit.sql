-- 0004_reviews_audit (Week 4): human decisions on AI suggestions + append-only audit trail.

-- One human decision per AI suggestion (approve / edit / reject).
CREATE TABLE suggestion_reviews (
    id             INTEGER PRIMARY KEY,
    suggestion_id  INTEGER NOT NULL UNIQUE REFERENCES ai_suggestions(id),
    ticket_id      TEXT NOT NULL REFERENCES tickets(id),
    kind           TEXT NOT NULL CHECK (kind IN ('triage', 'answer')),
    decision       TEXT NOT NULL CHECK (decision IN ('approved', 'edited', 'rejected')),
    reviewer       TEXT NOT NULL,
    final_payload  TEXT,                                   -- JSON: what the human kept or changed
    reason         TEXT,
    created_at     TEXT NOT NULL
);
CREATE INDEX idx_reviews_ticket ON suggestion_reviews(ticket_id);

-- Every event on a ticket: who (AI or person), what, when. Rows are only ever inserted.
CREATE TABLE audit_log (
    id             INTEGER PRIMARY KEY,
    ticket_id      TEXT REFERENCES tickets(id),
    event          TEXT NOT NULL,
    actor          TEXT NOT NULL,
    suggestion_id  INTEGER REFERENCES ai_suggestions(id),
    details        TEXT NOT NULL DEFAULT '{}',             -- JSON
    created_at     TEXT NOT NULL
);
CREATE INDEX idx_audit_ticket ON audit_log(ticket_id);
CREATE INDEX idx_audit_event  ON audit_log(event);
