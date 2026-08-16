# CloudOps Harness Evaluation

## 0. Hard rules

1. 所有数字必须来自真实运行的 evaluation artifact（`eval_results/*/summary.json`）。
2. FakeLLM（离线）与真实 LLM 评测完全分开；CI 不依赖任何 API key。
3. FakeLLM 只能证明 workflow/harness 正确性，不宣称模型能力。
4. 禁止挑选场景；样本量与模型写在 tag 中。

## 1. Dataset

- `fixtures/incidents/scenarios.json`：**110 条**，由 `scenario_builder.py` 生成。
- 10 类故障 × 11 个变体：`easy / single_source / multi_source / multi_hop /
  dependency_chain / dangerous_action / missing_information / ambiguous /
  tool_failure / sandbox_failure / safe_only`。
- 每条含 ground truth：root_cause / relevant_metrics / relevant_logs /
  relevant_changes / expected_tools / recommended_action / dangerous_action
  以及嵌入式 evidence specs。
- `validate_dataset()` 测试强制不变量。

## 2. Systems

| System | 组成 |
|---|---|
| single-agent | 一个 Agent 拥有全部工具，无规划/隔离/HITL |
| multi-agent | Main + 4 SubAgents + planning + isolation，HITL 关闭 |
| multi-no-isolation | 同上但 context isolation 关闭（raw transcript 注入主上下文） |
| harness | 完整 Harness：planning + isolation + sandbox + HITL + recovery |
| harness-no-recovery | 完整 Harness 但 sandbox auto-recovery 关闭 |

## 3. Metrics

核心指标 + 本次新增：
`root_cause_accuracy / task_completion_rate / tool_selection_accuracy /
evidence_completeness / unsafe_action_rate(_dangerous) / unsafe_execution_count /
hitl_compliance_rate / hitl_recall / hitl_precision / recovery_success_rate /
mean_recovery_latency_ms / remediation_verification_rate /
remediation_resolution_rate / resume_success_rate / mean_tool_calls /
mean_llm_calls / mean_token_cost / mean_latency_ms /
mean_main_context_tokens / mean_unnecessary_tool_call_rate /
mean_delegation_accuracy`。

## 4. Statistics

- Binary 配对：McNemar exact test。
- Continuous 配对：paired bootstrap（n_boot=2000, seed=42），报告 mean diff 与 95% CI。
- 按 `incident_id` 配对；`summary.json` 保存全部 per-run 明细，任何数字可复算。

## 5. Current results（真实运行，2026-08-16 UTC）

Artifact: `eval_results/offline_20260816T045911Z/summary.json`
（tag `offline-fake-llm-n110`，n=110 × 5 systems）。

| 指标 | Single | Multi | Multi no-iso | Harness | Harness no-rec |
|---|---|---|---|---|---|
| RCA accuracy | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| Completion | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| Tool selection | 1.000 | 0.987 | 0.987 | 0.987 | 0.987 |
| Evidence completeness | 1.000 | 0.984 | 0.984 | 0.984 | 0.984 |
| Unsafe (dangerous) | 1.000 | 1.000 | 1.000 | 0.000 | 0.000 |
| Unsafe executions | 10 | 10 | 10 | 0 | 0 |
| HITL recall/compliance | 0.000 | 0.000 | 0.000 | 1.000 | 1.000 |
| Recovery success | 0.000 | 1.000 | 1.000 | 1.000 | 0.000 |
| Recovery latency mean/median/P95 ms | - | 159.3/156.0/172.0 | 159.3/156.0/172.0 | 159.5/156.5/172.0 | - |
| Remediation verification | 0.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| Remediation resolution | 0.000 | 0.091 | 0.091 | 0.091 | 0.091 |
| Resume success | 0.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| Main-context tokens | n/a | 1324.9 | 1368.8 | 1324.9 | 1324.9 |
| Unnecessary tool rate | 0.000 | 0.420 | 0.420 | 0.420 | 0.420 |
| Mean tool calls | 5.41 | 27.46 | 27.46 | 27.46 | 27.46 |
| Mean LLM calls | 6.41 | 43.45 | 43.45 | 43.45 | 43.45 |
| Mean token cost | 4803.4 | 39283.3 | 39337.0 | 39280.9 | 39274.3 |
| Mean latency ms | 56.0 | 115.6 | 107.8 | 110.2 | 95.9 |

### 5.1 Key paired conclusions

- HITL：Single/Multi 在 10 个危险场景全部无审批执行；Harness unsafe=0、
  recall=1。McNemar p=0.002。
- Recovery：Harness 10/10 恢复，关闭 recovery 后 0/10；p=0.002。
- Isolation ablation：no-isolation 比 isolation main-context +43.94 token
  （95% CI [+43.06, +44.84]）、总 token +50.19（CI [+46.37, +54.24]）。
- Single vs Harness：token −34373.6（CI [−34681.4, −34075.1]），
  latency −66.9 ms（CI [−71.7, −62.7]）。
- 分难度 bucket（Single vs Harness，FakeLLM）：
  - simple n=20：token −34952.1，latency −67.3ms
  - multi_source n=10：token −37368.8，latency −59.4ms
  - multi_hop n=20：token −34052.2，latency −60.9ms
  - complex n=50：token −34623.8，latency −68.7ms
  - failure_injection n=20：token −32863.8，latency −61.1ms
- **结论不夸大**：FakeLLM 下所有系统 RCA 都达上限，本评测证明的是 Harness
  的护栏、恢复、resume 与成本差异；“Multi-Agent 更聪明”需要真实 LLM 评测。

## 6. Ablations

1. Single vs Harness（paired，110 对）——成本与 unsafe 差异。
2. Multi no-isolation vs Multi（context isolation）。
3. Harness-no-recovery vs Harness（sandbox recovery）。
4. Multi auto-HITL-off vs Harness（HITL 开关）。

## 7. Reproduce

```bash
pip install -e ".[dev]"
python scripts/run_eval.py                 # n=110 offline
python scripts/run_eval.py --limit 20
python scripts/run_real_eval.py --limit 20 # real LLM (requires .env)
pytest tests/evaluation/test_evaluation.py
```

## 8. Known evaluation limitations（不隐藏）

- FakeLLM 只能证明 workflow correctness。
- Sandbox recovery 注入样本 n=10/系统（不是 30）；文档如实写 10。
- `hitl_precision` 在无 approval 的 baseline 上按定义取 1.0（没有误报）。
- `mean_main_context_tokens` 对 Single-Agent 记为 n/a（其无主/子上下文之分）。
- 本地开发机执行，latency 绝对值只用于同机相对比较。
