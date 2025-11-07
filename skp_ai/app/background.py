"""Background job management and session state persistence."""
from __future__ import annotations

import json
import threading
import uuid
from concurrent.futures import Future, ThreadPoolExecutor
from datetime import datetime
from typing import Any, Callable, Dict, Optional

from .config import session_file
from .schema.models import SessionStage, SessionState
from .utils.logger import get_logger

logger = get_logger(__name__)


class JobRegistry:
    """Track active jobs and session state."""

    def __init__(self) -> None:
        self._jobs: Dict[str, Future] = {}
        self._states: Dict[str, SessionState] = {}
        self._lock = threading.RLock()
        self._executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="skp-build")

    def create_session(self, topic: str) -> SessionState:
        session_id = str(uuid.uuid4())
        state = SessionState(session_id=session_id, topic=topic)
        self._states[session_id] = state
        self._persist_state(state)
        return state

    def submit(self, session_id: str, fn: Callable[[SessionState], None]) -> Future:
        with self._lock:
            if session_id in self._jobs:
                raise ValueError(f"Session {session_id} already running")
            future = self._executor.submit(self._run_job, session_id, fn)
            self._jobs[session_id] = future
            return future

    def _run_job(self, session_id: str, fn: Callable[[SessionState], None]) -> None:
        state = self._states[session_id]
        try:
            fn(state)
        except Exception as exc:  # pragma: no cover - defensive
            logger.exception("Session %s failed: %s", session_id, exc)
            state.stage = SessionStage.FAILED
            state.detail = str(exc)
        finally:
            state.updated_at = datetime.utcnow()
            self._persist_state(state)
            with self._lock:
                self._jobs.pop(session_id, None)

    def get_state(self, session_id: str) -> Optional[SessionState]:
        with self._lock:
            if session_id in self._states:
                return self._states[session_id]
        # fallback to disk
        path = session_file(session_id, "state.json")
        if path.exists():
            with path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            state = SessionState.parse_obj(data)
            with self._lock:
                self._states[session_id] = state
            return state
        return None

    def update_state(self, session_id: str, **kwargs) -> SessionState:
        with self._lock:
            state = self._states[session_id]
            for key, value in kwargs.items():
                setattr(state, key, value)
            state.updated_at = datetime.utcnow()
            state.elapsed_seconds = (state.updated_at - state.created_at).total_seconds()
            self._persist_state(state)
            return state

    def _persist_state(self, state: SessionState) -> None:
        path = session_file(state.session_id, "state.json")
        with path.open("w", encoding="utf-8") as f:
            json.dump(state.dict(), f, default=str, indent=2)

    def save_manifest(self, session_id: str, manifest: Dict[str, Any]) -> None:
        path = session_file(session_id, "manifest.json")
        with path.open("w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)

    def save_skp(self, session_id: str, skp: Dict[str, Any]) -> None:
        path = session_file(session_id, "skp.json")
        with path.open("w", encoding="utf-8") as f:
            json.dump(skp, f, indent=2)


job_registry = JobRegistry()


def estimate_eta(stage: SessionStage, documents: int) -> float:
    stage_weights = {
        SessionStage.QUEUED: 5,
        SessionStage.DISCOVER: max(15, documents * 0.2),
        SessionStage.CLEAN: max(10, documents * 0.05),
        SessionStage.RANK: max(10, documents * 0.05),
        SessionStage.EMBED: max(20, documents * 0.15),
        SessionStage.SYNTHESIZE: 25,
        SessionStage.READY: 0,
        SessionStage.FAILED: 0,
    }
    return float(stage_weights.get(stage, 30))


def load_manifest(session_id: str) -> Optional[Dict[str, Any]]:
    path = session_file(session_id, "manifest.json")
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_skp(session_id: str) -> Optional[Dict[str, Any]]:
    path = session_file(session_id, "skp.json")
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)
