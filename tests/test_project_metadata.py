from __future__ import annotations

import tomllib
from pathlib import Path

import ai_automation_agents

ROOT = Path(__file__).resolve().parents[1]


def read_project() -> dict:
    with (ROOT / "pyproject.toml").open("rb") as project_file:
        return tomllib.load(project_file)["project"]


def test_package_version_matches_project_metadata() -> None:
    project = read_project()
    assert project["version"] == "0.1.0"
    assert ai_automation_agents.__version__ == project["version"]


def test_project_requires_supported_python() -> None:
    assert read_project()["requires-python"] == ">=3.11"


def test_default_install_is_the_lean_foundation() -> None:
    project = read_project()
    assert set(project["dependencies"]) == {
        "pydantic",
        "pydantic-settings",
        "python-dotenv",
        "httpx",
        "tenacity",
        "structlog",
        "typer",
        "rich",
    }
    assert project["scripts"]["ai-agents"] == "ai_automation_agents.cli:app"


def test_openai_is_a_focused_optional_extra() -> None:
    extras = read_project()["optional-dependencies"]
    assert extras["openai"] == ["openai"]
    assert {"pytest", "ruff", "mypy"} <= set(extras["dev"])


def test_every_project_requirement_is_unpinned() -> None:
    project = read_project()
    packages_by_profile = {"default": project["dependencies"], **project["optional-dependencies"]}
    for profile, packages in packages_by_profile.items():
        for package in packages:
            assert not any(operator in package for operator in ("==", "~=", ">", "<")), (
                f"{profile} unexpectedly pins or constrains {package}"
            )
