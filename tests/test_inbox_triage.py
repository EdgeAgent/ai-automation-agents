from ai_automation_agents.demo_data import SAMPLE_MESSAGES, build_demo_provider
from ai_automation_agents.fakes import FakeChatProvider
from ai_automation_agents.recipes.inbox_triage import InboxTriageAgent


def test_classification_of_sample_messages() -> None:
    agent = InboxTriageAgent(build_demo_provider())
    report = agent.triage(SAMPLE_MESSAGES)
    categories = {item.message_id: item.category for item in report.items}
    assert categories == {"m1": "urgent", "m2": "routine", "m3": "spam"}


def test_spam_gets_no_draft_and_others_do() -> None:
    agent = InboxTriageAgent(build_demo_provider())
    report = agent.triage(SAMPLE_MESSAGES)
    by_id = {item.message_id: item for item in report.items}
    assert by_id["m3"].draft_reply is None
    assert by_id["m1"].draft_reply
    assert by_id["m2"].draft_reply


def test_handoff_render_states_nothing_was_sent() -> None:
    agent = InboxTriageAgent(build_demo_provider())
    handoff = agent.triage(SAMPLE_MESSAGES).render_handoff()
    assert "## Urgent (1)" in handoff
    assert "## Spam (1)" in handoff
    assert "nothing was sent" in handoff


def test_unparsable_provider_output_defaults_to_routine() -> None:
    agent = InboxTriageAgent(FakeChatProvider(default="not json at all"))
    report = agent.triage(SAMPLE_MESSAGES[:1])
    assert report.items[0].category == "routine"
    assert "defaulted to routine" in report.items[0].reason


def test_unknown_category_from_provider_is_coerced_to_routine() -> None:
    provider = FakeChatProvider(
        rules=[("classify", '{"category": "banana", "reason": "model went rogue"}')],
        default="draft text",
    )
    agent = InboxTriageAgent(provider)
    report = agent.triage(SAMPLE_MESSAGES[:1])
    assert report.items[0].category == "routine"
