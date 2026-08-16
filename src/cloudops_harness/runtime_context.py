"""Context variables carrying the active run identity through async calls."""

from __future__ import annotations

from contextvars import ContextVar

current_user_id: ContextVar[str] = ContextVar("cloudops_harness_user_id", default="anonymous")
current_thread_id: ContextVar[str] = ContextVar("cloudops_harness_thread_id", default="")
current_run_id: ContextVar[str] = ContextVar("cloudops_harness_run_id", default="")
token_sink: ContextVar = ContextVar("cloudops_harness_token_sink", default=None)
