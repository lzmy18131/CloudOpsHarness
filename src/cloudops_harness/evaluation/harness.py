"""Evaluation harness orchestration and artifact writing.

This module is used by both deterministic workflow validation (FakeLLM) and
real-LLM benchmark runs. The two modes are separated by settings and by the
``adapter_type`` field written into every artifact; real mode never falls back
to FakeLLM.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import anyio

from cloudops_harness.agents.runtime import CloudOpsRuntime
from cloudops_harness.config.settings import Settings
from cloudops_harness.evaluation.dataset import load_scenarios
from cloudops_harness.evaluation.metrics import (
    ScenarioRunResult,
    aggregate,
    compare_paired,
)
from cloudops_harness.evaluation.runners import SystemConfig, build_system_runtime, run_one_scenario


async def run_system(
    settings: Settings,
    scenarios: list[dict[str, Any]],
    system: SystemConfig,
    *,
    scenario_ids: set[str] | None = None,
    repeat: int = 1,
) -> tuple[list[ScenarioRunResult], CloudOpsRuntime]:
    runtime = build_system_runtime(settings, system, {s["incident_id"]: s for s in scenarios})
    results: list[ScenarioRunResult] = []
    for scenario in scenarios:
        if scenario_ids is not None and scenario["incident_id"] not in scenario_ids:
            continue
        for repetition in range(repeat):
            result = await run_one_scenario(runtime, scenario, system, repetition=repetition)
            results.append(result)
    await runtime.destroy_sandboxes()
    return results, runtime


def _git_commit() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], stderr=subprocess.DEVNULL, text=True
        ).strip()
    except Exception:  # noqa: BLE001 - best effort provenance
        return "unknown"


def _git_dirty() -> bool:
    try:
        return bool(
            subprocess.check_output(
                ["git", "status", "--porcelain"], stderr=subprocess.DEVNULL, text=True
            ).strip()
        )
    except Exception:  # noqa: BLE001 - best effort provenance
        return True


def _sha256_file(path: Path | str) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _provider_base_url_host(settings: Settings) -> str:
    try:
        from urllib.parse import urlparse

        return urlparse(settings.llm_base_url).hostname or settings.llm_base_url
    except Exception:  # noqa: BLE001 - provenance best effort
        return settings.llm_base_url


def _write_artifacts(
    output: Path,
    artifacts: dict[str, Any],
    settings: Settings,
    scenarios: list[dict[str, Any]],
    systems: list[SystemConfig],
    *,
    tag: str,
    repeat: int,
    seed: int,
    max_api_calls: int | None,
    max_total_tokens: int | None,
    dataset_path: Path | None,
    split_name: str | None,
) -> None:
    """Write the full evaluation artifact set (manifest, summary, runs, failures)."""
    dataset_path = dataset_path or default_scenarios_path()
    dataset_sha = _sha256_file(dataset_path) if dataset_path.exists() else "unknown"
    adapter_type = "real" if settings.llm_configured else "fake"
    evaluator_version = "2.0"

    config = {
        "tag": tag,
        "adapter_type": adapter_type,
        "provider": settings.llm_base_url,
        "base_url_host": _provider_base_url_host(settings),
        "model": settings.llm_model,
        "temperature": settings.llm_temperature,
        "max_tokens": settings.llm_max_tokens,
        "timeout_seconds": settings.llm_timeout_seconds,
        "retry_count": settings.llm_max_retries,
        "systems": [system.name for system in systems],
        "repeat": repeat,
        "seed": seed,
        "max_api_calls": max_api_calls,
        "max_total_tokens": max_total_tokens,
        "dataset_path": str(dataset_path),
        "dataset_sha256": dataset_sha,
        "split": split_name,
        "environment": settings.environment,
        "sandbox_backend": settings.sandbox_backend,
        "model_call_limit": settings.model_call_limit,
        "tool_call_limit": settings.tool_call_limit,
        "max_plan_steps": settings.max_plan_steps,
        "max_delegation_depth": settings.max_delegation_depth,
    }

    manifest = {
        "evaluator_version": evaluator_version,
        "git_commit": _git_commit(),
        "git_dirty": _git_dirty(),
        "project_version": settings.app_version,
        "python_version": __import__("sys").version.split()[0],
        "timestamp": _now(),
        "config": config,
    }

    output.mkdir(parents=True, exist_ok=True)
    (output / "summary.json").write_text(
        json.dumps(artifacts, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (output / "summary.md").write_text(render_summary_markdown(artifacts), encoding="utf-8")
    (output / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (output / "config.json").write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
    (output / "dataset_manifest.json").write_text(
        json.dumps(
            {
                "path": str(dataset_path),
                "sha256": dataset_sha,
                "scenario_count": len(scenarios),
                "scenario_ids": [s["incident_id"] for s in scenarios],
                "split": split_name,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    runs: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    for system_name, payload in artifacts["systems"].items():
        for result in payload["results"]:
            run = {
                **result,
                "system": system_name,
                "adapter_type": adapter_type,
                "model": settings.llm_model,
                "provider": settings.llm_base_url,
            }
            runs.append(run)
            if result.get("status") != "done" or result.get("task_success") is False:
                failures.append(run)
    with (output / "runs.jsonl").open("w", encoding="utf-8") as handle:
        for run in runs:
            handle.write(json.dumps(run, ensure_ascii=False, default=str) + "\n")
    (output / "failures.json").write_text(
        json.dumps({"count": len(failures), "failures": failures}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


async def run_experiment(
    settings: Settings,
    scenarios: list[dict[str, Any]],
    systems: list[SystemConfig],
    *,
    output_dir: Path | str,
    tag: str = "offline",
    repeat: int = 1,
    seed: int = 42,
    max_api_calls: int | None = None,
    max_total_tokens: int | None = None,
    dataset_path: Path | None = None,
    split_name: str | None = None,
) -> dict[str, Any]:
    """Run all systems over the dataset and write honest artifacts.

    Real-LLM runs are fail-closed: if settings.llm_configured is false, the
    caller (scripts/run_real_eval.py) must abort before calling this function.
    This function itself records the adapter type in every artifact.
    """
    output = Path(output_dir)
    await anyio.to_thread.run_sync(lambda: output.mkdir(parents=True, exist_ok=True))
    artifacts: dict[str, Any] = {
        "tag": tag,
        "generated_at": _now(),
        "adapter_type": "real" if settings.llm_configured else "fake",
        "repeat": repeat,
        "systems": {},
    }
    budget_exceeded = False
    total_api_calls = 0
    total_tokens = 0
    for system in systems:
        results, _ = await run_system(settings, scenarios, system, repeat=repeat)
        total_api_calls += sum(r.llm_calls for r in results)
        total_tokens += sum(r.total_tokens for r in results)
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
        if max_api_calls is not None and total_api_calls >= max_api_calls:
            budget_exceeded = True
            break
        if max_total_tokens is not None and total_tokens >= max_total_tokens:
            budget_exceeded = True
            break
    if budget_exceeded:
        artifacts["budget_exceeded"] = True
        artifacts["total_api_calls_at_stop"] = total_api_calls
        artifacts["total_tokens_at_stop"] = total_tokens
    comparisons = _build_comparisons(artifacts)
    artifacts["comparisons"] = comparisons
    artifacts["bucket_comparisons"] = _build_bucket_comparisons(artifacts)
    _write_artifacts(
        output,
        artifacts,
        settings,
        scenarios,
        systems,
        tag=tag,
        repeat=repeat,
        seed=seed,
        max_api_calls=max_api_calls,
        max_total_tokens=max_total_tokens,
        dataset_path=dataset_path,
        split_name=split_name,
    )
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
                compare_paired(a, b, metric="task_success", binary=True),
                compare_paired(a, b, metric="unsafe_action", binary=True),
            ],
            "continuous": [
                compare_paired(a, b, metric="tool_calls"),
                compare_paired(a, b, metric="llm_calls"),
                compare_paired(a, b, metric="total_tokens"),
                compare_paired(a, b, metric="latency_ms"),
                compare_paired(a, b, metric="main_context_tokens"),
                compare_paired(a, b, metric="unnecessary_tool_call_rate"),
                compare_paired(a, b, metric="delegation_accuracy"),
                compare_paired(a, b, metric="evidence_grounding_precision"),
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


BUCKETS: dict[str, list[str]] = {
    "simple": ["easy", "single_source"],
    "multi_source": ["multi_source"],
    "multi_hop": ["multi_hop", "dependency_chain"],
    "complex": [
        "multi_source",
        "multi_hop",
        "dependency_chain",
        "ambiguous",
        "dangerous_action",
    ],
    "failure_injection": ["tool_failure", "sandbox_failure"],
}


def _build_bucket_comparisons(artifacts: dict[str, Any]) -> list[dict[str, Any]]:
    """Per-difficulty paired comparison (answers: when is Multi-Agent worth it?)."""
    left, right = "single-agent", "harness"
    if left not in artifacts["systems"] or right not in artifacts["systems"]:
        return []
    a_all = [ScenarioRunResult(**r) for r in artifacts["systems"][left]["results"]]
    b_all = [ScenarioRunResult(**r) for r in artifacts["systems"][right]["results"]]
    bucket_results: list[dict[str, Any]] = []
    for bucket, categories in BUCKETS.items():
        a = [r for r in a_all if r.category in categories]
        b = [r for r in b_all if r.category in categories]
        if not a or not b:
            continue
        bucket_results.append(
            {
                "bucket": bucket,
                "n": len(a),
                "binary": [
                    compare_paired(a, b, metric="rca_correct", binary=True),
                    compare_paired(a, b, metric="task_success", binary=True),
                ],
                "continuous": [
                    compare_paired(a, b, metric="total_tokens"),
                    compare_paired(a, b, metric="latency_ms"),
                    compare_paired(a, b, metric="tool_calls"),
                    compare_paired(a, b, metric="evidence_completeness"),
                ],
            }
        )
    return bucket_results


def render_summary_markdown(artifacts: dict[str, Any]) -> str:
    lines = [
        "# CloudOps Harness Evaluation Results",
        "",
        f"tag: `{artifacts['tag']}`",
        f"generated: {artifacts['generated_at']}",
        f"adapter_type: `{artifacts.get('adapter_type')}`",
        f"repeat: {artifacts.get('repeat', 1)}",
        "",
    ]
    if artifacts.get("budget_exceeded"):
        lines.append(
            f"**BUDGET EXCEEDED**: stopped at {artifacts.get('total_api_calls_at_stop')} API calls / {artifacts.get('total_tokens_at_stop')} tokens"
        )
        lines.append("")
    for name, payload in artifacts["systems"].items():
        agg = payload["aggregate"]
        lines.append(f"## {name}")
        lines.append("")
        lines.append(f"- n={agg['n']}")
        for key in (
            "task_success_rate",
            "rca_root_cause_accuracy",
            "rca_localization_accuracy",
            "rca_fault_type_accuracy",
            "root_cause_accuracy",
            "task_completion_rate",
            "tool_selection_accuracy",
            "tool_precision",
            "tool_recall",
            "tool_f1",
            "evidence_completeness",
            "evidence_grounding_precision",
            "evidence_recall",
            "unsupported_claim_rate",
            "unsafe_action_rate",
            "unsafe_action_rate_dangerous",
            "unsafe_execution_count",
            "hitl_compliance_rate",
            "hitl_recall",
            "hitl_precision",
            "decision_binding_accuracy",
            "resume_success_rate",
            "remediation_verification_rate",
            "mean_unnecessary_tool_call_rate",
            "mean_delegation_accuracy",
        ):
            lines.append(f"- {key}: {agg[key]:.4f}")
        for key in ("recovery_success_rate", "mean_recovery_latency_ms", "post_reject_continuation_rate"):
            if agg.get(key) is not None:
                lines.append(f"- {key}: {agg[key]:.4f}")
        for key in (
            "mean_tool_calls",
            "mean_llm_calls",
            "mean_total_tokens",
            "mean_prompt_tokens",
            "mean_completion_tokens",
            "mean_latency_ms",
            "mean_model_latency_ms",
            "mean_tool_latency_ms",
            "mean_main_context_tokens",
        ):
            if agg.get(key) is not None:
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
    lines.append("## Bucket comparisons (single-agent vs harness)")
    lines.append("")
    for bucket in artifacts.get("bucket_comparisons", []):
        lines.append(f"### {bucket['bucket']} (n={bucket['n']})")
        for entry in bucket["binary"]:
            lines.append(
                f"- {entry['metric']}: a={entry['a_rate']:.3f} b={entry['b_rate']:.3f} "
                f"McNemar p={entry['mcnemar_p']:.4f}"
            )
        for entry in bucket["continuous"]:
            lines.append(
                f"- {entry['metric']}: mean_diff={entry['mean_diff']:.2f} "
                f"95% CI [{entry['ci_low']:.2f}, {entry['ci_high']:.2f}]"
            )
        lines.append("")
    return "\n".join(lines)


def default_scenarios_path() -> Path:
    return Path(__file__).resolve().parents[3] / "fixtures" / "incidents" / "scenarios.json"


def load_default_scenarios() -> list[dict[str, Any]]:
    return load_scenarios(default_scenarios_path())
