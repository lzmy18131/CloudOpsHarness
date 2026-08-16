"""Middleware run context."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class RunContext:
    user_id: str
    thread_id: str
    run_id: str
    input_message: str = ""
    extras: dict[str, Any] = field(default_factory=dict)
    result: dict[str, Any] | None = None
