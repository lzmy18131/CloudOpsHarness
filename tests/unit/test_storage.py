"""Thread storage tests: history, interrupt/resume records, user isolation."""

from __future__ import annotations

import pytest

from cloudops_harness.storage.file_backend import FileThreadStorage


@pytest.fixture()
def storage(tmp_path) -> FileThreadStorage:
    return FileThreadStorage(tmp_path / "history")


@pytest.mark.asyncio
async def test_thread_lifecycle_records_everything(storage) -> None:
    await storage.append_event("t1", "alice", {"kind": "message", "role": "user", "content": "payment down"})
    await storage.append_event(
        "t1", "alice", {"kind": "interrupt", "type": "approval", "tool_name": "rollback_release"}
    )
    await storage.append_event("t1", "alice", {"kind": "resume", "decisions": [{"type": "approve"}]})
    await storage.append_event("t1", "alice", {"kind": "final", "content": "# Report", "status": "done"})

    record = await storage.get_thread("t1")
    assert record["status"] == "done"
    assert record["final_report"] == "# Report"
    assert record["interrupts"][0]["tool_name"] == "rollback_release"
    assert record["resumes"][0]["decisions"] == [{"type": "approve"}]

    listing = await storage.list_threads("alice")
    assert listing[0]["thread_id"] == "t1"
    assert "payment down" in listing[0]["preview"]


@pytest.mark.asyncio
async def test_user_isolation_in_history(storage) -> None:
    await storage.append_event("t-a", "alice", {"kind": "message", "role": "user", "content": "alice secret"})
    await storage.append_event("t-b", "bob", {"kind": "message", "role": "user", "content": "bob secret"})
    assert await storage.list_threads("bob")
    assert all(t["user_id"] == "bob" for t in await storage.list_threads("bob"))
    assert "alice" not in [t["user_id"] for t in await storage.list_threads("bob")]


@pytest.mark.asyncio
async def test_delete_thread(storage) -> None:
    await storage.append_event("t1", "alice", {"kind": "message", "role": "user", "content": "x"})
    assert await storage.delete_thread("t1") is True
    assert await storage.get_thread("t1") is None
    assert await storage.delete_thread("missing") is False


@pytest.mark.asyncio
async def test_same_thread_id_across_users_is_not_silently_merged(storage) -> None:
    await storage.append_event(
        "same-thread", "alice", {"kind": "message", "role": "user", "content": "alice"}
    )
    await storage.append_event("same-thread", "bob", {"kind": "message", "role": "user", "content": "bob"})
    alice = await storage.get_thread("same-thread", user_id="alice")
    bob = await storage.get_thread("same-thread", user_id="bob")
    assert alice["user_id"] == "alice" and bob["user_id"] == "bob"
    with pytest.raises(ValueError, match="ambiguous"):
        await storage.get_thread("same-thread")


@pytest.mark.asyncio
async def test_mongo_same_thread_id_write_delete_are_user_scoped(monkeypatch) -> None:
    import pymongo

    from cloudops_harness.storage.mongo_backend import MongoThreadStorage

    class _FakeResult:
        def __init__(self, deleted: int = 0) -> None:
            self.deleted_count = deleted

    class _FakeCollection:
        def __init__(self) -> None:
            self.docs: dict[tuple[str, str], dict[str, str]] = {}
            self.update_filters: list[dict[str, str]] = []
            self.delete_filters: list[dict[str, str]] = []

        @staticmethod
        def _key(filter_spec: dict[str, str]) -> tuple[str, str]:
            return (filter_spec.get("thread_id", ""), filter_spec.get("user_id", ""))

        async def update_one(self, filter_spec, update, upsert=False):
            self.update_filters.append(dict(filter_spec))
            key = self._key(filter_spec)
            self.docs.setdefault(
                key,
                {
                    "thread_id": filter_spec.get("thread_id", ""),
                    "user_id": filter_spec.get("user_id", ""),
                    "events": [],
                },
            )
            return _FakeResult()

        async def delete_one(self, filter_spec):
            self.delete_filters.append(dict(filter_spec))
            key = self._key(filter_spec)
            if key in self.docs and filter_spec.get("user_id") is not None:
                del self.docs[key]
                return _FakeResult(deleted=1)
            return _FakeResult()

    class _FakeDatabase:
        def __init__(self, collection: _FakeCollection) -> None:
            self.collection = collection

        def __getitem__(self, name: str) -> _FakeCollection:
            return self.collection

    class _FakeAsyncMongoClient:
        last: _FakeAsyncMongoClient | None = None

        def __init__(self, uri: str) -> None:
            self.collection = _FakeCollection()
            _FakeAsyncMongoClient.last = self

        def __getitem__(self, name: str) -> _FakeDatabase:
            return _FakeDatabase(self.collection)

    monkeypatch.setattr(pymongo, "AsyncMongoClient", _FakeAsyncMongoClient)
    storage = MongoThreadStorage("mongodb://fake")
    await storage.append_event(
        "incident-001", "alice", {"kind": "message", "role": "user", "content": "alice"}
    )
    await storage.append_event("incident-001", "bob", {"kind": "message", "role": "user", "content": "bob"})

    collection = _FakeAsyncMongoClient.last.collection
    assert collection.update_filters == [
        {"thread_id": "incident-001", "user_id": "alice"},
        {"thread_id": "incident-001", "user_id": "bob"},
    ]

    assert await storage.delete_thread("incident-001", user_id="alice") is True
    assert collection.delete_filters[-1] == {"thread_id": "incident-001", "user_id": "alice"}
    assert ("incident-001", "alice") not in collection.docs
    assert ("incident-001", "bob") in collection.docs
