from typer.testing import CliRunner

from ai_automation_agents.cli import app

runner = CliRunner()
WIDE = {"COLUMNS": "240"}


def test_recipes_command_lists_all_twelve() -> None:
    result = runner.invoke(app, ["recipes"], env=WIDE)
    assert result.exit_code == 0
    for name in ("lead-list-cleaner", "quote-drafter", "doc-qa", "code-review"):
        assert name in result.output


def test_version_command() -> None:
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert "0.1.0" in result.output


def test_run_lead_cleaner_demo() -> None:
    result = runner.invoke(app, ["run", "lead-list-cleaner", "--demo"], env=WIDE)
    assert result.exit_code == 0
    assert "Grades: A=2 B=1 C=1" in result.output


def test_run_approval_actor_demo_shows_valid_receipts() -> None:
    result = runner.invoke(app, ["run", "approval-gated-actor", "--demo"], env=WIDE)
    assert result.exit_code == 0
    assert "Receipts valid: True" in result.output
    assert "Denied: 1" in result.output


def test_run_inbox_triage_demo_shows_handoff() -> None:
    result = runner.invoke(app, ["run", "inbox-triage", "--demo"], env=WIDE)
    assert result.exit_code == 0
    assert "handoff list" in result.output
    assert "production server is down" in result.output


def test_run_quote_drafter_demo() -> None:
    result = runner.invoke(app, ["run", "quote-drafter", "--demo"], env=WIDE)
    assert result.exit_code == 0
    assert "Total: $1248.65" in result.output


def test_run_doc_qa_demo_shows_citations() -> None:
    # Regression: Rich markup must not swallow the [source] citations.
    result = runner.invoke(app, ["run", "doc-qa", "--demo"], env=WIDE)
    assert result.exit_code == 0
    assert "[pricing]" in result.output


def test_run_unknown_recipe_is_rejected() -> None:
    result = runner.invoke(app, ["run", "not-a-recipe", "--demo"])
    assert result.exit_code != 0
    assert "Unknown recipe" in result.output


def test_run_without_demo_flag_fails_closed() -> None:
    result = runner.invoke(app, ["run", "lead-list-cleaner"])
    assert result.exit_code == 1
    assert "--demo" in result.output


def test_pipeline_research_digest_demo() -> None:
    result = runner.invoke(app, ["pipeline", "research-digest", "--demo"], env=WIDE)
    assert result.exit_code == 0
    assert "# Research digest" in result.output


def test_pipeline_triage_leads_demo() -> None:
    result = runner.invoke(app, ["pipeline", "triage-leads", "--demo"], env=WIDE)
    assert result.exit_code == 0
    assert "Spam leads skipped" in result.output
    assert "score 70" in result.output


def test_full_demo_command() -> None:
    result = runner.invoke(app, ["demo"], env=WIDE)
    assert result.exit_code == 0
    assert "Summary:" in result.output
    assert "Pipeline: triage-leads" in result.output
