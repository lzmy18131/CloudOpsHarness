# CloudOps Harness Evaluation Results

tag: `offline-fake-llm-n110`
generated: 2026-08-16T06:06:13.437408Z

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
- mean_token_cost: 4803.36
- mean_latency_ms: 60.07
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
- mean_recovery_latency_ms: 171.7000
- mean_tool_calls: 27.45
- mean_llm_calls: 43.45
- mean_token_cost: 39278.21
- mean_latency_ms: 127.85
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
- mean_recovery_latency_ms: 170.3000
- mean_tool_calls: 27.45
- mean_llm_calls: 43.45
- mean_token_cost: 39335.22
- mean_latency_ms: 124.43
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
- mean_recovery_latency_ms: 173.6000
- mean_tool_calls: 27.45
- mean_llm_calls: 43.45
- mean_token_cost: 39286.18
- mean_latency_ms: 126.15
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
- mean_token_cost: 39275.42
- mean_latency_ms: 110.23
- mean_main_context_tokens: 1326.90

## Paired comparisons

### single-agent vs harness
- rca_correct: a=1.000 b=1.000 discordant b=0 c=0 McNemar p=1.0000
- task_completed: a=1.000 b=1.000 discordant b=0 c=0 McNemar p=1.0000
- unsafe_action: a=0.091 b=0.000 discordant b=10 c=0 McNemar p=0.0020
- tool_calls: mean_diff=-22.05 95% CI [-22.27, -21.83]
- llm_calls: mean_diff=-37.05 95% CI [-37.27, -36.83]
- token_cost: mean_diff=-34482.82 95% CI [-34790.90, -34185.25]
- latency_ms: mean_diff=-66.07 95% CI [-71.97, -61.04]
- main_context_tokens: mean_diff=-1326.90 95% CI [-1331.49, -1322.49]
- unnecessary_tool_call_rate: mean_diff=-0.43 95% CI [-0.44, -0.41]
- delegation_accuracy: mean_diff=-0.80 95% CI [-0.81, -0.79]

### multi-agent vs harness
- rca_correct: a=1.000 b=1.000 discordant b=0 c=0 McNemar p=1.0000
- task_completed: a=1.000 b=1.000 discordant b=0 c=0 McNemar p=1.0000
- unsafe_action: a=0.091 b=0.000 discordant b=10 c=0 McNemar p=0.0020
- tool_calls: mean_diff=0.00 95% CI [0.00, 0.00]
- llm_calls: mean_diff=0.00 95% CI [0.00, 0.00]
- token_cost: mean_diff=-7.97 95% CI [-14.91, -0.95]
- latency_ms: mean_diff=1.70 95% CI [-4.47, 7.03]
- main_context_tokens: mean_diff=0.00 95% CI [0.00, 0.00]
- unnecessary_tool_call_rate: mean_diff=-0.01 95% CI [-0.01, -0.00]
- delegation_accuracy: mean_diff=0.00 95% CI [0.00, 0.00]

### multi-agent vs multi-no-isolation
- rca_correct: a=1.000 b=1.000 discordant b=0 c=0 McNemar p=1.0000
- task_completed: a=1.000 b=1.000 discordant b=0 c=0 McNemar p=1.0000
- unsafe_action: a=0.091 b=0.091 discordant b=0 c=0 McNemar p=1.0000
- tool_calls: mean_diff=0.00 95% CI [0.00, 0.00]
- llm_calls: mean_diff=0.00 95% CI [0.00, 0.00]
- token_cost: mean_diff=-57.01 95% CI [-60.13, -53.92]
- latency_ms: mean_diff=3.42 95% CI [-1.89, 8.35]
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
- token_cost: mean_diff=-10.76 95% CI [-17.20, -4.65]
- latency_ms: mean_diff=-15.92 95% CI [-27.04, -4.94]
- main_context_tokens: mean_diff=0.00 95% CI [0.00, 0.00]
- unnecessary_tool_call_rate: mean_diff=0.00 95% CI [0.00, 0.00]
- delegation_accuracy: mean_diff=0.00 95% CI [0.00, 0.00]

## Bucket comparisons (single-agent vs harness)

### simple (n=20)
- rca_correct: a=1.000 b=1.000 McNemar p=1.0000
- task_completed: a=1.000 b=1.000 McNemar p=1.0000
- token_cost: mean_diff=-35057.70 95% CI [-35553.95, -34572.45]
- latency_ms: mean_diff=-61.80 95% CI [-71.35, -50.80]
- tool_calls: mean_diff=-22.40 95% CI [-22.70, -22.10]
- evidence_completeness: mean_diff=0.01 95% CI [0.00, 0.03]

### multi_source (n=10)
- rca_correct: a=1.000 b=1.000 McNemar p=1.0000
- task_completed: a=1.000 b=1.000 McNemar p=1.0000
- token_cost: mean_diff=-37483.50 95% CI [-38674.30, -36397.80]
- latency_ms: mean_diff=-64.10 95% CI [-71.90, -56.30]
- tool_calls: mean_diff=-24.90 95% CI [-25.20, -24.60]
- evidence_completeness: mean_diff=0.00 95% CI [0.00, 0.00]

### multi_hop (n=20)
- rca_correct: a=1.000 b=1.000 McNemar p=1.0000
- task_completed: a=1.000 b=1.000 McNemar p=1.0000
- token_cost: mean_diff=-34152.50 95% CI [-34618.15, -33698.20]
- latency_ms: mean_diff=-72.85 95% CI [-97.00, -54.85]
- tool_calls: mean_diff=-21.00 95% CI [-21.30, -20.75]
- evidence_completeness: mean_diff=0.02 95% CI [0.00, 0.04]

### complex (n=50)
- rca_correct: a=1.000 b=1.000 McNemar p=1.0000
- task_completed: a=1.000 b=1.000 McNemar p=1.0000
- token_cost: mean_diff=-34730.60 95% CI [-35298.30, -34190.14]
- latency_ms: mean_diff=-70.72 95% CI [-82.18, -61.72]
- tool_calls: mean_diff=-22.10 95% CI [-22.56, -21.66]
- evidence_completeness: mean_diff=0.01 95% CI [0.00, 0.03]

### failure_injection (n=20)
- rca_correct: a=1.000 b=1.000 McNemar p=1.0000
- task_completed: a=1.000 b=1.000 McNemar p=1.0000
- token_cost: mean_diff=-32990.00 95% CI [-33526.50, -32527.55]
- latency_ms: mean_diff=-59.40 95% CI [-67.25, -50.90]
- tool_calls: mean_diff=-21.80 95% CI [-22.05, -21.55]
- evidence_completeness: mean_diff=0.02 95% CI [0.00, 0.05]
