"""Week 2 — classifier, urgency scoring and routing engine (KGIT helpdesk)."""
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import pytest

from app import config
from app.services import classifier, priority
from app.services.triage import sla_due, triage

SCENARIOS = json.loads((Path(__file__).parent / "scenarios.json").read_text())


# ------------------------------------------------------------------ domain
def test_kgit_domain_is_active():
    d = config.domain()
    assert d.name == "kgit"
    assert d.categories == ["IT Support", "Access & Accounts", "Training & Courses", "HR & Admin", "Billing & Finance"]


# ------------------------------------------------------------------ classifier
def test_classifier_returns_known_category_and_confidence():
    p = classifier.predict("my laptop is very slow")
    assert p["category"] in config.domain().categories
    assert 0 <= p["confidence"] <= 1
    assert len(p["alternatives"]) == 2


def test_classifier_accuracy_on_frozen_test_set():
    """test_tickets.csv is never used for training or tuning (see data/kgit/test_set_frozen.sha256)."""
    df = pd.read_csv(config.domain().data_dir / "test_tickets.csv")
    preds = [classifier.predict(f"{s}. {b}")["category"] for s, b in zip(df.subject, df.body)]
    accuracy = (pd.Series(preds) == df.category).mean()
    assert accuracy >= 0.90, f"classifier accuracy dropped to {accuracy:.2f}"


def test_frozen_test_set_is_unchanged():
    import hashlib
    data = (config.domain().data_dir / "test_tickets.csv").read_bytes()
    expected = (config.domain().data_dir / "test_set_frozen.sha256").read_text().split()[0]
    assert hashlib.sha256(data).hexdigest() == expected


def test_test_set_is_not_in_training_data():
    from app.services.classifier import training_data
    test = pd.read_csv(config.domain().data_dir / "test_tickets.csv")
    train_texts = set(training_data()["text"])
    assert not any(f"{s}. {b}".lower() in train_texts for s, b in zip(test.subject, test.body))


# --------------------------------------------------------------- urgency score
@pytest.mark.parametrize("text,expected", [
    ("someone hacked my account", "Critical"),
    ("we will send a legal notice", "Critical"),
    ("the VPN is down for all employees", "Critical"),
    ("I was charged twice for the course fee", "High"),
    ("my laptop crashes and I cannot work", "High"),
    ("my salary has not been credited", "High"),
    ("I want to report harassment by a colleague", "High"),
    ("outlook is not syncing", "Medium"),
    ("the LMS video is buffering", "Medium"),
    ("how do I apply for leave?", "Low"),
    ("thanks for the great training session", "Low"),
])
def test_priority_levels(text, expected):
    assert priority.score(text)["priority"] == expected


def test_invoice_amount_is_not_mistaken_for_http_500():
    assert priority.score("invoice shows 4,500 instead of 3,900")["priority"] != "Critical"


def test_priority_gives_reasons():
    r = priority.score("URGENT!! I was charged twice")
    assert r["urgency_score"] == 4
    assert any("money" in reason for reason in r["reasons"])
    assert any("urgent" in reason for reason in r["reasons"])


# --------------------------------------------------------------------- routing
def test_every_category_has_a_team():
    teams = config.domain().teams
    assert len(teams) == 5 and all(teams.values())


@pytest.mark.parametrize("subject,body,category,team", [
    ("VPN", "The VPN is very slow today", "IT Support", "IT Service Desk"),
    ("Fee paid twice", "I was charged twice for the course fee.", "Billing & Finance", "Finance Team"),
    ("Salary", "Salary not credited", "HR & Admin", "HR & Admin Team"),
])
def test_ticket_routes_to_category_team(subject, body, category, team):
    r = triage(subject, body)
    assert r["category"] == category and r["team"] == team and not r["needs_escalation"]


def test_risky_ticket_routes_to_team_lead():
    r = triage("Hacked", "Someone logged in to my account, I did not do this.")
    assert r["team"] == "Team Lead" and r["needs_escalation"]
    assert r["suggested_team"] == config.domain().teams[r["category"]]


def test_low_confidence_is_flagged_for_human_review(monkeypatch):
    monkeypatch.setattr(config, "CLASSIFIER_CONFIDENCE_THRESHOLD", 0.99)
    r = triage("Question", "hello")
    assert r["needs_human_review"] and "low_classifier_confidence" in r["review_reasons"]


def test_sla_due_dates_follow_priority():
    start = datetime(2026, 11, 18, 9, 0, tzinfo=timezone.utc)
    assert sla_due("Critical", start)["first_response_due"].startswith("2026-11-18T10:00")
    assert sla_due("Low", start)["resolution_due"].startswith("2026-11-21T09:00")


def test_pii_is_redacted_before_classification():
    r = triage("Refund", "My card 4111 1111 1111 1111 was charged twice, call 9876543210")
    assert set(r["pii_found"]) >= {"CARD", "PHONE"}


# ---------------------------------------------------------- seeded scenarios
@pytest.mark.parametrize("s", SCENARIOS, ids=[s["id"] for s in SCENARIOS])
def test_seeded_scenarios(s):
    r = triage(s["subject"], s["body"])
    assert r["needs_escalation"] == s["escalate"], r["escalation_reasons"]
    assert r["priority"] in s["priority"], r["priority_reasons"]
    if s["category"]:
        # a wrong category is only acceptable if the system asked a human to check it
        assert r["category"] == s["category"] or r["needs_human_review"], (r["category"], r["category_confidence"])
