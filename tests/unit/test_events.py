"""Unified SSE event envelope tests."""

from __future__ import annotations

from cloudops_harness.agents.events import make_event, next_sequence, reset_sequence
from cloudops_harness.runtime_context import current_run_id, current_thread_id


def test_event_envelope_has_required_fields() -> None:
    reset_sequence()
    current_run_id.set("run-1")
    current_thread_id.set("thread-1")
    event = make_event("tool_start", tool_name="query_metrics", source="observability")
    assert event["event_type"] == "tool_start"
    assert event["type"] == "tool_start"
    assert event["run_id"] == "run-1"
    assert event["thread_id"] == "thread-1"
    assert event["source"] == "observability"
    assert event["tool_name"] == "query_metrics"
    assert event["timestamp"]
    assert event["sequence"] == 1


def test_sequence_is_monotonic_and_resettable() -> None:
    reset_sequence()
    assert next_sequence() == 1
    assert next_sequence() == 2
    reset_sequence()
    assert make_event("agent_start")["sequence"] == 1


def test_source_defaults_to_main() -> None:
    reset_sequence()
    assert make_event("plan")["source"] == "main"
