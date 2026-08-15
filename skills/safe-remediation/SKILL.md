---
name: safe-remediation
description: 安全修复决策：风险分级、先安全后生产、审批字段完整性
when_to_use: 需要制定修复方案时
tools: [get_service_health, get_current_release, verify_service_health]
safety: L2/L3 生产变更必须 HITL；reject 后必须给出替代方案
---

# Safe Remediation

## 风险分级
- L0 read-only：query/verify，自动执行
- L1 low-risk write：create_incident_ticket，可自动
- L2 production-changing：restart_service / scale_service，必须 HITL
- L3 high-risk destructive：rollback_release / apply_config_change，必须 HITL + reason + target + before-state + expected impact

## 原则
1. 先问：不改变生产能缓解吗？（ticket、告警、drain traffic、限流配置灰度）
2. 变更前记录 before-state（当前 release / replicas / config）。
3. 明确 expected impact 与回滚手段。
4. 每次只做一个变更；verify 通过再继续。
5. 用户 reject 后：不执行、记录 reject、给安全替代方案、继续完成报告。

## 输出
proposed_actions 必须包含：tool_name、arguments、risk_level、reason、target_environment、before_state、expected_impact。
