"""Text helpers for SKP-AI."""
from __future__ import annotations

import re
from typing import Iterable, List

TOKEN_LENGTH = 4  # rough heuristic: 1 token ~ 4 chars


def normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def chunk_text(text: str, min_tokens: int = 1200, max_tokens: int = 1600, overlap_tokens: int = 200) -> List[str]:
    """Chunk text by approximate token counts using character lengths."""
    if not text:
        return []
    text = normalize_whitespace(text)
    approx_chunk = max_tokens * TOKEN_LENGTH
    approx_overlap = overlap_tokens * TOKEN_LENGTH
    chunks: List[str] = []
    start = 0
    while start < len(text):
        end = min(len(text), start + approx_chunk)
        chunk = text[start:end]
        if len(chunk) < min_tokens * TOKEN_LENGTH and start != 0:
            # append to previous chunk
            chunks[-1] += " " + chunk
        else:
            chunks.append(chunk)
        start = max(end - approx_overlap, end)
    return [c.strip() for c in chunks if c.strip()]


def strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", " ", text)


def unique_everseen(iterable: Iterable[str]) -> List[str]:
    seen = set()
    unique: List[str] = []
    for item in iterable:
        if item not in seen:
            seen.add(item)
            unique.append(item)
    return unique


__all__ = ["chunk_text", "normalize_whitespace", "strip_html", "unique_everseen"]
