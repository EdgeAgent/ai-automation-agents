"""Recipe 07 — Inbox triage.

Classifies incoming messages as urgent, routine, or spam, drafts a reply
for everything that deserves one, and returns a handoff list for a human.
It never sends anything — there is deliberately no send path in this
module. Classification and drafting go through the injected chat provider;
tests and demos inject a fake.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel

from ai_automation_agents.providers import ChatProvider, extract_json

Category = Literal["urgent", "routine", "spam"]


class IncomingMessage(BaseModel):
    """One message to triage. ``lead`` carries optional structured lead data
    used by the triage → lead-responder pipeline."""

    id: str
    sender: str
    subject: str
    body: str
    lead: dict[str, Any] | None = None


class TriageItem(BaseModel):
    """One triaged message: its category and a draft reply, if any."""

    message_id: str
    sender: str
    subject: str
    category: Category
    reason: str = ""
    draft_reply: str | None = None


class TriageReport(BaseModel):
    """The handoff list: every message, classified, drafts attached."""

    items: list[TriageItem]

    def by_category(self, category: Category) -> list[TriageItem]:
        return [item for item in self.items if item.category == category]

    def render_handoff(self) -> str:
        """Render the handoff list as Markdown for a human reviewer."""
        lines = ["# Inbox triage — handoff list", ""]
        for category in ("urgent", "routine", "spam"):
            group = self.by_category(category)  # type: ignore[arg-type]
            lines.append(f"## {category.capitalize()} ({len(group)})")
            lines.append("")
            for item in group:
                lines.append(f"- **{item.subject}** — from {item.sender}")
                if item.reason:
                    lines.append(f"  - Why: {item.reason}")
                if item.draft_reply:
                    lines.append(f"  - Draft reply: {item.draft_reply}")
            lines.append("")
        lines.append("_Drafts only — nothing was sent._")
        return "\n".join(lines)


_CLASSIFY_PROMPT = """Classify this incoming message for a busy operator.
Message subject: {subject}
Message from: {sender}
Message body: {body}

Respond with JSON only: {{"category": "urgent" | "routine" | "spam", "reason": "short reason"}}.
- urgent: needs same-day human attention (outages, deadlines, unhappy customers, money at risk).
- routine: normal business that can be answered in due course.
- spam: unsolicited bulk, scams, or giveaways."""

_DRAFT_PROMPT = """Draft a short, professional reply to this {category} message.
Do not promise anything that needs approval. The draft is for human review.
Subject: {subject}
Body: {body}

Reply with the draft text only."""


class InboxTriageAgent:
    """Classify + draft over a batch of messages. Draft-only by design."""

    def __init__(self, provider: ChatProvider) -> None:
        self._provider = provider

    def _classify(self, message: IncomingMessage) -> tuple[Category, str]:
        raw = self._provider.complete(
            _CLASSIFY_PROMPT.format(
                subject=message.subject, sender=message.sender, body=message.body
            )
        )
        try:
            parsed = extract_json(raw)
            category = parsed.get("category", "routine")
            reason = str(parsed.get("reason", ""))
        except (ValueError, AttributeError):
            category, reason = "routine", "Provider output unparsable; defaulted to routine."
        if category not in ("urgent", "routine", "spam"):
            category = "routine"
        return category, reason  # type: ignore[return-value]

    def triage(self, messages: list[IncomingMessage]) -> TriageReport:
        """Classify every message and draft replies for non-spam."""
        items: list[TriageItem] = []
        for message in messages:
            category, reason = self._classify(message)
            draft = None
            if category != "spam":
                draft = self._provider.complete(
                    _DRAFT_PROMPT.format(
                        category=category, subject=message.subject, body=message.body
                    )
                ).strip()
            items.append(
                TriageItem(
                    message_id=message.id,
                    sender=message.sender,
                    subject=message.subject,
                    category=category,
                    reason=reason,
                    draft_reply=draft,
                )
            )
        return TriageReport(items=items)
