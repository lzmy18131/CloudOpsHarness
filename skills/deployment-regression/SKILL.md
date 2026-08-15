---
name: deployment-regression
description: 部署回归分析：release diff、config diff、rollout 时间与故障时间相关性
when_to_use: 故障与最近发布/配置变更可能相关
tools: [get_recent_deployments, get_config_diff, get_current_release, get_incident_history]
safety: 只判断相关性与因果证据；回滚必须走 HITL
---

# Deployment Regression Analysis

## 回答的核心问题
> 故障是否与最近变更存在时间相关性和因果证据？

## 步骤
1. `get_recent_deployments`：拿最近 3 个 release 的 deployed_at、trigger、notes。
2. 比较 anomaly_start 与 deployed_at：间隔 < 15 分钟 → 时间相关性高。
3. `get_config_diff(from, to)`：逐条检查配置语义变化。
4. 因果证据（时间相关性之外）：
   - 新版本专属日志模式在 anomaly window 密集出现
   - 回滚到旧版本后（历史上）指标恢复
   - config diff 直接改动池大小/超时/重试次数

## 输出
- 变更列表 + 时间相关性评分
- 因果证据或明确说明“仅时间相关，无因果证据”
- 建议：观察 / canary / 回滚（风险分级）
