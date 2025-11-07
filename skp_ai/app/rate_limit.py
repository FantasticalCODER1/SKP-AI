"""Simple per-IP token bucket rate limiter."""
from __future__ import annotations

import threading
import time
from typing import Dict

from fastapi import HTTPException, Request, status

from .config import RATE_LIMIT_RPS


class TokenBucket:
    def __init__(self, rate: float, capacity: float) -> None:
        self.rate = rate
        self.capacity = capacity
        self.tokens = capacity
        self.timestamp = time.monotonic()
        self.lock = threading.Lock()

    def consume(self, tokens: float = 1.0) -> bool:
        with self.lock:
            now = time.monotonic()
            elapsed = now - self.timestamp
            self.timestamp = now
            self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False


class RateLimiter:
    def __init__(self, rate: float) -> None:
        self.rate = rate
        self.capacity = max(1.0, rate * 2)
        self.buckets: Dict[str, TokenBucket] = {}
        self.lock = threading.Lock()

    def check(self, key: str) -> None:
        with self.lock:
            bucket = self.buckets.setdefault(key, TokenBucket(self.rate, self.capacity))
        if not bucket.consume():
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded",
            )


rate_limiter = RateLimiter(RATE_LIMIT_RPS)


def rate_limit_dependency(request: Request) -> None:
    client = request.client.host if request.client else "anonymous"
    rate_limiter.check(client)


__all__ = ["rate_limit_dependency", "rate_limiter", "RateLimiter", "TokenBucket"]
