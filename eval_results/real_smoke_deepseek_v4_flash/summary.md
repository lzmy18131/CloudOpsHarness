# CloudOps Harness Evaluation Results

tag: `real-llm-deepseek-v4-flash-n5-r1`
generated: 2026-08-21T09:24:07.812960Z
adapter_type: `real`
repeat: 1

## single-agent

- n=5
- task_success_rate: 0.4000
- rca_root_cause_accuracy: 0.4000
- rca_localization_accuracy: 1.0000
- rca_fault_type_accuracy: 0.4000
- root_cause_accuracy: 0.4000
- task_completion_rate: 1.0000
- tool_selection_accuracy: 0.9429
- tool_precision: 0.5127
- tool_recall: 0.9429
- tool_f1: 0.6553
- evidence_completeness: 1.0000
- evidence_grounding_precision: 0.0333
- evidence_recall: 0.0400
- unsupported_claim_rate: 0.9667
- unsafe_action_rate: 0.0000
- unsafe_action_rate_dangerous: 0.0000
- unsafe_execution_count: 0.0000
- hitl_compliance_rate: 1.0000
- hitl_recall: 1.0000
- hitl_precision: 1.0000
- decision_binding_accuracy: 1.0000
- resume_success_rate: 1.0000
- remediation_verification_rate: 0.0000
- mean_unnecessary_tool_call_rate: 0.3355
- mean_delegation_accuracy: 0.0000
- mean_tool_calls: 18.00
- mean_llm_calls: 7.20
- mean_total_tokens: 101670.40
- mean_prompt_tokens: 91842.20
- mean_completion_tokens: 9828.20
- mean_latency_ms: 64197.00
- mean_main_context_tokens: 0.00

## harness

- n=5
- task_success_rate: 0.0000
- rca_root_cause_accuracy: 0.0000
- rca_localization_accuracy: 0.0000
- rca_fault_type_accuracy: 0.0000
- root_cause_accuracy: 0.0000
- task_completion_rate: 0.0000
- tool_selection_accuracy: 0.8310
- tool_precision: 0.5402
- tool_recall: 0.8310
- tool_f1: 0.6502
- evidence_completeness: 1.0000
- evidence_grounding_precision: 0.0000
- evidence_recall: 0.0000
- unsupported_claim_rate: 0.0000
- unsafe_action_rate: 0.0000
- unsafe_action_rate_dangerous: 0.0000
- unsafe_execution_count: 0.0000
- hitl_compliance_rate: 1.0000
- hitl_recall: 1.0000
- hitl_precision: 1.0000
- decision_binding_accuracy: 1.0000
- resume_success_rate: 1.0000
- remediation_verification_rate: 0.0000
- mean_unnecessary_tool_call_rate: 0.0000
- mean_delegation_accuracy: 0.0000
- mean_tool_calls: 61.80
- mean_llm_calls: 23.80
- mean_total_tokens: 163968.80
- mean_prompt_tokens: 134144.80
- mean_completion_tokens: 29824.00
- mean_latency_ms: 171672.00
- mean_main_context_tokens: 0.00

## Paired comparisons

### single-agent vs harness
- rca_correct: a=0.400 b=0.000 discordant b=2 c=0 McNemar p=0.5000
- task_success: a=0.400 b=0.000 discordant b=2 c=0 McNemar p=0.5000
- unsafe_action: a=0.000 b=0.000 discordant b=0 c=0 McNemar p=1.0000
- tool_calls: mean_diff=-43.80 95% CI [-52.60, -34.80]
- llm_calls: mean_diff=-16.60 95% CI [-17.80, -15.40]
- total_tokens: mean_diff=-62298.40 95% CI [-97317.00, -22646.00]
- latency_ms: mean_diff=-107475.00 95% CI [-118187.40, -94772.40]
- main_context_tokens: mean_diff=0.00 95% CI [0.00, 0.00]
- unnecessary_tool_call_rate: mean_diff=0.34 95% CI [0.26, 0.43]
- delegation_accuracy: mean_diff=0.00 95% CI [0.00, 0.00]
- evidence_grounding_precision: mean_diff=0.03 95% CI [0.00, 0.10]

## Bucket comparisons (single-agent vs harness)

### simple (n=2)
- rca_correct: a=0.000 b=0.000 McNemar p=1.0000
- task_success: a=0.000 b=0.000 McNemar p=1.0000
- total_tokens: mean_diff=-58794.00 95% CI [-69963.00, -47625.00]
- latency_ms: mean_diff=-119695.50 95% CI [-123875.00, -115516.00]
- tool_calls: mean_diff=-49.50 95% CI [-59.00, -40.00]
- evidence_completeness: mean_diff=0.00 95% CI [0.00, 0.00]

### multi_source (n=1)
- rca_correct: a=1.000 b=0.000 McNemar p=1.0000
- task_success: a=1.000 b=0.000 McNemar p=1.0000
- total_tokens: mean_diff=-121823.00 95% CI [-121823.00, -121823.00]
- latency_ms: mean_diff=-112109.00 95% CI [-112109.00, -112109.00]
- tool_calls: mean_diff=-42.00 95% CI [-42.00, -42.00]
- evidence_completeness: mean_diff=0.00 95% CI [0.00, 0.00]

### multi_hop (n=2)
- rca_correct: a=0.500 b=0.000 McNemar p=1.0000
- task_success: a=0.500 b=0.000 McNemar p=1.0000
- total_tokens: mean_diff=-36040.50 95% CI [-86488.00, 14407.00]
- latency_ms: mean_diff=-92937.50 95% CI [-103796.00, -82079.00]
- tool_calls: mean_diff=-39.00 95% CI [-51.00, -27.00]
- evidence_completeness: mean_diff=0.00 95% CI [0.00, 0.00]

### complex (n=3)
- rca_correct: a=0.667 b=0.000 McNemar p=0.5000
- task_success: a=0.667 b=0.000 McNemar p=0.5000
- total_tokens: mean_diff=-64634.67 95% CI [-121823.00, 14407.00]
- latency_ms: mean_diff=-99328.00 95% CI [-112109.00, -82079.00]
- tool_calls: mean_diff=-40.00 95% CI [-51.00, -27.00]
- evidence_completeness: mean_diff=0.00 95% CI [0.00, 0.00]
