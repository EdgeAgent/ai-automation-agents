from pathlib import Path

import pytest

from ai_automation_agents.memory import MemoryStore


def test_set_get_roundtrip() -> None:
    store = MemoryStore()
    store.set("leads", "count", 3)
    assert store.get("leads", "count") == 3


def test_get_returns_default_for_missing_keys() -> None:
    store = MemoryStore()
    assert store.get("nope", "missing") is None
    assert store.get("nope", "missing", 42) == 42


def test_namespaces_are_isolated() -> None:
    store = MemoryStore()
    store.set("a", "key", "A")
    store.set("b", "key", "B")
    assert store.get("a", "key") == "A"
    assert store.get("b", "key") == "B"
    assert store.namespaces() == ["a", "b"]


def test_append_builds_a_list() -> None:
    store = MemoryStore()
    assert store.append("runs", "history", {"run": 1}) == [{"run": 1}]
    assert store.append("runs", "history", {"run": 2}) == [{"run": 1}, {"run": 2}]


def test_append_to_non_list_raises() -> None:
    store = MemoryStore()
    store.set("runs", "count", 5)
    with pytest.raises(TypeError):
        store.append("runs", "count", 6)


def test_persistence_roundtrip(tmp_path: Path) -> None:
    path = tmp_path / "memory.json"
    first = MemoryStore(path)
    first.set("scheduled-reporter", "run_count", 7)
    first.append("scheduled-reporter", "history", {"run": 7})

    second = MemoryStore(path)
    assert second.get("scheduled-reporter", "run_count") == 7
    assert second.namespace("scheduled-reporter")["history"] == [{"run": 7}]
