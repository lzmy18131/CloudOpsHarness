"""Real-LLM evaluation (fail-closed).

Requires LLM_API_KEY / LLM_BASE_URL / LLM_MODEL. This script never falls back
to FakeLLM: if a real endpoint/model is unavailable, runs are preserved as
FAILED and the artifact records ``adapter_type=real``. If the key is missing,
the script exits without producing a benchmark.
"""

from __future__ import annotations

import argparse
import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path

from cloudops_harness.config.settings import Settings
from cloudops_harness.evaluation.dataset import load_scenarios
from cloudops_harness.evaluation.harness import default_scenarios_path, run_experiment
from cloudops_harness.evaluation.runners import SystemConfig

PROJECT_ROOT = Path(__file__).resolve().parents[1]

SYSTEM_FACTORIES: dict[str, callable] = {
    "single-agent": lambda: SystemConfig(name="single-agent", mode="single", auto_approve_max_risk=3),
    "multi-agent": lambda: SystemConfig(name="multi-agent", mode="multi", auto_approve_max_risk=3),
    "multi-no-isolation": lambda: SystemConfig(
        name="multi-no-isolation", mode="multi", auto_approve_max_risk=3, context_isolation=False
    ),
    "harness": lambda: SystemConfig(
        name="harness", mode="harness", auto_approve_max_risk=1, sandbox_auto_recovery=True
    ),
    "harness-no-recovery": lambda: SystemConfig(
        name="harness-no-recovery", mode="harness", auto_approve_max_risk=1, sandbox_auto_recovery=False
    ),
}


def _settings(args: argparse.Namespace) -> Settings:
    kwargs: dict[str, object] = {
        "_env_file": str(PROJECT_ROOT / ".env"),
        "llm_temperature": args.temperature,
    }
    if args.model:
        kwargs["llm_model"] = args.model
    if args.base_url:
        kwargs["llm_base_url"] = args.base_url
    return Settings(**kwargs)


def _load_split_scenarios(split: str | None, dataset_path: Path) -> list[dict]:
    scenarios = load_scenarios(dataset_path)
    if split in {None, "all"}:
        return scenarios
    manifest_path = PROJECT_ROOT / "evaluation" / "manifests" / f"{split}.json"
    if not manifest_path.exists():
        raise SystemExit(f"split manifest not found: {manifest_path}")
    ids = set(json.loads(manifest_path.read_text(encoding="utf-8"))["ids"])
    return [s for s in scenarios if s["incident_id"] in ids]


async def run(args: argparse.Namespace) -> Path:
    from cloudops_harness.evaluation.real import RealEvalError, ensure_real_configured

    settings = _settings(args)
    try:
        ensure_real_configured(settings)
    except RealEvalError as exc:
        raise SystemExit(str(exc)) from exc
    systems = [SYSTEM_FACTORIES[name]() for name in args.systems]
    if not systems:
        raise SystemExit("--systems must contain at least one system")
    scenarios = _load_split_scenarios(args.split, args.dataset)
    if args.limit is not None:
        scenarios = scenarios[: args.limit]
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    model_slug = settings.llm_model.replace("/", "_")
    output_dir = (
        Path(args.output_dir)
        if args.output_dir
        else PROJECT_ROOT / "eval_results" / f"real_{model_slug}_{stamp}"
    )
    await run_experiment(
        settings,
        scenarios,
        systems,
        output_dir=output_dir,
        tag=f"real-llm-{settings.llm_model}-n{len(scenarios)}-r{args.repeat}",
        repeat=args.repeat,
        seed=args.seed,
        max_api_calls=args.max_api_calls,
        max_total_tokens=args.max_total_tokens,
        split_name=args.split,
        dataset_path=args.dataset,
    )
    print(f"real evaluation complete: {output_dir}")
    return output_dir


def main() -> None:
    parser = argparse.ArgumentParser(description="CloudOps Harness real-LLM evaluation (fail-closed)")
    parser.add_argument("--model", default=None, help="override LLM_MODEL")
    parser.add_argument("--base-url", default=None, help="override LLM_BASE_URL")
    parser.add_argument("--temperature", type=float, default=0.2, help="override LLM_TEMPERATURE")
    parser.add_argument(
        "--systems",
        default="single-agent,harness",
        help="comma-separated systems: single-agent,multi-agent,multi-no-isolation,harness,harness-no-recovery",
    )
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--repeat", type=int, default=3, help="repetitions per scenario/system (default 3)")
    parser.add_argument("--dataset", type=Path, default=default_scenarios_path())
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument(
        "--split",
        default=None,
        help="split manifest name under evaluation/manifests (dev, test, all, or custom file name)",
    )
    parser.add_argument("--max-api-calls", type=int, default=None, help="hard budget: stop after N LLM calls")
    parser.add_argument(
        "--max-total-tokens", type=int, default=None, help="hard budget: stop after N total tokens"
    )
    args = parser.parse_args()
    args.systems = [s.strip() for s in args.systems.split(",") if s.strip()]
    unknown = [s for s in args.systems if s not in SYSTEM_FACTORIES]
    if unknown:
        raise SystemExit(f"unknown system(s): {unknown}")
    asyncio.run(run(args))


if __name__ == "__main__":
    main()
