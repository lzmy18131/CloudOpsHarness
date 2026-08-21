"""Fail-closed helpers for real-LLM evaluation.

Real evaluation must never silently fall back to FakeLLM. These helpers make
that invariant explicit and unit-testable without network access.
"""

from __future__ import annotations

from cloudops_harness.config.settings import Settings
from cloudops_harness.llm.fake import FakeLLM
from cloudops_harness.llm.openai_adapter import OpenAICompatibleAdapter


class RealEvalError(RuntimeError):
    """Raised when a real evaluation precondition is not satisfied."""


def ensure_real_configured(settings: Settings) -> None:
    """Raise unless a real LLM API key is configured."""
    if not settings.llm_configured:
        raise RealEvalError(
            "LLM_API_KEY is not set; real evaluation aborted (no fabricated numbers). "
            "Real evaluation is fail-closed and never falls back to FakeLLM."
        )


def assert_adapter_is_real(adapter) -> None:
    """Raise if an adapter is FakeLLM or otherwise not the OpenAI-compatible adapter."""
    if isinstance(adapter, FakeLLM):
        raise RealEvalError("refusing to run real eval with FakeLLM adapter")
    if not isinstance(adapter, OpenAICompatibleAdapter):
        raise RealEvalError(f"unexpected adapter type for real eval: {type(adapter).__name__}")
