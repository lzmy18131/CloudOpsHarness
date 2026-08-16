"""DockerSandboxBackend: the real isolation boundary.

Container hardening: network disabled, all capabilities dropped,
no-new-privileges, read-only rootfs, tmpfs /tmp, memory/CPU/pid limits.
No host paths are mounted.
"""

from __future__ import annotations

import asyncio
import uuid
from pathlib import Path

from cloudops_harness.sandbox.protocol import ExecuteResult, SandboxBackend

MAX_OUTPUT_CHARS = 20000
ALLOWED_CWD = {"/workspace", "/tmp", "workspace", "tmp"}


class DockerSandboxBackend(SandboxBackend):
    backend_kind = "docker"

    def __init__(self, image: str = "python:3.11-slim", user_id: str = "anonymous") -> None:
        super().__init__()
        self.image = image
        self.user_id = user_id
        self.container_name = f"cloudops_harness-{user_id}-{uuid.uuid4().hex[:10]}"
        self._available: bool | None = None

    @staticmethod
    async def is_available() -> bool:
        try:
            process = await asyncio.create_subprocess_exec(
                "docker",
                "version",
                "--format",
                "{{.Server.Version}}",
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            return (
                await asyncio.wait_for(process.communicate(), timeout=5.0) is not None
                and process.returncode == 0
            )
        except (OSError, TimeoutError):
            return False

    async def _run(self, *args: str, timeout_seconds: float = 30.0) -> tuple[int, str, str]:
        process = await asyncio.create_subprocess_exec(
            "docker",
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout_seconds)
        except TimeoutError:
            process.kill()
            await process.communicate()
            return 124, "", f"docker command timed out after {timeout_seconds}s"
        return (
            process.returncode or 0,
            stdout.decode("utf-8", errors="replace"),
            stderr.decode("utf-8", errors="replace"),
        )

    async def create(self) -> None:
        code, _, stderr = await self._run(
            "run",
            "-d",
            "--name",
            self.container_name,
            "--network",
            "none",
            "--cap-drop",
            "ALL",
            "--security-opt",
            "no-new-privileges",
            "--read-only",
            "--tmpfs",
            "/tmp:rw,noexec,nosuid,size=64m",
            "--tmpfs",
            "/workspace:rw,nosuid,nodev,size=256m",
            "-m",
            "256m",
            "--cpus",
            "0.5",
            "--pids-limit",
            "64",
            "-w",
            "/workspace",
            self.image,
            "sleep",
            "infinity",
            timeout_seconds=120.0,
        )
        if code != 0:
            raise RuntimeError(f"docker run failed: {stderr}")

    async def connect(self) -> None:
        code, stdout, _ = await self._run("inspect", "--format", "{{.State.Running}}", self.container_name)
        if code != 0 or "true" not in stdout:
            raise RuntimeError(f"container {self.container_name} is not running")

    async def ping(self) -> bool:
        code, stdout, _ = await self._run(
            "exec", self.container_name, "python", "-c", "print('cloudops_harness-ok')"
        )
        return code == 0 and "cloudops_harness-ok" in stdout

    async def execute(
        self, command: str, *, cwd: str = "/workspace", timeout_seconds: float | None = None
    ) -> ExecuteResult:
        if cwd not in ALLOWED_CWD:
            raise ValueError(f"docker sandbox cwd not allowed: {cwd!r}")
        started = asyncio.get_event_loop().time()
        code, stdout, stderr = await self._run(
            "exec",
            self.container_name,
            "sh",
            "-c",
            f"cd {cwd} && {command}",
            timeout_seconds=timeout_seconds or 30.0,
        )
        truncated = len(stdout) + len(stderr) > MAX_OUTPUT_CHARS
        return ExecuteResult(
            exit_code=code,
            stdout=stdout[:MAX_OUTPUT_CHARS],
            stderr=stderr[:MAX_OUTPUT_CHARS],
            truncated=truncated,
            duration_ms=(asyncio.get_event_loop().time() - started) * 1000,
        )

    async def upload(self, path: str, content: bytes) -> None:
        if path.startswith("/") or ".." in Path(path).parts:
            raise ValueError(f"invalid container path: {path!r}")
        parent = str(Path(path).parent).replace("\\", "/")
        if parent and parent != ".":
            code, _, stderr = await self._run(
                "exec", self.container_name, "mkdir", "-p", f"/workspace/{parent}"
            )
            if code != 0:
                raise RuntimeError(f"docker mkdir failed: {stderr}")
        host_dir = Path.home() / ".cloudops_harness-docker-tmp"
        host_dir.mkdir(parents=True, exist_ok=True)
        host_file = host_dir / f"{uuid.uuid4().hex}.tmp"
        host_file.write_bytes(content)
        try:
            code, _, stderr = await self._run(
                "cp", str(host_file), f"{self.container_name}:/workspace/{path}"
            )
            if code != 0:
                raise RuntimeError(f"docker cp failed: {stderr}")
        finally:
            host_file.unlink(missing_ok=True)

    async def download(self, path: str) -> bytes:
        host_dir = Path.home() / ".cloudops_harness-docker-tmp"
        host_dir.mkdir(parents=True, exist_ok=True)
        host_file = host_dir / f"{uuid.uuid4().hex}.out"
        try:
            code, _, stderr = await self._run(
                "cp", f"{self.container_name}:/workspace/{path}", str(host_file)
            )
            if code != 0:
                raise FileNotFoundError(f"download failed: {stderr}")
            return host_file.read_bytes()
        finally:
            host_file.unlink(missing_ok=True)

    async def destroy(self) -> None:
        await self._run("rm", "-f", self.container_name)
