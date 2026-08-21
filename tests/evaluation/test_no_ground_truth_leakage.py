"""Ground-truth leakage audit for real-LLM evaluation.

These tests assert that evaluator-only fields (root_cause, fault_type,
expected_tools, recommended_action, incident_id, ...) never appear in LLM
prompts or in tool responses returned to the model.
"""

from __future__ import annotations

import pytest

from cloudops_harness.agents.context import assemble_main_messages
from cloudops_harness.evaluation.harness import load_default_scenarios
from cloudops_harness.llm.models import LLMMessage
from cloudops_harness.providers.mock import MockOpsProvider

EVALUATOR_ONLY_FIELDS = {
    "root_cause",
    "expected_tools",
    "recommended_action",
    "fix_action",
    "safe_alternative",
    "remediation",
    "root_cause_id",
    "root_cause_component",
    "fault_category",
    "metric_specs",
    "log_specs",
    "changes",
    "subagent_tools",
    "expected_decision",
    "forbidden_actions",
    "allowed_actions",
    "required_approval_risk_level",
}


def _scenario() -> dict:
    return next(s for s in load_default_scenarios() if s["category"] == "dangerous_action")


def _message_text(messages: list[LLMMessage]) -> str:
    return "\n".join(m.content or "" for m in messages)


def test_main_prompt_has_no_ground_truth() -> None:
    scenario = _scenario()
    state = {
        "user_id": "eval-user",
        "service": scenario["service"],
        "environment": "prod",
        "time_range_start": scenario["anomaly_start"],
        "time_range_end": scenario["anomaly_end"],
        "scenario": scenario,
        "subagent_reports": {},
        "plan": [],
        "messages": [],
    }
    messages = assemble_main_messages(state, scenario=scenario)
    text = _message_text(messages).lower()
    assert "incident_id" not in text
    assert "inc-" not in text
    for field in EVALUATOR_ONLY_FIELDS:
        # Search for the field as a JSON/structured key, not as a natural-language word
        # (e.g. "changes" appears in the system prompt as a normal word).
        assert f'"{field}"' not in text and f"'{field}'" not in text


@pytest.mark.asyncio
async def test_subagent_prompt_has_no_incident_id_or_ground_truth(tmp_path) -> None:
    from cloudops_harness.agents.runtime import CloudOpsRuntime
    from cloudops_harness.config.settings import Settings

    scenario = _scenario()
    settings = Settings(
        _env_file=None,
        environment="test",
        data_dir=tmp_path / "data",
        fixtures_dir=tmp_path / "fixtures",
        skills_dir=tmp_path / "skills",
        sandbox_backend="local",
    )
    # The runtime requires fixtures for subagent configs and skills.
    import shutil
    from pathlib import Path

    project = Path(__file__).resolve().parents[2]  # noqa: ASYNC240 - test setup only
    (tmp_path / "fixtures").mkdir(parents=True, exist_ok=True)  # noqa: ASYNC240 - test setup only
    shutil.copytree(
        project / "fixtures" / "incidents", tmp_path / "fixtures" / "incidents", dirs_exist_ok=True
    )
    shutil.copytree(project / "skills", tmp_path / "skills", dirs_exist_ok=True)
    runtime = CloudOpsRuntime(settings)
    runner = runtime.subagent_runner
    config = runtime.subagent_configs["observability"]
    brief = "INCIDENT TASK: query health\nservice: payment-service"
    # We only check the system prompt construction path by monkeypatching the loop
    # to avoid running tools in this leakage test.
    captured: list[str] = []

    async def fake_loop_run(self, messages, **kwargs):
        captured.append("\n".join(m.content or "" for m in messages))
        from cloudops_harness.agents.loop import LoopResult, LoopStats

        return LoopResult(
            messages=messages,
            final_content="ok",
            stats=LoopStats(llm_calls=1),
            finished=True,
        )

    import cloudops_harness.agents.loop as loop_mod

    original = loop_mod.AgentLoop.run
    loop_mod.AgentLoop.run = fake_loop_run  # type: ignore[method-assign]
    try:
        await runner.run(config, brief, {"scenario": scenario, "service": scenario["service"]})
    finally:
        loop_mod.AgentLoop.run = original  # type: ignore[method-assign]
    text = "\n".join(captured).lower()
    assert "incident_id" not in text
    assert "inc-" not in text
    for field in EVALUATOR_ONLY_FIELDS:
        assert field not in text


@pytest.mark.asyncio
async def test_tool_responses_do_not_leak_evaluator_labels() -> None:
    scenario = _scenario()
    provider = MockOpsProvider(fixtures_dir="fixtures")
    provider.activate_scenario(scenario)
    logs = await provider.query_logs(
        scenario["service"], scenario["anomaly_start"], scenario["anomaly_end"], limit=50
    )
    for entry in logs.entries:
        assert "incident_id" not in entry.extra
        assert "INC-" not in str(entry.extra)
    history = await provider.get_incident_history(scenario["service"])
    for item in history:
        assert item.fault_type == "[redacted]"
        assert item.root_cause == "[redacted]"
    health = await provider.get_service_health(scenario["service"])
    assert health.message == "active incident detected"
