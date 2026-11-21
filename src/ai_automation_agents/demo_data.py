"""Sample inputs and scripted fakes for the CLI demos.

Everything here is deterministic: the demo provider answers from rules, the
demo HTTP client serves two canned pages, and the clock is fixed. Running a
demo therefore produces the same output on every machine — which is the
point of fakes-first design.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime

from ai_automation_agents.fakes import FakeChatProvider, FakeHttpClient
from ai_automation_agents.recipes.inbox_triage import IncomingMessage

DEMO_NOW = datetime(2026, 11, 21, 14, 0, tzinfo=UTC)


def demo_clock() -> datetime:
    """A fixed clock so demo output never changes between runs."""
    return DEMO_NOW


SAMPLE_CSV = """name,email,phone,company,source
Dana White,dana@northwind.example,(313) 555-0142,Northwind Traders,web form
Marcus Lee,marcus@leeproperties.example,313-555-0199,Lee Properties,referral
Dana White,dana@northwind.example,(313) 555-0142,Northwind Traders,web form
Pat Nope,not-an-email,123,Unknown,import
Sam Ortiz,sam@ortiz.example,,Ortiz Group,web form
"""

SAMPLE_MESSAGES: list[IncomingMessage] = [
    IncomingMessage(
        id="m1",
        sender="ops@client.example",
        subject="URGENT: production server is down",
        body="The production server is down and customers cannot check out. Need help now.",
    ),
    IncomingMessage(
        id="m2",
        sender="billing@supplier.example",
        subject="Question about my invoice",
        body="Hi, invoice 1042 shows a different total than the quote. Can you check?",
    ),
    IncomingMessage(
        id="m3",
        sender="winner@promo.example",
        subject="You won a crypto giveaway",
        body="Claim your prize now — send 0.1 BTC to unlock your winnings.",
    ),
]

PIPELINE_MESSAGES: list[IncomingMessage] = [
    IncomingMessage(
        id="p1",
        sender="dana@northwind.example",
        subject="Interested in your automation package",
        body="We want help automating order intake. Budget is approved on our side.",
        lead={
            "id": "lead-dana",
            "name": "Dana",
            "email": "dana@northwind.example",
            "company": "Northwind Traders",
            "location": "Detroit",
            "budget": 2500,
            "interest": "automation package for order intake",
            "message": "We want help automating order intake.",
        },
    ),
    IncomingMessage(
        id="p2",
        sender="winner@promo.example",
        subject="You won a crypto giveaway",
        body="Claim your prize now.",
        lead={
            "id": "lead-spam",
            "name": "Prize Winner",
            "email": "winner@promo.example",
            "company": "",
            "location": "",
            "budget": 0,
            "interest": "crypto giveaway",
            "message": "Claim your prize now.",
        },
    ),
]

SAMPLE_TRANSCRIPT = (
    "Sam: We decided to launch Project Falcon on March 3. "
    "Priya: I'll draft the launch announcement by Friday. "
    "Sam: Budget is approved at $12,000. "
    "Lee: I still need the final pricing from finance. "
    "Priya: I'll book the demo room for March 1."
)

SAMPLE_DIFF = """diff --git a/billing.py b/billing.py
--- a/billing.py
+++ b/billing.py
@@ -1,2 +1,3 @@
+def charge(card, amount):
+    query = "SELECT * FROM cards WHERE id = " + card
+    return run(query, amount)
"""

RESEARCH_PAGES: dict[str, str] = {
    "https://example.com/approval-gates": (
        "<html><head><title>Approval gates</title></head><body>"
        "<h1>Approval gates</h1>"
        "<p>Approval gates keep a human in charge of agent actions. An agent "
        "proposes an action, a human approves or denies it, and only approved "
        "actions run.</p>"
        "<script>trackPageview()</script>"
        "</body></html>"
    ),
    "https://example.com/receipts": (
        "<html><body><h1>Receipt logs</h1>"
        "<p>Receipt logs record what an agent did, step by step. Hash-chained "
        "receipts make tampering evident, because editing one entry breaks "
        "the chain.</p></body></html>"
    ),
}

_MEETING_JSON = json.dumps(
    {
        "title": "Project Falcon launch sync",
        "summary": "The team confirmed the Project Falcon launch date and budget.",
        "decisions": ["Launch Project Falcon on March 3", "Budget approved at $12,000"],
        "action_items": [
            {"task": "Draft the launch announcement", "owner": "Priya", "due": "Friday"},
            {"task": "Book the demo room", "owner": "Priya", "due": "March 1"},
        ],
        "open_questions": ["Final pricing from finance"],
    }
)

_REVIEW_JSON = json.dumps(
    [
        {
            "file": "billing.py",
            "line": 2,
            "severity": "critical",
            "category": "security",
            "message": "SQL built by string concatenation — use parameterized queries.",
        },
        {
            "file": "billing.py",
            "line": 1,
            "severity": "minor",
            "category": "maintainability",
            "message": "charge() has no docstring or type hints.",
        },
    ]
)

_SOCIAL = (
    "Local-first AI agents: your data stays on your machine, your agents do the busywork. "
    "Twelve recipes, all tested with fakes.\n"
    "TAGS: #AIagents #LocalFirst\n"
    "---\n"
    "Approval gates are the difference between an agent you trust and an agent you fear. "
    "Propose, approve, execute — with receipts.\n"
    "TAGS: #AIautomation #HumanInTheLoop\n"
    "---\n"
    "Step 1 was the toolbox. Step 2 is the agents: routing, memory, and pipelines on top.\n"
    "TAGS: #Python #GenerativeAI"
)


def build_demo_provider() -> FakeChatProvider:
    """A scripted provider covering every demo prompt in this package."""
    return FakeChatProvider(
        rules=[
            (
                "draft a short, professional reply",
                "Thanks for reaching out — we are on it and will update you shortly.",
            ),
            (
                "write a short follow-up message for this meeting",
                (
                    "Thanks everyone — notes and action items from today's sync are attached. "
                    "Shout if anything is missing."
                ),
            ),
            ("project falcon", _MEETING_JSON),
            ("draft social posts", _SOCIAL),
            (
                "answer the research question",
                (
                    "Approval gates keep a human in charge: agents propose actions, humans "
                    "approve or deny them, and only approved actions execute. Hash-chained "
                    "receipt logs record every step, so tampering is evident."
                ),
            ),
            ("review this diff like a careful senior engineer", _REVIEW_JSON),
            (
                "name: dana",
                (
                    "Hi Dana — thanks for reaching out about automating order "
                    "intake at Northwind Traders. Happy to walk through how the package "
                    "would fit your workflow this week."
                ),
            ),
            (
                "name: marcus",
                (
                    "Hi Marcus — thanks for your interest in a website "
                    "refresh. Could we set up a short call to scope it properly?"
                ),
            ),
            (
                "server is down",
                json.dumps(
                    {"category": "urgent", "reason": "Production outage affecting customers."}
                ),
            ),
            (
                "crypto giveaway",
                json.dumps({"category": "spam", "reason": "Unsolicited giveaway lure."}),
            ),
            (
                "automation package",
                json.dumps({"category": "routine", "reason": "New business inquiry."}),
            ),
            (
                "invoice",
                json.dumps(
                    {"category": "routine", "reason": "Billing question, no deadline pressure."}
                ),
            ),
        ],
        default="",
    )


def build_demo_http() -> FakeHttpClient:
    """A fake HTTP client serving the two canned research pages."""
    return FakeHttpClient(pages=dict(RESEARCH_PAGES))
