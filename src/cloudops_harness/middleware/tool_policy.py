"""Middleware 9: tool risk policy observability."""

from __future__ import annotations

import logging

from cloudops_harness.middleware.base import Middleware
from cloudops_harness.middleware.models import RunContext
from cloudops_harness.tools.risk import RiskPolicy

logger = logging.getLogger("cloudops_harness.middleware.tool_policy")


class ToolPolicyMiddleware(Middleware):
    name = "tool_policy"

    def __init__(self, policy: RiskPolicy) -> None:
        self.policy = policy

    async def before_run(self, ctx: RunContext) -> None:
        ctx.extras["auto_approve_max_risk"] = self.policy.auto_approve_max_risk
        logger.info(
            "tool policy active: auto-approve up to L%d; L2/L3 require HITL",
            self.policy.auto_approve_max_risk,
        )

    async def after_run(self, ctx: RunContext) -> None:
        return None
