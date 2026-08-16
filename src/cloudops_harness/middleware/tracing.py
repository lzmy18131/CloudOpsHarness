"""Middleware: run-level tracing events."""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from cloudops_harness.agents.events import emit
from cloudops_harness.middleware.base import Middleware
from cloudops_harness.middleware.models import RunContext

logger = logging.getLogger("cloudops_harness.middleware.tracing")


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


class TracingMiddleware(Middleware):
    name = "tracing"

    async def before_run(self, ctx: RunContext) -> None:
        emit("run_start", run_id=ctx.run_id, thread_id=ctx.thread_id, user_id=ctx.user_id, at=_now())
        logger.info("run %s started for thread %s", ctx.run_id, ctx.thread_id)

    async def after_run(self, ctx: RunContext) -> None:
        status = (ctx.result or {}).get("status", "unknown") if isinstance(ctx.result, dict) else "unknown"
        emit("run_end", run_id=ctx.run_id, status=status, at=_now())
        logger.info("run %s ended with status=%s", ctx.run_id, status)
