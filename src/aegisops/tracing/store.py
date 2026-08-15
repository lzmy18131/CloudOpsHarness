"""JSONL trace store for agent observability."""

from __future__ import annotations

import json
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


class TraceStore:
    """Append-only JSONL records; queryable by thread_id/run_id/user_id."""

    def __init__(self, traces_dir: Path | str) -> None:
        self.directory = Path(traces_dir)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.path = self.directory / "traces.jsonl"
        self._lock = threading.Lock()

    def append(self, record: dict[str, Any]) -> None:
        record["at"] = _now()
        with self._lock:
            with self.path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")

    def query(
        self,
        *,
        thread_id: str | None = None,
        run_id: str | None = None,
        user_id: str | None = None,
        limit: int = 200,
    ) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        matches: list[dict[str, Any]] = []
        with self._lock:
            with self.path.open("r", encoding="utf-8") as handle:
                for line in handle:
                    try:
                        record = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if thread_id and record.get("thread_id") != thread_id:
                        continue
                    if run_id and record.get("run_id") != run_id:
                        continue
                    if user_id and record.get("user_id") != user_id:
                        continue
                    matches.append(record)
        return matches[-limit:]
