# Example — Recipe 07, inbox triage

**Input:** `messages.json` — three messages: a production outage, a
billing question, and a giveaway scam.

**Run:**

```bash
ai-agents run inbox-triage --demo
```

**Expected output:** `expected-handoff.md` — the handoff list a human
works from: urgent first with a draft reply ready, the routine billing
question with its draft, and the spam with no draft at all. Nothing was
sent; there is no send path in the recipe.
