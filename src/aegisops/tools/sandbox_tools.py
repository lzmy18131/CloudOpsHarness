"""Sandbox execution tools exposed to sandbox-enabled subagents.

These tools are registered on the shared ToolRegistry at runtime, so YAML
subagent configs only need ``sandbox: true`` to receive them.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from aegisops.runtime_context import current_user_id
from aegisops.sandbox.breaker import SandboxCircuitBreaker
from aegisops.sandbox.manager import SandboxManager

SANDBOX_TOOL_NAMES = {"sandbox_execute", "sandbox_read_file", "sandbox_write_file"}


class SandboxExecuteArgs(BaseModel):
    command: str = Field(description="Shell command (sandboxed); prefer python -c for analysis")
    timeout_seconds: float = Field(default=10.0, ge=1.0, le=60.0)


class SandboxReadFileArgs(BaseModel):
    path: str = Field(description="Workspace-relative file path")


class SandboxWriteFileArgs(BaseModel):
    path: str
    content: str


class SandboxToolBridge:
    """Executor used by the dynamic sandbox_* tool definitions."""

    def __init__(
        self,
        manager: SandboxManager,
        breaker: SandboxCircuitBreaker,
        *,
        auto_recovery: bool = True,
    ) -> None:
        self.manager = manager
        self.breaker = breaker
        self.auto_recovery = auto_recovery

    async def _proxy(self):
        return await self.manager.ensure(current_user_id.get())

    async def execute(self, command: str, timeout_seconds: float = 10.0) -> dict[str, Any]:
        proxy = await self._proxy()
        try:
            result = await self.breaker.execute(proxy, command, timeout_seconds=timeout_seconds)
        except Exception as exc:  # noqa: BLE001 - backend-level failure path
            if not self.auto_recovery:
                raise RuntimeError(f"sandbox failure (recovery disabled): {exc}") from exc
            await self.manager.rebuild(proxy)
            result = await self.breaker.execute(proxy, command, timeout_seconds=timeout_seconds)
        return result.to_dict()

    async def read_file(self, path: str) -> dict[str, Any]:
        proxy = await self._proxy()
        try:
            content = await proxy.download(path)
            return {"path": path, "content": content.decode("utf-8", errors="replace")[:20000]}
        except Exception as exc:  # noqa: BLE001 - tool boundary
            return {"path": path, "error": str(exc)}

    async def write_file(self, path: str, content: str) -> dict[str, Any]:
        proxy = await self._proxy()
        await proxy.upload(path, content.encode("utf-8"))
        return {"path": path, "bytes": len(content.encode("utf-8"))}
