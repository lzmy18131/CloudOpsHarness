"""Middleware 8: tool call limit accounting (hard stop lives in ToolRegistry)."""

from __future__ import annotations

import logging

from aegisops.middleware.base import Middleware
from aegisops.middleware.models import RunContext
from aegisops.tools.registry import ToolRegistry

logger = logging.getLogger("aegisops.middleware.tool_limit")


class ToolCallLimitMiddleware(Middleware):
    name = "tool_call_limit"

    def __init__(self, registry: ToolRegistry) -> None:
        self.registry = registry

    async def before_run(self, ctx: RunContext) -> None:
        ctx.extras["tool_calls_before"] = sum(self.registry.call_counts.values())

    async def after_run(self, ctx: RunContext) -> None:
        after = sum(self.registry.call_counts.values())
        this_run = after - int(ctx.extras.get("tool_calls_before", 0))
        ctx.extras["tool_calls_this_run"] = this_run
        if after >= self.registry.settings.tool_call_limit:
            logger.warning(
                "tool call budget nearly exhausted: %d/%d", after, self.registry.settings.tool_call_limit
            )
