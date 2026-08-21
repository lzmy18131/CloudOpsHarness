"""Generate deterministic dev/test holdout manifests.

The split is deterministic round-robin by category: each scenario category is
sampled before any category is sampled twice, giving a dev set that covers all
task types and a larger blind test set.
"""

from __future__ import annotations

import collections
import hashlib
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATASET = PROJECT_ROOT / "fixtures" / "incidents" / "scenarios.json"
OUT_DIR = PROJECT_ROOT / "evaluation" / "manifests"
DEV_SIZE = 30


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    scenarios = json.loads(DATASET.read_text(encoding="utf-8"))["scenarios"]
    by_category: dict[str, list[str]] = collections.defaultdict(list)
    for scenario in scenarios:
        by_category[scenario["category"]].append(scenario["incident_id"])
    order = sorted(by_category, key=lambda c: (-len(by_category[c]), c))
    remaining = {c: list(v) for c, v in by_category.items()}
    dev: list[str] = []
    used: set[str] = set()
    while len(dev) < DEV_SIZE:
        progressed = False
        for category in order:
            if len(dev) >= DEV_SIZE:
                break
            if remaining[category]:
                dev.append(remaining[category].pop(0))
                used.add(dev[-1])
                progressed = True
        if not progressed:
            break
    if len(dev) < DEV_SIZE:
        for category in order:
            for incident_id in remaining[category]:
                if len(dev) >= DEV_SIZE:
                    break
                dev.append(incident_id)
                used.add(incident_id)
            if len(dev) >= DEV_SIZE:
                break
    test = [s["incident_id"] for s in scenarios if s["incident_id"] not in used]
    sha = _sha256(DATASET)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "dev.json").write_text(
        json.dumps({"dataset_sha256": sha, "ids": dev}, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (OUT_DIR / "test.json").write_text(
        json.dumps({"dataset_sha256": sha, "ids": test}, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"dev={len(dev)} test={len(test)} sha={sha}")


if __name__ == "__main__":
    main()
