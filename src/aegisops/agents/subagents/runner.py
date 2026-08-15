"""SubAgent execution: isolated context, tool whitelist, structured report.

Each run creates a fresh adapter instance (for FakeLLM this resets the
scenario-driven tool cursor), builds an independent message window, executes
its own read-only tools, and returns one ``SubAgentReport``. The transcript
never reaches the main-agent context.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from aegisops.agents.loop import AgentLoop, LoopStats
from aegisops.agents.models import EvidenceItem, SubAgentReport
from aegisops.agents.subagents.loader import SubAgentConfig
from aegisops.llm.base import ModelAdapter
from aegisops.llm.models import LLMMessage
from aegisops.llm.structured import StructuredOutputError, generate_structured
from aegisops.tools.registry import ToolRegistry
from aegisops.tools.sandbox_tools import SANDBOX_TOOL_NAMES


@dataclass
class SubAgentRunResult:
    report: SubAgentReport
    transcript: list[dict[str, Any]] = field(default_factory=list)
    full_tool_results: list[dict[str, Any]] = field(default_factory=list)
    stats: LoopStats | None = None
    degraded: bool = False


class SubAgentRunner:
    """Executes one declarative subagent config in an isolated context."""

    def __init__(
        self,
        registry: ToolRegistry,
        adapter_factory: Callable[..., ModelAdapter],
        *,
        skills_frontmatter: dict[str, list[dict[str, Any]]] | None = None,
        max_llm_calls_per_run: int = 8,
    ) -> None:
        self.registry = registry
        self.adapter_factory = adapter_factory
        self.skills_frontmatter = skills_frontmatter or {}
        self.max_llm_calls_per_run = max_llm_calls_per_run

    async def run(
        self,
        config: SubAgentConfig,
        task_brief: str,
        state: dict[str, Any],
    ) -> SubAgentRunResult:
        scenario = state.get("scenario") or {}
        adapter = self.adapter_factory(scenario or None)
        system_parts = [config.system_prompt, f"AGENT_ROLE: {config.name}", "READ-ONLY TOOLS ONLY."]
        for skill_name in config.skills:
            for meta in self.skills_frontmatter.get(skill_name, []):
                system_parts.append(
                    f"SKILL {meta.get('name', skill_name)}: {meta.get('description', '')} "
                    f"(when needed: {meta.get('path', '')})"
                )
        if scenario:
            system_parts.append(f"INCIDENT_ID: {scenario.get('incident_id', '')}")
        messages = [
            LLMMessage(role="system", content="\n".join(system_parts)),
            LLMMessage(role="user", content=task_brief),
        ]

        full_results: list[dict[str, Any]] = []
        tool_names = set(config.tools)
        if config.sandbox:
            tool_names |= SANDBOX_TOOL_NAMES
        loop = AgentLoop(
            adapter,
            self.registry,
            agent_name=config.name,
            max_iterations=min(config.max_iterations, self.max_llm_calls_per_run),
        )
        loop_result = await loop.run(
            messages,
            tool_names=tool_names,
            read_only=True,
            max_tool_result_chars=config.max_tool_result_chars,
            full_results=full_results,
        )

        try:
            report = await generate_structured(
                adapter,
                loop_result.messages,
                schema_name="SubAgentReport",
                output_model=SubAgentReport,
                max_retries=1,
            )
            report.source = config.name
        except StructuredOutputError:
            report = SubAgentReport(
                source=config.name,
                summary=loop_result.final_content[:2000] or "no structured report",
                signals=[],
                hypotheses=[],
                confidence=0.0,
                degraded=True,
            )

        if not report.evidence:
            report.evidence = [
                EvidenceItem(
                    source=config.name,
                    summary=f"{item['tool']}: {'ok' if item['ok'] else item['error']}",
                    detail={"tool": item["tool"], "arguments": item.get("arguments", {})},
                )
                for item in full_results
            ]

        degraded = loop_result.stats.degraded or report.degraded
        transcript = [m.model_dump() for m in loop_result.messages]
        return SubAgentRunResult(
            report=report,
            transcript=transcript,
            full_tool_results=full_results,
            stats=loop_result.stats,
            degraded=degraded,
        )
