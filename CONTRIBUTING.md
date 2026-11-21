# Contributing

Thanks for helping make AI Automation Agents more useful to Python developers.

## Before opening an issue

- Check existing issues and discussions for a similar request.
- Include your Python version, operating system, the recipe or command involved, and the full error output when reporting a problem.
- For recipe requests, explain the job the agent does, what it must never do, and which provider boundary it needs.

## Development setup

Use Python 3.11 or newer, then run from the repository root:

```bash
python -m venv .venv
# Activate .venv for your shell, then:
python -m pip install -e ".[openai,dev]"
ruff check .
ruff format --check .
pytest
```

## Pull request guidelines

- Keep the default install lean; provider SDKs belong in their optional extra.
- Every recipe follows the house rules in `docs/build-your-own-recipe.md`: typed input/output models, providers behind the interfaces in `providers.py`, an honest "sends anything?" answer, and tests that run entirely on fakes.
- Drafting recipes stay draft-only. Anything that executes goes through the approval gate.
- Do not add exact version pins to `pyproject.toml`; this project resolves current compatible versions at installation time.
- When adding a recipe, register it in `router.py`, add a demo runner, update the README table, and note it in the changelog.
- Run the CI commands locally and describe any trade-offs in the PR.

By submitting a contribution, you agree that it may be distributed under this project's MIT license.
