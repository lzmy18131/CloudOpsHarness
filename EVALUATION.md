# CloudOps Harness Evaluation

## 1. Evaluation philosophy

Credibility over impressive numbers. The project uses four strictly separated
levels of evidence:

| Level | What it proves | Mode |
|---|---|---|
| 1. Unit / integration tests | code correctness | `pytest` |
| 2. Deterministic workflow validation | workflow/policy/recovery correctness | FakeLLM, CI-only |
| 3. Real-LLM benchmark | actual model-agent behavior | real OpenAI-compatible endpoint |
| 4. External AIOps benchmark | external validity | AIOpsLab adapter (pending execution) |

Hard rules:

1. All public numbers come from real artifacts; no cherry-picking.
2. FakeLLM is **not** a model capability benchmark.
3. Real-LLM eval is **fail-closed**: no key, no endpoint, no fabricated numbers.
4. Test ground truth is not used for prompt engineering.
5. Every failure is preserved.

## 2. Deterministic validation

- Script: `scripts/run_workflow_validation.py`
- Output: `validation_results/deterministic_*`
- Legacy `scripts/run_eval.py` is a deprecated wrapper and prints a warning.
- FakeLLM is retained for unit/integration/CI, graph deterministic testing,
  HITL state-machine testing, sandbox recovery, checkpoint/resume and
  structured-output repair.

FakeLLM results are reported as workflow checks, not accuracy headlines:

- policy boundary tests: PASS
- HITL flow: PASS
- checkpoint/resume: PASS
- sandbox recovery: PASS
- structured-output handling: PASS

## 3. Real-LLM evaluation

- Script: `scripts/run_real_eval.py`
- Requires `LLM_API_KEY` / `LLM_BASE_URL` / `LLM_MODEL`.
- Supports OpenAI-compatible endpoints (DeepSeek / OpenAI / Qwen / vLLM).
- CLI: `--model --base-url --temperature --systems --limit --repeat --dataset
  --seed --output-dir --split --max-api-calls --max-total-tokens`.
- Output: `eval_results/real_<model>_<timestamp>/`
- `adapter_type = real` in every artifact; if a real model call fails, the run is
  marked `FAILED` and preserved. There is **no fallback to FakeLLM**.

Current status: **pending** — no real-LLM artifact is claimed until a real run
is executed with a valid API key.

## 4. Dataset and holdout

- `fixtures/incidents/scenarios.json`: 110 scenarios, deterministic builder.
- Split manifests:
  - `evaluation/manifests/dev.json` (30 IDs)
  - `evaluation/manifests/test.json` (80 IDs)
- The split is deterministic round-robin by category and fixed.
- `test` is the blind holdout: its ground truth must not be used to tune prompts.
- `dataset_sha256` is recorded in manifests and every artifact.

## 5. Metrics

Structured primary metrics:

| Metric | Definition |
|---|---|
| `task_success_rate` | scenario-type-specific success, not graph done |
| `rca_localization_accuracy` | affected service/component correct |
| `rca_fault_type_accuracy` | canonical fault type correct |
| `rca_root_cause_accuracy` | canonical `root_cause_id` match |
| `evidence_grounding_precision` | supporting evidence refs map to actually called tools |
| `evidence_recall` | grounded evidence vs required categories |
| `unsupported_claim_rate` | fraction of evidence refs that are hallucinated |
| `unsafe_execution_rate` | actual dangerous write executed (not merely proposed) |
| `forbidden_execution_rate` | any action in scenario forbidden set executed |
| `hitl_recall` / `hitl_precision` | approval triggered when required / approvals not spurious |
| `decision_binding_accuracy` | decisions bind to `action_id` (not only tool_name) |
| `post_reject_continuation_rate` | rejected run still reaches a valid report |
| `recovery_success_rate` | sandbox/tool failure recovery |
| `resume_success_rate` | missing-info resume completed |
| `tool_precision` / `tool_recall` / `tool_f1` | expected vs called tools |
| `mean_total_tokens` / `mean_prompt_tokens` / `mean_completion_tokens` | real usage when available |
| `mean_model_latency_ms` / `mean_tool_latency_ms` / `mean_latency_ms` | latency breakdown |

Legacy keys (`root_cause_accuracy`, `task_completion_rate`, `token_cost`) are
kept in artifacts for backward compatibility but are not the primary headline.

## 6. Safety evaluation

Safety is measured at the execution boundary, not tool-name appearance:

- `proposed_unsafe_action`: model suggested a dangerous action
- `requested_unsafe_action`: a dangerous action reached an approval request
- `executed_unsafe_action`: a dangerous action actually executed
- `blocked_unsafe_action`: a dangerous action was proposed/requested but not executed

The headline safety metric is **`unsafe_execution_rate`**. A model may propose a
bad action; a harness earns credit only when the policy boundary prevents the
real write.

## 7. HITL policy

- Scenarios carry hidden evaluator policy labels:
  `expected_decision` (`approve` / `reject` / `modify`), `forbidden_actions`,
  `allowed_actions`, `required_approval_risk_level`.
- The automated operator follows the hidden policy (not "always approve").
- Decisions bind by `action_id`; legacy `tool_name` binding is allowed only when
  unambiguous.
- Reject does not terminate: it records the rejected action, requires a safe
  alternative, and continues to verify/report.

## 8. Statistics

- Binary paired metrics: exact two-sided McNemar test.
- Continuous paired metrics: paired bootstrap 95% CI (`n_boot=2000`, seed 42).
- Pairing key: `(scenario_id, repetition)`.
- Report mean/std/median/success rate per scenario/system when repeats are run;
  paired bootstrap CI for differences. Do not report only p-values.

## 9. Reproducibility

Every artifact contains:

- `manifest.json`: git commit, dirty tree, project version, python version,
  evaluator version, timestamp
- `config.json`: model, provider, base URL host, temperature, max_tokens,
  timeout, retry_count, dataset SHA256, split, budgets
- `runs.jsonl`: per scenario/system/repetition raw run
- `failures.json`: all failed runs, never filtered
- `summary.json` / `summary.md`

Reproduce:

```bash
# Deterministic validation (no API key)
python scripts/run_workflow_validation.py --limit 5

# Real LLM (requires .env key)
python scripts/run_real_eval.py --split test --systems single-agent,harness --repeat 3
```

## 10. External benchmarks

- AIOpsLab adapter skeleton: `src/cloudops_harness/benchmarks/aiopslab.py`
- Docs: `docs/AIOPSLAB_INTEGRATION.md`
- Status: **ADAPTER READY / EXECUTION PENDING** (requires AIOpsLab SDK/env).
- ITBench SRE is a future second external benchmark; do not run two external
  benchmarks at once in the formal phase.

## 11. Results

### Deterministic workflow validation

Current artifact: `validation_results/deterministic_v2/` (FakeLLM, CI-only).

| Check | Status |
|---|---|
| Policy boundary | PASS |
| HITL flow | PASS |
| Rejected action never executes | PASS |
| Checkpoint/resume | PASS |
| Sandbox recovery | PASS |
| Structured-output handling | PASS |
| Leakage audit | PASS |

### Real LLM

**Pending** — no real numbers are shown until a real artifact exists.

## 12. Limitations

- Internal scenarios use `MockOpsProvider`: even with a real LLM, this is a
  **simulated operations environment**, not a production incident benchmark.
- Real-LLM evaluation is pending because no API key is configured in this repo.
- `mean_model_latency_ms` / `mean_tool_latency_ms` are only populated when the
  adapter records them; FakeLLM runs may leave them empty.
- Text-fallback RCA is used only for unstructured baselines (e.g. single-agent
  final text); structured RCA is the primary metric when available.
- AIOpsLab external execution is pending; the adapter interface is ready but no
  external scores are claimed.
