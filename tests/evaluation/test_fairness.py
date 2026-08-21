"""Fairness tests: compared systems share the same model configuration and output schema."""

from __future__ import annotations

from pathlib import Path

import pytest
from langgraph.checkpoint.memory import InMemorySaver

from cloudops_harness.agents.models import RcaHypothesis
from cloudops_harness.agents.single import build_single_agent_graph
from cloudops_harness.config.settings import Settings
from cloudops_harness.evaluation.harness import load_default_scenarios
from cloudops_harness.evaluation.runners import SystemConfig, build_system_runtime
from cloudops_harness.llm.fake import FakeLLM
from cloudops_harness.providers.mock import MockOpsProvider
from cloudops_harness.tools.registry import ToolRegistry

PROJECT_ROOT = Path(__file__).resolve().parents[2]

SHARED_EVAL_SCHEMA_FIELDS = {
    "affected_service",
    "root_cause",
    "root_cause_component",
    "fault_category",
    "confidence",
    "supporting_evidence",
}


def test_systems_use_same_model_config(tmp_path) -> None:
    settings = Settings(
        _env_file=None,
        environment="test",
        data_dir=tmp_path / "data",
        fixtures_dir=tmp_path / "fixtures",
        skills_dir=tmp_path / "skills",
        llm_model="deepseek-chat",
        llm_temperature=0.2,
    )
    systems = [
        SystemConfig(name="single-agent", mode="single", auto_approve_max_risk=3),
        SystemConfig(name="harness", mode="harness", auto_approve_max_risk=1),
    ]
    scenario_index: dict = {}
    runtimes = [build_system_runtime(settings, s, scenario_index) for s in systems]
    for runtime in runtimes:
        assert runtime.settings.llm_model == "deepseek-chat"
        assert runtime.settings.llm_temperature == 0.2
        assert runtime.settings.llm_base_url == settings.llm_base_url


@pytest.mark.asyncio
async def test_single_and_harness_share_final_eval_schema() -> None:
    # The schema used by the full Harness is RcaHypothesis; Single-Agent must
    # emit the same structured fields so the comparison is fair.
    assert SHARED_EVAL_SCHEMA_FIELDS <= set(RcaHypothesis.model_fields.keys())

    settings = Settings(_env_file=None, environment="test", sandbox_backend="local")
    registry = ToolRegistry(MockOpsProvider(fixtures_dir=PROJECT_ROOT / "fixtures"), settings)
    scenario = next(s for s in load_default_scenarios() if s["category"] == "single_source")
    llm = FakeLLM(scenario=scenario)
    graph = build_single_agent_graph(llm, registry, checkpointer=InMemorySaver())
    result = await graph.ainvoke(
        {"messages": [{"role": "user", "content": scenario["user_query"]}]},
        config={"configurable": {"thread_id": "fairness-single"}},
    )
    assert result.get("status") == "done"
    assert SHARED_EVAL_SCHEMA_FIELDS <= set(result.get("rca", {}).keys())
