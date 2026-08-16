"""Middleware 8: tool call limit accounting (hard stop lives in ToolRegistry)."""

from __future__ import annotations

import logging

from cloudops_harness.middleware.base import Middleware
from cloudops_harness.middleware.models import RunContext
from cloudops_harness.tools.registry import ToolRegistry

logger = logging.getLogger("cloudops_harness.middleware.tool_limit")


class ToolCallLimitMiddleware(Middleware):
    name = "tool_call_limit"

    def __init__(self, registry: ToolRegistry) -> None:
        self.registry = registry

    async def before_run(self, ctx: RunContext) -> None:
        ctx.extras["tool_calls_before"] = sum(self.registry.global_telemetry.values())

    async def after_run(self, ctx: RunContext) -> None:
        after = sum(self.registry.global_telemetry.values())
        this_run = after - int(ctx.extras.get("tool_calls_before", 0))
        ctx.extras["tool_calls_this_run"] = this_run
        if after >= self.registry.settings.tool_call_limit:
            logger.warning(
                "tool call budget nearly exhausted: %d/%d", after, self.registry.settings.tool_call_limit
            )
