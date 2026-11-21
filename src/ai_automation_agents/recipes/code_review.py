"""Recipe 12 — Code-review assistant.

Diff/patch text in → a structured findings list out. The provider reads the
diff and answers with a strict JSON contract; findings are validated into
typed models with severity counts, ready for a human reviewer to act on.
The assistant comments on code — it never edits, commits, or merges.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from ai_automation_agents.providers import ChatProvider, extract_json

Severity = Literal["critical", "major", "minor", "nit"]


class ReviewFinding(BaseModel):
    """One structured review finding."""

    file: str
    line: int = 0
    severity: Severity = "minor"
    category: str = "general"
    message: str


class ReviewReport(BaseModel):
    """Findings plus severity counts and a parse health flag."""

    findings: list[ReviewFinding] = Field(default_factory=list)
    counts: dict[str, int] = Field(default_factory=dict)
    parsed_ok: bool = True
    warnings: list[str] = Field(default_factory=list)

    def render(self) -> str:
        """Render the findings as a Markdown list grouped by severity."""
        lines = ["# Code review findings", ""]
        for severity in ("critical", "major", "minor", "nit"):
            group = [f for f in self.findings if f.severity == severity]
            if not group:
                continue
            lines.append(f"## {severity.capitalize()} ({len(group)})")
            lines.append("")
            for finding in group:
                location = f"{finding.file}:{finding.line}" if finding.line else finding.file
                lines.append(f"- `{location}` [{finding.category}] {finding.message}")
            lines.append("")
        if not self.findings:
            lines.append("No findings.")
        return "\n".join(lines)


_PROMPT = """Review this diff like a careful senior engineer. Look for bugs, security
issues, and clear maintainability problems — not style preferences.
Diff:
{diff}

Respond with JSON only: a list of findings, each
{{"file": "...", "line": 0, "severity": "critical" | "major" | "minor" | "nit",
  "category": "...", "message": "..."}}.
Return an empty list when the diff is clean."""


class CodeReviewAgent:
    """Structured review findings from a diff, via the injected provider."""

    def __init__(self, provider: ChatProvider) -> None:
        self._provider = provider

    def review(self, diff: str) -> ReviewReport:
        """Review ``diff`` and return validated, counted findings."""
        if not diff.strip():
            return ReviewReport(findings=[], counts={}, parsed_ok=True)
        raw = self._provider.complete(_PROMPT.format(diff=diff))
        try:
            parsed = extract_json(raw)
            findings = [ReviewFinding(**item) for item in parsed]
        except (ValueError, TypeError) as exc:
            return ReviewReport(
                findings=[],
                counts={},
                parsed_ok=False,
                warnings=[f"Provider output could not be parsed ({exc}); no findings returned."],
            )
        counts: dict[str, int] = {}
        for finding in findings:
            counts[finding.severity] = counts.get(finding.severity, 0) + 1
        return ReviewReport(findings=findings, counts=counts, parsed_ok=True)
