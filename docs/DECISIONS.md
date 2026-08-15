# Design Decisions (ADR)

记录本项目关键取舍。格式：Decision / Alternatives / Reason / Trade-off。

---

## ADR-001: LangGraph 原生实现，不采用 DeepAgents
- **Decision**: 使用 `langgraph==1.2.x` + `langgraph-checkpoint-sqlite` 原生实现 Harness 等价能力。
- **Alternatives**: DeepAgents（PDF 原项目使用的框架）。
- **Reason**: DeepAgents 当前版本仍在快速演进、API 稳定性弱于 LangGraph 本体；本项目需要 `interrupt()`、SQLite checkpointer、自定义 subagent 隔离、SSE 双流与精确事件控制，LangGraph 原生层已覆盖全部需求且可控。用户要求“核心行为正确，不允许为了框架名称牺牲稳定性”。
- **Trade-off**: 需要自行实现 subagent 委派与摘要中间件；换来无隐藏依赖、可测试、面试时能逐行解释。

## ADR-002: 默认 SQLite checkpoint + 文件 storage，MongoDB 降为可选
- **Decision**: checkpoint 用 `AsyncSqliteSaver`；history/memory/traces 默认 JSON 文件（`StorageBackend` protocol）；`MongoStorageBackend` 作为 extras 提供，compose 可选启动。
- **Alternatives**: 像原项目一样硬依赖 MongoDB。
- **Reason**: clone → 安装 → 运行 必须零外部服务可复现；CI 不依赖容器。SQLite checkpoint 支持跨进程重启恢复，满足 HITL resume 要求。
- **Trade-off**: 生产多副本水平扩展需要切 Mongo；接口已预留，换 backend 不动业务代码。

## ADR-003: Sandbox 双后端：Docker 优先、Local 兜底
- **Decision**: `SandboxBackend` Protocol 下实现 `DockerSandboxBackend`（生产/强隔离）与 `LocalSandboxBackend`（开发机无 Docker 时兜底）。启动时自动探测 Docker，不可用则回退 Local 并写 warning 日志。
- **Alternatives**: 仅 Docker（demo 门槛高）；仅 Local（安全边界不足）。
- **Reason**: 需求明确“项目必须在没有 OpenSandbox 商业环境情况下可运行”，同时面试演示机器未必有 Docker。诚实处理：README 明确两种后端的隔离差异，生产配置强制 Docker。
- **Trade-off**: 两个 backend 的语义略有差异（资源限制、网络隔离）；协议层统一，测试主要覆盖 Local，Docker backend 用命令构造测试保证不误拼参数。

## ADR-004: MCP in-process transport 为默认
- **Decision**: MCP server 与 Agent 同进程通过 `MCPToolAdapter` 调用（绕过 stdio 的进程开销）；提供 stdio transport 供独立部署与集成测试。
- **Alternatives**: 所有工具调用都走 stdio 子进程。
- **Reason**: Windows 开发环境子进程管道有额外复杂度，且单进程 demo 可调试性更好；MCP 边界（server + tool schema + adapter）仍然真实存在。
- **Trade-off**: in-process 模式不验证网络层 MCP；stdio 模式有独立集成测试覆盖。

## ADR-005: FakeLLM / DeterministicLLM 作为离线一等公民
- **Decision**: 测试与离线 evaluation 全部使用规则驱动的 `FakeLLM`（决定工具调用序列与 JSON 输出），真实 LLM 只用于 demo 与 real eval（需 `LLM_API_KEY`）。
- **Alternatives**: 测试 mock httpx；evaluation 依赖真实 API。
- **Reason**: CI 必须无 key 可跑；evaluation 需要可复现、可审计；真实 LLM 结果单独归档，禁止混入伪造。
- **Trade-off**: FakeLLM 不度量模型能力，只度量 harness 正确性——这正是本项目的度量目标，README 会明确说明。

## ADR-006: 数据库事实与 LLM Memory 严格分离
- **Decision**: 服务 owner、依赖、当前版本、restart policy 全部来自 `ServiceCatalog` 工具；`PreferenceStore` 只保存用户偏好（语言/报告风格/时区/审批策略等）。
- **Alternatives**: 让 LLM 从历史对话“记住”CMDB 事实。
- **Reason**: 数据库事实会漂移，LLM 记忆会产生过期幻觉；这是本项目面试回答“Memory vs Database facts”的代码证据。
- **Trade-off**: 需要额外一次 catalog 工具调用；换来事实单一来源。

## ADR-007: SubAgent 返回 Pydantic 结构化报告，不返回自由文本
- **Decision**: 每个 SubAgent 的最终输出必须解析为 `SubAgentReport`（service/signals/hypotheses/evidence/confidence），解析失败自动修复一次，再失败降级为 `{summary, raw_excerpt}` 报告并标记 `degraded=true`。
- **Alternatives**: SubAgent 返回 markdown 自由文本。
- **Reason**: 主 Agent 的上下文隔离与后续指标（Evidence Completeness / RCA Accuracy）都依赖结构化证据；自由文本会把 context explosion 问题重新引入主 Agent。
- **Trade-off**: 需要 robust JSON 解析层；由 `llm/structured.py` 统一处理。

## ADR-008: HITL 采用两段式：MissingInfoGuard + ActionApprovalNode
- **Decision**: 缺信息与危险操作分开 interrupt，payload 类型 `missing_info` / `approval`；resume 载荷 `{supplement}` / `{decisions:[{type: approve|reject}]}`。reject 不终止：记录决策 → 生成安全替代方案 → 继续 verify + report。
- **Alternatives**: 单层 interrupt；reject 后直接结束。
- **Reason**: 与 PDF 双层中断思想一致；需求明确 reject 后“不能直接结束”。
- **Trade-off**: resume 分支逻辑更多；由 executor 状态机统一处理。

## ADR-009: SSE 中断检测以 graph state 的 `pending_interrupt` 为最终裁决
- **Decision**: interrupt 节点先把 payload 写入 state，再调用 `interrupt()`；SSE 生成器在 stream 结束后读取 snapshot values 兜底发 `interrupt` 事件。
- **Alternatives**: 只依赖 stream `values`/`custom` 事件检测。
- **Reason**: 不同 LangGraph 版本 interrupts 的流式表现有差异；state 兜底保证前后端状态一致。
- **Trade-off**: state 多一个字段；换来确定性与版本稳健。

## ADR-010: 不加入向量数据库 / GraphRAG
- **Decision**: MVP 不做 embedding、vector store、GraphRAG。
- **Reason**: 用户明确 GraphRAG 由另一个项目展示；本项目的重点是 Harness + Agent Runtime，堆向量库只会稀释核心。
- **Trade-off**: 历史 incident 检索用结构化过滤 + 关键词，足够 MVP 场景。

## ADR-011: 评价数据 60+ 条由模板生成器生产，不手写 60 条重复 JSON
- **Decision**: `scenario_builder.py` 从 10 类故障模板 × 服务/参数组合生成 60+ 条唯一场景，导出 `fixtures/incidents/scenarios.json`；每条含独立 evidence 内容与 ground truth。
- **Reason**: 手写 60 条 JSON 易错且不可维护；生成器保证 schema 一致、覆盖矩阵明确。
- **Trade-off**: 场景同模板有结构性相似；通过不同 service、窗口、关键日志/指标组合保证可区分性。

## ADR-012: 评估结果绝不伪造
- **Decision**: `eval_results/` 只放真实运行产物；README 引用 `eval_results/*/summary.json`。FakeLLM offline eval 明确标注“harness correctness evaluation”，真实 LLM eval 单独脚本与目录。
- **Reason**: 用户硬性规则；面试时被追问数据来源可以给出 artifact 复算路径。
- **Trade-off**: 无。

## ADR-013: 默认端口 8090，前缀 /api
- **Decision**: FastAPI 监听 8090（与 PDF 一致），静态页 `/`，API 全部 `/api/*`。
- **Alternatives**: 8000/3000。
- **Reason**: 保留原项目端口习惯，降低前端 fetch 心智负担。
- **Trade-off**: 无。

## ADR-014: 依赖全部固定版本，`pyproject.toml` 为准
- **Decision**: 每个运行时依赖 pin 精确版本；`requirements.txt` 由 pyproject 导出说明；CI 用 `pip install -e ".[dev]"`。
- **Reason**: clone 后可复现是验收标准。
- **Trade-off**: 需要手动升级；CHANGELOG 记录版本。
