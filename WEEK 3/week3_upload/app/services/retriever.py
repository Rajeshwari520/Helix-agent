"""FAQ retriever: TF-IDF (word + character n-grams) with cosine similarity.

Runs fully offline. Can be swapped for sentence embeddings + FAISS/Chroma later
without changing the RAG service (same search() interface).
"""
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.pipeline import FeatureUnion

RETRIEVER_VERSION = "tfidf-cosine-v1"


class FAQRetriever:
    def __init__(self, faqs: list[dict]):
        self.faqs = faqs
        # The question is repeated so it weighs more than the answer text
        docs = [f"{f['question']} {f['question']} {f['answer']}".lower() for f in faqs]
        self.vectorizer = FeatureUnion([
            ("word", TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True, stop_words="english")),
            ("char", TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), sublinear_tf=True)),
        ])
        self.matrix = self.vectorizer.fit_transform(docs) if docs else None

    def search(self, query: str, k: int = 3, category: str | None = None) -> list[dict]:
        if self.matrix is None:
            return []
        scores = cosine_similarity(self.vectorizer.transform([query.lower()]), self.matrix)[0]  # = average of word and char similarity
        ranked = sorted(range(len(self.faqs)), key=lambda i: scores[i], reverse=True)
        hits = []
        for i in ranked:
            f = self.faqs[i]
            if category and f["category"] != category:
                continue
            hits.append({**f, "score": round(float(scores[i]), 3)})
            if len(hits) == k:
                break
        return hits
