"""OpenAI-compatible chat completions adapter.

Works with DeepSeek, OpenAI, Qwen (DashScope compatible mode), vLLM and any
endpoint that speaks the OpenAI chat-completions dialect. Key/URL/model come
from environment only (LLM_API_KEY / LLM_BASE_URL / LLM_MODEL).
"""

from __future__ import annotations

import json
from typing import Any

from openai import AsyncOpenAI

from cloudops_harness.config.settings import Settings
from cloudops_harness.llm.base import ModelAdapter
from cloudops_harness.llm.models import AssistantTurn, LLMMessage, ToolCall, Usage


class OpenAICompatibleAdapter(ModelAdapter):
    """Thin, typed wrapper around AsyncOpenAI."""

    name = "openai-compatible"

    def __init__(self, settings: Settings) -> None:
        if not settings.llm_configured:
            raise ValueError("LLM_API_KEY is required for OpenAICompatibleAdapter")
        self.settings = settings
        self.client = AsyncOpenAI(
            api_key=settings.llm_api_key,
            base_url=settings.llm_base_url,
            timeout=settings.llm_timeout_seconds,
            max_retries=settings.llm_max_retries,
        )

    def build_params(
        self,
        messages: list[LLMMessage],
        tools: list[dict[str, Any]] | None = None,
        response_format: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Assemble request kwargs (exposed for unit testing without network)."""
        params: dict[str, Any] = {
            "model": self.settings.llm_model,
            "messages": [m.model_dump(exclude_none=True, exclude={"name"}) for m in messages],
            "temperature": self.settings.llm_temperature,
        }
        if self.settings.llm_max_tokens is not None:
            params["max_tokens"] = self.settings.llm_max_tokens
        if tools:
            params["tools"] = tools
            params["tool_choice"] = "auto"
        if response_format:
            params["response_format"] = response_format
        return params

    async def generate(
        self,
        messages: list[LLMMessage],
        tools: list[dict[str, Any]] | None = None,
        response_format: dict[str, Any] | None = None,
    ) -> AssistantTurn:
        params = self.build_params(messages, tools, response_format)
        response = await self.client.chat.completions.create(**params)
        self.call_count += 1
        choice = response.choices[0]
        message = choice.message
        tool_calls = [
            ToolCall(
                id=tc.id or f"call-{index}",
                name=tc.function.name,
                arguments=self._parse_arguments(tc.function.arguments),
            )
            for index, tc in enumerate(message.tool_calls or [])
        ]
        usage = Usage()
        if response.usage is not None:
            usage = Usage(
                prompt_tokens=response.usage.prompt_tokens or 0,
                completion_tokens=response.usage.completion_tokens or 0,
                total_tokens=response.usage.total_tokens or 0,
            )
        self.usage_total += usage.total_tokens
        self.usage_prompt_total += usage.prompt_tokens
        self.usage_completion_total += usage.completion_tokens
        if self.token_callback is not None and message.content:
            self.token_callback({"type": "token", "content": message.content, "source": "main"})
        return AssistantTurn(
            content=message.content,
            tool_calls=tool_calls,
            finish_reason=choice.finish_reason or "stop",
            usage=usage,
            raw=response.model_dump(),
        )

    @staticmethod
    def _parse_arguments(raw: str | None) -> dict[str, Any]:
        if not raw:
            return {}
        try:
            parsed = json.loads(raw)
            return parsed if isinstance(parsed, dict) else {"value": parsed}
        except json.JSONDecodeError:
            return {"_raw": raw}
