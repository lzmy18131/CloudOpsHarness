---
name: latency-analysis
description: P99/P95 延迟升高分析方法：分层定位、异常窗口、相关信号
when_to_use: latency_p99_ms / latency_p50_ms 异常，或用户报告卡顿、超时
tools: [query_metrics, query_logs, get_service_topology]
safety: read-only 分析；不直接 restart/rollback
---

# Latency Analysis

## 1. 画形状
- step：变更后瞬间抬高 → 部署/配置相关
- spike：瞬时冲高回落 → 流量/缓存失效
- ramp：持续爬升 → 资源饱和/泄漏

## 2. 分层
- 先看自身：cpu、memory、queue_depth、thread_pool_active
- 再看依赖：upstream_p99_ms、redis_p99_ms、db_pool_wait_ms
- `get_service_topology` 确认依赖方向，避免把下游故障归因到本服务

## 3. 关联
- 时间轴对齐：anomaly window vs deployment time vs config change time
- 日志聚类：timeout 出现的位置（inbound / outbound / db / cache）

## 4. 输出
- 结构化报告：anomaly_start、signals、hypotheses（带证据）、confidence
- 不要输出原始日志给 Incident Commander
