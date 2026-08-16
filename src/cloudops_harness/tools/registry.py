"""ToolRegistry: single source of truth for agent-callable operations.

The registry turns ``OpsProvider`` methods into LLM/MCP tool definitions and
enforces the Risk Policy at the boundary: an unapproved high-risk call can
never reach the provider.
"""

from __future__ import annotations

import asyncio
import json
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel, ValidationError

from cloudops_harness.common.circuit_breaker import CircuitBreaker, CircuitOpenError
from cloudops_harness.config.settings import Settings
from cloudops_harness.providers.protocol import OpsProvider
from cloudops_harness.runtime_context import current_run_id
from cloudops_harness.tools.budget import get_tool_budget, start_tool_budget
from cloudops_harness.tools.pii import redact_pii
from cloudops_harness.tools.risk import RISK_POLICY, RiskPolicy, ToolRisk
from cloudops_harness.tools.schemas import (
    ApplyConfigChangeArgs,
    CreateIncidentTicketArgs,
    DryRunActionArgs,
    GetConfigDiffArgs,
    GetCurrentReleaseArgs,
    GetIncidentHistoryArgs,
    GetRecentDeploymentsArgs,
    GetServiceCatalogArgs,
    GetServiceHealthArgs,
    GetServiceTopologyArgs,
    QueryLogsArgs,
    QueryMetricsArgs,
    RestartServiceArgs,
    RollbackReleaseArgs,
    ScaleServiceArgs,
    VerifyServiceHealthArgs,
)


class ToolApprovalRequiredError(RuntimeError):
    """Raised when a production-changing tool is called without HITL approval."""


class ToolExecutionError(RuntimeError):
    """Raised internally when a provider call fails; converted to ToolResult at the boundary."""


class ToolNotFoundError(RuntimeError):
    """Raised for unknown tool names."""


@dataclass(frozen=True)
class ToolDefinition:
    name: str
    description: str
    args_model: type[BaseModel]
    risk: ToolRisk
    handler: Callable[..., Awaitable[Any]]


@dataclass
class ToolResult:
    ok: bool
    tool_name: str
    content: str
    data: dict[str, Any] = field(default_factory=dict)
    latency_ms: float = 0.0
    error: str | None = None


class ToolObserver:
    """Hook used by tracing middleware; default no-op."""

    async def on_tool_start(
        self, agent: str, tool_name: str, args: dict[str, Any], risk_level: int = 0
    ) -> None: ...
    async def on_tool_end(self, agent: str, result: ToolResult) -> None: ...


class ToolRegistry:
    """Owns tool definitions, serialization and policy enforcement."""

    def __init__(
        self,
        provider: OpsProvider,
        settings: Settings,
        observer: ToolObserver | None = None,
        breaker: CircuitBreaker | None = None,
    ) -> None:
        self.provider = provider
        self.settings = settings
        self.pii_redaction = settings.pii_redaction
        self.policy = RiskPolicy(auto_approve_max_risk=settings.auto_approve_max_risk)
        self.observer = observer or ToolObserver()
        self.breaker = breaker or CircuitBreaker(name="ops-tools", failure_threshold=3, cooldown_seconds=15.0)
        self._definitions = self._build_definitions()
        # Telemetry only: cumulative per-process counters for observability.
        self.global_telemetry: dict[str, int] = {}

    # ------------------------------------------------------------------ setup
    def _build_definitions(self) -> dict[str, ToolDefinition]:
        defs = [
            (
                "dry_run_action",
                "Preview a production action (planned change, before state, expected impact, rollback method, risk) without executing it.",
                DryRunActionArgs,
                self.provider.dry_run_action,
            ),
            (
                "query_metrics",
                "Query time-series metrics for a service and window.",
                QueryMetricsArgs,
                self.provider.query_metrics,
            ),
            (
                "query_logs",
                "Query structured logs for a service and window, with level/pattern filters.",
                QueryLogsArgs,
                self.provider.query_logs,
            ),
            (
                "get_service_health",
                "Get current health status and key metrics of a service.",
                GetServiceHealthArgs,
                self.provider.get_service_health,
            ),
            (
                "get_service_topology",
                "Get the service dependency topology (optionally centered on one service).",
                GetServiceTopologyArgs,
                self.provider.get_service_topology,
            ),
            (
                "get_recent_deployments",
                "List recent deployments for a service.",
                GetRecentDeploymentsArgs,
                self.provider.get_recent_deployments,
            ),
            (
                "get_config_diff",
                "Show configuration changes between two releases of a service.",
                GetConfigDiffArgs,
                self.provider.get_config_diff,
            ),
            (
                "get_incident_history",
                "Return historical incidents for a service (lessons learned).",
                GetIncidentHistoryArgs,
                self.provider.get_incident_history,
            ),
            (
                "get_current_release",
                "Return the currently active release of a service.",
                GetCurrentReleaseArgs,
                self.provider.get_current_release,
            ),
            (
                "get_service_catalog",
                "Return service catalog entries (owner, repo, SLO, restart policy).",
                GetServiceCatalogArgs,
                self.provider.get_service_catalog,
            ),
            (
                "verify_service_health",
                "Re-check a service after remediation and report whether it recovered.",
                VerifyServiceHealthArgs,
                self.provider.verify_service_health,
            ),
            (
                "create_incident_ticket",
                "Create an incident ticket (low-risk write).",
                CreateIncidentTicketArgs,
                self.provider.create_incident_ticket,
            ),
            (
                "restart_service",
                "Restart a production service (production-changing, HITL required).",
                RestartServiceArgs,
                self.provider.restart_service,
            ),
            (
                "rollback_release",
                "Roll a service back to a previous release (high-risk destructive, HITL required).",
                RollbackReleaseArgs,
                self.provider.rollback_release,
            ),
            (
                "scale_service",
                "Change the replica count of a service (production-changing, HITL required).",
                ScaleServiceArgs,
                self.provider.scale_service,
            ),
            (
                "apply_config_change",
                "Apply a configuration change to a service (high-risk destructive, HITL required).",
                ApplyConfigChangeArgs,
                self.provider.apply_config_change,
            ),
        ]
        return {
            name: ToolDefinition(
                name=name, description=description, args_model=model, risk=RISK_POLICY[name], handler=handler
            )
            for name, description, model, handler in defs
        }

    # ------------------------------------------------------------------ access
    def get(self, name: str) -> ToolDefinition:
        try:
            return self._definitions[name]
        except KeyError as exc:
            raise ToolNotFoundError(name) from exc

    def definitions(self, names: set[str] | None = None, read_only: bool = False) -> list[ToolDefinition]:
        result = []
        for definition in self._definitions.values():
            if names is not None and definition.name not in names:
                continue
            if read_only and not definition.risk.read_only:
                continue
            result.append(definition)
        return sorted(result, key=lambda d: d.name)

    def openai_schemas(self, names: set[str] | None = None, read_only: bool = False) -> list[dict[str, Any]]:
        """OpenAI tool-calling compatible JSON for a tool subset."""
        return [
            {
                "type": "function",
                "function": {
                    "name": d.name,
                    "description": d.description,
                    "parameters": d.args_model.model_json_schema(),
                },
            }
            for d in self.definitions(names=names, read_only=read_only)
        ]

    def register_dynamic(
        self,
        name: str,
        description: str,
        args_model: type[BaseModel],
        handler: Callable[..., Awaitable[Any]],
        *,
        read_only: bool = True,
    ) -> None:
        """Register a non-provider tool (e.g. sandbox execution) at runtime."""
        from cloudops_harness.tools.risk import RiskLevel, ToolRisk

        self._definitions[name] = ToolDefinition(
            name=name,
            description=description,
            args_model=args_model,
            risk=ToolRisk(
                name=name,
                level=RiskLevel.READ_ONLY if read_only else RiskLevel.LOW_RISK_WRITE,
                read_only=read_only,
            ),
            handler=handler,
        )

    # ------------------------------------------------------------------ invoke
    async def call(
        self,
        name: str,
        arguments: dict[str, Any],
        *,
        agent: str = "main",
        approved: bool = False,
        bypass_breaker: bool = False,
    ) -> ToolResult:
        """Validate args, enforce risk policy and call the provider.

        ``approved=True`` is set by the executor node only after a valid HITL
        decision has been recorded in graph state.
        """
        definition = self.get(name)
        if definition.risk.level > self.settings.auto_approve_max_risk and not approved:
            raise ToolApprovalRequiredError(
                f"{name} requires HITL approval (risk level {int(definition.risk.level)})"
            )
        try:
            arguments = definition.args_model.model_validate(arguments).model_dump()
        except ValidationError as exc:
            raise ValueError(f"invalid arguments for {name}: {exc}") from exc

        self.global_telemetry[name] = self.global_telemetry.get(name, 0) + 1

        budget = get_tool_budget()
        if budget is None:
            budget = start_tool_budget(str(current_run_id.get() or "implicit"), self.settings.tool_call_limit)
        if not budget.record(name):
            return ToolResult(
                ok=False,
                tool_name=name,
                content="",
                error=(
                    f"tool call limit exceeded for run {budget.run_id} "
                    f"({budget.max_calls} max; {budget.calls} used)"
                ),
            )
        await self.observer.on_tool_start(agent, name, arguments, risk_level=int(definition.risk.level))
        started = time.monotonic()

        async def _invoke() -> ToolResult:
            try:
                data = await asyncio.wait_for(
                    definition.handler(**arguments),
                    timeout=self.settings.tool_timeout_seconds,
                )
                raw_content = json.dumps(
                    data.model_dump() if hasattr(data, "model_dump") else data,
                    default=str,
                    ensure_ascii=False,
                )
                content = redact_pii(raw_content) if self.pii_redaction else raw_content
                return ToolResult(
                    ok=True,
                    tool_name=name,
                    content=content,
                    data=data.model_dump()
                    if hasattr(data, "model_dump")
                    else (data if isinstance(data, dict) else {"value": data}),
                    latency_ms=(time.monotonic() - started) * 1000,
                )
            except TimeoutError as exc:
                raise ToolExecutionError(f"tool timeout after {self.settings.tool_timeout_seconds}s") from exc
            except Exception as exc:  # noqa: BLE001 - boundary converts any provider error to ToolResult
                raise ToolExecutionError(f"{type(exc).__name__}: {exc}") from exc

        try:
            result = await _invoke() if bypass_breaker else await self.breaker.protect(_invoke)
        except CircuitOpenError as exc:
            result = ToolResult(
                ok=False,
                tool_name=name,
                content="",
                error=str(exc),
                latency_ms=(time.monotonic() - started) * 1000,
            )
        except ToolExecutionError as exc:
            result = ToolResult(
                ok=False,
                tool_name=name,
                content="",
                error=str(exc),
                latency_ms=(time.monotonic() - started) * 1000,
            )
        await self.observer.on_tool_end(agent, result)
        return result
