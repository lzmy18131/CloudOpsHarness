# CloudOps Harness Evaluation Results

tag: `deterministic-fake-llm-n110`
generated: 2026-08-21T06:29:28.080919Z
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
- mean_total_tokens: 4693.31
- mean_prompt_tokens: 0.00
- mean_completion_tokens: 0.00
- mean_latency_ms: 66.63
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
- mean_recovery_latency_ms: 210.8000
- mean_tool_calls: 27.45
- mean_llm_calls: 43.45
- mean_total_tokens: 38879.51
- mean_prompt_tokens: 0.00
- mean_completion_tokens: 0.00
- mean_latency_ms: 150.42
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
- mean_recovery_latency_ms: 207.8000
- mean_tool_calls: 27.45
- mean_llm_calls: 43.45
- mean_total_tokens: 38933.13
- mean_prompt_tokens: 0.00
- mean_completion_tokens: 0.00
- mean_latency_ms: 143.02
- mean_main_context_tokens: 1365.84

## harness

- n=110
- task_success_rate: 0.9545
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
- mean_recovery_latency_ms: 215.6000
- mean_tool_calls: 27.45
- mean_llm_calls: 43.45
- mean_total_tokens: 38876.15
- mean_prompt_tokens: 0.00
- mean_completion_tokens: 0.00
- mean_latency_ms: 141.22
- mean_main_context_tokens: 1319.90

## harness-no-recovery

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
- recovery_success_rate: 0.0000
- mean_tool_calls: 27.45
- mean_llm_calls: 43.45
- mean_total_tokens: 38869.63
- mean_prompt_tokens: 0.00
- mean_completion_tokens: 0.00
- mean_latency_ms: 113.36
- mean_main_context_tokens: 1319.90

## Paired comparisons

### single-agent vs harness
- rca_correct: a=1.000 b=1.000 discordant b=0 c=0 McNemar p=1.0000
- task_success: a=0.727 b=0.955 discordant b=5 c=30 McNemar p=0.0000
- unsafe_action: a=0.000 b=0.000 discordant b=0 c=0 McNemar p=1.0000
- tool_calls: mean_diff=-22.05 95% CI [-22.27, -21.83]
- llm_calls: mean_diff=-37.05 95% CI [-37.27, -36.83]
- total_tokens: mean_diff=-34182.84 95% CI [-34481.40, -33890.03]
- latency_ms: mean_diff=-74.59 95% CI [-79.94, -70.19]
- main_context_tokens: mean_diff=-1319.90 95% CI [-1324.49, -1315.49]
- unnecessary_tool_call_rate: mean_diff=-0.44 95% CI [-0.45, -0.42]
- delegation_accuracy: mean_diff=-0.80 95% CI [-0.81, -0.79]
- evidence_grounding_precision: mean_diff=-0.99 95% CI [-0.99, -0.98]

### multi-agent vs harness
- rca_correct: a=1.000 b=1.000 discordant b=0 c=0 McNemar p=1.0000
- task_success: a=0.864 b=0.955 discordant b=0 c=10 McNemar p=0.0020
- unsafe_action: a=0.091 b=0.000 discordant b=10 c=0 McNemar p=0.0020
- tool_calls: mean_diff=0.00 95% CI [0.00, 0.00]
- llm_calls: mean_diff=0.00 95% CI [0.00, 0.00]
- total_tokens: mean_diff=3.36 95% CI [-3.74, 10.59]
- latency_ms: mean_diff=9.20 95% CI [2.63, 15.20]
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
- total_tokens: mean_diff=-53.62 95% CI [-57.09, -50.24]
- latency_ms: mean_diff=7.40 95% CI [1.91, 12.87]
- main_context_tokens: mean_diff=-45.94 95% CI [-46.84, -45.06]
- unnecessary_tool_call_rate: mean_diff=0.00 95% CI [0.00, 0.00]
- delegation_accuracy: mean_diff=0.00 95% CI [0.00, 0.00]
- evidence_grounding_precision: mean_diff=0.00 95% CI [0.00, 0.00]

### harness-no-recovery vs harness
- rca_correct: a=1.000 b=1.000 discordant b=0 c=0 McNemar p=1.0000
- task_success: a=0.864 b=0.955 discordant b=0 c=10 McNemar p=0.0020
- unsafe_action: a=0.000 b=0.000 discordant b=0 c=0 McNemar p=1.0000
- recovery_success: a=0.000 b=1.000 discordant b=0 c=10 McNemar p=0.0020
- tool_calls: mean_diff=0.00 95% CI [0.00, 0.00]
- llm_calls: mean_diff=0.00 95% CI [0.00, 0.00]
- total_tokens: mean_diff=-6.52 95% CI [-13.16, -0.06]
- latency_ms: mean_diff=-27.85 95% CI [-42.36, -14.50]
- main_context_tokens: mean_diff=0.00 95% CI [0.00, 0.00]
- unnecessary_tool_call_rate: mean_diff=0.00 95% CI [0.00, 0.00]
- delegation_accuracy: mean_diff=0.00 95% CI [0.00, 0.00]
- evidence_grounding_precision: mean_diff=0.00 95% CI [0.00, 0.00]

## Bucket comparisons (single-agent vs harness)

### simple (n=20)
- rca_correct: a=1.000 b=1.000 McNemar p=1.0000
- task_success: a=1.000 b=0.950 McNemar p=1.0000
- total_tokens: mean_diff=-34790.30 95% CI [-35297.25, -34288.20]
- latency_ms: mean_diff=-73.40 95% CI [-80.35, -65.35]
- tool_calls: mean_diff=-22.40 95% CI [-22.70, -22.10]
- evidence_completeness: mean_diff=0.01 95% CI [0.00, 0.03]

### multi_source (n=10)
- rca_correct: a=1.000 b=1.000 McNemar p=1.0000
- task_success: a=1.000 b=1.000 McNemar p=1.0000
- total_tokens: mean_diff=-36840.80 95% CI [-37950.90, -35805.00]
- latency_ms: mean_diff=-68.70 95% CI [-78.30, -59.40]
- tool_calls: mean_diff=-24.90 95% CI [-25.20, -24.60]
- evidence_completeness: mean_diff=0.00 95% CI [0.00, 0.00]

### multi_hop (n=20)
- rca_correct: a=1.000 b=1.000 McNemar p=1.0000
- task_success: a=1.000 b=0.900 McNemar p=0.5000
- total_tokens: mean_diff=-33892.35 95% CI [-34360.20, -33433.60]
- latency_ms: mean_diff=-73.50 95% CI [-85.90, -64.80]
- tool_calls: mean_diff=-21.00 95% CI [-21.30, -20.75]
- evidence_completeness: mean_diff=0.02 95% CI [0.00, 0.04]

### complex (n=50)
- rca_correct: a=1.000 b=1.000 McNemar p=1.0000
- task_success: a=0.800 b=0.940 McNemar p=0.0923
- total_tokens: mean_diff=-34389.76 95% CI [-34918.92, -33877.40]
- latency_ms: mean_diff=-70.66 95% CI [-76.84, -65.32]
- tool_calls: mean_diff=-22.10 95% CI [-22.56, -21.66]
- evidence_completeness: mean_diff=0.01 95% CI [0.00, 0.03]

### failure_injection (n=20)
- rca_correct: a=1.000 b=1.000 McNemar p=1.0000
- task_success: a=0.500 b=1.000 McNemar p=0.0020
- total_tokens: mean_diff=-32721.70 95% CI [-33260.35, -32263.95]
- latency_ms: mean_diff=-79.70 95% CI [-103.65, -63.35]
- tool_calls: mean_diff=-21.80 95% CI [-22.05, -21.55]
- evidence_completeness: mean_diff=0.02 95% CI [0.00, 0.05]
