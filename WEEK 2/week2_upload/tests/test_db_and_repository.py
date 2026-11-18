"""Week 2 — schema migrations and ticket CRUD (KGIT helpdesk)."""
import pytest

from app import config, db, repository


def test_migrations_create_all_tables(conn):
    assert {"tickets", "users", "teams", "categories", "ai_suggestions", "faqs", "app_settings",
            "schema_migrations"} <= db.table_names(conn)


def test_migrations_run_only_once(make_db):
    c, _ = make_db()
    assert db.migrate(c) == ["0001_init.sql", "0002_faq_store.sql", "0003_app_settings.sql"]
    assert db.migrate(c) == []


def test_database_refuses_data_from_another_domain(conn):
    conn.execute("UPDATE app_settings SET value = 'other-client' WHERE key = 'domain'")
    conn.commit()
    with pytest.raises(RuntimeError):
        db.ensure_domain(conn)


def test_reference_data_seeded(conn):
    assert {r["name"] for r in conn.execute("SELECT name FROM categories")} == set(config.domain().categories)
    assert db.count(conn, "categories") == 5
    assert db.count(conn, "teams") == 6          # 5 KGIT teams + Team Lead
    assert db.count(conn, "users") == 3


def test_create_ticket_is_auto_triaged(conn):
    t = repository.create_ticket(conn, subject="Fee paid twice", body="I was charged twice for the course fee.",
                                 channel="email", customer_ref="EMP-1001")
    assert t["id"] == "TCK-0001"
    assert t["status"] == "Triaged"
    assert t["category"] == "Billing & Finance"
    assert t["priority"] == "High"
    assert t["team"] == "Finance Team"
    assert t["sla_first_response_due"] and t["sla_resolution_due"]


def test_ticket_ids_increment(conn):
    a = repository.create_ticket(conn, subject="Leave", body="How do I apply for leave?", channel="chat", customer_ref="E")
    b = repository.create_ticket(conn, subject="Leave", body="How do I apply for leave?", channel="chat", customer_ref="E")
    assert (a["id"], b["id"]) == ("TCK-0001", "TCK-0002")


def test_escalated_ticket_goes_to_team_lead(conn):
    t = repository.create_ticket(conn, subject="Hacked", body="Someone logged in to my account, I did not do this.",
                                 channel="web_form", customer_ref="E")
    assert t["status"] == "Escalated"
    assert t["team"] == "Team Lead"
    assert t["needs_escalation"] is True
    assert "security_or_fraud" in t["escalation_reasons"]


def test_get_missing_ticket_returns_none(conn):
    assert repository.get_ticket(conn, "TCK-9999") is None


def test_update_ticket_human_override(conn):
    t = repository.create_ticket(conn, subject="Leave", body="How do I apply for leave?", channel="chat", customer_ref="E")
    u = repository.update_ticket(conn, t["id"], {"priority": "High", "status": "In Progress", "id": "HACK"})
    assert u["priority"] == "High" and u["status"] == "In Progress"
    assert u["id"] == t["id"]  # non-updatable fields are ignored


def test_soft_delete(conn):
    t = repository.create_ticket(conn, subject="Leave", body="How do I apply for leave?", channel="chat", customer_ref="E")
    assert repository.delete_ticket(conn, t["id"]) is True
    assert repository.get_ticket(conn, t["id"]) is None
    row = conn.execute("SELECT is_deleted FROM tickets WHERE id = ?", (t["id"],)).fetchone()
    assert row["is_deleted"] == 1
    assert repository.delete_ticket(conn, t["id"]) is False


def test_queue_is_ordered_by_priority(conn):
    repository.seed_tickets_from_csv(conn)
    queue = repository.list_tickets(conn, limit=200)
    order = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3}
    ranks = [order[t["priority"]] for t in queue]
    assert ranks == sorted(ranks)
    assert len(queue) == 50


def test_queue_filters(conn):
    repository.seed_tickets_from_csv(conn)
    it = repository.list_tickets(conn, category="IT Support", limit=200)
    assert it and all(t["category"] == "IT Support" for t in it)
    escalated = repository.list_tickets(conn, escalated=True, limit=200)
    assert escalated and all(t["needs_escalation"] for t in escalated)


def test_sla_starts_from_ticket_creation_time(conn):
    t = repository.create_ticket(conn, subject="Hacked", body="Someone logged in, I did not do this",
                                 channel="email", customer_ref="E", created_at="2026-11-01T10:00:00+00:00")
    assert t["priority"] == "Critical"
    assert t["sla_first_response_due"] == "2026-11-01T11:00:00+00:00"
    assert t["sla_resolution_due"] == "2026-11-01T18:00:00+00:00"


def test_triage_suggestion_is_stored(conn):
    t = repository.create_ticket(conn, subject="VPN", body="The VPN is very slow today.", channel="chat",
                                 customer_ref="E")
    sugg = repository.list_suggestions(conn, t["id"])
    assert len(sugg) == 1 and sugg[0]["kind"] == "triage"
    assert sugg[0]["payload"]["category"] == t["category"]
