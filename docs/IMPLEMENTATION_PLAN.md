# AegisOps Implementation Plan

执行顺序严格按依赖方向推进；每阶段完成标准 = **代码 + 测试 + lint 全绿 + BUILD_STATUS 更新**。不允许测试失败进入下一阶段。

## Phase 0 — 阅读 PDF，建立映射 ✅ 进行中
- 交付：`docs/PDF_TO_AIOPS_MAPPING.md`、本文档、`docs/DECISIONS.md`、`BUILD_STATUS.md`。

## Phase 1 — 项目初始化
- `pyproject.toml`（固定版本依赖）、`.env.example`、`.gitignore`
- `Settings`（pydantic-settings）+ 结构化 logging
- FastAPI app + `GET /api/health`
- `tests/unit/test_config.py`、`tests/unit/test_health.py`
- GitHub Actions CI（ruff + pytest，无真实 LLM key）

## Phase 2 — MockOpsProvider + Fixtures
- `OpsProvider` Protocol（read + write action 接口）
- `ServiceCatalog`、`Topology`、`DeploymentHistory`、`ConfigHistory`、`HistoricalIncidents`、`LogCorpus` fixtures
- `MockOpsProvider`：确定性 telemetry 生成 + anomaly 注入 + action 模拟 + 故障注入开关
- 测试：catalog/topology/deployments/config-diff/incident-history/health 查询正确；action 幂等。

## Phase 3 — Python MCP Server
- `mcp/server.py`（FastMCP）：`query_metrics / query_logs / get_service_health / get_service_topology / get_recent_deployments / get_config_diff / get_incident_history / get_current_release / verify_service_health`（L0）
- `mcp/client.py`：in-process adapter + stdio transport
- 测试：tools 列表、调用 read-only 工具、MCP 不可用降级。

## Phase 4 — Single Agent
- `ModelAdapter` protocol + `OpenAICompatibleAdapter` + `FakeLLM`
- `ToolRegistry` + Risk Policy（L0–L3）+ 通用 `ToolNode`（错误转 ToolMessage，不崩图）
- Single-Agent graph：User → Agent loop → Tools → Answer
- 测试：FakeLLM 端到端；真实 adapter 构造与 tool JSON schema 单测（不联网）。

## Phase 5 — Main + SubAgents
- `agents/subagents/configs/*.yaml`（observability/log_analysis/change_analysis/remediation）
- `load_subagent_configs / resolve_subagent_tools / validate_subagent_config`
- Main（Incident Commander）按 plan 顺序委派；每个 SubAgent 独立上下文/工具白名单，返回 Pydantic `SubAgentReport`
- 测试：委派链、YAML 校验、SubAgent 隔离、工具白名单越权被拒。

## Phase 6 — Planning + Context Isolation + Compression
- `PlanStep` 状态机；planner 生成 13 步故障排查链并写入 state
- 主 Agent 上下文只含证据摘要（测试注入大量 raw logs，断言主 LLM 调用不含 raw 内容）
- `ContextCompressor`：阈值触发摘要/offload，保留 decisions/evidence/plan/hypotheses

## Phase 7 — Memory + Skills
- `PreferenceStore`（JSON 默认，user 作用域）；MemoryUpdateMiddleware
- `SkillRegistry`（frontmatter 渐进披露）、8 个 AIOps skills
- `SkillInstaller` 安全校验（allowlist/type/size/static inspection/sandbox test/approval）
- SkillsSync + UserSkillsRestore middleware

## Phase 8 — Sandbox
- `SandboxBackend` Protocol；`DockerSandboxBackend`（安全参数：`--network none --cap-drop ALL --read-only --tmpfs /tmp --user nobody`）+ `LocalSandboxBackend`
- `SandboxManager`（prewarm/claim/cache/reconnect/rebuild/destroy，user 隔离）+ `SandboxBackendProxy`（热替换）
- `SandboxHealthMiddleware` + `SandboxCircuitBreaker`
- 测试：正常执行、健康恢复、backend 替换后引用不变、用户 A/B 隔离。

## Phase 9 — HITL + Checkpoint + Resume
- MissingInfoGuard：`interrupt({type: missing_info})`；`POST /api/chat/{thread_id}/resume` 携带 supplement
- ActionApprovalNode：L2/L3 → `interrupt({type: approval, action_requests})`；approve/reject 分支
- LangGraph `AsyncSqliteSaver` checkpoint；`Command(resume=...)`
- 测试：中断不重跑、approve 执行、reject 给替代方案、跨 saver 实例恢复。

## Phase 10 — SSE + Frontend
- `POST /api/chat/stream`：`token / plan / agent_start / agent_end / tool_start / tool_args / tool_result / tool_end / interrupt / error / done`，带 `source`
- messages 流 token；custom 流结构化事件；interrupt 用 state 字段兜底检测
- `static/index.html + app.js`：chat、todo、agent/tool 活动、interrupt banner、history、报告渲染
- 测试：SSE 事件序列、token 顺序、interrupt 一致性。

## Phase 11 — Failure Injection
- tool timeout / sandbox crash / invalid tool result / malformed structured output / MCP unavailable / storage unavailable / resume after restart
- retry + fallback + circuit breaker + graceful degradation
- 测试全部有对应 failure test。

## Phase 12 — Evaluation Harness
- 60+ scenario dataset（模板生成 + JSON export，覆盖 7 类难度）
- Runners：SingleAgent / MultiAgent / Harness（ablation 开关）
- 指标：RCA Accuracy / Task Completion / Tool Selection / Evidence Completeness / Unsafe Action Rate / HITL Compliance / Recovery Success / Mean Tool Calls / Mean LLM Calls / Token Cost / Latency
- 统计：McNemar（binary 配对）+ paired bootstrap 95% CI（连续）
- 运行真实 artifact，禁止伪造；提供 `scripts/run_eval.py`（FakeLLM 确定性验证）与 `scripts/run_real_eval.py`（真实 LLM，需 key）。

## Phase 13 — Docs + README
- README（11 节，真实结论）、ARCHITECTURE、EVALUATION、SECURITY、BUILD_REPORT、CHANGELOG

## Phase 14 — 最终验收
- 全量 pytest + ruff 通过；FastAPI 启动、SSE、demo 脚本可跑；BUILD_STATUS 更新为完成。
