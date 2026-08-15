"""Agent-domain Pydantic models: plans, evidence, subagent reports, actions."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

StepStatus = Literal["pending", "in_progress", "completed", "failed"]


class PlanStep(BaseModel):
    id: str
    title: str
    agent: str = "main"
    status: StepStatus = "pending"


class IncidentPlan(BaseModel):
    steps: list[PlanStep]

    def mark(self, step_id: str, status: StepStatus) -> None:
        for step in self.steps:
            if step.id == step_id:
                step.status = status
                return

    def next_pending(self) -> PlanStep | None:
        for step in self.steps:
            if step.status == "pending":
                return step
        return None


class EvidenceItem(BaseModel):
    source: str
    summary: str
    detail: dict[str, Any] = Field(default_factory=dict)
    tokens: int = 0


class ProposedAction(BaseModel):
    tool_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    risk_level: int = 0
    reason: str = ""
    target_environment: str = "prod"
    before_state: dict[str, Any] = Field(default_factory=dict)
    expected_impact: str = ""


class SubAgentReport(BaseModel):
    """Structured output returned by every subagent; the ONLY thing main sees."""

    source: str
    summary: str
    signals: list[str] = Field(default_factory=list)
    hypotheses: list[str] = Field(default_factory=list)
    evidence: list[EvidenceItem] = Field(default_factory=list)
    confidence: float = 0.0
    anomaly_start: str | None = None
    anomaly_end: str | None = None
    degraded: bool = False
    # remediation-specific fields
    proposed_actions: list[ProposedAction] = Field(default_factory=list)
    dangerous_action: bool = False
    safe_alternative: str = ""
    diagnostics: list[str] = Field(default_factory=list)


class RcaHypothesis(BaseModel):
    root_cause: str
    fault_type: str = "unknown"
    confidence: float = 0.0
    evidence_summary: str = ""
    unresolved: list[str] = Field(default_factory=list)


class RemediationProposal(BaseModel):
    proposed_actions: list[ProposedAction] = Field(default_factory=list)
    safe_alternative: str = ""
    requires_approval: bool = False
    diagnostics: list[str] = Field(default_factory=list)
    risk_assessment: str = ""


class ActionRequest(BaseModel):
    tool_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    risk_level: int
    reason: str = ""
    target_environment: str = "prod"
    before_state: dict[str, Any] = Field(default_factory=dict)
    expected_impact: str = ""


class InterruptPayload(BaseModel):
    type: Literal["missing_info", "approval"]
    message: str
    questions: list[str] = Field(default_factory=list)
    action_requests: list[ActionRequest] = Field(default_factory=list)


class Decision(BaseModel):
    type: Literal["approve", "reject"]
    tool_name: str | None = None
    comment: str = ""


class ActionRecord(BaseModel):
    tool_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    decision: str = "approved"
    result: dict[str, Any] = Field(default_factory=dict)
    at: str = ""


class IncidentReportData(BaseModel):
    incident_id: str = ""
    service: str = ""
    title: str = ""
    root_cause: str = ""
    confidence: float = 0.0
    timeline: list[dict[str, Any]] = Field(default_factory=list)
    evidence_summary: list[str] = Field(default_factory=list)
    actions_taken: list[ActionRecord] = Field(default_factory=list)
    verification: dict[str, Any] = Field(default_factory=dict)
    rejected_actions: list[ActionRecord] = Field(default_factory=list)
    safe_alternatives: list[str] = Field(default_factory=list)
    markdown: str = ""
