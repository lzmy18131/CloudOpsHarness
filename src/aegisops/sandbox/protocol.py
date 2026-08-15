"""Sandbox backend protocol.

All sandbox access goes through this boundary. Backends: LocalSandboxBackend
(dev fallback, NOT a security boundary) and DockerSandboxBackend (the real
isolation boundary with network/capability/resource restrictions).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class ExecuteResult:
    exit_code: int
    stdout: str
    stderr: str
    truncated: bool = False
    duration_ms: float = 0.0

    @property
    def ok(self) -> bool:
        return self.exit_code == 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "exit_code": self.exit_code,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "truncated": self.truncated,
            "duration_ms": self.duration_ms,
        }


class SandboxBackend(ABC):
    """One execution workspace for one user."""

    backend_kind: str = "protocol"

    def __init__(self, backend_id: str | None = None) -> None:
        self.backend_id = backend_id or f"{self.backend_kind}-{id(self):x}"

    @abstractmethod
    async def create(self) -> None: ...

    @abstractmethod
    async def connect(self) -> None: ...

    @abstractmethod
    async def ping(self) -> bool: ...

    @abstractmethod
    async def execute(
        self, command: str, *, cwd: str = "/workspace", timeout_seconds: float | None = None
    ) -> ExecuteResult: ...

    @abstractmethod
    async def upload(self, path: str, content: bytes) -> None: ...

    @abstractmethod
    async def download(self, path: str) -> bytes: ...

    @abstractmethod
    async def destroy(self) -> None: ...


class SandboxBackendProxy:
    """Stable handle with explicit delegation and hot-swappable backend.

    Consumers hold this proxy forever; recovery replaces the wrapped backend
    without changing the proxy identity (the key property from the PDF
    architecture).
    """

    def __init__(self, backend: SandboxBackend, user_id: str = "anonymous") -> None:
        self.user_id = user_id
        self._backend = backend
        self.replacement_history: list[str] = [backend.backend_id]

    @property
    def backend(self) -> SandboxBackend:
        return self._backend

    @property
    def backend_id(self) -> str:
        return self._backend.backend_id

    def replace_backend(self, backend: SandboxBackend) -> str:
        """Atomically swap the wrapped backend; returns the replaced id."""
        previous = self._backend.backend_id
        self._backend = backend
        self.replacement_history.append(backend.backend_id)
        return previous

    async def create(self) -> None:
        await self._backend.create()

    async def connect(self) -> None:
        await self._backend.connect()

    async def ping(self) -> bool:
        return await self._backend.ping()

    async def execute(
        self, command: str, *, cwd: str = "/workspace", timeout_seconds: float | None = None
    ) -> ExecuteResult:
        return await self._backend.execute(command, cwd=cwd, timeout_seconds=timeout_seconds)

    async def upload(self, path: str, content: bytes) -> None:
        await self._backend.upload(path, content)

    async def download(self, path: str) -> bytes:
        return await self._backend.download(path)

    async def destroy(self) -> None:
        await self._backend.destroy()
