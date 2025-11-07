"""Ranking and clustering pipeline."""
from __future__ import annotations

from dataclasses import dataclass
from typing import List

from rank_bm25 import BM25Okapi
from sklearn.cluster import MiniBatchKMeans
from sklearn.feature_extraction.text import TfidfVectorizer

from ..utils.logger import get_logger
from ..utils.text import normalize_whitespace
from .scrape import RawDocument

logger = get_logger(__name__)


@dataclass
class RankedDocument:
    document: RawDocument
    score: float
    cluster: int


def _bm25_scores(topic: str, documents: List[RawDocument]) -> List[float]:
    if not documents:
        return []
    tokenized_corpus = [normalize_whitespace(doc.text).split() for doc in documents]
    if not any(tokenized_corpus):
        return [0.0] * len(documents)
    bm25 = BM25Okapi(tokenized_corpus)
    query = normalize_whitespace(topic).split()
    if not query:
        return [0.0] * len(documents)
    scores = bm25.get_scores(query)
    normalized = scores.astype(float)
    max_score = float(normalized.max()) if normalized.size else 1.0
    if max_score == 0:
        return [0.0] * len(documents)
    return (normalized / max_score).tolist()


def _cluster_documents(documents: List[RawDocument], n_clusters: int = 3) -> List[int]:
    texts = [doc.text for doc in documents]
    vectorizer = TfidfVectorizer(max_features=5000)
    matrix = vectorizer.fit_transform(texts)
    clusters = MiniBatchKMeans(n_clusters=min(n_clusters, len(documents)), random_state=42)
    labels = clusters.fit_predict(matrix)
    return list(labels)


def run(topic: str, documents: List[RawDocument]) -> List[RankedDocument]:
    if not documents:
        return []
    bm25_scores = _bm25_scores(topic, documents)
    clusters = _cluster_documents(documents, n_clusters=min(5, len(documents)))
    ranked: List[RankedDocument] = []
    for idx, doc in enumerate(documents):
        authority = 0.8
        if "gov" in doc.url or "edu" in doc.url:
            authority = 0.95
        recency = 0.5
        composite = 0.6 * bm25_scores[idx] + 0.3 * authority + 0.1 * recency
        ranked.append(RankedDocument(document=doc, score=float(composite), cluster=clusters[idx]))
    ranked.sort(key=lambda item: item.score, reverse=True)
    logger.info("Ranked %s documents", len(ranked))
    return ranked


__all__ = ["RankedDocument", "run"]
