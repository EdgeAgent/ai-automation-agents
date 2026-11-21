from ai_automation_agents.demo_data import SAMPLE_DIFF, build_demo_provider
from ai_automation_agents.fakes import FakeChatProvider
from ai_automation_agents.recipes.code_review import CodeReviewAgent


def test_findings_are_structured_and_counted() -> None:
    agent = CodeReviewAgent(build_demo_provider())
    report = agent.review(SAMPLE_DIFF)
    assert report.parsed_ok is True
    assert report.counts == {"critical": 1, "minor": 1}
    critical = report.findings[0]
    assert critical.file == "billing.py"
    assert critical.severity == "critical"
    assert critical.category == "security"


def test_render_groups_by_severity() -> None:
    agent = CodeReviewAgent(build_demo_provider())
    rendered = agent.review(SAMPLE_DIFF).render()
    assert "## Critical (1)" in rendered
    assert "`billing.py:2`" in rendered


def test_empty_diff_short_circuits_without_calling_provider() -> None:
    provider = FakeChatProvider(default="should not be used")
    agent = CodeReviewAgent(provider)
    report = agent.review("   ")
    assert report.findings == []
    assert provider.prompts == []


def test_garbage_provider_output_is_reported_not_faked() -> None:
    agent = CodeReviewAgent(FakeChatProvider(default="no json here"))
    report = agent.review(SAMPLE_DIFF)
    assert report.parsed_ok is False
    assert report.findings == []
    assert report.warnings
