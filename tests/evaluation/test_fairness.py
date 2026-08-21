"""Fairness tests: compared systems share the same model configuration."""

from __future__ import annotations

from cloudops_harness.config.settings import Settings
from cloudops_harness.evaluation.runners import SystemConfig, build_system_runtime


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
