"""Small, dependency-free circuit breaker shared by tools and sandbox.

States: CLOSED -> (failures >= threshold) -> OPEN -> (cooldown elapsed) ->
HALF_OPEN -> (success) -> CLOSED | (failure) -> OPEN.
Every state change is recorded in ``transitions`` for observability/tests.
"""

from __future__ import annotations

import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, TypeVar

T = TypeVar("T")


class CircuitState(StrEnum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitOpenError(RuntimeError):
    """Raised when a call is rejected because the breaker is OPEN."""


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


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
    transitions: list[dict[str, Any]] = field(default_factory=list)

    @property
    def state(self) -> CircuitState:
        return self._state

    @property
    def failure_count(self) -> int:
        return self._failure_count

    def _transition(self, to: CircuitState, reason: str) -> None:
        self.transitions.append({"from": self._state.value, "to": to.value, "reason": reason, "at": _now()})
        self._state = to

    def _trip_if_needed(self) -> None:
        if self._failure_count >= self.failure_threshold:
            self._transition(CircuitState.OPEN, f"failure_threshold={self.failure_threshold} reached")
            self._opened_at = time.monotonic()

    def allow(self) -> bool:
        if self._state == CircuitState.CLOSED:
            return True
        if self._state == CircuitState.OPEN:
            if self._opened_at is not None and time.monotonic() - self._opened_at >= self.cooldown_seconds:
                self._transition(CircuitState.HALF_OPEN, "cooldown elapsed; probing")
                self._half_open_probe = False
                return True
            return False
        # HALF_OPEN: allow exactly one probe.
        if not self._half_open_probe:
            self._half_open_probe = True
            return True
        return False

    def record_success(self) -> None:
        previous = self._state.value
        self._failure_count = 0
        self._opened_at = None
        self._state = CircuitState.CLOSED
        self._half_open_probe = False
        if previous != CircuitState.CLOSED.value:
            self.transitions.append(
                {"from": previous, "to": CircuitState.CLOSED.value, "reason": "probe succeeded", "at": _now()}
            )

    def record_failure(self) -> None:
        self._failure_count += 1
        if self._state == CircuitState.HALF_OPEN:
            self._transition(CircuitState.OPEN, "half-open probe failed")
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
