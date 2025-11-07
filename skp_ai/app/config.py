"""Application configuration utilities for SKP-AI backend."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict

from dotenv import load_dotenv

load_dotenv()

ROOT_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT_DIR / "data"
CACHE_DIR = DATA_DIR / "skp_cache"
ROBOTS_CACHE_DIR = DATA_DIR / "robots_cache"
ALLOWLIST_PATH = Path(os.getenv("ALLOWLIST_PATH", DATA_DIR / "allowlist.json"))

# ensure directories exist
CACHE_DIR.mkdir(parents=True, exist_ok=True)
ROBOTS_CACHE_DIR.mkdir(parents=True, exist_ok=True)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
PORT = int(os.getenv("PORT", "8000"))
SAFE_SCRAPE = os.getenv("SAFE_SCRAPE", "true").lower() == "true"
RATE_LIMIT_RPS = float(os.getenv("RATE_LIMIT_RPS", "3"))
MAX_SCRAPE_DOCS = int(os.getenv("MAX_SCRAPE_DOCS", "300"))
TOP_K_RETRIEVAL = int(os.getenv("TOP_K_RETRIEVAL", "12"))
MODEL_EMBED = os.getenv("MODEL_EMBED", "text-embedding-3-large")
MODEL_SUMMARY = os.getenv("MODEL_SUMMARY", "gpt-4o-mini")
MODEL_CHAT = os.getenv("MODEL_CHAT", "gpt-5")
SKP_CACHE_PATH = Path(os.getenv("SKP_CACHE_PATH", str(CACHE_DIR)))
ROBOTS_CACHE_PATH = Path(os.getenv("ROBOTS_CACHE_PATH", str(ROBOTS_CACHE_DIR)))

SKP_CACHE_PATH.mkdir(parents=True, exist_ok=True)
ROBOTS_CACHE_PATH.mkdir(parents=True, exist_ok=True)

DEFAULT_TIMEOUT = 30


def load_allowlist() -> Dict[str, Any]:
    """Load allowlist JSON; return empty dict if missing."""
    if not ALLOWLIST_PATH.exists():
        return {}
    with ALLOWLIST_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def get_session_dir(session_id: str) -> Path:
    """Return directory for a session, creating if necessary."""
    session_dir = SKP_CACHE_PATH / f"skp_{session_id}"
    session_dir.mkdir(parents=True, exist_ok=True)
    return session_dir


def session_file(session_id: str, name: str) -> Path:
    """Return path to a named file in the session directory."""
    return get_session_dir(session_id) / name


__all__ = [
    "OPENAI_API_KEY",
    "PORT",
    "SAFE_SCRAPE",
    "RATE_LIMIT_RPS",
    "MAX_SCRAPE_DOCS",
    "TOP_K_RETRIEVAL",
    "MODEL_EMBED",
    "MODEL_SUMMARY",
    "MODEL_CHAT",
    "SKP_CACHE_PATH",
    "ROBOTS_CACHE_PATH",
    "DEFAULT_TIMEOUT",
    "load_allowlist",
    "get_session_dir",
    "session_file",
]
