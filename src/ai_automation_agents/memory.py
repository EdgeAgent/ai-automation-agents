"""A small shared memory store recipes can read and write.

One JSON file, standard library only. Recipes namespace their keys
(``lead-responder``, ``scheduled-reporter``, ...) so a single store can be
shared by a whole pipeline without collisions. With no path, the store is
in-memory only — which is what tests and demos use unless they specifically
exercise persistence.
"""

from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any


class MemoryStore:
    """Namespaced key/value memory with optional JSON-file persistence."""

    def __init__(self, path: Path | str | None = None) -> None:
        self._path = Path(path) if path is not None else None
        self._lock = threading.Lock()
        self._data: dict[str, dict[str, Any]] = {}
        if self._path is not None and self._path.exists():
            loaded = json.loads(self._path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                self._data = loaded

    def get(self, namespace: str, key: str, default: Any = None) -> Any:
        """Return ``namespace/key`` or ``default`` when absent."""
        with self._lock:
            return self._data.get(namespace, {}).get(key, default)

    def set(self, namespace: str, key: str, value: Any) -> None:
        """Store a JSON-serializable ``value`` at ``namespace/key``."""
        with self._lock:
            self._data.setdefault(namespace, {})[key] = value
            self._persist()

    def append(self, namespace: str, key: str, item: Any) -> list[Any]:
        """Append ``item`` to the list at ``namespace/key`` and return it."""
        with self._lock:
            entries = self._data.setdefault(namespace, {}).setdefault(key, [])
            if not isinstance(entries, list):
                raise TypeError(f"{namespace}/{key} does not hold a list.")
            entries.append(item)
            self._persist()
            return list(entries)

    def namespace(self, namespace: str) -> dict[str, Any]:
        """Return a shallow copy of everything stored under ``namespace``."""
        with self._lock:
            return dict(self._data.get(namespace, {}))

    def namespaces(self) -> list[str]:
        """Return the sorted list of namespaces currently in use."""
        with self._lock:
            return sorted(self._data)

    def _persist(self) -> None:
        if self._path is None:
            return
        self._path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self._path.with_suffix(self._path.suffix + ".tmp")
        temporary.write_text(json.dumps(self._data, indent=2, sort_keys=True), encoding="utf-8")
        temporary.replace(self._path)
