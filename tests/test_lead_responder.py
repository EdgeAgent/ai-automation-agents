from ai_automation_agents.demo_data import build_demo_provider
from ai_automation_agents.memory import MemoryStore
from ai_automation_agents.recipes.lead_responder import (
    Lead,
    LeadCriteria,
    LeadResponderAgent,
    score_lead,
)

CRITERIA = LeadCriteria(min_budget=1000, keywords=["automation"], locations=["Detroit"])
DANA = Lead(
    id="lead-dana",
    name="Dana",
    email="dana@northwind.example",
    company="Northwind Traders",
    location="Detroit",
    budget=2500,
    interest="automation package for order intake",
    message="We want help automating order intake.",
)
MARCUS = Lead(
    id="lead-marcus",
    name="Marcus",
    location="Austin",
    budget=300,
    interest="website refresh",
    message="Thinking about a new site.",
)


def test_scoring_rewards_budget_keywords_and_location() -> None:
    score, reasons = score_lead(DANA, CRITERIA)
    assert score == 70
    assert any("Budget" in reason for reason in reasons)
    assert any("automation" in reason for reason in reasons)


def test_scoring_gives_zero_for_a_poor_fit() -> None:
    score, _ = score_lead(MARCUS, CRITERIA)
    assert score == 0


def test_keyword_points_are_capped() -> None:
    criteria = LeadCriteria(keywords=["alpha", "beta", "gamma", "delta"])
    lead = Lead(id="x", name="X", interest="alpha beta gamma delta", message="")
    score, _ = score_lead(lead, criteria)
    assert score == 45


def test_respond_produces_a_draft_not_a_send() -> None:
    agent = LeadResponderAgent(build_demo_provider(), MemoryStore())
    response = agent.respond(DANA, CRITERIA)
    assert response.status == "draft"
    assert response.score.passes is True
    assert "Dana" in response.draft
    approved = agent.approve(response)
    assert approved.status == "approved"


def test_memory_recognizes_a_returning_lead() -> None:
    memory = MemoryStore()
    agent = LeadResponderAgent(build_demo_provider(), memory)
    first = agent.respond(DANA, CRITERIA)
    second = agent.respond(DANA, CRITERIA)
    assert first.score.prior_contacts == 0
    assert second.score.prior_contacts == 1
    assert memory.get("lead-responder", "contacts:lead-dana") == 2
    assert len(memory.get("lead-responder", "history")) == 2
