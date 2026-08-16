"""Real-LLM evaluation.

Requires LLM_API_KEY / LLM_BASE_URL / LLM_MODEL. Never fabricates results:
this script either runs against a real endpoint or exits with a clear error.
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


async def run(limit: int | None) -> Path:
    settings = Settings(_env_file=str(PROJECT_ROOT / ".env"))
    if not settings.llm_configured:
        raise SystemExit("LLM_API_KEY is not set; real evaluation aborted (no fabricated numbers).")
    scenarios = load_default_scenarios()
    if limit:
        scenarios = scenarios[:limit]
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    output_dir = PROJECT_ROOT / "eval_results" / f"real_{settings.llm_model.replace('/', '_')}_{stamp}"
    systems = [
        SystemConfig(name="single-agent", mode="single", auto_approve_max_risk=3),
        SystemConfig(name="harness", mode="harness", auto_approve_max_risk=1),
    ]
    await run_experiment(
        settings,
        scenarios,
        systems,
        output_dir=output_dir,
        tag=f"real-llm-{settings.llm_model}-n{len(scenarios)}",
    )
    print(f"real evaluation complete: {output_dir}")
    return output_dir


def main() -> None:
    parser = argparse.ArgumentParser(description="CloudOps Harness real-LLM evaluation")
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()
    asyncio.run(run(args.limit))


if __name__ == "__main__":
    main()
