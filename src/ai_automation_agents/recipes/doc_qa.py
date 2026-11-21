"""Recipe 03 — Document Q&A with citations.

Answers questions over a small local document set. Retrieval is keyword
overlap by default, or cosine similarity when an embedder is plugged in.
Answers are extractive — built from the best-matching sentences of the
best-matching document — and always carry their source. When nothing clears
the relevance threshold the agent says so and flags escalation instead of
inventing an answer.
"""

from __future__ import annotations

import re

from pydantic import BaseModel, Field

from ai_automation_agents.providers import Embedder
from ai_automation_agents.retrieval import Document, Retriever, tokenize

DEFAULT_THRESHOLD = 0.35


class Answer(BaseModel):
    """One answer: text, cited sources, and whether a human is needed."""

    question: str
    text: str
    sources: list[str] = Field(default_factory=list)
    found: bool
    escalate: bool
    confidence: float


class DocQAAgent:
    """Extractive Q&A over a fixed local document set."""

    def __init__(
        self,
        documents: list[Document],
        embedder: Embedder | None = None,
        threshold: float = DEFAULT_THRESHOLD,
    ) -> None:
        self._retriever = Retriever(documents, embedder=embedder)
        self._threshold = threshold

    def answer(self, question: str) -> Answer:
        """Answer ``question`` from the document set, or escalate."""
        results = self._retriever.search(question, limit=1)
        if not results or results[0].score < self._threshold:
            return Answer(
                question=question,
                text=("I don't know — no document in the set covers that. Escalating to a human."),
                sources=[],
                found=False,
                escalate=True,
                confidence=results[0].score if results else 0.0,
            )
        best = results[0]
        passage = self._best_passage(question, best.document.text)
        return Answer(
            question=question,
            text=f"{passage} [{best.document.id}]",
            sources=[best.document.id],
            found=True,
            escalate=False,
            confidence=round(min(best.score, 1.0), 3),
        )

    @staticmethod
    def _best_passage(question: str, text: str, max_sentences: int = 2) -> str:
        query_terms = set(tokenize(question))
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]
        if not sentences:
            return text.strip()
        scored = sorted(
            sentences,
            key=lambda s: len(query_terms & set(tokenize(s))),
            reverse=True,
        )
        chosen = [s for s in scored if query_terms & set(tokenize(s))][:max_sentences]
        return " ".join(chosen) if chosen else sentences[0]
