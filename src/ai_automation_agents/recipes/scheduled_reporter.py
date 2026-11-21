"""Recipe 05 — Scheduled reporter.

Builds a digest from structured inputs. The core is a pure function —
sections in, Markdown out — and a thin reporter/scheduler layer adds the
schedule pattern: the reporter remembers its last run in shared memory, and
the scheduler runs it only when it is due. Clock and memory are injected,
so the whole pattern is testable without sleeping or waiting.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime, timedelta

from pydantic import BaseModel, Field

from ai_automation_agents.memory import MemoryStore

NAMESPACE = "scheduled-reporter"


class ReportSection(BaseModel):
    """One digest section: a heading and its bullet lines."""

    heading: str
    lines: list[str] = Field(default_factory=list)


class ReportInput(BaseModel):
    """Structured input for one digest."""

    title: str
    sections: list[ReportSection] = Field(default_factory=list)
    footer: str = ""


def build_digest(report: ReportInput, generated_at: datetime) -> str:
    """Render ``report`` as a Markdown digest. Pure function, no I/O."""
    lines = [f"# {report.title}", "", f"_Generated {generated_at.isoformat()}_", ""]
    for section in report.sections:
        lines.append(f"## {section.heading}")
        lines.append("")
        if section.lines:
            lines.extend(f"- {line}" for line in section.lines)
        else:
            lines.append("_Nothing to report._")
        lines.append("")
    if report.footer:
        lines.append("---")
        lines.append(report.footer)
    return "\n".join(lines).rstrip() + "\n"


def _utc_now() -> datetime:
    return datetime.now(UTC)


class Reporter:
    """Builds digests and remembers each run in shared memory."""

    def __init__(
        self,
        memory: MemoryStore,
        clock: Callable[[], datetime] = _utc_now,
    ) -> None:
        self._memory = memory
        self._clock = clock

    def run_once(self, report: ReportInput) -> str:
        """Build the digest and record the run in memory."""
        now = self._clock()
        digest = build_digest(report, now)
        run_count = int(self._memory.get(NAMESPACE, "run_count", 0)) + 1
        self._memory.set(NAMESPACE, "run_count", run_count)
        self._memory.set(NAMESPACE, "last_run_at", now.isoformat())
        self._memory.set(NAMESPACE, "last_title", report.title)
        self._memory.append(
            NAMESPACE,
            "history",
            {"run": run_count, "at": now.isoformat(), "title": report.title},
        )
        return digest

    def last_run_at(self) -> datetime | None:
        """Return the time of the most recent run, if any."""
        raw = self._memory.get(NAMESPACE, "last_run_at")
        return datetime.fromisoformat(raw) if raw else None


class DigestScheduler:
    """Runs a reporter when the configured interval has elapsed."""

    def __init__(
        self,
        reporter: Reporter,
        interval: timedelta,
        clock: Callable[[], datetime] = _utc_now,
    ) -> None:
        self._reporter = reporter
        self._interval = interval
        self._clock = clock

    def is_due(self) -> bool:
        """True when no run exists yet, or the interval has elapsed."""
        last = self._reporter.last_run_at()
        if last is None:
            return True
        return self._clock() - last >= self._interval

    def tick(self, report: ReportInput) -> str | None:
        """Run the reporter if due; otherwise return ``None``."""
        if not self.is_due():
            return None
        return self._reporter.run_once(report)
