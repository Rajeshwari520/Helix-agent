"""Backend facts for the "Backend" page and GET /system (read-only, no secrets)."""
from app import config, db
from app.services import classifier, knowledge
from app.services.retriever import RETRIEVER_VERSION

VERSION = "0.5.0"
TABLES = ["tickets", "ai_suggestions", "suggestion_reviews", "audit_log", "faqs", "users", "teams", "categories"]


def info(conn) -> dict:
    latency = {r["kind"]: {"avg_ms": round(r["avg"] or 0, 1), "max_ms": round(r["mx"] or 0, 1), "count": r["n"]}
               for r in conn.execute("SELECT kind, AVG(latency_ms) AS avg, MAX(latency_ms) AS mx, COUNT(*) AS n "
                                     "FROM ai_suggestions GROUP BY kind")}
    return {
        "version": VERSION,
        "domain": config.domain().name,
        "database": {
            "engine": "PostgreSQL" if conn.dialect == "postgres" else "SQLite",
            "migrations": [r["name"] for r in conn.execute("SELECT name FROM schema_migrations ORDER BY name")],
            "rows": {t: db.count(conn, t) for t in TABLES},
        },
        "ai": {
            "classifier": classifier.MODEL_VERSION,
            "classifier_threshold": config.CLASSIFIER_CONFIDENCE_THRESHOLD,
            "retriever": RETRIEVER_VERSION,
            "retrieval_min_score": config.RETRIEVAL_MIN_SCORE,
            "retrieval_top_k": config.RETRIEVAL_TOP_K,
            "corpus_version": knowledge.corpus_version(conn),
            "approved_faqs": len(knowledge.current_faqs(conn)),
            "latency": latency,
        },
        "sla_hours": {k: {"first_response": v[0], "resolution": v[1]} for k, v in config.SLA_HOURS.items()},
    }
