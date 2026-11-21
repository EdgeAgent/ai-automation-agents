"""Recipe 10 — Social-content drafter.

Topic + platform in → draft post variants with hashtags out. Draft-only by
design: this module drafts and validates; it has no posting path at all.
Variants come from the injected provider; each draft is checked against the
platform's character limit and flagged when it runs over.
"""

from __future__ import annotations

import re

from pydantic import BaseModel, Field

from ai_automation_agents.providers import ChatProvider

PLATFORM_LIMITS: dict[str, int] = {
    "x": 280,
    "linkedin": 3000,
    "instagram": 2200,
    "facebook": 63206,
    "threads": 500,
}


class PostDraft(BaseModel):
    """One draft post variant."""

    platform: str
    text: str
    hashtags: list[str] = Field(default_factory=list)
    char_count: int
    within_limit: bool


_PROMPT = """Write {variants} short draft social posts about: {topic}
Platform: {platform} (character limit {limit}). Separate each post with a line containing only ---.
End each post with a line starting "TAGS:" followed by hashtags.
Drafts only — write them as proposals for human review, with no calls to action that promise results."""


def _parse_block(block: str, platform: str, limit: int) -> PostDraft | None:
    text_lines: list[str] = []
    hashtags: list[str] = []
    for line in block.strip().splitlines():
        if line.strip().upper().startswith("TAGS:"):
            hashtags = re.findall(r"#\w+", line)
        else:
            text_lines.append(line)
    text = "\n".join(text_lines).strip()
    if not text:
        return None
    full = f"{text} {' '.join(hashtags)}".strip()
    return PostDraft(
        platform=platform,
        text=text,
        hashtags=hashtags,
        char_count=len(full),
        within_limit=len(full) <= limit,
    )


class SocialDrafterAgent:
    """Drafts post variants per platform. Never posts."""

    def __init__(self, provider: ChatProvider) -> None:
        self._provider = provider

    def draft(self, topic: str, platform: str = "x", variants: int = 3) -> list[PostDraft]:
        """Return up to ``variants`` draft posts for ``topic``."""
        platform = platform.lower()
        if platform not in PLATFORM_LIMITS:
            choices = ", ".join(sorted(PLATFORM_LIMITS))
            raise ValueError(f"Unknown platform {platform!r}. Known: {choices}")
        limit = PLATFORM_LIMITS[platform]
        raw = self._provider.complete(
            _PROMPT.format(variants=variants, topic=topic, platform=platform, limit=limit)
        )
        drafts = []
        for block in raw.split("---"):
            parsed = _parse_block(block, platform, limit)
            if parsed is not None:
                drafts.append(parsed)
        return drafts[:variants]
