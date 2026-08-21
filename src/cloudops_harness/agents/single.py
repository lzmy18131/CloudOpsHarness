"""Single-agent baseline graph.

One agent owns every tool and reasons in one shared context. Used as the
control condition in evaluation and as the simplest possible LangGraph
deployment. It deliberately has no planning, no subagent isolation, no HITL
gate and no sandbox - those are added by the full CloudOps Harness harness.
"""

from __future__ import annotations

import operator
from typing import Annotated, Any, TypedDict

from langgraph.graph import END, START, StateGraph

from cloudops_harness.agents.models import RcaHypothesis
from cloudops_harness.llm.base import ModelAdapter, ModelCallLimitError
from cloudops_harness.llm.models import LLMMessage
from cloudops_harness.llm.structured import StructuredOutputError, generate_structured
from cloudops_harness.tools.registry import ToolApprovalRequiredError, ToolRegistry


class SingleAgentState(TypedDict, total=False):
    messages: Annotated[list[dict[str, Any]], operator.add]
    final_output: str
    status: str
    rca: dict[str, Any]
    thread_id: str
    user_id: str


def as_llm_messages(messages: list[dict[str, Any]]) -> list[LLMMessage]:
    """Convert LangGraph dict messages to LLMMessage models."""
    converted: list[LLMMessage] = []
    for item in messages:
        role = item.get("role", "user")
        if role not in {"system", "user", "assistant", "tool"}:
            continue
        converted.append(
            LLMMessage(
                role=role,
                content=str(item.get("content", "")),
                tool_call_id=item.get("tool_call_id"),
                tool_calls=item.get("tool_calls"),
            )
        )
    return converted


def dict_message(message: LLMMessage) -> dict[str, Any]:
    """Convert an LLMMessage to the LangGraph dict representation."""
    payload: dict[str, Any] = {"role": message.role, "content": message.content}
    if message.tool_call_id:
        payload["tool_call_id"] = message.tool_call_id
    if message.name:
        payload["name"] = message.name
    if message.tool_calls:
        payload["tool_calls"] = [c.model_dump() for c in message.tool_calls]
    return payload


def build_single_agent_graph(
    adapter: ModelAdapter,
    registry: ToolRegistry,
    *,
    approve_writes: bool = False,
    max_llm_calls: int = 10,
    checkpointer: Any = None,
) -> Any:
    """Build the Single-Agent LangGraph graph (async nodes, async invocation)."""

    def _system_prompt() -> str:
        return (
            "You are a single AIOps agent with full access to operations tools. "
            "Diagnose the user's incident and answer clearly. Call tools as needed."
        )

    async def agent_node(state: SingleAgentState) -> dict[str, Any]:
        messages = as_llm_messages(state["messages"])
        if not any(m.role == "system" for m in messages):
            messages.insert(0, LLMMessage(role="system", content=_system_prompt()))
        tools = registry.openai_schemas()
        turn = await adapter.generate(messages, tools=tools)
        appended = dict_message(
            LLMMessage(role="assistant", content=turn.content or "", tool_calls=turn.tool_calls or None)
        )
        if not turn.tool_calls:
            # Produce a structured RCA in the same final evaluation schema used by
            # the full Harness. This keeps Single-Agent scoring fair and prevents
            # the baseline from relying only on free-text substring fallback.
            try:
                rca = await generate_structured(
                    adapter,
                    messages,
                    schema_name="RcaHypothesis",
                    output_model=RcaHypothesis,
                    max_retries=1,
                )
                rca_dump = rca.model_dump()
            except (StructuredOutputError, ModelCallLimitError) as exc:
                rca_dump = {
                    "root_cause": turn.content or "",
                    "fault_type": "unknown",
                    "fault_category": "unknown",
                    "affected_service": "unknown",
                    "root_cause_component": "unknown",
                    "confidence": 0.0,
                    "supporting_evidence": [],
                    "unresolved": [f"structured output failed: {exc}"],
                }
            return {
                "messages": [appended],
                "final_output": turn.content or "",
                "status": "done",
                "rca": rca_dump,
            }
        return {"messages": [appended]}

    async def tools_node(state: SingleAgentState) -> dict[str, Any]:
        assistant = next((m for m in reversed(state["messages"]) if m.get("role") == "assistant"), None)
        if assistant is None:
            return {"status": "error"}
        tool_messages: list[dict[str, Any]] = []
        for call in assistant.get("tool_calls", []):
            try:
                result = await registry.call(
                    call["name"], call["arguments"], agent="single-agent", approved=approve_writes
                )
                content = result.content if result.ok else f"ERROR: {result.error}"
            except ToolApprovalRequiredError as exc:
                content = f"ERROR: {exc}"
            tool_messages.append(
                {"role": "tool", "tool_call_id": call["id"], "name": call["name"], "content": content}
            )
        return {"messages": tool_messages}

    def route_after_agent(state: SingleAgentState) -> str:
        last = next((m for m in reversed(state["messages"]) if m.get("role") == "assistant"), None)
        if last and last.get("tool_calls"):
            return "tools"
        return END

    graph = StateGraph(SingleAgentState)
    graph.add_node("agent", agent_node)
    graph.add_node("tools", tools_node)
    graph.add_edge(START, "agent")
    graph.add_conditional_edges("agent", route_after_agent, {"tools": "tools", END: END})
    graph.add_edge("tools", "agent")
    return graph.compile(checkpointer=checkpointer)
