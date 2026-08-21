# Resume Claims

These claims are supported by code, tests and committed real artifacts. They are
intentionally conservative.

## Engineering Claims

- 基于 LangGraph 设计并实现 Stateful Multi-Agent Runtime，支持专业 SubAgent 调度与结构化证据聚合。
- 构建 ToolRegistry 风险边界（L0–L3），未审批的高风险工具无法执行。
- 实现 HITL 审批流，支持 `action_id` 精确绑定、拒绝后安全替代与继续执行。
- 实现 SQLite Checkpoint / Resume，支持中断后恢复且不重跑已完成步骤。
- 实现 Sandbox Recovery 与 Circuit Breaker：故障后热替换 backend 并重试。
- 实现 Context Isolation：主 Agent 不读取原始 SubAgent transcript，只接收结构化证据。
- 实现 MCP / FastMCP Tool Adapter 与可替换 OpsProvider。

## Evaluation Claims

- 构建 FakeLLM / Real LLM 严格分离的评测体系；FakeLLM 仅用于 deterministic CI/regression。
- 构建 ground-truth leakage audit，自动检查 prompt / tool response 不包含 evaluator-only label。
- 使用 DeepSeek-V4-Flash 真实 API 完成 fail-closed real evaluation，adapter 类型在 artifact 中记录为 `real`。
- 完成 Single-Agent vs Full Harness 的 limited paired real-LLM comparison（n=5 paired dev incidents）。
- 记录真实 token usage、model calls、latency、safety、recovery 与 failure taxonomy。
- 生成可复现 artifact：`runs.jsonl`、`summary.json`、`manifest.json`、`failures.json`、`checksums.sha256`。

## Portfolio-Scale Scope

- 这是 Portfolio-scale evaluation，不是 academic leaderboard，也不是 production benchmark。
- 正式 paired sample 为 5 个 dev incidents；Formal Harness-20 因 stop-loss 未完成，未作为 paired claim。
- 不声称 SOTA、production proven、100% RCA 或 external benchmark validated。

## Positioning

项目适合以下岗位方向：

- Agent / LLM Application Engineer
- AI Platform / Agent Infra
- LLM Application Developer
- AIOps / Reliability Engineer
