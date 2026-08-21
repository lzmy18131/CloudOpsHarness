# CloudOps Harness Evaluation Results

tag: `real-llm-deepseek-v4-flash-n5-r1`
generated: 2026-08-21T10:12:37.626641Z
adapter_type: `real`
repeat: 1

## single-agent

- n=5
- task_success_rate: 0.0000
- rca_root_cause_accuracy: 0.0000
- rca_localization_accuracy: 1.0000
- rca_fault_type_accuracy: 0.2000
- root_cause_accuracy: 0.0000
- task_completion_rate: 1.0000
- tool_selection_accuracy: 0.9429
- tool_precision: 0.4771
- tool_recall: 0.9429
- tool_f1: 0.6227
- evidence_completeness: 1.0000
- evidence_grounding_precision: 0.4286
- evidence_recall: 0.9333
- unsupported_claim_rate: 0.5714
- unsafe_action_rate: 0.0000
- unsafe_action_rate_dangerous: 0.0000
- unsafe_execution_count: 0.0000
- hitl_compliance_rate: 0.0000
- hitl_recall: 0.0000
- hitl_precision: 1.0000
- decision_binding_accuracy: 1.0000
- resume_success_rate: 1.0000
- remediation_verification_rate: 0.0000
- mean_unnecessary_tool_call_rate: 0.4156
- mean_delegation_accuracy: 0.0000
- recovery_success_rate: 0.0000
- mean_tool_calls: 23.20
- mean_llm_calls: 9.20
- mean_total_tokens: 162068.20
- mean_prompt_tokens: 150520.60
- mean_completion_tokens: 11547.60
- mean_latency_ms: 87940.60
- mean_main_context_tokens: 0.00

## harness

- n=5
- task_success_rate: 0.2000
- rca_root_cause_accuracy: 0.0000
- rca_localization_accuracy: 1.0000
- rca_fault_type_accuracy: 0.2000
- root_cause_accuracy: 0.0000
- task_completion_rate: 1.0000
- tool_selection_accuracy: 0.8310
- tool_precision: 0.4115
- tool_recall: 0.8310
- tool_f1: 0.5466
- evidence_completeness: 1.0000
- evidence_grounding_precision: 0.0333
- evidence_recall: 0.0667
- unsupported_claim_rate: 0.9667
- unsafe_action_rate: 0.0000
- unsafe_action_rate_dangerous: 0.0000
- unsafe_execution_count: 0.0000
- hitl_compliance_rate: 0.0000
- hitl_recall: 0.0000
- hitl_precision: 1.0000
- decision_binding_accuracy: 1.0000
- resume_success_rate: 1.0000
- remediation_verification_rate: 0.0000
- mean_unnecessary_tool_call_rate: 0.3005
- mean_delegation_accuracy: 0.8024
- recovery_success_rate: 1.0000
- mean_tool_calls: 75.00
- mean_llm_calls: 32.20
- mean_total_tokens: 199208.20
- mean_prompt_tokens: 154944.40
- mean_completion_tokens: 44263.80
- mean_latency_ms: 284168.80
- mean_main_context_tokens: 1355.40

## Paired comparisons

### single-agent vs harness
- rca_correct: a=0.000 b=0.000 discordant b=0 c=0 McNemar p=1.0000
- task_success: a=0.000 b=0.200 discordant b=0 c=1 McNemar p=1.0000
- unsafe_action: a=0.000 b=0.000 discordant b=0 c=0 McNemar p=1.0000
- tool_calls: mean_diff=-51.80 95% CI [-59.40, -42.40]
- llm_calls: mean_diff=-23.00 95% CI [-24.60, -21.40]
- total_tokens: mean_diff=-37140.00 95% CI [-125072.00, 98027.00]
- latency_ms: mean_diff=-196228.20 95% CI [-264353.00, -138234.40]
- main_context_tokens: mean_diff=-1355.40 95% CI [-1400.60, -1309.40]
- unnecessary_tool_call_rate: mean_diff=0.12 95% CI [0.01, 0.25]
- delegation_accuracy: mean_diff=-0.80 95% CI [-0.85, -0.75]
- evidence_grounding_precision: mean_diff=0.40 95% CI [0.03, 0.77]

## Bucket comparisons (single-agent vs harness)

### simple (n=1)
- rca_correct: a=0.000 b=0.000 McNemar p=1.0000
- task_success: a=0.000 b=0.000 McNemar p=1.0000
- total_tokens: mean_diff=236254.00 95% CI [236254.00, 236254.00]
- latency_ms: mean_diff=-96203.00 95% CI [-96203.00, -96203.00]
- tool_calls: mean_diff=-34.00 95% CI [-34.00, -34.00]
- evidence_completeness: mean_diff=0.00 95% CI [0.00, 0.00]

### multi_source (n=1)
- rca_correct: a=0.000 b=0.000 McNemar p=1.0000
- task_success: a=0.000 b=0.000 McNemar p=1.0000
- total_tokens: mean_diff=-142515.00 95% CI [-142515.00, -142515.00]
- latency_ms: mean_diff=-204078.00 95% CI [-204078.00, -204078.00]
- tool_calls: mean_diff=-61.00 95% CI [-61.00, -61.00]
- evidence_completeness: mean_diff=0.00 95% CI [0.00, 0.00]

### multi_hop (n=1)
- rca_correct: a=0.000 b=0.000 McNemar p=1.0000
- task_success: a=0.000 b=0.000 McNemar p=1.0000
- total_tokens: mean_diff=-76112.00 95% CI [-76112.00, -76112.00]
- latency_ms: mean_diff=-198485.00 95% CI [-198485.00, -198485.00]
- tool_calls: mean_diff=-49.00 95% CI [-49.00, -49.00]
- evidence_completeness: mean_diff=0.00 95% CI [0.00, 0.00]

### complex (n=3)
- rca_correct: a=0.000 b=0.000 McNemar p=1.0000
- task_success: a=0.000 b=0.000 McNemar p=1.0000
- total_tokens: mean_diff=-114566.33 95% CI [-142515.00, -76112.00]
- latency_ms: mean_diff=-240073.00 95% CI [-317656.00, -198485.00]
- tool_calls: mean_diff=-56.67 95% CI [-61.00, -49.00]
- evidence_completeness: mean_diff=0.00 95% CI [0.00, 0.00]

### failure_injection (n=1)
- rca_correct: a=0.000 b=0.000 McNemar p=1.0000
- task_success: a=0.000 b=1.000 McNemar p=1.0000
- total_tokens: mean_diff=-78255.00 95% CI [-78255.00, -78255.00]
- latency_ms: mean_diff=-164719.00 95% CI [-164719.00, -164719.00]
- tool_calls: mean_diff=-55.00 95% CI [-55.00, -55.00]
- evidence_completeness: mean_diff=0.00 95% CI [0.00, 0.00]
