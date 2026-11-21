from ai_automation_agents.demo import DEMO_FAQ
from ai_automation_agents.recipes.support_faq import FaqEntry, SupportFaqAgent


def test_known_question_answers_with_citation() -> None:
    agent = SupportFaqAgent(DEMO_FAQ)
    answer = agent.answer("Can I get a refund for my pack?")
    assert answer.escalate is False
    assert answer.sources == ["faq-refund"]
    assert "14 days" in answer.text
    assert "[faq-refund]" in answer.text


def test_hours_question_matches_hours_entry() -> None:
    agent = SupportFaqAgent(DEMO_FAQ)
    answer = agent.answer("When are you open?")
    assert answer.escalate is False
    assert answer.sources == ["faq-hours"]


def test_unknown_question_escalates_to_a_human() -> None:
    agent = SupportFaqAgent(DEMO_FAQ)
    answer = agent.answer("Do you offer gift wrapping?")
    assert answer.escalate is True
    assert answer.sources == []
    assert "escalating" in answer.text


def test_empty_faq_set_always_escalates() -> None:
    agent = SupportFaqAgent([])
    assert agent.answer("What are your hours?").escalate is True


def test_custom_entries_are_used() -> None:
    entries = [
        FaqEntry(id="e1", question="How do I reset my password?", answer="Use the reset link.")
    ]
    agent = SupportFaqAgent(entries)
    answer = agent.answer("password reset help")
    assert answer.escalate is False
    assert answer.sources == ["e1"]
