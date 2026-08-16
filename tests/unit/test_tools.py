"""Tests for ToolRegistry, Risk Policy and the circuit breaker."""

from __future__ import annotations

from pathlib import Path

import pytest

from aegisops.common.circuit_breaker import CircuitBreaker, CircuitOpenError
from aegisops.config.settings import Settings
from aegisops.providers.mock import MockOpsProvider
from aegisops.tools.registry import ToolApprovalRequiredError, ToolRegistry
from aegisops.tools.risk import RiskLevel, RiskPolicy

PROJECT_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture()
def registry() -> ToolRegistry:
    settings = Settings(_env_file=None, environment="test", tool_timeout_seconds=5.0)
    return ToolRegistry(MockOpsProvider(fixtures_dir=PROJECT_ROOT / "fixtures"), settings)


def test_risk_policy_levels() -> None:
    policy = RiskPolicy(auto_approve_max_risk=1)
    assert policy.risk_for("query_metrics").level == RiskLevel.READ_ONLY
    assert policy.risk_for("create_incident_ticket").level == RiskLevel.LOW_RISK_WRITE
    assert policy.risk_for("restart_service").level == RiskLevel.PRODUCTION_CHANGING
    assert policy.risk_for("rollback_release").level == RiskLevel.HIGH_RISK_DESTRUCTIVE
    assert policy.requires_hitl("restart_service") is True
    assert policy.requires_hitl("query_logs") is False
    required = policy.required_fields("rollback_release")
    assert {"reason", "target_environment", "before_state", "expected_impact"} <= required


def test_openai_schemas_read_only_subset(registry) -> None:
    schemas = registry.openai_schemas(read_only=True)
    names = {s["function"]["name"] for s in schemas}
    assert "query_metrics" in names
    assert "restart_service" not in names
    assert all("parameters" in s["function"] for s in schemas)


@pytest.mark.asyncio
async def test_read_only_tool_call_through_registry(registry) -> None:
    result = await registry.call(
        "query_metrics",
        {
            "service": "payment-service",
            "metric": "latency_p99_ms",
            "start": "2026-01-01T00:00:00Z",
            "end": "2026-01-01T01:00:00Z",
        },
    )
    assert result.ok is True
    assert result.data["metric"] == "latency_p99_ms"


@pytest.mark.asyncio
async def test_high_risk_tool_requires_approval(registry) -> None:
    with pytest.raises(ToolApprovalRequiredError):
        await registry.call("restart_service", {"service": "payment-service", "reason": "test"})
    result = await registry.call(
        "restart_service", {"service": "payment-service", "reason": "approved test"}, approved=True
    )
    assert result.ok is True
    assert registry.provider.action_log[-1]["action"] == "restart_service"


@pytest.mark.asyncio
async def test_invalid_arguments_rejected(registry) -> None:
    with pytest.raises(ValueError):
        await registry.call("query_metrics", {"service": "payment-service", "metric": "latency_p99_ms"})


@pytest.mark.asyncio
async def test_circuit_breaker_opens_after_failures() -> None:
    breaker = CircuitBreaker(name="test", failure_threshold=2, cooldown_seconds=30)
    calls = 0

    async def fail() -> None:
        nonlocal calls
        calls += 1
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError):
        await breaker.protect(fail)
    with pytest.raises(RuntimeError):
        await breaker.protect(fail)
    assert breaker.state.value == "open"
    with pytest.raises(CircuitOpenError):
        await breaker.protect(fail)
    assert calls == 2  # third call rejected before execution


@pytest.mark.asyncio
async def test_tool_registry_breaker_degrades_gracefully() -> None:
    breaker = CircuitBreaker(name="ops", failure_threshold=2, cooldown_seconds=60)
    settings = Settings(_env_file=None, environment="test", tool_timeout_seconds=5.0)
    provider = MockOpsProvider(fixtures_dir=PROJECT_ROOT / "fixtures")
    registry = ToolRegistry(provider, settings, breaker=breaker)
    provider.fault_injection.fail_next["query_metrics"] = 2
    args = {
        "service": "payment-service",
        "metric": "cpu_usage",
        "start": "2026-01-01T00:00:00Z",
        "end": "2026-01-01T01:00:00Z",
    }
    first = await registry.call("query_metrics", args)
    second = await registry.call("query_metrics", args)
    third = await registry.call("query_metrics", args)
    assert first.ok is False and second.ok is False
    assert "OPEN" in third.error
    assert breaker.state.value == "open"


def test_pii_redaction_replaces_common_shapes() -> None:
    from aegisops.tools.pii import redact_pii

    text = "contact alice@example.com or +86 138-0013-8000 with key sk-abcdef1234567890"
    out = redact_pii(text)
    assert "alice@example.com" not in out
    assert "138-0013-8000" not in out
    assert "sk-abcdef1234567890" not in out
    assert out.count("[REDACTED]") == 3


@pytest.mark.asyncio
async def test_registry_redacts_tool_content(monkeypatch) -> None:
    class _FakeResult:
        def model_dump(self, **kwargs):
            return {"entries": [{"message": "user alice@example.com failed"}]}

    async def fake_logs(self, service, start, end, level=None, pattern=None, limit=100):
        return _FakeResult()

    settings = Settings(_env_file=None, environment="test", tool_timeout_seconds=5.0)
    provider = MockOpsProvider(fixtures_dir=PROJECT_ROOT / "fixtures")
    monkeypatch.setattr(type(provider), "query_logs", fake_logs)
    registry = ToolRegistry(provider, settings)
    registry.pii_redaction = True
    result = await registry.call(
        "query_logs",
        {"service": "payment-service", "start": "2026-01-01T00:00:00Z", "end": "2026-01-01T01:00:00Z"},
    )
    assert result.ok is True
    assert "alice@example.com" not in result.content
    assert "[REDACTED]" in result.content


async def test_circuit_breaker_records_transitions() -> None:
    breaker = CircuitBreaker(name="transition-test", failure_threshold=2, cooldown_seconds=0.0)

    async def fail():
        raise RuntimeError("down")

    for _ in range(2):
        with pytest.raises(RuntimeError):
            await breaker.protect(fail)
    assert [(t["from"], t["to"]) for t in breaker.transitions] == [("closed", "open")]

    await breaker.protect(lambda: _ok())
    assert [(t["from"], t["to"]) for t in breaker.transitions] == [
        ("closed", "open"),
        ("open", "half_open"),
        ("half_open", "closed"),
    ]
    assert all("at" in t and "reason" in t for t in breaker.transitions)


async def _ok():
    return True
