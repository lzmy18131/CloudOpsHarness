"""Unit tests for declarative subagent loading and validation."""

from __future__ import annotations

from pathlib import Path

import pytest

from aegisops.agents.subagents.loader import (
    SubAgentConfigError,
    load_subagent_configs,
    resolve_subagent_tools,
    validate_subagent_config,
)
from aegisops.config.settings import Settings
from aegisops.providers.mock import MockOpsProvider
from aegisops.tools.registry import ToolRegistry

PROJECT_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture()
def registry() -> ToolRegistry:
    settings = Settings(_env_file=None, environment="test")
    return ToolRegistry(MockOpsProvider(fixtures_dir=PROJECT_ROOT / "fixtures"), settings)


def test_load_subagent_configs_finds_four_agents() -> None:
    configs = load_subagent_configs()
    names = {config.name for config in configs}
    assert names == {"observability", "log-analysis", "change-analysis", "remediation"}


def test_all_bundled_configs_are_valid(registry) -> None:
    for config in load_subagent_configs():
        assert validate_subagent_config(config, registry) == []


def test_resolve_subagent_tools_maps_names(registry) -> None:
    config = next(c for c in load_subagent_configs() if c.name == "observability")
    resolved = resolve_subagent_tools(config, registry)
    assert {tool.name for tool in resolved} == set(config.tools)


def test_write_tools_above_l1_are_forbidden_in_subagent_config(registry) -> None:
    from aegisops.agents.subagents.loader import SubAgentConfig

    config = SubAgentConfig(
        name="rogue",
        description="tries to restart services",
        tools=["restart_service"],
        skills=[],
        system_prompt="bad",
    )
    errors = validate_subagent_config(config, registry)
    assert any("risk level 2" in error for error in errors)


def test_unknown_tool_reported(registry) -> None:
    from aegisops.agents.subagents.loader import SubAgentConfig

    config = SubAgentConfig(
        name="broken",
        description="unknown tool",
        tools=["not_a_tool"],
        skills=[],
        system_prompt="bad",
    )
    errors = validate_subagent_config(config, registry)
    assert errors == ["unknown tool: not_a_tool"]


def test_resolve_unknown_tool_raises(registry) -> None:
    from aegisops.agents.subagents.loader import SubAgentConfig

    config = SubAgentConfig(
        name="broken", description="x", tools=["not_a_tool"], skills=[], system_prompt="x"
    )
    with pytest.raises(SubAgentConfigError):
        resolve_subagent_tools(config, registry)
