"""Offline deterministic evaluation (no LLM key required).

Runs Single-Agent / Multi-Agent / Harness (and ablations) over the scenario
dataset with FakeLLM and writes real, reproducible artifacts to eval_results/.
"""

from __future__ import annotations

import argparse
import asyncio
from datetime import UTC, datetime
from pathlib import Path

from aegisops.config.settings import Settings
from aegisops.evaluation.harness import load_default_scenarios, run_experiment
from aegisops.evaluation.runners import SystemConfig

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


async def run(limit: int | None, data_dir: Path) -> Path:
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
    output_dir = PROJECT_ROOT / "eval_results" / f"offline_{stamp}"
    artifacts = await run_experiment(
        settings, scenarios, systems(), output_dir=output_dir, tag=f"offline-fake-llm-n{len(scenarios)}"
    )
    print(f"evaluation complete: {output_dir}")
    for name, payload in artifacts["systems"].items():
        agg = payload["aggregate"]
        print(
            f"{name}: rca={agg['root_cause_accuracy']:.3f} completion={agg['task_completion_rate']:.3f} "
            f"unsafe={agg['unsafe_action_rate']:.3f} hitl={agg['hitl_compliance_rate']:.3f}"
        )
    return output_dir


def main() -> None:
    parser = argparse.ArgumentParser(description="AegisOps offline evaluation")
    parser.add_argument("--limit", type=int, default=None, help="limit scenarios (default: full dataset)")
    parser.add_argument("--data-dir", type=Path, default=PROJECT_ROOT / "data" / "eval")
    args = parser.parse_args()
    asyncio.run(run(args.limit, args.data_dir))


if __name__ == "__main__":
    main()
