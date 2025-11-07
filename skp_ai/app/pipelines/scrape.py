"""Scraping pipeline using aiohttp and trafilatura."""
from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import aiohttp
import trafilatura

from ..config import (
    DEFAULT_TIMEOUT,
    MAX_SCRAPE_DOCS,
    ROBOTS_CACHE_PATH,
    SAFE_SCRAPE,
    load_allowlist,
)
from ..utils.logger import get_logger
from ..utils.text import normalize_whitespace

logger = get_logger(__name__)


@dataclass
class RawDocument:
    url: str
    title: str
    text: str
    html: str
    source: str


async def _fetch(session: aiohttp.ClientSession, url: str) -> Optional[str]:
    try:
        async with session.get(url, timeout=DEFAULT_TIMEOUT, allow_redirects=True) as resp:
            if resp.status >= 400:
                logger.debug("Failed to fetch %s: %s", url, resp.status)
                return None
            return await resp.text()
    except Exception as exc:  # pragma: no cover - network issues
        logger.debug("Error fetching %s: %s", url, exc)
        return None


async def _load_robots(session: aiohttp.ClientSession, domain: str) -> RobotFileParser:
    cache_file = ROBOTS_CACHE_PATH / f"{domain.replace(':', '_')}.txt"
    if cache_file.exists():
        text = cache_file.read_text(encoding="utf-8")
    else:
        text = ""
        for scheme in ("https", "http"):
            robots_url = f"{scheme}://{domain}/robots.txt"
            html = await _fetch(session, robots_url)
            if html is not None:
                text = html
                break
        cache_file.write_text(text, encoding="utf-8")
    parser = RobotFileParser()
    parser.set_url(f"https://{domain}/robots.txt")
    parser.parse(text.splitlines())
    return parser


async def _is_allowed(session: aiohttp.ClientSession, url: str, user_agent: str = "SKP-AI") -> bool:
    domain = urlparse(url).netloc
    parser = await _load_robots(session, domain)
    allowed = parser.can_fetch(user_agent, url)
    if not allowed:
        logger.debug("Blocked by robots.txt: %s", url)
    return allowed


async def _extract(url: str, html: str) -> Optional[RawDocument]:
    metadata = trafilatura.extract(html, include_links=True, include_comments=False, include_tables=False, output_format="json")
    if metadata:
        data = json.loads(metadata)
        text = normalize_whitespace(data.get("text", ""))
        if not text:
            return None
        title = data.get("title") or data.get("sitename") or url
        return RawDocument(url=url, title=title, text=text, html=html, source=data.get("source-url", url))
    text = trafilatura.extract(html) or ""
    text = normalize_whitespace(text)
    if not text:
        return None
    return RawDocument(url=url, title=url, text=text, html=html, source=url)


async def _fetch_allowed(session: aiohttp.ClientSession, url: str) -> Optional[RawDocument]:
    if not await _is_allowed(session, url):
        return None
    html = await _fetch(session, url)
    if html is None:
        return None
    return await _extract(url, html)


async def _scrape_urls(urls: Iterable[str]) -> List[RawDocument]:
    headers = {"User-Agent": "SessionKnowledgeProfileAI/1.0"}
    connector = aiohttp.TCPConnector(limit_per_host=4)
    async with aiohttp.ClientSession(headers=headers, connector=connector) as session:
        tasks = [_fetch_allowed(session, url) for url in urls]
        results = await asyncio.gather(*tasks)
    documents = [doc for doc in results if doc is not None]
    logger.info("Scraped %s documents", len(documents))
    return documents


def _candidate_urls(topic: str, allowlist: Dict[str, Any]) -> List[str]:
    seed_urls = allowlist.get("seed_urls", [])
    domains = [entry.get("domain") for entry in allowlist.get("domains", []) if entry.get("domain")]
    candidates: List[str] = []
    candidates.extend(seed_urls)
    for domain in domains:
        candidates.append(f"https://{domain}")
    # deduplicate while preserving order
    seen = set()
    ordered: List[str] = []
    for url in candidates:
        if not url:
            continue
        if url not in seen:
            seen.add(url)
            ordered.append(url)
    return ordered[:MAX_SCRAPE_DOCS]


def run(topic: str) -> List[RawDocument]:
    allowlist = load_allowlist()
    urls = _candidate_urls(topic, allowlist)
    if not urls:
        logger.warning("Allowlist provided no candidate URLs; skipping scrape")
        return []
    allowed_domains = {entry.get("domain") for entry in allowlist.get("domains", [])}
    filtered_urls = [url for url in urls if not allowed_domains or urlparse(url).netloc in allowed_domains]
    if SAFE_SCRAPE:
        loop = asyncio.new_event_loop()
        try:
            asyncio.set_event_loop(loop)
            documents = loop.run_until_complete(_scrape_urls(filtered_urls))
        finally:
            loop.run_until_complete(loop.shutdown_asyncgens())
            loop.close()
            asyncio.set_event_loop(None)
        return documents
    # SAFE_SCRAPE false -> read cached samples
    samples_dir = ROBOTS_CACHE_PATH.parent / "samples"
    documents: List[RawDocument] = []
    for url in filtered_urls:
        sample_file = samples_dir / f"{urlparse(url).netloc}.txt"
        if sample_file.exists():
            text = sample_file.read_text(encoding="utf-8")
            documents.append(RawDocument(url=url, title=url, text=text, html=text, source=url))
    return documents


__all__ = ["RawDocument", "run"]
