"""Logging utilities using Rich."""
from __future__ import annotations

import logging
from typing import Optional

from rich.console import Console
from rich.logging import RichHandler

_console = Console()


def configure_logging(level: int = logging.INFO) -> None:
    """Configure root logging with Rich handler if not already configured."""
    if any(isinstance(h, RichHandler) for h in logging.getLogger().handlers):
        return
    logging.basicConfig(
        level=level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(console=_console, rich_tracebacks=True)],
    )


def get_logger(name: Optional[str] = None) -> logging.Logger:
    configure_logging()
    return logging.getLogger(name or "skp_ai")


__all__ = ["configure_logging", "get_logger"]
