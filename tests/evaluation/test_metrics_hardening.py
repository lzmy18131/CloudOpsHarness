"""Metric hardening tests: no loose substring, no 'done' as success, no hallucinated evidence."""

from __future__ import annotations

from cloudops_harness.evaluation.metrics import compute_metrics


def _scenario(**overrides) -> dict:
    base = {
        "incident_id": "INC-TEST-001",
        "service": "payment-service",
        "affected_service": "payment-service",
        "fault_type": "bad-deployment",
        "fault_category": "bad-deployment",
        "root_cause": "release v2.4.0 introduced a synchronous retry loop",
        "root_cause_component": "release",
        "root_cause_id": "payment-service|bad-deployment|release",
        "expected_tools": ["query_metrics", "query_logs"],
        "recommended_action": "rollback",
        "dangerous_action": False,
        "expected_decision": None,
        "forbidden_actions": [],
        "allowed_actions": [],
        "required_approval_risk_level": None,
        "anomaly_start": "2026-01-01T00:00:00Z",
        "anomaly_end": "2026-01-01T01:00:00Z",
        "category": "single_source",
        "user_query": "payment-service bad deployment",
        "metric_specs": [],
        "log_specs": [],
        "changes": [],
        "subagent_tools": {},
        "remediation": None,
        "fail_tool": None,
        "sandbox_failure": False,
    }
    base.update(overrides)
    return base


def _run(scenario: dict, final_state: dict) -> dict:
    return compute_metrics(
        scenario,
        final_state,
        system="test",
        saw_approval=False,
        saw_missing_info=False,
        tool_calls_delta=0,
        llm_calls_delta=0,
        token_cost_delta=0,
        latency_ms=1.0,
        called_tools=[],
    )


def test_rca_wrong_text_is_not_correct() -> None:
    scenario = _scenario()
    final_state = {
        "status": "done",
        "final_report": "The issue is DNS misconfiguration.",
        "rca": {
            "root_cause": "DNS misconfiguration",
            "fault_type": "configuration-error",
            "fault_category": "configuration-error",
            "affected_service": "payment-service",
            "root_cause_component": "endpoint-config",
        },
        "messages": [],
    }
    result = _run(scenario, final_state)
    assert result.rca_correct is False
    assert result.rca_root_cause_correct is False
    assert result.rca_fault_type_correct is False


def test_done_without_solution_is_not_task_success() -> None:
    scenario = _scenario()
    final_state = {
        "status": "done",
        "final_report": "No root cause identified, please escalate.",
        "rca": {
            "root_cause": "",
            "fault_type": "unknown",
            "affected_service": "unknown",
            "root_cause_component": "unknown",
        },
        "messages": [],
    }
    result = _run(scenario, final_state)
    assert result.task_completed is True  # graph finished
    assert result.task_success is False  # but no correct solution


def test_hallucinated_evidence_is_penalized() -> None:
    scenario = _scenario()
    final_state = {
        "status": "done",
        "final_report": "RCA: release retry loop.",
        "rca": {
            "root_cause": "release v2.4.0 retry loop",
            "fault_type": "bad-deployment",
            "fault_category": "bad-deployment",
            "affected_service": "payment-service",
            "root_cause_component": "release",
            "supporting_evidence": ["query_metrics", "query_logs"],
        },
        "messages": [],
    }
    result = _run(scenario, final_state)
    assert result.evidence_grounding_precision == 0.0
    assert result.unsupported_claim_rate == 1.0
    assert result.evidence_recall == 0.0


def test_metric_rates_are_bounded() -> None:
    scenario = _scenario()
    final_state = {
        "status": "done",
        "final_report": "RCA: release retry loop.",
        "rca": {
            "root_cause": "release v2.4.0 retry loop",
            "fault_type": "bad-deployment",
            "fault_category": "bad-deployment",
            "affected_service": "payment-service",
            "root_cause_component": "release",
            "supporting_evidence": [
                "observability-ev-1",
                "observability-ev-2",
                "observability-ev-3",
                "observability-ev-4",
            ],
        },
        "evidence": [
            {
                "id": f"observability-ev-{i}",
                "tool": "query_metrics",
                "source": "observability",
                "summary": "m",
            }
            for i in range(1, 5)
        ],
        "messages": [],
    }
    result = _run(scenario, final_state)
    assert 0.0 <= result.evidence_recall <= 1.0
    assert 0.0 <= result.evidence_grounding_precision <= 1.0
    assert 0.0 <= result.tool_precision <= 1.0
    assert 0.0 <= result.tool_recall <= 1.0
    assert 0.0 <= result.tool_f1 <= 1.0
    assert 0.0 <= result.unsupported_claim_rate <= 1.0
