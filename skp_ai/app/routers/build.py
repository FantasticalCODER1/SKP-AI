"""Session build endpoints."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from ..background import estimate_eta, job_registry
from ..pipelines import clean, embed, rank, scrape, synthesize
from ..schema.contracts import BuildRequest, SessionStatusResponse, StartSessionResponse
from ..schema.models import SessionStage
from ..utils.logger import get_logger

router = APIRouter()
logger = get_logger(__name__)


def _update_stage(session_id: str, stage: SessionStage, detail: str = "", documents: int = 0) -> None:
    job_registry.update_state(
        session_id,
        stage=stage,
        detail=detail,
        eta_seconds=estimate_eta(stage, documents),
    )


def _execute_pipeline(state) -> None:
    session_id = state.session_id
    topic = state.topic
    try:
        _update_stage(session_id, SessionStage.DISCOVER, "Discovering sources")
        raw_documents = scrape.run(topic)
        documents_count = len(raw_documents)
        job_registry.update_state(session_id, documents_discovered=documents_count)

        _update_stage(session_id, SessionStage.CLEAN, "Cleaning corpus", documents_count)
        cleaned_documents = clean.run(raw_documents)
        job_registry.update_state(session_id, documents_retained=len(cleaned_documents))

        _update_stage(session_id, SessionStage.RANK, "Ranking documents", len(cleaned_documents))
        ranked_documents = rank.run(topic, cleaned_documents)

        _update_stage(session_id, SessionStage.EMBED, "Embedding knowledge base", len(ranked_documents))
        chunks, metadata = embed.run(session_id, ranked_documents)
        manifest = {"chunks": chunks, "metadata": metadata}
        job_registry.save_manifest(session_id, manifest)

        _update_stage(session_id, SessionStage.SYNTHESIZE, "Synthesizing evidence", len(ranked_documents))
        summary, citations = synthesize.run(topic, ranked_documents)
        ledger_payload = [citation.dict() for citation in citations]
        skp_payload = {
            "topic": topic,
            "summary": summary,
            "ledger": ledger_payload,
            "documents": [
                {
                    "url": doc.document.url,
                    "title": doc.document.title,
                    "score": doc.score,
                    "cluster": doc.cluster,
                }
                for doc in ranked_documents
            ],
        }
        job_registry.save_skp(session_id, skp_payload)
        job_registry.update_state(
            session_id,
            stage=SessionStage.READY,
            detail="Build complete",
            eta_seconds=0.0,
            evidence_count=len(citations),
            ledger=ledger_payload,
        )
        logger.info("Session %s ready", session_id)
    except Exception as exc:  # pragma: no cover - pipeline error
        logger.exception("Pipeline failed for session %s: %s", session_id, exc)
        job_registry.update_state(
            session_id,
            stage=SessionStage.FAILED,
            detail=str(exc),
            eta_seconds=None,
        )
        raise


@router.post("/start_session", response_model=StartSessionResponse, status_code=status.HTTP_202_ACCEPTED)
async def start_session(payload: BuildRequest) -> StartSessionResponse:
    if not payload.topic.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Topic is required")
    state = job_registry.create_session(payload.topic.strip())
    job_registry.submit(state.session_id, _execute_pipeline)
    return StartSessionResponse(session_id=state.session_id, status=state.stage)


@router.get("/session_status/{session_id}", response_model=SessionStatusResponse)
async def session_status(session_id: str) -> SessionStatusResponse:
    state = job_registry.get_state(session_id)
    if state is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    return SessionStatusResponse(
        session_id=state.session_id,
        topic=state.topic,
        stage=state.stage,
        elapsed_seconds=state.elapsed_seconds,
        eta_seconds=state.eta_seconds,
        detail=state.detail,
    )


__all__ = ["router"]
