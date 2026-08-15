"""Middleware 4: restore user-installed persistent skills into the sandbox."""

from __future__ import annotations

import logging
from pathlib import Path

from aegisops.middleware.base import Middleware
from aegisops.middleware.models import RunContext
from aegisops.sandbox.manager import SandboxManager

logger = logging.getLogger("aegisops.middleware.user_skills_restore")


class UserSkillsRestoreMiddleware(Middleware):
    name = "user_skills_restore"

    def __init__(self, manager: SandboxManager, user_skills_dir: Path | str) -> None:
        self.manager = manager
        self.user_skills_dir = Path(user_skills_dir)

    async def before_run(self, ctx: RunContext) -> None:
        proxy = await self.manager.ensure(ctx.user_id)
        user_dir = self.user_skills_dir / ctx.user_id
        if not user_dir.exists():
            ctx.extras["user_skills_restored"] = 0
            return
        restored = 0
        for skill_dir in user_dir.iterdir():
            skill_md = skill_dir / "SKILL.md"
            if not skill_md.exists():
                continue
            await proxy.upload(f"skills/{skill_dir.name}/SKILL.md", skill_md.read_bytes())
            restored += 1
        ctx.extras["user_skills_restored"] = restored
        logger.info("restored %d user skills for %s", restored, ctx.user_id)

    async def after_run(self, ctx: RunContext) -> None:
        return None
