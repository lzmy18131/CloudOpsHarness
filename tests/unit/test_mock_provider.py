"""MockOpsProvider tests: fixtures, telemetry synthesis, scenarios, injection."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from aegisops.providers.mock import MockOpsProvider
from aegisops.providers.models import HealthStatus
from aegisops.providers.protocol import (
    OpsProviderError,
    ProviderUnavailable,
    ToolTimeoutError,
    UnknownServiceError,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def make_scenario(**overrides: Any) -> dict[str, Any]:
    scenario = {
        "incident_id": "INC-TEST-001",
        "service": "payment-service",
        "fault_type": "bad-deployment",
        "severity": "P1",
        "title": "payment-service latency spike after deployment",
        "anomaly_start": "2026-01-15T00:00:00Z",
        "anomaly_end": "2026-01-15T01:00:00Z",
        "fix_action": "rollback_release",
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
                "id": "DEP-TEST-900",
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
    }
    scenario.update(overrides)
    return scenario


@pytest.fixture()
def provider() -> MockOpsProvider:
    return MockOpsProvider(fixtures_dir=PROJECT_ROOT / "fixtures")


@pytest.mark.asyncio
async def test_catalog_and_topology_load(provider) -> None:
    catalog = await provider.get_service_catalog()
    assert len(catalog) == 6
    assert "payment-service" in {s.name for s in catalog}
    topology = await provider.get_service_topology()
    assert "mysql-primary" in topology.nodes
    assert any(e.source == "order-service" and e.target == "payment-service" for e in topology.edges)


@pytest.mark.asyncio
async def test_query_metrics_baseline_and_shape(provider) -> None:
    result = await provider.query_metrics(
        "payment-service", "latency_p99_ms", "2026-01-14T00:00:00Z", "2026-01-14T01:00:00Z"
    )
    assert len(result.points) == 61
    assert result.anomalous is False
    assert "p99" in result.summary

    provider.activate_scenario(make_scenario())
    anomalous = await provider.query_metrics(
        "payment-service", "latency_p99_ms", "2026-01-15T00:00:00Z", "2026-01-15T01:00:00Z"
    )
    assert anomalous.anomalous is True
    assert anomalous.anomaly_window == {
        "start": "2026-01-15T00:00:00Z",
        "end": "2026-01-15T01:00:00Z",
    }
    assert anomalous.summary["max"] >= 1700


@pytest.mark.asyncio
async def test_query_logs_pattern_and_scenario_evidence(provider) -> None:
    provider.activate_scenario(make_scenario())
    result = await provider.query_logs(
        "payment-service",
        "2026-01-15T00:00:00Z",
        "2026-01-15T01:00:00Z",
        pattern="timeout after release",
        limit=10,
    )
    assert result.total >= 6
    assert all("timeout after release" in e.message for e in result.entries)
    assert "timeout after release" in result.error_patterns


@pytest.mark.asyncio
async def test_health_reflects_active_scenario(provider) -> None:
    health = await provider.get_service_health("payment-service")
    assert health.status == HealthStatus.HEALTHY
    provider.activate_scenario(make_scenario())
    degraded = await provider.get_service_health("payment-service")
    assert degraded.status == HealthStatus.DEGRADED


@pytest.mark.asyncio
async def test_deployments_merge_scenario_change(provider) -> None:
    provider.activate_scenario(make_scenario())
    records = await provider.get_recent_deployments("payment-service")
    assert records[0].id == "DEP-TEST-900"
    assert records[0].version == "v2.4.0"


@pytest.mark.asyncio
async def test_config_diff_between_releases(provider) -> None:
    diff = await provider.get_config_diff("payment-service", "v2.2.2", "v2.3.0")
    assert diff.from_version == "v2.2.2"
    assert diff.to_version == "v2.3.0"
    assert any(c.id == "CFG-4001" for c in diff.changes)


@pytest.mark.asyncio
async def test_rollback_updates_release_and_resolves_scenario(provider) -> None:
    provider.activate_scenario(make_scenario())
    assert await provider.get_current_release("payment-service") == "v2.3.0"
    result = await provider.rollback_release("payment-service", "v2.3.0", "bad latency after deploy")
    assert result.ok is True
    assert len(provider.action_log) == 1
    assert provider.resolved_scenarios == {"INC-TEST-001"}
    health = await provider.get_service_health("payment-service")
    assert health.status == HealthStatus.HEALTHY


@pytest.mark.asyncio
async def test_write_actions_record_state(provider) -> None:
    ticket = await provider.create_incident_ticket(
        "order-service", "checkout timeout", "P1", "users cannot complete checkout"
    )
    assert ticket.id.startswith("INC-")
    scaled = await provider.scale_service("order-service", 12, "traffic spike")
    assert scaled.detail["before_replicas"] == 6
    assert provider.replicas["order-service"] == 12


@pytest.mark.asyncio
async def test_unknown_service_raises(provider) -> None:
    with pytest.raises(UnknownServiceError):
        await provider.get_service_health("billing-service")


@pytest.mark.asyncio
async def test_fault_injection_fail_then_recover(provider) -> None:
    provider.fault_injection.fail_next["query_metrics"] = 1
    with pytest.raises(OpsProviderError):
        await provider.query_metrics(
            "payment-service", "cpu_usage", "2026-01-01T00:00:00Z", "2026-01-01T01:00:00Z"
        )
    result = await provider.query_metrics(
        "payment-service", "cpu_usage", "2026-01-01T00:00:00Z", "2026-01-01T01:00:00Z"
    )
    assert result.metric == "cpu_usage"


@pytest.mark.asyncio
async def test_fault_injection_timeout_and_unavailable(provider) -> None:
    provider.fault_injection.timeout_tools.add("query_logs")
    with pytest.raises(ToolTimeoutError):
        await provider.query_logs("payment-service", "2026-01-01T00:00:00Z", "2026-01-01T01:00:00Z")
    provider.fault_injection.unavailable = True
    with pytest.raises(ProviderUnavailable):
        await provider.get_service_health("payment-service")
