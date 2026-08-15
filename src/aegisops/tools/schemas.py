"""Pydantic argument schemas for every AegisOps tool.

Schemas double as the JSON Schema exposed to LLM tool-calling and as the MCP
tool input schema, so there is exactly one source of truth.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class QueryMetricsArgs(BaseModel):
    service: str = Field(description="Service name from the service catalog")
    metric: str = Field(description="Metric name, e.g. latency_p99_ms, error_rate, cpu_usage")
    start: str = Field(description="ISO-8601 start time, e.g. 2026-01-15T00:00:00Z")
    end: str = Field(description="ISO-8601 end time")


class QueryLogsArgs(BaseModel):
    service: str
    start: str
    end: str
    level: str | None = Field(default=None, description="Filter by level, e.g. ERROR")
    pattern: str | None = Field(default=None, description="Case-insensitive substring filter")
    limit: int = Field(default=100, ge=1, le=500)


class GetServiceHealthArgs(BaseModel):
    service: str


class GetServiceTopologyArgs(BaseModel):
    service: str | None = Field(default=None, description="Optional center service")


class GetRecentDeploymentsArgs(BaseModel):
    service: str
    limit: int = Field(default=10, ge=1, le=50)


class GetConfigDiffArgs(BaseModel):
    service: str
    from_version: str | None = Field(default=None)
    to_version: str | None = Field(default=None)


class GetIncidentHistoryArgs(BaseModel):
    service: str
    limit: int = Field(default=10, ge=1, le=50)


class GetCurrentReleaseArgs(BaseModel):
    service: str


class GetServiceCatalogArgs(BaseModel):
    service: str | None = Field(default=None)


class VerifyServiceHealthArgs(BaseModel):
    service: str


class CreateIncidentTicketArgs(BaseModel):
    service: str
    title: str
    severity: str = Field(description="P0/P1/P2/P3")
    description: str


class RestartServiceArgs(BaseModel):
    service: str
    reason: str = Field(description="Required justification for the production change")


class RollbackReleaseArgs(BaseModel):
    service: str
    to_version: str = Field(description="Target release to roll back to")
    reason: str = Field(description="Required justification for the production change")


class ScaleServiceArgs(BaseModel):
    service: str
    replicas: int = Field(ge=0, le=100)
    reason: str = Field(description="Required justification for the production change")


class ApplyConfigChangeArgs(BaseModel):
    service: str
    key: str
    value: str
    reason: str = Field(description="Required justification for the production change")
