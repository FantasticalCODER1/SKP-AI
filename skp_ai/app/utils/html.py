"""HTML related utilities."""
from __future__ import annotations

from typing import Iterable

from bs4 import BeautifulSoup


def extract_main_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for element in soup(["script", "style", "noscript"]):
        element.extract()
    return " ".join(soup.stripped_strings)


def extract_links(html: str) -> Iterable[str]:
    soup = BeautifulSoup(html, "html.parser")
    for a in soup.find_all("a", href=True):
        yield a["href"]


__all__ = ["extract_main_text", "extract_links"]
