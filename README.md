# CloudOps Harness

**一句话定位**：CloudOps Harness 是一个基于 Harness Engineering 的企业级 AIOps Multi-Agent 智能故障响应平台——多个专业 Agent 在一个安全、可恢复、可审计的 LangGraph Runtime 中完成故障诊断、根因分析、修复建议、高风险操作审批、执行与事后报告。

**CloudOps Harness — Harness-Engineered Multi-Agent Platform for AIOps Incident Response.**

## 1. Why

传统 Agent 处理长周期 IT 故障排查任务时会遇到五类工程问题：

| 问题 | CloudOps Harness 的 Harness 机制 |
|---|---|
| Context explosion（原始日志/指标淹没主 Agent） | SubAgent 独立上下文，主 Agent 只收 Pydantic 结构化证据摘要 |
| Tool misuse（模型绕过限制执行生产变更） | Risk Policy L0–L3 + ToolRegistry 边界强制 + 双层 HITL interrupt |
| State loss（HTTP 断开后从头再来） | LangGraph checkpoint（SQLite，默认）+ `Command(resume)`，支持进程重启后恢复 |
| Unsafe operation（无审批重启/回滚） | `interrupt({type:"approval", action_requests})`，reject 后记录并给安全替代方案 |
| Failure recovery（沙箱/工具挂了无限重试） | Sandbox health → manager rebuild → proxy 热替换 + Circuit Breaker（CLOSED/OPEN/HALF_OPEN） |

## 2. Architecture

```
FastAPI :8090
  ├─ POST /api/chat/stream   SSE(token/plan/agent_*/tool_*/interrupt/done)
  ├─ POST /api/chat/{id}/resume   Command(resume={supplement|decisions})
  ├─ GET/DELETE /api/history · GET /api/traces · GET /api/threads/{id}/state
  │
  ├─ MiddlewareStack (11, 可插拔/可关闭/有日志)
  ├─ LangGraph graph: prepare → planner(13-step todo) → 4 SubAgents
  │      → synthesize(RCA) → executor(HITL) → pause(interrupt) → verify → report
  ├─ ModelAdapter: OpenAI-compatible (DeepSeek/OpenAI/Qwen) 或 FakeLLM (offline)
  ├─ ToolRegistry → MCPToolAdapter → FastMCP → MockOpsProvider
  ├─ Sandbox: Health → Manager → Proxy(热替换) → Docker/Local Backend
  └─ Memory(用户偏好) · Skills(渐进披露) · SQLite checkpoint · JSONL traces
```

详见 [`ARCHITECTURE.md`](ARCHITECTURE.md)。所有机制在 [`docs/PDF_TO_AIOPS_MAPPING.md`](docs/PDF_TO_AIOPS_MAPPING.md) 中与原始 PDF 逐条对应。

## 3. End-to-End Demo

无需任何 API Key（默认 FakeLLM 离线确定性驱动）：

```bash
git clone https://github.com/lzmy18131/CloudOpsHarness.git && cd CloudOpsHarness
python -m venv .venv
# Windows: .venv\Scripts\activate   /  Linux: source .venv/bin/activate
pip install -e ".[dev]"

# Demo 1: bad deployment → HITL approve → rollback → verify → report
python -m cloudops_harness.demo --demo 1
# Demo 2: DB pool exhaustion → sandbox analysis → remediation
python -m cloudops_harness.demo --demo 2
# Demo 3: dangerous action REJECTED → safe alternative，不执行生产变更
python -m cloudops_harness.demo --demo 3
# Demo 4: sandbox crash → automatic recovery → HITL → SQLite 重启 → resume
python -m cloudops_harness.demo --demo 4

# Web UI + SSE
uvicorn cloudops_harness.api.app:create_app --factory --port 8090
# 打开 http://127.0.0.1:8090
```

## 4. Harness Design

- **Planning**：`PlanStep(pending/in_progress/completed/failed/skipped)` 持久化在 graph state，SSE `plan` 事件实时推送。
- **SubAgent 声明式**：`src/cloudops_harness/agents/subagents/configs/*.yaml`。新增 Agent = 新增一个 YAML；`load_subagent_configs / resolve_subagent_tools / validate_subagent_config`。
- **Context Engineering 四层**：Input（policy+偏好+skills frontmatter）→ Isolation（transcript 永不进主上下文）→ Compression（阈值 offload+摘要）→ Long-term Memory（用户偏好；CMDB 事实一律走工具）。
- **Memory vs Database facts**：`PreferenceStore` 只存偏好；owner/version/dependency/restart policy 从 Service Catalog 工具查询。
- **Skills**：启动只注入 name/description/metadata，需要时 `load_body()`；动态安装经 URL allowlist → 类型/大小限制 → 静态检查 → 沙箱测试 → 审批。
- **Failure recovery**：tool timeout / sandbox crash / MCP down / malformed JSON / Mongo down 均有测试；resume after restart 有 SQLite checkpoint 测试。

## 5. Multi-Agent

| Agent | 职责 | 工具 | 输出 |
|---|---|---|---|
| Incident Commander (main) | triage/plan/dispatch/RCA/HITL/report | 证据摘要 + 执行器 | `IncidentReport` |
| Observability | metrics/health/latency/saturation/anomaly window | query_metrics, health, topology… | 结构化 `SubAgentReport` |
| Log Analysis | 日志聚类/traceback/超时/相关性（沙箱 grep/python） | query_logs, health, sandbox_* | 结构化 `SubAgentReport` |
| Change Analysis | deployment/config diff/时间与因果相关性 | releases, diff, history | 结构化 `SubAgentReport` |
| Remediation | 修复规划/风险分级/runbook/替代方案（**不执行写操作**） | verify, health, catalog… | `ProposedAction[]` |

## 6. Sandbox

`SandboxBackend` Protocol 下实现：
- `DockerSandboxBackend`：`--network none --cap-drop ALL --no-new-privileges --read-only --tmpfs /tmp:rw,noexec,nosuid,size=64m --tmpfs /workspace:rw,nosuid,nodev,size=256m --memory 256m --cpus 0.5 --pids-limit 64`，提供**项目级执行隔离边界**（不是 hardened microVM sandbox）。
- `LocalSandboxBackend`：无 Docker 开发机兜底（**不是强隔离边界**，文档已明确）。

故障恢复路径：execute 失败 → circuit breaker 记录 → `manager.rebuild()` → `proxy.replace_backend()` → 重试成功。`tests/failure/test_sandbox_recovery.py` 自动化验证。

## 7. HITL

- 缺失信息：`interrupt({type:"missing_info"})` → resume `{supplement}`。
- 危险操作：`interrupt({type:"approval", action_requests})` → resume `{decisions:[{type:"approve"|"reject"}]}`。
- Reject 不终止：记录 `rejected_actions` → 输出安全替代方案 → 继续 verify + report。
- Checkpoint 在 interrupt 前落盘；`POST /api/chat/{thread_id}/resume` 从原状态继续，不重跑。

## 8. Evaluation

### Real LLM Evaluation

**Status: limited paired validation completed (stop-loss closure)**

- Model: **DeepSeek-V4-Flash** (`deepseek-v4-flash`)
- Provider: DeepSeek OpenAI-compatible API
- Environment: **Real LLM + simulated operations environment (MockOpsProvider)**
- Paired real runs: **5 dev incidents × 2 systems × 1 repetition = 10 real runs**
- Artifact: `eval_results/real_smoke_deepseek_v4_flash_final/`

This is a **portfolio-scale limited paired validation**, not an academic or
production benchmark. A planned 20-scenario Formal Harness run was started but
stopped under the project stop-loss policy before producing a complete paired
artifact; only the completed paired smoke subset is used for Single-vs-Harness
claims. A separate `Single-Agent` formal-20 exploratory artifact exists
(`eval_results/real_deepseek_v4_flash_portfolio_formal_single/`), but it is not
paired and is not used in the headline comparison.

| Metric | Single Agent | Full Harness | Delta |
| --- | ---: | ---: | ---: |
| Task Success | 0.000 | 0.200 | +0.200 |
| RCA Accuracy | 0.000 | 0.000 | 0.000 |
| Service Localization | 1.000 | 1.000 | 0.000 |
| Evidence Grounding Precision | 0.429 | 0.033 | −0.395 |
| Unsupported Claim Rate | 0.571 | 0.967 | +0.395 |
| Tool F1 | 0.623 | 0.547 | −0.076 |
| HITL Recall | 0.000 | 0.000 | 0.000 |
| Unapproved Unsafe Execution | 0.000 | 0.000 | 0.000 |
| Recovery Success | 0.000 | 1.000 | +1.000 |
| Mean Total Tokens | 162,068 | 199,208 | +37,140 |
| Mean Model Calls | 9.2 | 32.2 | +23.0 |
| P95 Latency (ms) | 63,906 | 303,391 | +239,485 |

Numbers above are read from the real artifact. Harness costs substantially more
tokens, model calls and latency; on this small sample it improved recovery
success but did not improve RCA or evidence grounding.

```bash
# Requires LLM_API_KEY / LLM_BASE_URL / LLM_MODEL in .env
python scripts/run_real_eval.py --split portfolio_smoke_5 --repeat 1 --systems single-agent,harness --temperature 0
```

### Deterministic Workflow Validation

`FakeLLM` is a deterministic test driver used for CI and architecture regression.
**It is NOT used to claim model intelligence.**

| Check | Status |
|---|---|
| Policy boundary (dangerous tools cannot bypass HITL) | PASS |
| HITL flow (approve / reject / action_id binding) | PASS |
| Rejected action never executes + continuation | PASS |
| Checkpoint / resume | PASS |
| Sandbox recovery | PASS |
| Structured-output handling | PASS |
| Leakage audit (no evaluator ground truth in prompts/tools) | PASS |

Results artifact: `validation_results/deterministic_v2/` (n=110 × systems,
FakeLLM/CI-only). Historical FakeLLM artifacts remain in `eval_results/` for audit.

Methodology and honest limitations: [`EVALUATION.md`](EVALUATION.md).


## 9. Claim → Evidence 映射

每个核心 claim 都可被面试官沿着代码/测试/artifact 验证：

| Claim | Code | Test / Artifact |
|---|---|---|
| Main 不读 raw logs/metrics | `assemble_main_messages()` 不读取 `transcripts` | `tests/unit/test_planning_context.py`, `tests/integration/test_main_agent.py` |
| Context Compression 真的运行 | `compress_main_context()` 在 synthesize 调用 | `test_compress_main_context_preserves_evidence_and_reduces_tokens` + `context_stats` |
| 危险工具无法绕过 HITL | `ToolRegistry.call(approved=...)` 抛 `ToolApprovalRequiredError` | `test_tools.py`, `tests/security/test_security.py` |
| Prompt injection 不改 policy | log 注入文本只能留在 transcript | `tests/security/test_security.py` |
| HITL interrupt + resume 不重跑 | `pause` 唯一 interrupt + SQLite checkpoint | `test_main_agent.py`, `test_checkpoint_resume.py`（含 tool call 计数断言） |
| 进程重启后 resume | `AsyncSqliteSaver` | `test_checkpoint_resume.py` |
| Sandbox crash 自动恢复 | `manager.rebuild()` + `proxy.replace_backend()` | `tests/failure/test_sandbox_recovery.py` |
| 用户隔离（sandbox/memory/history） | 每 user 独立 workspace/文件；user_id/thread_id 中央校验 | `test_sandbox.py`, `test_security.py`, `test_storage.py` |
| Circuit breaker 状态机 + transition 记录 | `CircuitBreaker.transitions` | `test_tools.py::test_circuit_breaker_records_transitions` |
| 无限循环防护 | `LimitedModelAdapter` / tool limit / max_plan_steps / delegation depth | 代码 `llm/base.py`, `nodes.py`；行为由 limit 测试覆盖 |
| SSE 统一 envelope | `agents/events.py` | `tests/unit/test_events.py`, `test_api.py` |
| 结构化输出校验矩阵 | `generate_structured` retry/repair/fallback | `tests/unit/test_llm.py`（missing/wrong/truncated/extra/invalid confidence） |
| Memory 与 CMDB 分离 | `PreferenceStore` 只存偏好；catalog 走工具 | `test_skills_memory.py` |
| Skills 渐进披露 + 加载记录 | frontmatter-only 注入 + `skills_loaded` 统计 | `test_skills_memory.py`, runner 日志 |
| Dynamic skill 安全门 | `SkillInstaller` | `test_skills_memory.py`（7 项安全测试） |
| Dry run before HITL | `dry_run_action` L0 + `ActionRequest.dry_run` | `test_tools.py`, executor 代码 |
| Remediation 后 verify + resolved | `build_verify_node` before/after + resolved | `test_main_agent.py`（最终状态） |
| Evaluation 数字可复算 | raw per-run 明细 + manifest | `validation_results/deterministic_*/runs.jsonl` |

## 10. Quick Start

```bash
# 依赖（固定版本）
pip install -e ".[dev]"
# 测试（无需 API key）
pytest -q
ruff check src tests scripts
# 服务
cp .env.example .env        # 可选：填入 LLM_API_KEY 使用真实模型
uvicorn cloudops_harness.api.app:create_app --factory --port 8090
# 可选 MongoDB（默认 file/SQLite 零依赖）
docker compose up -d mongo   # 然后 CLOUDOPS_STORAGE_BACKEND=mongo
```

## 11. Limitations

- **User isolation is logical isolation between supplied user IDs, not a production authentication/authorization boundary.** API 在提供 user_id 时执行 thread ownership 校验；但 Demo Identity 不能替代登录系统。
- DockerSandboxBackend provides project-level execution isolation (read-only root, restricted writable workspace, resource controls). It is not a hardened multi-tenant microVM sandbox.
- LocalSandboxBackend 仅用于开发演示；生产/不可信输入必须 `CLOUDOPS_SANDBOX_BACKEND=docker`。
- FakeLLM 评测度量的是 **harness 正确性**，不是语言模型能力；真实 LLM 结果用 `scripts/run_real_eval.py` 单独生成，当前为 limited paired validation（stop-loss closure），不是完整 formal paired benchmark。
- 即使接入真实 LLM，当前内部 benchmark 仍运行在 **MockOpsProvider 模拟运维环境** 上，应描述为 `Real LLM, simulated operations environment`，不得声称 production incident benchmark。
- 离线 FakeLLM 确定性验证的有效信息集中在 **unsafe/HITL 合规、恢复能力、resume、tool boundary 与 workflow correctness**；它不能证明任何模型智能。见 EVALUATION.md 的诚实说明。
- MCP 默认 in-process transport；跨进程 stdio：`python -m cloudops_harness.mcp.server`。
- 无向量数据库 / GraphRAG（刻意不做，聚焦 Harness）。
