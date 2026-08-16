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
