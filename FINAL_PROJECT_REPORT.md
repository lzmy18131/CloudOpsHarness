# CloudOps Harness — Final Project Report

## 1. Objective

CloudOps Harness is a **reliability-oriented Multi-Agent Runtime for AIOps
incident response**. The objective is not to make a base LLM "smarter"; it is to
make agent execution safer, more recoverable and more auditable through a
LangGraph-based harness.

## 2. Architecture

- FastAPI + SSE event stream
- LangGraph stateful graph: prepare → planner → subagents → synthesize → executor → verify → report
- Middleware stack (11 pluggable middlewares)
- Model adapter: OpenAI-compatible (DeepSeek / OpenAI / Qwen / vLLM) or FakeLLM (offline)
- ToolRegistry → MCP → MockOpsProvider
- Sandbox chain: health → manager → proxy → Docker/Local backend
- SQLite checkpoint / resume
- JSONL traces

## 3. Why Harness

A single agent can diagnose incidents, but long-running agentic workflows need:

- context isolation
- policy boundaries
- HITL
- checkpoint/resume
- sandbox recovery
- circuit breakers

The Harness is designed to trade higher inference cost for these properties.

## 4. Context Isolation

Subagent transcripts never enter the main-agent context. The main agent only
receives structured `SubAgentReport` evidence. This is enforced by
`assemble_main_messages()` and covered by integration tests.

## 5. Tool Safety Boundary

`ToolRegistry` enforces risk levels L0–L3. Dangerous production-changing tools
cannot be called without HITL approval. `ToolApprovalRequiredError` is raised at
the boundary, not in prompt text.

## 6. HITL

- Missing information → interrupt → resume with supplement
- Dangerous action → approval request with `action_id`
- Reject does not terminate; safe alternative + continue
- Decisions bind by `action_id`; legacy tool-name binding only when unambiguous

## 7. Checkpoint / Resume

LangGraph checkpoints are written before interrupts. A process restart can resume
from the same state without re-running completed tool calls. Covered by
`tests/integration/test_checkpoint_resume.py`.

## 8. Sandbox Recovery & Circuit Breaker

Sandbox execute failures trigger circuit breaker → manager rebuild → proxy hot
swap → retry. The proxy identity remains stable across rebuilds.

## 9. Evaluation Methodology

- FakeLLM is deterministic validation / CI only, **not** a capability benchmark.
- Real evaluation is fail-closed: no key, no fallback to FakeLLM.
- Ground-truth leakage audit is automated.
- Real artifacts contain `adapter_type=real`, model, base URL host, dataset SHA256,
  runs.jsonl, failures.json, manifest.json, config.json.

## 10. DeepSeek-V4-Flash Real Evaluation

- Model: `deepseek-v4-flash`
- Base URL: `https://api.deepseek.com`
- Temperature: `0.0`
- Provider usage tokens recorded from API responses.
- Real paired runs completed on **5 dev incidents** (Single + Harness).
- A 20-scenario Formal Harness run was started but stopped under stop-loss before
  producing a complete paired artifact.

## 11. Formal-20 Results

**Not completed as a paired benchmark.**

- `Single-Agent` formal-20 exploratory artifact exists:
  `eval_results/real_deepseek_v4_flash_portfolio_formal_single/`
- `Harness` formal-20 did not complete; no paired formal-20 table is claimed.

## 12. Stability-10 Results

**Incomplete exploratory artifact excluded from formal claims.**

- `Single-Agent` stability-10 artifact exists:
  `eval_results/real_deepseek_v4_flash_portfolio_stability_single/`
- Stability Harness was not run to avoid disproportionate API cost.

## 13. Single vs Harness Trade-offs (limited paired n=5)

From `eval_results/real_smoke_deepseek_v4_flash_final/`:

| Metric | Single | Harness | Delta |
| --- | ---: | ---: | ---: |
| Task Success | 0.000 | 0.200 | +0.200 |
| RCA Accuracy | 0.000 | 0.000 | 0.000 |
| Service Localization | 1.000 | 1.000 | 0.000 |
| Evidence Grounding Precision | 0.429 | 0.033 | −0.395 |
| Unsupported Claim Rate | 0.571 | 0.967 | +0.395 |
| Tool F1 | 0.623 | 0.547 | −0.076 |
| HITL Recall | 0.000 | 0.000 | 0.000 |
| Unapproved Unsafe Execution | 0.000 | 0.000 | 0.000 |
| Recovery Success | 0.000 | 1.000 | +1.000 |
| Mean Total Tokens | 162,068 | 199,208 | +37,140 |
| Mean Model Calls | 9.2 | 32.2 | +23.0 |
| P95 Latency (ms) | 63,906 | 303,391 | +239,485 |

Interpretation: this is a **portfolio-scale smoke/limited validation**. The
Harness did not improve RCA or evidence grounding on this sample. It did improve
recovery success and never performed an unapproved unsafe execution, but at
substantially higher token, call and latency cost.

## 14. Cost / Latency

- Harness uses ~3.5× more model calls than Single (32.2 vs 9.2).
- Harness uses ~1.23× more total tokens (199k vs 162k).
- Harness P95 latency is ~4.7× higher (303s vs 64s).

This is the expected cost of orchestration, safety checks, subagents and recovery.

## 15. Failure Analysis

A full formal failure analysis was not possible because Harness-20 did not
complete. From the limited real smoke, observed issues include:

- Low RCA accuracy for both systems (0.000 on n=5): model structured RCA did not
  match canonical `root_cause_id`.
- High unsupported claim rate for Harness (0.967): supporting evidence references
  were often not traceable to actually called tools.
- Single achieved higher evidence grounding precision (0.429) than Harness (0.033).
- Harness recovery success was 1.000 vs Single 0.000 on the sandbox-failure case.

See `eval_results/real_smoke_deepseek_v4_flash_final/failure_analysis.md`.

## 16. Limitations

- Real LLM, but Ops backend is **simulated MockOpsProvider**, not production.
- Portfolio-scale sample: paired n=5; Single formal-20 exploratory n=20 unpaired.
- No completed paired Formal-20 Harness artifact.
- No completed Stability Harness.
- One real model only (`deepseek-v4-flash`); results are not generalizable.
- AIOpsLab external benchmark not executed in the portfolio release.
- Harness inference overhead is high.

## 17. External Benchmark Status

**AIOpsLab: adapter scaffold available; external execution not included in
portfolio release.**

## 18. Reproducibility

- Real artifacts: `eval_results/real_smoke_deepseek_v4_flash_final/`,
  `eval_results/real_deepseek_v4_flash_portfolio_formal_single/`,
  `eval_results/real_deepseek_v4_flash_portfolio_stability_single/`
- Manifests: `evaluation/manifests/portfolio_*.json`
- Lock: `evaluation/portfolio_eval_lock.json`
- Tests: `pytest -q` (150 passed, 1 skipped)
- Lint/format: pass

## 19. Final Conclusion

CloudOps Harness demonstrates a real DeepSeek-V4-Flash integration with
fail-closed evaluation, leakage controls, safety boundaries and recovery
machinery. On the limited paired sample, the Full Harness did **not** make the
base LLM smarter; it traded significantly higher cost/latency for recovery and
safety-oriented control. This is an honest portfolio-scale result.

**Project is frozen as the final portfolio release.**
