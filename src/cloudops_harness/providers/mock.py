"""MockOpsProvider: deterministic, scenario-driven operations backend.

Design goals
------------
* No external cluster required: metrics, logs, deployments and config changes
  are synthesised deterministically from fixtures + an optional set of active
  incident scenarios (see ``fixtures/incidents/scenarios.json``).
* Every public method honours the ``OpsProvider`` protocol so a future
  Prometheus/Loki/Kubernetes adapter can replace this class without touching
  agents or tools.
* ``FaultInjection`` hooks allow the failure test-suite and demos to break the
  backend on demand (tool timeout, MCP down, injected errors).
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import math
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from cloudops_harness.providers.models import (
    ActionResult,
    ConfigChange,
    ConfigDiffResult,
    DeploymentRecord,
    DryRunResult,
    FaultInjection,
    HealthStatus,
    HistoricalIncident,
    IncidentTicket,
    LogEntry,
    LogsResult,
    MetricPoint,
    MetricsResult,
    ServiceHealth,
    ServiceInfo,
    Topology,
    TopologyEdge,
)
from cloudops_harness.providers.protocol import (
    OpsProvider,
    OpsProviderError,
    ProviderUnavailable,
    ToolTimeoutError,
    UnknownServiceError,
)

# Baseline metric profiles: metric -> (baseline, noise amplitude).
METRIC_PROFILES: dict[str, tuple[float, float]] = {
    "latency_p99_ms": (120.0, 40.0),
    "error_rate": (0.5, 0.4),
    "request_rate": (600.0, 120.0),
    "cpu_usage": (38.0, 12.0),
    "memory_usage": (45.0, 8.0),
    "db_pool_active": (8.0, 4.0),
    "db_pool_wait_ms": (4.0, 3.0),
    "db_connections_max": (50.0, 0.0),
    "redis_p99_ms": (8.0, 4.0),
    "upstream_p99_ms": (55.0, 15.0),
    "disk_usage": (42.0, 6.0),
    "gc_pause_ms": (12.0, 6.0),
    "queue_depth": (4.0, 3.0),
    "thread_pool_active": (12.0, 5.0),
    "http_5xx_rate": (0.1, 0.1),
}

DEFAULT_REPLICAS = {
    "api-gateway": 4,
    "user-service": 3,
    "order-service": 6,
    "payment-service": 4,
    "inventory-service": 3,
    "notification-service": 2,
}


def _iso(dt: datetime) -> str:
    return dt.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _parse_iso(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _hash01(*parts: object) -> float:
    digest = hashlib.md5("|".join(str(p) for p in parts).encode("utf-8")).hexdigest()
    return int(digest[:8], 16) / float(0xFFFFFFFF)


class MockOpsProvider(OpsProvider):
    """Deterministic implementation of the ops world for MVP, tests and evals."""

    def __init__(self, fixtures_dir: Path | str | None = None, seed: int = 42) -> None:
        self.seed = seed
        self.fixtures_dir = Path(fixtures_dir) if fixtures_dir else Path("fixtures")
        self.active_scenarios: dict[str, dict[str, Any]] = {}
        self.fault_injection = FaultInjection()
        self.resolved_scenarios: set[str] = set()
        self.action_log: list[dict[str, Any]] = []
        self._ticket_counter = 0
        self.replicas = dict(DEFAULT_REPLICAS)
        self.config_overrides: dict[str, dict[str, str]] = {}

        self._catalog: list[ServiceInfo] = [
            ServiceInfo.model_validate(item) for item in self._load_json("service_catalog.json")
        ]
        self.catalog_by_name = {s.name: s for s in self._catalog}
        topology_data = self._load_json("topology.json") or {"nodes": [], "edges": []}
        self.topology = Topology(
            nodes=topology_data["nodes"],
            edges=[TopologyEdge.model_validate(e) for e in topology_data["edges"]],
        )
        self._deployments: list[DeploymentRecord] = [
            DeploymentRecord.model_validate(item) for item in self._load_json("deployments.json")
        ]
        self._config_history: list[ConfigChange] = [
            ConfigChange.model_validate(item) for item in self._load_json("config_history.json")
        ]
        self._historical: list[HistoricalIncident] = [
            HistoricalIncident.model_validate(item) for item in self._load_json("historical_incidents.json")
        ]
        self._log_corpus: dict[str, list[dict[str, Any]]] = self._load_json("log_corpus.json")
        self.current_releases = {s.name: s.current_release for s in self._catalog}

    # ------------------------------------------------------------------ setup
    def _load_json(self, name: str) -> Any:
        path = self.fixtures_dir / name
        if not path.exists():
            return [] if name != "log_corpus.json" else {}
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    def activate_scenario(self, scenario: dict[str, Any]) -> None:
        """Activate one incident scenario (from the evaluation dataset)."""
        self.active_scenarios[scenario["incident_id"]] = scenario

    def deactivate_scenarios(self) -> None:
        self.active_scenarios.clear()
        self.resolved_scenarios.clear()

    # ------------------------------------------------------------- read tools
    async def query_metrics(self, service: str, metric: str, start: str, end: str) -> MetricsResult:
        self._require_service(service)
        await self._pre_call("query_metrics")
        start_dt, end_dt = _parse_iso(start), _parse_iso(end)
        if end_dt <= start_dt:
            end_dt = start_dt + timedelta(hours=1)
        baseline, noise = METRIC_PROFILES.get(metric, (50.0, 10.0))
        unit = self._unit_for(metric)
        step = self._step_for(start_dt, end_dt)
        points: list[MetricPoint] = []
        anomalous = False
        anomaly_window: dict[str, str] | None = None

        cursor = start_dt
        while cursor <= end_dt and len(points) < 400:
            value = baseline + self._noise(service, metric, cursor, noise)
            for scenario in self.active_scenarios.values():
                if not self._scenario_applies(scenario, service):
                    continue
                spec = self._metric_spec(scenario, metric, service)
                if spec is None:
                    continue
                anomaly_value = self._anomaly_value(spec, cursor, scenario, baseline)
                if anomaly_value is not None:
                    value = max(value, anomaly_value)
                    anomalous = True
                    anomaly_window = {
                        "start": scenario["anomaly_start"],
                        "end": scenario["anomaly_end"],
                    }
            points.append(MetricPoint(timestamp=_iso(cursor), value=round(value, 4)))
            cursor += step

        summary = self._summarize(points)
        return MetricsResult(
            service=service,
            metric=metric,
            start=_iso(start_dt),
            end=_iso(end_dt),
            unit=unit,
            points=points,
            summary=summary,
            anomalous=anomalous,
            anomaly_window=anomaly_window,
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
        self._require_service(service)
        await self._pre_call("query_logs")
        start_dt, end_dt = _parse_iso(start), _parse_iso(end)
        entries: list[LogEntry] = []

        # Baseline corpus.
        corpus = self._log_corpus.get(service, [])
        for _ in range(min(60, max(4, int((end_dt - start_dt).total_seconds() / 900)))):
            for template in corpus:
                if len(entries) >= 2000:
                    break
                if level and template["level"] != level.upper():
                    continue
                if pattern and pattern.lower() not in template["message"].lower():
                    continue
                ts = start_dt + timedelta(
                    seconds=_hash01(service, template["message"], len(entries), self.seed)
                    * (end_dt - start_dt).total_seconds()
                )
                entries.append(
                    LogEntry(
                        timestamp=_iso(ts),
                        level=template["level"],
                        service=service,
                        message=template["message"],
                    )
                )

        # Scenario evidence.
        scenario_patterns: set[str] = set()
        for scenario in self.active_scenarios.values():
            if not self._scenario_applies(scenario, service):
                continue
            for spec in scenario.get("log_specs", []):
                if spec.get("service", scenario.get("service")) != service:
                    continue
                message = spec["message"]
                if pattern and pattern.lower() not in message.lower():
                    continue
                if level and spec.get("level") != level.upper():
                    continue
                scenario_patterns.add(str(spec.get("pattern", message)))
                count = int(spec.get("count", 8))
                for i in range(count):
                    ts = self._scenario_time(scenario, start_dt, end_dt, i, count)
                    if ts is None:
                        continue
                    entries.append(
                        LogEntry(
                            timestamp=_iso(ts),
                            level=spec.get("level", "ERROR"),
                            service=service,
                            message=message,
                            # Do not attach scenario incident_id: it is evaluator-only
                            # metadata and can leak fault-type prefixes to the model.
                            trace_id=f"trace-{int(_hash01(service, message, i, self.seed) * 0xFFFFFFFF):032x}",
                            extra={},
                        )
                    )

        entries.sort(key=lambda e: e.timestamp)
        truncated = len(entries) > limit
        entries = entries[:limit]
        error_patterns = sorted(scenario_patterns)
        return LogsResult(
            service=service,
            start=_iso(start_dt),
            end=_iso(end_dt),
            query={"level": level, "pattern": pattern, "limit": limit},
            total=len(entries),
            returned=len(entries),
            truncated=truncated,
            entries=entries,
            error_patterns=error_patterns,
        )

    async def get_service_health(self, service: str) -> ServiceHealth:
        self._require_service(service)
        await self._pre_call("get_service_health")
        return self._compute_health(service)

    async def get_service_topology(self, service: str | None = None) -> Topology:
        await self._pre_call("get_service_topology")
        if service is None:
            return self.topology
        self._require_service(service)
        nodes = {service}
        edges: list[TopologyEdge] = []
        for edge in self.topology.edges:
            if edge.source == service or edge.target == service:
                nodes.add(edge.source)
                nodes.add(edge.target)
                edges.append(edge)
        return Topology(nodes=sorted(nodes), edges=edges)

    async def get_recent_deployments(self, service: str, limit: int = 10) -> list[DeploymentRecord]:
        self._require_service(service)
        await self._pre_call("get_recent_deployments")
        records = [d for d in self._deployments if d.service == service]
        for scenario in self.active_scenarios.values():
            if scenario.get("service") != service:
                continue
            for change in scenario.get("changes", []):
                if change["kind"] != "deployment":
                    continue
                records.append(
                    DeploymentRecord(
                        id=change["id"],
                        service=service,
                        version=change["to_version"],
                        previous_version=change.get("from_version"),
                        deployed_at=change["applied_at"],
                        operator=change.get("operator", "release-bot"),
                        trigger=change.get("trigger", "pipeline"),
                        status="succeeded",
                        diff_id=f"DIFF-{change['id']}",
                        notes=change.get("summary", ""),
                    )
                )
        unique = {r.id: r for r in records}
        ordered = sorted(unique.values(), key=lambda r: r.deployed_at, reverse=True)
        return ordered[:limit]

    async def get_config_diff(
        self, service: str, from_version: str | None = None, to_version: str | None = None
    ) -> ConfigDiffResult:
        self._require_service(service)
        await self._pre_call("get_config_diff")
        deployments = [d for d in self._deployments if d.service == service]
        for scenario in self.active_scenarios.values():
            if scenario.get("service") != service:
                continue
            for change in scenario.get("changes", []):
                if change["kind"] == "deployment":
                    deployments.append(
                        DeploymentRecord(
                            id=change["id"],
                            service=service,
                            version=change["to_version"],
                            previous_version=change.get("from_version"),
                            deployed_at=change["applied_at"],
                            operator=change.get("operator", "release-bot"),
                            trigger="pipeline",
                            status="succeeded",
                            diff_id=f"DIFF-{change['id']}",
                            notes=change.get("summary", ""),
                        )
                    )
        by_version = {d.version: d for d in deployments}
        to_version = to_version or self.current_releases.get(service)
        if from_version is None:
            previous = sorted(
                (d for d in deployments if d.version != to_version),
                key=lambda d: d.deployed_at,
                reverse=True,
            )
            from_version = previous[0].version if previous else to_version
        if to_version not in by_version:
            return ConfigDiffResult(service=service, from_version=from_version, to_version=to_version)

        from_time = _parse_iso(by_version[from_version].deployed_at) if from_version in by_version else None
        to_time = _parse_iso(by_version[to_version].deployed_at)
        changes: list[ConfigChange] = []
        for change in self._config_history:
            if change.service != service:
                continue
            applied = _parse_iso(change.applied_at)
            if from_time and applied <= from_time:
                continue
            if applied > to_time:
                continue
            changes.append(change)
        for scenario in self.active_scenarios.values():
            if scenario.get("service") != service:
                continue
            for change in scenario.get("changes", []):
                if change["kind"] != "config":
                    continue
                changes.append(
                    ConfigChange(
                        id=change["id"],
                        service=service,
                        path=change["config_path"],
                        before=change.get("before", ""),
                        after=change.get("after", ""),
                        applied_at=change["applied_at"],
                        deployment_id=change.get("deployment_id"),
                        operator=change.get("operator", "unknown"),
                        summary=change.get("summary", ""),
                    )
                )
        summary = "; ".join(c.summary for c in changes) or "no config changes in window"
        return ConfigDiffResult(
            service=service,
            from_version=from_version,
            to_version=to_version,
            changes=changes,
            summary=summary,
        )

    async def get_incident_history(self, service: str, limit: int = 10) -> list[HistoricalIncident]:
        self._require_service(service)
        await self._pre_call("get_incident_history")
        records = [i for i in self._historical if i.service == service]
        # Leakage guard: historical incidents are returned to the model as
        # lessons/titles only. Exact root_cause/fault_type labels are evaluator
        # ground truth in this synthetic environment and must not be exposed.
        sanitized = [
            i.model_copy(update={"fault_type": "[redacted]", "root_cause": "[redacted]"}) for i in records
        ]
        return sorted(sanitized, key=lambda i: i.occurred_at, reverse=True)[:limit]

    async def get_current_release(self, service: str) -> str:
        self._require_service(service)
        await self._pre_call("get_current_release")
        return self.current_releases.get(service, self.catalog_by_name[service].current_release)

    async def get_service_catalog(self, service: str | None = None) -> list[ServiceInfo]:
        await self._pre_call("get_service_catalog")
        if service is None:
            return list(self._catalog)
        self._require_service(service)
        return [self.catalog_by_name[service]]

    async def verify_service_health(self, service: str) -> ServiceHealth:
        self._require_service(service)
        await self._pre_call("verify_service_health")
        return self._compute_health(service)

    # ------------------------------------------------------------ write tools
    async def dry_run_action(
        self, action: str, service: str, environment: str, params: dict[str, Any]
    ) -> DryRunResult:
        self._require_service(service)
        common = {"action": action, "target": service, "environment": environment}
        if action == "rollback_release":
            before = self.current_releases.get(service, self.catalog_by_name[service].current_release)
            target = params.get("to_version", before)
            return DryRunResult(
                **common,
                planned_change=f"release {before} -> {target}",
                before_state={"release": before},
                expected_result="latency/error rate return to baseline",
                rollback_method=f"rollback_release back to {before} (reverse the change)",
                risk_level=3,
            )
        if action == "scale_service":
            before = self.replicas.get(service, 1)
            target = params.get("replicas", before)
            return DryRunResult(
                **common,
                planned_change=f"replicas {before} -> {target}",
                before_state={"replicas": before},
                expected_result="request queue drains; latency recovers",
                rollback_method=f"scale_service back to {before} replicas",
                risk_level=2,
            )
        if action == "restart_service":
            return DryRunResult(
                **common,
                planned_change="restart all pods (rolling)",
                before_state={"release": self.current_releases.get(service)},
                expected_result="transient saturation cleared",
                rollback_method="restart is not reversible; rely on release config",
                risk_level=2,
            )
        if action == "apply_config_change":
            key = params.get("key", "")
            value = params.get("value", "")
            return DryRunResult(
                **common,
                planned_change=f"set {key}={value}",
                before_state={"config_overrides": dict(self.config_overrides.get(service, {}))},
                expected_result="configuration restored to intended value",
                rollback_method=f"apply_config_change {key} back to previous value",
                risk_level=3,
            )
        return DryRunResult(
            **common,
            valid=False,
            planned_change="unsupported action",
            before_state={},
            expected_result="",
            rollback_method="",
            risk_level=0,
        )

    async def create_incident_ticket(
        self, service: str, title: str, severity: str, description: str
    ) -> IncidentTicket:
        self._require_service(service)
        await self._pre_call("create_incident_ticket")
        self._ticket_counter += 1
        ticket = IncidentTicket(
            id=f"INC-{self._ticket_counter:04d}",
            service=service,
            title=title,
            severity=severity,
            created_at=_iso(datetime.now(UTC)),
        )
        self._record_action(
            "create_incident_ticket",
            service,
            {"title": title, "severity": severity, "description": description},
            ticket.model_dump(),
        )
        return ticket

    async def restart_service(self, service: str, reason: str) -> ActionResult:
        self._require_service(service)
        await self._pre_call("restart_service")
        before = self._compute_health(service).model_dump()
        self._record_action("restart_service", service, {"reason": reason}, {"before": before})
        # A restart clears transient saturation scenarios.
        self._maybe_resolve(service, "restart_service")
        return ActionResult(
            ok=True,
            action="restart_service",
            target=service,
            message=f"{service} restarted (reason: {reason})",
            detail={"before_status": before["status"]},
        )

    async def rollback_release(self, service: str, to_version: str, reason: str) -> ActionResult:
        self._require_service(service)
        await self._pre_call("rollback_release")
        deployments = await self.get_recent_deployments(service)
        if not any(d.version == to_version for d in deployments):
            raise OpsProviderError(f"version {to_version} not found in deployment history for {service}")
        before = self.current_releases.get(service)
        self.current_releases[service] = to_version
        self._record_action(
            "rollback_release",
            service,
            {"to_version": to_version, "reason": reason},
            {"before_release": before, "after_release": to_version},
        )
        self._maybe_resolve(service, "rollback_release")
        return ActionResult(
            ok=True,
            action="rollback_release",
            target=service,
            message=f"{service} rolled back {before} -> {to_version} (reason: {reason})",
            detail={"before_release": before, "after_release": to_version},
        )

    async def scale_service(self, service: str, replicas: int, reason: str) -> ActionResult:
        self._require_service(service)
        await self._pre_call("scale_service")
        if replicas < 0 or replicas > 100:
            raise OpsProviderError(f"replicas out of allowed range: {replicas}")
        before = self.replicas.get(service)
        self.replicas[service] = replicas
        self._record_action(
            "scale_service", service, {"replicas": replicas, "reason": reason}, {"before_replicas": before}
        )
        self._maybe_resolve(service, "scale_service")
        return ActionResult(
            ok=True,
            action="scale_service",
            target=service,
            message=f"{service} scaled {before} -> {replicas} replicas (reason: {reason})",
            detail={"before_replicas": before, "after_replicas": replicas},
        )

    async def apply_config_change(self, service: str, key: str, value: str, reason: str) -> ActionResult:
        self._require_service(service)
        await self._pre_call("apply_config_change")
        before = self.config_overrides.get(service, {}).get(key)
        self.config_overrides.setdefault(service, {})[key] = value
        self._record_action(
            "apply_config_change", service, {"key": key, "value": value, "reason": reason}, {"before": before}
        )
        self._maybe_resolve(service, "apply_config_change")
        return ActionResult(
            ok=True,
            action="apply_config_change",
            target=service,
            message=f"{service} config {key}={value} applied (reason: {reason})",
            detail={"key": key, "before": before, "after": value},
        )

    # ------------------------------------------------------------- internals
    def _require_service(self, service: str) -> None:
        if service not in self.catalog_by_name:
            raise UnknownServiceError(f"unknown service: {service}")

    async def _pre_call(self, tool_name: str) -> None:
        injection = self.fault_injection
        if injection.unavailable:
            raise ProviderUnavailable("ops backend unavailable (injected)")
        remaining = injection.fail_next.get(tool_name, 0)
        if remaining > 0:
            injection.fail_next[tool_name] = remaining - 1
            raise OpsProviderError(f"injected failure for {tool_name}")
        if tool_name in injection.timeout_tools:
            await asyncio.sleep(0.2)
            raise ToolTimeoutError(f"injected timeout for {tool_name}")

    def _record_action(self, action: str, target: str, args: dict, result: dict) -> None:
        self.action_log.append(
            {
                "action": action,
                "target": target,
                "args": args,
                "result": result,
                "at": _iso(datetime.now(UTC)),
            }
        )

    def _maybe_resolve(self, service: str, action: str) -> None:
        for scenario in self.active_scenarios.values():
            if scenario.get("service") != service:
                continue
            if scenario.get("fix_action") == action:
                self.resolved_scenarios.add(scenario["incident_id"])

    def _compute_health(self, service: str) -> ServiceHealth:
        if service in self.fault_injection.health_overrides:
            status = self.fault_injection.health_overrides[service]
            message = "health override (fault injection)"
        else:
            scenario = self._scenario_for(service)
            if scenario and scenario["incident_id"] in self.resolved_scenarios:
                status, message = HealthStatus.HEALTHY, "remediation verified"
            elif scenario:
                status = HealthStatus.DOWN if scenario.get("severity") == "P0" else HealthStatus.DEGRADED
                # Generic message only: the scenario title contains the fault label
                # and is evaluator metadata, not public service health text.
                message = "active incident detected"
            else:
                status, message = HealthStatus.HEALTHY, "within SLO"

        metrics = {
            metric: round(self._last_value(service, metric, baseline), 3)
            for metric, (baseline, _) in list(METRIC_PROFILES.items())[:9]
        }
        dependencies: dict[str, HealthStatus] = {}
        for edge in self.topology.edges:
            if edge.source != service:
                continue
            target = edge.target
            if target not in self.catalog_by_name:
                continue
            target_scenario = self._scenario_for(target)
            if target_scenario is None:
                dependencies[target] = HealthStatus.HEALTHY
            elif target_scenario.get("severity") == "P0":
                dependencies[target] = HealthStatus.DOWN
            else:
                dependencies[target] = HealthStatus.DEGRADED
        recent = [entry["action"] for entry in self.action_log if entry["target"] == service][-5:]
        return ServiceHealth(
            service=service,
            status=status,
            checked_at=_iso(datetime.now(UTC)),
            message=message,
            metrics=metrics,
            dependencies=dependencies,
            recent_actions=recent,
        )

    def _scenario_for(self, service: str) -> dict[str, Any] | None:
        matches = []
        for scenario in self.active_scenarios.values():
            affected = {scenario.get("service", "")} | set(scenario.get("affected_services", []))
            if service in affected:
                matches.append(scenario)
        if not matches:
            return None
        return max(matches, key=lambda s: s.get("severity", "P3"))

    def _scenario_applies(self, scenario: dict[str, Any], service: str) -> bool:
        return service in ({scenario.get("service", "")} | set(scenario.get("affected_services", [])))

    def _last_value(self, service: str, metric: str, baseline: float) -> float:
        now = datetime.now(UTC)
        value = baseline + self._noise(service, metric, now, 5.0)
        for scenario in self.active_scenarios.values():
            if not self._scenario_applies(scenario, service):
                continue
            spec = self._metric_spec(scenario, metric, service)
            if spec is None:
                continue
            anomaly = self._anomaly_value(spec, now, scenario, baseline)
            if anomaly is not None:
                value = max(value, anomaly)
        return value

    def _metric_spec(self, scenario: dict, metric: str, service: str | None = None) -> dict[str, Any] | None:
        for spec in scenario.get("metric_specs", []):
            if spec.get("metric") != metric:
                continue
            if service is not None and spec.get("service", scenario.get("service")) != service:
                continue
            return spec
        return None

    def _anomaly_value(
        self, spec: dict[str, Any], ts: datetime, scenario: dict[str, Any], baseline: float
    ) -> float | None:
        start = _parse_iso(scenario["anomaly_start"])
        end = _parse_iso(scenario["anomaly_end"])
        if not (start <= ts <= end):
            return None
        shape = spec.get("shape", "step")
        lo = float(spec.get("anomaly_min", baseline))
        hi = float(spec.get("anomaly_max", baseline))
        progress = (ts - start).total_seconds() / max((end - start).total_seconds(), 1.0)
        if shape == "step":
            return hi
        if shape == "ramp":
            return baseline + (hi - baseline) * min(progress, 1.0)
        if shape == "spike":
            center = start + (end - start) / 2
            sigma = max((end - start).total_seconds() / 8, 60)
            factor = math.exp(-((ts - center).total_seconds() ** 2) / (2 * sigma * sigma))
            return lo + (hi - lo) * factor
        if shape == "wave":
            return lo + (hi - lo) * (0.5 + 0.5 * math.sin(2 * math.pi * progress))
        return hi

    def _scenario_time(
        self, scenario: dict, start: datetime, end: datetime, index: int, count: int
    ) -> datetime | None:
        window_start = _parse_iso(scenario["anomaly_start"])
        window_end = _parse_iso(scenario["anomaly_end"])
        overlap_start = max(start, window_start)
        overlap_end = min(end, window_end)
        if overlap_end <= overlap_start:
            return None
        span = (overlap_end - overlap_start).total_seconds()
        return overlap_start + timedelta(seconds=span * ((index + 0.5) / max(count, 1)))

    def _noise(self, service: str, metric: str, ts: datetime, amplitude: float) -> float:
        noise = (_hash01(service, metric, ts.replace(microsecond=0).isoformat(), self.seed) - 0.5) * 2
        return noise * amplitude

    def _step_for(self, start: datetime, end: datetime) -> timedelta:
        seconds = max((end - start).total_seconds(), 60)
        if seconds > 12 * 3600:
            return timedelta(minutes=20)
        if seconds > 2 * 3600:
            return timedelta(minutes=10)
        return timedelta(minutes=1)

    @staticmethod
    def _summarize(points: list[MetricPoint]) -> dict[str, float]:
        if not points:
            return {"min": 0, "max": 0, "mean": 0, "last": 0}
        values = [p.value for p in points]
        ordered = sorted(values)
        p99_index = min(len(ordered) - 1, int(len(ordered) * 0.99))
        return {
            "min": round(min(values), 3),
            "max": round(max(values), 3),
            "mean": round(sum(values) / len(values), 3),
            "p99": round(ordered[p99_index], 3),
            "last": round(values[-1], 3),
        }

    @staticmethod
    def _unit_for(metric: str) -> str:
        if "latency" in metric or metric.endswith("_ms"):
            return "ms"
        if "rate" in metric or metric.endswith("_usage"):
            return "percent"
        if "request" in metric or "queue" in metric or "pool" in metric or "thread" in metric:
            return "count"
        return "value"
