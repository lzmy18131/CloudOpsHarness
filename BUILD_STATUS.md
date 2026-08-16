# BUILD_STATUS

> 仓库：https://github.com/lzmy18131/CloudOpsHarness
> 版本：**v0.2.2** · commit：见 `git log`（最新） · tag：**v0.2.2**

## v0.2.2 Final Bug Fix 状态

| Fix | Severity | 说明 | Tests |
|---|---|---|---|
| HITL exact action binding | P0 | 每个 `ActionRequest` 唯一 `action_id`；Decision 必须精确绑定；无明确 decision 默认 **reject**，删除 `decisions[0]` 兜底误批准 | `tests/unit/test_hitl.py`（multi-action / nonexistent id / ambiguous legacy） |
| Checkpoint 按用户隔离 | P0 | LangGraph checkpoint 命名空间 `user_id:thread_id`；`get_thread(thread_id, user_id=...)` 作用域查询，跨用户同 thread_id 直接报 ambiguity，绝不静默串状态 | `test_checkpoint_resume.py` + `test_storage.py` |
| Model-call budget 并发安全 | P1 | 从 Runtime 共享 counter 改为 ContextVar `ModelCallBudget`（run-scoped，保留硬上限） | `tests/unit/test_llm.py`（concurrent run isolation / overflow） |
| Docker upload 嵌套路径 | P1 | `upload()` 先 `mkdir -p` 父目录再 `docker cp` | args test + real-Docker smoke（daemon 可用时） |
| ToolCallLimitMiddleware 读 run budget | non-blocker | middleware 统计与硬上限口径一致 | full regression |
| MIT LICENSE | non-blocker | 补齐开源许可证 | n/a |

## v0.2.1 Release Blocker 修复状态（历史，已并入 v0.2.2）

| Blocker | Status | Tests |
|---|---|---|
| 项目改名 CloudOps Harness（package/env/docs/UI/metadata + legacy shim） | ✅ | full regression |
| Tool call limit run-scoped（ContextVar budget；telemetry 分离） | ✅ | 3 budget regression tests |
| dry_run_action 真正注册 + valid payload + dry-run 失败阻断 HITL | ✅ | registry + executor payload tests |
| Docker /workspace writable tmpfs + real Docker smoke | ✅ / ⚠️本机 skip | args test + docker smoke（daemon 可用时） |
| Sandbox 无 Proxy→Proxy；连续 recovery | ✅ | 3×recovery identity test |
| user_id/thread_id 中央校验 + path containment + traversal tests | ✅ | 4 traversal cases |
| Recovery latency 真正测量 failure→rebuild→hot-swap→retry | ✅ | latency payload test |
| 版本 0.2.1 / n=110 / 11 middleware / planning 五状态 / claims 一致 | ✅ | n/a |

## 最终状态（v0.2.2）

- Tests：**collected 134 · passed 133 · failed 0 · skipped 1**（skipped = real-Docker smoke，本机 daemon 不可用）
- ruff check ✅ · ruff format --check ✅
- Evaluation：`eval_results/offline_20260816T060613Z/summary.json`（n=110 × 5 systems）
- Demos：A/B/C/D PASS
- uvicorn smoke：health（CloudOps Harness v0.2.2）/ SSE / resume / traces PASS
- 真实 LLM eval：NOT COMPLETED（无 key；`scripts/run_real_eval.py` 就绪）
- 沙箱 recovery 样本：n=10，已如实报告

## 封版结论

**PROJECT FROZEN — READY FOR FINAL REVIEW / INTERVIEW PREPARATION**
