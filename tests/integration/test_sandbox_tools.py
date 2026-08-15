"""Sandbox tools exposed through ToolRegistry (local backend)."""

from __future__ import annotations

from pathlib import Path

import pytest

from aegisops.agents.runtime import AegisRuntime
from aegisops.config.settings import Settings
from aegisops.runtime_context import current_user_id

PROJECT_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture()
def runtime(tmp_path) -> AegisRuntime:
    settings = Settings(
        _env_file=None,
        environment="test",
        data_dir=tmp_path / "data",
        fixtures_dir=PROJECT_ROOT / "fixtures",
        skills_dir=PROJECT_ROOT / "skills",
        sandbox_backend="local",
    )
    return AegisRuntime(settings)


@pytest.mark.asyncio
async def test_sandbox_execute_tool(runtime) -> None:
    current_user_id.set("alice")
    result = await runtime.registry.call(
        "sandbox_execute", {"command": 'python -c "print(sum(range(5)))"', "timeout_seconds": 5}
    )
    assert result.ok is True
    assert "10" in result.data["stdout"]


@pytest.mark.asyncio
async def test_sandbox_read_write_tools_are_user_scoped(runtime) -> None:
    current_user_id.set("alice")
    write = await runtime.registry.call("sandbox_write_file", {"path": "notes.txt", "content": "alice-note"})
    assert write.ok is True
    read = await runtime.registry.call("sandbox_read_file", {"path": "notes.txt"})
    assert "alice-note" in read.data["content"]

    current_user_id.set("bob")
    bob_read = await runtime.registry.call("sandbox_read_file", {"path": "notes.txt"})
    assert bob_read.ok is False or "error" in bob_read.data


@pytest.mark.asyncio
async def test_sandbox_execute_rejects_forbidden_command(runtime) -> None:
    current_user_id.set("alice")
    result = await runtime.registry.call("sandbox_execute", {"command": "rm -rf /", "timeout_seconds": 5})
    assert result.ok is False
    assert "forbidden" in result.error.lower()


@pytest.mark.asyncio
async def test_sandbox_failure_recovers_and_continues(runtime) -> None:
    current_user_id.set("alice")
    proxy = await runtime.sandbox_manager.ensure("alice")
    await proxy.destroy()  # simulate backend death
    result = await runtime.registry.call(
        "sandbox_execute", {"command": "python -c \"print('after-recovery')\"", "timeout_seconds": 5}
    )
    # Local backend re-creates the workspace on connect; docker path uses health middleware.
    assert result.ok is True
    assert "after-recovery" in result.data["stdout"]
