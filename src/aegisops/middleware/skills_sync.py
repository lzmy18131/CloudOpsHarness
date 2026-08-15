"""Middleware 3: sync bundled skills into the user sandbox workspace."""

from __future__ import annotations

import logging
from pathlib import Path

import anyio

from aegisops.middleware.base import Middleware
from aegisops.middleware.models import RunContext
from aegisops.sandbox.manager import SandboxManager
from aegisops.skills.registry import SkillRegistry

logger = logging.getLogger("aegisops.middleware.skills_sync")


class SkillsSyncMiddleware(Middleware):
    name = "skills_sync"

    def __init__(self, manager: SandboxManager, skills: SkillRegistry) -> None:
        self.manager = manager
        self.skills = skills

    async def before_run(self, ctx: RunContext) -> None:
        proxy = await self.manager.ensure(ctx.user_id)
        uploaded = 0
        for metadata in self.skills.list_metadata():
            try:
                body = await anyio.to_thread.run_sync(Path(metadata.path).read_text, "utf-8")
                await proxy.upload(f"skills/{metadata.name}/SKILL.md", body.encode("utf-8"))
                uploaded += 1
            except Exception:  # noqa: BLE001 - one failed skill must not block the run
                logger.warning("failed to sync skill %s", metadata.name, exc_info=True)
        ctx.extras["skills_synced"] = uploaded
        logger.info("synced %d skills to sandbox for %s", uploaded, ctx.user_id)

    async def after_run(self, ctx: RunContext) -> None:
        return None
