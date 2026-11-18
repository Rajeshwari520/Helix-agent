"""Database layer: PostgreSQL (main) or SQLite (quick local fallback).

Choose with the DATABASE_URL environment variable:
    postgresql://helix:helix@localhost:5432/helix_kgit  -> PostgreSQL (needs `pip install psycopg[binary]`)
    sqlite:///helix_kgit.db                             -> SQLite file (fallback)

All SQL in the app is written once with `?` placeholders; the wrapper converts
them to `%s` for PostgreSQL. Rows behave like dicts in both databases.

Migrations live in app/migrations/postgres/*.sql and app/migrations/sqlite/*.sql.
Each file is applied once and recorded in the schema_migrations table.
"""
import sqlite3
from datetime import datetime, timezone

from app import config


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


class Database:
    """Thin wrapper so the rest of the code does not care which database is used."""

    def __init__(self, raw, dialect: str):
        self.raw = raw
        self.dialect = dialect  # "postgres" or "sqlite"

    def execute(self, sql: str, params=()):
        if self.dialect == "postgres":
            return self.raw.execute(sql.replace("?", "%s"), tuple(params) or None)
        return self.raw.execute(sql, tuple(params))

    def executescript(self, script: str) -> None:
        if self.dialect == "postgres":
            self.raw.execute(script)
        else:
            self.raw.executescript(script)

    def commit(self) -> None:
        self.raw.commit()

    def rollback(self) -> None:
        self.raw.rollback()

    def close(self) -> None:
        self.raw.close()


def connect(url: str | None = None) -> Database:
    url = url or config.DATABASE_URL or config.database_url()
    if url.startswith(("postgresql://", "postgres://")):
        try:
            import psycopg
            from psycopg.rows import dict_row
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("PostgreSQL selected but psycopg is not installed: "
                               "pip install \"psycopg[binary]\"") from exc
        return Database(psycopg.connect(url, row_factory=dict_row), "postgres")

    path = url.removeprefix("sqlite:///") if url.startswith("sqlite:///") else url
    raw = sqlite3.connect(path, check_same_thread=False)
    raw.row_factory = sqlite3.Row
    raw.execute("PRAGMA foreign_keys = ON")
    return Database(raw, "sqlite")


def migrate(db: Database) -> list[str]:
    """Apply any migrations that have not run yet. Returns the names applied."""
    db.execute("CREATE TABLE IF NOT EXISTS schema_migrations (name TEXT PRIMARY KEY, applied_at TEXT)")
    db.commit()
    done = {r["name"] for r in db.execute("SELECT name FROM schema_migrations")}
    applied = []
    for path in sorted((config.MIGRATIONS_DIR / db.dialect).glob("*.sql")):
        if path.name in done:
            continue
        db.executescript(path.read_text(encoding="utf-8"))
        db.execute("INSERT INTO schema_migrations (name, applied_at) VALUES (?, ?)", (path.name, now_iso()))
        db.commit()
        applied.append(path.name)
    return applied


def table_names(db: Database) -> set[str]:
    if db.dialect == "postgres":
        sql = "SELECT table_name AS name FROM information_schema.tables WHERE table_schema = current_schema()"
    else:
        sql = "SELECT name FROM sqlite_master WHERE type = 'table'"
    return {r["name"] for r in db.execute(sql)}


def count(db: Database, table: str) -> int:
    return db.execute(f"SELECT COUNT(*) AS n FROM {table}").fetchone()["n"]


def seed_reference_data(db: Database) -> None:
    """Teams, categories and demo users for the active domain (idempotent)."""
    teams = config.domain().teams
    for team in list(teams.values()) + [config.ESCALATION_TEAM]:
        db.execute("INSERT INTO teams (name) VALUES (?) ON CONFLICT (name) DO NOTHING", (team,))
    for cat, team in teams.items():
        db.execute(
            "INSERT INTO categories (name, default_team_id) "
            "VALUES (?, (SELECT id FROM teams WHERE name = ?)) ON CONFLICT (name) DO NOTHING", (cat, team))
    demo_users = [
        ("Demo Agent", "agent@helix.local", "agent", list(teams.values())[0]),
        ("Demo Lead", "lead@helix.local", "lead", config.ESCALATION_TEAM),
        ("Demo Admin", "admin@helix.local", "admin", None),
    ]
    for name, email, role, team in demo_users:
        db.execute(
            "INSERT INTO users (name, email, role, team_id, created_at) "
            "VALUES (?, ?, ?, (SELECT id FROM teams WHERE name = ?), ?) ON CONFLICT (email) DO NOTHING",
            (name, email, role, team, now_iso()))
    db.commit()


def ensure_domain(db: Database) -> str:
    """Record the domain on first start; refuse to start if the database belongs to another domain."""
    current = config.domain().name
    row = db.execute("SELECT value FROM app_settings WHERE key = 'domain'").fetchone()
    if row is None:
        db.execute("INSERT INTO app_settings (key, value) VALUES ('domain', ?)", (current,))
        db.commit()
        return current
    if row["value"] != current:
        raise RuntimeError(
            f"This database holds '{row['value']}' data but HELIX_DOMAIN is '{current}'. "
            f"Use a separate database for each domain (set DATABASE_URL).")
    return current
