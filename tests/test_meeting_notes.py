from ai_automation_agents.demo_data import SAMPLE_TRANSCRIPT, build_demo_provider
from ai_automation_agents.fakes import FakeChatProvider
from ai_automation_agents.recipes.meeting_notes import MeetingNotesAgent


def test_decisions_and_action_items_are_extracted() -> None:
    agent = MeetingNotesAgent(build_demo_provider())
    notes = agent.process(SAMPLE_TRANSCRIPT)
    assert "Launch Project Falcon on March 3" in notes.decisions
    assert notes.action_items[0].task == "Draft the launch announcement"
    assert notes.action_items[0].owner == "Priya"
    assert notes.action_items[0].due == "Friday"
    assert notes.open_questions == ["Final pricing from finance"]


def test_follow_up_draft_is_produced() -> None:
    agent = MeetingNotesAgent(build_demo_provider())
    notes = agent.process(SAMPLE_TRANSCRIPT)
    assert "action items" in notes.follow_up_draft


def test_render_has_all_sections() -> None:
    agent = MeetingNotesAgent(build_demo_provider())
    rendered = agent.process(SAMPLE_TRANSCRIPT).render()
    assert "## Decisions" in rendered
    assert "## Action items" in rendered
    assert "- [ ] Draft the launch announcement — Priya (due Friday)" in rendered
    assert "## Follow-up draft" in rendered


def test_garbage_provider_output_degrades_with_a_warning() -> None:
    agent = MeetingNotesAgent(FakeChatProvider(default="total nonsense"))
    notes = agent.process("Any transcript.")
    assert notes.decisions == []
    assert notes.action_items == []
    assert notes.warnings
