# Build your own recipe — Recipe 13 is yours

The twelve recipes in this repo follow one pattern. Follow the same steps
and your recipe gets the same guarantees: typed in/out, testable with
fakes, routable, and honest about what it does.

## The house rules

1. **Typed input, typed output.** Pydantic models for both. No loose dicts
   crossing the recipe boundary.
2. **Providers behind interfaces.** If the recipe needs a model, an HTTP
   fetch, embeddings, or a side effect, it takes the matching protocol
   from `providers.py` in its constructor. It never imports a vendor SDK.
3. **Draft-only by default.** If your recipe's natural output could send,
   post, buy, or delete — it doesn't. It drafts, and anything that acts
   goes through the approval gate (Recipe 06).
4. **Degrade, don't invent.** Unparseable provider output becomes a
   warning or an escalation, never fabricated content.
5. **Tests on fakes.** If a test needs the network, an API key, or money,
   the recipe is wired wrong.

## Step by step

### 1. Write the module

Create `src/ai_automation_agents/recipes/invoice_chaser.py`:

```python
"""Recipe 13 — Invoice chaser.

Overdue invoice in → a polite, firm payment-reminder draft out.
Draft-only: a human reviews and sends.
"""

from __future__ import annotations

from pydantic import BaseModel

from ai_automation_agents.providers import ChatProvider


class Invoice(BaseModel):
    """One overdue invoice."""

    number: str
    client: str
    amount_due: float
    days_overdue: int


class ReminderDraft(BaseModel):
    """The draft reminder and its approval state."""

    invoice_number: str
    tone: str  # "gentle" | "firm" | "final"
    draft: str
    status: str = "draft"


_PROMPT = """Write a {tone} payment-reminder email draft for a human to review.
Client: {client}. Invoice {number} for ${amount} is {days} days overdue.
Do not threaten consequences that need approval. Draft only."""


class InvoiceChaserAgent:
    """Drafts payment reminders. Never sends."""

    def __init__(self, provider: ChatProvider) -> None:
        self._provider = provider

    def draft_reminder(self, invoice: Invoice) -> ReminderDraft:
        tone = (
            "gentle"
            if invoice.days_overdue < 14
            else ("firm" if invoice.days_overdue < 30 else "final")
        )
        draft = self._provider.complete(
            _PROMPT.format(
                tone=tone,
                client=invoice.client,
                number=invoice.number,
                amount=invoice.amount_due,
                days=invoice.days_overdue,
            )
        ).strip()
        return ReminderDraft(invoice_number=invoice.number, tone=tone, draft=draft, status="draft")
```

Note what the template does: the deterministic part (tone selection) is
plain code; the provider does only the language work; the output model
carries `status: draft` so nobody mistakes it for a sent email.

### 2. Test it with a fake

Create `tests/test_invoice_chaser.py`:

```python
from ai_automation_agents.fakes import FakeChatProvider
from ai_automation_agents.recipes.invoice_chaser import Invoice, InvoiceChaserAgent


def test_gentle_tone_for_recent_invoice() -> None:
    provider = FakeChatProvider(default="Dear client, a friendly reminder...")
    agent = InvoiceChaserAgent(provider)
    result = agent.draft_reminder(
        Invoice(number="1042", client="Northwind", amount_due=450.0, days_overdue=3)
    )
    assert result.tone == "gentle"
    assert result.status == "draft"
    assert "1042" in provider.prompts[0]
```

### 3. Register it

Add a `RecipeInfo` to `RECIPES` in `router.py` — number 13, name
`invoice-chaser`, an honest provider/sends entry, and routing keywords
(`["invoice", "overdue", "payment reminder", "chase payment"]`). The CLI
table and the keyword router pick it up automatically.

### 4. Add a demo runner

Add a `demo_invoice_chaser()` function in `demo.py`, register it in
`RUNNERS`, and `ai-agents run invoice-chaser --demo` works. Demos use
`demo_data.build_demo_provider()` — add a rule there if your recipe needs
a scripted answer.

### 5. Document it

Add a row to the README recipe table and a short per-recipe section, a
`CHANGELOG.md` entry, and — if your recipe chains with others — consider a
pipeline and a walkthrough page like the two in this folder.

## Checklist

- [ ] Module in `recipes/` with typed input/output models
- [ ] Providers injected via `providers.py` protocols only
- [ ] Draft-only, or side effects behind the approval gate
- [ ] Tests run entirely on fakes and pass
- [ ] Registry entry in `router.py` (number, keywords, honest "sends?")
- [ ] Demo runner in `demo.py`
- [ ] README table row + section, CHANGELOG entry
- [ ] `ruff check .`, `ruff format --check .`, `pytest` all green
