# Example — Recipe 03, document Q&A

**Input:** `documents.md` — three small documents (services, pricing,
delivery), and `questions.txt` — one answerable question and one the set
deliberately does not cover.

**Run:**

```bash
ai-agents run doc-qa --demo
```

**Expected output:** `expected-answers.md` — a cited answer for the first
question, an honest escalation for the second.
