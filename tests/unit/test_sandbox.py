"""Sandbox unit tests: local backend, proxy, breaker, docker arg construction."""

from __future__ import annotations

import pytest

from aegisops.sandbox.breaker import SandboxCircuitBreaker
from aegisops.sandbox.docker_backend import DockerSandboxBackend
from aegisops.sandbox.local_backend import LocalSandboxBackend
from aegisops.sandbox.manager import SandboxManager
from aegisops.sandbox.protocol import SandboxBackendProxy


@pytest.fixture()
def local_backend(tmp_path):
    return LocalSandboxBackend(tmp_path / "box", user_id="alice")


@pytest.mark.asyncio
async def test_local_backend_execute_upload_download(local_backend) -> None:
    await local_backend.create()
    assert await local_backend.ping() is True
    result = await local_backend.execute('python -c "print(21*2)"')
    assert result.ok is True
    assert "42" in result.stdout
    await local_backend.upload("data/input.txt", b"hello sandbox")
    content = await local_backend.download("data/input.txt")
    assert content == b"hello sandbox"


@pytest.mark.asyncio
async def test_local_backend_rejects_forbidden_command(local_backend) -> None:
    await local_backend.create()
    with pytest.raises(ValueError, match="forbidden"):
        await local_backend.execute("rm -rf /")


@pytest.mark.asyncio
async def test_local_backend_blocks_path_escape(local_backend) -> None:
    await local_backend.create()
    with pytest.raises(ValueError, match="escapes"):
        await local_backend.upload("../outside.txt", b"nope")


@pytest.mark.asyncio
async def test_user_isolation_between_workspaces(tmp_path) -> None:
    backend_a = LocalSandboxBackend(tmp_path / "user-a", user_id="alice")
    backend_b = LocalSandboxBackend(tmp_path / "user-b", user_id="bob")
    await backend_a.create()
    await backend_b.create()
    await backend_a.execute("python -c \"open('secret.txt','w').write('alice-secret')\"")
    listing = await backend_b.execute("python -c \"import os; print(sorted(os.listdir('.')))\"")
    assert "secret.txt" not in listing.stdout
    with pytest.raises(FileNotFoundError):
        await backend_b.download("secret.txt")


@pytest.mark.asyncio
async def test_proxy_delegation_and_backend_identity(tmp_path) -> None:
    first = LocalSandboxBackend(tmp_path / "first", user_id="u")
    await first.create()
    proxy = SandboxBackendProxy(first, user_id="u")
    assert (await proxy.execute("python -c \"print('a')\"")).stdout.strip() == "a"

    second = LocalSandboxBackend(tmp_path / "second", user_id="u")
    await second.create()
    old = proxy.replace_backend(second)
    assert old == first.backend_id
    assert proxy.backend_id == second.backend_id
    assert proxy.replacement_history == [first.backend_id, second.backend_id]
    assert (await proxy.execute("python -c \"print('b')\"")).stdout.strip() == "b"


@pytest.mark.asyncio
async def test_circuit_breaker_half_open_transition() -> None:
    breaker = SandboxCircuitBreaker(failure_threshold=1, cooldown_seconds=0.0)

    async def fail() -> None:
        raise ConnectionError("down")

    with pytest.raises(ConnectionError):
        await breaker.protect(fail)
    assert breaker.state.value == "open"
    result = await breaker.protect(lambda: asyncio_sleep_return())
    assert result == "ok"
    assert breaker.state.value == "closed"


async def asyncio_sleep_return() -> str:
    return "ok"


@pytest.mark.asyncio
async def test_circuit_breaker_trips_and_recovers(tmp_path) -> None:
    class FailingBackend(LocalSandboxBackend):
        async def execute(self, command: str, **kwargs):
            raise ConnectionError("sandbox unreachable")

    breaker = SandboxCircuitBreaker(failure_threshold=2, cooldown_seconds=60.0)
    proxy = SandboxBackendProxy(FailingBackend(tmp_path / "fail", user_id="u"), user_id="u")
    with pytest.raises(ConnectionError):
        await breaker.execute(proxy, "echo hi")
    with pytest.raises(ConnectionError):
        await breaker.execute(proxy, "echo hi")
    assert breaker.state.value == "open"
    with pytest.raises(Exception, match="OPEN"):
        await breaker.execute(proxy, "echo hi")

    # After backend replacement the breaker is reset manually (cooldown not
    # elapsed yet); the next execute closes the circuit.
    healthy = LocalSandboxBackend(tmp_path / "healthy", user_id="u")
    await healthy.create()
    proxy.replace_backend(healthy)
    breaker.reset()
    result = await breaker.execute(proxy, "python -c \"print('back')\"")
    assert "back" in result.stdout
    assert breaker.state.value == "closed"


@pytest.mark.asyncio
async def test_manager_falls_back_when_docker_create_fails(tmp_path) -> None:
    class BrokenDockerBackend(LocalSandboxBackend):
        backend_kind = "docker"

        async def create(self) -> None:
            raise RuntimeError("docker run failed")

    calls = []

    async def broken(user_id: str):
        calls.append("docker")
        return BrokenDockerBackend(tmp_path / f"broken-{user_id}", user_id)

    async def local(user_id: str):
        calls.append("local")
        return LocalSandboxBackend(tmp_path / f"local-{user_id}", user_id)

    manager = SandboxManager(broken, fallback_factory=local)
    proxy = await manager.ensure("alice")
    assert proxy.backend.backend_kind == "local"
    assert calls == ["docker", "local"]
    assert (await proxy.execute('python -c "print(1)"')).stdout.strip() == "1"


@pytest.mark.asyncio
async def test_docker_backend_builds_hardened_run_command(monkeypatch) -> None:
    captured: list[tuple] = []

    async def fake_run(self, *args, **kwargs):
        captured.append(args)
        return 0, "", ""

    monkeypatch.setattr(DockerSandboxBackend, "_run", fake_run)
    backend = DockerSandboxBackend(image="python:3.11-slim", user_id="u")
    await backend.create()
    args = captured[0]
    assert "--network" in args and "none" in args
    assert "--cap-drop" in args and "ALL" in args
    assert "--security-opt" in args and "no-new-privileges" in args
    assert "--read-only" in args
    assert "--pids-limit" in args
    assert "-v" not in args  # no host volume mounts
    await backend.execute('python -c "print(1)"')
    assert captured[1][2] == "sh"
    assert 'cd /workspace && python -c "print(1)"' in captured[1][4]
