"""Versioned FAQ knowledge store.

Rules:
  * An FAQ is identified by faq_id (FAQ-001). Each edit adds a new VERSION row.
  * New versions start as 'draft'. Only an approved version becomes current.
  * The RAG service only reads rows where status='approved' AND is_current=1.
  * corpus_version() returns a hash of the current approved corpus, stored with
    every AI answer so we know exactly which knowledge was used.
"""
import csv
import hashlib
import json

from app import config, db
from app.db import now_iso


def _dict(row):
    return dict(row) if row else None


def load_from_csv(conn, csv_path=None, approved_by: str = "seed: synthetic prototype data") -> int:
    """Import data/faqs.csv as version 1 (approved) if the store is empty."""
    if db.count(conn, "faqs"):
        return 0
    with open(csv_path or config.domain().data_dir / "faqs.csv", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    ts = now_iso()
    for r in rows:
        conn.execute(
            "INSERT INTO faqs (faq_id, version, category, question, answer, status, is_current, approved_by, "
            "created_at, approved_at) VALUES (?, 1, ?, ?, ?, 'approved', 1, ?, ?, ?)",
            (r["faq_id"], r["category"], r["question"], r["answer"], approved_by, ts, ts))
    conn.commit()
    return len(rows)


def current_faqs(conn, category: str | None = None) -> list[dict]:
    sql = "SELECT * FROM faqs WHERE status = 'approved' AND is_current = 1"
    args = []
    if category:
        sql += " AND category = ?"
        args.append(category)
    return [dict(r) for r in conn.execute(sql + " ORDER BY faq_id", args)]


def get_faq(conn, faq_id: str) -> dict | None:
    return _dict(conn.execute("SELECT * FROM faqs WHERE faq_id = ? AND is_current = 1", (faq_id,)).fetchone())


def history(conn, faq_id: str) -> list[dict]:
    return [dict(r) for r in conn.execute("SELECT * FROM faqs WHERE faq_id = ? ORDER BY version", (faq_id,))]


def propose_version(conn, faq_id: str | None, category: str, question: str, answer: str) -> dict:
    """Create a draft. faq_id=None creates a brand-new FAQ."""
    if faq_id is None:
        last = conn.execute("SELECT faq_id FROM faqs ORDER BY faq_id DESC LIMIT 1").fetchone()
        faq_id = f"FAQ-{int(last['faq_id'].split('-')[1]) + 1 if last else 1:03d}"
        version = 1
    else:
        row = conn.execute("SELECT MAX(version) AS v FROM faqs WHERE faq_id = ?", (faq_id,)).fetchone()
        if row["v"] is None:
            raise KeyError(faq_id)
        version = row["v"] + 1
    conn.execute(
        "INSERT INTO faqs (faq_id, version, category, question, answer, status, is_current, created_at) "
        "VALUES (?, ?, ?, ?, ?, 'draft', 0, ?)", (faq_id, version, category, question, answer, now_iso()))
    conn.commit()
    return _dict(conn.execute("SELECT * FROM faqs WHERE faq_id = ? AND version = ?", (faq_id, version)).fetchone())


def approve(conn, faq_id: str, version: int, approved_by: str) -> dict:
    row = conn.execute("SELECT * FROM faqs WHERE faq_id = ? AND version = ?", (faq_id, version)).fetchone()
    if row is None:
        raise KeyError(f"{faq_id} v{version}")
    conn.execute("UPDATE faqs SET is_current = 0 WHERE faq_id = ?", (faq_id,))
    conn.execute("UPDATE faqs SET status = 'retired' WHERE faq_id = ? AND status = 'approved'", (faq_id,))
    conn.execute("UPDATE faqs SET status = 'approved', is_current = 1, approved_by = ?, approved_at = ? "
                 "WHERE faq_id = ? AND version = ?", (approved_by, now_iso(), faq_id, version))
    conn.commit()
    return get_faq(conn, faq_id)


def corpus_version(conn) -> str:
    rows = conn.execute("SELECT faq_id, version FROM faqs WHERE status = 'approved' AND is_current = 1 "
                        "ORDER BY faq_id").fetchall()
    payload = [config.domain().name] + [[r["faq_id"], r["version"]] for r in rows]
    digest = hashlib.sha256(json.dumps(payload).encode()).hexdigest()[:12]
    return f"kb-{config.domain().name}-{digest}"


def export_snapshot(conn, path) -> dict:
    """Write the current approved corpus to a JSON file (evidence of the versioned corpus)."""
    snapshot = {"corpus_version": corpus_version(conn), "exported_at": now_iso(),
                "faqs": [{k: f[k] for k in ("faq_id", "version", "category", "question", "answer", "approved_by")}
                         for f in current_faqs(conn)]}
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(snapshot, fh, indent=2)
    return snapshot
