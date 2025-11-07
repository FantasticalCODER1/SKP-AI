"""ChromaDB store helpers."""
from __future__ import annotations

from pathlib import Path
from typing import List, Optional

import chromadb

from ..config import get_session_dir


class SessionVectorStore:
    def __init__(self, session_id: str) -> None:
        self.session_id = session_id
        self.persist_dir = str(get_session_dir(session_id) / "chroma")
        Path(self.persist_dir).mkdir(parents=True, exist_ok=True)
        self.client = chromadb.PersistentClient(path=self.persist_dir)
        self.collection = self.client.get_or_create_collection(name="skp")

    def add(
        self,
        ids: List[str],
        documents: List[str],
        metadatas: List[dict],
        embeddings: Optional[List[List[float]]] = None,
    ) -> None:
        kwargs = {"ids": ids, "documents": documents, "metadatas": metadatas}
        if embeddings is not None:
            kwargs["embeddings"] = embeddings
        self.collection.add(**kwargs)

    def query(self, query_texts: List[str], n_results: int) -> dict:
        return self.collection.query(query_texts=query_texts, n_results=n_results)


__all__ = ["SessionVectorStore"]
