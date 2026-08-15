"""Declarative subagent loading (add a YAML file = add a subagent)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, ValidationError


class SubAgentConfig(BaseModel):
    name: str
    description: str
    tools: list[str] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    system_prompt: str
    max_iterations: int = 6
    max_tool_result_chars: int = 4000
    context_budget_tokens: int = 12000
    sandbox: bool = False


class SubAgentConfigError(RuntimeError):
    """One or more subagent YAML configs are invalid."""


def default_config_dir() -> Path:
    return Path(__file__).resolve().parent / "configs"


def load_subagent_configs(config_dir: Path | str | None = None) -> list[SubAgentConfig]:
    """Load every ``*.yaml`` from the configs directory."""
    directory = Path(config_dir) if config_dir else default_config_dir()
    configs: list[SubAgentConfig] = []
    for path in sorted(directory.glob("*.yaml")):
        with path.open("r", encoding="utf-8") as handle:
            raw = yaml.safe_load(handle)
        try:
            configs.append(SubAgentConfig.model_validate(raw))
        except ValidationError as exc:
            raise SubAgentConfigError(f"invalid subagent config {path}: {exc}") from exc
    return configs


def validate_subagent_config(config: SubAgentConfig, registry: Any) -> list[str]:
    """Return a list of validation errors (empty means valid).

    Policy: subagents only receive read-only tools. Production-changing tools
    are proposed by the remediation agent and executed by the Incident
    Commander after HITL - never called inside a subagent context.
    """
    errors: list[str] = []
    if not config.name:
        errors.append("name is required")
    if not config.description:
        errors.append("description is required")
    if not config.system_prompt:
        errors.append("system_prompt is required")
    if not config.tools:
        errors.append("tools must not be empty")
    for tool_name in config.tools:
        try:
            definition = registry.get(tool_name)
        except Exception:  # noqa: BLE001 - unknown tool reported as config error
            errors.append(f"unknown tool: {tool_name}")
            continue
        if int(definition.risk.level) > 1:
            errors.append(
                f"tool {tool_name} has risk level {int(definition.risk.level)} (> L1) "
                "and is forbidden in subagent configs"
            )
    return errors


def resolve_subagent_tools(config: SubAgentConfig, registry: Any) -> list[Any]:
    """Resolve YAML tool names to registry tool definitions."""
    resolved = []
    for tool_name in config.tools:
        try:
            resolved.append(registry.get(tool_name))
        except Exception as exc:  # noqa: BLE001
            raise SubAgentConfigError(f"{config.name}: unknown tool {tool_name}") from exc
    return resolved
