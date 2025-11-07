"""Contracts exposed via API."""
from __future__ import annotations

from pydantic import BaseModel, validator

from .models import (
    AnswerContract,
    AskRequest,
    BuildRequest,
    ErrorResponse,
    SessionStage,
    SessionStatusResponse,
)


class StartSessionResponse(BaseModel):
    session_id: str
    status: SessionStage


class AskResponse(BaseModel):
    answer: AnswerContract

    @validator("answer")
    def ensure_disclaimer(cls, value: AnswerContract) -> AnswerContract:  # noqa: N805
        return value.with_disclaimer()


__all__ = [
    "BuildRequest",
    "AskRequest",
    "AnswerContract",
    "StartSessionResponse",
    "AskResponse",
    "SessionStatusResponse",
    "ErrorResponse",
    "SessionStage",
]
