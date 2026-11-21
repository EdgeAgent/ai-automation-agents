from ai_automation_agents.demo_data import RESEARCH_PAGES, build_demo_http, build_demo_provider
from ai_automation_agents.fakes import FakeHttpClient
from ai_automation_agents.recipes.web_research import WebResearchAgent, extract_text

QUESTION = "How do approval gates keep agent actions safe?"


def test_research_summarizes_with_sources() -> None:
    agent = WebResearchAgent(build_demo_http(), build_demo_provider())
    report = agent.research(QUESTION, list(RESEARCH_PAGES))
    assert len(report.sources) == 2
    assert all(source.fetched for source in report.sources)
    assert "Approval gates keep a human in charge" in report.summary


def test_script_content_is_not_extracted() -> None:
    text = extract_text(RESEARCH_PAGES["https://example.com/approval-gates"])
    assert "trackPageview" not in text
    assert "Approval gates keep a human in charge" in text


def test_head_title_is_not_counted_as_page_text() -> None:
    html = (
        "<html><head><title>Metadata Only Title</title></head>"
        "<body><p>Visible body text.</p></body></html>"
    )
    text = extract_text(html)
    assert "Metadata Only Title" not in text
    assert "Visible body text." in text


def test_failed_fetch_is_recorded_not_invented_around() -> None:
    agent = WebResearchAgent(build_demo_http(), build_demo_provider())
    report = agent.research(QUESTION, ["https://example.com/missing"])
    assert report.sources[0].fetched is False
    assert "No sources could be fetched" in report.summary


def test_mixed_success_and_failure_still_summarizes() -> None:
    agent = WebResearchAgent(build_demo_http(), build_demo_provider())
    urls = ["https://example.com/approval-gates", "https://example.com/missing"]
    report = agent.research(QUESTION, urls)
    assert [source.fetched for source in report.sources] == [True, False]
    assert "human in charge" in report.summary
    rendered = report.render()
    assert "FETCH FAILED" in rendered


def test_empty_client_means_no_summary() -> None:
    agent = WebResearchAgent(FakeHttpClient(), build_demo_provider())
    report = agent.research(QUESTION, [])
    assert report.sources == []
    assert "No sources" in report.summary
