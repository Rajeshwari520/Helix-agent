"""Triage = classify category + score priority + route to team + escalation check + SLA."""
import time
from datetime import datetime, timedelta, timezone

from app import config
from app.services import classifier, guardrails, priority


def sla_due(priority_level: str, created_at: datetime | None = None) -> dict:
    start = created_at or datetime.now(timezone.utc)
    first, resolve = config.SLA_HOURS[priority_level]
    fmt = lambda d: d.replace(microsecond=0).isoformat()
    return {"first_response_due": fmt(start + timedelta(hours=first)),
            "resolution_due": fmt(start + timedelta(hours=resolve))}


def triage(subject: str, body: str, created_at: datetime | None = None) -> dict:
    t0 = time.perf_counter()
    text = f"{subject}. {body}"

    guard = guardrails.check(text)
    cat = classifier.predict(guard["redacted_text"])
    pri = priority.score(text)

    # Risk-based escalation -> Team Lead
    reasons = list(guard["sensitive_topics"])
    if guard["prompt_injection"]:
        reasons.append("prompt_injection")
    if pri["priority"] == "Critical":
        reasons.append("critical_priority")
    escalate = bool(reasons)

    # Uncertainty -> a human must confirm the category before routing is trusted
    review_reasons = []
    if cat["confidence"] < config.CLASSIFIER_CONFIDENCE_THRESHOLD:
        review_reasons.append("low_classifier_confidence")

    team = config.domain().teams[cat["category"]]
    return {
        "category": cat["category"],
        "category_confidence": cat["confidence"],
        "category_alternatives": cat["alternatives"],
        "priority": pri["priority"],
        "urgency_score": pri["urgency_score"],
        "priority_reasons": pri["reasons"],
        "team": config.ESCALATION_TEAM if escalate else team,
        "suggested_team": team,
        "needs_escalation": escalate,
        "escalation_reasons": reasons,
        "needs_human_review": bool(review_reasons),
        "review_reasons": review_reasons,
        "ai_answer_allowed": guard["ai_answer_allowed"],
        "pii_found": guard["pii_found"],
        "sla": sla_due(pri["priority"], created_at),
        "model_version": cat["model_version"],
        "latency_ms": round((time.perf_counter() - t0) * 1000, 1),
    }
