"""LangGraph state for the CloudOps Harness Incident Response graph."""

from __future__ import annotations

import operator
from typing import Annotated, Any, TypedDict


class IncidentState(TypedDict, total=False):
    """Persisted graph state (checkpointed by LangGraph).

    Context-isolation invariant: ``messages`` (the main-agent context) never
    contains raw telemetry transcripts. Raw subagent transcripts live in
    ``transcripts`` and structured summaries in ``evidence``.
    """

    messages: Annotated[list[dict[str, Any]], operator.add]
    user_id: str
    thread_id: str
    run_id: str
    user_query: str
    service: str
    environment: str
    time_range_start: str
    time_range_end: str
    scenario: dict[str, Any]
    scenario_id: str

    plan: list[dict[str, Any]]
    current_step_index: int
    delegation_depth: int
    plan_events: Annotated[list[dict[str, Any]], operator.add]

    evidence: Annotated[list[dict[str, Any]], operator.add]
    subagent_reports: dict[str, dict[str, Any]]
    transcripts: dict[str, list[dict[str, Any]]]
    subagent_stats: dict[str, dict[str, Any]]

    rca: dict[str, Any]
    remediation_plan: dict[str, Any]
    decisions: Annotated[list[dict[str, Any]], operator.add]
    executed_actions: Annotated[list[dict[str, Any]], operator.add]
    rejected_actions: Annotated[list[dict[str, Any]], operator.add]
    verification: dict[str, Any]

    pending_interrupt: dict[str, Any]
    interrupt_resume: dict[str, Any]
    final_report: str
    report_data: dict[str, Any]
    status: str
    errors: Annotated[list[str], operator.add]
    context_stats: dict[str, Any]
    compression_events: Annotated[list[dict[str, Any]], operator.add]
