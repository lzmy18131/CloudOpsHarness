"""Risk policy for every production tool.

Level 0 - read-only                -> auto-execute
Level 1 - low-risk write           -> auto or policy (create ticket)
Level 2 - production-changing      -> HITL required (restart, scale)
Level 3 - high-risk destructive    -> HITL + reason + target + before-state + expected impact
                                     (rollback, apply_config_change)
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum


class RiskLevel(IntEnum):
    READ_ONLY = 0
    LOW_RISK_WRITE = 1
    PRODUCTION_CHANGING = 2
    HIGH_RISK_DESTRUCTIVE = 3


@dataclass(frozen=True)
class ToolRisk:
    name: str
    level: RiskLevel
    read_only: bool
    requires_reason: bool = False
    requires_target: bool = False
    requires_before_state: bool = False
    requires_expected_impact: bool = False


READ_ONLY_TOOLS = {
    "query_metrics",
    "query_logs",
    "get_service_health",
    "get_service_topology",
    "get_recent_deployments",
    "get_config_diff",
    "get_incident_history",
    "get_current_release",
    "get_service_catalog",
    "verify_service_health",
    "dry_run_action",
}

RISK_POLICY: dict[str, ToolRisk] = {
    **{name: ToolRisk(name=name, level=RiskLevel.READ_ONLY, read_only=True) for name in READ_ONLY_TOOLS},
    "create_incident_ticket": ToolRisk(
        name="create_incident_ticket", level=RiskLevel.LOW_RISK_WRITE, read_only=False
    ),
    "restart_service": ToolRisk(
        name="restart_service",
        level=RiskLevel.PRODUCTION_CHANGING,
        read_only=False,
        requires_reason=True,
        requires_target=True,
    ),
    "scale_service": ToolRisk(
        name="scale_service",
        level=RiskLevel.PRODUCTION_CHANGING,
        read_only=False,
        requires_reason=True,
        requires_target=True,
    ),
    "rollback_release": ToolRisk(
        name="rollback_release",
        level=RiskLevel.HIGH_RISK_DESTRUCTIVE,
        read_only=False,
        requires_reason=True,
        requires_target=True,
        requires_before_state=True,
        requires_expected_impact=True,
    ),
    "apply_config_change": ToolRisk(
        name="apply_config_change",
        level=RiskLevel.HIGH_RISK_DESTRUCTIVE,
        read_only=False,
        requires_reason=True,
        requires_target=True,
        requires_before_state=True,
        requires_expected_impact=True,
    ),
}


class RiskPolicy:
    """Policy evaluation used by the executor node and tool middleware."""

    def __init__(self, auto_approve_max_risk: int = 1) -> None:
        self.auto_approve_max_risk = auto_approve_max_risk

    def risk_for(self, tool_name: str) -> ToolRisk:
        return RISK_POLICY[tool_name]

    def requires_hitl(self, tool_name: str) -> bool:
        return self.risk_for(tool_name).level > self.auto_approve_max_risk

    def required_fields(self, tool_name: str) -> set[str]:
        risk = self.risk_for(tool_name)
        fields: set[str] = set()
        if risk.requires_reason:
            fields.add("reason")
        if risk.requires_target:
            fields.add("target_environment")
        if risk.requires_before_state:
            fields.add("before_state")
        if risk.requires_expected_impact:
            fields.add("expected_impact")
        return fields
