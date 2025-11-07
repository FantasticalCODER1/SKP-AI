"""Cleaning pipeline to deduplicate and filter documents."""
from __future__ import annotations

from typing import List

import textdistance

from ..utils.logger import get_logger
from ..utils.text import normalize_whitespace
from .scrape import RawDocument

logger = get_logger(__name__)


def run(documents: List[RawDocument]) -> List[RawDocument]:
    if not documents:
        return []
    cleaned: List[RawDocument] = []
    texts: List[str] = []
    for doc in documents:
        text = normalize_whitespace(doc.text)
        if len(text.split()) < 150:
            continue
        duplicate = False
        for existing in texts:
            similarity = textdistance.sorensen(text, existing)
            if similarity > 0.9:
                duplicate = True
                break
        if not duplicate:
            cleaned.append(RawDocument(url=doc.url, title=doc.title, text=text, html=doc.html, source=doc.source))
            texts.append(text)
    logger.info("Cleaned %s -> %s documents", len(documents), len(cleaned))
    return cleaned


__all__ = ["run"]
