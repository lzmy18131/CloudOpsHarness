# BUILD_STATUS

> 持续更新。规则：每完成一个 Phase（代码 + 测试 + lint 全绿）才更新状态。
> 项目根目录：`D:\AegisOps`

## 专项整改（v0.2.0）完成状态

| Phase | 内容 | Status | Implemented | Tests | Known Issues | Next Step |
|---|---|---|---|---|---|---|
| 0 | 全仓审计 | ✅ completed | `docs/CODE_AUDIT.md`（60+ 项逐条 status/evidence/priority） | n/a | 无 | - |
| P0-1 | SSE 统一 envelope | ✅ completed | `event_type/run_id/thread_id/source/timestamp/sequence`；前端去重 | `test_events.py`, `test_api.py` | 无 | - |
| P0-2 | Context compression 接入 | ✅ completed | synthesize 前 `compress_main_context`；tokens before/after/ratio/preserved | `test_planning_context.py` | 无 | - |
| P0-3 | Planning/循环硬限制 | ✅ completed | skipped 状态；max_plan_steps；max_delegation_depth；LimitedModelAdapter | nodes/loop 测试 | 无 | - |
| P0-4 | dry-run + HITL + injection 测试 | ✅ completed | `dry_run_action` L0；审批 payload 带 dry_run；security tests | `test_security.py`, `test_tools.py` | 无 | - |
| P0-5 | Evidence/RCA 可追溯 | ✅ completed | EvidenceItem id/tool/ts/service/raw_ref；RCA supporting/contradicting；change-agent causal fields | `test_main_agent.py` | 无 | - |
| P0-6 | Dataset 110 + bucket 对比 + 新指标 | ✅ completed | easy/dependency_chain/ambiguous；17 项指标；bucket comparisons | `test_evaluation.py`, artifact | FakeLLM 只度量 harness | - |
| P0-7 | Breaker transitions + recovery latency | ✅ completed | transitions 记录；mean_recovery_latency_ms | `test_tools.py`, artifact | n=10 注入 | - |
| P1 | Trace/PII/skill-load/structured matrix/LLM timeout | ✅ completed | trace timeline、PII middleware、skills_loaded、校验矩阵、timeout retry | 对应 unit/failure tests | 无 | - |
| P1 | Demo D | ✅ completed | sandbox crash → recovery → HITL → SQLite restart → resume | `data/demo_reports/demo4_*.md` | 无 | - |
| P2 | Docs/README claim 映射 | ✅ completed | README Claim→Evidence 表；EVALUATION/ARCHITECTURE/SECURITY/BUILD_REPORT 更新 | n/a | 无 | GitHub push |

## 最终状态
- 测试：**117 passed**（unit 88 / integration 14 / failure 8 / security 3 / evaluation 4）
- Lint/Format：`ruff check src tests scripts` + `ruff format --check` ✅
- Evaluation artifact：`eval_results/offline_20260816T030945Z/summary.json`
  （n=110 × 5 systems，FakeLLM 离线，真实运行）
- Demo：A/B/C/D 全部通过（`data/demo_reports/`）
- 真实 LLM 评测：**NOT COMPLETED**（无 LLM_API_KEY；脚本 `scripts/run_real_eval.py` 就绪）
- 沙箱 recovery 注入样本：n=10/系统（非 30，已如实声明）

## 环境
- Python: 3.11.15 (venv `D:\AegisOps\.venv`)
- 项目路径: `D:\AegisOps`
- 重要：本机全局 `PYTHONPATH` 指向 hermes 环境，所有 venv 命令必须 `env -u PYTHONPATH` 前缀。
