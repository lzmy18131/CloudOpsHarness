# BUILD_STATUS

> 项目根目录：本地仓库（GitHub: lzmy18131/CloudOpsHarness）
> 版本：v0.2.1-final · commit：见 git log · tag：v0.2.1-resume

## v0.2.1 Release Blocker 修复状态

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

## 最终状态

- Tests：**collected 125 · passed 124 · failed 0 · skipped 1**（skipped = real-Docker smoke，本机 daemon 不可用）
- ruff check ✅ · ruff format --check ✅
- Evaluation：`eval_results/offline_20260816T045911Z/summary.json`（n=110 × 5 systems）
- Demos：A/B/C/D PASS
- uvicorn smoke：health（CloudOps Harness v0.2.1）/ SSE / resume / traces PASS
- 真实 LLM eval：NOT COMPLETED（无 key；脚本就绪）
- 沙箱 recovery 样本：n=10，已如实报告

## 封版结论

**PROJECT READY FOR FINAL REVIEW**
