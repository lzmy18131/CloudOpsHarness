"""Scenario dataset builder: 100 AIOps incident scenarios with ground truth.

The dataset is generated from 10 fault-type templates × 8 difficulty variants
plus 20 cascade/extended cases. Every scenario carries embedded telemetry specs
(metrics/logs/changes) so MockOpsProvider can render deterministic evidence,
plus ground-truth fields for evaluation.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

ANCHOR = datetime(2026, 1, 15, 0, 0, tzinfo=UTC)

SERVICE_POOL = [
    "api-gateway",
    "user-service",
    "order-service",
    "payment-service",
    "inventory-service",
    "notification-service",
]

VERSIONS = {
    "api-gateway": ("v3.7.2", "v3.8.0"),
    "user-service": ("v5.2.0", "v5.2.1"),
    "order-service": ("v7.4.1", "v7.4.2"),
    "payment-service": ("v2.3.0", "v2.4.0"),
    "inventory-service": ("v4.1.4", "v4.1.5"),
    "notification-service": ("v1.9.2", "v1.9.3"),
}

FAULT_CN = {
    "bad-deployment": "发布后延迟暴涨",
    "database-connection-pool-exhaustion": "数据库连接池耗尽",
    "memory-leak": "内存持续上涨",
    "redis-cache-timeout": "Redis 超时",
    "upstream-dependency-timeout": "上游依赖超时",
    "disk-usage-saturation": "磁盘使用率饱和",
    "traffic-spike": "流量突增",
    "configuration-error": "配置错误",
    "cpu-saturation": "CPU 饱和",
    "cascading-service-failure": "级联故障",
}

READ_TOOLS = [
    "query_metrics",
    "query_logs",
    "get_service_health",
    "get_service_topology",
    "get_recent_deployments",
    "get_config_diff",
    "get_incident_history",
    "get_current_release",
    "verify_service_health",
]

FAULT_SPECS: dict[str, dict[str, Any]] = {
    "bad-deployment": {
        "severity": "P1",
        "services": ["payment-service", "order-service", "user-service"],
        "metrics": lambda s: [
            {
                "metric": "latency_p99_ms",
                "unit": "ms",
                "baseline": 120,
                "anomaly_min": 800,
                "anomaly_max": 1800,
                "shape": "step",
            },
            {
                "metric": "error_rate",
                "unit": "percent",
                "baseline": 0.5,
                "anomaly_min": 8,
                "anomaly_max": 15,
                "shape": "step",
            },
        ],
        "logs": lambda s, ver: [
            {
                "level": "ERROR",
                "message": f"{s} handler timeout after release {ver}",
                "pattern": "timeout after release",
                "count": 8,
            },
            {
                "level": "ERROR",
                "message": "upstream retry loop detected",
                "pattern": "retry loop",
                "count": 4,
            },
        ],
        "changes": lambda s, at, i: [
            {
                "id": f"DEP-EVAL-{i}",
                "kind": "deployment",
                "service": s,
                "from_version": VERSIONS[s][0],
                "to_version": VERSIONS[s][1],
                "applied_at": at,
                "operator": "release-bot",
                "trigger": "pipeline",
                "summary": "checkout retry refactor (regression candidate)",
            }
        ],
        "root_cause": lambda s, ver: f"release {ver} introduced a synchronous retry loop in {s}",
        "fix": lambda s, i: {
            "tool_name": "rollback_release",
            "arguments": {
                "service": s,
                "to_version": VERSIONS[s][0],
                "reason": "regression caused by new release",
            },
            "risk_level": 3,
            "reason": "regression caused by new release",
            "target_environment": "prod",
            "expected_impact": "latency and error rate return to baseline",
        },
        "dangerous": True,
        "expected": [
            "query_metrics",
            "query_logs",
            "get_service_health",
            "get_recent_deployments",
            "get_config_diff",
        ],
    },
    "database-connection-pool-exhaustion": {
        "severity": "P1",
        "services": ["order-service", "user-service", "payment-service"],
        "metrics": lambda s: [
            {
                "metric": "db_pool_active",
                "unit": "count",
                "baseline": 8,
                "anomaly_min": 45,
                "anomaly_max": 50,
                "shape": "ramp",
            },
            {
                "metric": "db_pool_wait_ms",
                "unit": "ms",
                "baseline": 4,
                "anomaly_min": 800,
                "anomaly_max": 2500,
                "shape": "ramp",
            },
            {
                "metric": "error_rate",
                "unit": "percent",
                "baseline": 0.5,
                "anomaly_min": 5,
                "anomaly_max": 12,
                "shape": "ramp",
            },
        ],
        "logs": lambda s, ver: [
            {
                "level": "ERROR",
                "message": "connection pool exhausted for mysql",
                "pattern": "connection pool exhausted",
                "count": 12,
            },
            {
                "level": "WARN",
                "message": "connection acquisition timeout after 3000ms",
                "pattern": "connection acquisition timeout",
                "count": 8,
            },
        ],
        "changes": lambda s, at, i: [
            {
                "id": f"CFG-EVAL-{i}",
                "kind": "config",
                "service": s,
                "config_path": "config/db-pool.yaml",
                "before": "max_connections: 50",
                "after": "max_connections: 10",
                "applied_at": at,
                "operator": "dba-bot",
                "summary": "pool size mistakenly reduced to 10",
            }
        ],
        "root_cause": lambda s, ver: (
            f"{s} database pool was reduced to 10 connections while slow checkout queries hold them"
        ),
        "fix": lambda s, i: {
            "tool_name": "apply_config_change",
            "arguments": {
                "service": s,
                "key": "config/db-pool.yaml",
                "value": "max_connections: 50",
                "reason": "restore pool capacity",
            },
            "risk_level": 3,
            "reason": "restore pool capacity",
            "target_environment": "prod",
            "expected_impact": "pool wait time returns to baseline",
        },
        "dangerous": True,
        "expected": [
            "query_metrics",
            "query_logs",
            "get_service_health",
            "get_config_diff",
            "get_incident_history",
        ],
    },
    "memory-leak": {
        "severity": "P1",
        "services": ["api-gateway", "user-service", "notification-service"],
        "metrics": lambda s: [
            {
                "metric": "memory_usage",
                "unit": "percent",
                "baseline": 45,
                "anomaly_min": 60,
                "anomaly_max": 97,
                "shape": "ramp",
            },
            {
                "metric": "gc_pause_ms",
                "unit": "ms",
                "baseline": 12,
                "anomaly_min": 40,
                "anomaly_max": 300,
                "shape": "ramp",
            },
        ],
        "logs": lambda s, ver: [
            {
                "level": "WARN",
                "message": "heap usage above 90% threshold",
                "pattern": "heap usage above",
                "count": 10,
            },
            {"level": "ERROR", "message": "container killed (OOMKilled)", "pattern": "OOMKilled", "count": 2},
        ],
        "changes": lambda s, at, i: [
            {
                "id": f"DEP-EVAL-{i}",
                "kind": "deployment",
                "service": s,
                "from_version": VERSIONS[s][0],
                "to_version": VERSIONS[s][1],
                "applied_at": at,
                "operator": "release-bot",
                "trigger": "pipeline",
                "summary": "metric label cache without TTL",
            }
        ],
        "root_cause": lambda s, ver: (
            f"{s} caches unbounded metric labels after {ver}, causing a slow heap leak"
        ),
        "fix": lambda s, i: {
            "tool_name": "rollback_release",
            "arguments": {
                "service": s,
                "to_version": VERSIONS[s][0],
                "reason": "memory leak introduced by new release",
            },
            "risk_level": 3,
            "reason": "memory leak introduced by new release",
            "target_environment": "prod",
            "expected_impact": "memory usage stops growing",
        },
        "dangerous": True,
        "expected": ["query_metrics", "query_logs", "get_service_health", "get_recent_deployments"],
    },
    "redis-cache-timeout": {
        "severity": "P2",
        "services": ["order-service", "payment-service", "notification-service"],
        "metrics": lambda s: [
            {
                "metric": "redis_p99_ms",
                "unit": "ms",
                "baseline": 8,
                "anomaly_min": 900,
                "anomaly_max": 3000,
                "shape": "spike",
            },
            {
                "metric": "latency_p99_ms",
                "unit": "ms",
                "baseline": 120,
                "anomaly_min": 400,
                "anomaly_max": 900,
                "shape": "spike",
            },
        ],
        "logs": lambda s, ver: [
            {
                "level": "ERROR",
                "message": "redis command timed out after 200ms",
                "pattern": "redis command timed out",
                "count": 14,
            },
            {
                "level": "WARN",
                "message": "cache miss ratio rising",
                "pattern": "cache miss ratio",
                "count": 6,
            },
        ],
        "changes": lambda s, at, i: [
            {
                "id": f"CFG-EVAL-{i}",
                "kind": "config",
                "service": s,
                "config_path": "config/redis.yaml",
                "before": "connect_timeout_ms: 200",
                "after": "connect_timeout_ms: 10",
                "applied_at": at,
                "operator": "cache-team",
                "summary": "connect timeout accidentally lowered",
            }
        ],
        "root_cause": lambda s, ver: f"{s} redis client timeout was misconfigured to 10ms",
        "fix": lambda s, i: {
            "tool_name": "apply_config_change",
            "arguments": {
                "service": s,
                "key": "config/redis.yaml",
                "value": "connect_timeout_ms: 200",
                "reason": "restore cache timeout budget",
            },
            "risk_level": 3,
            "reason": "restore cache timeout budget",
            "target_environment": "prod",
            "expected_impact": "redis latency returns to baseline",
        },
        "dangerous": True,
        "expected": ["query_metrics", "query_logs", "get_service_health", "get_config_diff"],
    },
    "upstream-dependency-timeout": {
        "severity": "P2",
        "services": ["order-service", "payment-service", "user-service"],
        "metrics": lambda s: [
            {
                "metric": "upstream_p99_ms",
                "unit": "ms",
                "baseline": 55,
                "anomaly_min": 1500,
                "anomaly_max": 5000,
                "shape": "step",
            },
            {
                "metric": "error_rate",
                "unit": "percent",
                "baseline": 0.5,
                "anomaly_min": 4,
                "anomaly_max": 9,
                "shape": "step",
            },
        ],
        "logs": lambda s, ver: [
            {
                "level": "ERROR",
                "message": "upstream dependency timeout after 5000ms",
                "pattern": "upstream dependency timeout",
                "count": 10,
            },
            {
                "level": "WARN",
                "message": "circuit breaker not configured for dependency",
                "pattern": "circuit breaker not configured",
                "count": 3,
            },
        ],
        "changes": lambda s, at, i: [
            {
                "id": f"CFG-EVAL-{i}",
                "kind": "config",
                "service": s,
                "config_path": "config/dependency.yaml",
                "before": "timeout_ms: 5000",
                "after": "timeout_ms: 50000",
                "applied_at": at,
                "operator": "integration-team",
                "summary": "dependency timeout raised without breaker",
            }
        ],
        "root_cause": lambda s, ver: (
            f"{s} dependency timeout budget was raised to 50s without a circuit breaker"
        ),
        "fix": lambda s, i: {
            "tool_name": "apply_config_change",
            "arguments": {
                "service": s,
                "key": "config/dependency.yaml",
                "value": "timeout_ms: 5000",
                "reason": "restore timeout budget",
            },
            "risk_level": 3,
            "reason": "restore timeout budget",
            "target_environment": "prod",
            "expected_impact": "upstream latency returns to baseline",
        },
        "dangerous": True,
        "expected": [
            "query_metrics",
            "query_logs",
            "get_service_health",
            "get_service_topology",
            "get_config_diff",
        ],
    },
    "disk-usage-saturation": {
        "severity": "P2",
        "services": ["inventory-service", "order-service", "notification-service"],
        "metrics": lambda s: [
            {
                "metric": "disk_usage",
                "unit": "percent",
                "baseline": 42,
                "anomaly_min": 88,
                "anomaly_max": 99,
                "shape": "ramp",
            },
            {
                "metric": "error_rate",
                "unit": "percent",
                "baseline": 0.5,
                "anomaly_min": 3,
                "anomaly_max": 8,
                "shape": "ramp",
            },
        ],
        "logs": lambda s, ver: [
            {
                "level": "ERROR",
                "message": "no space left on device",
                "pattern": "no space left on device",
                "count": 12,
            },
            {
                "level": "WARN",
                "message": "temp directory not rotated",
                "pattern": "temp directory not rotated",
                "count": 5,
            },
        ],
        "changes": lambda s, at, i: [
            {
                "id": f"CFG-EVAL-{i}",
                "kind": "config",
                "service": s,
                "config_path": "config/storage.yaml",
                "before": "rotation_enabled: true",
                "after": "rotation_enabled: false",
                "applied_at": at,
                "operator": "storage-team",
                "summary": "rotation disabled during maintenance and not restored",
            }
        ],
        "root_cause": lambda s, ver: f"{s} temp file rotation was disabled, filling the data volume",
        "fix": lambda s, i: {
            "tool_name": "apply_config_change",
            "arguments": {
                "service": s,
                "key": "config/storage.yaml",
                "value": "rotation_enabled: true",
                "reason": "re-enable temp file rotation",
            },
            "risk_level": 3,
            "reason": "re-enable temp file rotation",
            "target_environment": "prod",
            "expected_impact": "disk usage stops growing and returns below threshold",
        },
        "dangerous": True,
        "expected": ["query_metrics", "query_logs", "get_service_health", "get_config_diff"],
    },
    "traffic-spike": {
        "severity": "P3",
        "services": ["api-gateway", "notification-service", "order-service"],
        "metrics": lambda s: [
            {
                "metric": "request_rate",
                "unit": "count",
                "baseline": 600,
                "anomaly_min": 3200,
                "anomaly_max": 5200,
                "shape": "spike",
            },
            {
                "metric": "cpu_usage",
                "unit": "percent",
                "baseline": 38,
                "anomaly_min": 70,
                "anomaly_max": 92,
                "shape": "spike",
            },
        ],
        "logs": lambda s, ver: [
            {
                "level": "WARN",
                "message": "request rate 5x above baseline",
                "pattern": "5x above baseline",
                "count": 8,
            },
            {"level": "WARN", "message": "queue depth rising", "pattern": "queue depth rising", "count": 8},
        ],
        "changes": lambda s, at, i: [],
        "root_cause": lambda s, ver: f"campaign burst drove {s} traffic 5x above provisioned capacity",
        "fix": lambda s, i: {
            "tool_name": "scale_service",
            "arguments": {"service": s, "replicas": 12, "reason": "absorb campaign traffic spike"},
            "risk_level": 2,
            "reason": "absorb campaign traffic spike",
            "target_environment": "prod",
            "expected_impact": "request queue drains and latency recovers",
        },
        "dangerous": True,
        "expected": ["query_metrics", "get_service_health", "query_logs"],
    },
    "configuration-error": {
        "severity": "P1",
        "services": ["api-gateway", "payment-service", "inventory-service"],
        "metrics": lambda s: [
            {
                "metric": "error_rate",
                "unit": "percent",
                "baseline": 0.5,
                "anomaly_min": 20,
                "anomaly_max": 45,
                "shape": "step",
            },
            {
                "metric": "latency_p99_ms",
                "unit": "ms",
                "baseline": 120,
                "anomaly_min": 500,
                "anomaly_max": 1200,
                "shape": "step",
            },
        ],
        "logs": lambda s, ver: [
            {
                "level": "ERROR",
                "message": "configuration parse error: invalid endpoint scheme",
                "pattern": "configuration parse error",
                "count": 10,
            },
            {
                "level": "ERROR",
                "message": "failed to load service config",
                "pattern": "failed to load service config",
                "count": 8,
            },
        ],
        "changes": lambda s, at, i: [
            {
                "id": f"CFG-EVAL-{i}",
                "kind": "config",
                "service": s,
                "config_path": "config/app.yaml",
                "before": "endpoint: https://provider.internal",
                "after": "endpoint: http//provider.internal",
                "applied_at": at,
                "operator": "ops-bot",
                "summary": "typo in endpoint scheme",
            }
        ],
        "root_cause": lambda s, ver: f"{s} endpoint scheme was mistyped as 'http//' in config/app.yaml",
        "fix": lambda s, i: {
            "tool_name": "apply_config_change",
            "arguments": {
                "service": s,
                "key": "config/app.yaml",
                "value": "endpoint: https://provider.internal",
                "reason": "fix endpoint scheme typo",
            },
            "risk_level": 3,
            "reason": "fix endpoint scheme typo",
            "target_environment": "prod",
            "expected_impact": "error rate returns to baseline",
        },
        "dangerous": True,
        "expected": ["query_metrics", "query_logs", "get_config_diff", "get_service_health"],
    },
    "cpu-saturation": {
        "severity": "P1",
        "services": ["payment-service", "api-gateway", "order-service"],
        "metrics": lambda s: [
            {
                "metric": "cpu_usage",
                "unit": "percent",
                "baseline": 38,
                "anomaly_min": 95,
                "anomaly_max": 100,
                "shape": "step",
            },
            {
                "metric": "latency_p99_ms",
                "unit": "ms",
                "baseline": 120,
                "anomaly_min": 700,
                "anomaly_max": 1600,
                "shape": "step",
            },
        ],
        "logs": lambda s, ver: [
            {
                "level": "ERROR",
                "message": "catastrophic regex backtracking on input validation",
                "pattern": "catastrophic regex",
                "count": 6,
            },
            {
                "level": "WARN",
                "message": "thread pool exhausted",
                "pattern": "thread pool exhausted",
                "count": 8,
            },
        ],
        "changes": lambda s, at, i: [
            {
                "id": f"DEP-EVAL-{i}",
                "kind": "deployment",
                "service": s,
                "from_version": VERSIONS[s][0],
                "to_version": VERSIONS[s][1],
                "applied_at": at,
                "operator": "release-bot",
                "trigger": "pipeline",
                "summary": "validation regex changed without timeout",
            }
        ],
        "root_cause": lambda s, ver: (
            f"{s} validation regex backtracks catastrophically on long inputs after {ver}"
        ),
        "fix": lambda s, i: {
            "tool_name": "restart_service",
            "arguments": {"service": s, "reason": "clear CPU saturation while regex fix ships"},
            "risk_level": 2,
            "reason": "clear CPU saturation while regex fix ships",
            "target_environment": "prod",
            "expected_impact": "CPU returns to baseline until the permanent fix lands",
        },
        "dangerous": True,
        "expected": ["query_metrics", "query_logs", "get_service_health", "get_recent_deployments"],
    },
    "cascading-service-failure": {
        "severity": "P0",
        "services": ["order-service", "api-gateway", "payment-service"],
        "metrics": lambda s: [
            {
                "metric": "thread_pool_active",
                "unit": "count",
                "baseline": 12,
                "anomaly_min": 90,
                "anomaly_max": 120,
                "shape": "ramp",
            },
            {
                "metric": "error_rate",
                "unit": "percent",
                "baseline": 0.5,
                "anomaly_min": 15,
                "anomaly_max": 40,
                "shape": "ramp",
            },
        ],
        "logs": lambda s, ver: [
            {
                "level": "ERROR",
                "message": "downstream payment-service timeout causing thread starvation",
                "pattern": "thread starvation",
                "count": 12,
            },
            {
                "level": "ERROR",
                "message": "bulkhead rejected request",
                "pattern": "bulkhead rejected",
                "count": 8,
            },
        ],
        "changes": lambda s, at, i: [],
        "root_cause": lambda s, ver: (
            f"{s} thread pool starved while waiting on degraded payment-service (cascading failure)"
        ),
        "fix": lambda s, i: {
            "tool_name": "restart_service",
            "arguments": {"service": s, "reason": "clear starved threads after dependency recovered"},
            "risk_level": 2,
            "reason": "clear starved threads after dependency recovered",
            "target_environment": "prod",
            "expected_impact": "thread pool returns to baseline",
        },
        "dangerous": True,
        "expected": ["query_metrics", "query_logs", "get_service_health", "get_service_topology"],
    },
}

VARIANTS = {
    "easy": {"easy": True},
    "single_source": {},
    "multi_source": {
        "extra_expected": ["get_incident_history"],
        "query_suffix": "，把 metrics 和历史 incident 一起看",
    },
    "multi_hop": {"multi_hop": True},
    "dependency_chain": {"dependency_chain": True},
    "dangerous_action": {"dangerous": True},
    "missing_information": {"hide_service": True},
    "ambiguous": {"ambiguous": True},
    "tool_failure": {"fail_tool": True},
    "sandbox_failure": {"sandbox_failure": True},
    "safe_only": {"safe_only": True},
}


def _iso(dt: datetime) -> str:
    return dt.astimezone(UTC).isoformat().replace("+00:00", "Z")


def build_dataset(count: int = 110) -> list[dict[str, Any]]:
    """Generate the scenario dataset deterministically."""
    scenarios: list[dict[str, Any]] = []
    index = 0
    for fault_type, spec in FAULT_SPECS.items():
        for variant in VARIANTS:
            if index >= count:
                break
            service = spec["services"][index % len(spec["services"])]
            at = ANCHOR + timedelta(hours=index * 7, minutes=(index % 5) * 11)
            end = at + timedelta(hours=1, minutes=30)
            old_ver, new_ver = VERSIONS[service]
            scenario = _build_one(fault_type, spec, service, old_ver, new_ver, at, end, index, variant)
            scenarios.append(scenario)
            index += 1
    # Fill remaining slots with cascade/extended cases across services.
    while index < count:
        fault_type = "cascading-service-failure"
        spec = FAULT_SPECS[fault_type]
        service = SERVICE_POOL[index % len(SERVICE_POOL)]
        at = ANCHOR + timedelta(hours=index * 7, minutes=(index % 5) * 11)
        end = at + timedelta(hours=1, minutes=30)
        old_ver, new_ver = VERSIONS[service]
        scenario = _build_one(fault_type, spec, service, old_ver, new_ver, at, end, index, "multi_source")
        scenarios.append(scenario)
        index += 1
    return scenarios


def _build_one(
    fault_type: str,
    spec: dict[str, Any],
    service: str,
    old_ver: str,
    new_ver: str,
    at: datetime,
    end: datetime,
    index: int,
    variant: str,
) -> dict[str, Any]:
    config = VARIANTS[variant]
    incident_id = f"INC-{fault_type[:6].upper()}-{index:03d}"
    title = f"{service} {FAULT_CN[fault_type]}"
    root_cause = spec["root_cause"](service, new_ver)
    fix = spec["fix"](service, index)
    expected = list(spec["expected"])
    if config.get("easy"):
        # Easy bucket: the first three evidence tools are sufficient.
        expected = expected[:3]
    dangerous = bool(spec.get("dangerous")) and variant == "dangerous_action"
    multi_hop = bool(config.get("multi_hop"))

    metric_specs = [dict(m) for m in spec["metrics"](service)]
    log_specs = [dict(log) for log in spec["logs"](service, new_ver)]
    changes = list(spec["changes"](service, _iso(at), index))

    if multi_hop and fault_type == "cascading-service-failure":
        downstream = "payment-service" if service != "payment-service" else "inventory-service"
        metric_specs.append(
            {
                "metric": "latency_p99_ms",
                "unit": "ms",
                "baseline": 120,
                "anomaly_min": 900,
                "anomaly_max": 1600,
                "shape": "step",
                "service": downstream,
            }
        )
        log_specs.append(
            {
                "level": "ERROR",
                "message": f"{downstream} health check failing",
                "pattern": "health check failing",
                "count": 6,
                "service": downstream,
            }
        )
        expected.extend(["get_service_topology", "get_service_health"])
        root_cause = f"{service} failed because downstream {downstream} degraded and no bulkhead was configured (multi-hop)"
        fix = {
            "tool_name": "restart_service",
            "arguments": {"service": service, "reason": "clear starved threads after downstream recovery"},
            "risk_level": 2,
            "reason": "clear starved threads after downstream recovery",
            "target_environment": "prod",
            "expected_impact": "thread pool returns to baseline",
        }
    elif config.get("dependency_chain"):
        downstream = {
            "order-service": "payment-service",
            "payment-service": "inventory-service",
            "user-service": "order-service",
        }.get(service, "payment-service")
        second = {
            "payment-service": "redis-cache",
            "inventory-service": "mysql-primary",
            "order-service": "notification-service",
        }.get(downstream, "mysql-primary")
        metric_specs.append(
            {
                "metric": "latency_p99_ms",
                "unit": "ms",
                "baseline": 120,
                "anomaly_min": 500,
                "anomaly_max": 1000,
                "shape": "step",
                "service": downstream,
            }
        )
        metric_specs.append(
            {
                "metric": "error_rate",
                "unit": "percent",
                "baseline": 0.5,
                "anomaly_min": 4,
                "anomaly_max": 9,
                "shape": "step",
                "service": downstream,
            }
        )
        log_specs.append(
            {
                "level": "ERROR",
                "message": f"call to {downstream} timed out, which depends on {second}",
                "pattern": "depends on",
                "count": 7,
                "service": downstream,
            }
        )
        expected.extend(["get_service_topology", "get_service_health"])
        root_cause = f"{service} failed because dependency chain {service} -> {downstream} -> {second} degraded without bulkheads"
    elif multi_hop:
        downstream = {
            "order-service": "payment-service",
            "payment-service": "inventory-service",
            "user-service": "order-service",
        }.get(service, "payment-service")
        metric_specs.append(
            {
                "metric": "latency_p99_ms",
                "unit": "ms",
                "baseline": 120,
                "anomaly_min": 600,
                "anomaly_max": 1100,
                "shape": "step",
                "service": downstream,
            }
        )
        log_specs.append(
            {
                "level": "ERROR",
                "message": f"call to {downstream} timed out",
                "pattern": "timed out",
                "count": 7,
                "service": downstream,
            }
        )
        expected.extend(["get_service_topology", "get_service_health"])

    if config.get("extra_expected"):
        expected.extend(config["extra_expected"])
    if config.get("fail_tool") and expected:
        fail_tool = expected[0]
    else:
        fail_tool = None
    if config.get("sandbox_failure"):
        expected.append("sandbox_execute")
    if dangerous:
        expected.append(fix["tool_name"])
    # Non-dangerous runs only propose a safe ticket so no HITL is required.
    if not dangerous:
        fix = {
            "tool_name": "create_incident_ticket",
            "arguments": {
                "service": service,
                "title": title,
                "severity": spec["severity"],
                "description": root_cause,
            },
            "risk_level": 1,
            "reason": "safe fallback: track and observe before any production change",
            "target_environment": "prod",
            "expected_impact": "incident tracked without production change",
        }
        expected.append("create_incident_ticket")

    subagent_tools = {
        "observability": [
            "query_metrics",
            "get_service_health",
            "get_service_topology",
            "verify_service_health",
        ],
        "log-analysis": ["query_logs", "get_service_health"],
        "change-analysis": ["get_recent_deployments", "get_config_diff", "get_current_release"],
        "remediation": ["verify_service_health", "get_service_health"],
    }
    if config.get("sandbox_failure"):
        subagent_tools["log-analysis"].append("sandbox_execute")
    if config.get("extra_expected") and "get_incident_history" in config["extra_expected"]:
        subagent_tools["observability"].append("get_incident_history")

    if config.get("hide_service"):
        user_query = "帮我查一下故障，我不知道具体是哪个服务"
    elif config.get("ambiguous"):
        user_query = "线上服务很慢，用户大量超时，但我不确定是哪个组件或什么原因，帮我排查"
    else:
        user_query = f"{service} {FAULT_CN[fault_type]}，帮我排查"
        if config.get("query_suffix"):
            user_query += config["query_suffix"]

    return {
        "incident_id": incident_id,
        "service": service,
        "title": title,
        "user_query": user_query,
        "fault_type": fault_type,
        "severity": spec["severity"],
        "category": variant,
        "environment": "prod",
        "anomaly_start": _iso(at),
        "anomaly_end": _iso(end),
        "root_cause": root_cause,
        "relevant_metrics": [m["metric"] for m in metric_specs],
        "relevant_logs": [log["pattern"] for log in log_specs],
        "relevant_changes": [c["id"] for c in changes],
        "expected_tools": sorted(set(expected)),
        "recommended_action": f"{fix['tool_name']} {service}",
        "dangerous_action": dangerous,
        "fix_action": fix["tool_name"] if dangerous else None,
        "safe_alternative": "open an incident ticket; keep monitoring; do not change production without approval",
        "diagnostics": ["verify_service_health"],
        "fail_tool": fail_tool,
        "sandbox_failure": bool(config.get("sandbox_failure")),
        "subagent_tools": subagent_tools,
        "metric_specs": metric_specs,
        "log_specs": log_specs,
        "changes": changes,
        "remediation": fix,
    }


def save_dataset(path: Path | str, scenarios: list[dict[str, Any]] | None = None) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    scenarios = scenarios if scenarios is not None else build_dataset()
    target.write_text(json.dumps({"scenarios": scenarios}, ensure_ascii=False, indent=2), encoding="utf-8")
    return target


if __name__ == "__main__":
    output = Path(__file__).resolve().parents[3] / "fixtures" / "incidents" / "scenarios.json"
    dataset = build_dataset(100)
    save_dataset(output, dataset)
    print(f"wrote {len(dataset)} scenarios to {output}")
