# Changelog

Notable changes to AI Automation Agents are documented here.

## [0.1.0] - 2026-11-21

### Added

- Twelve numbered recipes in build order: lead-list cleaner, quote drafter, document Q&A, support FAQ, scheduled reporter, approval-gated actor, inbox triage, lead responder, meeting notes, social drafter, web research, and code review.
- Provider interfaces (chat, HTTP, embedder, executor) with shipped fakes, so every recipe is testable and demoable with zero network, zero API keys, and zero paid calls.
- An approval gate with a tamper-evident, hash-chained receipt log (Recipe 06) reusable by any recipe.
- A shared JSON memory store recipes can read/write under their own namespaces.
- A recipe registry and task router — deterministic keyword routing by default, provider-pluggable routing as an option.
- Two tested reference pipelines: web-research → scheduled-reporter and inbox-triage → lead-responder.
- The `ai-agents` CLI: list recipes, run any recipe on fakes with `--demo`, run pipelines, and a full demo summary. Plus `scripts/demo.py`.
- Docs: architecture, a build-your-own-recipe guide ("Recipe 13 is yours"), and one walkthrough per pipeline.
- Examples with sample inputs and expected outputs for the lead-list cleaner, quote drafter, document Q&A, and inbox triage recipes.
