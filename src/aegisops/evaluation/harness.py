"""Evaluation harness orchestration and artifact writing."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import anyio

from aegisops.agents.runtime import AegisRuntime
from aegisops.config.settings import Settings
from aegisops.evaluation.dataset import load_scenarios
from aegisops.evaluation.metrics import (
    ScenarioRunResult,
    aggregate,
    compare_paired,
)
from aegisops.evaluation.runners import SystemConfig, build_system_runtime, run_one_scenario


async def run_system(
    settings: Settings,
    scenarios: list[dict[str, Any]],
    system: SystemConfig,
    *,
    scenario_ids: set[str] | None = None,
) -> tuple[list[ScenarioRunResult], AegisRuntime]:
    runtime = build_system_runtime(settings, system, {s["incident_id"]: s for s in scenarios})
    results: list[ScenarioRunResult] = []
    for scenario in scenarios:
        if scenario_ids is not None and scenario["incident_id"] not in scenario_ids:
            continue
        result = await run_one_scenario(runtime, scenario, system)
        results.append(result)
    await runtime.destroy_sandboxes()
    return results, runtime


async def run_experiment(
    settings: Settings,
    scenarios: list[dict[str, Any]],
    systems: list[SystemConfig],
    *,
    output_dir: Path | str,
    tag: str = "offline",
) -> dict[str, Any]:
    """Run all systems over the dataset and write honest artifacts."""
    output = Path(output_dir)
    await anyio.to_thread.run_sync(output.mkdir, True, True)
    artifacts: dict[str, Any] = {"tag": tag, "generated_at": _now(), "systems": {}}
    for system in systems:
        results, _ = await run_system(settings, scenarios, system)
        aggregates = aggregate(results)
        artifacts["systems"][system.name] = {
            "config": {
                "mode": system.mode,
                "auto_approve_max_risk": system.auto_approve_max_risk,
                "context_isolation": system.context_isolation,
                "sandbox_auto_recovery": system.sandbox_auto_recovery,
            },
            "aggregate": aggregates,
            "results": [result.__dict__ for result in results],
        }
    comparisons = _build_comparisons(artifacts)
    artifacts["comparisons"] = comparisons
    summary_path = output / "summary.json"
    summary_path.write_text(json.dumps(artifacts, ensure_ascii=False, indent=2), encoding="utf-8")
    markdown_path = output / "summary.md"
    markdown_path.write_text(render_summary_markdown(artifacts), encoding="utf-8")
    return artifacts


def _build_comparisons(artifacts: dict[str, Any]) -> list[dict[str, Any]]:
    comparisons: list[dict[str, Any]] = []
    pairs = [
        ("single-agent", "harness"),
        ("multi-agent", "harness"),
        ("multi-agent", "multi-no-isolation"),
        ("harness-no-recovery", "harness"),
    ]
    for left, right in pairs:
        if left not in artifacts["systems"] or right not in artifacts["systems"]:
            continue
        a = [ScenarioRunResult(**r) for r in artifacts["systems"][left]["results"]]
        b = [ScenarioRunResult(**r) for r in artifacts["systems"][right]["results"]]
        entry: dict[str, Any] = {
            "pair": f"{left} vs {right}",
            "binary": [
                compare_paired(a, b, metric="rca_correct", binary=True),
                compare_paired(a, b, metric="task_completed", binary=True),
                compare_paired(a, b, metric="unsafe_action", binary=True),
            ],
            "continuous": [
                compare_paired(a, b, metric="tool_calls"),
                compare_paired(a, b, metric="llm_calls"),
                compare_paired(a, b, metric="token_cost"),
                compare_paired(a, b, metric="latency_ms"),
            ],
        }
        if left == "harness-no-recovery":
            recovery_a = [r for r in a if r.recovery_success is not None]
            recovery_b = [r for r in b if r.recovery_success is not None]
            if recovery_a and recovery_b:
                entry["binary"].append(
                    compare_paired(recovery_a, recovery_b, metric="recovery_success", binary=True)
                )
        comparisons.append(entry)
    return comparisons


def render_summary_markdown(artifacts: dict[str, Any]) -> str:
    lines = [
        "# AegisOps Evaluation Results",
        "",
        f"tag: `{artifacts['tag']}`",
        f"generated: {artifacts['generated_at']}",
        "",
    ]
    for name, payload in artifacts["systems"].items():
        agg = payload["aggregate"]
        lines.append(f"## {name}")
        lines.append("")
        lines.append(f"- n={agg['n']}")
        for key in (
            "root_cause_accuracy",
            "task_completion_rate",
            "tool_selection_accuracy",
            "evidence_completeness",
            "unsafe_action_rate",
            "unsafe_action_rate_dangerous",
            "hitl_compliance_rate",
        ):
            lines.append(f"- {key}: {agg[key]:.4f}")
        for key in ("recovery_success_rate",):
            if agg.get(key) is not None:
                lines.append(f"- {key}: {agg[key]:.4f}")
        for key in ("mean_tool_calls", "mean_llm_calls", "mean_token_cost", "mean_latency_ms"):
            lines.append(f"- {key}: {agg[key]:.2f}")
        lines.append("")
    lines.append("## Paired comparisons")
    lines.append("")
    for comparison in artifacts.get("comparisons", []):
        lines.append(f"### {comparison['pair']}")
        for entry in comparison["binary"]:
            lines.append(
                f"- {entry['metric']}: a={entry['a_rate']:.3f} b={entry['b_rate']:.3f} "
                f"discordant b={entry['b']} c={entry['c']} McNemar p={entry['mcnemar_p']:.4f}"
            )
        for entry in comparison["continuous"]:
            lines.append(
                f"- {entry['metric']}: mean_diff={entry['mean_diff']:.2f} "
                f"95% CI [{entry['ci_low']:.2f}, {entry['ci_high']:.2f}]"
            )
        lines.append("")
    return "\n".join(lines)


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def default_scenarios_path() -> Path:
    return Path(__file__).resolve().parents[3] / "fixtures" / "incidents" / "scenarios.json"


def load_default_scenarios() -> list[dict[str, Any]]:
    return load_scenarios(default_scenarios_path())
