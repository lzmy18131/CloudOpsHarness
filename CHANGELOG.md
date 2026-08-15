# Changelog

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
