"""The recipe registry and the task router.

The registry is the single source of truth for the twelve recipes — the
CLI, the docs, and the router all read from it. The router turns a
natural-language task into a recipe choice two ways: deterministic keyword
scoring (default, fully testable), or an injected chat provider asked to
pick from the registry (pluggable, fake in tests). Routing is a decision,
not an execution — running the recipe stays an explicit step.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from pydantic import BaseModel

from ai_automation_agents.providers import ChatProvider


@dataclass(frozen=True)
class RecipeInfo:
    """Registry metadata for one recipe."""

    number: int
    name: str
    title: str
    description: str
    provider: str  # "none", "chat", or "chat + http"
    sends: str  # honest answer to "does it send anything?"
    keywords: list[str] = field(default_factory=list)


RECIPES: list[RecipeInfo] = [
    RecipeInfo(
        1,
        "lead-list-cleaner",
        "Lead-list cleaner",
        "Dedupe a lead CSV, flag bad contacts, grade every row A/B/C.",
        "none",
        "No — local only",
        ["lead list", "csv", "dedupe", "clean leads", "grade leads", "spreadsheet of leads"],
    ),
    RecipeInfo(
        2,
        "quote-drafter",
        "Quote drafter",
        "Itemized quote with tax, totals, and a deposit split. Deterministic math.",
        "none",
        "No — local only",
        ["quote", "estimate", "price a job", "invoice draft", "deposit"],
    ),
    RecipeInfo(
        3,
        "doc-qa",
        "Document Q&A",
        "Answer questions over local documents, with cited sources.",
        "none",
        "No — local only",
        ["answer questions", "documents", "documentation", "look up", "knowledge base", "cite"],
    ),
    RecipeInfo(
        4,
        "support-faq",
        "Support FAQ agent",
        "FAQ answers with citations and an escalate-to-human path.",
        "none",
        "No — draft-only",
        ["faq", "support questions", "help desk", "customer questions", "escalate"],
    ),
    RecipeInfo(
        5,
        "scheduled-reporter",
        "Scheduled reporter",
        "Build a digest from structured inputs on a schedule, with run memory.",
        "none",
        "No — local only",
        ["digest", "report", "scheduled", "summary email draft", "weekly update", "briefing"],
    ),
    RecipeInfo(
        6,
        "approval-gated-actor",
        "Approval-gated actor",
        "Propose actions, get human approval, execute with tamper-evident receipts.",
        "none",
        "Gated — approved actions only, via your executor",
        ["approve", "approval", "execute actions", "batch job", "receipts", "human in the loop"],
    ),
    RecipeInfo(
        7,
        "inbox-triage",
        "Inbox triage",
        "Classify incoming messages and draft replies. Never sends.",
        "chat",
        "No — draft-only",
        ["inbox", "triage", "email", "messages", "classify mail", "draft replies"],
    ),
    RecipeInfo(
        8,
        "lead-responder",
        "Lead responder",
        "Score leads against criteria and draft approval-gated follow-ups.",
        "chat",
        "No — draft-only",
        ["lead", "follow up", "follow-up", "score leads", "prospect", "sales reply"],
    ),
    RecipeInfo(
        9,
        "meeting-notes",
        "Meeting-notes agent",
        "Decisions, action items with owners, and a follow-up draft from a transcript.",
        "chat",
        "No — draft-only",
        ["meeting", "transcript", "notes", "action items", "minutes", "decisions"],
    ),
    RecipeInfo(
        10,
        "social-drafter",
        "Social-content drafter",
        "Draft post variants and hashtags per platform. Never posts.",
        "chat",
        "No — draft-only",
        ["social", "post", "tweet", "linkedin", "content", "hashtags", "draft a post"],
    ),
    RecipeInfo(
        11,
        "web-research",
        "Web-research agent",
        "Fetch pages, extract text, summarize with a source list.",
        "chat + http",
        "No — reads only",
        ["research", "web", "fetch", "summarize pages", "sources", "look into"],
    ),
    RecipeInfo(
        12,
        "code-review",
        "Code-review assistant",
        "Structured findings from a diff: file, line, severity, message.",
        "chat",
        "No — comments only",
        ["code review", "review", "diff", "patch", "pull request", "findings"],
    ),
]

RECIPES_BY_NAME: dict[str, RecipeInfo] = {recipe.name: recipe for recipe in RECIPES}


class RouteDecision(BaseModel):
    """Where a task was routed, and why."""

    recipe: str
    confidence: float
    reason: str
    method: str  # "keywords" or "provider"


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def keyword_route(task: str) -> RouteDecision:
    """Route ``task`` by keyword overlap with the registry. Deterministic."""
    task_lower = task.lower()
    task_tokens = _tokens(task)
    best: RecipeInfo | None = None
    best_score = 0.0
    for recipe in RECIPES:
        score = 0.0
        for keyword in recipe.keywords:
            if " " in keyword:
                if keyword in task_lower:
                    score += 3.0
            elif keyword in task_tokens:
                score += 2.0
        name_tokens = set(recipe.name.split("-"))
        score += 1.0 * len(name_tokens & task_tokens)
        if score > best_score:
            best, best_score = recipe, score
    if best is None or best_score == 0:
        return RouteDecision(
            recipe="",
            confidence=0.0,
            reason="No recipe matched the task keywords.",
            method="keywords",
        )
    confidence = round(min(best_score / 6.0, 1.0), 2)
    return RouteDecision(
        recipe=best.name,
        confidence=confidence,
        reason=f"Keyword score {best_score:g} for '{best.name}'.",
        method="keywords",
    )


_PROVIDER_PROMPT = """Pick the single best recipe for this task. Recipes:
{recipes}

Task: {task}

Respond with the recipe name only."""


class Router:
    """Routes natural-language tasks to recipes.

    With no provider, routing is the deterministic keyword scorer. With a
    provider, the model picks from the registry and the keyword scorer is
    the fallback when the model answers with something unusable.
    """

    def __init__(self, provider: ChatProvider | None = None) -> None:
        self._provider = provider

    def route(self, task: str) -> RouteDecision:
        """Return the routing decision for ``task``."""
        if self._provider is not None:
            listing = "\n".join(f"- {r.name}: {r.description}" for r in RECIPES)
            raw = self._provider.complete(_PROVIDER_PROMPT.format(recipes=listing, task=task))
            choice = raw.strip().strip("`").lower()
            if choice in RECIPES_BY_NAME:
                return RouteDecision(
                    recipe=choice,
                    confidence=0.9,
                    reason="Provider selected from the registry.",
                    method="provider",
                )
            fallback = keyword_route(task)
            fallback.reason = "Provider answer was not a recipe name; keyword fallback used."
            return fallback
        return keyword_route(task)
