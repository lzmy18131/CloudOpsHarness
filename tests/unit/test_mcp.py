"""MCP boundary tests: FastMCP server + in-process OpsProvider adapter."""

from __future__ import annotations

from pathlib import Path

import pytest

from cloudops_harness.mcp.client import MCPToolAdapter
from cloudops_harness.mcp.server import CloudOpsMcpServer, McpToolError
from cloudops_harness.providers.mock import MockOpsProvider

PROJECT_ROOT = Path(__file__).resolve().parents[2]

REQUIRED_MCP_TOOLS = {
    "query_metrics",
    "query_logs",
    "get_service_health",
    "get_service_topology",
    "get_recent_deployments",
    "get_config_diff",
    "get_incident_history",
    "get_current_release",
    "verify_service_health",
    "create_incident_ticket",
    "restart_service",
    "rollback_release",
    "scale_service",
    "apply_config_change",
    "get_service_catalog",
}


@pytest.fixture()
def server() -> CloudOpsMcpServer:
    return CloudOpsMcpServer(provider=MockOpsProvider(fixtures_dir=PROJECT_ROOT / "fixtures"))


@pytest.fixture()
def adapter(server) -> MCPToolAdapter:
    return MCPToolAdapter(server=server)


@pytest.mark.asyncio
async def test_mcp_exposes_all_required_tools(server) -> None:
    tools = await server.list_tools()
    assert REQUIRED_MCP_TOOLS <= set(tools)


@pytest.mark.asyncio
async def test_mcp_tool_call_returns_structured_content(server) -> None:
    result = await server.call_tool(
        "query_metrics",
        {
            "service": "payment-service",
            "metric": "latency_p99_ms",
            "start": "2026-01-01T00:00:00Z",
            "end": "2026-01-01T01:00:00Z",
        },
    )
    assert result["metric"] == "latency_p99_ms"
    assert len(result["points"]) == 61


@pytest.mark.asyncio
async def test_adapter_implements_ops_provider_through_mcp(adapter) -> None:
    catalog = await adapter.get_service_catalog()
    assert len(catalog) == 10
    release = await adapter.get_current_release("order-service")
    assert release == "v7.4.2"
    health = await adapter.get_service_health("user-service")
    assert health.status.value == "healthy"


@pytest.mark.asyncio
async def test_adapter_write_action_round_trip(adapter, server) -> None:
    ticket = await adapter.create_incident_ticket("order-service", "checkout down", "P1", "users blocked")
    assert ticket.id.startswith("INC-")
    provider: MockOpsProvider = server.provider  # type: ignore[assignment]
    assert provider.action_log[-1]["action"] == "create_incident_ticket"


@pytest.mark.asyncio
async def test_mcp_error_propagates(server) -> None:
    server.provider.fault_injection.unavailable = True  # type: ignore[union-attr]
    with pytest.raises(McpToolError):
        await server.call_tool("get_service_health", {"service": "payment-service"})
