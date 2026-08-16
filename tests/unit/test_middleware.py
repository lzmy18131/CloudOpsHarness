"""Middleware stack tests: ordering, toggling, skills sync, memory update."""

from __future__ import annotations

from pathlib import Path

import pytest

from cloudops_harness.agents.runtime import CloudOpsRuntime
from cloudops_harness.config.settings import Settings
from cloudops_harness.middleware.base import MiddlewareStack
from cloudops_harness.middleware.factory import build_middleware_stack
from cloudops_harness.middleware.models import RunContext

PROJECT_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture()
def runtime(tmp_path) -> CloudOpsRuntime:
    settings = Settings(
        _env_file=None,
        environment="test",
        data_dir=tmp_path / "data",
        fixtures_dir=PROJECT_ROOT / "fixtures",
        skills_dir=PROJECT_ROOT / "skills",
        sandbox_backend="local",
    )
    return CloudOpsRuntime(settings)


@pytest.mark.asyncio
async def test_middleware_stack_runs_in_order_and_uploads_skills(runtime) -> None:
    stack: MiddlewareStack = runtime.middleware
    ctx = RunContext(
        user_id="alice", thread_id="t1", run_id="r1", input_message="payment-service 以后都用表格"
    )
    await stack.run(ctx, lambda: _ok())
    phases = [call["middleware"] for call in stack.calls]
    assert phases[:2] == ["sandbox_health", "context_injection"]
    assert ctx.extras["skills_synced"] >= 8
    assert ctx.extras["preferences_updated"] == {"preferred_output": "表格"}
    proxy = await runtime.sandbox_manager.ensure("alice")
    content = await proxy.download("skills/latency-analysis/SKILL.md")
    assert b"Latency Analysis" in content


@pytest.mark.asyncio
async def test_middleware_can_be_disabled(runtime) -> None:
    stack: MiddlewareStack = runtime.middleware
    stack.disable("skills_sync")
    ctx = RunContext(user_id="bob", thread_id="t2", run_id="r2", input_message="hi")
    await stack.run(ctx, lambda: _ok())
    assert "skills_synced" not in ctx.extras
    assert "sandbox_backend_id" in ctx.extras


@pytest.mark.asyncio
async def test_context_injection_loads_preferences_and_skills(runtime) -> None:
    runtime.memory.update("alice", preferred_language="en-US")
    ctx = RunContext(user_id="alice", thread_id="t3", run_id="r3", input_message="hi")
    await runtime.middleware.run(ctx, lambda: _ok())
    assert ctx.extras["preferences"]["preferred_language"] == "en-US"
    assert len(ctx.extras["skills_frontmatter"]) >= 8
    assert ctx.extras["policy"]["auto_approve_max_risk"] == 1


@pytest.mark.asyncio
async def test_build_middleware_stack_has_required_names(runtime) -> None:
    stack = build_middleware_stack(runtime)
    names = [m.name for m in stack.middlewares]
    for required in (
        "sandbox_health",
        "context_injection",
        "skills_sync",
        "user_skills_restore",
        "memory_update",
        "sandbox_breaker",
        "model_call_limit",
        "tool_call_limit",
        "pii_redaction",
    ):
        assert required in names


async def _ok():
    return {"status": "done"}
