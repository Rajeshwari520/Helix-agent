"""Test fixtures.

By default tests use an in-memory SQLite database (fast, no setup).
To run the SAME tests against PostgreSQL:

    set TEST_DATABASE_URL=postgresql://helix:helix@localhost:5432/helix      (Windows cmd)
    $env:TEST_DATABASE_URL="postgresql://helix:helix@localhost:5432/helix"  (PowerShell)
    python -m pytest -q

Each PostgreSQL test gets its own temporary schema, dropped afterwards.
"""
import os
import sys
import uuid
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import config, db  # noqa: E402
from app.services import knowledge  # noqa: E402
from app.services.retriever import FAQRetriever  # noqa: E402

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")


def _with_search_path(url: str, schema: str) -> str:
    sep = "&" if "?" in url else "?"
    return f"{url}{sep}options=-csearch_path%3D{schema}"


@pytest.fixture
def make_db():
    """Factory: returns (Database, url) for a brand-new empty database."""
    created = []

    def _make():
        if TEST_DATABASE_URL:
            schema = "t_" + uuid.uuid4().hex[:12]
            admin = db.connect(TEST_DATABASE_URL)
            admin.execute(f"CREATE SCHEMA {schema}")
            admin.commit()
            admin.close()
            url = _with_search_path(TEST_DATABASE_URL, schema)
            created.append(schema)
            return db.connect(url), url
        return db.connect(":memory:"), ":memory:"

    yield _make
    for schema in created:
        admin = db.connect(TEST_DATABASE_URL)
        admin.execute(f"DROP SCHEMA {schema} CASCADE")
        admin.commit()
        admin.close()


@pytest.fixture(params=["kgit"])
def domain(request):
    d = config.set_domain(request.param)
    yield d
    config.set_domain("kgit")


@pytest.fixture
def conn(make_db, domain):
    """Fresh database with migrations, reference data and FAQs for the active domain."""
    c, _ = make_db()
    db.migrate(c)
    db.ensure_domain(c)
    db.seed_reference_data(c)
    knowledge.load_from_csv(c)
    yield c
    c.close()


@pytest.fixture
def retriever(conn):
    return FAQRetriever(knowledge.current_faqs(conn)), knowledge.corpus_version(conn)
