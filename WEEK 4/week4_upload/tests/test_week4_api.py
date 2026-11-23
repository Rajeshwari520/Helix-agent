"""Week 4 API: agent page, queue, meta, review endpoint and audit endpoints. Skipped if fastapi is missing."""
import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")
from fastapi.testclient import TestClient  # noqa: E402

from app import config  # noqa: E402


@pytest.fixture
def client(tmp_path, monkeypatch, make_db):
    from tests.conftest import TEST_DATABASE_URL
    url = make_db()[1] if TEST_DATABASE_URL else f"sqlite:///{tmp_path / 'w4.db'}"
    monkeypatch.setattr(config, "DATABASE_URL", url)
    config.set_domain("kgit")
    from app.main import app
    with TestClient(app) as c:
        yield c


def triage_id(client, tid):
    return [s for s in client.get(f"/tickets/{tid}/suggestions").json() if s["kind"] == "triage"][-1]["id"]


def test_pages_and_lists(client):
    assert "Agent workspace" in client.get("/agent").text
    assert '<div id="root">' in client.get("/dashboard").text          # same React app, dashboard view
    js = client.get("/ui/app.js")
    assert js.status_code == 200 and js.headers["content-type"].startswith("text/javascript")
    assert client.get("/ui/app.css").status_code == 200
    assert client.get("/ui/index.html").status_code == 404             # only the two bundle files are served
    q = client.get("/queue", params={"clock": "demo"}).json()
    assert len(q["tickets"]) > 0 and q["sla_clock"]["mode"] == "demo"
    m = client.get("/meta").json()
    assert "Team Lead" in m["teams"] and len(m["categories"]) == 5


def test_review_flow_and_status_codes(client):
    tid = "TCK-0011"
    sid = triage_id(client, tid)
    url = f"/tickets/{tid}/suggestions/{sid}/review"
    assert client.post(url, json={"decision": "approve"}).status_code == 422               # no reviewer
    assert client.post(url, json={"decision": "maybe", "reviewer": "Raj"}).status_code == 422
    assert client.post(url, json={"decision": "reject", "reviewer": "Raj"}).status_code == 422  # no reason
    assert client.post(url, json={"decision": "edit", "reviewer": "Raj", "category": "Delivery"}).status_code == 422
    r = client.post(url, json={"decision": "edit", "reviewer": "Raj", "priority": "High"})
    assert r.status_code == 200 and r.json()["ticket"]["priority"] == "High"
    assert client.post(url, json={"decision": "approve", "reviewer": "Raj"}).status_code == 409
    assert client.post(f"/tickets/{tid}/suggestions/999999/review",
                       json={"decision": "approve", "reviewer": "Raj"}).status_code == 404

    ans = client.post(f"/tickets/{tid}/answer").json()
    assert ans["requires_human_approval"] and ans["suggestion_id"]
    r = client.post(f"/tickets/{tid}/suggestions/{ans['suggestion_id']}/review",
                    json={"decision": "approve", "reviewer": "Raj"})
    assert r.status_code == 200 and r.json()["reply_sent"] and r.json()["ticket"]["status"] == "Waiting on Customer"

    trail = client.get(f"/tickets/{tid}/audit").json()
    assert [e["event"] for e in trail][-3:] == ["suggestion_approved", "reply_sent", "ticket_updated"]
    assert client.get("/audit", params={"event": "reply_sent"}).json()[0]["ticket_id"] == tid
    assert client.get("/tickets/TCK-9999/audit").status_code == 404


def test_patch_and_delete_record_who(client):
    assert client.patch("/tickets/TCK-0002", json={"status": "In Progress", "changed_by": "Raj"}).status_code == 200
    assert client.delete("/tickets/TCK-0003", params={"deleted_by": "Lead"}).status_code == 204
    assert client.get("/tickets/TCK-0002/audit").json()[-1]["actor"] == "Raj"
    assert client.get("/audit", params={"event": "ticket_deleted"}).json()[0]["actor"] == "Lead"


def test_system_info(client):
    s = client.get("/system").json()
    assert s["version"] == client.get("/health").json()["version"]
    assert s["database"]["rows"]["tickets"] == 50 and "0004_reviews_audit.sql" in s["database"]["migrations"]
    assert s["ai"]["approved_faqs"] == 30 and s["ai"]["corpus_version"].startswith("kb-kgit-")
    assert "password" not in str(s).lower() and "database_url" not in str(s).lower()
