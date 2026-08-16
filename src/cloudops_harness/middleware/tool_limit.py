"""Middleware 8: run-scoped tool call accounting.

The hard limit is enforced by ``ToolRegistry.call`` via the ContextVar
``ToolCallBudget``; this middleware only reports the current run's usage.
"""

from __future__ import annotations

import logging

from cloudops_harness.middleware.base import Middleware
from cloudops_harness.middleware.models import RunContext
from cloudops_harness.tools.budget import get_tool_budget
from cloudops_harness.tools.registry import ToolRegistry

logger = logging.getLogger("cloudops_harness.middleware.tool_limit")


class ToolCallLimitMiddleware(Middleware):
    name = "tool_call_limit"

    def __init__(self, registry: ToolRegistry) -> None:
        self.registry = registry

    async def before_run(self, ctx: RunContext) -> None:
        ctx.extras["tool_calls_this_run"] = 0

    async def after_run(self, ctx: RunContext) -> None:
        budget = get_tool_budget()
        calls = budget.calls if budget is not None else 0
        ctx.extras["tool_calls_this_run"] = calls
        if budget is not None and (budget.exhausted or calls >= budget.max_calls):
            logger.warning(
                "tool call budget exhausted for run %s: %d/%d",
                budget.run_id,
                calls,
                budget.max_calls,
            )
