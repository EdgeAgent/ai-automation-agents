"""Pipelines: recipes chained so one recipe's output feeds the next.

Two reference pipelines ship with the repo and are covered by tests:

- ``research_digest_pipeline`` — web-research → scheduled-reporter:
  research a question, then publish the summary into a scheduled digest.
- ``triage_leads_pipeline`` — inbox-triage → lead-responder: triage the
  inbox, then score and draft follow-ups for the messages that carry leads
  (spam never reaches the responder).
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from ai_automation_agents.recipes.inbox_triage import InboxTriageAgent, IncomingMessage
from ai_automation_agents.recipes.lead_responder import (
    Lead,
    LeadCriteria,
    LeadResponderAgent,
    LeadResponse,
)
from ai_automation_agents.recipes.scheduled_reporter import Reporter, ReportInput, ReportSection
from ai_automation_agents.recipes.web_research import ResearchReport, WebResearchAgent


def research_digest_pipeline(
    researcher: WebResearchAgent,
    reporter: Reporter,
    question: str,
    urls: list[str],
    digest_title: str = "Research digest",
) -> tuple[ResearchReport, str]:
    """Research ``question`` and fold the result into a scheduled digest.

    Returns the research report and the rendered digest. The reporter
    records the run in shared memory like any other scheduled run.
    """
    report = researcher.research(question, urls)
    source_lines = [
        f"{source.url} — {'fetched' if source.fetched else 'FETCH FAILED'}"
        for source in report.sources
    ]
    digest_input = ReportInput(
        title=digest_title,
        sections=[
            ReportSection(heading=f"Research: {question}", lines=[report.summary]),
            ReportSection(heading="Sources", lines=source_lines),
        ],
        footer="Produced by the research → reporter pipeline. Draft — review before sharing.",
    )
    return report, reporter.run_once(digest_input)


class TriageLeadsResult(BaseModel):
    """The combined output of the triage → lead-responder pipeline."""

    triage_counts: dict[str, int]
    lead_responses: list[LeadResponse] = Field(default_factory=list)
    skipped_spam_leads: int = 0


def triage_leads_pipeline(
    triage: InboxTriageAgent,
    responder: LeadResponderAgent,
    messages: list[IncomingMessage],
    criteria: LeadCriteria,
) -> TriageLeadsResult:
    """Triage messages, then score + draft for the leads among them.

    A message participates when it carries structured lead data. Spam is
    counted and skipped — it never reaches the lead responder. Every
    produced follow-up stays in ``draft`` status.
    """
    report = triage.triage(messages)
    counts = {
        category: len(report.by_category(category))  # type: ignore[arg-type]
        for category in ("urgent", "routine", "spam")
    }
    by_id = {message.id: message for message in messages}
    responses: list[LeadResponse] = []
    skipped = 0
    for item in report.items:
        message = by_id[item.message_id]
        if message.lead is None:
            continue
        if item.category == "spam":
            skipped += 1
            continue
        responses.append(responder.respond(Lead(**message.lead), criteria))
    return TriageLeadsResult(
        triage_counts=counts,
        lead_responses=responses,
        skipped_spam_leads=skipped,
    )
