"""Failure-recovery tests: sandbox dies → health check fails → manager rebuilds
→ proxy hot-swaps → agent can continue. This is the automated test required by
the spec for the recovery path."""

from __future__ import annotations

import pytest

from aegisops.sandbox.health import SandboxHealthCheck, SandboxHealthMiddleware
from aegisops.sandbox.local_backend import LocalSandboxBackend
from aegisops.sandbox.manager import SandboxManager
from aegisops.sandbox.protocol import SandboxBackendProxy


class DyingBackend(LocalSandboxBackend):
    """Backend that works once, then simulates container death."""

    def __init__(self, workspace, user_id: str) -> None:
        super().__init__(workspace, user_id)
        self.dead = False

    async def ping(self) -> bool:
        if self.dead:
            raise ConnectionError("container destroyed")
        return await super().ping()

    async def execute(self, command: str, **kwargs):
        if self.dead:
            raise ConnectionError("container destroyed")
        return await super().execute(command, **kwargs)


@pytest.fixture()
def recovery_env(tmp_path):
    counter = {"n": 0}

    async def factory(user_id: str):
        counter["n"] += 1
        workspace = tmp_path / "sandboxes" / f"{user_id}-{counter['n']}"
        backend = (
            DyingBackend(workspace, user_id) if counter["n"] == 1 else LocalSandboxBackend(workspace, user_id)
        )
        return backend

    manager = SandboxManager(factory, seed_files={"skills/README.md": b"seeded"})
    return manager, counter


@pytest.mark.asyncio
async def test_health_check_rebuilds_and_hot_swaps_proxy(recovery_env) -> None:
    manager, counter = recovery_env
    health = SandboxHealthCheck(manager)
    proxy: SandboxBackendProxy = await manager.ensure("alice")
    original_id = proxy.backend_id
    await proxy.execute("python -c \"print('alive')\"")

    # Simulate the container being destroyed behind our back.
    backend: DyingBackend = proxy.backend  # type: ignore[assignment]
    backend.dead = True

    assert await health.run(proxy) is True
    assert proxy is manager.proxies["alice"]  # proxy identity unchanged
    assert proxy.backend_id != original_id
    result = await proxy.execute("python -c \"print('recovered')\"")
    assert "recovered" in result.stdout
    assert manager.events[-1]["event"] == "recovered"
    assert manager.events[-1]["old"] == original_id
    # Seeded files were re-uploaded into the rebuilt workspace.
    assert (await proxy.download("skills/README.md")) == b"seeded"


@pytest.mark.asyncio
async def test_middleware_before_run_returns_healthy_proxy(recovery_env) -> None:
    manager, _ = recovery_env
    middleware = SandboxHealthMiddleware(manager)
    proxy = await middleware.before_run("alice")
    backend: DyingBackend = proxy.backend  # type: ignore[assignment]
    backend.dead = True
    recovered = await middleware.before_run("alice")
    assert recovered.backend_id != proxy.backend_id
    assert (await recovered.execute("python -c \"print('ok')\"")).ok is True


@pytest.mark.asyncio
async def test_manager_ensure_rebuilds_dead_user_proxy(recovery_env) -> None:
    manager, _ = recovery_env
    proxy = await manager.ensure("alice")
    backend: DyingBackend = proxy.backend  # type: ignore[assignment]
    backend.dead = True
    proxy2 = await manager.ensure("alice")
    assert proxy2.backend_id != proxy.backend_id
