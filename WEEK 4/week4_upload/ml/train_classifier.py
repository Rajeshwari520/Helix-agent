"""Week 2 — train and evaluate the ticket category classifier for one domain.

Train: data/<domain>/train_tickets.csv (450 template tickets)
       + data/<domain>/tickets.csv and dev_tickets.csv (100 hand-written tickets, weighted 3x)
Test:  data/<domain>/test_tickets.csv  (50 hand-written tickets, FROZEN — never used for training or tuning)

Outputs:
  models/<domain>_category_classifier.joblib
  docs/<domain>/week2_classifier_metrics.json
  docs/<domain>/week2_confusion_matrix.png

Run from the project root:
  python -m ml.train_classifier
"""
import argparse
import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from sklearn.metrics import (ConfusionMatrixDisplay, accuracy_score, classification_report,
                             confusion_matrix, f1_score)
from sklearn.model_selection import StratifiedKFold, cross_val_score

from app import config
from app.services import classifier
from app.services.classifier import MODEL_VERSION, build_pipeline, training_data


def main(domain_name: str):
    d = config.set_domain(domain_name)
    out = config.ROOT / "docs" / d.name
    out.mkdir(parents=True, exist_ok=True)

    train = training_data(d.data_dir)
    test = pd.read_csv(d.data_dir / "test_tickets.csv")
    test["text"] = (test["subject"] + ". " + test["body"]).str.lower()

    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    cv_f1 = cross_val_score(build_pipeline(), train["text"], train["category"], cv=cv, scoring="f1_macro")

    model = build_pipeline().fit(train["text"], train["category"])
    probs = model.predict_proba(test["text"])
    test["pred"] = model.classes_[probs.argmax(axis=1)]
    test["confidence"] = probs.max(axis=1)

    acc = accuracy_score(test["category"], test["pred"])
    f1 = f1_score(test["category"], test["pred"], average="macro")
    report = classification_report(test["category"], test["pred"], output_dict=True, zero_division=0)

    correct = test["category"] == test["pred"]
    thresholds = {}
    for t in [0.30, 0.35, 0.40, 0.45, 0.50, 0.60]:
        kept = test["confidence"] >= t
        thresholds[str(t)] = {
            "flagged_for_review_pct": round(float((~kept).mean()), 3),
            "accuracy_on_kept": round(float(correct[kept].mean()), 3) if kept.any() else None,
            "wrong_but_not_flagged": int((~correct & kept).sum()),
        }

    config.MODEL_DIR.mkdir(exist_ok=True)
    classifier.save_model(model, d.classifier_path)

    metrics = {
        "domain": d.name,
        "model_version": MODEL_VERSION,
        "train_size": len(train),
        "test_size": len(test),
        "test_file": "test_tickets.csv (frozen, sha256 in data/kgit/test_set_frozen.sha256)",
        "cv_macro_f1_mean": round(float(cv_f1.mean()), 3),
        "cv_macro_f1_std": round(float(cv_f1.std()), 3),
        "test_accuracy": round(acc, 3),
        "test_macro_f1": round(f1, 3),
        "per_class": {k: {m: round(v, 3) for m, v in r.items()}
                      for k, r in report.items() if k in d.categories},
        "confidence_thresholds": thresholds,
        "misclassified": test.loc[~correct, ["ticket_id", "subject", "category", "pred", "confidence"]]
                             .round(3).to_dict(orient="records"),
    }
    baseline = d.data_dir / "baseline_predictions.csv"
    if baseline.exists():
        base = pd.read_csv(baseline)
        metrics["rule_baseline_accuracy_on_these_50"] = round(accuracy_score(base["category"], base["pred_category"]), 3)
    base_json = config.ROOT / "docs" / d.name / "baseline_metrics.json"
    if base_json.exists():
        metrics["rule_baseline_accuracy_on_unseen_wording"] = json.loads(base_json.read_text()).get(
            "rules_on_unseen_wording_accuracy")
    (out / "week2_classifier_metrics.json").write_text(json.dumps(metrics, indent=2))

    fig, ax = plt.subplots(figsize=(7.5, 6))
    ConfusionMatrixDisplay(confusion_matrix(test["category"], test["pred"], labels=d.categories),
                           display_labels=d.categories).plot(ax=ax, cmap="Blues", colorbar=False)
    ax.set_title(f"Frozen test set, 50 unseen tickets (acc {acc:.2f}, macro-F1 {f1:.2f})")
    ax.tick_params(axis="x", rotation=30)
    plt.tight_layout()
    plt.savefig(out / "week2_confusion_matrix.png", dpi=120)
    plt.close(fig)

    print(classification_report(test["category"], test["pred"], zero_division=0))
    print(json.dumps({k: metrics[k] for k in ("domain", "cv_macro_f1_mean", "test_accuracy", "test_macro_f1")}))
    print("thresholds:", json.dumps(thresholds))
    print("misclassified:", json.dumps(metrics["misclassified"], indent=1))
    return metrics


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--domain", default="kgit", choices=config.DOMAINS)
    main(ap.parse_args().domain)
