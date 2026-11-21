from datetime import UTC, datetime, timedelta

from ai_automation_agents.memory import MemoryStore
from ai_automation_agents.recipes.scheduled_reporter import (
    DigestScheduler,
    Reporter,
    ReportInput,
    ReportSection,
    build_digest,
)

T0 = datetime(2026, 11, 21, 14, 0, tzinfo=UTC)
REPORT = ReportInput(
    title="Friday digest",
    sections=[
        ReportSection(heading="Wins", lines=["Shipped the repo"]),
        ReportSection(heading="Quiet corner", lines=[]),
    ],
    footer="Draft — review before sharing.",
)


def test_build_digest_renders_sections_and_footer() -> None:
    digest = build_digest(REPORT, T0)
    assert digest.startswith("# Friday digest")
    assert "## Wins" in digest
    assert "- Shipped the repo" in digest
    assert "_Nothing to report._" in digest
    assert "Draft — review before sharing." in digest
    assert "2026-11-21T14:00:00+00:00" in digest


def test_reporter_records_runs_in_memory() -> None:
    memory = MemoryStore()
    reporter = Reporter(memory, clock=lambda: T0)
    reporter.run_once(REPORT)
    reporter.run_once(REPORT)
    assert memory.get("scheduled-reporter", "run_count") == 2
    assert memory.get("scheduled-reporter", "last_title") == "Friday digest"
    assert len(memory.get("scheduled-reporter", "history")) == 2
    assert reporter.last_run_at() == T0


def test_scheduler_runs_when_never_run_before() -> None:
    reporter = Reporter(MemoryStore(), clock=lambda: T0)
    scheduler = DigestScheduler(reporter, timedelta(hours=1), clock=lambda: T0)
    assert scheduler.is_due() is True
    assert scheduler.tick(REPORT) is not None


def test_scheduler_waits_for_the_interval() -> None:
    now = [T0]
    reporter = Reporter(MemoryStore(), clock=lambda: now[0])
    scheduler = DigestScheduler(reporter, timedelta(hours=1), clock=lambda: now[0])
    assert scheduler.tick(REPORT) is not None
    assert scheduler.tick(REPORT) is None
    now[0] = T0 + timedelta(hours=2)
    assert scheduler.tick(REPORT) is not None
