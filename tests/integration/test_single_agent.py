"""Single-agent LangGraph integration tests with FakeLLM (no network)."""

from __future__ import annotations

from pathlib import Path

import pytest
from langgraph.checkpoint.memory import InMemorySaver

from cloudops_harness.agents.single import build_single_agent_graph
from cloudops_harness.config.settings import Settings
from cloudops_harness.llm.fake import FakeLLM, ScriptedTurn
from cloudops_harness.providers.mock import MockOpsProvider
from cloudops_harness.tools.registry import ToolRegistry

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def make_registry() -> ToolRegistry:
    settings = Settings(_env_file=None, environment="test", tool_timeout_seconds=5.0)
    return ToolRegistry(MockOpsProvider(fixtures_dir=PROJECT_ROOT / "fixtures"), settings)


@pytest.mark.asyncio
async def test_single_agent_health_check_flow() -> None:
    llm = FakeLLM(
        script=[
            ScriptedTurn(
                match="check payment",
                tool_call_name="get_service_health",
                tool_call_args={"service": "payment-service"},
            ),
            ScriptedTurn(match="healthy", content="payment-service is healthy"),
        ]
    )
    graph = build_single_agent_graph(llm, make_registry(), checkpointer=InMemorySaver())
    result = await graph.ainvoke(
        {"messages": [{"role": "user", "content": "please check payment-service"}]},
        config={"configurable": {"thread_id": "t-single-1"}},
    )
    assert result["final_output"] == "payment-service is healthy"
    assert result["status"] == "done"


@pytest.mark.asyncio
async def test_single_agent_follows_multiple_tools() -> None:
    llm = FakeLLM(
        script=[
            ScriptedTurn(
                match="metrics",
                tool_call_name="query_metrics",
                tool_call_args={
                    "service": "order-service",
                    "metric": "error_rate",
                    "start": "2026-01-01T00:00:00Z",
                    "end": "2026-01-01T01:00:00Z",
                },
            ),
            ScriptedTurn(
                match="anomalous",
                tool_call_name="query_logs",
                tool_call_args={
                    "service": "order-service",
                    "start": "2026-01-01T00:00:00Z",
                    "end": "2026-01-01T01:00:00Z",
                    "pattern": "error",
                },
            ),
            ScriptedTurn(match="order-service", content="evidence collected, order-service degraded"),
        ]
    )
    graph = build_single_agent_graph(llm, make_registry())
    result = await graph.ainvoke(
        {"messages": [{"role": "user", "content": "collect metrics and logs for order-service"}]}
    )
    assert result["final_output"].startswith("evidence collected")
    assert llm.calls[0]["tool_names"]  # agent saw the full tool surface


@pytest.mark.asyncio
async def test_single_agent_does_not_execute_dangerous_tool_without_approval() -> None:
    llm = FakeLLM(
        script=[
            ScriptedTurn(
                match="restart",
                tool_call_name="restart_service",
                tool_call_args={"service": "payment-service", "reason": "test"},
            ),
            ScriptedTurn(match="approval", content="cannot restart: approval required"),
        ]
    )
    graph = build_single_agent_graph(llm, make_registry(), approve_writes=False)
    result = await graph.ainvoke({"messages": [{"role": "user", "content": "restart payment-service"}]})
    tool_messages = [m for m in result["messages"] if m.get("role") == "tool"]
    assert tool_messages and "approval" in tool_messages[0]["content"]
