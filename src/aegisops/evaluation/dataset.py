"""Evaluation dataset loading and invariants."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_scenarios(path: Path | str) -> list[dict[str, Any]]:
    with Path(path).open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    records = data if isinstance(data, list) else data.get("scenarios", [])
    return records


def validate_dataset(scenarios: list[dict[str, Any]]) -> list[str]:
    """Return invariant violations (empty list = dataset is valid)."""
    issues: list[str] = []
    ids = [s.get("incident_id") for s in scenarios]
    if len(scenarios) < 60:
        issues.append(f"dataset too small: {len(scenarios)} < 60")
    if len(set(ids)) != len(ids):
        issues.append("duplicate incident ids")
    required = {
        "incident_id",
        "service",
        "fault_type",
        "root_cause",
        "relevant_metrics",
        "relevant_logs",
        "relevant_changes",
        "expected_tools",
        "recommended_action",
        "dangerous_action",
        "anomaly_start",
        "anomaly_end",
    }
    fault_types = {s.get("fault_type") for s in scenarios}
    for scenario in scenarios:
        missing = required - set(scenario)
        if missing:
            issues.append(f"{scenario.get('incident_id')}: missing {sorted(missing)}")
        if not scenario.get("expected_tools"):
            issues.append(f"{scenario.get('incident_id')}: empty expected_tools")
    required_faults = {
        "database-connection-pool-exhaustion",
        "bad-deployment",
        "memory-leak",
        "redis-cache-timeout",
        "upstream-dependency-timeout",
        "disk-usage-saturation",
        "traffic-spike",
        "configuration-error",
        "cpu-saturation",
        "cascading-service-failure",
    }
    missing_faults = required_faults - fault_types
    if missing_faults:
        issues.append(f"missing fault types: {sorted(missing_faults)}")
    return issues


def dataset_stats(scenarios: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "n": len(scenarios),
        "fault_types": sorted({s["fault_type"] for s in scenarios}),
        "categories": sorted({s["category"] for s in scenarios}),
        "dangerous": sum(1 for s in scenarios if s.get("dangerous_action")),
        "missing_information": sum(1 for s in scenarios if s.get("category") == "missing_information"),
        "tool_failure": sum(1 for s in scenarios if s.get("category") == "tool_failure"),
        "sandbox_failure": sum(1 for s in scenarios if s.get("sandbox_failure")),
    }
