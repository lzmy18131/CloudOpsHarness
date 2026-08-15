"""Middleware 2: inject runtime policy, user preferences and skill frontmatter."""

from __future__ import annotations

import logging

from aegisops.memory.preferences import PreferenceStore
from aegisops.middleware.base import Middleware
from aegisops.middleware.models import RunContext
from aegisops.skills.registry import SkillRegistry

logger = logging.getLogger("aegisops.middleware.context_injection")


class ContextInjectionMiddleware(Middleware):
    name = "context_injection"

    def __init__(
        self, memory: PreferenceStore, skills: SkillRegistry, auto_approve_max_risk: int = 1
    ) -> None:
        self.memory = memory
        self.skills = skills
        self.auto_approve_max_risk = auto_approve_max_risk

    async def before_run(self, ctx: RunContext) -> None:
        preferences = self.memory.get(ctx.user_id)
        skill_meta = [m.model_dump() for m in self.skills.list_metadata()]
        ctx.extras["preferences"] = preferences
        ctx.extras["skills_frontmatter"] = skill_meta
        ctx.extras["policy"] = {"auto_approve_max_risk": self.auto_approve_max_risk}
        logger.info(
            "context injected for %s: %d skills, language=%s",
            ctx.user_id,
            len(skill_meta),
            preferences.get("preferred_language"),
        )

    async def after_run(self, ctx: RunContext) -> None:
        return None
