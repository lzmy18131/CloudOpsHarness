"""End-to-end main-agent integration tests with the deterministic FakeLLM."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from aegisops.agents.runtime import AegisRuntime
from aegisops.config.settings import Settings

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def make_scenario() -> dict[str, Any]:
    return {
        "incident_id": "INC-INT-001",
        "service": "payment-service",
        "title": "payment-service P99 latency spike after v2.4.0 deployment",
        "fault_type": "bad-deployment",
        "severity": "P1",
        "anomaly_start": "2026-01-15T00:00:00Z",
        "anomaly_end": "2026-01-15T01:00:00Z",
        "root_cause": "release v2.4.0 introduced a synchronous retry loop in the checkout handler",
        "relevant_metrics": ["latency_p99_ms", "error_rate"],
        "relevant_logs": ["timeout after release"],
        "relevant_changes": ["DEP-INT-900"],
        "expected_tools": [
            "query_metrics",
            "query_logs",
            "get_service_health",
            "get_recent_deployments",
            "get_config_diff",
            "verify_service_health",
        ],
        "recommended_action": "rollback payment-service v2.4.0 -> v2.3.0",
        "dangerous_action": True,
        "fix_action": "rollback_release",
        "safe_alternative": "open an incident ticket; drain traffic; do not restart in place",
        "diagnostics": ["verify_service_health"],
        "subagent_tools": {
            "observability": [
                "query_metrics",
                "get_service_health",
                "get_service_topology",
                "verify_service_health",
            ],
            "log-analysis": ["query_logs", "get_service_health"],
            "change-analysis": ["get_recent_deployments", "get_config_diff", "get_current_release"],
            "remediation": ["verify_service_health", "get_service_health"],
        },
        "metric_specs": [
            {
                "metric": "latency_p99_ms",
                "unit": "ms",
                "baseline": 120,
                "anomaly_min": 800,
                "anomaly_max": 1800,
                "shape": "step",
            }
        ],
        "log_specs": [
            {
                "level": "ERROR",
                "message": "checkout handler timeout after release v2.4.0",
                "pattern": "timeout after release",
                "count": 6,
            }
        ],
        "changes": [
            {
                "id": "DEP-INT-900",
                "kind": "deployment",
                "service": "payment-service",
                "from_version": "v2.3.0",
                "to_version": "v2.4.0",
                "applied_at": "2026-01-15T00:00:00Z",
                "operator": "release-bot",
                "trigger": "pipeline",
                "summary": "checkout retry refactor",
            }
        ],
        "remediation": {
            "tool_name": "rollback_release",
            "arguments": {
                "service": "payment-service",
                "to_version": "v2.3.0",
                "reason": "v2.4.0 checkout retry loop caused P99 latency spike",
            },
            "risk_level": 3,
            "reason": "v2.4.0 checkout retry loop caused P99 latency spike",
            "target_environment": "prod",
            "expected_impact": "P99 latency returns to baseline",
        },
    }


@pytest.fixture()
def runtime(tmp_path) -> AegisRuntime:
    settings = Settings(
        _env_file=None,
        environment="test",
        data_dir=tmp_path / "data",
        fixtures_dir=PROJECT_ROOT / "fixtures",
        skills_dir=PROJECT_ROOT / "skills",
    )
    runtime = AegisRuntime(settings)
    scenario = make_scenario()
    runtime.scenario_index = {scenario["incident_id"]: scenario}
    return runtime


def graph_for(runtime):
    return runtime.build_graph(checkpointer=InMemorySaver())


@pytest.mark.asyncio
async def test_full_approval_flow_end_to_end(runtime) -> None:
    graph = graph_for(runtime)
    config = {"configurable": {"thread_id": "thread-approve"}}
    first = await graph.ainvoke(
        {
            "messages": [
                {"role": "user", "content": "payment-service 昨晚发布新版本后 P99 延迟暴涨，帮我排查"}
            ]
        },
        config=config,
    )
    assert first["pending_interrupt"]["type"] == "approval"
    assert first["pending_interrupt"]["action_requests"][0]["tool_name"] == "rollback_release"
    assert first["remediation_plan"]["requires_approval"] is True

    final = await graph.ainvoke(
        Command(resume={"decisions": [{"type": "approve", "tool_name": "rollback_release"}]}),
        config=config,
    )
    assert final["status"] == "done"
    assert "Incident Report" in final["final_report"]
    assert final["executed_actions"][0]["tool_name"] == "rollback_release"
    assert runtime.base_provider.action_log[-1]["action"] == "rollback_release"
    assert runtime.base_provider.current_releases["payment-service"] == "v2.3.0"

    # Context isolation: raw logs stay in the transcript, never in main messages.
    raw_messages = json.dumps(final["messages"], ensure_ascii=False)
    assert "checkout handler timeout after release" not in raw_messages
    log_transcript = json.dumps(final["transcripts"]["log-analysis"], ensure_ascii=False)
    assert "checkout handler timeout after release" in log_transcript
    # All four subagents produced structured reports.
    assert set(final["subagent_reports"]) == {
        "observability",
        "log-analysis",
        "change-analysis",
        "remediation",
    }
    # Change agent separates temporal correlation from causal evidence.
    change_report = final["subagent_reports"]["change-analysis"]
    assert change_report.get("temporal_correlation") is True
    assert change_report.get("causal_confidence", 1.0) < 0.6
    # Evidence is traceable back to tool results; RCA references evidence ids.
    for item in final["evidence"]:
        assert item.get("id")
        assert item.get("raw_ref")
    assert final["rca"].get("supporting_evidence")


@pytest.mark.asyncio
async def test_rejection_flow_records_decision_and_safe_alternative(runtime) -> None:
    graph = graph_for(runtime)
    config = {"configurable": {"thread_id": "thread-reject"}}
    first = await graph.ainvoke(
        {"messages": [{"role": "user", "content": "payment-service 发布后延迟暴涨，请排查"}]},
        config=config,
    )
    assert first["pending_interrupt"]["type"] == "approval"

    final = await graph.ainvoke(
        Command(
            resume={"decisions": [{"type": "reject", "tool_name": "rollback_release", "comment": "别动生产"}]}
        ),
        config=config,
    )
    assert final["status"] == "done"
    assert final["rejected_actions"][0]["decision"] == "reject"
    assert final["executed_actions"] == []
    assert "Rejected Actions" in final["final_report"]
    assert "safe alternative" in final["final_report"].lower() or "drain traffic" in final["final_report"]
    assert runtime.base_provider.action_log == []


@pytest.mark.asyncio
async def test_missing_info_interrupt_then_resume_with_supplement(runtime) -> None:
    graph = graph_for(runtime)
    config = {"configurable": {"thread_id": "thread-missing"}}
    first = await graph.ainvoke(
        {"messages": [{"role": "user", "content": "帮我查一下故障"}]},
        config=config,
    )
    assert first["pending_interrupt"]["type"] == "missing_info"
    assert first["status"] == "awaiting_info"

    second = await graph.ainvoke(
        Command(resume={"supplement": "payment-service 昨晚发布新版本后延迟暴涨"}),
        config=config,
    )
    assert second["pending_interrupt"]["type"] == "approval"
    assert second["service"] == "payment-service"
