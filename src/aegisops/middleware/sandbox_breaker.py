"""Middleware 6: sandbox circuit breaker gate."""

from __future__ import annotations

import logging

from aegisops.middleware.base import Middleware
from aegisops.middleware.models import RunContext
from aegisops.sandbox.breaker import SandboxCircuitBreaker

logger = logging.getLogger("aegisops.middleware.sandbox_breaker")


class SandboxCircuitBreakerMiddleware(Middleware):
    name = "sandbox_breaker"

    def __init__(self, breaker: SandboxCircuitBreaker) -> None:
        self.breaker = breaker

    async def before_run(self, ctx: RunContext) -> None:
        ctx.extras["sandbox_breaker_state"] = self.breaker.state.value
        if self.breaker.state.value == "open":
            logger.warning("sandbox circuit is OPEN; sandbox tools will degrade gracefully")

    async def after_run(self, ctx: RunContext) -> None:
        ctx.extras["sandbox_breaker_state_end"] = self.breaker.state.value
