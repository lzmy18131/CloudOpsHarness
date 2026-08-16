"""Middleware 5: update long-term user preference memory after each run."""

from __future__ import annotations

import logging
import re

from cloudops_harness.memory.preferences import PreferenceStore
from cloudops_harness.middleware.base import Middleware
from cloudops_harness.middleware.models import RunContext

logger = logging.getLogger("cloudops_harness.middleware.memory_update")

PREFERENCE_PATTERNS = [
    (re.compile(r"以后都用\s*([\u4e00-\u9fa5A-Za-z]+)"), "preferred_output"),
    (re.compile(r"prefer\s+([a-z_]+)", re.IGNORECASE), "preferred_output"),
    (re.compile(r"报告用\s*([\u4e00-\u9fa5A-Za-z]+)"), "preferred_report_style"),
]


class MemoryUpdateMiddleware(Middleware):
    name = "memory_update"

    def __init__(self, memory: PreferenceStore) -> None:
        self.memory = memory

    async def before_run(self, ctx: RunContext) -> None:
        return None

    async def after_run(self, ctx: RunContext) -> None:
        text = ctx.input_message
        updated: dict[str, str] = {}
        for pattern, field in PREFERENCE_PATTERNS:
            match = pattern.search(text)
            if match:
                updated[field] = match.group(1).strip()
        if updated:
            self.memory.update(ctx.user_id, **updated)
            logger.info("preferences updated for %s: %s", ctx.user_id, updated)
        ctx.extras["preferences_updated"] = updated
