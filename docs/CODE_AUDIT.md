# CloudOps Harness CODE AUDIT（专项整改审计）

> 审计时间：2026-08-16（UTC）
> 审计对象：`D:\CloudOps Harness`（v0.1.0，commit `951c8dd`）
> 审计方法：逐条对照专项整改 Prompt 的 60 项要求，读取代码/测试/artifact 后给出
> `PASS / PARTIAL / FAIL / NOT IMPLEMENTED` 与 `P0/P1/P2` 优先级。
> 结论使用规则：**文档写什么不重要，代码 + 测试 + artifact 决定状态。**

## 1. 定位与残留

| # | Requirement | Current Implementation | Status | Evidence | Problem | Required Change | Priority |
|---|---|---|---|---|---|---|---|
| 1 | 不是聊天/套壳 Multi-Agent | LangGraph 13 步故障链 + 4 个专业 SubAgent + HITL + sandbox | PASS | `src/cloudops_harness/agents/graph.py`, `nodes.py`, integration tests | 无 | - | - |
| 2 | 无采购/ERP/供应商残留 | 全仓检索无业务残留（mapping 文档仅为对照说明） | PASS | grep 结果；`docs/PDF_TO_AIOPS_MAPPING.md` 仅作对照 | 无 | - | - |
| 3 | 微服务环境完整 + MockOpsProvider | 6 服务 catalog + topology + metrics/logs/deployments/config/history | PASS | `fixtures/*.json`, `providers/mock.py` | 无 | - | - |
| 4 | Provider Dependency Inversion | `OpsProvider` ABC；`MCPToolAdapter` 是默认实现 | PASS | `providers/protocol.py` | 无 | - | - |

## 2. 故障场景与数据集

| # | Requirement | Current | Status | Evidence | Problem | Required Change | Priority |
|---|---|---|---|---|---|---|---|
| 5 | 10 类故障 + ground truth 字段 | 10 类 × 11 变体 = 110 条 | PASS | `fixtures/incidents/scenarios.json`, `scenario_builder.py` | 无 | - | - |
| 6 | ≥60 最好 100+ | 110 条 | PASS | 同上 | 无 | - | - |
| 7 | easy / dependency-chain / ambiguous 覆盖 | 缺失这 3 个显式 bucket（single_source 接近 easy，但无显式分类） | FAIL | `scenario_builder.py` 的 `VARIANTS` | 评测 bucket 不完整，面试会被追问“难度分层” | 增加 `easy`、`dependency_chain`、`ambiguous` 变体并重新生成 dataset（110 条） | P0 |
| 8 | machine-readable ground truth | 每场景含 root_cause/relevant_*/expected_tools/dangerous_action | PASS | dataset 不变量测试 | 无 | - | - |

## 3. Main Agent 与 SubAgent

| # | Requirement | Current | Status | Evidence | Problem | Required Change | Priority |
|---|---|---|---|---|---|---|---|
| 9 | Main 不读 raw logs/metrics | Main 只 `assemble_main_messages`，raw 在 transcripts | PASS | `agents/context.py` + `test_planning_context.py` | 无 | - | - |
| 10 | 四个专业 SubAgent 独立 prompt/tools/skills/context | YAML 声明式 + `SubAgentRunner` | PASS | `subagents/configs/*.yaml`, `runner.py` | 无 | - | - |
| 11 | Log Agent 大量日志只留在其 context | full tool results 存 transcript；main 不接触 | PASS | `runner.py` + isolation test | 无 | - | - |
| 12 | 新增 Agent = 新增 YAML | loader 全量扫描 YAML | PASS | `loader.py` | 无 | - | - |
| 13 | Change Agent 区分相关性与因果 | prompt 已写“不能仅凭时间推断因果” | PARTIAL | `change_analysis.yaml` | 输出 schema 没有 `correlation/causal_confidence` 字段，无法量化 | 增加结构化 correlation 字段 + FakeLLM 分支 + 测试 | P0 |
| 14 | Remediation Agent 不能绕过 HITL | 其工具白名单 L≤1；executor 才执行写操作 | PASS | `loader.py` 校验 + `nodes.py` executor | 无 | - | - |
| 15 | Agent→Agent 用 Pydantic schema | `SubAgentReport` + `generate_structured` | PASS | `agents/models.py` | 无 | - | - |

## 4. Planning / Context Engineering

| # | Requirement | Current | Status | Evidence | Problem | Required Change | Priority |
|---|---|---|---|---|---|---|---|
| 16 | Plan 是真实 state（pending/in_progress/completed/failed/skipped） | state 里有 plan，但无 `skipped`；恢复依赖 checkpoint | PARTIAL | `agents/state.py`, `planner.py` | `skipped` 缺失；无 max plan iterations 上限 | 增加 `skipped` 状态；`max_plan_steps` 硬上限；超限 graceful stop + partial report | P0 |
| 17 | checkpoint 恢复 plan 状态 | plan 在 checkpoint state 中，SQLite 跨重启测试通过 | PASS | `test_checkpoint_resume.py` | 无 | - | - |
| 18 | Context Compression 必须真的运行并量化 | `ContextCompressor` 只被单元测试，graph 从未调用 | FAIL | `agents/context.py` vs `nodes.py` 无调用 | 文档说“支持压缩”，实际主流程没触发 | 在 graph 主上下文中触发压缩；记录 before/after tokens、ratio、preserved fields；测试 | P0 |
| 19 | Main Agent input tokens 量化 | 未记录 | FAIL | `context_stats` 仅 prepare_tokens | isolation ablation 只能比总 token，不够精确 | synthesize 记录 `main_context_tokens`；eval 增加该指标 | P0 |
| 20 | Memory vs CMDB 分离 | PreferenceStore 只存偏好；catalog 走工具 | PASS | `memory/preferences.py`, `providers/mock.py` | 无 | - | - |
| 21 | Memory user-scoped + A/B 测试 | file 按 user 分目录 + 测试 | PASS | `test_skills_memory.py` | 可再补“A 文件不被 B 读”显式断言 | 补显式 isolation 测试 | P2 |

## 5. Tools / MCP / Risk / HITL

| # | Requirement | Current | Status | Evidence | Problem | Required Change | Priority |
|---|---|---|---|---|---|---|---|
| 22 | 15 个 MCP/tool 边界 | FastMCP 15 工具 + MCPToolAdapter | PASS | `mcp/server.py`, `mcp/client.py` | 无 | - | - |
| 23 | Risk L0–L3 代码级强制 | `ToolRegistry.call(approved=...)` 抛错；subagent 白名单校验 | PASS | `tools/risk.py`, `registry.py` | 无 | - | - |
| 24 | prompt injection 不能绕过 policy | 结构化输出 + 工具门禁 | PARTIAL | `test_tools.py` approval test | 没有显式 injection testcase（日志含 IGNORE/CALL restart_service） | 增加 security test：injected log 不改 risk policy、不触发动作 | P0 |
| 25 | 两层 interrupt（missing info / approval） | 已实现 | PASS | `test_main_agent.py` | 无 | - | - |
| 26 | reject 后记录 + 替代方案 + 继续报告 | 已实现 | PASS | demo3 + rejection test | 无 | - | - |
| 27 | L3 审批字段完整 | reason/target/before-state/expected-impact | PASS | `nodes.py` executor | 无 | - | - |
| 28 | Dry Run | 未实现 | NOT IMPLEMENTED | - | 高风险动作直接进审批，缺少 dry_run 预览 | executor 生成 `dry_run`（target/planned/before/expected/rollback_method/risk）并入 interrupt payload | P1 |
| 29 | resume 不重跑前序步骤 | SQLite checkpoint + 工具调用不重复测试 | PARTIAL | `test_checkpoint_resume.py` | 测试只断言最终结果，未断言 tool call IDs 不重复 | 增加 resume 前后 tool trace 对比测试 | P0 |

## 6. SSE / Observability / Failure

| # | Requirement | Current | Status | Evidence | Problem | Required Change | Priority |
|---|---|---|---|---|---|---|---|
| 30 | SSE 事件类型齐全 | 11 类事件 | PASS | `test_api.py` | 无 | - | - |
| 31 | 事件统一 schema：run_id/thread_id/timestamp/sequence | 事件没有统一 envelope | FAIL | `events.py`, `chat.py` | UI 无法去重/排序/关联 run | `emit()` 统一注入 run_id/thread_id/ts/sequence；前端按 sequence 去重 | P0 |
| 32 | disconnect/reconnect/resume 一致性 | resume 端点 + 状态检测 | PARTIAL | `chat.py` | 无 sequence/去重；事件协议不完整 | 随 #31 修复 | P0 |
| 33 | trace 含 model/tokens/risk/HITL/agent 时间线 | 当前只有 tool_start/end（agent/thread/run/user/latency/status/error） | PARTIAL | `tracing/store.py`, `runtime.py` | 缺 model、token、risk level、HITL decision | observer 补 risk；节点记录 agent/HITL；middleware 记录 run 汇总 | P1 |
| 34 | tool timeout / MCP down / sandbox crash / malformed output / Mongo down / resume after restart 注入测试 | 全部有 | PASS | `tests/failure/` | LLM timeout 与 partial SSE disconnect 未显式覆盖 | 增加 LLM timeout failure test（FakeLLM 抛 timeout）；SSE 断连以 resume 测试覆盖并文档说明 | P1 |
| 35 | Circuit Breaker 状态 + transition 记录 | 状态机有，但无 transition 日志 | PARTIAL | `common/circuit_breaker.py` | 无法展示 OPEN→HALF_OPEN→CLOSED 轨迹 | 增加 `transitions` 记录 + 测试 | P0 |
| 36 | 无限循环防护（model/tool/plan/delegation depth/timeout） | AgentLoop max_iterations + tool limit | PARTIAL | `loop.py`, `registry.py` | model limit 只事后记录；无 plan/delegation depth 上限 | 硬限制 + graceful partial report | P0 |
| 37 | Structured output 校验矩阵（missing/wrong/truncated/extra/invalid confidence） | retry/fallback 有，测试覆盖 malformed 与 retry | PARTIAL | `llm/structured.py`, `test_llm.py` | 测试矩阵不完整；confidence 无边界 | Pydantic `ge/le` 边界 + 完整矩阵测试 | P1 |

## 7. Sandbox / Skills / Memory / Security

| # | Requirement | Current | Status | Evidence | Problem | Required Change | Priority |
|---|---|---|---|---|---|---|---|
| 38 | Sandbox Protocol + Docker + Proxy + Manager + Health | 已实现 | PASS | `sandbox/` | 无 | - | - |
| 39 | sandbox crash → rebuild → replace → 继续（自动测试） | 已实现且测试 | PASS | `tests/failure/test_sandbox_recovery.py` | 无 | - | - |
| 40 | user A/B sandbox 隔离 | 已实现且测试 | PASS | `test_sandbox.py` | 无 | - | - |
| 41 | Docker 后端安全参数 + host 敏感路径不暴露 | flags 测试覆盖 | PASS | `test_sandbox.py` | 无 volume mount 断言缺失 | 补 `-v` 不存在断言 | P2 |
| 42 | Local backend 诚实定位（非强隔离） | 文档明示 | PASS | `SECURITY.md` | 无 | - | - |
| 43 | Skills 渐进披露 + 加载记录 | frontmatter 注入 prompt；body 按需 | PARTIAL | `skills/registry.py`, `runner.py` | 未记录“哪个 Agent 加载哪个 Skill” | runner 记录 skill_loads 到 stats + 日志 + 测试 | P1 |
| 44 | Dynamic skill 安全门 | allowlist/type/size/静态检查/审批/测试 runner | PASS | `skills/installer.py` + tests | 无 | - | - |
| 45 | PII Redaction | 未实现 | NOT IMPLEMENTED | - | middleware 列表缺失 | `PIIRedactionMiddleware` + registry 内容脱敏 + 测试 | P1 |
| 46 | Evidence 可追溯（source/tool/ts/service/raw_ref） | EvidenceItem 只有 source/summary/detail | PARTIAL | `agents/models.py` | raw reference 缺失 | 扩展 EvidenceItem；runner 从 full tool results 填充 | P0 |
| 47 | RCA hypothesis 带 supporting/contradicting evidence | 未实现 | FAIL | `RcaHypothesis` | 面试攻击点 | 增加 evidence ids + synthesize 填充 + report 展示 | P0 |
| 48 | Remediation 后 verify（before/after + resolved） | verify 节点存在 | PARTIAL | `nodes.py` | 未显式 resolved/not-resolved 判断；无 before 对比 | verification 增加 before_state 与 resolved 字段 | P1 |

## 8. Evaluation

| # | Requirement | Current | Status | Evidence | Problem | Required Change | Priority |
|---|---|---|---|---|---|---|---|
| 49 | A/B/C 三个 baseline | single / multi / harness 均有 | PASS | `eval_results/*` | 无 | - | - |
| 50 | 核心指标齐全 | 有 11 项 | PARTIAL | `metrics.py` | 缺 unnecessary calls、delegation accuracy、main context tokens、verification rate、resume success | 新增 5 项指标 | P0 |
| 51 | paired + McNemar + bootstrap + CI | 已实现 | PASS | artifact comparisons | 无 | - | - |
| 52 | bucket 分析（simple/complex/multi-source/multi-hop） | 未实现 | FAIL | - | 无法回答“何时用 Multi-Agent” | 按 bucket 输出 paired 对比 | P0 |
| 53 | ≥3 组 ablation | isolation、recovery、single-vs-harness 有 | PARTIAL | artifact | no-HITL 有（multi auto=3）；无 no-planning | 保留现有 4 组即可（要求≥3），文档写明 | P2 |
| 54 | Sandbox recovery 量化 | 10 个场景 paired，但无 recovery latency | PARTIAL | artifact | 建议 30 次注入 | 记录 recovery latency；文档说明样本量 n=10，不吹“30” | P1 |
| 55 | HITL recall/precision/unsafe count | 未实现显式指标 | FAIL | `metrics.py` | 无法回答“HITL 拦了多少” | 增加 hitl_recall/hitl_precision/unsafe_execution_count | P0 |
| 56 | raw artifacts 可复算 | summary.json 含 per-run 明细 | PASS | artifact | 无 | - | - |
| 57 | FakeLLM 只证明 workflow correctness（文档诚实） | 已声明 | PASS | README/EVALUATION | 无 | - | - |

## 9. CI / 依赖 / 前端 / Demo / Docs

| # | Requirement | Current | Status | Evidence | Problem | Required Change | Priority |
|---|---|---|---|---|---|---|---|
| 58 | CI ruff+pytest 无 key/外部服务 | 已实现 | PASS | `.github/workflows/ci.yml` | 无 | - | - |
| 59 | 依赖固定版本 | 全部 pin | PASS | `pyproject.toml` | 无 | - | - |
| 60 | 前端够用 | chat/SSE/todo/agent/tool/interrupt/history/report | PASS | `static/` | sequence 去重随 #31 补 | - | P0 |
| 61 | Demo A/B/C | 已实测 | PASS | `data/demo_reports/` | 无 | - | - |
| 62 | Demo D（sandbox crash / resume） | 未实现 | NOT IMPLEMENTED | - | 加分 demo 缺失 | 新增 `--demo 4` | P1 |
| 63 | README claim 可追代码/测试/artifact | 大部分有 | PARTIAL | README | 部分 claim 未逐一映射 | 重写 claim 映射表 | P0 |
| 64 | Limitations 明确 | 已写 | PASS | README | 无 | - | - |

## 整改顺序

1. **P0**：SSE envelope → ContextCompressor 集成 → planning 上限/skipped → dry_run/injection/HITL 指标 → evidence/RCA 可追溯 → dataset 扩展与 bucket → breaker transitions → resume 不重跑测试 → README claim 映射。
2. **P1**：trace 补全 → PII redaction → structured-output 矩阵 → skill load 记录 → recovery latency → Demo D → LLM timeout test。
3. **P2**：memory isolation 显式断言、Docker no-volume 断言、UI 去重。

> 所有修改完成后重跑：ruff + pytest + failure/security tests + 全量 evaluation + 3 个 demo + 新 Demo D + 真实服务器 SSE 冒烟，并重新生成 BUILD_REPORT/EVALUATION/SECURITY/ARCHITECTURE。


## 整改执行结果（2026-08-16）

| # | 原状态 | 整改动作 | 证据 | 新状态 |
|---|---|---|---|---|
| 7 | FAIL | 新增 easy/dependency_chain/ambiguous 变体，dataset 100→110 | `scenario_builder.py`, `tests/evaluation/test_evaluation.py` | PASS |
| 13 | PARTIAL | change-analysis 增加 correlation/causal_confidence 字段 + prompt + FakeLLM + 测试 | `change_analysis.yaml`, `fake.py`, `test_main_agent.py` | PASS |
| 16 | PARTIAL | PlanStep 增加 skipped；max_plan_steps/max_delegation_depth 硬限；partial report 路由 | `models.py`, `nodes.py`, `graph.py` | PASS |
| 18 | FAIL | `compress_main_context()` 在 synthesize 实际触发；记录 before/after/ratio/preserved | `context.py`, `nodes.py`, `test_planning_context.py` | PASS |
| 19 | FAIL | `context_stats.main_context_tokens` + eval 指标 + isolation 对比 | `metrics.py`, artifact | PASS |
| 24 | PARTIAL | `tests/security/test_security.py` prompt injection + registry bypass 测试 | security tests | PASS |
| 28 | NOT IMPLEMENTED | `dry_run_action` L0 工具 + `ActionRequest.dry_run` 进审批 payload | `providers/`, `tools/`, `nodes.py` | PASS |
| 29 | PARTIAL | checkpoint 测试断言 pre-interrupt 工具调用次数不增长 | `test_checkpoint_resume.py` | PASS |
| 31 | FAIL | 统一事件 envelope + sequence + 前端去重 + 单测/API 测试 | `events.py`, `chat.py`, `app.js`, `test_events.py`, `test_api.py` | PASS |
| 33 | PARTIAL | tool trace 加 risk_level；节点记录 agent/HITL/action/verify/report | `runtime.py`, `nodes.py`, `test_api.py` | PASS |
| 35 | PARTIAL | CircuitBreaker.transitions 记录 + 测试 | `common/circuit_breaker.py`, `test_tools.py` | PASS |
| 36 | PARTIAL | LimitedModelAdapter 硬停 + 节点 graceful degradation + plan/depth 上限 | `llm/base.py`, `nodes.py`, `loop.py`, `planner.py` | PASS |
| 37 | PARTIAL | confidence 加 ge/le 边界 + missing/wrong/truncated/extra/invalid 测试矩阵 | `models.py`, `test_llm.py` | PASS |
| 43 | PARTIAL | runner 记录 skills_loaded 到 stats + 日志 | `runner.py`, `nodes.py` | PASS |
| 45 | NOT IMPLEMENTED | PII redaction 中间件 + ToolRegistry 边界脱敏 + 测试 | `tools/pii.py`, `middleware/`, `test_tools.py` | PASS |
| 46 | PARTIAL | EvidenceItem 增加 id/tool/timestamp/service/raw_ref；runner 归一化 | `models.py`, `runner.py` | PASS |
| 47 | FAIL | RcaHypothesis supporting/contradicting evidence + report 展示 | `models.py`, `nodes.py`, `report.py` | PASS |
| 48 | PARTIAL | verification 增加 resolved/before/after | `nodes.py`, `report.py` | PASS |
| 50 | PARTIAL | 新增 5+ 指标（unsafe count、HITL recall/precision、recovery latency、main context tokens、unnecessary calls、delegation、resume、verification） | `metrics.py`, artifact | PASS |
| 52 | FAIL | bucket_comparisons（simple/multi_source/multi_hop/complex/failure_injection） | `harness.py`, artifact | PASS |
| 54 | PARTIAL | recovery latency 指标 + n=10 如实声明 | artifact, `EVALUATION.md` | PARTIAL（n=10 非 30，已声明） |
| 55 | FAIL | hitl_recall / hitl_precision / unsafe_execution_count | `metrics.py`, artifact | PASS |
| 62 | NOT IMPLEMENTED | Demo D（sandbox crash + SQLite restart + resume） | `demo.py`, `data/demo_reports/demo4_*.md` | PASS |
| 63 | PARTIAL | README 增加 Claim→Evidence 映射表 | `README.md` | PASS |
| 34 | PARTIAL | LLM timeout retry 测试；partial SSE disconnect 通过 resume 测试覆盖并文档说明 | `test_failure_injection.py`, `EVALUATION.md` | PASS |
