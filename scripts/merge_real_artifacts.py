"""Merge separately-run Single-Agent and Harness real artifacts into one artifact.

Usage:
    python scripts/merge_real_artifacts.py --single <dir> --harness <dir> --out <dir>
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from cloudops_harness.evaluation.harness import (
    _build_bucket_comparisons,
    _build_comparisons,
    render_summary_markdown,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--single", required=True, type=Path)
    parser.add_argument("--harness", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()

    systems = {}
    for system_name, src in (("single-agent", args.single), ("harness", args.harness)):
        summary = json.loads((src / "summary.json").read_text(encoding="utf-8"))
        systems[system_name] = summary["systems"][system_name]

    artifacts = {
        "tag": "real-deepseek-v4-flash-portfolio-merged",
        "generated_at": summary.get("generated_at", ""),
        "adapter_type": "real",
        "repeat": 1,
        "systems": systems,
    }
    artifacts["comparisons"] = _build_comparisons(artifacts)
    artifacts["bucket_comparisons"] = _build_bucket_comparisons(artifacts)

    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "summary.json").write_text(
        json.dumps(artifacts, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (args.out / "summary.md").write_text(render_summary_markdown(artifacts), encoding="utf-8")

    runs = []
    failures = []
    for system_name, src in (("single-agent", args.single), ("harness", args.harness)):
        with (src / "runs.jsonl").open("r", encoding="utf-8") as handle:
            for line in handle:
                run = json.loads(line)
                run["system"] = system_name
                runs.append(run)
                if run.get("status") != "done" or run.get("task_success") is False:
                    failures.append(run)
    with (args.out / "runs.jsonl").open("w", encoding="utf-8") as handle:
        for run in runs:
            handle.write(json.dumps(run, ensure_ascii=False, default=str) + "\n")
    (args.out / "failures.json").write_text(
        json.dumps({"count": len(failures), "failures": failures}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    # Copy provenance/config from the single-agent artifact (safe; no key).
    for name in ("manifest.json", "config.json", "dataset_manifest.json"):
        src = args.single / name
        if src.exists():
            (args.out / name).write_text(src.read_text(encoding="utf-8"), encoding="utf-8")

    print(f"merged artifact written to {args.out}")


if __name__ == "__main__":
    main()
