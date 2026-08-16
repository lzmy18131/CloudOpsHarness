"""Checkpoint tests: HITL interrupt survives a simulated process restart."""

from __future__ import annotations

from pathlib import Path

import pytest
from langgraph.types import Command
from tests.integration.test_main_agent import make_scenario

from cloudops_harness.agents.checkpoint import open_checkpointer
from cloudops_harness.agents.runtime import CloudOpsRuntime
from cloudops_harness.config.settings import Settings

PROJECT_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture()
def runtime(tmp_path) -> CloudOpsRuntime:
    settings = Settings(
        _env_file=None,
        environment="test",
        data_dir=tmp_path / "data",
        fixtures_dir=PROJECT_ROOT / "fixtures",
        skills_dir=PROJECT_ROOT / "skills",
        checkpoint_backend="sqlite",
        sandbox_backend="local",
    )
    runtime = CloudOpsRuntime(settings)
    scenario = make_scenario()
    runtime.scenario_index = {scenario["incident_id"]: scenario}
    return runtime


@pytest.mark.asyncio
async def test_resume_after_process_restart(runtime) -> None:
    config = {"configurable": {"thread_id": "thread-restart"}}
    settings: Settings = runtime.settings

    # Process 1: run until the approval interrupt, then "die".
    handle1 = await open_checkpointer(settings)
    graph1 = runtime.build_graph(handle1.saver)
    first = await graph1.ainvoke(
        {"messages": [{"role": "user", "content": "payment-service 昨晚发布新版本后延迟暴涨，帮我排查"}]},
        config=config,
    )
    assert first["pending_interrupt"]["type"] == "approval"
    # Evidence that pre-interrupt work is checkpointed and must NOT re-run.
    plan_before = [(s["id"], s["status"]) for s in first["plan"]]
    calls_before = {
        tool: count
        for tool, count in runtime.registry.global_telemetry.items()
        if tool in {"query_logs", "get_recent_deployments", "get_config_diff"}
    }
    await handle1.aclose()

    # Process 2: reopen the same SQLite file and resume from the checkpoint.
    handle2 = await open_checkpointer(settings)
    graph2 = runtime.build_graph(handle2.saver)
    final = await graph2.ainvoke(
        Command(resume={"decisions": [{"type": "approve", "tool_name": "rollback_release"}]}),
        config=config,
    )
    assert final["status"] == "done"
    assert final["executed_actions"][0]["tool_name"] == "rollback_release"
    assert "Incident Report" in final["final_report"]
    # Plan and completed evidence steps survived the restart untouched.
    plan_after = [(s["id"], s["status"]) for s in final["plan"]]
    for step_id, status in plan_before[:8]:
        assert (step_id, status) in plan_after
    for tool, count in calls_before.items():
        assert runtime.registry.global_telemetry.get(tool, 0) == count, (
            f"{tool} re-executed after resume (was {count}, now {runtime.registry.global_telemetry.get(tool, 0)})"
        )
    await handle2.aclose()
