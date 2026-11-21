# Security policy

This repository contains agent *patterns* and runnable examples. It does not operate a hosted service, and the default install makes no network calls.

## Reporting a vulnerability

Please do not publish exploit details in a public issue. Use GitHub's private vulnerability reporting feature for this repository if it is enabled. Otherwise, contact the repository maintainer privately and provide the affected recipe/module, Python and platform details, impact, and reproduction steps. Avoid including credentials, private data, or live exploit payloads.

## Working safely with these recipes

- Keep API keys and service credentials in a secret manager or protected environment variables; never commit them. `.env` is git-ignored on purpose.
- Treat model output, fetched web pages, transcripts, and diffs as untrusted input. Recipes parse provider output defensively, but a live model can still produce plausible nonsense — keep a human in the loop where output matters.
- Anything that acts on the world should go through the approval gate (`ai_automation_agents.approval`): propose, human decision, execute, receipt. Do not wire a drafting recipe directly to a send/post/execute path.
- The shared memory store is a local JSON file. Do not put secrets in it, and do not share a memory file across trust boundaries.
- Review dependency update proposals before merging or deploying, and create an application-specific lock file for deployed applications.
