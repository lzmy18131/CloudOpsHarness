# AIOpsLab Integration (External Validity)

**Status: ADAPTER READY / EXTERNAL EXECUTION PENDING**

This document describes how CloudOps Harness can be run as an agent client
against [Microsoft AIOpsLab](https://github.com/microsoft/aiopslab). The goal is
not to copy AIOpsLab into this repository; it is to map AIOpsLab's environment,
telemetry and action APIs onto CloudOps Harness's `ToolRegistry` / `OpsProvider`
boundaries so the same harness, safety and recovery machinery can be evaluated on
an independent benchmark.

## 1. Why external benchmark

The internal `fixtures/incidents/scenarios.json` is authored by the project
itself. Even with a real LLM and a blind holdout split, there is still a risk of
"self-designed task -> self-designed system -> self-scored". AIOpsLab provides:

- independent task definitions and fault injection
- microservice environment with metrics/logs/traces
- standard agent-cloud interface
- external ground truth and evaluator
- comparable horizontal results

Priority order (per Evaluation v2.0):

1. Own Real-LLM Holdout
2. **AIOpsLab**
3. IBM ITBench SRE (future external validity)

## 2. Environment startup (requires AIOpsLab)

```bash
# Outside this repository, clone and start AIOpsLab:
git clone https://github.com/microsoft/AIOpsLab.git
cd AIOpsLab
# Follow upstream README to launch the environment service, workload generator,
# and fault injection service.
```

CloudOps Harness does **not** vendor or reimplement AIOpsLab.

## 3. Harness connection

The adapter lives in:

```
src/cloudops_harness/benchmarks/aiopslab.py
```

It defines:

- `AIOpsLabEnvironment` protocol — the seam expected from an AIOpsLab client
- `AIOpsLabAdapter` — maps CloudOps Harness tool concepts to AIOpsLab calls
- `AIOpsLabBenchmarkRunner` — high-level smoke/pilot/formal runner skeleton

To connect:

```python
from cloudops_harness.benchmarks.aiopslab import AIOpsLabAdapter

env = MyAIOpsLabClient(...)          # implement AIOpsLabEnvironment
adapter = AIOpsLabAdapter(env, run_id="run-001")
provider = adapter.to_ops_provider() # TODO: complete with real AIOpsLab SDK
```

## 4. Telemetry mapping

| CloudOps Harness tool | AIOpsLab concept |
|---|---|
| `query_metrics` | time-series metrics service |
| `query_logs` | structured log service |
| `get_service_health` | service health endpoint |
| `get_service_topology` | service dependency graph |
| `get_recent_deployments` | deployment/change feed |
| `get_config_diff` | configuration diff |
| `get_incident_history` | incident history / lessons (sanitized) |
| `execute_action` | mitigation action (mapped through risk policy) |

All read-only telemetry flows through the normal `ToolRegistry`; write/mitigation
actions must pass the same risk policy and HITL gates as internal scenarios.

## 5. Action mapping and safety

AIOpsLab mitigation actions (e.g. restart, rollback, scale, config change) are
mapped to the existing L2/L3 tool definitions. The CloudOps Harness policy
boundary remains authoritative:

- L0 read-only tools: auto
- L1 low-risk writes: auto or policy
- L2/L3 production-changing/destructive actions: HITL required
- rejected actions are never executed; safe alternatives and continuation are preserved

## 6. Benchmark execution

After `to_ops_provider()` is implemented for the installed AIOpsLab version:

```bash
# Smoke (small, cheap)
python scripts/run_external_aiopslab.py --mode smoke --limit 5
# Pilot (20-30 scenarios)
python scripts/run_external_aiopslab.py --mode pilot
# Formal holdout (when stable)
python scripts/run_external_aiopslab.py --mode formal
```

A `scripts/run_external_aiopslab.py` runner is **not yet committed** because the
adapter execution path is pending. Do not invent numbers before the environment
runs.

## 7. Metrics and artifacts

External benchmark results use the same artifact schema:

```
benchmark_results/aiopslab_<run>/manifest.json
benchmark_results/aiopslab_<run>/summary.json
benchmark_results/aiopslab_<run>/summary.md
benchmark_results/aiopslab_<run>/runs.jsonl
benchmark_results/aiopslab_<run>/failures.json
```

The same metrics (task success, structured RCA, safety, HITL, evidence grounding,
cost/latency) apply. No result may be cherry-picked; all failures are kept.

## 8. Current limitation

This repository currently implements the **adapter interface skeleton**. Running
an actual AIOpsLab benchmark requires the AIOpsLab SDK/environment to be
installed and `AIOpsLabAdapter.to_ops_provider()` to be completed against the
installed version. Until then the honest status is:

> integration implemented, external benchmark execution pending
