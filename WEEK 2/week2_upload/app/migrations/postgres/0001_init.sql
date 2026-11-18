-- 0001_init: core ticket schema (Week 2) — PostgreSQL
-- Timestamps are stored as ISO-8601 text (same as the SQLite version) so the API
-- returns identical JSON from both databases.

CREATE TABLE teams (
    id          SERIAL PRIMARY KEY,
    name        TEXT NOT NULL UNIQUE
);

CREATE TABLE categories (
    id              SERIAL PRIMARY KEY,
    name            TEXT NOT NULL UNIQUE,
    default_team_id INTEGER NOT NULL REFERENCES teams(id),
    active          SMALLINT NOT NULL DEFAULT 1
);

CREATE TABLE users (
    id          SERIAL PRIMARY KEY,
    name        TEXT NOT NULL,
    email       TEXT NOT NULL UNIQUE,
    role        TEXT NOT NULL CHECK (role IN ('customer', 'agent', 'lead', 'admin')),
    team_id     INTEGER REFERENCES teams(id),
    created_at  TEXT NOT NULL
);

CREATE TABLE tickets (
    id                 TEXT PRIMARY KEY,                     -- e.g. TCK-0001
    customer_ref       TEXT NOT NULL,
    channel            TEXT NOT NULL CHECK (channel IN ('email', 'web_form', 'chat')),
    subject            TEXT NOT NULL,
    body               TEXT NOT NULL,
    status             TEXT NOT NULL DEFAULT 'New',
    category           TEXT,
    priority           TEXT CHECK (priority IN ('Low', 'Medium', 'High', 'Critical')),
    team               TEXT,
    assignee_id        INTEGER REFERENCES users(id),
    needs_escalation   SMALLINT NOT NULL DEFAULT 0,
    escalation_reasons TEXT,                                 -- JSON list
    sla_first_response_due TEXT,
    sla_resolution_due     TEXT,
    is_deleted         SMALLINT NOT NULL DEFAULT 0,
    created_at         TEXT NOT NULL,
    updated_at         TEXT NOT NULL
);
CREATE INDEX idx_tickets_status   ON tickets(status);
CREATE INDEX idx_tickets_priority ON tickets(priority);
CREATE INDEX idx_tickets_team     ON tickets(team);

CREATE TABLE ai_suggestions (
    id             SERIAL PRIMARY KEY,
    ticket_id      TEXT NOT NULL REFERENCES tickets(id),
    kind           TEXT NOT NULL CHECK (kind IN ('triage', 'answer')),
    payload        TEXT NOT NULL,                            -- JSON
    model_version  TEXT NOT NULL,
    latency_ms     DOUBLE PRECISION,
    created_at     TEXT NOT NULL
);
CREATE INDEX idx_suggestions_ticket ON ai_suggestions(ticket_id);
