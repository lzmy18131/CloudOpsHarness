# Real Smoke Failure Analysis (Limited Paired n=5)

This analysis is offline from `runs.jsonl`. No additional DeepSeek API calls were
made.

## Summary

- Single RCA accuracy: 0.000 / 5
- Harness RCA accuracy: 0.000 / 5
- Single task success: 0.000 / 5
- Harness task success: 0.200 / 5
- Harness recovery success: 1.000 / 5
- Single recovery success: 0.000 / 5

## Most Common Failure Categories

- Wrong canonical RCA: model structured diagnosis did not match `root_cause_id`.
- Unsupported evidence claims: supporting evidence references were not traceable
  to tools actually called in the run (especially Harness).
- Low evidence grounding precision in Harness (0.033).

## Representative Cases

### Case 1 — RCA mismatch (both systems)

- Scenario: normal/simple diagnosis in dev smoke
- Ground truth: canonical root cause release regression
- Predicted: model identified a plausible incident narrative but did not emit the
  canonical `affected_service | fault_type | root_cause_component` triple.
- Tools used: expected read tools were mostly called.
- Root failure reason: structured RCA normalization / canonical matching is strict.

### Case 2 — Harness unsupported evidence

- Scenario: multi-source / complex dev case
- Harness evidence refs often pointed to internal evidence IDs that were not
  resolved to actual called tool names.
- Root failure reason: evidence grounding mapping in this run did not connect
  final `supporting_evidence` to tool call records.

### Case 3 — Recovery improvement

- Scenario: sandbox failure dev case
- Harness recovered via sandbox hot-swap; Single had no recovery path.
- Result: Harness recovery success 1.0 vs Single 0.0.

## Note

This is a stop-loss limited analysis. It is not a formal-20 failure analysis.
