"""Deterministic fakes for every provider boundary.

These are real, shipped code — not test-only scaffolding. The CLI demos run
on them, and the test suite uses them (plus small per-test stubs) so nothing
in this repository needs a network, an API key, or a paid model call to be
verified end to end.
"""

from __future__ import annotations

import hashlib
import math
import re
from typing import Any

from ai_automation_agents.providers import HttpFetchError


class FakeChatProvider:
    """A scripted :class:`ChatProvider`.

    Rules are ``(needle, response)`` pairs; the first rule whose needle
    appears in the prompt (case-insensitive) wins. Every prompt is recorded
    in ``prompts`` so tests can assert what a recipe actually asked.
    """

    def __init__(
        self,
        rules: list[tuple[str, str]] | None = None,
        default: str = "",
    ) -> None:
        self.rules = rules or []
        self.default = default
        self.prompts: list[str] = []

    def complete(self, prompt: str) -> str:
        self.prompts.append(prompt)
        lowered = prompt.lower()
        for needle, response in self.rules:
            if needle.lower() in lowered:
                return response
        return self.default


class FakeHttpClient:
    """A scripted :class:`HttpClient` serving canned pages by exact URL."""

    def __init__(self, pages: dict[str, str] | None = None) -> None:
        self.pages = pages or {}
        self.requested: list[str] = []

    def get(self, url: str) -> str:
        self.requested.append(url)
        if url not in self.pages:
            raise HttpFetchError(f"FakeHttpClient has no page for {url}")
        return self.pages[url]


class FakeEmbedder:
    """A deterministic bag-of-words embedder.

    Each token is hashed into one of ``dimensions`` buckets and counted, then
    the vector is L2-normalized. Texts sharing words land close together,
    which is all the retrieval recipes need from an embedder in tests.
    """

    def __init__(self, dimensions: int = 64) -> None:
        self.dimensions = dimensions

    def embed(self, text: str) -> list[float]:
        vector = [0.0] * self.dimensions
        for token in re.findall(r"[a-z0-9]+", text.lower()):
            digest = hashlib.sha256(token.encode()).digest()
            bucket = int.from_bytes(digest[:4], "big") % self.dimensions
            vector[bucket] += 1.0
        norm = math.sqrt(sum(value * value for value in vector))
        if norm == 0:
            return vector
        return [value / norm for value in vector]


class FakeExecutor:
    """An :class:`Executor` that records calls instead of causing effects."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def execute(self, action: str, payload: dict[str, Any]) -> dict[str, Any]:
        self.calls.append((action, payload))
        return {"status": "ok", "action": action, "simulated": True}
