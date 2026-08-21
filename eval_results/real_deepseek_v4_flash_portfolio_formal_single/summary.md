# CloudOps Harness Evaluation Results

tag: `real-llm-deepseek-v4-flash-n20-r1`
generated: 2026-08-21T10:43:52.876203Z
adapter_type: `real`
repeat: 1

## single-agent

- n=20
- task_success_rate: 0.0500
- rca_root_cause_accuracy: 0.0500
- rca_localization_accuracy: 0.9500
- rca_fault_type_accuracy: 0.1000
- root_cause_accuracy: 0.0500
- task_completion_rate: 0.9500
- tool_selection_accuracy: 0.8595
- tool_precision: 0.3949
- tool_recall: 0.8595
- tool_f1: 0.5345
- evidence_completeness: 0.9500
- evidence_grounding_precision: 0.4654
- evidence_recall: 0.7625
- unsupported_claim_rate: 0.4846
- unsafe_action_rate: 0.0000
- unsafe_action_rate_dangerous: 0.0000
- unsafe_execution_count: 0.0000
- hitl_compliance_rate: 0.0000
- hitl_recall: 0.0000
- hitl_precision: 1.0000
- decision_binding_accuracy: 1.0000
- resume_success_rate: 0.0000
- remediation_verification_rate: 0.0000
- mean_unnecessary_tool_call_rate: 0.3667
- mean_delegation_accuracy: 0.0000
- recovery_success_rate: 0.0000
- mean_tool_calls: 30.70
- mean_llm_calls: 10.85
- mean_total_tokens: 213641.55
- mean_prompt_tokens: 202062.10
- mean_completion_tokens: 11579.45
- mean_latency_ms: 89998.40
- mean_main_context_tokens: 0.00

## Paired comparisons

## Bucket comparisons (single-agent vs harness)
