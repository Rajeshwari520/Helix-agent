"""Choose the category model WITHOUT touching the frozen test set.

Candidates are compared with 5-fold cross-validation where every validation fold
contains only HAND-WRITTEN tickets (data/kgit/tickets.csv + dev_tickets.csv).
Training for each fold = all template tickets + the other hand-written folds.

Also picks the human-review confidence threshold from the out-of-fold predictions.

  python -m ml.select_model      -> docs/kgit/model_selection.json
"""
import json

import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold
from sklearn.naive_bayes import ComplementNB
from sklearn.pipeline import FeatureUnion, Pipeline
from sklearn.svm import LinearSVC

from app import config
from app.services.classifier import handwritten_data, template_data


def features(char_range=(2, 5)):
    return FeatureUnion([
        ("word", TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True)),
        ("char", TfidfVectorizer(analyzer="char_wb", ngram_range=char_range, sublinear_tf=True, min_df=2)),
    ])


CANDIDATES = {
    "logreg_C10 (current)": lambda: Pipeline([("f", features()), ("m", LogisticRegression(C=10, max_iter=3000, class_weight="balanced"))]),
    "logreg_C3": lambda: Pipeline([("f", features()), ("m", LogisticRegression(C=3, max_iter=3000, class_weight="balanced"))]),
    "logreg_C30": lambda: Pipeline([("f", features()), ("m", LogisticRegression(C=30, max_iter=3000, class_weight="balanced"))]),
    "linear_svm_calibrated": lambda: Pipeline([("f", features()), ("m", CalibratedClassifierCV(LinearSVC(C=0.5), cv=3))]),
    "complement_nb": lambda: Pipeline([("f", TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True)), ("m", ComplementNB(alpha=0.3))]),
}


def run(handwritten_weight: int = 3):
    tmpl = template_data()
    hand = handwritten_data().reset_index(drop=True)
    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=7)
    results = {}
    oof = {}
    for name, make in CANDIDATES.items():
        preds = np.empty(len(hand), dtype=object)
        conf = np.zeros(len(hand))
        for tr, va in skf.split(hand.text, hand.category):
            train = pd.concat([tmpl] + [hand.iloc[tr]] * handwritten_weight)
            model = make().fit(train.text, train.category)
            p = model.predict_proba(hand.text.iloc[va])
            preds[va] = model.classes_[p.argmax(1)]
            conf[va] = p.max(1)
        correct = preds == hand.category.values
        results[name] = {"cv_accuracy_on_handwritten": round(float(correct.mean()), 3)}
        oof[name] = (correct, conf)
    best = max(results, key=lambda k: results[k]["cv_accuracy_on_handwritten"])
    correct, conf = oof[best]
    thresholds = {}
    for t in [0.30, 0.35, 0.40, 0.45, 0.50, 0.55, 0.60]:
        kept = conf >= t
        thresholds[str(t)] = {"flagged_pct": round(float((~kept).mean()), 3),
                              "accuracy_on_rest": round(float(correct[kept].mean()), 3) if kept.any() else None,
                              "wrong_not_flagged": int((~correct & kept).sum())}
    out = {"handwritten_tickets": len(hand), "template_tickets": len(tmpl),
           "handwritten_weight": handwritten_weight, "candidates": results, "best": best,
           "threshold_analysis_best_model_out_of_fold": thresholds}
    (config.ROOT / "docs" / config.domain().name / "model_selection.json").write_text(json.dumps(out, indent=2))
    print(json.dumps(out, indent=2))
    return out


if __name__ == "__main__":
    run()
