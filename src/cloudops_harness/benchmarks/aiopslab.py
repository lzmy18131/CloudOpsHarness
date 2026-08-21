"""AIOpsLab adapter skeleton (Microsoft AIOpsLab).

This module is intentionally a thin adapter, not a fork of AIOpsLab. It defines
the mapping between CloudOps Harness's OpsProvider/ToolRegistry concepts and
AIOpsLab's external environment/evaluator services.

Status: **ADAPTER READY / EXTERNAL EXECUTION PENDING**.
The exact AIOpsLab HTTP/gRPC surface may differ between releases; before running
a benchmark, update the method bodies below to the installed AIOpsLab SDK.

See ``docs/AIOPSLAB_INTEGRATION.md`` for environment startup and mapping.
"""

from __future__ import annotations

from typing import Any, Protocol


class AIOpsLabEnvironment(Protocol):
    """Minimal protocol for an AIOpsLab environment service.

    The real AIOpsLab exposes an environment service that can start/stop a
    microservice workload, inject faults, and return telemetry. This protocol is
    the seam CloudOps Harness uses.
    """

    async def start(self, workload: str, fault_profile: dict[str, Any]) -> str: ...
    async def stop(self, run_id: str) -> None: ...
    async def inject_fault(self, run_id: str, fault: dict[str, Any]) -> None: ...
    async def query_metrics(self, service: str, metric: str, start: str, end: str) -> dict[str, Any]: ...
    async def query_logs(
        self, service: str, start: str, end: str, pattern: str | None = None, limit: int = 100
    ) -> dict[str, Any]: ...
    async def get_health(self, service: str) -> dict[str, Any]: ...
    async def get_topology(self) -> dict[str, Any]: ...
    async def get_changes(self, service: str) -> dict[str, Any]: ...
    async def execute_action(self, action: str, service: str, params: dict[str, Any]) -> dict[str, Any]: ...


class AIOpsLabAdapter:
    """Adapter between CloudOps Harness tools and an AIOpsLab environment.

    The adapter is deliberately provider-agnostic: it accepts any object
    implementing :class:`AIOpsLabEnvironment`, so a real AIOpsLab client or a
    local dev harness can be plugged in.
    """

    def __init__(self, environment: AIOpsLabEnvironment, *, run_id: str | None = None) -> None:
        self.environment = environment
        self.run_id = run_id
        self.action_log: list[dict[str, Any]] = []

    # ------------------------------------------------------------------ read
    async def query_metrics(self, service: str, metric: str, start: str, end: str) -> dict[str, Any]:
        return await self.environment.query_metrics(service, metric, start, end)

    async def query_logs(
        self,
        service: str,
        start: str,
        end: str,
        level: str | None = None,
        pattern: str | None = None,
        limit: int = 100,
    ) -> dict[str, Any]:
        return await self.environment.query_logs(service, start, end, pattern=pattern, limit=limit)

    async def get_service_health(self, service: str) -> dict[str, Any]:
        return await self.environment.get_health(service)

    async def get_service_topology(self, service: str | None = None) -> dict[str, Any]:
        topology = await self.environment.get_topology()
        if service is None:
            return topology
        # Keep only edges/nodes connected to the requested service.
        nodes = {service}
        edges = [
            edge
            for edge in topology.get("edges", [])
            if edge.get("source") == service or edge.get("target") == service
        ]
        for edge in edges:
            nodes.add(edge.get("source"))
            nodes.add(edge.get("target"))
        return {"nodes": sorted(nodes), "edges": edges}

    async def get_recent_deployments(self, service: str, limit: int = 10) -> list[dict[str, Any]]:
        changes = await self.environment.get_changes(service)
        deployments = [c for c in changes if c.get("kind") == "deployment"]
        return deployments[:limit]

    async def get_config_diff(
        self, service: str, from_version: str | None = None, to_version: str | None = None
    ) -> dict[str, Any]:
        changes = await self.environment.get_changes(service)
        return {"service": service, "changes": [c for c in changes if c.get("kind") == "config"]}

    # ------------------------------------------------------------------ write
    async def execute_action(self, action: str, service: str, params: dict[str, Any]) -> dict[str, Any]:
        result = await self.environment.execute_action(action, service, params)
        self.action_log.append({"action": action, "service": service, "params": params, "result": result})
        return result

    # ------------------------------------------------------------ integration
    def to_ops_provider(self):
        """Return an OpsProvider-compatible wrapper for ToolRegistry.

        This is where the actual AIOpsLab client is mapped to CloudOps Harness's
        ``OpsProvider`` protocol. Implement each method by delegating to the
        methods above when a real AIOpsLab environment is available.
        """
        raise NotImplementedError(
            "AIOpsLab OpsProvider mapping requires the installed AIOpsLab SDK. "
            "See docs/AIOPSLAB_INTEGRATION.md; external execution is pending."
        )


class AIOpsLabBenchmarkRunner:
    """High-level runner for a CloudOps Harness vs AIOpsLab evaluation.

    It mirrors the phases used by the internal real-LLM benchmark: smoke ->
    pilot -> formal holdout. No benchmark numbers are generated until an actual
    AIOpsLab environment is available.
    """

    def __init__(self, adapter: AIOpsLabAdapter, evaluator: Any | None = None) -> None:
        self.adapter = adapter
        self.evaluator = evaluator

    async def run(self, scenario_ids: list[str]) -> dict[str, Any]:
        raise NotImplementedError(
            "AIOpsLab external benchmark execution is pending; adapter interface is ready."
        )
