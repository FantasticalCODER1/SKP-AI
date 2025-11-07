"""Retrieval utilities."""
from __future__ import annotations

from typing import List, Tuple

from ..config import TOP_K_RETRIEVAL
from ..utils.logger import get_logger
from .store import SessionVectorStore

logger = get_logger(__name__)


def retrieve(session_id: str, query: str, top_k: int = TOP_K_RETRIEVAL) -> List[Tuple[str, dict]]:
    store = SessionVectorStore(session_id)
    try:
        results = store.query(query_texts=[query], n_results=top_k)
    except ValueError:
        logger.debug("Vector store empty for session %s", session_id)
        return []
    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    scores = results.get("distances", [[]])[0]
    payload: List[Tuple[str, dict]] = []
    for doc, meta, score in zip(documents, metadatas, scores):
        meta = meta or {}
        meta["score"] = score
        payload.append((doc, meta))
    logger.debug("Retrieved %s documents for %s", len(payload), session_id)
    return payload


__all__ = ["retrieve"]
