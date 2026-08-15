# AegisOps Evaluation Results

tag: `offline-fake-llm-n100`
generated: 2026-08-15T17:30:21.310380Z

## single-agent

- n=100
- root_cause_accuracy: 1.0000
- task_completion_rate: 1.0000
- tool_selection_accuracy: 1.0000
- evidence_completeness: 1.0000
- unsafe_action_rate: 0.1000
- unsafe_action_rate_dangerous: 1.0000
- hitl_compliance_rate: 0.0000
- recovery_success_rate: 0.0000
- mean_tool_calls: 5.63
- mean_llm_calls: 6.63
- mean_token_cost: 4975.60
- mean_latency_ms: 69.38

## multi-agent

- n=100
- root_cause_accuracy: 1.0000
- task_completion_rate: 1.0000
- tool_selection_accuracy: 0.9390
- evidence_completeness: 0.9262
- unsafe_action_rate: 0.1000
- unsafe_action_rate_dangerous: 1.0000
- hitl_compliance_rate: 0.0000
- recovery_success_rate: 1.0000
- mean_tool_calls: 27.10
- mean_llm_calls: 43.10
- mean_token_cost: 38032.64
- mean_latency_ms: 130.78

## multi-no-isolation

- n=100
- root_cause_accuracy: 1.0000
- task_completion_rate: 1.0000
- tool_selection_accuracy: 0.9390
- evidence_completeness: 0.9262
- unsafe_action_rate: 0.1000
- unsafe_action_rate_dangerous: 1.0000
- hitl_compliance_rate: 0.0000
- recovery_success_rate: 1.0000
- mean_tool_calls: 27.10
- mean_llm_calls: 43.10
- mean_token_cost: 38082.61
- mean_latency_ms: 134.36

## harness

- n=100
- root_cause_accuracy: 1.0000
- task_completion_rate: 1.0000
- tool_selection_accuracy: 0.9390
- evidence_completeness: 0.9262
- unsafe_action_rate: 0.0000
- unsafe_action_rate_dangerous: 0.0000
- hitl_compliance_rate: 1.0000
- recovery_success_rate: 1.0000
- mean_tool_calls: 27.00
- mean_llm_calls: 43.10
- mean_token_cost: 38043.02
- mean_latency_ms: 131.86

## harness-no-recovery

- n=100
- root_cause_accuracy: 1.0000
- task_completion_rate: 1.0000
- tool_selection_accuracy: 0.9390
- evidence_completeness: 0.9262
- unsafe_action_rate: 0.0000
- unsafe_action_rate_dangerous: 0.0000
- hitl_compliance_rate: 1.0000
- recovery_success_rate: 0.0000
- mean_tool_calls: 27.00
- mean_llm_calls: 43.10
- mean_token_cost: 38041.38
- mean_latency_ms: 113.60

## Paired comparisons

### single-agent vs harness
- rca_correct: a=1.000 b=1.000 discordant b=0 c=0 McNemar p=1.0000
- task_completed: a=1.000 b=1.000 discordant b=0 c=0 McNemar p=1.0000
- unsafe_action: a=0.100 b=0.000 discordant b=10 c=0 McNemar p=0.0020
- tool_calls: mean_diff=-21.37 95% CI [-21.50, -21.24]
- llm_calls: mean_diff=-36.47 95% CI [-36.61, -36.35]
- token_cost: mean_diff=-33067.42 95% CI [-33316.44, -32817.95]
- latency_ms: mean_diff=-62.48 95% CI [-69.20, -56.55]

### multi-agent vs harness
- rca_correct: a=1.000 b=1.000 discordant b=0 c=0 McNemar p=1.0000
- task_completed: a=1.000 b=1.000 discordant b=0 c=0 McNemar p=1.0000
- unsafe_action: a=0.100 b=0.000 discordant b=10 c=0 McNemar p=0.0020
- tool_calls: mean_diff=0.10 95% CI [0.05, 0.16]
- llm_calls: mean_diff=0.00 95% CI [0.00, 0.00]
- token_cost: mean_diff=-10.38 95% CI [-16.87, -3.75]
- latency_ms: mean_diff=-1.08 95% CI [-7.23, 4.23]

### multi-agent vs multi-no-isolation
- rca_correct: a=1.000 b=1.000 discordant b=0 c=0 McNemar p=1.0000
- task_completed: a=1.000 b=1.000 discordant b=0 c=0 McNemar p=1.0000
- unsafe_action: a=0.100 b=0.100 discordant b=0 c=0 McNemar p=1.0000
- tool_calls: mean_diff=0.00 95% CI [0.00, 0.00]
- llm_calls: mean_diff=0.00 95% CI [0.00, 0.00]
- token_cost: mean_diff=-49.97 95% CI [-54.09, -45.70]
- latency_ms: mean_diff=-3.58 95% CI [-10.26, 2.57]

### harness-no-recovery vs harness
- rca_correct: a=1.000 b=1.000 discordant b=0 c=0 McNemar p=1.0000
- task_completed: a=1.000 b=1.000 discordant b=0 c=0 McNemar p=1.0000
- unsafe_action: a=0.000 b=0.000 discordant b=0 c=0 McNemar p=1.0000
- recovery_success: a=0.000 b=1.000 discordant b=0 c=10 McNemar p=0.0020
- tool_calls: mean_diff=0.00 95% CI [0.00, 0.00]
- llm_calls: mean_diff=0.00 95% CI [0.00, 0.00]
- token_cost: mean_diff=-1.64 95% CI [-5.34, 2.02]
- latency_ms: mean_diff=-18.26 95% CI [-33.92, -3.74]
