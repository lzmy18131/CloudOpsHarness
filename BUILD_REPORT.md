# AegisOps Build Report

- 项目根目录：`D:\AegisOps`
- 构建完成时间：2026-08-15（UTC）
- 最终验证：`101 passed` · `ruff check src tests scripts` ✅ · `ruff format --check` ✅
- 真实评估 artifact：`eval_results/offline_20260815T173021Z/summary.json`

## 1. Phase 完成情况

| Phase | 内容 | 状态 |
|---|---|---|
| 0 | PDF 阅读 + 机制映射文档 | ✅ |
| 1 | 项目初始化（pyproject/Settings/logging/health/CI） | ✅ |
| 2 | MockOpsProvider + fixtures | ✅ |
| 3 | FastMCP server + MCPToolAdapter | ✅ |
| 4 | Single Agent（ModelAdapter + FakeLLM + graph） | ✅ |
| 5 | Main + 4 SubAgents（YAML 声明式） | ✅ |
| 6 | Planning + Context Isolation + Compression | ✅ |
| 7 | Memory + Skills（渐进披露 + 安全安装器） | ✅ |
| 8 | Sandbox（Docker/Local/Proxy/Manager/Health/Breaker） | ✅ |
| 9 | HITL + Checkpoint + Resume（含跨重启测试） | ✅ |
| 10 | SSE + 静态前端 + History/Traces API | ✅ |
| 11 | Failure injection（tool timeout/MCP down/sandbox crash/Mongo fallback） | ✅ |
| 12 | Evaluation harness（100 场景、5 systems、McNemar/bootstrap） | ✅ |
| 13 | README/ARCHITECTURE/EVALUATION/SECURITY/BUILD_REPORT/CHANGELOG | ✅ |
| 14 | 最终验收（全量测试、真实服务器 SSE 冒烟、3 个 demo） | ✅ |

## 2. 测试

- 总计：**101 passed**（`pytest -q`）
- 分类：unit 74 · integration 17 · failure 7 · evaluation 4（含 1 个 4-scenario harness 集成）
- CI：`.github/workflows/ci.yml` 运行 `ruff check src tests scripts` + `ruff format --check` + `pytest -q`，不依赖 LLM key 与外部服务。

## 3. Evaluation（真实运行，未伪造）

100 个 scenario × 5 systems，全部 per-scenario 明细在 artifact 中。

| 指标 | Single | Multi | Multi no-iso | Harness | Harness no-rec |
|---|---|---|---|---|---|
| Root Cause Accuracy | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| Task Completion | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| Unsafe Action（危险场景） | 1.000 | 1.000 | 1.000 | **0.000** | 0.000 |
| HITL Compliance | 0.000 | 0.000 | 0.000 | **1.000** | 1.000 |
| Recovery Success | 0.000 | 1.000 | 1.000 | **1.000** | 0.000 |
| Mean Token Cost | 4975.6 | 38032.6 | 38082.6 | 38043.0 | 38041.4 |
| Mean Latency (ms) | 69.4 | 130.8 | 134.4 | 131.9 | 113.6 |

- Unsafe：Single/Harness 与 Multi/Harness 的 McNemar p=0.002。
- Recovery：Harness vs Harness-no-recovery p=0.002。
- Token：Single−Harness diff −33067（95% CI [−33316, −32818]）。
- Isolation：no-isolation−isolation diff −49.97 token（95% CI [−54.1, −45.7]）。
- 结论：离线 FakeLLM 度量 harness 护栏与成本，不宣称“Multi-Agent 更聪明”。

## 4. Demo 验证

- `python -m aegisops.demo --demo 1`：HITL approve → `rollback_release` → verify → report ✅
- `python -m aegisops.demo --demo 2`：DB pool evidence → `apply_config_change` → report ✅
- `python -m aegisops.demo --demo 3`：reject `rollback_release`，Actions Taken=None，输出安全替代 ✅
- 真实 uvicorn 冒烟：`/api/health` 200，`/` 与 `/static/app.js` 200，SSE 流包含
  token/plan/agent/tool/interrupt，resume 后 history 记录 interrupt+resume+done ✅

## 5. Known Issues / Limitations

1. `LocalSandboxBackend` 是开发兜底，不是内核级安全边界；不可信输入必须 `AEGIS_SANDBOX_BACKEND=docker`。
2. FakeLLM 离线评测度量 harness 正确性；真实模型质量需要 `scripts/run_real_eval.py`。
3. 本机 Docker Desktop 凭据助手异常时，auto 模式已自动回退 Local（有测试覆盖）；Docker 后端本身需正常 Docker daemon。
4. `MCPToolAdapter` 默认 in-process；跨进程用 `python -m aegisops.mcp.server`（stdio）。
5. SQLite/file 存储为单机设计；水平扩展切 MongoDB（extras + compose）。

## 6. Reproduce

```bash
cd D:\AegisOps
.venv\Scripts\python -m pip install -e ".[dev]"
.venv\Scripts\python -m pytest -q
.venv\Scripts\python -m ruff check src tests scripts
.venv\Scripts\python -m ruff format --check src tests scripts
.venv\Scripts\python scripts\run_eval.py --limit 20     # offline eval
.venv\Scripts\python -m uvicorn aegisops.api.app:create_app --factory --port 8090
```
