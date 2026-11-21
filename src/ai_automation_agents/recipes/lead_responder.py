"""Recipe 08 — Lead responder.

Scores a lead against your criteria with transparent, deterministic points,
drafts a follow-up through the injected provider, and holds the draft
behind an approval flag: a draft is *not* a send, and nothing in this module
can send. Shared memory records every contact, so a returning lead is
recognized and the follow-up is framed as a follow-up.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from ai_automation_agents.memory import MemoryStore
from ai_automation_agents.providers import ChatProvider

NAMESPACE = "lead-responder"


class Lead(BaseModel):
    """One inbound lead."""

    id: str
    name: str
    email: str = ""
    company: str = ""
    location: str = ""
    budget: float = 0.0
    interest: str = ""
    message: str = ""


class LeadCriteria(BaseModel):
    """What a good lead looks like, for scoring."""

    min_budget: float = 0.0
    keywords: list[str] = Field(default_factory=list)
    locations: list[str] = Field(default_factory=list)
    pass_score: int = 50


class LeadScore(BaseModel):
    """A lead's score with the reasons, so a human can audit it."""

    score: int
    passes: bool
    reasons: list[str] = Field(default_factory=list)
    prior_contacts: int = 0


class LeadResponse(BaseModel):
    """A scored lead plus its follow-up draft and approval state."""

    lead: Lead
    score: LeadScore
    draft: str
    status: str = "draft"  # draft -> approved; there is no "sent" state here


def score_lead(lead: Lead, criteria: LeadCriteria) -> tuple[int, list[str]]:
    """Score ``lead`` against ``criteria``. Pure and deterministic.

    Budget fit is worth up to 40 points, each matched interest keyword 15
    (capped at 45), and a location match 15.
    """
    reasons: list[str] = []
    score = 0
    if criteria.min_budget > 0:
        if lead.budget >= criteria.min_budget:
            score += 40
            reasons.append(f"Budget {lead.budget:g} meets minimum {criteria.min_budget:g} (+40)")
        else:
            reasons.append(f"Budget {lead.budget:g} below minimum {criteria.min_budget:g} (+0)")
    haystack = f"{lead.interest} {lead.message}".lower()
    matched = [kw for kw in criteria.keywords if kw.lower() in haystack]
    if matched:
        gained = min(15 * len(matched), 45)
        score += gained
        reasons.append(f"Matched keywords {matched} (+{gained})")
    if criteria.locations:
        if lead.location.lower() in {loc.lower() for loc in criteria.locations}:
            score += 15
            reasons.append(f"Location {lead.location} is in target area (+15)")
        else:
            reasons.append(f"Location {lead.location} outside target area (+0)")
    return min(score, 100), reasons


_DRAFT_PROMPT = """Draft a short follow-up message to this lead. Warm, specific, no hype.
Do not promise pricing or timelines that need approval. This is a draft for human review.
Name: {name}
Company: {company}
Interest: {interest}
Their message: {message}
{prior_note}
Draft:"""


class LeadResponderAgent:
    """Score, remember, and draft follow-ups — approval-gated."""

    def __init__(self, provider: ChatProvider, memory: MemoryStore | None = None) -> None:
        self._provider = provider
        self._memory = memory or MemoryStore()

    def respond(self, lead: Lead, criteria: LeadCriteria) -> LeadResponse:
        """Score ``lead``, draft a follow-up, and record the contact."""
        prior = int(self._memory.get(NAMESPACE, f"contacts:{lead.id}", 0))
        raw_score, reasons = score_lead(lead, criteria)
        if prior:
            reasons.append(f"Prior contact on record ({prior} previous) — framed as follow-up")
        score = LeadScore(
            score=raw_score,
            passes=raw_score >= criteria.pass_score,
            reasons=reasons,
            prior_contacts=prior,
        )
        prior_note = (
            f"Note: we have contacted this lead {prior} time(s) before; "
            "write it as a gentle follow-up."
            if prior
            else ""
        )
        draft = self._provider.complete(
            _DRAFT_PROMPT.format(
                name=lead.name,
                company=lead.company,
                interest=lead.interest,
                message=lead.message,
                prior_note=prior_note,
            )
        ).strip()
        self._memory.set(NAMESPACE, f"contacts:{lead.id}", prior + 1)
        self._memory.append(
            NAMESPACE,
            "history",
            {"lead_id": lead.id, "score": raw_score, "status": "draft"},
        )
        return LeadResponse(lead=lead, score=score, draft=draft, status="draft")

    @staticmethod
    def approve(response: LeadResponse) -> LeadResponse:
        """Flip a draft to approved. Approval still sends nothing."""
        response.status = "approved"
        return response
