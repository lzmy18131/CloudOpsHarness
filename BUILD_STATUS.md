# BUILD_STATUS

> 持续更新。规则：每完成一个 Phase（代码 + 测试 + lint 全绿）才更新状态。
> 项目根目录：`D:\AegisOps`

| Phase | 内容 | Status | Implemented | Tests | Known Issues | Next Step |
|---|---|---|---|---|---|---|
| 0 | PDF 阅读 + 文档 | ✅ completed | `docs/PDF_TO_AIOPS_MAPPING.md`, `docs/IMPLEMENTATION_PLAN.md`, `docs/DECISIONS.md`, 本文档 | n/a | 无 | - |
| 1 | 项目初始化 | ✅ completed | pyproject / Settings / logging / FastAPI health / CI | 8 unit | 无 | - |
| 2 | MockOpsProvider + fixtures | ✅ completed | Protocol + models + MockOpsProvider + 5 类 fixtures + 故障注入 | 12 unit | 无 | - |
| 3 | MCP server | ✅ completed | FastMCP 15 工具 + AegisMcpServer + MCPToolAdapter | 6 unit | 无 | - |
| 4 | Single Agent | ✅ completed | ModelAdapter + OpenAI adapter + FakeLLM + AgentLoop + SingleAgent graph | 13 unit/integration | 无 | - |
| 5 | Main + SubAgents | ✅ completed | 4 个 YAML SubAgent + loader/validator/runner + 委派 graph | 12 unit/integration | 无 | - |
| 6 | Planning + Context | ✅ completed | 13 步 plan 状态机、evidence-only 主上下文、ContextCompressor、隔离测试 | 8 unit/integration | 无 | - |
| 7 | Memory + Skills | ✅ completed | PreferenceStore、8 个 SKILL.md、SkillRegistry、SkillInstaller 安全门 | 11 unit | 无 | - |
| 8 | Sandbox | ✅ completed | Protocol + Docker/Local backend + Proxy + Manager + Health + Breaker + 恢复/回退测试 | 12 unit/failure | Local 后端非强安全边界（文档已声明） | - |
| 9 | HITL + Resume | ✅ completed | missing_info/approval 双层 interrupt、Command(resume)、reject 分支、SQLite 跨重启测试 | 4 integration | 无 | - |
| 10 | SSE + Frontend | ✅ completed | SSE 双流（messages+custom）+ 静态 UI + history/traces API | 4 integration | 无 | - |
| 11 | Failure injection | ✅ completed | tool timeout / invalid result / MCP down / sandbox crash / Mongo fallback / restart resume | 7 failure | 无 | - |
| 12 | Evaluation harness | ✅ completed | 100 scenarios、5 systems、10+ metrics、McNemar、paired bootstrap、真实 artifact | 4 evaluation | FakeLLM 只度量 harness 正确性（文档诚实声明） | - |
| 13 | Docs | ✅ completed | README/ARCHITECTURE/EVALUATION/SECURITY/BUILD_REPORT/CHANGELOG | n/a | 无 | - |
| 14 | 最终验收 | ✅ completed | 101 tests 全绿；ruff 全绿；uvicorn 冒烟 + SSE/resume/history 实测；3 demos 通过 | 101 total | 无 | GitHub push |

## 最终状态
- 测试：`101 passed`
- Lint/Format：`ruff check src tests scripts` + `ruff format --check` 全绿
- 评估 artifact：`eval_results/offline_20260815T173021Z/summary.json`（n=100 × 5 systems，真实运行）
- Demo 报告：`data/demo_reports/demo{1,2,3}_*.md`
- 真实服务器冒烟：`/api/health` 200；SSE 事件链完整；resume 后 history 记录 interrupt/resume/final

## 环境
- Python: 3.11.15 (venv `D:\AegisOps\.venv`)
- 项目路径: `D:\AegisOps`
- 重要：本机全局 `PYTHONPATH` 指向 hermes 环境，所有 venv 命令必须 `env -u PYTHONPATH` 前缀。
