"""Middleware 7: model call limit accounting."""

from __future__ import annotations

import logging

from aegisops.llm.fake import FakeLLM
from aegisops.middleware.base import Middleware
from aegisops.middleware.models import RunContext

logger = logging.getLogger("aegisops.middleware.model_limit")


class ModelCallLimitMiddleware(Middleware):
    name = "model_call_limit"

    def __init__(self, limit: int = 60, adapters: list | None = None) -> None:
        self.limit = limit
        self.adapters = adapters or []

    def _total_calls(self) -> int:
        return sum(len(adapter.calls) for adapter in self.adapters if isinstance(adapter, FakeLLM))

    async def before_run(self, ctx: RunContext) -> None:
        ctx.extras["model_call_limit"] = self.limit
        ctx.extras["model_calls_before"] = self._total_calls()

    async def after_run(self, ctx: RunContext) -> None:
        calls = self._total_calls() - int(ctx.extras.get("model_calls_before", 0))
        ctx.extras["model_calls_this_run"] = calls
        if calls > self.limit:
            logger.error("model call limit exceeded: %d > %d", calls, self.limit)
