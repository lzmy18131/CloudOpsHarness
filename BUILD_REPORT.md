# AegisOps Build Report（专项整改后）

- 项目根目录：`D:\AegisOps`
- 完成时间：2026-08-16（UTC）
- Python：3.11.15（venv `D:\AegisOps\.venv`）
- 依赖：见 `pyproject.toml`（全部 pin：langgraph 1.2.11 / fastapi 0.141.1 /
  pydantic 2.13.4 / fastmcp 3.4.7 / openai 2.54.0 …）
- 最终验证：**117 passed**（见下）；`ruff check src tests scripts` ✅；
  `ruff format --check src tests scripts` ✅

## 1. 整改变更（相对 v0.1.0）

### 删除的错误设计
- 无（核心架构未降级）；修正了早期“compression 只测不用”、事件无 envelope、
  评测无 bucket、recovery latency 被 PII 误伤等实现缺口。

### 核心架构变化 / 新增
- **SSE 统一 envelope**：每个事件 `event_type/type/run_id/thread_id/source/
  timestamp/sequence`；前端按 sequence 去重。
- **Context compression 真正接入**：synthesize 前执行 `compress_main_context`，
  保护 system/evidence/tail，记录 tokens before/after/ratio；`mean_main_context_tokens` 进入评测。
- **Planning 硬限制**：`max_plan_steps`（超出标记 skipped → partial report）、
  `max_delegation_depth` 守卫；`model_call_limit` 用 `LimitedModelAdapter` 硬停。
- **Dry run**：新增 L0 工具 `dry_run_action`（planned change/before/expected/
  rollback/risk），审批请求携带 `dry_run`。
- **Evidence 可追溯**：`EvidenceItem.id/tool/timestamp/service/raw_ref`；
  RCA 带 `supporting/contradicting_evidence`；change agent 输出
  `temporal_correlation/correlation/causal_confidence`。
- **Circuit breaker transitions** 持久记录。
- **Verification**：`resolved` 标志 + before/after state。
- **PII redaction**：工具结果进任何 Agent 上下文前脱敏 email/phone/api-key。
- **Trace timeline**：tool_start(risk)/tool_end、agent_start/end、hitl_decision、
  action_executed、verification、incident_report。
- **Dataset 110 条**：新增 easy / dependency_chain / ambiguous bucket。
- **评测指标**：新增 unsafe_execution_count、hitl_recall/precision、
  recovery latency、remediation verification/resolution、resume success、
  main-context tokens、unnecessary tool rate、delegation accuracy、bucket comparisons。
- **Demo D**：sandbox crash → 自动恢复 → HITL → SQLite 重启 → resume。

## 2. 测试

| 类别 | 数量 | 关键用例 |
|---|---|---|
| unit | 88 | config/schemas/risk/tools/memory/skills/loader/sandbox/breaker/events/PII/structured-output 矩阵 |
| integration | 14 | Main→SubAgent、MCP、HITL、checkpoint、SSE envelope、resume 不重跑、sandbox tools |
| failure | 8 | tool timeout、invalid result、MCP down、Mongo fallback、LLM timeout retry、sandbox crash recovery |
| security | 3 | prompt injection、risk-policy bypass、user memory isolation |
| evaluation | 4 | dataset 110 不变量、metrics/stats、4-scenario harness 集成 |
| **total** | **117 passed** | `pytest -q` |

## 3. Evaluation（真实运行）

- Artifact：`eval_results/offline_20260816T030945Z/summary.json`
- 配置：FakeLLM（deterministic），n=110 × 5 systems，本地 Windows 开发机。
- 真实 LLM：**未运行**（无 key）。`scripts/run_real_eval.py` 就绪，结果单独目录。

关键结果（详见 `EVALUATION.md`）：

| | Single | Multi | Multi no-iso | Harness | Harness no-rec |
|---|---|---|---|---|---|
| Unsafe (dangerous) | 1.000 | 1.000 | 1.000 | **0.000** | 0.000 |
| Unsafe executions | 10 | 10 | 10 | **0** | 0 |
| HITL recall | 0.000 | 0.000 | 0.000 | **1.000** | 1.000 |
| Recovery success | 0.000 | 1.000 | 1.000 | **1.000** | 0.000 |
| Mean recovery latency ms | - | 159.3 | 173.4 | 159.5 | - |
| Resume success | 0.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| Mean main-context tokens | n/a | 1324.9 | 1368.8 | 1324.9 | 1324.9 |
| Mean token cost | 4799.2 | 39171.5 | 39221.7 | 39172.8 | 39170.4 |
| Mean latency ms | 56.8 | 121.3 | 124.9 | 123.7 | 109.2 |

配对结论：
- Unsafe：Single/Harness、Multi/Harness McNemar p=0.002。
- Recovery：Harness vs no-recovery p=0.002。
- Isolation：main context +43.94 token（95% CI [+43.06,+44.84]）。
- Single vs Harness token −34373.6（CI [−34681.4,−34075.1]）。
- Bucket：simple/multi_source/multi_hop/complex/failure_injection 见 artifact。

## 4. Demo 验证

- Demo A（bad deployment approve）：✅ `rollback_release` → verify → report
- Demo B（DB pool）：✅ sandbox 证据 → `apply_config_change`
- Demo C（reject）：✅ Actions Taken=None + Rejected Actions + 安全替代
- Demo D（sandbox crash/resume）：✅ 恢复 → HITL → SQLite 重启 → resume → done
- 真实 uvicorn 冒烟：health/static/SSE/resume/history/traces 实测通过（API 集成测试覆盖）

## 5. Known Limitations / Remaining Issues

1. FakeLLM 评测只证明 harness correctness；真实 LLM 结果 NOT COMPLETED（无 key）。
2. Sandbox recovery 注入样本 n=10/系统，不是 30；文档如实写。
3. LocalSandboxBackend 非内核级隔离；不可信输入必须 Docker backend。
4. MCP 默认 in-process transport；stdio 部署见 `python -m aegisops.mcp.server`。
5. SQLite/file 存储单机设计；Mongo 为可选 extras。
6. mypy 未纳入 CI（ruff + pytest 已覆盖 lint/行为；类型注解齐全但 strict mypy 未调通）。
7. UI 是演示级，不做多连接历史回放。

## 6. Reproduce

```bash
cd D:\AegisOps
.venv\Scripts\python -m pip install -e ".[dev]"
.venv\Scripts\python -m pytest -q
.venv\Scripts\python -m ruff check src tests scripts
.venv\Scripts\python scripts\run_eval.py --limit 20
.venv\Scripts\python -m uvicorn aegisops.api.app:create_app --factory --port 8090
```
