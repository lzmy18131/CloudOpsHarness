"""Evaluation runners: Single-Agent / Multi-Agent / full Harness."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from cloudops_harness.agents.runtime import CloudOpsRuntime
from cloudops_harness.agents.single import build_single_agent_graph
from cloudops_harness.config.settings import Settings
from cloudops_harness.evaluation.metrics import ScenarioRunResult, compute_metrics
from cloudops_harness.runtime_context import current_run_id, current_thread_id, current_user_id
from cloudops_harness.sandbox.local_backend import LocalSandboxBackend


@dataclass
class SystemConfig:
    name: str
    mode: str  # "single" | "multi" | "harness"
    auto_approve_max_risk: int = 1
    context_isolation: bool = True
    sandbox_auto_recovery: bool = True


class DyingSandbox(LocalSandboxBackend):
    """Backend whose execute dies while ping stays healthy (eval injection).

    ping must stay healthy so SandboxManager.ensure does not pre-empt the
    recovery path under test; the failure surfaces on execute itself.
    """

    def __init__(self, workspace: Path, user_id: str) -> None:
        super().__init__(workspace, user_id)
        self.dead = False

    async def ping(self) -> bool:
        if self.dead:
            return True
        return await super().ping()

    async def execute(self, command: str, **kwargs):
        if self.dead:
            raise ConnectionError("eval-injected sandbox death")
        return await super().execute(command, **kwargs)


def build_system_runtime(
    settings: Settings,
    system: SystemConfig,
    scenario_index: dict[str, dict[str, Any]],
) -> CloudOpsRuntime:
    system_settings = settings.model_copy(
        update={
            "auto_approve_max_risk": system.auto_approve_max_risk,
            "context_isolation": system.context_isolation,
            "sandbox_auto_recovery": system.sandbox_auto_recovery,
        }
    )
    runtime = CloudOpsRuntime(system_settings)
    runtime.scenario_index = scenario_index
    return runtime


def _snapshot(runtime: CloudOpsRuntime) -> dict[str, Any]:
    adapters = getattr(runtime, "created_adapters", [])
    return {
        "tool_counts": dict(runtime.registry.global_telemetry),
        "llm_calls": sum(getattr(a, "call_count", 0) for a in adapters),
        "tokens": sum(getattr(a, "usage_total", 0) for a in adapters),
    }


async def _invoke_until_settled(
    graph: Any,
    scenario: dict[str, Any],
    thread_id: str,
    *,
    approve: bool = True,
) -> tuple[dict[str, Any], bool, bool]:
    """Run the graph and auto-answer every interrupt (HITL loop for evals)."""
    saw_approval = False
    saw_missing_info = False
    result = await graph.ainvoke(
        {
            "messages": [{"role": "user", "content": scenario["user_query"]}],
            "user_id": "eval-user",
            "thread_id": thread_id,
            "run_id": f"run-{uuid.uuid4().hex[:8]}",
        },
        config={"configurable": {"thread_id": thread_id}},
    )
    for _ in range(6):
        pending = result.get("pending_interrupt")
        if not pending:
            break
        if pending.get("type") == "approval":
            saw_approval = True
            decisions = [
                {
                    "type": "approve" if approve else "reject",
                    "tool_name": request.get("tool_name"),
                }
                for request in pending.get("action_requests", [])
            ]
            result = await graph.ainvoke(
                Command(resume={"decisions": decisions}),
                config={"configurable": {"thread_id": thread_id}},
            )
        elif pending.get("type") == "missing_info":
            saw_missing_info = True
            result = await graph.ainvoke(
                Command(resume={"supplement": f"{scenario['service']} {scenario['title']}"}),
                config={"configurable": {"thread_id": thread_id}},
            )
        else:
            break
    return result, saw_approval, saw_missing_info


async def run_one_scenario(
    runtime: CloudOpsRuntime,
    scenario: dict[str, Any],
    system: SystemConfig,
) -> ScenarioRunResult:
    """Run one scenario and convert the run into metrics."""
    provider = runtime.base_provider
    provider.deactivate_scenarios()
    provider.activate_scenario(scenario)
    if scenario.get("fail_tool"):
        provider.fault_injection.fail_next[scenario["fail_tool"]] = 1
    if scenario.get("sandbox_failure"):
        proxy = await runtime.sandbox_manager.ensure("eval-user")
        dying = DyingSandbox(runtime.settings.data_dir / f"eval-dying-{scenario['incident_id']}", "eval-user")
        await dying.create()
        dying.dead = True
        proxy.replace_backend(dying)

    run_id = f"eval-{system.name}-{scenario['incident_id']}"
    runtime.start_tool_budget(run_id)
    runtime.reset_model_budget()
    before = _snapshot(runtime)
    started = time.monotonic()
    thread_id = f"eval-{system.name}-{scenario['incident_id']}"
    current_user_id.set("eval-user")
    current_thread_id.set(thread_id)
    current_run_id.set(f"run-{uuid.uuid4().hex[:8]}")
    if system.mode == "single":
        graph = build_single_agent_graph(
            runtime.adapter_for(scenario),
            runtime.registry,
            approve_writes=True,
            checkpointer=InMemorySaver(),
        )
        result = await graph.ainvoke(
            {"messages": [{"role": "user", "content": scenario["user_query"]}]},
            config={"configurable": {"thread_id": thread_id}},
        )
        saw_approval = False
        saw_missing_info = False
    else:
        graph = runtime.build_graph(checkpointer=InMemorySaver())
        result, saw_approval, saw_missing_info = await _invoke_until_settled(
            graph, scenario, thread_id, approve=True
        )
    latency_ms = (time.monotonic() - started) * 1000
    after = _snapshot(runtime)

    called_tools = sorted(
        name for name, count in after["tool_counts"].items() if count > before["tool_counts"].get(name, 0)
    )
    metrics = compute_metrics(
        scenario,
        result,
        system=system.name,
        saw_approval=saw_approval,
        saw_missing_info=saw_missing_info,
        tool_calls_delta=sum(after["tool_counts"].values()) - sum(before["tool_counts"].values()),
        llm_calls_delta=after["llm_calls"] - before["llm_calls"],
        token_cost_delta=after["tokens"] - before["tokens"],
        latency_ms=latency_ms,
        called_tools=called_tools,
    )
    provider.deactivate_scenarios()
    provider.fault_injection = type(provider.fault_injection)()
    return metrics
