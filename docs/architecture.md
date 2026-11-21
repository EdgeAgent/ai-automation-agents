# Architecture

How the pieces of AI Automation Agents fit together: recipes, providers,
the router, shared memory, pipelines, and the approval gate.

## The one-sentence version

A **recipe** is a small, typed unit of agent work. It never talks to a
vendor SDK or the network directly — it talks to a **provider interface**.
The **router** picks which recipe a task belongs to, **pipelines** chain
recipes together, **memory** lets recipes remember across runs, and the
**approval gate** stands between any proposal and any real-world effect.

## Component map

```text
                        ┌────────────────────┐
   task sentence ──────▶│      Router        │  keyword scoring (default)
                        │  (router.py)       │  or provider-pluggable
                        └─────────┬──────────┘
                                  │ recipe name
                                  ▼
┌──────────────┐   ┌─────────────────────────────┐   ┌──────────────────┐
│  Pipelines   │──▶│          Recipes 01–12      │──▶│     Providers    │
│ (pipelines)  │   │  typed in → typed out       │   │ chat / http /    │
└──────────────┘   │                             │   │ embedder /       │
                   │   draft-only by design      │   │ executor         │
                   └──────┬──────────────┬───────┘   └──────────────────┘
                          │              │              ▲            ▲
                          ▼              ▼              │ fakes      │ real adapters
                   ┌────────────┐  ┌───────────────┐    │ (tests,    │ (OpenAI, httpx)
                   │  Memory    │  │ Approval gate │    │  demos)    │
                   │ (memory)   │  │ (approval)    │    └────────────┘
                   └────────────┘  └───────────────┘
```

## Providers: the honest seam

`providers.py` defines four small protocols:

| Interface | Used by | Real adapter | Fake |
| --- | --- | --- | --- |
| `ChatProvider.complete(prompt) -> str` | triage, lead responder, meeting notes, social drafter, web research, code review, router (optional) | `OpenAIChatProvider` (needs the `[openai]` extra) | `FakeChatProvider` (scripted rules) |
| `HttpClient.get(url) -> str` | web research | `HttpxHttpClient` | `FakeHttpClient` (canned pages) |
| `Embedder.embed(text) -> list[float]` | doc-qa (optional) | bring your own | `FakeEmbedder` (deterministic hashing) |
| `Executor.execute(action, payload) -> dict` | approval-gated actor | yours to write | `FakeExecutor` (records calls) |

Because recipes depend only on these protocols, the entire repository —
all twelve recipes, both pipelines, the router, the CLI demos — is verified
by tests that inject fakes. Zero network, zero API keys, zero paid calls.
Swapping a fake for a real adapter changes the wiring, not the recipe.

Provider output is treated as untrusted: recipes that ask for JSON parse it
defensively (`extract_json` finds the first JSON span in prose or code
fences) and degrade to a warning, a default, or an escalation — never to
invented content.

## Recipes

One module per recipe under `src/ai_automation_agents/recipes/`, each with
pydantic models for input and output. Two families:

- **Deterministic (01–06)** — no provider. Pure functions and components:
  CSV cleaning, Decimal quote math, keyword retrieval, digest building,
  the approval gate. Same input, same output, every time.
- **Provider-backed (07–12)** — a chat provider (and, for web research, an
  HTTP client) does the language work; the recipe owns the contract:
  prompts, parsing, validation, and the draft-only boundary.

Every recipe answers the registry question "sends anything?" honestly, and
the answer is some form of "no" for all twelve: drafting recipes stop at
drafts, and the one executing component runs only human-approved actions
through an executor the operator supplies.

## Router and registry

`router.py` holds the registry — the single source of truth for the twelve
recipes (number, name, description, provider need, sends-anything answer,
routing keywords). The CLI table, the docs, and the router all read it.

Routing is a *decision*, returned as a `RouteDecision` with a confidence
and a reason; it never executes anything by itself. Default routing is
deterministic keyword scoring. With a provider injected, the model chooses
from the registry and the keyword scorer is the fallback when the model's
answer is not a recipe name.

## Memory

`memory.py` is a namespaced key/value store backed by one JSON file
(standard library only, atomic replace on write), or by RAM when no path is
given. Recipes own namespaces (`lead-responder`, `scheduled-reporter`), so
a pipeline can share one store without collisions. Memory is how the lead
responder knows Dana was contacted before, and how the reporter knows when
it last ran. It is a local file: no secrets belong in it.

## Pipelines

`pipelines.py` contains plain functions that wire recipe instances
together — no framework, no magic:

- `research_digest_pipeline(researcher, reporter, question, urls)` —
  web-research's report becomes a section in the reporter's digest.
- `triage_leads_pipeline(triage, responder, messages, criteria)` —
  triage classifies; messages carrying lead data flow to the responder,
  except spam, which is counted and dropped first.

Because pipelines take already-constructed recipe objects, tests build them
with fakes and assert on the chained behavior end to end.

## The approval gate

`approval.py` is the safety core, usable by any recipe (and by your own
Recipe 13):

1. `gate.propose(action, payload, reason)` — registers a pending proposal.
2. `gate.approve(id)` / `gate.deny(id)` — a human decision; deciding twice
   is an error.
3. `gate.execute(id, executor)` — only for approved proposals; pending or
   denied proposals raise. The gate fails closed.
4. Every step appends to a `ReceiptLog`: each entry's SHA-256 commits to
   the previous entry's hash, so `log.verify()` detects edited, reordered,
   or deleted history.

## Failure philosophy

Fail closed, degrade honestly, never invent. Missing token in Step 1's API
became 401s; here the same instinct shows up as: unparseable provider
output → warning + empty structure; no matching document → "I don't know"
+ escalation; failed fetch → a recorded failed source; denied proposal →
an exception, not a quiet no-op.
