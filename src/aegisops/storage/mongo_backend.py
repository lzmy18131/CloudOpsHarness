"""Optional MongoDB thread storage (extras: pip install -e ".[mongo]")."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from aegisops.storage.base import ThreadStorage


class MongoThreadStorage(ThreadStorage):
    """Conversation history in MongoDB. Used when AEGIS_STORAGE_BACKEND=mongo."""

    def __init__(self, uri: str, database: str = "aegisops") -> None:
        try:
            from pymongo import AsyncMongoClient
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise RuntimeError("pymongo not installed; use 'pip install aegisops[mongo]'") from exc
        self.client = AsyncMongoClient(uri)
        self.collection = self.client[database]["threads"]

    async def list_threads(self, user_id: str) -> list[dict[str, Any]]:
        cursor = self.collection.find({"user_id": user_id}).sort("updated_at", -1).limit(100)
        result = []
        async for record in cursor:
            result.append(
                {
                    "thread_id": record["thread_id"],
                    "user_id": record["user_id"],
                    "created_at": record.get("created_at"),
                    "updated_at": record.get("updated_at"),
                    "status": record.get("status"),
                    "preview": "",
                }
            )
        return result

    async def get_thread(self, thread_id: str) -> dict[str, Any] | None:
        record = await self.collection.find_one({"thread_id": thread_id})
        if record is None:
            return None
        record.pop("_id", None)
        return record

    async def append_event(self, thread_id: str, user_id: str, event: dict[str, Any]) -> None:
        now = datetime.now(UTC).isoformat().replace("+00:00", "Z")
        event["at"] = now
        kind = event.get("kind")
        update: dict[str, Any] = {"$set": {"updated_at": now}, "$push": {"events": event}}
        if kind == "message":
            update["$push"]["messages"] = {"role": event.get("role"), "content": event.get("content", "")}
        elif kind == "interrupt":
            update["$push"]["interrupts"] = event
            update["$set"]["status"] = "interrupted"
        elif kind == "resume":
            update["$push"]["resumes"] = event
            update["$set"]["status"] = "running"
        elif kind == "final":
            update["$set"]["final_report"] = event.get("content", "")
            update["$set"]["status"] = event.get("status", "done")
        await self.collection.update_one(
            {"thread_id": thread_id},
            {
                "$setOnInsert": {"thread_id": thread_id, "user_id": user_id, "created_at": now},
                **update,
            },
            upsert=True,
        )

    async def delete_thread(self, thread_id: str) -> bool:
        result = await self.collection.delete_one({"thread_id": thread_id})
        return result.deleted_count > 0
