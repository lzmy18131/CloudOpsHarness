# Changelog

## v0.2.2 — Final Bug Fix Release (2026-08-16)

- HITL multi-action approval now requires exact `action_id` binding; no explicit decision => reject (no `decisions[0]` fallback approval).
- LangGraph checkpoint config namespaced as `user_id:thread_id`; storage `get_thread(thread_id, user_id=...)` scopes lookups and refuses ambiguous cross-user collisions.
- Model-call budget moved from a shared Runtime counter to a ContextVar-backed `ModelCallBudget` (concurrent run-scoped, hard stop preserved).
- DockerSandboxBackend.upload creates parent directories (`mkdir -p`) before `docker cp`, so nested seed/skill paths work on a real daemon.
- ToolCallLimitMiddleware now reports the run-scoped budget instead of process-global telemetry.
- Added MIT LICENSE.

## v0.2.1 — Final Resume Release (2026-08-16)

- Project renamed from AegisOps to CloudOps Harness (package `cloudops_harness`, env prefix `CLOUDOPS_`, legacy import shim kept).
- Tool call limit is now run-scoped (ContextVar `ToolCallBudget`); global telemetry split from enforcement; concurrency regression tests added.
- `dry_run_action` is actually registered in `ToolRegistry`; L2/L3 approval payloads contain valid `before_state / expected_impact / rollback_method / valid=true`.
- DockerSandboxBackend mounts a writable `/workspace` tmpfs next to the read-only root; real-Docker smoke test added (auto-skip without daemon).
- SandboxManager.rebuild now hot-swaps a `SandboxBackend` (never Proxy→Proxy); triple-recovery identity test added.
- Central `validate_identifier()` for user_id/thread_id + path containment; path-traversal tests added; optional thread ownership checks (403) in history/resume.
- Recovery latency now measures failure→rebuild→hot-swap→retry success (not post-recovery command duration); payload and trace include failed/replacement backend + rebuild/retry/total ms.
- Release consistency: version 0.2.1, evaluation n=110, 11 middleware, planning states include `skipped`, security claims scoped honestly.

## v0.2.0 — 2026-08-16（专项整改）

### Added
- Unified SSE event envelope (run_id/thread_id/timestamp/sequence) + UI dedup.
- Context compression wired into synthesize with quantified stats.
- Hard limits: model-call budget, max_plan_steps (skipped + partial report), max_delegation_depth.
- dry_run_action L0 tool + dry-run in every HITL approval request.
- Evidence traceability (id/tool/timestamp/service/raw_ref) and RCA supporting/contradicting evidence.
- Change-agent temporal_correlation/correlation/causal_confidence fields.
- Circuit breaker transition log.
- Verification resolved flag + before/after state.
- PII redaction middleware + tool-boundary redaction.
- Richer trace timeline (risk level, agent, HITL decision, action, verification, report).
- Dataset expanded to 110 scenarios (easy/dependency_chain/ambiguous buckets).
- New evaluation metrics + bucket comparisons + recovery latency.
- Security tests (prompt injection / risk bypass / memory isolation).
- Demo D: sandbox crash + process restart resume.

### Fixed
- Resume test now proves pre-interrupt tool calls are not re-executed.
- PII phone regex no longer corrupts numeric tool output.

## v0.1.0 — 2026-08-15

### Added
- Harness-Engineered LangGraph incident-response graph: planning todo, four
  declarative subagents, RCA synthesis, HITL executor, verification, report.
- MockOpsProvider with 10 fault types, deterministic metrics/logs/deployments/
  config diffs/topology and fault-injection hooks.
- FastMCP server + in-process `MCPToolAdapter` boundary (15 tools).
- Risk policy L0–L3 with approval payloads (reason/target/before-state/impact).
- Dual interrupts: missing-info supplement + dangerous-action approval;
  reject → recorded + safe alternative + report.
- SQLite checkpoint persistence (`langgraph-checkpoint-sqlite`); resume after
  process restart covered by tests.
- SSE event stream (`token/plan/agent_*/tool_*/interrupt/error/done`) with
  `messages` + `custom` dual stream modes; static HTML/JS UI.
- Sandbox chain: protocol, Docker backend (hardened), Local fallback, manager
  (prewarm/claim/rebuild/destroy), hot-swap proxy, health middleware, circuit
  breaker, `sandbox_execute/read/write` tools.
- Middleware stack (10): sandbox health, context injection, skills sync, user
  skills restore, memory update, sandbox breaker, model/tool limits, tool
  policy, tracing.
- Memory: per-user `PreferenceStore`; CMDB facts stay in provider tools.
- Skills: 8 progressive-disclosure `SKILL.md` packs + safe `SkillInstaller`.
- Evaluation harness: 100-scenario dataset, Single/Multi/Harness runners,
  McNemar + paired bootstrap, honest JSON/Markdown artifacts.
- History/traces APIs, optional MongoDB storage backend, Dockerfile, compose,
  CI (ruff + pytest, no LLM key).
