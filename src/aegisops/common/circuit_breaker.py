"""Small, dependency-free circuit breaker shared by tools and sandbox.

States: CLOSED -> (failures >= threshold) -> OPEN -> (cooldown elapsed) ->
HALF_OPEN -> (success) -> CLOSED | (failure) -> OPEN.
"""

from __future__ import annotations

import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from enum import StrEnum
from typing import TypeVar

T = TypeVar("T")


class CircuitState(StrEnum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitOpenError(RuntimeError):
    """Raised when a call is rejected because the breaker is OPEN."""


@dataclass
class CircuitBreaker:
    """Async circuit breaker with failure threshold and cooldown."""

    failure_threshold: int = 3
    cooldown_seconds: float = 30.0
    name: str = "circuit"
    _failure_count: int = 0
    _opened_at: float | None = None
    _state: CircuitState = CircuitState.CLOSED
    _half_open_probe: bool = field(default=False, init=False)

    @property
    def state(self) -> CircuitState:
        return self._state

    @property
    def failure_count(self) -> int:
        return self._failure_count

    def _trip_if_needed(self) -> None:
        if self._failure_count >= self.failure_threshold:
            self._state = CircuitState.OPEN
            self._opened_at = time.monotonic()

    def allow(self) -> bool:
        if self._state == CircuitState.CLOSED:
            return True
        if self._state == CircuitState.OPEN:
            if self._opened_at is not None and time.monotonic() - self._opened_at >= self.cooldown_seconds:
                self._state = CircuitState.HALF_OPEN
                self._half_open_probe = False
                return True
            return False
        # HALF_OPEN: allow exactly one probe.
        if not self._half_open_probe:
            self._half_open_probe = True
            return True
        return False

    def record_success(self) -> None:
        self._failure_count = 0
        self._opened_at = None
        self._state = CircuitState.CLOSED
        self._half_open_probe = False

    def record_failure(self) -> None:
        self._failure_count += 1
        if self._state == CircuitState.HALF_OPEN:
            self._state = CircuitState.OPEN
            self._opened_at = time.monotonic()
            self._half_open_probe = False
        else:
            self._trip_if_needed()

    def reset(self) -> None:
        self.record_success()

    async def protect(self, call: Callable[[], Awaitable[T]]) -> T:
        """Run ``call`` under breaker protection; raises CircuitOpenError when open."""
        if not self.allow():
            raise CircuitOpenError(f"circuit '{self.name}' is OPEN")
        try:
            result = await call()
        except Exception:
            self.record_failure()
            raise
        self.record_success()
        return result
