"""Unit tests for planning and context compression."""

from __future__ import annotations

from cloudops_harness.agents.context import (
    ContextCompressor,
    assemble_main_messages,
    compress_main_context,
    evidence_block,
)
from cloudops_harness.agents.planner import PLAN_TEMPLATE, build_default_plan
from cloudops_harness.llm.models import LLMMessage


def test_default_plan_has_thirteen_steps() -> None:
    plan = build_default_plan()
    assert len(plan.steps) == 13
    assert plan.steps[0].id == "triage"
    assert plan.steps[-1].id == "report"
    assert len(PLAN_TEMPLATE) == 13


def test_evidence_block_renders_reports_not_transcripts() -> None:
    state = {
        "subagent_reports": {
            "log-analysis": {
                "summary": "pool exhaustion pattern",
                "signals": ["db_pool_wait_ms"],
                "hypotheses": ["db pool exhausted"],
                "confidence": 0.9,
            }
        },
        "transcripts": {"log-analysis": {"messages": [{"role": "tool", "content": "RAW_LOG_SECRET"}]}},
        "plan": [{"id": "triage", "status": "completed"}],
        "rca": {"root_cause": "db pool", "confidence": 0.8},
    }
    block = evidence_block(state)
    assert "pool exhaustion" in block
    assert "RAW_LOG_SECRET" not in block


def test_assemble_main_messages_excludes_raw_transcripts() -> None:
    state = {
        "user_id": "user-a",
        "service": "payment-service",
        "environment": "prod",
        "time_range_start": "t0",
        "time_range_end": "t1",
        "subagent_reports": {},
        "plan": [{"id": "triage", "status": "completed"}],
        "transcripts": {"log-analysis": {"messages": [{"role": "tool", "content": "RAW_LOG_LINE_42"}]}},
        "messages": [{"role": "user", "content": "debug payment"}],
    }
    messages = assemble_main_messages(state)
    joined = "\n".join(m.content for m in messages)
    assert "RAW_LOG_LINE_42" not in joined
    assert "user_id: user-a" in joined


def test_compressor_offloads_old_turns_and_keeps_tail() -> None:
    compressor = ContextCompressor(threshold_tokens=50, keep_last=2)
    messages = [
        LLMMessage(role="system", content="sys"),
        LLMMessage(role="user", content="x" * 300),
        LLMMessage(role="assistant", content="y" * 300),
        LLMMessage(role="user", content="keep me recent"),
        LLMMessage(role="assistant", content="recent answer"),
    ]
    compressed, offloaded = compressor.compress(messages)
    assert len(offloaded) == 2
    assert compressed[-1].content == "recent answer"
    assert "[compressed history]" in compressed[1].content
    assert any(m.role == "system" for m in compressed)


def test_compressor_noop_below_threshold() -> None:
    compressor = ContextCompressor(threshold_tokens=100000, keep_last=2)
    messages = [LLMMessage(role="user", content="short")]
    compressed, offloaded = compressor.compress(messages)
    assert offloaded == []
    assert compressed == messages


def test_compress_main_context_preserves_evidence_and_reduces_tokens() -> None:
    messages = [
        LLMMessage(role="system", content="trusted system instructions"),
        LLMMessage(role="user", content="Evidence so far:\ncritical-error-code-500-config-value-42"),
        *[LLMMessage(role="user", content=f"old turn {i} " + "x" * 400) for i in range(10)],
        LLMMessage(role="assistant", content="recent answer"),
    ]
    compressed, stats = compress_main_context(messages, threshold_tokens=600, keep_last=2)
    assert stats["compressed"] is True
    assert stats["tokens_after"] < stats["tokens_before"]
    assert stats["offloaded_turns"] > 0
    joined = "\n".join(m.content for m in compressed)
    assert "critical-error-code-500-config-value-42" in joined  # evidence preserved
    assert "recent answer" in joined  # tail preserved
