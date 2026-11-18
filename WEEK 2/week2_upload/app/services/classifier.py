"""Ticket category classifier: TF-IDF (word + character n-grams) + Logistic Regression."""
from functools import lru_cache

import joblib
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import FeatureUnion, Pipeline

from app import config

MODEL_VERSION = "tfidf-logreg-v1"


def build_pipeline() -> Pipeline:
    features = FeatureUnion([
        ("word", TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True, min_df=1)),
        ("char", TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5), sublinear_tf=True, min_df=2)),
    ])
    return Pipeline([
        ("features", features),
        ("clf", LogisticRegression(C=10, max_iter=3000, class_weight="balanced")),
    ])


HANDWRITTEN_FILES = ["tickets.csv", "dev_tickets.csv"]   # realistic labeled tickets
HANDWRITTEN_WEIGHT = 3                                    # each hand-written ticket counts 3x


def template_data(data_dir=None) -> pd.DataFrame:
    df = pd.read_csv((data_dir or config.domain().data_dir) / "train_tickets.csv")
    return pd.DataFrame({"text": df["text"].str.lower(), "category": df["category"]})


def handwritten_data(data_dir=None) -> pd.DataFrame:
    """Hand-written labeled tickets used for TRAINING. The frozen test_tickets.csv is never included."""
    data_dir = data_dir or config.domain().data_dir
    frames = []
    for name in HANDWRITTEN_FILES:
        path = data_dir / name
        if path.exists():
            df = pd.read_csv(path)
            frames.append(pd.DataFrame({"text": (df["subject"] + ". " + df["body"]).str.lower(),
                                        "category": df["category"]}))
    return pd.concat(frames, ignore_index=True)


def training_data(data_dir=None) -> pd.DataFrame:
    return pd.concat([template_data(data_dir)] + [handwritten_data(data_dir)] * HANDWRITTEN_WEIGHT,
                     ignore_index=True)


def train(data_dir=None) -> Pipeline:
    df = training_data(data_dir)
    model = build_pipeline()
    model.fit(df["text"], df["category"])
    return model


@lru_cache(maxsize=None)
def _model_for(domain_name: str) -> Pipeline:
    d = config.load_domain(domain_name)
    if d.classifier_path.exists():
        try:
            return joblib.load(d.classifier_path)
        except Exception:  # saved with another scikit-learn version -> retrain
            pass
    model = train(d.data_dir)
    config.MODEL_DIR.mkdir(exist_ok=True)
    joblib.dump(model, d.classifier_path)
    return model


def get_model() -> Pipeline:
    """Model for the active domain (loaded from models/, or trained from data/<domain>/train_tickets.csv)."""
    return _model_for(config.domain().name)


def predict(text: str) -> dict:
    model = get_model()
    probs = model.predict_proba([text.lower()])[0]
    ranked = sorted(zip(model.classes_, probs), key=lambda p: p[1], reverse=True)
    return {
        "category": ranked[0][0],
        "confidence": round(float(ranked[0][1]), 3),
        "alternatives": [{"category": c, "probability": round(float(p), 3)} for c, p in ranked[1:3]],
        "model_version": MODEL_VERSION,
    }
