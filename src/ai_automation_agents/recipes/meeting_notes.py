"""Recipe 09 — Meeting-notes agent.

Transcript or rough notes in → a structured summary out: decisions,
action items with owners and due dates, open questions, and a follow-up
draft ready for a human to send. Extraction goes through the injected chat
provider with a strict JSON contract; malformed provider output degrades
to an empty structure with a warning, never to invented content.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from ai_automation_agents.providers import ChatProvider, extract_json


class ActionItem(BaseModel):
    """One action item: what, who, and by when (as stated, may be blank)."""

    task: str
    owner: str = ""
    due: str = ""


class MeetingNotes(BaseModel):
    """Structured meeting outcome."""

    title: str = "Meeting"
    summary: str = ""
    decisions: list[str] = Field(default_factory=list)
    action_items: list[ActionItem] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)
    follow_up_draft: str = ""
    warnings: list[str] = Field(default_factory=list)

    def render(self) -> str:
        """Render the notes as Markdown."""
        lines = [f"# {self.title}", "", self.summary, "", "## Decisions", ""]
        lines.extend(f"- {d}" for d in self.decisions)
        lines.extend(["", "## Action items", ""])
        for item in self.action_items:
            owner = f" — {item.owner}" if item.owner else ""
            due = f" (due {item.due})" if item.due else ""
            lines.append(f"- [ ] {item.task}{owner}{due}")
        if self.open_questions:
            lines.extend(["", "## Open questions", ""])
            lines.extend(f"- {q}" for q in self.open_questions)
        if self.follow_up_draft:
            lines.extend(["", "## Follow-up draft", "", self.follow_up_draft])
        return "\n".join(lines)


_EXTRACT_PROMPT = """Extract structured notes from this meeting transcript.
Transcript:
{transcript}

Respond with JSON only:
{{"title": "short title", "summary": "2-3 sentence summary",
  "decisions": ["..."],
  "action_items": [{{"task": "...", "owner": "...", "due": "..."}}],
  "open_questions": ["..."]}}
Use only what the transcript says. Leave owner/due empty when not stated."""

_FOLLOWUP_PROMPT = """Write a short follow-up message for this meeting, for human review before sending.
Summary: {summary}
Decisions: {decisions}
Action items: {actions}

Follow-up draft:"""


class MeetingNotesAgent:
    """Turns transcripts into decisions, owners, and a follow-up draft."""

    def __init__(self, provider: ChatProvider) -> None:
        self._provider = provider

    def process(self, transcript: str) -> MeetingNotes:
        """Extract structured notes and a follow-up draft from ``transcript``."""
        warnings: list[str] = []
        raw = self._provider.complete(_EXTRACT_PROMPT.format(transcript=transcript))
        try:
            parsed = extract_json(raw)
            notes = MeetingNotes(
                title=str(parsed.get("title", "Meeting")),
                summary=str(parsed.get("summary", "")),
                decisions=[str(d) for d in parsed.get("decisions", [])],
                action_items=[ActionItem(**item) for item in parsed.get("action_items", [])],
                open_questions=[str(q) for q in parsed.get("open_questions", [])],
            )
        except (ValueError, TypeError, AttributeError) as exc:
            warnings.append(f"Provider output could not be parsed ({exc}); returning empty notes.")
            notes = MeetingNotes(warnings=warnings)
        actions = "; ".join(
            f"{item.task} ({item.owner or 'unassigned'})" for item in notes.action_items
        )
        notes.follow_up_draft = self._provider.complete(
            _FOLLOWUP_PROMPT.format(
                summary=notes.summary,
                decisions="; ".join(notes.decisions),
                actions=actions,
            )
        ).strip()
        notes.warnings = warnings
        return notes
