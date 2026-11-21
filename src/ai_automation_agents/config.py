"""Environment-backed settings for live (non-demo) runs.

Demos and tests never read these — they inject fakes directly. Settings only
matter when a real provider is wired in, and they fail safe: no key is
required to import this module or run anything in the test suite.
"""

from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Settings read from ``AI_AGENTS_``-prefixed environment variables / .env."""

    model_config = SettingsConfigDict(env_prefix="AI_AGENTS_", env_file=".env", extra="ignore")

    openai_api_key: str | None = None
    model: str = "gpt-4o-mini"
    memory_path: Path = Path(".ai-agents-memory.json")
