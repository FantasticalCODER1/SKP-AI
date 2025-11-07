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
    min_length = min_tokens * TOKEN_LENGTH
    chunks: List[str] = []
    start = 0
    text_length = len(text)
    while start < text_length:
        end = min(text_length, start + approx_chunk)
        chunk = text[start:end]
        append_to_previous = len(chunk) < min_length and bool(chunks)
        if append_to_previous:
            chunks[-1] = f"{chunks[-1]} {chunk}".strip()
        else:
            chunks.append(chunk.strip())
        if end >= text_length:
            break
        if append_to_previous:
            start = end
        else:
            next_start = max(0, end - approx_overlap)
            if next_start <= start:
                start = end
            else:
                start = next_start
    return [c for c in chunks if c]


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
