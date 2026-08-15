---
name: incident-response
description: 通用故障响应流程：triage → observe → hypothesize → remediate → verify → postmortem
when_to_use: 用户报告任何服务故障、延迟升高、错误率升高、可用性下降
tools: [get_service_health, query_metrics, query_logs]
safety: read-only runbook；任何生产变更必须走 HITL 审批
---

# Incident Response Runbook

## 1. Triage
- 确认 service、environment、time range。
- 缺信息时触发 missing_info interrupt，不要猜测。

## 2. Observe
- `get_service_health` 获取当前状态与依赖健康。
- `query_metrics` 查 latency_p99_ms / error_rate / cpu_usage / memory_usage / saturation 指标。
- 用 anomaly window 圈定起点。

## 3. Hypothesize
- 指标偏离类型 → 候选根因：
  - latency ↑ + error_rate ↑ 且 deployment 刚发生 → bad deployment
  - db_pool_wait_ms ↑ → connection pool exhaustion
  - memory_usage 线性爬升 → memory leak
  - redis_p99_ms ↑ → cache timeout
  - upstream_p99_ms ↑ → dependency timeout
  - disk_usage → 100 → disk saturation
  - request_rate 5x 基线 → traffic spike
  - cpu_usage ~100 → cpu saturation
- 假设必须能被日志/变更证据支持或反驳。

## 4. Remediate
- 先安全动作（ticket、drain traffic、canary、runbook）。
- 生产变更必须由 Incident Commander 在 HITL approve 后执行。

## 5. Verify
- `verify_service_health` 恢复后确认。

## 6. Postmortem
- 时间线、根因、证据、动作、follow-ups。
