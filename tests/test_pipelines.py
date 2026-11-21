from ai_automation_agents.demo_data import (
    PIPELINE_MESSAGES,
    RESEARCH_PAGES,
    build_demo_http,
    build_demo_provider,
)
from ai_automation_agents.memory import MemoryStore
from ai_automation_agents.pipelines import research_digest_pipeline, triage_leads_pipeline
from ai_automation_agents.recipes.inbox_triage import InboxTriageAgent
from ai_automation_agents.recipes.lead_responder import LeadCriteria, LeadResponderAgent
from ai_automation_agents.recipes.scheduled_reporter import Reporter
from ai_automation_agents.recipes.web_research import WebResearchAgent

QUESTION = "How do approval gates keep agent actions safe?"
CRITERIA = LeadCriteria(min_budget=1000, keywords=["automation"], locations=["Detroit"])


def test_research_digest_pipeline_chains_summary_into_a_digest() -> None:
    researcher = WebResearchAgent(build_demo_http(), build_demo_provider())
    memory = MemoryStore()
    reporter = Reporter(memory)
    report, digest = research_digest_pipeline(researcher, reporter, QUESTION, list(RESEARCH_PAGES))
    assert "human in charge" in report.summary
    assert "human in charge" in digest
    assert "## Sources" in digest
    assert "https://example.com/approval-gates — fetched" in digest
    assert memory.get("scheduled-reporter", "run_count") == 1


def test_triage_leads_pipeline_scores_real_leads_and_skips_spam() -> None:
    triage = InboxTriageAgent(build_demo_provider())
    responder = LeadResponderAgent(build_demo_provider(), MemoryStore())
    result = triage_leads_pipeline(triage, responder, PIPELINE_MESSAGES, CRITERIA)
    assert result.triage_counts == {"urgent": 0, "routine": 1, "spam": 1}
    assert result.skipped_spam_leads == 1
    assert len(result.lead_responses) == 1
    response = result.lead_responses[0]
    assert response.lead.name == "Dana"
    assert response.score.score == 70
    assert response.status == "draft"
