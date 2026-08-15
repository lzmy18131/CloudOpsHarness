"""Model Adapter protocol.

Every LLM-facing component talks to this protocol, never to a vendor SDK
directly. Implementations: OpenAICompatibleAdapter (DeepSeek/OpenAI/Qwen/vLLM)
and FakeLLM (deterministic, offline, used by tests/CI/eval).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from aegisops.llm.models import AssistantTurn, LLMMessage


class ModelAdapter(ABC):
    """Unified async completion interface."""

    name: str = "model-adapter"
    token_callback: Any = None  # callable(dict) -> None, set by the SSE endpoint
    usage_total: int = 0  # rough token accounting used by evaluation
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
