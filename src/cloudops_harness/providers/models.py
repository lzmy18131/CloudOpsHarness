"""Pydantic models shared by the ops provider layer and tool layer."""

from __future__ import annotations

from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, Field


class HealthStatus(StrEnum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    DOWN = "down"


class MetricPoint(BaseModel):
    timestamp: str
    value: float


class MetricsResult(BaseModel):
    service: str
    metric: str
    start: str
    end: str
    unit: str
    points: list[MetricPoint] = Field(default_factory=list)
    summary: dict[str, float] = Field(default_factory=dict)
    anomalous: bool = False
    anomaly_window: dict[str, str] | None = None


class LogEntry(BaseModel):
    timestamp: str
    level: str
    service: str
    message: str
    trace_id: str | None = None
    extra: dict[str, Any] = Field(default_factory=dict)


class LogsResult(BaseModel):
    service: str
    start: str
    end: str
    query: dict[str, Any] = Field(default_factory=dict)
    total: int = 0
    returned: int = 0
    truncated: bool = False
    entries: list[LogEntry] = Field(default_factory=list)
    error_patterns: list[str] = Field(default_factory=list)


class ServiceHealth(BaseModel):
    service: str
    status: HealthStatus
    checked_at: str
    message: str = ""
    metrics: dict[str, float] = Field(default_factory=dict)
    dependencies: dict[str, HealthStatus] = Field(default_factory=dict)
    recent_actions: list[str] = Field(default_factory=list)


class ServiceInfo(BaseModel):
    name: str
    owner: str
    team: str
    repository: str
    runtime: str
    tier: Literal["edge", "core", "support"]
    current_release: str
    restart_policy: str
    sla_p99_ms: int
    description: str


class TopologyEdge(BaseModel):
    source: str
    target: str
    kind: Literal["sync", "async", "db", "cache", "event"]
    weight: int = 1


class Topology(BaseModel):
    nodes: list[str]
    edges: list[TopologyEdge]

    def downstream_of(self, service: str) -> list[str]:
        return [e.target for e in self.edges if e.source == service]

    def upstream_of(self, service: str) -> list[str]:
        return [e.source for e in self.edges if e.target == service]


class DeploymentRecord(BaseModel):
    id: str
    service: str
    version: str
    previous_version: str | None = None
    deployed_at: str
    operator: str
    trigger: str
    status: str = "succeeded"
    diff_id: str
    notes: str = ""


class ConfigChange(BaseModel):
    id: str
    service: str
    path: str
    before: str
    after: str
    applied_at: str
    deployment_id: str | None = None
    operator: str
    summary: str


class ConfigDiffResult(BaseModel):
    service: str
    from_version: str
    to_version: str
    changes: list[ConfigChange] = Field(default_factory=list)
    summary: str = ""


class HistoricalIncident(BaseModel):
    id: str
    service: str
    title: str
    fault_type: str
    root_cause: str
    severity: str
    occurred_at: str
    resolved_at: str
    lesson: str


class IncidentTicket(BaseModel):
    id: str
    service: str
    title: str
    severity: str
    status: str = "open"
    created_at: str


class DryRunResult(BaseModel):
    action: str
    target: str
    environment: str = "prod"
    valid: bool = True
    planned_change: str
    before_state: dict[str, Any] = Field(default_factory=dict)
    expected_result: str
    rollback_method: str
    risk_level: int = 0


class ActionResult(BaseModel):
    ok: bool
    action: str
    target: str
    message: str
    detail: dict[str, Any] = Field(default_factory=dict)


class FaultInjection(BaseModel):
    """Test/demo hooks to deliberately break provider behavior."""

    fail_next: dict[str, int] = Field(default_factory=dict)
    timeout_tools: set[str] = Field(default_factory=set)
    unavailable: bool = False
    health_overrides: dict[str, HealthStatus] = Field(default_factory=dict)
    sandbox_backend_down: bool = False
