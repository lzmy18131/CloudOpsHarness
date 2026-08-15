---
name: memory-leak-analysis
description: 内存泄漏识别：memory_usage 线性爬升、GC 行为与堆分析入口
when_to_use: memory_usage 持续上升不回落、OOM kill、gc_pause_ms 增大
tools: [query_metrics, query_logs, get_service_health]
safety: 只做观察与建议；heap dump 属于高成本诊断，需与 owner 确认
---

# Memory Leak Analysis

## 识别
- `memory_usage` 呈 ramp 形状，不随流量下降而回落。
- `gc_pause_ms` 持续上升说明堆压力增大。
- 日志出现 `OutOfMemoryError` / `container killed (OOM)`。

## 与流量尖峰区分
- 流量尖峰：memory 随 request_rate 同步升降，回落基线。
- 泄漏：request_rate 回落但 memory 不回落。

## 分析步骤
1. 确定泄漏起点（ramp 起点时间）。
2. 对照 deployment 记录——泄漏常由最近版本引入。
3. 沙箱内对 GC 日志做线性拟合：
```python
import json, sys
data = json.load(sys.stdin)
xs, ys = [], []
for i, p in enumerate(data["points"]):
    xs.append(i); ys.append(p["value"])
n = len(xs)
mx, my = sum(xs)/n, sum(ys)/n
slope = sum((x-mx)*(y-my) for x, y in zip(xs, ys)) / max(sum((x-mx)**2 for x in xs), 1)
print(f"memory_ramp_slope={slope:.4f}")
```
4. 候选：metric label 基数爆炸、缓存无 TTL、goroutine/线程泄漏。

## 修复
- 回滚可疑版本（L3 需审批）
- 增加对象池上限或 TTL 配置（L3 需审批）
- 长期：CI 加入 GC/heap profiling gate
