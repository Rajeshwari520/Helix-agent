"""Week 3 — RAG scorecard on the 50 synthetic tickets of a domain.

data/<domain>/rag_eval.csv gives the expected outcome per ticket:
  FAQ-xxx   -> the FAQ that should be cited first
  NONE      -> no approved FAQ covers it; the system should NOT answer
  ESCALATE  -> sensitive ticket; AI must not draft an answer

Run from the project root:
  python -m ml.evaluate_rag
"""
import argparse
import json

import pandas as pd

from app import config, db
from app.services import knowledge, rag
from app.services.retriever import FAQRetriever


def outcome(expected: str, res: dict) -> str:
    top = res["citations"][0]["faq_id"] if res["citations"] else None
    if expected == "ESCALATE":
        return "correct_escalation" if res["status"] in ("escalated", "refused") else "missed_escalation"
    if res["status"] in ("escalated", "refused"):
        return "unnecessary_escalation"
    if expected == "NONE":
        return "correct_abstain" if res["status"] == "low_confidence" else "answered_without_faq"
    if res["status"] == "low_confidence":
        return "missed_answer"
    return "correct_answer" if top == expected else "wrong_faq"


def evaluate(threshold: float, retriever, corpus_version, tickets, expected) -> dict:
    config.RETRIEVAL_MIN_SCORE = threshold
    rows = []
    for _, t in tickets.iterrows():
        res = rag.answer(f"{t['subject']}. {t['body']}", retriever, corpus_version)
        rows.append({"ticket_id": t["ticket_id"], "expected": expected[t["ticket_id"]],
                     "status": res["status"], "top_faq": res["citations"][0]["faq_id"] if res["citations"] else None,
                     "score": res["confidence"], "outcome": outcome(expected[t["ticket_id"]], res)})
    df = pd.DataFrame(rows)
    df["top_faq"] = df["top_faq"].fillna("-")
    counts = df["outcome"].value_counts().to_dict()
    answerable = (df["expected"].str.startswith("FAQ")).sum()
    answered = df["status"].eq("answered").sum()
    return {
        "threshold": threshold,
        "counts": counts,
        "answer_precision": round(counts.get("correct_answer", 0) / answered, 3) if answered else None,
        "answer_coverage": round(counts.get("correct_answer", 0) / answerable, 3),
        "escalation_recall": round(counts.get("correct_escalation", 0) / (df["expected"] == "ESCALATE").sum(), 3),
        "rows": df,
    }


def main(domain_name: str):
    d = config.set_domain(domain_name)
    out = config.ROOT / "docs" / d.name
    out.mkdir(parents=True, exist_ok=True)
    conn = db.connect(":memory:")
    db.migrate(conn)
    knowledge.load_from_csv(conn)
    retriever = FAQRetriever(knowledge.current_faqs(conn))
    cv = knowledge.corpus_version(conn)

    tickets = pd.read_csv(d.data_dir / "tickets.csv")
    expected = dict(pd.read_csv(d.data_dir / "rag_eval.csv").values)

    sweep = [evaluate(t, retriever, cv, tickets, expected) for t in [0.10, 0.15, 0.20, 0.25, 0.30, 0.35]]
    for s in sweep:
        print(s["threshold"], {k: s[k] for k in ("answer_precision", "answer_coverage", "escalation_recall")}, s["counts"])

    chosen = float(json.loads((config.ROOT / "docs" / "rag_threshold.json").read_text())["threshold"]) \
        if (config.ROOT / "docs" / "rag_threshold.json").exists() else 0.20
    final = next(s for s in sweep if abs(s["threshold"] - chosen) < 1e-9)
    final["rows"].to_csv(d.data_dir / "rag_eval_results.csv", index=False)
    scorecard = {
        "domain": d.name,
        "corpus_version": cv,
        "retriever": "tfidf-cosine-v1",
        "chosen_threshold": chosen,
        "metrics": {k: final[k] for k in ("answer_precision", "answer_coverage", "escalation_recall")},
        "outcomes": final["counts"],
        "threshold_sweep": [{k: s[k] for k in ("threshold", "answer_precision", "answer_coverage",
                                                "escalation_recall", "counts")} for s in sweep],
        "errors": final["rows"][~final["rows"]["outcome"].isin(
            ["correct_answer", "correct_abstain", "correct_escalation"])].to_dict(orient="records"),
    }
    (out / "week3_rag_scorecard.json").write_text(json.dumps(scorecard, indent=2, default=int))
    print(json.dumps({k: scorecard[k] for k in ("chosen_threshold", "metrics", "outcomes")}, indent=2))
    print("errors:", json.dumps(scorecard["errors"], indent=1))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--domain", default="kgit", choices=config.DOMAINS)
    main(ap.parse_args().domain)
