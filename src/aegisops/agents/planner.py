"""Planning: structured incident plan generation with deterministic fallback."""

from __future__ import annotations

from typing import Any

from aegisops.agents.models import IncidentPlan, PlanStep
from aegisops.llm.base import ModelAdapter
from aegisops.llm.models import LLMMessage
from aegisops.llm.structured import StructuredOutputError, generate_structured

# Canonical 13-step AIOps triage chain (matching the prompt's example flow).
PLAN_TEMPLATE: list[tuple[str, str, str]] = [
    ("triage", "确认故障服务与环境", "main"),
    ("health", "查询服务健康指标", "observability"),
    ("metrics", "确定异常开始时间与指标偏离", "observability"),
    ("logs", "查询异常窗口日志并聚类错误模式", "log-analysis"),
    ("changes", "查询最近部署与配置变更", "change-analysis"),
    ("dependencies", "检查上下游依赖健康", "observability"),
    ("hypothesis", "汇总证据并形成 Root-Cause Hypothesis", "main"),
    ("diagnose", "运行安全诊断验证根因", "remediation"),
    ("remediation", "生成修复方案与安全分级", "remediation"),
    ("hitl", "高风险操作请求人工批准", "main"),
    ("execute", "执行获批修复动作", "main"),
    ("verify", "执行后验证服务恢复", "observability"),
    ("report", "生成 Incident Report", "main"),
]


def build_default_plan() -> IncidentPlan:
    return IncidentPlan(
        steps=[PlanStep(id=step_id, title=title, agent=agent) for step_id, title, agent in PLAN_TEMPLATE]
    )


async def generate_incident_plan(
    adapter: ModelAdapter,
    *,
    service: str,
    user_query: str,
    environment: str,
    time_range_start: str,
    time_range_end: str,
) -> IncidentPlan:
    """Ask the model for a plan; fall back to the canonical template on failure."""
    fallback = build_default_plan()
    messages = [
        LLMMessage(
            role="system",
            content=(
                "You are the Incident Commander planner. Produce a concise, ordered investigation "
                "plan for the AIOps incident. Agent names must be one of: main, observability, "
                "log-analysis, change-analysis, remediation. Use ids: triage, health, metrics, logs, "
                "changes, dependencies, hypothesis, diagnose, remediation, hitl, execute, verify, report. "
                "Return JSON only."
            ),
        ),
        LLMMessage(
            role="user",
            content=(
                f"service={service}\nenvironment={environment}\nwindow={time_range_start}..{time_range_end}\n"
                f"user query: {user_query}"
            ),
        ),
    ]
    try:
        plan = await generate_structured(
            adapter,
            messages,
            schema_name="IncidentPlan",
            output_model=IncidentPlan,
            max_retries=0,
        )
        if not plan.steps:
            return fallback
        return plan
    except StructuredOutputError:
        return fallback


def mark_step(plan: IncidentPlan, step_id: str, status: str) -> IncidentPlan:
    plan.mark(step_id, status)  # type: ignore[arg-type]
    return plan


def plan_summary(plan: list[dict[str, Any]]) -> str:
    return " | ".join(f"{s['id']}:{s['status']}" for s in plan)


def brief_for_step(step: dict[str, Any], state: dict[str, Any]) -> str:
    """Build the isolated task brief sent to a subagent for one plan step."""
    window = f"{state.get('time_range_start', 'unknown')} .. {state.get('time_range_end', 'unknown')}"
    return (
        f"INCIDENT TASK: {step['title']}\n"
        f"service: {state.get('service', 'unknown')}\n"
        f"environment: {state.get('environment', 'prod')}\n"
        f"anomaly window: {window}\n"
        "Return ONLY the structured JSON report described in your system prompt."
    )
