# CODE_REVIEW_FIX_REPORT (v0.2.2-final)

## 1. Project Rename

- Old name: AegisOps / aegisops / AEGIS_
- New name: **CloudOps Harness**
  - 英文：CloudOps Harness — Harness-Engineered Multi-Agent Incident Response Platform
  - 中文：CloudOps Harness —— 基于 Harness Engineering 的企业级 Multi-Agent 智能故障响应平台
- Files changed: 139（全部 tracked docs/source/tests/static/pyproject/compose/Dockerfile/CI 相关文本）
- Package: `src/cloudops_harness/`；distribution `cloudops_harness`；env prefix `CLOUDOPS_`
- Compatibility: `src/aegisops/__init__.py` shim maps legacy `aegisops.*` imports to `cloudops_harness`
- 残留检查：`git grep AegisOps|aegisops|AEGIS_` 在 tracked 文件中为 0（CHANGELOG 的“原名为 AegisOps”是 rename 记录本身）

## 2. Tool Budget Fix

- BEFORE: `ToolRegistry.call_counts` 是 Registry 实例级全局累计；`tool_call_limit=120` 在进程生命周期内跨 run 泄漏，服务跑久后新用户可能被旧调用数限制。
- ROOT CAUSE: enforcement 与 telemetry 共用一个全局 dict。
- AFTER: `tools/budget.py::ToolCallBudget`（ContextVar，run_id/current_calls/max_calls/per_tool）；`ToolRegistry` 使用当前 context 的 budget 做硬限制；`global_telemetry` 只做统计，不参与 enforcement。API/eval 在每次 invocation 前 `start_tool_budget(run_id)`。
- TESTS:
  - `test_tool_budget_is_run_scoped_not_process_scoped`：run A 用满 120，run B 从 0 开始。
  - `test_tool_budget_is_isolated_across_concurrent_runs`：并发 80+70 不互相影响。
  - `test_registry_gracefully_stops_single_run_overflow`：单 run 超限 graceful stop，telemetry 继续累计。

## 3. Dry Run Fix

- BEFORE: executor 调用 `registry.call("dry_run_action", ...)`，但 `ToolRegistry._build_definitions()` 未注册该工具；`ToolNotFoundError` 被 except 捕获成 `{"error": ...}` 后混入 approval payload。
- ROOT CAUSE: schema/risk/provider 已存在，registry wiring 缺失。
- AFTER:
  - `DryRunActionArgs(action, service, environment, params)` 注册为 L0 工具。
  - `DryRunResult` 含 `valid/action/target/environment/planned_change/before_state/expected_result/rollback_method/risk_level`。
  - Executor 强制 dry-run valid=true 才继续 HITL；invalid/失败返回 `status=dry_run_failed`，不进入审批。
- TESTS:
  - `test_dry_run_action_is_registered_and_returns_valid_payload`（L2 restart + L3 rollback，before_state 断言）
  - `test_main_agent.py` approval 流程断言 `dry_run["valid"] is True` 且含 before_state / expected_impact / rollback_method。

## 4. Docker Workspace

- BEFORE: `--read-only` root，仅 `/tmp` tmpfs；`docker cp` 到 `/workspace`、skill sync、诊断脚本在只读 root 上可能失败。
- AFTER: 保留 read-only root，新增 `--tmpfs /workspace:rw,nosuid,nodev,size=256m`。
- TESTS:
  - 参数级：`test_docker_backend_builds_hardened_run_command` 断言 `/workspace:` tmpfs。
  - 真实 smoke：`tests/integration/test_docker_sandbox.py` 完整 create→ping→upload→read→execute write→download→destroy；daemon 可用时运行，否则 `pytest.skip`（本机 daemon 不可用 → 当前 1 skipped，已如实记录）。

## 5. Sandbox Proxy

- BEFORE: `rebuild()` 调用 `_build()`（返回 `SandboxBackendProxy`）再 `proxy.replace_backend(rebuilt)`，形成 Proxy→Proxy→Backend，连续 recovery 会继续嵌套。
- AFTER: 拆分 `_build_backend()`（返回 Backend）与 `_build()`（Backend→Proxy→seed）；`rebuild()` 使用 `_build_backend()` + `replace_backend(new Backend)` + `_seed_proxy()`，并断言无嵌套。
- TESTS:
  - `test_three_consecutive_recoveries_keep_proxy_stable_without_nesting`：3 次 recovery，`id(proxy)` 不变、`id(proxy.backend)` 改变、backend 非 Proxy。
  - 原 `test_health_check_rebuilds_and_hot_swaps_proxy` 继续通过。

## 6. User Isolation

- Identifier: `security/identifiers.py::validate_identifier()`（`^[A-Za-z0-9_-]{1,64}$`）应用于 Memory、FileThreadStorage、SandboxManager、ChatRequest。路径 containment: `ensure_path_contained()`。
- Thread ownership: resume/history detail/history delete 在提供 `user_id` 时校验 owner，不匹配返回 403。
- Boundary statement（README/SECURITY）：User isolation = logical isolation between supplied user IDs（Demo Identity），**不是 production authentication/authorization**；不伪装多租户 auth。
- TESTS: `test_path_traversal_identifiers_are_rejected`（../admin、../../etc、/tmp/a、../../../x）；user A/B memory/sandbox/history 隔离测试保持通过。

## 7. Recovery Latency

- BEFORE: `mean_recovery_latency_ms` 实际读取恢复后那条 `sandbox_execute` 的 `duration_ms`（命令执行时间），语义错误。
- AFTER: `SandboxToolBridge.execute()` 从第一次 failure detection 计时：rebuild_ms（含 hot swap）+ retry_ms = total_recovery_ms；返回 `recovery{failed_backend,replacement_backend,rebuild_ms,retry_ms,total_recovery_ms,success}`；`metrics._recovery_latency()` 只读 `recovery.total_recovery_ms`。
- TEST: `test_recovery_latency_payload_measures_rebuild_plus_retry` 断言 failed/replacement backend 不同、total=rebuild+retry、retry exit_code 0。
- NEW RESULTS（n=10/系统）：
  - Harness: mean 159.5 / median 156.5 / P95 172.0 ms，10/10 success
  - Harness-no-recovery: 0/10

## 8. Release Cleanup

- version: 0.2.1（pyproject / Settings.app_version / __init__ / docs）
- evaluation n: 统一 110（README / EVALUATION / BUILD_REPORT / ARCHITECTURE）
- middleware: 统一 11
- planning: pending / in_progress / completed / failed / skipped 统一
- README security claims: HITL 代码强制、prompt injection 表述为 “tested paths 下无法直接授权 L2/L3”，Docker 边界表述为 project-level isolation。
- Old evaluation artifact 移除，仅保留新 artifact。

## 9. Tests

- collected: **125**
- passed: **124**
- failed: **0**
- skipped: **1**（real-Docker smoke，本机 daemon/image 不可用）
- ruff: pass · ruff format: pass

## 10. Evaluation

- 新 artifact: `eval_results/offline_20260816T060613Z/summary.json`
- n=110 × 5 systems；系统与指标见 EVALUATION.md / BUILD_REPORT.md。

## 11. Demo

- A: PASS（dry-run valid → HITL approve → rollback → verify → report）
- B: PASS（DB pool → sandbox → RCA）
- C: PASS（reject → no action → safe alternative）
- D: PASS（sandbox crash → rebuild 同 proxy → HITL → SQLite reopen → resume → finish）

## 12b. v0.2.2 final bug fixes

- HITL exact action binding (no fallback approval): `agents/hitl.py` + `tests/unit/test_hitl.py`.
- Checkpoint user namespace + scoped storage: `api/chat.py`, `storage/file_backend.py` + tests.
- Model budget ContextVar: `llm/budget.py` + tests.
- Docker upload parent-dir creation: `sandbox/docker_backend.py` + real smoke nested path.
- ToolCallLimitMiddleware run-budget warning; MIT LICENSE.

## 12. Remaining Limitations

- Real-LLM evaluation：NOT COMPLETED（无 key，脚本就绪）。
- 本机 Docker daemon 不可用：Docker real smoke 为 skipped；CI 有 Docker 时自动执行。
- Sandbox recovery 注入 n=10，未夸大为 30。
- User isolation 为 logical isolation（Demo Identity），非生产 authN/authZ。
- DockerSandboxBackend 为 project-level isolation，非 hardened microVM sandbox。
- LocalSandboxBackend 仅 dev fallback。
- mypy strict 未纳入 CI。
