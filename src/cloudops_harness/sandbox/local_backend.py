"""LocalSandboxBackend: zero-dependency fallback for dev machines.

Important honesty note: this backend provides workspace separation and command
allowlisting but is NOT a strong security boundary (no kernel-level process or
network isolation). Production/demo-with-untrusted-code must use
DockerSandboxBackend.
"""

from __future__ import annotations

import asyncio
import re
import shutil
from pathlib import Path

from cloudops_harness.sandbox.protocol import ExecuteResult, SandboxBackend

FORBIDDEN_COMMANDS = [
    r"\brm\s+-rf\s+[/\\]",
    r"\bmkfs\b",
    r"\bdd\s+if=",
    r":\(\)\s*\{",
    r">\s*/dev/sd",
    r"C:\\Windows\\System32",
    r"del\s+/[fsq]\s+[A-Z]:",
]

MAX_OUTPUT_CHARS = 20000


class LocalSandboxBackend(SandboxBackend):
    """Per-user directory + subprocess execution with allowlist and truncation."""

    backend_kind = "local"

    def __init__(self, workspace: Path | str, user_id: str, backend_id: str | None = None) -> None:
        super().__init__(backend_id)
        self.root = Path(workspace)
        self.workspace = self.root / "workspace"
        self.user_id = user_id

    async def create(self) -> None:
        self.workspace.mkdir(parents=True, exist_ok=True)
        (self.workspace / ".cloudops_harness-owner").write_text(self.backend_id, encoding="utf-8")

    async def connect(self) -> None:
        if not self.workspace.exists():
            await self.create()

    async def ping(self) -> bool:
        try:
            probe = self.workspace / ".ping"
            probe.write_text("ok", encoding="utf-8")
            return probe.read_text(encoding="utf-8") == "ok"
        except OSError:
            return False

    def _check_command(self, command: str) -> None:
        for pattern in FORBIDDEN_COMMANDS:
            if re.search(pattern, command, re.IGNORECASE):
                raise ValueError(f"forbidden sandbox command pattern: {pattern!r}")

    def _resolve(self, path: str) -> Path:
        relative = Path(path.replace("\\", "/").lstrip("/"))
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError(f"path escapes sandbox workspace: {path!r}")
        target = self.workspace / relative
        if not str(target.resolve()).startswith(str(self.workspace.resolve())):
            raise ValueError(f"path escapes sandbox workspace: {path!r}")
        return target

    async def execute(
        self, command: str, *, cwd: str = "/workspace", timeout_seconds: float | None = None
    ) -> ExecuteResult:
        await self.connect()
        self._check_command(command)
        working = self._resolve(cwd or "workspace") if cwd and cwd != "/workspace" else self.workspace
        if not working.exists():
            return ExecuteResult(exit_code=1, stdout="", stderr=f"cwd does not exist: {working}")
        started = asyncio.get_event_loop().time()
        process = await asyncio.create_subprocess_shell(
            command,
            cwd=str(working),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout_seconds or 30.0)
        except TimeoutError:
            process.kill()
            await process.communicate()
            return ExecuteResult(
                exit_code=124,
                stdout="",
                stderr=f"command timed out after {timeout_seconds or 30.0}s",
                duration_ms=(asyncio.get_event_loop().time() - started) * 1000,
            )
        stdout_text = stdout.decode("utf-8", errors="replace")
        stderr_text = stderr.decode("utf-8", errors="replace")
        truncated = len(stdout_text) + len(stderr_text) > MAX_OUTPUT_CHARS
        return ExecuteResult(
            exit_code=process.returncode or 0,
            stdout=stdout_text[:MAX_OUTPUT_CHARS],
            stderr=stderr_text[:MAX_OUTPUT_CHARS],
            truncated=truncated,
            duration_ms=(asyncio.get_event_loop().time() - started) * 1000,
        )

    async def upload(self, path: str, content: bytes) -> None:
        await self.connect()
        target = self._resolve(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)

    async def download(self, path: str) -> bytes:
        target = self._resolve(path)
        if not target.exists():
            raise FileNotFoundError(path)
        return target.read_bytes()

    async def destroy(self) -> None:
        if self.root.exists():
            shutil.rmtree(self.root, ignore_errors=True)
