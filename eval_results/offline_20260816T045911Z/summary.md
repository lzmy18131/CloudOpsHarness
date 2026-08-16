# CloudOps Harness Evaluation Results

tag: `offline-fake-llm-n110`
generated: 2026-08-16T04:59:11.771024Z

## single-agent

- n=110
- root_cause_accuracy: 1.0000
- task_completion_rate: 1.0000
- tool_selection_accuracy: 1.0000
- evidence_completeness: 1.0000
- unsafe_action_rate: 0.0909
- unsafe_action_rate_dangerous: 1.0000
- unsafe_execution_count: 10.0000
- hitl_compliance_rate: 0.0000
- hitl_recall: 0.0000
- hitl_precision: 1.0000
- resume_success_rate: 0.0000
- remediation_verification_rate: 0.0000
- mean_unnecessary_tool_call_rate: 0.0000
- mean_delegation_accuracy: 0.0000
- recovery_success_rate: 0.0000
- mean_tool_calls: 5.41
- mean_llm_calls: 6.41
- mean_token_cost: 4803.44
- mean_latency_ms: 55.96
- mean_main_context_tokens: 0.00

## multi-agent

- n=110
- root_cause_accuracy: 1.0000
- task_completion_rate: 1.0000
- tool_selection_accuracy: 0.9870
- evidence_completeness: 0.9842
- unsafe_action_rate: 0.0909
- unsafe_action_rate_dangerous: 1.0000
- unsafe_execution_count: 10.0000
- hitl_compliance_rate: 0.0000
- hitl_recall: 0.0000
- hitl_precision: 1.0000
- resume_success_rate: 1.0000
- remediation_verification_rate: 1.0000
- mean_unnecessary_tool_call_rate: 0.4204
- mean_delegation_accuracy: 0.7974
- recovery_success_rate: 1.0000
- mean_recovery_latency_ms: 159.3000
- mean_tool_calls: 27.45
- mean_llm_calls: 43.45
- mean_token_cost: 39283.31
- mean_latency_ms: 115.62
- mean_main_context_tokens: 1326.90

## multi-no-isolation

- n=110
- root_cause_accuracy: 1.0000
- task_completion_rate: 1.0000
- tool_selection_accuracy: 0.9870
- evidence_completeness: 0.9842
- unsafe_action_rate: 0.0909
- unsafe_action_rate_dangerous: 1.0000
- unsafe_execution_count: 10.0000
- hitl_compliance_rate: 0.0000
- hitl_recall: 0.0000
- hitl_precision: 1.0000
- resume_success_rate: 1.0000
- remediation_verification_rate: 1.0000
- mean_unnecessary_tool_call_rate: 0.4204
- mean_delegation_accuracy: 0.7974
- recovery_success_rate: 1.0000
- mean_recovery_latency_ms: 159.3000
- mean_tool_calls: 27.45
- mean_llm_calls: 43.45
- mean_token_cost: 39336.98
- mean_latency_ms: 107.82
- mean_main_context_tokens: 1372.84

## harness

- n=110
- root_cause_accuracy: 1.0000
- task_completion_rate: 1.0000
- tool_selection_accuracy: 0.9870
- evidence_completeness: 0.9842
- unsafe_action_rate: 0.0000
- unsafe_action_rate_dangerous: 0.0000
- unsafe_execution_count: 0.0000
- hitl_compliance_rate: 1.0000
- hitl_recall: 1.0000
- hitl_precision: 1.0000
- resume_success_rate: 1.0000
- remediation_verification_rate: 1.0000
- mean_unnecessary_tool_call_rate: 0.4256
- mean_delegation_accuracy: 0.7974
- recovery_success_rate: 1.0000
- mean_recovery_latency_ms: 159.5000
- mean_tool_calls: 27.45
- mean_llm_calls: 43.45
- mean_token_cost: 39280.94
- mean_latency_ms: 110.23
- mean_main_context_tokens: 1326.90

## harness-no-recovery

- n=110
- root_cause_accuracy: 1.0000
- task_completion_rate: 1.0000
- tool_selection_accuracy: 0.9870
- evidence_completeness: 0.9842
- unsafe_action_rate: 0.0000
- unsafe_action_rate_dangerous: 0.0000
- unsafe_execution_count: 0.0000
- hitl_compliance_rate: 1.0000
- hitl_recall: 1.0000
- hitl_precision: 1.0000
- resume_success_rate: 1.0000
- remediation_verification_rate: 1.0000
- mean_unnecessary_tool_call_rate: 0.4256
- mean_delegation_accuracy: 0.7974
- recovery_success_rate: 0.0000
- mean_tool_calls: 27.45
- mean_llm_calls: 43.45
- mean_token_cost: 39274.32
- mean_latency_ms: 95.88
- mean_main_context_tokens: 1326.90

## Paired comparisons

### single-agent vs harness
- rca_correct: a=1.000 b=1.000 discordant b=0 c=0 McNemar p=1.0000
- task_completed: a=1.000 b=1.000 discordant b=0 c=0 McNemar p=1.0000
- unsafe_action: a=0.091 b=0.000 discordant b=10 c=0 McNemar p=0.0020
- tool_calls: mean_diff=-22.05 95% CI [-22.27, -21.83]
- llm_calls: mean_diff=-37.05 95% CI [-37.27, -36.83]
- token_cost: mean_diff=-34477.50 95% CI [-34783.38, -34179.85]
- latency_ms: mean_diff=-54.26 95% CI [-58.45, -50.27]
- main_context_tokens: mean_diff=-1326.90 95% CI [-1331.49, -1322.49]
- unnecessary_tool_call_rate: mean_diff=-0.43 95% CI [-0.44, -0.41]
- delegation_accuracy: mean_diff=-0.80 95% CI [-0.81, -0.79]

### multi-agent vs harness
- rca_correct: a=1.000 b=1.000 discordant b=0 c=0 McNemar p=1.0000
- task_completed: a=1.000 b=1.000 discordant b=0 c=0 McNemar p=1.0000
- unsafe_action: a=0.091 b=0.000 discordant b=10 c=0 McNemar p=0.0020
- tool_calls: mean_diff=0.00 95% CI [0.00, 0.00]
- llm_calls: mean_diff=0.00 95% CI [0.00, 0.00]
- token_cost: mean_diff=2.37 95% CI [-4.59, 9.83]
- latency_ms: mean_diff=5.39 95% CI [0.38, 10.08]
- main_context_tokens: mean_diff=0.00 95% CI [0.00, 0.00]
- unnecessary_tool_call_rate: mean_diff=-0.01 95% CI [-0.01, -0.00]
- delegation_accuracy: mean_diff=0.00 95% CI [0.00, 0.00]

### multi-agent vs multi-no-isolation
- rca_correct: a=1.000 b=1.000 discordant b=0 c=0 McNemar p=1.0000
- task_completed: a=1.000 b=1.000 discordant b=0 c=0 McNemar p=1.0000
- unsafe_action: a=0.091 b=0.091 discordant b=0 c=0 McNemar p=1.0000
- tool_calls: mean_diff=0.00 95% CI [0.00, 0.00]
- llm_calls: mean_diff=0.00 95% CI [0.00, 0.00]
- token_cost: mean_diff=-53.67 95% CI [-57.09, -50.16]
- latency_ms: mean_diff=7.80 95% CI [3.00, 12.42]
- main_context_tokens: mean_diff=-45.94 95% CI [-46.84, -45.06]
- unnecessary_tool_call_rate: mean_diff=0.00 95% CI [0.00, 0.00]
- delegation_accuracy: mean_diff=0.00 95% CI [0.00, 0.00]

### harness-no-recovery vs harness
- rca_correct: a=1.000 b=1.000 discordant b=0 c=0 McNemar p=1.0000
- task_completed: a=1.000 b=1.000 discordant b=0 c=0 McNemar p=1.0000
- unsafe_action: a=0.000 b=0.000 discordant b=0 c=0 McNemar p=1.0000
- recovery_success: a=0.000 b=1.000 discordant b=0 c=10 McNemar p=0.0020
- tool_calls: mean_diff=0.00 95% CI [0.00, 0.00]
- llm_calls: mean_diff=0.00 95% CI [0.00, 0.00]
- token_cost: mean_diff=-6.62 95% CI [-13.35, -0.39]
- latency_ms: mean_diff=-14.35 95% CI [-24.05, -4.57]
- main_context_tokens: mean_diff=0.00 95% CI [0.00, 0.00]
- unnecessary_tool_call_rate: mean_diff=0.00 95% CI [0.00, 0.00]
- delegation_accuracy: mean_diff=0.00 95% CI [0.00, 0.00]

## Bucket comparisons (single-agent vs harness)

### simple (n=20)
- rca_correct: a=1.000 b=1.000 McNemar p=1.0000
- task_completed: a=1.000 b=1.000 McNemar p=1.0000
- token_cost: mean_diff=-35049.40 95% CI [-35545.55, -34562.50]
- latency_ms: mean_diff=-57.80 95% CI [-71.30, -47.00]
- tool_calls: mean_diff=-22.40 95% CI [-22.70, -22.10]
- evidence_completeness: mean_diff=0.01 95% CI [0.00, 0.03]

### multi_source (n=10)
- rca_correct: a=1.000 b=1.000 McNemar p=1.0000
- task_completed: a=1.000 b=1.000 McNemar p=1.0000
- token_cost: mean_diff=-37477.30 95% CI [-38669.40, -36392.10]
- latency_ms: mean_diff=-56.20 95% CI [-63.90, -48.40]
- tool_calls: mean_diff=-24.90 95% CI [-25.20, -24.60]
- evidence_completeness: mean_diff=0.00 95% CI [0.00, 0.00]

### multi_hop (n=20)
- rca_correct: a=1.000 b=1.000 McNemar p=1.0000
- task_completed: a=1.000 b=1.000 McNemar p=1.0000
- token_cost: mean_diff=-34148.55 95% CI [-34612.15, -33694.45]
- latency_ms: mean_diff=-52.45 95% CI [-57.10, -48.35]
- tool_calls: mean_diff=-21.00 95% CI [-21.30, -20.75]
- evidence_completeness: mean_diff=0.02 95% CI [0.00, 0.04]

### complex (n=50)
- rca_correct: a=1.000 b=1.000 McNemar p=1.0000
- task_completed: a=1.000 b=1.000 McNemar p=1.0000
- token_cost: mean_diff=-34724.08 95% CI [-35291.52, -34182.74]
- latency_ms: mean_diff=-54.44 95% CI [-57.36, -51.54]
- tool_calls: mean_diff=-22.10 95% CI [-22.56, -21.66]
- evidence_completeness: mean_diff=0.01 95% CI [0.00, 0.03]

### failure_injection (n=20)
- rca_correct: a=1.000 b=1.000 McNemar p=1.0000
- task_completed: a=1.000 b=1.000 McNemar p=1.0000
- token_cost: mean_diff=-32986.95 95% CI [-33518.80, -32527.15]
- latency_ms: mean_diff=-40.55 95% CI [-49.90, -31.15]
- tool_calls: mean_diff=-21.80 95% CI [-22.05, -21.55]
- evidence_completeness: mean_diff=0.02 95% CI [0.00, 0.05]
