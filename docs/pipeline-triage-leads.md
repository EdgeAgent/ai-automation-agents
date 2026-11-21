# Pipeline: inbox-triage → lead-responder

**Chain:** Recipe 07 (inbox-triage) feeds Recipe 08 (lead-responder).
**Run it:** `ai-agents pipeline triage-leads --demo`
**Code:** `triage_leads_pipeline` in `src/ai_automation_agents/pipelines.py`

## What it does

1. The triage agent classifies every incoming message (urgent / routine /
   spam) and drafts replies for the non-spam ones.
2. The pipeline looks at the messages that carry structured lead data
   (the optional `lead` field on `IncomingMessage`).
3. **Spam is counted and skipped** — a spam message's lead never reaches
   the responder, so junk can't consume scoring, drafting, or a human's
   review time.
4. Each surviving lead is scored against the criteria and gets a follow-up
   draft from the lead responder. The responder records the contact in
   shared memory, so tomorrow's run recognizes a returning lead.
5. The result reports triage counts, the number of skipped spam leads,
   and the lead responses — every one still in `draft` status.

## Why this shape

An inbox mixes customers, suppliers, leads, and junk. Triage is the cheap
filter; the responder is the expensive, careful step. Ordering them this
way means the careful step only ever sees real inquiries — and the
approval gate stays where it belongs: nothing in this pipeline sends
anything, no matter what either recipe produced.

## Wiring it live

```python
from ai_automation_agents.memory import MemoryStore
from ai_automation_agents.pipelines import triage_leads_pipeline
from ai_automation_agents.providers import OpenAIChatProvider
from ai_automation_agents.recipes.inbox_triage import InboxTriageAgent
from ai_automation_agents.recipes.lead_responder import LeadCriteria, LeadResponderAgent

provider = OpenAIChatProvider()
triage = InboxTriageAgent(provider)
responder = LeadResponderAgent(provider, MemoryStore(".ai-agents-memory.json"))
criteria = LeadCriteria(min_budget=1000, keywords=["automation"], locations=["Detroit"])

result = triage_leads_pipeline(triage, responder, messages_from_your_inbox, criteria)
for response in result.lead_responses:
    ...  # human reviews; approve with LeadResponderAgent.approve(response)
```

The `lead` field on a message is where your inbox integration does its
extraction (form fields, a CRM webhook, a parser). Keeping it optional
means the same triage recipe serves inboxes with no leads at all.
