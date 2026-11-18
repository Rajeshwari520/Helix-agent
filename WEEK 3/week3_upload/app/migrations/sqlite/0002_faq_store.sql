-- 0002_faq_store: versioned FAQ knowledge store (Week 3)
-- Each edit creates a NEW row (new version). Only rows with status='approved'
-- and is_current=1 are used by the RAG answer service.

CREATE TABLE faqs (
    row_id       INTEGER PRIMARY KEY,
    faq_id       TEXT NOT NULL,                               -- e.g. FAQ-001 (stable across versions)
    version      INTEGER NOT NULL,
    category     TEXT NOT NULL,
    question     TEXT NOT NULL,
    answer       TEXT NOT NULL,
    status       TEXT NOT NULL CHECK (status IN ('draft', 'approved', 'retired')),
    is_current   INTEGER NOT NULL DEFAULT 0,
    approved_by  TEXT,
    created_at   TEXT NOT NULL,
    approved_at  TEXT,
    UNIQUE (faq_id, version)
);
CREATE INDEX idx_faqs_current ON faqs(is_current, status);
