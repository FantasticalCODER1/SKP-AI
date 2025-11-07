"""Synthesis pipeline building the session knowledge profile."""
from __future__ import annotations

from typing import List, Tuple

from openai import OpenAI

from ..config import MODEL_SUMMARY, OPENAI_API_KEY
from ..schema.models import Citation
from ..utils.logger import get_logger
from .rank import RankedDocument

logger = get_logger(__name__)


def _format_documents(ranked_documents: List[RankedDocument], limit: int = 5) -> str:
    snippets = []
    for idx, ranked in enumerate(ranked_documents[:limit]):
        doc = ranked.document
        snippet = doc.text[:2000]
        snippets.append(f"Source {idx + 1}: {doc.title}\nURL: {doc.url}\nContent: {snippet}")
    return "\n\n".join(snippets)


def _summarize(topic: str, ranked_documents: List[RankedDocument]) -> str:
    context = _format_documents(ranked_documents)
    if not OPENAI_API_KEY:
        logger.warning("OPENAI_API_KEY not set; using heuristic summary")
        return (
            f"Summary for {topic}: {ranked_documents[0].document.text[:500]}"
            if ranked_documents
            else f"Summary for {topic}: insufficient data."
        )
    client = OpenAI(api_key=OPENAI_API_KEY)
    prompt = (
        "You are an analyst building a concise research briefing. "
        "Focus on factual synthesis and avoid speculation."
    )
    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": f"Topic: {topic}\n\nSources:\n{context}\n\nCreate a 4 paragraph summary."},
    ]
    response = client.chat.completions.create(model=MODEL_SUMMARY, messages=messages, temperature=0.2)
    return response.choices[0].message.content.strip()


def _build_ledger(ranked_documents: List[RankedDocument]) -> List[Citation]:
    citations: List[Citation] = []
    for idx, ranked in enumerate(ranked_documents[:12]):
        doc = ranked.document
        citation_id = f"S{idx + 1:02d}"
        title = doc.title[:200]
        citations.append(Citation(id=citation_id, title=title, url=doc.url, source=doc.source))
    return citations


def run(topic: str, ranked_documents: List[RankedDocument]) -> Tuple[str, List[Citation]]:
    if not ranked_documents:
        return "No data collected.", []
    summary = _summarize(topic, ranked_documents)
    citations = _build_ledger(ranked_documents)
    return summary, citations


__all__ = ["run"]
