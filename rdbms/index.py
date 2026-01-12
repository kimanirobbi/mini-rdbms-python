import json
import os
from typing import Any, Dict, Set

from .exceptions import IndexErrorRDB


class Index:
    """Simple hash-based index persisted as JSON: value->list of primary keys."""

    def __init__(self, path: str, column: str):
        self.path = path
        self.column = column
        self._map: Dict[str, Set[str]] = {}
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        self._load()

    def _load(self):
        if not os.path.exists(self.path):
            self._map = {}
            return
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                raw = json.load(f)
            self._map = {k: set(v) for k, v in raw.items()}
        except Exception as e:
            raise IndexErrorRDB(f"Failed to load index {self.path}: {e}")

    def _persist(self):
        # write as value -> list
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump({k: list(v) for k, v in self._map.items()}, f, indent=2)

    def add(self, value: Any, pk: str):
        key = json.dumps(value, sort_keys=True)
        if key not in self._map:
            self._map[key] = set()
        self._map[key].add(str(pk))
        self._persist()

    def remove(self, value: Any, pk: str):
        key = json.dumps(value, sort_keys=True)
        if key in self._map and str(pk) in self._map[key]:
            self._map[key].remove(str(pk))
            if not self._map[key]:
                del self._map[key]
            self._persist()

    def lookup(self, value: Any) -> Set[str]:
        key = json.dumps(value, sort_keys=True)
        return set(self._map.get(key, set()))
