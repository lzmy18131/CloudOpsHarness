"""Context variables carrying the active run identity through async calls."""

from __future__ import annotations

from contextvars import ContextVar

current_user_id: ContextVar[str] = ContextVar("aegisops_user_id", default="anonymous")
current_thread_id: ContextVar[str] = ContextVar("aegisops_thread_id", default="")
current_run_id: ContextVar[str] = ContextVar("aegisops_run_id", default="")
token_sink: ContextVar = ContextVar("aegisops_token_sink", default=None)
