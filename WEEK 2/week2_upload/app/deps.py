"""Shared FastAPI dependencies."""
from app import db
from app.services import knowledge
from app.services.retriever import FAQRetriever

_retriever_cache: dict = {}


def get_db():
    conn = db.connect()
    try:
        yield conn
    finally:
        conn.close()


def get_retriever(conn) -> tuple[FAQRetriever, str]:
    """Rebuild the retriever only when the approved corpus changes."""
    version = knowledge.corpus_version(conn)
    if _retriever_cache.get("version") != version:
        _retriever_cache["retriever"] = FAQRetriever(knowledge.current_faqs(conn))
        _retriever_cache["version"] = version
    return _retriever_cache["retriever"], version
