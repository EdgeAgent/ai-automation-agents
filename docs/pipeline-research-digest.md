# Pipeline: web-research → scheduled-reporter

**Chain:** Recipe 11 (web-research) feeds Recipe 05 (scheduled-reporter).
**Run it:** `ai-agents pipeline research-digest --demo`
**Code:** `research_digest_pipeline` in `src/ai_automation_agents/pipelines.py`

## What it does

1. The web-research agent fetches the given URLs through its HTTP client,
   extracts readable text, and summarizes what the pages say about the
   question — with a full source list.
2. The pipeline folds the summary into a `ReportInput` as a digest
   section, adds a Sources section (each URL marked fetched or failed),
   and hands it to the reporter.
3. The reporter renders the Markdown digest and records the run in shared
   memory (`scheduled-reporter` namespace: run count, last run time,
   history) — so this pipeline participates in the same schedule pattern
   as any other digest.

## Why this shape

Research that nobody reads is waste; a digest nobody can source is worse.
Chaining the two recipes means every scheduled research digest carries its
evidence with it, and a failed fetch shows up in the digest as a failed
source instead of disappearing.

## Wiring it live

```python
from ai_automation_agents.memory import MemoryStore
from ai_automation_agents.pipelines import research_digest_pipeline
from ai_automation_agents.providers import HttpxHttpClient, OpenAIChatProvider
from ai_automation_agents.recipes.scheduled_reporter import Reporter
from ai_automation_agents.recipes.web_research import WebResearchAgent

researcher = WebResearchAgent(HttpxHttpClient(), OpenAIChatProvider())
reporter = Reporter(MemoryStore(".ai-agents-memory.json"))
report, digest = research_digest_pipeline(
    researcher,
    reporter,
    "How do approval gates keep agent actions safe?",
    ["https://example.com/approval-gates", "https://example.com/receipts"],
)
```

Swap the reporter for a `DigestScheduler` and the same pipeline runs on an
interval. The digest is a draft — where it goes next (email, chat, a
ticket) is a human's decision, or an approval-gated action.
