-- 0001_init: core ticket schema (Week 2)
-- Written in portable SQL (SQLite now, PostgreSQL later: change TEXT timestamps to TIMESTAMPTZ).

CREATE TABLE teams (
    id          INTEGER PRIMARY KEY,
    name        TEXT NOT NULL UNIQUE
);

CREATE TABLE categories (
    id              INTEGER PRIMARY KEY,
    name            TEXT NOT NULL UNIQUE,
    default_team_id INTEGER NOT NULL REFERENCES teams(id),
    active          INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE users (
    id          INTEGER PRIMARY KEY,
    name        TEXT NOT NULL,
    email       TEXT NOT NULL UNIQUE,
    role        TEXT NOT NULL CHECK (role IN ('customer', 'agent', 'lead', 'admin')),
    team_id     INTEGER REFERENCES teams(id),
    created_at  TEXT NOT NULL
);

CREATE TABLE tickets (
    id                TEXT PRIMARY KEY,                      -- e.g. TCK-0001
    customer_ref      TEXT NOT NULL,
    channel           TEXT NOT NULL CHECK (channel IN ('email', 'web_form', 'chat')),
    subject           TEXT NOT NULL,
    body              TEXT NOT NULL,
    status            TEXT NOT NULL DEFAULT 'New',
    category          TEXT,
    priority          TEXT CHECK (priority IN ('Low', 'Medium', 'High', 'Critical')),
    team              TEXT,
    assignee_id       INTEGER REFERENCES users(id),
    needs_escalation  INTEGER NOT NULL DEFAULT 0,
    escalation_reasons TEXT,                                 -- JSON list
    sla_first_response_due TEXT,
    sla_resolution_due     TEXT,
    is_deleted        INTEGER NOT NULL DEFAULT 0,
    created_at        TEXT NOT NULL,
    updated_at        TEXT NOT NULL
);
CREATE INDEX idx_tickets_status   ON tickets(status);
CREATE INDEX idx_tickets_priority ON tickets(priority);
CREATE INDEX idx_tickets_team     ON tickets(team);

-- Every AI suggestion is stored so a human decision can be linked to it (audit, Week 4)
CREATE TABLE ai_suggestions (
    id             INTEGER PRIMARY KEY,
    ticket_id      TEXT NOT NULL REFERENCES tickets(id),
    kind           TEXT NOT NULL CHECK (kind IN ('triage', 'answer')),
    payload        TEXT NOT NULL,                            -- JSON
    model_version  TEXT NOT NULL,
    latency_ms     REAL,
    created_at     TEXT NOT NULL
);
CREATE INDEX idx_suggestions_ticket ON ai_suggestions(ticket_id);
