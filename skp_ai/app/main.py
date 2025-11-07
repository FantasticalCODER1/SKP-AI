"""FastAPI application entry point."""
from __future__ import annotations

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .rate_limit import rate_limit_dependency
from .routers import build, chat, health
from .telemetry import register_telemetry
from .utils.logger import configure_logging

configure_logging()

app = FastAPI(title="Session Knowledge Profile AI", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_telemetry(app)

app.include_router(health.router)
app.include_router(build.router, dependencies=[Depends(rate_limit_dependency)])
app.include_router(chat.router, dependencies=[Depends(rate_limit_dependency)])


__all__ = ["app"]
