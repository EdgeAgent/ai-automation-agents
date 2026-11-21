"""Retrieval helpers shared by the document recipes (doc-qa, support-faq).

The default retriever is keyword overlap — transparent, deterministic, and
good enough for small local document sets. An embedder can be plugged in
instead; the doc-qa recipe then ranks by cosine similarity. Either way the
recipes cite the sources they used and escalate when nothing clears the
relevance threshold.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field

from ai_automation_agents.providers import Embedder

STOPWORDS = frozenset(
    [
        "a",
        "an",
        "the",
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "of",
        "to",
        "in",
        "on",
        "for",
        "and",
        "or",
        "with",
        "at",
        "by",
        "from",
        "what",
        "which",
        "who",
        "whom",
        "this",
        "that",
        "these",
        "those",
        "it",
        "its",
        "as",
        "do",
        "does",
        "did",
        "can",
        "could",
        "should",
        "would",
        "will",
        "shall",
        "may",
        "might",
        "i",
        "you",
        "he",
        "she",
        "we",
        "they",
        "me",
        "him",
        "her",
        "us",
        "them",
        "my",
        "your",
        "his",
        "our",
        "their",
        "how",
        "when",
        "where",
        "why",
        "not",
        "no",
        "yes",
        "if",
        "then",
        "than",
        "so",
    ]
)


def tokenize(text: str) -> list[str]:
    """Lowercase word tokens with stopwords removed."""
    return [token for token in re.findall(r"[a-z0-9]+", text.lower()) if token not in STOPWORDS]


@dataclass(frozen=True)
class Document:
    """One retrievable document: an id, a title, and plain text."""

    id: str
    title: str
    text: str


@dataclass(frozen=True)
class ScoredDocument:
    """A document plus its relevance score for one query (higher is better)."""

    document: Document
    score: float
    matched_terms: list[str] = field(default_factory=list)


def keyword_score(query_terms: list[str], document: Document) -> ScoredDocument:
    """Score a document by weighted query-term overlap.

    Title matches count double. The raw count is normalized by the square
    root of the document's token count so long documents do not win by bulk.
    """
    title_terms = tokenize(document.title)
    body_terms = tokenize(document.text)
    matched: list[str] = []
    raw = 0.0
    for term in set(query_terms):
        in_title = title_terms.count(term)
        in_body = body_terms.count(term)
        if in_title or in_body:
            matched.append(term)
            raw += 2.0 * in_title + 1.0 * in_body
    length = max(len(body_terms), 1)
    return ScoredDocument(document, raw / math.sqrt(length), sorted(matched))


def cosine_similarity(left: list[float], right: list[float]) -> float:
    """Cosine similarity between two vectors (0.0 when either is empty)."""
    if not left or not right or len(left) != len(right):
        return 0.0
    dot = sum(a * b for a, b in zip(left, right, strict=True))
    norm_left = math.sqrt(sum(a * a for a in left))
    norm_right = math.sqrt(sum(b * b for b in right))
    if norm_left == 0 or norm_right == 0:
        return 0.0
    return dot / (norm_left * norm_right)


class Retriever:
    """Ranks documents for a query, by keywords or by embeddings."""

    def __init__(self, documents: list[Document], embedder: Embedder | None = None) -> None:
        self._documents = list(documents)
        self._embedder = embedder
        self._embeddings: dict[str, list[float]] = {}
        if embedder is not None:
            for document in self._documents:
                combined = f"{document.title}\n{document.text}"
                self._embeddings[document.id] = embedder.embed(combined)

    def search(self, query: str, limit: int = 3) -> list[ScoredDocument]:
        """Return up to ``limit`` documents ranked best-first for ``query``."""
        if self._embedder is not None:
            query_vector = self._embedder.embed(query)
            scored = [
                ScoredDocument(
                    document,
                    cosine_similarity(query_vector, self._embeddings[document.id]),
                )
                for document in self._documents
            ]
        else:
            query_terms = tokenize(query)
            scored = [keyword_score(query_terms, document) for document in self._documents]
        scored.sort(key=lambda item: item.score, reverse=True)
        return scored[:limit]

    def __len__(self) -> int:
        return len(self._documents)
