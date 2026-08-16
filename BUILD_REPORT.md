# CloudOps Harness Build Report (v0.2.2 Final Bug Fix Release)

- 项目根目录：本地仓库（GitHub: lzmy18131/CloudOpsHarness）
- Python 3.11.15（项目 venv）
- 依赖全部固定（langgraph 1.2.11 / fastapi 0.141.1 / pydantic 2.13.4 / fastmcp 3.4.7 / openai 2.54.0 …）
- `ruff check src tests scripts` ✅ · `ruff format --check` ✅
- Tests：**collected 134 · passed 133 · failed 0 · skipped 1**（skipped = real-Docker smoke，本机 daemon 不可用）

## v0.2.2 Final Bug Fixes (on top of v0.2.1)

- HITL multi-action exact `action_id` binding; no decision => reject (unit tests cover multi-action, nonexistent id, ambiguous legacy).
- Checkpoint `user_id:thread_id` namespace; storage `get_thread(thread_id, user_id=...)`; ambiguity test + namespace isolation test.
- Model-call budget ContextVar (`llm/budget.py`) concurrency/overflow tests.
- Docker `upload()` creates parent dirs before `docker cp`.
- ToolCallLimitMiddleware uses run budget; MIT LICENSE added.

## v0.2.1 Blockers Fixed

| Blocker | Before | Fix | Test |
|---|---|---|---|
| Tool call limit | Registry 进程级累计，跨 run 泄漏 | `ToolCallBudget` ContextVar，run-scoped；global_telemetry 仅统计 | per-run / concurrent / overflow 3 tests |
| dry_run_action | registry 未注册，approval 捕获 error 当 payload | 注册 L0 工具 + valid payload 强制；invalid 直接阻断 HITL | registry + executor payload tests |
| Docker workspace | read-only root 下 /workspace 不可写 | `--tmpfs /workspace:rw,nosuid,nodev,size=256m` | args test + real-Docker smoke（daemon 可用时运行，否则 skip） |
| Sandbox proxy | rebuild 后 Proxy→Proxy→Backend | `_build_backend()` 返回 Backend，`replace_backend(new Backend)` | 连续 3 次 recovery：id(proxy) 不变、backend 更换、无嵌套 |
| Identifier security | user_id/thread_id 直接拼路径 | `validate_identifier()` + path containment + API 403 ownership 检查 | traversal tests（../admin, ../../etc, /tmp/a, ../../../x） |
| Recovery latency | 测的是恢复后单条命令 duration | failure→rebuild→hot-swap→retry 全链路计时 | payload `recovery` 字段 test；evaluation 读 total_recovery_ms |
| Rename | AegisOps | CloudOps Harness（`cloudops_harness` package + `aegisops` import shim + CLOUDOPS_ env） | full regression |
| Version | 0.1.0/0.2.0 | 0.2.1（pyproject/Settings/__init__/docs 一致） | n/a |

## Evaluation (真实运行)

- Artifact：`eval_results/offline_20260816T060613Z/summary.json`（n=110 × 5 systems，FakeLLM offline）
- Real LLM：**NOT COMPLETED**（无 API key；`scripts/run_real_eval.py` 就绪）

| | Single | Multi | Multi no-iso | Harness | Harness no-rec |
|---|---|---|---|---|---|
| RCA / Completion | 1.000 / 1.000 | 1.000 / 1.000 | 1.000 / 1.000 | 1.000 / 1.000 | 1.000 / 1.000 |
| Unsafe (dangerous) | 1.000 (10 exec) | 1.000 (10 exec) | 1.000 (10 exec) | **0.000 (0)** | 0.000 (0) |
| HITL recall | 0.000 | 0.000 | 0.000 | **1.000** | 1.000 |
| Recovery | 0/10 | 10/10 | 10/10 | **10/10** | 0/10 |
| Recovery latency mean/median/P95 ms | - | 159.3/156.0/172.0 | 159.3/156.0/172.0 | 159.5/156.5/172.0 | - |
| Resume success | 0.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| Main-context tokens | n/a | 1326.9 | 1372.8 | 1326.9 | 1326.9 |
| Mean token cost | 4803.4 | 39283.3 | 39337.0 | 39280.9 | 39274.3 |
| Mean latency ms | 56.0 | 115.6 | 107.8 | 110.2 | 95.9 |

- Unsafe：Single/Harness、Multi/Harness McNemar p=0.002。
- Recovery：Harness vs no-recovery p=0.002。
- Isolation：main-context +45.9 token（CI 见 artifact）；不夸大为 “dramatically reduces”。
- FakeLLM 结论：验证 harness/safety/recovery/overhead，不代表真实模型智能。

## Demos & Smoke

- Demo A：dry-run 成功 → HITL approve → rollback → verify → report ✅
- Demo B：DB pool → sandbox → RCA ✅
- Demo C：reject → no action → safe alternative ✅
- Demo D：sandbox crash → 同 proxy 重建 → HITL → SQLite reopen → resume → finish ✅
- uvicorn：health/SSE interrupt/resume/history/trace 实测 ✅

## Limitations

1. 真实 LLM evaluation NOT COMPLETED（无 key）。
2. Docker real smoke 本机跳过（daemon/image 不可用）；CI 上 Docker 可用时自动执行。
3. Sandbox recovery 注入样本 n=10；不做 30 的夸大。
4. User isolation = logical isolation（Demo Identity），不是生产 authN/authZ；API 在提供 user_id 时校验 thread ownership。
5. DockerSandboxBackend 是项目级隔离，不是 hardened microVM sandbox。
6. LocalSandboxBackend 仅 dev fallback。
7. mypy strict 未纳入 CI。
