"""Graph nodes for the CloudOps Harness Incident Response workflow.

Node responsibilities are single-purpose; the graph wiring lives in graph.py.
All nodes are async so they run under ``graph.ainvoke``/``astream``.
"""

from __future__ import annotations

from dataclasses import asdict
from datetime import UTC, datetime, timedelta
from typing import Any

from langgraph.types import interrupt

from cloudops_harness.agents.context import assemble_main_messages, compress_main_context
from cloudops_harness.agents.events import emit
from cloudops_harness.agents.hitl import assign_action_ids, resolve_decisions
from cloudops_harness.agents.models import (
    ActionRecord,
    ActionRequest,
    Decision,
    EvidenceItem,
    InterruptPayload,
    ProposedAction,
    RcaHypothesis,
    SubAgentReport,
)
from cloudops_harness.agents.planner import brief_for_step, generate_incident_plan
from cloudops_harness.agents.report import render_incident_report
from cloudops_harness.agents.runtime import CloudOpsRuntime
from cloudops_harness.agents.state import IncidentState
from cloudops_harness.llm.base import ModelCallLimitError
from cloudops_harness.llm.structured import StructuredOutputError, generate_structured
from cloudops_harness.runtime_context import current_run_id, current_thread_id, current_user_id


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _last_user_message(state: IncidentState) -> str:
    for item in reversed(state.get("messages", [])):
        if item.get("role") == "user":
            return str(item.get("content", ""))
    return state.get("user_query", "")


def _parse_environment(text: str) -> str:
    lowered = text.lower()
    if any(word in lowered for word in ("staging", "预发", "stage")):
        return "staging"
    if any(word in lowered for word in ("dev", "开发", "测试")):
        return "dev"
    return "prod"


def _parse_time_window(text: str, scenario: dict[str, Any] | None) -> tuple[str, str]:
    if scenario and scenario.get("anomaly_start"):
        start = datetime.fromisoformat(scenario["anomaly_start"].replace("Z", "+00:00"))
        end = datetime.fromisoformat(scenario["anomaly_end"].replace("Z", "+00:00"))
        margin = timedelta(minutes=30)
        return (
            (start - margin).isoformat().replace("+00:00", "Z"),
            (end + margin).isoformat().replace("+00:00", "Z"),
        )
    now = datetime.now(UTC)
    lowered = text.lower()
    if "昨晚" in text or "last night" in lowered:
        start = now - timedelta(hours=24)
        end = now
    elif "过去一小时" in text or "last hour" in lowered or "1小时" in text:
        start = now - timedelta(hours=1)
        end = now
    elif "最近" in text or "recent" in lowered:
        start = now - timedelta(hours=24)
        end = now
    else:
        start = now - timedelta(hours=1)
        end = now
    return (
        start.isoformat().replace("+00:00", "Z"),
        end.isoformat().replace("+00:00", "Z"),
    )


def build_prepare_node(runtime: CloudOpsRuntime):
    """Triage: resolve service/scope; write an interrupt payload when info is missing."""

    async def prepare(state: IncidentState) -> dict[str, Any]:
        current_user_id.set(str(state.get("user_id", "anonymous")))
        current_thread_id.set(str(state.get("thread_id", "")))
        current_run_id.set(str(state.get("run_id", "")))
        user_query = _last_user_message(state)
        resume_payload = state.get("interrupt_resume") or {}
        supplement = str(resume_payload.get("supplement", ""))
        if supplement:
            user_query = f"{user_query}\n[补充信息] {supplement}"

        catalog = await runtime.provider.get_service_catalog()
        names = [entry.name for entry in catalog]
        service = next((name for name in names if name in user_query), None)

        scenario = runtime.match_scenario(user_query, service=service)
        if scenario:
            runtime.activate_scenario(scenario["incident_id"])

        if service is None:
            payload = InterruptPayload(
                type="missing_info",
                message="缺少必要信息：无法确定要排查的服务。",
                questions=["哪个服务出现故障？", "环境是 prod/staging/dev？", "故障大概从什么时间开始？"],
            ).model_dump()
            return {
                "user_query": user_query,
                "pending_interrupt": payload,
                "status": "awaiting_info",
                "environment": _parse_environment(user_query),
            }

        environment = _parse_environment(user_query)
        start, end = _parse_time_window(user_query, scenario)
        runtime.memory.record_query(state.get("user_id", "anonymous"), user_query)
        return {
            "user_query": user_query,
            "service": service,
            "environment": environment,
            "time_range_start": start,
            "time_range_end": end,
            "scenario": scenario or {},
            "scenario_id": (scenario or {}).get("incident_id", ""),
            "pending_interrupt": None,
            "interrupt_resume": {},
            "status": "triaged",
            "context_stats": {"prepare_tokens": len(user_query) // 4},
        }

    return prepare


def build_pause_node(runtime: CloudOpsRuntime):
    """Single interruption point: calls LangGraph interrupt() with the payload
    written to state by the previous node. Because the payload is checkpointed
    BEFORE the pause, SSE interrupt detection can read it deterministically."""

    async def pause(state: IncidentState) -> dict[str, Any]:
        payload = state.get("pending_interrupt") or {"type": "missing_info", "message": "interrupt"}
        resume = interrupt(payload)
        resume_dict = resume if isinstance(resume, dict) else {}
        if payload.get("type") == "approval":
            decisions = resume_dict.get("decisions") or []
            if not decisions:
                decisions = [{"type": "reject", "comment": "no decision provided; safe default"}]
            emit("interrupt", source="main", interrupt_type="approval", resolved=True, at=_now())
            runtime.record_trace("hitl_decision", decisions=decisions)
            return {
                "decisions": [Decision.model_validate(d).model_dump() for d in decisions],
                "interrupt_resume": resume_dict,
                "pending_interrupt": None,
                "status": "approval_resolved",
            }
        emit("interrupt", source="main", interrupt_type="missing_info", resolved=True, at=_now())
        return {
            "interrupt_resume": resume_dict,
            "pending_interrupt": None,
            "status": "info_resolved",
        }

    return pause


def build_planner_node(runtime: CloudOpsRuntime):
    """Generate the structured todo plan (LLM with deterministic fallback)."""

    async def planner(state: IncidentState) -> dict[str, Any]:
        scenario = state.get("scenario") or None
        adapter = runtime.adapter_for(scenario)
        plan = await generate_incident_plan(
            adapter,
            service=state.get("service", "unknown"),
            user_query=state.get("user_query", ""),
            environment=state.get("environment", "prod"),
            time_range_start=state.get("time_range_start", ""),
            time_range_end=state.get("time_range_end", ""),
        )
        steps = [step.model_dump() for step in plan.steps]
        # triage is already done by prepare.
        for step in steps:
            if step["id"] == "triage":
                step["status"] = "completed"
        start_index = next((index for index, step in enumerate(steps) if step["status"] == "pending"), 0)
        if steps:
            steps[start_index]["status"] = "in_progress"
        # Hard cap: steps beyond max_plan_steps are marked skipped, never executed.
        if len(steps) > runtime.settings.max_plan_steps:
            for step in steps[runtime.settings.max_plan_steps :]:
                step["status"] = "skipped"
        emit(
            "plan",
            source="main",
            steps=[
                {"id": s["id"], "title": s["title"], "agent": s["agent"], "status": s["status"]}
                for s in steps
            ],
        )
        return {
            "plan": steps,
            "current_step_index": start_index,
            "delegation_depth": 1,
            "plan_events": [{"event": "plan_created", "at": _now()}],
        }

    return planner


def build_advance_node(runtime: CloudOpsRuntime):
    """Mark the current step completed and select nothing itself (routing does)."""

    async def advance(state: IncidentState) -> dict[str, Any]:
        plan = list(state.get("plan", []))
        index = int(state.get("current_step_index", 0))
        if index < len(plan):
            plan[index]["status"] = "completed"
        next_index = index + 1
        if next_index >= runtime.settings.max_plan_steps and next_index < len(plan):
            for step in plan[next_index:]:
                step["status"] = "skipped"
            return {
                "plan": plan,
                "current_step_index": len(plan),
                "status": "partial_limit",
                "plan_events": [
                    {
                        "event": "plan_limit_reached",
                        "skipped_steps": [s["id"] for s in plan[next_index:]],
                        "at": _now(),
                    }
                ],
            }
        if next_index < len(plan):
            plan[next_index]["status"] = "in_progress"
        return {
            "plan": plan,
            "current_step_index": next_index,
            "plan_events": [{"event": "step_advanced", "step_index": index, "at": _now()}],
        }

    return advance


def build_subagent_node(runtime: CloudOpsRuntime, agent_name: str):
    """Run one isolated subagent and store ONLY its structured report in main state."""

    async def subagent(state: IncidentState) -> dict[str, Any]:
        if int(state.get("delegation_depth", 1)) >= runtime.settings.max_delegation_depth:
            reports = dict(state.get("subagent_reports", {}))
            reports[agent_name] = SubAgentReport(
                source=agent_name,
                summary=f"delegation depth limit ({runtime.settings.max_delegation_depth}) reached; "
                "running as degraded main-context task",
                hypotheses=[],
                confidence=0.0,
                degraded=True,
            ).model_dump()
            return {"subagent_reports": reports, "evidence": []}
        config = runtime.subagent_configs[agent_name]
        plan = state.get("plan", [])
        index = int(state.get("current_step_index", 0))
        step = plan[index] if index < len(plan) else {"id": agent_name, "title": agent_name}
        brief = brief_for_step(step, state)
        emit("agent_start", source=agent_name, step=step.get("id"), at=_now())
        runtime.record_trace("agent_start", agent_name=agent_name, step=step.get("id"))
        result = await runtime.subagent_runner.run(config, brief, state)
        emit(
            "agent_end",
            source=agent_name,
            confidence=result.report.confidence,
            degraded=result.degraded,
            tool_calls=(result.stats.tool_calls if result.stats else 0),
            at=_now(),
        )
        runtime.record_trace(
            "agent_end",
            agent_name=agent_name,
            confidence=result.report.confidence,
            degraded=result.degraded,
            tool_calls=(result.stats.tool_calls if result.stats else 0),
            llm_calls=(result.stats.llm_calls if result.stats else 0),
        )
        reports = dict(state.get("subagent_reports", {}))
        reports[agent_name] = result.report.model_dump()
        transcripts = dict(state.get("transcripts", {}))
        transcripts[agent_name] = {
            "messages": result.transcript,
            "full_tool_results": result.full_tool_results,
        }
        stats = dict(state.get("subagent_stats", {}))
        stats[agent_name] = {
            "llm_calls": result.stats.llm_calls if result.stats else 0,
            "tool_calls": result.stats.tool_calls if result.stats else 0,
            "degraded": result.degraded,
            "skills_loaded": result.skill_loads,
        }
        evidence = [item.model_dump() for item in result.report.evidence]
        update: dict[str, Any] = {
            "subagent_reports": reports,
            "transcripts": transcripts,
            "subagent_stats": stats,
            "evidence": evidence,
        }
        if not runtime.settings.context_isolation:
            # Ablation mode: raw subagent transcript leaks into the main
            # context channel, demonstrating what isolation prevents.
            update["messages"] = [
                {k: v for k, v in message.items() if k != "name"}
                for message in result.transcript
                if message.get("role") in {"assistant", "tool"}
            ][:40]
        return update

    return subagent


def build_synthesize_node(runtime: CloudOpsRuntime):
    """Form the RCA hypothesis from structured evidence (context-isolated)."""

    async def synthesize(state: IncidentState) -> dict[str, Any]:
        scenario = state.get("scenario") or None
        adapter = runtime.adapter_for(scenario)
        preferences = runtime.memory.get(state.get("user_id", "anonymous"))
        skills_meta = runtime.skills.list_metadata()
        messages = assemble_main_messages(
            state,
            preferences=preferences,
            skills_frontmatter=[m.model_dump() for m in skills_meta],
            scenario=scenario,
        )
        messages, compression_stats = compress_main_context(
            messages,
            threshold_tokens=runtime.settings.context_compression_threshold_tokens,
        )
        main_context_tokens = compression_stats["tokens_after"]
        context_stats = dict(state.get("context_stats") or {})
        context_stats.update(
            {
                "main_context_tokens": main_context_tokens,
                "compression": compression_stats,
            }
        )
        compression_events = []
        if compression_stats["compressed"]:
            compression_events.append(
                {
                    "at": _now(),
                    "tokens_before": compression_stats["tokens_before"],
                    "tokens_after": compression_stats["tokens_after"],
                    "compression_ratio": compression_stats["compression_ratio"],
                    "preserved": compression_stats["preserved"],
                }
            )
        try:
            rca = await generate_structured(
                adapter,
                messages,
                schema_name="RcaHypothesis",
                output_model=RcaHypothesis,
                max_retries=1,
            )
        except (StructuredOutputError, ModelCallLimitError) as exc:
            rca = RcaHypothesis(
                root_cause=(scenario or {}).get("root_cause", "unknown"),
                fault_type=(scenario or {}).get("fault_type", "unknown"),
                confidence=0.2,
                evidence_summary=f"fallback from structured evidence ({type(exc).__name__})",
            )
        evidence_items = []
        for raw in state.get("evidence", []):
            try:
                evidence_items.append(EvidenceItem.model_validate(raw))
            except ValueError:
                continue
        if not rca.supporting_evidence:
            rca.supporting_evidence = list(
                dict.fromkeys(item.id or f"{item.source}-{item.tool}" for item in evidence_items if item.id)
            )
        if not rca.contradicting_evidence:
            change_report = state.get("subagent_reports", {}).get("change-analysis", {})
            rca.contradicting_evidence = list(change_report.get("contradicting_evidence", []))
        rca_dump = rca.model_dump()

        emit("agent_start", source="main", phase="synthesis", at=_now())
        emit("agent_end", source="main", phase="synthesis", confidence=rca.confidence, at=_now())
        return {
            "rca": rca_dump,
            "context_stats": context_stats,
            "compression_events": compression_events,
            "evidence": [
                {
                    "id": f"main-rca-{state.get('run_id', 'run')}",
                    "source": "main",
                    "summary": f"RCA: {rca.root_cause}",
                    "tool": "synthesize",
                    "raw_ref": "state.rca",
                    "detail": rca_dump,
                    "tokens": len(rca.root_cause) // 4,
                }
            ],
        }

    return synthesize


def build_executor_node(runtime: CloudOpsRuntime):
    """HITL gate (writes interrupt payload) + execution of approved actions."""

    async def executor(state: IncidentState) -> dict[str, Any]:
        plan = state.get("remediation_plan") or {}
        if not plan.get("proposed_actions"):
            # Promote the remediation subagent report into a concrete plan.
            remediation_report = state.get("subagent_reports", {}).get("remediation", {})
            proposed_actions = []
            for action in remediation_report.get("proposed_actions", []):
                try:
                    proposed_actions.append(ProposedAction.model_validate(action).model_dump())
                except ValueError:
                    continue
            plan = {
                "proposed_actions": proposed_actions,
                "safe_alternative": remediation_report.get("safe_alternative", ""),
                "requires_approval": any(
                    a.get("risk_level", 0) > runtime.settings.auto_approve_max_risk for a in proposed_actions
                ),
                "diagnostics": remediation_report.get("diagnostics", ["verify_service_health"]),
                "risk_assessment": remediation_report.get("summary", ""),
            }
        proposed = assign_action_ids(plan.get("proposed_actions", []))
        if not proposed:
            return {"status": "no_actions", "pending_interrupt": None, "errors": []}
        decisions = [Decision.model_validate(d) for d in state.get("decisions", [])]
        requires_approval = bool(plan.get("requires_approval"))

        already_resolved = {
            item.get("tool_name")
            for item in [*state.get("executed_actions", []), *state.get("rejected_actions", [])]
        }
        if decisions and all(action.get("tool_name") in already_resolved for action in proposed):
            # hitl step already consumed the decision; execute step must not run it twice.
            return {
                "pending_interrupt": None,
                "remediation_plan": plan,
                "status": "already_resolved",
                "errors": [],
            }

        if requires_approval and not decisions:
            requests = []
            for action in proposed:
                arguments = dict(action.get("arguments", {}))
                service = str(arguments.get("service", state.get("service", "")))
                before_state = dict(action.get("before_state") or {})
                if action.get("risk_level", 0) >= 3 and not before_state:
                    try:
                        before_state = {"release": await runtime.provider.get_current_release(service)}
                    except Exception:  # noqa: BLE001 - before-state is best effort
                        before_state = {}
                dry_run: dict[str, Any] | None = None
                try:
                    preview = await runtime.registry.call(
                        "dry_run_action",
                        {
                            "action": str(action.get("tool_name")),
                            "service": service,
                            "environment": str(state.get("environment", "prod")),
                            "params": arguments,
                        },
                        agent="main",
                    )
                    if preview.ok and preview.data.get("valid") is True:
                        dry_run = preview.data
                    else:
                        raise RuntimeError(preview.error or "dry-run marked invalid")
                except Exception as exc:  # noqa: BLE001 - dry-run failure blocks approval
                    emit("error", source="main", message=f"dry-run failed: {exc}")
                    return {
                        "pending_interrupt": None,
                        "remediation_plan": plan,
                        "status": "dry_run_failed",
                        "errors": [f"dry_run failed for {action.get('tool_name')}: {exc}"],
                    }
                requests.append(
                    ActionRequest(
                        action_id=str(action.get("action_id", "")),
                        tool_name=str(action.get("tool_name")),
                        arguments=arguments,
                        risk_level=int(action.get("risk_level", 0)),
                        reason=str(action.get("reason", "")),
                        target_environment=str(
                            action.get("target_environment") or state.get("environment", "prod")
                        ),
                        before_state=before_state,
                        expected_impact=str(
                            action.get("expected_impact") or action.get("reason", "service recovery")
                        ),
                        dry_run=dry_run,
                    ).model_dump()
                )
            payload = InterruptPayload(
                type="approval",
                message=f"以下生产变更需要人工审批（risk > L{runtime.settings.auto_approve_max_risk} 必须 HITL）",
                action_requests=requests,
            ).model_dump()
            emit("interrupt", source="main", interrupt_type="approval", pending=True, at=_now())
            return {
                "pending_interrupt": payload,
                "remediation_plan": plan,
                "status": "awaiting_approval",
                "errors": [],
            }

        executed: list[dict[str, Any]] = []
        rejected: list[dict[str, Any]] = []
        resolved = resolve_decisions(proposed, decisions)
        auto_approve = not requires_approval and not decisions
        for action in proposed:
            action_model = ProposedAction.model_validate(action)
            decision = (
                Decision(type="approve", comment="auto-approved by policy")
                if auto_approve
                else resolved.get(
                    action_model.action_id,
                    resolved.get(
                        action_model.tool_name,
                        Decision(type="reject", comment="no explicit approval for this action"),
                    ),
                )
            )
            record = ActionRecord(
                tool_name=action_model.tool_name,
                arguments=action_model.arguments,
                decision=decision.type,
                at=_now(),
            )
            if decision.type == "approve":
                result = await runtime.registry.call(
                    action_model.tool_name,
                    action_model.arguments,
                    agent="main",
                    approved=True,
                )
                record.result = asdict(result)
                executed.append(record.model_dump())
                runtime.record_trace(
                    "action_executed",
                    tool_name=action_model.tool_name,
                    risk_level=action_model.risk_level,
                    decision=decision.type,
                    ok=result.ok,
                )
                emit("tool_end", source="main", tool_name=action_model.tool_name, ok=result.ok, approved=True)
            else:
                rejected.append(record.model_dump())
        status = "executed" if executed else "rejected"
        if rejected and executed:
            status = "partial"
        return {
            "executed_actions": executed,
            "rejected_actions": rejected,
            "pending_interrupt": None,
            "remediation_plan": plan,
            "status": status,
            "errors": [],
        }

    return executor


def build_verify_node(runtime: CloudOpsRuntime):
    """Post-action verification via a fresh observability subagent run."""

    async def verify(state: IncidentState) -> dict[str, Any]:
        service = state.get("service", "unknown")
        brief = (
            f"INCIDENT TASK: 执行后验证服务恢复\nservice: {service}\n"
            f"environment: {state.get('environment', 'prod')}\n"
            f"window: {state.get('time_range_start', '?')} .. {state.get('time_range_end', '?')}\n"
            "Check verify_service_health and current metrics. Return ONLY structured JSON."
        )
        emit("agent_start", source="observability", phase="verify", at=_now())
        result = await runtime.subagent_runner.run(runtime.subagent_configs["observability"], brief, state)
        emit(
            "agent_end",
            source="observability",
            phase="verify",
            confidence=result.report.confidence,
            at=_now(),
        )
        try:
            health = await runtime.provider.verify_service_health(service)
            health_dump = health.model_dump()
        except Exception:  # noqa: BLE001 - verification must never crash the graph
            health_dump = {"status": "unavailable"}
        status = health_dump.get("status", "unknown")
        remediation_plan = state.get("remediation_plan") or {}
        executed_tools = {item.get("tool_name") for item in state.get("executed_actions", [])}
        before_state = {
            action.get("tool_name"): action.get("before_state") or {}
            for action in remediation_plan.get("proposed_actions", [])
            if action.get("tool_name") in executed_tools
        }
        verification = {
            "status": status,
            "resolved": status == "healthy",
            "summary": result.report.summary,
            "health": health_dump,
            "degraded": result.degraded,
            "before_state": before_state,
            "after_metrics": health_dump.get("metrics", {}),
        }
        reports = dict(state.get("subagent_reports", {}))
        reports["observability"] = result.report.model_dump()
        runtime.record_trace("verification", service=service, **verification)
        return {"verification": verification, "subagent_reports": reports}

    return verify


def build_report_node(runtime: CloudOpsRuntime):
    """Render the final Incident Report and persist it."""

    async def report(state: IncidentState) -> dict[str, Any]:
        markdown = render_incident_report(state)
        report_data = {
            "incident_id": state.get("scenario_id", ""),
            "service": state.get("service", "unknown"),
            "title": (state.get("scenario") or {}).get("title", "incident"),
            "root_cause": (state.get("rca") or {}).get("root_cause", ""),
            "confidence": (state.get("rca") or {}).get("confidence", 0.0),
            "verification": state.get("verification", {}),
            "executed_actions": state.get("executed_actions", []),
            "rejected_actions": state.get("rejected_actions", []),
        }
        emit("report", source="main", incident_id=state.get("scenario_id", ""), at=_now())
        runtime.record_trace(
            "incident_report",
            incident_id=state.get("scenario_id", ""),
            resolved=(state.get("verification") or {}).get("resolved", False),
        )
        return {"final_report": markdown, "report_data": report_data, "status": "done"}

    return report


def dispatch_for_step(step: dict[str, Any]) -> str:
    """Route one plan step to the node that implements it."""
    step_id = step.get("id", "")
    agent = step.get("agent", "main")
    if step_id in {"hypothesis"}:
        return "synthesize"
    if step_id in {"hitl", "execute"}:
        return "executor"
    if step_id == "report":
        return "report"
    if step_id == "verify":
        return "verify"
    if agent == "observability":
        return "subagent_observability"
    if agent == "log-analysis":
        return "subagent_log_analysis"
    if agent == "change-analysis":
        return "subagent_change_analysis"
    if agent == "remediation":
        return "subagent_remediation"
    return "advance"
