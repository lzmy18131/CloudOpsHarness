"""Model Adapter protocol.

Every LLM-facing component talks to this protocol, never to a vendor SDK
directly. Implementations: OpenAICompatibleAdapter (DeepSeek/OpenAI/Qwen/vLLM)
and FakeLLM (deterministic, offline, used by tests/CI/eval).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from cloudops_harness.llm.budget import ModelCallBudget, get_model_budget, start_model_budget
from cloudops_harness.llm.models import AssistantTurn, LLMMessage


class ModelCallLimitError(RuntimeError):
    """Hard stop raised when the global model-call budget is exhausted."""


class ModelAdapter(ABC):
    """Unified async completion interface."""

    name: str = "model-adapter"
    token_callback: Any = None  # callable(dict) -> None, set by the SSE endpoint
    usage_total: int = 0  # rough token accounting used by evaluation
    usage_prompt_total: int = 0
    usage_completion_total: int = 0
    call_count: int = 0

    @abstractmethod
    async def generate(
        self,
        messages: list[LLMMessage],
        tools: list[dict[str, Any]] | None = None,
        response_format: dict[str, Any] | None = None,
    ) -> AssistantTurn:
        """One completion call (may include tool calls or structured output)."""

    @staticmethod
    def estimate_tokens(text: str) -> int:
        """Cheap token estimator used by context compression heuristics."""
        return max(1, len(text) // 4)


class LimitedModelAdapter(ModelAdapter):
    """Enforces a hard per-run model-call budget around any adapter.

    The budget lives in a ContextVar (one per graph invocation / request), so
    concurrent runs never share or reset each other's counters. Attributes
    delegate to the wrapped adapter so FakeLLM introspection (``calls``),
    usage accounting and token callbacks keep working.
    """

    name = "limited-model-adapter"

    def __init__(self, adapter: ModelAdapter, *, max_calls: int) -> None:
        self._adapter = adapter
        self.max_calls = max_calls

    def __getattr__(self, item: str) -> Any:
        return getattr(self._adapter, item)

    async def generate(
        self,
        messages: list[LLMMessage],
        tools: list[dict[str, Any]] | None = None,
        response_format: dict[str, Any] | None = None,
    ) -> AssistantTurn:
        budget: ModelCallBudget | None = get_model_budget()
        if budget is None:
            budget = start_model_budget("implicit", self.max_calls)
        if not budget.record():
            raise ModelCallLimitError(
                f"model call limit exceeded for run {budget.run_id} "
                f"({budget.max_calls}); graceful degradation engaged"
            )
        return await self._adapter.generate(messages, tools=tools, response_format=response_format)
