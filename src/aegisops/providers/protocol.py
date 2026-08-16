"""OpsProvider protocol: the single adapter boundary for all operations data.

Production integrations (Prometheus / Loki / Elasticsearch / Kubernetes /
GitHub / Grafana / cloud APIs) implement this protocol; the MVP ships
``MockOpsProvider`` which satisfies it deterministically on a laptop.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from aegisops.providers.models import (
    ActionResult,
    ConfigDiffResult,
    DeploymentRecord,
    DryRunResult,
    HistoricalIncident,
    IncidentTicket,
    LogsResult,
    MetricsResult,
    ServiceHealth,
    ServiceInfo,
    Topology,
)


class OpsProviderError(RuntimeError):
    """Base error for provider failures."""


class ProviderUnavailable(OpsProviderError):
    """The whole backend (e.g. MCP gateway) is unreachable."""


class ToolTimeoutError(OpsProviderError):
    """A provider call exceeded its deadline."""


class UnknownServiceError(OpsProviderError):
    """Requested service is not in the service catalog."""


class OpsProvider(ABC):
    """Read/write contract between AegisOps agents and the operations world."""

    # ---- read-only (Risk Level 0) -------------------------------------
    @abstractmethod
    async def query_metrics(self, service: str, metric: str, start: str, end: str) -> MetricsResult: ...

    @abstractmethod
    async def query_logs(
        self,
        service: str,
        start: str,
        end: str,
        level: str | None = None,
        pattern: str | None = None,
        limit: int = 100,
    ) -> LogsResult: ...

    @abstractmethod
    async def get_service_health(self, service: str) -> ServiceHealth: ...

    @abstractmethod
    async def get_service_topology(self, service: str | None = None) -> Topology: ...

    @abstractmethod
    async def get_recent_deployments(self, service: str, limit: int = 10) -> list[DeploymentRecord]: ...

    @abstractmethod
    async def get_config_diff(
        self, service: str, from_version: str | None = None, to_version: str | None = None
    ) -> ConfigDiffResult: ...

    @abstractmethod
    async def get_incident_history(self, service: str, limit: int = 10) -> list[HistoricalIncident]: ...

    @abstractmethod
    async def get_current_release(self, service: str) -> str: ...

    @abstractmethod
    async def get_service_catalog(self, service: str | None = None) -> list[ServiceInfo]: ...

    @abstractmethod
    async def verify_service_health(self, service: str) -> ServiceHealth: ...

    # ---- write / action (Risk Level 1-3) -------------------------------
    @abstractmethod
    async def dry_run_action(self, tool_name: str, arguments: dict[str, Any]) -> DryRunResult: ...

    @abstractmethod
    async def create_incident_ticket(
        self, service: str, title: str, severity: str, description: str
    ) -> IncidentTicket: ...

    @abstractmethod
    async def restart_service(self, service: str, reason: str) -> ActionResult: ...

    @abstractmethod
    async def rollback_release(self, service: str, to_version: str, reason: str) -> ActionResult: ...

    @abstractmethod
    async def scale_service(self, service: str, replicas: int, reason: str) -> ActionResult: ...

    @abstractmethod
    async def apply_config_change(self, service: str, key: str, value: str, reason: str) -> ActionResult: ...
