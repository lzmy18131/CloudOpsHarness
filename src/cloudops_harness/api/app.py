"""FastAPI application factory for CloudOps Harness."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from cloudops_harness.agents.checkpoint import open_checkpointer
from cloudops_harness.agents.runtime import CloudOpsRuntime
from cloudops_harness.api.chat import router as chat_router
from cloudops_harness.api.meta import router as meta_router
from cloudops_harness.config.logging_conf import setup_logging
from cloudops_harness.config.settings import PROJECT_ROOT, Settings
from cloudops_harness.storage.file_backend import FileThreadStorage
from cloudops_harness.storage.mongo_backend import MongoThreadStorage
from cloudops_harness.tracing.store import TraceStore

STATIC_DIR = PROJECT_ROOT / "static"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Create every long-lived component; release them on shutdown."""
    settings: Settings = app.state.settings
    settings.ensure_dirs()
    setup_logging(settings.log_level)

    runtime = CloudOpsRuntime(settings)
    trace_store = TraceStore(settings.traces_dir)
    runtime.registry.observer.trace_store = trace_store
    runtime.trace_store = trace_store
    if settings.storage_backend == "mongo":
        try:
            storage = MongoThreadStorage(settings.mongo_uri, settings.mongo_database)
        except RuntimeError:
            import logging

            logging.getLogger("cloudops_harness.storage").warning(
                "MongoDB backend unavailable (pymongo not installed); falling back to FileThreadStorage"
            )
            storage = FileThreadStorage(settings.history_dir)
    else:
        storage = FileThreadStorage(settings.history_dir)
    checkpointer = await open_checkpointer(settings)
    graph = runtime.build_graph(checkpointer.saver)

    app.state.runtime = runtime
    app.state.trace_store = trace_store
    app.state.storage = storage
    app.state.checkpointer = checkpointer
    app.state.graph = graph
    try:
        yield
    finally:
        await checkpointer.aclose()
        await runtime.destroy_sandboxes()


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build the FastAPI application (single composition root)."""
    settings = settings or Settings()
    settings.ensure_dirs()
    setup_logging(settings.log_level)

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        lifespan=lifespan,
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
    )
    app.state.settings = settings

    origins = [o.strip() for o in settings.allowed_origins.split(",") if o.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins or ["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(chat_router)
    app.include_router(meta_router)

    @app.get("/api/health", tags=["system"])
    async def health() -> dict:
        return {
            "status": "ok",
            "app": settings.app_name,
            "version": settings.app_version,
            "environment": settings.environment,
            "llm_mode": "real" if settings.llm_configured else "offline-fake",
            "sandbox_backend": settings.sandbox_backend,
            "storage_backend": settings.storage_backend,
            "checkpoint_backend": settings.checkpoint_backend,
            "time": datetime.now(UTC).isoformat(),
        }

    if STATIC_DIR.exists():
        app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

        @app.get("/", include_in_schema=False)
        async def index() -> FileResponse:
            return FileResponse(STATIC_DIR / "index.html")

    return app
