"""Evaluation harness tests: dataset invariants, metrics, stats, small run."""

from __future__ import annotations

import math
from pathlib import Path

import pytest

from cloudops_harness.config.settings import Settings
from cloudops_harness.evaluation.dataset import dataset_stats, validate_dataset
from cloudops_harness.evaluation.harness import load_default_scenarios, run_experiment
from cloudops_harness.evaluation.metrics import ScenarioRunResult, mcnemar_pvalue, paired_bootstrap
from cloudops_harness.evaluation.runners import SystemConfig

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_dataset_has_100_scenarios_and_all_invariants() -> None:
    scenarios = load_default_scenarios()
    assert len(scenarios) == 110
    assert validate_dataset(scenarios) == []
    stats = dataset_stats(scenarios)
    assert len(stats["fault_types"]) == 10
    assert {
        "easy",
        "single_source",
        "multi_source",
        "multi_hop",
        "dependency_chain",
        "dangerous_action",
        "missing_information",
        "ambiguous",
        "tool_failure",
        "sandbox_failure",
    } <= set(stats["categories"])
    assert stats["dangerous"] >= 10
    assert stats["missing_information"] >= 10
    assert stats["tool_failure"] >= 10
    assert stats["sandbox_failure"] >= 10


def test_mcnemar_exact_pvalue() -> None:
    # 10 discordant pairs all in one direction -> very small two-sided p.
    p = mcnemar_pvalue(10, 0)
    assert p < 0.01
    assert mcnemar_pvalue(0, 0) == 1.0


def test_paired_bootstrap_ci_matches_direction() -> None:
    a = [3.0, 4.0, 5.0, 6.0]
    b = [1.0, 2.0, 3.0, 4.0]
    result = paired_bootstrap(a, b, n_boot=200)
    assert math.isclose(result["mean_diff"], 2.0)
    assert result["ci_low"] <= 2.0 <= result["ci_high"]


@pytest.mark.asyncio
async def test_small_experiment_runs_and_writes_artifacts(tmp_path) -> None:
    settings = Settings(
        _env_file=None,
        environment="test",
        data_dir=tmp_path / "data",
        fixtures_dir=PROJECT_ROOT / "fixtures",
        skills_dir=PROJECT_ROOT / "skills",
        sandbox_backend="local",
    )
    scenarios = load_default_scenarios()[:4]
    systems = [
        SystemConfig(name="single-agent", mode="single", auto_approve_max_risk=3),
        SystemConfig(name="harness", mode="harness"),
    ]
    output = tmp_path / "results"
    artifacts = await run_experiment(settings, scenarios, systems, output_dir=output, tag="test")
    assert (output / "summary.json").exists()
    assert (output / "summary.md").exists()
    for name in ("single-agent", "harness"):
        payload = artifacts["systems"][name]
        assert payload["aggregate"]["n"] == 4
        assert len(payload["results"]) == 4
        for result in payload["results"]:
            assert ScenarioRunResult(**result).scenario_id
    comparison = artifacts["comparisons"][0]
    assert comparison["pair"] == "single-agent vs harness"
    assert len(comparison["binary"]) == 3
    assert len(comparison["continuous"]) == 8
    assert any(b["bucket"] == "simple" for b in artifacts["bucket_comparisons"])
