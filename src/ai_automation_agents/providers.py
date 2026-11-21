"""Provider interfaces every recipe is built against.

Recipes never import a vendor SDK directly. They depend on one of the small
protocols below, so tests and demos inject fakes (see :mod:`...fakes`) and a
live run injects a real adapter. This is the same fakes-first discipline as
the Step 1 starter kit: zero network, zero paid calls, zero secrets in tests.
"""

from __future__ import annotations

import json
import re
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class ChatProvider(Protocol):
    """A text-in/text-out model boundary."""

    def complete(self, prompt: str) -> str:
        """Return the model's completion for ``prompt``."""
        ...


@runtime_checkable
class HttpClient(Protocol):
    """A minimal read-only HTTP boundary for the web-research recipe."""

    def get(self, url: str) -> str:
        """Return the response body for ``url`` or raise :class:`HttpFetchError`."""
        ...


@runtime_checkable
class Embedder(Protocol):
    """A text-to-vector boundary used by the retrieval recipes."""

    def embed(self, text: str) -> list[float]:
        """Return an embedding vector for ``text``."""
        ...


@runtime_checkable
class Executor(Protocol):
    """The side-effect boundary used by the approval-gated actor."""

    def execute(self, action: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Perform ``action`` with ``payload`` and return a result mapping."""
        ...


class HttpFetchError(RuntimeError):
    """Raised when an HTTP fetch fails; recipes record it instead of crashing."""


class HttpxHttpClient:
    """Real :class:`HttpClient` backed by httpx. Never used in tests."""

    def __init__(self, timeout: float = 20.0) -> None:
        self._timeout = timeout

    def get(self, url: str) -> str:
        import httpx

        try:
            response = httpx.get(url, timeout=self._timeout, follow_redirects=True)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise HttpFetchError(f"GET {url} failed: {exc}") from exc
        return response.text


class OpenAIChatProvider:
    """Real :class:`ChatProvider` backed by the OpenAI Python SDK.

    The SDK is an optional install (``pip install -e ".[openai]"``) and is
    imported lazily so the default install — and the whole test suite — never
    needs it. Never used in tests.
    """

    def __init__(self, api_key: str | None = None, model: str = "gpt-4o-mini") -> None:
        self._api_key = api_key
        self._model = model

    def complete(self, prompt: str) -> str:
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError(
                "The openai package is not installed. Install the provider profile: "
                'python -m pip install -e ".[openai]"'
            ) from exc
        client = OpenAI(api_key=self._api_key)
        response = client.chat.completions.create(
            model=self._model,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.choices[0].message.content or ""


def extract_json(text: str) -> Any:
    """Extract the first JSON object or array embedded in provider output.

    Providers are asked to answer with JSON, but real models wrap it in prose
    or code fences. This finds the first balanced ``{...}`` or ``[...]`` span
    and parses it, raising ``ValueError`` when no JSON is present.
    """
    fenced = re.search(r"```(?:json)?\s*(.*?)```", text, flags=re.DOTALL)
    candidate = fenced.group(1) if fenced else text
    starts = [i for i in (candidate.find("{"), candidate.find("[")) if i >= 0]
    if not starts:
        raise ValueError("No JSON object or array found in provider output.")
    start = min(starts)
    opener = candidate[start]
    closer = "}" if opener == "{" else "]"
    depth = 0
    in_string = False
    escaped = False
    for index in range(start, len(candidate)):
        char = candidate[index]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == opener:
            depth += 1
        elif char == closer:
            depth -= 1
            if depth == 0:
                return json.loads(candidate[start : index + 1])
    raise ValueError("Unbalanced JSON in provider output.")
