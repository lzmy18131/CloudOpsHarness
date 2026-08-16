"""Reusable LLM ↔ tool loop used by subagents (and the single-agent baseline).

Keeps one generic implementation for: call LLM → collect tool_calls → execute
via ToolRegistry → feed ToolMessages back → repeat until final answer or limit.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from cloudops_harness.llm.base import ModelAdapter, ModelCallLimitError
from cloudops_harness.llm.models import LLMMessage, ToolCall
from cloudops_harness.tools.registry import ToolApprovalRequiredError, ToolRegistry, ToolResult


@dataclass
class LoopStats:
    llm_calls: int = 0
    tool_calls: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    degraded: bool = False
    tool_results: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class LoopResult:
    messages: list[LLMMessage]
    final_content: str
    stats: LoopStats
    finished: bool


class AgentLoop:
    """Deterministic, bounded agentic loop shared by all subagents."""

    def __init__(
        self,
        adapter: ModelAdapter,
        registry: ToolRegistry,
        *,
        agent_name: str = "agent",
        max_iterations: int = 8,
    ) -> None:
        self.adapter = adapter
        self.registry = registry
        self.agent_name = agent_name
        self.max_iterations = max_iterations

    async def run(
        self,
        messages: list[LLMMessage],
        *,
        tool_names: set[str] | None = None,
        read_only: bool = True,
        approved: bool = False,
        max_tool_result_chars: int | None = None,
        full_results: list[dict[str, Any]] | None = None,
    ) -> LoopResult:
        """Run the loop. ``tool_names=None`` means every read-only tool.

        Tool results longer than ``max_tool_result_chars`` are truncated in the
        model context; the full payload is appended to ``full_results`` for
        evidence extraction and isolation tests.
        """
        working = list(messages)
        stats = LoopStats()
        if full_results is None:
            full_results = []
        if tool_names is None:
            tools = self.registry.openai_schemas(read_only=read_only)
        else:
            tools = self.registry.openai_schemas(names=tool_names, read_only=read_only)

        for _ in range(self.max_iterations):
            try:
                turn = await self.adapter.generate(working, tools=tools or None)
            except ModelCallLimitError as exc:
                stats.degraded = True
                working.append(
                    LLMMessage(
                        role="assistant",
                        content=f"[{self.agent_name}] model-call budget exhausted: {exc}. Returning partial evidence collected so far.",
                    )
                )
                return LoopResult(
                    messages=working, final_content=working[-1].content, stats=stats, finished=False
                )
            except TimeoutError as exc:
                stats.degraded = True
                working.append(
                    LLMMessage(
                        role="assistant",
                        content=f"[{self.agent_name}] LLM call timed out: {exc}. Returning partial evidence collected so far.",
                    )
                )
                return LoopResult(
                    messages=working, final_content=working[-1].content, stats=stats, finished=False
                )
            stats.llm_calls += 1
            stats.prompt_tokens += turn.usage.prompt_tokens
            stats.completion_tokens += turn.usage.completion_tokens
            working.append(
                LLMMessage(
                    role="assistant",
                    content=turn.content or "",
                    tool_calls=turn.tool_calls or None,
                )
            )
            if not turn.tool_calls:
                return LoopResult(
                    messages=working, final_content=turn.content or "", stats=stats, finished=True
                )

            for call in turn.tool_calls:
                result = await self._execute(call, approved=approved)
                stats.tool_calls += 1
                stats.tool_results.append({"tool": call.name, "ok": result.ok, "error": result.error})
                full_results.append(
                    {
                        "tool": call.name,
                        "arguments": call.arguments,
                        "ok": result.ok,
                        "content": result.content,
                        "error": result.error,
                    }
                )
                content = result.content if result.ok else f"ERROR: {result.error}"
                if max_tool_result_chars and len(content) > max_tool_result_chars:
                    content = (
                        content[:max_tool_result_chars]
                        + f"... [{len(content) - max_tool_result_chars} chars truncated]"
                    )
                working.append(LLMMessage(role="tool", content=content, tool_call_id=call.id, name=call.name))

        stats.degraded = True
        working.append(
            LLMMessage(
                role="assistant",
                content=f"[{self.agent_name}] stopped after {self.max_iterations} iterations (loop limit reached).",
            )
        )
        return LoopResult(messages=working, final_content=working[-1].content, stats=stats, finished=False)

    async def _execute(self, call: ToolCall, approved: bool) -> Any:
        try:
            return await self.registry.call(
                call.name, call.arguments, agent=self.agent_name, approved=approved
            )
        except ToolApprovalRequiredError as exc:
            return ToolResult(ok=False, tool_name=call.name, content="", error=str(exc))
