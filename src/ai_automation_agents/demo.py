"""Runnable demos for every recipe, all on fakes.

Each runner wires a recipe to the scripted demo provider / fake HTTP client
from :mod:`ai_automation_agents.demo_data`, feeds it the sample inputs, and
returns a printable summary. The CLI calls these; so does
``scripts/demo.py``. No demo touches the network or a paid model.
"""

from __future__ import annotations

from decimal import Decimal

from ai_automation_agents import demo_data
from ai_automation_agents.approval import ApprovalGate
from ai_automation_agents.fakes import FakeExecutor
from ai_automation_agents.memory import MemoryStore
from ai_automation_agents.pipelines import research_digest_pipeline, triage_leads_pipeline
from ai_automation_agents.recipes.approval_actor import ApprovalGatedActor, PlannedAction
from ai_automation_agents.recipes.code_review import CodeReviewAgent
from ai_automation_agents.recipes.doc_qa import DocQAAgent
from ai_automation_agents.recipes.inbox_triage import InboxTriageAgent
from ai_automation_agents.recipes.lead_cleaner import clean_leads
from ai_automation_agents.recipes.lead_responder import (
    Lead,
    LeadCriteria,
    LeadResponderAgent,
)
from ai_automation_agents.recipes.meeting_notes import MeetingNotesAgent
from ai_automation_agents.recipes.quote_drafter import QuoteItem, QuoteRequest, build_quote
from ai_automation_agents.recipes.scheduled_reporter import (
    Reporter,
    ReportInput,
    ReportSection,
)
from ai_automation_agents.recipes.social_drafter import SocialDrafterAgent
from ai_automation_agents.recipes.support_faq import FaqEntry, SupportFaqAgent
from ai_automation_agents.recipes.web_research import WebResearchAgent
from ai_automation_agents.retrieval import Document
from ai_automation_agents.router import Router

DEMO_DOCS = [
    Document(
        id="services",
        title="Edge Agency services",
        text=(
            "Edge Agency builds AI automation for small businesses. Services include "
            "AI receptionists, lead list building, and workflow automation with n8n "
            "and Make. The AI receptionist answers calls, books appointments, and "
            "sends a summary after each call."
        ),
    ),
    Document(
        id="pricing",
        title="Pricing and first pack",
        text=(
            "The first lead pack costs $50 and includes 5 leads built to the buyer's "
            "criteria. Regular packs cost $149. A monthly pipeline costs $450 for "
            "25 leads."
        ),
    ),
    Document(
        id="delivery",
        title="Delivery and turnaround",
        text=(
            "Lead packs are delivered by email within two business days. Every lead "
            "includes the owner's contact phone number."
        ),
    ),
]

DEMO_FAQ = [
    FaqEntry(
        id="faq-hours",
        question="What are your business hours?",
        answer="We are open Monday to Friday, 9am to 5pm Eastern.",
    ),
    FaqEntry(
        id="faq-refund",
        question="What is your refund policy?",
        answer="Unused lead packs can be refunded within 14 days of delivery.",
    ),
    FaqEntry(
        id="faq-shipping",
        question="Do you ship outside Canada?",
        answer="We deliver lead packs by email worldwide; there is no physical shipping.",
    ),
    FaqEntry(
        id="faq-contact",
        question="How do I reach a human?",
        answer="Reply to any email from us or use the contact form; a human replies "
        "within one business day.",
    ),
]

DEMO_CRITERIA = LeadCriteria(
    min_budget=1000,
    keywords=["automation"],
    locations=["Detroit"],
    pass_score=50,
)


def demo_lead_cleaner() -> str:
    result = clean_leads(demo_data.SAMPLE_CSV)
    stats = result.stats
    lines = [
        (
            f"Input rows: {stats['input_rows']} → kept {stats['kept_rows']} "
            f"(duplicates removed: {stats['duplicates_removed']})"
        ),
        f"Grades: A={stats['grade_a']} B={stats['grade_b']} C={stats['grade_c']}",
        "",
        result.cleaned_csv.strip(),
    ]
    return "\n".join(lines)


def demo_quote_drafter() -> str:
    quote = build_quote(
        QuoteRequest(
            client="Riverside Dental",
            items=[
                QuoteItem(description="AI receptionist setup", unit_price=Decimal(400)),
                QuoteItem(description="Lead pack — 25 leads", unit_price=Decimal(450)),
            ],
            labor_hours=Decimal(3),
            labor_rate=Decimal(85),
            tax_rate=Decimal(13),
            deposit_percent=Decimal(30),
        )
    )
    return quote.render()


def demo_doc_qa() -> str:
    agent = DocQAAgent(DEMO_DOCS)
    lines = []
    for question in ("How much does the first lead pack cost?", "What is the capital of France?"):
        answer = agent.answer(question)
        lines.append(f"Q: {question}\nA: {answer.text} (found={answer.found})")
    return "\n".join(lines)


def demo_support_faq() -> str:
    agent = SupportFaqAgent(DEMO_FAQ)
    lines = []
    for question in ("Can I get a refund for my pack?", "Do you offer gift wrapping?"):
        answer = agent.answer(question)
        lines.append(f"Q: {question}\nA: {answer.text} (escalate={answer.escalate})")
    return "\n".join(lines)


def demo_scheduled_reporter() -> str:
    memory = MemoryStore()
    reporter = Reporter(memory, clock=demo_data.demo_clock)
    digest = reporter.run_once(
        ReportInput(
            title="Friday digest",
            sections=[
                ReportSection(
                    heading="Wins",
                    lines=["Shipped the agents repo", "Starter-kit tests still green"],
                ),
                ReportSection(heading="Numbers", lines=["Recipes: 12", "Pipelines: 2"]),
            ],
        )
    )
    return digest + f"\nRuns recorded in memory: {memory.get('scheduled-reporter', 'run_count')}"


def demo_approval_actor() -> str:
    actor = ApprovalGatedActor(ApprovalGate(clock=demo_data.demo_clock))
    executor = FakeExecutor()
    plan = [
        PlannedAction(
            action="send_report",
            payload={"to": "team@example.com"},
            reason="Weekly digest is ready",
        ),
        PlannedAction(action="archive_files", payload={"count": 12}, reason="Monthly cleanup"),
        PlannedAction(
            action="delete_records", payload={"table": "drafts"}, reason="Proposed purge"
        ),
    ]
    result = actor.run_plan(plan, decide=lambda p: p.action != "delete_records", executor=executor)
    return (
        f"Executed: {len(result.executed)} · Denied: {len(result.denied)} · "
        f"Executor calls: {len(executor.calls)} · Receipts valid: {result.receipts_valid}\n"
        "The delete_records proposal was denied and never reached the executor."
    )


def demo_inbox_triage() -> str:
    agent = InboxTriageAgent(demo_data.build_demo_provider())
    return agent.triage(demo_data.SAMPLE_MESSAGES).render_handoff()


def demo_lead_responder() -> str:
    memory = MemoryStore()
    agent = LeadResponderAgent(demo_data.build_demo_provider(), memory)
    dana = Lead(
        id="lead-dana",
        name="Dana",
        email="dana@northwind.example",
        company="Northwind Traders",
        location="Detroit",
        budget=2500,
        interest="automation package for order intake",
        message="We want help automating order intake.",
    )
    marcus = Lead(
        id="lead-marcus",
        name="Marcus",
        email="marcus@leeproperties.example",
        company="Lee Properties",
        location="Austin",
        budget=300,
        interest="website refresh",
        message="Thinking about a new site.",
    )
    first = agent.respond(dana, DEMO_CRITERIA)
    second = agent.respond(dana, DEMO_CRITERIA)
    other = agent.respond(marcus, DEMO_CRITERIA)
    lines = [
        f"Dana — score {first.score.score} (passes={first.score.passes}), status {first.status}",
        (
            f"Dana again — prior contacts noted: {second.score.prior_contacts} "
            "(memory recognized the returning lead)"
        ),
        f"Marcus — score {other.score.score} (passes={other.score.passes})",
        "",
        f"Draft for Dana: {first.draft}",
    ]
    return "\n".join(lines)


def demo_meeting_notes() -> str:
    agent = MeetingNotesAgent(demo_data.build_demo_provider())
    return agent.process(demo_data.SAMPLE_TRANSCRIPT).render()


def demo_social_drafter() -> str:
    agent = SocialDrafterAgent(demo_data.build_demo_provider())
    drafts = agent.draft("local-first AI agents", platform="x", variants=3)
    lines = []
    for index, draft in enumerate(drafts, start=1):
        lines.append(
            f"{index}. ({draft.char_count} chars, within limit: {draft.within_limit}) "
            f"{draft.text} {' '.join(draft.hashtags)}"
        )
    return "\n".join(lines)


def demo_web_research() -> str:
    agent = WebResearchAgent(demo_data.build_demo_http(), demo_data.build_demo_provider())
    report = agent.research(
        "How do approval gates keep agent actions safe?",
        list(demo_data.RESEARCH_PAGES),
    )
    return report.render()


def demo_code_review() -> str:
    agent = CodeReviewAgent(demo_data.build_demo_provider())
    report = agent.review(demo_data.SAMPLE_DIFF)
    return report.render() + f"\nCounts by severity: {report.counts}"


RUNNERS = {
    "lead-list-cleaner": demo_lead_cleaner,
    "quote-drafter": demo_quote_drafter,
    "doc-qa": demo_doc_qa,
    "support-faq": demo_support_faq,
    "scheduled-reporter": demo_scheduled_reporter,
    "approval-gated-actor": demo_approval_actor,
    "inbox-triage": demo_inbox_triage,
    "lead-responder": demo_lead_responder,
    "meeting-notes": demo_meeting_notes,
    "social-drafter": demo_social_drafter,
    "web-research": demo_web_research,
    "code-review": demo_code_review,
}


def run_recipe_demo(name: str) -> str:
    """Run one recipe's demo and return its printable summary."""
    if name not in RUNNERS:
        choices = ", ".join(sorted(RUNNERS))
        raise ValueError(f"Unknown recipe {name!r}. Available: {choices}")
    return RUNNERS[name]()


def run_pipeline_demo(name: str) -> str:
    """Run one reference pipeline end to end on fakes."""
    if name == "research-digest":
        researcher = WebResearchAgent(demo_data.build_demo_http(), demo_data.build_demo_provider())
        reporter = Reporter(MemoryStore(), clock=demo_data.demo_clock)
        _, digest = research_digest_pipeline(
            researcher,
            reporter,
            "How do approval gates keep agent actions safe?",
            list(demo_data.RESEARCH_PAGES),
        )
        return digest
    if name == "triage-leads":
        triage = InboxTriageAgent(demo_data.build_demo_provider())
        responder = LeadResponderAgent(demo_data.build_demo_provider(), MemoryStore())
        result = triage_leads_pipeline(
            triage, responder, demo_data.PIPELINE_MESSAGES, DEMO_CRITERIA
        )
        lines = [
            f"Triage counts: {result.triage_counts}",
            f"Spam leads skipped before the responder: {result.skipped_spam_leads}",
        ]
        for response in result.lead_responses:
            lines.append(
                f"Lead {response.lead.name}: score {response.score.score}, "
                f"status {response.status} (draft — not sent)"
            )
        return "\n".join(lines)
    raise ValueError(f"Unknown pipeline {name!r}. Available: research-digest, triage-leads")


def run_full_demo() -> str:
    """Run the headline demos and both pipelines; return a summary report."""
    sections: list[str] = ["AI AUTOMATION AGENTS — DEMO (all fakes, nothing sent)", ""]
    router = Router()
    for task in (
        "Please clean and dedupe this CSV of leads",
        "Draft a follow-up for this new lead",
    ):
        decision = router.route(task)
        sections.append(f"Router: '{task}' → {decision.recipe} ({decision.method})")
    sections.append("")
    for name in (
        "lead-list-cleaner",
        "quote-drafter",
        "inbox-triage",
        "lead-responder",
        "approval-gated-actor",
    ):
        sections.append(f"===== Recipe: {name} =====")
        sections.append(run_recipe_demo(name))
        sections.append("")
    for pipeline in ("research-digest", "triage-leads"):
        sections.append(f"===== Pipeline: {pipeline} =====")
        sections.append(run_pipeline_demo(pipeline))
        sections.append("")
    sections.append(
        "Summary: 5 recipes + 2 pipelines ran end to end on fake providers. "
        "Zero network calls, zero paid model calls, zero messages sent."
    )
    return "\n".join(sections)
