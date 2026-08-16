"""File-backed thread storage (zero-dependency default)."""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from cloudops_harness.security.identifiers import validate_identifier
from cloudops_harness.storage.base import ThreadStorage


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _safe(value: str) -> str:
    return validate_identifier(value, field="thread_id")


class FileThreadStorage(ThreadStorage):
    """One JSON file per thread under ``history_dir/<user_id>/<thread_id>.json``."""

    def __init__(self, history_dir: Path | str) -> None:
        self.root = Path(history_dir)
        self.root.mkdir(parents=True, exist_ok=True)
        self._lock = asyncio.Lock()

    def _path(self, user_id: str, thread_id: str) -> Path:
        return self.root / validate_identifier(user_id, field="user_id") / f"{_safe(thread_id)}.json"

    async def list_threads(self, user_id: str) -> list[dict[str, Any]]:
        user_dir = self.root / _safe(user_id)
        if not user_dir.exists():
            return []
        threads: list[dict[str, Any]] = []
        for path in user_dir.glob("*.json"):
            record = json.loads(path.read_text(encoding="utf-8"))
            threads.append(
                {
                    "thread_id": record["thread_id"],
                    "user_id": record["user_id"],
                    "created_at": record["created_at"],
                    "updated_at": record["updated_at"],
                    "status": record.get("status", "unknown"),
                    "preview": (record.get("messages") or [{}])[-1].get("content", "")[:160]
                    if record.get("messages")
                    else "",
                }
            )
        return sorted(threads, key=lambda t: t["updated_at"], reverse=True)

    async def get_thread(self, thread_id: str, user_id: str | None = None) -> dict[str, Any] | None:
        """Get one thread. With user_id the lookup is namespaced; without it a
        cross-user collision raises ValueError (never silently picks a winner)."""
        if user_id is not None:
            path = self._path(user_id, thread_id)
            return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None
        matches = []
        for user_dir in self.root.glob("*"):
            if not user_dir.is_dir():
                continue
            path = user_dir / f"{_safe(thread_id)}.json"
            if path.exists():
                matches.append(json.loads(path.read_text(encoding="utf-8")))
        if len(matches) > 1:
            raise ValueError(f"thread_id {thread_id!r} is ambiguous across users; supply user_id")
        return matches[0] if matches else None

    async def append_event(self, thread_id: str, user_id: str, event: dict[str, Any]) -> None:
        async with self._lock:
            path = self._path(user_id, thread_id)
            if path.exists():
                record = json.loads(path.read_text(encoding="utf-8"))
            else:
                record = {
                    "thread_id": thread_id,
                    "user_id": user_id,
                    "created_at": _now(),
                    "updated_at": _now(),
                    "status": "running",
                    "messages": [],
                    "interrupts": [],
                    "resumes": [],
                    "events": [],
                }
            record["updated_at"] = _now()
            event["at"] = _now()
            kind = event.get("kind")
            if kind == "message":
                record["messages"].append(
                    {"role": event.get("role", "user"), "content": event.get("content", "")}
                )
            elif kind == "interrupt":
                record["interrupts"].append(event)
                record["status"] = "interrupted"
            elif kind == "resume":
                record["resumes"].append(event)
                record["status"] = "running"
            elif kind == "final":
                record["final_report"] = event.get("content", "")
                record["status"] = event.get("status", "done")
            record["events"].append(event)
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp = path.with_suffix(".tmp")
            tmp.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
            tmp.replace(path)

    async def delete_thread(self, thread_id: str, user_id: str | None = None) -> bool:
        if user_id is not None:
            path = self._path(user_id, thread_id)
            if path.exists():
                path.unlink()
                return True
            return False
        for user_dir in self.root.glob("*"):
            path = user_dir / f"{_safe(thread_id)}.json"
            if path.exists():
                path.unlink()
                return True
        return False
