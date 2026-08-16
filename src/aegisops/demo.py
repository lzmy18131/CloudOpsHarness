"""Deterministic demos (no LLM key needed).

Demo 1: bad deployment -> HITL approve -> rollback -> verify -> report.
Demo 2: DB pool exhaustion -> evidence -> sandbox analysis -> remediation.
Demo 3: dangerous action REJECTED -> safe alternative -> report without change.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from aegisops.agents.runtime import AegisRuntime
from aegisops.config.settings import PROJECT_ROOT, Settings
from aegisops.evaluation.dataset import load_scenarios

DATASET = PROJECT_ROOT / "fixtures" / "incidents" / "scenarios.json"


def pick_scenario(fault_type: str, category: str = "dangerous_action") -> dict[str, Any]:
    scenarios = load_scenarios(DATASET)
    for scenario in scenarios:
        if scenario["fault_type"] == fault_type and scenario["category"] == category:
            return scenario
    raise RuntimeError(f"no scenario for {fault_type}/{category}")


async def run_demo(demo: int, out: str | None = None) -> None:
    settings = Settings(
        _env_file=None,
        environment="dev",
        data_dir=PROJECT_ROOT / "data" / "demo",
        fixtures_dir=PROJECT_ROOT / "fixtures",
        skills_dir=PROJECT_ROOT / "skills",
        checkpoint_backend="sqlite" if demo == 4 else "memory",
    )
    runtime = AegisRuntime(settings)
    if demo == 4:
        await run_demo_sandbox_crash_resume(runtime)
        return
    if demo == 1:
        scenario = pick_scenario("bad-deployment")
        approve = True
    elif demo == 2:
        scenario = pick_scenario("database-connection-pool-exhaustion")
        approve = True
    else:
        scenario = pick_scenario("bad-deployment")
        approve = False

    runtime.scenario_index = {scenario["incident_id"]: scenario}
    graph = runtime.build_graph(checkpointer=InMemorySaver())
    thread_id = f"demo-{demo}"
    config = {"configurable": {"thread_id": thread_id}}
    print(f"=== Demo {demo}: {scenario['title']} ===")
    print(f"user: {scenario['user_query']}")

    result = await graph.ainvoke(
        {
            "messages": [{"role": "user", "content": scenario["user_query"]}],
            "user_id": "demo-user",
            "thread_id": thread_id,
            "run_id": f"demo-run-{demo}",
        },
        config=config,
    )
    for _ in range(4):
        pending = result.get("pending_interrupt")
        if not pending:
            break
        print(f"[interrupt] {pending['type']}: {pending.get('message', '')}")
        if pending["type"] == "approval":
            decisions = [
                {
                    "type": "approve" if approve else "reject",
                    "tool_name": request.get("tool_name"),
                    "comment": "" if approve else "operator rejected in demo",
                }
                for request in pending.get("action_requests", [])
            ]
            result = await graph.ainvoke(Command(resume={"decisions": decisions}), config=config)
        else:
            result = await graph.ainvoke(
                Command(resume={"supplement": f"{scenario['service']} {scenario['title']}"}), config=config
            )

    for source, report in result.get("subagent_reports", {}).items():
        print(f"[{source}] {report.get('summary', '')}")

    if result.get("executed_actions"):
        for action in result["executed_actions"]:
            print(f"[executed] {action['tool_name']} {action['arguments']}")
    if result.get("rejected_actions"):
        for action in result["rejected_actions"]:
            print(
                f"[rejected] {action['tool_name']} -> safe alternative: "
                f"{result.get('remediation_plan', {}).get('safe_alternative', '')}"
            )

    print()
    print(result.get("final_report", "no report"))
    report_dir = Path(out) if out else PROJECT_ROOT / "data" / "demo_reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    path = report_dir / f"demo{demo}_{scenario['incident_id']}.md"
    path.write_text(result.get("final_report", ""), encoding="utf-8")
    print(f"\nreport saved: {path}")
    await runtime.destroy_sandboxes()


async def run_demo_sandbox_crash_resume(runtime: AegisRuntime) -> None:
    """Demo D: sandbox crash -> automatic recovery -> HITL interrupt ->
    simulated process restart (SQLite checkpoint reopen) -> resume -> finish."""
    from langgraph.checkpoint.memory import InMemorySaver
    from langgraph.types import Command

    from aegisops.agents.checkpoint import open_checkpointer
    from aegisops.evaluation.runners import DyingSandbox

    scenario = pick_scenario("bad-deployment", "sandbox_failure")
    runtime.scenario_index = {scenario["incident_id"]: scenario}
    runtime.activate_scenario(scenario["incident_id"])
    proxy = await runtime.sandbox_manager.ensure("demo-user")
    dying = DyingSandbox(runtime.settings.data_dir / "demo4-dying", "demo-user")
    await dying.create()
    dying.dead = True
    proxy.replace_backend(dying)
    print(f"=== Demo 4: {scenario['title']} (sandbox crash + resume) ===")

    if runtime.settings.checkpoint_backend == "sqlite":
        handle = await open_checkpointer(runtime.settings)
        graph = runtime.build_graph(checkpointer=handle.saver)
    else:
        handle = None
        graph = runtime.build_graph(checkpointer=InMemorySaver())
    config = {"configurable": {"thread_id": "demo-4"}}
    first = await graph.ainvoke(
        {
            "messages": [{"role": "user", "content": scenario["user_query"]}],
            "user_id": "demo-user",
            "thread_id": "demo-4",
            "run_id": "demo4-run",
        },
        config=config,
    )
    print("[stage 1] sandbox crash auto-recovered:", runtime.sandbox_manager.events[-1])
    pending = first.get("pending_interrupt")
    print(f"[stage 2] HITL interrupt: {pending.get('type') if pending else None}")
    if handle is not None:
        await handle.aclose()
        print("[stage 3] simulated process restart: checkpoint handle closed")

    handle2 = (
        await open_checkpointer(runtime.settings) if runtime.settings.checkpoint_backend == "sqlite" else None
    )
    graph2 = runtime.build_graph(checkpointer=handle2.saver if handle2 else InMemorySaver())
    final = await graph2.ainvoke(
        Command(resume={"decisions": [{"type": "approve", "tool_name": "rollback_release"}]}),
        config=config,
    )
    print("[stage 4] resumed and finished:", final.get("status"))
    print(final.get("final_report", "")[:1200])
    if handle2 is not None:
        await handle2.aclose()
    report_dir = PROJECT_ROOT / "data" / "demo_reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    path = report_dir / f"demo4_{scenario['incident_id']}.md"
    path.write_text(final.get("final_report", ""), encoding="utf-8")
    print(f"\nreport saved: {path}")


if __name__ == "__main__":
    import argparse
    import asyncio

    parser = argparse.ArgumentParser()
    parser.add_argument("--demo", type=int, choices=[1, 2, 3, 4], default=1)
    parser.add_argument("--out", default=None)
    args = parser.parse_args()
    asyncio.run(run_demo(args.demo, args.out))
