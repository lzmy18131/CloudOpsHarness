"""Middleware protocol and stack."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from typing import Any

from aegisops.middleware.models import RunContext

logger = logging.getLogger("aegisops.middleware")


class Middleware(ABC):
    name: str = "middleware"

    @abstractmethod
    async def before_run(self, ctx: RunContext) -> None: ...

    @abstractmethod
    async def after_run(self, ctx: RunContext) -> None: ...


class MiddlewareStack:
    """Ordered, individually toggleable middleware pipeline."""

    def __init__(self, middlewares: list[Middleware] | None = None) -> None:
        self.middlewares: list[Middleware] = middlewares or []
        self.disabled: set[str] = set()
        self.calls: list[dict[str, Any]] = []

    def disable(self, name: str) -> None:
        self.disabled.add(name)

    def enable(self, name: str) -> None:
        self.disabled.discard(name)

    def _active(self) -> list[Middleware]:
        return [m for m in self.middlewares if m.name not in self.disabled]

    def active(self) -> list[Middleware]:
        """Public accessor for streaming endpoints that need manual phases."""
        return self._active()

    async def run(self, ctx: RunContext, invoke: Callable[[], Awaitable[Any]]) -> Any:
        for middleware in self._active():
            await middleware.before_run(ctx)
            self.calls.append({"middleware": middleware.name, "phase": "before"})
        result = await invoke()
        ctx.result = result if isinstance(result, dict) else {"value": result}
        for middleware in reversed(self._active()):
            await middleware.after_run(ctx)
            self.calls.append({"middleware": middleware.name, "phase": "after"})
        return result
