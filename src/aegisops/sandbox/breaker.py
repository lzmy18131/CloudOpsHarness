"""Circuit breaker for sandbox operations."""

from __future__ import annotations

from aegisops.common.circuit_breaker import CircuitBreaker
from aegisops.sandbox.protocol import ExecuteResult, SandboxBackendProxy


class SandboxCircuitBreaker(CircuitBreaker):
    """Trips on backend-level exceptions (not on non-zero user scripts)."""

    def __init__(self, failure_threshold: int = 3, cooldown_seconds: float = 30.0) -> None:
        super().__init__(
            failure_threshold=failure_threshold, cooldown_seconds=cooldown_seconds, name="sandbox"
        )

    async def execute(
        self,
        proxy: SandboxBackendProxy,
        command: str,
        *,
        timeout_seconds: float | None = None,
    ) -> ExecuteResult:
        return await self.protect(lambda: proxy.execute(command, timeout_seconds=timeout_seconds))
