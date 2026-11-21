"""Recipe 11 — Web-research agent.

Question + URLs in → a sourced summary out. Pages are fetched through the
injected HTTP client, reduced to readable text with the standard library,
and summarized through the injected chat provider. Every source is listed
with an excerpt — and a fetch failure is recorded as a failed source, never
silently dropped or invented around.
"""

from __future__ import annotations

import re
from html.parser import HTMLParser

from pydantic import BaseModel, Field

from ai_automation_agents.providers import ChatProvider, HttpClient, HttpFetchError

MAX_PAGE_CHARS = 6000


class _TextExtractor(HTMLParser):
    """Collects visible text, skipping script/style/head-title content."""

    _SKIP_TAGS = ("script", "style", "noscript", "title")

    def __init__(self) -> None:
        super().__init__()
        self._skip = 0
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list) -> None:
        if tag in self._SKIP_TAGS:
            self._skip += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in self._SKIP_TAGS and self._skip:
            self._skip -= 1

    def handle_data(self, data: str) -> None:
        if not self._skip and data.strip():
            self.parts.append(data.strip())


def extract_text(html: str) -> str:
    """Reduce an HTML page to readable text."""
    parser = _TextExtractor()
    parser.feed(html)
    text = " ".join(parser.parts)
    return re.sub(r"\s+", " ", text).strip()


class ResearchSource(BaseModel):
    """One fetched source (or a recorded fetch failure)."""

    url: str
    excerpt: str = ""
    fetched: bool = True
    error: str = ""


class ResearchReport(BaseModel):
    """A summary with the sources it was built from."""

    question: str
    summary: str
    sources: list[ResearchSource] = Field(default_factory=list)

    def render(self) -> str:
        """Render the report as Markdown with a source list."""
        lines = [f"# Research: {self.question}", "", self.summary, "", "## Sources", ""]
        for source in self.sources:
            if source.fetched:
                lines.append(f'- {source.url} — "{source.excerpt[:120]}..."')
            else:
                lines.append(f"- {source.url} — FETCH FAILED: {source.error}")
        return "\n".join(lines)


_SUMMARY_PROMPT = """Answer the research question using only the sources below.
Question: {question}

Sources:
{sources}

Write a concise summary that answers the question. Do not add facts that are not in the sources."""


class WebResearchAgent:
    """Fetches, extracts, and summarizes with a full source list."""

    def __init__(self, http_client: HttpClient, provider: ChatProvider) -> None:
        self._http = http_client
        self._provider = provider

    def research(self, question: str, urls: list[str]) -> ResearchReport:
        """Fetch ``urls`` and summarize what they say about ``question``."""
        sources: list[ResearchSource] = []
        source_blocks: list[str] = []
        for url in urls:
            try:
                html = self._http.get(url)
            except HttpFetchError as exc:
                sources.append(ResearchSource(url=url, fetched=False, error=str(exc)))
                continue
            text = extract_text(html)[:MAX_PAGE_CHARS]
            sources.append(ResearchSource(url=url, excerpt=text[:300]))
            source_blocks.append(f"[{url}]\n{text}")
        if not source_blocks:
            return ResearchReport(
                question=question,
                summary="No sources could be fetched, so no summary was produced.",
                sources=sources,
            )
        summary = self._provider.complete(
            _SUMMARY_PROMPT.format(question=question, sources="\n\n".join(source_blocks))
        ).strip()
        return ResearchReport(question=question, summary=summary, sources=sources)
