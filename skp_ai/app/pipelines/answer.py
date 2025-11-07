"""Answer generation pipeline using retrieval augmented generation."""
from __future__ import annotations

import json
from typing import Dict, List, Tuple

from openai import OpenAI

from ..config import MODEL_CHAT, OPENAI_API_KEY
from ..retriever.search import retrieve
from ..schema.models import AnswerContract, Citation
from ..utils.logger import get_logger

logger = get_logger(__name__)


def _format_context(passages: List[Tuple[str, Dict]]) -> str:
    formatted = []
    for idx, (text, meta) in enumerate(passages, start=1):
        formatted.append(
            f"Passage {idx} (score={meta.get('score', 0):.4f}):\nTitle: {meta.get('title')}\nURL: {meta.get('url')}\n{text[:2000]}"
        )
    return "\n\n".join(formatted)


def _call_model(question: str, topic: str, context: str, citations: List[Citation]) -> AnswerContract:
    if not OPENAI_API_KEY:
        logger.warning("OPENAI_API_KEY not set; generating heuristic answer")
        summary = f"{question} relates to {topic}. Data unavailable."
        return AnswerContract(
            summary=summary,
            reasoning_points=["Insufficient data"],
            next_steps=["Provide an OpenAI API key to enable full synthesis."],
            risks=["Information incomplete"],
            citations=citations,
            assumptions=["No authoritative data retrieved"],
            confidence=0.1,
        )
    client = OpenAI(api_key=OPENAI_API_KEY)
    instructions = (
        "You are Session Knowledge Profile AI. Answer using only the provided context. "
        "Respond with valid JSON matching the AnswerContract schema. "
        "Assign citations using the provided IDs and include the disclaimer text in the summary."
    )
    prompt = (
        f"Topic: {topic}\nQuestion: {question}\n\nContext:\n{context}\n\n"
        f"Citations:\n{json.dumps([c.dict() for c in citations], indent=2)}\n\n"
        "Return a JSON object with keys summary, reasoning_points, next_steps, risks, citations, assumptions, confidence."
    )
    messages = [
        {"role": "system", "content": instructions},
        {"role": "user", "content": prompt},
    ]
    response = client.chat.completions.create(model=MODEL_CHAT, messages=messages, temperature=0.2)
    content = response.choices[0].message.content
    return _parse_answer(content, citations, client, messages)


def _parse_answer(content: str, citations: List[Citation], client: OpenAI, messages: List[Dict]) -> AnswerContract:
    try:
        data = json.loads(content)
        data["citations"] = [citation.dict() for citation in citations]
        return AnswerContract.parse_obj(data)
    except Exception as exc:
        logger.warning("Failed to parse JSON answer: %s", exc)
        repair_prompt = (
            "The previous response was invalid JSON. Please return valid JSON adhering to the AnswerContract schema."
        )
        messages.append({"role": "assistant", "content": content})
        messages.append({"role": "user", "content": repair_prompt})
        retry = client.chat.completions.create(model=MODEL_CHAT, messages=messages, temperature=0.1)
        data = json.loads(retry.choices[0].message.content)
        data["citations"] = [citation.dict() for citation in citations]
        return AnswerContract.parse_obj(data)


def answer_question(session_id: str, topic: str, question: str, citations: List[Citation]) -> AnswerContract:
    passages = retrieve(session_id, question)
    context = _format_context(passages)
    answer = _call_model(question, topic, context, citations)
    return answer


__all__ = ["answer_question"]
