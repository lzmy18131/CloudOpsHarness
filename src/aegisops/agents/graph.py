"""LangGraph wiring for the AegisOps Incident Response workflow."""

from __future__ import annotations

from typing import Any

from langgraph.graph import END, START, StateGraph

from aegisops.agents.nodes import (
    build_advance_node,
    build_executor_node,
    build_pause_node,
    build_planner_node,
    build_prepare_node,
    build_report_node,
    build_subagent_node,
    build_synthesize_node,
    build_verify_node,
    dispatch_for_step,
)
from aegisops.agents.runtime import AegisRuntime
from aegisops.agents.state import IncidentState


def build_incident_graph(runtime: AegisRuntime, checkpointer: Any = None) -> Any:
    """Compile the full harness graph."""
    graph = StateGraph(IncidentState)

    graph.add_node("prepare", build_prepare_node(runtime))
    graph.add_node("pause", build_pause_node(runtime))
    graph.add_node("planner", build_planner_node(runtime))
    graph.add_node("advance", build_advance_node(runtime))
    graph.add_node("subagent_observability", build_subagent_node(runtime, "observability"))
    graph.add_node("subagent_log_analysis", build_subagent_node(runtime, "log-analysis"))
    graph.add_node("subagent_change_analysis", build_subagent_node(runtime, "change-analysis"))
    graph.add_node("subagent_remediation", build_subagent_node(runtime, "remediation"))
    graph.add_node("synthesize", build_synthesize_node(runtime))
    graph.add_node("executor", build_executor_node(runtime))
    graph.add_node("verify", build_verify_node(runtime))
    graph.add_node("report", build_report_node(runtime))

    graph.add_edge(START, "prepare")

    def route_after_prepare(state: IncidentState) -> str:
        if state.get("pending_interrupt"):
            return "pause"
        return "planner"

    graph.add_conditional_edges("prepare", route_after_prepare, {"pause": "pause", "planner": "planner"})

    def route_after_pause(state: IncidentState) -> str:
        return "prepare" if state.get("status") == "info_resolved" else "executor"

    graph.add_conditional_edges("pause", route_after_pause, {"prepare": "prepare", "executor": "executor"})

    def route_after_planner(state: IncidentState) -> str:
        plan = state.get("plan", [])
        if not plan:
            return END
        index = int(state.get("current_step_index", 0))
        if state.get("status") == "partial_limit":
            # Plan budget exhausted: still emit a partial incident report.
            return "report"
        return dispatch_for_step(plan[index]) if index < len(plan) else END

    graph.add_conditional_edges("planner", route_after_planner)
    graph.add_conditional_edges("advance", route_after_planner)

    graph.add_edge("subagent_observability", "advance")
    graph.add_edge("subagent_log_analysis", "advance")
    graph.add_edge("subagent_change_analysis", "advance")
    graph.add_edge("subagent_remediation", "advance")
    graph.add_edge("synthesize", "advance")

    def route_after_executor(state: IncidentState) -> str:
        return "pause" if state.get("pending_interrupt") else "advance"

    graph.add_conditional_edges("executor", route_after_executor, {"pause": "pause", "advance": "advance"})
    graph.add_edge("verify", "advance")
    graph.add_edge("report", END)

    return graph.compile(checkpointer=checkpointer)
