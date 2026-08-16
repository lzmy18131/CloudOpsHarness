"""SandboxManager: per-user lifecycle (create/claim/cache/reconnect/rebuild/destroy)."""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import Any

from cloudops_harness.sandbox.protocol import SandboxBackend, SandboxBackendProxy
from cloudops_harness.security.identifiers import validate_identifier

logger = logging.getLogger("cloudops_harness.sandbox.manager")


class SandboxManager:
    """Owns the user_id -> proxy mapping and a warm reserve slot."""

    def __init__(
        self,
        backend_factory: Callable[[str], Awaitable[SandboxBackend]],
        *,
        seed_files: dict[str, bytes] | None = None,
        prewarm: bool = False,
        fallback_factory: Callable[[str], Awaitable[SandboxBackend]] | None = None,
    ) -> None:
        self.backend_factory = backend_factory
        self.fallback_factory = fallback_factory
        self.seed_files = seed_files or {}
        self.prewarm_enabled = prewarm
        self.proxies: dict[str, SandboxBackendProxy] = {}
        self._warm_reserve: SandboxBackendProxy | None = None
        self.events: list[dict[str, Any]] = []

    async def _build_backend(self, user_id: str) -> SandboxBackend:
        """Create exactly one backend (no proxy). Used by normal build and rebuild."""
        backend = await self.backend_factory(user_id)
        try:
            await backend.create()
        except Exception as exc:  # noqa: BLE001 - auto mode falls back to Local
            if self.fallback_factory is None:
                raise
            logger.warning(
                "%s backend creation failed (%s); falling back to Local backend",
                backend.backend_kind,
                exc,
            )
            backend = await self.fallback_factory(user_id)
            await backend.create()
        return backend

    async def _seed_proxy(self, proxy: SandboxBackendProxy) -> None:
        for path, content in self.seed_files.items():
            try:
                await proxy.upload(path, content)
            except Exception:  # noqa: BLE001 - seeding must not block a rebuild
                logger.warning("failed to seed %s", path, exc_info=True)

    async def _build(self, user_id: str) -> SandboxBackendProxy:
        backend = await self._build_backend(user_id)
        proxy = SandboxBackendProxy(backend, user_id=user_id)
        await self._seed_proxy(proxy)
        self.events.append({"event": "created", "user_id": user_id, "backend_id": backend.backend_id})
        return proxy

    async def prewarm(self) -> None:
        if self._warm_reserve is None and self.prewarm_enabled:
            self._warm_reserve = await self._build("__warm__")

    async def ensure(self, user_id: str) -> SandboxBackendProxy:
        """Return a healthy proxy for user_id, rebuilding when necessary."""
        user_id = validate_identifier(user_id, field="user_id")
        await self.prewarm()
        existing = self.proxies.get(user_id)
        if existing is not None:
            try:
                if await existing.ping():
                    return existing
            except Exception:  # noqa: BLE001 - unreachable backend triggers rebuild
                logger.warning("cached sandbox %s unreachable; rebuilding", existing.backend_id)
            await self._dispose(existing)
        if self._warm_reserve is not None:
            proxy = self._warm_reserve
            proxy.user_id = user_id
            self._warm_reserve = None
            self.proxies[user_id] = proxy
            self.events.append({"event": "claimed_warm", "user_id": user_id, "backend_id": proxy.backend_id})
            return proxy
        proxy = await self._build(user_id)
        self.proxies[user_id] = proxy
        return proxy

    async def recover(self, proxy: SandboxBackendProxy) -> bool:
        """Health-check → rebuild → hot-swap. Returns True when rebuilt."""
        try:
            if await proxy.ping():
                return False
        except Exception:  # noqa: BLE001 - unreachable backend triggers recovery
            logger.info("sandbox %s unreachable; rebuilding", proxy.backend_id)
        return await self.rebuild(proxy)

    async def rebuild(self, proxy: SandboxBackendProxy) -> bool:
        """Unconditionally rebuild and hot-swap a proxy (used by the breaker)."""
        old_id = proxy.backend_id
        await self._dispose(proxy)
        backend = await self._build_backend(proxy.user_id)
        replaced = proxy.replace_backend(backend)
        assert not isinstance(proxy.backend, SandboxBackendProxy), "nested sandbox proxy detected"
        await self._seed_proxy(proxy)
        self.events.append(
            {"event": "recovered", "user_id": proxy.user_id, "old": replaced, "new": backend.backend_id}
        )
        logger.warning("sandbox hot-swapped %s -> %s (proxy identity unchanged)", old_id, backend.backend_id)
        return True

    async def _dispose(self, proxy: SandboxBackendProxy) -> None:
        try:
            await proxy.destroy()
        except Exception:  # noqa: BLE001 - destroying a dead sandbox must not fail recovery
            logger.debug("destroy of %s failed (ignored)", proxy.backend_id)

    async def destroy_user(self, user_id: str) -> None:
        proxy = self.proxies.pop(user_id, None)
        if proxy is not None:
            await self._dispose(proxy)

    async def destroy_all(self) -> None:
        for proxy in list(self.proxies.values()):
            await self._dispose(proxy)
        self.proxies.clear()
        if self._warm_reserve is not None:
            await self._dispose(self._warm_reserve)
            self._warm_reserve = None

    def stats(self) -> dict[str, Any]:
        return {
            "active": len(self.proxies),
            "warm_reserve": self._warm_reserve.backend_id if self._warm_reserve else None,
            "events": self.events[-20:],
        }
