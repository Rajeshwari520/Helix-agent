"""Dashboard numbers (service) + page/stats endpoints (API, skipped if fastapi is missing)."""
from datetime import datetime, timedelta, timezone

import pytest

from app import db, repository
from app.services import dashboard, knowledge


@pytest.fixture
def seeded(make_db, domain):
    conn, _ = make_db()
    db.migrate(conn)
    db.ensure_domain(conn)
    db.seed_reference_data(conn)
    knowledge.load_from_csv(conn)
    repository.seed_tickets_from_csv(conn)
    yield conn
    conn.close()


def test_counts_add_up(seeded):
    s = dashboard.stats(seeded)
    assert s["kpis"]["total"] == 50
    assert sum(s["by_priority"].values()) == 50
    assert sum(s["by_category"].values()) == 50
    assert sum(s["sla"].values()) == s["kpis"]["open"]
    assert s["knowledge"]["approved_faqs"] == 30


def test_queue_is_most_urgent_first(seeded):
    order = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3}
    ranks = [order[t["priority"]] for t in dashboard.stats(seeded)["queue"]]
    assert ranks == sorted(ranks)


def test_escalated_count_matches_tickets(seeded):
    escalated = len(repository.list_tickets(seeded, escalated=True, limit=500))
    assert dashboard.stats(seeded)["kpis"]["escalated"] == escalated


def test_sla_state():
    now = datetime(2026, 11, 10, 12, 0, tzinfo=timezone.utc)
    t = lambda due, status="Triaged": {"status": status, "sla_first_response_due": due.isoformat()}
    assert dashboard.sla_state(t(now - timedelta(minutes=1)), now) == "breached"
    assert dashboard.sla_state(t(now + timedelta(hours=2)), now) == "due_soon"
    assert dashboard.sla_state(t(now + timedelta(hours=10)), now) == "on_track"
    assert dashboard.sla_state(t(now - timedelta(hours=5), "Resolved"), now) == "closed"


def test_demo_clock_is_one_hour_after_newest_ticket(seeded):
    s = dashboard.stats(seeded, clock="demo")
    newest = max(t["created_at"] for t in s["queue"])
    assert s["sla_clock"]["mode"] == "demo"
    assert datetime.fromisoformat(s["sla_clock"]["as_of"]) == datetime.fromisoformat(newest) + timedelta(hours=1)
    # in real time the early-November demo tickets are all overdue
    real = dashboard.stats(seeded, now=datetime(2026, 12, 1, tzinfo=timezone.utc))
    assert real["sla"]["breached"] == real["kpis"]["open"]


def test_new_ticket_shows_up(seeded):
    before = dashboard.stats(seeded)["kpis"]["total"]
    repository.create_ticket(seeded, subject="VPN not working", body="VPN fails for the whole team today",
                             channel="chat", customer_ref="CUST-ANON")
    assert dashboard.stats(seeded)["kpis"]["total"] == before + 1


def test_model_metrics_are_read_from_docs(seeded):
    m = dashboard.stats(seeded)["model_metrics"]
    if not m:
        pytest.skip("docs/kgit metric files not present")
    assert 0 <= m["classifier"]["category_accuracy"] <= 1


def test_dashboard_page_and_stats_endpoint(tmp_path, monkeypatch):
    pytest.importorskip("fastapi")
    pytest.importorskip("httpx")
    from fastapi.testclient import TestClient
    from app import config
    monkeypatch.setattr(config, "DATABASE_URL", f"sqlite:///{tmp_path / 'dash.db'}")
    config.set_domain("kgit")
    from app.main import app
    with TestClient(app) as c:
        page = c.get("/dashboard")
        assert page.status_code == 200 and "Helix Agent" in page.text
        s = c.get("/dashboard/stats?clock=demo").json()
        assert s["kpis"]["total"] == 50 and s["sla_clock"]["mode"] == "demo"
        assert c.get("/dashboard/stats?clock=bad").status_code == 422
        assert c.get("/", follow_redirects=False).headers["location"] == "/dashboard"


def test_react_bundle_is_built():
    """The built React UI must be committed so the app runs without Node (rebuild: cd frontend && npm run build)."""
    from app import config
    ui = config.ROOT / "app" / "static" / "ui"
    assert (ui / "index.html").exists() and (ui / "app.css").exists()
    assert (ui / "app.js").stat().st_size > 50_000
