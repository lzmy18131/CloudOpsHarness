"""Deprecated wrapper for deterministic workflow validation.

Use ``scripts/run_workflow_validation.py`` instead. This script exists only for
backward compatibility and explicitly warns that FakeLLM results are NOT a
model capability benchmark.
"""

from __future__ import annotations

import sys

import run_workflow_validation


def main() -> None:
    print(
        "WARNING: deterministic FakeLLM validation only; not a model capability benchmark. "
        "Use scripts/run_workflow_validation.py for the current interface.",
        file=sys.stderr,
    )
    run_workflow_validation.main()


if __name__ == "__main__":
    main()
