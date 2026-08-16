"""MCP tool adapter: implements OpsProvider by calling the MCP boundary.

This is the default provider used by agents, so every business-system
operation crosses the MCP tool boundary even in the single-process demo.
"""

from __future__ import annotations

from typing import Any

from cloudops_harness.mcp.server import CloudOpsMcpServer
from cloudops_harness.providers.models import (
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
from cloudops_harness.providers.protocol import OpsProvider


class MCPToolAdapter(OpsProvider):
    """OpsProvider backed by an in-process FastMCP server."""

    def __init__(self, server: CloudOpsMcpServer | None = None, provider: Any = None) -> None:
        self.server = server or CloudOpsMcpServer(provider=provider)

    async def _call(self, name: str, arguments: dict[str, Any]) -> Any:
        return await self.server.call_tool(name, arguments)

    async def query_metrics(self, service: str, metric: str, start: str, end: str) -> MetricsResult:
        return MetricsResult.model_validate(
            await self._call(
                "query_metrics", {"service": service, "metric": metric, "start": start, "end": end}
            )
        )

    async def query_logs(
        self,
        service: str,
        start: str,
        end: str,
        level: str | None = None,
        pattern: str | None = None,
        limit: int = 100,
    ) -> LogsResult:
        return LogsResult.model_validate(
            await self._call(
                "query_logs",
                {
                    "service": service,
                    "start": start,
                    "end": end,
                    "level": level,
                    "pattern": pattern,
                    "limit": limit,
                },
            )
        )

    async def get_service_health(self, service: str) -> ServiceHealth:
        return ServiceHealth.model_validate(await self._call("get_service_health", {"service": service}))

    async def get_service_topology(self, service: str | None = None) -> Topology:
        return Topology.model_validate(await self._call("get_service_topology", {"service": service}))

    async def get_recent_deployments(self, service: str, limit: int = 10) -> list[DeploymentRecord]:
        data = await self._call("get_recent_deployments", {"service": service, "limit": limit})
        return [DeploymentRecord.model_validate(item) for item in data]

    async def get_config_diff(
        self, service: str, from_version: str | None = None, to_version: str | None = None
    ) -> ConfigDiffResult:
        return ConfigDiffResult.model_validate(
            await self._call(
                "get_config_diff",
                {"service": service, "from_version": from_version, "to_version": to_version},
            )
        )

    async def get_incident_history(self, service: str, limit: int = 10) -> list[HistoricalIncident]:
        data = await self._call("get_incident_history", {"service": service, "limit": limit})
        return [HistoricalIncident.model_validate(item) for item in data]

    async def get_current_release(self, service: str) -> str:
        data = await self._call("get_current_release", {"service": service})
        return str(data["release"])

    async def get_service_catalog(self, service: str | None = None) -> list[ServiceInfo]:
        data = await self._call("get_service_catalog", {"service": service})
        return [ServiceInfo.model_validate(item) for item in data]

    async def verify_service_health(self, service: str) -> ServiceHealth:
        return ServiceHealth.model_validate(await self._call("verify_service_health", {"service": service}))

    async def dry_run_action(self, action: str, service: str, environment: str, params: dict) -> DryRunResult:
        return DryRunResult.model_validate(
            await self._call(
                "dry_run_action",
                {"action": action, "service": service, "environment": environment, "params": params},
            )
        )

    async def create_incident_ticket(
        self, service: str, title: str, severity: str, description: str
    ) -> IncidentTicket:
        return IncidentTicket.model_validate(
            await self._call(
                "create_incident_ticket",
                {"service": service, "title": title, "severity": severity, "description": description},
            )
        )

    async def restart_service(self, service: str, reason: str) -> ActionResult:
        return ActionResult.model_validate(
            await self._call("restart_service", {"service": service, "reason": reason})
        )

    async def rollback_release(self, service: str, to_version: str, reason: str) -> ActionResult:
        return ActionResult.model_validate(
            await self._call(
                "rollback_release", {"service": service, "to_version": to_version, "reason": reason}
            )
        )

    async def scale_service(self, service: str, replicas: int, reason: str) -> ActionResult:
        return ActionResult.model_validate(
            await self._call("scale_service", {"service": service, "replicas": replicas, "reason": reason})
        )

    async def apply_config_change(self, service: str, key: str, value: str, reason: str) -> ActionResult:
        return ActionResult.model_validate(
            await self._call(
                "apply_config_change", {"service": service, "key": key, "value": value, "reason": reason}
            )
        )
