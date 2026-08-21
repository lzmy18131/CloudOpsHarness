"""Deterministic workflow validation (FakeLLM, CI-only).

This is NOT a model capability benchmark. FakeLLM is a scenario-driven test
driver; it proves workflow/policy/recovery correctness, not intelligence.
Results are written to ``validation_results/deterministic_*``.
"""

from __future__ import annotations

import argparse
import asyncio
from datetime import UTC, datetime
from pathlib import Path

from cloudops_harness.config.settings import Settings
from cloudops_harness.evaluation.harness import load_default_scenarios, run_experiment
from cloudops_harness.evaluation.runners import SystemConfig

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def systems() -> list[SystemConfig]:
    return [
        SystemConfig(name="single-agent", mode="single", auto_approve_max_risk=3),
        SystemConfig(name="multi-agent", mode="multi", auto_approve_max_risk=3),
        SystemConfig(
            name="multi-no-isolation",
            mode="multi",
            auto_approve_max_risk=3,
            context_isolation=False,
        ),
        SystemConfig(name="harness", mode="harness", auto_approve_max_risk=1, sandbox_auto_recovery=True),
        SystemConfig(
            name="harness-no-recovery",
            mode="harness",
            auto_approve_max_risk=1,
            sandbox_auto_recovery=False,
        ),
    ]


async def run(
    limit: int | None,
    data_dir: Path,
    output_dir: Path | None = None,
    repeat: int = 1,
    seed: int = 42,
) -> Path:
    settings = Settings(
        _env_file=None,
        environment="test",
        data_dir=data_dir,
        fixtures_dir=PROJECT_ROOT / "fixtures",
        skills_dir=PROJECT_ROOT / "skills",
        sandbox_backend="local",
    )
    scenarios = load_default_scenarios()
    if limit:
        scenarios = scenarios[:limit]
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    target = output_dir or PROJECT_ROOT / "validation_results" / f"deterministic_{stamp}"
    artifacts = await run_experiment(
        settings,
        scenarios,
        systems(),
        output_dir=target,
        tag=f"deterministic-fake-llm-n{len(scenarios)}",
        repeat=repeat,
        seed=seed,
    )
    print(f"deterministic validation complete: {target}")
    for name, payload in artifacts["systems"].items():
        agg = payload["aggregate"]
        print(
            f"{name}: task_success={agg['task_success_rate']:.3f} "
            f"rca={agg['rca_root_cause_accuracy']:.3f} unsafe_exec={agg['unsafe_execution_count']}"
        )
    return target


def main() -> None:
    parser = argparse.ArgumentParser(
        description="CloudOps Harness deterministic workflow validation (FakeLLM, CI-only, NOT a benchmark)"
    )
    parser.add_argument("--limit", type=int, default=None, help="limit scenarios (default: full dataset)")
    parser.add_argument("--data-dir", type=Path, default=PROJECT_ROOT / "data" / "eval")
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--repeat", type=int, default=1)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    asyncio.run(run(args.limit, args.data_dir, args.output_dir, args.repeat, args.seed))


if __name__ == "__main__":
    main()
