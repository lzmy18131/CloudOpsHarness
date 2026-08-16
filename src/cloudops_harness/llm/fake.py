"""Deterministic offline LLM used by tests, CI and the offline evaluation.

Two operating modes:

* **Scripted**: ``FakeLLM(script=[ScriptedTurn(...)])`` replays fixed turns.
* **Scenario-driven**: give ``FakeLLM(scenario=...)`` a scenario dict and it
  acts as a rule-based Incident Commander: it picks the next expected
  read-only tool, builds valid arguments from the scenario ground truth, and
  returns structured JSON matching the Pydantic schemas used by the graph.

The scenario-driven mode is explicitly a *harness correctness* driver, not a
language model. Real-model evaluation uses OpenAICompatibleAdapter with the
same interfaces and is run separately (``scripts/run_real_eval.py``).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any

from cloudops_harness.llm.base import ModelAdapter
from cloudops_harness.llm.models import AssistantTurn, LLMMessage, ToolCall, Usage


@dataclass
class ScriptedTurn:
    """One deterministic FakeLLM reply."""

    content: str = ""
    tool_call_name: str | None = None
    tool_call_args: dict[str, Any] = field(default_factory=dict)
    json_payload: dict[str, Any] | None = None
    match: str | None = None  # require this substring in the conversation to fire


class FakeLLM(ModelAdapter):
    """Rule-based ModelAdapter with full call recording."""

    name = "fake-llm"

    def __init__(
        self,
        script: list[ScriptedTurn] | None = None,
        scenario: dict[str, Any] | None = None,
        scenario_index: dict[str, dict[str, Any]] | None = None,
        default_content: str = "Understood. I will proceed step by step.",
    ) -> None:
        self.script = list(script or [])
        self._script_cursor = 0
        self.scenario = scenario
        self.scenario_index = scenario_index or {}
        self.default_content = default_content
        self.calls: list[dict[str, Any]] = []
        self.called_tools: set[str] = set()
        self._call_counter = 0

    # ------------------------------------------------------------------ API
    async def generate(
        self,
        messages: list[LLMMessage],
        tools: list[dict[str, Any]] | None = None,
        response_format: dict[str, Any] | None = None,
    ) -> AssistantTurn:
        self._call_counter += 1
        self.call_count = self._call_counter
        context = "\n".join(f"{m.role}: {m.content}" for m in messages)
        self.usage_total += self.estimate_tokens(context) + 16
        tool_names = [t["function"]["name"] for t in tools or []]
        self.calls.append(
            {
                "call": self._call_counter,
                "messages": [m.model_dump() for m in messages],
                "tool_names": tool_names,
                "response_format": response_format,
            }
        )

        scenario = self._find_scenario(context)
        if response_format is not None:
            scripted = self._find_scripted_turn(context)
            if scripted is not None:
                self._consume_scripted(scripted[0])
                payload = scripted[1].json_payload
                content = (
                    json.dumps(payload, ensure_ascii=False)
                    if payload is not None
                    else (scripted[1].content or "{}")
                )
                self._emit_tokens(content, context)
                return AssistantTurn(
                    content=content,
                    finish_reason="stop",
                    usage=Usage(
                        prompt_tokens=self.estimate_tokens(context),
                        completion_tokens=len(content) // 4,
                    ),
                )
            payload = self._structured_payload(response_format, scenario, messages, tool_names, context)
            content = json.dumps(payload, ensure_ascii=False)
            self._emit_tokens(content, context)
            return AssistantTurn(
                content=content,
                finish_reason="stop",
                usage=Usage(
                    prompt_tokens=self.estimate_tokens(context),
                    completion_tokens=len(content) // 4,
                ),
            )

        if tools:
            scripted = self._find_scripted_turn(context)
            if scripted is not None and scripted[1].tool_call_name:
                self._consume_scripted(scripted[0])
                return AssistantTurn(
                    content="",
                    tool_calls=[
                        ToolCall(
                            id=f"fake-call-{self._call_counter}",
                            name=scripted[1].tool_call_name,
                            arguments=scripted[1].tool_call_args,
                        )
                    ],
                    finish_reason="tool_calls",
                    usage=Usage(prompt_tokens=self.estimate_tokens(context)),
                )
            if scenario:
                tool_call = self._pick_tool(scenario, tool_names)
                if tool_call is not None:
                    return AssistantTurn(
                        content="",
                        tool_calls=[tool_call],
                        finish_reason="tool_calls",
                        usage=Usage(prompt_tokens=self.estimate_tokens(context)),
                    )

        scripted = self._find_scripted_turn(context)
        if scripted is not None:
            self._consume_scripted(scripted[0])
            content = scripted[1].content or self.default_content
            self._emit_tokens(content, context)
            return AssistantTurn(
                content=content,
                finish_reason="stop",
                usage=Usage(prompt_tokens=self.estimate_tokens(context)),
            )
        if scenario:
            content = self._scenario_final_text(scenario)
            self._emit_tokens(content, context)
            return AssistantTurn(
                content=content,
                finish_reason="stop",
                usage=Usage(prompt_tokens=self.estimate_tokens(context)),
            )
        self._emit_tokens(self.default_content, context)
        return AssistantTurn(
            content=self.default_content,
            finish_reason="stop",
            usage=Usage(prompt_tokens=self.estimate_tokens(context)),
        )

    # -------------------------------------------------------------- helpers
    def _emit_tokens(self, content: str, context: str) -> None:
        if self.token_callback is None or not content:
            return
        source = self._role_from_context(context)
        for index in range(0, len(content), 16):
            self.token_callback({"type": "token", "content": content[index : index + 16], "source": source})

    def _find_scenario(self, context: str) -> dict[str, Any] | None:
        if self.scenario is not None:
            return self.scenario
        match = re.search(r"INCIDENT_ID[:=]\s*(INC-[A-Za-z0-9-]+)", context)
        if match and match.group(1) in self.scenario_index:
            return self.scenario_index[match.group(1)]
        return None

    def _find_scripted_turn(self, context: str) -> tuple[int, ScriptedTurn] | None:
        for index, candidate in enumerate(self.script):
            if index < self._script_cursor:
                continue
            if candidate.match and candidate.match not in context:
                continue
            return index, candidate
        return None

    def _consume_scripted(self, index: int) -> None:
        self._script_cursor = index + 1

    def _pick_tool(self, scenario: dict[str, Any], tool_names: list[str]) -> ToolCall | None:
        role = self._role_from_context(str(self.calls[-1]["messages"]))
        expected = scenario.get("expected_tools", [])
        allowed = scenario.get("subagent_tools", {})
        for name in tool_names:
            if name in self.called_tools:
                continue
            if allowed and role in allowed and name in allowed[role]:
                self.called_tools.add(name)
                return ToolCall(
                    id=f"fake-call-{self._call_counter}-{name}",
                    name=name,
                    arguments=self._tool_args(scenario, name),
                )
            if (not allowed or role not in allowed) and name in expected:
                self.called_tools.add(name)
                return ToolCall(
                    id=f"fake-call-{self._call_counter}-{name}",
                    name=name,
                    arguments=self._tool_args(scenario, name),
                )
        return None

    def _role_from_context(self, raw: str) -> str:
        match = re.search(r"AGENT_ROLE:\s*([a-z-]+)", raw)
        return match.group(1) if match else "main"

    def _tool_args(self, scenario: dict[str, Any], tool_name: str) -> dict[str, Any]:
        service = scenario["service"]
        start = scenario["anomaly_start"]
        end = scenario["anomaly_end"]
        if tool_name == "query_metrics":
            metric = scenario.get("metric_specs", [{}])[0].get("metric", "latency_p99_ms")
            return {"service": service, "metric": metric, "start": start, "end": end}
        if tool_name == "query_logs":
            pattern = scenario.get("log_specs", [{}])[0].get("pattern", "error")
            return {"service": service, "start": start, "end": end, "pattern": pattern, "limit": 100}
        if tool_name in {
            "get_service_health",
            "get_service_topology",
            "get_recent_deployments",
            "get_config_diff",
            "get_incident_history",
            "get_current_release",
            "verify_service_health",
            "get_service_catalog",
        }:
            args: dict[str, Any] = {"service": service}
            if tool_name == "get_recent_deployments":
                args["limit"] = 10
            return args
        remediation = scenario.get("remediation", {})
        if remediation.get("tool") == tool_name:
            args = dict(remediation.get("args", {}))
            args.setdefault("reason", scenario.get("recommended_action", "remediation"))
            return args
        if tool_name == "restart_service":
            return {"service": service, "reason": scenario.get("recommended_action", "restart to recover")}
        if tool_name == "scale_service":
            return {
                "service": service,
                "replicas": 12,
                "reason": scenario.get("recommended_action", "scale out"),
            }
        if tool_name == "rollback_release":
            previous = scenario.get("changes", [{}])[0].get("from_version", "v0.0.0")
            return {
                "service": service,
                "to_version": previous,
                "reason": scenario.get("recommended_action", "rollback"),
            }
        if tool_name == "apply_config_change":
            change = next((c for c in scenario.get("changes", []) if c.get("kind") == "config"), {})
            return {
                "service": service,
                "key": change.get("config_path", "config"),
                "value": change.get("restore_value", change.get("before", "")),
                "reason": scenario.get("recommended_action", "restore configuration"),
            }
        if tool_name == "sandbox_execute":
            return {"command": "python -c \"print('sandbox-ok')\"", "timeout_seconds": 5}
        if tool_name == "sandbox_read_file":
            return {"path": "analysis.txt"}
        if tool_name == "sandbox_write_file":
            return {"path": "analysis.txt", "content": "sandbox evidence"}
        if tool_name == "create_incident_ticket":
            return {
                "service": service,
                "title": scenario.get("title", "incident"),
                "severity": scenario.get("severity", "P1"),
                "description": scenario.get("root_cause", "incident"),
            }
        return {}

    def _structured_payload(
        self,
        response_format: dict[str, Any],
        scenario: dict[str, Any] | None,
        messages: list[LLMMessage],
        tool_names: list[str],
        context: str,
    ) -> dict[str, Any]:
        schema_name = self._schema_name(response_format)
        role = self._role_from_context(context)
        if schema_name in {"IncidentPlan", "plan"}:
            return self._plan_payload(scenario)
        if schema_name in {"SubAgentReport", "subagent_report"}:
            return self._subagent_payload(role, scenario, messages)
        if schema_name in {"RcaHypothesis", "rca"}:
            if scenario:
                return {
                    "root_cause": scenario["root_cause"],
                    "confidence": 0.9,
                    "evidence_summary": f"evidence from {', '.join(scenario.get('relevant_metrics', []) + scenario.get('relevant_logs', []))}",
                    "unresolved": [],
                    "fault_type": scenario["fault_type"],
                }
            return {
                "root_cause": "unknown",
                "confidence": 0.1,
                "evidence_summary": "",
                "unresolved": ["insufficient evidence"],
                "fault_type": "unknown",
            }
        if schema_name in {"RemediationProposal", "remediation"}:
            return self._remediation_payload(scenario)
        if schema_name in {"IncidentReport", "report"}:
            return {"report": self._scenario_final_text(scenario) if scenario else self.default_content}
        return {"result": self.default_content}

    def _schema_name(self, response_format: dict[str, Any]) -> str:
        schema = response_format.get("json_schema") or {}
        return str(schema.get("name", response_format.get("aegis_schema", "unknown")))

    def _plan_payload(self, scenario: dict[str, Any] | None) -> dict[str, Any]:
        steps = [
            ("triage", "确认故障服务与环境", "main"),
            ("health", "查询服务健康状态与关键指标", "observability"),
            ("metrics", "分析异常窗口内的 metrics", "observability"),
            ("logs", "查询并聚类异常窗口日志", "log-analysis"),
            ("changes", "核对最近部署与配置变更", "change-analysis"),
            ("dependencies", "检查上下游依赖健康", "observability"),
            ("hypothesis", "汇总证据并形成 RCA hypothesis", "main"),
            ("diagnose", "运行安全诊断验证根因", "remediation"),
            ("remediation", "制定修复方案并评估风险", "remediation"),
            ("hitl", "高风险操作申请人工审批", "main"),
            ("execute", "执行获批修复动作", "main"),
            ("verify", "验证服务恢复", "observability"),
            ("report", "生成 Incident Report", "main"),
        ]
        return {
            "steps": [
                {"id": step_id, "title": title, "agent": agent, "status": "pending"}
                for step_id, title, agent in steps
            ]
        }

    def _subagent_payload(
        self, role: str, scenario: dict[str, Any] | None, messages: list[LLMMessage]
    ) -> dict[str, Any]:
        if scenario is None:
            return {
                "source": role,
                "summary": "no scenario loaded",
                "signals": [],
                "hypotheses": [],
                "evidence": [],
                "confidence": 0.0,
                "anomaly_start": None,
                "anomaly_end": None,
            }
        service = scenario["service"]
        evidence = [
            {"source": role, "tool": name, "summary": self._evidence_summary(scenario, name)}
            for name in scenario.get("expected_tools", [])
        ]
        base = {
            "source": role,
            "summary": f"{service}: {scenario['title']}",
            "signals": list(scenario.get("relevant_metrics", [])),
            "hypotheses": [f"{scenario['fault_type']}: {scenario['root_cause']}"],
            "evidence": evidence,
            "confidence": 0.85,
            "anomaly_start": scenario["anomaly_start"],
            "anomaly_end": scenario["anomaly_end"],
        }
        if role == "observability":
            base["summary"] = (
                f"{service} health degraded during anomaly window; metrics confirm {', '.join(scenario.get('relevant_metrics', []))} deviation"
            )
        elif role == "log-analysis":
            base["summary"] = (
                f"log analysis found {len(scenario.get('log_specs', []))} error pattern(s): {', '.join(s['pattern'] for s in scenario.get('log_specs', []))}"
            )
            base["signals"] = [s["pattern"] for s in scenario.get("log_specs", [])]
        elif role == "change-analysis":
            changes = scenario.get("changes", [])
            base["summary"] = (
                f"change analysis found {len(changes)} recent change(s) temporally correlated with "
                "anomaly onset; causal evidence requires version-split or rollback confirmation"
            )
            base["signals"] = [c.get("id", "change") for c in changes]
            base["temporal_correlation"] = bool(changes)
            base["correlation"] = "deployment/config timestamp falls inside the anomaly window"
            base["causal_confidence"] = 0.35 if changes else 0.1
            base["supporting_evidence"] = [c.get("id", "change") for c in changes]
            base["contradicting_evidence"] = ["no rollback confirmation / version split evidence yet"]
        elif role == "remediation":
            base["summary"] = (
                f"remediation plan prepared; recommended action: {scenario.get('recommended_action', 'none')}"
            )
            base["proposed_actions"] = [scenario["remediation"]] if scenario.get("remediation") else []
            base["dangerous_action"] = bool(scenario.get("dangerous_action"))
        return base

    @staticmethod
    def _evidence_summary(scenario: dict[str, Any], tool_name: str) -> str:
        mapping = {
            "query_metrics": f"anomalous metrics in {scenario['anomaly_start']}..{scenario['anomaly_end']}",
            "query_logs": "matching error log patterns found",
            "get_service_health": f"{scenario['service']} is degraded",
            "get_recent_deployments": "recent deployment records inspected",
            "get_config_diff": "configuration diff inspected",
            "get_incident_history": "historical incidents inspected",
            "get_service_topology": "dependency topology inspected",
            "verify_service_health": "health re-checked",
        }
        return mapping.get(tool_name, f"{tool_name} executed")

    def _remediation_payload(self, scenario: dict[str, Any] | None) -> dict[str, Any]:
        if scenario is None:
            return {
                "proposed_actions": [],
                "safe_alternative": "collect more evidence",
                "requires_approval": False,
                "diagnostics": [],
            }
        remediation = scenario.get("remediation", {})
        proposed = [remediation] if remediation else []
        return {
            "proposed_actions": proposed,
            "safe_alternative": scenario.get(
                "safe_alternative",
                "continue monitoring; open ticket; do not change production without approval",
            ),
            "requires_approval": bool(scenario.get("dangerous_action")),
            "diagnostics": scenario.get("diagnostics", ["verify_service_health"]),
        }

    def _scenario_final_text(self, scenario: dict[str, Any]) -> str:
        return (
            f"[CloudOps Harness] Root cause hypothesis for {scenario['incident_id']}: {scenario['root_cause']}. "
            f"Recommended action: {scenario.get('recommended_action', 'observe and escalate')}."
        )
