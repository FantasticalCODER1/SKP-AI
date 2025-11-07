"""Chat endpoints for answering questions."""
from __future__ import annotations

from typing import List

from fastapi import APIRouter, HTTPException

from ..background import job_registry, load_skp
from ..pipelines.answer import answer_question
from ..schema.contracts import AskRequest, AskResponse
from ..schema.models import Citation, ErrorResponse, SessionStage
from ..utils.logger import get_logger

router = APIRouter()
logger = get_logger(__name__)


def _load_citations(session_id: str) -> List[Citation]:
    state = job_registry.get_state(session_id)
    citations_data = state.ledger if state else []
    if not citations_data:
        skp_data = load_skp(session_id) or {}
        citations_data = skp_data.get("ledger", [])
    citations: List[Citation] = []
    for item in citations_data:
        try:
            citations.append(Citation.parse_obj(item))
        except Exception:
            logger.debug("Skipping malformed citation entry: %s", item)
    return citations


@router.post("/ask/{session_id}", response_model=AskResponse, responses={409: {"model": ErrorResponse}})
async def ask_question(session_id: str, payload: AskRequest) -> AskResponse:
    state = job_registry.get_state(session_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Session not found")
    if state.stage != SessionStage.READY:
        error = ErrorResponse(
            status="building" if state.stage != SessionStage.FAILED else "failed",
            stage=state.stage,
            eta_seconds=state.eta_seconds,
        )
        raise HTTPException(status_code=409, detail=error.dict())
    citations = _load_citations(session_id)
    answer = answer_question(session_id, state.topic, payload.question, citations)
    return AskResponse(answer=answer)


__all__ = ["router"]
