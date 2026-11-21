"""Recipe 04 — Support FAQ agent.

Answers customer questions from a local FAQ set, with a citation for every
answer and an explicit escalation path: when no entry clears the relevance
threshold, the agent says it does not know and routes the question to a
human instead of guessing. Draft-only — it returns answers for a human or a
caller to use; it talks to no customer itself.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from ai_automation_agents.retrieval import Document, Retriever

DEFAULT_THRESHOLD = 0.30


class FaqEntry(BaseModel):
    """One FAQ entry: the canonical question and its approved answer."""

    id: str
    question: str
    answer: str
    tags: list[str] = Field(default_factory=list)


class FaqAnswer(BaseModel):
    """One support answer, or an escalation when nothing matched."""

    question: str
    text: str
    sources: list[str] = Field(default_factory=list)
    escalate: bool


class SupportFaqAgent:
    """Keyword-matched FAQ answers with citations and escalation."""

    def __init__(self, entries: list[FaqEntry], threshold: float = DEFAULT_THRESHOLD) -> None:
        self._entries = {entry.id: entry for entry in entries}
        documents = [
            Document(id=entry.id, title=entry.question, text=f"{entry.question} {entry.answer}")
            for entry in entries
        ]
        self._retriever = Retriever(documents)
        self._threshold = threshold

    def answer(self, question: str) -> FaqAnswer:
        """Answer from the FAQ set, or escalate to a human."""
        results = self._retriever.search(question, limit=1)
        if not results or results[0].score < self._threshold:
            return FaqAnswer(
                question=question,
                text=(
                    "I don't have an approved answer for that yet. "
                    "I'm escalating this to a human who can help."
                ),
                sources=[],
                escalate=True,
            )
        entry = self._entries[results[0].document.id]
        return FaqAnswer(
            question=question,
            text=f"{entry.answer} [{entry.id}]",
            sources=[entry.id],
            escalate=False,
        )
