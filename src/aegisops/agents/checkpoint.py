"""Checkpointer factory: in-memory for tests, SQLite for restart-safe runs."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from langgraph.checkpoint.memory import InMemorySaver

from aegisops.config.settings import Settings


@dataclass
class CheckpointerHandle:
    saver: Any
    _exit: Any = None

    async def aclose(self) -> None:
        if self._exit is not None:
            await self._exit(None, None, None)


async def open_checkpointer(settings: Settings) -> CheckpointerHandle:
    """Open a checkpointer. SQLite survives process restarts."""
    if settings.checkpoint_backend == "memory":
        return CheckpointerHandle(InMemorySaver())
    from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

    settings.checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    context = AsyncSqliteSaver.from_conn_string(str(settings.checkpoint_path))
    saver = await context.__aenter__()
    return CheckpointerHandle(saver, _exit=context.__aexit__)
