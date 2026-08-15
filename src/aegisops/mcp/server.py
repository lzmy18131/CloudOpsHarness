"""FastMCP server exposing every OpsProvider operation as an MCP tool.

The same server powers two transports:
* in-process: ``MCPToolAdapter`` calls ``AegisMcpServer.call_tool`` directly
  (default for the FastAPI app and tests).
* stdio: ``python -m aegisops.mcp.server`` (standalone deployment; point it at
  the fixtures dir with ``AEGIS_FIXTURES_DIR``).
"""

from __future__ import annotations

import argparse
from typing import Any

from fastmcp import FastMCP

from aegisops.providers.mock import MockOpsProvider
from aegisops.providers.protocol import OpsProvider


class McpToolError(RuntimeError):
    """Raised when an MCP tool invocation reports an error."""


def _dump(model: Any) -> dict[str, Any]:
    return model.model_dump(mode="json") if hasattr(model, "model_dump") else {"result": model}


def create_mcp_server(provider: OpsProvider | None = None) -> FastMCP:
    """Build a FastMCP server backed by an OpsProvider."""
    provider = provider or MockOpsProvider()
    mcp = FastMCP(
        name="aegisops-ops",
        instructions="AegisOps operations tools (metrics, logs, topology, releases, remediation actions).",
    )

    @mcp.tool()
    async def query_metrics(service: str, metric: str, start: str, end: str) -> dict:
        """Query time-series metrics for a service and time window."""
        return _dump(await provider.query_metrics(service, metric, start, end))

    @mcp.tool()
    async def query_logs(
        service: str,
        start: str,
        end: str,
        level: str | None = None,
        pattern: str | None = None,
        limit: int = 100,
    ) -> dict:
        """Query structured logs with optional level and substring filters."""
        return _dump(await provider.query_logs(service, start, end, level, pattern, limit))

    @mcp.tool()
    async def get_service_health(service: str) -> dict:
        """Get current health status and key metrics of a service."""
        return _dump(await provider.get_service_health(service))

    @mcp.tool()
    async def get_service_topology(service: str | None = None) -> dict:
        """Get the service dependency topology, optionally centered on one service."""
        return _dump(await provider.get_service_topology(service))

    @mcp.tool()
    async def get_recent_deployments(service: str, limit: int = 10) -> dict:
        """List recent deployments for a service."""
        return _dump(
            [d.model_dump(mode="json") for d in await provider.get_recent_deployments(service, limit)]
        )

    @mcp.tool()
    async def get_config_diff(
        service: str, from_version: str | None = None, to_version: str | None = None
    ) -> dict:
        """Show configuration changes between two releases."""
        return _dump(await provider.get_config_diff(service, from_version, to_version))

    @mcp.tool()
    async def get_incident_history(service: str, limit: int = 10) -> dict:
        """Return historical incidents and lessons learned for a service."""
        return _dump([i.model_dump(mode="json") for i in await provider.get_incident_history(service, limit)])

    @mcp.tool()
    async def get_current_release(service: str) -> dict:
        """Return the currently active release of a service."""
        return _dump({"service": service, "release": await provider.get_current_release(service)})

    @mcp.tool()
    async def get_service_catalog(service: str | None = None) -> dict:
        """Return service catalog entries (owner, repo, SLO, restart policy)."""
        return _dump([s.model_dump(mode="json") for s in await provider.get_service_catalog(service)])

    @mcp.tool()
    async def verify_service_health(service: str) -> dict:
        """Re-check a service after remediation and report whether it recovered."""
        return _dump(await provider.verify_service_health(service))

    @mcp.tool()
    async def create_incident_ticket(service: str, title: str, severity: str, description: str) -> dict:
        """Create an incident ticket (low-risk write)."""
        return _dump(await provider.create_incident_ticket(service, title, severity, description))

    @mcp.tool()
    async def restart_service(service: str, reason: str) -> dict:
        """Restart a production service. HITL approval required by AegisOps risk policy."""
        return _dump(await provider.restart_service(service, reason))

    @mcp.tool()
    async def rollback_release(service: str, to_version: str, reason: str) -> dict:
        """Roll a service back to a previous release. HITL approval required."""
        return _dump(await provider.rollback_release(service, to_version, reason))

    @mcp.tool()
    async def scale_service(service: str, replicas: int, reason: str) -> dict:
        """Change the replica count of a service. HITL approval required."""
        return _dump(await provider.scale_service(service, replicas, reason))

    @mcp.tool()
    async def apply_config_change(service: str, key: str, value: str, reason: str) -> dict:
        """Apply a configuration change to a service. HITL approval required."""
        return _dump(await provider.apply_config_change(service, key, value, reason))

    return mcp


class AegisMcpServer:
    """Thin wrapper around FastMCP with a stable programmatic API."""

    def __init__(self, provider: OpsProvider | None = None) -> None:
        self.provider = provider or MockOpsProvider()
        self.mcp = create_mcp_server(self.provider)

    async def call_tool(self, name: str, arguments: dict[str, Any] | None = None) -> Any:
        try:
            result = await self.mcp.call_tool(name, arguments or {})
        except Exception as exc:  # noqa: BLE001 - normalize every transport error at the boundary
            raise McpToolError(f"{name} failed: {exc}") from exc
        if getattr(result, "is_error", False):
            raise McpToolError(str(result))
        content = result.structured_content
        # FastMCP wraps tool return values as {"result": <value>}; unwrap it.
        if isinstance(content, dict) and set(content.keys()) == {"result"}:
            content = content["result"]
        return content

    async def list_tools(self) -> list[str]:
        try:
            tools = await self.mcp.get_tools()
        except AttributeError:
            tools = await self.mcp._list_tools()  # noqa: SLF001 - version compatibility
        return sorted(getattr(tool, "name", str(tool)) for tool in tools)


def main() -> None:
    """Standalone stdio entrypoint: python -m aegisops.mcp.server."""
    parser = argparse.ArgumentParser(description="AegisOps MCP server")
    parser.add_argument("--fixtures-dir", default=None)
    args = parser.parse_args()
    provider = MockOpsProvider(fixtures_dir=args.fixtures_dir) if args.fixtures_dir else MockOpsProvider()
    server = create_mcp_server(provider)
    server.run(transport="stdio")


if __name__ == "__main__":
    main()
