"""Middleware 1: sandbox health check + automatic recovery before each run."""

from __future__ import annotations

import logging

from aegisops.middleware.base import Middleware
from aegisops.middleware.models import RunContext
from aegisops.sandbox.health import SandboxHealthMiddleware as Health

logger = logging.getLogger("aegisops.middleware.sandbox_health")


class SandboxHealthMiddleware(Middleware):
    name = "sandbox_health"

    def __init__(self, health: Health) -> None:
        self.health = health

    async def before_run(self, ctx: RunContext) -> None:
        proxy = await self.health.before_run(ctx.user_id)
        ctx.extras["sandbox_backend_id"] = proxy.backend_id
        logger.info("sandbox healthy for user %s (%s)", ctx.user_id, proxy.backend_id)

    async def after_run(self, ctx: RunContext) -> None:
        return None
