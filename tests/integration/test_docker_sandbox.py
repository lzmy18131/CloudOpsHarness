"""Real DockerSandboxBackend smoke test.

Runs only when a working Docker daemon + python:3.11-slim image are available;
otherwise skips (marked integration/docker).
"""

from __future__ import annotations

import pytest

from cloudops_harness.sandbox.docker_backend import DockerSandboxBackend


@pytest.mark.integration
@pytest.mark.docker
@pytest.mark.asyncio
async def test_docker_backend_full_workspace_roundtrip() -> None:
    if not await DockerSandboxBackend.is_available():
        pytest.skip("docker daemon unavailable")
    backend = DockerSandboxBackend(image="python:3.11-slim", user_id="docker-smoke")
    try:
        await backend.create()
    except RuntimeError as exc:
        pytest.skip(f"docker image/daemon unavailable: {exc}")

    try:
        assert await backend.ping() is True
        await backend.upload("data/in.txt", b"hello-from-host")
        assert await backend.download("data/in.txt") == b"hello-from-host"

        write = await backend.execute(
            "python -c \"open('/workspace/out.txt','w').write('written-in-sandbox')\""
        )
        assert write.ok is True, write.stderr
        assert await backend.download("out.txt") == b"written-in-sandbox"

        run = await backend.execute('python -c "print(6*7)"')
        assert "42" in run.stdout
    finally:
        await backend.destroy()
