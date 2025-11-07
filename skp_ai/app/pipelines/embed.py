"""Embedding pipeline using OpenAI embeddings."""
from __future__ import annotations

import hashlib
from typing import Any, Dict, List, Tuple

import numpy as np
from openai import OpenAI

from ..config import MODEL_EMBED, OPENAI_API_KEY
from ..retriever.store import SessionVectorStore
from ..utils.logger import get_logger
from ..utils.text import chunk_text
from .rank import RankedDocument

logger = get_logger(__name__)


def _pseudo_embedding(text: str, dimensions: int = 1536) -> List[float]:
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    repeat = (dimensions + len(digest) - 1) // len(digest)
    data = (digest * repeat)[:dimensions]
    vector = np.frombuffer(data, dtype=np.uint8).astype(float)
    norm = np.linalg.norm(vector)
    if norm == 0:
        return vector.tolist()
    return (vector / norm).tolist()


def _embed_openai(chunks: List[str]) -> List[List[float]]:
    if not OPENAI_API_KEY:
        logger.warning("OPENAI_API_KEY not set; using deterministic embeddings")
        return [_pseudo_embedding(chunk) for chunk in chunks]
    client = OpenAI(api_key=OPENAI_API_KEY)
    response = client.embeddings.create(model=MODEL_EMBED, input=chunks)
    return [item.embedding for item in response.data]


def run(session_id: str, ranked_documents: List[RankedDocument]) -> Tuple[List[Dict[str, str]], List[Dict[str, Any]]]:
    store = SessionVectorStore(session_id)
    chunk_records: List[Dict[str, str]] = []
    metadata_records: List[Dict[str, Any]] = []
    for idx, ranked in enumerate(ranked_documents):
        doc = ranked.document
        chunks = chunk_text(doc.text)
        if not chunks:
            continue
        embeddings = _embed_openai(chunks)
        ids = [f"{session_id}_{idx}_{i}" for i in range(len(chunks))]
        metadatas = [
            {
                "url": doc.url,
                "title": doc.title,
                "cluster": ranked.cluster,
                "rank_score": ranked.score,
                "chunk_index": i,
            }
            for i in range(len(chunks))
        ]
        store.add(ids=ids, documents=chunks, metadatas=metadatas, embeddings=embeddings)
        for chunk_id, chunk_text_value, metadata in zip(ids, chunks, metadatas):
            chunk_records.append({"id": chunk_id, "text": chunk_text_value})
            metadata_records.append(metadata)
    logger.info("Embedded %s chunks", len(chunk_records))
    return chunk_records, metadata_records


__all__ = ["run"]
