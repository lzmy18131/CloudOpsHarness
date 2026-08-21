# CloudOps Harness Evaluation Results

tag: `deterministic-fake-llm-n110`
generated: 2026-08-21T06:23:29.452131Z
adapter_type: `fake`
repeat: 1

## single-agent

- n=110
- task_success_rate: 0.7273
- rca_root_cause_accuracy: 1.0000
- rca_localization_accuracy: 1.0000
- rca_fault_type_accuracy: 0.7273
- root_cause_accuracy: 1.0000
- task_completion_rate: 1.0000
- tool_selection_accuracy: 1.0000
- tool_precision: 1.0000
- tool_recall: 1.0000
- tool_f1: 1.0000
- evidence_completeness: 1.0000
- evidence_grounding_precision: 0.0000
- evidence_recall: 0.0000
- unsupported_claim_rate: 0.0000
- unsafe_action_rate: 0.0000
- unsafe_action_rate_dangerous: 0.0000
- unsafe_execution_count: 0.0000
- hitl_compliance_rate: 0.0000
- hitl_recall: 0.0000
- hitl_precision: 1.0000
- decision_binding_accuracy: 1.0000
- resume_success_rate: 0.0000
- remediation_verification_rate: 0.0000
- mean_unnecessary_tool_call_rate: 0.0000
- mean_delegation_accuracy: 0.0000
- recovery_success_rate: 0.0000
- mean_tool_calls: 5.41
- mean_llm_calls: 6.41
- mean_total_tokens: 4692.62
- mean_prompt_tokens: 0.00
- mean_completion_tokens: 0.00
- mean_latency_ms: 75.73
- mean_main_context_tokens: 0.00

## multi-agent

- n=110
- task_success_rate: 0.8636
- rca_root_cause_accuracy: 1.0000
- rca_localization_accuracy: 1.0000
- rca_fault_type_accuracy: 1.0000
- root_cause_accuracy: 1.0000
- task_completion_rate: 1.0000
- tool_selection_accuracy: 0.9870
- tool_precision: 0.5796
- tool_recall: 0.9870
- tool_f1: 0.7268
- evidence_completeness: 0.9842
- evidence_grounding_precision: 0.9870
- evidence_recall: 6.3621
- unsupported_claim_rate: 0.0130
- unsafe_action_rate: 0.0909
- unsafe_action_rate_dangerous: 1.0000
- unsafe_execution_count: 10.0000
- hitl_compliance_rate: 0.0000
- hitl_recall: 0.0000
- hitl_precision: 1.0000
- decision_binding_accuracy: 1.0000
- resume_success_rate: 1.0000
- remediation_verification_rate: 1.0000
- mean_unnecessary_tool_call_rate: 0.4362
- mean_delegation_accuracy: 0.7974
- recovery_success_rate: 1.0000
- mean_recovery_latency_ms: 227.9000
- mean_tool_calls: 27.45
- mean_llm_calls: 43.45
- mean_total_tokens: 38875.19
- mean_prompt_tokens: 0.00
- mean_completion_tokens: 0.00
- mean_latency_ms: 166.64
- mean_main_context_tokens: 1319.90

## multi-no-isolation

- n=110
- task_success_rate: 0.8636
- rca_root_cause_accuracy: 1.0000
- rca_localization_accuracy: 1.0000
- rca_fault_type_accuracy: 1.0000
- root_cause_accuracy: 1.0000
- task_completion_rate: 1.0000
- tool_selection_accuracy: 0.9870
- tool_precision: 0.5796
- tool_recall: 0.9870
- tool_f1: 0.7268
- evidence_completeness: 0.9842
- evidence_grounding_precision: 0.9870
- evidence_recall: 6.3621
- unsupported_claim_rate: 0.0130
- unsafe_action_rate: 0.0909
- unsafe_action_rate_dangerous: 1.0000
- unsafe_execution_count: 10.0000
- hitl_compliance_rate: 0.0000
- hitl_recall: 0.0000
- hitl_precision: 1.0000
- decision_binding_accuracy: 1.0000
- resume_success_rate: 1.0000
- remediation_verification_rate: 1.0000
- mean_unnecessary_tool_call_rate: 0.4362
- mean_delegation_accuracy: 0.7974
- recovery_success_rate: 1.0000
- mean_recovery_latency_ms: 237.4000
- mean_tool_calls: 27.45
- mean_llm_calls: 43.45
- mean_total_tokens: 38928.70
- mean_prompt_tokens: 0.00
- mean_completion_tokens: 0.00
- mean_latency_ms: 159.23
- mean_main_context_tokens: 1365.84

## harness

- n=110
- task_success_rate: 0.8636
- rca_root_cause_accuracy: 1.0000
- rca_localization_accuracy: 1.0000
- rca_fault_type_accuracy: 1.0000
- root_cause_accuracy: 1.0000
- task_completion_rate: 1.0000
- tool_selection_accuracy: 0.9870
- tool_precision: 0.5744
- tool_recall: 0.9870
- tool_f1: 0.7225
- evidence_completeness: 0.9842
- evidence_grounding_precision: 0.9870
- evidence_recall: 6.3621
- unsupported_claim_rate: 0.0130
- unsafe_action_rate: 0.0000
- unsafe_action_rate_dangerous: 0.0000
- unsafe_execution_count: 0.0000
- hitl_compliance_rate: 1.0000
- hitl_recall: 1.0000
- hitl_precision: 1.0000
- decision_binding_accuracy: 1.0000
- resume_success_rate: 1.0000
- remediation_verification_rate: 1.0000
- mean_unnecessary_tool_call_rate: 0.4362
- mean_delegation_accuracy: 0.7974
- recovery_success_rate: 1.0000
- mean_recovery_latency_ms: 223.6000
- mean_tool_calls: 27.45
- mean_llm_calls: 43.45
- mean_total_tokens: 38878.84
- mean_prompt_tokens: 0.00
- mean_completion_tokens: 0.00
- mean_latency_ms: 147.72
- mean_main_context_tokens: 1319.90

## harness-no-recovery

- n=110
- task_success_rate: 0.7727
- rca_root_cause_accuracy: 1.0000
- rca_localization_accuracy: 1.0000
- rca_fault_type_accuracy: 1.0000
- root_cause_accuracy: 1.0000
- task_completion_rate: 1.0000
- tool_selection_accuracy: 0.9870
- tool_precision: 0.5744
- tool_recall: 0.9870
- tool_f1: 0.7225
- evidence_completeness: 0.9842
- evidence_grounding_precision: 0.9870
- evidence_recall: 6.3621
- unsupported_claim_rate: 0.0130
- unsafe_action_rate: 0.0000
- unsafe_action_rate_dangerous: 0.0000
- unsafe_execution_count: 0.0000
- hitl_compliance_rate: 1.0000
- hitl_recall: 1.0000
- hitl_precision: 1.0000
- decision_binding_accuracy: 1.0000
- resume_success_rate: 1.0000
- remediation_verification_rate: 1.0000
- mean_unnecessary_tool_call_rate: 0.4362
- mean_delegation_accuracy: 0.7974
- recovery_success_rate: 0.0000
- mean_tool_calls: 27.45
- mean_llm_calls: 43.45
- mean_total_tokens: 38871.51
- mean_prompt_tokens: 0.00
- mean_completion_tokens: 0.00
- mean_latency_ms: 124.86
- mean_main_context_tokens: 1319.90

## Paired comparisons

### single-agent vs harness
- rca_correct: a=1.000 b=1.000 discordant b=0 c=0 McNemar p=1.0000
- task_success: a=0.727 b=0.864 discordant b=5 c=20 McNemar p=0.0041
- unsafe_action: a=0.000 b=0.000 discordant b=0 c=0 McNemar p=1.0000
- tool_calls: mean_diff=-22.05 95% CI [-22.27, -21.83]
- llm_calls: mean_diff=-37.05 95% CI [-37.27, -36.83]
- total_tokens: mean_diff=-34186.22 95% CI [-34483.14, -33895.09]
- latency_ms: mean_diff=-71.99 95% CI [-77.40, -67.07]
- main_context_tokens: mean_diff=-1319.90 95% CI [-1324.49, -1315.49]
- unnecessary_tool_call_rate: mean_diff=-0.44 95% CI [-0.45, -0.42]
- delegation_accuracy: mean_diff=-0.80 95% CI [-0.81, -0.79]
- evidence_grounding_precision: mean_diff=-0.99 95% CI [-0.99, -0.98]

### multi-agent vs harness
- rca_correct: a=1.000 b=1.000 discordant b=0 c=0 McNemar p=1.0000
- task_success: a=0.864 b=0.864 discordant b=0 c=0 McNemar p=1.0000
- unsafe_action: a=0.091 b=0.000 discordant b=10 c=0 McNemar p=0.0020
- tool_calls: mean_diff=0.00 95% CI [0.00, 0.00]
- llm_calls: mean_diff=0.00 95% CI [0.00, 0.00]
- total_tokens: mean_diff=-3.65 95% CI [-11.83, 4.54]
- latency_ms: mean_diff=18.92 95% CI [12.04, 25.56]
- main_context_tokens: mean_diff=0.00 95% CI [0.00, 0.00]
- unnecessary_tool_call_rate: mean_diff=0.00 95% CI [0.00, 0.00]
- delegation_accuracy: mean_diff=0.00 95% CI [0.00, 0.00]
- evidence_grounding_precision: mean_diff=0.00 95% CI [0.00, 0.00]

### multi-agent vs multi-no-isolation
- rca_correct: a=1.000 b=1.000 discordant b=0 c=0 McNemar p=1.0000
- task_success: a=0.864 b=0.864 discordant b=0 c=0 McNemar p=1.0000
- unsafe_action: a=0.091 b=0.091 discordant b=0 c=0 McNemar p=1.0000
- tool_calls: mean_diff=0.00 95% CI [0.00, 0.00]
- llm_calls: mean_diff=0.00 95% CI [0.00, 0.00]
- total_tokens: mean_diff=-53.51 95% CI [-57.48, -49.64]
- latency_ms: mean_diff=7.41 95% CI [0.70, 13.97]
- main_context_tokens: mean_diff=-45.94 95% CI [-46.84, -45.06]
- unnecessary_tool_call_rate: mean_diff=0.00 95% CI [0.00, 0.00]
- delegation_accuracy: mean_diff=0.00 95% CI [0.00, 0.00]
- evidence_grounding_precision: mean_diff=0.00 95% CI [0.00, 0.00]

### harness-no-recovery vs harness
- rca_correct: a=1.000 b=1.000 discordant b=0 c=0 McNemar p=1.0000
- task_success: a=0.773 b=0.864 discordant b=0 c=10 McNemar p=0.0020
- unsafe_action: a=0.000 b=0.000 discordant b=0 c=0 McNemar p=1.0000
- recovery_success: a=0.000 b=1.000 discordant b=0 c=10 McNemar p=0.0020
- tool_calls: mean_diff=0.00 95% CI [0.00, 0.00]
- llm_calls: mean_diff=0.00 95% CI [0.00, 0.00]
- total_tokens: mean_diff=-7.33 95% CI [-14.28, -1.45]
- latency_ms: mean_diff=-22.85 95% CI [-35.76, -10.44]
- main_context_tokens: mean_diff=0.00 95% CI [0.00, 0.00]
- unnecessary_tool_call_rate: mean_diff=0.00 95% CI [0.00, 0.00]
- delegation_accuracy: mean_diff=0.00 95% CI [0.00, 0.00]
- evidence_grounding_precision: mean_diff=0.00 95% CI [0.00, 0.00]

## Bucket comparisons (single-agent vs harness)

### simple (n=20)
- rca_correct: a=1.000 b=1.000 McNemar p=1.0000
- task_success: a=1.000 b=0.950 McNemar p=1.0000
- total_tokens: mean_diff=-34793.65 95% CI [-35297.15, -34297.10]
- latency_ms: mean_diff=-85.90 95% CI [-103.10, -74.30]
- tool_calls: mean_diff=-22.40 95% CI [-22.70, -22.10]
- evidence_completeness: mean_diff=0.01 95% CI [0.00, 0.03]

### multi_source (n=10)
- rca_correct: a=1.000 b=1.000 McNemar p=1.0000
- task_success: a=1.000 b=1.000 McNemar p=1.0000
- total_tokens: mean_diff=-36848.10 95% CI [-37958.00, -35821.70]
- latency_ms: mean_diff=-67.20 95% CI [-77.90, -56.90]
- tool_calls: mean_diff=-24.90 95% CI [-25.20, -24.60]
- evidence_completeness: mean_diff=0.00 95% CI [0.00, 0.00]

### multi_hop (n=20)
- rca_correct: a=1.000 b=1.000 McNemar p=1.0000
- task_success: a=1.000 b=0.900 McNemar p=0.5000
- total_tokens: mean_diff=-33896.80 95% CI [-34363.40, -33439.90]
- latency_ms: mean_diff=-64.85 95% CI [-70.35, -58.60]
- tool_calls: mean_diff=-21.00 95% CI [-21.30, -20.75]
- evidence_completeness: mean_diff=0.02 95% CI [0.00, 0.04]

### complex (n=50)
- rca_correct: a=1.000 b=1.000 McNemar p=1.0000
- task_success: a=0.800 b=0.740 McNemar p=0.2500
- total_tokens: mean_diff=-34393.98 95% CI [-34922.84, -33881.70]
- latency_ms: mean_diff=-69.40 95% CI [-73.12, -65.26]
- tool_calls: mean_diff=-22.10 95% CI [-22.56, -21.66]
- evidence_completeness: mean_diff=0.01 95% CI [0.00, 0.03]

### failure_injection (n=20)
- rca_correct: a=1.000 b=1.000 McNemar p=1.0000
- task_success: a=0.500 b=1.000 McNemar p=0.0020
- total_tokens: mean_diff=-32726.00 95% CI [-33263.40, -32268.40]
- latency_ms: mean_diff=-53.85 95% CI [-62.50, -45.25]
- tool_calls: mean_diff=-21.80 95% CI [-22.05, -21.55]
- evidence_completeness: mean_diff=0.02 95% CI [0.00, 0.05]
