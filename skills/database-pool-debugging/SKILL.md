---
name: database-pool-debugging
description: 数据库连接池耗尽的识别、证据链与修复方案
when_to_use: db_pool_wait_ms / db_pool_active 异常升高，或日志出现 connection pool exhausted / timeout waiting for connection
tools: [query_metrics, query_logs, get_service_health]
safety: 禁止直接改数据库参数；先定位占用连接的慢查询
---

# Database Connection Pool Exhaustion Debugging

## 证据链
1. `query_metrics(service, "db_pool_active")`：接近 max_connections。
2. `query_metrics(service, "db_pool_wait_ms")`：显著 > 基线。
3. `query_logs` 聚类：`connection pool exhausted`、`timeout waiting for connection`、`connection acquisition timeout`。
4. 与历史 incident（HIST-002）比对。

## 常见根因
- 慢查询/全表扫描持有连接过久
- 事务未提交或锁等待
- 上游流量突增导致请求排队
- 池配置过小（max_connections 配置错误）
- 连接泄漏（客户端忘记 close）

## 诊断脚本（沙箱内）
```python
# 输入 metrics 结果，计算池饱和时间窗口
import json, sys
data = json.load(sys.stdin)
points = data["points"]
saturated = [p for p in points if p["value"] > 0.8 * data.get("max", 50)]
print(f"saturated_points={len(saturated)} first={saturated[0]['timestamp'] if saturated else None}")
```

## 修复方向
- 短期：扩容连接池（config change，L3 需审批）
- 中期：慢查询优化、增加索引、读写分离
- 长期：连接泄漏监控告警、池水位 dashboard
