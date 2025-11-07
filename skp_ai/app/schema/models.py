"""Pydantic models for internal state."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class SessionStage(str, Enum):
    QUEUED = "queued"
    DISCOVER = "discover"
    CLEAN = "clean"
    RANK = "rank"
    EMBED = "embed"
    SYNTHESIZE = "synthesize"
    READY = "ready"
    FAILED = "failed"


class SessionState(BaseModel):
    session_id: str
    topic: str
    stage: SessionStage = SessionStage.QUEUED
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    eta_seconds: Optional[float] = None
    elapsed_seconds: float = 0.0
    detail: Optional[str] = None
    documents_discovered: int = 0
    documents_retained: int = 0
    evidence_count: int = 0
    ledger: List[Dict[str, str]] = Field(default_factory=list)


class SessionStatusResponse(BaseModel):
    session_id: str
    topic: str
    stage: SessionStage
    elapsed_seconds: float
    eta_seconds: Optional[float]
    detail: Optional[str]


class BuildRequest(BaseModel):
    topic: str
    user_context: Optional[Dict[str, str]] = None


class AskRequest(BaseModel):
    question: str
    context: Optional[Dict[str, str]] = None


class Citation(BaseModel):
    id: str
    title: str
    url: str
    source: str


class AnswerContract(BaseModel):
    summary: str
    reasoning_points: List[str]
    next_steps: List[str]
    risks: List[str]
    citations: List[Citation]
    assumptions: List[str]
    confidence: float

    def with_disclaimer(self) -> "AnswerContract":
        disclaimer = "This information is for general educational purposes only."
        summary = self.summary
        if disclaimer.lower() not in summary.lower():
            summary = f"{summary}\n\n{disclaimer}"
        return AnswerContract(
            summary=summary,
            reasoning_points=self.reasoning_points,
            next_steps=self.next_steps,
            risks=self.risks,
            citations=self.citations,
            assumptions=self.assumptions,
            confidence=self.confidence,
        )


class AllowlistEntry(BaseModel):
    domain: str
    title: Optional[str]


class Allowlist(BaseModel):
    domains: List[AllowlistEntry]


class ErrorResponse(BaseModel):
    status: str
    stage: SessionStage
    eta_seconds: Optional[float]
