# PDF → AegisOps Mapping（Harness 机制继承与重映射）

> 来源文档：《基于 Harness Engineering 架构的企业实战项目》（PDF，35 页，约 5.7MB）。
> 本文档回答一个问题：原项目的哪些 **Harness 机制** 值得继承，它们被如何重新实现为 AIOps 场景，以及落在本仓库的哪个模块。
>
> 原则：**继承工程机制，不继承采购业务**。原项目中的 supplier / part / purchase order / 报价 / 图表商城等业务一律不出现。

## 0. 原文核心结论（我们继承的思想）

- Harness Engineering 定义：Agent = Model + Harness。Harness 是模型之外的一切——规划、工具、记忆、沙箱、状态管理、恢复、护栏。
- 传统 Agent 长周期任务的六大问题：上下文窗口爆炸、状态丢失、工具调用混乱、缺乏规划、无法从失败中恢复、危险操作无护栏。
- 原项目把 Harness 落为可点名的组件：TodoList / SubAgent / Context Management（Input + Compression + Isolation + Long-term Memory）/ Skills / Sandbox（五组件 + 热替换）/ Middleware（9 件套）/ HITL（双层 interrupt）/ SSE 双流 / MongoDBSaver checkpoint / Memory（用户偏好）。

## 1. 机制继承映射总表

| # | PDF 原机制 | 是否保留 | AegisOps（AIOps）版本实现 | 对应代码模块 |
|---|---|---|---|---|
| 1 | 任务 Planning / write_todos | ✅ 保留并强化 | `PlanStep` 状态机（pending/in_progress/completed/failed），planner node 生成 13 步标准故障排查链，保存于 graph state，SSE `plan` 事件推送 | `agents/planner.py`, `agents/state.py` |
| 2 | Main Agent + SubAgent 委派 | ✅ 保留 | Incident Commander（主）+ Observability / LogAnalysis / ChangeAnalysis / Remediation 四个专业 SubAgent。主 Agent 只收结构化摘要 | `agents/graph.py`, `agents/main_agent.py`, `agents/subagents/` |
| 3 | SubAgent YAML 声明式配置 + 弹性加载 | ✅ 保留 | `src/aegisops/agents/subagents/configs/*.yaml`，`load_subagent_configs()` / `resolve_subagent_tools()` / `validate_subagent_config()`；新增 SubAgent = 新增 YAML | `agents/subagents/loader.py` + `configs/` |
| 4 | Context Input（启动加载） | ✅ 保留 | 每轮运行注入：runtime policy、用户偏好、服务上下文、可用 Skills frontmatter、调用预算 | `middleware/context_injection.py`, `middleware/base.py` |
| 5 | Context Isolation（SubAgent 隔离） | ✅ 保留 | SubAgent 独立消息窗口与工具白名单；raw logs/metrics 留在 SubAgent context，主 Agent 只接收 `SubAgentReport`（Pydantic 结构化摘要） | `agents/subagents/runner.py`, `agents/state.py` |
| 6 | Context Compression（阈值自动摘要/offload） | ✅ 保留 | `ContextCompressor`：主上下文超过 token 阈值后对旧轮次摘要，保留 decisions/evidence/plan/unresolved_hypotheses；工具结果超长自动截断并 offload | `agents/context.py` |
| 7 | Long-term Memory（跨线程用户偏好） | ✅ 保留并修正边界 | 只记忆用户偏好（语言、报告风格、时区、云、approval policy、owned services），**CMDB 服务事实一律走 Service Catalog 工具**，不让 LLM 背数据库事实 | `memory/preferences.py`, `middleware/memory_update.py`, `providers/catalog.py` |
| 8 | Skills 渐进式披露 | ✅ 保留 | `skills/*/SKILL.md` YAML frontmatter；启动只注入 name/description/metadata，需要时 `SkillRegistry.load_body()` | `skills/registry.py` |
| 9 | Skills 四阶段进化（同步→发现→创建/下载→分配持久化） | ✅ 保留并收紧安全 | `SkillsSyncMiddleware` 同步到沙箱；`SkillInstaller` 支持 URL allowlist / 文件类型限制 / 大小限制 / 静态检查 / 沙箱内测试 / approval policy | `skills/installer.py`, `middleware/skills_sync.py`, `middleware/user_skills_restore.py` |
| 10 | Sandbox 五组件（HealthMiddleware → Manager → Proxy → Backend Protocol → Docker） | ✅ 保留 | `SandboxBackend` Protocol；`DockerSandboxBackend`（`--network none --cap-drop ALL --read-only`）；`LocalSandboxBackend`（无 Docker 的开发机 fallback，文档明示弱隔离）；Proxy 热替换 `replace_backend()` | `sandbox/` 全目录 |
| 11 | Sandbox 生命周期（prewarm/claim/cache/reconnect/rebuild/destroy） | ✅ 保留 | `SandboxManager` 五态管理 + 预热池（可配置关闭，本地后端默认关闭预热） | `sandbox/manager.py` |
| 12 | 沙箱故障 → 热替换恢复 | ✅ 保留，有自动化测试 | health check 失败 → manager 重建 → `proxy.replace_backend()` → Agent 继续；测试注入 `FailingBackend` 验证链路 | `sandbox/health.py`, `tests/failure/test_sandbox_recovery.py` |
| 13 | HITL 第 1 层：数据补充 interrupt | ✅ 保留 | `MissingInfoGuard`：service/environment/time range 缺失 → `interrupt({type: missing_info})` → resume 携带 `{supplement}` | `agents/hitl.py`, `agents/graph.py` |
| 14 | HITL 第 2 层：危险操作审批 interrupt | ✅ 保留 | Risk Policy L0–L3；L2+ 必审，L3 额外要求 reason/target/before-state/expected-impact；approve → 执行；reject → 记录、给安全替代方案、继续出报告（不提前结束） | `tools/risk.py`, `agents/hitl.py`, `agents/executor.py` |
| 15 | Checkpointer / Resume | ✅ 保留 | LangGraph `AsyncSqliteSaver`（默认，跨进程重启可恢复）+ `Command(resume=...)` | `agents/graph.py`, `api/routes_chat.py` |
| 16 | SSE 双流（messages + values） | ✅ 保留等价能力 | `stream_mode=["messages","custom","updates"]`：messages 流输出 token/tool 事件，custom 流输出 plan/agent/tool/interrupt，interrupt 由状态字段 `pending_interrupt` 兜底检测，避免前后端不一致 | `api/routes_chat.py`, `tracing/events.py` |
| 17 | MCP 网关（原 Java ERP → FastMCP） | ✅ 保留，去掉 Java | 单进程 `FastMCP` server 暴露全部 OpsProvider 工具；LangGraph 侧通过 `MCPToolAdapter` 走同一 Tool Adapter 边界；支持 in-process 与 stdio 两种 transport | `mcp/server.py`, `mcp/client.py`, `tools/` |
| 18 | 中间件 9 件套 | ✅ 保留并重命名适配 | SandboxHealth / ContextInjection / SkillsSync / UserSkillsRestore / MemoryUpdate / SandboxCircuitBreaker / ModelCallLimit / ToolCallLimit + 新增 ToolPolicy / Tracing | `middleware/` 全目录 |
| 19 | 用户作用域隔离 | ✅ 保留 | user_id 隔离：sandbox workspace、memory、history、skills 全部按 user 分目录/命名空间；测试 user A 不能读 user B | `sandbox/manager.py`, `memory/preferences.py`, `storage/` |
| 20 | 熔断器（连续失败 OPEN→HALF_OPEN→CLOSED） | ✅ 保留 | `CircuitBreaker` 通用实现，Sandbox 与外部 Tool 各一个实例 | `sandbox/breaker.py`, `tools/breaker.py` |
| 21 | 调用限制（Model/Tool） | ✅ 保留 | ModelCallLimitMiddleware / ToolCallLimitMiddleware 强制终止防死循环 | `middleware/model_limit.py`, `middleware/tool_limit.py` |
| 22 | 供应商报价/采购单/图表 26 种 | ❌ 不继承（业务） | 替换为 metrics/logs/deployment/config-diff/topology/health 的 AIOps 工具族 | `providers/mock.py`, `tools/ops_tools.py` |
| 23 | Java ERP :8080 | ❌ 不继承 | Python MCP + OpsProvider Adapter（未来可接 Prometheus/Loki/K8s/GitHub/Grafana） | `providers/protocol.py`, `mcp/server.py` |
| 24 | OpenSandbox 商业私有环境 | ⚠️ 可选等价物 | 默认 DockerSandboxBackend；无 Docker 用 LocalSandboxBackend 保底运行；不依赖任何商业沙箱 | `sandbox/backends/` |
| 25 | MongoDB（原硬依赖） | ⚠️ 降为可选 | 默认 SQLite checkpoint + JSON 文件 storage；`StorageBackend` protocol 提供 `MongoStorageBackend`（extras `mongo`），compose 可选启动 | `storage/`, `compose.yml` |

## 2. AIOps 业务映射

| 采购原项目 | AegisOps |
|---|---|
| 供应商/物料/订单数据 | service catalog / topology / metrics / logs / deployments / config history / historical incidents |
| 下单流程 | Incident Response 流程：triage → plan → observe → analyze → hypothesize → remediate → verify → postmortem |
| request_order_info 补充 | MissingInfoGuard：environment / time range / service 缺失补充 |
| order_create/update 审批 | restart / scale / rollback / apply_config_change 审批（L2/L3） |
| 采购分析报告 | Incident Report（RCA + evidence + timeline + remediation + verification + follow-ups） |
| 图表 26 种 | 结构化证据摘要 + 可选 markdown 报告（不堆图表，聚焦 agent engineering） |

## 3. 10 类 AIOps 故障场景（每个都有 Ground Truth）

1. database-connection-pool-exhaustion
2. bad-deployment
3. memory-leak
4. redis-cache-timeout
5. upstream-dependency-timeout
6. disk-usage-saturation
7. traffic-spike
8. configuration-error
9. cpu-saturation
10. cascading-service-failure

每个 scenario 的 ground truth 字段：`incident_id / service / fault_type / root_cause / relevant_metrics / relevant_logs / relevant_changes / expected_tools / recommended_action / dangerous_action`。数据集由模板生成器生产 60+ 条非重复记录（见 `src/aegisops/evaluation/scenario_builder.py` 与 `fixtures/incidents/scenarios.json`）。

## 4. 继承后不允许出现的内容（验收红线）

- ❌ procurement / supplier / part / purchase order / 报价 / 商城 等原业务命名
- ❌ 原项目目录名 `api_view / agent / mcp_server / procurement_analyst / procurement_order`
- ❌ Java / ERP / OpenSandbox 商业依赖
- ❌ 任何硬编码 API Key
