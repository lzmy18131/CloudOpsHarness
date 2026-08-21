# CloudOps Harness Evaluation Results

tag: `real-llm-deepseek-v4-flash-n10-r1`
generated: 2026-08-21T11:34:18.191388Z
adapter_type: `real`
repeat: 1

## single-agent

- n=10
- task_success_rate: 0.1000
- rca_root_cause_accuracy: 0.1000
- rca_localization_accuracy: 1.0000
- rca_fault_type_accuracy: 0.1000
- root_cause_accuracy: 0.1000
- task_completion_rate: 1.0000
- tool_selection_accuracy: 0.9357
- tool_precision: 0.4286
- tool_recall: 0.9357
- tool_f1: 0.5790
- evidence_completeness: 1.0000
- evidence_grounding_precision: 0.6269
- evidence_recall: 1.0467
- unsupported_claim_rate: 0.3731
- unsafe_action_rate: 0.0000
- unsafe_action_rate_dangerous: 0.0000
- unsafe_execution_count: 0.0000
- hitl_compliance_rate: 0.0000
- hitl_recall: 0.0000
- hitl_precision: 1.0000
- decision_binding_accuracy: 1.0000
- resume_success_rate: 1.0000
- remediation_verification_rate: 0.0000
- mean_unnecessary_tool_call_rate: 0.3773
- mean_delegation_accuracy: 0.0000
- recovery_success_rate: 0.0000
- mean_tool_calls: 33.50
- mean_llm_calls: 12.10
- mean_total_tokens: 317283.90
- mean_prompt_tokens: 303189.90
- mean_completion_tokens: 14094.00
- mean_latency_ms: 112465.60
- mean_main_context_tokens: 0.00

## Paired comparisons

## Bucket comparisons (single-agent vs harness)
