"""User preference memory (the only thing the LLM is allowed to remember).

CMDB facts (owner, version, dependencies, restart policy) are deliberately NOT
stored here - they come from ServiceCatalog/topology tools. This class stores
cross-thread user preferences only.
"""

from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any

from aegisops.config.settings import Settings

DEFAULT_PREFERENCES: dict[str, Any] = {
    "preferred_language": "zh-CN",
    "preferred_report_style": "markdown",
    "preferred_cloud": "aws",
    "preferred_timezone": "UTC",
    "preferred_output": "concise",
    "owned_services": [],
    "change_approval_policy": "default",
    "recent_queries": [],
}


class PreferenceStore:
    """File-backed, per-user preference memory with an in-process lock."""

    def __init__(self, settings: Settings) -> None:
        self.directory = settings.memory_dir
        self.directory.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def _path_for(self, user_id: str) -> Path:
        safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in user_id) or "anonymous"
        return self.directory / f"{safe}.json"

    def _read(self, path: Path) -> dict[str, Any]:
        try:
            with path.open("r", encoding="utf-8") as handle:
                stored = json.load(handle)
        except (json.JSONDecodeError, OSError):
            stored = {}
        merged = dict(DEFAULT_PREFERENCES)
        merged.update(stored)
        return merged

    def get(self, user_id: str) -> dict[str, Any]:
        path = self._path_for(user_id)
        with self._lock:
            if not path.exists():
                return dict(DEFAULT_PREFERENCES)
            return self._read(path)

    def update(self, user_id: str, **fields: Any) -> dict[str, Any]:
        """Merge fields into preferences and persist atomically."""
        path = self._path_for(user_id)
        with self._lock:
            current = dict(DEFAULT_PREFERENCES) if not path.exists() else self._read(path)
            for key, value in fields.items():
                if isinstance(value, list) and isinstance(current.get(key), list):
                    combined = list(dict.fromkeys([*value, *current[key]]))[:50]
                    current[key] = combined
                else:
                    current[key] = value
            tmp = path.with_suffix(".tmp")
            with tmp.open("w", encoding="utf-8") as handle:
                json.dump(current, handle, ensure_ascii=False, indent=2)
            tmp.replace(path)
            return current

    def record_query(self, user_id: str, query: str) -> dict[str, Any]:
        current = self.get(user_id)
        recent = [query, *current.get("recent_queries", [])]
        return self.update(user_id, recent_queries=recent[:10])
