"""Sandbox health sentinel and recovery entry point.

Used both by the middleware stack and directly by tests: ping the proxy; when
the backend is unreachable, ask the manager to rebuild and hot-swap it.
"""

from __future__ import annotations

import logging

from aegisops.sandbox.manager import SandboxManager
from aegisops.sandbox.protocol import SandboxBackendProxy

logger = logging.getLogger("aegisops.sandbox.health")


class SandboxHealthCheck:
    """Ping → recover pipeline."""

    def __init__(self, manager: SandboxManager) -> None:
        self.manager = manager

    async def run(self, proxy: SandboxBackendProxy) -> bool:
        """Return True when the proxy was recovered during this check."""
        try:
            healthy = await proxy.ping()
        except Exception:  # noqa: BLE001 - any transport error means unhealthy
            healthy = False
        if healthy:
            return False
        return await self.manager.recover(proxy)


class SandboxHealthMiddleware:
    """ensure → ping → recover → return healthy proxy."""

    def __init__(self, manager: SandboxManager) -> None:
        self.manager = manager
        self.health = SandboxHealthCheck(manager)

    async def before_run(self, user_id: str) -> SandboxBackendProxy:
        proxy = await self.manager.ensure(user_id)
        await self.health.run(proxy)
        return proxy
