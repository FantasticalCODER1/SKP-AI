"""Telemetry and logging integration."""
from __future__ import annotations

import time
from typing import Callable

from fastapi import FastAPI, Request
from prometheus_client import Counter, Histogram, make_asgi_app

REQUEST_LATENCY = Histogram(
    "skpai_request_latency_seconds",
    "Latency of HTTP requests",
    labelnames=["method", "path"],
)
REQUEST_COUNT = Counter(
    "skpai_request_total",
    "Total HTTP requests",
    labelnames=["method", "path", "status"],
)


def register_telemetry(app: FastAPI) -> None:
    metrics_app = make_asgi_app()

    @app.middleware("http")
    async def metrics_middleware(request: Request, call_next: Callable):  # type: ignore[type-arg]
        start = time.perf_counter()
        response = await call_next(request)
        elapsed = time.perf_counter() - start
        path = request.url.path
        REQUEST_LATENCY.labels(request.method, path).observe(elapsed)
        REQUEST_COUNT.labels(request.method, path, str(response.status_code)).inc()
        return response

    app.mount("/metrics", metrics_app)


__all__ = ["register_telemetry", "REQUEST_LATENCY", "REQUEST_COUNT"]
