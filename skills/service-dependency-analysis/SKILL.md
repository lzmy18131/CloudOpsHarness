---
name: service-dependency-analysis
description: 服务依赖健康分析：拓扑、上下游饱和、级联故障识别
when_to_use: 多服务同时异常、怀疑级联故障或依赖超时
tools: [get_service_topology, get_service_health, query_metrics]
safety: read-only；不得修改拓扑或依赖配置
---

# Service Dependency Analysis

## 方法
1. `get_service_topology(service)` 获取一阶依赖。
2. 对每个下游 `get_service_health`：
   - 下游 degraded/down → 本服务异常可能是级联结果
3. 检查本服务对下游的调用指标 `upstream_p99_ms`。
4. 级联故障特征：多个上游服务同时 degraded，根因服务是最深依赖。

## 输出
- 依赖健康矩阵
- 根因候选排序（最深的 down 节点优先）
- 隔离建议：bulkhead、timeout budget、circuit breaker（改动需 HITL）

## 注意
不要只凭拓扑猜测；每个节点都要有 metric/log 证据。
