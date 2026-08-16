# AegisOps Evaluation Results

tag: `offline-fake-llm-n110`
generated: 2026-08-16T03:09:45.235423Z

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
- mean_token_cost: 4799.23
- mean_latency_ms: 56.83
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
- mean_token_cost: 39171.46
- mean_latency_ms: 121.31
- mean_main_context_tokens: 1324.90

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
- mean_recovery_latency_ms: 173.4000
- mean_tool_calls: 27.45
- mean_llm_calls: 43.45
- mean_token_cost: 39221.65
- mean_latency_ms: 124.85
- mean_main_context_tokens: 1368.84

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
- mean_unnecessary_tool_call_rate: 0.4204
- mean_delegation_accuracy: 0.7974
- recovery_success_rate: 1.0000
- mean_recovery_latency_ms: 159.5000
- mean_tool_calls: 27.36
- mean_llm_calls: 43.45
- mean_token_cost: 39172.81
- mean_latency_ms: 123.74
- mean_main_context_tokens: 1324.90

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
- mean_unnecessary_tool_call_rate: 0.4204
- mean_delegation_accuracy: 0.7974
- recovery_success_rate: 0.0000
- mean_tool_calls: 27.36
- mean_llm_calls: 43.45
- mean_token_cost: 39170.38
- mean_latency_ms: 109.23
- mean_main_context_tokens: 1324.90

## Paired comparisons

### single-agent vs harness
- rca_correct: a=1.000 b=1.000 discordant b=0 c=0 McNemar p=1.0000
- task_completed: a=1.000 b=1.000 discordant b=0 c=0 McNemar p=1.0000
- unsafe_action: a=0.091 b=0.000 discordant b=10 c=0 McNemar p=0.0020
- tool_calls: mean_diff=-21.95 95% CI [-22.18, -21.74]
- llm_calls: mean_diff=-37.05 95% CI [-37.27, -36.83]
- token_cost: mean_diff=-34373.58 95% CI [-34681.35, -34075.07]
- latency_ms: mean_diff=-66.91 95% CI [-71.73, -62.65]
- main_context_tokens: mean_diff=-1324.90 95% CI [-1329.49, -1320.49]
- unnecessary_tool_call_rate: mean_diff=-0.42 95% CI [-0.44, -0.41]
- delegation_accuracy: mean_diff=-0.80 95% CI [-0.81, -0.79]

### multi-agent vs harness
- rca_correct: a=1.000 b=1.000 discordant b=0 c=0 McNemar p=1.0000
- task_completed: a=1.000 b=1.000 discordant b=0 c=0 McNemar p=1.0000
- unsafe_action: a=0.091 b=0.000 discordant b=10 c=0 McNemar p=0.0020
- tool_calls: mean_diff=0.09 95% CI [0.05, 0.15]
- llm_calls: mean_diff=0.00 95% CI [0.00, 0.00]
- token_cost: mean_diff=-1.35 95% CI [-8.96, 6.16]
- latency_ms: mean_diff=-2.43 95% CI [-7.51, 2.24]
- main_context_tokens: mean_diff=0.00 95% CI [0.00, 0.00]
- unnecessary_tool_call_rate: mean_diff=0.00 95% CI [0.00, 0.00]
- delegation_accuracy: mean_diff=0.00 95% CI [0.00, 0.00]

### multi-agent vs multi-no-isolation
- rca_correct: a=1.000 b=1.000 discordant b=0 c=0 McNemar p=1.0000
- task_completed: a=1.000 b=1.000 discordant b=0 c=0 McNemar p=1.0000
- unsafe_action: a=0.091 b=0.091 discordant b=0 c=0 McNemar p=1.0000
- tool_calls: mean_diff=0.00 95% CI [0.00, 0.00]
- llm_calls: mean_diff=0.00 95% CI [0.00, 0.00]
- token_cost: mean_diff=-50.19 95% CI [-54.24, -46.37]
- latency_ms: mean_diff=-3.55 95% CI [-11.13, 2.40]
- main_context_tokens: mean_diff=-43.94 95% CI [-44.84, -43.06]
- unnecessary_tool_call_rate: mean_diff=0.00 95% CI [0.00, 0.00]
- delegation_accuracy: mean_diff=0.00 95% CI [0.00, 0.00]

### harness-no-recovery vs harness
- rca_correct: a=1.000 b=1.000 discordant b=0 c=0 McNemar p=1.0000
- task_completed: a=1.000 b=1.000 discordant b=0 c=0 McNemar p=1.0000
- unsafe_action: a=0.000 b=0.000 discordant b=0 c=0 McNemar p=1.0000
- recovery_success: a=0.000 b=1.000 discordant b=0 c=10 McNemar p=0.0020
- tool_calls: mean_diff=0.00 95% CI [0.00, 0.00]
- llm_calls: mean_diff=0.00 95% CI [0.00, 0.00]
- token_cost: mean_diff=-2.43 95% CI [-6.31, 1.27]
- latency_ms: mean_diff=-14.51 95% CI [-25.93, -4.26]
- main_context_tokens: mean_diff=0.00 95% CI [0.00, 0.00]
- unnecessary_tool_call_rate: mean_diff=0.00 95% CI [0.00, 0.00]
- delegation_accuracy: mean_diff=0.00 95% CI [0.00, 0.00]

## Bucket comparisons (single-agent vs harness)

### simple (n=20)
- rca_correct: a=1.000 b=1.000 McNemar p=1.0000
- task_completed: a=1.000 b=1.000 McNemar p=1.0000
- token_cost: mean_diff=-34952.10 95% CI [-35452.50, -34462.70]
- latency_ms: mean_diff=-67.30 95% CI [-76.15, -58.65]
- tool_calls: mean_diff=-22.40 95% CI [-22.70, -22.10]
- evidence_completeness: mean_diff=0.01 95% CI [0.00, 0.03]

### multi_source (n=10)
- rca_correct: a=1.000 b=1.000 McNemar p=1.0000
- task_completed: a=1.000 b=1.000 McNemar p=1.0000
- token_cost: mean_diff=-37368.80 95% CI [-38561.70, -36274.90]
- latency_ms: mean_diff=-59.40 95% CI [-65.80, -53.30]
- tool_calls: mean_diff=-24.90 95% CI [-25.20, -24.60]
- evidence_completeness: mean_diff=0.00 95% CI [0.00, 0.00]

### multi_hop (n=20)
- rca_correct: a=1.000 b=1.000 McNemar p=1.0000
- task_completed: a=1.000 b=1.000 McNemar p=1.0000
- token_cost: mean_diff=-34052.15 95% CI [-34521.05, -33596.90]
- latency_ms: mean_diff=-60.85 95% CI [-65.95, -56.25]
- tool_calls: mean_diff=-21.00 95% CI [-21.30, -20.75]
- evidence_completeness: mean_diff=0.02 95% CI [0.00, 0.04]

### complex (n=50)
- rca_correct: a=1.000 b=1.000 McNemar p=1.0000
- task_completed: a=1.000 b=1.000 McNemar p=1.0000
- token_cost: mean_diff=-34623.76 95% CI [-35192.84, -34081.56]
- latency_ms: mean_diff=-68.70 95% CI [-77.78, -61.94]
- tool_calls: mean_diff=-21.90 95% CI [-22.40, -21.44]
- evidence_completeness: mean_diff=0.01 95% CI [0.00, 0.03]

### failure_injection (n=20)
- rca_correct: a=1.000 b=1.000 McNemar p=1.0000
- task_completed: a=1.000 b=1.000 McNemar p=1.0000
- token_cost: mean_diff=-32863.80 95% CI [-33397.30, -32406.45]
- latency_ms: mean_diff=-61.05 95% CI [-68.80, -53.15]
- tool_calls: mean_diff=-21.80 95% CI [-22.05, -21.55]
- evidence_completeness: mean_diff=0.02 95% CI [0.00, 0.05]
