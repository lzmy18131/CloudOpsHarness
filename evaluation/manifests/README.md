# Holdout Manifests

- `dev.json` — 30 scenario IDs for prompt/system development.
- `test.json` — 80 scenario IDs for blind holdout evaluation.

Rules:

1. Test ground truth must **not** be used for prompt engineering or system tuning.
2. If you tune on `test`, the split is no longer blind; move those scenarios to `dev`.
3. The `dataset_sha256` in each manifest must match
   `fixtures/incidents/scenarios.json`; if the dataset changes, regenerate the
   manifests and audit whether the split semantics are preserved.

Regenerate with the same deterministic round-robin-by-category logic used in the
initial generation (see `scripts/generate_manifests.py` when added).
