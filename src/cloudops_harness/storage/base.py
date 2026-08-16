"""Thread/history storage protocol."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class ThreadStorage(ABC):
    @abstractmethod
    async def list_threads(self, user_id: str) -> list[dict[str, Any]]: ...

    @abstractmethod
    async def get_thread(self, thread_id: str) -> dict[str, Any] | None: ...

    @abstractmethod
    async def append_event(self, thread_id: str, user_id: str, event: dict[str, Any]) -> None: ...

    @abstractmethod
    async def delete_thread(self, thread_id: str, user_id: str | None = None) -> bool: ...
