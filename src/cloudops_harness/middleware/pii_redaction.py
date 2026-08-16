"""Middleware: PII redaction policy observability.

The actual redaction happens inside ToolRegistry.call() before tool content
reaches any agent context; this middleware records the policy per run and
redacts the input message copy held in the run context.
"""

from __future__ import annotations

import logging

from cloudops_harness.middleware.base import Middleware
from cloudops_harness.middleware.models import RunContext
from cloudops_harness.tools.pii import redact_pii

logger = logging.getLogger("cloudops_harness.middleware.pii_redaction")


class PIIRedactionMiddleware(Middleware):
    name = "pii_redaction"

    def __init__(self, enabled: bool = True) -> None:
        self.enabled = enabled

    async def before_run(self, ctx: RunContext) -> None:
        ctx.extras["pii_redaction"] = self.enabled
        if self.enabled and ctx.input_message:
            ctx.input_message = redact_pii(ctx.input_message)
        logger.info("PII redaction enabled=%s", self.enabled)

    async def after_run(self, ctx: RunContext) -> None:
        return None
