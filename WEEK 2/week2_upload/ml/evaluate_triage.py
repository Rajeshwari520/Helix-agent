"""Evaluate triage (category, priority, escalation) on a labeled ticket file.

  python -m ml.evaluate_triage data/kgit/test_tickets.csv            # summary only
  python -m ml.evaluate_triage data/kgit/dev_tickets.csv --errors    # also list errors (dev sets only!)

The frozen TEST set (data/kgit/test_tickets.csv) must only be scored, never tuned on:
do not use --errors on it while developing.
"""
import argparse
import json

import pandas as pd

from app.services.triage import triage


def evaluate(path: str, show_errors: bool = False) -> dict:
    df = pd.read_csv(path)
    r = [triage(s, b) for s, b in zip(df.subject, df.body)]
    cat = pd.Series([x["category"] for x in r]) == df.category
    pri = pd.Series([x["priority"] for x in r]) == df.priority
    esc = pd.Series(["Yes" if x["needs_escalation"] else "No" for x in r]) == df.needs_escalation
    rev = pd.Series([x["needs_human_review"] for x in r])
    risky = df.needs_escalation == "Yes"
    out = {
        "file": path, "tickets": len(df),
        "category_accuracy": round(cat.mean(), 3),
        "priority_accuracy": round(pri.mean(), 3),
        "escalation_accuracy": round(esc.mean(), 3),
        "risky_tickets_caught": round(esc[risky].mean(), 3),
        "all_three_correct": round((cat & pri & esc).mean(), 3),
        "category_correct_or_flagged": round((cat | rev).mean(), 3),
        "flagged_for_review": int(rev.sum()),
    }
    if show_errors:
        out["errors"] = [
            {"id": df.ticket_id[i], "subject": df.subject[i],
             "category": (df.category[i], r[i]["category"], r[i]["category_confidence"]) if not cat[i] else None,
             "priority": (df.priority[i], r[i]["priority"], r[i]["priority_reasons"]) if not pri[i] else None,
             "escalation": (df.needs_escalation[i], r[i]["escalation_reasons"]) if not esc[i] else None}
            for i in range(len(df)) if not (cat[i] and pri[i] and esc[i])]
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    ap.add_argument("--errors", action="store_true")
    a = ap.parse_args()
    print(json.dumps(evaluate(a.path, a.errors), indent=2, default=str))
